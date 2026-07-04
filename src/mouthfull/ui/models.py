"""
models.py — Speech Models Page
--------------------------------
Browse, install, and select speech-to-text models with advanced progress UI.
"""
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QProgressBar, QFrame, QSizePolicy
)
from mouthfull.ui.theme import Colors
from mouthfull.ui.widgets import Card, StatusBadge

STATUS_META = {
    "not_installed": ("neutral", "Not Installed"),
    "downloading": ("info", "Downloading"),
    "paused": ("warning", "Paused"),
    "installed": ("success", "Installed"),
    "error": ("error", "Failed"),
}

AVAILABLE_MODELS = [
    {
        "id": "nvidia/parakeet-tdt-1.1b", 
        "name": "NVIDIA Parakeet TDT v3", 
        "engine": "parakeet", 
        "size": "1.1 GB",
        "lang": "English", 
        "accuracy": "Excellent", 
        "speed": "Fastest",
        "desc": "(Recommended) Extremely fast and accurate Transducer model.",
        "hardware": "GPU Recommended"
    },
    {
        "id": "moonshine", 
        "name": "Moonshine", 
        "engine": "moonshine", 
        "size": "300 MB",
        "lang": "English", 
        "accuracy": "Good", 
        "speed": "Ultra Low Latency",
        "desc": "Ultra low latency model optimized for real-time dictation.",
        "hardware": "CPU / GPU"
    },
    {
        "id": "large-v3-turbo", 
        "name": "Whisper Large v3 Turbo", 
        "engine": "faster_whisper", 
        "size": "1.6 GB",
        "lang": "Multilingual", 
        "accuracy": "Excellent", 
        "speed": "Fast",
        "desc": "Quantized turbo version of the largest Whisper model.",
        "hardware": "GPU Recommended"
    },
    {
        "id": "distil-large-v3", 
        "name": "Distil-Whisper", 
        "engine": "faster_whisper", 
        "size": "750 MB",
        "lang": "English", 
        "accuracy": "Very Good", 
        "speed": "Very Fast",
        "desc": "Lightweight distilled version of Whisper Large.",
        "hardware": "CPU / GPU"
    },
    {
        "id": "tiny.en", 
        "name": "Whisper Tiny (English)", 
        "engine": "faster_whisper", 
        "size": "150 MB",
        "lang": "English", 
        "accuracy": "Good", 
        "speed": "Ultra Fast",
        "desc": "The fastest official Whisper model. Perfect for quick dictation on older hardware.",
        "hardware": "CPU / GPU"
    },
    {
        "id": "nvidia/canary-1b", 
        "name": "NVIDIA Canary 1B", 
        "engine": "canary", 
        "size": "1.1 GB",
        "lang": "Multilingual", 
        "accuracy": "Highest Accuracy", 
        "speed": "Moderate",
        "desc": "Highest accuracy multilingual ASR model by NVIDIA.",
        "hardware": "GPU Required"
    },
]


