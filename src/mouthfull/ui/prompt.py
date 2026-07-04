"""UI Page for Prompt Processor Configuration."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFrame
)
from mouthfull.ui.widgets.toggle_switch import ToggleSwitch

class PromptProcessorPage(QWidget):
    on_settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PromptProcessorPage")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Title
        title = QLabel("Prompt Processor")
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title)

        subtitle = QLabel("Optionally wrap your transcribed speech in a custom prompt before sending it to the LLM.")
        subtitle.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        layout.addWidget(subtitle)

        # Toggle Switch
        toggle_row = QHBoxLayout()
        self.enable_toggle = ToggleSwitch()
        toggle_label = QLabel("Enable Prompt Processor")
        toggle_label.setStyleSheet("color: #e0e0e0; font-size: 16px; font-weight: 500;")
        
        toggle_row.addWidget(self.enable_toggle)
        toggle_row.addWidget(toggle_label)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        # Template Editor
        template_label = QLabel("Prompt Template")
        template_label.setStyleSheet("color: #e0e0e0; font-size: 16px; font-weight: 500;")
        layout.addWidget(template_label)
        
        desc = QLabel("Use {{input}} as the placeholder for your dictated text.")
        desc.setStyleSheet("color: #a0a0a0; font-size: 13px; font-style: italic;")
        layout.addWidget(desc)

        self.template_input = QTextEdit()
        self.template_input.setPlaceholderText("Please respond to this: {{input}}")
        self.template_input.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                color: #ffffff;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                padding: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #6d5cff;
            }
        """)
        layout.addWidget(self.template_input, 1)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_reset = QPushButton("Reset to Default")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #444444; }
        """)
        
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #6d5cff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #7b6bff; }
        """)

        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        # Signals
        self.btn_save.clicked.connect(self._on_save)
        self.btn_reset.clicked.connect(self._on_reset)

    def set_config(self, config_dict):
        """Load state from config."""
        self.enable_toggle.setChecked(config_dict.get("enabled", False))
        self.template_input.setPlainText(config_dict.get("template", "Please process the following dictated text carefully:\n\n{{input}}\n\nProvide the refined text below."))

    def _on_save(self):
        settings = {
            "enabled": self.enable_toggle.isChecked(),
            "template": self.template_input.toPlainText()
        }
        self.on_settings_changed.emit(settings)

    def _on_reset(self):
        self.template_input.setPlainText("Please process the following dictated text carefully:\n\n{{input}}\n\nProvide the refined text below.")
