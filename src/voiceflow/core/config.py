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

def get_appdata_dir() -> Path:
    """Get the standard Windows AppData path for VoiceFlow."""
    import os
    appdata = os.environ.get('APPDATA', '')
    if not appdata:
        appdata = str(Path.home() / 'AppData' / 'Roaming')
    
    path = Path(appdata) / 'VoiceFlowLocal'
    path.mkdir(parents=True, exist_ok=True)
    return path

# ---------------------------------------------------------------------------
# Section models
# ---------------------------------------------------------------------------



class AudioConfig(BaseModel):
    """Microphone / audio-capture settings."""

    device_index: Optional[int] = None
    sample_rate: int = Field(default=16_000, ge=8_000, le=48_000)
    channels: int = Field(default=1, ge=1, le=2)
    chunk_size: int = Field(default=1024, ge=256, le=8192)
    input_gain: int = Field(default=70, ge=0, le=100)
    noise_suppression: bool = True
    save_audio: bool = False  # Debugging: save raw audio to disk


class VADConfig(BaseModel):
    """Silero Voice-Activity-Detection settings."""

    enabled: bool = True
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    min_speech_duration_ms: int = Field(default=250, ge=0)
    padding_ms: int = Field(default=300, ge=0)


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

    model_config = SettingsConfigDict(env_file=str(get_appdata_dir() / ".env"), env_file_encoding="utf-8", extra="ignore")


class LLMConfig(BaseModel):
    """LLM refinement engine settings."""

    enabled: bool = True
    provider: str = "ollama"  # e.g., llamacpp, ollama, openai, anthropic, gemini, openrouter, custom
    model: str = "llama3"
    api_base: Optional[str] = None  # Used for custom APIs or overriding defaults

    # Local model specific
    model_path: Optional[str] = "models/llm/model.gguf"
    n_gpu_layers: int = 0

    n_ctx: int = Field(default=2048, ge=512)
    max_tokens: int = Field(default=512, ge=64)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    prompt_template: str = "default"


class HotkeyConfig(BaseModel):
    """Global hotkey settings."""

    combination: str = "ctrl+space"
    mode: Literal["push_to_talk", "toggle"] = "toggle"


class InjectionConfig(BaseModel):
    """Text-injection settings."""

    method: Literal["typewrite", "clipboard"] = "typewrite"
    keystroke_delay: float = Field(default=0.01, ge=0.0, le=1.0)


class UIConfig(BaseModel):
    """User interface settings."""

    theme: Literal["system", "light", "dark"] = "system"
    startup_on_windows: bool = False
    minimize_to_tray: bool = True
    auto_check_updates: bool = True
    show_notifications: bool = True
    show_tray: bool = True
    first_run: bool = True

    # Orb Settings
    show_orb: bool = True
    show_app_icon: bool = True
    voice_animations: bool = True
    orb_transparency: float = Field(default=0.9, ge=0.1, le=1.0)
    animation_intensity: float = Field(default=1.0, ge=0.1, le=3.0)
    always_on_top: bool = True
    orb_size: int = Field(default=80, ge=40, le=200)
    
    # Position on screen (None means near cursor)
    orb_pos_x: Optional[int] = None
    orb_pos_y: Optional[int] = None


class LoggingConfig(BaseModel):
    """Logging settings."""

    level: str = "INFO"
    log_file: str | None = "logs/voiceflow.log"
    rotation: str = "10 MB"
    retention: int = 3
    send_telemetry: bool = False

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

def get_default_config_path() -> Path:
    return get_appdata_dir() / "config.yaml"

def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else get_default_config_path()

    if not config_path.exists():
        # Create a default configuration if it doesn't exist in AppData
        config_path.write_text("audio:\n  device_index: null\nstt:\n  engine: faster_whisper\n  model_size: tiny.en\nllm:\n  enabled: true\n  provider: ollama\nhotkey:\n  combination: ctrl+space\n  mode: toggle\ninjection:\n  method: clipboard\nui:\n  theme: system\n")
        
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML: {exc}") from exc

    try:
        config = AppConfig(**raw)
        # Force log file to be inside AppData if not absolute
        if config.logging.log_file and not Path(config.logging.log_file).is_absolute():
            config.logging.log_file = str(get_appdata_dir() / "logs" / Path(config.logging.log_file).name)
        return config
    except Exception as exc:
        raise ConfigError(f"Configuration validation failed: {exc}") from exc


def save_config(config: AppConfig, path: str | Path | None = None) -> None:
    """Save the configuration back to disk."""
    config_path = Path(path) if path else get_default_config_path()
    try:
        raw = config.model_dump()
        config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    except Exception as exc:
        raise ConfigError(f"Failed to save configuration: {exc}") from exc
