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
