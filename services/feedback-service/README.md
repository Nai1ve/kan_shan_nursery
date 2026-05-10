# feedback-service

历史反馈服务。它把发布后的互动数据转成二次创作资产。

优先级：P2
难度：S

## 边界

负责：

- 历史文章反馈列表。
- 评论摘要。
- 支持观点、反方观点、补充材料提取。
- 二次文章种子建议。
- Memory 更新建议。

不负责：

- 不直接写入 Memory。
- 不直接发布文章。
- 不直接调用知乎评论接口，必须通过 `zhihu-adapter`。

## P0 任务

- `GET /health`
- `GET /feedback/articles`
- `GET /feedback/articles/{article_id}`
- `POST /feedback/sync`
- `GET /feedback/articles/{article_id}/comments-summary`
- `POST /feedback/articles/{article_id}/second-seed`
- `POST /feedback/articles/{article_id}/memory-update-request`

## 允许修改

- `services/feedback-service/**`
- `packages/shared-schemas/**` 中 feedback schema

## 禁止修改

- `profile-service` Memory apply/reject 逻辑
- `seed-service` 种子主表
- `zhihu-adapter` 评论字段映射

## 参考文档

- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-技术文档.md`

## 验收标准

- 可返回 mock 文章反馈列表。
- 评论摘要能生成反方观点和补充材料。
- 二次文章操作能创建 seed 请求或返回 seed payload。
- Memory 只生成更新建议，不自动生效。
