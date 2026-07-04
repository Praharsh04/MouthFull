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

from voiceflow import __app_name__, __version__
from voiceflow.core.config import load_config
from voiceflow.core.events import EventBus
from voiceflow.core.logger import logger, setup_logging

if TYPE_CHECKING:
    from pathlib import Path


class VoiceFlowApp:
    """Main application class.

    Manages the full lifecycle: init → run → shutdown.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config = load_config(config_path)
        setup_logging(self._config)
        self._bus = EventBus()
        self._running = False

        logger.info("{} v{} initialising", __app_name__, __version__)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialise all pipeline components and start the application."""
        logger.info("Starting {} pipeline…", __app_name__)

        from voiceflow.input.hotkey import HotkeyListener
        from voiceflow.audio.capture import AudioCapture
        from voiceflow.audio.vad import VoiceActivityDetector
        from voiceflow.ui import SystemTray, FloatingOverlay
        from voiceflow.stt.service import STTService
        from voiceflow.llm.service import LLMService
        from voiceflow.injection.injector import TextInjector

        self._hotkey = HotkeyListener(self._config.hotkey, self._bus)
        self._capture = AudioCapture(self._config.audio, self._bus)
        self._vad = VoiceActivityDetector(self._config.vad, self._bus)
        self._stt = STTService(self._config.stt, self._bus)
        self._llm = LLMService(self._config.llm, self._bus)
        self._injector = TextInjector(self._config.injection, self._bus)
        self._overlay = FloatingOverlay(self._config.ui, self._bus)
        self._tray = SystemTray(self._config, self._bus)

        await self._hotkey.start()
        await self._capture.start()
        await self._vad.start()
        await self._stt.start()
        await self._llm.start()
        await self._injector.start()
        await self._overlay.start()
        await self._tray.start()

        self._running = True
        logger.info("{} is ready — press your hotkey to dictate!", __app_name__)
        
        from voiceflow.core.events import NotificationEvent
        await self._bus.emit(NotificationEvent(
            title="VoiceFlow Local",
            message=f"Ready! Press {self._config.hotkey.combination.upper()} to dictate."
        ))

    async def stop(self) -> None:
        """Gracefully shut down all components."""
        if not self._running:
            return

        logger.info("Shutting down {}…", __app_name__)

        await self._tray.stop()
        await self._overlay.stop()
        await self._injector.stop()
        await self._llm.stop()
        await self._stt.stop()
        await self._vad.stop()
        await self._capture.stop()
        await self._hotkey.stop()

        self._running = False
        logger.info("{} stopped.", __app_name__)

    async def run_forever(self) -> None:
        """Run the application until interrupted."""
        await self.start()

        # Keep the event loop alive until a shutdown signal arrives.
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
            while True:
                await asyncio.sleep(1) # Keep loop running on Windows to allow KeyboardInterrupt
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await self.stop()
