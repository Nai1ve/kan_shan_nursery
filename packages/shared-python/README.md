# Shared Python

Python 共享工具目录，只放无业务含义的基础工具。

优先级：P2
难度：S

## 边界

允许放：

- 统一错误结构。
- request id 工具。
- 时间处理。
- 配置读取。
- 日志初始化。
- Redis key hash 工具。
- HMAC 签名底层工具，但不放具体知乎业务 client。

不允许放：

- 业务逻辑。
- service 间共享 repository。
- 具体 Prompt。
- DTO 主定义。
- 任何依赖具体服务表结构的代码。

## P0 任务

- `request_id` helper。
- `error_response` helper。
- `utc_now_iso` / Unix timestamp conversion。
- `stable_json_hash`。
- `settings` 基础读取。

## 允许修改

- `packages/shared-python/**`

## 禁止修改

- 各服务业务代码。
- `packages/shared-schemas/**` schema 主定义。

## 参考文档

- `docs/工程约束与提交规范.md`
- `docs/看山小苗圃-服务拆分与开发协作.md`

## 验收标准

- 工具函数不依赖任何具体服务。
- 单元测试覆盖 hash、时间、错误结构。
- 不出现业务关键词如 seed、sprout、writing session 的具体逻辑。
