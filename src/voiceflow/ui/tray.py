"""System tray icon and menu using pystray.

Responsibilities:
- Display a tray icon with state-based colours (idle, recording, processing, error).
- Provide a context menu with common actions.
- Show Windows toast notifications for status changes.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item

from voiceflow.core.events import NotificationEvent, StatusChanged
from voiceflow.core.logger import logger
from voiceflow.ui.settings import SettingsWindow

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig
    from voiceflow.core.events import EventBus


class SystemTray:
    """System tray icon manager."""

    def __init__(self, config: AppConfig, event_bus: EventBus) -> None:
        self._config = config
        self._bus = event_bus
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None
        self._loop = asyncio.get_running_loop()

    def _create_image(self, color: str) -> Image.Image:
        """Create a simple circle icon of a given color."""
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill=color)
        return image

    def _on_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Open the settings window (blocks the tray thread temporarily, which is OK for this simple app)."""
        logger.info("Opening Settings window...")
        window = SettingsWindow(self._config)
        window.show()

    def _on_about(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Show the About dialog."""
        import tkinter as tk
        from tkinter import messagebox

        from voiceflow import __version__

        root = tk.Tk()
        root.withdraw()
        msg = f"VoiceFlow Local v{__version__}\n\n"
        msg += f"Global Hotkey: {self._config.hotkey.combination.upper()} ({self._config.hotkey.mode})\n"
        msg += f"Text Injection: {self._config.injection.method}\n\n"
        msg += "A private, completely local AI dictation assistant."
        messagebox.showinfo("About VoiceFlow Local", msg, master=root)
        root.destroy()

    def _on_quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Quit the application."""
        logger.info("Quit selected from tray.")
        icon.stop()
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)

    def _run_tray(self) -> None:
        menu = pystray.Menu(
            item("Settings...", self._on_settings),
            item("About...", self._on_about),
            item("Quit", self._on_quit),
        )
        self._icon = pystray.Icon(
            "voiceflow",
            self._create_image("gray"),
            "VoiceFlow Local",
            menu=menu
        )
        self._icon.run()

    async def start(self) -> None:
        """Create the tray icon and start listening for events."""
        if not self._config.ui.show_tray:
            return

        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

        # Wait a moment for icon to initialize
        await asyncio.sleep(0.2)

        self._bus.subscribe(StatusChanged, self._on_status_changed)
        self._bus.subscribe(NotificationEvent, self._on_notification)
        logger.info("SystemTray started.")

    async def stop(self) -> None:
        """Remove the tray icon."""
        self._bus.unsubscribe(StatusChanged, self._on_status_changed)
        self._bus.unsubscribe(NotificationEvent, self._on_notification)
        if self._icon is not None:
            self._icon.stop()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        logger.info("SystemTray stopped.")

    async def _on_status_changed(self, event: StatusChanged) -> None:
        """Update tray icon color based on status."""
        if self._icon is None:
            return

        color_map = {
            "idle": "gray",
            "recording": "red",
            "processing": "blue",
            "refining": "blue",
            "done": "green",
            "error": "orange",
        }
        color = color_map.get(event.status, "gray")
        self._icon.icon = self._create_image(color)

    async def _on_notification(self, event: NotificationEvent) -> None:
        """Show an OS toast notification."""
        if self._icon is not None and getattr(self._icon, "HAS_NOTIFICATION", True) and self._config.ui.show_notifications:
            try:
                self._icon.notify(event.message, event.title)
            except Exception as e:
                logger.warning(f"Failed to show notification: {e}")
