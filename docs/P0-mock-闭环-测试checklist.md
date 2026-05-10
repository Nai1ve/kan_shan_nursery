# P0 Mock 闭环测试 Checklist

最后更新：2026-05-11

本 checklist 对应 v0.4 P0 mock 闭环。所有服务都已实现 mock 模式，前端可以只调用 `api-gateway` 跑完整 demo。

---

## 0. 准备

### 0.1 安装依赖（每个服务都需要）

```bash
cd services/<service-name>
python3 -m venv .venv && source .venv/bin/activate   # 可选：每服务独立 venv
pip install -r requirements.txt
```

或者一次性在仓库根目录安装：

```bash
for svc in api-gateway content-service feedback-service llm-service profile-service seed-service sprout-service writing-service zhihu-adapter; do
  pip install -r services/$svc/requirements.txt
done
```

### 0.2 一键启动 8 个后端服务

```bash
bash scripts/run_all_services.sh
```

- [ ] 控制台依次输出 `starting <service> on :<port>` 共 9 行（含 gateway）
- [ ] `output/service-logs/*.log` 全部生成，无 traceback
- [ ] `curl http://127.0.0.1:8000/health` 返回 200，`data.downstream` 中 8 个服务 `ready=true`

---

## 1. 单元测试（必须先全部通过）

```bash
for svc in api-gateway content-service feedback-service llm-service profile-service seed-service sprout-service writing-service zhihu-adapter; do
  echo "===== $svc ====="
  python3 -m unittest discover -s services/$svc/tests
done
```

期望计数：

- [ ] api-gateway：5 ok
- [ ] content-service：9 ok
- [ ] feedback-service：7 ok
- [ ] llm-service：4 ok
- [ ] profile-service：6 ok
- [ ] seed-service：5 ok
- [ ] sprout-service：9 ok
- [ ] writing-service：7 ok
- [ ] zhihu-adapter：7 ok
- [ ] **合计 59 ok，0 fail**

---

## 2. 健康检查

| 服务 | URL | 期望 |
|---|---|---|
| api-gateway | `curl http://127.0.0.1:8000/health` | `data.status=ok` 且 8 个 downstream `ready=true` |
| profile-service | `curl http://127.0.0.1:8010/health` | `{"status":"ok","service":"profile-service"}` |
| content-service | `curl http://127.0.0.1:8020/health` | `{"status":"ok","service":"content-service"}` |
| seed-service | `curl http://127.0.0.1:8030/health` | `{"status":"ok","service":"seed-service"}` |
| sprout-service | `curl http://127.0.0.1:8040/health` | `{"status":"ok","service":"sprout-service"}` |
| writing-service | `curl http://127.0.0.1:8050/health` | `{"status":"ok","service":"writing-service"}` |
| feedback-service | `curl http://127.0.0.1:8060/health` | `{"status":"ok","service":"feedback-service"}` |
| zhihu-adapter | `curl http://127.0.0.1:8070/health` | `{"status":"ok","service":"zhihu-adapter"}` |
| llm-service | `curl http://127.0.0.1:8080/health` | `{"status":"ok","service":"llm-service"}` |

- [ ] 9 个 `/health` 全部返回 200

---

## 3. 网关 Envelope / Request-Id

```bash
curl -i -H 'X-Request-Id: req-manual-001' http://127.0.0.1:8000/api/v1/profile/me
```

- [ ] 响应头含 `X-Request-Id: req-manual-001`
- [ ] 响应体为 `{"request_id":"req-manual-001","data":{...},"meta":{"service":"profile"}}`
- [ ] 不带 `X-Request-Id` 时网关自动生成 `req-xxxxxxxxxxxx`

故意触发错误：

```bash
curl -i http://127.0.0.1:8000/api/v1/seeds/missing-seed
```

- [ ] 状态码 `404`
- [ ] 响应体形如 `{"request_id":"...","error":{"code":"DOWNSTREAM_ERROR","detail":{"service":"seed","downstreamStatus":404,...}}}`

降级模拟：

```bash
GATEWAY_READY_SERVICES=profile,seed bash scripts/run_all_services.sh
```

- [ ] 调 `/api/v1/content` 返回 503，`error.code=SERVICE_NOT_READY`，`error.detail.service=content`

---

## 4. P0 链路 1：今日看什么 → 加入种子库

```bash
# 4.1 拉 bootstrap（兴趣分类 + 卡片）
curl http://127.0.0.1:8000/api/v1/content
```

