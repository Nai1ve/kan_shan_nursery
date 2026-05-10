# llm-service

模型调用服务。v0.5 升级为多 LLM 视角 Agent 框架：业务服务只调 `POST /llm/tasks/{task_type}`，"哪个 task 用哪个 provider、哪个 persona"全部由 `config/providers.json` 配置决定。

优先级：P1
难度：H

## 边界

负责：

- 维护 task type 契约（业务服务的稳定入口）。
- provider 注册表（mock / zhihu_direct / openai_compat）。
- per-task 路由 + multi_persona 编排（圆桌审稿）。
- prompt 模板（`prompts/v1/<task>.md` + `prompts/v1/personas/<id>.md`）。
- JSON 输出 schema 校验。
- 内存或 Redis 缓存（命中跳过子 persona 调用）。
- 显式 fallback：单 task 主 provider 失败降级到 mock；multi_persona 单 persona 失败仅替补该 persona。
- LLM trace（`output/llm-trace/YYYY-MM-DD.jsonl`）。

不负责：

- 不直接调用 `developer.zhihu.com`（直答仍由 `zhihu-adapter` 封装）。
- 不保存业务主状态（seed / writing / feedback 的状态机在各自服务内）。
- 不感知前端 UI。

## 任务清单

P0 已实现的 task：

- `POST /llm/tasks/summarize-content`
- `POST /llm/tasks/extract-controversies`
- `POST /llm/tasks/generate-writing-angles`
- `POST /llm/tasks/answer-seed-question`
- `POST /llm/tasks/supplement-material`
- `POST /llm/tasks/sprout-opportunities`
- `POST /llm/tasks/argument-blueprint`
- `POST /llm/tasks/draft`
- `POST /llm/tasks/roundtable-review`（multi_persona 模式）
- `POST /llm/tasks/feedback-summary`

通用入口：

```text
POST /llm/tasks/{task_type}
{
  "taskType": "<task_type>",      # 必须与 path 一致
  "input": { ... },
  "promptVersion": "v1",
  "schemaVersion": "v1"
}
```

响应：

```json
{
  "taskType": "...",
  "schemaVersion": "v1",
  "output": { ... },
  "fallback": false,
  "routeMeta": { "mode": "single | multi_persona", "provider": "...", "fallback": false },
  "subCalls": [ ... ],
  "cache": { "hit": false, "key": "llm:...", "ttlSeconds": 21600 }
}
```

## 架构

```text
business service
        │  POST /llm/tasks/{task_type}
        ▼
    llm-service (8080)
    ├─ validators            (request / output)
    ├─ cache                 (memory or redis)
    ├─ Registry              (load config/providers.json)
    ├─ Router                (single 或 multi_persona)
    ├─ providers/
    │    ├─ mock.py
    │    ├─ zhihu_direct.py
    │    └─ openai_compat.py (env 缺失时不注册)
    ├─ prompts/v1/
    │    ├─ <task>.md
    │    └─ personas/<id>.md
    └─ Tracer                (output/llm-trace/*.jsonl)
```

## 多 LLM 视角

### 单视角路由（默认）

`config/providers.json` 内 `routing.per_task` 为每个 task 指定主 provider + fallback，例如：

```json
"summarize-content": {"provider": "zhihu_direct", "fallback": "mock"}
```

主 provider 失败时降级到 fallback，并在响应里 `fallback=true`、`routeMeta.fallbackTo=...`。

### 多 persona（圆桌审稿）

`roundtable-review` 在 `config/providers.json` 中声明为 `mode: multi_persona`，并列出 4 个 reviewer：

```json
"roundtable-review": {
  "mode": "multi_persona",
  "personas": [
    {"id": "logic_reviewer", "provider": "zhihu_direct", "persona_prompt": "personas/logic_reviewer.md"},
    {"id": "human_editor",   "provider": "zhihu_direct", "persona_prompt": "personas/human_editor.md"},
    {"id": "opponent_reader","provider": "zhihu_direct", "persona_prompt": "personas/opponent_reader.md"},
    {"id": "community_editor","provider": "zhihu_direct", "persona_prompt": "personas/community_editor.md"}
  ]
}
```

router 行为：

