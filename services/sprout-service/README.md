# sprout-service

今日发芽服务。

职责：

- 用户主动触发发芽。
- 匹配历史种子、热点、关注流和用户 Memory。
- 计算 Activation Score。
- 生成发芽机会。

P0 接口：

- `GET /health`
- `POST /sprout/runs`
- `GET /sprout/runs/{run_id}`
- `GET /sprout/opportunities`
