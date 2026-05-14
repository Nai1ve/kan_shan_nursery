# 看山小苗圃 - OAuth 画像生成实现记录

更新时间：2026-05-13

## 实现概述

实现了"看山小苗圃-高风险核心任务细化说明"中的 **任务 B: OAuth 画像生成最小闭环**。

### 目标

用户完成注册和知乎 OAuth 关联后，系统用两类信息生成画像：
- 用户主动填写的信息（onboarding）
- OAuth 授权获得的知乎信息（user/followed/followers/moments）

### 数据流

```text
用户注册 / 登录
→ 填写兴趣、写作偏好、基础资料
→ profile-service 保存临时画像
→ 用户关联知乎账号
→ profile-service 拉取 access_token
→ zhihu-adapter 获取 /user、/user/followed、/user/followers、/user/moments
→ profile-service 清洗为 ProfileSignalBundle
→ llm-service profile-memory-synthesis
→ profile-service 生成 memory_update_requests
→ 前端展示"待确认画像增强"
→ 用户确认 / 编辑 / 拒绝
→ 确认后写入 globalMemory 和 interestMemories
```

---

## 文件清单

### 后端（profile-service）

| 文件 | 操作 | 说明 |
|------|------|------|
| `services/profile-service/app/models.py` | 修改 | 添加 EnrichmentJobTable |
| `services/profile-service/app/enrichment/__init__.py` | 新建 | 模块初始化，导出核心类 |
| `services/profile-service/app/enrichment/models.py` | 新建 | ProfileSignalBundle、EnrichmentJob 数据结构 |
| `services/profile-service/app/enrichment/repository.py` | 新建 | EnrichmentRepository 抽象接口 |
| `services/profile-service/app/enrichment/memory_repository.py` | 新建 | 内存存储实现 |
| `services/profile-service/app/enrichment/pg_repository.py` | 新建 | PostgreSQL 存储实现 |
| `services/profile-service/app/enrichment/service.py` | 新建 | EnrichmentService 核心逻辑 |
| `services/profile-service/app/enrichment/transformer.py` | 新建 | LLM 输入输出转换 |
| `services/profile-service/app/enrichment/runner.py` | 新建 | 任务执行器（被 scheduler 调用） |
| `services/profile-service/app/main.py` | 修改 | 添加 enrichment job 端点 |
| `services/profile-service/app/scheduler.py` | 修改 | 添加 enrichment job 轮询任务 |

### API Gateway

| 文件 | 操作 | 说明 |
|------|------|------|
| `services/api-gateway/app/main.py` | 修改 | 添加 enrichment job 路由代理 |

### 前端

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/lib/types.ts` | 修改 | 添加 EnrichmentJob、MemoryUpdateRequest 类型 |
| `frontend/lib/api-client.ts` | 修改 | 添加 enrichment job API 函数 |
| `frontend/components/auth/ProfileGenerationPanel.tsx` | 修改 | 增强任务状态展示 |
| `frontend/components/kanshan-app.tsx` | 修改 | 集成真实的 memory update requests |

### 数据库

| 文件 | 操作 | 说明 |
|------|------|------|
| `infra/postgres/init.sql` | 修改 | 添加 enrichment_jobs 表 |

---

## 数据模型

### EnrichmentJobTable

```python
class EnrichmentJobTable(Base):
    __tablename__ = "enrichment_jobs"
    __table_args__ = {"schema": "profile"}

    job_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")  # queued|running|completed|failed|fallback
    trigger = Column(String, nullable=False, default="oauth_bound")
    include_sources = Column(Text, nullable=True)  # JSON array
    temporary_profile = Column(Text, nullable=True)  # JSON
    signal_counts = Column(Text, nullable=True)  # JSON
    memory_update_request_ids = Column(Text, nullable=True)  # JSON array
    error_message = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
```

### ProfileSignalBundle

```python
@dataclass
class ProfileSignalSourceItem:
    evidence_id: str
    source_type: str  # onboarding|zhihu_user|followed|followers|moments|manual_content
    source_id: str
    title: Optional[str] = None
    excerpt: Optional[str] = None
    author_name: Optional[str] = None
    headline: Optional[str] = None
    action_text: Optional[str] = None
    published_at: Optional[str] = None
    confidence_hint: float = 0.5

