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

## 项目是什么

看山小苗圃是一个围绕知乎内容生态设计的读写一体创作工作台。它不从空白输入框开始让 AI 直接生成文章，而是把创作拆成一条更符合真实习惯的链路：

```text
看见好内容
  -> 形成真实观点
  -> 沉淀观点种子
  -> 在合适热点下发芽
  -> 进入写作苗圃逐步成文
  -> 用反馈修正画像和表达方式
```

产品核心是三件事：

| 模块 | 作用 |
|:---|:---|
| 今日看什么 | 从知乎热榜、知乎搜索、全网搜索、关注流等输入中筛选值得看的内容，并组织成面向创作的阅读卡片 |
| 观点种子库 | 保存用户阅读后的认同、反对、疑问、材料和初步观点，而不是只收藏原始内容 |
| 写作苗圃 | 通过观点确认、蓝图、大纲、初稿、圆桌审稿和定稿，把观点逐步整理成可发布草案 |

看山小苗圃强调：**AI 辅助表达，但不替用户决定立场。**

---

## 为什么要做

知乎创作者面对的核心问题不是“不会让 AI 写一篇文章”，而是：

1. **不知道看什么**
   信息流、热榜、关注流和搜索结果都很丰富，但用户很容易被碎片内容牵着走。看山小苗圃希望把输入重新筛选、解释和组织，让用户少看一点，但看得更准。

2. **看完没有沉淀**
   点赞、收藏和转发保存的是内容本身，不一定保存用户当时的想法。项目用“观点种子”保存用户对内容的反应、疑问、反方和可写角度。

3. **有观点但写不清楚**
   很多用户不是没有表达欲，而是不知道如何确认观点、组织论证、回应反方和补充个人经验。写作苗圃把写作拆成可控步骤，让用户始终能修改、重生成和决定是否继续。

4. **AI 内容需要质量边界**
   项目不鼓励无上下文的一键代写。所有生成都应基于用户看过的内容、选择的立场、积累的材料和确认过的 Memory。

---

## 产品闭环

```text
知乎 OAuth 与用户画像
  -> 兴趣 Memory / 写作偏好 / LLM 配置
  -> 今日看什么
  -> 用户表态、提问、加入种子
  -> 观点种子库与继续浇水
  -> 今日发芽手动触发
  -> 写作苗圃逐步成文
  -> 用户复制定稿并自行发布
  -> 历史反馈沉淀为下一轮创作资产
```

## 项目完成度

当前版本已经具备一条完整可演示的读写创作链路：从知乎真实内容输入，到用户画像和 Memory 注入，再到观点种子、今日发芽和写作苗圃。

| 能力 | 完成度 | Demo 展示点 |
|:---|:---:|:---|
| 知乎输入 | 已接入 | 热榜、知乎搜索、全网搜索、OAuth 关注流可进入内容链路 |
| 用户画像 / Memory | 已接入 | 用户兴趣、写作偏好、知乎授权数据和 LLM 配置可形成创作上下文 |
| 今日看什么 | 可演示 | 基于真实知乎数据生成兴趣卡片，支持刷新浏览、展开来源、转化观点种子 |
| 观点种子库 | 可演示 | 支持认同/反对/疑问、继续浇水、材料沉淀和成熟度管理 |
| 今日发芽 | 可演示 | 用户主动触发后，结合热点、种子和 Memory 推荐写作机会 |
| 写作苗圃 | 可演示 | 支持核心观点、论证蓝图、大纲、初稿、圆桌审稿和定稿草案 |
| LLM 服务 | 已接入 | 支持平台能力、用户自配 LLM、任务路由、失败兜底和前端提示 |
| 历史反馈 | 方案成型 | 可承接发布后的评论摘要、二次选题和画像更新建议 |
| 部署运维 | 可部署 | Docker Compose、数据库同步、版本备份和一键回滚脚本已整理 |

发布阶段的产品口径是：系统生成定稿草案，用户检查后复制并自行发布到知乎，保证最终内容经过人工确认；平台侧记录创作结果并进入反馈分析链路。

---

## 技术架构

项目采用前后端分离 + FastAPI 微服务架构。前端只访问 `api-gateway`，后端服务通过统一 DTO、Redis 短缓存和 PostgreSQL 持久化协作。

