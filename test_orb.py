import sys
import math
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget

THEMES = {
    "idle":      {"a": "#4f7cff", "b": "#6d5cff", "c": "#9b5cff"},
    "listening": {"a": "#33c7ff", "b": "#4f9bff", "c": "#5c7dff"},
    "speaking":  {"a": "#ff5c9d", "b": "#ff6f4f", "c": "#ffb454"},
    "processing":{"a": "#6d5cff", "b": "#9b5cff", "c": "#c15cff"},
    "error":     {"a": "#ff5c5c", "b": "#ff8a3d", "c": "#ffb454"},
}

def hexToRgb(hex_str):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

class VoiceOrb(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(220, 220)
        self.state = 'idle'
        self.level = 0.0
        self._smoothLevel = 0.0
        self.t = 0.0
        
        self._color = THEMES["idle"].copy()
        self._targetColor = THEMES["idle"].copy()
        self._particles = []
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._loop)
        self.timer.start(16) # ~60fps
        
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
            
    def _loop(self):
        self.t += 0.016
        self._lerpColor()
        self.update()
        
    def _hexA(self, hex_str, alpha):
        c = QColor(hex_str)
        c.setAlphaF(max(0.0, min(1.0, alpha)))
        return c
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        size = self.width()
        cx, cy = size / 2, size / 2
        baseR = size * 0.28
        
        targetLevel = self.level
        speed = 1.0
        
        if self.state == 'idle':
            targetLevel = 0.12 + 0.05 * math.sin(self.t * 1.2)
            speed = 0.4
        elif self.state == 'listening':
            speed = 1.1
        elif self.state == 'speaking':
            targetLevel = max(self.level, 0.35 + 0.35 * abs(math.sin(self.t * 4.5)))
            speed = 1.8
        elif self.state == 'processing': # thinking
            targetLevel = 0.18
            speed = 0.9
        elif self.state == 'error':
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
        if self.state == 'processing':
            p.save()
            p.translate(cx, cy)
            p.rotate(math.degrees(self.t * 1.6))
            ringR = radius * 1.35
            grad = QLinearGradient(-ringR, 0, ringR, 0)
            grad.setColorAt(0.0, self._hexA(a, 0.0))
            grad.setColorAt(0.5, self._hexA(a, 0.8))
            grad.setColorAt(1.0, self._hexA(a, 0.0))
            
            import PySide6.QtGui as QtGui
            pen = QtGui.QPen(grad, 2.5)
            p.setPen(pen)
            p.setBrush(Qt.PenStyle.NoPen)
            # drawArc takes (x, y, w, h, startAngle, spanAngle) in 1/16ths of a degree
            p.drawArc(int(-ringR), int(-ringR), int(ringR*2), int(ringR*2), 0, int(252 * 16)) # 1.4 * 180 = 252 degrees
            p.restore()
            
        # Listening rings
        if self.state == 'listening' and level > 0.15:
            for i in range(2):
                phase = (self.t * 0.9 + i * 0.5) % 1.0
                r = radius * (1 + phase * 1.1)
                alpha = (1 - phase) * 0.25 * (0.4 + level)
                p.setPen(QtGui.QPen(self._hexA(a, alpha), 1.5))
                p.setBrush(Qt.PenStyle.NoPen)
                p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
                
        # Error pulse
        if self.state == 'error':
            pulse = 0.5 + 0.5 * math.sin(self.t * 4)
            p.setPen(QtGui.QPen(self._hexA(a, 0.3 + pulse * 0.3), 2.0))
            p.setBrush(Qt.PenStyle.NoPen)
            err_r = radius * 1.2
            p.drawEllipse(int(cx - err_r), int(cy - err_r), int(err_r * 2), int(err_r * 2))
            
        # Blob Layers
        self._drawBlobLayer(p, cx, cy, radius, self.t, speed, level, 48, 1.0, 0.16, [a, b, c], 1.0)
        self._drawBlobLayer(p, cx, cy, radius * 0.86, self.t, speed * 1.3, level, 40, -0.7, 0.1, [b, c, a], 0.55)
        
        # Highlight
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = VoiceOrb()
    w.show()
    sys.exit(app.exec())
