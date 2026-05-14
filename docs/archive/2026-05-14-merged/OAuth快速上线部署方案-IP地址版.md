# OAuth 快速上线部署方案（同源环境 - IP 地址版）

最后更新：2026-05-14

---

## 📋 场景说明

- ✅ 使用服务器 IP 地址（非域名）
- ✅ 已有知乎 OAuth 凭证
- ✅ 使用 live 模式（真实知乎 API）
- ✅ 同源环境（前端和后端在同一服务器）

**预计耗时**：10-15 分钟

---

## 🎯 部署流程概览

```
1. 知乎开放平台配置（5 分钟）
   ↓
2. 服务器环境配置（3 分钟）
   ↓
3. 防火墙/反向代理配置（2 分钟）
   ↓
4. 启动服务（1 分钟）
   ↓
5. 验证 OAuth 流程（2 分钟）
```

---

## 📝 Step 1: 知乎开放平台配置（5 分钟）

### 1.1 登录知乎开放平台

访问 https://open.zhihu.com/ ，找到你的应用。

### 1.2 配置回调地址

**⚠️ 关键：必须与代码配置完全一致**

```
http://<YOUR_SERVER_IP>:3000/auth/zhihu/callback
```

**注意事项**：
- 使用 **HTTP**（IP 地址无法申请正式 SSL 证书）
- 端口必须是 **3000**（前端服务端口）
- 路径必须是 `/auth/zhihu/callback`
- **不要**使用 `https://`（除非你配置了自签名证书）

### 1.3 确认证证

- `app_id` ✅ 已有
- `app_key` ✅ 已有

### 1.4 检查应用权限

确保已申请以下权限：
- `user_info`（获取用户基本信息）
- 其他你需要的权限

---

## 🔧 Step 2: 服务器环境配置（3 分钟）

### 2.1 SSH 登录服务器

```bash
ssh user@<YOUR_SERVER_IP>
cd /opt/kanshan
```

### 2.2 配置环境变量

```bash
cd infra
cp .env.example .env  # 如果没有，手动创建
vi .env
```

**修改以下配置**：

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 前端访问后端的地址（浏览器端使用）
# IP 地址版本：直接使用 IP + 端口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KANSHAN_GATEWAY_URL=http://<YOUR_SERVER_IP>:8000
KANSHAN_ZHIHU_URL=http://<YOUR_SERVER_IP>:8070

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据库密码（必须改成强密码）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSTGRES_PASSWORD=<YOUR_STRONG_PASSWORD>
DATABASE_URL=postgresql+psycopg://kanshan:<YOUR_STRONG_PASSWORD>@postgres:5432/kanshan

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 存储后端（生产环境用 postgres）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STORAGE_BACKEND=postgres

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Provider 模式（你选择 live 模式）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROVIDER_MODE=live
```

### 2.3 配置知乎凭证

```bash
cd /opt/kanshan
cp services/config.example.yaml services/config.yaml
vi services/config.yaml
```

**修改关键配置**：

```yaml
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 全局配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
provider_mode: live
storage_backend: postgres
database_url: "postgresql+psycopg://kanshan:<YOUR_STRONG_PASSWORD>@postgres:5432/kanshan"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CORS 白名单（IP 地址版本）
# 允许前端访问后端的来源地址
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cors_origins:
  - "http://<YOUR_SERVER_IP>:3000"
  - "http://<YOUR_SERVER_IP>"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 知乎 OAuth 配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
zhihu:
  oauth:
    app_id: "<YOUR_APP_ID>"
    app_key: "<YOUR_APP_KEY>"
    # ⚠️ 关键：回调地址必须与知乎开放平台配置完全一致
    # 使用 IP 地址时，必须用 HTTP（无法使用 HTTPS）
    redirect_uri: "http://<YOUR_SERVER_IP>:3000/auth/zhihu/callback"
    base_url: "https://openapi.zhihu.com"
    access_token: ""
    access_token_expires_at: 0

  # 如果你有其他知乎凭证，也在这里配置
  # community:
  #   app_key: "..."
  #   app_secret: "..."
  #   base_url: "https://openapi.zhihu.com"
  #   writable_ring_ids:
  #     - "..."
  #   default_ring_id: "..."
  # data_platform:
  #   access_secret: "..."
  #   base_url: "https://developer.zhihu.com"
  #   default_model: "zhida-thinking-1p5"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 缓存配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cache:
  backend: redis
  redis_url: "redis://redis:6379/0"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 日志配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
