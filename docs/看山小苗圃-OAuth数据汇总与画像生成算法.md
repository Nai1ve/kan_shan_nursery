# 看山小苗圃-OAuth 数据汇总与画像生成算法

本文档只描述知乎 OAuth 数据采集、LLM 汇总画像、证据追踪、限流、隐私与画像合并策略。前端入口和用户管理见：`docs/看山小苗圃-前端入口与用户管理方案.md`。

---

## 1. 核心结论

画像生成不应该完全依赖确定性规则，也不应该把全部原始数据直接丢给 LLM。

推荐方案是混合流程：

```text
确定性预处理
→ LLM 总结整理
→ 规则校验与风险审查
→ 用户确认
→ 写入长期 Memory
```

其中：

- 确定性规则负责清洗、脱敏、去重、截断、来源标注、候选信号预筛和额度控制。
- LLM 负责总结、归纳、解释、生成 Memory 草稿。
- 规则校验负责防止隐私泄露、过度推断、无证据结论和覆盖用户显式偏好。

---

## 2. “确定性规则提取”是什么意思

这里的确定性规则不是指“用关键词规则替代 LLM 生成用户画像”。它指的是 LLM 前后的工程化控制步骤。

### 2.1 确定性规则适合做什么

适合做：

```text
1. 数据清洗：HTML 去标签、时间格式转换、空字段过滤。
2. 隐私脱敏：删除 email、phone_no 等不应进入 LLM 的字段。
3. 去重：重复标题、重复作者、重复动态去重。
4. 截断：每条 excerpt 控制长度，避免 token 爆炸。
5. 来源标注：每条信号保留 sourceType/sourceId/evidenceId。
6. 候选兴趣映射：把 “AI 编程”“代码生成”“Copilot” 初步映射到 AI Coding。
7. 置信度初值：用户主动填写 > 用户回答 > 关注动态 > 关注列表 > 粉丝列表。
8. 输入预算控制：每类来源最多取多少条。
9. 输出校验：LLM 生成的每条 Memory 必须有 evidenceRefs。
```

### 2.2 确定性规则不适合做什么

不适合做：

```text
1. 判断用户真正相信什么。
2. 归纳复杂写作风格。
3. 解释用户为什么关注某类内容。
4. 生成自然语言 Memory。
5. 处理反讽、语境、跨领域类比。
6. 从弱信号中推断稳定偏好。
```

这些更适合交给 LLM 做总结整理。

### 2.3 为什么不能直接全丢给 LLM

原因：

- 成本不可控：关注列表、动态和回答内容可能很长。
- 隐私风险：原始 OAuth 返回里可能有邮箱、手机号等字段。
- 幻觉风险：LLM 容易把关注对象的观点误当成用户观点。
- 可解释性差：没有 evidenceId，用户无法知道画像依据。
- 不稳定：同一批数据多次输入可能产出差异较大。

所以更好的结构是：规则先把输入整理成“干净、有来源、可控长度”的信号包，再让 LLM 总结。

---

## 3. LLM 使用策略

### 3.1 Provider 优先级

用户需要能配置自己的 LLM。平台只能提供有限免费接口，必须限流。

LLM 路由优先级：

```text
1. 用户自有 LLM provider
   - 用户已配置
   - provider 测试通过
   - 任务在 enabledTasks 中
   - 未超过用户自设预算/频率

2. 平台免费 provider
   - 默认可用
   - 受平台每日额度、每分钟频率、任务级额度限制
   - 超限后不再调用

3. 降级 provider
   - mock/template
   - 只生成最低限度结果
   - 明确标记 fallback=true
```

### 3.2 平台免费接口限流

平台免费接口可以使用知乎直答 Agent 或其他免费额度，但必须按用户和任务限流。

建议 Redis key：

```text
quota:llm:platform:{task_type}:{user_id}:{yyyyMMdd}
quota:llm:platform:global:{task_type}:{yyyyMMdd}
rate:llm:platform:{user_id}:{minute}
rate:llm:platform:global:{minute}
```

建议 P0 默认额度，可按实际接口额度调整：

