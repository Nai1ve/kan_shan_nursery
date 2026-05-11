# zhihu-adapter

知乎开放接口适配服务。它是所有知乎 API 的唯一出口，业务服务只能消费标准 DTO。

优先级：P0
难度：M

## 边界

负责：

- Community Client：HMAC 签名，圈子、评论、发布、点赞、故事。
- OAuth Client：authorize → code → access_token 流程，用户信息、关注列表、粉丝列表、关注动态。
- Data Platform Client：Bearer access_secret，热榜、知乎搜索、全网搜索、直答。
- Redis 短缓存。
- 额度计数与写操作节流。
- 圈子白名单（发布/评论/点赞 ring_id 校验）。
- 官方 raw 字段映射为标准 DTO（`ZhihuContentItem` 风格）。
- 错误码归一化（ZHIHU_AUTH_FAILED / ZHIHU_RATE_LIMITED / ZHIHU_INVALID_REQUEST / ZHIHU_RING_NOT_WRITABLE / ZHIHU_UPSTREAM_ERROR / ZHIHU_UNAVAILABLE）。
- 结构化日志（jsonl + 控制台）。

不负责：

- 不生成 `WorthReadingCard`。
- 不生成观点种子。
- 不写用户画像。
- 不决定文章是否发布，只提供受控发布接口。

## 凭证

凭证统一由 `services/config.yaml` 提供（已通过 `.gitignore` 保护），参考 `services/config.example.yaml`：

```yaml
provider_mode: live           # 切换 mock / live
zhihu:
  community:
    app_key: <用户 token>       # 知乎个人主页 people/<这一段>
    app_secret: <ring/moltbook 申请>
    writable_ring_ids:
      - "2001009660925334090"
      - "2015023739549529606"
      - "2029619126742656657"
    default_ring_id: "2029619126742656657"
  oauth:
    app_id: <OAuth app_id>
    app_key: <OAuth app_key>
    redirect_uri: "http://127.0.0.1:8070/zhihu/oauth/callback"
    access_token: ""            # 走完 OAuth 流程后填写
  data_platform:
    access_secret: <developer.zhihu.com 个人中心>
    default_model: zhida-thinking-1p5
  quota:
    hot_list: 100
    zhihu_search: 1000
    global_search: 1000
    direct_answer: 100
```

环境变量优先级最高（用于 CI / 临时覆盖）：`ZHIHU_APP_KEY` / `ZHIHU_APP_SECRET` / `ZHIHU_ACCESS_TOKEN` / `ZHIHU_ACCESS_SECRET` / `PROVIDER_MODE` 等。

## P0 任务

- `GET /health`
- `GET /zhihu/hot-list`
- `GET /zhihu/zhihu-search`
- `GET /zhihu/global-search`
- `POST /zhihu/direct-answer`
- `GET /zhihu/ring-detail`
- `GET /zhihu/comments`
- `GET /zhihu/story-list`
- `GET /zhihu/story-detail`
- `GET /zhihu/user`
- `GET /zhihu/following-feed`
- `GET /zhihu/user-followed`
- `GET /zhihu/user-followers`
- `POST /zhihu/publish/mock-or-live`
- `POST /zhihu/comment/create`
- `POST /zhihu/reaction`
- `GET /zhihu/oauth/authorize`（支持 `?redirect=true` 直接 302 到知乎授权页）
- `GET /zhihu/oauth/callback`（接收 code，换 access_token，渲染人读 HTML 提示用户复制 token 到 config.yaml）

## Redis Key

```text
zhihu:hot_list:{limit}
zhihu:zhihu_search:{query_hash}:{count}
zhihu:global_search:{query_hash}:{count}
zhihu:direct_answer:{model}:{messages_hash}:stream_false
zhihu:ring_detail:{ring_id}:{page_num}:{page_size}
zhihu:comment_list:{content_type}:{content_token}
zhihu:story_list
zhihu:story_detail:{work_id}
zhihu:user:{user_id}:{token_hash}
zhihu:user_moments:{user_id}:{token_hash}
zhihu:user_followed:{user_id}:{page}:{per_page}:{token_hash}
zhihu:user_followers:{user_id}:{page}:{per_page}:{token_hash}
quota:{endpoint}:{user_id}:{yyyyMMdd}
```

## 错误码

| 上游 | adapter 对外 | HTTP |
| --- | --- | --- |
| Community status=1 / OAuth code=401 / Data 20001 | `ZHIHU_AUTH_FAILED` | 401 |
| Community 429 / Data 30001 / 本地 quota 耗尽 | `ZHIHU_RATE_LIMITED` (`QuotaExceeded` 也归此) | 429 |
| Data 10001 / Community 参数错 | `ZHIHU_INVALID_REQUEST` | 400 |
| 本地 ring 白名单不通过 | `ZHIHU_RING_NOT_WRITABLE` | 400 |
| Data 90001 / 5xx / 未知 | `ZHIHU_UPSTREAM_ERROR` | 502 |
| 网络 / 超时 | `ZHIHU_UNAVAILABLE` | 502 |

## OAuth 流程

