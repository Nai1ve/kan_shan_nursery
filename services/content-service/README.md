# content-service

今日看什么和内容输入服务。

职责：

- 按输入分类展示内容。
- 兴趣小类内容卡片。
- 关注流精选。
- 偶遇输入。
- 多来源原始出处保留。
- 内容摘要、争议点、可写角度。

P0 接口：

- `GET /health`
- `GET /content/today?category_id=ai-coding`
- `GET /content/cards/{card_id}`
- `POST /content/cards/{card_id}/summarize`
