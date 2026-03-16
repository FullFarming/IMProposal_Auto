"""
전역 설정.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Anthropic API
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8_192
    temperature: float = 0.3

    # 파이프라인
    max_parallel_agents: int = 4
    output_dir: str = "output"

    # 템플릿 가드레일
    max_bullets_per_slide: int = 5
    max_slides_per_section: int = 6
    template_fit_threshold: int = 70  # 이 점수 미만이면 재작성

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()
