"""
qa_review_agent 전용 출력 스키마.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class QAReviewOutput(BaseModel):
    agent_name: str = "qa_review_agent"
    overall_score: int = Field(..., ge=0, le=100)
    critical_issues: list[str] = Field(default_factory=list)
    logic_issues: list[str] = Field(default_factory=list)
    template_issues: list[str] = Field(default_factory=list)
    duplication_issues: list[str] = Field(default_factory=list)
    human_validation_required: list[str] = Field(default_factory=list)
    final_recommendation: str = Field(
        ..., description="approve / revise / partial approve"
    )
