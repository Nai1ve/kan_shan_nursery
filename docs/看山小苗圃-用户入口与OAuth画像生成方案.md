# 看山小苗圃-用户入口与 OAuth 画像生成方案

本文档用于评估下一阶段的前端入口调整、用户管理系统、知乎 OAuth 绑定流程，以及基于 OAuth 开放能力生成用户画像 Memory 的算法方案。

本文不是代码实现文档，而是开发前的方案文档。后续实现时需要同步更新：

- `docs/开发路线图.md`
- `docs/看山小苗圃-开发设计与实施.md`
- `docs/看山小苗圃-当前前端接口文档.md`
- `services/profile-service/README.md`
- `services/api-gateway/README.md`
- `services/zhihu-adapter/README.md`
- `services/llm-service/README.md`

---

## 1. 当前进度判断

根据当前 git 和文档，项目已经完成到 v0.6 左右：

- 前端已经支持 `mock` / `gateway` 两种模式。
- `api-gateway` 已有统一 envelope、CORS、下游服务代理。
- `profile-service` 已有演示画像、兴趣 Memory、Memory update request。
- `zhihu-adapter` 已有 OAuth authorize/callback、关注流、关注列表、粉丝列表能力。
- `llm-service` 已有多 provider / task route / prompt / trace 框架，但业务服务还未全面接入真实 LLM。
- 前端入口仍然是旧的三选项：关联知乎账号 / 首次画像采集 / 直接演示模式。

当前最大问题不是某一个页面样式，而是入口状态机不成立：

```text
当前入口：
用户打开页面
→ 可以直接进入演示 / 画像 / OAuth
→ 没有注册、登录、用户身份、会话、OAuth 绑定状态
→ 无法把知乎授权结果和某个用户绑定
→ 无法为真实用户生成可追踪的 Memory
```

目标入口应调整为：

```text
新用户访问平台
→ 注册 / 登录
→ 提示关联知乎账号
→ 选择兴趣领域与写作风格
→ 立即生成一份临时画像 Memory
→ 后台通过 OAuth 拉取用户信息、关注列表、粉丝列表、关注动态
→ LLM 汇总分析，生成增强画像 Memory
→ 用户可查看、确认、编辑
→ 进入今日看什么 / 种子库 / 写作苗圃
```

---

## 2. 设计原则

### 2.1 用户身份先于 OAuth

OAuth 授权必须绑定到一个本地用户，否则无法判断：

- 这个 `access_token` 属于谁。
- 生成的 Memory 应该写给谁。
- 用户是否完成了 onboarding。
- 后台画像生成任务应该关联哪个用户。

因此入口顺序必须是：

```text
register/login → zhihu binding → onboarding → profile generation → app
```

而不是直接：

```text
open app → zhihu adapter authorize
```

### 2.2 临时画像先可用，增强画像后补全

知乎鉴权当前未完全开放，OAuth 拉取也可能失败。产品不能卡死在 OAuth 上。

规则：

- 用户完成兴趣领域和写作风格选择后，立即生成 `provisional` 画像。
- 如果知乎未绑定或 OAuth 失败，用户仍可进入平台使用基础功能。
- OAuth 绑定成功后，后台生成 `enriched` 画像。
- 增强画像生成完成后，展示差异和证据来源，由用户确认应用或编辑后应用。

### 2.3 AI 生成画像必须可解释、可回滚

用户画像会影响推荐和写作，不能黑盒覆盖。

规则：

- 每条 Memory 变更要带来源证据。
- 低置信度推断不能直接写入长期 Memory。
- 不使用手机号、邮箱等敏感信息生成写作画像。
- 用户可编辑、拒绝、重新生成。
- 写作 session 的 `memoryOverride` 仍只影响本次写作，不覆盖长期 Memory。

### 2.4 前端只认平台状态，不认服务细节

前端不应该理解知乎 token、adapter 配置、LLM provider。

前端只关心：

```ts
currentUser
sessionStatus
zhihuBindingStatus
onboardingStatus
profileGenerationStatus
profileMemory
```

所有真实调用通过 `api-gateway`。

---

## 3. 新入口状态机

### 3.1 用户状态

建议新增前端状态枚举：

```ts
type AuthStatus =
  | "guest"
  | "registered"
  | "authenticated"
  | "logged_out";

type ZhihuBindingStatus =
  | "not_started"
  | "authorizing"
  | "bound"
  | "failed"
  | "skipped"
  | "unavailable";

type OnboardingStatus =
  | "not_started"
  | "preferences_pending"
  | "provisional_ready"
  | "completed";

type ProfileGenerationStatus =
  | "not_started"
  | "queued"
  | "collecting_oauth_data"
  | "analyzing"
  | "draft_ready"
  | "applied"
  | "failed";
```

组合后的平台入口状态：

