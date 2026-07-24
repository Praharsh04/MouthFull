"""Groq API provider."""

from __future__ import annotations

from mouthfull.utils.exceptions import LLMInferenceError
from mouthfull.backend.llm.providers.base_api import APIProviderBase


class GroqProvider(APIProviderBase):
    """Provider for Groq."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("Groq client not loaded.")

        api_key = self._api_keys.groq_api_key
        if not api_key:
            raise LLMInferenceError("Groq API key is missing.")

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
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
        
        from mouthfull.utils.logger import logger
        logger.debug(f"Provider: groq | Model: {self._config.model} | Endpoint: {url} | Payload: {payload}")

        try:
            response = await self._client.post(url, headers=headers, json=payload)
            if response.status_code == 429:
                raise LLMInferenceError("Rate limit exceeded for Groq API.")
            elif response.status_code == 401:
                raise LLMInferenceError("Invalid Groq API Key.")
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMInferenceError(f"Groq inference failed: {e}") from e
