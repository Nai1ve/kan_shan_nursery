# Frontend

前端应用目录。

P0 目标：

- 从 `docs/kanshan_nursery_prototype.html` 迁移核心页面。
- 只调用 `api-gateway`。
- 支持演示模式。
- 串联完整 mock 闭环。

页面：

- 登录 / 首次画像采集
- 今日看什么
- 我的种子库
- 今日发芽
- 写作苗圃
- 历史反馈
- 个人画像 / Memory

## 本地运行

```bash
npm install
npm run dev
```

默认访问 `http://127.0.0.1:3000`。当前阶段仅使用 Next.js 本地 mock API：

- `GET /api/mock/profile`
- `GET /api/mock/content`
- `GET /api/mock/seeds`
- `GET /api/mock/sprout`
- `GET /api/mock/feedback`

## 校验

```bash
npm run lint
npm run build
```
