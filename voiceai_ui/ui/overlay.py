"""
overlay.py — Floating AI Orb
----------------------------
A small, frameless, always-on-top, draggable orb that reflects the app's
current state (idle / listening / processing / speaking / error). This is
the visual heartbeat of the app, always visible while active, similar in
spirit to Phone Link's floating controls or a voice-assistant orb.

Backend integration points
---------------------------
Signals (UI -> backend):
    orb.clicked_signal        -> emitted on left click (typically toggles recording)
    orb.double_clicked_signal -> emitted on double click (e.g. open dashboard)
    orb.right_clicked_signal  -> emitted on right click (e.g. open context menu)
    orb.dragged_signal(QPoint)-> emitted while being dragged, new position

Methods (backend -> UI):
    orb.set_state("idle" | "listening" | "processing" | "speaking" | "error")
    orb.update_audio_level(level: float)   # 0.0 - 1.0, drives reactive pulse while listening
    orb.set_visible(bool)
    orb.show_transcript_preview(text: str) # small floating caption above the orb
"""
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QFont
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect

from ui.theme import Colors

STATE_COLORS = {
    "idle": Colors.ORB_IDLE,
    "listening": Colors.ORB_LISTENING,
    "processing": Colors.ORB_PROCESSING,
    "speaking": Colors.ORB_SPEAKING,
    "error": Colors.ORB_ERROR,
}

STATE_LABELS = {
    "idle": "Idle",
    "listening": "Listening…",
    "processing": "Thinking…",
    "speaking": "Speaking…",
    "error": "Error",
}


class TranscriptBubble(QLabel):
    """Small caption bubble shown above the orb, e.g. live partial transcript."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setMaximumWidth(260)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            background-color: {Colors.BG_SURFACE_ALT};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER};
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 11px;
        """)
        self.hide()


class AIOrb(QWidget):
    clicked_signal = Signal()
    double_clicked_signal = Signal()
    right_clicked_signal = Signal(QPoint)
    dragged_signal = Signal(QPoint)

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint |
                          Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(84, 84)

        self._state = "idle"
        self._level = 0.0
        self._display_level = 0.0
        self._pulse_phase = 0.0
        self._drag_offset = None

        # Idle breathing / reactive pulse animation loop
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(33)

        # Caption bubble, positioned above the orb
        self._bubble = TranscriptBubble(self)
        self._bubble_hide_timer = QTimer(self)
        self._bubble_hide_timer.setSingleShot(True)
        self._bubble_hide_timer.timeout.connect(self._bubble.hide)

        self._reposition_bubble()

        # Fade-in on creation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade.setDuration(220)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---------------------------------------------------------------- backend API
    def set_state(self, state: str):
        """Backend -> UI: idle | listening | processing | speaking | error"""
        if state not in STATE_COLORS:
            state = "idle"
        self._state = state
        self.update()

    def update_audio_level(self, level: float):
        """Backend -> UI: push mic RMS/peak level while listening (0.0 - 1.0)."""
        self._level = max(0.0, min(1.0, level))

    def show_transcript_preview(self, text: str, duration_ms: int = 3000):
        """Backend -> UI: show a live/partial transcript caption above the orb."""
        if not text:
            self._bubble.hide()
            return
        self._bubble.setText(text)
        self._reposition_bubble()
        self._bubble.show()
        self._bubble_hide_timer.start(duration_ms)

    def set_visible(self, visible: bool):
        self.setVisible(visible)
        if visible:
            self._opacity_effect.setOpacity(0.0)
            self._fade.start()

    def snap_to_corner(self, screen_geo, corner: str = "bottom-right", margin: int = 24):
        """Convenience placement helper (bottom-right is the common default)."""
        w, h = self.width(), self.height()
        x = screen_geo.right() - w - margin if "right" in corner else screen_geo.left() + margin
        y = screen_geo.bottom() - h - margin if "bottom" in corner else screen_geo.top() + margin
        self.move(x, y)

    # ---------------------------------------------------------------- internals
    def _reposition_bubble(self):
        self._bubble.adjustSize()
        bw = self._bubble.width()
        self._bubble.move((self.width() - bw) // 2, -self._bubble.height() - 10)

    def _on_tick(self):
        self._pulse_phase += 0.08
        if self._display_level < self._level:
            self._display_level += (self._level - self._display_level) * 0.4
        else:
            self._display_level *= 0.85
        self.update()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._reposition_bubble()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked_signal.emit(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            self.dragged_signal.emit(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.clicked_signal.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked_signal.emit()

    def paintEvent(self, event):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        base_r = 26
        color = QColor(STATE_COLORS[self._state])

        # Reactive / breathing ring
        if self._state == "listening":
            ring_r = base_r + 6 + self._display_level * 14
        else:
            breathe = (math.sin(self._pulse_phase) + 1) / 2  # 0..1
            ring_r = base_r + 4 + breathe * 5

        ring_color = QColor(color)
        ring_color.setAlpha(70)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ring_color)
        p.drawEllipse(int(cx - ring_r), int(cy - ring_r), int(ring_r * 2), int(ring_r * 2))

        # Core orb with radial gradient
        grad = QRadialGradient(cx, cy - base_r * 0.3, base_r * 1.4)
        core_light = QColor(color).lighter(140)
        grad.setColorAt(0.0, core_light)
        grad.setColorAt(1.0, color)
        p.setBrush(grad)
        p.drawEllipse(int(cx - base_r), int(cy - base_r), int(base_r * 2), int(base_r * 2))

        # Spinner arc while processing
        if self._state == "processing":
            p.setPen(Qt.PenStyle.NoPen)
            spinner_color = QColor("#ffffff")
            spinner_color.setAlpha(200)
            p.setBrush(spinner_color)
            angle_deg = (self._pulse_phase * 80) % 360
            p.save()
            p.translate(cx, cy)
            p.rotate(angle_deg)
            p.drawEllipse(int(base_r - 6), -3, 6, 6)
            p.restore()

    def hide_state_label(self):
        pass  # placeholder hook if a text label under the orb is later desired


def make_orb_for_backend() -> AIOrb:
    """Factory used by app.py; kept separate so a backend module can import
    just this function without pulling in the rest of app.py."""
    orb = AIOrb()
    return orb
