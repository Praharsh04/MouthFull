"""
dashboard.py — Dashboard Page
------------------------------
Landing page: current status, big start/stop control, live mic level,
quick stats, and a recent activity feed (recent transcriptions/commands).

Backend integration
---------------------
Signals (UI -> backend):
    dashboard.on_start_clicked()          -- Signal(), toggle button pressed to start
    dashboard.on_stop_clicked()           -- Signal(), toggle button pressed to stop
    dashboard.on_quick_action(str)        -- Signal(str), e.g. "push_to_talk", "clear_history"

Methods (backend -> UI):
    dashboard.update_status(state)                    # idle|listening|processing|speaking|error
    dashboard.update_audio_level(level)                # 0.0-1.0
    dashboard.update_stats(words, commands, uptime)    # session counters
    dashboard.add_activity_entry(text, kind, timestamp)
    dashboard.set_backend_connected(bool)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QListWidget, QListWidgetItem, QScrollArea
)

from ui.theme import Colors
from ui.widgets import Card, StatusBadge, AudioLevelMeter

STATE_META = {
    "idle": ("neutral", "Idle"),
    "listening": ("info", "Listening"),
    "processing": ("warning", "Processing"),
    "speaking": ("success", "Speaking"),
    "error": ("error", "Error"),
}


class StatCard(Card):
    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent=parent)
        self.body_layout().setContentsMargins(16, 14, 16, 14)
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        self.body_layout().addWidget(self.value_label)
        self.body_layout().addWidget(label_widget)

    def set_value(self, value: str):
        self.value_label.setText(value)


class DashboardPage(QWidget):
    # ---- backend-facing signals ----
    on_start_clicked = Signal()
    on_stop_clicked = Signal()
    on_quick_action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_active = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)
        self.backend_badge = StatusBadge("Backend Disconnected", "neutral")
        header.addWidget(self.backend_badge)
        outer.addLayout(header)

        # ---------------- Main status card ----------------
        status_card = Card()
        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)

        left_col = QVBoxLayout()
        self.state_badge = StatusBadge("Idle", "neutral")
        left_col.addWidget(self.state_badge)

        self.big_label = QLabel("Ready when you are")
        self.big_label.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        left_col.addWidget(self.big_label)

        self.hotkey_hint = QLabel("Press  Ctrl+Shift+Space  or click Start to begin dictating")
        self.hotkey_hint.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        left_col.addWidget(self.hotkey_hint)

        self.meter = AudioLevelMeter()
        left_col.addSpacing(6)
        left_col.addWidget(self.meter)

        status_layout.addLayout(left_col, 1)

        self.toggle_btn = QPushButton("▶  Start Listening")
        self.toggle_btn.setProperty("variant", "primary")
        self.toggle_btn.setFixedSize(180, 46)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        status_layout.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        status_card.body_layout().addLayout(status_layout)
        outer.addWidget(status_card)

        # ---------------- Stat tiles ----------------
        stats_grid = QGridLayout()
        stats_grid.setSpacing(14)
        self.stat_words = StatCard("Words Transcribed (session)", "0")
        self.stat_commands = StatCard("Commands Executed", "0")
        self.stat_uptime = StatCard("Session Uptime", "00:00:00")
        self.stat_model = StatCard("Active Speech Model", "Whisper Small (en)")
        stats_grid.addWidget(self.stat_words, 0, 0)
        stats_grid.addWidget(self.stat_commands, 0, 1)
        stats_grid.addWidget(self.stat_uptime, 0, 2)
        stats_grid.addWidget(self.stat_model, 0, 3)
        outer.addLayout(stats_grid)

        # ---------------- Quick actions ----------------
        quick_card = Card(title="Quick Actions")
        actions_row = QHBoxLayout()
        for label, action_id in [
            ("🔇 Mute Mic", "mute_mic"),
            ("🗑️ Clear History", "clear_history"),
            ("🧪 Test Injection", "test_injection"),
            ("🔄 Reload Model", "reload_model"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, a=action_id: self.on_quick_action.emit(a))
            actions_row.addWidget(btn)
        actions_row.addStretch(1)
        quick_card.body_layout().addLayout(actions_row)
        outer.addWidget(quick_card)

        # ---------------- Recent activity ----------------
        activity_card = Card(title="Recent Activity")
        self.activity_list = QListWidget()
        self.activity_list.setMinimumHeight(200)
        activity_card.body_layout().addWidget(self.activity_list)
        outer.addWidget(activity_card, 1)

        self._seed_dummy_data()

    # ---------------------------------------------------------------- internal
    def _on_toggle_clicked(self):
        self._is_active = not self._is_active
        if self._is_active:
            self.toggle_btn.setText("⏸  Stop Listening")
            self.toggle_btn.setProperty("variant", "danger")
            self.on_start_clicked.emit()
        else:
            self.toggle_btn.setText("▶  Start Listening")
            self.toggle_btn.setProperty("variant", "primary")
            self.on_stop_clicked.emit()
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)

    def _seed_dummy_data(self):
        for text, kind, ts in [
            ("\"Open a new email to Sarah about the quarterly report\"", "command", "2 min ago"),
            ("\"The meeting has been moved to 3 PM tomorrow, please update...\"", "transcript", "6 min ago"),
            ("Switched speech model to Whisper Small (en)", "system", "18 min ago"),
            ("\"Undo that last sentence\"", "command", "22 min ago"),
            ("LLM provider switched to Claude Sonnet 5", "system", "1 hr ago"),
        ]:
            self.add_activity_entry(text, kind, ts)

    # ---------------------------------------------------------------- backend API
    def update_status(self, state: str):
        kind, label = STATE_META.get(state, ("neutral", "Idle"))
        self.state_badge.set_status(kind, label)
        messages = {
            "idle": "Ready when you are",
            "listening": "Listening for speech…",
            "processing": "Transcribing and thinking…",
            "speaking": "Injecting text…",
            "error": "Something went wrong",
        }
        self.big_label.setText(messages.get(state, "Ready when you are"))
        self.meter.set_active(state == "listening")

    def update_audio_level(self, level: float):
        self.meter.update_audio_level(level)

    def update_stats(self, words: int = None, commands: int = None, uptime: str = None, model: str = None):
        if words is not None:
            self.stat_words.set_value(str(words))
        if commands is not None:
            self.stat_commands.set_value(str(commands))
        if uptime is not None:
            self.stat_uptime.set_value(uptime)
        if model is not None:
            self.stat_model.set_value(model)

    def add_activity_entry(self, text: str, kind: str = "transcript", timestamp: str = "now"):
        icons = {"command": "⚡", "transcript": "📝", "system": "⚙️", "error": "❌"}
        item = QListWidgetItem(f"{icons.get(kind, '•')}  {text}   —   {timestamp}")
        self.activity_list.insertItem(0, item)

    def set_backend_connected(self, connected: bool):
        self.backend_badge.set_status("success" if connected else "neutral",
                                       "Backend Connected" if connected else "Backend Disconnected")

    def set_running_silent(self, running: bool):
        """Reflect an externally-driven start/stop without re-emitting click signals."""
        self._is_active = running
        self.toggle_btn.setText("⏸  Stop Listening" if running else "▶  Start Listening")
