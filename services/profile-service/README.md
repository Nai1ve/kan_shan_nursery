# profile-service

用户画像和 Memory 服务。P0 阶段 Memory 不单独拆服务，而是作为 `app/memory` 子模块维护。

优先级：P0
难度：S

## 边界

负责：

- demo 用户和后续真实用户资料。
- 首次画像采集。
- 全局 Memory。
- 兴趣分类 Memory。
- Memory 展示、编辑、版本记录。
- Memory 更新建议的确认、拒绝、修改。

不负责：

- 不生成内容卡片。
- 不创建观点种子。
- 不直接读取知乎接口。
- 不把历史反馈自动写入 Memory，必须生成待确认请求。

## P0 任务

- `GET /health`
- `GET /profiles/me`
- `PUT /profiles/me`
- `POST /profiles/onboarding`
- `GET /profiles/me/interests`
- `PUT /profiles/me/interests/{interest_id}`
- `GET /memory/me`
- `PUT /memory/me/global`
- `GET /memory/me/interests/{interest_id}`
- `PUT /memory/me/interests/{interest_id}`
- `GET /memory/update-requests`
- `POST /memory/update-requests/{request_id}/apply`
- `POST /memory/update-requests/{request_id}/reject`

## 数据落点

- `users`
- `global_profiles`
- `interest_profiles`
- `memory_entries`
- `memory_versions`
- `memory_update_requests`

## 允许修改

- `services/profile-service/**`
- `packages/shared-schemas/**` 中 profile / memory schema

## 禁止修改

- `seed-service` 的种子状态逻辑
- `writing-service` 的 session 状态机
- `feedback-service` 的反馈分析逻辑

## 参考文档

- `docs/看山小苗圃-技术文档.md`
- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-服务拆分与开发协作.md`

## 验收标准

- 能返回完整 `ProfileData` 和 `MemorySummary`。
- 兴趣 Memory 可按 `interestId` 读取。
- 写作苗圃可读取 Memory 注入摘要。
- Memory 更新请求不会自动覆盖原 Memory。
