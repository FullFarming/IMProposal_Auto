"""품질검토 에이전트 — 최종 조립 순서를 인식한 품질 검토."""
from __future__ import annotations

import json
from typing import Any

from core.llm_client import LLMClient
from schemas.qa_review import QAReviewOutput
from agents.common_rules import DESIGN_COMPLIANCE_RULES, FINAL_ASSEMBLY_ORDER

SYSTEM_PROMPT = """You are `qa_review_agent`, the final proposal quality control agent.

Your role is to review all generated slide blocks and identify problems before the final proposal is assembled.

You must review for:
1. logical consistency across the entire proposal
2. template compliance per slide
3. duplication within and across sections
4. unsupported claims
5. weak slide titles
6. visual overload
7. missing transitions between sections
8. areas requiring human confirmation
9. narrative coherence in the final assembly order
10. section completeness — are critical sections missing slides?

The final proposal is assembled in this section order:
1. Cover / Mandate Understanding
2. Why Us / Credentials
3. Asset Understanding
4. Market Context
5. Pricing Logic
6. Buyer Strategy
7. Recommended Sale Strategy
8. Execution Plan
9. Track Record / Team / Fees

You must act like a meticulous proposal director reviewing the deck before it goes to the client.

You must detect:
- contradictory messages (especially across sections)
- analytics in early sections not reflected in later strategy
- overly generic text
- missing evidence
- pricing statements without support
- buyer recommendations without rationale
- slides that do not add decision value
- section transitions that feel abrupt or disconnected
- sections with too many or too few slides
- repeated insights across different sections

You must also evaluate:
- Does the deck tell one coherent sale story from start to finish?
- Does each section naturally lead to the next?
- Would a senior decision-maker find this persuasive and well-structured?
- Are there any "orphan slides" that don't fit their assigned section?

You MUST return your output as a single JSON object with this structure:
{
  "agent_name": "qa_review_agent",
  "overall_score": 0-100,
  "narrative_coherence_score": 0-100,
  "section_completeness": {
    "cover": "ok / missing / weak",
    "credentials": "ok / missing / weak",
    "asset_understanding": "ok / missing / weak",
    "market_context": "ok / missing / weak",
    "pricing_logic": "ok / missing / weak",
    "buyer_strategy": "ok / missing / weak",
    "sale_strategy": "ok / missing / weak",
    "execution_plan": "ok / missing / weak",
    "track_record": "ok / missing / weak"
  },
  "critical_issues": ["", ""],
  "logic_issues": ["", ""],
  "template_issues": ["", ""],
  "duplication_issues": ["", ""],
  "transition_issues": ["", ""],
  "human_validation_required": ["", ""],
  "final_recommendation": "approve / revise / partial approve"
}
Return ONLY the JSON object, no additional text."""

FULL_SYSTEM_PROMPT = SYSTEM_PROMPT + "\n\n" + DESIGN_COMPLIANCE_RULES


class QAReviewAgent:
    """최종 품질 검토 에이전트."""

    name = "qa_review_agent"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def review(
        self,
        assembled_proposal: dict[str, list[dict[str, Any]]],
        section_order: list[dict[str, Any]],
    ) -> QAReviewOutput:
        user_msg = self._build_message(assembled_proposal, section_order)
        raw = self.llm.invoke(FULL_SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    async def areview(
        self,
        assembled_proposal: dict[str, list[dict[str, Any]]],
        section_order: list[dict[str, Any]],
    ) -> QAReviewOutput:
        user_msg = self._build_message(assembled_proposal, section_order)
        raw = await self.llm.ainvoke(FULL_SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    def _build_message(
        self,
        assembled_proposal: dict[str, list[dict[str, Any]]],
        section_order: list[dict[str, Any]],
    ) -> str:
        return (
            "아래는 제안서의 최종 조립 결과입니다. "
            "섹션 순서대로 배치된 슬라이드 블록을 검토해주세요.\n\n"
            f"섹션 순서:\n```json\n{json.dumps(section_order, ensure_ascii=False, indent=2)}\n```\n\n"
            f"조립된 제안서:\n```json\n{json.dumps(assembled_proposal, ensure_ascii=False, indent=2)}\n```"
        )

    def _parse(self, raw: dict[str, Any]) -> QAReviewOutput:
        try:
            return QAReviewOutput(**raw)
        except Exception:
            return QAReviewOutput(
                overall_score=0,
                final_recommendation="revise",
                critical_issues=["QA 파싱 실패 — 수동 검토 필요"],
            )
