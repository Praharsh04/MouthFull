"""LLM Refinement service.

Listens for TranscriptReady events, runs the configured LLM provider,
and emits RefinedTextReady.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from voiceflow.core.config import APIKeys
from voiceflow.core.events import PipelineError, RefinedTextReady, StatusChanged, TranscriptReady
from voiceflow.core.logger import logger
from voiceflow.llm.providers import get_provider

if TYPE_CHECKING:
    from voiceflow.core.config import LLMConfig
    from voiceflow.core.events import EventBus
    from voiceflow.llm.base import LLMEngine


class LLMService:
    """Service to handle text refinement using LLMs."""

    def __init__(self, config: LLMConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._engine: LLMEngine | None = None
        self._api_keys = APIKeys()
        self._loop = asyncio.get_running_loop()
        self._aborted = False

    async def start(self) -> None:
        """Initialize the LLM provider and subscribe to events."""
        from voiceflow.core.events import PipelineAbort
        self._bus.subscribe(PipelineAbort, self._on_abort)
        if not self._config.enabled:
            logger.info("LLM Service is disabled.")
            # If disabled, we should just pass the transcript through directly.
            # But we'll handle that in _on_transcript_ready.
            self._bus.subscribe(TranscriptReady, self._on_transcript_ready)
            return

        logger.info("Initializing LLM Provider: {}", self._config.provider)
        try:
            provider_cls = get_provider(self._config.provider)
            self._engine = provider_cls(self._config, self._api_keys)
            await self._engine.load_model()
        except Exception as e:
            logger.error("Failed to load LLM Provider: {}", e)
            await self._bus.emit(PipelineError(stage="llm_load", error=e))
            return

        self._bus.subscribe(TranscriptReady, self._on_transcript_ready)
        logger.info("LLM Service started.")

    async def stop(self) -> None:
        """Unsubscribe and unload the model."""
        from voiceflow.core.events import PipelineAbort
        self._bus.unsubscribe(PipelineAbort, self._on_abort)
        self._bus.unsubscribe(TranscriptReady, self._on_transcript_ready)
        if self._engine:
            await self._engine.unload_model()
            self._engine = None
        logger.info("LLM Service stopped.")

    async def _on_abort(self, event) -> None:
        self._aborted = True

    async def _on_transcript_ready(self, event: TranscriptReady) -> None:
        self._aborted = False
        if not self._config.enabled or not self._engine:
            # Pass-through if disabled
            await self._bus.emit(RefinedTextReady(text=event.text))
            return

        logger.info("Refining transcript: '{}'", event.text)
        await self._bus.emit(StatusChanged(status="processing", message="Refining..."))

        try:
            refined_text = await self._engine.refine(event.text)
            
            if self._aborted:
                logger.info("LLM aborted.")
                return

            logger.info("Refined text: '{}'", refined_text)

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
