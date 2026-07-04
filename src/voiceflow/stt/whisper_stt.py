"""faster-whisper STT implementation.

Responsibilities:
- Load a CTranslate2 Whisper model (tiny → large-v3).
- Run transcription with configurable language and compute type.
- Emit TranscriptReady event with the resulting text.

This module contains the interface and wiring only.
Business logic will be implemented in Phase 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from voiceflow.stt.base import STTEngine

if TYPE_CHECKING:
    from voiceflow.core.config import STTConfig
    from voiceflow.core.events import EventBus


class WhisperSTT(STTEngine):
    """faster-whisper speech-to-text engine."""

    def __init__(self, config: STTConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._model = None

    async def load_model(self) -> None:
        """Load the faster-whisper model."""
        raise NotImplementedError

    async def transcribe(self, audio: NDArray[np.float32], sample_rate: int) -> str:
        """Transcribe audio using faster-whisper."""
        raise NotImplementedError

    async def unload_model(self) -> None:
        """Release the faster-whisper model."""
        raise NotImplementedError
