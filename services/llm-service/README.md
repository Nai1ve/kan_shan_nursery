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

## 当前实现

服务入口统一为：

```text
POST /llm/tasks/{task_type}
```

请求体仍保留 `taskType`，网关调用时需要和 path 中的 `{task_type}` 一致。这样可以同时支持前端按独立 endpoint 调用，也能让服务内部复用同一套校验和缓存逻辑。

启动：

```bash
cd services/llm-service
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

测试：

```bash
python3 -m unittest discover -s services/llm-service/tests -v
python3 -m py_compile services/llm-service/app/*.py services/llm-service/tests/*.py
```

环境变量：

```text
LLM_PROVIDER_MODE=mock | zhihu
ZHIHU_ADAPTER_URL=http://127.0.0.1:8070
LLM_DEFAULT_MODEL=zhida-thinking-1p5
LLM_CACHE_BACKEND=memory | redis
REDIS_URL=redis://127.0.0.1:6379/0
```

P0 默认 `mock` + `memory`，便于离线测试。联调或部署时可以切到 `zhihu` + `redis`，真实直答仍通过 `zhihu-adapter` 发起，`llm-service` 不直接持有知乎 Data Platform 密钥。

示例：

```bash
curl -X POST http://127.0.0.1:8080/llm/tasks/answer-seed-question \
  -H 'Content-Type: application/json' \
  -d '{"taskType":"answer-seed-question","input":{"question":"这个判断有没有可靠证据？"}}'
```

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