| 状态 | 说明 | 前端应该展示 |
| --- | --- | --- |
| guest | 未注册未登录 | 注册 / 登录页 |
| registered | 注册成功但未选择是否关联知乎 | 关联知乎提示页 |
| zhihu_pending | 正在授权或授权失败 | 授权进度、失败原因、稍后关联入口 |
| preferences_pending | 需要选择领域和写作风格 | 兴趣领域和风格问卷 |
| provisional_ready | 临时画像已生成 | 可以进入主应用，提示增强画像后台处理中 |
| enrichment_running | OAuth 数据汇总中 | 进度条，不阻塞主应用 |
| enrichment_review | 增强画像草稿待确认 | 展示 Memory 变化、证据来源、确认/编辑/拒绝 |
| ready | 长期画像可用 | 进入完整工作台 |

### 3.2 页面流转

建议路由或页面层级：

```text
/
  AuthGate
    ├─ /register
    ├─ /login
    ├─ /onboarding/zhihu
    ├─ /onboarding/preferences
    ├─ /onboarding/profile-generation
    └─ /app
```

如果继续保持单页组件，也要把 `LoginScreen` 拆成明确步骤：

```text
AuthEntry
RegisterPanel
LoginPanel
ZhihuLinkPanel
PreferenceOnboardingPanel
ProfileGenerationPanel
KanshanAppShell
```

---

## 4. 前端调整方案

### 4.1 替换当前 LoginScreen

当前 `LoginScreen` 的三个入口不再作为正式入口：

- 关联知乎账号
- 首次使用，先建立画像
- 直接进入演示模式

新的正式入口：

```text
看山小苗圃
一句话说明：从知乎输入到观点表达的创作工作台

[注册并开始] [已有账号登录]
```

演示模式仍可保留，但应放在开发者入口或路演入口中，避免和真实用户流程混在一起：

```text
开发/路演：进入演示模式
```

### 4.2 注册页

字段建议：

```ts
RegisterRequest {
  nickname: string;
  email?: string;
  username?: string;
  password: string;
}
```

黑客松阶段可简化：

- `nickname`
- `email` 或 `username`
- `password`

前端行为：

1. 用户提交注册。
2. 调 `POST /api/v1/auth/register`。
3. 成功后写入 `CurrentUser`，进入知乎关联页。
4. 注册失败展示明确原因。

### 4.3 登录页

字段建议：

```ts
LoginRequest {
  identifier: string;
  password: string;
}
```

成功后：

1. 调 `GET /api/v1/auth/me` 获取完整入口状态。
2. 根据用户状态跳转：
   - 未绑定知乎 → 关联页
   - 未完成偏好 → 偏好页
   - 已有画像 → 工作台

### 4.4 关联知乎账号页

页面目标：让用户理解为什么要关联，以及当前不可用时能继续。

展示内容：

```text
关联知乎账号后，我们会读取：
- 当前授权用户基本信息
- 关注列表
- 粉丝列表
- 关注动态

这些信息用于生成你的创作画像 Memory，帮助系统理解：
- 你长期关注什么
- 你的信息来源偏好
- 你的潜在读者是谁
- 哪些话题适合推荐给你
```

按钮：

- `关联知乎账号`
- `暂时跳过，先建立本地画像`
- `查看将使用哪些数据`

状态展示：

```ts
ZhihuBindingViewModel {
  status: ZhihuBindingStatus;
  zhihuName?: string;
  avatarUrl?: string;
  lastAuthorizedAt?: string;
  errorMessage?: string;
  unavailableReason?: string;
}
```

当前知乎鉴权未开放时：

- `status = unavailable` 或 `failed`
- 页面显示：“知乎授权能力暂未开放，当前先使用你填写的信息生成临时画像。”
- 允许进入下一步。

### 4.5 兴趣领域与写作风格页

这一页在注册后必须执行，即使 OAuth 未绑定也要执行。

#### 兴趣领域

字段：

```ts
SelectedInterest {
  interestId: string;
  selected: boolean;
  selfRatedLevel: "beginner" | "intermediate" | "advanced";
  intent: "read" | "write" | "both";
}
```

候选领域沿用当前兴趣小类：

- Agent 工程化
- AI Coding
- RAG / 检索
- 后端工程
- 程序员成长
- 金融风控
- 医学 AI
- 产品设计
- 内容创作

注意：

- `关注流精选` 和 `偶遇输入` 是输入来源，不是用户主动选择的兴趣领域。
- 前端不应把它们放进长期兴趣 Memory 的主分类。

#### 写作风格

当前已有 12 个问卷问题，可以保留但需要结构化保存。

建议字段：

