# api-gateway

前端唯一调用入口。不得实现复杂业务逻辑，只做鉴权上下文、聚合、路由和错误归一化。

优先级：P0
难度：M

## 边界

负责：

- 注入 demo user / 当前用户上下文。
- 生成和透传 `request_id`。
- 聚合 profile、content、seed、sprout、writing、feedback 响应。
- 统一错误格式。
- 对前端隐藏内部服务地址。

不负责：

- 不直接调用知乎 API。
- 不直接调用直答 Agent。
- 不计算卡片评分、成熟度、发芽指数。
- 不直接读写业务表。

## P0 任务

- `GET /health`
- `GET /api/v1/profile/me`
- `PUT /api/v1/profile/me`
- `GET /api/v1/profile/interests`
- `GET /api/v1/memory/injection/{interest_id}`
- `GET /api/v1/memory/update-requests`
- `POST /api/v1/memory/update-requests`
- `POST /api/v1/memory/update-requests/{request_id}/apply`
- `POST /api/v1/memory/update-requests/{request_id}/reject`
- `GET /api/v1/content`
- `GET /api/v1/content/cards?categoryId=xxx`
- `POST /api/v1/content/categories/{categoryId}/refresh`
- `GET /api/v1/seeds`
- `POST /api/v1/seeds`
- `POST /api/v1/seeds/from-card`
- `GET /api/v1/seeds/{seed_id}`
- `PATCH /api/v1/seeds/{seed_id}`
- `POST /api/v1/seeds/{seed_id}/questions`
- `PATCH /api/v1/seeds/{seed_id}/questions/{question_id}`
- `POST /api/v1/seeds/{seed_id}/materials`
- `POST /api/v1/seeds/{seed_id}/materials/agent-supplement`
- `PATCH /api/v1/seeds/{seed_id}/materials/{material_id}`
- `DELETE /api/v1/seeds/{seed_id}/materials/{material_id}`
- `POST /api/v1/seeds/{target_seed_id}/merge`
- `POST /api/v1/llm/tasks/{task_type}`
- `POST /api/v1/sprout/start`
- `GET /api/v1/sprout/opportunities`
- `POST /api/v1/writing/sessions`
- `GET /api/v1/feedback/articles`

## 当前实现

P0 网关使用统一 envelope：

```json
{
  "request_id": "req-xxx",
  "data": {}
}
```

失败统一为：

```json
{
  "request_id": "req-xxx",
  "error": {
    "code": "SERVICE_NOT_READY",
    "message": "Service is not ready: content",
    "detail": {}
  }
}
```

同时响应头会带 `X-Request-Id`。如果请求头传入 `X-Request-Id`，网关会透传给下游服务。

默认已就绪服务（v0.4 P0 闭环完成后）：

```text
profile, seed, zhihu, llm, content, sprout, writing, feedback
```

可通过环境变量覆盖（用于在某个下游临时不可用时降级）：

```text
GATEWAY_READY_SERVICES=profile,seed,zhihu,llm
```

启动：

```bash
cd services/api-gateway
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

测试：

```bash
python3 -m unittest discover -s services/api-gateway/tests -v
python3 -m py_compile services/api-gateway/app/*.py services/api-gateway/tests/*.py
```

环境变量：

```text
PROFILE_SERVICE_URL=http://127.0.0.1:8010
CONTENT_SERVICE_URL=http://127.0.0.1:8020
SEED_SERVICE_URL=http://127.0.0.1:8030
SPROUT_SERVICE_URL=http://127.0.0.1:8040
WRITING_SERVICE_URL=http://127.0.0.1:8050
FEEDBACK_SERVICE_URL=http://127.0.0.1:8060
ZHIHU_ADAPTER_URL=http://127.0.0.1:8070
LLM_SERVICE_URL=http://127.0.0.1:8080
GATEWAY_REQUEST_TIMEOUT_SECONDS=20
```

## 允许修改

- `services/api-gateway/**`
- `packages/shared-schemas/**` 中 gateway 需要的接口契约

## 禁止修改

- 其他服务实现代码
- 前端业务逻辑
- `docs/知乎API.md`

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-服务拆分与开发协作.md`
- `packages/shared-schemas/README.md`

## 验收标准

- OpenAPI 能看到所有 P0 路由。
- 所有响应包含 `request_id`。
- 下游服务异常能转成统一错误。
- mock 模式下前端可以只接 gateway 跑完整 Demo。


## 启动

依赖（建议在每个服务用独立 venv 隔离，也可以全仓库共用一个）：

```bash
cd services/api-gateway
python3 -m venv .venv && source .venv/bin/activate    # 可选
pip install -r requirements.txt
```

启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

预期输出（envelope，含 8 个下游 readiness）：

```json
{
  "request_id": "req-xxxxxxxxxxxx",
  "data": {
    "status": "ok",
    "service": "api-gateway",
    "demoUserId": "demo-user",
    "downstream": {
      "profile":  { "baseUrl": "http://127.0.0.1:8010", "ready": true },
      "content":  { "baseUrl": "http://127.0.0.1:8020", "ready": true },
      "seed":     { "baseUrl": "http://127.0.0.1:8030", "ready": true },
      "sprout":   { "baseUrl": "http://127.0.0.1:8040", "ready": true },
      "writing":  { "baseUrl": "http://127.0.0.1:8050", "ready": true },
      "feedback": { "baseUrl": "http://127.0.0.1:8060", "ready": true },
      "zhihu":    { "baseUrl": "http://127.0.0.1:8070", "ready": true },
      "llm":      { "baseUrl": "http://127.0.0.1:8080", "ready": true }
    }
  }
}
```

## 测试

```bash
python3 -m unittest discover -s services/api-gateway/tests -v
python3 -m py_compile services/api-gateway/app/*.py services/api-gateway/tests/*.py
```

## 配置

凭证 / 端口 / 模式统一由 `services/config.yaml` 提供（已被 `.gitignore`），模板：

```bash
cp services/config.example.yaml services/config.yaml
```

环境变量优先级最高，可临时覆盖：

```text
PROVIDER_MODE=mock | live
KANSHAN_LOG_DIR=output/logs
KANSHAN_LOG_LEVEL=INFO | DEBUG
```

启动日志写到：

- `output/logs/api-gateway-YYYY-MM-DD.jsonl`（机器可读）
- 控制台 stderr（人读一行）

## 一键启动 9 个服务

```bash
bash scripts/run_all_services.sh         # 仅后端
bash scripts/dev_up.sh                   # 后端 + 前端，前端切到 gateway 模式
```
