# 看山小苗圃 - 上线部署与 OAuth 跑通方案

更新时间：2026-05-14

本文面向正式上线或比赛现场部署，目标是让知乎 OAuth 流程稳定跑通，并兼容当前代码中的前端 ticket 桥接、profile-service 绑定用户、zhihu-adapter 换取 token 的实现方式。

---

## 1. 核心结论

线上最稳方案：

```text
一个公网 HTTPS 域名
→ /                 反向代理到 frontend:3000
→ /api/*            反向代理到 api-gateway:8000
→ 其它后端服务       只在 Docker 内网互通，不直接暴露给浏览器
```

OAuth 回调地址必须使用前端页面：

```text
https://<domain>/auth/zhihu/callback
```

不要把知乎 OAuth redirect URI 配成：

```text
https://<domain>/api/v1/auth/zhihu/callback
https://<domain>/zhihu/oauth/callback
http://127.0.0.1:3000/auth/zhihu/callback
http://127.0.0.1:8070/zhihu/oauth/callback
```

原因：

```text
1. 当前前端 callback 页负责接收知乎回调，并用相对路径请求 /api/v1/auth/zhihu/callback。
2. api-gateway 再代理到 profile-service。
3. profile-service 调 zhihu-adapter 换 token、拉用户信息、写入 zhihu_bindings，并签发短期 login ticket。
4. 前端 success 页把 ticket 通过 postMessage / localStorage 交回主页面。
5. 主页面 exchange-ticket 后保存本地 session，再进入 LLM 配置或工作台。
```

因此，线上必须保证：

```text
前端主页
/auth/zhihu/callback
/oauth/zhihu/success
/api/v1/auth/zhihu/*
```

在浏览器看来都是同一个公网 origin。

---

## 2. 当前 OAuth 实现链路

### 2.1 用户点击授权

前端组件：

```text
frontend/components/auth/ZhihuLinkPanel.tsx
```

动作：

```text
GET /api/v1/auth/zhihu/authorize
→ api-gateway
→ profile-service
→ zhihu-adapter /zhihu/oauth/authorize
→ 返回知乎 authorize URL
→ 前端追加 state(opener_origin, session_id)
→ window.open(authorizeUrl)
```

### 2.2 知乎回调前端

知乎开放平台回调：

```text
https://<domain>/auth/zhihu/callback?authorization_code=xxx&state=xxx
```

前端页面：

```text
frontend/app/auth/zhihu/callback/page.tsx
```

动作：

```text
读取 authorization_code / code
读取 state 中的 opener_origin / session_id
请求相对路径：
GET /api/v1/auth/zhihu/callback?code=xxx&session_id=xxx&state=xxx
```

### 2.3 后端换 token 并绑定用户

后端链路：

```text
api-gateway
→ profile-service /auth/zhihu/callback
→ zhihu-adapter /zhihu/oauth/callback?code=xxx
→ 知乎 /access_token
→ zhihu-adapter /zhihu/user?access_token=xxx
→ profile-service 写入 zhihu_bindings
→ profile-service 创建本地用户或复用已有知乎用户
→ profile-service 生成 login ticket
```

关键依赖：

```text
profile-service 必须能在容器内访问 zhihu-adapter：
ZHIHU_ADAPTER_URL=http://zhihu-adapter:8070
```

### 2.4 前端接收 ticket

后端返回 ticket 后，前端 callback 页面跳转：

```text
/oauth/zhihu/success?ticket=xxx&opener_origin=https%3A%2F%2F<domain>
```

success 页：

```text
frontend/app/oauth/zhihu/success/page.tsx
```

动作：

```text
postMessage(ticket) 给主页面
主页面 AuthEntry 收到 ticket
POST /api/v1/auth/zhihu/exchange-ticket
保存 session 到 localStorage
根据 setupState 进入：
  llm_pending → LLM 配置
  preferences_pending → 兴趣 / 风格配置
  ready / provisional_ready → 工作台
```

---

## 3. 生产拓扑

### 3.1 推荐拓扑

```text
浏览器
  ↓
https://<domain>
  ↓
Caddy / Nginx
  ├─ /api/* → api-gateway:8000
  └─ /*     → frontend:3000

Docker 内网：
api-gateway      → profile-service / content-service / seed-service / ...
profile-service  → zhihu-adapter
content-service  → zhihu-adapter / profile-service / llm-service
llm-service      → zhihu-adapter 或用户配置 provider
zhihu-adapter    → openapi.zhihu.com / developer.zhihu.com
```

