"""Abstract interface for speech-to-text engines.

All STT implementations must inherit from STTEngine and implement
the transcribe() method.  This enables swapping backends (e.g.,
faster-whisper ↔ whisper.cpp) without modifying pipeline code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray


class STTEngine(ABC):
    """Base class for speech-to-text engines."""

    @abstractmethod
    async def load_model(self) -> None:
        """Load the STT model into memory."""

    @abstractmethod
    async def transcribe(self, audio: NDArray[np.float32], sample_rate: int) -> str:
        """Transcribe audio to text.

        Parameters
        ----------
        audio:
            Mono float32 audio waveform, values in [-1.0, 1.0].
        sample_rate:
            Sample rate in Hz.

        Returns
        -------
        str
            The transcribed text.
        """

    @abstractmethod
    async def unload_model(self) -> None:
        """Release model resources."""
