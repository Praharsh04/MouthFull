"""
logs.py — Log Viewer Page
---------------------------
Scrollable, filterable, color-coded log viewer, similar to Docker Desktop's
container logs pane.

Backend integration
---------------------
Signals (UI -> backend):
    logs_page.on_clear_logs_clicked()
    logs_page.on_export_logs_clicked()
    logs_page.on_level_filter_changed(level: str)      # "ALL"|"DEBUG"|"INFO"|"WARNING"|"ERROR"

Methods (backend -> UI):
    logs_page.update_logs(entries: list[dict])   # full refresh: [{"time","level","source","message"}]
    logs_page.append_log(entry: dict)            # append single new line (streaming)
    logs_page.set_autoscroll(bool)
"""
import random
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)

from ui.theme import Colors

LEVEL_COLORS = {
    "DEBUG": Colors.TEXT_MUTED,
    "INFO": Colors.INFO,
    "WARNING": Colors.WARNING,
    "ERROR": Colors.ERROR,
}

DUMMY_SOURCES = ["hotkey.manager", "audio.recorder", "stt.whisper", "llm.anthropic", "injector.win32", "eventbus"]
DUMMY_MESSAGES = [
    ("INFO", "hotkey.manager", "Global hotkey Ctrl+Shift+Space registered successfully"),
    ("INFO", "audio.recorder", "Microphone stream opened (48kHz, mono)"),
    ("DEBUG", "stt.whisper", "Loaded model 'whisper-small-en' onto device: cpu"),
    ("INFO", "eventbus", "Published event: recording.started"),
    ("INFO", "audio.recorder", "Captured 3.2s of audio (avg level: 0.41)"),
    ("DEBUG", "stt.whisper", "Transcription completed in 412ms"),
    ("INFO", "llm.anthropic", "Sent 1 message to claude-sonnet-5 (142 tokens)"),
    ("WARNING", "llm.anthropic", "Response latency exceeded 500ms threshold (612ms)"),
    ("INFO", "injector.win32", "Injected 87 characters into focused window 'Outlook'"),
    ("ERROR", "stt.whisper", "CUDA not available, falling back to CPU inference"),
    ("INFO", "eventbus", "Published event: transcription.completed"),
    ("DEBUG", "hotkey.manager", "Key release detected, stopping capture"),
]


class LogsPage(QWidget):
    on_clear_logs_clicked = Signal()
    on_export_logs_clicked = Signal()
    on_level_filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries = []
        self._autoscroll = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Logs")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Filter logs…")
        self.search_box.setFixedWidth(220)
        self.search_box.textChanged.connect(self._apply_filters)
        header.addWidget(self.search_box)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self._on_level_changed)
        header.addWidget(self.level_combo)

        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.toggled.connect(self.set_autoscroll)
        header.addWidget(self.autoscroll_check)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.on_export_logs_clicked.emit)
        header.addWidget(export_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("variant", "danger")
        clear_btn.clicked.connect(self._on_clear)
        header.addWidget(clear_btn)

        outer.addLayout(header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "Level", "Source", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setFont_ = None
        outer.addWidget(self.table, 1)

        self._seed_dummy_logs()

    def _seed_dummy_logs(self):
        now = datetime.now()
        entries = []
        for i, (level, source, msg) in enumerate(DUMMY_MESSAGES):
            ts = now - timedelta(seconds=(len(DUMMY_MESSAGES) - i) * 7)
            entries.append({"time": ts.strftime("%H:%M:%S"), "level": level, "source": source, "message": msg})
        self.update_logs(entries)

    def _row_widgets(self, entry: dict):
        time_item = QTableWidgetItem(entry.get("time", ""))
        level = entry.get("level", "INFO")
        level_item = QTableWidgetItem(level)
        level_item.setForeground(QColor(LEVEL_COLORS.get(level, Colors.TEXT_PRIMARY)))
        source_item = QTableWidgetItem(entry.get("source", ""))
        source_item.setForeground(QColor(Colors.TEXT_SECONDARY))
        message_item = QTableWidgetItem(entry.get("message", ""))
        for item in (time_item, level_item, source_item, message_item):
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return [time_item, level_item, source_item, message_item]

    def _apply_filters(self):
        query = self.search_box.text().lower().strip()
        level_filter = self.level_combo.currentText()
        for row in range(self.table.rowCount()):
            entry = self._all_entries[row] if row < len(self._all_entries) else {}
            matches_query = query in entry.get("message", "").lower() or query in entry.get("source", "").lower()
            matches_level = level_filter == "ALL" or entry.get("level") == level_filter
            self.table.setRowHidden(row, not (matches_query and matches_level))

    def _on_level_changed(self, level: str):
        self._apply_filters()
        self.on_level_filter_changed.emit(level)

    def _on_clear(self):
        self.table.setRowCount(0)
        self._all_entries.clear()
        self.on_clear_logs_clicked.emit()

    # ---------------------------------------------------------------- backend API
    def update_logs(self, entries: list):
        self._all_entries = list(entries)
        self.table.setRowCount(0)
        for entry in entries:
            self._insert_row(entry)
        self._apply_filters()
        if self._autoscroll:
            self.table.scrollToBottom()

    def append_log(self, entry: dict):
        self._all_entries.append(entry)
        self._insert_row(entry)
        self._apply_filters()
        if self._autoscroll:
            self.table.scrollToBottom()

    def _insert_row(self, entry: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, item in enumerate(self._row_widgets(entry)):
            self.table.setItem(row, col, item)

    def set_autoscroll(self, enabled: bool):
        self._autoscroll = enabled
        self.autoscroll_check.blockSignals(True)
        self.autoscroll_check.setChecked(enabled)
        self.autoscroll_check.blockSignals(False)
