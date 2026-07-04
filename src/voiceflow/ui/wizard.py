"""
wizard.py — Setup Wizard
--------------------------
First-run onboarding flow: Welcome -> Permissions -> Hotkey Setup ->
Model Selection -> Finish. Built as a custom QWizard-like flow (QStackedWidget
+ step indicator) so styling stays consistent with the rest of the app.

Backend integration
---------------------
Signals (UI -> backend):
    wizard.on_permission_requested(permission: str)   # "microphone" | "accessibility"
    wizard.on_model_chosen(model_id: str)
    wizard.on_hotkey_configured(combo: str)
    wizard.finished.connect(...)                       # Qt built-in, emitted on Finish
    wizard.skipped_signal                              # emitted if user clicks "Skip Setup"

Methods (backend -> UI):
    wizard.set_permission_status(permission: str, granted: bool)
    wizard.set_download_progress(pct: int)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QStackedWidget, QRadioButton, QButtonGroup, QProgressBar, QFrame
)

from voiceflow.ui.theme import Colors, APP_QSS
from voiceflow.ui.widgets import HotkeyRecorder, StatusBadge


class StepIndicator(QWidget):
    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self._steps = steps
        self._current = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._dots = []
        for i, _ in enumerate(steps):
            dot = QLabel()
            dot.setFixedSize(28, 4)
            self._dots.append(dot)
            layout.addWidget(dot)
        layout.addStretch(1)
        self._refresh()

    def set_step(self, index: int):
        self._current = index
        self._refresh()

    def _refresh(self):
        for i, dot in enumerate(self._dots):
            color = Colors.ACCENT if i <= self._current else Colors.BORDER
            dot.setStyleSheet(f"background-color: {color}; border-radius: 2px;")


class WizardPage(QWidget):
    """Base class for a single wizard step: emoji/icon, title, body, then
    subclasses add their own interactive content in the middle section."""

    def __init__(self, icon: str, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        import qtawesome as qta
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color="#D4AF37").pixmap(40, 40))
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_lbl)

        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setWordWrap(True)
        subtitle_lbl.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(subtitle_lbl)

        layout.addSpacing(14)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        layout.addLayout(self.content_layout)
        layout.addStretch(1)


class WelcomePage(WizardPage):
    def __init__(self, parent=None):
        super().__init__("fa5s.comments", "Welcome to VoiceFlow AI",
                          "Turn your voice into text and commands anywhere on Windows. "
                          "This quick setup will get your microphone, hotkeys, and AI models ready to go.",
                          parent)


class PermissionsPage(WizardPage):
    permission_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__("fa5s.lock", "Grant Permissions",
                          "VoiceFlow AI needs the following permissions to capture your voice and type on your behalf.",
                          parent)
        self.badges = {}
        for perm_id, label, granted in [
            ("microphone", "Microphone access", False),
            ("accessibility", "Accessibility (text injection)", False),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12.5px;")
            row.addWidget(lbl)
            row.addStretch(1)
            badge = StatusBadge("Not Granted", "neutral")
            self.badges[perm_id] = badge
            row.addWidget(badge)
            grant_btn = QPushButton("Grant")
            grant_btn.setFixedWidth(80)
            grant_btn.clicked.connect(lambda checked, p=perm_id: self.permission_requested.emit(p))
            row.addWidget(grant_btn)
            self.content_layout.addLayout(row)

    def set_permission_status(self, permission: str, granted: bool):
        if permission in self.badges:
            self.badges[permission].set_status("success" if granted else "neutral",
                                                 "Granted" if granted else "Not Granted")


class HotkeyPage(WizardPage):
    hotkey_configured = Signal(str)

    def __init__(self, parent=None):
        super().__init__("fa5s.keyboard", "Choose Your Hotkey",
                          "Pick a global shortcut to start and stop dictation from anywhere.",
                          parent)
        row = QHBoxLayout()
        lbl = QLabel("Start/stop listening:")
        lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12.5px;")
        row.addWidget(lbl)
        row.addStretch(1)
        self.recorder = HotkeyRecorder("Ctrl+Shift+Space")
        self.recorder.hotkey_changed.connect(self.hotkey_configured.emit)
        row.addWidget(self.recorder)
        self.content_layout.addLayout(row)


class ModelSelectionPage(WizardPage):
    model_chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__("fa5s.microphone", "Choose a Speech Model",
                          "Smaller models respond faster; larger models are more accurate. You can change this anytime.",
                          parent)
        self.group = QButtonGroup(self)
        for model_id, label, desc, checked in [
            ("whisper-tiny", "Fast", "Whisper Tiny — lowest latency, good for short commands", False),
            ("whisper-small-en", "Balanced (Recommended)", "Whisper Small (English) — best balance of speed and accuracy", True),
            ("whisper-large-v3", "Accurate", "Whisper Large v3 — highest accuracy, requires more resources", False),
        ]:
            radio = QRadioButton(f"{label}")
            radio.setChecked(checked)
            radio.toggled.connect(lambda ch, m=model_id: ch and self.model_chosen.emit(m))
            self.group.addButton(radio)
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10.5px; margin-left: 24px;")
            self.content_layout.addWidget(radio)
            self.content_layout.addWidget(desc_lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        self.content_layout.addWidget(self.progress)

    def set_download_progress(self, pct: int):
        self.progress.setVisible(0 <= pct < 100)
        self.progress.setValue(pct)


class FinishPage(WizardPage):
    def __init__(self, parent=None):
        super().__init__("fa5s.glass-cheers", "You're All Set!",
                          "VoiceFlow AI is ready to use. Try pressing your hotkey now, or open the dashboard "
                          "to explore more settings and speech models.",
                          parent)


class SetupWizard(QDialog):
    skipped_signal = Signal()
    on_permission_requested = Signal(str)
    on_model_chosen = Signal(str)
    on_hotkey_configured = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoiceFlow AI — Setup")
        self.setFixedSize(560, 480)
        self.setStyleSheet(APP_QSS + f"QDialog {{ background-color: {Colors.BG_APP}; }}")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedWidget()
        self.welcome = WelcomePage()
        self.permissions = PermissionsPage()
        self.hotkey = HotkeyPage()
        self.model = ModelSelectionPage()
        self.finish = FinishPage()

        for page in (self.welcome, self.permissions, self.hotkey, self.model, self.finish):
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        # wire child signals up to wizard-level backend-facing signals
        self.permissions.permission_requested.connect(self.on_permission_requested.emit)
        self.hotkey.hotkey_configured.connect(self.on_hotkey_configured.emit)
        self.model.model_chosen.connect(self.on_model_chosen.emit)

        footer = QFrame()
        footer.setStyleSheet(f"background-color: {Colors.BG_SURFACE}; border-top: 1px solid {Colors.BORDER_SOFT};")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 14, 24, 14)

        self.step_indicator = StepIndicator(["welcome", "permissions", "hotkey", "model", "finish"])
        footer_layout.addWidget(self.step_indicator)
        footer_layout.addStretch(1)

        self.skip_btn = QPushButton("Skip Setup")
        self.skip_btn.setProperty("variant", "ghost")
        self.skip_btn.clicked.connect(self._on_skip)
        footer_layout.addWidget(self.skip_btn)

        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._go_back)
        footer_layout.addWidget(self.back_btn)

        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("variant", "primary")
        self.next_btn.clicked.connect(self._go_next)
        footer_layout.addWidget(self.next_btn)

        root.addWidget(footer)

        self._index = 0
        self._update_nav()

    def _go_next(self):
        if self._index < self.stack.count() - 1:
            self._index += 1
            self.stack.setCurrentIndex(self._index)
            self.step_indicator.set_step(self._index)
            self._update_nav()
        else:
            self.accept()

    def _go_back(self):
        if self._index > 0:
            self._index -= 1
            self.stack.setCurrentIndex(self._index)
            self.step_indicator.set_step(self._index)
            self._update_nav()

    def _update_nav(self):
        self.back_btn.setEnabled(self._index > 0)
        is_last = self._index == self.stack.count() - 1
        self.next_btn.setText("Get Started" if is_last else "Next")
        self.skip_btn.setVisible(not is_last)

    def _on_skip(self):
        self.skipped_signal.emit()
        self.reject()

    # ---------------------------------------------------------------- backend API
    def set_permission_status(self, permission: str, granted: bool):
        self.permissions.set_permission_status(permission, granted)

    def set_download_progress(self, pct: int):
        self.model.set_download_progress(pct)
