"""Audio input device enumeration and selection.

Responsibilities:
- List available audio input devices.
- Validate that the configured device index exists.
- Provide a helper to select a device interactively.
"""

from __future__ import annotations

from dataclasses import dataclass

import sounddevice as sd

from mouthfull.utils.exceptions import AudioDeviceNotFoundError


@dataclass
class AudioDevice:
    """Represents a detected audio input device."""

    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float


def list_input_devices() -> list[AudioDevice]:
    """Return all available audio input devices."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append(
                AudioDevice(
                    index=i,
                    name=dev["name"],
                    max_input_channels=dev["max_input_channels"],
                    default_sample_rate=dev["default_samplerate"],
                )
            )
    return devices


def validate_device_index(index: int | None) -> int:
    """Validate that *index* is a valid input device, returning it.

    If *index* is ``None``, return the system default device index.
    """
    if index is None:
        default = sd.default.device[0]
        if default is None or default < 0:
            raise AudioDeviceNotFoundError("No default audio input device found.")
        return default

    try:
        dev = sd.query_devices(index)
        if dev["max_input_channels"] <= 0:
            raise AudioDeviceNotFoundError(f"Device {index} has no input channels.")
        return index
    except ValueError as e:
        raise AudioDeviceNotFoundError(f"Invalid audio device index {index}: {e}")
