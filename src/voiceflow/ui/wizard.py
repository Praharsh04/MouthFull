"""First-time Setup Wizard."""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
import threading

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig

class SetupWizard:
    def __init__(self, config: 'AppConfig'):
        self.config = config
        self.root = None

    def show_blocking(self):
        self.root = tk.Tk()
        self.root.title("Welcome to VoiceFlow Local")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
            
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="First-Time Setup", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))
        
        ttk.Label(main_frame, text="Welcome! Let's get your local AI dictation ready.", wraplength=450).pack(pady=(0, 20))
        
        # Audio
        audio_frame = ttk.LabelFrame(main_frame, text="1. Microphone Setup", padding="10")
        audio_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(audio_frame, text="VoiceFlow uses your default system microphone.", wraplength=400).pack()
        
        # LLM
        llm_frame = ttk.LabelFrame(main_frame, text="2. LLM Provider (Optional)", padding="10")
        llm_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(llm_frame, text="If you use OpenAI, enter your API key to refine dictations. Leave blank for local.", wraplength=400).pack(pady=(0, 5))
        
        self.api_key_var = tk.StringVar(value=self.config.llm.api_key or "")
        entry = ttk.Entry(llm_frame, textvariable=self.api_key_var, show="*")
        entry.pack(fill=tk.X)
        
        # Hotkey
        hotkey_frame = ttk.LabelFrame(main_frame, text="3. Global Hotkey", padding="10")
        hotkey_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(hotkey_frame, text=f"Hold {self.config.hotkey.combination.upper()} to record.", font=("Segoe UI", 10, "bold")).pack()
        
        # Finish
        ttk.Button(main_frame, text="Complete Setup", command=self._finish).pack(pady=10)
        
        self.root.mainloop()
        
    def _finish(self):
        self.config.llm.api_key = self.api_key_var.get()
        if self.config.llm.api_key:
            self.config.llm.provider = "openai"
            self.config.llm.model = "gpt-4o-mini"
        self.config.ui.first_run = False
        import json
        from voiceflow.core.config import get_default_config_path
        config_path = get_default_config_path()
        try:
            with open(config_path, "w") as f:
                json.dump(self.config.dict(), f, indent=4)
        except Exception:
            pass
        self.root.destroy()
