"""
모든 하위 에이전트의 공통 베이스 클래스.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from core.llm_client import LLMClient
from schemas.slide_block import AgentOutput

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """하위 에이전트 공통 인터페이스."""

    name: str = "base_agent"
    section_name: str = ""
    objective: str = ""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # ── 서브클래스가 구현 ──────────────────────────────────
    @abstractmethod
    def system_prompt(self) -> str:
        """에이전트 시스템 프롬프트."""

    @abstractmethod
    def build_user_message(self, context: dict[str, Any]) -> str:
        """context dict → LLM user message 문자열."""

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
            # slide_blocks가 리스트인지 확인
            slide_blocks = raw.get("slide_blocks", [])
            if not isinstance(slide_blocks, list):
                slide_blocks = []

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
