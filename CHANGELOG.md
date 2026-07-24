# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-24
### Added
- **Application-Aware Prompt Routing**: Automatically detects the active application (e.g., VS Code, Chrome) and applies custom LLM prompts tailored to that app.
- **Premium UI Overhaul**: Redesigned the Prompt Processor and AI Providers interface into a unified, modal-driven, high-density dashboard inspired by Raycast and Wispr Flow.
- **Default Fallback**: Introduced a robust default prompt fallback system if an application does not have a specific prompt configured.
- **App Discovery Integration**: Built an OS registry scanner for an intuitive, searchable dropdown to quickly add installed applications to the prompt registry.
### Changed
- Removed the manual "Enable Prompt Processor" toggle; prompt processing is now automatic, transparent, and skips AI API calls completely (zero latency) if no prompt is matched.
- Merged the standalone "LLM Providers" tab entirely into the Prompt Processor via a compact accordion UI.
- Upgraded configuration schema to `v2` ensuring 100% backward compatibility for existing users while supporting the new features.
### Fixed
- Fixed accidental inclusion of API keys in repository files.
- Addressed minor edge cases in the text injection pipeline.


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
