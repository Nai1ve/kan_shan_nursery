# sprout-service

今日发芽服务。它只在用户主动触发后运行，用历史种子匹配今日热点和新信息。

优先级：P2
难度：VH

## 边界

负责：

- 创建发芽 run。
- 读取未发布种子、兴趣 Memory、热点/搜索/关注流信号。
- 计算 `activationScore`。
- 生成 `SproutOpportunity`。
- 当日 Redis 缓存。
- 补充资料、换角度、暂时不写、开始写作。

不负责：

- 不创建基础观点种子。
- 不生成完整文章。
- 不直接调用知乎 API。
- 不修改长期 Memory。

## P0 任务

- `GET /health`
- `POST /sprout/start`
- `GET /sprout/runs/{run_id}`
- `GET /sprout/opportunities`
- `POST /sprout/opportunities/{opportunity_id}/supplement`
- `POST /sprout/opportunities/{opportunity_id}/switch-angle`
- `POST /sprout/opportunities/{opportunity_id}/dismiss`
- `POST /sprout/opportunities/{opportunity_id}/start-writing`

## 计算规则

```text
activationScore =
种子成熟度 25%
+ 热点相关性 25%
+ 时效性 20%
+ 新信息增益 15%
+ 写作潜力 15%
- 重复发布惩罚
- 证据不足惩罚
```

## 允许修改

- `services/sprout-service/**`
- `packages/shared-schemas/**` 中 sprout schema

## 禁止修改

- `seed-service` 的成熟度公式
- `content-service` 的卡片评分
- `writing-service` 的写作状态机

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-技术文档.md`

## 验收标准

- 未发布种子可以生成发芽机会。
- 同日同输入命中 `sprout:*` 缓存。
- 补充资料能回写 seed material。
- 换角度只修改 opportunity，不改 seed 原始观点。


## 启动

依赖（建议在每个服务用独立 venv 隔离，也可以全仓库共用一个）：

```bash
cd services/sprout-service
python3 -m venv .venv && source .venv/bin/activate    # 可选
pip install -r requirements.txt
```

启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8040 --reload
```

健康检查：

```bash
curl -s http://127.0.0.1:8040/health | python3 -m json.tool
```

预期输出：

```json
{
  "status": "ok",
  "service": "sprout-service"
}
```

## 测试

```bash
python3 -m unittest discover -s services/sprout-service/tests -v
python3 -m py_compile services/sprout-service/app/*.py services/sprout-service/tests/*.py
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

- `output/logs/sprout-service-YYYY-MM-DD.jsonl`（机器可读）
- 控制台 stderr（人读一行）

## 一键启动 9 个服务

```bash
bash scripts/run_all_services.sh         # 仅后端
bash scripts/dev_up.sh                   # 后端 + 前端，前端切到 gateway 模式
```
