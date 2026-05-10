# api-gateway

前端唯一调用入口。不得实现复杂业务逻辑，只做鉴权上下文、聚合、路由和错误归一化。

优先级：P0
难度：M

## 边界

负责：

- 注入 demo user / 当前用户上下文。
- 生成和透传 `request_id`。
- 聚合 profile、content、seed、sprout、writing、feedback 响应。
- 统一错误格式。
- 对前端隐藏内部服务地址。

不负责：

- 不直接调用知乎 API。
- 不直接调用直答 Agent。
- 不计算卡片评分、成熟度、发芽指数。
- 不直接读写业务表。

## P0 任务

- `GET /health`
- `GET /api/v1/profile/me`
- `GET /api/v1/content`
- `GET /api/v1/content/cards?categoryId=xxx`
- `POST /api/v1/content/categories/{categoryId}/refresh`
- `GET /api/v1/seeds`
- `POST /api/v1/seeds`
- `POST /api/v1/seeds/from-card`
- `POST /api/v1/sprout/start`
- `GET /api/v1/sprout/opportunities`
- `POST /api/v1/writing/sessions`
- `GET /api/v1/feedback/articles`

## 允许修改

- `services/api-gateway/**`
- `packages/shared-schemas/**` 中 gateway 需要的接口契约

## 禁止修改

- 其他服务实现代码
- 前端业务逻辑
- `docs/知乎API.md`

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-服务拆分与开发协作.md`
- `packages/shared-schemas/README.md`

## 验收标准

- OpenAPI 能看到所有 P0 路由。
- 所有响应包含 `request_id`。
- 下游服务异常能转成统一错误。
- mock 模式下前端可以只接 gateway 跑完整 Demo。
