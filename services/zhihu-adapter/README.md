# zhihu-adapter

知乎开放接口适配服务。它是所有知乎 API 的唯一出口，业务服务只能消费标准 DTO。

优先级：P0
难度：M

## 边界

负责：

- Community Client：HMAC 签名，圈子、评论、发布、点赞、故事。
- OAuth Client：Bearer access_token，用户信息、关注列表、粉丝列表、关注动态。
- Data Platform Client：Bearer access_secret，热榜、知乎搜索、全网搜索、直答。
- Redis 短缓存。
- 额度计数与写操作节流。
- 官方 raw 字段映射为 `ZhihuContentItem`。

不负责：

- 不生成 `WorthReadingCard`。
- 不生成观点种子。
- 不写用户画像。
- 不决定文章是否发布，只提供受控发布接口。

## P0 任务

- `GET /health`
- `GET /zhihu/hot-list`
- `GET /zhihu/zhihu-search`
- `GET /zhihu/global-search`
- `POST /zhihu/direct-answer`
- `GET /zhihu/ring-detail`
- `GET /zhihu/comments`
- `GET /zhihu/story-list`
- `GET /zhihu/story-detail`
- `GET /zhihu/following-feed`
- `GET /zhihu/user-followed`
- `GET /zhihu/user-followers`
- `POST /zhihu/publish/mock-or-live`
- `POST /zhihu/comment/create`
- `POST /zhihu/reaction`

## Redis Key

```text
zhihu:hot_list:{limit}
zhihu:zhihu_search:{query_hash}:{count}
zhihu:global_search:{query_hash}:{count}
zhihu:direct_answer:{model}:{messages_hash}:stream_false
zhihu:ring_detail:{ring_id}:{page_num}:{page_size}
zhihu:comment_list:{content_type}:{content_token}
zhihu:story_list
zhihu:story_detail:{work_id}
zhihu:user_moments:{user_id}
zhihu:user_followed:{user_id}:{page}:{per_page}
zhihu:user_followers:{user_id}:{page}:{per_page}
quota:{endpoint}:{user_id}:{yyyyMMdd}
```

## 允许修改

- `services/zhihu-adapter/**`
- `packages/shared-schemas/**` 中 zhihu schema

## 禁止修改

- 业务服务内部评分、种子、发芽、写作逻辑
- 前端页面
- `docs/知乎API.md`

## 参考文档

- `docs/知乎API.md`
- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/工程约束与提交规范.md`

## 验收标准

- 三类鉴权逻辑隔离。
- 读取型接口第二次相同请求命中 Redis。
- 缓存命中不增加 quota。
- 热榜、知乎搜索、全网搜索、故事、关注动态都能映射到 `ZhihuContentItem`。
- 真实发布/评论/点赞必须支持 mock/live 开关，默认 mock。
