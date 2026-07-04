# 🎙️ MouthFull AI

Welcome to **MouthFull**! Your all-in-one, fully local AI voice assistant and transcription tool.

MouthFull allows you to easily transcribe speech, control local AI models, and chat with AI assistants entirely on your own hardware without relying on cloud services. We prioritize your privacy, low latency, and ease of use.

---

## 🚀 Getting Started

We've made launching MouthFull as easy as possible! 

If you are using the compiled version, simply look for the **MouthFull** shortcut on your Desktop or double-click `MouthFull.exe`. 

**No terminal or command prompt needed!** 

### For Developers (Running from Source)
If you want to run the code directly, make sure you have Python 3.10+ installed and run the following in your terminal:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python -m mouthfull
```

---

## 🎯 Key Features

- **Blazing Fast Defaults**: MouthFull now ships with `faster-whisper` (`tiny.en`) out of the box for ultra-low latency, real-time voice dictation that works flawlessly even on older hardware.
- **One-Click STT Models**: Effortlessly browse and download top-tier Speech-to-Text models (like NVIDIA Canary, Whisper Large v3 Turbo, and Moonshine) directly from the beautiful UI. Switch models instantly without restarting!
- **Privacy First**: Everything runs locally on your PC. No data is sent to external servers unless you explicitly configure a cloud LLM provider.
- **Global Hotkey**: Press `Ctrl + Space` from anywhere on your PC to toggle the microphone and start speaking. 
- **Dynamic Floating Orb**: A sleek, fully animated desktop widget gives you visual feedback while you speak! The orb smoothly fades in on hotkey trigger and automatically dismisses itself when your task is complete so it never clutters your screen.
- **Fast and Lightweight**: Built with performance in mind using PySide6, asyncio, and optimized AI pipelines.

---

## 🛠️ How to Use

1. **Launch the App:** Open MouthFull via your Desktop shortcut or `MouthFull.exe`.
2. **Start Speaking:** Hold or press `Ctrl + Space` (default hotkey) to capture audio. The floating orb will appear at the bottom of your screen and pulse to your voice. When you release or finish, the AI will transcribe and process your speech, and the orb will smoothly hide itself!
3. **Download a Model (Optional):** Go to the **Speech Models** page, select a recommended high-accuracy model (like Whisper Large), and click "Install". Wait for the download to finish, then hit "Select" to swap engines instantly.

### Customization
- Head over to the **Settings** page to change your microphone, adjust the global hotkey, or tweak the theme.
- Go to the **LLMs** page if you want to connect your transcription directly to an AI language model (like Llama, Mistral, or OpenAI).

---

## 💬 Support & Troubleshooting

- **Audio not working?** Make sure you selected the correct microphone in the Settings tab.
- **Models failing to download?** Check your internet connection. You can pause and resume downloads at any time.
- **App feels slow?** Check the **Performance** tab to see latency breakdowns. Running AI models locally requires a capable CPU/GPU. Try using a smaller model like `Whisper Tiny` or `Moonshine` if things feel sluggish.

Enjoy using MouthFull! 🚀