| 任务 | 单用户每日 | 全局每日 | 说明 |
| --- | ---: | ---: | --- |
| `profile-signal-summarize` | 3 | 50 | 画像信号总结 |
| `profile-memory-synthesize` | 3 | 50 | 生成画像草稿 |
| `profile-risk-review` | 5 | 80 | 风险审查较短 |
| `summarize-content` | 30 | 500 | 内容摘要 |
| `answer-seed-question` | 20 | 300 | 疑问回答 |
| `supplement-material` | 20 | 300 | 补证据/找反方 |
| `argument-blueprint` | 10 | 150 | 写作蓝图 |
| `draft` | 5 | 80 | 初稿生成，成本最高 |
| `roundtable-review` | 5 | 80 | 多 persona，成本高 |

规则：

```text
缓存命中不扣额度。
provider 失败不扣额度。
schema 校验失败不扣额度，但记录失败次数。
调用成功才增加 quota。
超限返回 LLM_QUOTA_EXCEEDED。
```

### 3.3 用户自有 LLM 限流

即便用户配置自己的 LLM，平台也要做基础频率保护，避免拖垮服务。

建议 Redis key：

```text
quota:llm:user_provider:{provider_id}:{task_type}:{user_id}:{yyyyMMdd}
rate:llm:user_provider:{provider_id}:{user_id}:{minute}
```

用户自有 LLM 可以配置：

```ts
UserLlmProviderConfig {
  dailyCallLimit?: number;
  rpmLimit?: number;
  dailyBudgetCents?: number;
}
```

平台默认保护：

```text
每用户每分钟最多 20 次 LLM task
每个写作 draft 任务最多同时 1 个进行中
profile enrichment job 每用户每日最多 3 次
```

---

## 4. OAuth 输入来源

当前 `docs/知乎API.md` 明确可用的 OAuth 能力：

| 来源 | 接口 | 用途 | 信号强度 |
| --- | --- | --- | --- |
| 用户基本信息 | `GET /user` | 昵称、简介、headline | 高 |
| 关注列表 | `GET /user/followed` | 长期信息源偏好 | 中 |
| 粉丝列表 | `GET /user/followers` | 潜在读者画像 | 中低 |
| 关注动态 | `GET /user/moments` | 最近阅读和互动输入 | 中高 |

用户回答内容是强信号，但当前文档里没有稳定的“获取当前用户全部回答/文章”接口。因此 P0 降级策略：

1. 如果后续开放 authored content API，优先接入。
2. 如果 `/user/moments` 能识别当前用户自己的回答/文章，抽取为用户创作样本。
3. 支持用户手动粘贴 1-3 篇代表回答或文章。
4. 用知乎搜索昵称 + 兴趣关键词只能作为低置信度补充，不直接写入长期 Memory。

---

## 5. 数据采集上限

为控制成本和接口压力，P0 建议：

```text
user info: 1 次
followed: page 0-2, per_page 20, 最多 60 人
followers: page 0-2, per_page 20, 最多 60 人
moments: 默认返回条数，最多 50 条
authored content samples: 最多 20 条
manual content samples: 最多 3 条
```

Redis 缓存：

```text
zhihu:user:{user_id}: 30 分钟
zhihu:user_followed:{user_id}:{page}:{per_page}: 30 分钟
zhihu:user_followers:{user_id}:{page}:{per_page}: 30 分钟
zhihu:user_moments:{user_id}: 10 分钟
profile_enrichment_snapshot:{user_id}:{snapshot_hash}: 6 小时
```

---

## 6. 数据清洗与标准化

进入 LLM 前先生成标准化信号：

```ts
ProfileSignalSourceItem {
  evidenceId: string;
  sourceType:
    | "onboarding"
    | "zhihu_user"
    | "followed"
    | "followers"
    | "moments"
    | "authored_content"
    | "manual_content";
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

清洗规则：

```text
1. 删除 email、phone_no。
2. HTML 去标签。
3. excerpt 截断到 160-240 字。
4. title + author + action_time 相同视为重复。
5. 相同作者过多时限采样，避免单一作者支配画像。
6. 每条信号生成 evidenceId。
7. 所有信号保留 sourceType，供 LLM 区分信号强弱。
```

---

## 7. 预筛候选信号

预筛不是最终画像判断，只是为 LLM 准备更好的输入。

### 7.1 信号权重初值

```text
onboarding interests: 1.00
manual authored content: 0.95
authored content API: 0.90
zhihu user headline/description: 0.75
following moments: 0.65
followed user headline/description: 0.45
followers headline/description: 0.30
```

### 7.2 时间衰减

```text
recencyWeight =
  1.0  if 7 天内
  0.85 if 30 天内
  0.65 if 90 天内
  0.45 otherwise