```ts
WritingStyleSurvey {
  logicDepth: 1 | 2 | 3 | 4 | 5;
  stanceSharpness: 1 | 2 | 3 | 4 | 5;
  personalExperienceWillingness: 1 | 2 | 3 | 4 | 5;
  expressionSharpness: 1 | 2 | 3 | 4 | 5;
  preferredFormat: "zhihu_answer" | "balanced" | "long_article" | "column" | "draft";
  evidenceVsJudgment: "evidence_first" | "balanced" | "judgment_first";
  wantsCounterArguments: boolean;
  openingStyle: "direct" | "balanced" | "story";
  titleStyle: "restrained" | "balanced" | "spreadable";
  uncertaintyTolerance: 1 | 2 | 3 | 4 | 5;
  emotionalTemperature: "cold" | "balanced" | "emotional";
  aiAssistanceBoundary: "outline" | "paragraph" | "draft" | "polish" | "publish_ready";
}
```

### 4.6 画像生成进度页

提交偏好后，立即生成临时画像并进入进度页。

前端展示：

```text
正在建立你的创作画像

已完成：
✓ 保存兴趣领域
✓ 生成临时画像

后台进行中：
- 读取知乎用户信息
- 汇总关注列表
- 汇总粉丝列表
- 分析关注动态
- 生成增强 Memory
```

如果 OAuth 未绑定：

```text
知乎账号暂未关联，当前使用你填写的信息生成临时画像。你可以先进入工作台，稍后在个人画像页重新关联知乎并增强画像。
```

按钮：

- `进入工作台`
- `查看临时画像`
- `稍后关联知乎`

### 4.7 主应用中的状态提示

进入工作台后，顶部或个人画像页需要显示画像状态：

```text
画像状态：临时画像 / OAuth 增强中 / 增强画像待确认 / 已应用增强画像
知乎账号：未关联 / 已关联 / 授权失效
```

个人画像页新增区块：

```text
授权与数据来源
- 知乎账号绑定状态
- 上次 OAuth 数据同步时间
- 已使用的数据：用户信息、关注列表、粉丝列表、关注动态、用户回答内容
- 重新同步并生成画像
- 解除绑定
```

### 4.8 前端本地状态变更

当前 `DemoState` 需要拆出平台状态。建议新增：

```ts
CurrentUser {
  id: string;
  nickname: string;
  email?: string;
  createdAt: string;
}

UserSetupState {
  authStatus: AuthStatus;
  zhihuBindingStatus: ZhihuBindingStatus;
  onboardingStatus: OnboardingStatus;
  profileGenerationStatus: ProfileGenerationStatus;
  canEnterApp: boolean;
  profileConfidence?: number;
}
```

前端初始化不再直接加载业务 bootstrap，而是先调用：

```text
GET /api/v1/auth/me
```

返回后按状态决定加载哪个页面。

---

## 5. 后端接口建议

### 5.1 Auth / 用户管理接口

建议暂时不新增独立 `auth-service`，先由 `profile-service` 增加 `auth` 子模块承载用户、会话、知乎绑定和 onboarding 状态。

原因：

- 当前项目已经有 `profile-service` 负责用户画像和真实用户资料。
- 黑客松阶段再拆一个 `auth-service` 会增加部署和联调成本。
- 后续如果用户管理变复杂，可以再拆服务。

Gateway 暴露接口：

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

Profile-service 内部接口：

```text
POST /auth/register
POST /auth/login
POST /auth/logout
GET  /auth/me
```

返回建议：

```ts
AuthMeResponse {
  user?: CurrentUser;
  setupState: UserSetupState;
  profile?: ProfileData;
  zhihuBinding?: ZhihuBindingViewModel;
}
```

会话策略：

- 正式推荐：`HttpOnly` cookie session。
- 前端 `fetch` 需要 `credentials: "include"`。
- `api-gateway` 负责读取 session，向下游透传 `X-Kanshan-User-Id`。
- 本地开发可先用内存 session，后续换 Redis 或数据库。

### 5.2 OAuth 绑定接口

当前前端直接跳 `zhihu-adapter /zhihu/oauth/authorize?redirect=true`，这个做法无法把 token 绑定到本地用户。

建议改成：

```text
GET  /api/v1/auth/zhihu/authorize
GET  /api/v1/auth/zhihu/callback
GET  /api/v1/auth/zhihu/binding
DELETE /api/v1/auth/zhihu/binding
```

目标流程：

```text
frontend
→ GET /api/v1/auth/zhihu/authorize
→ gateway 生成 state(userId, nonce, returnTo)
→ gateway 请求 zhihu-adapter 生成 authorize_url
→ frontend 跳转知乎授权页
→ 知乎回调 /api/v1/auth/zhihu/callback?code=...&state=...
→ gateway 校验 state
→ gateway 调 zhihu-adapter 交换 token
→ profile-service 保存 ZhihuOAuthBinding
→ redirect frontend /onboarding/preferences 或 /profile?zhihu=bound
```

