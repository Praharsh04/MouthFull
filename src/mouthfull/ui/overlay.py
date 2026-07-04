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
import math
import PySide6.QtGui as QtGui
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect

from mouthfull.ui.theme import Colors

THEMES = {
    "idle":      {"a": "#4f7cff", "b": "#6d5cff", "c": "#9b5cff"},
    "listening": {"a": "#00d4ff", "b": "#00bfff", "c": "#87ceeb"},
    "speaking":  {"a": "#ff5c9d", "b": "#ff6f4f", "c": "#ffb454"},
    "processing":{"a": "#84cc16", "b": "#a3e635", "c": "#d9f99d"},
    "error":     {"a": "#ff5c5c", "b": "#ff8a3d", "c": "#ffb454"},
}

def hexToRgb(hex_str):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


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
        self.setFixedSize(280, 280)

        self._state = "idle"
        self._level = 0.0
        self._smoothLevel = 0.0
        self.t = 0.0
        self._drag_offset = None
        
        self._scale = 1.0
        self._y_offset = 0.0
        
        self._color = THEMES["idle"].copy()
        self._targetColor = THEMES["idle"].copy()

        # Idle breathing / reactive pulse animation loop
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(33)
        
        # Auto-dismiss timeout (fallback)
        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self.hide_orb)

        # Caption bubble, positioned above the orb
        self._bubble = TranscriptBubble(self)
        self._bubble_hide_timer = QTimer(self)
        self._bubble_hide_timer.setSingleShot(True)
        self._bubble_hide_timer.timeout.connect(self._bubble.hide)

        self._reposition_bubble()

        # Animations
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        
        from PySide6.QtCore import QParallelAnimationGroup
        
        # Enter animation
        self._anim_enter = QParallelAnimationGroup(self)
        fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        scale_in = QPropertyAnimation(self, b"scale")
        scale_in.setDuration(200)
        scale_in.setStartValue(0.9)
        scale_in.setEndValue(1.0)
        scale_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        slide_in = QPropertyAnimation(self, b"y_offset")
        slide_in.setDuration(200)
        slide_in.setStartValue(10.0)
        slide_in.setEndValue(0.0)
        slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._anim_enter.addAnimation(fade_in)
        self._anim_enter.addAnimation(scale_in)
        self._anim_enter.addAnimation(slide_in)
        
        # Exit animation
        self._anim_exit = QParallelAnimationGroup(self)
        fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        scale_out = QPropertyAnimation(self, b"scale")
        scale_out.setDuration(200)
        scale_out.setStartValue(1.0)
        scale_out.setEndValue(0.9)
        scale_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        slide_out = QPropertyAnimation(self, b"y_offset")
        slide_out.setDuration(200)
        slide_out.setStartValue(0.0)
        slide_out.setEndValue(10.0)
        slide_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self._anim_exit.addAnimation(fade_out)
        self._anim_exit.addAnimation(scale_out)
        self._anim_exit.addAnimation(slide_out)
        
        self._anim_exit.finished.connect(self.hide)

    @Property(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val
        self.update()

    @Property(float)
    def y_offset(self):
        return self._y_offset

    @y_offset.setter
    def y_offset(self, val):
        self._y_offset = val
        self.update()

    def hide_orb(self):
        if self.isVisible():
            self._anim_enter.stop()
            self._anim_exit.start()

    # ---------------------------------------------------------------- backend API
    def set_state(self, state: str):
        """Backend -> UI: idle | listening | processing | speaking | error"""
        if state not in THEMES:
            state = "idle"
        self._state = state
        self._targetColor = THEMES[state].copy()
        
        if state != "idle":
            # Task is active, keep orb alive
            self._auto_dismiss_timer.stop()
            if not self.isVisible():
                self.set_visible(True)
        else:
            # Returned to idle, dismiss after 1.5s
            self._auto_dismiss_timer.start(1500)
            
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
        if visible:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                self.snap_to_corner(screen.availableGeometry())
                
            self._anim_exit.stop()
            self.setVisible(True)
            self._anim_enter.start()
            # Start a fallback timer just in case it gets stuck
            self._auto_dismiss_timer.start(15000)
        else:
            self.hide_orb()

    def snap_to_corner(self, screen_geo, corner: str = "bottom-center", margin: int = 48):
        """Convenience placement helper (bottom-center is the new default)."""
        w, h = self.width(), self.height()
        if "center" in corner:
            x = screen_geo.left() + (screen_geo.width() - w) // 2
        else:
            x = screen_geo.right() - w - margin if "right" in corner else screen_geo.left() + margin
            
        y = screen_geo.bottom() - h - margin if "bottom" in corner else screen_geo.top() + margin
        self.move(x, y)

    # ---------------------------------------------------------------- internals
    def _reposition_bubble(self):
        self._bubble.adjustSize()
        bw = self._bubble.width()
        self._bubble.move((self.width() - bw) // 2, -self._bubble.height() - 10)
        
    def _noise(self, x):
        s = math.sin(x * 12.9898) * 43758.5453
        return s - math.floor(s)
        
    def _smoothNoise(self, x):
        i = math.floor(x)
        f = x - i
        a = self._noise(i)
        b = self._noise(i + 1)
        u = f * f * (3 - 2 * f)
        return a + (b - a) * u
        
    def _lerpColor(self):
        rate = 0.06
        for k in ['a', 'b', 'c']:
            cur = hexToRgb(self._color[k])
            tgt = hexToRgb(self._targetColor[k])
            r = cur[0] + (tgt[0] - cur[0]) * rate
            g = cur[1] + (tgt[1] - cur[1]) * rate
            b = cur[2] + (tgt[2] - cur[2]) * rate
            self._color[k] = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            
    def _hexA(self, hex_str, alpha):
        c = QColor(hex_str)
        c.setAlphaF(max(0.0, min(1.0, alpha)))
        return c

    def _on_tick(self):
        self.t += 0.033
        self._lerpColor()
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
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        size = self.width()
        cx, cy = size / 2, size / 2
        
        # Apply enter/exit animations
        p.translate(cx, cy + self._y_offset)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)
        
        # Orb core remains the same size as when widget was 160x160, but scaled down slightly as requested
        logical_size = 120
        baseR = logical_size * 0.28
        
        targetLevel = self._level
        speed = 1.0
        
        if self._state == 'idle':
            targetLevel = 0.12 + 0.05 * math.sin(self.t * 1.2)
            speed = 0.4
        elif self._state == 'listening':
            speed = 1.1
        elif self._state == 'speaking':
            targetLevel = max(self._level, 0.35 + 0.35 * abs(math.sin(self.t * 4.5)))
            speed = 1.8
        elif self._state == 'processing':
            targetLevel = 0.18
            speed = 0.9
        elif self._state == 'error':
            targetLevel = 0.2 + 0.1 * abs(math.sin(self.t * 3))
            speed = 0.6
            
        self._smoothLevel += (targetLevel - self._smoothLevel) * 0.12
        level = self._smoothLevel
        radius = baseR * (1 + level * 0.55)
        
        a, b, c = self._color['a'], self._color['b'], self._color['c']
        
        # Glow
        glowR = radius * (2.2 + level * 0.6)
        glow = QRadialGradient(cx, cy, glowR, cx, cy)
        glow.setColorAt(0.0, self._hexA(b, 0.35 + level * 0.25))
        glow.setColorAt(1.0, self._hexA(b, 0.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(int(cx - glowR), int(cy - glowR), int(glowR * 2), int(glowR * 2))
        
        # Thinking ring
        if self._state == 'processing':
            p.save()
            p.translate(cx, cy)
            p.rotate(math.degrees(self.t * 1.6))
            ringR = radius * 1.35
            grad = QLinearGradient(-ringR, 0, ringR, 0)
            grad.setColorAt(0.0, self._hexA(a, 0.0))
            grad.setColorAt(0.5, self._hexA(a, 0.8))
            grad.setColorAt(1.0, self._hexA(a, 0.0))
            
            pen = QtGui.QPen(grad, 2.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(int(-ringR), int(-ringR), int(ringR*2), int(ringR*2), 0, int(252 * 16))
            p.restore()
            
        # Listening rings
        if self._state == 'listening' and level > 0.15:
            for i in range(2):
                phase = (self.t * 0.9 + i * 0.5) % 1.0
                r = radius * (1 + phase * 1.1)
                alpha = (1 - phase) * 0.25 * (0.4 + level)
                p.setPen(QtGui.QPen(self._hexA(a, alpha), 1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
                
        # Error pulse
        if self._state == 'error':
            pulse = 0.5 + 0.5 * math.sin(self.t * 4)
            p.setPen(QtGui.QPen(self._hexA(a, 0.3 + pulse * 0.3), 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            err_r = radius * 1.2
            p.drawEllipse(int(cx - err_r), int(cy - err_r), int(err_r * 2), int(err_r * 2))
            
        # Blob Layers
        self._drawBlobLayer(p, cx, cy, radius, self.t, speed, level, 48, 1.0, 0.16, [a, b, c], 1.0)
        self._drawBlobLayer(p, cx, cy, radius * 0.86, self.t, speed * 1.3, level, 40, -0.7, 0.1, [b, c, a], 0.55)
        
        # Highlight reflection
        hl = QRadialGradient(cx - radius * 0.35, cy - radius * 0.4, radius * 0.6, cx - radius * 0.35, cy - radius * 0.4)
        hl.setColorAt(0.0, QColor(255, 255, 255, int(255 * 0.55)))
        hl.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(hl)
        p.drawEllipse(int(cx - radius * 0.85), int(cy - radius * 0.9), int(radius * 1.1), int(radius * 1.1))
        
    def _drawBlobLayer(self, p, cx, cy, radius, t, speed, level, points, phaseDir, ampScale, colors, alpha):
        distortAmp = radius * (0.05 + level * ampScale)
        path = QPainterPath()
        for i in range(points + 1):
            theta = (i / points) * math.pi * 2
            n = self._smoothNoise(theta * 2.1 + t * speed * 0.6 * phaseDir) - 0.5
            r = radius + n * distortAmp
            x = cx + math.cos(theta) * r
            y = cy + math.sin(theta) * r
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        
        c1, c2, c3 = colors
        grad = QRadialGradient(cx, cy, radius * 1.1, cx - radius * 0.3, cy - radius * 0.35)
        grad.setColorAt(0.0, self._hexA(c1, alpha))
        grad.setColorAt(0.55, self._hexA(c2, alpha))
        grad.setColorAt(1.0, self._hexA(c3, alpha))
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawPath(path)

    def hide_state_label(self):
        pass  # placeholder hook if a text label under the orb is later desired

def make_orb_for_backend() -> AIOrb:
    """Factory used by app.py; kept separate so a backend module can import
    just this function without pulling in the rest of app.py."""
    orb = AIOrb()
    return orb
