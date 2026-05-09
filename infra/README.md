# Infra

P0 阶段只提供数据库和 Redis 骨架。

启动基础依赖：

```bash
cd infra
cp .env.example .env
docker compose --env-file .env up -d
```

后续服务容器稳定后，再把 `frontend`、`api-gateway` 和各业务服务加入 compose。
