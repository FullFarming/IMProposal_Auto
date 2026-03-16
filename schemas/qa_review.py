"""
qa_review_agent 전용 출력 스키마.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class QAReviewOutput(BaseModel):
    agent_name: str = "qa_review_agent"
    overall_score: int = Field(..., ge=0, le=100)
    narrative_coherence_score: int = Field(
        default=0, ge=0, le=100,
        description="전체 제안서의 서사 일관성 점수",
    )
    section_completeness: dict[str, str] = Field(
        default_factory=dict,
        description="섹션별 완성도 (ok / missing / weak)",
    )
    critical_issues: list[str] = Field(default_factory=list)
    logic_issues: list[str] = Field(default_factory=list)
    template_issues: list[str] = Field(default_factory=list)
    duplication_issues: list[str] = Field(default_factory=list)
    transition_issues: list[str] = Field(
        default_factory=list,
        description="섹션 전환 시 끊김/부자연스러운 부분",
    )
    human_validation_required: list[str] = Field(default_factory=list)
    final_recommendation: str = Field(
        ..., description="approve / revise / partial approve"
    )