需要对 `zhihu-adapter` 增加一个内部 token exchange 能力，避免 callback 直接返回 token 给用户复制：

```text
POST /zhihu/oauth/exchange
body: { code: string }
return: { access_token, token_type, expires_in }
```

当前 v0.6 adapter 的 callback 返回 HTML 并让用户复制 token 到 `config.yaml`。这个只适合单人联调，不适合平台用户管理。

### 5.3 OAuth 数据采集接口

Gateway 暴露：

```text
POST /api/v1/profile/enrichment-jobs
GET  /api/v1/profile/enrichment-jobs/{jobId}
POST /api/v1/profile/enrichment-jobs/{jobId}/apply
POST /api/v1/profile/enrichment-jobs/{jobId}/reject
```

Profile-service 内部：

```text
POST /profile/enrichment-jobs
GET  /profile/enrichment-jobs/{jobId}
POST /profile/enrichment-jobs/{jobId}/apply
POST /profile/enrichment-jobs/{jobId}/reject
```

Job 创建后由 profile-service 编排：

```text
profile-service
→ zhihu-adapter: /zhihu/user
→ zhihu-adapter: /zhihu/user-followed
→ zhihu-adapter: /zhihu/user-followers
→ zhihu-adapter: /zhihu/following-feed
→ llm-service: profile-signal-extract
→ llm-service: profile-memory-synthesize
→ llm-service: profile-risk-review
→ 生成 ProfileMemoryDraft 或 MemoryUpdateRequest
```

### 5.4 zhihu-adapter 需要补的能力

当前已有：

```text
GET /zhihu/oauth/authorize
GET /zhihu/oauth/callback
GET /zhihu/following-feed
GET /zhihu/user-followed
GET /zhihu/user-followers
```

建议补：

```text
GET  /zhihu/user
POST /zhihu/oauth/exchange
```

并改造 OAuthClient 支持 per-user token，而不是只读取全局 `services/config.yaml` 中的 `zhihu.oauth.access_token`。

建议内部调用方式：

```text
X-Kanshan-User-Id: user_xxx
X-Zhihu-Access-Token: encrypted/decrypted server-side token only inside backend network
```

或者：

```text
profile-service 保存 token
gateway 调 adapter 时从 profile-service 获取 token 并注入内部 header
adapter 不持久化 token
```

前端永远不能拿到 `access_token`。

---

## 6. 数据模型建议

### 6.1 用户与会话

```ts
User {
  id: string;
  nickname: string;
  email?: string;
  username?: string;
  passwordHash: string;
  createdAt: string;
  updatedAt: string;
}

Session {
  id: string;
  userId: string;
  expiresAt: string;
  createdAt: string;
}
```

### 6.2 知乎绑定

```ts
ZhihuOAuthBinding {
  userId: string;
  zhihuUid: string;
  hashId?: string;
  fullname: string;
  headline?: string;
  avatarPath?: string;
  accessTokenEncrypted: string;
  tokenType: "Bearer";
  expiresAt?: string;
  lastAuthorizedAt: string;
  status: "bound" | "expired" | "revoked" | "failed";
}
```

### 6.3 Onboarding 输入

```ts
OnboardingProfile {
  userId: string;
  selectedInterests: SelectedInterest[];
  writingStyleSurvey: WritingStyleSurvey;
  avoidances: string;
  selfDescription?: string;
  createdAt: string;
  updatedAt: string;
}
```

### 6.4 OAuth 数据快照

```ts
ProfileSourceSnapshot {
  id: string;
  userId: string;
  jobId: string;
  sourceType: "zhihu_user" | "followed" | "followers" | "moments" | "authored_content" | "onboarding";
  fetchedAt: string;
  itemCount: number;
  rawHash: string;
  sanitizedItems: unknown[];
  ttlExpiresAt?: string;
}
```

建议：

- P0 可以只存 sanitized 数据，不存 raw。
- 如果存 raw，必须短 TTL 或本地加密。
- 手机号、邮箱不进入 LLM 输入。

### 6.5 画像生成任务

```ts
ProfileEnrichmentJob {
  id: string;
  userId: string;
  status:
    | "queued"
    | "collecting_oauth_data"
    | "analyzing"
    | "draft_ready"
    | "applied"
    | "failed";
  progress: number;
  sourceCoverage: SourceCoverage;
  draft?: GeneratedProfileMemory;
  error?: string;
  createdAt: string;
  updatedAt: string;
}
```

### 6.6 生成画像草稿

