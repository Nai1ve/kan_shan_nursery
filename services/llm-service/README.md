# llm-service

模型调用服务。P0 使用知乎直答 Agent 和 mock provider，统一 Prompt、schema 校验、缓存和 fallback。

优先级：P1
难度：H

## 边界

负责：

- 调用 `zhihu-adapter` 的 direct-answer 能力或内部 provider。
- Prompt 模板管理。
- JSON schema 校验。
- Redis 短缓存。
- mock / fallback。
- 直答结果、摘要、争议点、写作角度、草稿、圆桌审稿。

不负责：

- 不直接调用 `developer.zhihu.com`，直答官方调用由 `zhihu-adapter` 封装。
- 不保存业务主状态。
- 不决定 seed 状态或 writing 状态。

## P0 任务

- `GET /health`
- `POST /llm/tasks/summarize-content`
- `POST /llm/tasks/extract-controversies`
- `POST /llm/tasks/generate-writing-angles`
- `POST /llm/tasks/answer-seed-question`
- `POST /llm/tasks/supplement-material`
- `POST /llm/tasks/sprout-opportunities`
- `POST /llm/tasks/argument-blueprint`
- `POST /llm/tasks/draft`
- `POST /llm/tasks/roundtable-review`
- `POST /llm/tasks/feedback-summary`

## 缓存

```text
zhihu:direct_answer:{model}:{messages_hash}:stream_false
llm:content_card:{source_hash}:{prompt_version}
llm:{task_type}:{input_hash}:{prompt_version}:{schema_version}
```

## 允许修改

- `services/llm-service/**`
- `services/llm-service/prompts/**`
- `packages/shared-schemas/**` 中 llm task schema

## 禁止修改

- `zhihu-adapter` 三类鉴权实现
- 业务服务状态机
- 前端页面

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/知乎API.md`
- `docs/看山小苗圃-技术文档.md`

## 验收标准

- 每个任务有 mock 输出和 schema 校验。
- 相同输入命中 Redis 缓存。
- 直答错误能转成统一错误。
- P0 默认 `stream=false`。
