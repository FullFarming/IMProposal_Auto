"""템플릿 전담 에이전트 — 제안서 템플릿 준수 검증 및 리라이트."""
from __future__ import annotations

import json
from typing import Any

from core.llm_client import LLMClient
from schemas.template_guardian import TemplateGuardianOutput

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

For every incoming content block, you must evaluate:
- Is it too long?
- Is it too vague?
- Is it repetitive?
- Is it suitable for the firm's template?
- Should it be table / chart / matrix / diagram instead of bullets?
- Is the title persuasive enough?
- Is the slide useful for decision-makers?

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
  "final_template_ready_block": {
    "slide_title": "",
    "slide_purpose": "",
    "headline": "",
    "body_bullets": ["", "", ""],
    "recommended_visual": "",
    "layout_guidance": "",
    "template_notes": "",
    "speaker_note": ""
  }
}
Return ONLY the JSON object, no additional text."""


class TemplateGuardianAgent:
    """
    template_guardian는 BaseAgent를 상속하지 않는다.
    슬라이드 블록 하나하나를 받아서 검증/리라이트하는 특수 에이전트.
    """

    name = "template_guardian"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def review_slide_block(self, slide_block: dict[str, Any]) -> TemplateGuardianOutput:
        """단일 슬라이드 블록 검증."""
        user_msg = (
            "아래 슬라이드 블록을 회사 템플릿 기준으로 검증하고, "
            "필요하면 리라이트해주세요.\n\n"
            f"```json\n{json.dumps(slide_block, ensure_ascii=False, indent=2)}\n```"
        )
        raw = self.llm.invoke(SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    async def areview_slide_block(self, slide_block: dict[str, Any]) -> TemplateGuardianOutput:
        """비동기 단일 슬라이드 블록 검증."""
        user_msg = (
            "아래 슬라이드 블록을 회사 템플릿 기준으로 검증하고, "
            "필요하면 리라이트해주세요.\n\n"
            f"```json\n{json.dumps(slide_block, ensure_ascii=False, indent=2)}\n```"
        )
        raw = await self.llm.ainvoke(SYSTEM_PROMPT, user_msg)
        return self._parse(raw)

    def review_all_blocks(self, slide_blocks: list[dict[str, Any]]) -> list[TemplateGuardianOutput]:
        """전체 슬라이드 블록을 순차 검증."""
        return [self.review_slide_block(block) for block in slide_blocks]

    async def areview_all_blocks(self, slide_blocks: list[dict[str, Any]]) -> list[TemplateGuardianOutput]:
        """비동기 전체 슬라이드 블록 검증."""
        import asyncio
        tasks = [self.areview_slide_block(block) for block in slide_blocks]
        return await asyncio.gather(*tasks)

    def _parse(self, raw: dict[str, Any]) -> TemplateGuardianOutput:
        try:
            return TemplateGuardianOutput(**raw)
        except Exception:
            return TemplateGuardianOutput(
                template_fit_score=0,
                content_decision="revise",
                density_warning="파싱 실패 — 수동 검토 필요",
            )
