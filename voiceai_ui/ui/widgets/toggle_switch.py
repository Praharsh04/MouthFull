"""
ToggleSwitch
------------
A Fluent/iOS-style animated on/off switch.

Backend integration:
    switch.toggled.connect(your_handler)   # bool
    switch.setChecked(True/False)          # to reflect external state changes
"""
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal, QSize
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QAbstractButton, QSizePolicy

from ui.theme import Colors


class ToggleSwitch(QAbstractButton):
    toggled_signal = Signal(bool)  # alias-friendly explicit signal (toggled() also emitted natively)

    def __init__(self, parent=None, checked: bool = False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self._pos = 1.0 if checked else 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._animate)
        self.toggled.connect(self.toggled_signal.emit)

    def sizeHint(self):
        return QSize(42, 24)

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def getPos(self):
        return self._pos

    def setPos(self, value):
        self._pos = value
        self.update()

    pos = Property(float, getPos, setPos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        track_off = QColor(Colors.BORDER)
        track_on = QColor(Colors.ACCENT)

        r = track_off.red() + (track_on.red() - track_off.red()) * self._pos
        g = track_off.green() + (track_on.green() - track_off.green()) * self._pos
        b = track_off.blue() + (track_on.blue() - track_off.blue()) * self._pos
        track_color = QColor(int(r), int(g), int(b))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)

        knob_d = h - 4
        x = 2 + (w - knob_d - 4) * self._pos
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(int(x), 2, knob_d, knob_d)

    # Explicit backend-facing API -------------------------------------------------
    def set_checked_silent(self, checked: bool):
        """Set state without emitting toggled() — useful when backend pushes state."""
        self.blockSignals(True)
        self.setChecked(checked)
        self._pos = 1.0 if checked else 0.0
        self.blockSignals(False)
        self.update()
