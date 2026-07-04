"""Global hotkey listener using pynput.

Responsibilities:
- Register a configurable global hotkey (e.g. Ctrl+Shift+Space).
- Support push-to-talk and toggle modes.
- Emit HotkeyPressed / HotkeyReleased events.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pynput import keyboard

from mouthfull.utils.events import HotkeyPressed, HotkeyReleased
from mouthfull.utils.logger import logger

if TYPE_CHECKING:
    from mouthfull.configs.config import HotkeyConfig
    from mouthfull.utils.events import EventBus


class HotkeyListener:
    """Global hotkey listener."""

    def __init__(self, config: HotkeyConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._listener: keyboard.Listener | None = None
        self._active = False
        self._loop = asyncio.get_running_loop()

        # We use pynput's HotKey helper to parse and track the combination
        try:
            # Convert "ctrl+space" to "<ctrl>+<space>" for pynput
            parts = [f"<{p.strip()}>" if len(p.strip()) > 1 else p.strip() for p in self._config.combination.lower().split('+')]
            pynput_combo = '+'.join(parts)
            self._hotkey_keys = keyboard.HotKey.parse(pynput_combo)
        except Exception as e:
            logger.error("Failed to parse hotkey combination '{}': {}", self._config.combination, e)
            self._hotkey_keys = []

        self._hotkey_tracker = keyboard.HotKey(self._hotkey_keys, self._on_activate)
        self._pressed_keys: set[keyboard.Key | keyboard.KeyCode] = set()

    def _on_activate(self) -> None:
        """Called by pynput when the exact combination is pressed."""
        if self._config.mode == "toggle":
            if not getattr(self, "_is_recording", False):
                self._is_recording = True
                logger.debug("Hotkey activated (Toggle ON).")
                asyncio.run_coroutine_threadsafe(self._bus.emit(HotkeyPressed()), self._loop)
            # If already recording, we do nothing. They must press Enter to stop.
        else:
            if not self._active:
                self._active = True
                logger.debug("Hotkey activated (PTT ON).")
                asyncio.run_coroutine_threadsafe(self._bus.emit(HotkeyPressed()), self._loop)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return
        
        # Abort pipeline if ESC is pressed
        if key == keyboard.Key.esc:
            logger.info("ESC pressed. Aborting pipeline.")
            from mouthfull.utils.events import PipelineAbort, StatusChanged
            asyncio.run_coroutine_threadsafe(self._bus.emit(PipelineAbort()), self._loop)
            asyncio.run_coroutine_threadsafe(self._bus.emit(StatusChanged(status="idle")), self._loop)
            if hasattr(self, "_is_recording"): self._is_recording = False
            return
            
        # If in toggle mode and recording, Enter stops it
        if self._config.mode == "toggle" and getattr(self, "_is_recording", False) and key == keyboard.Key.enter:
            logger.info("Enter pressed. Stopping toggle recording.")
            self._is_recording = False
            asyncio.run_coroutine_threadsafe(self._bus.emit(HotkeyReleased()), self._loop)
            return

        key = self._listener.canonical(key) if self._listener else key
        self._pressed_keys.add(key)
        self._hotkey_tracker.press(key)

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return
        key = self._listener.canonical(key) if self._listener else key
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)

        self._hotkey_tracker.release(key)

        # Handle Push-to-Talk release
        if self._config.mode == "push_to_talk" and self._active:
            still_pressed = all(k in self._pressed_keys for k in self._hotkey_keys)
            if not still_pressed:
                self._active = False
                logger.debug("Hotkey deactivated (PTT OFF).")
                asyncio.run_coroutine_threadsafe(self._bus.emit(HotkeyReleased()), self._loop)

    async def start(self) -> None:
        """Start listening for the global hotkey."""
        if not self._hotkey_keys:
            logger.warning("No valid hotkey configured. Listening disabled.")
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info("Hotkey listener started (combination: {}, mode: {}).",
                    self._config.combination, self._config.mode)

    async def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            logger.info("Hotkey listener stopped.")