- [ ] `data.categories` 至少包含 `agent / ai-coding / rag / backend / growth / following / serendipity`
- [ ] `data.cards` ≥ 12 张
- [ ] 每张卡片含 `originalSources`（≥1 个）

```bash
# 4.2 按分类查询
curl 'http://127.0.0.1:8000/api/v1/content/cards?categoryId=ai-coding'
```

- [ ] 返回的卡片 `categoryId` 全部为 `ai-coding`
- [ ] **每个 interest 分类至少 2 张卡**（agent / ai-coding / rag / backend / growth）

```bash
# 4.3 来源全文
curl http://127.0.0.1:8000/api/v1/content/cards/ai-coding-moat
curl http://127.0.0.1:8000/api/v1/content/cards/ai-coding-moat/sources/source-ai-coding-4-hot
```

- [ ] 单卡接口返回完整字段（含 `relevanceScore`、`originalSources`）
- [ ] 单 source 接口返回 `fullContent`（多段文字）

```bash
# 4.4 刷新分类
curl -X POST http://127.0.0.1:8000/api/v1/content/categories/ai-coding/refresh
curl 'http://127.0.0.1:8000/api/v1/content/cards?categoryId=ai-coding'
```

- [ ] 第一次刷新 `refreshState.refreshCount=1`，`visibleCardIds` 出现 `-r1` 后缀
- [ ] 第二次刷新 `refreshCount=2`，卡片 id 改为 `-r2`，原 `-r1` 不再返回
- [ ] 刷新 ai-coding **不影响** seed / profile / writing 接口数据

```bash
# 4.5 卡片摘要刷新
curl -X POST -H 'Content-Type: application/json' \
  -d '{"focus":"失败模式"}' \
  http://127.0.0.1:8000/api/v1/content/cards/agent-quality/summarize
```

- [ ] 返回 `summary` 含 `[focus=失败模式]` 前缀
- [ ] `controversies` / `writingAngles` 非空

```bash
# 4.6 加入种子库（从卡片）
curl -X POST -H 'Content-Type: application/json' \
  -d '{"cardId":"ai-coding-moat","reaction":"agree","userNote":"测试笔记","card":{"id":"ai-coding-moat","categoryId":"ai-coding","title":"AI Coding 产品的壁垒到底在哪里？","contentSummary":"模型能力、入口、上下文","controversies":["反方"],"writingAngles":["护城河可能不在会写代码"],"originalSources":[]}}' \
  http://127.0.0.1:8000/api/v1/seeds/from-card
```

- [ ] 返回 `data.id` 以 `seed-` 开头
- [ ] `data.userReaction=agree`、`data.userNote=测试笔记`
- [ ] `data.maturityScore` 为数字
- [ ] `data.status` ∈ `{water_needed, sproutable}`
- [ ] 第二次相同 `cardId` 调用：返回同一个 `id`（去重逻辑）

```bash
# 4.7 列种子库
curl http://127.0.0.1:8000/api/v1/seeds
```

- [ ] 包含上一步创建的 seed id

---

## 5. P0 链路 2：浇水 / 提问 / 合并

> 用 4.6 返回的 `seed_id` 替换下面的 `<SID>`

```bash
# 5.1 提问
curl -X POST -H 'Content-Type: application/json' \
  -d '{"question":"反方会怎么质疑这个结论？"}' \
  http://127.0.0.1:8000/api/v1/seeds/<SID>/questions
```

- [ ] 返回 seed 的 `questions[0].agentAnswer` 非空
- [ ] `wateringMaterials` 多了 `open_question` 和（`evidence` 或 `counterargument`）

```bash
# 5.2 标记问题已解决
curl -X PATCH -H 'Content-Type: application/json' \
  -d '{"status":"resolved"}' \
  http://127.0.0.1:8000/api/v1/seeds/<SID>/questions/<QID>
```

- [ ] `questions[0].status=resolved`
- [ ] 对应的 `open_question` 材料 `adopted=true`

```bash
# 5.3 添加 / 编辑 / 删除材料
curl -X POST -H 'Content-Type: application/json' \
  -d '{"type":"personal_experience","title":"项目经验","content":"我做金融数据同步时...","adopted":true}' \
  http://127.0.0.1:8000/api/v1/seeds/<SID>/materials
```

- [ ] 新增材料后 `maturityScore` 增大或不变
- [ ] PATCH `adopted=false` 后再 DELETE 不报错

```bash
# 5.4 Agent 补充
curl -X POST -H 'Content-Type: application/json' \
  -d '{"type":"counterargument"}' \
  http://127.0.0.1:8000/api/v1/seeds/<SID>/materials/agent-supplement
```

