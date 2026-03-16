"""품질검토 에이전트."""
from __future__ import annotations

import json
from typing import Any

from core.llm_client import LLMClient
from schemas.qa_review import QAReviewOutput

SYSTEM_PROMPT = """You are `qa_review_agent`, the final proposal quality control agent.

Your role is to review all generated slide blocks and identify problems before the final proposal is assembled.

You must review for:
1. logical consistency
2. template compliance
3. duplication
4. unsupported claims
5. weak slide titles
6. visual overload
7. missing transitions between sections
8. areas requiring human confirmation

You must act like a meticulous proposal director.

You must detect:
- contradictory messages
- analytics not reflected in strategy
- overly generic text
- missing evidence
- pricing statements without support
- buyer recommendations without rationale
- slides that do not add decision value

You MUST return your output as a single JSON object with this structure:
{
  "agent_name": "qa_review_agent",
  "overall_score": 0-100,
  "critical_issues": ["", ""],
  "logic_issues": ["", ""],
  "template_issues": ["", ""],
  "duplication_issues": ["", ""],
  "human_validation_required": ["", ""],
  "final_recommendation": "approve / revise / partial approve"
}
Return ONLY the JSON object, no additional text."""


class QAReviewAgent:
    """최종 품질 검토 에이전트."""

    name = "qa_review_agent"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def review(self, all_slide_blocks: list[dict[str, Any]], section_map: dict[str, Any]) -> QAReviewOutput:
        user_msg = (
            "아래는 제안서의 전체 슬라이드 블록과 섹션 구조입니다. "
            "최종 품질 검토를 수행해주세요.\n\n"
            f"슬라이드 블록:\n```json\n{json.dumps(all_slide_blocks, ensure_ascii=False, indent=2)}\n```\n\n"
            f"섹션 구조:\n```json\n{json.dumps(section_map, ensure_ascii=False, indent=2)}\n```"
        )
        raw = self.llm.invoke(SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    async def areview(self, all_slide_blocks: list[dict[str, Any]], section_map: dict[str, Any]) -> QAReviewOutput:
        user_msg = (
            "아래는 제안서의 전체 슬라이드 블록과 섹션 구조입니다. "
            "최종 품질 검토를 수행해주세요.\n\n"
            f"슬라이드 블록:\n```json\n{json.dumps(all_slide_blocks, ensure_ascii=False, indent=2)}\n```\n\n"
            f"섹션 구조:\n```json\n{json.dumps(section_map, ensure_ascii=False, indent=2)}\n```"
        )
        raw = await self.llm.ainvoke(SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    def _parse(self, raw: dict[str, Any]) -> QAReviewOutput:
        try:
            return QAReviewOutput(**raw)
        except Exception:
            return QAReviewOutput(
                overall_score=0,
                final_recommendation="revise",
                critical_issues=["QA 파싱 실패 — 수동 검토 필요"],
            )