```ts
GeneratedProfileMemory {
  globalMemory: GlobalMemory;
  interestMemories: MemorySummary[];
  audienceInsights: AudienceInsight[];
  sourceCoverage: SourceCoverage;
  confidence: number;
  evidenceRefs: MemoryEvidenceRef[];
  warnings: string[];
}

MemoryEvidenceRef {
  evidenceId: string;
  sourceType: string;
  sourceId: string;
  text: string;
  supportsField: string;
  confidence: number;
}
```

---

## 7. OAuth 信息汇总算法

### 7.1 输入来源

OAuth 可用数据按优先级分层：

| 来源 | 接口 | 用途 | 权重 |
| --- | --- | --- | --- |
| 用户主动填写 | onboarding | 明确兴趣、风格、禁忌 | 最高 |
| 用户基本信息 | `GET /user` | 昵称、简介、headline、头像 | 高 |
| 用户回答内容 | 直接接口若开放；否则从动态/搜索/手动导入降级 | 写作风格、知识领域、观点习惯 | 高 |
| 关注动态 | `GET /user/moments` | 最近输入来源、关注主题、内容偏好 | 中高 |
| 关注列表 | `GET /user/followed` | 长期信息源、人群和领域偏好 | 中 |
| 粉丝列表 | `GET /user/followers` | 潜在读者画像、受众构成 | 中低 |

注意：当前本地 `docs/知乎API.md` 只明确了 `/user`、`/user/followed`、`/user/followers`、`/user/moments`。没有看到稳定的“获取当前用户全部回答列表”接口。

因此“用户回答内容”的 P0 降级策略是：

1. 如果 OAuth 文档后续补充 authored content API，优先使用。
2. 如果 `/user/moments` 中能识别当前用户自己的发布或回答，抽取其中 target。
3. 使用知乎搜索，以用户昵称 + 自选兴趣关键词检索，低置信度标注。
4. 允许用户手动粘贴 1-3 篇代表回答或文章，作为高置信度样本。

### 7.2 数据采集上限

为了避免接口额度和 LLM token 爆炸，建议 P0 上限：

```text
user info: 1 次
followed: page 0-2, per_page 20, 最多 60 人
followers: page 0-2, per_page 20, 最多 60 人
moments: 默认返回条数，最多取 50 条
authored content samples: 最多 20 条
```

缓存：

- OAuth 数据使用 Redis 短缓存即可。
- 关注/粉丝列表 TTL 30 分钟。
- 关注动态 TTL 10 分钟。
- 用户信息 TTL 30 分钟。
- 画像生成任务自身保存 snapshot hash，避免同一批数据重复分析。

### 7.3 数据清洗

进入 LLM 前做标准化和脱敏：

```text
1. 删除 email、phone_no。
2. 用户名、头像、url 可保留用于展示，但不作为画像推断依据。
3. HTML 摘要去标签。
4. 每条内容保留 sourceId、sourceType、title、excerpt、author、actionText、time。
5. 超长 excerpt 截断到 160-240 字。
6. 对重复标题和重复作者去重。
```

标准化结构：

```ts
ProfileSignalSourceItem {
  sourceType: "onboarding" | "zhihu_user" | "followed" | "followers" | "moments" | "authored_content";
  sourceId: string;
  title?: string;
  excerpt?: string;
  authorName?: string;
  headline?: string;
  actionText?: string;
  publishedAt?: string;
  url?: string;
  confidenceHint: number;
}
```

### 7.4 主题候选提取

先用确定性规则生成候选主题，再交给 LLM 精炼。

确定性规则：

```text
onboarding interests → 初始主题，baseWeight = 1.0
用户 headline/description → 提取关键词，baseWeight = 0.7
用户回答内容 title/excerpt → baseWeight = 0.9
关注动态 title/excerpt → baseWeight = 0.65
关注列表 headline/description → baseWeight = 0.45
粉丝列表 headline/description → baseWeight = 0.3
```

时间衰减：

```text
recencyWeight =
  1.0       if 7 天内
  0.85      if 30 天内
  0.65      if 90 天内
  0.45      otherwise
```

主题得分：

```text
topicScore =
  onboardingMatch * 0.35
+ authoredContentMatch * 0.25
+ momentsMatch * 0.20
+ followedProfileMatch * 0.10
+ followerAudienceMatch * 0.05
+ recencyAndDensity * 0.05
```

置信度：

```text
confidence = min(0.95,
  0.25
+ sourceTypeCount * 0.12
+ evidenceCount * 0.03
+ onboardingAgreement * 0.20
- contradictionPenalty
)
```

规则：

- 用户主动选择的兴趣不会被 OAuth 分析删除，只能降权或标注“证据不足”。
- OAuth 分析发现的新兴趣如果置信度低于 0.65，只作为推荐候选，不直接进入长期兴趣 Memory。

### 7.5 写作风格提取

写作风格来自两类信号：

- 用户问卷：强信号。
- 用户回答内容：强信号，如果可获取。
- 关注动态和关注列表：弱信号，只说明用户阅读偏好，不等于用户写作风格。

