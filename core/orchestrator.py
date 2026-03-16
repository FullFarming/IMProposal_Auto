"""
proposal_orchestrator — 6단계 파이프라인으로 제안서 자동 생성을 지휘.

Stage 1: 입력 분해 및 사전 검증
Stage 2: 기반 분석 (병렬 — asset, location, market, buyer)
Stage 3: 파생 분석 (valuation, enduser, deal strategy)
Stage 4: 실행 계획
Stage 5: 문안 정제 + 템플릿 적합화
Stage 6: 최종 QA 검토
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.llm_client import LLMClient
from schemas.slide_block import AgentOutput

# 에이전트 임포트
from agents.asset_analysis_agent import AssetAnalysisAgent
from agents.location_demand_agent import LocationDemandAgent
from agents.market_analysis_agent import MarketAnalysisAgent
from agents.buyer_segmentation_agent import BuyerSegmentationAgent
from agents.valuation_agent import ValuationAgent
from agents.enduser_strategy_agent import EnduserStrategyAgent
from agents.deal_strategy_agent import DealStrategyAgent
from agents.execution_plan_agent import ExecutionPlanAgent
from agents.slide_narrative_agent import SlideNarrativeAgent
from agents.template_guardian_agent import TemplateGuardianAgent
from agents.qa_review_agent import QAReviewAgent

logger = logging.getLogger(__name__)

ORCHESTRATOR_SYSTEM_PROMPT = """You are `proposal_orchestrator`, the master agent for automating a sell-side commercial real estate advisory proposal.
Your primary mission is not just to summarize materials, but to produce a proposal-ready structure that matches the firm's presentation template, storytelling style, slide logic, and decision-making flow.
You must think like a senior sell-side advisor and proposal director at a top-tier commercial real estate consulting firm.

Your goals are:
1. Understand the assignment as a real sell-side advisory proposal, not a generic research report.
2. Break the work into specialized streams and dispatch tasks to sub-agents.
3. Ensure that every output is compatible with the company's proposal template and visual communication style.
4. Maintain one coherent deal story from asset analysis to execution plan.
5. Reject outputs that are analytically correct but unsuitable for slide-based proposal design.
6. Produce sections in the same logic as a real proposal:
   - asset understanding
   - market analysis
   - valuation logic
   - buyer strategy
   - execution plan
   - proposal narrative

Core operating principles:
- One slide = one message.
- Every slide title must be conclusion-driven.
- Do not allow long paragraphs unless unavoidable.
- Translate analysis into presentation-ready slide blocks.
- Separate evidence from interpretation.
- Flag data insufficiency instead of fabricating.
- Always optimize for management review readability.
- Always preserve the firm's proposal tone: formal, analytical, concise, persuasive.

When multiple agent outputs conflict:
- prioritize template consistency first
- then analytical coherence
- then completeness
- never keep contradictory messages across slides

You must always ask:
- What is the single strongest sale narrative for this asset?
- Which buyer type is most plausible?
- Which pricing logic is defendable?
- Which slides are truly necessary in the firm's template?
- What should be shown visually vs described in text?

Do not produce generic consultant filler language.
Do not create decorative slides without decision value.
Do not over-describe. Convert to boardroom-grade proposal language.

