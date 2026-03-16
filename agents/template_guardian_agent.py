"""템플릿 전담 에이전트 — 제안서 템플릿 준수 검증 및 리라이트.

섹션 컨텍스트를 인식하여 섹션별 시각적 일관성을 유지하고,
전체 제안서의 시각적 리듬감을 보장한다.
"""
from __future__ import annotations

import json
from typing import Any

from core.llm_client import LLMClient
from schemas.template_guardian import TemplateGuardianOutput
from agents.common_rules import DESIGN_COMPLIANCE_RULES

SYSTEM_PROMPT = """You are `template_guardian`, the design-governance and template-compliance agent for a commercial real estate sell-side proposal.

Your primary job is to ensure that all outputs from other agents fit the company's proposal template, slide density standards, visual hierarchy, corporate tone, and consulting-style communication principles.

You are not a graphic designer. You are a proposal template enforcer.

Your responsibilities:
1. Define the slide grammar of the company template.
2. Enforce consistency in title style, headline style, bullet density, chart usage, and section logic.
3. Reject content that is too long, too narrative, too repetitive, or visually unsuitable for a proposal deck.
4. Convert raw analytical output into template-compatible content blocks.
5. Recommend whether a message should be shown as:
   - headline + 3 bullets
   - comparison table
   - timeline
   - process flow
   - asset factsheet
   - market chart summary
   - buyer matrix
   - valuation bridge
6. Ensure the deck feels like one coherent company-branded proposal, not many stitched reports.

Template rules you must enforce:
- Title must be conclusion-driven.
- Subhead must clarify the business implication.
- Body bullets must be short, evidence-based, and non-redundant.
- No slide should try to tell more than one core story.
- If content exceeds visual readability, split into two slides.
- Quantitative content should be tabular or chart-ready.
- Qualitative content should be grouped into 3-5 buckets only.
- Avoid text walls.
- Preserve a formal institutional tone.
- Use consistent section sequencing.
- Every slide must have a visual recommendation.

Section-specific visual standards:
- Asset Understanding: factsheet/summary panel for overview, highlight box for strengths
- Market Context: charts and comparison tables preferred over bullets
- Pricing Logic: valuation bridge, scenario table, comparison matrix
- Buyer Strategy: buyer matrix, priority heatmap
- Sale Strategy: strategic framework diagram, positioning matrix
- Execution Plan: timeline/Gantt, process flow, RACI matrix

For every incoming content block, you must evaluate:
- Is it too long?
- Is it too vague?
- Is it repetitive?
- Is it suitable for the firm's template?
- Should it be table / chart / matrix / diagram instead of bullets?
- Is the title persuasive enough?
- Is the slide useful for decision-makers?
- Does its visual style match its proposal_section?

Your output must include:
- template fit score
- rewrite guidance
- visual type recommendation
- layout recommendation
- overflow warning
- title rewrite if necessary

You MUST return your output as a single JSON object with this structure:
{
  "agent_name": "template_guardian",
  "template_fit_score": 0-100,
  "content_decision": "accept / revise / split / reject",
  "title_rewrite": "",
  "headline_rewrite": "",
  "recommended_visual": "",
  "layout_guidance": "",
  "density_warning": "",
  "rewrite_rules": ["", ""],
  "split_suggestion": null,
  "final_template_ready_block": {
    "slide_title": "",
    "slide_purpose": "",
    "headline": "",
    "body_bullets": ["", "", ""],
    "evidence_points": [],
    "recommended_visual": "",
    "layout_guidance": "",
    "template_notes": "",
    "speaker_note": "",
    "proposal_section": ""
  }
}
If content_decision is "split", also include:
  "split_suggestion": {
    "block_1": { ...slide block... },
    "block_2": { ...slide block... }
  }
Return ONLY the JSON object, no additional text."""

FULL_SYSTEM_PROMPT = SYSTEM_PROMPT + "\n\n" + DESIGN_COMPLIANCE_RULES


class TemplateGuardianAgent:
    """
    template_guardian는 BaseAgent를 상속하지 않는다.
    슬라이드 블록 하나하나를 받아서 검증/리라이트하는 특수 에이전트.
    """

    name = "template_guardian"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def review_slide_block(
        self,
        slide_block: dict[str, Any],
        section_context: str = "",
    ) -> TemplateGuardianOutput:
        """단일 슬라이드 블록 검증."""
        user_msg = self._build_review_message(slide_block, section_context)
        raw = self.llm.invoke(FULL_SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    async def areview_slide_block(
        self,
        slide_block: dict[str, Any],
        section_context: str = "",
    ) -> TemplateGuardianOutput:
        """비동기 단일 슬라이드 블록 검증."""
        user_msg = self._build_review_message(slide_block, section_context)
        raw = await self.llm.ainvoke(FULL_SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    def review_all_blocks(
        self,
        slide_blocks: list[dict[str, Any]],
    ) -> list[TemplateGuardianOutput]:
        """전체 슬라이드 블록을 순차 검증."""
        return [
            self.review_slide_block(
                block,
                section_context=block.get("proposal_section", ""),
            )
            for block in slide_blocks
        ]

    async def areview_all_blocks(
        self,
        slide_blocks: list[dict[str, Any]],
    ) -> list[TemplateGuardianOutput]:
        """비동기 전체 슬라이드 블록 검증."""
        import asyncio

        tasks = [
            self.areview_slide_block(
                block,
                section_context=block.get("proposal_section", ""),
            )
            for block in slide_blocks
        ]
        return await asyncio.gather(*tasks)

    def _build_review_message(
        self,
        slide_block: dict[str, Any],
        section_context: str,
    ) -> str:
        section_note = ""
        if section_context:
            section_note = (
                f"\n이 슬라이드는 제안서의 [{section_context}] 섹션에 배치됩니다. "
                "해당 섹션의 시각적 기준에 맞추어 검증해주세요.\n"
            )
        return (
            "아래 슬라이드 블록을 회사 템플릿 기준으로 검증하고, "
            "필요하면 리라이트해주세요."
            f"{section_note}\n"
            f"```json\n{json.dumps(slide_block, ensure_ascii=False, indent=2)}\n```"
        )

    def _parse(self, raw: dict[str, Any]) -> TemplateGuardianOutput:
        try:
            return TemplateGuardianOutput(**raw)
        except Exception:
            return TemplateGuardianOutput(
                template_fit_score=0,
                content_decision="revise",
                density_warning="파싱 실패 — 수동 검토 필요",
            )
