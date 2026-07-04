"""Text injection service.

Listens for RefinedTextReady events and injects the text into the currently
focused application using clipboard + Ctrl-V for speed and multiline support.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
import pyperclip
from pynput.keyboard import Controller, Key

from voiceflow.core.events import RefinedTextReady, StatusChanged, PipelineError
from voiceflow.core.logger import logger

if TYPE_CHECKING:
    from voiceflow.core.config import InjectionConfig
    from voiceflow.core.events import EventBus


class TextInjector:
    """Injects text globally on Windows."""

    def __init__(self, config: InjectionConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._keyboard = Controller()

    async def start(self) -> None:
        """Subscribe to RefinedTextReady."""
        self._bus.subscribe(RefinedTextReady, self._on_text_ready)
        logger.info("TextInjector started.")

    async def stop(self) -> None:
        """Unsubscribe."""
        self._bus.unsubscribe(RefinedTextReady, self._on_text_ready)
        logger.info("TextInjector stopped.")

    async def _on_text_ready(self, event: RefinedTextReady) -> None:
        """Inject the text."""
        text = event.text.strip()
        if not text:
            await self._bus.emit(StatusChanged(status="idle", message=""))
            return

        logger.info("Injecting text: '{}'", text)
        
        try:
            # Run injection synchronously in a background thread to avoid blocking asyncio
            await asyncio.to_thread(self._inject_sync, text)
            await self._bus.emit(StatusChanged(status="idle", message=""))
        except Exception as e:
            logger.error("Text injection failed: {}", e)
            await self._bus.emit(PipelineError(stage="injection", error=e))
            await self._bus.emit(StatusChanged(status="error", message="Injection Error"))

    def _inject_sync(self, text: str) -> None:
        """Synchronous method to inject text via clipboard."""
        
        # 1. Save current clipboard
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception as e:
            logger.warning("Could not read old clipboard: {}", e)

        # 2. Set new text to clipboard
        try:
            pyperclip.copy(text)
        except Exception as e:
            raise RuntimeError(f"Failed to copy to clipboard: {e}") from e

        # 3. Simulate Ctrl+V
        # Wait a tiny bit to ensure the clipboard is registered by the OS
        time.sleep(0.05)
        
        try:
            with self._keyboard.pressed(Key.ctrl):
                self._keyboard.press('v')
                self._keyboard.release('v')
        except Exception as e:
            raise RuntimeError(f"Failed to simulate keystrokes: {e}") from e
            
        # 4. Wait for the app to consume the paste before restoring clipboard
        time.sleep(0.1)

        # 5. Restore old clipboard
        try:
            pyperclip.copy(old_clipboard)
        except Exception as e:
            logger.warning("Could not restore old clipboard: {}", e)
