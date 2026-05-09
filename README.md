# 看山小苗圃

看山小苗圃是一个面向知乎创作者的读写一体 AI 创作 Agent。

核心链路：

```text
看到好内容
↓
产生想法
↓
沉淀观点种子
↓
今日发芽
↓
写作苗圃
↓
圆桌审稿
↓
定稿草案
↓
历史反馈回流 Memory
```

## 当前基线

权威文档在 `docs/`：

- `看山小苗圃-产品文档.md`
- `看山小苗圃-技术文档.md`
- `看山小苗圃-服务拆分与开发协作.md`
- `kanshan_nursery_prototype.html`

后续实现以产品文档和技术文档为准，原型作为交互参考。

## 仓库结构

```text
frontend/                 前端应用
services/                 后端服务
packages/shared-schemas/  共享接口契约
packages/shared-python/   Python 共享工具
infra/                    本地和演示部署配置
docs/                     产品、技术和协作文档
scripts/                  本地辅助脚本
```

## 开发原则

- 先跑通 P0 演示闭环，再接真实知乎接口。
- 每个服务必须先支持 mock 模式。
- 前端只调用 `api-gateway`。
- Token、知乎接口凭证、模型 key 只放后端环境变量。
- 昂贵任务必须用户主动触发。
- Memory 更新必须用户确认后写入。
- 每完成一个小版本就提交一次 Git。

## Git 工作流

当前仓库使用 Git 管理。建议按小版本提交：

```text
v0.1 文档和原型
v0.2 目录与契约骨架
v0.3 服务 health check
v0.4 P0 mock 链路
v0.5 LLM service 接入
```

提交前建议运行：

```bash
git status --short
```
