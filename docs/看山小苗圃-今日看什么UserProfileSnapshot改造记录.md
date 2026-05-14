# 今日看什么 — UserProfileSnapshot 改造记录

更新时间：2026-05-13（第二轮更新）

## 1. 改造目标

将 content-service 的卡片获取流程从"请求时实时调用 profile-service"改为"后台同步用户快照 + 请求时本地选卡"，实现：

- 请求时零外部 HTTP 调用（profile-service 不可用时仍能工作）
- 用户画像、兴趣 Memory、已展示卡片等信息落盘为中间状态
- 为后续个性化评分和关注流缓存打下基础

## 2. 架构变更

### 改造前

```
GET /content?interest_ids=shuma,zhichang
  → content-service 收到 interest_ids（由 api-gateway 从 profile-service 获取）
  → 从系统内容池过滤
  → 返回卡片（无 Memory 评分上下文）
```

问题：
- interest_ids 由 api-gateway 实时调用 profile-service 解析，profile-service 挂了整个链路断
- content-service 无法使用 interestMemory 做个性化评分
- 已展示卡片跟踪使用全局 Redis set，不区分用户

### 改造后

```
后台（启动时 + 每 24h）:
  profile-service /profiles/me
    → build_snapshot_from_profile()
    → SnapshotRepository.save_snapshot()
    → 写入 PostgreSQL content.user_profile_snapshots + Redis 缓存

请求时:
  GET /content?user_id=xxx
    → SnapshotRepository.get_snapshot(user_id)
    → snapshot.interest_ids 过滤内容池
    → snapshot.interest_memories 本地评分
    → snapshot.shown_card_ids 排除已看
    → 返回 Top 3 卡片
    → mark_cards_shown() 写回 snapshot + DB
```

## 3. 变更文件清单

### 新建文件

| 文件 | 用途 |
|------|------|
| `services/content-service/app/snapshot.py` | UserProfileSnapshot 数据结构、序列化、变更检测 |
| `services/content-service/app/snapshot_repository.py` | PostgreSQL + Redis + 内存三级存储 |

### 修改文件

| 文件 | 变更内容 |
|------|---------|
| `infra/postgres/init.sql` | 新增 `content` schema、`user_profile_snapshots` 和 `user_shown_cards` 表 |
| `services/content-service/requirements.txt` | 添加 `psycopg[binary]`、`sqlalchemy` |
| `services/content-service/app/scheduler.py` | 新增 `sync_user_snapshots()` 函数，在 `fetch_and_cache_content()` 开头调用 |
| `services/content-service/app/service.py` | `bootstrap()`/`list_cards()`/`refresh_category()` 改为从 snapshot 读取用户信息；移除对 profile-service 的 HTTP 依赖 |
| `services/content-service/app/repository.py` | 移除 `_get_interest_memory()` 的 HTTP 调用；`list_cards()` 接受 `interest_memories` 参数 |
| `services/content-service/app/main.py` | 所有接口新增 `user_id` 参数；`refresh_category` 从 body 读取 `user_id` 和 `exclude_ids` |
| `services/api-gateway/app/main.py` | content 相关端点透传 `user_id`（从 session 解析） |

## 4. 新增数据结构

### UserProfileSnapshot

```python
@dataclass
class UserProfileSnapshot:
    user_id: str
    interests: list[str]                    # ["AI Coding", "职场成长"]
    interest_ids: list[str]                 # ["shuma", "zhichang"]
    global_memory: dict[str, Any]           # 完整 globalMemory
    interest_memories: list[dict[str, Any]] # 完整 interestMemories 列表
    following_user_ids: list[str]           # OAuth 关注列表（P1）
    shown_card_ids: set[str]                # 已展示卡片 ID
    updated_at: str                         # ISO 时间戳
    source_hash: str                        # MD5，用于检测画像变更
```

### 数据库表

```sql
-- 用户画像快照
CREATE TABLE content.user_profile_snapshots (
    user_id VARCHAR PRIMARY KEY,
    snapshot JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    source_hash VARCHAR
);

-- 用户已展示卡片
CREATE TABLE content.user_shown_cards (
    user_id VARCHAR NOT NULL,
    card_id VARCHAR NOT NULL,
    shown_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, card_id)
);
```

