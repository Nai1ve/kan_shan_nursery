# api-gateway

前端唯一调用入口。

职责：

- 演示用户注入。
- 聚合后端服务响应。
- 统一错误格式。
- request id / trace id。
- 转发到各业务服务。

P0 接口：

- `GET /health`
- `GET /api/today`
- `POST /api/seeds`
- `POST /api/sprout/runs`
- `GET /api/sprout/runs/{run_id}`
- `POST /api/writing/sessions`
