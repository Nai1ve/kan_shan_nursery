# profile-service

用户画像和 Memory 服务。

P0 阶段 Memory 不单独拆服务，而是作为 `app/memory` 子模块维护。

职责：

- 用户与演示账号。
- 首次画像采集。
- 全局画像。
- 兴趣分类画像。
- Memory 展示、编辑、版本记录。
- Memory 更新请求确认。

P0 接口：

- `GET /health`
- `GET /profiles/me`
- `PUT /profiles/me`
- `GET /profiles/me/interests`
- `PUT /profiles/me/interests/{interest_id}`
- `POST /profiles/onboarding`
- `GET /memory/me`
- `PUT /memory/me/global`
- `GET /memory/me/interests/{interest_id}`
- `PUT /memory/me/interests/{interest_id}`
- `GET /memory/update-requests`
- `POST /memory/update-requests/{request_id}/apply`
- `POST /memory/update-requests/{request_id}/reject`