logging:
  jsonl_dir: /app/output/logs
  console_level: INFO
```

---

## 🛡️ Step 3: 防火墙/反向代理配置（2 分钟）

### 方案 A: 直接暴露端口（简单直接）

```bash
# 开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 3000/tcp  # 前端
sudo ufw allow 8000/tcp  # API Gateway
sudo ufw allow 8070/tcp  # 知乎适配器（可选，用于 OAuth 回调）
sudo ufw enable
```

**访问方式**：
- 前端：`http://<YOUR_SERVER_IP>:3000`
- API：`http://<YOUR_SERVER_IP>:8000`

### 方案 B: Nginx 反向代理（推荐，简化访问）

如果你希望通过 80 端口访问，配置 Nginx：

```bash
sudo apt install -y nginx
sudo vi /etc/nginx/sites-available/kanshan
```

**配置内容**：

```nginx
server {
    listen 80;
    server_name <YOUR_SERVER_IP>;

    # API 请求转发到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # 其他请求（包括 OAuth 回调）转发到前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**启用配置**：

```bash
sudo ln -s /etc/nginx/sites-available/kanshan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**如果使用 Nginx**，需要调整配置：
- `KANSHAN_GATEWAY_URL=http://<YOUR_SERVER_IP>/api`（不带端口）
- `redirect_uri=http://<YOUR_SERVER_IP>/auth/zhihu/callback`（不带端口）
- 知乎开放平台回调地址也相应调整

---

## 🚀 Step 4: 启动服务（1 分钟）

### 4.1 构建并启动所有服务

```bash
cd /opt/kanshan
bash scripts/deploy.sh --build
```

### 4.2 检查服务状态

```bash
# 查看容器状态
docker compose -f infra/docker-compose.yml ps

# 预期输出：所有容器状态为 healthy
# kanshan-postgres      ...   Up (healthy)
# kanshan-redis         ...   Up (healthy)
# kanshan-api-gateway   ...   Up (healthy)
# kanshan-frontend      ...   Up (healthy)
# ...
```

### 4.3 健康检查

```bash
# 检查 API Gateway
curl -s http://localhost:8000/health | python3 -m json.tool

# 检查前端
curl -s http://localhost:3000
```

### 4.4 查看日志（如果有问题）

```bash
# 查看所有服务日志
docker compose -f infra/docker-compose.yml logs -f

# 查看特定服务日志
docker compose -f infra/docker-compose.yml logs -f zhihu-adapter
docker compose -f infra/docker-compose.yml logs -f profile-service
```

---

## ✅ Step 5: 验证 OAuth 流程（2 分钟）

### 5.1 访问首页

浏览器访问：
```
http://<YOUR_SERVER_IP>:3000
```

### 5.2 测试 OAuth 登录

1. **点击登录按钮**：选择"知乎登录"或"使用知乎账号登录"
2. **跳转到知乎授权页面**：
   - 应该看到知乎的授权页面
   - 显示你的应用名称和请求的权限
3. **点击授权**：同意授权
4. **自动跳回**：
   - 应该跳回 `http://<YOUR_SERVER_IP>:3000/oauth/zhihu/success`
   - 显示"授权成功，正在通知主页面..."
5. **完成登录**：主页面显示已登录状态

### 5.3 验证要点

✅ **成功标志**：
- 浏览器地址栏显示 `http://<YOUR_SERVER_IP>:3000/oauth/zhihu/success?ticket=...`
- 页面显示"授权成功"
- 主页面显示用户头像/昵称
- 控制台无错误日志

❌ **失败排查**：
- 如果跳转到知乎后报错：检查 `redirect_uri` 是否与知乎开放平台一致
- 如果回调后显示错误：查看浏览器控制台和后端日志
- 如果无法跳转：检查网络连接和防火墙配置

---

## 🔍 故障排查

### 问题 1: OAuth 回调失败（404）

**症状**：点击授权后，跳回时显示 404

**原因**：反向代理未正确配置 `/auth/*` 路径

**解决**：
- 确保 Nginx 将 `/auth/*` 转发到前端（3000 端口）
- 或者直接使用 3000 端口访问

### 问题 2: "redirect_uri 不匹配"

**症状**：知乎授权页面显示"redirect_uri 不匹配"

**原因**：知乎开放平台配置与代码不一致

**解决**：
1. 检查知乎开放平台的回调地址
2. 检查 `services/config.yaml` 中的 `redirect_uri`
3. **两者必须完全一致**（包括 `http://` 和端口号）

