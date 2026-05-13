# 看山小苗圃-Agent 体系设计

> 2026-05-13 流程校准：24 小时冲刺阶段以 `docs/看山小苗圃-核心流程校准方案.md` 为准。本文档保留为 Agent 任务边界和后续细化参考。

本文档定义系统内所有 Agent 的职责、调用方式、输入输出契约、落库边界和安全约束。

看山小苗圃里的 Agent 不是无限自主行动体，而是：

```text
明确任务入口
+ 明确输入上下文
+ 明确 JSON 输出
+ 明确用户确认点
```

核心原则：

1. Agent 只辅助理解、求证、组织和表达，不替用户决定立场。
2. 所有模型调用统一经过 `llm-service`。
3. 所有 Agent 输出必须经过 schema 校验和业务服务二次解释。
4. 发布、评论、点赞等社区动作必须由用户显式触发。

---

## 1. 总体架构

```text
frontend
  ↓
api-gateway
  ↓
business services
  ↓
llm-service
  ↓
provider router
  ├─ mock
  ├─ zhihu_direct
  └─ openai_compat
```

业务服务只调用：

```text
POST /llm/tasks/{task_type}
```

不直接调用模型供应商，不直接拼接最终 prompt。

---

## 2. Agent 分层

| 层级 | 目标 | 典型 Agent |
| --- | --- | --- |
| 输入理解层 | 看懂来源、提炼信息 | 内容理解、观点拆解、选题编辑 |
| 观点培养层 | 处理种子、疑问、材料 | 疑问求证、浇水材料、相似种子合并 |
| 发芽判断层 | 判断今天是否值得写 | 发芽机会、换角度 |
| 写作表达层 | 组织论证、生成草稿、审稿 | 论证结构、初稿编辑、圆桌审稿 |
| 画像反馈层 | 生成 Memory 建议和反馈摘要 | OAuth 画像分析、反馈分析、Memory 建议 |

---

## 3. llm-service 通用契约

请求：

```json
{
  "taskType": "summarize-content",
  "input": {},
  "promptVersion": "v1",
  "schemaVersion": "v1"
}
```

响应：

```json
{
  "taskType": "summarize-content",
  "schemaVersion": "v1",
  "output": {},
  "fallback": false,
  "routeMeta": {
    "mode": "single",
    "provider": "openai_compat",
    "fallback": false
  },
  "subCalls": [],
  "cache": {
    "hit": false,
    "key": "llm:...",
    "ttlSeconds": 21600
  }
}
```

统一缓存键：

```text
llm:{task_type}:{input_hash}:{prompt_version}:{schema_version}
```

输出校验失败：

```text
llm-service 返回 LLM_OUTPUT_SCHEMA_INVALID
业务服务可选择 fallback mock 或降级规则输出
```

---

## 4. Provider 策略

### 4.1 provider 类型

| Provider | 用途 | 说明 |
| --- | --- | --- |
| `mock` | 离线开发、兜底 | 永远可用 |
| `zhihu_direct` | 知乎直答 Agent | 通过 zhihu-adapter 调 `developer.zhihu.com/v1/chat/completions` |
| `openai_compat` | 用户自配 LLM | 用户可配置 Base URL / Model / API Key |

### 4.2 路由原则

```text
轻量任务 → 平台免费额度或 mock
高价值任务 → 用户自配 LLM 优先
圆桌审稿 → multi_persona 并发
失败 → 单任务 fallback，不影响业务状态机
```

### 4.3 用户自配 LLM

用户管理页允许配置自己的 LLM。

约束：

- API Key 只提交后端加密保存。
- 前端不保存明文。
- 平台免费额度必须限流。
- 高成本任务应由用户显式触发。

---

## 5. Agent 清单

### 5.1 内容理解 Agent

```text
task_type: summarize-content
owner: content-service
prompt: services/llm-service/prompts/v1/summarize-content.md
```

调用场景：

- 用户点击“总结一下”。
- content-service 生成 WorthReadingCard 后做 enrichment。

输入：

