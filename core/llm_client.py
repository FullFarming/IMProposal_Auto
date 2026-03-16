"""
Anthropic API 래퍼 — 모든 에이전트가 이 클라이언트를 통해 LLM을 호출한다.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from config.settings import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    """얇은 Anthropic wrapper. system prompt + user message → 구조화 JSON 반환."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """LLM 호출 후 JSON dict 반환. 파싱 실패 시 raw text를 감싸 반환."""
        response = self.client.messages.create(
            model=self.settings.model,
            max_tokens=max_tokens or self.settings.max_tokens,
            temperature=temperature if temperature is not None else self.settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # JSON 블록 추출 시도
        json_text = raw
        if "```json" in raw:
            json_text = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            json_text = raw.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패 — raw text 반환")
            return {"raw_text": raw}

    async def ainvoke(
        self,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """비동기 LLM 호출."""
        async_client = anthropic.AsyncAnthropic(
            api_key=self.settings.anthropic_api_key
        )
        response = await async_client.messages.create(
            model=self.settings.model,
            max_tokens=max_tokens or self.settings.max_tokens,
            temperature=temperature if temperature is not None else self.settings.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        json_text = raw
        if "```json" in raw:
            json_text = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            json_text = raw.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패 — raw text 반환")
            return {"raw_text": raw}
