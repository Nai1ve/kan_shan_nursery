#!/usr/bin/env bash
# 前端按钮联通验证脚本
# 通过 curl 模拟前端按钮点击，验证后端日志中出现对应事件。
set -euo pipefail

GW="http://127.0.0.1:8000"
LOG_DIR="output/logs"
DATE=$(date +%F)
PASS=0
FAIL=0

check() {
  local label="$1" method="$2" path="$3" event="$4" svc="$5" body="${6:-}"
  local log_file="${LOG_DIR}/${svc}-${DATE}.jsonl"

  if [[ "$method" == "POST" ]]; then
    if [[ -n "$body" ]]; then
      curl -s -X POST "${GW}${path}" -H 'Content-Type: application/json' -d "$body" >/dev/null 2>&1 || true
    else
      curl -s -X POST "${GW}${path}" -H 'Content-Type: application/json' -d '{}' >/dev/null 2>&1 || true
    fi
  else
    curl -s "${GW}${path}" >/dev/null 2>&1 || true
  fi

  sleep 0.3

  if [[ -f "$log_file" ]] && grep -q "\"event\": \"${event}\"" "$log_file" 2>/dev/null; then
    echo "  PASS  ${label} -> ${event}"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  ${label} -> ${event} (not found in ${log_file})"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== 前端按钮联通验证 ==="
echo ""

# 1. 注册
check "注册" POST "/api/v1/auth/register" "auth_register" "profile-service" '{"nickname":"test-user","password":"test123456","username":"testuser"}'

# 2. 登录
check "登录" POST "/api/v1/auth/login" "auth_login" "profile-service" '{"identifier":"testuser","password":"test123456"}'

# 3. 查询当前用户
check "查询当前用户" GET "/api/v1/auth/me" "auth_me" "profile-service"

# 4. 内容初始化
check "内容初始化" GET "/api/v1/content" "content_bootstrap" "content-service"

# 5. 刷新分类
check "刷新分类" POST "/api/v1/content/categories/agent/refresh" "content_category_refresh" "content-service"

# 6. 从卡片创建种子
check "从卡片创建种子" POST "/api/v1/seeds/from-card" "seed_from_card" "seed-service" '{"cardId":"ai-coding-moat","categoryId":"ai-coding","reaction":"agree"}'

# 7. 创建种子
check "创建种子" POST "/api/v1/seeds" "seed_create" "seed-service" '{"title":"测试种子","coreClaim":"测试主张"}'

# 8. 添加问题
SEED_ID=$(curl -s "${GW}/api/v1/seeds" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print(d['items'][0]['id'])" 2>/dev/null || echo "seed-1")
check "添加问题" POST "/api/v1/seeds/${SEED_ID}/questions" "seed_question_add" "seed-service" '{"question":"这是一个测试问题？"}'

# 9. 添加材料
check "添加材料" POST "/api/v1/seeds/${SEED_ID}/materials" "seed_material_add" "seed-service" '{"type":"evidence","title":"测试材料","content":"测试内容"}'

# 10. 合并种子
check "合并种子" POST "/api/v1/seeds/${SEED_ID}/merge" "seed_merge" "seed-service" '{"sourceSeedId":"seed-agent-quality"}'

# 11. 开始发芽
check "开始发芽" POST "/api/v1/sprout/start" "sprout_start" "sprout-service"

# 12. 发芽机会操作
OPP_ID=$(curl -s "${GW}/api/v1/sprout/opportunities" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print(d['items'][0]['id'])" 2>/dev/null || echo "opp-1")
check "发芽补充资料" POST "/api/v1/sprout/opportunities/${OPP_ID}/supplement" "sprout_opportunity_action" "sprout-service"

# 13. 创建写作会话
check "创建写作会话" POST "/api/v1/writing/sessions" "writing_session_create" "writing-service" '{"seedId":"seed-1","interestId":"agent","coreClaim":"测试主张"}'

# 14. 确认主张
WS_ID=$(curl -s -X POST "${GW}/api/v1/writing/sessions" -H 'Content-Type: application/json' -d '{"seedId":"seed-1","interestId":"agent"}' | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print(d['sessionId'])" 2>/dev/null || echo "ws-1")
check "确认主张" POST "/api/v1/writing/sessions/${WS_ID}/confirm-claim" "writing_state_transition" "writing-service"

# 15. 生成蓝图
check "生成蓝图" POST "/api/v1/writing/sessions/${WS_ID}/blueprint" "writing_state_transition" "writing-service"

# 16. 生成初稿
check "生成初稿" POST "/api/v1/writing/sessions/${WS_ID}/draft" "writing_state_transition" "writing-service"

# 17. 模拟发布
curl -s -X POST "${GW}/api/v1/writing/sessions/${WS_ID}/finalize" -H 'Content-Type: application/json' >/dev/null 2>&1 || true
check "模拟发布" POST "/api/v1/writing/sessions/${WS_ID}/publish/mock" "writing_publish" "writing-service"

# 18. 反馈文章列表
check "反馈文章列表" GET "/api/v1/feedback/articles" "feedback_article_list" "feedback-service"

# 19. 生成二次种子
check "生成二次种子" POST "/api/v1/feedback/articles/article-moat/second-seed" "feedback_second_seed" "feedback-service"

# 20. Memory 更新建议
check "Memory更新建议" POST "/api/v1/feedback/articles/article-moat/memory-update-request" "feedback_memory_update" "feedback-service"

# 21. LLM 任务
check "LLM任务" POST "/api/v1/llm/tasks/summarize-content" "llm_task_started" "llm-service" '{"taskType":"summarize-content","input":{"title":"test"}}'

# 22. Gateway 代理日志
check "Gateway代理" GET "/api/v1/profile/me" "gateway_proxy" "api-gateway"

echo ""
echo "=== 结果: ${PASS} PASS / ${FAIL} FAIL ==="
