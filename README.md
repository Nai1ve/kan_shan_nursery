<div align="center">

# 看山小苗圃

**面向知乎创作者的读写一体 AI 创作工作台**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)

*不是让 AI 代写文章，而是把真实创作过程拆成一条可追溯链路*

</div>

![alt text](docs/page.png)
---

## 产品理念

```text
看见好内容 → 形成真实观点 → 沉淀观点种子 → 在合适热点下发芽 → 进入写作苗圃逐步成文 → 用反馈修正画像和表达
```

> 当前项目处于黑客松 Demo 冲刺状态，核心目标是展示"高质量输入 → 观点形成 → 写作表达"的闭环。

---

## 当前进度

<sub>更新时间：2026-05-14</sub>

| 模块 | 状态 | 说明 |
|:---|:---:|:---|
| 登录 / 用户入口 | :green_circle: | 注册登录、知乎 OAuth 绑定、本地跳过授权调试 |
| 用户画像 / Memory | :green_circle: | 基础画像、兴趣 Memory、LLM 配置、OAuth 后画像生成 |
| 知乎能力接入 | :green_circle: | 热榜、搜索、全网搜索、OAuth 关注流链路 |
| 今日看什么 | :blue_circle: | 基于真实知乎数据返回兴趣卡片，支持扩展和刷新浏览 |
| 观点种子库 | :blue_circle: | 卡片转种子、认同/反对/疑问、浇水材料、成熟度 |
| 今日发芽 | :large_orange_diamond: | sprout-service、热点/种子/Memory 匹配和 LLM 任务入口 |
| 写作苗圃 | :blue_circle: | 已接入后端状态机：观点确认 → 蓝图 → 大纲 → 初稿 → 圆桌审稿 → 定稿 |
| LLM 服务 | :green_circle: | 平台兜底、用户自配 LLM、任务路由和失败提示 |
| 历史反馈 | :large_orange_diamond: | Demo 展示和后续扩展，真实数据回流受开放接口限制 |
| 部署 | :green_circle: | Docker Compose 线上部署已跑通 OAuth |

---

## 核心链路

```text
用户登录 / 跳过授权
  ↓
选择兴趣与写作偏好
  ↓
今日看什么：读取热榜 / 搜索 / 关注流 / 全网搜索
  ↓
用户对卡片表态、提问或加入种子库
  ↓
种子库：观点、材料、疑问、反方、成熟度
  ↓
今日发芽：手动触发，用热点和 Memory 激活可写种子
  ↓
写作苗圃：逐步生成观点、蓝图、大纲、草稿、审稿与定稿
  ↓
用户复制定稿并自行发布，系统记录模拟发布与后续反馈建议
```

---

## 已知关键问题

<details>
<summary><b>1. 写作苗圃仍需端到端回归</b></summary>

当前仍需重点回归：

- 用户重新生成 / 手动编辑蓝图后的大纲和初稿状态
- 圆桌审稿中用户发言、Agent 多轮对话、建议采纳和定稿上下文
- 页面刷新后的 writing session 恢复
- 后端 LLM 失败、用户自配 LLM 失效时的前端提示

后续收敛方向：

- 后端 writing-service 返回 `nextAllowedActions`
- 前端完全按 `nextAllowedActions` 控制按钮可用性
- 补充 opportunity → writing session → feedback article 的端到端测试

</details>

<details>
<summary><b>2. 当前没有接入知乎自动发布</b></summary>

写作苗圃最后阶段的真实边界：

1. 生成定稿草案
2. 用户人工检查和修改
3. 用户点击"复制最终稿"
4. 用户自行粘贴到知乎发布
5. 系统只做"模拟发布"记录和后续反馈链路演示

代码中的 `publish/mock` 是 Demo 状态记录，不是真实知乎发布。

</details>

<details>
<summary><b>3. 数据库结构需要同步</b></summary>

部分线上问题来自旧 PostgreSQL 卷未执行新的初始化 SQL。遇到缺字段、缺 schema 时：

```bash
bash scripts/sync_db_schema.sh --docker
```

重点关注：`profile.users.setup_state`、`sprout.opportunities.run_id`、`sprout.runs`、`content.user_profile_snapshots` 等。

</details>

---

## 技术架构

```text
frontend/                  Next.js 前端
services/                  FastAPI 微服务
  ├── api-gateway/         前端唯一入口
  ├── profile-service/     用户、画像、Memory、OAuth 绑定
  ├── content-service/     今日看什么
  ├── seed-service/        观点种子库
  ├── sprout-service/      今日发芽
  ├── writing-service/     写作苗圃
  ├── feedback-service/    历史反馈
  ├── zhihu-adapter/       知乎 API 适配层
  └── llm-service/         LLM provider 路由和 Agent 任务
packages/
  ├── shared-python/       配置、日志、数据库等 Python 共享能力
  └── shared-schemas/      DTO / OpenAPI / JSON Schema
infra/                     Docker Compose、Postgres 初始化脚本
docs/                      产品、技术、算法、部署和任务拆分文档
scripts/                   本地启动、部署、校验脚本
```

### 服务端口

| 服务 | 端口 | 服务 | 端口 |
|:---|:---:|:---|:---:|
| frontend | 3000 | writing-service | 8050 |
| api-gateway | 8000 | feedback-service | 8060 |
| profile-service | 8010 | zhihu-adapter | 8070 |
| content-service | 8020 | llm-service | 8080 |
| seed-service | 8030 | sprout-service | 8040 |

---

## 快速开始

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/Nai1ve/kan_shan_nursery.git
cd kan_shan_nursery

# 一键启动（Docker + 9 个后端服务 + 前端）
bash scripts/dev_up.sh
```

前端入口：http://127.0.0.1:3000

### 线上部署

```bash
cd /opt/kanshan
git pull
bash scripts/deploy.sh
```

部署脚本会自动备份当前版本、同步数据库 schema、构建并启动所有服务。

```bash
# 查看和回滚备份
bash scripts/deploy.sh --list-backups
bash scripts/deploy.sh --rollback latest
```

### 健康检查

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

---

## 开发原则

| # | 原则 |
|:--:|:---|
| 1 | AI 辅助表达，但不替用户决定立场 |
| 2 | 输入质量先于输出质量 |
| 3 | 观点种子是读写闭环的核心资产 |
| 4 | 昂贵 LLM 任务必须用户主动触发 |
| 5 | Memory 更新需要用户可感知、可确认、可拒绝 |
| 6 | 前端只调用 api-gateway，不直接调用业务服务 |
| 7 | 涉及用户个人内容优先走用户自配 LLM，通用提取走平台能力 |

---

<div align="center">

## 关于作者

**刘沛泽** · 全栈开发 · 专注 Agent 开发

期望岗位：**Agent 开发**

<br/>

<img src="./docs/DeepZeCode.jpg" alt="公众号：DeepZeCode" width="200" />

**欢迎关注公众号「DeepZeCode」**

这里有 Agent 开发的实战经验、架构思考和技术探索

也期待各大厂的实习 offer 砸过来 :rocket:

<br/>

:email: **邮箱**：[lpz970821@163.com](mailto:lpz970821@163.com)

:gem: **公众号**：DeepZeCode

</div>
