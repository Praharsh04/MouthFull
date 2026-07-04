"""Application configuration with Pydantic validation.

Loads settings from ``config.yaml`` at the project root, with overrides
from environment variables prefixed with ``VOICEFLOW_``.

Usage::

    from voiceflow.core.config import load_config

    config = load_config()           # uses default config.yaml
    config = load_config("alt.yaml") # custom path
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from voiceflow.core.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Section models
# ---------------------------------------------------------------------------


class AudioConfig(BaseModel):
    """Microphone / audio-capture settings."""

    device_index: Optional[int] = None
    sample_rate: int = Field(16_000, ge=8_000, le=48_000)
    channels: int = Field(1, ge=1, le=2)
    chunk_size: int = Field(1024, ge=256, le=8192)
    save_audio: bool = False  # Debugging: save raw audio to disk


class VADConfig(BaseModel):
    """Silero Voice-Activity-Detection settings."""

    enabled: bool = True
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    min_speech_duration_ms: int = Field(250, ge=0)
    padding_ms: int = Field(300, ge=0)


class STTConfig(BaseModel):
    """Speech-to-text engine settings."""

    engine: Literal["faster_whisper", "parakeet"] = "parakeet"
    # Model size can be whisper sizes or parakeet model tags like "nvidia/parakeet-ctc-0.6b"
    model_size: str = "nvidia/parakeet-ctc-0.6b"
    device: Literal["auto", "cpu", "cuda"] = "auto"
    compute_type: Literal["auto", "int8", "float16", "float32"] = "auto"
    language: Optional[str] = None
    model_path: Optional[str] = None


from pydantic_settings import BaseSettings, SettingsConfigDict

class APIKeys(BaseSettings):
    """API keys loaded from .env or environment variables."""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    custom_api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class LLMConfig(BaseModel):
    """LLM refinement engine settings."""

    enabled: bool = True
    provider: str = "ollama"  # e.g., llamacpp, ollama, openai, anthropic, gemini, openrouter, custom
    model: str = "llama3"
    api_base: Optional[str] = None  # Used for custom APIs or overriding defaults
    
    # Local model specific
    model_path: Optional[str] = "models/llm/model.gguf"
    n_gpu_layers: int = 0
    
    n_ctx: int = Field(2048, ge=512)
    max_tokens: int = Field(512, ge=64)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    prompt_template: str = "default"


class HotkeyConfig(BaseModel):
    """Global hotkey settings."""

    combination: str = "ctrl+space"
    mode: Literal["push_to_talk", "toggle"] = "push_to_talk"


class InjectionConfig(BaseModel):
    """Text-injection settings."""

    method: Literal["typewrite", "clipboard"] = "typewrite"
    keystroke_delay: float = Field(0.01, ge=0.0, le=1.0)


class UIConfig(BaseModel):
    """System-tray UI settings."""

    show_tray: bool = True
    show_notifications: bool = True
    theme: Literal["light", "dark", "system"] = "system"
    startup_on_windows: bool = False


class LoggingConfig(BaseModel):
    """Logging settings."""

    level: str = "INFO"
    log_file: Optional[str] = "logs/voiceflow.log"
    rotation: str = "10 MB"
    retention: int = 3

    @field_validator("level")
    @classmethod
    def _validate_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"level must be one of {allowed}, got '{v}'")
        return upper


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------


class AppConfig(BaseModel):
    """Root application configuration."""

    audio: AudioConfig = AudioConfig()
    vad: VADConfig = VADConfig()
    stt: STTConfig = STTConfig()
    llm: LLMConfig = LLMConfig()
    hotkey: HotkeyConfig = HotkeyConfig()
    injection: InjectionConfig = InjectionConfig()
    ui: UIConfig = UIConfig()
    logging: LoggingConfig = LoggingConfig()


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = Path("config.yaml")


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load and validate application configuration from a YAML file.

    Parameters
    ----------
    path:
        Path to the YAML config file.  Falls back to ``config.yaml``
        in the current working directory.

    Returns
    -------
    AppConfig
        The fully validated configuration object.

    Raises
    ------
    ConfigError
        If the file cannot be read or validation fails.
    """
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path.resolve()}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML: {exc}") from exc

    try:
        return AppConfig(**raw)
    except Exception as exc:
        raise ConfigError(f"Configuration validation failed: {exc}") from exc