class ModelRow(Card):
    def __init__(self, model: dict, on_install, on_remove, on_select, on_pause, on_resume, on_cancel, parent=None):
        super().__init__(parent=parent)
        self.model_id = model["id"]
        self._on_install = on_install
        self._on_remove = on_remove
        self._on_select = on_select
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_cancel = on_cancel
        self.body_layout().setContentsMargins(16, 16, 16, 16)
        self.body_layout().setSpacing(12)

        # -- Top Row --
        top_row = QHBoxLayout()
        name_col = QVBoxLayout()
        name_col.setSpacing(4)

        name_line = QHBoxLayout()
        self.name_label = QLabel(model["name"])
        self.name_label.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        name_line.addWidget(self.name_label)

        self.active_badge = QLabel("ACTIVE")
        self.active_badge.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 10px; font-weight: 800;
            background-color: {Colors.ACCENT_SOFT}; border-radius: 4px; padding: 2px 6px;
        """)
        self.active_badge.hide()
        name_line.addWidget(self.active_badge)
        name_line.addStretch(1)
        name_col.addLayout(name_line)

        desc_lbl = QLabel(model["desc"])
        desc_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        name_col.addWidget(desc_lbl)

        meta = QLabel(f"Size: {model['size']} · Lang: {model['lang']} · Acc: {model['accuracy']} · Speed: {model['speed']} · H/W: {model['hardware']}")
        meta.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        name_col.addWidget(meta)

        top_row.addLayout(name_col, 1)

        self.status_badge = StatusBadge(*reversed(STATUS_META["not_installed"]))
        top_row.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignTop)

        self.action_btn = QPushButton()
        self.action_btn.setFixedWidth(120)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        top_row.addWidget(self.action_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.setFixedWidth(70)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self._on_remove(self.model_id))
        self.delete_btn.hide()
        top_row.addWidget(self.delete_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.body_layout().addLayout(top_row)

        # -- Progress Section --
        self.progress_widget = QWidget()
        prog_layout = QVBoxLayout(self.progress_widget)
        prog_layout.setContentsMargins(0, 10, 0, 0)
        prog_layout.setSpacing(6)
        
        info_row = QHBoxLayout()
        self.stage_lbl = QLabel("Preparing...")
        self.stage_lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 11px; font-weight: 600;")
        self.stats_lbl = QLabel("0% (0 MB/s) - ETA: 0s")
        self.stats_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        info_row.addWidget(self.stage_lbl)
        info_row.addStretch(1)
        info_row.addWidget(self.stats_lbl)
        prog_layout.addLayout(info_row)

        bar_ctrl_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(12)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BG_APP};
                border-radius: 6px;
                border: 1px solid {Colors.BORDER_SOFT};
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.ACCENT};
                border-radius: 5px;
            }}
        """)
        bar_ctrl_row.addWidget(self.progress, 1)

        self.pause_resume_btn = QPushButton("Pause")
        self.pause_resume_btn.setFixedSize(60, 24)
        self.pause_resume_btn.clicked.connect(self._toggle_pause)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("variant", "danger")
        self.cancel_btn.setFixedSize(60, 24)
        self.cancel_btn.clicked.connect(lambda: self._on_cancel(self.model_id))

        bar_ctrl_row.addWidget(self.pause_resume_btn)
        bar_ctrl_row.addWidget(self.cancel_btn)
        
        prog_layout.addLayout(bar_ctrl_row)
        self.progress_widget.hide()
        self.body_layout().addWidget(self.progress_widget)

        self._status = "not_installed"
        self._refresh_action_button()
        self.action_btn.clicked.connect(self._handle_action)

    def _toggle_pause(self):
        if self._status == "downloading":
            self._on_pause(self.model_id)
        elif self._status == "paused":
            self._on_resume(self.model_id)

    def _refresh_action_button(self):
        if self._status == "installed":
            self.action_btn.setText("Use Model")
            self.action_btn.setProperty("variant", "primary")
            self.action_btn.show()
            self.delete_btn.show()
            self.progress_widget.hide()
        elif self._status in ("downloading", "paused"):
            self.action_btn.hide()
            self.delete_btn.hide()
            self.progress_widget.show()
            self.pause_resume_btn.setText("Resume" if self._status == "paused" else "Pause")
        elif self._status == "error":
            self.action_btn.setText("Retry")
            self.action_btn.setProperty("variant", None)
            self.action_btn.show()
            self.delete_btn.hide()
            self.progress_widget.hide()
        else:
            self.action_btn.setText("Install")
            self.action_btn.setProperty("variant", None)
            self.action_btn.show()
            self.delete_btn.hide()
            self.progress_widget.hide()
            
        self.action_btn.style().unpolish(self.action_btn)
        self.action_btn.style().polish(self.action_btn)

    def _handle_action(self):
        if self._status == "installed":
            self._on_select(self.model_id)
        else:
            self._on_install(self.model_id)

    def set_status(self, status: str):
        self._status = status
        kind, label = STATUS_META.get(status, ("neutral", "Unknown"))
        self.status_badge.set_status(kind, label)
        self._refresh_action_button()

    def update_progress(self, pct: float, speed_mbps: float, rem_mb: float, eta: float, stage: str):
        if self.progress.value() != int(pct):
            self.progress.setValue(int(pct))
        self.stage_lbl.setText(stage)
        self.stats_lbl.setText(f"{pct:.1f}% ({speed_mbps:.2f} MB/s) - ETA: {int(eta)}s - Rem: {rem_mb:.1f} MB")
        if not self.progress_widget.isVisible() and self._status in ("downloading", "paused"):
            self.progress_widget.show()

    def set_active(self, active: bool):
        self.active_badge.setVisible(active)
        if active:
            self.action_btn.setText("Active")
            self.action_btn.setEnabled(False)
        else:
            if self._status == "installed":
                self.action_btn.setText("Use Model")
            self.action_btn.setEnabled(True)


class ModelsPage(QWidget):
    on_model_install_clicked = Signal(str)
    on_model_remove_clicked = Signal(str)
    on_model_selected = Signal(str)
    on_model_pause_clicked = Signal(str)
    on_model_resume_clicked = Signal(str)
    on_model_cancel_clicked = Signal(str)
    on_refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = {}
        self._active_model_id = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Speech Models")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)

        import qtawesome as qta
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(" Search models...")
        self.search_box.addAction(qta.icon('fa5s.search', color="#a7a8ac"), QLineEdit.ActionPosition.LeadingPosition)
        self.search_box.setFixedWidth(250)
        self.search_box.textChanged.connect(self._apply_filter)
        header.addWidget(self.search_box)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(qta.icon('fa5s.sync', color="#fff"))
        refresh_btn.clicked.connect(self.on_refresh_clicked.emit)
        header.addWidget(refresh_btn)
        outer.addLayout(header)

        subtitle = QLabel("Manage local speech-to-text engines. Downloads run in the background and support pause/resume.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setSpacing(12)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)
        self.list_layout.addStretch(1)

    def _apply_filter(self, text: str):
        text = text.lower().strip()
        for model_id, row in self._rows.items():
            row.setVisible(text in row.name_label.text().lower())

    def update_models(self, models: list):
        for row in self._rows.values():
            row.setParent(None)
        self._rows.clear()
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for model in models:
            row = ModelRow(
                model,
                on_install=lambda mid: self.on_model_install_clicked.emit(mid),
                on_remove=lambda mid: self.on_model_remove_clicked.emit(mid),
                on_select=lambda mid: self.on_model_selected.emit(mid),
                on_pause=lambda mid: self.on_model_pause_clicked.emit(mid),
                on_resume=lambda mid: self.on_model_resume_clicked.emit(mid),
                on_cancel=lambda mid: self.on_model_cancel_clicked.emit(mid),
            )
            row.set_active(model["id"] == self._active_model_id)
            row.set_status(model.get("status", "not_installed"))
            self._rows[model["id"]] = row
            self.list_layout.addWidget(row)
        self.list_layout.addStretch(1)

    def update_download_progress(self, model_id: str, pct: float, speed_mbps: float, rem_mb: float, eta: float, stage: str):
        if model_id in self._rows:
            self._rows[model_id].update_progress(pct, speed_mbps, rem_mb, eta, stage)

    def set_model_status(self, model_id: str, status: str):
        if model_id in self._rows:
            self._rows[model_id].set_status(status)

    def set_active_model(self, model_id: str):
        self._active_model_id = model_id
        for mid, row in self._rows.items():
            row.set_active(mid == model_id)
