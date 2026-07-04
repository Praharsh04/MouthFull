"""
AudioLevelMeter
---------------
A horizontal bar-style VU meter (EarTrumpet-inspired) showing microphone
input level as a sequence of segments that light up.

Backend integration:
    meter.update_audio_level(level)   # level: float 0.0 - 1.0, call this ~20-30x/sec
    meter.set_active(True/False)      # dims the meter when mic isn't recording
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget, QSizePolicy

from voiceflow.ui.theme import Colors


class AudioLevelMeter(QWidget):
    SEGMENTS = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._display_level = 0.0
        self._active = False
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Smooth decay so the meter doesn't jump around jarringly.
        self._decay_timer = QTimer(self)
        self._decay_timer.timeout.connect(self._smooth_step)
        self._decay_timer.start(33)

    # ---- Backend-facing API -----------------------------------------------
    def update_audio_level(self, level: float):
        """Push a new RMS/peak level from the backend (0.0 - 1.0)."""
        self._level = max(0.0, min(1.0, level))

    def set_active(self, active: bool):
        self._active = active
        if not active:
            self._level = 0.0
        self.update()

    # ---- internal -----------------------------------------------------------
    def _smooth_step(self):
        target = self._level
        if self._display_level < target:
            self._display_level += (target - self._display_level) * 0.5
        else:
            self._display_level += (target - self._display_level) * 0.25
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        gap = 3
        seg_w = (w - gap * (self.SEGMENTS - 1)) / self.SEGMENTS
        lit_count = int(self._display_level * self.SEGMENTS)

        for i in range(self.SEGMENTS):
            x = i * (seg_w + gap)
            ratio = i / self.SEGMENTS
            if i < lit_count and self._active:
                if ratio > 0.85:
                    color = QColor(Colors.ERROR)
                elif ratio > 0.65:
                    color = QColor(Colors.WARNING)
                else:
                    color = QColor(Colors.ACCENT)
            else:
                color = QColor(Colors.BORDER_SOFT)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(int(x), 0, int(seg_w), h, 2, 2)
