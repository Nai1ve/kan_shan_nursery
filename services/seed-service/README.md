# seed-service

观点种子服务。它是“看什么”和“写什么”之间的状态中心。

优先级：P0
难度：M

## 边界

负责：

- 从内容卡片创建或更新观点种子。
- 用户 reaction：认同、反对、有疑问、补充、想写。
- 疑问线程和多轮追问状态。
- 四格浇水材料。
- 成熟度计算和状态流转。
- 合并相似种子。

不负责：

- 不直接调用知乎 API。
- 不生成内容卡片。
- 不生成完整文章。
- 不更新长期 Memory。

## P0 任务

- `GET /health`
- `GET /seeds`
- `POST /seeds`
- `POST /seeds/from-card`
- `GET /seeds/{seed_id}`
- `PATCH /seeds/{seed_id}`
- `POST /seeds/{seed_id}/questions`
- `PATCH /seeds/{seed_id}/questions/{question_id}`
- `POST /seeds/{seed_id}/materials`
- `PATCH /seeds/{seed_id}/materials/{material_id}`
- `DELETE /seeds/{seed_id}/materials/{material_id}`
- `POST /seeds/{seed_id}/materials/agent-supplement`
- `POST /seeds/{target_seed_id}/merge`

## 当前实现

P0 使用内存仓储，进程重启后数据会丢失。服务实现保持和 `packages/shared-schemas/schemas/seed.json` 对齐，后续替换为数据库仓储时只需要替换 repository 层。

启动：

```bash
cd services/seed-service
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8030 --reload
```

测试：

```bash
python3 -m unittest discover -s services/seed-service/tests -v
python3 -m py_compile services/seed-service/app/*.py services/seed-service/tests/*.py
```

示例：

```bash
curl -X POST http://127.0.0.1:8030/seeds/from-card \
  -H 'Content-Type: application/json' \
  -d '{"cardId":"card-ai-coding-001","reaction":"agree","userNote":"这个方向值得写"}'
```

## 计算规则

```text
maturityScore =
min(96, 32 + 已采纳材料类型数 * 14 + 疑问总数 * 3 + 已解决疑问数 * 4)
```

状态：

```text
writing / published 保持
否则 maturityScore >= 70 → sproutable
否则 → water_needed
```

## 允许修改

- `services/seed-service/**`
- `packages/shared-schemas/**` 中 seed schema

## 禁止修改

- `content-service` 卡片生成逻辑
- `writing-service` session 状态机
- `profile-service` Memory 存储

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `frontend/lib/types.ts`
- `docs/看山小苗圃-技术文档.md`

## 验收标准

- 从同一 `cardId` 多次操作不会重复创建多个种子。
- `有疑问` 会生成 `SeedQuestion` 和浇水材料。
- 标记已解决 / 仍需补材料会改变问题状态和成熟度。
- 材料新增、编辑、删除、采纳后成熟度符合公式。


## 启动

依赖（建议在每个服务用独立 venv 隔离，也可以全仓库共用一个）：

```bash
cd services/seed-service
python3 -m venv .venv && source .venv/bin/activate    # 可选
pip install -r requirements.txt
```

启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8030 --reload
```

健康检查：

```bash
curl -s http://127.0.0.1:8030/health | python3 -m json.tool
```

预期输出：

```json
{
  "status": "ok",
  "service": "seed-service"
}
```

## 测试

```bash
python3 -m unittest discover -s services/seed-service/tests -v
python3 -m py_compile services/seed-service/app/*.py services/seed-service/tests/*.py
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

- `output/logs/seed-service-YYYY-MM-DD.jsonl`（机器可读）
- 控制台 stderr（人读一行）

## 一键启动 9 个服务

```bash
bash scripts/run_all_services.sh         # 仅后端
bash scripts/dev_up.sh                   # 后端 + 前端，前端切到 gateway 模式
```
