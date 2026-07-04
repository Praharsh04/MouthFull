"""Typed event definitions and async EventBus.

The EventBus is the backbone of VoiceFlow's pipeline architecture.
Modules emit events without knowing who consumes them, and subscribe
to events without knowing who produces them.

Usage::

    bus = EventBus()
    bus.subscribe(TranscriptReady, my_handler)
    await bus.emit(TranscriptReady(text="hello world"))
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, TypeVar

import numpy as np
from numpy.typing import NDArray

from voiceflow.core.logger import logger

# ---------------------------------------------------------------------------
# Event dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HotkeyPressed:
    """Emitted when the user presses the dictation hotkey."""


@dataclass(frozen=True, slots=True)
class HotkeyReleased:
    """Emitted when the user releases the dictation hotkey."""


@dataclass(frozen=True, slots=True)
class AudioCaptured:
    """Emitted when a complete audio recording is available."""

    audio: NDArray[np.float32]
    sample_rate: int


@dataclass(frozen=True, slots=True)
class SpeechDetected:
    """Emitted after VAD confirms speech in the audio."""

    audio: NDArray[np.float32]
    sample_rate: int


@dataclass(frozen=True, slots=True)
class TranscriptReady:
    """Emitted when STT produces a raw transcript."""

    text: str


@dataclass(frozen=True, slots=True)
class RefinedTextReady:
    """Emitted when the LLM finishes refining the transcript."""

    text: str


@dataclass(frozen=True, slots=True)
class PipelineError:
    """Emitted when an error occurs in the pipeline."""
    
    stage: str
    error: Exception


@dataclass(frozen=True, slots=True)
class AudioLevelChanged:
    """Emitted during audio capture to indicate microphone volume (0.0 to 1.0)."""
    
    level: float
    

@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """Emitted to trigger an OS-level notification."""
    
    title: str
    message: str


@dataclass(frozen=True, slots=True)
class StatusChanged:
    """Emitted when the application status changes (for UI updates)."""

    status: str  # "idle", "recording", "processing", "error"
    message: str = ""


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------

# Type variable for event classes.
E = TypeVar("E")

# A handler is an async callable that receives an event instance.
EventHandler = Callable[[Any], Coroutine[Any, Any, None]]


class EventBus:
    """Async publish-subscribe event bus.

    Handlers are invoked in the order they were subscribed, and errors
    in one handler do not prevent subsequent handlers from running.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[EventHandler]] = {}

    def subscribe(self, event_type: type[E], handler: EventHandler) -> None:
        """Register *handler* to be called when *event_type* is emitted."""
        self._subscribers.setdefault(event_type, []).append(handler)
        logger.debug(
            "Subscribed {} to {}",
            handler.__qualname__,
            event_type.__name__,
        )

    def unsubscribe(self, event_type: type[E], handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        handlers = self._subscribers.get(event_type, [])
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    async def emit(self, event: Any) -> None:
        """Dispatch *event* to all registered handlers for its type."""
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.trace("No handlers for {}", event_type.__name__)
            return

        logger.debug(
            "Emitting {} to {} handler(s)",
            event_type.__name__,
            len(handlers),
        )

        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Handler {} failed for {}",
                    handler.__qualname__,
                    event_type.__name__,
                )
