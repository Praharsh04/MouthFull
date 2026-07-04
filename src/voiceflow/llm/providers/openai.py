"""OpenAI API provider."""

from __future__ import annotations

from voiceflow.llm.providers.base_api import APIProviderBase
from voiceflow.core.exceptions import LLMInferenceError


class OpenAIProvider(APIProviderBase):
    """Provider for OpenAI."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("OpenAI client not loaded.")
            
        api_key = self._api_keys.openai_api_key
        if not api_key:
            raise LLMInferenceError("OpenAI API key is missing.")
            
        url = self._config.api_base or "https://api.openai.com/v1"
        url = url.rstrip("/") + "/chat/completions"
        
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
        
        try:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMInferenceError(f"OpenAI inference failed: {e}") from e