@dataclass
class ProfileSignalBundle:
    user_id: str
    generated_at: str
    onboarding: dict  # selectedInterestIds, writingStyleAnswers, selfDescription
    signals: list[ProfileSignalSourceItem]
```

### EnrichmentJob

```python
@dataclass
class EnrichmentJob:
    job_id: str
    user_id: str
    status: str = "queued"  # queued|running|completed|failed|fallback
    trigger: str = "oauth_bound"
    include_sources: list[str] = field(default_factory=lambda: ["zhihu_user", "followed", "followers", "moments"])
    temporary_profile: Optional[dict] = None
    signal_counts: dict = field(default_factory=dict)
    memory_update_request_ids: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
```

---

## API 端点

### 创建 Enrichment Job

```http
POST /profiles/me/enrichment-jobs
```

**请求体**：
```json
{
  "trigger": "oauth_bound",
  "includeSources": ["zhihu_user", "followed", "followers", "moments"]
}
```

**响应**：
```json
{
  "jobId": "enrich-abc123",
  "status": "queued",
  "temporaryProfileReady": true
}
```

### 查询最新 Enrichment Job

```http
GET /profiles/me/enrichment-jobs/latest
```

**响应**：
```json
{
  "jobId": "enrich-abc123",
  "status": "completed",
  "temporaryProfile": {},
  "signalCounts": {
    "zhihu_user": 1,
    "followed": 20,
    "followers": 15,
    "moments": 30
  },
  "memoryUpdateRequestIds": ["memreq-xxx", "memreq-yyy"],
  "errorMessage": null
}
```

### API Gateway 路由

```http
POST /api/v1/profile/enrichment-jobs → POST /profiles/me/enrichment-jobs
GET  /api/v1/profile/enrichment-jobs/latest → GET /profiles/me/enrichment-jobs/latest
```

---

## 核心逻辑

### EnrichmentService

核心类，职责：

1. **create_job(user_id, trigger, include_sources)** - 创建任务
2. **get_latest_job(user_id)** - 查询最新任务
3. **run_enrichment(job_id, access_token, profile, existing_memory, interest_catalog)** - 执行画像增强流程

### 执行流程

```python
async def run_enrichment(job_id, access_token, profile, existing_memory, interest_catalog):
    # 1. 更新状态为 running
    # 2. 收集 OAuth 信号
    oauth_signals = await _collect_oauth_signals(access_token, include_sources)

    # 3. 构建信号包
    bundle = _build_signal_bundle(user_id, profile, oauth_signals)

    # 4. 调用 LLM 合成
    llm_output = await _call_llm_synthesis(bundle, existing_memory, interest_catalog, profile)

    # 5. 生成 MemoryUpdateRequest
    requests = transform_llm_output_to_requests(llm_output, user_id, existing_memory)

    # 6. 保存请求
    request_ids = [await _save_memory_update_request(req) for req in requests]

    # 7. 更新状态为 completed
    job.status = "completed"
    job.memory_update_request_ids = request_ids
```

### Fallback 机制

- OAuth 数据获取失败 → 状态设为 `fallback`，使用临时画像
- LLM 调用失败 → 回退到基于规则的简单画像生成
- fallback 不影响用户正常使用

### 任务执行器（数据库轮询）

```python
class EnrichmentRunner:
    async def _poll_loop(self):
        while self._running:
            await self._process_queued_jobs()
            await asyncio.sleep(self._poll_interval)  # 默认 10 秒

    async def _process_queued_jobs(self):
        jobs = await self._repo.get_queued_jobs()
        for job in jobs:
            await self._execute_job(job.job_id)
```

---

## LLM 输入输出

### 输入格式

```json
{
  "taskType": "profile-memory-synthesis",
  "input": {
    "user": {
      "nickname": "用户昵称",
      "interests": ["数码科技", "职场教育"],
      "writingStyle": {},
      "selfDescription": "创作者"
    },
    "interactions": {
      "seedReactions": [],
      "questions": [],
      "writingHistory": [],
      "socialConnections": [],
      "contentInteractions": []
    },
    "currentMemory": {
      "globalMemory": {},
      "interestMemories": []
    }
  }
}
```

### 输出格式

```json
{
  "globalMemory": {
    "longTermBackground": "用户长期背景描述",
    "contentPreference": "内容偏好描述",
    "writingStyle": "写作风格描述",
    "recommendationStrategy": "推荐策略",
    "riskReminder": "风险提醒"
  },
  "interestMemories": [
    {
      "interestId": "shuma",
      "interestName": "数码科技",
      "knowledgeLevel": "中级",
      "preferredPerspective": ["AI工具", "编程实践"],
      "evidencePreference": "个人经验 + 案例",
      "writingReminder": "不要只讲参数和发布会",
      "feedbackSummary": ""
    }
  ]
}
```

---

## 前端集成

### 类型定义

```typescript
interface EnrichmentJob {
  jobId: string | null;
  status: "not_started" | "queued" | "running" | "completed" | "failed" | "fallback";
  temporaryProfile?: ProfileData;
  signalCounts?: Record<string, number>;
  memoryUpdateRequestIds?: string[];
  errorMessage?: string;
}

