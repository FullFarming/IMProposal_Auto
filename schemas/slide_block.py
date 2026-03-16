"""
공통 슬라이드 블록 스키마 — 모든 에이전트가 이 형식으로 출력한다.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SlideBlock(BaseModel):
    """단일 슬라이드 블록. 모든 에이전트가 이 단위로 결과를 생산한다."""

    slide_title: str = Field(..., description="결론형 제목")
    slide_purpose: str = Field(..., description="이 슬라이드가 존재하는 이유")
    headline: str = Field(..., description="핵심 메시지 1줄")
    body_bullets: list[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=7,
        description="본문 bullet 3~5개 (최대 7)",
    )
    evidence_points: list[str] = Field(
        default_factory=list, description="근거 데이터 포인트"
    )
    recommended_visual: str = Field(
        "", description="표/차트/다이어그램 등 시각화 제안"
    )
    layout_guidance: str = Field(
        "", description="템플릿상 배치 권장 영역"
    )
    template_notes: str = Field(
        "", description="템플릿 준수 관련 참고사항"
    )
    speaker_note: str = Field("", description="발표자 메모")
    proposal_section: str = Field(
        "",
        description=(
            "이 슬라이드가 속하는 제안서 섹션 ID. "
            "cover / credentials / asset_understanding / market_context / "
            "pricing_logic / buyer_strategy / sale_strategy / "
            "execution_plan / track_record"
        ),
    )


class AgentOutput(BaseModel):
    """모든 하위 에이전트의 공통 반환 스키마."""

    agent_name: str
    section_name: str
    objective: str
    key_message: str = ""
    insights: list[str] = Field(default_factory=list)
    slide_blocks: list[SlideBlock] = Field(default_factory=list)
    risks_or_gaps: list[str] = Field(default_factory=list)
    requires_human_validation: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    raw_extras: dict = Field(
        default_factory=dict,
        description="에이전트별 추가 필드 (buyer_segments, valuation_range 등)",
    )
