
import os
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame, QScrollArea, QLineEdit,
    QComboBox, QDialog, QListWidget, QListWidgetItem, QMenu
)

from mouthfull.ui.theme import Colors, Metrics
from mouthfull.ui.widgets.toggle_switch import ToggleSwitch
from mouthfull.ui.widgets.card import Card
from mouthfull.ui.widgets.status_badge import StatusBadge

from mouthfull.utils.installed_apps import get_installed_applications

CONN_META = {
    "untested": ("neutral", "Not Tested"),
    "testing":  ("info",    "Testing…"),
    "success":  ("success", "Connected"),
    "error":    ("error",   "Connection Failed"),
}

# ═══════════════════════════════════════════════════════════════════════
#  App Picker Dialog (Searchable Dropdown)
# ═══════════════════════════════════════════════════════════════════════

class AppPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Application")
        self.setFixedSize(500, 450)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search installed applications or enter custom executable...")
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_INPUT};
                border: 1px solid {Colors.ACCENT};
                border-radius: 8px;
                font-size: 14px; padding: 0 12px;
            }}
        """)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none; outline: none;
            }}
            QListWidget::item {{
                padding: 10px; border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {Colors.ACCENT_SOFT};
            }}
        """)
        self.list_widget.setIconSize(QSize(32, 32))
        layout.addWidget(self.list_widget)

        self.btn_custom = QPushButton("Add Custom Executable")
        self.btn_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom.clicked.connect(self.accept)
        self.btn_custom.setVisible(False)
        layout.addWidget(self.btn_custom)

        self._apps = get_installed_applications()
        self._populate_list("")

        self.search_input.textChanged.connect(self._populate_list)
        self.list_widget.itemActivated.connect(self.accept)

    def _populate_list(self, query: str):
        self.list_widget.clear()
        query = query.lower()
        has_match = False
        for app in self._apps:
            if query in app["name"].lower() or query in app["executable"].lower():
                has_match = True
                item = QListWidgetItem()
                item.setText(f"{app['name']}\n{app['executable']}")
                from PySide6.QtWidgets import QFileIconProvider
                from PySide6.QtCore import QFileInfo
                icon_provider = QFileIconProvider()
                if os.path.exists(app["icon_path"]):
                    icon = icon_provider.icon(QFileInfo(app["icon_path"]))
                    item.setIcon(icon)
                item.setData(Qt.ItemDataRole.UserRole, app)
                self.list_widget.addItem(item)
        self.btn_custom.setVisible(bool(query and not has_match and query.endswith(".exe")))
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def get_selected_app(self):
        if self.list_widget.currentItem() and not self.btn_custom.isVisible():
            return self.list_widget.currentItem().data(Qt.ItemDataRole.UserRole)
        elif self.search_input.text().strip():
            exe = self.search_input.text().strip()
            name = exe.replace(".exe", "").capitalize()
            return {"name": name, "executable": exe, "icon_path": ""}
        return None

# ═══════════════════════════════════════════════════════════════════════
#  Prompt Editor Modal
# ═══════════════════════════════════════════════════════════════════════

