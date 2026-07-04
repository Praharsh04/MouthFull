"""Custom API provider."""

from __future__ import annotations

from voiceflow.core.exceptions import LLMInferenceError
from voiceflow.llm.providers.openai import OpenAIProvider


class CustomAPIProvider(OpenAIProvider):
    """Provider for a Custom API (OpenAI-compatible)."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("Custom API client not loaded.")

        api_key = self._api_keys.custom_api_key
        if not self._config.api_base:
            raise LLMInferenceError("api_base must be provided for custom API.")

        url = self._config.api_base.rstrip("/") + "/chat/completions"

        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": raw_text}
            ],
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMInferenceError(f"Custom API inference failed: {e}") from e
