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


## 启动

依赖（建议在每个服务用独立 venv 隔离，也可以全仓库共用一个）：

```bash
cd services/writing-service
python3 -m venv .venv && source .venv/bin/activate    # 可选
pip install -r requirements.txt
```

启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

健康检查：

```bash
curl -s http://127.0.0.1:8050/health | python3 -m json.tool
```

预期输出：

```json
{
  "status": "ok",
  "service": "writing-service"
}
```

## 测试

```bash
python3 -m unittest discover -s services/writing-service/tests -v
python3 -m py_compile services/writing-service/app/*.py services/writing-service/tests/*.py
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

- `output/logs/writing-service-YYYY-MM-DD.jsonl`（机器可读）
- 控制台 stderr（人读一行）

## 一键启动 9 个服务

```bash
bash scripts/run_all_services.sh         # 仅后端
bash scripts/dev_up.sh                   # 后端 + 前端，前端切到 gateway 模式
```
