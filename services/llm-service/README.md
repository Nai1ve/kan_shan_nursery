# llm-service

模型调用服务。

职责：

- 统一 LLM provider。
- Prompt 模板管理。
- JSON schema 校验。
- LLM 结果缓存。
- mock / fallback。

P0 接口：

- `GET /health`
- `POST /llm/tasks/summarize-content`
- `POST /llm/tasks/extract-controversies`
- `POST /llm/tasks/generate-seed`
- `POST /llm/tasks/sprout-opportunities`
- `POST /llm/tasks/argument-blueprint`
- `POST /llm/tasks/draft`
- `POST /llm/tasks/roundtable-review`
- `POST /llm/tasks/feedback-summary`
