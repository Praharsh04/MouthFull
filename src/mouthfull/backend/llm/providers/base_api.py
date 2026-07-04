"""Base API Provider class for remote LLMs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from mouthfull.backend.llm.base import LLMEngine

if TYPE_CHECKING:
    from mouthfull.configs.config import APIKeys, LLMConfig


class APIProviderBase(LLMEngine):
    """Base class for HTTP-based LLM providers."""

    def __init__(self, config: LLMConfig, api_keys: APIKeys) -> None:
        self._config = config
        self._api_keys = api_keys
        self._client: httpx.AsyncClient | None = None

    async def load_model(self) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(timeout=30.0)

    async def unload_model(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_system_prompt(self) -> str:
        """Get the system prompt based on config.prompt_template."""
        from mouthfull.backend.llm.prompts import get_template
        return get_template(self._config.prompt_template)
