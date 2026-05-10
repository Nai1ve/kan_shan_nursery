# Frontend

前端应用目录。当前已具备 Next.js mock 闭环，后续逐步从本地 mock API 切换到 `api-gateway`。

优先级：P1
难度：M

## 边界

负责：

- 页面展示和用户交互。
- 登录 / 演示模式入口。
- 今日看什么、种子库、今日发芽、写作苗圃、历史反馈、画像页。
- 卡片展开、来源展开、弹窗、表单、Toast 等 UI 状态。
- 调用 `api-gateway` 的前端 client。

不负责：

- 不直接调用知乎 API。
- 不直接调用 Redis。
- 不直接调用 LLM / 直答 Agent。
- 不在前端实现后端业务权威逻辑；mock 阶段可临时保留，接 API 后迁移到服务端。

## P0/P1 任务

- 保持当前 mock 闭环可演示。
- 将 `frontend/lib/types.ts` 与 `packages/shared-schemas` 对齐。
- 把 `frontend/lib/api-client.ts` 从 `/api/mock/*` 逐步切到 `/api/v1/*`。
- 今日看什么接入 content API。
- 种子库接入 seed API。
- 写作苗圃接入 writing API，保留 `memoryOverride` 可编辑。
- 历史反馈接入 feedback API。

## 允许修改

- `frontend/**`
- `packages/shared-schemas/**` 中前端类型镜像

## 禁止修改

- 后端服务业务逻辑。
- `docs/知乎API.md`。
- 服务 README 的边界定义，除非同步更新总文档。

## 参考文档

- `docs/kanshan_nursery_prototype.html`
- `docs/看山小苗圃-接口功能与数据流文档.md`
- `docs/看山小苗圃-产品文档.md`
- `frontend/lib/types.ts`

## 本地运行

```bash
npm install
npm run dev
```

默认访问 `http://127.0.0.1:3000`。

当前本地 mock API：

- `GET /api/mock/profile`
- `GET /api/mock/content`
- `GET /api/mock/seeds`
- `GET /api/mock/sprout`
- `GET /api/mock/feedback`

## 验收标准

```bash
npm run lint
npm run build
```

浏览器验收：

- 切换所有兴趣分类、关注流、偶遇输入。
- 来源全文可展开。
- 有疑问、继续浇水、开始写作、模拟发布完整闭环可用。
- 390px 移动端无明显按钮重叠。
