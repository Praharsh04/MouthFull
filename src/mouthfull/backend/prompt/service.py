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

    @property
    def _app_prompts_cache(self):
        # Cache the lowercased mapping to support O(1) lookups
        # Re-evaluates if the config dictionary changes size or is updated
        if not hasattr(self, '_cached_prompts') or self._last_config_id != id(self._config.app_prompts):
            self._cached_prompts = {k.lower(): v for k, v in self._config.app_prompts.items()}
            self._last_config_id = id(self._config.app_prompts)
        return self._cached_prompts

    async def _on_transcript_ready(self, event: TranscriptReady) -> None:
        self._aborted = False

        if not event.text.strip():
            await self._bus.emit(StatusChanged(status="idle", message=""))
            return

        # ── Fast O(1) Application Lookup ──
        process_name, display_name = getattr(event, 'app_context', None) or (None, None)
        
        app_entry = None
        if process_name:
            app_entry = self._app_prompts_cache.get(process_name.lower())
            
        template = None
        provider = None
        model = None
        
        if app_entry:
            template = app_entry.prompt
            provider = app_entry.provider
            model = app_entry.model
            logger.info("Using Application Prompt for '{}'", display_name)
        elif self._config.default_prompt.strip():
            template = self._config.default_prompt
            provider = getattr(self._config, 'default_provider', None)
            model = getattr(self._config, 'default_model', None)
            logger.info("No app prompt found. Using Default Prompt.")
        else:
            logger.info("No matching prompt and no default prompt. Bypassing AI processing.")
            await self._bus.emit(RefinedTextReady(text=event.text))
            return

        # ── LLM Pipeline Path ──
        logger.info("Stage: Prompt Assembly - Applying template to transcript")
        try:
            
            # Replace placeholder with actual transcript
            if "{{transcription}}" in template:
                prompt = template.replace("{{transcription}}", event.text)
            elif "{{input}}" in template:
                prompt = template.replace("{{input}}", event.text)
            else:
                prompt = f"{template}\n\n{event.text}"
            
            if self._aborted:
                return

            logger.info(f"Stage: Prompt Assembly - Generated prompt: {prompt}")
            
            # Emit PromptReady with provider and model metadata attached
            prompt_event = PromptReady(
                text=prompt, 
                is_prompt=True,
                provider=provider,
                model=model
            )
            
            await self._bus.emit(prompt_event)

        except Exception as e:
            logger.error(f"Prompt processing failed: {e}")
            # Fallback: emit raw text directly to avoid pipeline stall
            await self._bus.emit(RefinedTextReady(text=event.text))