### 问题 3: 跨域错误（CORS）

**症状**：浏览器控制台显示 CORS 错误

**原因**：`cors_origins` 配置不正确

**解决**：
确保 `services/config.yaml` 中包含：
```yaml
cors_origins:
  - "http://<YOUR_SERVER_IP>:3000"
  - "http://<YOUR_SERVER_IP>"
```

### 问题 4: 前端无法访问后端

**症状**：前端显示"网络错误"或无法加载数据

**原因**：`KANSHAN_GATEWAY_URL` 配置错误

**解决**：
- 检查 `infra/.env` 中的 `KANSHAN_GATEWAY_URL`
- 确保使用 `http://<YOUR_SERVER_IP>:8000`（不是 Docker 内部地址）
- 确保防火墙开放 8000 端口

### 问题 5: 容器启动失败

**症状**：`docker compose ps` 显示容器退出

**原因**：配置错误或依赖问题

**解决**：
```bash
# 查看详细日志
docker compose -f infra/docker-compose.yml logs

# 常见问题：
# 1. 数据库密码错误
# 2. 端口冲突
# 3. 内存不足
```

---

## 📋 配置文件速查表

| 文件 | 配置项 | 值 | 说明 |
|------|--------|-----|------|
| `infra/.env` | `KANSHAN_GATEWAY_URL` | `http://<IP>:8000` | 浏览器访问 API 的地址 |
| `infra/.env` | `KANSHAN_ZHIHU_URL` | `http://<IP>:8070` | 浏览器访问知乎适配器的地址 |
| `infra/.env` | `PROVIDER_MODE` | `live` | 使用真实知乎 API |
| `services/config.yaml` | `zhihu.oauth.redirect_uri` | `http://<IP>:3000/auth/zhihu/callback` | OAuth 回调地址 |
| `services/config.yaml` | `cors_origins` | `["http://<IP>:3000"]` | CORS 白名单 |
| 知乎开放平台 | 回调地址 | `http://<IP>:3000/auth/zhihu/callback` | 必须与代码一致 |

---

## ✅ 上线检查清单

- [ ] 知乎开放平台配置回调地址（与代码完全一致）
- [ ] `infra/.env` 配置正确（`KANSHAN_GATEWAY_URL`、`PROVIDER_MODE`）
- [ ] `services/config.yaml` 配置正确（`redirect_uri`、`cors_origins`）
- [ ] 防火墙开放端口（3000、8000）
- [ ] 所有容器健康运行（`docker compose ps`）
- [ ] OAuth 流程测试通过（完整走一遍授权流程）
- [ ] 后端日志无错误（`docker compose logs`）

---

## 🎯 快速验证命令

```bash
# 1. 检查服务状态
docker compose -f infra/docker-compose.yml ps

# 2. 检查健康接口
curl -s http://localhost:8000/health | python3 -m json.tool

# 3. 检查前端
curl -s http://localhost:3000 | head -20

# 4. 查看日志
docker compose -f infra/docker-compose.yml logs -f zhihu-adapter
```

---

## 💡 优化建议

### 安全性

1. **使用强密码**：数据库密码、知乎凭证等
2. **限制 CORS 白名单**：只允许可信来源
3. **定期轮换凭证**：知乎 app_key 等

### 性能

1. **启用 Redis 缓存**：减少数据库压力
2. **配置日志轮转**：避免磁盘占满
3. **监控资源使用**：CPU、内存、磁盘

### 可维护性

1. **使用版本控制**：配置文件也纳入 Git
2. **文档记录**：记录所有配置变更
3. **备份策略**：定期备份数据库

---

## 🆘 紧急回滚

如果 OAuth 功能有问题，可以临时禁用：

### 方案 1: 切换到 mock 模式

```bash
vi /opt/kanshan/services/config.yaml
# 修改 provider_mode: mock

# 重启服务
docker compose -f infra/docker-compose.yml restart
```

### 方案 2: 隐藏前端 OAuth 入口

临时注释掉前端的知乎登录按钮（需要修改前端代码）。

### 方案 3: 回滚代码

```bash
cd /opt/kanshan
git log --oneline  # 找到上一个稳定版本
git checkout <commit-hash>
bash scripts/deploy.sh --build
```

---

## 📚 相关文档

- [部署指南.md](./部署指南.md) - 完整部署文档（包含域名版本）
- [看山小苗圃-OAuth画像生成实现记录.md](./看山小苗圃-OAuth画像生成实现记录.md) - OAuth 技术细节
- [看山小苗圃-接口功能与数据流文档.md](./看山小苗圃-接口功能与数据流文档.md) - 接口说明

