"""
모든 하위 에이전트의 공통 베이스 클래스.

핵심 변경: system_prompt()의 반환값에 공통 디자인/템플릿 준수 규칙과
워크플로우 컨텍스트를 자동 주입한다. 서브클래스는 _agent_prompt()만 구현하면 된다.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from core.llm_client import LLMClient
from schemas.slide_block import AgentOutput
from agents.common_rules import DESIGN_COMPLIANCE_RULES, OPERATING_WORKFLOW_RULES

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """하위 에이전트 공통 인터페이스."""

    name: str = "base_agent"
    section_name: str = ""
    objective: str = ""

    # 이 에이전트가 담당하는 제안서 섹션 ID (FINAL_ASSEMBLY_ORDER 참조)
    proposal_section_id: str = ""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # ── 서브클래스가 구현 ──────────────────────────────────

    @abstractmethod
    def _agent_prompt(self) -> str:
        """에이전트 고유 시스템 프롬프트. 공통 규칙은 자동 주입된다."""

    @abstractmethod
    def build_user_message(self, context: dict[str, Any]) -> str:
        """context dict → LLM user message 문자열."""

    # ── 공통 프롬프트 조합 ─────────────────────────────────

    def system_prompt(self) -> str:
        """에이전트 고유 프롬프트 + 공통 디자인 규칙 + 워크플로우 컨텍스트."""
        return (
            self._agent_prompt()
            + "\n\n"
            + DESIGN_COMPLIANCE_RULES
            + "\n\n"
            + OPERATING_WORKFLOW_RULES
        )

    # ── 공통 실행 ──────────────────────────────────────────

    def run(self, context: dict[str, Any]) -> AgentOutput:
        """동기 실행."""
        logger.info("[%s] 실행 시작", self.name)
        user_msg = self.build_user_message(context)
        raw = self.llm.invoke(self.system_prompt(), user_msg)
        return self._parse(raw)

    async def arun(self, context: dict[str, Any]) -> AgentOutput:
        """비동기 실행."""
        logger.info("[%s] 비동기 실행 시작", self.name)
        user_msg = self.build_user_message(context)
        raw = await self.llm.ainvoke(self.system_prompt(), user_msg)
        return self._parse(raw)

    # ── 파싱 ───────────────────────────────────────────────

    def _parse(self, raw: dict[str, Any]) -> AgentOutput:
        """LLM 응답 dict → AgentOutput. 실패 시 raw_extras에 보관."""
        try:
            slide_blocks = raw.get("slide_blocks", [])
            if not isinstance(slide_blocks, list):
                slide_blocks = []

            # 각 슬라이드 블록에 proposal_section 태그 주입
            for block in slide_blocks:
                if isinstance(block, dict) and not block.get("proposal_section"):
                    block["proposal_section"] = self.proposal_section_id

            return AgentOutput(
                agent_name=raw.get("agent_name", self.name),
                section_name=raw.get("section_name", self.section_name),
                objective=raw.get("objective", self.objective),
                key_message=raw.get("key_message", ""),
                insights=raw.get("insights", []),
                slide_blocks=slide_blocks,
                risks_or_gaps=raw.get("risks_or_gaps", []),
                requires_human_validation=raw.get("requires_human_validation", []),
                raw_extras={
                    k: v
                    for k, v in raw.items()
                    if k
                    not in {
                        "agent_name",
                        "section_name",
                        "objective",
                        "key_message",
                        "insights",
                        "slide_blocks",
                        "risks_or_gaps",
                        "requires_human_validation",
                    }
                },
            )
        except Exception as exc:
            logger.warning("[%s] 파싱 실패: %s", self.name, exc)
            return AgentOutput(
                agent_name=self.name,
                section_name=self.section_name,
                objective=self.objective,
                raw_extras=raw,
            )