### 3.2 不推荐拓扑

```text
前端一个域名，OAuth callback 另一个域名。
前端通过公网直连 zhihu-adapter:8070。
使用随机 trycloudflare 域名作为正式 OAuth redirect URI。
把 redirect_uri 配到 /zhihu/oauth/callback。
把 /auth/zhihu/callback 代理到后端而不是前端。
```

这些都会导致 postMessage/localStorage 不同源、redirect URI 不匹配、或者浏览器访问失败。

---

## 4. 域名与反向代理配置

### 4.1 Caddy 推荐配置

```caddyfile
<domain> {
    encode gzip

    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    handle {
        reverse_proxy 127.0.0.1:3000
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
    }
}
```

验证：

```bash
curl -I https://<domain>/
curl -s https://<domain>/api/v1/auth/zhihu/authorize
```

### 4.2 Nginx 等价规则

关键点只有两个：

```text
/api/ 代理到 127.0.0.1:8000
/     代理到 127.0.0.1:3000
```

不要给 `/auth/zhihu/callback` 单独转发到后端，它必须由 Next.js 前端处理。

---

## 5. 知乎开放平台配置

知乎开放平台中的 redirect URI 必须和运行时配置完全一致：

```text
https://<domain>/auth/zhihu/callback
```

要求：

```text
1. 协议必须一致：http 和 https 不能混用。
2. 域名必须一致，不能用 127.0.0.1、localhost 或旧 Cloudflare 临时域名。
3. path 必须是 /auth/zhihu/callback。
4. 末尾斜杠要保持一致，建议不要加尾斜杠。
```

如果使用 Cloudflare Tunnel：

```text
1. 必须使用稳定 named tunnel 域名。
2. 不要使用随机 trycloudflare 域名做正式 redirect URI。
3. 每次域名变化都需要同步修改知乎开放平台 redirect URI 和 ZHIHU_OAUTH_REDIRECT_URI。
```

---

## 6. 环境变量方案

当前 Dockerfile 不会把 `services/config.yaml` 自动复制到容器里。正式部署建议优先用环境变量注入，不依赖容器内配置文件路径。

### 6.1 infra/.env 示例

不要提交真实值。

```bash
# 公网 origin
PUBLIC_ORIGIN=https://<domain>

# 前端构建时写入浏览器端。必须公网可达，不能填 Docker 内网地址。
KANSHAN_GATEWAY_URL=https://<domain>
KANSHAN_ZHIHU_URL=https://<domain>

# 运行模式与存储
PROVIDER_MODE=live
STORAGE_BACKEND=postgres
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql+psycopg://kanshan:<strong-password>@postgres:5432/kanshan
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=https://<domain>

# OAuth state 签名密钥，生产必须替换
OAUTH_STATE_SECRET=<random-long-secret>

# 知乎 Community 能力
ZHIHU_APP_KEY=<community-app-key>
ZHIHU_APP_SECRET=<community-app-secret>
ZHIHU_COMMUNITY_BASE_URL=https://openapi.zhihu.com
ZHIHU_DEFAULT_RING_ID=<default-ring-id>

# 知乎 OAuth 能力
ZHIHU_OAUTH_APP_ID=<oauth-app-id>
ZHIHU_OAUTH_APP_KEY=<oauth-app-key>
ZHIHU_OAUTH_REDIRECT_URI=https://<domain>/auth/zhihu/callback
ZHIHU_OAUTH_BASE_URL=https://openapi.zhihu.com

# 知乎 Data Platform 能力
ZHIHU_ACCESS_SECRET=<developer-access-secret>
ZHIHU_DATA_PLATFORM_BASE_URL=https://developer.zhihu.com
LLM_DEFAULT_MODEL=zhida-thinking-1p5

# LLM
LLM_PROVIDER_MODE=openai_compat
OPENAI_COMPAT_BASE_URL=<openai-compatible-base-url>
OPENAI_COMPAT_API_KEY=<api-key>
OPENAI_COMPAT_MODEL=<model>
```

### 6.2 Docker Compose 必须补充的环境变量

当前 compose 中只有 api-gateway 明确配置了完整服务间 URL。为了 OAuth 和关注流在容器内跑通，至少需要给以下服务补充：

