"""
StatusBadge / StatusDot
------------------------
Small pill/dot indicators used across Dashboard, Models, LLMs, Logs pages
to show state such as: online/offline, installed/downloading/error, etc.

Backend integration:
    badge.set_status("success", "Connected")
    dot.set_state("active")   # active | idle | error | disabled
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout

from voiceflow.ui.theme import Colors

STATUS_COLORS = {
    "success": Colors.SUCCESS,
    "warning": Colors.WARNING,
    "error": Colors.ERROR,
    "info": Colors.INFO,
    "neutral": Colors.TEXT_MUTED,
}


class StatusDot(QWidget):
    """A small colored circle, optionally pulsing state conveyed by color only
    (animation handled by AnimatedDot subclass if needed)."""

    def __init__(self, state: str = "neutral", size: int = 9, parent=None):
        super().__init__(parent)
        self._state = state
        self._size = size
        self.setFixedSize(size, size)

    def set_state(self, state: str):
        self._state = state if state in STATUS_COLORS else "neutral"
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(STATUS_COLORS.get(self._state, Colors.TEXT_MUTED)))
        p.drawEllipse(0, 0, self._size, self._size)


class StatusBadge(QWidget):
    """Pill-shaped badge: dot + label, e.g. '● Connected'."""

    def __init__(self, text: str = "", status: str = "neutral", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 3, 12, 3)
        layout.setSpacing(6)

        self._dot = StatusDot(status, 8)
        self._label = QLabel(text)
        self._label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")

        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        self._status = status
        self._apply_bg()

    def _apply_bg(self):
        color = STATUS_COLORS.get(self._status, Colors.TEXT_MUTED)
        self.setStyleSheet(
            f"StatusBadge {{ background-color: {color}1c; border: 1px solid {color}55; border-radius: 10px; }}"
        )

    def set_status(self, status: str, text: str = None):
        self._status = status if status in STATUS_COLORS else "neutral"
        self._dot.set_state(self._status)
        if text is not None:
            self._label.setText(text)
        self._apply_bg()

    def sizeHint(self):
        return QSize(self._label.sizeHint().width() + 34, 22)
