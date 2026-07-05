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
        self._bg_loop: asyncio.AbstractEventLoop | None = None
        self._bg_thread: threading.Thread | None = None

    def _create_engine(self) -> STTEngine:
        if self._config.engine == "faster_whisper":
            return WhisperSTT(self._config)
        elif self._config.engine == "parakeet":
            from mouthfull.backend.stt.parakeet_stt import ParakeetSTT
            return ParakeetSTT(self._config)
        else:
            raise ValueError(f"Unknown STT engine: {self._config.engine}")

    def _run_bg_loop(self, loop: asyncio.AbstractEventLoop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def start(self) -> None:
        """Initialize the engine and subscribe to events."""
        import threading
        
        self._bg_loop = asyncio.new_event_loop()
        self._bg_thread = threading.Thread(target=self._run_bg_loop, args=(self._bg_loop,), daemon=True)
        self._bg_thread.start()
        
        logger.info("Initializing STT Engine: {}", self._config.engine)
        self._engine = self._create_engine()
        try:
            # Load model in the background loop
            future = asyncio.run_coroutine_threadsafe(self._engine.load_model(), self._bg_loop)
            await asyncio.wrap_future(future)
        except Exception as e:
            logger.warning("Failed to load STT model ({}): {}", self._config.engine, e)
            if self._config.engine == "parakeet":
                logger.info("Automatically falling back to faster_whisper STT engine...")
                self._config.engine = "faster_whisper"
                self._engine = self._create_engine()
                try:
                    future = asyncio.run_coroutine_threadsafe(self._engine.load_model(), self._bg_loop)
                    await asyncio.wrap_future(future)
                except Exception as fallback_err:
                    logger.exception("Fallback STT model also failed to load: {}", fallback_err)
                    await self._bus.emit(PipelineError(stage="stt_load", error=fallback_err))
                    return
            else:
                logger.exception("Fatal STT model load error.")
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
        if self._engine and self._bg_loop:
            future = asyncio.run_coroutine_threadsafe(self._engine.unload_model(), self._bg_loop)
            await asyncio.wrap_future(future)
            self._engine = None
            
        if self._bg_loop:
            self._bg_loop.call_soon_threadsafe(self._bg_loop.stop)
            if self._bg_thread:
                self._bg_thread.join(timeout=1.0)
            self._bg_loop.close()
            self._bg_loop = None
        logger.info("STT Service stopped.")

    async def _on_abort(self, event) -> None:
        self._aborted = True

    async def _on_speech_detected(self, event: SpeechDetected) -> None:
        self._aborted = False
        if not self._engine:
            return

        logger.info("Stage: STT - Transcribing {} seconds of audio...", len(event.audio) / event.sample_rate)

        # Display progress in overlay
        await self._bus.emit(StatusChanged(status="processing", message="Transcribing..."))

        try:
            import time
            start_time = time.perf_counter()
            
            # Submit to persistent background loop
            future = asyncio.run_coroutine_threadsafe(
                self._engine.transcribe(event.audio, event.sample_rate),
                self._bg_loop
            )
            transcript = await asyncio.wrap_future(future)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            from mouthfull.utils.events import PipelineTiming
            await self._bus.emit(PipelineTiming(stage="stt", duration_ms=duration_ms))

            if self._aborted:
                logger.info("STT aborted.")
                return

            logger.info("Stage: STT - Result: '{}'", transcript)

            if transcript.strip():
                await self._bus.emit(TranscriptReady(text=transcript, app_context=event.app_context))
            else:
                logger.warning("Empty transcription result.")
                await self._bus.emit(StatusChanged(status="idle", message=""))

        except Exception as e:
            logger.error("Transcription failed: {}", e)
            await self._bus.emit(PipelineError(stage="stt_transcribe", error=e))
            await self._bus.emit(StatusChanged(status="error", message="STT Error"))