```yaml
services:
  profile-service:
    environment:
      PROVIDER_MODE: ${PROVIDER_MODE:-live}
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
      STORAGE_BACKEND: ${STORAGE_BACKEND:-postgres}
      ZHIHU_ADAPTER_URL: http://zhihu-adapter:8070
      LLM_SERVICE_URL: http://llm-service:8080
      OAUTH_STATE_SECRET: ${OAUTH_STATE_SECRET}

  content-service:
    environment:
      PROVIDER_MODE: ${PROVIDER_MODE:-live}
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
      STORAGE_BACKEND: ${STORAGE_BACKEND:-postgres}
      PROFILE_SERVICE_URL: http://profile-service:8010
      ZHIHU_ADAPTER_URL: http://zhihu-adapter:8070
      LLM_SERVICE_URL: http://llm-service:8080

  llm-service:
    environment:
      PROVIDER_MODE: ${PROVIDER_MODE:-live}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
      ZHIHU_ADAPTER_URL: http://zhihu-adapter:8070
      LLM_PROVIDER_MODE: ${LLM_PROVIDER_MODE:-openai_compat}
      OPENAI_COMPAT_BASE_URL: ${OPENAI_COMPAT_BASE_URL}
      OPENAI_COMPAT_API_KEY: ${OPENAI_COMPAT_API_KEY}
      OPENAI_COMPAT_MODEL: ${OPENAI_COMPAT_MODEL}

  zhihu-adapter:
    environment:
      PROVIDER_MODE: ${PROVIDER_MODE:-live}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
      ZHIHU_APP_KEY: ${ZHIHU_APP_KEY}
      ZHIHU_APP_SECRET: ${ZHIHU_APP_SECRET}
      ZHIHU_COMMUNITY_BASE_URL: ${ZHIHU_COMMUNITY_BASE_URL:-https://openapi.zhihu.com}
      ZHIHU_DEFAULT_RING_ID: ${ZHIHU_DEFAULT_RING_ID}
      ZHIHU_OAUTH_APP_ID: ${ZHIHU_OAUTH_APP_ID}
      ZHIHU_OAUTH_APP_KEY: ${ZHIHU_OAUTH_APP_KEY}
      ZHIHU_OAUTH_REDIRECT_URI: ${ZHIHU_OAUTH_REDIRECT_URI}
      ZHIHU_OAUTH_BASE_URL: ${ZHIHU_OAUTH_BASE_URL:-https://openapi.zhihu.com}
      ZHIHU_ACCESS_SECRET: ${ZHIHU_ACCESS_SECRET}
      ZHIHU_DATA_PLATFORM_BASE_URL: ${ZHIHU_DATA_PLATFORM_BASE_URL:-https://developer.zhihu.com}
      LLM_DEFAULT_MODEL: ${LLM_DEFAULT_MODEL:-zhida-thinking-1p5}
```

前端构建参数：

```yaml
frontend:
  build:
    args:
      NEXT_PUBLIC_KANSHAN_BACKEND_MODE: gateway
      NEXT_PUBLIC_KANSHAN_GATEWAY_URL: ${KANSHAN_GATEWAY_URL}
      NEXT_PUBLIC_ZHIHU_ADAPTER_URL: ${KANSHAN_ZHIHU_URL}
```

注意：

```text
NEXT_PUBLIC_KANSHAN_GATEWAY_URL 必须是 https://<domain>。
不能填 http://api-gateway:8000，因为这是 Docker 内网地址，浏览器访问不到。
```

---

## 7. 当前代码上线前必须处理的问题

### 7.1 success 页的本地 fallback

当前：

```text
frontend/app/oauth/zhihu/success/page.tsx
```

存在本地调试残留逻辑：

```text
非本地 origin 时重定向到 LOCAL_FALLBACK_ORIGIN
```

上线前必须改成：

```text
生产环境不跳本地 fallback。
success 页保持在 https://<domain>/oauth/zhihu/success。
只向 opener_origin 或当前 origin postMessage。
```

否则正式域名授权成功后，可能又被带回本地地址，导致主页面无法收到 ticket。

### 7.2 Cloudflare dev origin

`next.config.ts` 中的 `allowedDevOrigins` 只用于 Next.js dev server。

生产环境：

```text
npm run build / npm start 不依赖 allowedDevOrigins。
不要把随机 trycloudflare 域名当作正式配置写死。
```

### 7.3 zhihu-adapter 不应由浏览器直接访问

当前 OAuth 正式链路不需要浏览器访问：

```text
NEXT_PUBLIC_ZHIHU_ADAPTER_URL
```

