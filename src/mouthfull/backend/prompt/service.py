"""Prompt Processor service.

Intercepts TranscriptReady, injects the transcription into a user-defined prompt template,
and emits PromptReady for the LLM.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from mouthfull.utils.events import TranscriptReady, PromptReady, RefinedTextReady, PipelineAbort, StatusChanged
from mouthfull.utils.logger import logger

if TYPE_CHECKING:
    from mouthfull.configs.config import PromptProcessorConfig
    from mouthfull.utils.events import EventBus


class PromptProcessorService:
    """Service to handle wrapping transcripts in a prompt template.

    Architecture:
        - When ENABLED:  TranscriptReady → PromptReady (routed to LLM) → RefinedTextReady
        - When DISABLED: TranscriptReady → RefinedTextReady directly (zero-latency bypass)

    The Prompt Processor toggle is the single source of truth for whether
    the LLM pipeline is engaged.  There is no separate LLM toggle.
    """

    def __init__(self, config: PromptProcessorConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._aborted = False
        
        # We will compute lowercase keys on the fly to support dynamic config updates

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

        if not event.text.strip():
            await self._bus.emit(StatusChanged(status="idle", message=""))
            return

        if not self._config.enabled:
            # ── Fast path: bypass LLM entirely, emit directly to injector ──
            logger.info("Prompt Processor disabled. Bypassing LLM and emitting RefinedTextReady.")
            await self._bus.emit(RefinedTextReady(text=event.text))
            return

        # ── Slow path: wrap in prompt template and route through LLM ──
        logger.info("Applying prompt template to transcript...")
        try:
            template = self._config.default_prompt
            
            process_name, display_name = event.app_context if event.app_context else (None, None)
            
            if process_name:
                logger.info("Detected app context: '{}' ({})", display_name, process_name)
                process_name_lower = process_name.lower()
                # Build lowercased mapping on the fly to support dynamic config updates
                app_prompts_lower = {
                    k.lower(): v.prompt for k, v in self._config.app_prompts.items()
                }
                if process_name_lower in app_prompts_lower:
                    template = app_prompts_lower[process_name_lower]
                    logger.debug("Using context-specific template for '{}'", display_name)
            
            # Replace placeholder with actual transcript
            prompt = template.replace("{{input}}", event.text)
            
            if self._aborted:
                return

            logger.debug(f"Generated prompt: {prompt}")
            await self._bus.emit(PromptReady(text=prompt, is_prompt=True))

        except Exception as e:
            logger.error(f"Prompt processing failed: {e}")
            # Fallback: emit raw text directly to avoid pipeline stall
            await self._bus.emit(RefinedTextReady(text=event.text))
