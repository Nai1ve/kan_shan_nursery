# Infra

基础设施目录。P0 先提供 Redis 和 PostgreSQL 骨架，服务容器化可以后置。

优先级：P2
难度：S

## 边界

负责：

- Redis。
- PostgreSQL + pgvector。
- 本地 `.env.example`。
- Docker Compose 基础依赖。
- 后续服务容器的网络和端口编排。

不负责：

- 不实现服务业务逻辑。
- 不保存真实 secret。
- 不替服务生成数据库 migration。

## P0 任务

- `docker-compose.yml` 提供 Redis。
- `docker-compose.yml` 提供 PostgreSQL。
- `.env.example` 包含本地默认端口和 mock 开关。
- 文档说明如何清理本地依赖。

## 允许修改

- `infra/**`
- 根目录部署说明文档，若后续需要

## 禁止修改

- 服务业务代码。
- 前端页面。
- `docs/知乎API.md`。

## 参考文档

- `docs/看山小苗圃-服务拆分与开发协作.md`
- `docs/工程约束与提交规范.md`

## 本地启动

```bash
cd infra
cp .env.example .env
docker compose --env-file .env up -d
```

## 验收标准

- Redis 可连接。
- PostgreSQL 可连接。
- 不需要真实知乎 secret 也能启动基础依赖。
- 后续可以把 `frontend`、`api-gateway` 和各业务服务逐步加入 compose。
