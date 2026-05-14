# 看山小苗圃 · 本地 Dev 调试

更新时间：2026-05-14

本文用于本地直接运行 9 个 Python 服务和前端 dev server，同时使用 Docker Compose 只启动 Postgres / Redis 依赖。

## 1. 前置条件

本地需要：

```text
Python 3.10+
Node.js 20+
Docker
```

不需要本机安装独立 PostgreSQL，也不需要本机安装 `psql`。`scripts/dev_up.sh` 会使用 `kanshan-postgres` 容器内的 `psql` 同步表结构。

## 2. 本地 dev 架构

```text
frontend dev server      127.0.0.1:3000   本机 Node
api-gateway              127.0.0.1:8000   本机 uvicorn
profile-service          127.0.0.1:8010   本机 uvicorn
content-service          127.0.0.1:8020   本机 uvicorn
seed-service             127.0.0.1:8030   本机 uvicorn
sprout-service           127.0.0.1:8040   本机 uvicorn
writing-service          127.0.0.1:8050   本机 uvicorn
feedback-service         127.0.0.1:8060   本机 uvicorn
zhihu-adapter            127.0.0.1:8070   本机 uvicorn
llm-service              127.0.0.1:8080   本机 uvicorn
Postgres                 127.0.0.1:5432   Docker container
Redis                    127.0.0.1:6379   Docker container
```

## 3. 同步完整表结构

`scripts/dev_up.sh` 会自动执行：

```bash
bash scripts/sync_db_schema.sh --docker
```

如果只想手动同步表结构：

```bash
cd /Users/liupeize/Documents/kanshan
cd infra && docker compose up -d postgres redis && cd ..
bash scripts/sync_db_schema.sh --docker
```

这个脚本会执行：

```text
infra/postgres/sync_schema.sql
```

它是幂等的，可以重复运行，用于修复旧表缺字段、缺 schema、缺索引的问题。

## 4. 配置服务

复制配置：

```bash
cp services/config.example.yaml services/config.yaml
cp frontend/.env.example frontend/.env.local
```

修改 `services/config.yaml`：

```yaml
provider_mode: mock
storage_backend: postgres
database_url: "postgresql+psycopg://kanshan:kanshan_dev_password@127.0.0.1:5432/kanshan"

cache:
  backend: redis
  redis_url: "redis://127.0.0.1:6379/0"
```

如果要接真实知乎 API，再把 `provider_mode` 改为 `live`，并填写知乎凭证。

修改 `frontend/.env.local`：

```bash
NEXT_PUBLIC_KANSHAN_BACKEND_MODE=gateway
NEXT_PUBLIC_KANSHAN_GATEWAY_URL=http://127.0.0.1:8000
NEXT_PUBLIC_ZHIHU_ADAPTER_URL=http://127.0.0.1:8070
NEXT_PUBLIC_ZHIHU_OAUTH_AUTO_START=0
```

`scripts/dev_up.sh` 会强制把本机服务使用的 `DATABASE_URL` 改为 `127.0.0.1`，避免误用 Docker 内网主机名 `postgres`。

## 5. 安装依赖

建议使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -e packages/shared-python
for s in services/*/; do pip install -r "$s/requirements.txt"; done

cd frontend
npm install
cd ..
```

## 6. 启动本地 dev

在虚拟环境激活状态下：

```bash
cd /Users/liupeize/Documents/kanshan
bash scripts/dev_up.sh
```

脚本会按顺序执行：

```text
1. 启动 Docker 里的 postgres / redis
2. 用 docker exec 进入 kanshan-postgres 执行 infra/postgres/sync_schema.sql
3. 在本机启动 9 个 Python 服务
4. 在本机启动前端 dev server
```

访问：

```text
http://127.0.0.1:3000
```

服务健康检查：

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s http://127.0.0.1:8040/health
curl -s http://127.0.0.1:8080/health
```

日志位置：

```text
output/service-logs/*.log
output/logs/*.jsonl
```

## 7. 常见问题

如果看到：

```text
could not translate host name "postgres"
```

说明你用了 Docker 环境的连接串。本地非 Docker 要改为：

```text
127.0.0.1
```

如果看到：

```text
column xxx does not exist
```

先执行：

```bash
bash scripts/sync_db_schema.sh --docker
```

如果看到端口冲突，例如本机已有 PostgreSQL 占用 `5432`，可以在 `infra/.env` 中改：

```bash
POSTGRES_PORT=15432
```

然后重新执行 `bash scripts/dev_up.sh`。脚本会用 `127.0.0.1:${POSTGRES_PORT}` 作为本机服务连接地址。
