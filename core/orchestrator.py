"""
proposal_orchestrator — 8단계 파이프라인으로 제안서 자동 생성을 지휘.

Step 1: Parse — 입력 자료 파싱 및 정보 분류
Step 2: Classify — 정보를 에이전트별 범주로 분류
Step 3: Dispatch — 전문 에이전트에 작업 배정 (병렬/순차)
Step 4: Collect — 에이전트 결과 수집 (key_message, slide blocks, missing data, human validation)
Step 5: Narrative — slide_narrative_agent로 전체 정제
Step 6: Template — template_guardian으로 템플릿 준수 검증
Step 7: QA — qa_review_agent로 최종 검토
Step 8: Assemble — 최종 제안서 섹션 순서대로 조립

최종 조립 순서:
  1. Cover / Mandate Understanding
  2. Why Us / Credentials
  3. Asset Understanding
  4. Market Context
  5. Pricing Logic
  6. Buyer Strategy
  7. Recommended Sale Strategy
  8. Execution Plan
  9. Track Record / Team / Fees
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.llm_client import LLMClient
from schemas.slide_block import AgentOutput

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
from agents.common_rules import (
    DESIGN_COMPLIANCE_RULES,
    OPERATING_WORKFLOW_RULES,
    FINAL_ASSEMBLY_ORDER,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Orchestrator system prompt (Step 1-2 에 사용)
# ──────────────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM_PROMPT = (
    """You are `proposal_orchestrator`, the master agent for automating a sell-side commercial real estate advisory proposal.
Your primary mission is not just to summarize materials, but to produce a proposal-ready structure that matches the firm's presentation template, storytelling style, slide logic, and decision-making flow.
You must think like a senior sell-side advisor and proposal director at a top-tier commercial real estate consulting firm.

Your goals are:
1. Understand the assignment as a real sell-side advisory proposal, not a generic research report.
2. Break the work into specialized streams and dispatch tasks to sub-agents.
3. Ensure that every output is compatible with the company's proposal template and visual communication style.
4. Maintain one coherent deal story from asset analysis to execution plan.
5. Reject outputs that are analytically correct but unsuitable for slide-based proposal design.

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

Given the raw input data, perform STEP 1 (Parse) and STEP 2 (Classify).

Return a JSON with:
{
  "project_understanding": "",
  "sale_narrative_thesis": "",
  "data_classification": {
    "asset_analysis": {"available": true, "data_keys": [], "notes": ""},
    "location_demand": {"available": true, "data_keys": [], "notes": ""},
    "market_analysis": {"available": true, "data_keys": [], "notes": ""},
    "valuation": {"available": true, "data_keys": [], "notes": ""},
    "buyer_segmentation": {"available": true, "data_keys": [], "notes": ""},
    "enduser_strategy": {"available": true, "data_keys": [], "notes": ""},
    "deal_strategy": {"available": true, "data_keys": [], "notes": ""},
    "execution_plan": {"available": true, "data_keys": [], "notes": ""}
  },
  "missing_data": [""],
  "automatable_sections": [""],
  "requires_human_input_sections": [""],
  "agent_dispatch_plan": [
    {"agent": "", "priority": 1, "parallel_group": 1, "notes": ""}
  ],
  "recommended_slide_count": 0,
  "human_review_items": [""],
  "cover_slide_content": {
    "mandate_scope": "",
    "asset_name": "",
    "advisory_type": "",
    "key_objectives": [""]
  }
}
Return ONLY the JSON object."""
    + "\n\n"
    + DESIGN_COMPLIANCE_RULES
    + "\n\n"
    + OPERATING_WORKFLOW_RULES
)

# ──────────────────────────────────────────────────────────────
# Cover / Credentials / Track Record 생성용 프롬프트
# ──────────────────────────────────────────────────────────────

COVER_CREDENTIALS_PROMPT = (
    """You are a senior proposal writer for a commercial real estate advisory firm.
Generate slide blocks for the specified proposal sections based on the provided context.

You must generate slide blocks for:
1. Cover / Mandate Understanding — project scope, key objectives, asset summary
2. Why Us / Credentials — firm differentiation, relevant expertise
3. Track Record / Team / Fees — placeholder structure for team and fee sections

