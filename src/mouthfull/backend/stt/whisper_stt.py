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

from mouthfull.backend.stt.base import STTEngine

if TYPE_CHECKING:
    from mouthfull.configs.config import STTConfig
    from mouthfull.utils.events import EventBus


class WhisperSTT(STTEngine):
    """faster-whisper speech-to-text engine."""

    def __init__(self, config: STTConfig) -> None:
        self._config = config
        self._model = None

    async def load_model(self) -> None:
        """Load the faster-whisper model."""
        import asyncio
        def _sync_load():
            import os
            import sys
            import faster_whisper
            from faster_whisper import WhisperModel
            from mouthfull.utils.logger import logger
            
            # 1. Comprehensive Diagnostics
            is_frozen = getattr(sys, 'frozen', False)
            exe_location = sys.executable
            cwd = os.getcwd()
            meipass = getattr(sys, '_MEIPASS', 'N/A')
            
            logger.info("--- STT Initialization Diagnostics ---")
            logger.info(f"Mode: {'Packaged (Frozen)' if is_frozen else 'Development'}")
            logger.info(f"Executable Location: {exe_location}")
            logger.info(f"Current Working Directory: {cwd}")
            if is_frozen:
                logger.info(f"sys._MEIPASS: {meipass}")
            
            # 2. VAD Model Validation (The NO_SUCHFILE Root Cause)
            try:
                import faster_whisper.utils
                vad_assets_dir = faster_whisper.utils.get_assets_path()
                vad_model_path = os.path.join(vad_assets_dir, "silero_vad_v6.onnx")
                
                logger.info(f"Resolved VAD ONNX Directory: {vad_assets_dir}")
                logger.info(f"Expected VAD ONNX Path: {vad_model_path}")
                
                if os.path.exists(vad_model_path):
                    logger.info("VAD ONNX file exists: TRUE")
                else:
                    logger.error("VAD ONNX file exists: FALSE")
                    logger.error("FATAL: The required silero_vad_v6.onnx file is missing from the package.")
                    logger.error("This indicates a packaging flaw (missing --collect-data=faster_whisper in PyInstaller).")
                    
                    # Attempt automated fallback recovery if we are packaged
                    if is_frozen:
                        fallback_path = os.path.join(meipass, "faster_whisper", "assets", "silero_vad_v6.onnx")
                        if os.path.exists(fallback_path):
                            logger.info(f"Found VAD model in fallback location: {fallback_path}")
                            # We must patch get_assets_path temporarily to survive this run if possible
                            faster_whisper.utils.get_assets_path = lambda: os.path.dirname(fallback_path)
                            logger.info("Patched faster_whisper.utils.get_assets_path dynamically to resolve error.")
                        else:
                            raise FileNotFoundError(f"Missing ONNX VAD model at {vad_model_path}. Please rebuild with --collect-data=faster_whisper")
                    else:
                        raise FileNotFoundError(f"Missing ONNX VAD model at {vad_model_path}")
            except Exception as e:
                logger.error(f"VAD Model Validation Exception: {e}")
                raise

            # 3. STT Model Download Directory
            # Resolve persistent AppData directory for storing models instead of relying on default temp caches
            app_data = os.getenv('APPDATA', os.path.expanduser('~'))
            models_dir = os.path.join(app_data, 'MouthFullLocal', 'models')
            os.makedirs(models_dir, exist_ok=True)
            logger.info(f"Persistent Models Directory initialized at: {models_dir}")
            
            # 4. Device and Model Configuration
            device = self._config.device
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
                
            compute_type = self._config.compute_type
            if compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
                
            model_size = self._config.model_size
            if model_size.startswith("nvidia/"):
                model_size = "tiny"
                
            logger.info("Loading faster-whisper model '{}' on {} with {} into {}", model_size, device, compute_type, models_dir)
            
            try:
                model = WhisperModel(model_size, device=device, compute_type=compute_type, download_root=models_dir)
                logger.info("WhisperModel successfully loaded.")
                return model
            except Exception as e:
                logger.error(f"Failed to load WhisperModel: {e}")
                raise

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
                beam_size=1, 
                language=self._config.language, 
                condition_on_previous_text=False,
                vad_filter=True
            )
            text = " ".join([segment.text for segment in segments])
            return text.strip()

        return await asyncio.to_thread(_sync_transcribe)

    async def unload_model(self) -> None:
        """Release the faster-whisper model."""
        if self._model:
            del self._model
            self._model = None
