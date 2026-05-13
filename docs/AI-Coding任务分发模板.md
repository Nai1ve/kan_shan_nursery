# AI Coding 任务分发模板

把任务交给其他模型时，直接复制这个模板，并替换具体内容。

```text
任务名称：

背景：
看山小苗圃是一个知乎读写一体创作 Agent。请先阅读：
- docs/看山小苗圃-产品文档.md
- docs/看山小苗圃-核心流程校准方案.md
- docs/看山小苗圃-接口功能与数据流文档.md
- docs/看山小苗圃-服务拆分与开发协作.md
- docs/工程约束与提交规范.md

只允许修改：
- services/<service-name>/**
- packages/shared-schemas/<domain>/**

不要修改：
- 其他服务目录
- docs，除非任务明确要求
- infra/docker-compose.yml，除非任务明确要求

必须实现：
- <接口 1>
- <接口 2>
- <接口 3>

必须提供：
- Pydantic schema
- FastAPI router
- service/repository 分层
- mock 数据
- README 启动说明
- pytest 样例

验收标准：
- 服务有 /health
- pytest 通过
- OpenAPI 能看到接口
- 不依赖真实知乎接口或真实 LLM
- 不读取其他服务的数据表

输出：
- 简述改动
- 列出修改文件
- 说明如何运行测试
```

## 推荐分发任务

适合交给其他模型：

- `profile-service` 的基础 CRUD。
- `feedback-service` mock 数据和页面接口。
- `zhihu-adapter` mock provider。
- `content-service` 静态 mock 数据。
- 前端表单和列表组件。
- Dockerfile / README 初稿。
- 单元测试样例。

建议 Codex 把关：

- shared schema。
- Memory 注入。
- 种子状态机。
- 今日发芽。
- 写作苗圃 8 步状态机。
- LLM prompt 与 JSON 校验。
- 端到端 demo flow。
