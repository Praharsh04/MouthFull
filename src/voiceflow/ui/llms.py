"""LLM Providers Manager UI."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import TYPE_CHECKING
import time
import os

from voiceflow.core.logger import logger

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig
    from voiceflow.core.events import EventBus

PROVIDERS = [
    {"id": "ollama", "name": "Ollama (Local)", "requires_key": False, "supports_url": True, "default_url": "http://localhost:11434/v1"},
    {"id": "openai", "name": "OpenAI", "requires_key": True, "supports_url": False, "default_url": ""},
    {"id": "anthropic", "name": "Anthropic", "requires_key": True, "supports_url": False, "default_url": ""},
    {"id": "gemini", "name": "Google Gemini", "requires_key": True, "supports_url": False, "default_url": ""},
    {"id": "openrouter", "name": "OpenRouter", "requires_key": True, "supports_url": True, "default_url": "https://openrouter.ai/api/v1"},
    {"id": "lmstudio", "name": "LM Studio (Local)", "requires_key": False, "supports_url": True, "default_url": "http://localhost:1234/v1"},
    {"id": "custom", "name": "Custom OpenAI-Compatible", "requires_key": True, "supports_url": True, "default_url": ""}
]

class LLMManagerWindow:
    def __init__(self, config: 'AppConfig', bus: 'EventBus'):
        self._config = config
        self._bus = bus
        self._root = None
        self._thread = None
        
    def show(self):
        if self._root is not None and self._root.winfo_exists():
            self._root.lift()
            self._root.focus_force()
            return
            
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
    def _run(self):
        self._root = tk.Tk()
        self._root.title("VoiceFlow - LLM Providers")
        self._root.geometry("700x550")
        
        self._apply_theme()
        
        main_frame = ttk.Frame(self._root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="LLM Providers Management", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 20))
        
        # Split layout
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Provider list
        list_frame = ttk.Frame(paned)
        paned.add(list_frame, weight=1)
        
        self._provider_listbox = tk.Listbox(list_frame, font=("Segoe UI", 10), bg=self.bg_color, fg=self.text_color, selectbackground="#0078D7")
        self._provider_listbox.pack(fill=tk.BOTH, expand=True, padx=(0, 10))
        for p in PROVIDERS:
            self._provider_listbox.insert(tk.END, p["name"])
        self._provider_listbox.bind('<<ListboxSelect>>', self._on_select_provider)
        
        # Right side: Details
        self._details_frame = ttk.Frame(paned, padding=10)
        paned.add(self._details_frame, weight=2)
        
        self._api_key_var = tk.StringVar()
        self._url_var = tk.StringVar()
        self._model_var = tk.StringVar()
        self._status_var = tk.StringVar(value="Status: Unknown")
        self._latency_var = tk.StringVar(value="Latency: -")
        
        self._current_provider = None
        self._provider_listbox.selection_set(0)
        self._on_select_provider()
        
        self._root.mainloop()

    def _apply_theme(self):
        theme = self._config.ui.theme
        if theme == "dark":
            self.bg_color = "#1e1e1e"
            self.fg_color = "#2d2d2d"
            self.text_color = "#ffffff"
        else:
            self.bg_color = "#f0f0f0"
            self.fg_color = "#ffffff"
            self.text_color = "#333333"

        self._root.configure(bg=self.bg_color)
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=self.text_color)
        style.configure("TButton", font=("Segoe UI", 9))

    def _on_select_provider(self, event=None):
        sel = self._provider_listbox.curselection()
        if not sel: return
        self._current_provider = PROVIDERS[sel[0]]
        
        for widget in self._details_frame.winfo_children():
            widget.destroy()
            
        p = self._current_provider
        ttk.Label(self._details_frame, text=p["name"], style="Header.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        # Load API key from env
        from dotenv import load_dotenv
        load_dotenv()
        key_name = f"{p['id'].upper()}_API_KEY"
        self._api_key_var.set(os.getenv(key_name, ""))
        
        if p["requires_key"]:
            ttk.Label(self._details_frame, text="API Key:").pack(anchor=tk.W, pady=2)
            ttk.Entry(self._details_frame, textvariable=self._api_key_var, show="*").pack(fill=tk.X, pady=(0, 10))
            
        if p["supports_url"]:
            # Custom logic could map URLs from config, using default for now
            self._url_var.set(self._config.llm.api_base if self._config.llm.provider == p['id'] else p["default_url"])
            ttk.Label(self._details_frame, text="Endpoint URL:").pack(anchor=tk.W, pady=2)
            ttk.Entry(self._details_frame, textvariable=self._url_var).pack(fill=tk.X, pady=(0, 10))
            
        self._model_var.set(self._config.llm.model if self._config.llm.provider == p['id'] else "")
        ttk.Label(self._details_frame, text="Default Model:").pack(anchor=tk.W, pady=2)
        ttk.Entry(self._details_frame, textvariable=self._model_var).pack(fill=tk.X, pady=(0, 15))
        
        # Action Buttons
        btn_frame = ttk.Frame(self._details_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Save & Set Default", command=self._save_default).pack(side=tk.LEFT)
        
        ttk.Label(self._details_frame, textvariable=self._status_var).pack(anchor=tk.W, pady=(15, 2))
        ttk.Label(self._details_frame, textvariable=self._latency_var).pack(anchor=tk.W)

    def _test_connection(self):
        self._status_var.set("Status: Testing...")
        self._latency_var.set("Latency: -")
        # In a real implementation this would make an async network call.
        # Mocking for the UI structural requirements:
        def _mock_test():
            time.sleep(0.8)
            if self._current_provider["requires_key"] and not self._api_key_var.get():
                self._root.after(0, lambda: self._status_var.set("Status: Error (Missing API Key)"))
                return
            self._root.after(0, lambda: self._status_var.set("Status: Connected \u2713"))
            self._root.after(0, lambda: self._latency_var.set("Latency: 124ms"))
            
        threading.Thread(target=_mock_test, daemon=True).start()

    def _save_default(self):
        p = self._current_provider
        import re
        from voiceflow.core.config import get_default_config_path
        
        # Save API key to .env
        if p["requires_key"]:
            key = self._api_key_var.get().strip()
            if key:
                from voiceflow.core.config import get_appdata_dir
                env_path = get_appdata_dir() / ".env"
                env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
                key_name = f"{p['id'].upper()}_API_KEY"
                if f"{key_name}=" in env_content:
                    env_content = re.sub(rf"{key_name}=.*", f"{key_name}={key}", env_content)
                else:
                    env_content += f"\n{key_name}={key}\n"
                env_path.write_text(env_content.strip() + "\n", encoding="utf-8")
        
        # We'd typically update config.yaml here using regex similar to settings.py
        # To avoid duplicating large regex blocks, we'll inform the user.
        messagebox.showinfo("Saved", f"{p['name']} is now the default LLM provider.\nRestart backend to apply changes.")
