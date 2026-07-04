"""Voice Activity Detection using Silero VAD (ONNX).

Responsibilities:
- Load the Silero VAD model via ONNX Runtime.
- Analyse captured audio to detect speech segments.
- Trim silence and emit SpeechDetected if voice is found.
- Discard audio and notify the user if no speech is detected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from voiceflow.core.config import VADConfig
    from voiceflow.core.events import EventBus


from voiceflow.core.events import AudioCaptured, SpeechDetected
from voiceflow.core.logger import logger
import numpy as np


class VoiceActivityDetector:
    """Silero VAD wrapper (Pass-through for now)."""

    def __init__(self, config: VADConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus

    async def start(self) -> None:
        """Load the VAD model (if available) and subscribe to AudioCaptured events."""
        # Attempt to load Silero VAD ONNX model; if unavailable, fall back to RMS threshold.
        try:
            import onnxruntime as ort
            # The Silero VAD model file path could be configured; using bundled placeholder
            model_path = None
            # Attempt to locate model in package data (not implemented), fallback.
            if model_path:
                self._session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
                logger.info("Silero VAD model loaded.")
            else:
                self._session = None
                logger.info("Silero VAD model not found, using RMS threshold detection.")
        except Exception as e:
            self._session = None
            logger.warning("Failed to load Silero VAD model: %s. Falling back to RMS detection.", e)
        self._bus.subscribe(AudioCaptured, self._on_audio_captured)
        logger.info("VAD initialized and subscribed to AudioCaptured.")

    async def stop(self) -> None:
        """Release model resources."""
        self._bus.unsubscribe(AudioCaptured, self._on_audio_captured)

    async def _on_audio_captured(self, event: AudioCaptured) -> None:
        """Process captured audio and emit SpeechDetected if speech is detected.

        If a Silero VAD model is loaded, use it for detection; otherwise fall back to a simple RMS threshold.
        """
        if not self._config.enabled:
            # VAD disabled; forward audio directly.
            await self._bus.emit(SpeechDetected(audio=event.audio, sample_rate=event.sample_rate))
            return

        # If we have a loaded ONNX session, use it (placeholder – actual inference omitted for brevity).
        if getattr(self, "_session", None):
            try:
                # Silero VAD expects float32 waveform, shape (1, n_samples)
                wav = event.audio.astype(np.float32)
                wav = wav.reshape(1, -1)
                # The model typically outputs probability per frame; here we just call it.
                probs = self._session.run(None, {self._session.get_inputs()[0].name: wav})[0]
                # Simple heuristic: speech if any probability exceeds threshold.
                if (probs > self._config.threshold).any():
                    await self._bus.emit(SpeechDetected(audio=event.audio, sample_rate=event.sample_rate))
                else:
                    logger.debug("VAD filtered out non‑speech audio (model).")
                return
            except Exception as e:
                logger.warning("Silero VAD inference failed (%s); falling back to RMS.", e)

        # RMS based fallback detection.
        rms = float(np.sqrt(np.mean(event.audio ** 2)))
        if rms >= self._config.threshold:
            await self._bus.emit(SpeechDetected(audio=event.audio, sample_rate=event.sample_rate))
        else:
            logger.debug("VAD filtered out non‑speech audio (RMS threshold).")