- [ ] 返回的 seed 中多一条 `counterargument` 材料、`sourceLabel` 含 "Agent"

---

## 6. P0 链路 3：今日发芽

```bash
# 6.1 用户主动触发
curl -X POST -H 'Content-Type: application/json' \
  -d '{"interestId":"ai-coding"}' \
  http://127.0.0.1:8000/api/v1/sprout/start
```

- [ ] 返回 `data.status=completed`、`data.cacheHit=false`、`data.opportunities[].interestId=ai-coding`
- [ ] 记下 `data.id`

```bash
# 6.2 同一 interest 再触发：命中缓存
curl -X POST -H 'Content-Type: application/json' \
  -d '{"interestId":"ai-coding"}' \
  http://127.0.0.1:8000/api/v1/sprout/start
```

- [ ] `data.cacheHit=true`，且 `data.id` 与 6.1 一致

```bash
# 6.3 拉发芽机会
curl 'http://127.0.0.1:8000/api/v1/sprout/opportunities?interest_id=ai-coding'
```

- [ ] 列表按 `score` 降序，全部 `interestId=ai-coding`

```bash
# 6.4 补充资料 / 换角度 / 暂时不写 / 开始写作
curl -X POST -H 'Content-Type: application/json' -d '{"material":"补充企业落地复盘"}' \
  http://127.0.0.1:8000/api/v1/sprout/opportunities/sprout-moat/supplement
curl -X POST -H 'Content-Type: application/json' -d '{"angle":"反方视角"}' \
  http://127.0.0.1:8000/api/v1/sprout/opportunities/sprout-moat/switch-angle
curl -X POST http://127.0.0.1:8000/api/v1/sprout/opportunities/sprout-moat/dismiss
curl -X POST http://127.0.0.1:8000/api/v1/sprout/opportunities/sprout-quality/start-writing
```

- [ ] supplement：opportunity `status=supplemented`，返回 `seedMaterial`（type=evidence）
- [ ] switch-angle：`status=angle_changed`，`activatedSeed` 不变（不改原始观点）
- [ ] dismiss：`status=dismissed`
- [ ] start-writing：返回 `writingHandoff.{seedId, interestId, coreClaim, suggestedTitle, suggestedAngle}`

---

## 7. P0 链路 4：写作苗圃 8 步

```bash
# 7.1 创建 session
curl -X POST -H 'Content-Type: application/json' \
  -d '{"seedId":"seed-ai-coding-moat","interestId":"ai-coding","coreClaim":"AI 编程工具的护城河可能不在会写代码","articleType":"工程复盘","tone":"balanced"}' \
  http://127.0.0.1:8000/api/v1/writing/sessions
```

- [ ] 返回 `data.draftStatus=claim_confirming`、`data.confirmed=false`
- [ ] `data.memoryOverride.interestId=ai-coding`，含 `writingReminder`
- [ ] 记下 `data.sessionId`

```bash
# 7.2 修改 memoryOverride（只影响当前 session）
curl -X PATCH -H 'Content-Type: application/json' \
  -d '{"memoryOverride":{"interestId":"ai-coding","interestName":"AI Coding","knowledgeLevel":"中级","preferredPerspective":["工程视角"],"evidencePreference":"案例优先","writingReminder":"session-only override"}}' \
  http://127.0.0.1:8000/api/v1/writing/sessions/<SESSION_ID>
```

- [ ] `memoryOverride.writingReminder=session-only override`
- [ ] 调 `GET /api/v1/memory/me` 全局 Memory **未变**（不污染 profile-service）

```bash
# 7.3 8 步状态机
curl -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:8000/api/v1/writing/sessions/<SID>/confirm-claim
curl -X POST http://127.0.0.1:8000/api/v1/writing/sessions/<SID>/blueprint
curl -X POST http://127.0.0.1:8000/api/v1/writing/sessions/<SID>/draft
curl -X POST http://127.0.0.1:8000/api/v1/writing/sessions/<SID>/roundtable
curl -X POST http://127.0.0.1:8000/api/v1/writing/sessions/<SID>/finalize
curl -X POST -H 'Content-Type: application/json' -d '{"title":"定稿测试"}' http://127.0.0.1:8000/api/v1/writing/sessions/<SID>/publish/mock
```

每一步对应的 `draftStatus`：

