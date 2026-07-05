"""UI Page for Prompt Processor Configuration."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFrame, QScrollArea, QLineEdit
)
from mouthfull.ui.theme import Colors
from mouthfull.ui.widgets.toggle_switch import ToggleSwitch
from mouthfull.ui.widgets.card import Card

class AppPromptRow(Card):
    """A row for editing a specific application's prompt."""
    
    on_delete = Signal(str)  # process_name
    on_save = Signal(str, str, str)  # process_name, display_name, prompt

    def __init__(self, process_name: str, display_name: str, prompt: str, parent=None):
        super().__init__(title=display_name, subtitle=process_name, parent=parent)
        self.process_name = process_name
        self.display_name = display_name
        
        # Action Buttons in header
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.ERROR};
                border: 1px solid {Colors.ERROR};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 85, 85, 0.1); }}
        """)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
        """)
        
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_save)
        
        header_widget = QWidget()
        header_widget.setLayout(btn_layout)
        self.add_header_widget(header_widget)
        
        # Editor
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlainText(prompt)
        self.prompt_input.setPlaceholderText(f"Prompt for {display_name}...")
        self.prompt_input.setFixedHeight(80)
        self.prompt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Consolas', monospace;
                font-size: 13px;
                padding: 8px;
            }}
            QTextEdit:focus {{ border: 1px solid {Colors.ACCENT}; }}
        """)
        self.body_layout().addWidget(self.prompt_input)
        
        self.btn_delete.clicked.connect(lambda: self.on_delete.emit(self.process_name))
        self.btn_save.clicked.connect(lambda: self.on_save.emit(self.process_name, self.display_name, self.prompt_input.toPlainText()))


class PromptProcessorPage(QWidget):
    on_settings_changed = Signal(dict)
    on_add_current_app = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PromptProcessorPage")
        self._app_prompts = {}
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Title
        title = QLabel("Application Prompt Manager")
        title.setObjectName("PageTitle")
        title.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)

        subtitle = QLabel("Automatically apply different prompts based on the active application.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 14px;")
        layout.addWidget(subtitle)

        # Toggle Switch
        toggle_row = QHBoxLayout()
        self.enable_toggle = ToggleSwitch()
        toggle_label = QLabel("Enable Prompt Processor")
        toggle_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 500;")
        
        toggle_row.addWidget(self.enable_toggle)
        toggle_row.addWidget(toggle_label)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        # Default Prompt
        default_label = QLabel("Default Prompt")
        default_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 500;")
        layout.addWidget(default_label)
        
        desc = QLabel("Used whenever no application-specific prompt exists.")
        desc.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 13px; font-style: italic;")
        layout.addWidget(desc)

        self.default_template_input = QTextEdit()
        self.default_template_input.setFixedHeight(100)
        self.default_template_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Consolas', monospace;
                font-size: 14px;
                padding: 12px;
            }}
            QTextEdit:focus {{ border: 1px solid {Colors.ACCENT}; }}
        """)
        layout.addWidget(self.default_template_input)

        # Application Specific Prompts Header
        app_header_layout = QHBoxLayout()
        app_label = QLabel("Application Prompts")
        app_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 500;")
        app_header_layout.addWidget(app_label)
        app_header_layout.addStretch()
        
        self.btn_add_app = QPushButton("+ Add Current Application")
        self.btn_add_app.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_CARD};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BORDER_SOFT}; }}
        """)
        self.btn_add_app.clicked.connect(self.on_add_current_app.emit)
        app_header_layout.addWidget(self.btn_add_app)
        layout.addLayout(app_header_layout)

        # Scroll Area for Apps
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.app_list_layout = QVBoxLayout(container)
        self.app_list_layout.setSpacing(12)
        self.app_list_layout.setContentsMargins(0, 0, 8, 0)
        self.app_list_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        self.btn_save_all = QPushButton("Save All Settings")
        self.btn_save_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
        """)
        btn_row.addWidget(self.btn_save_all)
        layout.addLayout(btn_row)

        self.btn_save_all.clicked.connect(self._on_save_all)
        self.enable_toggle.toggled_signal.connect(lambda _: self._on_save_all())

    def set_config(self, config_dict):
        """Load state from config."""
        self.enable_toggle.set_checked_silent(config_dict.get("enabled", False))
        self.default_template_input.setPlainText(config_dict.get("default_prompt", "Process normally.\n\n{{input}}"))
        
        self._app_prompts = config_dict.get("app_prompts", {})
        self._render_app_list()

    def add_app_prompt(self, process_name: str, display_name: str):
        if process_name not in self._app_prompts:
            self._app_prompts[process_name] = {
                "name": display_name,
                "prompt": "Process normally.\n\n{{input}}"
            }
            self._render_app_list()

    def _render_app_list(self):
        # Clear existing
        while self.app_list_layout.count() > 1:  # Keep stretch at end
            item = self.app_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add items
        for process_name, data in self._app_prompts.items():
            row = AppPromptRow(process_name, data["name"], data["prompt"])
            row.on_delete.connect(self._on_delete_app)
            row.on_save.connect(self._on_save_app)
            self.app_list_layout.insertWidget(self.app_list_layout.count() - 1, row)

    def _on_delete_app(self, process_name: str):
        if process_name in self._app_prompts:
            del self._app_prompts[process_name]
            self._render_app_list()
            self._on_save_all()
            
    def _on_save_app(self, process_name: str, display_name: str, prompt: str):
        self._app_prompts[process_name] = {
            "name": display_name,
            "prompt": prompt
        }
        self._on_save_all()

    def _on_save_all(self):
        # Read back inputs to dict just in case they haven't pressed individual save buttons
        for i in range(self.app_list_layout.count() - 1):
            widget = self.app_list_layout.itemAt(i).widget()
            if isinstance(widget, AppPromptRow):
                self._app_prompts[widget.process_name]["prompt"] = widget.prompt_input.toPlainText()

        settings = {
            "enabled": self.enable_toggle.isChecked(),
            "default_prompt": self.default_template_input.toPlainText(),
            "app_prompts": self._app_prompts
        }
        self.on_settings_changed.emit(settings)