## 5. 存储层级

SnapshotRepository 采用三级降级策略：

```
Redis (TTL 1h, 热缓存)
  ↓ miss
PostgreSQL (持久化)
  ↓ miss / DB 不可用
内存 dict (进程级降级)
```

写入时三级同步写入，任意一级失败不阻塞。

## 6. 后台同步流程

`sync_user_snapshots()` 在 `fetch_and_cache_content()` 开头调用：

```text
1. 调用 profile-service /profiles/me 获取用户画像
2. 提取 user_id（响应中的 userId 字段，兜底 "default"）
3. 读取已有 snapshot，比较 source_hash
4. 若未变更 → 跳过（日志 snapshot_sync_unchanged）
5. 若已变更 → build_snapshot_from_profile() → save_snapshot()
```

## 7. 请求时选卡流程

### bootstrap(user_id)

```text
1. SnapshotRepository.get_snapshot(user_id)
   → Redis → PostgreSQL → 内存 → None
2. 有效 snapshot 存在？
   是 → interest_ids = snapshot.interest_ids
   否 → interest_ids = 请求参数（向后兼容）
3. content_scheduler.get_cached_cards() 获取系统内容池
4. _filter_cards(cards, interest_ids) 按兴趣过滤
5. 遍历卡片，按 categoryId 匹配 interestMemory
6. score_card(card, memory) 本地评分
7. 排序 → 排除 shown_card_ids → 取 Top 3
8. mark_cards_shown() 写回 snapshot + DB
```

### refresh_category(category_id, user_id, exclude_ids)

```text
1. 校验 category_id 有效
2. 合并 snapshot.shown_card_ids + exclude_ids
3. 从内容池取该分类未展示卡片
4. 评分排序 → 取 Top 3 → 标记已展示
5. 若未展示卡片不足 → 触发 _fetch_new_content_for_category()
```

## 8. API 变更

### GET /content

```
参数: user_id (可选), interest_ids (可选，向后兼容)
优先级: snapshot.interest_ids > interest_ids 参数
```

### GET /content/cards

```
参数: category_id, user_id (可选), interest_ids (可选), limit
```

### POST /content/categories/{category_id}/refresh

```
Body: { "user_id": "xxx", "exclude_ids": ["card-1", "card-2"] }
```

### api-gateway 透传

- `GET /api/v1/content` — 从 session 解析 user_id，透传给 content-service
- `GET /api/v1/content/cards` — 同上
- `POST /api/v1/content/categories/{id}/refresh` — 从 session 解析 user_id 注入 body

## 9. 流程符合性验证

对照设计文档 `看山小苗圃-今日看什么卡片获取与推流设计.md` 和 `看山小苗圃-核心流程校准方案.md`，逐项确认：

| 设计要求 | 实现状态 | 说明 |
|---------|---------|------|
| 系统级内容缓存（用户无关） | 符合 | `kanshan:content:cards` 存储系统级候选池 |
| 用户请求时现场组卡 | 符合 | `bootstrap()` 从 snapshot 获取兴趣和 Memory 后本地评分选卡 |
| 每次返回 3 张 | 符合 | `top_cards[:3]` |
| 刷新时排除已展示 | 符合 | `shown_card_ids` 排除 |
| 刷新返回未展示下一批 | 符合 | `refresh_category()` 先取 unshown，不足再 fetch |
| 用户画像落盘为中间状态 | 符合 | `UserProfileSnapshot` 持久化到 PostgreSQL |
| 请求时零外部 HTTP 调用 | 符合 | 评分和选卡全部基于 snapshot 本地数据 |
| interestMemory 用于评分 | 符合 | `_find_matching_memory()` 按 categoryId 匹配 |
| 关注流 OAuth 未开放时返回空态 | 符合 | snapshot 中 `following_user_ids` 默认空列表 |
| Redis 命中不扣额度 | 符合 | zhihu-adapter 缓存层不变 |
| LLM 失败降级 | 符合 | enricher 异常不阻塞卡片返回 |

### 当前 P0 简化项