- [ ] confirm-claim → `confirmed=true`，`draftStatus=claim_confirming`
- [ ] blueprint → `blueprint_ready`，返回 `blueprint.arguments`（≥3 条）和 `responseStrategy`
- [ ] draft → `draft_ready`、`savedDraft=true`、`draft.outline` 4 条
- [ ] roundtable → `reviewing`，`review.reviewers` 3 个角色
- [ ] finalize → `finalized`，`finalized.publishingNotice` 提示不会自动发布
- [ ] publish/mock → `published`、`publishedArticle.publishMode=mock`、有 `feedbackHandoff`

错误用例：

- [ ] 在 `claim_confirming` 直接 POST blueprint：返回 409，`error.code=INVALID_TRANSITION`

---

## 8. P0 链路 5：历史反馈

```bash
curl http://127.0.0.1:8000/api/v1/feedback/articles
curl http://127.0.0.1:8000/api/v1/feedback/articles/article-moat
curl http://127.0.0.1:8000/api/v1/feedback/articles/article-moat/comments-summary
curl -X POST http://127.0.0.1:8000/api/v1/feedback/articles/article-moat/second-seed
curl -X POST http://127.0.0.1:8000/api/v1/feedback/articles/article-moat/memory-update-request
```

- [ ] 列表至少 2 篇文章，含 `metrics`
- [ ] 单文章详情含 `commentInsights[]`
- [ ] comments-summary 同时返回 `supportingViews` / `counterArguments` / `supplementaryMaterials` / `secondArticleAngles`
- [ ] second-seed 返回 `seedPayload`（不会自动写入 seed-service）
- [ ] memory-update-request 返回 `memoryUpdateRequest.status=pending`，`note` 强调"不自动写入 Memory"

二次确认 Memory 不被自动覆盖：

- [ ] 调用 second-seed 后，`GET /api/v1/seeds` 没有自动多出新种子
- [ ] 调用 memory-update-request 后，`GET /api/v1/memory/me` 全局 Memory **未变**
- [ ] 通过 `POST /api/v1/memory/update-requests/{request_id}/apply` 才会真正落地（profile-service 已支持）

---

## 9. Profile / Memory（已实现服务回归）

```bash
curl http://127.0.0.1:8000/api/v1/profile/me
curl http://127.0.0.1:8000/api/v1/profile/interests
curl http://127.0.0.1:8000/api/v1/memory/injection/ai-coding
curl 'http://127.0.0.1:8000/api/v1/memory/update-requests?status=pending'
```

- [ ] profile/me 返回 `nickname`、`interestMemories[]`
- [ ] interests 列表非空，元素含 `interestId`、`knowledgeLevel`
- [ ] memory/injection/ai-coding 返回可注入写作的 summary
- [ ] update-requests 列表可过滤 status

---

## 10. 边界 / 防呆

- [ ] `POST /api/v1/seeds`（缺 `cardId`）→ 400 `INVALID_REQUEST`
- [ ] `POST /api/v1/writing/sessions`（缺 `seedId`）→ 400 `INVALID_REQUEST`
- [ ] `POST /api/v1/writing/sessions`（`tone=loud`）→ 400 `INVALID_REQUEST`
- [ ] `GET /api/v1/content/cards/missing-id` → 404 `CARD_NOT_FOUND`
- [ ] `GET /api/v1/sprout/runs/missing` → 404 `RUN_NOT_FOUND`
- [ ] `POST /api/v1/sprout/opportunities/missing/dismiss` → 404 `OPPORTUNITY_NOT_FOUND`

---

## 11. 服务边界自检（Demo 评审用）

- [ ] 关掉 `zhihu-adapter`：网关 `/api/v1/content` 仍能返回（content-service 在 mock 模式不依赖 zhihu）
- [ ] 关掉 `llm-service`：网关 `/api/v1/seeds/from-card` 仍能返回（seed-service mock 不依赖 llm）
- [ ] 关掉 `profile-service`：网关 `/api/v1/profile/me` 返回 502 `DOWNSTREAM_UNAVAILABLE`
- [ ] 没有任何一条命令直接打到 `:8010-:8080` 的内部端口（前端只走 :8000）
- [ ] 没有 Token / 知乎接口凭证出现在响应体里

---

## 12. 验收口径（出问题时回看）

- [ ] 五条 P0 链路（今日看什么 / 加入种子库 / 浇水提问 / 今日发芽 / 写作苗圃 / 历史反馈）全部能跑通
- [ ] Memory 任何更新都需要 `apply` 才生效（feedback / writing 都不会自动覆盖）
- [ ] 昂贵动作（发芽 run、卡片 summarize、Agent 补充）只在用户主动触发时才发生
- [ ] 网关响应永远带 `request_id`（无论成功或失败）
- [ ] 关掉任意一个非主路径服务，链路降级而不是 500
