# zhihu-adapter

知乎开放接口适配服务。

职责：

- 统一调用知乎开放接口。
- mock / cached / live 三种模式。
- token 管理。
- 限流和缓存。

P0 接口：

- `GET /health`
- `GET /zhihu/hot-list`
- `GET /zhihu/search`
- `GET /zhihu/global-search`
- `GET /zhihu/following-feed`
- `GET /zhihu/ring-detail`
- `GET /zhihu/comments`
