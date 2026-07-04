"""Ollama API provider."""

from __future__ import annotations

from voiceflow.llm.providers.base_api import APIProviderBase
from voiceflow.core.exceptions import LLMInferenceError


class OllamaProvider(APIProviderBase):
    """Provider for local Ollama instances."""

    async def refine(self, raw_text: str) -> str:
        if not self._client:
            raise LLMInferenceError("Ollama client not loaded.")
            
        url = self._config.api_base or "http://localhost:11434"
        url = url.rstrip("/") + "/api/chat"
        
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": raw_text}
            ],
            "stream": False,
            "options": {
                "temperature": self._config.temperature,
                "num_predict": self._config.max_tokens,
            }
        }
        
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
        except Exception as e:
            raise LLMInferenceError(f"Ollama inference failed: {e}") from e