Each slide block must include the proposal_section tag.

Return a JSON with:
{
  "agent_name": "proposal_orchestrator",
  "section_name": "framing sections",
  "objective": "generate cover, credentials, and track record frames",
  "key_message": "",
  "insights": [],
  "slide_blocks": [
    {
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
  ]
}
Return ONLY the JSON object."""
    + "\n\n"
    + DESIGN_COMPLIANCE_RULES
)


# ──────────────────────────────────────────────────────────────
# PipelineResult
# ──────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """전체 파이프라인 실행 결과."""

    # Step 1-2
    project_understanding: dict[str, Any] = field(default_factory=dict)

    # Step 3-4: 에이전트별 결과
    agent_results: dict[str, AgentOutput] = field(default_factory=dict)

    # Step 5: 서사 정제 결과
    narrative_result: AgentOutput | None = None

    # Step 6: 템플릿 검증 결과
    template_reviews: list[Any] = field(default_factory=list)

    # Step 7: QA 검토 결과
    qa_result: Any = None

    # Step 8: 최종 조립 — 섹션별 슬라이드 블록
    assembled_proposal: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # 평탄화된 최종 슬라이드 목록 (순서대로)
    final_slide_blocks: list[dict[str, Any]] = field(default_factory=list)

    # 메타데이터
    section_order: list[dict[str, Any]] = field(default_factory=list)
    all_missing_data: list[str] = field(default_factory=list)
    all_human_validation: list[str] = field(default_factory=list)

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


# ──────────────────────────────────────────────────────────────
# ProposalOrchestrator
# ──────────────────────────────────────────────────────────────

class ProposalOrchestrator:
    """8단계 파이프라인 오케스트레이터."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.llm = LLMClient(self.settings)
        self.result = PipelineResult()
        self.result.section_order = FINAL_ASSEMBLY_ORDER

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

    # ══════════════════════════════════════════════════════════
    # 메인 실행
    # ══════════════════════════════════════════════════════════

    async def run(self, input_data: dict[str, Any]) -> PipelineResult:
        """전체 8단계 파이프라인 비동기 실행."""
        logger.info("=" * 60)
        logger.info("PROPOSAL PIPELINE START — 8-Step Workflow")
        logger.info("=" * 60)

        # Step 1-2: Parse & Classify
        await self._step1_2_parse_and_classify(input_data)

        # Step 3-4: Dispatch & Collect (병렬 그룹별 실행)
        await self._step3_4_dispatch_and_collect(input_data)

        # Step 5: Narrative rewriting
        await self._step5_narrative_rewrite()

        # Step 6: Template compliance
        await self._step6_template_compliance()

        # Step 7: QA review
        await self._step7_qa_review()

        # Step 8: Final assembly
        self._step8_assemble()

        logger.info("=" * 60)
        logger.info("PROPOSAL PIPELINE COMPLETE — %d slides assembled",
                     len(self.result.final_slide_blocks))
        logger.info("=" * 60)

        return self.result

    def run_sync(self, input_data: dict[str, Any]) -> PipelineResult:
        """동기 래퍼."""
        return asyncio.run(self.run(input_data))

    # ══════════════════════════════════════════════════════════
    # Step 1-2: Parse & Classify
    # ══════════════════════════════════════════════════════════

    async def _step1_2_parse_and_classify(self, input_data: dict[str, Any]) -> None:
        logger.info("[Step 1-2] 입력 자료 파싱 및 정보 분류")

        user_msg = (
            "아래 원본 입력 자료를 분석하여:\n"
            "1) 프로젝트 이해 (이 자산의 매각 자문 배경)\n"
            "2) 데이터를 에이전트별 범주로 분류\n"
            "3) 누락 데이터 식별\n"
            "4) 에이전트 배정 계획 수립\n"
            "5) 커버 슬라이드 콘텐츠 초안\n\n"
            f"```json\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n```"
        )
        result = await self.llm.ainvoke(ORCHESTRATOR_SYSTEM_PROMPT, user_msg)
        self.result.project_understanding = result

        missing = result.get("missing_data", [])
        if missing:
            self.result.all_missing_data.extend(missing)
            logger.warning("[Step 1-2] 누락 데이터: %s", missing)

        logger.info("[Step 1-2] 완료 — 매각 서사: %s",
                     result.get("sale_narrative_thesis", "N/A"))

    # ══════════════════════════════════════════════════════════
    # Step 3-4: Dispatch & Collect
    # ══════════════════════════════════════════════════════════

    async def _step3_4_dispatch_and_collect(self, input_data: dict[str, Any]) -> None:
        logger.info("[Step 3-4] 에이전트 배정 및 결과 수집")

        context = {
            "asset_data": input_data.get("asset_data", {}),
            "location_data": input_data.get("location_data", {}),
            "market_data": input_data.get("market_data", {}),
        }

        # ── Parallel Group 1: 기반 분석 (서로 의존성 없음) ──
        logger.info("[Step 3] Group 1 — asset, location, market, buyer (병렬)")
        g1_results = await asyncio.gather(
            self.asset_agent.arun(context),
            self.location_agent.arun(context),
            self.market_agent.arun(context),
            self.buyer_agent.arun(context),
        )

        self.result.agent_results["asset_analysis"] = g1_results[0]
        self.result.agent_results["location_demand"] = g1_results[1]
        self.result.agent_results["market_analysis"] = g1_results[2]
        self.result.agent_results["buyer_segmentation"] = g1_results[3]

        self._collect_metadata(g1_results)
        logger.info("[Step 3] Group 1 완료")

        # ── Parallel Group 2: 파생 분석 (G1 결과 필요) ──────
        logger.info("[Step 3] Group 2 — valuation, enduser (병렬)")
        g1_context = {
            **context,
            "asset_analysis_result": g1_results[0].model_dump(),
            "location_demand_result": g1_results[1].model_dump(),
            "market_analysis_result": g1_results[2].model_dump(),
            "buyer_segmentation_result": g1_results[3].model_dump(),
        }

        g2_results = await asyncio.gather(
            self.valuation_agent.arun(g1_context),
            self.enduser_agent.arun(g1_context),
        )

        self.result.agent_results["valuation"] = g2_results[0]
        self.result.agent_results["enduser_strategy"] = g2_results[1]

        self._collect_metadata(g2_results)
        logger.info("[Step 3] Group 2 완료")

        # ── Sequential: deal_strategy (G1+G2 결과 필요) ─────
        logger.info("[Step 3] deal_strategy (순차)")
        g2_context = {
            **g1_context,
            "valuation_result": g2_results[0].model_dump(),
            "enduser_strategy_result": g2_results[1].model_dump(),
        }

        deal_result = await self.deal_agent.arun(g2_context)
        self.result.agent_results["deal_strategy"] = deal_result
        self._collect_metadata([deal_result])
        logger.info("[Step 3] deal_strategy 완료")

        # ── Sequential: execution_plan (deal_strategy 결과 필요) ─
        logger.info("[Step 3] execution_plan (순차)")
        exec_context = {
            **context,
            "deal_strategy_result": deal_result.model_dump(),
        }

        exec_result = await self.execution_agent.arun(exec_context)
        self.result.agent_results["execution_plan"] = exec_result
        self._collect_metadata([exec_result])
        logger.info("[Step 3] execution_plan 완료")

        # ── Cover / Credentials / Track Record 프레임 생성 ──
        logger.info("[Step 3] cover/credentials/track_record 프레임 생성")
        await self._generate_framing_sections(input_data)

        logger.info("[Step 4] 전체 에이전트 결과 수집 완료 — %d개 에이전트",
                     len(self.result.agent_results))

    async def _generate_framing_sections(self, input_data: dict[str, Any]) -> None:
        """커버, 자격, 실적 섹션의 뼈대 슬라이드를 생성."""
        cover_content = self.result.project_understanding.get("cover_slide_content", {})
        user_msg = (
            "아래 프로젝트 정보를 기반으로 다음 3개 섹션의 슬라이드 블록을 생성해주세요:\n"
            "1. cover — 표지/자문 범위 이해\n"
            "2. credentials — Why Us / 자격\n"
            "3. track_record — 실적/팀/수수료 (뼈대만)\n\n"
            f"프로젝트 이해:\n```json\n{json.dumps(cover_content, ensure_ascii=False, indent=2)}\n```\n\n"
            f"자산 개요:\n```json\n{json.dumps(input_data.get('asset_data', {}), ensure_ascii=False, indent=2)}\n```"
        )

        raw = await self.llm.ainvoke(COVER_CREDENTIALS_PROMPT, user_msg)

        # 파싱
        slide_blocks = raw.get("slide_blocks", [])
        if not isinstance(slide_blocks, list):
            slide_blocks = []

        framing_output = AgentOutput(
            agent_name="proposal_orchestrator",
            section_name="framing sections",
            objective="generate cover, credentials, and track record frames",
            key_message=raw.get("key_message", ""),
            slide_blocks=slide_blocks,
        )
        self.result.agent_results["framing"] = framing_output

    # ══════════════════════════════════════════════════════════
    # Step 5: Narrative Rewrite
    # ══════════════════════════════════════════════════════════

    async def _step5_narrative_rewrite(self) -> None:
        logger.info("[Step 5] 슬라이드 서사 정제")

        all_blocks = self._collect_all_slide_blocks_as_dicts()
        section_order = [
            {"section_id": s["section_id"], "section_name": s["section_name"]}
            for s in FINAL_ASSEMBLY_ORDER
        ]

        context = {
            "all_slide_blocks": all_blocks,
            "section_order": section_order,
        }

        self.result.narrative_result = await self.narrative_agent.arun(context)

        logger.info(
            "[Step 5] 완료 — 정제된 슬라이드 %d장",
            len(self.result.narrative_result.slide_blocks)
            if self.result.narrative_result
            else 0,
        )

    # ══════════════════════════════════════════════════════════
    # Step 6: Template Compliance
    # ══════════════════════════════════════════════════════════

    async def _step6_template_compliance(self) -> None:
        logger.info("[Step 6] 템플릿 준수 검증")

        # narrative_result의 블록 사용, 없으면 원본
        if self.result.narrative_result and self.result.narrative_result.slide_blocks:
            blocks = [
                sb.model_dump() if hasattr(sb, "model_dump") else sb
                for sb in self.result.narrative_result.slide_blocks
            ]
        else:
            blocks = self._collect_all_slide_blocks_as_dicts()

        self.result.template_reviews = await self.template_guardian.areview_all_blocks(
            blocks
        )

        # 결과 처리: accept/revise → 사용, split → 분할, reject → 제거
        approved_blocks: list[dict[str, Any]] = []
        rejected_count = 0

        for i, review in enumerate(self.result.template_reviews):
            if review.content_decision == "reject":
                rejected_count += 1
                logger.warning("[Step 6] 슬라이드 %d 거부됨: %s", i, review.density_warning)
                continue

            if review.content_decision == "split" and review.split_suggestion:
                # 분할된 두 블록 추가
                b1 = review.split_suggestion.get("block_1")
                b2 = review.split_suggestion.get("block_2")
                if b1:
                    approved_blocks.append(b1)
                if b2:
                    approved_blocks.append(b2)
            elif review.final_template_ready_block:
                approved_blocks.append(review.final_template_ready_block.model_dump())
            elif i < len(blocks):
                # 원본 유지 (수동 검토 필요)
                approved_blocks.append(blocks[i])

        logger.info(
            "[Step 6] 완료 — 승인 %d장, 거부 %d장",
            len(approved_blocks),
            rejected_count,
        )

        # 임시 저장 (Step 7-8에서 사용)
        self.result.final_slide_blocks = approved_blocks

    # ══════════════════════════════════════════════════════════
    # Step 7: QA Review
    # ══════════════════════════════════════════════════════════

    async def _step7_qa_review(self) -> None:
        logger.info("[Step 7] 최종 QA 검토")

        # 섹션별로 그룹화하여 QA에 전달
        assembled = self._group_blocks_by_section(self.result.final_slide_blocks)

        self.result.qa_result = await self.qa_agent.areview(
            assembled,
            FINAL_ASSEMBLY_ORDER,
        )

        logger.info(
            "[Step 7] QA 완료 — 전체 점수: %s, 서사 일관성: %s, 판정: %s",
            self.result.qa_result.overall_score,
            self.result.qa_result.narrative_coherence_score,
            self.result.qa_result.final_recommendation,
        )

    # ══════════════════════════════════════════════════════════
    # Step 8: Final Assembly
    # ══════════════════════════════════════════════════════════

    def _step8_assemble(self) -> None:
        """최종 제안서를 섹션 순서대로 조립."""
        logger.info("[Step 8] 최종 제안서 조립")

        assembled = self._group_blocks_by_section(self.result.final_slide_blocks)
        self.result.assembled_proposal = assembled

        # 순서대로 평탄화
        ordered_blocks: list[dict[str, Any]] = []
        for section in FINAL_ASSEMBLY_ORDER:
            sid = section["section_id"]
            section_blocks = assembled.get(sid, [])
            ordered_blocks.extend(section_blocks)

            if not section_blocks:
                logger.warning(
                    "[Step 8] 섹션 '%s' (%s)에 슬라이드가 없습니다",
                    sid,
                    section["section_name"],
                )

        self.result.final_slide_blocks = ordered_blocks

        logger.info(
            "[Step 8] 조립 완료 — 총 %d장, %d개 섹션",
            len(ordered_blocks),
            len([s for s in FINAL_ASSEMBLY_ORDER if assembled.get(s["section_id"])]),
        )

    # ══════════════════════════════════════════════════════════
    # 유틸리티
    # ══════════════════════════════════════════════════════════

    def _collect_all_slide_blocks_as_dicts(self) -> list[dict[str, Any]]:
        """모든 에이전트 결과에서 슬라이드 블록을 dict 리스트로 수집."""
        blocks: list[dict[str, Any]] = []
        for output in self.result.agent_results.values():
            if output and output.slide_blocks:
                for sb in output.slide_blocks:
                    blocks.append(
                        sb.model_dump() if hasattr(sb, "model_dump") else sb
                    )
        return blocks

    def _group_blocks_by_section(
        self, blocks: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """슬라이드 블록을 proposal_section별로 그룹화."""
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for block in blocks:
            section = block.get("proposal_section", "unassigned")
            if not section:
                section = "unassigned"
            grouped[section].append(block)
        return dict(grouped)

    def _collect_metadata(self, outputs: list[AgentOutput]) -> None:
        """에이전트 결과에서 missing_data, human_validation 수집."""
        for output in outputs:
            if output.missing_data:
                self.result.all_missing_data.extend(output.missing_data)
            if output.requires_human_validation:
                self.result.all_human_validation.extend(output.requires_human_validation)
            if output.risks_or_gaps:
                self.result.all_missing_data.extend(output.risks_or_gaps)

    def save_output(self, output_dir: str | Path | None = None) -> Path:
        """결과를 JSON 파일로 저장."""
        out_dir = Path(output_dir or self.settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 전체 결과
        output_path = out_dir / "proposal_output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, ensure_ascii=False, indent=2)

        # 최종 슬라이드 블록 (순서대로)
        slides_path = out_dir / "final_slides.json"
        with open(slides_path, "w", encoding="utf-8") as f:
            json.dump(self.result.final_slide_blocks, f, ensure_ascii=False, indent=2)

        # 섹션별 조립 결과
        assembled_path = out_dir / "assembled_proposal.json"
        with open(assembled_path, "w", encoding="utf-8") as f:
            json.dump(self.result.assembled_proposal, f, ensure_ascii=False, indent=2)

        # 수동 검토 필요 항목
        review_path = out_dir / "human_review_items.json"
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "missing_data": self.result.all_missing_data,
                    "human_validation": self.result.all_human_validation,
                    "qa_result": (
                        self.result.qa_result.model_dump()
                        if self.result.qa_result and hasattr(self.result.qa_result, "model_dump")
                        else {}
                    ),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info("결과 저장 완료: %s", out_dir)
        return out_dir