```json
{
  "cardTitle": "...",
  "sources": [
    {
      "sourceId": "...",
      "sourceType": "zhihu_search",
      "title": "...",
      "author": "...",
      "summary": "...",
      "fullContent": "..."
    }
  ],
  "memory": {
    "interestName": "...",
    "preferredPerspective": [],
    "evidencePreference": "..."
  }
}
```

输出：

```json
{
  "summary": "这组内容主要讨论...",
  "keyPoints": ["...", "..."],
  "sourceIds": ["src-1", "src-2"],
  "nextAction": "可以提炼争议点"
}
```

业务落点：

```text
WorthReadingCard.contentSummary
WorthReadingCard.recommendationReason
```

约束：

- 不编造来源。
- 不生成完整文章。
- 不替用户表态。

---

### 5.2 观点拆解 Agent

```text
task_type: extract-controversies
owner: content-service / seed-service
prompt: extract-controversies.md
```

调用场景：

- 生成今日看什么卡片。
- 从卡片创建观点种子。
- 继续浇水时寻找反方质疑。

输出：

```json
{
  "controversies": [
    {
      "claim": "AI Coding 降低实现门槛",
      "opposition": "但可能削弱基本功训练",
      "whyItMatters": "决定用户写作时应讨论工具效率还是能力结构"
    }
  ]
}
```

业务落点：

```text
WorthReadingCard.controversies
IdeaSeed.counterArguments
WateringMaterial(type=counterargument)
```

---

### 5.3 选题编辑 Agent

```text
task_type: generate-writing-angles
owner: content-service / writing-service / sprout-service
prompt: generate-writing-angles.md
```

调用场景：

- 卡片 enrichment 生成可写角度。
- 今日发芽“换个角度”。
- 种子库“基于它写一篇”。

输出：

```json
{
  "angles": [
    {
      "title": "AI 时代，程序员真正需要训练的是什么？",
      "angle": "从机械刷题转向问题建模和工程判断",
      "fitScore": 86
    }
  ]
}
```

约束：

- 角度必须来自来源和种子，不凭空造热点。
- `fitScore` 只是辅助排序，最终写作仍由用户选择。

---

### 5.4 疑问求证 Agent

```text
task_type: answer-seed-question
owner: seed-service
prompt: answer-seed-question.md
```

调用场景：

- 今日看什么卡片点击“有疑问”。
- 四格材料板里的待解决问题继续追问。

输入：

```json
{
  "seed": {},
  "question": "这个判断的反方证据是什么？",
  "questionThread": [],
  "sources": [],
  "materials": []
}
```

输出：

```json
{
  "answer": "...",
  "statusRecommendation": "resolved | needs_material",
  "materials": [
    {
      "type": "evidence",
      "title": "...",
      "content": "...",
      "sourceLabel": "..."
    }
  ],
  "followUpQuestions": ["..."]
}
```

业务落点：

```text
SeedQuestion.agentAnswer
WateringMaterial(type=open_question)
WateringMaterial(type=evidence/counterargument)
maturityScore 重新计算
```

用户动作：

```text
标记已解决 → SeedQuestion.status = resolved，线程结束
仍需补材料 → SeedQuestion.status = needs_material，可继续追问
```

约束：

- 引用来源必须来自输入 sourceIds。
- 不足时必须明确 `needs_material`。

---

### 5.5 浇水材料 Agent

```text
task_type: supplement-material
owner: seed-service / sprout-service
prompt: supplement-material.md
```

调用场景：

- 四格材料板点击“Agent 补证据”。
- 四格材料板点击“Agent 找反方”。
- 今日发芽点击“补充资料”。

输入：

```json
{
  "seed": {},
  "materialType": "evidence | counterargument",
  "existingMaterials": [],
  "sources": [],
  "questionContext": "..."
}
```

输出：

```json
{
  "material": {
    "type": "evidence",
    "title": "可补充的事实证据",
    "content": "...",
    "sourceLabel": "知乎搜索 / 全网搜索",
    "sourceIds": [],
    "adopted": false
  }
}
```

业务落点：

```text
WateringMaterial
IdeaSeed.maturityScore
IdeaSeed.status
```