```text
frontend/                  Next.js 前端工作台
services/                  FastAPI 微服务
  ├── api-gateway/         前端统一入口、服务代理、错误格式
  ├── profile-service/     用户、知乎绑定、画像、Memory、LLM 配置
  ├── content-service/     今日看什么卡片、内容池、刷新浏览
  ├── seed-service/        观点种子、疑问线程、浇水材料、成熟度
  ├── sprout-service/      今日发芽机会计算
  ├── writing-service/     写作苗圃状态机
  ├── feedback-service/    历史反馈与二次创作资产
  ├── zhihu-adapter/       知乎 API 适配、Redis 缓存、额度控制
  └── llm-service/         LLM provider 路由、任务模板、兜底策略
packages/
  ├── shared-python/       配置、日志、数据库等共享能力
  └── shared-schemas/      DTO / OpenAPI / JSON Schema
infra/                     Docker Compose、PostgreSQL 初始化脚本
docs/                      产品、算法、接口、部署和协作文档
scripts/                   本地启动、部署、数据库同步脚本
```

### 服务端口

| 服务 | 端口 | 服务 | 端口 |
|:---|:---:|:---|:---:|
| frontend | 3000 | writing-service | 8050 |
| api-gateway | 8000 | feedback-service | 8060 |
| profile-service | 8010 | zhihu-adapter | 8070 |
| content-service | 8020 | llm-service | 8080 |
| seed-service | 8030 | sprout-service | 8040 |

### 核心技术点

| 方向 | 设计 |
|:---|:---|
| 知乎能力接入 | `zhihu-adapter` 拆分 Community / OAuth / Data Platform 客户端，统一映射为内部 `ZhihuContentItem` |
| 缓存与额度 | Redis 短缓存，缓存命中不扣额度，缓存 miss 后检查 quota 再回源 |
| 今日看什么 | 先构建与用户无关的内容池，再按用户兴趣、画像和行为现场计算卡片 |
| 今日发芽 | 用户主动触发，用热点缓存、种子成熟度、Memory 和近期卡片计算写作机会 |
| 写作苗圃 | 后端维护写作状态机，前端按阶段展示观点、蓝图、大纲、初稿、审稿和定稿 |
| LLM 路由 | 平台 LLM 处理通用摘要和提取；用户自配 LLM 处理个人观点、写作内容和 Memory 注入 |

---

## 文档导航

完整文档索引见 [docs/README.md](docs/README.md)。常用入口如下：

| 类型 | 文档 |
|:---|:---|
| 产品与 Demo | [产品文档](docs/看山小苗圃-产品文档.md) / [项目完成度与 Demo 说明](docs/看山小苗圃-项目完成度与Demo说明.md) / [核心流程校准方案](docs/看山小苗圃-核心流程校准方案.md) |
| 算法与 Agent | [今日看什么卡片获取与推流设计](docs/看山小苗圃-今日看什么卡片获取与推流设计.md) / [今日发芽算法实现方案](docs/看山小苗圃-今日发芽算法实现方案.md) / [高风险核心任务细化说明](docs/看山小苗圃-高风险核心任务细化说明.md) |
| 画像与反馈 | [OAuth 数据汇总与画像生成算法](docs/看山小苗圃-OAuth数据汇总与画像生成算法.md) / [历史反馈实现方案](docs/看山小苗圃-历史反馈实现方案.md) |
| 接口与服务 | [接口功能与数据流文档](docs/看山小苗圃-接口功能与数据流文档.md) / [服务拆分与开发协作](docs/看山小苗圃-服务拆分与开发协作.md) / [知乎 API](docs/知乎API.md) |
| 数据库与部署 | [数据库结构定稿](docs/数据库结构定稿.md) / [实际部署清单与一键脚本](docs/看山小苗圃-实际部署清单与一键脚本.md) / [部署指南](docs/部署指南.md) |
| 协作约束 | [AI-Coding 任务分发模板](docs/AI-Coding任务分发模板.md) / [工程约束与提交规范](docs/工程约束与提交规范.md) |

---

## 快速开始

### 本地开发

```bash
git clone https://github.com/Nai1ve/kan_shan_nursery.git
cd kan_shan_nursery

# Docker 启动基础依赖，并按脚本启动后端和前端
bash scripts/dev_up.sh
```

前端入口：

```text
http://127.0.0.1:3000
```

### 线上部署

```bash
cd /opt/kanshan
git pull
bash scripts/deploy.sh
```

部署脚本负责备份当前版本、同步数据库 schema、构建镜像并启动服务。

```bash
# 查看备份
bash scripts/deploy.sh --list-backups

# 回滚到最近一次备份
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
| 4 | 昂贵 LLM 任务必须由用户主动触发 |
| 5 | Memory 更新需要用户可感知、可确认、可拒绝 |
| 6 | 前端只调用 api-gateway，不直接调用业务服务 |
| 7 | 涉及用户个人内容优先走用户自配 LLM，通用提取走平台能力 |
| 8 | 定稿由用户复制并自行发布，最终表达权保留给用户 |

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
