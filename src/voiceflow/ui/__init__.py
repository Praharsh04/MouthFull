"""User interface components (tray icon, overlays, notifications)."""

from .tray import SystemTray
from .overlay import FloatingOverlay

__all__ = ["SystemTray", "FloatingOverlay"]
