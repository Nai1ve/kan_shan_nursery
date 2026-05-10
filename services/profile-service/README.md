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
- `GET /memory/injection/{interest_id}`
- `GET /memory/update-requests`
- `POST /memory/update-requests`
- `POST /memory/update-requests/{request_id}/apply`
- `POST /memory/update-requests/{request_id}/reject`

## 当前实现

P0 使用内存仓储，进程重启后恢复默认演示画像。代码按 `profile` 和 `memory` 子模块拆分，便于后续把 Memory 独立成服务或替换为数据库仓储。

默认兴趣画像覆盖：

```text
Agent 工程化、AI Coding、RAG / 检索、后端工程、程序员成长、金融风控、医学 AI、产品设计、内容创作、关注流精选、偶遇输入
```

启动：

```bash
cd services/profile-service
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

测试：

```bash
python3 -m unittest discover -s services/profile-service/tests -v
python3 -m py_compile services/profile-service/app/*.py services/profile-service/app/profile/*.py services/profile-service/app/memory/*.py services/profile-service/tests/*.py
```

示例：

```bash
curl http://127.0.0.1:8010/profiles/me
curl http://127.0.0.1:8010/memory/injection/ai-coding
```

Memory 更新请求规则：

- `POST /memory/update-requests` 只创建待确认请求。
- `apply` 才会写入全局 Memory 或兴趣 Memory。
- `reject` 只改变请求状态，不修改 Memory。
- `memoryOverride` 属于写作 session，不由本服务直接覆盖长期 Memory。

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
