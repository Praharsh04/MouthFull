"""
HotkeyRecorder
--------------
A click-to-record field for capturing a global hotkey combination, similar to
PowerToys' shortcut editors.

Backend integration:
    recorder.hotkey_changed.connect(your_on_hotkey_changed)  # str, e.g. "Ctrl+Shift+Space"
    recorder.set_hotkey("Ctrl+Shift+Space")   # to reflect saved/backend state
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QPushButton

from ui.theme import Colors

MODIFIER_KEYS = {Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta}


class HotkeyRecorder(QPushButton):
    hotkey_changed = Signal(str)

    def __init__(self, initial: str = "Ctrl+Shift+Space", parent=None):
        super().__init__(initial, parent)
        self._recording = False
        self._value = initial
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setMinimumWidth(180)
        self.clicked.connect(self._start_recording)
        self._apply_style()

    def _apply_style(self):
        border = Colors.ACCENT if self._recording else Colors.BORDER
        bg = Colors.BG_INPUT
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-family: Consolas, monospace;
                font-weight: 600;
                padding: 4px 12px;
            }}
        """)

    def _start_recording(self):
        self._recording = True
        self.setText("Press keys...")
        self._apply_style()
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self._recording:
            return super().keyPressEvent(event)

        key = event.key()
        if key in (Qt.Key.Key_Escape,):
            self._recording = False
            self.setText(self._value)
            self._apply_style()
            self.releaseKeyboard()
            return

        if key in MODIFIER_KEYS:
            return  # wait for a full combo

        seq_parts = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            seq_parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            seq_parts.append("Shift")
        if mods & Qt.KeyboardModifier.AltModifier:
            seq_parts.append("Alt")
        if mods & Qt.KeyboardModifier.MetaModifier:
            seq_parts.append("Win")

        key_name = QKeySequence(key).toString()
        seq_parts.append(key_name)
        combo = "+".join(seq_parts)

        self._value = combo
        self._recording = False
        self.setText(combo)
        self._apply_style()
        self.releaseKeyboard()
        self.hotkey_changed.emit(combo)

    def set_hotkey(self, combo: str):
        """Backend -> UI: reflect a hotkey value without triggering recording."""
        self._value = combo
        self.setText(combo)

    def current_hotkey(self) -> str:
        return self._value
