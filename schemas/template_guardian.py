"""
template_guardian 전용 출력 스키마.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .slide_block import SlideBlock


class TemplateGuardianOutput(BaseModel):
    agent_name: str = "template_guardian"
    template_fit_score: int = Field(..., ge=0, le=100)
    content_decision: str = Field(
        ..., description="accept / revise / split / reject"
    )
    title_rewrite: str = ""
    headline_rewrite: str = ""
    recommended_visual: str = ""
    layout_guidance: str = ""
    density_warning: str = ""
    rewrite_rules: list[str] = Field(default_factory=list)
    final_template_ready_block: SlideBlock | None = None
