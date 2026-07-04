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
        self.root.geometry("500x350")
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
        
        # Hotkey
        hotkey_frame = ttk.LabelFrame(main_frame, text="2. Global Hotkey", padding="10")
        hotkey_frame.pack(fill=tk.X, pady=(0, 20))
        if self.config.hotkey.mode == "toggle":
            ttk.Label(hotkey_frame, text=f"Press {self.config.hotkey.combination.upper()} to start recording, and Enter to stop.", font=("Segoe UI", 10, "bold")).pack()
        else:
            ttk.Label(hotkey_frame, text=f"Hold {self.config.hotkey.combination.upper()} to record.", font=("Segoe UI", 10, "bold")).pack()
        
        # Finish
        ttk.Button(main_frame, text="Complete Setup", command=self._finish).pack(pady=10)
        
        self.root.mainloop()
        
    def _finish(self):
        self.config.ui.first_run = False
        import yaml
        from voiceflow.core.config import get_default_config_path
        config_path = get_default_config_path()
        try:
            # Dump to dict, avoiding pydantic v2 warning if possible
            data = self.config.model_dump() if hasattr(self.config, 'model_dump') else self.config.dict()
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
        except Exception as e:
            print("Failed to save config in wizard:", e)
        self.root.destroy()
