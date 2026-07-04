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

## Installation

### Pre-built Windows Executable
*(Coming Soon - Check Releases)*

### From Source
1. Clone the repository: `git clone https://github.com/Praharsh04/Vociflow.git`
2. Install Python 3.10+
3. Install dependencies: `pip install -e .`
4. Run the app: `python -m voiceflow`

## Configuration

On first run, VoiceFlow Local will open a Setup Wizard to help you select your STT engine and LLM provider. Settings are saved locally to `config.yaml` and `.env` (for API keys).

## Usage

1. Start the application. It will run quietly in the system tray.
2. Focus on any text field in any application.
3. Hold `Ctrl+Space` (or your configured hotkey), speak your thought naturally, and release.
4. The floating overlay will indicate "Processing..." then "Refining...".
5. The final, beautifully formatted text will instantly appear in your active text field!

## License

MIT License. See `LICENSE` for details.