提取维度：

```ts
WritingStyleSignals {
  logicDepth: number;
  stanceSharpness: number;
  evidenceDensity: number;
  personalExperienceDensity: number;
  counterArgumentAwareness: number;
  emotionalTemperature: number;
  titleStyle: "restrained" | "balanced" | "spreadable";
  preferredArticleForm: string[];
}
```

规则：

- 如果没有用户回答内容，不要从关注流强推断“用户自己的写作风格”。
- 只能说“用户偏好的阅读内容具有某种风格”。
- 画像文案中要区分：`写作风格` 和 `阅读偏好`。

---

## 8. LLM 任务设计

### 8.1 任务一：profile-signal-extract

用途：把清洗后的 OAuth 数据和 onboarding 输入转为结构化信号。

输入：

```ts
ProfileSignalExtractInput {
  onboarding: OnboardingProfile;
  zhihuUser?: SanitizedZhihuUser;
  followed: ProfileSignalSourceItem[];
  followers: ProfileSignalSourceItem[];
  moments: ProfileSignalSourceItem[];
  authoredContent: ProfileSignalSourceItem[];
  existingProfile?: ProfileData;
}
```

输出：

```ts
ProfileSignalExtractOutput {
  topicCandidates: {
    topic: string;
    matchedInterestId?: string;
    score: number;
    confidence: number;
    evidenceIds: string[];
    reason: string;
  }[];
  writingStyleSignals: WritingStyleSignals;
  audienceInsights: {
    audienceLabel: string;
    evidenceIds: string[];
    confidence: number;
  }[];
  risks: string[];
  insufficientData: string[];
}
```

Prompt 约束：

```text
- 只输出 JSON。
- 所有结论必须引用 evidenceIds。
- 不使用邮箱、手机号、性别进行内容推荐和写作风格推断。
- 区分“用户自己的表达风格”和“用户偏好的阅读风格”。
- 不要把关注列表中的某个作者观点直接当成用户观点。
```

### 8.2 任务二：profile-memory-synthesize

用途：从结构化信号生成 `ProfileData` 和 `MemorySummary[]`。

输入：

```ts
ProfileMemorySynthesizeInput {
  user: CurrentUser;
  onboarding: OnboardingProfile;
  signalExtract: ProfileSignalExtractOutput;
  existingProfile?: ProfileData;
}
```

输出：

```ts
ProfileMemorySynthesizeOutput {
  globalMemory: {
    longTermBackground: string;
    contentPreference: string;
    writingStyle: string;
    recommendationStrategy: string;
    riskReminder: string;
  };
  interestMemories: MemorySummary[];
  confidence: number;
  evidenceRefs: MemoryEvidenceRef[];
  suggestedNewInterests: string[];
  warnings: string[];
}
```

生成规则：

- `longTermBackground` 只写用户明确填写或知乎简介能支持的信息。
- `contentPreference` 可以综合关注流、关注列表、用户主动兴趣。
- `writingStyle` 以问卷和用户回答内容为主。
- `recommendationStrategy` 要说明兴趣小类、关注流、偶遇输入如何配合。
- `riskReminder` 要指出内容生产风险，例如过度抽象、缺少个人经验、证据不足、AI 味过重。

### 8.3 任务三：profile-risk-review

用途：审查画像草稿是否过度推断、是否使用敏感信息、是否覆盖用户明确偏好。

输入：

```ts
ProfileRiskReviewInput {
  draft: ProfileMemorySynthesizeOutput;
  evidenceRefs: MemoryEvidenceRef[];
  onboarding: OnboardingProfile;
}
```

输出：

```ts
ProfileRiskReviewOutput {
  safeToApply: boolean;
  requiredEdits: string[];
  lowConfidenceFields: string[];
  privacyWarnings: string[];
}
```

规则：

- `safeToApply = false` 时，只能生成待确认草稿，不自动写入长期 Memory。
- 即使 `safeToApply = true`，也建议在首次画像生成时给用户展示确认页。

---

## 9. 画像合并策略

画像来源优先级：

```text
用户显式填写 > 用户手动编辑 Memory > 用户回答内容 > 用户基本信息 > 关注动态 > 关注列表 > 粉丝列表
```

合并规则：

1. 用户主动选择的兴趣不删除。
2. 用户主动填写的 `avoidances` 不被 LLM 覆盖。
3. 用户手动编辑过的 Memory 字段需要版本标记，LLM 只能生成更新建议。
4. OAuth 增强画像首次生成时，可以作为草稿展示；用户确认后应用。
5. 后续重新生成只能进入 `MemoryUpdateRequest`，不能静默覆盖。

输出状态：

