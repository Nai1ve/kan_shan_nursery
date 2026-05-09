# seed-service

观点种子服务。

职责：

- 从内容卡片生成观点种子。
- 管理种子状态。
- 支持继续浇水。
- 支持合并相似种子。

P0 接口：

- `GET /health`
- `GET /seeds`
- `POST /seeds`
- `GET /seeds/{seed_id}`
- `PUT /seeds/{seed_id}`
- `POST /seeds/{seed_id}/water`
- `POST /seeds/merge`
