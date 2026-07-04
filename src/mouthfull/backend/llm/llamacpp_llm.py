"""Local llama.cpp engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mouthfull.backend.llm.base import LLMEngine
from mouthfull.utils.exceptions import LLMModelLoadError, LLMInferenceError
from mouthfull.utils.logger import logger

if TYPE_CHECKING:
    from mouthfull.configs.config import LLMConfig


class LlamaCppLLM(LLMEngine):
    """Local LLM refinement using llama.cpp."""

    def __init__(self, config: LLMConfig, api_keys: Any = None) -> None:
        self._config = config
        self._api_keys = api_keys
        self._llm = None

    async def load_model(self) -> None:
        """Load the model via llama_cpp."""
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise LLMModelLoadError("llama-cpp-python is not installed.") from e

        logger.info("Loading llama.cpp model from {}", self._config.model_path)
        try:
            self._llm = Llama(
                model_path=self._config.model_path,
                n_gpu_layers=self._config.n_gpu_layers,
                n_ctx=self._config.n_ctx,
                verbose=False
            )
            logger.info("llama.cpp model loaded.")
        except Exception as e:
            raise LLMModelLoadError(f"Failed to load llama.cpp model: {e}") from e

    async def refine(self, raw_text: str) -> str:
        """Refine using local model."""
        if not self._llm:
            raise LLMInferenceError("llama.cpp model not loaded.")
            
        from mouthfull.backend.llm.prompts import get_template
        system_prompt = get_template(self._config.prompt_template)
        
        try:
            import asyncio
            # Run inference in a thread to not block asyncio loop
            def _sync_infer():
                return self._llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text}
                    ],
                    max_tokens=self._config.max_tokens,
                    temperature=self._config.temperature,
                )
            
            response = await asyncio.to_thread(_sync_infer)
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMInferenceError(f"llama.cpp inference failed: {e}") from e

    async def unload_model(self) -> None:
        if self._llm is not None:
            logger.info("Unloading llama.cpp model...")
            del self._llm
            self._llm = None