class PromptEditorModal(QDialog):
    def __init__(self, title_text, app_data, providers_cache, parent=None, is_default=False):
        super().__init__(parent)
        self.setWindowTitle("Edit Prompt")
        self.setFixedSize(600, 500)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)

        self.app_data = app_data.copy()
        self._providers_cache = providers_cache
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(title_text)
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)

        settings_row = QHBoxLayout()
        prov_lbl = QLabel("Provider:")
        prov_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 600; font-size: 13px;")
        settings_row.addWidget(prov_lbl)
        
        self.provider_combo = QComboBox()
        self.provider_combo.setFixedHeight(36)
        settings_row.addWidget(self.provider_combo, 1)
        
        mod_lbl = QLabel("Model:")
        mod_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 600; font-size: 13px;")
        settings_row.addWidget(mod_lbl)
        
        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(36)
        settings_row.addWidget(self.model_combo, 2)
        
        layout.addLayout(settings_row)
        
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self._update_provider_list()
        
        init_prov = app_data.get("provider")
        init_model = app_data.get("model")
        if init_prov:
            idx = self.provider_combo.findData(init_prov)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        if init_model:
            self.model_combo.setCurrentText(init_model)

        prompt_lbl = QLabel("Prompt Template:")
        prompt_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 600; font-size: 13px;")
        layout.addWidget(prompt_lbl)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlainText(app_data.get("prompt", "Process normally.\n\n{{input}}"))
        self.prompt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Consolas', monospace;
                font-size: 13px;
                padding: 12px;
            }}
            QTextEdit:focus {{ border: 1px solid {Colors.ACCENT}; }}
        """)
        layout.addWidget(self.prompt_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        if not is_default:
            self.btn_delete = QPushButton("Delete")
            self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_delete.setFixedHeight(36)
            self.btn_delete.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {Colors.ERROR};
                    border: 1px solid {Colors.ERROR}; border-radius: 8px; padding: 0 16px;
                }}
                QPushButton:hover {{ background-color: rgba(255, 85, 85, 0.1); }}
            """)
            self.btn_delete.clicked.connect(self.reject_delete)
            btn_row.addWidget(self.btn_delete)
            
        btn_row.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT}; color: white;
                border: none; border-radius: 8px; padding: 0 24px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
        """)
        self.btn_save.clicked.connect(self.accept_save)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)

    def _update_provider_list(self):
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        for p in self._providers_cache:
            self.provider_combo.addItem(p["name"], p["id"])
        self.provider_combo.blockSignals(False)
        self._on_provider_changed()

    def _on_provider_changed(self):
        prov_id = self.provider_combo.currentData()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for p in self._providers_cache:
            if p["id"] == prov_id:
                self.model_combo.addItems(p.get("models", []))
                break
        self.model_combo.blockSignals(False)

    def accept_save(self):
        self.app_data["provider"] = self.provider_combo.currentData()
        self.app_data["model"] = self.model_combo.currentText()
        self.app_data["prompt"] = self.prompt_input.toPlainText().strip()
        self.done(1) # Accept
        
    def reject_delete(self):
        self.done(2) # Delete

# ═══════════════════════════════════════════════════════════════════════
#  App Prompt Card
# ═══════════════════════════════════════════════════════════════════════

class AppPromptCard(QFrame):
    on_delete = Signal(str)
    on_edit = Signal(str, dict)

    def __init__(self, process_name: str, app_data: dict, providers_cache: list, parent=None):
        super().__init__(parent)
        self.process_name = process_name
        self.app_data = app_data
        self.display_name = app_data.get("name", process_name)
        self._providers_cache = providers_cache
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            AppPromptCard {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 12px;
            }}
            AppPromptCard:hover {{
                border: 1px solid {Colors.BORDER};
                background-color: {Colors.BG_SURFACE_ALT};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(12)
        
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        from PySide6.QtWidgets import QFileIconProvider
        from PySide6.QtCore import QFileInfo
        icon = None
        paths = [
            f"C:\\Program Files\\{self.display_name}\\{process_name}",
            f"C:\\Program Files (x86)\\{self.display_name}\\{process_name}",
            f"C:\\Windows\\System32\\{process_name}",
            f"C:\\Windows\\{process_name}"
        ]
        provider = QFileIconProvider()
        for p in paths:
            if os.path.exists(p):
                icon = provider.icon(QFileInfo(p))
                break
        if icon:
            icon_lbl.setPixmap(icon.pixmap(32, 32))
        else:
            icon_lbl.setStyleSheet(f"background: {Colors.BORDER}; border-radius: 6px;")
        
        header.addWidget(icon_lbl)
        
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        name_lbl = QLabel(self.display_name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        exe_lbl = QLabel(self.process_name)
        exe_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-family: monospace;")
        title_col.addWidget(name_lbl)
        title_col.addWidget(exe_lbl)
        header.addLayout(title_col, 1)

        self.btn_menu = QPushButton("⋮")
        self.btn_menu.setFixedSize(24, 24)
        self.btn_menu.setStyleSheet("background: transparent; color: white; border: none; font-size: 18px; font-weight: bold;")
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_menu.clicked.connect(self._show_menu)
        header.addWidget(self.btn_menu)
        
        layout.addLayout(header)

        info_row = QHBoxLayout()
        provider_name = self.app_data.get("provider", "None")
        for p in self._providers_cache:
            if p["id"] == provider_name:
                provider_name = p["name"]
                break
        
        model_name = self.app_data.get("model", "None")
        
        info_lbl = QLabel(f"<span style='color:{Colors.TEXT_MUTED}'>Model:</span> <span style='font-weight:600;'>{provider_name} • {model_name}</span>")
        info_lbl.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_PRIMARY};")
        info_row.addWidget(info_lbl)
        layout.addLayout(info_row)

        prompt_preview = QLabel(self.app_data.get("prompt", "").replace("\n", " ").strip())
        prompt_preview.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-family: monospace;")
        prompt_preview.setWordWrap(True)
        prompt_preview.setFixedHeight(30)
        layout.addWidget(prompt_preview)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._edit()

    def _show_menu(self, event=None):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {Colors.BG_SURFACE_ALT}; border: 1px solid {Colors.BORDER}; border-radius: 6px; }}
            QMenu::item {{ padding: 6px 24px; color: {Colors.TEXT_PRIMARY}; }}
            QMenu::item:selected {{ background-color: {Colors.ACCENT_SOFT}; }}
        """)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(self.mapToGlobal(self.btn_menu.pos() + QSize(0, 24)))
        if action == edit_action:
            self._edit()
        elif action == delete_action:
            self.on_delete.emit(self.process_name)

    def _edit(self):
        modal = PromptEditorModal(f"Edit {self.display_name}", self.app_data, self._providers_cache, self)
        res = modal.exec()
        if res == 1:
            self.app_data = modal.app_data
            self.on_edit.emit(self.process_name, self.app_data)
        elif res == 2:
            self.on_delete.emit(self.process_name)

