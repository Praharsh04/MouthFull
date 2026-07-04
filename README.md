# VoiceFlow Local

A private, completely local AI dictation assistant for Windows.

VoiceFlow Local allows you to dictate text using your microphone and have it intelligently transcribed and refined using local AI models, then automatically injected into whatever application you are using. No cloud APIs required, ensuring absolute privacy.

## Features

- **Global Hotkey Dictation**: Press and hold a hotkey (e.g., `Ctrl+Space`), speak, and release to type.
- **Local Speech-to-Text**: Powered by Faster-Whisper or NVIDIA Parakeet for highly accurate, offline transcription.
- **AI Refinement**: Automatically fixes grammar, removes filler words, and formats text using local LLMs via Ollama, Llama.cpp, or custom APIs (OpenAI, Anthropic, Gemini, OpenRouter also supported).
- **Global Text Injection**: Instantly pastes the refined text into your active window (Word, browser, code editor, etc.).
- **Modern UI**: Lightweight system tray integration and a beautiful floating status overlay.
- **Custom Prompts**: Manage and switch between custom prompt templates easily.

---

## Installation Guide

### Option 1: Installer (Recommended)
1. Go to the [Releases](../../releases) page.
2. Download `VoiceFlow_Local_Setup.exe`.
3. Run the installer and follow the instructions.
4. Launch VoiceFlow Local from the Start Menu or Desktop shortcut.

### Option 2: Portable ZIP
1. Go to the [Releases](../../releases) page.
2. Download `VoiceFlow_Local_Portable.zip`.
3. Extract the ZIP to your desired location.
4. Run `VoiceFlow.exe`.

### Option 3: From Source (Developers)
1. Clone the repository: `git clone https://github.com/voiceflow/voiceflow-local.git`
2. Install Python 3.10+
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `python -m voiceflow` (or double click `run_dev.bat`)

---

## Development Guide

### Setting up the Environment
1. Clone the repository.
2. Open a terminal and run `pip install -r requirements.txt` to install all dependencies.
3. To run the app during development, you can use `run_dev.bat` or `python -m voiceflow`.

### Building the Project
We use PyInstaller to bundle the application into a standalone Windows executable.
- Run `build.bat` or `build.ps1` to create the `dist/Release/VoiceFlow` directory.
- To create the installer, install [Inno Setup](https://jrsoftware.org/isinfo.php) and compile `installer.iss`.

### Clean Up
- Run `clean.bat` to remove the `build` and `dist` directories.

---

## Architecture Overview

VoiceFlow Local is built with a decoupled architecture for maximum stability and responsiveness:

1. **Frontend (UI)**: Built with PySide6 (Qt). Manages the System Tray, Settings Window, Models/LLM Configuration Pages, and the floating AI Orb.
2. **Backend (Services)**:
   - **Audio Capture**: Uses `sounddevice` to stream raw audio.
   - **VAD (Voice Activity Detection)**: Monitors microphone levels and segments speech.
   - **STT (Speech-to-Text)**: Translates audio into raw text using `faster-whisper`.
   - **LLM Refinement**: Refines the raw text using local (Ollama) or remote APIs.
   - **Injector**: Uses `pynput` and `pyperclip` to inject the final text into the active window.
3. **EventBus**: The frontend and backend communicate purely via an asynchronous `EventBus` (`voiceflow.core.events`). This ensures UI operations never block backend processing and vice-versa.

---

## Contributing Guide

We welcome contributions! 
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/awesome-feature`).
3. Make your changes.
4. Test your changes locally.
5. Create a Pull Request against the `main` branch.

Please ensure your code conforms to the existing style and architecture. The project uses `ruff` for linting.

---

## License

MIT License. See `LICENSE` for details.