---

## 🔧 本地调试兼容说明（Cloudflare Tunnel）

**当前状态**：本地使用 Cloudflare Tunnel 穿透，代码中有硬编码的 trycloudflare.com 域名。

**策略**：本地保留这些配置，线上部署时删除。

### 📍 需要修改的文件（共 3 个）

#### 1. `frontend/next.config.ts` (第 13-14 行)

**当前代码**：
```typescript
allowedDevOrigins: [
  "127.0.0.1",
  "localhost",
  "curve-bytes-weed-delivering.trycloudflare.com",  // ❌ 删除
  "leading-compare-yields-grove.trycloudflare.com", // ❌ 删除
],
```

**线上部署时改为**：
```typescript
allowedDevOrigins: [
  "127.0.0.1",
  "localhost",
],
```

#### 2. `frontend/components/auth/AuthEntry.tsx` (第 25-33 行)

**当前代码**：
```typescript
function isTrustedOauthMessageOrigin(origin: string): boolean {
  if (typeof window === "undefined") return false;
  if (origin === window.location.origin) return true;
  try {
    return new URL(origin).hostname.endsWith(".trycloudflare.com");  // ❌ 删除
  } catch {
    return false;
  }
}
```

**线上部署时改为**：
```typescript
function isTrustedOauthMessageOrigin(origin: string): boolean {
  if (typeof window === "undefined") return false;
  return origin === window.location.origin;
}
```

#### 3. `frontend/lib/auth/auth-client.ts` (第 66-75 行)

**当前代码**：
```typescript
function shouldUseSameOriginGateway(): boolean {
  if (typeof window === "undefined") return false;
  if (!window.location.hostname.endsWith(".trycloudflare.com")) return false;  // ❌ 删除
  try {
    const gateway = new URL(GATEWAY_URL);
    return gateway.hostname === "127.0.0.1" || gateway.hostname === "localhost";
  } catch {
    return false;
  }
}
```

**线上部署时改为**：
```typescript
function shouldUseSameOriginGateway(): boolean {
  return false;
}
```

### 🚀 上线部署操作步骤

**Step 1: SSH 登录服务器，拉取代码**
```bash
cd /opt/kanshan
git pull origin main
```

**Step 2: 修改前端代码（删除 Cloudflare 配置）**
```bash
# 使用 sed 命令快速删除（推荐）
cd /opt/kanshan/frontend

# 删除 next.config.ts 中的 trycloudflare 行
sed -i '/trycloudflare\.com/d' next.config.ts

# 或者手动编辑
vi next.config.ts
# 删除第 13-14 行

vi components/auth/AuthEntry.tsx
# 修改 isTrustedOauthMessageOrigin 函数（见上方）

vi lib/auth/auth-client.ts
# 修改 shouldUseSameOriginGateway 函数（见上方）
```

**Step 3: 重新构建前端**
```bash
cd /opt/kanshan/frontend
npm run build
```

**Step 4: 重新部署**
```bash
cd /opt/kanshan
bash scripts/deploy.sh --build
```

### 📋 上线检查清单（补充）

- [ ] 删除 `next.config.ts` 中的 trycloudflare.com 行
- [ ] 修改 `AuthEntry.tsx` 中的 `isTrustedOauthMessageOrigin` 函数
- [ ] 修改 `auth-client.ts` 中的 `shouldUseSameOriginGateway` 函数
- [ ] 重新构建前端（`npm run build`）
- [ ] 重新部署所有服务
- [ ] 测试 OAuth 流程

### 💡 优化建议：使用环境变量区分

**更好的方案**：使用环境变量区分线上/线下环境，避免手动修改代码。

#### 方案 1: 使用 `.env.production`

创建 `frontend/.env.production`：
```bash
NEXT_PUBLIC_IS_PRODUCTION=true
```

然后在代码中检查：
```typescript
// next.config.ts
const isProduction = process.env.NEXT_PUBLIC_IS_PRODUCTION === 'true';

allowedDevOrigins: isProduction
  ? ["127.0.0.1", "localhost"]
  : [
      "127.0.0.1",
      "localhost",
      "curve-bytes-weed-delivering.trycloudflare.com",
      "leading-compare-yields-grove.trycloudflare.com",
    ],
```

#### 方案 2: 使用 Git 分支