# ═══════════════════════════════════════════════════════════════════════
#  Provider UI Management
# ═══════════════════════════════════════════════════════════════════════

class _ProviderAccordionItem(QFrame):
    def __init__(self, provider: dict, on_test, on_key_changed, on_save, on_selected, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.provider_id = provider["id"]
        self.on_selected = on_selected
        
        self.setStyleSheet(f"""
            _ProviderAccordionItem {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 8px;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.header = QWidget()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_lay = QHBoxLayout(self.header)
        header_lay.setContentsMargins(12, 12, 12, 12)
        
        name_lbl = QLabel(provider["name"])
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        header_lay.addWidget(name_lbl)
        
        self.badge = StatusBadge()
        header_lay.addWidget(self.badge)
        header_lay.addStretch()
        
        self.chevron = QLabel("▾")
        self.chevron.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 16px;")
        header_lay.addWidget(self.chevron)
        main_layout.addWidget(self.header)
        
        self.body = QWidget()
        body_lay = QVBoxLayout(self.body)
        body_lay.setContentsMargins(12, 0, 12, 12)
        body_lay.setSpacing(8)
        
        if provider.get("requires_key", True):
            key_lbl = QLabel("API Key")
            key_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-weight: 600;")
            body_lay.addWidget(key_lbl)
            
            key_row = QHBoxLayout()
            self.key_input = QLineEdit()
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_input.setPlaceholderText("sk-•••••••••••••••••••••••")
            self.key_input.setFixedHeight(32)
            if provider.get("key_set", False):
                self.key_input.setText("sk-" + "•" * 20)
            self.key_input.textChanged.connect(lambda text: on_key_changed(self.provider_id, text))
            key_row.addWidget(self.key_input, 1)
            
            test_btn = QPushButton("Test")
            test_btn.setFixedSize(60, 32)
            test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            test_btn.clicked.connect(lambda: on_test(self.provider_id))
            key_row.addWidget(test_btn)
            
            save_btn = QPushButton("Save")
            save_btn.setProperty("variant", "primary")
            save_btn.setFixedSize(60, 32)
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: on_save(self.provider_id))
            save_btn.setStyleSheet(f"background-color: {Colors.ACCENT}; color: white; border: none; border-radius: 6px;")
            key_row.addWidget(save_btn)
            
            body_lay.addLayout(key_row)
        else:
            local_lbl = QLabel("No API key required — runs locally")
            local_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px; font-style: italic;")
            body_lay.addWidget(local_lbl)
            
        main_layout.addWidget(self.body)
        self.body.setVisible(False)
        self.expanded = False
        
        self.header.mousePressEvent = self._toggle
        
    def set_connection_status(self, status: str):
        color, text = CONN_META.get(status, CONN_META["untested"])
        self.badge.set_status(color, text)
        
    def _toggle(self, event):
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        self.chevron.setText("▴" if self.expanded else "▾")
        if self.expanded and self.on_selected:
            self.on_selected(self.provider_id)
        self.parent()._on_accordion_toggled(self)

class ProviderManagerModal(QDialog):
    def __init__(self, providers_cache, on_test, on_key_changed, on_save, on_provider_selected, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Providers")
        self.setFixedSize(500, 500)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Global AI Providers")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)
        layout.addSpacing(12)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0,0,0,0)
        self.list_layout.setSpacing(8)
        
        self.panels = []
        for prov in providers_cache:
            panel = _ProviderAccordionItem(prov, on_test, on_key_changed, on_save, on_provider_selected, self)
            self.panels.append(panel)
            self.list_layout.addWidget(panel)
            
        self.list_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER}; border-radius: 8px; }}
            QPushButton:hover {{ background-color: {Colors.BG_SURFACE_ALT}; }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)
        
    def _on_accordion_toggled(self, active_panel):
        if active_panel.expanded:
            for p in self.panels:
                if p != active_panel and p.expanded:
                    p.expanded = False
                    p.body.setVisible(False)
                    p.chevron.setText("▾")
                    
    def set_connection_status(self, provider_id: str, status: str):
        for p in self.panels:
            if p.provider_id == provider_id:
                p.set_connection_status(status)

# ═══════════════════════════════════════════════════════════════════════
#  Main Page
# ═══════════════════════════════════════════════════════════════════════

class _SectionHeader(QWidget):
    def __init__(self, title: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(lbl)
        layout.addStretch()

class PromptProcessorPage(QWidget):
    on_settings_changed = Signal(dict)
    on_test_connection_clicked = Signal(str)
    on_api_key_changed = Signal(str, str)
    on_save_clicked = Signal(str)
    on_provider_selected = Signal(str)
    on_model_variant_changed = Signal(str, str)
    on_add_current_app = Signal()

    def __init__(self):
        super().__init__()
        self._app_prompts = {}
        self._providers_cache = []
        self._default_prompt = {}
        self.provider_modal = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {Colors.BG_APP}; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {Colors.BG_APP};")
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(32, 32, 32, 32)
        self._main_layout.setSpacing(24)

        scroll.setWidget(container)
        outer.addWidget(scroll)

        self._build_header()
        self._build_default_prompt_section()
        self._build_app_prompts_section()

        self._main_layout.addStretch(1)

    def _build_header(self):
        hdr_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("Prompt Processor")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        title_col.addWidget(title)
        
        subtitle = QLabel("Configure intelligent application-aware prompt routing.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 13px;")
        title_col.addWidget(subtitle)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()
        
        self.btn_providers = QPushButton("⚙ AI Providers")
        self.btn_providers.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_providers.setFixedHeight(36)
        self.btn_providers.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SURFACE_ALT}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_SOFT}; border-radius: 8px; padding: 0 16px; font-weight: 600;
            }}
            QPushButton:hover {{ border: 1px solid {Colors.BORDER}; background-color: {Colors.BG_CARD}; }}
        """)
        self.btn_providers.clicked.connect(self._show_provider_modal)
        hdr_row.addWidget(self.btn_providers)
        
        self._main_layout.addLayout(hdr_row)

    def _build_default_prompt_section(self):
        self.default_prompt_card = QFrame()
        self.default_prompt_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.default_prompt_card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_CARD};
                border: 1px dashed {Colors.BORDER};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {Colors.TEXT_MUTED}; }}
        """)
        lay = QVBoxLayout(self.default_prompt_card)
        lay.setContentsMargins(16, 12, 16, 12)
        
        lbl = QLabel("Default Prompt Fallback")
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        lay.addWidget(lbl)
        
        desc = QLabel("Used for all applications that do not have a specific prompt configured. Click to edit.")
        desc.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        lay.addWidget(desc)
        
        self.default_prompt_card.mousePressEvent = self._edit_default_prompt
        self._main_layout.addWidget(self.default_prompt_card)

    def _edit_default_prompt(self, event=None):
        modal = PromptEditorModal("Edit Default Prompt", self._default_prompt, self._providers_cache, self, is_default=True)
        if modal.exec() == 1:
            self._default_prompt = modal.app_data
            self._on_save_all()

    def _build_app_prompts_section(self):
        hdr = _SectionHeader("Application Prompts")
        self._main_layout.addWidget(hdr)

        self._app_prompt_body = QWidget()
        body = QVBoxLayout(self._app_prompt_body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        top_row = QHBoxLayout()
        self.btn_add_app = QPushButton("+ Add Application")
        self.btn_add_app.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_app.setFixedHeight(32)
        self.btn_add_app.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white; border: none; border-radius: 8px; padding: 0 16px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
        """)
        self.btn_add_app.clicked.connect(self._show_add_app_dialog)
        top_row.addWidget(self.btn_add_app)
        top_row.addStretch()
        body.addLayout(top_row)

        self.app_list_layout = QVBoxLayout()
        self.app_list_layout.setSpacing(12)
        body.addLayout(self.app_list_layout)

        self._main_layout.addWidget(self._app_prompt_body)

    # ── API ──────────────────────────────────────────────────────────

    def set_config(self, config_dict):
        self._app_prompts = config_dict.get("app_prompts", {})
        self._default_prompt = {
            "prompt": config_dict.get("default_prompt", ""),
            "provider": config_dict.get("default_provider", ""),
            "model": config_dict.get("default_model", ""),
        }
        self._render_app_list()

    def add_app_prompt(self, process_name: str, display_name: str):
        if process_name not in self._app_prompts:
            self._app_prompts[process_name] = {
                "name": display_name,
                "prompt": "Process normally.\n\n{{input}}",
                "provider": "ollama",
                "model": "llama3"
            }
            self._render_app_list()

    def update_providers(self, providers: list):
        self._providers_cache = providers
        if self.provider_modal:
            pass 
        for i in range(self.app_list_layout.count()):
            widget = self.app_list_layout.itemAt(i).widget()
            if isinstance(widget, AppPromptCard):
                pass 

    def set_connection_status(self, provider_id: str, status: str):
        if self.provider_modal:
            self.provider_modal.set_connection_status(provider_id, status)

    def set_active_provider(self, provider_id: str):
        pass 

    # ── Internal ─────────────────────────────────────────────────────

    def _show_provider_modal(self):
        self.provider_modal = ProviderManagerModal(
            self._providers_cache,
            on_test=self.on_test_connection_clicked.emit,
            on_key_changed=self.on_api_key_changed.emit,
            on_save=self.on_save_clicked.emit,
            on_provider_selected=self.on_provider_selected.emit,
            parent=self
        )
        self.provider_modal.exec()

    def _show_add_app_dialog(self):
        from mouthfull.utils.logger import logger
        logger.info("Add Application button clicked. Opening AppPickerDialog.")
        try:
            dialog = AppPickerDialog(self)
            dialog.move(self.mapToGlobal(self.btn_add_app.pos()) + QSize(0, 30))
            if dialog.exec():
                app_data = dialog.get_selected_app()
                if app_data:
                    exe = app_data["executable"]
                    logger.info(f"Validating selected application: {exe}")
                    if exe not in self._app_prompts:
                        logger.info(f"Adding new application to registry: {exe}")
                        self._app_prompts[exe] = {
                            "name": app_data["name"],
                            "prompt": "Process normally.\n\n{{input}}",
                            "provider": self._providers_cache[0]["id"] if self._providers_cache else "",
                            "model": ""
                        }
                        self._render_app_list()
                        self._on_save_all()
                    else:
                        logger.info(f"Application already exists. Preserving settings and preventing duplicate: {exe}")
                        # Could scroll to it here if we wanted to
        except Exception as e:
            logger.exception(f"Exception during Add Application workflow: {e}")

    def _render_app_list(self):
        from mouthfull.utils.logger import logger
        logger.debug("Refreshing application UI list.")
        while self.app_list_layout.count() > 0:
            item = self.app_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for process_name, data in self._app_prompts.items():
            card = AppPromptCard(process_name, data, self._providers_cache)
            card.on_delete.connect(self._on_delete_app)
            card.on_edit.connect(self._on_edit_app)
            self.app_list_layout.addWidget(card)

    def _on_delete_app(self, process_name: str):
        if process_name in self._app_prompts:
            del self._app_prompts[process_name]
            self._render_app_list()
            self._on_save_all()
            
    def _on_edit_app(self, process_name: str, app_data: dict):
        self._app_prompts[process_name] = app_data
        self._render_app_list()
        self._on_save_all()

    def _on_save_all(self):
        from mouthfull.utils.logger import logger
        logger.info("Save started for Prompt Processor settings.")
        try:
            settings = {
                "enabled": True, 
                "default_prompt": self._default_prompt.get("prompt", ""),
                "default_provider": self._default_prompt.get("provider", ""),
                "default_model": self._default_prompt.get("model", ""),
                "app_prompts": self._app_prompts,
            }
            self.on_settings_changed.emit(settings)
            logger.info("Save completed successfully.")
        except Exception as e:
            logger.exception(f"Exception during save: {e}")
