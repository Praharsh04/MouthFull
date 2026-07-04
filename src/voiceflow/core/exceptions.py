"""Custom exception hierarchy for VoiceFlow Local.

All VoiceFlow exceptions inherit from VoiceFlowError, making it easy
to catch any application-level error with a single except clause.
"""


class VoiceFlowError(Exception):
    """Base exception for all VoiceFlow errors."""


# --- Configuration -----------------------------------------------------------

class ConfigError(VoiceFlowError):
    """Raised when configuration loading or validation fails."""


# --- Audio -------------------------------------------------------------------

class AudioError(VoiceFlowError):
    """Base exception for audio-related errors."""


class AudioDeviceNotFoundError(AudioError):
    """Raised when the specified audio input device cannot be found."""


class AudioCaptureError(AudioError):
    """Raised when audio capture fails during recording."""


# --- Voice Activity Detection ------------------------------------------------

class VADError(VoiceFlowError):
    """Raised when voice activity detection encounters an error."""


# --- Speech-to-Text ----------------------------------------------------------

class STTError(VoiceFlowError):
    """Base exception for speech-to-text errors."""


class STTModelLoadError(STTError):
    """Raised when the STT model fails to load."""


class STTTranscriptionError(STTError):
    """Raised when transcription of audio fails."""


# --- LLM Refinement ----------------------------------------------------------

class LLMError(VoiceFlowError):
    """Base exception for LLM-related errors."""


class LLMModelLoadError(LLMError):
    """Raised when the LLM model fails to load."""


class LLMInferenceError(LLMError):
    """Raised when LLM inference (text refinement) fails."""


# --- Input / Injection -------------------------------------------------------

class HotkeyError(VoiceFlowError):
    """Raised when hotkey registration or listening fails."""


class TextInjectionError(VoiceFlowError):
    """Raised when typing text into the active window fails."""


# --- Pipeline ----------------------------------------------------------------

class PipelineError(VoiceFlowError):
    """Raised when the processing pipeline encounters a fatal error."""
