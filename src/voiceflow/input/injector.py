"""Text injection into the currently active window.

Responsibilities:
- Simulate keystrokes using Win32 SendInput API.
- Provide clipboard-paste fallback.
- Handle full Unicode via VK_PACKET scan codes.

This module contains the interface and wiring only.
Business logic will be implemented in Phase 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from voiceflow.core.config import InjectionConfig
    from voiceflow.core.events import EventBus


class TextInjector:
    """Injects refined text into the active window."""

    def __init__(self, config: InjectionConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus

    async def start(self) -> None:
        """Subscribe to RefinedTextReady events."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Cleanup."""
        raise NotImplementedError
