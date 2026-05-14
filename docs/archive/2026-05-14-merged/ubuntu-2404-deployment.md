# 看山小苗圃 · Ubuntu 24.04 部署指南

最后更新：2026-05-12

本文档提供在 Ubuntu 24.04 LTS 上部署看山小苗圃的完整指南，包含从系统初始化到生产环境配置的所有步骤。

---

## 目录

1. [服务器要求](#1-服务器要求)
2. [系统初始化](#2-系统初始化)
3. [代码部署](#3-代码部署)
4. [环境配置](#4-环境配置)
5. [Docker Compose 部署](#5-docker-compose-部署)
6. [反向代理配置](#6-反向代理配置)
7. [SSL/HTTPS 配置](#7-sslhttps-配置)
8. [数据备份与恢复](#8-数据备份与恢复)
9. [运维命令速查](#9-运维命令速查)
10. [故障排查](#10-故障排查)
11. [安全加固](#11-安全加固)

---

## 1. 服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 系统 | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 40 GB SSD | 80 GB SSD |
| 网络 | 公网 IP | 公网 IP + 域名 |
| Docker | 24+ | 最新稳定版 |
| Docker Compose | v2+ | 最新稳定版 |

**端口要求：**
- 22: SSH
- 80: HTTP（用于 HTTPS 重定向）
- 443: HTTPS
- 3000: 前端（可选，可通过反向代理隐藏）
- 8000: API Gateway（可选，可通过反向代理隐藏）

---

## 2. 系统初始化

### 2.1 系统更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git vim htop unzip
```

### 2.2 安装 Docker

```bash
# 安装 Docker（官方脚本）
curl -fsSL https://get.docker.com | sudo sh

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录使 docker 组生效
# 或者运行：newgrp docker

# 验证 Docker 安装
docker --version
docker compose version
```

### 2.3 配置 Docker 镜像加速（中国大陆）

```bash
# 创建 Docker 配置目录
sudo mkdir -p /etc/docker

# 配置镜像加速器
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://hub-mirror.c.163.com",
    "https://mirror.aliyuncs.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

# 重启 Docker 服务
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 2.4 配置防火墙

```bash
# 启用 UFW 防火墙
sudo ufw enable

# 允许 SSH
sudo ufw allow 22/tcp

# 允许 HTTP 和 HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果需要直接访问前端和 API（可选）
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp

# 查看防火墙状态
sudo ufw status verbose
```

### 2.5 创建部署用户（推荐）

```bash
# 创建专用部署用户
sudo useradd -m -s /bin/bash kanshan
sudo usermod -aG docker kanshan

# 切换到部署用户
su - kanshan
```

---

## 3. 代码部署

### 3.1 拉取代码

```bash
# 创建项目目录
sudo mkdir -p /opt/kanshan
sudo chown $USER:$USER /opt/kanshan

# 克隆代码
cd /opt/kanshan
git clone https://github.com/Nai1ve/kan_shan_nursery.git .

# 或者从已有目录复制
# rsync -avz /path/to/local/kanshan/ /opt/kanshan/
```

### 3.2 目录结构

```
/opt/kanshan/
├── frontend/          # 前端代码
├── services/          # 后端服务
│   ├── api-gateway/
│   ├── content-service/
│   ├── feedback-service/
│   ├── llm-service/
│   ├── profile-service/
│   ├── seed-service/
│   ├── sprout-service/
│   ├── writing-service/
│   └── zhihu-adapter/
├── packages/          # 共享包
├── infra/             # 基础设施配置
│   ├── docker-compose.yml
│   ├── .env           # 环境变量（需要配置）
│   └── postgres/      # 数据库初始化脚本
├── scripts/           # 部署脚本
└── docs/              # 文档
```

---

## 4. 环境配置

### 4.1 创建环境变量文件

```bash
cd /opt/kanshan/infra

# 从模板创建 .env 文件
cp .env.deploy .env

# 编辑配置
vi .env
```

### 4.2 必填配置项

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 前端访问后端的地址（浏览器端使用，必须公网可达）
# 填你的服务器公网 IP 或域名
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KANSHAN_GATEWAY_URL=http://<你的服务器公网IP>:8000
KANSHAN_ZHIHU_URL=http://<你的服务器公网IP>:8070

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据库密码（必须改成强密码）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSTGRES_PASSWORD=<你的强密码>
DATABASE_URL=postgresql+psycopg://kanshan:<你的强密码>@postgres:5432/kanshan

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 存储后端（生产环境用 postgres）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STORAGE_BACKEND=postgres

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Provider 模式
# - mock: 使用模拟数据，不需要知乎凭证（测试用）
# - live: 使用真实知乎 API（需要知乎凭证）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROVIDER_MODE=mock
```

### 4.3 知乎凭证配置（live 模式必填）

如果使用 live 模式，需要配置知乎 API 凭证：

```bash
# 创建配置文件
cd /opt/kanshan
cp services/config.example.yaml services/config.yaml

# 编辑配置
vi services/config.yaml
```

填写以下内容：

```yaml
provider_mode: live
storage_backend: postgres
database_url: "postgresql+psycopg://kanshan:<你的密码>@postgres:5432/kanshan"

zhihu:
  community:
    # 来源：知乎个人主页 → "..." → 复制链接，取 people/ 后那串
    app_key: "<知乎 user-token>"
    # 来源：知乎开放平台申请
    app_secret: "<app-secret>"
    base_url: "https://openapi.zhihu.com"
    writable_ring_ids:
      - "<你的圈子 ID>"
    default_ring_id: "<你的默认圈子 ID>"

  oauth:
    # 来源：知乎开放平台 → 应用管理
    app_id: "<app_id>"
    app_key: "<app_key>"
    # 回调地址必须与知乎开放平台配置一致
    redirect_uri: "http://<你的服务器IP>:8070/zhihu/oauth/callback"
    base_url: "https://openapi.zhihu.com"

  data_platform:
    # 来源：https://developer.zhihu.com/ 个人中心
    access_secret: "<access_secret>"
    base_url: "https://developer.zhihu.com"
    default_model: "zhida-thinking-1p5"

  quota:
    hot_list: 100
    zhihu_search: 1000
    global_search: 1000
    direct_answer: 100

cache:
  backend: redis
  redis_url: "redis://redis:6379/0"

logging:
  jsonl_dir: /app/output/logs
  console_level: INFO
```

---

## 5. Docker Compose 部署

### 5.1 构建并启动服务

```bash
cd /opt/kanshan

# 构建所有镜像
docker compose -f infra/docker-compose.yml build

# 启动所有服务
docker compose -f infra/docker-compose.yml up -d

# 查看容器状态
docker compose -f infra/docker-compose.yml ps
```

### 5.2 等待服务就绪

```bash
# 等待所有服务健康检查通过（约 1-2 分钟）
echo "等待服务启动..."
sleep 30

# 检查服务健康状态
docker compose -f infra/docker-compose.yml ps

# 测试 API Gateway
curl -s http://localhost:8000/health | python3 -m json.tool
```

### 5.3 查看日志

```bash
# 查看所有服务日志
docker compose -f infra/docker-compose.yml logs -f

# 查看特定服务日志
docker compose -f infra/docker-compose.yml logs -f api-gateway
docker compose -f infra/docker-compose.yml logs -f profile-service
```

---

## 6. 反向代理配置

### 6.1 选项 A: Caddy（推荐）

Caddy 自动处理 HTTPS 证书，配置简单。

```bash
# 安装 Caddy
sudo apt install -y caddy

# 停止默认服务
sudo systemctl stop caddy
```

创建配置文件 `/etc/caddy/Caddyfile`：

```
你的域名.com {
    # API 请求
    handle /api/* {
        reverse_proxy localhost:8000
    }

    # 健康检查
    handle /health {
        reverse_proxy localhost:8000
    }

    # 前端
    handle {
        reverse_proxy localhost:3000
    }

    # 安全头
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # 启用压缩
    encode gzip

    # 请求体大小限制
    request_body {
        max_size 10MB
    }

    # 日志
    log {
        output file /var/log/caddy/access.log {
            roll_size 100mb
            roll_keep 10
        }
    }
}
```

启动 Caddy：

```bash
# 验证配置
sudo caddy validate --config /etc/caddy/Caddyfile

# 启动服务
sudo systemctl enable caddy
sudo systemctl start caddy

# 查看状态
sudo systemctl status caddy
```

### 6.2 选项 B: Nginx

```bash
# 安装 Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# 停止默认服务
sudo systemctl stop nginx
```

创建配置文件 `/etc/nginx/sites-available/kanshan`：

```nginx
server {
    listen 80;
    server_name 你的域名.com;

    # Let's Encrypt 验证
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # 重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name 你的域名.com;

    # SSL 证书（稍后配置）
    ssl_certificate     /etc/letsencrypt/live/你的域名.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/你的域名.com/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 启用压缩
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1000;

    # 请求体大小限制
    client_max_body_size 10m;

    # API 请求
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://127.0.0.1:3000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

启用配置：

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/kanshan /etc/nginx/sites-enabled/

# 删除默认配置
sudo rm -f /etc/nginx/sites-enabled/default

# 验证配置
sudo nginx -t

# 启动服务
sudo systemctl enable nginx
sudo systemctl start nginx
```

---

## 7. SSL/HTTPS 配置

### 7.1 使用 Let's Encrypt（免费）

**Caddy 自动配置：**
Caddy 会自动申请和续期证书，无需手动配置。

**Nginx 手动配置：**

```bash
# 申请证书
sudo certbot --nginx -d 你的域名.com -d www.你的域名.com

# 测试自动续期
sudo certbot renew --dry-run

# 设置自动续期定时任务
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

### 7.2 使用自签名证书（测试环境）

```bash
# 生成自签名证书
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/kanshan.key \
    -out /etc/ssl/certs/kanshan.crt \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Kanshan/CN=你的域名.com"

# 更新 Nginx 配置使用自签名证书
# ssl_certificate     /etc/ssl/certs/kanshan.crt;
# ssl_certificate_key /etc/ssl/private/kanshan.key;
```

### 7.3 验证 HTTPS

```bash
# 测试 HTTPS 连接
curl -I https://你的域名.com

# 检查证书信息
openssl s_client -connect 你的域名.com:443 -servername 你的域名.com
```

---

## 8. 数据备份与恢复

### 8.1 数据库备份

```bash
# 创建备份目录
mkdir -p /opt/kanshan/backups

# 手动备份
docker exec kanshan-postgres pg_dump -U kanshan kanshan | gzip > /opt/kanshan/backups/backup-$(date +%F).sql.gz

# 查看备份文件
ls -lh /opt/kanshan/backups/
```

### 8.2 自动备份脚本

创建备份脚本 `/opt/kanshan/scripts/backup.sh`：

```bash
#!/bin/bash
# 看山小苗圃自动备份脚本

BACKUP_DIR="/opt/kanshan/backups"
RETENTION_DAYS=7

# 创建备份
docker exec kanshan-postgres pg_dump -U kanshan kanshan | gzip > "$BACKUP_DIR/backup-$(date +%F_%H-%M).sql.gz"

# 删除旧备份
find "$BACKUP_DIR" -name "backup-*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "备份完成: $(date)"
```

设置定时任务：

```bash
# 添加执行权限
chmod +x /opt/kanshan/scripts/backup.sh

# 编辑定时任务
crontab -e

# 添加每天凌晨 3 点备份
0 3 * * * /opt/kanshan/scripts/backup.sh >> /var/log/kanshan-backup.log 2>&1
```

### 8.3 数据恢复

```bash
# 恢复数据库
gunzip < /opt/kanshan/backups/backup-YYYY-MM-DD_HH-MM.sql.gz | docker exec -i kanshan-postgres psql -U kanshan kanshan

# 验证恢复
docker exec kanshan-postgres psql -U kanshan kanshan -c "\dt"
```

### 8.4 Redis 数据备份

```bash
# Redis 自动持久化（RDB + AOF）
# 默认配置已启用，数据保存在 Docker volume 中

# 手动触发 RDB 快照
docker exec kanshan-redis redis-cli BGSAVE

# 备份 Redis 数据
docker cp kanshan-redis:/data/dump.rdb /opt/kanshan/backups/redis-$(date +%F).rdb
```

---

## 9. 运维命令速查

### 9.1 服务管理

```bash
# 查看所有容器状态
docker compose -f infra/docker-compose.yml ps

# 启动所有服务
docker compose -f infra/docker-compose.yml up -d

# 停止所有服务
docker compose -f infra/docker-compose.yml down

# 重启所有服务
docker compose -f infra/docker-compose.yml restart

# 重启单个服务
docker compose -f infra/docker-compose.yml restart api-gateway
docker compose -f infra/docker-compose.yml restart profile-service

# 查看服务日志
docker compose -f infra/docker-compose.yml logs -f
docker compose -f infra/docker-compose.yml logs -f api-gateway
```

### 9.2 更新部署

```bash
cd /opt/kanshan

# 拉取最新代码
git pull

# 重新构建并部署
bash scripts/deploy.sh --build

# 或者手动操作
docker compose -f infra/docker-compose.yml down
docker compose -f infra/docker-compose.yml build
docker compose -f infra/docker-compose.yml up -d
```

### 9.3 健康检查

```bash
# 检查 API Gateway
curl -s http://localhost:8000/health | python3 -m json.tool

# 检查所有服务
for port in 8010 8020 8030 8040 8050 8060 8070 8080; do
    echo "检查端口 $port:"
    curl -s http://localhost:$port/health | python3 -m json.tool
done

# 检查 PostgreSQL
docker exec kanshan-postgres pg_isready -U kanshan

# 检查 Redis
docker exec kanshan-redis redis-cli ping
```

### 9.4 资源监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h
docker system df

# 清理未使用的镜像和容器
docker system prune -f

# 清理所有未使用资源（包括 volume）
docker system prune -a --volumes -f
```

### 9.5 数据库管理

```bash
# 连接数据库
docker exec -it kanshan-postgres psql -U kanshan kanshan

# 查看表
docker exec kanshan-postgres psql -U kanshan kanshan -c "\dt"

# 查看表结构
docker exec kanshan-postgres psql -U kanshan kanshan -c "\d+ table_name"

# 查看数据
docker exec kanshan-postgres psql -U kanshan kanshan -c "SELECT * FROM schema.table LIMIT 10;"
```

---

## 10. 故障排查

### 10.1 常见问题

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 前端报 `ERR_NAME_NOT_RESOLVED` | `KANSHAN_GATEWAY_URL` 配置错误 | 改为公网 IP 或域名 |
| 注册/登录 401 | 用户不存在或密码错误 | 先注册，或检查密码 |
| PostgreSQL 连接失败 | 数据库未启动或密码错误 | 检查 `DATABASE_URL` 和 `POSTGRES_PASSWORD` |
| Redis 连接失败 | Redis 未启动 | `docker compose up -d redis` |
| 知乎 API 报错 | 凭证未配置或过期 | 检查 `services/config.yaml` |
| Docker Hub 拉取超时 | 网络问题 | 配置 Docker 镜像加速 |
| 容器启动失败 | 端口被占用 | 检查端口占用，修改端口映射 |
| 内存不足 | 服务器资源不足 | 增加服务器内存或优化配置 |

### 10.2 日志查看

```bash
# 查看所有服务日志
docker compose -f infra/docker-compose.yml logs -f

# 查看特定服务日志
docker compose -f infra/docker-compose.yml logs -f api-gateway

# 查看系统日志
journalctl -u docker -f

# 查看 Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 查看 Caddy 日志
tail -f /var/log/caddy/access.log
```

### 10.3 调试模式

```bash
# 启用调试日志
# 修改 services/config.yaml
logging:
  console_level: DEBUG

# 重启服务
docker compose -f infra/docker-compose.yml restart

# 查看调试日志
docker compose -f infra/docker-compose.yml logs -f api-gateway
```

### 10.4 性能问题

```bash
# 检查容器资源使用
docker stats

# 检查数据库连接数
docker exec kanshan-postgres psql -U kanshan kanshan -c "SELECT count(*) FROM pg_stat_activity;"

# 检查慢查询
docker exec kanshan-postgres psql -U kanshan kanshan -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# 检查 Redis 内存使用
docker exec kanshan-redis redis-cli info memory
```

---

## 11. 安全加固

### 11.1 系统安全

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装安全工具
sudo apt install -y fail2ban unattended-upgrades

# 配置自动安全更新
sudo dpkg-reconfigure -plow unattended-upgrades

# 配置 fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo vi /etc/fail2ban/jail.local
# 启用 SSH 保护
# [sshd]
# enabled = true
# maxretry = 5
# bantime = 3600

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 11.2 Docker 安全

```bash
# 限制容器资源
# 在 docker-compose.yml 中添加：
# deploy:
#   resources:
#     limits:
#       cpus: '0.50'
#       memory: 512M

# 只读文件系统（可选）
# read_only: true
# tmpfs:
#   - /tmp

# 非 root 用户运行
# user: "1000:1000"
```

### 11.3 网络安全

```bash
# 限制入站流量
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 只允许必要端口
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 限制 SSH 访问（可选）
sudo ufw allow from <你的IP> to any port 22
```

### 11.4 数据安全

```bash
# 加密备份
# 使用 GPG 加密备份文件
gpg --symmetric --cipher-algo AES256 /opt/kanshan/backups/backup-YYYY-MM-DD.sql.gz

# 定期轮换密钥
# 更新数据库密码
# 更新 API 密钥
```

---

## 附录 A: 快速部署脚本

创建一键部署脚本 `/opt/kanshan/scripts/deploy-ubuntu.sh`：

```bash
#!/bin/bash
# 看山小苗圃 Ubuntu 24.04 一键部署脚本

set -e

echo "=== 看山小苗圃部署脚本 ==="

# 检查系统
if [[ $(lsb_release -rs) != "24.04" ]]; then
    echo "警告：此脚本针对 Ubuntu 24.04，其他版本可能不兼容"
fi

# 安装 Docker
echo "安装 Docker..."
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 配置防火墙
echo "配置防火墙..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 部署代码
echo "部署代码..."
sudo mkdir -p /opt/kanshan
sudo chown $USER:$USER /opt/kanshan
cd /opt/kanshan
# git clone https://github.com/Nai1ve/kan_shan_nursery.git .

# 配置环境
echo "配置环境..."
cd /opt/kanshan/infra
cp .env.deploy .env
echo "请编辑 /opt/kanshan/infra/.env 文件配置环境变量"

# 启动服务
echo "启动服务..."
cd /opt/kanshan
docker compose -f infra/docker-compose.yml up -d

echo "=== 部署完成 ==="
echo "请访问 http://$(hostname -I | awk '{print $1}'):3000"
```

---

## 附录 B: 配置文件参考

### B.1 环境变量完整列表

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `KANSHAN_GATEWAY_URL` | 浏览器访问 API 的地址 | - | 是 |
| `KANSHAN_ZHIHU_URL` | 浏览器访问知乎适配器的地址 | - | 是 |
| `POSTGRES_PASSWORD` | 数据库密码 | - | 是 |
| `DATABASE_URL` | 数据库连接串 | - | 是 |
| `STORAGE_BACKEND` | 存储后端 | `postgres` | 是 |
| `PROVIDER_MODE` | 知乎 API 模式 | `mock` | 否 |
| `REDIS_URL` | Redis 连接地址 | `redis://redis:6379/0` | 否 |
| `LLM_PROVIDER_MODE` | LLM 提供商模式 | `mock` | 否 |

### B.2 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| frontend | 3000 | 3000 | 前端 |
| api-gateway | 8000 | 8000 | API 网关 |
| profile-service | 8010 | - | 用户服务 |
| content-service | 8020 | - | 内容服务 |
| seed-service | 8030 | - | 种子服务 |
| sprout-service | 8040 | - | 发芽服务 |
| writing-service | 8050 | - | 写作服务 |
| feedback-service | 8060 | - | 反馈服务 |
| zhihu-adapter | 8070 | - | 知乎适配器 |
| llm-service | 8080 | - | LLM 服务 |
| postgres | 5432 | 5432 | PostgreSQL |
| redis | 6379 | 6379 | Redis |

---

## 附录 C: 常用命令速查卡

```bash
# 服务管理
docker compose -f infra/docker-compose.yml up -d      # 启动
docker compose -f infra/docker-compose.yml down        # 停止
docker compose -f infra/docker-compose.yml restart     # 重启
docker compose -f infra/docker-compose.yml ps          # 状态
docker compose -f infra/docker-compose.yml logs -f     # 日志

# 更新部署
cd /opt/kanshan && git pull && bash scripts/deploy.sh --build

# 数据库备份
docker exec kanshan-postgres pg_dump -U kanshan kanshan | gzip > backup.sql.gz

# 健康检查
curl -s http://localhost:8000/health

# 清理资源
docker system prune -f
```

---

**文档维护者：** 看山小苗圃开发团队
**最后更新：** 2026-05-12
**版本：** 1.0