- 4 个 persona 通过线程池并发调用各自 provider。
- 每个 persona 的 `persona_prompt` 拼接到主 prompt 之后再发送。
- 任一 persona 失败 → 仅该 persona 走 mock 替补；其它继续。
- 输出聚合：`output.reviews[]` 含 `_persona / _provider` 标注，按 `severity (high → medium → low)` 排序。
- `subCalls` 给出每个 persona 的 provider、fallback、latencyMs。
- 整体缓存命中跳过所有 persona 子调用（保证 reviewer 一致性）。

### Provider 全局开关

```text
LLM_PROVIDER_MODE=mock   # 强制所有 task / persona 走 mock（默认，离线开发）
LLM_PROVIDER_MODE=zhihu  # 走 config 路由（zhihu_direct + mock fallback）
```

OpenAI 兼容 provider 需要同时配 `OPENAI_COMPAT_BASE_URL` 和 `OPENAI_COMPAT_API_KEY`，否则 registry 不注册（current stub 会抛错）。

## Trace

每次 `LlmService.run_task` 写一行 jsonl：

```json
{
  "ts": "2026-05-11T10:30:12",
  "taskType": "roundtable-review",
  "mode": "multi_persona",
  "provider": "multi_persona",
  "fallback": false,
  "cacheHit": false,
  "latencyMs": 182,
  "promptVersion": "v1",
  "schemaVersion": "v1",
  "inputHash": "abc...",
  "subCalls": [
    {"personaId": "logic_reviewer", "provider": "zhihu_direct", "fallback": false, "latencyMs": 120}
  ]
}
```

文件路径：`${LLM_TRACE_DIR}/<YYYY-MM-DD>.jsonl`，默认 `output/llm-trace/`，测试可通过 `LLM_TRACE_ENABLED=0` 关闭。

## 启动

```bash
cd services/llm-service
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```

## 测试

```bash
python3 -m unittest discover -s services/llm-service/tests -v
python3 -m py_compile services/llm-service/app/*.py services/llm-service/app/providers/*.py services/llm-service/tests/*.py
```

当前 10 个用例覆盖：mock 全 task、cache 命中、task 不匹配、zhihu provider 失败 fallback、provider_mode 切换、openai_compat 缺 env 不注册、multi_persona 4 reviewer 聚合、persona 单点失败仅替补、trace 字段完整。

## 环境变量

```text
LLM_PROVIDER_MODE=mock | zhihu
LLM_DEFAULT_MODEL=zhida-thinking-1p5
LLM_PROMPT_VERSION=v1
LLM_SCHEMA_VERSION=v1
LLM_CACHE_BACKEND=memory | redis
REDIS_URL=redis://127.0.0.1:6379/0
LLM_CACHE_TTL_SECONDS=21600
LLM_REQUEST_TIMEOUT_SECONDS=20
LLM_TRACE_DIR=output/llm-trace
LLM_TRACE_ENABLED=1 | 0
ZHIHU_ADAPTER_URL=http://127.0.0.1:8070
# OpenAI 兼容 provider（v0.5 不强制启用）
OPENAI_COMPAT_BASE_URL=
OPENAI_COMPAT_API_KEY=
OPENAI_COMPAT_MODEL=
```

## 缓存键

```text
llm:{task_type}:{input_hash}:{prompt_version}:{schema_version}
```

multi_persona 整体作为一条缓存条目，命中后跳过所有子 persona 调用。

## 允许修改

- `services/llm-service/**`
- `services/llm-service/prompts/**`
- `services/llm-service/config/providers.json`
- `packages/shared-schemas/**` 中 llm task schema

## 禁止修改

- `zhihu-adapter` 三类鉴权实现
- 业务服务状态机
- 前端页面

## 参考文档

- `docs/看山小苗圃-开发设计与实施.md`（多 LLM 视角框架）
- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/知乎API.md`
- `docs/看山小苗圃-技术文档.md`

## 验收标准（v0.5）

- 每个 task 在 mock 模式下输出仍满足 `validators.TASK_REQUIRED_KEYS`。
- `LLM_PROVIDER_MODE=zhihu` 切换主 provider，下游不感知。
- roundtable-review mock 路由下返回 4 个 reviewer，按 severity 排序，每条带 `_persona` 和 `_provider`。
- 同输入二次调用命中 cache，subCalls 不重复执行。
- `output/llm-trace/<日期>.jsonl` 至少包含一条记录，字段齐全。
