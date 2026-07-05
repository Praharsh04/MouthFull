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

from mouthfull.utils.events import PipelineError, RefinedTextReady, StatusChanged
from mouthfull.utils.logger import logger

if TYPE_CHECKING:
    from mouthfull.configs.config import InjectionConfig
    from mouthfull.utils.events import EventBus


class TextInjector:
    """Injects text globally on Windows."""

    def __init__(self, config: InjectionConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._keyboard = Controller()
        self._aborted = False

    async def start(self) -> None:
        """Subscribe to RefinedTextReady."""
        from mouthfull.utils.events import PipelineAbort, HotkeyPressed
        self._bus.subscribe(HotkeyPressed, self._on_hotkey)
        self._bus.subscribe(PipelineAbort, self._on_abort)
        self._bus.subscribe(RefinedTextReady, self._on_text_ready)
        logger.info("TextInjector started.")

    async def stop(self) -> None:
        """Unsubscribe."""
        from mouthfull.utils.events import PipelineAbort, HotkeyPressed
        self._bus.unsubscribe(HotkeyPressed, self._on_hotkey)
        self._bus.unsubscribe(PipelineAbort, self._on_abort)
        self._bus.unsubscribe(RefinedTextReady, self._on_text_ready)
        logger.info("TextInjector stopped.")

    async def _on_hotkey(self, event) -> None:
        self._aborted = False

    async def _on_abort(self, event) -> None:
        self._aborted = True

    async def _on_text_ready(self, event: RefinedTextReady) -> None:
        """Inject the text."""
        if self._aborted:
            logger.info("Injection aborted.")
            return

        text = event.text.strip()
        if not text:
            await self._bus.emit(StatusChanged(status="idle", message=""))
            return

        logger.info("Injecting text: '{}'", text)

        try:
            import time
            start_time = time.perf_counter()
            # Run injection synchronously in a background thread to avoid blocking asyncio
            await asyncio.to_thread(self._inject_sync, text)
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("Text successfully injected in {:.2f}ms.", duration_ms)
            from mouthfull.utils.events import PipelineTiming
            await self._bus.emit(PipelineTiming(stage="inject", duration_ms=duration_ms))
            
            await self._bus.emit(StatusChanged(status="idle", message=""))
        except Exception as e:
            logger.error("Text injection failed: {}", e)
            await self._bus.emit(PipelineError(stage="injection", error=e))
            await self._bus.emit(StatusChanged(status="error", message="Injection Error"))

    def _inject_sync(self, text: str) -> None:
        """Synchronous method to inject text."""
        if self._config.method == "typewrite":
            self._typewrite(text)
        else:
            self._clipboard_inject(text)
            
        if getattr(self._config, "auto_enter", False):
            time.sleep(0.05)
            self._keyboard.press(Key.enter)
            self._keyboard.release(Key.enter)

    def _typewrite(self, text: str) -> None:
        """Inject text by simulating keystrokes."""
        delay = self._config.keystroke_delay
        for char in text:
            # Handle newlines explicitly
            if char == '\n':
                self._keyboard.press(Key.enter)
                self._keyboard.release(Key.enter)
            else:
                self._keyboard.type(char)
            if delay > 0:
                time.sleep(delay)

    def _clipboard_inject(self, text: str) -> None:
        """Inject text via clipboard (fast but overwrites clipboard temporarily).

        If the paste simulation fails or the target app appears to block it,
        automatically falls back to keystroke-based injection (_typewrite).
        """
        # 1. Save current clipboard
        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception as e:
            logger.warning("Could not read old clipboard: {}", e)

        try:
            # 2. Set new text to clipboard
            pyperclip.copy(text)

            # 3. Simulate Ctrl+V
            time.sleep(0.01)
            with self._keyboard.pressed(Key.ctrl):
                self._keyboard.press('v')
                self._keyboard.release('v')

            # 4. Wait for the app to consume the paste
            time.sleep(0.02)

            # Note: We cannot reliably verify if the paste was consumed because 
            # Ctrl+V does not clear the clipboard. We only fall back if an 
            # exception occurs during simulation.

        except Exception as e:
            # Paste simulation failed entirely – fall back to typewrite
            logger.warning(
                "Clipboard injection failed ({}). Falling back to typewrite injection.", e
            )
            self._typewrite(text)

        finally:
            # 6. Restore old clipboard
            try:
                if old_clipboard:
                    pyperclip.copy(old_clipboard)
            except Exception as e:
                logger.warning("Could not restore old clipboard: {}", e)
