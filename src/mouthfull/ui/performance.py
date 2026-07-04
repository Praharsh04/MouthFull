"""
performance.py — Performance Dashboard Page
----------------------------------------------
Live resource + pipeline latency monitoring (CPU, RAM, GPU, per-stage
latency breakdown), rendered with lightweight custom-painted sparkline
charts (no extra chart dependency required).

Backend integration
---------------------
Methods (backend -> UI):
    perf_page.update_metric("cpu", value)         # value 0-100 (%)
    perf_page.update_metric("ram", value)         # value 0-100 (%)
    perf_page.update_metric("gpu", value)         # value 0-100 (%)
    perf_page.update_latency_breakdown(dict)      # {"capture": 12, "stt": 180, "llm": 340, "inject": 8} (ms)
    perf_page.update_pipeline_stats(dict)         # {"avg_latency_ms": 540, "p95_latency_ms": 810, "requests": 128}

Signals (UI -> backend):
    perf_page.on_reset_stats_clicked()
"""
import random
from collections import deque

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton

from mouthfull.ui.theme import Colors
from mouthfull.ui.widgets import Card


class Sparkline(QWidget):
    def __init__(self, color: str, max_points: int = 60, y_max: float = 100.0, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._data = deque([0.0] * max_points, maxlen=max_points)
        self._y_max = y_max
        self.setMinimumHeight(64)

    def push(self, value: float):
        self._data.append(max(0.0, min(self._y_max, value)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self._data)
        if n < 2:
            return

        step_x = w / (n - 1)
        points = []
        for i, v in enumerate(self._data):
            x = i * step_x
            y = h - (v / self._y_max) * (h - 4) - 2
            points.append((x, y))

        # Filled area under the curve
        grad = QLinearGradient(0, 0, 0, h)
        fill_color = QColor(self._color)
        fill_color.setAlpha(70)
        grad.setColorAt(0.0, fill_color)
        transparent = QColor(self._color)
        transparent.setAlpha(0)
        grad.setColorAt(1.0, transparent)

        path_points = points + [(w, h), (0, h)]
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(*points[0])
        for x, y in points[1:]:
            path.lineTo(x, y)
        path.lineTo(w, h)
        path.lineTo(0, h)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawPath(path)

        pen = QPen(self._color)
        pen.setWidth(2)
        p.setPen(pen)
        for i in range(len(points) - 1):
            p.drawLine(int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1]))


class MetricTile(Card):
    def __init__(self, label: str, color: str, unit: str = "%", parent=None):
        super().__init__(parent=parent)
        self.body_layout().setContentsMargins(16, 14, 16, 14)
        header = QHBoxLayout()
        title = QLabel(label)
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self.value_label = QLabel(f"0{unit}")
        self.value_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 700;")
        header.addWidget(self.value_label)
        self.body_layout().addLayout(header)

        self.unit = unit
        self.spark = Sparkline(color)
        self.body_layout().addWidget(self.spark)

    def push(self, value: float):
        self.value_label.setText(f"{value:.0f}{self.unit}")
        self.spark.push(value)


class LatencyBar(QWidget):
    """Horizontal stacked bar showing per-stage latency proportion."""

    STAGE_COLORS = {
        "capture": Colors.INFO,
        "stt": Colors.ACCENT,
        "llm": Colors.WARNING,
        "inject": Colors.SUCCESS,
    }
    STAGE_LABELS = {
        "capture": "Audio Capture",
        "stt": "Speech-to-Text",
        "llm": "LLM Processing",
        "inject": "Text Injection",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {"capture": 0, "stt": 0, "llm": 0, "inject": 0}
        self.setMinimumHeight(34)

    def set_data(self, data: dict):
        self._data = data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), 14
        total = sum(self._data.values()) or 1
        x = 0
        for stage, value in self._data.items():
            seg_w = (value / total) * w
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.STAGE_COLORS.get(stage, Colors.TEXT_MUTED)))
            p.drawRoundedRect(int(x), 0, int(seg_w) + 1, h, 3, 3)
            x += seg_w


class PerformancePage(QWidget):
    on_reset_stats_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Performance")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)
        reset_btn = QPushButton("Reset Stats")
        reset_btn.clicked.connect(self.on_reset_stats_clicked.emit)
        header.addWidget(reset_btn)
        outer.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.cpu_tile = MetricTile("CPU Usage", Colors.INFO)
        self.ram_tile = MetricTile("Memory Usage", Colors.ACCENT)
        self.gpu_tile = MetricTile("GPU Usage", Colors.SUCCESS)
        grid.addWidget(self.cpu_tile, 0, 0)
        grid.addWidget(self.ram_tile, 0, 1)
        grid.addWidget(self.gpu_tile, 0, 2)
        outer.addLayout(grid)

        # Pipeline summary
        summary_card = Card(title="Pipeline Latency")
        stats_row = QHBoxLayout()
        self.avg_label = self._stat_label("Avg Latency", "0 ms")
        self.p95_label = self._stat_label("P95 Latency", "0 ms")
        self.req_label = self._stat_label("Requests (session)", "0")
        stats_row.addWidget(self.avg_label)
        stats_row.addWidget(self.p95_label)
        stats_row.addWidget(self.req_label)
        stats_row.addStretch(1)
        summary_card.body_layout().addLayout(stats_row)

        self.latency_bar = LatencyBar()
        summary_card.body_layout().addWidget(self.latency_bar)

        legend_row = QHBoxLayout()
        for stage, label in LatencyBar.STAGE_LABELS.items():
            color = LatencyBar.STAGE_COLORS[stage]
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px;")
            text = QLabel(label)
            text.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; margin-right: 12px;")
            pair = QHBoxLayout()
            pair.setSpacing(4)
            pair.addWidget(dot)
            pair.addWidget(text)
            legend_row.addLayout(pair)
        legend_row.addStretch(1)
        summary_card.body_layout().addLayout(legend_row)

        outer.addWidget(summary_card)
        outer.addStretch(1)



    def _stat_label(self, label, value):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 24, 0)
        layout.setSpacing(2)
        v = QLabel(value)
        v.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        l = QLabel(label)
        l.setStyleSheet(f"font-size: 10.5px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(v)
        layout.addWidget(l)
        box.value_widget = v
        return box



    # ---------------------------------------------------------------- backend API
    def update_metric(self, metric: str, value: float):
        if metric == "cpu":
            self.cpu_tile.push(value)
        elif metric == "ram":
            self.ram_tile.push(value)
        elif metric == "gpu":
            self.gpu_tile.push(value)

    def update_latency_breakdown(self, data: dict):
        self.latency_bar.set_data(data)

    def update_pipeline_stats(self, data: dict):
        if "avg_latency_ms" in data:
            self.avg_label.value_widget.setText(f"{data['avg_latency_ms']} ms")
        if "p95_latency_ms" in data:
            self.p95_label.value_widget.setText(f"{data['p95_latency_ms']} ms")
        if "requests" in data:
            self.req_label.value_widget.setText(str(data["requests"]))


