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

from voiceflow.core.events import HotkeyPressed, HotkeyReleased
from voiceflow.core.logger import logger

if TYPE_CHECKING:
    from voiceflow.core.config import HotkeyConfig
    from voiceflow.core.events import EventBus


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
            self._hotkey_keys = keyboard.HotKey.parse(self._config.combination)
        except Exception as e:
            logger.error("Failed to parse hotkey combination '{}': {}", self._config.combination, e)
            self._hotkey_keys = []
            
        self._hotkey_tracker = keyboard.HotKey(self._hotkey_keys, self._on_activate)
        self._pressed_keys: set[keyboard.Key | keyboard.KeyCode] = set()

    def _on_activate(self) -> None:
        """Called by pynput when the exact combination is pressed."""
        if not self._active:
            self._active = True
            logger.debug("Hotkey activated.")
            # Dispatch to asyncio loop
            asyncio.run_coroutine_threadsafe(self._bus.emit(HotkeyPressed()), self._loop)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
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
        
        # If we were active and now we aren't holding all the keys
        if self._active:
            # Check if any key from the combination is released
            # Since pynput HotKey doesn't give a deactivate callback, we manually check
            still_pressed = all(k in self._pressed_keys for k in self._hotkey_keys)
            if not still_pressed:
                self._active = False
                logger.debug("Hotkey deactivated.")
                
                # In toggle mode, we only emit HotkeyReleased if it was a second press.
                # Actually, in toggle mode, HotkeyPressed handles starting/stopping.
                # But for push_to_talk, release stops.
                if self._config.mode == "push_to_talk":
                    asyncio.run_coroutine_threadsafe(self._bus.emit(HotkeyReleased()), self._loop)
                else:
                    # For toggle mode, HotkeyReleased is not emitted on physical key release,
                    # we would emit HotkeyReleased on the *next* activate. 
                    # We will handle toggle logic in the app orchestrator or here.
                    # Let's just emit HotkeyReleased if we are in push_to_talk mode.
                    pass

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
