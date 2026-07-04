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

    def __init__(self, config: STTConfig) -> None:
        self._config = config
        self._model = None

    async def load_model(self) -> None:
        """Load the faster-whisper model."""
        import asyncio
        def _sync_load():
            from faster_whisper import WhisperModel
            from voiceflow.core.logger import logger
            
            # Map auto device to CPU or CUDA
            device = self._config.device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
            compute_type = self._config.compute_type
            if compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
                
            model_size = self._config.model_size
            if model_size.startswith("nvidia/"):
                # fallback if user left parakeet model size in whisper
                model_size = "tiny"
                
            logger.info("Loading faster-whisper model '{}' on {} with {}", model_size, device, compute_type)
            return WhisperModel(model_size, device=device, compute_type=compute_type)

        self._model = await asyncio.to_thread(_sync_load)

    async def transcribe(self, audio: NDArray[np.float32], sample_rate: int) -> str:
        """Transcribe audio using faster-whisper."""
        if not self._model:
            raise RuntimeError("Whisper model not loaded.")
            
        import asyncio
        def _sync_transcribe():
            # faster-whisper expects a float32 numpy array
            segments, info = self._model.transcribe(
                audio, 
                beam_size=5, 
                language=self._config.language, 
                condition_on_previous_text=False
            )
            text = " ".join([segment.text for segment in segments])
            return text.strip()

        return await asyncio.to_thread(_sync_transcribe)

    async def unload_model(self) -> None:
        """Release the faster-whisper model."""
        if self._model:
            del self._model
            self._model = None
