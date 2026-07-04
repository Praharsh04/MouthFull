"""Floating overlay UI using Tkinter.

Responsibilities:
- Display a small, borderless, always-on-top window.
- Show current state (Listening, Processing, Refining, Done, Error).
- Show microphone volume indicator.
- Animate processing state.
"""

from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
import time

from voiceflow.core.events import StatusChanged, AudioLevelChanged
from voiceflow.core.logger import logger

if TYPE_CHECKING:
    from voiceflow.core.config import UIConfig
    from voiceflow.core.events import EventBus


class FloatingOverlay:
    """A small borderless floating window to show current status."""

    def __init__(self, config: UIConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._root: tk.Tk | None = None
        self._label: tk.Label | None = None
        self._progress: ttk.Progressbar | None = None
        self._thread: threading.Thread | None = None
        self._loop = asyncio.get_running_loop()
        self._ready_event = threading.Event()
        
        self._current_status = "idle"
        self._anim_dots = 0
        self._anim_running = False

    def _run_tk(self) -> None:
        """Run the Tkinter mainloop in a separate thread."""
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.85)
        
        width = 220
        height = 55
        x = (self._root.winfo_screenwidth() // 2) - (width // 2)
        y = self._root.winfo_screenheight() - height - 100
        self._root.geometry(f"{width}x{height}+{x}+{y}")
        
        self._root.configure(bg="#2d2d2d")
        
        # UI Elements
        frame = tk.Frame(self._root, bg="#2d2d2d")
        frame.pack(expand=True, fill="both", padx=10, pady=5)
        
        self._label = tk.Label(frame, text="Ready", fg="white", bg="#2d2d2d", font=("Segoe UI", 12, "bold"))
        self._label.pack(side=tk.TOP, fill="x")
        
        # Audio level / progress bar
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("green.Horizontal.TProgressbar", foreground="green", background="#4dff4d")
        
        self._progress = ttk.Progressbar(frame, style="green.Horizontal.TProgressbar", orient="horizontal", length=200, mode="determinate")
        self._progress.pack(side=tk.BOTTOM, fill="x", pady=(2, 0))
        
        self._root.withdraw()
        self._ready_event.set()
        self._root.mainloop()

    async def start(self) -> None:
        """Start the overlay thread and subscribe to events."""
        if not self._config.show_notifications:
            return

        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        await asyncio.to_thread(self._ready_event.wait)
        
        self._bus.subscribe(StatusChanged, self._on_status_changed)
        self._bus.subscribe(AudioLevelChanged, self._on_audio_level)
        logger.info("Floating overlay started.")

    async def stop(self) -> None:
        """Stop the overlay."""
        self._bus.unsubscribe(StatusChanged, self._on_status_changed)
        self._bus.unsubscribe(AudioLevelChanged, self._on_audio_level)
        if self._root is not None:
            self._root.after(0, self._root.destroy)
            self._thread.join(timeout=1.0)
            self._root = None
            self._thread = None
        logger.info("Floating overlay stopped.")

    def _animate(self) -> None:
        if not self._anim_running or self._root is None or self._label is None:
            return
            
        base_text = "Processing" if self._current_status == "processing" else "Refining"
        if self._current_status in ["processing", "refining"]:
            dots = "." * (self._anim_dots % 4)
            self._label.config(text=f"{base_text}{dots}")
            self._anim_dots += 1
            self._progress.configure(mode="indeterminate")
            self._progress.start(10)
            self._root.after(400, self._animate)
        else:
            self._progress.stop()
            self._progress.configure(mode="determinate", value=0)

    async def _on_status_changed(self, event: StatusChanged) -> None:
        if self._root is None or self._label is None:
            return
            
        def update_ui() -> None:
            self._current_status = event.status
            if event.status == "idle":
                self._root.withdraw()
                self._anim_running = False
                self._progress.stop()
                self._progress.configure(mode="determinate", value=0)
            else:
                self._root.deiconify()
                self._label.config(text=event.message)
                
                # Colors
                if event.status == "recording":
                    self._label.config(fg="#ff4d4d")
                    self._anim_running = False
                    self._progress.stop()
                    self._progress.configure(mode="determinate")
                elif event.status in ["processing", "refining"]:
                    self._label.config(fg="#4da6ff")
                    if not self._anim_running:
                        self._anim_running = True
                        self._animate()
                elif event.status == "done":
                    self._label.config(fg="#4dff4d")
                    self._anim_running = False
                    self._progress.stop()
                    self._progress.configure(value=100, mode="determinate")
                elif event.status == "error":
                    self._label.config(fg="#ffcc00")
                    self._anim_running = False
                    self._progress.stop()
                    self._progress.configure(value=0, mode="determinate")
                else:
                    self._label.config(fg="white")
                    
        self._root.after(0, update_ui)

    async def _on_audio_level(self, event: AudioLevelChanged) -> None:
        """Update the audio level meter during recording."""
        if self._root is None or self._progress is None or self._current_status != "recording":
            return
            
        def update_meter():
            if self._current_status == "recording":
                # event.level is 0.0 to 1.0
                self._progress.configure(value=event.level * 100)
                
        self._root.after(0, update_meter)
