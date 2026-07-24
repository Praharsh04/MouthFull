"""
NavRail
-------
Left-hand navigation rail for the main application window (Docker Desktop /
PowerToys style). Purely presentational + signal emission; the app.py file
owns the QStackedWidget page switching.

Backend integration:
    nav.page_changed.connect(your_handler)  # str: page id
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QButtonGroup, QSizePolicy

from mouthfull.ui.theme import Colors, Metrics


from PySide6.QtGui import QIcon
import os

NAV_ITEMS = [
    ("dashboard", "home.svg", "Dashboard"),
    ("models", "mic.svg", "Speech Models"),
    ("prompt", "file-text.svg", "Prompt Processor"),
    ("performance", "bar-chart.svg", "Performance"),
    ("logs", "scroll.svg", "Logs"),
    ("settings", "settings.svg", "Settings"),
]


class NavButton(QPushButton):
    def __init__(self, icon_name: str, label: str, page_id: str):
        super().__init__(f"  {label}")
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons", icon_name)
        self.setIcon(QIcon(icon_path))
        self.page_id = page_id
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(42)
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                border: none;
                border-radius: {Metrics.RADIUS_MD}px;
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                padding-left: 14px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {Colors.BG_CARD_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background: {Colors.ACCENT_SOFT};
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                border-left: 3px solid {Colors.ACCENT};
            }}
        """)


class NavRail(QWidget):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(Metrics.NAV_WIDTH)
        self.setStyleSheet(f"background-color: {Colors.BG_SURFACE}; border-right: 1px solid {Colors.BORDER_SOFT};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 16)
        layout.setSpacing(4)

        import os
        img_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons", "message-circle.svg").replace("\\", "/")
        brand = QLabel(f"<img src='{img_path}' width='16' height='16'>  MouthFull AI")
        brand.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY}; padding: 6px 8px 18px 8px;")
        layout.addWidget(brand)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons = {}

        for page_id, icon, label in NAV_ITEMS:
            btn = NavButton(icon, label, page_id)
            self._group.addButton(btn)
            btn.clicked.connect(lambda checked, pid=page_id: self.page_changed.emit(pid))
            layout.addWidget(btn)
            self.buttons[page_id] = btn

        layout.addStretch(1)

        version = QLabel("v1.4.0 · Backend: Disconnected")
        version.setObjectName("VersionLabel")
        version.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; padding: 6px 8px;")
        self.version_label = version
        layout.addWidget(version)

        self.buttons["dashboard"].setChecked(True)

    def set_active(self, page_id: str):
        if page_id in self.buttons:
            self.buttons[page_id].setChecked(True)

    def set_backend_status_text(self, text: str):
        """e.g. nav.set_backend_status_text('Backend: Connected')"""
        self.version_label.setText(f"v1.4.0 · {text}")
