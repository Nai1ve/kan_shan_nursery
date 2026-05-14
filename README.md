# 看山小苗圃

看山小苗圃是一个面向知乎创作者的读写一体 AI 创作工作台。项目目标不是让 AI 从空白页直接代写文章，而是把真实创作过程拆成一条可追溯链路：

```text
看见好内容
  ↓
形成真实观点
  ↓
沉淀观点种子
  ↓
在合适热点下发芽
  ↓
进入写作苗圃逐步成文
  ↓
发布后用反馈修正画像和表达
```

当前项目处于黑客松 Demo 冲刺状态，核心目标是展示“高质量输入 → 观点形成 → 写作表达”的闭环，而不是完整商业化产品。

---

## 当前进度

更新时间：2026-05-14

| 模块 | 当前状态 | 说明 |
| --- | --- | --- |
| 登录 / 用户入口 | 基本可用 | 支持注册登录、知乎 OAuth 绑定入口、本地跳过授权调试。线上 OAuth 主流程已跑通过。 |
| 用户画像 / Memory | 基本可用 | 支持基础画像、兴趣 Memory、LLM 配置、OAuth 后画像生成任务框架。画像更新仍需继续打磨。 |
| 知乎能力接入 | 基本可用 | 热榜、知乎搜索、全网搜索、OAuth 关注流链路已有真实接入。圈子、评论、反馈相关能力仍偏演示/预留。 |
| 今日看什么 | 可演示 | 已能基于真实知乎数据返回兴趣卡片，并支持卡片扩展、来源展示、刷新/下一条式浏览。内容质量和推流算法仍需继续优化。 |
| 观点种子库 | 可演示 | 支持从卡片转种子、认同/反对/疑问、四格浇水材料、成熟度等核心交互。 |
| 今日发芽 | 部分可用 | 已有 sprout-service、热点/种子/Memory 匹配和 LLM 任务入口。线上仍需要关注数据库结构同步和服务健康。 |
| 写作苗圃 | 有明显 bug | 前端写作流程和后端 writing-service 状态机目前没有保持同步，部分步骤可能前端已推进但后端 session state 未一致。该模块不能作为稳定主链路，需要优先修复。 |
| LLM 服务 | 基本可用 | 支持平台兜底、用户自配 LLM、任务路由和失败提示。通用提取走平台能力，涉及用户个人内容优先走用户配置。 |
| 历史反馈 | 方案和部分接口存在 | 当前主要用于 Demo 展示和后续扩展，真实知乎发布后数据回流能力受开放接口限制。 |
| 部署 | 可用但需检查 | Docker Compose 线上部署已跑通过 OAuth。旧数据库卷可能需要执行 schema 同步 SQL。 |

---

## 已知关键问题

### 1. 写作苗圃状态机不同步

这是当前最重要的已知 bug。

问题表现：

```text
前端有自己的写作步骤状态
后端 writing-service 也有 session state
两者没有形成严格单一事实源
```

可能导致：

```text
1. 前端显示进入下一步，但后端 session 仍停留在旧状态。
2. 重新刷新页面后写作进度丢失或回退。
3. 圆桌审稿、定稿、模拟发布等动作的后端状态不可完全信任。
4. 今日发芽进入写作苗圃后，seed / opportunity / writing session 的关系不稳定。
```

后续修复方向：

```text
1. 后端 writing-service 定义唯一状态机。
2. 前端只展示后端返回的 session state，不自行推导关键步骤。
3. 每个按钮动作都调用后端 transition API。
4. 后端返回 nextAllowedActions，前端按它控制按钮可用性。
5. 补充从 opportunity → writing session → feedback article 的端到端测试。
```

### 2. 数据库结构需要同步

部分线上问题来自旧 PostgreSQL 卷未执行新的初始化 SQL。遇到缺字段、缺 schema 时，应先执行当前数据库同步脚本或对应 SQL，再重启服务。

重点关注：

```text
profile.users.setup_state
sprout.opportunities.run_id
sprout.opportunities.trigger_type
sprout.runs
content.user_profile_snapshots
content.user_shown_cards
```

### 3. 今日看什么仍需提升推荐质量

当前已经能返回真实数据，但推荐质量仍依赖后续算法优化：

```text
1. 公共内容缓存和用户个性化排序需要继续稳定。
2. 卡片摘要、争议点、可写角度应尽量在缓存构建时完成，减少前端等待。
3. 关注流精选已接通，但仍需控制调用成本和失败降级。
```

---

## 当前核心链路

```text
用户登录 / 跳过授权
  ↓
选择兴趣与写作偏好
  ↓
今日看什么：读取热榜 / 搜索 / 关注流 / 全网搜索
  ↓
用户对卡片表态、提问或加入种子库
  ↓
种子库：观点、材料、疑问、反方、成熟度
  ↓
今日发芽：手动触发，用热点和 Memory 激活可写种子
  ↓
写作苗圃：逐步生成观点、蓝图、大纲、草稿、审稿与定稿
  ↓
历史反馈：记录反馈并生成后续 Memory 建议
```

其中当前最稳定的 Demo 链路是：

```text
今日看什么 → 观点种子库 → 今日发芽机会展示
```

写作苗圃目前只能作为“功能方向展示”，不应作为稳定闭环的最终验收点。

---

## 本地开发

推荐使用：

```bash
bash scripts/dev_up.sh
```

当前本地调试口径：

```text
前端：Next.js dev server
后端：9 个 FastAPI 服务用 uvicorn 在本机分端口运行
数据库 / Redis：可使用 Docker dev 服务
```

默认端口：

| 服务 | 端口 |
| --- | --- |
| frontend | 3000 |
| api-gateway | 8000 |
| profile-service | 8010 |
| content-service | 8020 |
| seed-service | 8030 |
| sprout-service | 8040 |
| writing-service | 8050 |
| feedback-service | 8060 |
| zhihu-adapter | 8070 |
| llm-service | 8080 |

前端入口：

```text
http://127.0.0.1:3000
```

---

## 线上部署

推荐使用：

```bash
cd /opt/kanshan
git pull
bash scripts/deploy.sh
```

如果只重建部分服务：

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build api-gateway frontend llm-service sprout-service
```

健康检查：

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8040/health
curl -s http://127.0.0.1:8080/health
```

---

## 仓库结构

```text
frontend/                  Next.js 前端
services/                  FastAPI 微服务
  ├── api-gateway/         前端唯一入口
  ├── profile-service/     用户、画像、Memory、OAuth 绑定
  ├── content-service/     今日看什么
  ├── seed-service/        观点种子库
  ├── sprout-service/      今日发芽
  ├── writing-service/     写作苗圃
  ├── feedback-service/    历史反馈
  ├── zhihu-adapter/       知乎 API 适配层
  └── llm-service/         LLM provider 路由和 Agent 任务
packages/
  ├── shared-python/       配置、日志、数据库等 Python 共享能力
  └── shared-schemas/      DTO / OpenAPI / JSON Schema
infra/                     Docker Compose、Postgres 初始化脚本
docs/                      产品、技术、算法、部署和任务拆分文档
scripts/                   本地启动、部署、校验脚本
```

---

## 开发原则

```text
1. AI 辅助表达，但不替用户决定立场。
2. 输入质量先于输出质量。
3. 观点种子是读写闭环的核心资产。
4. 昂贵 LLM 任务必须用户主动触发。
5. Memory 更新需要用户可感知、可确认、可拒绝。
6. 前端只调用 api-gateway，不直接调用业务服务。
7. 涉及用户个人内容优先走用户自配 LLM，通用提取走平台能力。
```