```text
前端 LoginScreen "关联知乎账号" 按钮
  ↓
GET http://127.0.0.1:8070/zhihu/oauth/authorize?redirect=true  → 302
  ↓
浏览器跳到 https://openapi.zhihu.com/authorize?app_id=...&redirect_uri=...&response_type=code
  ↓
用户授权后回跳 http://127.0.0.1:8070/zhihu/oauth/callback?code=xxx
  ↓
adapter 用 app_id+app_key+code 换 access_token
  ↓
渲染最小 HTML，提示把 access_token 写入 services/config.yaml 的 zhihu.oauth.access_token
```

v0.6 阶段：access_token 不自动持久化（演示用），用户手动复制到 config.yaml 后重启服务即可生效。后续可拆 token storage 到 profile-service 或 redis。

## 允许修改

- `services/zhihu-adapter/**`
- `packages/shared-schemas/**` 中 zhihu schema

## 禁止修改

- 业务服务内部评分、种子、发芽、写作逻辑
- 前端业务逻辑（除登录 OAuth 跳转）
- `docs/知乎API.md`

## 参考文档

- `docs/知乎API.md`
- `docs/看山小苗圃-开发设计与实施.md`（v0.6 章节）
- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/工程约束与提交规范.md`

## 验收标准（v0.6）

- 三类鉴权逻辑独立到三个 client，业务层不感知凭证差异。
- 读取型接口第二次相同请求命中 Redis；命中不增加 quota。
- 超限返回 `ZHIHU_RATE_LIMITED` (429)，业务服务能识别。
- 全网搜索 `<em>` 保留 rawHtml，同时给纯文本 summary。
- 故事内容展示 `usageNotice`。
- 圈子发布/评论/点赞前校验 ring_id 必须在 `writable_ring_ids`。
- OAuth authorize → code → token 流程能跑通（前端按钮 → adapter callback → 提示拷贝 token）。
- 全部事件落 `output/logs/zhihu-adapter-<日期>.jsonl`。
- 单元测试覆盖：HMAC 签名、mapper（em / story usageNotice）、缓存命中不扣额、quota 超限抛错、ring 白名单拒绝、OAuth authorize_url 构造、无 token 时 OAuth GET 抛 ZhihuAuthError、直答 OpenAI 兼容解析。

## 接口状态（2026-05-11 live 联调）

### 已通（12 个）

| 接口 | 数据源 | 说明 |
|------|--------|------|
| `GET /health` | - | 服务健康检查 |
| `GET /zhihu/hot-list` | Data Platform | 知乎热榜，live 返回真实数据 |
| `GET /zhihu/zhihu-search` | Data Platform | 知乎站内搜索 |
| `GET /zhihu/global-search` | Data Platform | 全网搜索（`<em>` 在 rawExcerptHtml 保留） |
| `POST /zhihu/direct-answer` | Data Platform | 知乎直答（OpenAI 兼容格式） |
| `GET /zhihu/ring-detail` | Community | 圈子详情 + 内容列表 |
| `GET /zhihu/comments` | Community | 评论列表 |
| `GET /zhihu/story-list` | Community | 故事概要列表 |
| `GET /zhihu/story-detail` | Community | 故事章节详情 |
| `POST /zhihu/publish/mock-or-live` | Community | 发布想法（需白名单 ring_id） |
| `POST /zhihu/comment/create` | Community | 创建评论 |
| `POST /zhihu/reaction` | Community | 点赞/取消点赞 |

### 待联调：OAuth 接口（需要 OAuth 凭证 + 授权流程）

以下接口需要通过 OAuth 授权流程获取 `access_token` 后才能使用。

`roach-7` 是社区接口的 `app_key`（用户标识），**不是** OAuth access_token，
不能直接用于 OAuth 接口。

| 接口 | 说明 | 前置条件 |
|------|------|---------|
| `GET /zhihu/user` | 获取当前授权用户信息 | 需要有效 access_token |
| `GET /zhihu/following-feed` | 获取关注动态 | 需要有效 access_token |
| `GET /zhihu/user-followed` | 获取关注列表 | 需要有效 access_token |
| `GET /zhihu/user-followers` | 获取粉丝列表 | 需要有效 access_token |
| `GET /zhihu/oauth/authorize` | 获取授权 URL（本身可用） | 需要配置 app_id + app_key |
| `GET /zhihu/oauth/callback` | 授权回调，换取 access_token | 需要真实 OAuth code |

**联调步骤：**

1. 在 `services/config.yaml` 填入 OAuth `app_id` 和 `app_key`（与 community 凭证不同）
2. 访问 `http://127.0.0.1:8070/zhihu/oauth/authorize?redirect=true` 跳转到知乎授权页
3. 用户授权后回调到 `/zhihu/oauth/callback?code=xxx`，页面显示 access_token
4. 把 access_token 填入 `config.yaml` 的 `zhihu.oauth.access_token`，重启服务
5. 以上 4 个 OAuth 数据接口即可正常调用

## 本地运行

```bash
cd services/zhihu-adapter
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8070 --reload
```

切换 live 模式：在 `services/config.yaml` 把 `provider_mode: live`，并填三类凭证。

## 测试

```bash
python3 -m unittest discover -s services/zhihu-adapter/tests -v
```

当前 13 个用例覆盖：签名、mapper、缓存/quota、ring 白名单、OAuth client、直答解析。
