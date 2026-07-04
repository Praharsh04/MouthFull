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
        self._settings_win = None

    def _create_menu(self) -> pystray.Menu:
        """Create the context menu."""
        from pystray import MenuItem
        return pystray.Menu(
            MenuItem("Open Dashboard", self._on_dashboard_clicked, default=True),
            MenuItem("Settings", self._on_settings_clicked),
            MenuItem("Restart Backend", self._on_restart_clicked),
            MenuItem("View Logs", self._on_logs_clicked),
            MenuItem("Exit", self._on_quit_clicked)
        )

    def _on_dashboard_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle Dashboard click."""
        from voiceflow.ui.dashboard import DashboardWindow
        if not hasattr(self, '_dashboard_win') or not self._dashboard_win:
            self._dashboard_win = DashboardWindow(self._config, self._bus)
        self._dashboard_win.show()

    def _on_settings_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle Settings click."""
        from voiceflow.ui.settings import SettingsWindow
        if not self._settings_win:
            self._settings_win = SettingsWindow(self._config)
        self._settings_win.show()

    def _on_restart_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle Restart Backend click."""
        logger.info("Restarting backend...")
        # Since components listen to config changes, we might emit a restart event
        # For now, log it. Full restart logic will be implemented.
        pass

    def _on_logs_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Handle View Logs click."""
        import os
        log_path = "logs/voiceflow.log"
        if os.path.exists(log_path):
            os.startfile(log_path)
            
    def _on_quit_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Quit the application."""
        logger.info("Quit selected from tray.")
        icon.stop()
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)

    def _create_image(self, color: str) -> Image.Image:
        """Create a simple circle icon of a given color."""
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill=color)
        return image

    def _run_tray(self) -> None:
        self._icon = pystray.Icon(
            "voiceflow",
            self._create_image("gray"),
            "VoiceFlow Local",
            menu=self._create_menu()
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
