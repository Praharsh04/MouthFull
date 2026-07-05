"""LLM Refinement service.

Listens for TranscriptReady events, runs the configured LLM provider,
and emits RefinedTextReady.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from mouthfull.configs.config import APIKeys
from mouthfull.utils.events import PipelineError, RefinedTextReady, StatusChanged, PromptReady
from mouthfull.utils.logger import logger
from mouthfull.backend.llm.providers import get_provider

if TYPE_CHECKING:
    from mouthfull.configs.config import LLMConfig
    from mouthfull.utils.events import EventBus
    from mouthfull.backend.llm.base import LLMEngine


class LLMService:
    """Service to handle text refinement using LLMs.

    The LLM is always initialized when the service starts.  Whether it
    actually receives work is controlled by the Prompt Processor: when the
    Prompt Processor is disabled it emits RefinedTextReady directly and
    no PromptReady event ever reaches this service.
    """

    def __init__(self, config: LLMConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._engine: LLMEngine | None = None
        self._api_keys = APIKeys()
        self._loop = asyncio.get_running_loop()
        self._aborted = False

    async def start(self) -> None:
        """Subscribe to events. The model will be loaded lazily on first use."""
        from mouthfull.utils.events import PipelineAbort
        self._bus.subscribe(PipelineAbort, self._on_abort)
        self._bus.subscribe(PromptReady, self._on_prompt_ready)
        logger.info("LLM Service started (model will load lazily).")

    async def stop(self) -> None:
        """Unsubscribe and unload the model."""
        from mouthfull.utils.events import PipelineAbort
        self._bus.unsubscribe(PipelineAbort, self._on_abort)
        self._bus.unsubscribe(PromptReady, self._on_prompt_ready)
        if self._engine:
            await self._engine.unload_model()
            self._engine = None
        logger.info("LLM Service stopped.")

    async def _on_abort(self, event) -> None:
        self._aborted = True

    async def _on_prompt_ready(self, event: PromptReady) -> None:
        self._aborted = False
        if not getattr(event, 'is_prompt', True):
            # Pass-through if event is not a prompt
            logger.info("LLM Service received non-prompt text. Passing through to TextInjector.")
            await self._bus.emit(RefinedTextReady(text=event.text))
            return

        # Lazy load the engine on first use
        if not self._engine:
            logger.info("Initializing LLM Provider lazily: {}", self._config.provider)
            await self._bus.emit(StatusChanged(status="processing", message="Loading LLM..."))
            try:
                from mouthfull.backend.llm.providers import get_provider
                provider_cls = get_provider(self._config.provider)
                self._engine = provider_cls(self._config, self._api_keys)
                await self._engine.load_model()
            except Exception as e:
                logger.error("Failed to load LLM Provider: {}", e)
                await self._bus.emit(PipelineError(stage="llm_load", error=e))
                await self._bus.emit(RefinedTextReady(text=event.text))
                return

        logger.info("Stage: LLM Request - Sending prompt to LLM provider '{}'", self._config.provider)
        await self._bus.emit(StatusChanged(status="processing", message="Refining..."))

        try:
            import time
            start_time = time.perf_counter()
            refined_text = await self._engine.refine(event.text)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            from mouthfull.utils.events import PipelineTiming
            await self._bus.emit(PipelineTiming(stage="llm", duration_ms=duration_ms))
            
            if self._aborted:
                logger.info("LLM aborted.")
                return

            logger.info("Stage: LLM Response - Received: '{}'", refined_text)

            if refined_text.strip():
                await self._bus.emit(RefinedTextReady(text=refined_text))
            else:
                logger.warning("Empty refinement result, falling back to raw.")
                await self._bus.emit(RefinedTextReady(text=event.text))

        except Exception as e:
            logger.error("LLM refinement failed: {}", e)
            await self._bus.emit(PipelineError(stage="llm_refine", error=e))
            await self._bus.emit(StatusChanged(status="error", message="LLM Error"))

            # Fallback to unrefined text
            await self._bus.emit(RefinedTextReady(text=event.text))
