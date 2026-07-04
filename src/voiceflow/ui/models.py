"""Speech Model Manager UI."""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import asyncio
from typing import TYPE_CHECKING
import time

from voiceflow.core.logger import logger

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig
    from voiceflow.core.events import EventBus

# Mock data for models based on requirements
SPEECH_MODELS = [
    {
        "id": "faster_whisper_base",
        "name": "Faster Whisper (Base)",
        "family": "Faster Whisper",
        "version": "1.0.0",
        "size": "140 MB",
        "perf": "Fast",
        "reqs": "CPU or 2GB VRAM",
        "installed": True
    },
    {
        "id": "faster_whisper_large",
        "name": "Faster Whisper (Large V3)",
        "family": "Faster Whisper",
        "version": "3.0.0",
        "size": "3.1 GB",
        "perf": "Accurate but slow",
        "reqs": "8GB VRAM",
        "installed": False
    },
    {
        "id": "parakeet_v2",
        "name": "NVIDIA Parakeet V2 (0.6B)",
        "family": "Parakeet",
        "version": "2.0.0",
        "size": "1.2 GB",
        "perf": "Very Fast",
        "reqs": "4GB VRAM",
        "installed": False
    },
    {
        "id": "parakeet_v3",
        "name": "NVIDIA Parakeet V3",
        "family": "Parakeet",
        "version": "3.0.0",
        "size": "2.4 GB",
        "perf": "Highly Accurate",
        "reqs": "6GB VRAM",
        "installed": False
    }
]

class DownloadTask:
    """A background asynchronous download task state."""
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.progress = 0.0
        self.status = "queued" # queued, downloading, paused, completed, error
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set() # True means running (not paused)

