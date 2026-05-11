# 看山小苗圃

看山小苗圃是一个面向知乎创作者的读写一体 AI 创作 Agent。它不是 AI 代写，而是把"看到好内容 → 沉淀好观点 → 写出好表达"做成可追溯的工作台。

```text
看到好内容
  ↓
产生想法 / 提疑问
  ↓
沉淀观点种子
  ↓
今日发芽（热点 × 历史种子）
  ↓
写作苗圃 8 步
  ↓
圆桌审稿（4 视角并发）
  ↓
定稿草案
  ↓
历史反馈回流 Memory
```

---

## 五分钟跑起来（mock 模式，不需要任何凭证）

```bash
# 1. 准备 Python 依赖（首次）
for s in services/*/; do pip install -r "$s/requirements.txt"; done

# 2. 给后端建一份本地配置（已被 .gitignore，可以随便填）
cp services/config.example.yaml services/config.yaml

# 3. 准备前端依赖（首次）
(cd frontend && npm install)

# 4. 一键起 9 个后端服务 + 前端（前端切到 gateway 模式）
bash scripts/dev_up.sh
```

打开 <http://127.0.0.1:3000> 选 "演示模式" 即可。

如果只想跑前端 mock 模式（零后端依赖）：

```bash
cd frontend && npm run dev
```

---

## 路线图（v0.1 - v0.9）

| 版本 | 内容 | 状态 |
| --- | --- | --- |
| v0.1-v0.4 | 文档、骨架、P0 mock 闭环 | ✅ 已完成 |
| v0.5 | LLM 基座 + 多视角 Agent 框架 + 网关联调 | ✅ 已完成 |
| v0.6 | 知乎 live 接入 + OAuth + quota + 全服务结构化日志 + 前端切到 gateway | ✅ 已完成 |
| v0.7 | 创作输入流推流算法 + 种子浇水强化 | 🔴 待开始 |
| v0.8 | 发芽算法 + 写作苗圃接 LLM + 圆桌 4 视角真实并发 | 🔴 待开始 |
| v0.9 | 反馈回流 + 评测指标 + Demo 演示打磨 | 🔴 待开始 |

详细版本说明：[docs/开发路线图.md](docs/开发路线图.md)
设计与实施总纲：[docs/看山小苗圃-开发设计与实施.md](docs/看山小苗圃-开发设计与实施.md)
v0.6 联调验证清单：[docs/v0.6-联调验证-checklist.md](docs/v0.6-联调验证-checklist.md)
v0.4 P0 mock 验证清单：[docs/P0-mock-闭环-测试checklist.md](docs/P0-mock-闭环-测试checklist.md)

---

## 仓库结构

```text
frontend/                  Next.js 前端（同时支持 mock 与 gateway 两种后端模式）
services/                  9 个 FastAPI 后端
  ├── api-gateway/         8000  前端唯一入口
  ├── profile-service/     8010  用户画像 + Memory
  ├── content-service/     8020  今日看什么
  ├── seed-service/        8030  观点种子 + 浇水
  ├── sprout-service/      8040  今日发芽
  ├── writing-service/     8050  写作苗圃 8 步
  ├── feedback-service/    8060  历史反馈
  ├── zhihu-adapter/       8070  知乎能力出口（mock / live）
  └── llm-service/         8080  LLM 任务路由 + 多 persona
  config.example.yaml      凭证 / 配置模板；复制为 config.yaml 后填
packages/
  ├── shared-python/       kanshan_shared（config loader + structured logging）
  └── shared-schemas/      OpenAPI / JSON Schema / examples
infra/                     docker-compose（postgres + redis）
docs/                      产品 / 技术 / 算法 / 开发设计文档
scripts/                   run_all_services.sh / dev_up.sh
output/                    运行时产物（日志 / trace）。.gitignored
```

---

## 依赖

- **Python 3.10+**：所有后端服务。
- **Node.js 20+ / npm**：前端。
- **Redis**（可选）：默认 `cache.backend=memory`，演示无需。要切到 Redis 改 `services/config.yaml`。
- **真实知乎凭证**（可选）：默认 `provider_mode=mock`，所有功能用 fixture；切到 live 需要在 `services/config.yaml` 填三类凭证，详见 [services/zhihu-adapter/README.md](services/zhihu-adapter/README.md)。

---

## 后端模式切换

`services/config.yaml`：

```yaml
provider_mode: mock         # 演示 / 离线开发
# provider_mode: live       # 真实知乎接入；需填 zhihu.community / oauth / data_platform
```

前端模式 `frontend/.env.local`（拷自 `frontend/.env.example`）：

```text
NEXT_PUBLIC_KANSHAN_BACKEND_MODE=mock        # 默认；走 Next.js /api/mock/*
# NEXT_PUBLIC_KANSHAN_BACKEND_MODE=gateway   # 真实联调；走 :8000/api/v1/*
NEXT_PUBLIC_KANSHAN_GATEWAY_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ZHIHU_ADAPTER_URL=http://127.0.0.1:8070
```

---

## 测试

```bash
# 全量后端单元测试（80 ok / 0 fail）
for svc in services/*/; do
  python3 -m unittest discover -s "$svc/tests"
done
python3 -m unittest discover -s packages/shared-python/tests
```

各服务单独测试见对应 `services/<svc>/README.md`。

---

## 开发原则

- 先跑通 P0 演示闭环，再接真实知乎接口。
- 每个服务必须先支持 mock 模式。
- 前端只调用 `api-gateway`，业务服务之间只通过 HTTP API 通信。
- 知乎 token / 模型 key 只放 `services/config.yaml` 或环境变量（绝不进 git）。
- 昂贵任务必须用户主动触发；Memory 更新必须用户确认。
- 每完成一个小版本就提交一次 Git。
