"""Application orchestrator — wires all modules and manages lifecycle.

Responsibilities:
- Load configuration.
- Initialise logging.
- Create the EventBus and all pipeline components.
- Wire events: Hotkey → Capture → VAD → STT → LLM → Inject.
- Handle graceful startup and shutdown.
"""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING

from mouthfull import __app_name__, __version__
from mouthfull.configs.config import load_config
from mouthfull.utils.events import EventBus
from mouthfull.utils.logger import logger, setup_logging

if TYPE_CHECKING:
    from pathlib import Path


class MouthFullApp:
    """Main application class.

    Manages the full lifecycle: init → run → shutdown.
    """

    def __init__(self, config_path: str | Path | None = None, config=None) -> None:
        self._config = config if config else load_config(config_path)
        setup_logging(self._config)
        self._bus = EventBus()
        self._running = False
        
        from mouthfull.utils.perf import PerformanceCollector
        self._perf = PerformanceCollector(self._bus)

        logger.info("{} v{} initialising", __app_name__, __version__)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start all services and begin the main loop."""
        logger.info("Starting MouthFull Local pipeline…")
        from mouthfull.utils.events import PipelineError, NotificationEvent

        # Subscribe to pipeline errors to notify user
        self._bus.subscribe(PipelineError, self._on_pipeline_error)

        from mouthfull.backend.audio.capture import AudioCapture
        from mouthfull.backend.audio.vad import VoiceActivityDetector
        from mouthfull.backend.injection.injector import TextInjector
        from mouthfull.backend.input.hotkey import HotkeyListener
        from mouthfull.backend.prompt.service import PromptProcessorService
        from mouthfull.backend.llm.service import LLMService
        from mouthfull.backend.stt.service import STTService

        self._hotkey = HotkeyListener(self._config.hotkey, self._bus)
        self._capture = AudioCapture(self._config.audio, self._bus)
        self._vad = VoiceActivityDetector(self._config.vad, self._bus)
        self._stt = STTService(self._config.stt, self._bus)
        self._prompt = PromptProcessorService(self._config.prompt_processor, self._bus)
        self._llm = LLMService(self._config.llm, self._bus)
        self._injector = TextInjector(self._config.injection, self._bus)

        await self._hotkey.start()
        await self._capture.start()
        await self._vad.start()
        await self._stt.start()
        await self._prompt.start()
        await self._llm.start()
        await self._injector.start()
        await self._perf.start()

        self._running = True
        logger.info("{} is ready — press your hotkey to dictate!", __app_name__)

        from mouthfull.utils.events import NotificationEvent
        await self._bus.emit(NotificationEvent(
            title="MouthFull Local",
            message=f"Ready! Press {self._config.hotkey.combination.upper()} to dictate."
        ))

    async def stop(self) -> None:
        """Gracefully shut down all components."""
        if not self._running:
            return

        logger.info("Shutting down {}…", __app_name__)

        await self._injector.stop()
        await self._llm.stop()
        await self._prompt.stop()
        await self._stt.stop()
        await self._vad.stop()
        await self._capture.stop()
        await self._hotkey.stop()
        await self._perf.stop()

        self._running = False
        logger.info("{} stopped.", __app_name__)

    async def run_forever(self) -> None:
        """Run until stopped."""
        await self.start()
        
        stop_event = asyncio.Event()

        def _signal_handler() -> None:
            logger.info("Received shutdown signal.")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                # Windows does not support add_signal_handler for SIGTERM.
                # Ctrl+C (SIGINT) is handled via KeyboardInterrupt instead.
                pass

        try:
            while not stop_event.is_set():
                await asyncio.sleep(1) # Keep loop running on Windows to allow KeyboardInterrupt
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await self.stop()

    async def _on_pipeline_error(self, event) -> None:
        from mouthfull.utils.events import NotificationEvent
        await self._bus.emit(NotificationEvent(
            title=f"Error in {event.stage}",
            message=str(event.error)
        ))