Given the raw input data, analyze it and return a JSON with:
{
  "project_understanding": "",
  "data_categories": [""],
  "missing_data": [""],
  "section_map": {
    "asset_understanding": {"automatable": true, "notes": ""},
    "location_demand": {"automatable": true, "notes": ""},
    "market_analysis": {"automatable": true, "notes": ""},
    "buyer_segmentation": {"automatable": true, "notes": ""},
    "valuation": {"automatable": true, "notes": ""},
    "enduser_strategy": {"automatable": true, "notes": ""},
    "deal_strategy": {"automatable": true, "notes": ""},
    "execution_plan": {"automatable": true, "notes": ""}
  },
  "sale_narrative_thesis": "",
  "recommended_slide_count": 0,
  "human_review_items": [""]
}
Return ONLY the JSON object."""


@dataclass
class PipelineResult:
    """전체 파이프라인 실행 결과."""

    project_understanding: dict[str, Any] = field(default_factory=dict)
    stage2_results: dict[str, AgentOutput] = field(default_factory=dict)
    stage3_results: dict[str, AgentOutput] = field(default_factory=dict)
    stage4_result: AgentOutput | None = None
    narrative_result: AgentOutput | None = None
    template_reviews: list[Any] = field(default_factory=list)
    qa_result: Any = None
    final_slide_blocks: list[dict[str, Any]] = field(default_factory=list)
    section_map: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _serialize(obj: Any) -> Any:
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "__dict__"):
                return {k: _serialize(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_serialize(v) for v in obj]
            return obj

        return _serialize(self.__dict__)


class ProposalOrchestrator:
    """6단계 파이프라인 오케스트레이터."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.llm = LLMClient(self.settings)
        self.result = PipelineResult()

        # 에이전트 인스턴스
        self.asset_agent = AssetAnalysisAgent(self.llm)
        self.location_agent = LocationDemandAgent(self.llm)
        self.market_agent = MarketAnalysisAgent(self.llm)
        self.buyer_agent = BuyerSegmentationAgent(self.llm)
        self.valuation_agent = ValuationAgent(self.llm)
        self.enduser_agent = EnduserStrategyAgent(self.llm)
        self.deal_agent = DealStrategyAgent(self.llm)
        self.execution_agent = ExecutionPlanAgent(self.llm)
        self.narrative_agent = SlideNarrativeAgent(self.llm)
        self.template_guardian = TemplateGuardianAgent(self.llm)
        self.qa_agent = QAReviewAgent(self.llm)

    # ── 메인 실행 ─────────────────────────────────────────

    async def run(self, input_data: dict[str, Any]) -> PipelineResult:
        """전체 6단계 파이프라인 비동기 실행."""
        logger.info("=" * 60)
        logger.info("파이프라인 시작")
        logger.info("=" * 60)

        # Stage 1: 입력 분해
        await self._stage1_decompose(input_data)

        # Stage 2: 기반 분석 (병렬)
        await self._stage2_foundation(input_data)

        # Stage 3: 파생 분석
        await self._stage3_derived(input_data)

        # Stage 4: 실행 계획
        await self._stage4_execution(input_data)

        # Stage 5: 문안 정제 + 템플릿 적합화
        await self._stage5_narrative_and_template()

        # Stage 6: QA 검토
        await self._stage6_qa_review()

        logger.info("=" * 60)
        logger.info("파이프라인 완료")
        logger.info("=" * 60)

        return self.result

    def run_sync(self, input_data: dict[str, Any]) -> PipelineResult:
        """동기 래퍼."""
        return asyncio.run(self.run(input_data))

    # ── Stage 1: 입력 분해 ────────────────────────────────

    async def _stage1_decompose(self, input_data: dict[str, Any]) -> None:
        logger.info("[Stage 1] 입력 자료 분해 및 사전 검증")

        user_msg = (
            "아래 원본 입력 자료를 분석하여 프로젝트 이해, 누락 데이터, "
            "섹션별 자동화 가능 여부를 판단해주세요.\n\n"
            f"```json\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n```"
        )
        result = await self.llm.ainvoke(ORCHESTRATOR_SYSTEM_PROMPT, user_msg)
        self.result.project_understanding = result
        self.result.section_map = result.get("section_map", {})

        missing = result.get("missing_data", [])
        if missing:
            logger.warning("[Stage 1] 누락 데이터 감지: %s", missing)

    # ── Stage 2: 기반 분석 (병렬) ─────────────────────────

    async def _stage2_foundation(self, input_data: dict[str, Any]) -> None:
        logger.info("[Stage 2] 기반 분석 에이전트 병렬 실행")

        context = {
            "asset_data": input_data.get("asset_data", {}),
            "location_data": input_data.get("location_data", {}),
            "market_data": input_data.get("market_data", {}),
        }

        asset_task = self.asset_agent.arun(context)
        location_task = self.location_agent.arun(context)
        market_task = self.market_agent.arun(context)
        buyer_task = self.buyer_agent.arun(context)

        results = await asyncio.gather(
            asset_task, location_task, market_task, buyer_task
        )

        self.result.stage2_results = {
            "asset_analysis": results[0],
            "location_demand": results[1],
            "market_analysis": results[2],
            "buyer_segmentation": results[3],
        }

        logger.info("[Stage 2] 기반 분석 완료 — %d개 에이전트", len(results))

    # ── Stage 3: 파생 분석 ────────────────────────────────

    async def _stage3_derived(self, input_data: dict[str, Any]) -> None:
        logger.info("[Stage 3] 파생 분석 에이전트 실행")

        # 2단계 결과를 context에 포함
        s2 = self.result.stage2_results
        context = {
            "asset_data": input_data.get("asset_data", {}),
            "location_data": input_data.get("location_data", {}),
            "market_data": input_data.get("market_data", {}),
            "asset_analysis_result": s2["asset_analysis"].model_dump() if s2.get("asset_analysis") else {},
            "location_demand_result": s2["location_demand"].model_dump() if s2.get("location_demand") else {},
            "market_analysis_result": s2["market_analysis"].model_dump() if s2.get("market_analysis") else {},
            "buyer_segmentation_result": s2["buyer_segmentation"].model_dump() if s2.get("buyer_segmentation") else {},
        }

        # valuation과 enduser는 병렬 가능, deal_strategy는 이들에 의존
        val_task = self.valuation_agent.arun(context)
        enduser_task = self.enduser_agent.arun(context)

        val_result, enduser_result = await asyncio.gather(val_task, enduser_task)

        # deal_strategy는 valuation/enduser 결과 필요
        context["valuation_result"] = val_result.model_dump()
        context["enduser_strategy_result"] = enduser_result.model_dump()

        deal_result = await self.deal_agent.arun(context)

        self.result.stage3_results = {
            "valuation": val_result,
            "enduser_strategy": enduser_result,
            "deal_strategy": deal_result,
        }

        logger.info("[Stage 3] 파생 분석 완료")

    # ── Stage 4: 실행 계획 ────────────────────────────────

    async def _stage4_execution(self, input_data: dict[str, Any]) -> None:
        logger.info("[Stage 4] 실행 계획 에이전트 실행")

        s3 = self.result.stage3_results
        context = {
            "asset_data": input_data.get("asset_data", {}),
            "deal_strategy_result": s3["deal_strategy"].model_dump() if s3.get("deal_strategy") else {},
        }

        self.result.stage4_result = await self.execution_agent.arun(context)
        logger.info("[Stage 4] 실행 계획 완료")

    # ── Stage 5: 문안 정제 + 템플릿 적합화 ────────────────

    async def _stage5_narrative_and_template(self) -> None:
        logger.info("[Stage 5] 문안 정제 및 템플릿 적합화")

        # 전체 슬라이드 블록 수집
        all_blocks = self._collect_all_slide_blocks()

        # 5-a: slide_narrative_agent로 정제
        context = {"all_slide_blocks": [b.model_dump() if hasattr(b, "model_dump") else b for b in all_blocks]}
        self.result.narrative_result = await self.narrative_agent.arun(context)

        # 5-b: template_guardian으로 검증
        narrative_blocks = []
        if self.result.narrative_result and self.result.narrative_result.slide_blocks:
            narrative_blocks = [
                sb.model_dump() if hasattr(sb, "model_dump") else sb
                for sb in self.result.narrative_result.slide_blocks
            ]
        else:
            narrative_blocks = [b.model_dump() if hasattr(b, "model_dump") else b for b in all_blocks]

        self.result.template_reviews = await self.template_guardian.areview_all_blocks(
            narrative_blocks
        )

        # 템플릿 통과한 블록만 최종 조립
        self.result.final_slide_blocks = []
        for i, review in enumerate(self.result.template_reviews):
            if review.content_decision in ("accept", "revise") and review.final_template_ready_block:
                self.result.final_slide_blocks.append(
                    review.final_template_ready_block.model_dump()
                )
            elif i < len(narrative_blocks):
                # 원본 유지 (수동 검토 필요)
                self.result.final_slide_blocks.append(narrative_blocks[i])

        logger.info(
            "[Stage 5] 완료 — 최종 슬라이드 %d장", len(self.result.final_slide_blocks)
        )

    # ── Stage 6: QA 검토 ──────────────────────────────────

    async def _stage6_qa_review(self) -> None:
        logger.info("[Stage 6] 최종 QA 검토")
        self.result.qa_result = await self.qa_agent.areview(
            self.result.final_slide_blocks,
            self.result.section_map,
        )
        logger.info(
            "[Stage 6] QA 완료 — 점수: %s, 판정: %s",
            self.result.qa_result.overall_score,
            self.result.qa_result.final_recommendation,
        )

    # ── 유틸리티 ──────────────────────────────────────────

    def _collect_all_slide_blocks(self) -> list:
        """모든 에이전트 결과에서 슬라이드 블록 수집."""
        blocks = []
        for output in list(self.result.stage2_results.values()) + list(
            self.result.stage3_results.values()
        ):
            if output and output.slide_blocks:
                blocks.extend(output.slide_blocks)
        if self.result.stage4_result and self.result.stage4_result.slide_blocks:
            blocks.extend(self.result.stage4_result.slide_blocks)
        return blocks

    def save_output(self, output_dir: str | Path | None = None) -> Path:
        """결과를 JSON 파일로 저장."""
        out_dir = Path(output_dir or self.settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        output_path = out_dir / "proposal_output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, ensure_ascii=False, indent=2)

        # 최종 슬라이드 블록만 별도 저장
        slides_path = out_dir / "final_slides.json"
        with open(slides_path, "w", encoding="utf-8") as f:
            json.dump(self.result.final_slide_blocks, f, ensure_ascii=False, indent=2)

        logger.info("결과 저장 완료: %s", out_dir)
        return out_dir