```bash
# 本地开发分支（保留 Cloudflare 配置）
git checkout -b dev/cloudflare-tunnel

# 线上部署分支（删除 Cloudflare 配置）
git checkout -b production
# 删除相关代码
git commit -m "remove: Cloudflare Tunnel configuration for production"
```

#### 方案 3: 使用部署脚本

创建 `scripts/deploy-production.sh`：
```bash
#!/bin/bash
# 部署前自动清理 Cloudflare 配置

cd /opt/kanshan/frontend

# 删除 trycloudflare 行
sed -i '/trycloudflare\.com/d' next.config.ts

# 修改 AuthEntry.tsx
sed -i 's/return new URL(origin).hostname.endsWith(".trycloudflare.com");/return false;/' components/auth/AuthEntry.tsx

# 修改 auth-client.ts
sed -i 's/if (!window.location.hostname.endsWith(".trycloudflare.com")) return false;/return false;/' lib/auth/auth-client.ts

# 重新构建
npm run build

# 部署
cd /opt/kanshan
bash scripts/deploy.sh --build
```

### ⚠️ 注意事项

1. **不要提交线上代码到 main 分支**
   - 本地保留 Cloudflare 配置
   - 线上使用部署脚本或手动修改

2. **备份修改**
   - 上线前备份修改后的文件
   - 方便回滚

3. **测试验证**
   - 修改后重新测试 OAuth 流程
   - 确保没有引入新问题

4. **文档记录**
   - 记录所有修改
   - 方便团队协作

---

## 📞 技术支持

如果遇到问题：

1. **查看日志**：`docker compose -f infra/docker-compose.yml logs -f`
2. **检查配置**：对比文档中的示例配置
3. **健康检查**：`curl -s http://localhost:8000/health`
4. **重启服务**：`docker compose -f infra/docker-compose.yml restart`

---

**最后更新**：2026-05-14
**适用场景**：同源环境 + IP 地址 + live 模式
**预计耗时**：10-15 分钟（含 Cloudflare 配置清理）

---

## 🎯 快速参考：Cloudflare 配置清理

### 本地环境（保留）
✅ 保留 Cloudflare Tunnel 配置
✅ 保留 trycloudflare.com 域名
✅ 方便本地调试

### 线上环境（删除）
❌ 删除 `next.config.ts` 中的 trycloudflare.com
❌ 删除 `AuthEntry.tsx` 中的 Cloudflare 检测
❌ 删除 `auth-client.ts` 中的 Cloudflare 网关逻辑

### 一键清理命令（线上执行）
```bash
cd /opt/kanshan/frontend

# 删除 trycloudflare 行
sed -i '/trycloudflare\.com/d' next.config.ts

# 修改 AuthEntry.tsx（简化信任验证）
sed -i 's/return new URL(origin).hostname.endsWith(".trycloudflare.com");/return false;/' components/auth/AuthEntry.tsx

# 修改 auth-client.ts（禁用 Cloudflare 网关检测）
sed -i 's/if (!window.location.hostname.endsWith(".trycloudflare.com")) return false;/return false;/' lib/auth/auth-client.ts

# 重新构建
npm run build

# 部署
cd /opt/kanshan
bash scripts/deploy.sh --build
```

### 修改前后对比

#### 1. next.config.ts
```diff
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
-   "curve-bytes-weed-delivering.trycloudflare.com",
-   "leading-compare-yields-grove.trycloudflare.com",
  ],
```

#### 2. AuthEntry.tsx
```diff
  function isTrustedOauthMessageOrigin(origin: string): boolean {
    if (typeof window === "undefined") return false;
-   if (origin === window.location.origin) return true;
-   try {
-     return new URL(origin).hostname.endsWith(".trycloudflare.com");
-   } catch {
-     return false;
-   }
+   return origin === window.location.origin;
  }
```

#### 3. auth-client.ts
```diff
  function shouldUseSameOriginGateway(): boolean {
-   if (typeof window === "undefined") return false;
-   if (!window.location.hostname.endsWith(".trycloudflare.com")) return false;
-   try {
-     const gateway = new URL(GATEWAY_URL);
-     return gateway.hostname === "127.0.0.1" || gateway.hostname === "localhost";
-   } catch {
-     return false;
-   }
+   return false;
  }
```

---

## 📞 紧急联系

如果遇到问题：
1. 查看文档：[部署指南.md](./部署指南.md)
2. 查看日志：`docker compose -f infra/docker-compose.yml logs -f`
3. 健康检查：`curl -s http://localhost:8000/health`
4. 重启服务：`docker compose -f infra/docker-compose.yml restart`
