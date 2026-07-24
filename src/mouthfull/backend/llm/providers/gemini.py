"""Gemini API provider."""

from __future__ import annotations

from mouthfull.utils.exceptions import LLMInferenceError
from mouthfull.backend.llm.providers.base_api import APIProviderBase


class GeminiProvider(APIProviderBase):
    """Provider for Google Gemini."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("Gemini client not loaded.")

        api_key = self._api_keys.gemini_api_key
        if not api_key:
            raise LLMInferenceError("Gemini API key is missing.")

        # Default: gemini-3.5-flash
        model = self._config.model if self._config.model else "gemini-3.5-flash"
        
        # Validation
        if not model.startswith("gemini"):
            from mouthfull.utils.logger import logger
            logger.error(f"Invalid model '{model}' for Gemini provider. Reverting to default.")
            model = "gemini-3.5-flash"

        base_url = self._config.api_base or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}"

        payload = {
            "systemInstruction": {
                "parts": [{"text": self._build_system_prompt()}]
            },
            "contents": [{
                "parts": [{"text": raw_text}]
            }],
            "generationConfig": {
                "temperature": self._config.temperature,
                "maxOutputTokens": self._config.max_tokens,
            }
        }
        
        from mouthfull.utils.logger import logger
        logger.debug(f"Provider: gemini | Model: {model} | Endpoint: {url.split('?')[0]} | Payload: {payload}")

        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise LLMInferenceError(f"Gemini inference failed: {e}") from e
