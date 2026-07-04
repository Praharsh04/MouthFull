"""Anthropic API provider."""

from __future__ import annotations

from voiceflow.core.exceptions import LLMInferenceError
from voiceflow.llm.providers.base_api import APIProviderBase


class AnthropicProvider(APIProviderBase):
    """Provider for Anthropic."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("Anthropic client not loaded.")

        api_key = self._api_keys.anthropic_api_key
        if not api_key:
            raise LLMInferenceError("Anthropic API key is missing.")

        url = self._config.api_base or "https://api.anthropic.com/v1"
        url = url.rstrip("/") + "/messages"

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self._config.model,
            "system": self._build_system_prompt(),
            "messages": [
                {"role": "user", "content": raw_text}
            ],
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"].strip()
        except Exception as e:
            raise LLMInferenceError(f"Anthropic inference failed: {e}") from e