```text
provisional: 仅由 onboarding 生成，可立即使用
enriched_draft: OAuth + LLM 生成，等待用户确认
enriched_applied: 用户确认后应用
stale: OAuth 数据超过有效期，建议重新同步
```

---

## 10. 用户回答内容的处理方案

用户希望“结合用户的回答内容”。当前需要先明确接口可用性。

### 10.1 如果知乎开放 authored content API

直接采集：

```text
GET /user/answers 或官方等价接口
GET /user/articles 或官方等价接口
```

分析字段：

- 标题
- 摘要
- 发布时间
- 互动数据
- 话题标签
- 评论摘要

### 10.2 如果没有 authored content API

采用降级策略：

| 策略 | 置信度 | 说明 |
| --- | --- | --- |
| 用户手动粘贴代表回答 | 高 | 最稳，适合 onboarding 增强项 |
| 关注动态中识别当前用户行为 | 中 | 如果 moments 中包含当前用户自己的回答行为 |
| 知乎搜索昵称 + 兴趣关键词 | 低 | 可能误召回同名用户，必须低置信度标注 |
| 暂不分析写作风格 | 安全 | 只用问卷生成写作风格 |

前端可在 onboarding 后加一个可选入口：

```text
你可以粘贴 1-3 篇你觉得代表自己的知乎回答或文章链接，帮助系统更准确理解你的表达风格。
```

P0 不强制。

---

## 11. 前端实现切片

### Phase A：入口状态机和 mock 用户管理

目标：先把入口逻辑走通，不依赖真实 OAuth。

改动范围：

```text
frontend/components/kanshan-app.tsx 或拆分 components/auth/*
frontend/lib/types.ts
frontend/lib/api-client.ts
frontend/lib/gateway-client.ts
frontend/app/api/mock/auth/* 可选
```

内容：

- 新注册页。
- 登录页。
- 知乎关联提示页。
- 兴趣领域和写作风格页。
- 画像生成状态页。
- 根据 `AuthMeResponse` 决定是否进入主工作台。

验收：

- 新用户不能直接进入主工作台，除非选择演示模式。
- 注册后进入知乎关联页。
- 跳过知乎后仍能填写兴趣和写作风格。
- 完成问卷后生成临时画像并进入主工作台。
- 个人画像页显示“临时画像”。

难度：M。

### Phase B：profile-service 增加用户、会话、onboarding 状态

目标：用户状态从前端本地变成后端可恢复。

改动范围：

```text
services/profile-service/app/auth/*
services/profile-service/app/profile/*
services/profile-service/tests/*
services/api-gateway/app/main.py
frontend/lib/gateway-client.ts
```

验收：

- `POST /api/v1/auth/register` 能创建用户。
- `POST /api/v1/auth/login` 能恢复用户。
- `GET /api/v1/auth/me` 返回 setup state。
- `POST /profiles/onboarding` 能保存兴趣和写作风格，并生成 provisional profile。

难度：M-H。

### Phase C：OAuth 绑定改到 gateway 回调

目标：OAuth token 绑定用户，而不是写到 config。

改动范围：

```text
services/api-gateway/app/main.py
services/zhihu-adapter/app/main.py
services/zhihu-adapter/app/live_client.py
services/profile-service/app/auth/*
frontend auth pages
```

验收：

- 前端点击“关联知乎账号”走 gateway authorize。
- callback 能识别本地用户。
- token 不出现在前端页面。
- profile-service 能显示知乎绑定状态。
- 当前知乎授权未开放时，前端能显示 unavailable/failed，并允许跳过。

难度：H。

### Phase D：OAuth 数据采集与画像生成任务

目标：绑定后自动生成增强画像草稿。

改动范围：

```text
services/profile-service/app/enrichment/*
services/zhihu-adapter/app/main.py
services/llm-service/prompts/v1/profile-*.md
services/llm-service/app/validators.py
services/api-gateway/app/main.py
frontend profile generation panel
```

验收：

- 能创建 enrichment job。
- job 状态可轮询。
- mock OAuth 数据也能生成 profile draft。
- draft 带 confidence、sourceCoverage、evidenceRefs。
- 用户确认后写入长期 Memory。
- 用户拒绝后不修改 Memory。

难度：H。

### Phase E：用户回答内容增强

目标：补上最能反映写作风格的内容源。

方案依赖知乎是否开放 authored content API。

可先做：

- 手动粘贴代表回答链接或文本。
- 作为 `authored_content` sourceType 进入 enrichment job。

难度：M。

---

## 12. 后端算法伪代码

