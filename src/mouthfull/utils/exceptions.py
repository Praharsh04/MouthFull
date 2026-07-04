"""Custom exception hierarchy for MouthFull Local.

All MouthFull exceptions inherit from MouthFullError, making it easy
to catch any application-level error with a single except clause.
"""


class MouthFullError(Exception):
    """Base exception for all MouthFull errors."""


# --- Configuration -----------------------------------------------------------

class ConfigError(MouthFullError):
    """Raised when configuration loading or validation fails."""


# --- Audio -------------------------------------------------------------------

class AudioError(MouthFullError):
    """Base exception for audio-related errors."""


class AudioDeviceNotFoundError(AudioError):
    """Raised when the specified audio input device cannot be found."""


class AudioCaptureError(AudioError):
    """Raised when audio capture fails during recording."""


# --- Voice Activity Detection ------------------------------------------------

class VADError(MouthFullError):
    """Raised when voice activity detection encounters an error."""


# --- Speech-to-Text ----------------------------------------------------------

class STTError(MouthFullError):
    """Base exception for speech-to-text errors."""


class STTModelLoadError(STTError):
    """Raised when the STT model fails to load."""


class STTTranscriptionError(STTError):
    """Raised when transcription of audio fails."""


# --- LLM Refinement ----------------------------------------------------------

class LLMError(MouthFullError):
    """Base exception for LLM-related errors."""


class LLMModelLoadError(LLMError):
    """Raised when the LLM model fails to load."""


class LLMInferenceError(LLMError):
    """Raised when LLM inference (text refinement) fails."""


# --- Input / Injection -------------------------------------------------------

class HotkeyError(MouthFullError):
    """Raised when hotkey registration or listening fails."""


class TextInjectionError(MouthFullError):
    """Raised when typing text into the active window fails."""


# --- Pipeline ----------------------------------------------------------------

class PipelineError(MouthFullError):
    """Raised when the processing pipeline encounters a fatal error."""
