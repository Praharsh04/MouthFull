"""
models.py — Speech Models Page
--------------------------------
Browse, install, and select speech-to-text models (Ollama Desktop style
model list) with size, status, and download progress per row.

Backend integration
---------------------
Signals (UI -> backend):
    models_page.on_model_install_clicked(model_id: str)
    models_page.on_model_remove_clicked(model_id: str)
    models_page.on_model_selected(model_id: str)     # set as active model
    models_page.on_model_cancel_download(model_id: str)
    models_page.on_refresh_clicked()

Methods (backend -> UI):
    models_page.update_models(models: list[dict])          # full refresh
    models_page.update_download_progress(model_id, pct)    # 0-100
    models_page.set_model_status(model_id, status)         # not_installed|downloading|installed|error
    models_page.set_active_model(model_id)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QProgressBar, QFrame
)

from ui.theme import Colors
from ui.widgets import Card, StatusBadge

STATUS_META = {
    "not_installed": ("neutral", "Not Installed"),
    "downloading": ("info", "Downloading"),
    "installed": ("success", "Installed"),
    "error": ("error", "Failed"),
}

DUMMY_MODELS = [
    {"id": "whisper-tiny", "name": "Whisper Tiny", "engine": "OpenAI Whisper", "size": "75 MB",
     "lang": "Multilingual", "status": "installed", "accuracy": "Basic", "speed": "Fastest"},
    {"id": "whisper-small-en", "name": "Whisper Small (English)", "engine": "OpenAI Whisper", "size": "244 MB",
     "lang": "English", "status": "installed", "accuracy": "Good", "speed": "Fast"},
    {"id": "whisper-medium", "name": "Whisper Medium", "engine": "OpenAI Whisper", "size": "769 MB",
     "lang": "Multilingual", "status": "downloading", "accuracy": "Very Good", "speed": "Moderate"},
    {"id": "whisper-large-v3", "name": "Whisper Large v3", "engine": "OpenAI Whisper", "size": "2.9 GB",
     "lang": "Multilingual", "status": "not_installed", "accuracy": "Excellent", "speed": "Slower"},
    {"id": "vosk-en-us", "name": "Vosk EN-US Small", "engine": "Vosk", "size": "40 MB",
     "lang": "English (US)", "status": "not_installed", "accuracy": "Basic", "speed": "Fastest"},
    {"id": "nvidia-parakeet", "name": "Parakeet TDT 1.1B", "engine": "NVIDIA NeMo", "size": "1.1 GB",
     "lang": "English", "status": "error", "accuracy": "Excellent", "speed": "Fast (GPU)"},
]


class ModelRow(Card):
    def __init__(self, model: dict, on_install, on_remove, on_select, on_cancel, parent=None):
        super().__init__(parent=parent)
        self.model_id = model["id"]
        self._on_install = on_install
        self._on_remove = on_remove
        self._on_select = on_select
        self._on_cancel = on_cancel
        self.body_layout().setContentsMargins(16, 12, 16, 12)

        top_row = QHBoxLayout()
        name_col = QVBoxLayout()
        name_col.setSpacing(2)

        name_line = QHBoxLayout()
        self.name_label = QLabel(model["name"])
        self.name_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        name_line.addWidget(self.name_label)

        self.active_badge = QLabel("ACTIVE")
        self.active_badge.setStyleSheet(f"""
            color: {Colors.ACCENT}; font-size: 9px; font-weight: 700;
            background-color: {Colors.ACCENT_SOFT}; border-radius: 4px; padding: 2px 6px;
        """)
        self.active_badge.hide()
        name_line.addWidget(self.active_badge)
        name_line.addStretch(1)
        name_col.addLayout(name_line)

        meta = QLabel(f"{model['engine']} · {model['size']} · {model['lang']} · Accuracy: {model['accuracy']} · Speed: {model['speed']}")
        meta.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10.5px;")
        name_col.addWidget(meta)

        top_row.addLayout(name_col, 1)

        self.status_badge = StatusBadge(*reversed(STATUS_META[model["status"]]))
        top_row.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self.action_btn = QPushButton()
        self.action_btn.setFixedWidth(110)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        top_row.addWidget(self.action_btn)

        self.body_layout().addLayout(top_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(8)
        self.progress.hide()
        self.body_layout().addWidget(self.progress)

        self._status = model["status"]
        self._refresh_action_button()
        self.action_btn.clicked.connect(self._handle_action)

    def _refresh_action_button(self):
        if self._status == "installed":
            self.action_btn.setText("Use Model")
            self.action_btn.setProperty("variant", "primary")
        elif self._status == "downloading":
            self.action_btn.setText("Cancel")
            self.action_btn.setProperty("variant", "danger")
            self.progress.show()
        elif self._status == "error":
            self.action_btn.setText("Retry")
            self.action_btn.setProperty("variant", None)
        else:
            self.action_btn.setText("Install")
            self.action_btn.setProperty("variant", None)
        self.action_btn.style().unpolish(self.action_btn)
        self.action_btn.style().polish(self.action_btn)
        if self._status != "downloading":
            self.progress.hide()

    def _handle_action(self):
        if self._status == "installed":
            self._on_select(self.model_id)
        elif self._status == "downloading":
            self._on_cancel(self.model_id)
        else:
            self._on_install(self.model_id)

    def set_status(self, status: str):
        self._status = status
        kind, label = STATUS_META.get(status, ("neutral", "Unknown"))
        self.status_badge.set_status(kind, label)
        self._refresh_action_button()

    def set_progress(self, pct: int):
        self.progress.setValue(pct)
        if not self.progress.isVisible() and self._status == "downloading":
            self.progress.show()

    def set_active(self, active: bool):
        self.active_badge.setVisible(active)


class ModelsPage(QWidget):
    on_model_install_clicked = Signal(str)
    on_model_remove_clicked = Signal(str)
    on_model_selected = Signal(str)
    on_model_cancel_download = Signal(str)
    on_refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = {}
        self._active_model_id = "whisper-small-en"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Speech Models")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search models…")
        self.search_box.setFixedWidth(220)
        self.search_box.textChanged.connect(self._apply_filter)
        header.addWidget(self.search_box)

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.clicked.connect(self.on_refresh_clicked.emit)
        header.addWidget(refresh_btn)
        outer.addLayout(header)

        subtitle = QLabel("Choose which speech-to-text engine transcribes your voice. Larger models are more accurate but slower.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setSpacing(10)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        self.list_layout.addStretch(1)
        self.update_models(DUMMY_MODELS)

    def _apply_filter(self, text: str):
        text = text.lower().strip()
        for model_id, row in self._rows.items():
            row.setVisible(text in row.name_label.text().lower())

    # ---------------------------------------------------------------- backend API
    def update_models(self, models: list):
        """Full refresh of the model list from backend data."""
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
                on_select=self._handle_select,
                on_cancel=lambda mid: self.on_model_cancel_download.emit(mid),
            )
            row.set_active(model["id"] == self._active_model_id)
            self._rows[model["id"]] = row
            self.list_layout.addWidget(row)

        self.list_layout.addStretch(1)

    def _handle_select(self, model_id):
        self.set_active_model(model_id)
        self.on_model_selected.emit(model_id)

    def update_download_progress(self, model_id: str, pct: int):
        if model_id in self._rows:
            self._rows[model_id].set_progress(pct)

    def set_model_status(self, model_id: str, status: str):
        if model_id in self._rows:
            self._rows[model_id].set_status(status)

    def set_active_model(self, model_id: str):
        self._active_model_id = model_id
        for mid, row in self._rows.items():
            row.set_active(mid == model_id)