class ModelManagerWindow:
    def __init__(self, config: 'AppConfig', bus: 'EventBus'):
        self._config = config
        self._bus = bus
        self._root = None
        self._thread = None
        self._downloads: dict[str, DownloadTask] = {}
        
    def show(self):
        if self._root is not None and self._root.winfo_exists():
            self._root.lift()
            self._root.focus_force()
            return
            
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
    def _run(self):
        self._root = tk.Tk()
        self._root.title("VoiceFlow - Speech Models")
        self._root.geometry("850x600")
        
        self._apply_theme()
        
        main_frame = ttk.Frame(self._root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Speech Model Manager", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 20))
        
        # Grid layout for models
        self._list_frame = ttk.Frame(main_frame)
        self._list_frame.pack(fill=tk.BOTH, expand=True)
        
        self._render_model_list()
        
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
        style.configure("TLabelframe", background=self.bg_color, foreground=self.text_color)
        style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.text_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.text_color)
        style.configure("Sub.TLabel", font=("Segoe UI", 10, "bold"), foreground=self.text_color)
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("Horizontal.TProgressbar", background="#0078D7")

    def _render_model_list(self):
        for widget in self._list_frame.winfo_children():
            widget.destroy()
            
        canvas = tk.Canvas(self._list_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self._progress_bars = {}
        self._status_labels = {}
        self._action_buttons = {}

        for idx, model in enumerate(SPEECH_MODELS):
            self._render_model_card(scrollable_frame, model, idx)

    def _render_model_card(self, parent, model, idx):
        card = ttk.LabelFrame(parent, text=model["name"], padding="10")
        card.pack(fill=tk.X, expand=True, pady=10, padx=10, ipady=5)
        
        # Info Grid
        info_frame = ttk.Frame(card)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(info_frame, text=f"Family: {model['family']} | Version: {model['version']}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Size: {model['size']} | Requirements: {model['reqs']}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Performance: {model['perf']}").pack(anchor=tk.W, pady=2)
        
        # Download Progress
        prog_frame = ttk.Frame(info_frame)
        prog_frame.pack(fill=tk.X, pady=5)
        
        pb = ttk.Progressbar(prog_frame, mode='determinate', style="Horizontal.TProgressbar")
        self._progress_bars[model["id"]] = pb
        
        stat = ttk.Label(prog_frame, text="Installed" if model["installed"] else "Not Installed", font=("Segoe UI", 8))
        self._status_labels[model["id"]] = stat
        
        stat.pack(side=tk.RIGHT)
        pb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        if not model["installed"]:
            pb.set(0)
        else:
            pb.set(100)
            
        # Actions
        action_frame = ttk.Frame(card)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        btns = {}
        if model["installed"]:
            btns['activate'] = ttk.Button(action_frame, text="Activate", command=lambda m=model: self._activate(m))
            btns['activate'].pack(pady=2, fill=tk.X)
            btns['remove'] = ttk.Button(action_frame, text="Remove", command=lambda m=model: self._remove(m))
            btns['remove'].pack(pady=2, fill=tk.X)
            btns['repair'] = ttk.Button(action_frame, text="Repair", command=lambda m=model: self._repair(m))
            btns['repair'].pack(pady=2, fill=tk.X)
        else:
            btns['install'] = ttk.Button(action_frame, text="Install", command=lambda m=model: self._install(m))
            btns['install'].pack(pady=2, fill=tk.X)
            
        self._action_buttons[model["id"]] = btns

    # --- Actions ---
    
    def _activate(self, model):
        # Update config directly since we are on same machine
        from voiceflow.core.config import get_default_config_path
        messagebox.showinfo("Activate", f"{model['name']} activated! (Requires Backend Restart)")
        
    def _remove(self, model):
        if messagebox.askyesno("Confirm", f"Remove {model['name']}?"):
            model['installed'] = False
            self._render_model_list()
            
    def _repair(self, model):
        self._install(model)

    def _install(self, model):
        mid = model["id"]
        if mid in self._downloads and self._downloads[mid].status in ["downloading", "paused"]:
            return
            
        task = DownloadTask(mid)
        task.status = "downloading"
        self._downloads[mid] = task
        
        # Replace Install button with Pause/Cancel
        frame = self._action_buttons[mid]['install'].master
        for w in frame.winfo_children(): w.destroy()
        
        btn_pause = ttk.Button(frame, text="Pause", command=lambda: self._toggle_pause(mid))
        btn_pause.pack(pady=2, fill=tk.X)
        btn_cancel = ttk.Button(frame, text="Cancel", command=lambda: self._cancel(mid))
        btn_cancel.pack(pady=2, fill=tk.X)
        
        self._action_buttons[mid] = {'pause': btn_pause, 'cancel': btn_cancel}
        
        # Start async worker
        threading.Thread(target=self._download_worker, args=(model, task), daemon=True).start()

    def _toggle_pause(self, mid):
        task = self._downloads.get(mid)
        if not task: return
        
        if task.status == "downloading":
            task.status = "paused"
            task._pause_event.clear()
            self._action_buttons[mid]['pause'].config(text="Resume")
            self._status_labels[mid].config(text="Paused")
        elif task.status == "paused":
            task.status = "downloading"
            task._pause_event.set()
            self._action_buttons[mid]['pause'].config(text="Pause")
            self._status_labels[mid].config(text=f"Downloading... {int(task.progress)}%")

    def _cancel(self, mid):
        task = self._downloads.get(mid)
        if task:
            task.status = "error"
            task._cancel_event.set()
            task._pause_event.set() # Unblock if paused
            
        # Revert UI
        self._render_model_list()

    def _download_worker(self, model, task: DownloadTask):
        # Simulated async chunked download
        try:
            for i in range(100):
                if task._cancel_event.is_set():
                    return
                
                task._pause_event.wait() # Block if paused
                
                if task._cancel_event.is_set():
                    return
                    
                time.sleep(0.05) # Simulate chunk download time
                task.progress = float(i + 1)
                
                # Update UI thread-safely
                if self._root and self._root.winfo_exists():
                    self._root.after(0, self._update_progress_ui, task.model_id, task.progress)
                    
            # Complete
            if not task._cancel_event.is_set():
                task.status = "completed"
                model["installed"] = True
                if self._root and self._root.winfo_exists():
                    self._root.after(0, self._render_model_list)
                    
        except Exception as e:
            logger.error(f"Download error: {e}")
            if self._root:
                self._root.after(0, self._cancel, task.model_id)

    def _update_progress_ui(self, mid, progress):
        if mid in self._progress_bars:
            self._progress_bars[mid].set(progress)
        if mid in self._status_labels:
            self._status_labels[mid].config(text=f"Downloading... {int(progress)}%")
