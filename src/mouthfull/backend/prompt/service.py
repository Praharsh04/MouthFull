"""Prompt Processor service.

Intercepts TranscriptReady, injects the transcription into a user-defined prompt template,
and emits PromptReady for the LLM.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from mouthfull.utils.events import TranscriptReady, PromptReady, PipelineAbort
from mouthfull.utils.logger import logger

if TYPE_CHECKING:
    from mouthfull.configs.config import PromptProcessorConfig
    from mouthfull.utils.events import EventBus


class PromptProcessorService:
    """Service to handle wrapping transcripts in a prompt template."""

    def __init__(self, config: PromptProcessorConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._aborted = False

    async def start(self) -> None:
        """Subscribe to events."""
        self._bus.subscribe(PipelineAbort, self._on_abort)
        self._bus.subscribe(TranscriptReady, self._on_transcript_ready)
        logger.info(f"Prompt Processor started (Enabled: {self._config.enabled})")

    async def stop(self) -> None:
        """Unsubscribe from events."""
        self._bus.unsubscribe(PipelineAbort, self._on_abort)
        self._bus.unsubscribe(TranscriptReady, self._on_transcript_ready)
        logger.info("Prompt Processor stopped.")

    async def _on_abort(self, event) -> None:
        self._aborted = True

    async def _on_transcript_ready(self, event: TranscriptReady) -> None:
        self._aborted = False

        if not self._config.enabled or not event.text.strip():
            # Pass-through
            await self._bus.emit(PromptReady(text=event.text))
            return

        logger.info("Applying prompt template to transcript...")
        try:
            # Replace placeholder with actual transcript
            prompt = self._config.template.replace("{{input}}", event.text)
            
            if self._aborted:
                return

            logger.debug(f"Generated prompt: {prompt}")
            await self._bus.emit(PromptReady(text=prompt))

        except Exception as e:
            logger.error(f"Prompt processing failed: {e}")
            # Fallback to unrefined text
            await self._bus.emit(PromptReady(text=event.text))
