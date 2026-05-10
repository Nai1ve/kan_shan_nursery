# writing-service

写作苗圃服务。它把成熟观点种子转成可编辑写作 session，不替用户决定立场。

优先级：P1
难度：H

## 边界

负责：

- 写作 session。
- 观点确认。
- 文章类型和语气。
- 兴趣 Memory 注入。
- 用户可修改 `memoryOverride`。
- 论证蓝图、草稿、圆桌审稿、定稿。
- 模拟发布后创建反馈记录。

不负责：

- 不直接读取知乎 API。
- 不创建基础内容卡片。
- 不直接覆盖 profile Memory。
- 不绕过用户确认发布真实内容。

## P0 任务

- `GET /health`
- `POST /writing/sessions`
- `GET /writing/sessions/{session_id}`
- `PATCH /writing/sessions/{session_id}`
- `POST /writing/sessions/{session_id}/confirm-claim`
- `POST /writing/sessions/{session_id}/blueprint`
- `POST /writing/sessions/{session_id}/draft`
- `POST /writing/sessions/{session_id}/roundtable`
- `POST /writing/sessions/{session_id}/finalize`
- `POST /writing/sessions/{session_id}/publish/mock`

## 状态

```text
claim_confirming
blueprint_ready
draft_ready
reviewing
finalized
published
```

## 允许修改

- `services/writing-service/**`
- `packages/shared-schemas/**` 中 writing schema
- `services/llm-service/prompts/**` 中写作相关 prompt，需同步说明

## 禁止修改

- `profile-service` Memory 主存储
- `seed-service` 种子成熟度计算
- `feedback-service` 反馈分析逻辑

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-技术文档.md`
- `frontend/lib/types.ts`

## 验收标准

- 创建 session 时能注入兴趣 Memory。
- `memoryOverride` 可修改且只影响当前 session。
- 模拟发布后 seed 变 `published`，并生成 feedback article。
- 所有写作阶段可 mock 返回稳定结构。
