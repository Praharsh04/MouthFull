"""
tray.py — System Tray
----------------------
EarTrumpet/PowerToys-style tray icon with a quick-access menu: current
status, start/stop toggle, quick actions, and links into the main window's
pages.

Backend integration
---------------------
Signals (UI -> backend):
    tray.start_stop_toggled(bool)      # True = start listening/service
    tray.open_dashboard_requested()
    tray.open_settings_requested()
    tray.quit_requested()
    tray.quick_action_triggered(str)   # e.g. "mute_mic", "push_to_talk"

Methods (backend -> UI):
    tray.update_status("listening" | "idle" | "processing" | "error" | "offline")
    tray.show_message(title, message, kind)   # native OS balloon/toast
"""
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from mouthfull.ui.theme import Colors

STATUS_TEXT = {
    "listening": "Listening…",
    "idle": "Idle",
    "processing": "Processing…",
    "error": "Error",
    "offline": "Backend Disconnected",
}

STATUS_COLOR = {
    "listening": Colors.ORB_LISTENING,
    "idle": Colors.ORB_IDLE,
    "processing": Colors.ORB_PROCESSING,
    "error": Colors.ORB_ERROR,
    "offline": Colors.TEXT_MUTED,
}


def _make_dot_icon(color_hex: str, size: int = 64) -> QIcon:
    """Generates a simple colored-circle tray icon (placeholder for a real .ico asset)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(0, 0, 0, 0))
    painter.setBrush(QColor(color_hex))
    margin = size * 0.12
    painter.drawEllipse(int(margin), int(margin), int(size - 2 * margin), int(size - 2 * margin))
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    start_stop_toggled = Signal(bool)
    open_dashboard_requested = Signal()
    open_settings_requested = Signal()
    quit_requested = Signal()
    quick_action_triggered = Signal(str)

    def __init__(self, app):
        super().__init__()
        self._app = app
        self._is_running = False
        self._status = "idle"

        self.icon = QSystemTrayIcon()
        self.icon.setIcon(_make_dot_icon(STATUS_COLOR["idle"]))
        self.icon.setToolTip("MouthFull AI — Idle")

        self.menu = QMenu()
        self._build_menu()
        self.icon.setContextMenu(self.menu)

        self.icon.activated.connect(self._on_activated)

    def _build_menu(self):
        self.status_action = QAction("● Idle")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()

        self.toggle_action = QAction("Start Listening")
        self.toggle_action.triggered.connect(self._on_toggle)
        self.menu.addAction(self.toggle_action)

        self.stop_processing_action = QAction("⏹ Stop Processing")
        self.stop_processing_action.triggered.connect(lambda: self.quick_action_triggered.emit("cancel_task"))
        self.stop_processing_action.setEnabled(False)
        self.menu.addAction(self.stop_processing_action)

        mute_action = QAction("Mute Microphone")
        mute_action.setCheckable(True)
        mute_action.triggered.connect(lambda checked: self.quick_action_triggered.emit("mute_mic"))
        self.menu.addAction(mute_action)
        self.mute_action = mute_action

        quit_action = QAction("Exit Application")
        quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(quit_action)

        self.menu.addSeparator()

        dash_action = QAction("Open Dashboard")
        dash_action.triggered.connect(self.open_dashboard_requested.emit)
        self.menu.addAction(dash_action)

        settings_action = QAction("Settings")
        settings_action.triggered.connect(self.open_settings_requested.emit)
        self.menu.addAction(settings_action)

    def _on_toggle(self):
        self._is_running = not self._is_running
        self.toggle_action.setText("Stop Listening" if self._is_running else "Start Listening")
        self.start_stop_toggled.emit(self._is_running)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_dashboard_requested.emit()

    # ---------------------------------------------------------------- backend API
    def update_status(self, status: str):
        """Backend -> UI: listening | idle | processing | error | offline"""
        if status not in STATUS_TEXT:
            status = "idle"
        self._status = status
        self.icon.setIcon(_make_dot_icon(STATUS_COLOR[status]))
        self.icon.setToolTip(f"MouthFull AI — {STATUS_TEXT[status]}")
        self.status_action.setText(f"● {STATUS_TEXT[status]}")
        self.stop_processing_action.setEnabled(status == "processing")

    def set_running_silent(self, running: bool):
        """Reflect backend-driven start/stop state without re-emitting toggle signal."""
        self._is_running = running
        self.toggle_action.setText("Stop Listening" if running else "Start Listening")

    def show_message(self, title: str, message: str, kind: str = "info"):
        icon_map = {
            "info": QSystemTrayIcon.MessageIcon.Information,
            "warning": QSystemTrayIcon.MessageIcon.Warning,
            "error": QSystemTrayIcon.MessageIcon.Critical,
            "success": QSystemTrayIcon.MessageIcon.Information,
        }
        self.icon.showMessage(title, message, icon_map.get(kind, QSystemTrayIcon.MessageIcon.Information), 4000)

    def show(self):
        self.icon.show()
