"""Floating AI Orb overlay.

Replaces the old status bar with a modern, fluid, draggable AI orb.
"""

import tkinter as tk
import time
import math
import asyncio
from typing import TYPE_CHECKING
from PIL import Image, ImageTk

from voiceflow.core.events import AudioLevelChanged, StatusChanged, TranscriptReady, PipelineError
from voiceflow.core.logger import logger
from voiceflow.utils.window import get_active_window_info

if TYPE_CHECKING:
    from voiceflow.core.config import UIConfig
    from voiceflow.core.events import EventBus

# Colors for states
STATE_COLORS = {
    "idle": "#4A90E2",         # Soft blue
    "listening": "#00E5FF",    # Bright cyan
    "processing": "#B066FE",   # Purple
    "refining": "#F5A623",     # Gold/Orange
    "ready": "#2ECC71",        # Green
    "error": "#E74C3C"         # Red
}

class FloatingOverlay:
    def __init__(self, config: 'UIConfig', event_bus: 'EventBus') -> None:
        self._config = config
        self._bus = event_bus
        self._root: tk.Toplevel | None = None
        
        self._state = "idle"
        self._status_text = ""
        self._audio_level = 0.0
        self._target_audio_level = 0.0
        self._anim_phase = 0.0
        self._is_visible = False
        
        self._app_icon_img = None
        self._app_icon_photo = None
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    async def start(self) -> None:
        """Start the overlay loop in a thread."""
        if not self._config.show_orb:
            return

        import threading
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()

        # Wait for initialization
        await asyncio.sleep(0.5)

        self._bus.subscribe(StatusChanged, self._on_status_changed)
        self._bus.subscribe(AudioLevelChanged, self._on_audio_level)
        self._bus.subscribe(TranscriptReady, self._on_transcript)
        logger.info("Floating Orb started.")

    async def stop(self) -> None:
        if not self._config.show_orb:
            return
        self._bus.unsubscribe(StatusChanged, self._on_status_changed)
        self._bus.unsubscribe(AudioLevelChanged, self._on_audio_level)
        self._bus.unsubscribe(TranscriptReady, self._on_transcript)
        if self._root:
            self._root.quit()

    def _run_tk(self) -> None:
        # Tkinter requires a root window
        import tkinter as tk
        from tkinter import font
        
        try:
            main_root = tk.Tk()
            main_root.withdraw()
        except tk.TclError:
            return

        self._root = tk.Toplevel(main_root)
        self._root.overrideredirect(True)
        if self._config.always_on_top:
            self._root.attributes('-topmost', True)

        # Transparency setup
        self._bg_color = "#010101" # Chroma key
        self._root.configure(bg=self._bg_color)
        self._root.attributes('-transparentcolor', self._bg_color)
        self._root.attributes('-alpha', 0.0) # start invisible
        
        size = self._config.orb_size
        canvas_size = size + 60 # Extra space for icon and text
        self._root.geometry(f"{canvas_size}x{canvas_size}")
        
        self._canvas = tk.Canvas(self._root, width=canvas_size, height=canvas_size, 
                                 bg=self._bg_color, highlightthickness=0)
        self._canvas.pack()

        # Orb Oval
        center = canvas_size // 2
        self._r_base = size // 2
        self._orb_id = self._canvas.create_oval(
            center - self._r_base, center - self._r_base - 10,
            center + self._r_base, center + self._r_base - 10,
            fill=STATE_COLORS["idle"], outline=""
        )

        # Status text
        self._font = font.Font(family="Segoe UI", size=9, weight="bold")
        self._text_id = self._canvas.create_text(
            center, center + self._r_base + 8,
            text="", fill="white", font=self._font
        )
        
        # App Icon
        self._icon_id = self._canvas.create_image(
            center, center + self._r_base + 25,
            image=None
        )

        # Draggable
        self._root.bind("<ButtonPress-1>", self._start_drag)
        self._root.bind("<B1-Motion>", self._do_drag)

        # Position near cursor initially
        self._place_near_cursor()

        # Animation loop
        self._update_app_icon()
        self._animate_loop()
        
        main_root.mainloop()

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _do_drag(self, event):
        x = self._root.winfo_x() - self._drag_start_x + event.x
        y = self._root.winfo_y() - self._drag_start_y + event.y
        self._root.geometry(f"+{x}+{y}")

    def _place_near_cursor(self):
        try:
            import win32gui
            x, y = win32gui.GetCursorPos()
            # Offset a bit to the bottom right
            offset = 20
            self._root.geometry(f"+{x + offset}+{y + offset}")
        except:
            pass

    def _update_app_icon(self):
        """Fetch active app icon every 1 second."""
        if self._config.show_app_icon and self._is_visible:
            # Running this natively in Tk thread might cause slight stutter, but it's fast enough.
            name, img = get_active_window_info()
            if img:
                img = img.resize((16, 16), Image.Resampling.LANCZOS)
                self._app_icon_photo = ImageTk.PhotoImage(img)
                self._canvas.itemconfig(self._icon_id, image=self._app_icon_photo)
            else:
                self._canvas.itemconfig(self._icon_id, image="")
        
        if self._root:
            self._root.after(1000, self._update_app_icon)

    def _animate_loop(self):
        """60 FPS animation loop."""
        if not self._root:
            return

        # Smooth volume
        self._audio_level += (self._target_audio_level - self._audio_level) * 0.2

        # Breathing / Pulse animation
        self._anim_phase += 0.1
        pulse = math.sin(self._anim_phase)
        
        size = self._config.orb_size
        canvas_size = size + 60
        center = canvas_size // 2
        
        # Calculate radius based on state
        r = self._r_base
        if self._state == "listening" and self._config.voice_animations:
            r = self._r_base + (self._audio_level * self._config.animation_intensity * 20)
        elif self._state in ["processing", "refining"]:
            r = self._r_base + (pulse * 3 * self._config.animation_intensity)
            
        # Draw new orb coordinates
        self._canvas.coords(
            self._orb_id,
            center - r, center - r - 10,
            center + r, center + r - 10
        )
        
        # Update Color
        target_color = STATE_COLORS.get(self._state, STATE_COLORS["idle"])
        self._canvas.itemconfig(self._orb_id, fill=target_color)
        
        # Update Text
        self._canvas.itemconfig(self._text_id, text=self._status_text)
        
        # Fade in / out
        current_alpha = self._root.attributes('-alpha')
        target_alpha = self._config.orb_transparency if self._is_visible else 0.0
        
        if abs(current_alpha - target_alpha) > 0.01:
            new_alpha = current_alpha + (target_alpha - current_alpha) * 0.15
            self._root.attributes('-alpha', new_alpha)
            
        self._root.after(16, self._animate_loop) # ~60 FPS

    # ---------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------

    async def _on_status_changed(self, event: StatusChanged) -> None:
        if not self._root:
            return
            
        if event.status == "recording":
            self._state = "listening"
            self._status_text = "Listening..."
            self._is_visible = True
            self._root.after(0, self._place_near_cursor)
        elif event.status == "processing":
            self._state = "processing"
            self._status_text = "Transcribing..."
        elif event.status == "refining":
            self._state = "refining"
            self._status_text = "Refining..."
        elif event.status == "error":
            self._state = "error"
            self._status_text = "Error"
            # Hide after 2 seconds
            self._root.after(2000, lambda: setattr(self, '_is_visible', False))
        elif event.status == "idle":
            self._state = "idle"
            self._status_text = ""
            self._is_visible = False

    async def _on_audio_level(self, event: AudioLevelChanged) -> None:
        # Range is roughly 0.0 to 1.0
        self._target_audio_level = event.level

    async def _on_transcript(self, event: TranscriptReady) -> None:
        self._state = "ready"
        self._status_text = "Ready!"
        # Will be hidden by injector setting idle, or we hide it here
        self._root.after(1000, lambda: setattr(self, '_is_visible', False))
