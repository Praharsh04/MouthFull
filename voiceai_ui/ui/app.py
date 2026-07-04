"""
app.py — Application Shell
------------------------------
Wires together the Nav Rail, all pages (Dashboard, Models, LLMs, Performance,
Logs, Settings), the System Tray, the Floating AI Orb, the Notification
Center, and Toasts into one cohesive main window.

This file intentionally contains ZERO backend logic. Every place a real
backend would plug in is marked with a `# BACKEND HOOK` comment. A backend
integrator should:
    1. Instantiate `MainWindow`.
    2. Connect to the many `on_*` / `*_clicked` / `*_changed` Signals exposed
       by `window.dashboard`, `window.models_page`, `window.llms_page`,
       `window.performance_page`, `window.logs_page`, `window.settings_page`,
       `window.tray`, `window.orb`, and `window.notification_center`.
    3. Call the corresponding `update_*` / `set_*` methods on those same
       objects whenever backend state changes, to reflect it in the UI.

Run directly (`python main.py`) to preview the fully-wired UI with dummy data
and a demo timer that simulates backend activity so every element looks alive.
"""
import sys

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame
)

from ui.theme import APP_QSS, Colors
from ui.widgets import NavRail, ToastManager
from ui.dashboard import DashboardPage
from ui.models import ModelsPage
from ui.llms import LLMProvidersPage
from ui.performance import PerformancePage
from ui.logs import LogsPage
from ui.settings import SettingsPage
from ui.tray import TrayIcon
from ui.overlay import AIOrb
from ui.notifications import NotificationCenter
from ui.wizard import SetupWizard