```

### 7.3 候选主题分数

```text
topicCandidateScore =
  sourceWeight
  * recencyWeight
  * textMatchScore
  * diversityBoost
```

其中：

- `textMatchScore` 可以用关键词、同义词表、兴趣标签映射得到。
- `diversityBoost` 防止所有候选都来自同一个来源或作者。
- 这里只用于排序 LLM 输入，不用于最终写入 Memory。

---

## 8. LLM 画像生成任务

### 8.1 profile-signal-summarize

用途：让 LLM 从标准化信号中总结用户兴趣、阅读偏好、受众线索和不确定项。

输入：

```ts
ProfileSignalSummarizeInput {
  onboarding: OnboardingProfile;
  signalItems: ProfileSignalSourceItem[];
  existingProfile?: ProfileData;
}
```

输出：

```ts
ProfileSignalSummarizeOutput {
  topicCandidates: {
    topic: string;
    matchedInterestId?: string;
    confidence: number;
    evidenceIds: string[];
    reason: string;
  }[];
  readingPreference: {
    summary: string;
    evidenceIds: string[];
  };
  writingStyleSignals: {
    summary: string;
    confidence: number;
    evidenceIds: string[];
    limitation: string;
  };
  audienceInsights: {
    audienceLabel: string;
    confidence: number;
    evidenceIds: string[];
  }[];
  insufficientData: string[];
}
```

Prompt 约束：

```text
- 只输出 JSON。
- 所有结论必须引用 evidenceIds。
- 不要用邮箱、手机号、性别生成画像。
- 不要把关注对象的观点直接当成用户观点。
- 如果没有用户回答样本，必须声明“写作风格主要来自问卷而非历史回答”。
```

### 8.2 profile-memory-synthesize

用途：把信号总结转为 `ProfileData` 和 `MemorySummary[]`。

输入：

```ts
ProfileMemorySynthesizeInput {
  user: CurrentUser;
  onboarding: OnboardingProfile;
  signalSummary: ProfileSignalSummarizeOutput;
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
  suggestedNewInterests: string[];
  confidence: number;
  evidenceRefs: MemoryEvidenceRef[];
  warnings: string[];
}
```

生成规则：

- `longTermBackground` 只写用户明确填写或知乎简介支持的信息。
- `contentPreference` 可以综合关注流、关注列表和主动兴趣。
- `writingStyle` 以问卷和用户创作样本为主。
- `recommendationStrategy` 要说明兴趣小类、关注流、偶遇输入如何配合。
- `riskReminder` 要指出容易过度抽象、缺少个人经验、证据不足、AI 味过重等风险。

### 8.3 profile-risk-review

用途：审查画像草稿是否可应用。

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

- `safeToApply=false` 时，只能生成待确认草稿。
- 首次增强画像即使 safe，也建议让用户确认。
- 后续重新生成必须走 MemoryUpdateRequest。

---

## 9. 画像合并策略

来源优先级：

```text
用户显式填写
> 用户手动编辑 Memory
> 用户回答/文章样本
> 用户基本信息
> 关注动态
> 关注列表
> 粉丝列表
```

合并规则：

1. 用户主动选择的兴趣不能被 OAuth 分析删除。
2. 用户主动填写的 `avoidances` 不能被 LLM 覆盖。
3. 用户手动编辑过的 Memory 字段只能生成更新建议。
4. OAuth 新发现兴趣如果置信度低于 0.65，只作为候选，不直接写入长期 Memory。
5. 粉丝列表只能用于“潜在读者画像”，不能推断用户自己的立场。
6. 关注列表只能用于“阅读偏好/信息源”，不能推断用户自己的观点。

画像状态：

```text
provisional: 仅由 onboarding 生成，可立即使用
enriched_draft: OAuth + LLM 生成，等待用户确认
enriched_applied: 用户确认后应用
stale: OAuth 数据超过有效期，建议重新同步
```

---

## 10. LLM Router 任务执行流程

```text
业务服务请求 llm-service task
↓
llm-service 检查用户 LLM 配置
↓
如果用户 provider 可用：走用户 provider
↓
否则检查平台免费额度
↓
平台额度可用：走 platform_free provider
↓
平台额度不可用：返回 LLM_QUOTA_EXCEEDED 或 fallback template
↓
输出 schema 校验
↓
写 trace + quota
```

trace 必须记录：

```json
{
  "taskType": "profile-memory-synthesize",
  "userId": "user_xxx",
  "providerSource": "user_provider | platform_free | fallback",
  "providerId": "...",
  "cacheHit": false,
  "quotaCharged": true,
  "latencyMs": 1234,
  "fallback": false,
  "inputHash": "...",
  "schemaVersion": "v1"
}
```

---

## 11. 用户回答内容方案

### 11.1 如果知乎开放 authored content API

优先接：

```text
GET /user/answers 或官方等价接口
GET /user/articles 或官方等价接口
```

采集字段：

- 标题
- 摘要
- 发布时间
- 互动数据
- 话题标签
- 评论摘要

### 11.2 如果没有 authored content API

降级策略：

| 策略 | 置信度 | 说明 |
| --- | --- | --- |
| 用户手动粘贴代表回答 | 高 | 最稳，适合 onboarding 增强项 |
| moments 中识别当前用户行为 | 中 | 如果动态包含当前用户自己的回答行为 |
| 知乎搜索昵称 + 兴趣关键词 | 低 | 可能误召回同名用户，必须低置信度 |
| 暂不分析历史写作风格 | 安全 | 用问卷生成写作风格 |

P0 建议先做“手动粘贴代表回答/文章”，成本低、可靠性高。

---

## 12. Enrichment Job 伪代码

```python
def run_profile_enrichment_job(job_id):
    job = mark(job_id, "collecting_oauth_data", progress=10)
    user_id = job.user_id

    onboarding = load_onboarding(user_id)
    llm_policy = load_user_llm_policy(user_id)

    snapshots = [snapshot("onboarding", sanitize_onboarding(onboarding))]

    if has_zhihu_binding(user_id):
        snapshots.append(fetch_zhihu_user(user_id))
        snapshots.extend(fetch_followed_pages(user_id, max_pages=3, per_page=20))
        snapshots.extend(fetch_followers_pages(user_id, max_pages=3, per_page=20))
        snapshots.append(fetch_following_moments(user_id))
        snapshots.extend(fetch_authored_content_if_available(user_id))

    snapshots.extend(load_manual_content_samples(user_id))

    normalized = normalize_redact_deduplicate(snapshots)
    candidates = deterministic_preselect(normalized, onboarding)

    mark(job_id, "analyzing", progress=45)

    signal_summary = llm.run_task(
        user_id=user_id,
        task_type="profile-signal-summarize",
        input_data={"onboarding": onboarding, "signalItems": candidates},
        policy=llm_policy,
    )

    draft = llm.run_task(
        user_id=user_id,
        task_type="profile-memory-synthesize",
        input_data={"onboarding": onboarding, "signalSummary": signal_summary},
        policy=llm_policy,
    )

    review = llm.run_task(
        user_id=user_id,
        task_type="profile-risk-review",
        input_data={"draft": draft, "evidenceRefs": draft["evidenceRefs"]},
        policy=llm_policy,
    )

    final_draft = apply_review_constraints(draft, review)
    save_profile_draft(job_id, final_draft)
    mark(job_id, "draft_ready", progress=100)
    return final_draft
```

---

## 13. 验收清单

1. 未配置用户 LLM 时，平台免费接口可用但受限流控制。
2. 平台免费额度超限后返回明确错误。
3. 用户自有 LLM 配置后，画像生成优先走用户 provider。
4. API Key 不出现在前端和日志。
5. OAuth 数据进入 LLM 前已脱敏。
6. LLM 输入带 evidenceId 和 sourceType。
7. LLM 输出每条 Memory 都能追溯 evidenceRefs。
8. 没有用户回答样本时，不强推断历史写作风格。
9. 关注列表不被当成用户立场。
10. 粉丝列表只用于受众洞察。
11. 低置信度兴趣只作为候选，不直接写长期 Memory。
12. 用户确认前不覆盖长期 Memory。
13. trace 能记录 providerSource、quotaCharged、cacheHit、fallback。
