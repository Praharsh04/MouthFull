"""Voice Activity Detection using Silero VAD (ONNX).

Responsibilities:
- Load the Silero VAD model via ONNX Runtime.
- Analyse captured audio to detect speech segments.
- Trim silence and emit SpeechDetected if voice is found.
- Discard audio and notify the user if no speech is detected.

This module contains the interface and wiring only.
Business logic will be implemented in Phase 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from voiceflow.core.config import VADConfig
    from voiceflow.core.events import EventBus


from voiceflow.core.events import AudioCaptured, SpeechDetected
from voiceflow.core.logger import logger

class VoiceActivityDetector:
    """Silero VAD wrapper (Pass-through for now)."""

    def __init__(self, config: VADConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus

    async def start(self) -> None:
        """Load model and subscribe to AudioCaptured events."""
        self._bus.subscribe(AudioCaptured, self._on_audio_captured)
        logger.info("VAD initialized (pass-through mode).")

    async def stop(self) -> None:
        """Release model resources."""
        self._bus.unsubscribe(AudioCaptured, self._on_audio_captured)

    async def _on_audio_captured(self, event: AudioCaptured) -> None:
        """Process captured audio and emit SpeechDetected."""
        if not self._config.enabled:
            await self._bus.emit(SpeechDetected(audio=event.audio, sample_rate=event.sample_rate))
            return
            
        # TODO: Implement actual Silero VAD logic.
        # For now, pass all audio through.
        logger.debug("VAD pass-through.")
        await self._bus.emit(SpeechDetected(audio=event.audio, sample_rate=event.sample_rate))
