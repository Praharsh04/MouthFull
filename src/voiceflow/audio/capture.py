"""Microphone audio capture using sounddevice.

Responsibilities:
- Open an audio input stream at the configured sample rate.
- Buffer audio frames while recording is active.
- Emit an AudioCaptured event when recording stops.
"""

from __future__ import annotations

import asyncio
import queue
from typing import TYPE_CHECKING, Any

import numpy as np
import sounddevice as sd
from numpy.typing import NDArray

from voiceflow.core.events import (
    AudioCaptured,
    HotkeyPressed,
    HotkeyReleased,
    PipelineError,
    StatusChanged,
    AudioLevelChanged,
)
from voiceflow.core.logger import logger

if TYPE_CHECKING:
    from voiceflow.core.config import AudioConfig
    from voiceflow.core.events import EventBus


class AudioCapture:
    """Manages microphone recording lifecycle."""

    def __init__(self, config: AudioConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        
        self._recording = False
        self._audio_queue: queue.Queue[NDArray[np.float32]] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._loop = asyncio.get_running_loop()

    async def start(self) -> None:
        """Subscribe to hotkey events to control recording."""
        self._bus.subscribe(HotkeyPressed, self._on_hotkey_pressed)
        self._bus.subscribe(HotkeyReleased, self._on_hotkey_released)
        logger.info("AudioCapture initialised.")

    async def stop(self) -> None:
        """Stop any active recording and unsubscribe."""
        self._bus.unsubscribe(HotkeyPressed, self._on_hotkey_pressed)
        self._bus.unsubscribe(HotkeyReleased, self._on_hotkey_released)
        if self._recording:
            await self._stop_recording()

    async def _on_hotkey_pressed(self, event: HotkeyPressed) -> None:
        if not self._recording:
            await self._start_recording()

    async def _on_hotkey_released(self, event: HotkeyReleased) -> None:
        if self._recording:
            await self._stop_recording()

    def _audio_callback(
        self, indata: NDArray[np.float32], frames: int, time: Any, status: sd.CallbackFlags
    ) -> None:
        """Called by sounddevice for each audio block."""
        if status:
            logger.warning("Audio capture status: {}", status)
        
        if self._recording:
            # indata is read-only, make a copy
            copied_data = indata.copy()
            self._audio_queue.put(copied_data)
            
            # Calculate RMS for volume meter
            if copied_data.size > 0:
                rms = float(np.sqrt(np.mean(copied_data**2)))
                # Normalize somewhat (0.0 to 1.0)
                level = min(1.0, rms * 10.0)
                asyncio.run_coroutine_threadsafe(
                    self._bus.emit(AudioLevelChanged(level=level)),
                    self._loop
                )

    async def _start_recording(self) -> None:
        logger.debug("Starting audio recording...")
        self._recording = True
        
        # Clear the queue
        while not self._audio_queue.empty():
            self._audio_queue.get_nowait()
            
        try:
            self._stream = sd.InputStream(
                device=self._config.device_index,
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype=np.float32,
                blocksize=self._config.chunk_size,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Recording started.")
            # Tell the UI we are recording
            asyncio.run_coroutine_threadsafe(
                self._bus.emit(StatusChanged(status="recording", message="Listening...")),
                self._loop
            )
        except Exception as e:
            self._recording = False
            logger.error("Failed to start audio stream (Permission or device error): {}", e)
            asyncio.run_coroutine_threadsafe(
                self._bus.emit(PipelineError(stage="audio_capture", error=e)),
                self._loop
            )
            asyncio.run_coroutine_threadsafe(
                self._bus.emit(StatusChanged(status="error", message="Mic Error")),
                self._loop
            )

    async def _stop_recording(self) -> None:
        logger.debug("Stopping audio recording...")
        self._recording = False
        
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            
        # Collect all frames
        frames = []
        while not self._audio_queue.empty():
            frames.append(self._audio_queue.get_nowait())
            
        if not frames:
            logger.warning("Recording stopped but no audio frames were captured.")
            asyncio.run_coroutine_threadsafe(
                self._bus.emit(StatusChanged(status="idle", message="")),
                self._loop
            )
            return
            
        audio_data = np.concatenate(frames, axis=0)
        # Ensure mono
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]
            
        logger.info("Recording stopped. Captured {:.2f}s of audio.", len(audio_data) / self._config.sample_rate)
        
        if getattr(self._config, 'save_audio', False):
            import soundfile as sf
            from pathlib import Path
            from datetime import datetime
            
            Path("logs").mkdir(exist_ok=True)
            filename = f"logs/debug_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            try:
                sf.write(filename, audio_data, self._config.sample_rate)
                logger.info("Saved debug audio to {}", filename)
            except Exception as e:
                logger.error("Failed to save debug audio: {}", e)
        
        # Tell the UI we are processing
        asyncio.run_coroutine_threadsafe(
            self._bus.emit(StatusChanged(status="processing", message="Processing...")),
            self._loop
        )
        
        # Emit the captured audio
        await self._bus.emit(AudioCaptured(audio=audio_data, sample_rate=self._config.sample_rate))
