"""Speech-to-Text orchestrator service.

Listens for SpeechDetected events, runs the configured STT engine,
and emits TranscriptReady.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from mouthfull.utils.events import PipelineError, SpeechDetected, StatusChanged, TranscriptReady
from mouthfull.utils.logger import logger
from mouthfull.backend.stt.whisper_stt import WhisperSTT

# ParakeetSTT will be imported dynamically if needed, to avoid import errors if not installed.

if TYPE_CHECKING:
    from mouthfull.configs.config import STTConfig
    from mouthfull.utils.events import EventBus
    from mouthfull.backend.stt.base import STTEngine


class STTService:
    """Service to handle speech transcription."""

    def __init__(self, config: STTConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._engine: STTEngine | None = None
        self._loop = asyncio.get_running_loop()
        self._aborted = False

    def _create_engine(self) -> STTEngine:
        if self._config.engine == "faster_whisper":
            return WhisperSTT(self._config)
        elif self._config.engine == "parakeet":
            from mouthfull.backend.stt.parakeet_stt import ParakeetSTT
            return ParakeetSTT(self._config)
        else:
            raise ValueError(f"Unknown STT engine: {self._config.engine}")

    async def start(self) -> None:
        """Initialize the engine and subscribe to events."""
        logger.info("Initializing STT Engine: {}", self._config.engine)
        self._engine = self._create_engine()
        try:
            await self._engine.load_model()
        except Exception as e:
            logger.exception("Failed to load STT model: {}", e)
            await self._bus.emit(PipelineError(stage="stt_load", error=e))
            return

        from mouthfull.utils.events import PipelineAbort
        self._bus.subscribe(SpeechDetected, self._on_speech_detected)
        self._bus.subscribe(PipelineAbort, self._on_abort)
        logger.info("STT Service started.")

    async def stop(self) -> None:
        """Unsubscribe and unload the model."""
        from mouthfull.utils.events import PipelineAbort
        self._bus.unsubscribe(SpeechDetected, self._on_speech_detected)
        self._bus.unsubscribe(PipelineAbort, self._on_abort)
        if self._engine:
            await self._engine.unload_model()
            self._engine = None
        logger.info("STT Service stopped.")

    async def _on_abort(self, event) -> None:
        self._aborted = True

    async def _on_speech_detected(self, event: SpeechDetected) -> None:
        self._aborted = False
        if not self._engine:
            return

        logger.info("Transcribing {} seconds of audio...", len(event.audio) / event.sample_rate)

        # Display progress in overlay
        await self._bus.emit(StatusChanged(status="processing", message="Transcribing..."))

        try:
            import time
            start_time = time.perf_counter()
            # Run transcription in a thread to not block asyncio if the engine is synchronous
            transcript = await asyncio.to_thread(
                self._run_transcription_sync, event.audio, event.sample_rate
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            from mouthfull.utils.events import PipelineTiming
            await self._bus.emit(PipelineTiming(stage="stt", duration_ms=duration_ms))

            if self._aborted:
                logger.info("STT aborted.")
                return

            logger.info("Transcription: {}", transcript)

            if transcript.strip():
                await self._bus.emit(TranscriptReady(text=transcript))
            else:
                logger.warning("Empty transcription result.")
                await self._bus.emit(StatusChanged(status="idle", message=""))

        except Exception as e:
            logger.error("Transcription failed: {}", e)
            await self._bus.emit(PipelineError(stage="stt_transcribe", error=e))
            await self._bus.emit(StatusChanged(status="error", message="STT Error"))

    def _run_transcription_sync(self, audio, sample_rate) -> str:
        """Wrapper to run the async/sync transcribe method in a thread safely.
        Because STTEngine.transcribe is marked as async, we use a new event loop.
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._engine.transcribe(audio, sample_rate))
        finally:
            loop.close()
