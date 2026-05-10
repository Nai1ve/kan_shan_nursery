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