约束：

- 只能补 `evidence` 或 `counterargument`，个人经验必须由用户提供。
- 不得编造数据。

---

### 5.6 发芽机会 Agent

```text
task_type: sprout-opportunities
owner: sprout-service
prompt: sprout-opportunities.md
```

调用场景：

- 用户点击“开始今日发芽”。
- 内容刷新后异步预生成机会。

输入：

```json
{
  "seed": {},
  "seedMaterials": [],
  "questions": [],
  "memory": {},
  "triggerTopics": [],
  "deterministicScores": {}
}
```

输出：

```json
{
  "opportunities": [
    {
      "seedId": "...",
      "triggerTopic": "...",
      "whyWorthWriting": "...",
      "suggestedTitle": "...",
      "suggestedAngle": "...",
      "suggestedMaterials": "...",
      "fitScore": 86,
      "materialGaps": [],
      "riskWarnings": []
    }
  ]
}
```

业务落点：

```text
SproutOpportunity
sprout_runs
sprout_opportunities
```

约束：

- 必须解释“为什么现在值得写”。
- 不允许推荐缺少材料且风险很高的种子直接写。

---

### 5.7 论证结构 Agent

```text
task_type: argument-blueprint
owner: writing-service
prompt: argument-blueprint.md
```

调用场景：

- 写作苗圃确认核心观点后，生成论证蓝图。

输入：

```json
{
  "seed": {},
  "materials": [],
  "questions": [],
  "memory": {},
  "articleType": "deep_analysis | experience_review | zhihu_answer | opinion_commentary"
}
```

输出：

```json
{
  "coreClaim": "...",
  "outline": [
    {
      "section": "为什么这个问题现在值得讨论",
      "points": []
    }
  ],
  "counterResponses": [],
  "memoryInjected": {
    "interestName": "...",
    "visibleSummary": "..."
  }
}
```

约束：

- 观点来自用户或种子。
- 结构可以辅助，但不能替用户决定立场。

---

### 5.8 初稿编辑 Agent

```text
task_type: draft
owner: writing-service
prompt: draft.md
```

调用场景：

- 用户确认论证蓝图后生成初稿。

输出：

```json
{
  "title": "...",
  "body": "...",
  "aiDisclosureSuggestion": "建议在发布时标注 AI 辅助整理。"
}
```

约束：

- 不冒充用户经历。
- 如果缺个人经验，必须用占位提示用户补充，而不是编造。
- 必须保留 AI 辅助声明建议。

---

### 5.9 圆桌审稿 Agent

```text
task_type: roundtable-review
owner: writing-service
mode: multi_persona
prompt: roundtable-review.md + personas/*
```

包含四个 reviewer：

| Persona | 职责 |
| --- | --- |
| `logic_reviewer` | 检查论证跳跃、概念偷换、未证明前提 |
| `human_editor` | 检查 AI 味、缺少个人经验、缺少真实细节 |
| `opponent_reader` | 从反方读者视角攻击漏洞 |
| `community_editor` | 检查标题、开头、知乎语境和 AI 声明风险 |

执行方式：

```text
4 个 persona 并发调用
任一 persona 失败 → 单 persona fallback mock
聚合 reviews[]，按 severity 排序
```

输出：

```json
{
  "reviews": [
    {
      "role": "logic_reviewer",
      "summary": "...",
      "problems": [],
      "suggestions": [],
      "severity": "high | medium | low"
    }
  ]
}
```

业务落点：

```text
WritingSession.adoptedSuggestions
前端圆桌审稿会
```

---

### 5.10 反馈分析 Agent

```text
task_type: feedback-summary
owner: feedback-service
prompt: feedback-summary.md
```

调用场景：

- 历史反馈页同步评论、点赞、收藏后。

输入：

```json
{
  "article": {},
  "metrics": {},
  "comments": [],
  "seed": {},
  "memory": {}
}
```

输出：

```json
{
  "summary": "...",
  "signals": [
    {
      "type": "reader_confusion | resonance | disagreement | request_more",
      "content": "..."
    }
  ],
  "secondArticleIdeas": []
}
```