```python
def start_onboarding(user_id, payload):
    save_onboarding(user_id, payload)
    provisional = build_provisional_profile(payload)
    save_profile(user_id, provisional, status="provisional")
    if has_zhihu_binding(user_id):
        job = enqueue_profile_enrichment(user_id)
    else:
        job = None
    return {"profile": provisional, "enrichmentJob": job}


def run_profile_enrichment_job(job_id):
    job = mark(job_id, "collecting_oauth_data", progress=10)
    user_id = job.user_id

    onboarding = load_onboarding(user_id)
    binding = load_zhihu_binding(user_id)

    snapshots = []
    snapshots.append(snapshot("onboarding", sanitize_onboarding(onboarding)))

    if binding and binding.status == "bound":
        snapshots.append(fetch_zhihu_user(user_id))
        snapshots.extend(fetch_followed_pages(user_id, max_pages=3, per_page=20))
        snapshots.extend(fetch_followers_pages(user_id, max_pages=3, per_page=20))
        snapshots.append(fetch_following_moments(user_id))
        snapshots.extend(fetch_authored_content_if_available(user_id))

    mark(job_id, "analyzing", progress=45)

    normalized = normalize_and_redact(snapshots)
    signal_input = build_signal_extract_input(onboarding, normalized, existing_profile(user_id))
    signals = llm.run_task("profile-signal-extract", signal_input)

    draft = llm.run_task("profile-memory-synthesize", {
        "user": load_user(user_id),
        "onboarding": onboarding,
        "signalExtract": signals,
        "existingProfile": existing_profile(user_id),
    })

    review = llm.run_task("profile-risk-review", {
        "draft": draft,
        "evidenceRefs": draft["evidenceRefs"],
        "onboarding": onboarding,
    })

    final_draft = apply_risk_review(draft, review)
    save_profile_draft(job_id, final_draft)
    mark(job_id, "draft_ready", progress=100)
    return final_draft
```

---

## 13. 风险与取舍

### 13.1 OAuth 未开放

处理：

- 前端状态 `unavailable`。
- 提供跳过入口。
- 用 onboarding 生成临时画像。
- 等 OAuth 开放后，在个人画像页重新绑定并生成增强画像。

### 13.2 用户回答内容不可获取

处理：

- 不强推断写作风格。
- 使用问卷作为写作风格主来源。
- 提供手动粘贴代表回答入口。

### 13.3 Token 存储复杂

处理：

- P0 可本地内存或加密文件，开发机可跑。
- 正式部署建议数据库加密存储，或 Redis 短期会话存储。
- 前端不接触 token。

### 13.4 LLM 过度推断

处理：

- 所有画像字段必须有 evidenceRefs。
- 低置信度字段标注。
- 首次增强画像需用户确认。
- 后续只生成 MemoryUpdateRequest。

### 13.5 用户管理增加开发量

处理：

- 不新增 auth-service，先在 profile-service 内做 auth 子模块。
- 演示模式继续保留。
- 优先做 mock auth flow，再接真实 OAuth。

---

## 14. 建议优先级

### P0：前端入口重构，mock 用户状态

必须先做。否则后续 OAuth 和画像任务没有页面承载。

内容：

- 注册 / 登录 UI。
- 知乎关联提示页。
- 兴趣领域和写作风格页。
- 临时画像生成。
- 主应用入口 gating。

### P1：profile-service 用户与 onboarding 状态

让入口状态可恢复。

内容：

- register/login/me。
- onboarding 保存。
- provisional profile。

### P2：OAuth 绑定链路改造

让授权结果绑定真实用户。

内容：

- gateway authorize/callback。
- profile-service 保存 binding。
- adapter token exchange 和 `/zhihu/user`。

### P3：画像生成任务与 LLM 接入

让 OAuth 数据真正变成 Memory。

内容：

- enrichment job。
- OAuth snapshots。
- profile-signal-extract。
- profile-memory-synthesize。
- profile-risk-review。
- 用户确认应用。

### P4：用户回答内容增强

提升画像质量，但不阻塞主流程。

内容：

- authored content API，如开放则接。
- 否则支持用户手动粘贴代表回答。

---

## 15. 最小验收清单

1. 新用户打开页面先看到注册/登录，不直接进入主工作台。
2. 注册成功后进入知乎关联提示页。
3. OAuth 不可用时，用户能看到明确原因并选择稍后关联。
4. 用户能选择兴趣领域和写作风格。
5. 完成 onboarding 后立即生成临时画像。
6. 临时画像能进入今日看什么、写作苗圃的 Memory 注入。
7. 用户能在个人画像页看到知乎绑定状态、画像状态、数据来源。
8. OAuth 绑定成功后能触发画像增强 job。
9. job 进度能轮询展示。
10. 增强画像草稿带证据来源和置信度。
11. 用户确认后才写入长期 Memory。
12. 用户拒绝后长期 Memory 不变。
13. 若用户回答内容不可获取，系统不假装已经分析用户写作风格。
14. 前端不会接触 `access_token`。
15. gateway / profile / zhihu / llm 的日志能追踪一次画像生成全过程。
