"""Typed event definitions and async EventBus.

The EventBus is the backbone of MouthFull's pipeline architecture.
Modules emit events without knowing who consumes them, and subscribe
to events without knowing who produces them.

Usage::

    bus = EventBus()
    bus.subscribe(TranscriptReady, my_handler)
    await bus.emit(TranscriptReady(text="hello world"))
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

import numpy as np
from numpy.typing import NDArray

from mouthfull.utils.logger import logger

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
    app_context: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class SpeechDetected:
    """Emitted after VAD confirms speech in the audio."""

    audio: NDArray[np.float32]
    sample_rate: int
    app_context: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class TranscriptReady:
    """Emitted when STT produces a raw transcript."""

    text: str
    app_context: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class PromptReady:
    """Emitted when the prompt processor has prepared the text for the LLM."""

    text: str
    is_prompt: bool = True


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
class PipelineAbort:
    """Emitted when the user cancels the current operation (e.g. by pressing Esc)."""



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


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Emitted periodically with system resource usage."""

    cpu_percent: float
    ram_percent: float
    gpu_percent: float | None


@dataclass(frozen=True, slots=True)
class PipelineTiming:
    """Emitted when a pipeline stage finishes to report its duration."""

    stage: str
    duration_ms: float


@dataclass(frozen=True, slots=True)
class ModelDownloadProgress:
    """Emitted during model downloads."""
    
    model_id: str
    percentage: float
    speed_mbps: float
    remaining_size_mb: float
    eta_sec: float
    stage: str # "Preparing", "Downloading", "Verifying", "Installing", "Complete"
    name: str


@dataclass(frozen=True, slots=True)
class ModelDownloadStatus:
    """Emitted when download status changes."""
    
    model_id: str
    status: str # "downloading", "paused", "cancelled", "error", "installed", "not_installed"
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
