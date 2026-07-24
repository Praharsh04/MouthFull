# 🎙️ MouthFull AI

Welcome to **MouthFull**! Your all-in-one, fully local AI voice dictation and transcription assistant.

MouthFull allows you to easily transcribe speech, inject text anywhere you want, and wrap your speech in dynamic LLM prompts entirely on your own hardware without relying on cloud services. We prioritize your privacy, ultra-low latency, and ease of use.

---

## 🚀 Getting Started

We've made launching MouthFull on Windows as easy as possible! 

### Download the Compiled Windows App (Easiest)
1. Go to the **[Releases](https://github.com/Praharsh04/Vociflow/releases)** page on our GitHub repository.
2. Download the latest `MouthFull.zip` release.
3. Extract the folder anywhere on your PC (e.g., your Documents folder).
4. Double click `MouthFull.exe` to launch the app!
*(Tip: Right-click `MouthFull.exe` and select "Send to > Desktop (create shortcut)" for quick access).*

**No terminal or command prompt needed!** 

### For Developers (Running or Building from Source)
If you want to run the code directly, make sure you have Python 3.10+ installed and run the following in your terminal:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python -m mouthfull

# 3. Build the Windows Executable locally
python scripts/build.py --config Release
```

The compiled output will be placed in `dist/Release/MouthFull/`.

---

## 🎯 Key Features

- **Blazing Fast Defaults**: MouthFull ships with NVIDIA's `Parakeet TDT 1.1b` out of the box for ultra-low latency, real-time voice dictation that works flawlessly and instantly.
- **Application-Aware Prompt Routing**: Seamlessly wrap your transcribed voice in a custom LLM prompt *automatically based on the app you are using*. The Prompt Processor detects your active window (VS Code, Chrome, etc.) and routes the text through your custom prompts using the `{{input}}` macro before typing it out!
- **Instant Text Injection**: Employs an ultra-fast clipboard injection method to instantly paste long blocks of generated text into your active editor (Codex, VS Code, Cursor, Chrome) without waiting for keystroke emulation.
- **One-Click STT Models**: Effortlessly browse and download top-tier Speech-to-Text models (NVIDIA Canary, Whisper Large v3 Turbo, Moonshine) directly from the beautiful UI. Switch models instantly!
- **Dynamic Floating Orb**: A sleek, fully animated desktop widget gives you visual feedback! The orb smoothly fades in on hotkey trigger, turns Sky Blue while listening, shifts to Green while processing, and dismisses itself when done.
- **Global Hotkey**: Press `Ctrl + Space` from anywhere on your PC to toggle the microphone and start speaking. 

---

## 🛠️ How to Use

1. **Launch the App:** Open MouthFull via your Desktop shortcut or `MouthFull.exe`.
2. **Start Speaking:** Hold or press `Ctrl + Space` (default hotkey) to capture audio. The floating orb will appear at the bottom center of your screen and pulse to your voice. When you finish, the AI will transcribe and type your speech instantly into whatever window you have focused!
3. **Use the Prompt Processor (Optional):** Go to the **Prompt Processor** tab. Add your favorite applications (e.g., VS Code) and set up specific prompts for them (like `Fix this code: {{input}}`). When you dictate into those apps, MouthFull will automatically process your voice through the AI provider and type the optimized result!
4. **Download a Model (Optional):** Go to the **Speech Models** page, select a recommended high-accuracy model, and click "Install". 

### Customization
- Head over to the **Settings** page to change your microphone, adjust the global hotkey, or tweak the theme.
- **Global Providers**: Go to the **Prompt Processor > AI Providers** to connect your transcription directly to an AI language model (like Ollama, Llama, Mistral, OpenAI, Anthropic, Gemini, Groq, Together).

---

## 💬 Support & Troubleshooting

- **Audio not working?** Make sure you selected the correct microphone in the Settings tab.
- **Models failing to download?** Check your internet connection. You can pause and resume downloads at any time.
- **App feels slow?** Running AI models locally requires a capable CPU/GPU. Try using a smaller model like `Moonshine` if things feel sluggish.
