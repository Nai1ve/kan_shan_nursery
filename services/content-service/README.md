# content-service

今日看什么和内容输入服务。它只解决“看什么”，不创建观点种子。

优先级：P0
难度：M

## 边界

负责：

- 兴趣小类、关注流、偶遇输入三类平级输入。
- Query Plan 生成。
- 调用 `zhihu-adapter` 获取标准 `ZhihuContentItem`。
- 聚合 2-3 个来源为 `WorthReadingCard`。
- 卡片评分、摘要、争议点、可写角度。
- 来源全文展示所需数据。
- 当前分类刷新和候选池轮换。

不负责：

- 不创建、修改观点种子。
- 不计算成熟度。
- 不执行今日发芽。
- 不直接调用知乎 API 或 Redis。

## P0 任务

- `GET /health`
- `GET /content`
- `GET /content/cards?category_id=ai-coding`
- `GET /content/cards/{card_id}`
- `GET /content/cards/{card_id}/sources/{source_id}`
- `POST /content/categories/{category_id}/refresh`
- `POST /content/cards/{card_id}/summarize`

## 计算规则

```text
relevanceScore =
兴趣匹配 35%
+ authorityLevel / rankingScore 20%
+ VoteUpCount / CommentCount 15%
+ 争议点数量 15%
+ EditTime / 热榜排序 10%
+ 可写角度质量 5%
```

## 允许修改

- `services/content-service/**`
- `packages/shared-schemas/**` 中 content schema

## 禁止修改

- `zhihu-adapter` 官方字段映射
- `seed-service` 种子写入逻辑
- `profile-service` Memory 存储逻辑

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/知乎API.md`
- `frontend/lib/types.ts`

## 验收标准

- 每个兴趣分类至少能返回 2-3 张卡片。
- 关注流和偶遇输入作为独立分类返回。
- 卡片包含 `originalSources`，来源可展示完整内容。
- 刷新当前分类不影响种子、写作 session、画像。