| 简化项 | 说明 |
|-------|------|
| 快照同步频率 | P0 随内容刷新一起执行（24h），P1 可独立 15min 循环 |
| ~~关注流~~ | ~~P0 返回空态~~ → 已实现，后台预取关注流数据并缓存 |
| 偶遇输入 | P0 使用热榜数据作为 serendipity，P1 增加 global_search |
| Query Plan | P0 使用 category_queries 的默认查询，P1 引入动态 QueryPlan |
| 多来源聚类 | P0 按 3 条一组简单聚合，P1 引入 Jaccard 聚类 |
| MMR 多样性重排 | P0 使用简单评分排序，P1 引入 MMR |

---

## 第二轮更新（2026-05-13）

### 问题发现

1. 关注流精选硬编码返回空列表，但用户已关联 OAuth
2. 卡片的推荐理由、摘要、争议、可写角度全部为空
3. enricher 发送给 llm-service 的数据格式与 prompt 期望不匹配
4. 需要实现抖音式渐进加载

### 新增变更文件

| 文件 | 变更内容 |
|------|---------|
| `services/content-service/app/enricher.py` | 修复输入格式：sources 改为结构化数组，userProfile 替代 memory |
| `services/content-service/app/zhihu_client.py` | 新增 `following_feed()` / `user_followed()` |
| `services/content-service/app/transformer.py` | 新增 `transform_following_to_card()` |
| `services/content-service/app/scheduler.py` | 预取关注流数据 + `_fetch_zhihu_token()` |
| `services/content-service/app/service.py` | 渐进加载 + `enrich_card_on_demand()` + `_update_card_in_cache()` |
| `services/content-service/app/main.py` | 新增 `POST /content/cards/{card_id}/enrich` |
| `services/profile-service/app/auth/service.py` | 新增 `get_zhihu_token()` |
| `services/profile-service/app/main.py` | 新增 `GET /internal/auth/zhihu-token` |
| `services/api-gateway/app/main.py` | 代理 enrich 端点 |
| `frontend/lib/types.ts` | WorthReadingCard 新增 `enriched?: boolean` |
| `frontend/lib/gateway-client.ts` | 新增 `gatewayEnrichCard()` |
| `frontend/lib/api-client.ts` | 新增 `enrichCard()` |
| `frontend/components/kanshan-app.tsx` | 展开卡片时触发按需富化 |

### 关注流实现

```text
1. profile-service 暴露内部接口 GET /internal/auth/zhihu-token?user_id=xxx
2. content-service scheduler 调用该接口获取 access_token
3. 调用 zhihu-adapter /zhihu/following-feed?access_token=xxx 获取关注动态
4. 调用 zhihu-adapter /zhihu/user-followed?access_token=xxx 获取关注列表
5. transform_following_to_card() 转为 WorthReadingCard (categoryId="following")
6. 写入系统内容池 Redis 缓存，与热榜、搜索结果同等对待
```

### LLM 富化修复

enricher 发送格式从文本块改为结构化 JSON：

```python
# 修复前（文本块）
"sources": "来源1: 标题\n类型: xxx\n作者: xxx\n摘要: ..."
"memory": "\n用户画像:\n- 兴趣领域: ..."

# 修复后（结构化 JSON）
"sources": [{"sourceId": "...", "sourceType": "...", "title": "...", "rawExcerpt": "..."}]
"userProfile": {"interests": [...], "writingStyle": "..."}
```

### 渐进加载（抖音模式）

```text
bootstrap():
  → 选 Top 3 卡片
  → 第 1 张：LLM 完整富化 → enriched: true
  → 第 2、3 张：仅基础数据 → enriched: false

前端展开卡片时:
  → 检查 card.enriched === false
  → 调用 POST /content/cards/{id}/enrich
  → LLM 富化 → 更新缓存 → 渲染
```

### 流程符合性更新

| 设计要求 | 实现状态 | 说明 |
|---------|---------|------|
| 关注流真实数据 | 已实现 | 后台预取 + 系统内容池缓存 |
| LLM 富化生效 | 已实现 | 格式修复 + 按需富化 |
| 渐进加载 | 已实现 | 第 1 张预富化，后续按需 |
| meta 字段正确 | 已实现 | following 显示"暂无动态"或" N 张卡" |