interface MemoryUpdateRequest {
  id: string;
  userId?: string;
  scope: "global" | "interest";
  interestId?: string;
  targetField: string;
  suggestedValue: string;
  reason: string;
  evidenceRefs?: string[];
  status: "pending" | "applied" | "rejected";
  createdAt: string;
}
```

### API 函数

```typescript
// 创建 enrichment job
export async function createEnrichmentJob(
  trigger: string = "oauth_bound",
  includeSources: string[] = ["zhihu_user", "followed", "followers", "moments"],
): Promise<{ jobId: string; status: string; temporaryProfileReady: boolean }>

// 查询最新 enrichment job
export async function getLatestEnrichmentJob(): Promise<EnrichmentJob>

// 查询 memory update requests
export async function getMemoryUpdateRequests(): Promise<MemoryUpdateRequest[]>

// 确认 memory update
export async function applyMemoryUpdate(requestId: string): Promise<void>

// 拒绝 memory update
export async function rejectMemoryUpdate(requestId: string): Promise<void>
```

### ProfileGenerationPanel 增强

- 轮询 `getLatestEnrichmentJob()` 获取任务状态
- 显示信号收集进度（signalCounts）
- 任务完成后显示待确认的 Memory 更新建议

### ProfileSection 集成

- 从 API 获取真实的 `memoryUpdateRequests`（替换 mock 数据）
- 实现 `applyMemoryRequest()` 和 `rejectMemoryRequest()` 调用 API
- 在 overview 面板显示 enrichment job 状态

---

## 测试验证

### 验收标准

1. ✅ 新用户不关联知乎，也能用主动填写信息生成临时画像
2. ✅ 关联知乎后能启动 enrichment job
3. ✅ OAuth 抓取失败时状态为 `fallback`，不影响使用
4. ✅ LLM 成功后生成待确认 Memory 更新，不直接覆盖
5. ✅ 用户确认后，`GET /profiles/me/interests` 能看到更新后的兴趣 Memory

### 测试场景

1. **场景 1：新用户注册**
   - 注册新用户
   - 完成 onboarding（选择兴趣、填写写作风格）
   - 验证临时画像已生成

2. **场景 2：关联知乎**
   - 绑定知乎账号
   - 观察 enrichment job 状态变化：queued → running → completed
   - 查看信号计数

3. **场景 3：OAuth 失败回退**
   - 模拟 OAuth 数据获取失败
   - 验证状态为 fallback
   - 验证用户仍可正常使用

4. **场景 4：确认 Memory 更新**
   - 查看待确认的 Memory 更新建议
   - 确认建议
   - 验证 Memory 已更新

5. **场景 5：拒绝 Memory 更新**
   - 查看待确认的 Memory 更新建议
   - 拒绝建议
   - 验证 Memory 未变更

---

## 依赖关系

```
profile-service
  ├── zhihu-adapter (OAuth 数据获取)
  ├── llm-service (画像合成)
  └── api-gateway (路由代理)
      └── frontend (用户界面)
```

---

## 环境变量

```bash
# profile-service
ZHIHU_ADAPTER_URL=http://127.0.0.1:8070
LLM_SERVICE_URL=http://127.0.0.1:8080
STORAGE_BACKEND=postgres  # 或 memory

# api-gateway
PROFILE_SERVICE_URL=http://127.0.0.1:8010
```

---

## 后续优化

1. **增量更新**：只更新变化的信号，避免重复处理
2. **并行获取**：OAuth 数据获取可以并行执行
3. **缓存优化**：缓存 LLM 输出，避免重复调用
4. **用户编辑**：支持用户在确认前编辑建议值
5. **版本管理**：记录 Memory 的变更历史