class TopBar(QFrame):
    """Slim header above the page stack: page title context + bell icon."""

    def __init__(self, on_bell_clicked, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(f"background-color: {Colors.BG_APP}; border-bottom: 1px solid {Colors.BORDER_SOFT};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 16, 0)

        layout.addStretch(1)

        self.bell_btn = QPushButton("🔔")
        self.bell_btn.setProperty("variant", "ghost")
        self.bell_btn.setFixedSize(34, 34)
        self.bell_btn.clicked.connect(on_bell_clicked)
        layout.addWidget(self.bell_btn)

        self.badge = QLabel("3")
        self.badge.setFixedSize(16, 16)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(f"""
            background-color: {Colors.ERROR}; color: white; border-radius: 8px;
            font-size: 9px; font-weight: 700;
        """)
        self.badge.setParent(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.badge.move(self.bell_btn.x() + 22, 6)

    def set_unread_count(self, n: int):
        self.badge.setVisible(n > 0)
        self.badge.setText(str(n) if n < 100 else "99+")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoiceFlow AI")
        self.resize(1180, 760)
        self.setMinimumSize(980, 620)
        self.setStyleSheet(APP_QSS)

        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------- Nav rail ----------------
        self.nav = NavRail()
        root_layout.addWidget(self.nav)

        # ---------------- Main content column ----------------
        content_col = QVBoxLayout()
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(0)

        self.topbar = TopBar(on_bell_clicked=self._toggle_notification_center)
        content_col.addWidget(self.topbar)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage()
        self.models_page = ModelsPage()
        self.llms_page = LLMProvidersPage()
        self.performance_page = PerformancePage()
        self.logs_page = LogsPage()
        self.settings_page = SettingsPage()

        self._pages = {
            "dashboard": self.dashboard,
            "models": self.models_page,
            "llms": self.llms_page,
            "performance": self.performance_page,
            "logs": self.logs_page,
            "settings": self.settings_page,
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        body_row.addWidget(self.stack, 1)

        # ---------------- Notification center (slide-out) ----------------
        self.notification_center = NotificationCenter()
        self.notification_center.setMaximumWidth(0)  # collapsed by default
        self._notif_open = False
        body_row.addWidget(self.notification_center)

        content_col.addLayout(body_row, 1)
        root_layout.addLayout(content_col, 1)

        # ---------------- Cross-cutting UI: toasts, orb, tray ----------------
        self.toast_manager = ToastManager(root)

        self.orb = AIOrb()
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.orb.snap_to_corner(screen.availableGeometry())

        self.tray = TrayIcon(QApplication.instance())

        self._wire_navigation()
        self._wire_tray()
        self._wire_orb()
        self._wire_cross_page_feedback()

        self.notification_center.on_notification_dismissed.connect(
            lambda nid: self.topbar.set_unread_count(max(0, int(self.topbar.badge.text() or 0) - 1))
        )

    # ---------------------------------------------------------------- wiring (UI <-> UI only)
    def _wire_navigation(self):
        self.nav.page_changed.connect(self._show_page)

    def _show_page(self, page_id: str):
        widget = self._pages.get(page_id)
        if widget:
            self.stack.setCurrentWidget(widget)
            self.nav.set_active(page_id)

    def _toggle_notification_center(self):
        self._notif_open = not self._notif_open
        target_width = 320 if self._notif_open else 0
        self.notification_center.setMaximumWidth(target_width)

    def _wire_tray(self):
        self.tray.open_dashboard_requested.connect(self._restore_from_tray)
        self.tray.open_settings_requested.connect(lambda: (self._restore_from_tray(), self._show_page("settings"), self.nav.set_active("settings")))
        self.tray.quit_requested.connect(QApplication.instance().quit)
        self.tray.show()

        # Keep tray + dashboard start/stop in sync at the UI level (demo only;
        # a real backend is the actual source of truth for "is running").
        self.tray.start_stop_toggled.connect(self._on_tray_toggle_demo)
        self.dashboard.on_start_clicked.connect(lambda: self.tray.set_running_silent(True))
        self.dashboard.on_stop_clicked.connect(lambda: self.tray.set_running_silent(False))

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_toggle_demo(self, running: bool):
        self.dashboard.set_running_silent(running)
        self.orb.set_state("listening" if running else "idle")
        self.tray.update_status("listening" if running else "idle")

    def _wire_orb(self):
        self.orb.clicked_signal.connect(self._on_orb_clicked_demo)
        self.orb.double_clicked_signal.connect(self._restore_from_tray)
        self.orb.set_visible(True)

    def _on_orb_clicked_demo(self):
        # BACKEND HOOK: replace this demo state-cycling with a call into the
        # backend's start/stop recording function; the backend should then
        # drive orb.set_state(...) based on real pipeline events.
        cycle = {"idle": "listening", "listening": "idle"}
        next_state = cycle.get(self.orb._state, "idle")
        self.orb.set_state(next_state)
        self.tray.update_status(next_state)
        self.dashboard.update_status(next_state)

    def _wire_cross_page_feedback(self):
        """Purely cosmetic cross-page wiring so the demo build feels alive
        (e.g. installing a model shows a toast). A real backend would trigger
        these same UI calls from its own event bus instead."""
        self.models_page.on_model_install_clicked.connect(self._demo_install_model)
        self.llms_page.on_test_connection_clicked.connect(self._demo_test_provider)

    def _demo_install_model(self, model_id: str):
        self.models_page.set_model_status(model_id, "downloading")
        self.toast_manager.notify("Download started", f"Installing {model_id}…", "info")

        progress = {"value": 0}
        timer = QTimer(self)

        def step():
            progress["value"] += 12
            self.models_page.update_download_progress(model_id, min(100, progress["value"]))
            if progress["value"] >= 100:
                timer.stop()
                self.models_page.set_model_status(model_id, "installed")
                self.toast_manager.notify("Download complete", f"{model_id} is ready to use.", "success")

        timer.timeout.connect(step)
        timer.start(280)

    def _demo_test_provider(self, provider_id: str):
        self.llms_page.set_connection_status(provider_id, "testing")
        QTimer.singleShot(900, lambda: (
            self.llms_page.set_connection_status(provider_id, "success"),
            self.toast_manager.notify("Connection successful", f"{provider_id} responded OK.", "success")
        ))

    def closeEvent(self, event):
        # BACKEND HOOK: a real backend may want to intercept this to keep
        # running in the background (minimize-to-tray) rather than quitting.
        event.ignore()
        self.hide()
        self.tray.show_message("Still running", "VoiceFlow AI is running in the background.", "info")


def run_setup_wizard_if_needed(app, main_window):
    """Demo helper: shows the setup wizard once at first launch. A backend
    would gate this on a real 'has the user completed setup' flag."""
    wizard = SetupWizard()

    def on_finished(result):
        main_window.show()

    wizard.finished.connect(on_finished)
    wizard.skipped_signal.connect(main_window.show)
    wizard.show()
    return wizard


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(APP_QSS)

    window = MainWindow()
    wizard = run_setup_wizard_if_needed(app, window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
