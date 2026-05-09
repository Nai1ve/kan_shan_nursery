# feedback-service

历史反馈服务。

职责：

- 文章表现 mock / 真实反馈。
- 评论反馈提取。
- 生成新种子建议。
- 生成 Memory 更新建议。

注意：

- feedback-service 不直接写入 Memory。
- Memory 更新建议需要用户在 profile-service/memory 中确认后生效。

P0 接口：

- `GET /health`
- `GET /feedback/articles`
- `GET /feedback/articles/{article_id}`
- `POST /feedback/articles/{article_id}/analyze`
