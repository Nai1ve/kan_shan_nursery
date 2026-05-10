# Shared Schemas

共享接口契约目录。优先级最高，因为它决定前端、gateway 和服务之间的 DTO 边界。

优先级：P0
难度：M

## 边界

负责：

- OpenAPI schema。
- JSON schema。
- TypeScript 类型说明。
- Python Pydantic schema 的字段来源说明。
- 状态枚举、错误码、通用响应结构。

不负责：

- 不放业务逻辑。
- 不放 repository。
- 不放 Prompt。
- 不放真实 secret 或环境变量。

## P0 任务

- `common`：`request_id`、错误结构、分页、时间字段。
- `profile`：`ProfileData`、`MemorySummary`、Memory update request。
- `content`：`InputCategory`、`ContentSource`、`WorthReadingCard`。
- `zhihu`：`ZhihuContentItem`、cache metadata、quota metadata。
- `seed`：`IdeaSeed`、`SeedQuestion`、`WateringMaterial`。
- `sprout`：`SproutOpportunity`、run 状态。
- `writing`：`WritingSession`、Memory override、draft 状态。
- `feedback`：`FeedbackArticle`、comment summary、second seed payload。

## 允许修改

- `packages/shared-schemas/**`

## 禁止修改

- 任何服务实现。
- 前端组件。

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `frontend/lib/types.ts`
- `docs/工程约束与提交规范.md`

## 验收标准

- 每个 P0 服务 README 中提到的 DTO 都能在 shared schema 中找到。
- schema 字段命名和 `frontend/lib/types.ts` 不冲突。
- schema 变更同步更新对应服务 README。