保留该变量可以，但正式流程应全部走：

```text
前端 → /api/v1/auth/zhihu/* → api-gateway → profile-service → zhihu-adapter
```

---

## 8. 上线步骤

### 8.1 准备域名和 HTTPS

```text
1. 域名解析到服务器。
2. 配置 Caddy / Nginx。
3. 确认 https://<domain> 可以打开前端。
4. 确认 https://<domain>/api/... 可以代理到 gateway。
```

### 8.2 配置知乎开放平台

```text
redirect URI = https://<domain>/auth/zhihu/callback
```

### 8.3 配置 infra/.env

按第 6 节填入：

```text
PUBLIC_ORIGIN
KANSHAN_GATEWAY_URL
ZHIHU_OAUTH_REDIRECT_URI
ZHIHU_OAUTH_APP_ID
ZHIHU_OAUTH_APP_KEY
ZHIHU_ACCESS_SECRET
```

### 8.4 重新构建前端

前端环境变量是 build-time 写入，改 `.env` 后必须重建：

```bash
docker compose -f infra/docker-compose.yml build --no-cache frontend
docker compose -f infra/docker-compose.yml up -d
```

### 8.5 验证服务健康

```bash
curl -s https://<domain>/api/v1/auth/me
curl -s https://<domain>/api/v1/auth/zhihu/authorize
```

授权 URL 中必须能看到编码后的：

```text
redirect_uri=https%3A%2F%2F<domain>%2Fauth%2Fzhihu%2Fcallback
```

### 8.6 浏览器验证 OAuth

```text
1. 打开 https://<domain>
2. 注册或进入知乎授权步骤
3. 点击“尝试关联知乎账号”
4. 弹出知乎授权页
5. 确认授权
6. 回到 https://<domain>/auth/zhihu/callback
7. 前端请求 /api/v1/auth/zhihu/callback
8. success 页 postMessage ticket
9. 主页面 exchange-ticket
10. 进入 LLM 配置或工作台
```

### 8.7 数据库验证

授权完成后检查：

```sql
select user_id, zhihu_uid, binding_status, bound_at, expired_at
from profile.zhihu_bindings
order by bound_at desc
limit 5;
```

必须看到：

```text
binding_status = bound
access_token 非空
```

---

## 9. 排错表

| 现象 | 优先检查 |
| --- | --- |
| 知乎提示 redirect_uri 不匹配 | 知乎开放平台配置、`ZHIHU_OAUTH_REDIRECT_URI`、授权 URL 中的 redirect_uri 三者是否完全一致 |
| 授权后打开“无法访问此网站” | redirect URI 仍是旧 Cloudflare / 127.0.0.1 / 未代理的后端地址 |
| callback 到了但 502 | api-gateway 到 profile-service，或 profile-service 到 zhihu-adapter 的 Docker 内网 URL 不通 |
| ticket 生成了但主页面没跳转 | success 页和主页面不是同源，或 success 页被本地 fallback 带走 |
| popup 成功但主页面没 session | `/api/v1/auth/zhihu/exchange-ticket` 失败，检查 ticket 是否过期或被重复消费 |
| 关注流为空 | profile.zhihu_bindings 没有 access_token，或 content-service 没有 `PROFILE_SERVICE_URL` / `ZHIHU_ADAPTER_URL` |
| 前端请求 http://api-gateway:8000 | 前端构建时 `KANSHAN_GATEWAY_URL` 填了 Docker 内网地址，需要重新 build frontend |
| CORS 报错 | 正式环境建议同源；如仍跨域，确认 `CORS_ORIGINS=https://<domain>` |

---

## 10. 最小验收标准

上线 OAuth 跑通的标准：

```text
1. https://<domain>/api/v1/auth/zhihu/authorize 返回真实知乎授权 URL。
2. 授权 URL 中 redirect_uri 指向 https://<domain>/auth/zhihu/callback。
3. 浏览器授权后不会跳到 127.0.0.1 或旧 Cloudflare 域名。
4. profile.zhihu_bindings 写入 bound 记录。
5. 主页面 localStorage 写入 kanshan:session:v1。
6. GET /api/v1/auth/me 返回 authenticated=true。
7. 新用户进入 llm_pending，老用户按 setupState 进入后续页面。
8. 关注流精选可以通过保存的 access_token 拉取数据。
```

只要以上 8 项通过，线上 OAuth 流程就可以认为可用于 Demo。