业务落点：

```text
FeedbackArticle.commentInsights
二次文章种子 payload
MemoryUpdateRequest 候选
```

约束：

- 不直接写长期 Memory。
- 只生成可审阅建议。

---

### 5.11 OAuth 画像分析 Agent

```text
task_type: profile-memory-synthesis
owner: profile-service
prompt: 后续新增
```

调用场景：

- 用户关联知乎账号后，后台汇总用户信息、粉丝、关注列表、关注动态。

输入：

```json
{
  "explicitProfile": {},
  "zhihuUserInfo": {},
  "followingUsers": [],
  "followers": [],
  "followingFeedSamples": [],
  "publicContentSamples": []
}
```

输出：

```json
{
  "globalMemoryDraft": {},
  "interestMemoryDrafts": [],
  "confidence": 0.82,
  "evidence": [
    {
      "field": "contentPreference",
      "reason": "关注流中高频出现工程经验复盘和 AI 工具讨论"
    }
  ],
  "updateRequests": []
}
```

业务落点：

```text
MemoryUpdateRequest
ProfileData provisional/enhanced state
```

约束：

- LLM 总结更合适，但必须带 evidence 和 confidence。
- 用户确认前不覆盖长期 Memory。

---

## 6. 编排流程

### 6.1 今日看什么

```text
content-service 聚合来源
→ summarize-content
→ extract-controversies
→ generate-writing-angles
→ WorthReadingCard
```

并发策略：

```text
同一张卡片的三个任务可以串行或并发。
P0 建议串行：summary → controversies/angles。
只 enrichment 每分类 Top 5，避免额度浪费。
```

### 6.2 有疑问

```text
seed-service 创建 question
→ answer-seed-question
→ 写入 question + materials
→ 用户标记 resolved / needs_material
```

### 6.3 继续浇水

```text
用户点击 Agent 补证据 / 找反方
→ supplement-material
→ seed-service 写 WateringMaterial
→ 重新计算 maturityScore
```

### 6.4 今日发芽

```text
sprout-service 规则评分 TopK
→ sprout-opportunities
→ SproutOpportunity
→ 用户补充资料 / 换角度 / 开始写作
```

### 6.5 写作苗圃

```text
argument-blueprint
→ draft
→ roundtable-review
→ final draft
```

---

## 7. 统一安全约束

所有 Agent 必须遵守：

1. 不生成自动发布动作。
2. 不批量评论、点赞、发布。
3. 不伪造个人经历。
4. 不伪造引用来源。
5. 高风险话题必须提示证据不足或需人工确认。
6. 输出必须 JSON 化，业务服务不能解析自由文本来写状态。
7. 用户长期 Memory 的更新必须经用户确认。
8. AI 辅助写作必须保留声明建议。

---

## 8. 观测与调试

每次调用记录：

```json
{
  "taskType": "roundtable-review",
  "provider": "openai_compat",
  "fallback": false,
  "latencyMs": 820,
  "cacheHit": false,
  "inputHash": "...",
  "promptVersion": "v1",
  "schemaVersion": "v1",
  "subCalls": []
}
```

落点：

```text
output/llm-trace/YYYY-MM-DD.jsonl
```

前端不展示原始 trace，只展示必要状态：

```text
已使用 Memory
已调用 Agent
结果来自 mock / 平台免费 / 自有模型
是否 fallback
```

---

## 9. 开发验收

1. 每个 task mock 模式可用。
2. 每个 task 输出满足 schema。
3. `LLM_PROVIDER_MODE=mock` 时不访问外部网络。
4. `LLM_PROVIDER_MODE=zhihu` 时经 `zhihu-adapter` 调直答。
5. `LLM_PROVIDER_MODE=openai` 或默认 openai_compat 时需要用户配置。
6. provider 失败后 fallback 不破坏业务状态。
7. roundtable-review 返回 4 个 persona review。
8. 疑问求证可多轮追问，resolved 后线程结束。
9. 浇水材料 Agent 不生成个人经历。
10. 反馈分析不直接写 Memory，只生成建议。
