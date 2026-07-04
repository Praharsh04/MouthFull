"""OpenRouter API provider."""

from __future__ import annotations

from mouthfull.utils.exceptions import LLMInferenceError
from mouthfull.backend.llm.providers.openai import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    """Provider for OpenRouter (OpenAI-compatible)."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("OpenRouter client not loaded.")

        api_key = self._api_keys.openrouter_api_key
        if not api_key:
            raise LLMInferenceError("OpenRouter API key is missing.")

        url = self._config.api_base or "https://openrouter.ai/api/v1"
        url = url.rstrip("/") + "/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/mouthfull",
            "X-Title": "MouthFull Local",
            "Content-Type": "application/json"
        }

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
            raise LLMInferenceError(f"OpenRouter inference failed: {e}") from e
