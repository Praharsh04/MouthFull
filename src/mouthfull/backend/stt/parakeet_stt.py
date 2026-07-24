"""NVIDIA Parakeet V2 Speech-to-Text engine.

Uses NVIDIA NeMo Toolkit to load and run Parakeet models.
"""

from __future__ import annotations

import gc
import os
import tempfile
from typing import TYPE_CHECKING

import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from mouthfull.utils.exceptions import STTModelLoadError, STTTranscriptionError
from mouthfull.utils.logger import logger
from mouthfull.backend.stt.base import STTEngine

if TYPE_CHECKING:
    from mouthfull.configs.config import STTConfig


class ParakeetSTT(STTEngine):
    """NVIDIA Parakeet (NeMo) STT engine."""

    def __init__(self, config: STTConfig) -> None:
        self._config = config
        self._model = None

    async def load_model(self) -> None:
        """Load the Parakeet model."""
        try:
            import nemo.collections.asr as nemo_asr
        except ImportError as e:
            raise STTModelLoadError(
                "nemo_toolkit is not installed. Please install it using: "
                "pip install nemo_toolkit[asr]"
            ) from e

        logger.info("Loading Parakeet model: {}", self._config.model_size)
        try:
            # Check if it's a CTC or RNNT/TDT model based on the name
            model_name_lower = self._config.model_size.lower()
            if "ctc" in model_name_lower:
                self._model = nemo_asr.models.EncDecCTCModelBPE.from_pretrained(
                    model_name=self._config.model_size
                )
            elif "rnnt" in model_name_lower or "tdt" in model_name_lower:
                self._model = nemo_asr.models.EncDecRNNTModel.from_pretrained(
                    model_name=self._config.model_size
                )
            else:
                # Default to RNNT if unsure (Parakeet v3 default)
                self._model = nemo_asr.models.EncDecRNNTModel.from_pretrained(
                    model_name=self._config.model_size
                )

            # Move to device if necessary (nemo handles cuda by default if available)
            if self._config.device == "cpu":
                import torch
                self._model.to(torch.device("cpu"))

            logger.info("Parakeet model loaded successfully.")
        except Exception as e:
            raise STTModelLoadError(f"Failed to load Parakeet model {self._config.model_size}: {e}") from e

    async def transcribe(self, audio: NDArray[np.float32], sample_rate: int) -> str:
        """Transcribe audio using NeMo.
        
        NeMo usually expects audio to be resampled to 16000 Hz and passed as a file path
        or a tensor. We will save to a temporary WAV file as it's the most robust way
        with NeMo's transcribe() API.
        """
        if self._model is None:
            raise STTTranscriptionError("Parakeet model is not loaded.")

        # NeMo Parakeet models expect 16kHz audio.
        if sample_rate != 16000:
            logger.warning("Parakeet expects 16000 Hz, got {}. Transcription may be poor.", sample_rate)

        # Write to temporary file for NeMo to process
        fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        try:
            sf.write(tmp_path, audio, sample_rate, subtype='PCM_16')

            # NeMo transcribe returns a tuple of lists.
            # Depending on model type (CTC vs RNNT), it might return 1 or 2 items.
            transcription_results = self._model.transcribe([tmp_path])

            # Handle different return formats from NeMo
            if isinstance(transcription_results, tuple):
                transcripts = transcription_results[0]
            else:
                transcripts = transcription_results

            if not transcripts:
                return ""

            return transcripts[0]

        except Exception as e:
            raise STTTranscriptionError(f"Parakeet transcription failed: {e}") from e
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    async def unload_model(self) -> None:
        """Release NeMo model from memory."""
        if self._model is not None:
            logger.info("Unloading Parakeet model...")
            del self._model
            self._model = None

            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            gc.collect()
