# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-04
### Added
- Initial Open Source Release.
- Global Hotkey listener using `pynput`.
- Audio capture via `sounddevice` with internal VAD (Voice Activity Detection).
- Speech-to-Text integration with NVIDIA Parakeet and Faster-Whisper.
- LLM Provider architecture supporting Ollama, Llama.cpp, OpenAI, Anthropic, Gemini, OpenRouter, and Custom APIs.
- Global text injection via Clipboard integration for high speed and reliability.
- Modern graphical Settings UI built with Tkinter.
- Floating transparent Status Overlay with real-time volume indicator and processing animations.
- System Tray integration with native Windows Toast notifications.
- Robust `.env` and `config.yaml` persistence.
