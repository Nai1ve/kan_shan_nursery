"""Memory management algorithm.

Analyzes user interactions and generates Memory update suggestions.

Data sources:
- Seed interactions (agree/disagree/question)
- Writing feedback
- Content browsing patterns
- Manual Memory edits

Memory layers:
- Short-term (7 days): Recent interactions
- Medium-term (30 days): Pattern recognition
- Long-term: Stable user profile traits
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("kanshan.profile.memory.algorithm")


class MemoryAlgorithm:
    """Analyzes user behavior and generates Memory update suggestions."""

    def __init__(self, repository=None, llm_service_url: str = "http://127.0.0.1:8080"):
        self.repository = repository
        self.llm_service_url = llm_service_url

    def analyze_seed_interactions(self, user_id: str, days: int = 7) -> dict[str, Any]:
        """Analyze user's seed interaction patterns.

        Returns:
            {
                "interest_stances": {interest_id: {"agree": N, "disagree": N, "neutral": N}},
                "top_questions": [question_topics],
                "knowledge_signals": {interest_id: level_change_suggestion},
            }
        """
        # This would query seed-service for user's interactions
        # For now, return placeholder structure
        return {
            "interest_stances": {},
            "top_questions": [],
            "knowledge_signals": {},
        }

    def analyze_writing_feedback(self, user_id: str) -> dict[str, Any]:
        """Analyze user's writing feedback patterns.

        Returns:
            {
                "style_trends": {dimension: trend},
                "improvement_areas": [area],
                "strengths": [strength],
            }
        """
        # This would query writing-service and feedback-service
        return {
            "style_trends": {},
            "improvement_areas": [],
            "strengths": [],
        }

    def generate_memory_suggestions(
        self,
        user_id: str,
        current_memory: dict[str, Any],
        seed_analysis: dict[str, Any] | None = None,
        writing_analysis: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate Memory update suggestions based on analysis.

        Returns list of update requests:
        [
            {
                "interestId": "shuma",
                "targetField": "preferredPerspective",
                "suggestedValue": ["AI 工具", "编程实践"],
                "reason": "用户最近在该领域连续 agree 了 5 篇关于 AI 工具的文章",
                "confidence": "high",
            },
            ...
        ]
        """
        suggestions = []

        if not seed_analysis:
            seed_analysis = self.analyze_seed_interactions(user_id)
        if not writing_analysis:
            writing_analysis = self.analyze_writing_feedback(user_id)

        # Analyze stance patterns
        for interest_id, stance_data in seed_analysis.get("interest_stances", {}).items():
            agree_count = stance_data.get("agree", 0)
            disagree_count = stance_data.get("disagree", 0)

            if agree_count >= 3:
                suggestions.append({
                    "interestId": interest_id,
                    "targetField": "preferredPerspective",
                    "suggestedValue": self._extract_perspective_from_agrees(interest_id),
                    "reason": f"用户在该领域连续认同了 {agree_count} 篇文章，表明对该方向有强烈偏好",
                    "confidence": "high" if agree_count >= 5 else "medium",
                })

            if disagree_count >= 3:
                suggestions.append({
                    "interestId": interest_id,
                    "targetField": "preferredPerspective",
                    "suggestedValue": self._extract_perspective_from_disagrees(interest_id),
                    "reason": f"用户在该领域连续反对了 {disagree_count} 篇文章，可能对该方向持保留态度",
                    "confidence": "medium",
                })

        # Analyze knowledge level signals
        for interest_id, signal in seed_analysis.get("knowledge_signals", {}).items():
            if signal.get("level_change"):
                suggestions.append({
                    "interestId": interest_id,
                    "targetField": "knowledgeLevel",
                    "suggestedValue": signal["level_change"],
                    "reason": signal.get("reason", "基于用户的问题深度和交互模式"),
                    "confidence": "medium",
                })

        # Analyze writing feedback
        for area in writing_analysis.get("improvement_areas", []):
            if area.get("field"):
                suggestions.append({
                    "interestId": area.get("interest_id", "global"),
                    "targetField": area["field"],
                    "suggestedValue": area.get("suggestion"),
                    "reason": area.get("reason", "基于写作反馈分析"),
                    "confidence": "medium",
                })

        return suggestions

    def _extract_perspective_from_agrees(self, interest_id: str) -> list[str]:
        """Extract preferred perspective from agreed articles."""
        # This would analyze the content of agreed articles
        # For now, return placeholder
        return []

    def _extract_perspective_from_disagrees(self, interest_id: str) -> list[str]:
        """Extract perspective signal from disagreed articles."""
        return []

    def build_enhanced_profile_prompt(
        self,
        nickname: str,
        interests: list[str],
        current_memory: dict[str, Any],
        interaction_summary: dict[str, Any],
    ) -> str:
        """Build prompt for LLM to generate enhanced profile suggestions."""

        prompt = f"""用户 {nickname} 的画像分析：

当前兴趣：{', '.join(interests)}

当前 Memory：
- 长期背景：{current_memory.get('globalMemory', {}).get('longTermBackground', '无')}
- 内容偏好：{current_memory.get('globalMemory', {}).get('contentPreference', '无')}
- 写作风格：{current_memory.get('globalMemory', {}).get('writingStyle', '无')}

最近交互摘要：
- 认同的观点：{interaction_summary.get('agree_count', 0)} 篇
- 反对的观点：{interaction_summary.get('disagree_count', 0)} 篇
- 提出的问题：{interaction_summary.get('question_count', 0)} 个

请根据以上信息，生成以下更新建议：
1. 内容偏好更新（如果有新的偏好信号）
2. 写作风格调整建议（基于交互模式）
3. 推荐策略优化建议
4. 风险提醒更新

请以 JSON 格式输出，包含 reason 字段说明更新原因。"""

        return prompt

    def call_llm_for_enhancement(self, prompt: str) -> dict[str, Any] | None:
        """Call LLM service for profile enhancement suggestions."""
        import urllib.request
        try:
            url = f"{self.llm_service_url}/llm/tasks/summarize-content"
            data = json.dumps({
                "input": {
                    "title": "用户画像增强",
                    "content": prompt,
                }
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("output")
        except Exception as e:
            logger.error("llm_enhancement_failed", extra={"error": str(e)})
            return None


# Confidence levels for Memory updates
CONFIDENCE_HIGH = "high"      # 3+ consistent signals
CONFIDENCE_MEDIUM = "medium"  # 2+ signals or strong single signal
CONFIDENCE_LOW = "low"        # Single weak signal


def should_auto_apply(confidence: str) -> bool:
    """Determine if a suggestion should be auto-applied (always False for safety)."""
    return False  # All suggestions require user confirmation


def format_update_reason(suggestion: dict[str, Any]) -> str:
    """Format a human-readable reason for the update."""
    interest = suggestion.get("interestId", "全局")
    field = suggestion.get("targetField", "")
    reason = suggestion.get("reason", "")

    field_labels = {
        "preferredPerspective": "偏好视角",
        "knowledgeLevel": "知识水平",
        "evidencePreference": "证据偏好",
        "writingReminder": "写作提醒",
        "longTermBackground": "长期背景",
        "contentPreference": "内容偏好",
        "writingStyle": "写作风格",
        "recommendationStrategy": "推荐策略",
        "riskReminder": "风险提醒",
    }

    field_label = field_labels.get(field, field)
    return f"[{interest}] {field_label}：{reason}"
