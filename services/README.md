# Services

后端服务目录。

P0 服务：

- `api-gateway`
- `profile-service`
- `content-service`
- `zhihu-adapter`
- `seed-service`
- `sprout-service`
- `writing-service`
- `feedback-service`
- `llm-service`

每个服务必须具备：

- `README.md`
- `/health`
- mock 模式
- OpenAPI
- 单元测试样例

Memory 维护在 `profile-service/app/memory`，后续复杂后再拆独立服务。
