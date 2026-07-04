"""
settings.py — Settings Page
------------------------------
Tabbed settings: General, Hotkeys, Audio, Advanced. Mirrors PowerToys-style
settings organization.

Backend integration
---------------------
Signals (UI -> backend):
    settings_page.on_setting_changed(key: str, value)   # generic catch-all, e.g. "launch_at_startup", True
    settings_page.on_hotkey_changed(action: str, combo: str)  # e.g. "toggle_listen", "Ctrl+Shift+Space"
    settings_page.on_audio_device_changed(device_name: str)
    settings_page.on_reset_defaults_clicked()

Methods (backend -> UI):
    settings_page.set_setting(key, value)          # reflect backend-driven state
    settings_page.set_audio_devices(list[str])
    settings_page.set_hotkey(action, combo)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QComboBox, QSlider, QScrollArea, QFrame
)

from mouthfull.ui.theme import Colors
from mouthfull.ui.widgets import Card, ToggleSwitch, HotkeyRecorder


class SettingRow(QWidget):
    """A single label(+description) / control row used throughout settings tabs."""

    def __init__(self, label: str, control: QWidget, description: str = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 12.5px; color: {Colors.TEXT_PRIMARY}; font-weight: 500;")
        text_col.addWidget(lbl)
        if description:
            desc = QLabel(description)
            desc.setStyleSheet(f"font-size: 10.5px; color: {Colors.TEXT_MUTED};")
            desc.setWordWrap(True)
            text_col.addWidget(desc)

        layout.addLayout(text_col, 1)
        layout.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


def _divider():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background-color: {Colors.BORDER_SOFT}; max-height: 1px; border: none;")
    return line


class GeneralTab(QWidget):
    setting_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        card = Card()
        body = card.body_layout()

        self.launch_toggle = ToggleSwitch(checked=True)
        self.launch_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("launch_at_startup", v))
        body.addWidget(SettingRow("Launch at Windows startup", self.launch_toggle,
                                   "Start MouthFull AI automatically when you sign in."))
        body.addWidget(_divider())

        self.tray_toggle = ToggleSwitch(checked=True)
        self.tray_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("minimize_to_tray", v))
        body.addWidget(SettingRow("Minimize to system tray", self.tray_toggle,
                                   "Keep running in the background when the window is closed."))
        body.addWidget(_divider())

        self.orb_toggle = ToggleSwitch(checked=True)
        self.orb_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("show_floating_orb", v))
        body.addWidget(SettingRow("Show floating AI orb", self.orb_toggle,
                                   "Display a small floating indicator while MouthFull AI is active."))
        body.addWidget(_divider())

        self.updates_toggle = ToggleSwitch(checked=True)
        self.updates_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("auto_check_updates", v))
        body.addWidget(SettingRow("Automatically check for updates", self.updates_toggle))
        body.addWidget(_divider())

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (default)", "Light", "Match Windows Theme"])
        self.theme_combo.setFixedWidth(180)
        self.theme_combo.currentTextChanged.connect(lambda v: self.setting_changed.emit("theme", v))
        body.addWidget(SettingRow("App theme", self.theme_combo))

        layout.addWidget(card)
        layout.addStretch(1)


class HotkeysTab(QWidget):
    hotkey_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        card = Card()
        body = card.body_layout()

        self.recorders = {}
        actions = [
            ("toggle_listen", "Start / stop listening", "Ctrl+Shift+Space"),
            ("push_to_talk", "Push-to-talk (hold)", "Ctrl+Shift+V"),
            ("mute_mic", "Mute microphone", "Ctrl+Shift+M"),
            ("cancel_dictation", "Cancel current dictation", "Escape"),
            ("open_dashboard", "Open dashboard", "Ctrl+Alt+D"),
        ]
        for i, (action_id, label, default) in enumerate(actions):
            rec = HotkeyRecorder(default)
            rec.hotkey_changed.connect(lambda combo, aid=action_id: self.hotkey_changed.emit(aid, combo))
            self.recorders[action_id] = rec
            body.addWidget(SettingRow(label, rec))
            if i < len(actions) - 1:
                body.addWidget(_divider())

        layout.addWidget(card)
        layout.addStretch(1)

    def set_hotkey(self, action: str, combo: str):
        if action in self.recorders:
            self.recorders[action].set_hotkey(combo)


class AudioTab(QWidget):
    setting_changed = Signal(str, object)
    audio_device_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        card = Card()
        body = card.body_layout()

        self.device_combo = QComboBox()
        self.device_combo.addItems([
            "Default Audio Device"
        ])
        self.device_combo.setFixedWidth(240)
        self.device_combo.currentTextChanged.connect(self.audio_device_changed.emit)
        body.addWidget(SettingRow("Input device", self.device_combo))
        body.addWidget(_divider())

        gain_slider = QSlider(Qt.Orientation.Horizontal)
        gain_slider.setRange(0, 100)
        gain_slider.setValue(70)
        gain_slider.setFixedWidth(200)
        gain_slider.valueChanged.connect(lambda v: self.setting_changed.emit("input_gain", v))
        body.addWidget(SettingRow("Input gain", gain_slider))
        body.addWidget(_divider())

        self.vad_toggle = ToggleSwitch(checked=True)
        self.vad_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("voice_activity_detection", v))
        body.addWidget(SettingRow("Voice activity detection", self.vad_toggle,
                                   "Automatically detect speech start/stop instead of relying only on hotkeys."))
        body.addWidget(_divider())

        self.noise_toggle = ToggleSwitch(checked=True)
        self.noise_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("noise_suppression", v))
        body.addWidget(SettingRow("Noise suppression", self.noise_toggle))
        body.addWidget(_divider())

        self.silence_combo = QComboBox()
        self.silence_combo.addItems(["0.5s", "1.0s", "1.5s", "2.0s"])
        self.silence_combo.setCurrentText("1.0s")
        self.silence_combo.setFixedWidth(100)
        self.silence_combo.currentTextChanged.connect(lambda v: self.setting_changed.emit("silence_timeout", v))
        body.addWidget(SettingRow("Silence timeout before auto-stop", self.silence_combo))

        layout.addWidget(card)
        layout.addStretch(1)

    def set_audio_devices(self, devices: list):
        current = self.device_combo.currentText()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        if current in devices:
            self.device_combo.setCurrentText(current)
        self.device_combo.blockSignals(False)


class AdvancedTab(QWidget):
    setting_changed = Signal(str, object)
    reset_defaults_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        card = Card()
        body = card.body_layout()

        self.debug_toggle = ToggleSwitch(checked=False)
        self.debug_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("debug_logging", v))
        body.addWidget(SettingRow("Enable debug logging", self.debug_toggle,
                                   "Verbose logs for troubleshooting; may impact performance."))
        body.addWidget(_divider())

        self.telemetry_toggle = ToggleSwitch(checked=False)
        self.telemetry_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("send_telemetry", v))
        body.addWidget(SettingRow("Send anonymous usage statistics", self.telemetry_toggle))
        body.addWidget(_divider())

        self.gpu_toggle = ToggleSwitch(checked=True)
        self.gpu_toggle.toggled_signal.connect(lambda v: self.setting_changed.emit("prefer_gpu", v))
        body.addWidget(SettingRow("Prefer GPU acceleration when available", self.gpu_toggle))
        body.addWidget(_divider())

        buttons_row = QHBoxLayout()
        export_btn = QPushButton("Export Diagnostics")
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setProperty("variant", "danger")
        reset_btn.clicked.connect(self.reset_defaults_clicked.emit)
        buttons_row.addWidget(export_btn)
        buttons_row.addWidget(reset_btn)
        buttons_row.addStretch(1)
        body.addLayout(buttons_row)

        layout.addWidget(card)
        layout.addStretch(1)


class SettingsPage(QWidget):
    on_setting_changed = Signal(str, object)
    on_hotkey_changed = Signal(str, str)
    on_audio_device_changed = Signal(str)
    on_reset_defaults_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        tabs = QTabWidget()
        self.general_tab = GeneralTab()
        self.hotkeys_tab = HotkeysTab()
        self.audio_tab = AudioTab()
        self.advanced_tab = AdvancedTab()

        tabs.addTab(self.general_tab, "General")
        tabs.addTab(self.hotkeys_tab, "Hotkeys")
        tabs.addTab(self.audio_tab, "Audio")
        tabs.addTab(self.advanced_tab, "Advanced")

        scroll.setWidget(tabs)
        outer.addWidget(scroll, 1)

        # Forward child-tab signals to the page-level, backend-facing signals
        self.general_tab.setting_changed.connect(self.on_setting_changed.emit)
        self.hotkeys_tab.hotkey_changed.connect(self.on_hotkey_changed.emit)
        self.audio_tab.setting_changed.connect(self.on_setting_changed.emit)
        self.audio_tab.audio_device_changed.connect(self.on_audio_device_changed.emit)
        self.advanced_tab.setting_changed.connect(self.on_setting_changed.emit)
        self.advanced_tab.reset_defaults_clicked.connect(self.on_reset_defaults_clicked.emit)

    # ---------------------------------------------------------------- backend API
    def set_setting(self, key: str, value):
        """Reflect a backend-driven setting change in the appropriate control."""
        mapping = {
            "launch_at_startup": self.general_tab.launch_toggle,
            "minimize_to_tray": self.general_tab.tray_toggle,
            "show_floating_orb": self.general_tab.orb_toggle,
            "auto_check_updates": self.general_tab.updates_toggle,
            "voice_activity_detection": self.audio_tab.vad_toggle,
            "noise_suppression": self.audio_tab.noise_toggle,
            "debug_logging": self.advanced_tab.debug_toggle,
            "send_telemetry": self.advanced_tab.telemetry_toggle,
            "prefer_gpu": self.advanced_tab.gpu_toggle,
        }
        widget = mapping.get(key)
        if isinstance(widget, ToggleSwitch):
            widget.set_checked_silent(bool(value))
        elif key == "input_gain":
            self.audio_tab.findChild(QSlider).blockSignals(True)
            self.audio_tab.findChild(QSlider).setValue(int(value))
            self.audio_tab.findChild(QSlider).blockSignals(False)
        elif key == "theme":
            combo = self.general_tab.theme_combo
            combo.blockSignals(True)
            if value == "dark":
                combo.setCurrentText("Dark (default)")
            elif value == "light":
                combo.setCurrentText("Light")
            elif value == "match":
                combo.setCurrentText("Match Windows Theme")
            combo.blockSignals(False)
        elif key == "silence_timeout":
            combo = self.audio_tab.silence_combo
            combo.blockSignals(True)
            combo.setCurrentText(f"{value / 1000.0}s")
            combo.blockSignals(False)

    def set_audio_devices(self, devices: list):
        self.audio_tab.set_audio_devices(devices)

    def set_hotkey(self, action: str, combo: str):
        self.hotkeys_tab.set_hotkey(action, combo)
