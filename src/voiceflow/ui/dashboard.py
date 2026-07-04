"""Main Dashboard window for VoiceFlow Local."""

import tkinter as tk
from tkinter import ttk
import asyncio
from typing import TYPE_CHECKING
import threading

from voiceflow.core.logger import logger
from voiceflow.core.events import StatusChanged, TranscriptReady, RefinedTextReady

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig
    from voiceflow.core.events import EventBus

class DashboardWindow:
    def __init__(self, config: 'AppConfig', bus: 'EventBus'):
        self._config = config
        self._bus = bus
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        
        # State vars
        self._status_var = None
        self._speech_model_var = None
        self._llm_var = None
        self._mic_var = None
        self._recent_activity = []

    def show(self):
        """Show the dashboard window, safely handling thread isolation."""
        if self._root is not None and self._root.winfo_exists():
            self._root.lift()
            self._root.focus_force()
            return
            
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self._root = tk.Tk()
        self._root.title("VoiceFlow Local - Dashboard")
        self._root.geometry("600x500")
        
        # Style
        theme = self._config.ui.theme
        if theme == "dark":
            bg_color = "#1e1e1e"
            fg_color = "#2d2d2d"
            text_color = "#ffffff"
        else:
            bg_color = "#f0f0f0"
            fg_color = "#ffffff"
            text_color = "#333333"

        self._root.configure(bg=bg_color)
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("TFrame", background=bg_color)
        style.configure("TLabelframe", background=bg_color, foreground=text_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=text_color)
        style.configure("TLabel", background=bg_color, foreground=text_color)
        style.configure("TButton", font=("Segoe UI", 9))
        
        self._status_var = tk.StringVar(value="Status: Idle")
        self._speech_model_var = tk.StringVar(value=f"Speech Model: {self._config.stt.engine.replace('_', ' ').title()}")
        self._llm_var = tk.StringVar(value=f"LLM Provider: {self._config.llm.provider.title()}")
        self._mic_var = tk.StringVar(value=f"Microphone: {self._config.audio.device_name or 'Default'}")
        
        # Layout
        main_frame = ttk.Frame(self._root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(main_frame, text="VoiceFlow Dashboard", font=("Segoe UI", 16, "bold"))
        header.pack(anchor="w", pady=(0, 20))
        
        # Info grid
        info_frame = ttk.LabelFrame(main_frame, text="Current State", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(info_frame, textvariable=self._status_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5, padx=10)
        ttk.Label(info_frame, textvariable=self._speech_model_var).grid(row=0, column=1, sticky="w", pady=5, padx=10)
        ttk.Label(info_frame, textvariable=self._llm_var).grid(row=1, column=0, sticky="w", pady=5, padx=10)
        ttk.Label(info_frame, textvariable=self._mic_var).grid(row=1, column=1, sticky="w", pady=5, padx=10)
        
        # Action Buttons
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=(0, 20))
        
        btn_start = ttk.Button(actions_frame, text="Start Listening", command=self._on_start_listen)
        btn_start.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_stop = ttk.Button(actions_frame, text="Stop Listening", command=self._on_stop_listen)
        btn_stop.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_restart = ttk.Button(actions_frame, text="Restart Backend", command=self._on_restart)
        btn_restart.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_settings = ttk.Button(actions_frame, text="Settings", command=self._on_settings)
        btn_settings.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_models = ttk.Button(actions_frame, text="Speech Models", command=self._on_models)
        btn_models.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_llms = ttk.Button(actions_frame, text="LLM Providers", command=self._on_llms)
        btn_llms.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_logs = ttk.Button(actions_frame, text="View Logs", command=self._on_logs)
        btn_logs.pack(side=tk.LEFT)
        
        # Recent Activity
        activity_frame = ttk.LabelFrame(main_frame, text="Recent Activity", padding="10")
        activity_frame.pack(fill=tk.BOTH, expand=True)
        
        self._activity_text = tk.Text(activity_frame, height=10, state="disabled", bg="#f0f0f0", font=("Consolas", 9))
        self._activity_text.pack(fill=tk.BOTH, expand=True)
        
        self._log_activity("Dashboard opened.")
        
        # Subscribe to events
        self._bus.subscribe(StatusChanged, self._on_status_changed_event)
        self._bus.subscribe(TranscriptReady, self._on_transcript_event)
        self._bus.subscribe(RefinedTextReady, self._on_refined_event)
        
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _on_close(self):
        self._bus.unsubscribe(StatusChanged, self._on_status_changed_event)
        self._bus.unsubscribe(TranscriptReady, self._on_transcript_event)
        self._bus.unsubscribe(RefinedTextReady, self._on_refined_event)
        self._root.destroy()
        self._root = None

    def _log_activity(self, text: str):
        if self._root is None or not self._root.winfo_exists():
            return
        def _append():
            self._activity_text.configure(state="normal")
            self._activity_text.insert(tk.END, text + "\n")
            self._activity_text.see(tk.END)
            self._activity_text.configure(state="disabled")
        self._root.after(0, _append)

    # --- Actions ---
    def _on_start_listen(self):
        pass # To be wired

    def _on_stop_listen(self):
        from voiceflow.core.events import PipelineAbort
        asyncio.run_coroutine_threadsafe(self._bus.emit(PipelineAbort()), asyncio.get_running_loop())
        self._log_activity("Pipeline abort requested.")

    def _on_restart(self):
        self._log_activity("Backend restart requested (Not fully implemented).")

    def _on_settings(self):
        from voiceflow.ui.settings import SettingsWindow
        win = SettingsWindow(self._config)
        win.show()

    def _on_models(self):
        from voiceflow.ui.models import ModelManagerWindow
        win = ModelManagerWindow(self._config, self._bus)
        win.show()

    def _on_llms(self):
        from voiceflow.ui.llms import LLMManagerWindow
        win = LLMManagerWindow(self._config, self._bus)
        win.show()

    def _on_logs(self):
        import os
        log_path = "logs/voiceflow.log"
        if os.path.exists(log_path):
            os.startfile(log_path)

    # --- Events ---
    async def _on_status_changed_event(self, event: StatusChanged):
        if self._root:
            self._root.after(0, lambda: self._status_var.set(f"Status: {event.status.title()}"))
            if event.message:
                self._log_activity(f"[{event.status.upper()}] {event.message}")

    async def _on_transcript_event(self, event: TranscriptReady):
        self._log_activity(f"Transcribed: {event.text}")

    async def _on_refined_event(self, event: RefinedTextReady):
        self._log_activity(f"Refined: {event.text}")
