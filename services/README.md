# Services

后端服务目录。每个子项目的 `README.md` 都是可直接分配给 AI Coding 模型的任务边界说明。

统一约束：

- 每个服务必须提供 `/health`、OpenAPI、mock provider、最小单元测试。
- 前端只调用 `api-gateway`，业务服务之间只通过 HTTP API 通信。
- 知乎接口只能由 `zhihu-adapter` 调用，直答 Agent 只能由 `llm-service` 调用。
- Redis 只做短缓存和额度计数，不作为业务主存储。
- Memory 维护在 `profile-service/app/memory`，P0 不拆独立 `memory-service`。

参考文档：

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-服务拆分与开发协作.md`
- `docs/看山小苗圃-技术文档.md`
- `docs/知乎API.md`
- `docs/工程约束与提交规范.md`

## 优先级排序

| 优先级 | 项目 | 原因 |
| --- | --- | --- |
| P0 | `packages/shared-schemas` | 先固定 DTO、错误结构、状态枚举，避免各服务各写一套 |
| P0 | `api-gateway` | 前端唯一入口，后续服务可以逐个替换 mock |
| P0 | `profile-service` | 今日看什么、发芽、写作都依赖用户画像和 Memory |
| P0 | `zhihu-adapter` | 热榜、搜索、关注流、故事、直答缓存都依赖它的标准 DTO |
| P0 | `content-service` | 直接支撑“今日看什么”主入口 |
| P0 | `seed-service` | 读写闭环的中间状态中心，承接卡片反应和浇水 |
| P1 | `frontend` | 已有 mock 版，等 API contract 稳定后逐步接 gateway |
| P1 | `llm-service` | P0 可 mock，真实摘要、问答、草稿再逐步接入 |
| P1 | `writing-service` | 基于 seed 和 Memory，先 session/mock，再接生成能力 |
| P2 | `sprout-service` | 算法和成本最高，先用 mock 机会跑通，再优化 |
| P2 | `feedback-service` | 依赖发布后的文章与评论，比赛 Demo 可先 mock |
| P2 | `infra` | 本地依赖先能跑 Redis/Postgres，服务容器化可后置 |
| P2 | `packages/shared-python` | 只沉淀无业务工具，随服务实现逐步补 |

## 难度排序

| 难度 | 项目 | 关键风险 |
| --- | --- | --- |
| S | `profile-service` | CRUD 为主，注意 Memory 结构不要混乱 |
| S | `feedback-service` | P0 mock 即可，注意不直接写 Memory |
| S | `infra` | 先提供 Redis/Postgres 骨架 |
| M | `api-gateway` | 需要统一错误、request id、服务聚合 |
| M | `packages/shared-schemas` | 需要和前端类型、后端 DTO 保持一致 |
| M | `zhihu-adapter` | 三类鉴权、Redis 缓存、额度计数、字段归一化 |
| M | `content-service` | Query Plan、卡片聚合、评分和来源展示 |
| M | `seed-service` | 种子状态、浇水材料、疑问线程、成熟度计算 |
| M | `frontend` | 页面已成型，难点是接 API 后保持闭环 |
| H | `llm-service` | Prompt、schema 校验、缓存、fallback |
| H | `writing-service` | 写作状态机、Memory 注入、草稿版本 |
| VH | `sprout-service` | 激活分计算、热点匹配、成本控制、结果解释 |
