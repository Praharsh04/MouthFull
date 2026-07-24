"""UI Page for unified Prompt Processor + AI Provider Configuration.

Embedded provider management and application-specific prompt configuration.
"""

import os
from PySide6.QtCore import Signal, Qt, QSize, QSortFilterProxyModel, QAbstractListModel
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame, QScrollArea, QLineEdit,
    QComboBox, QRadioButton, QButtonGroup, QDialog,
    QListWidget, QListWidgetItem,
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
    """A Raycast-style searchable list of installed applications."""
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

        # Search bar
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

        # List
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

        self._apps = get_installed_applications()
        self._populate_list("")

        self.search_input.textChanged.connect(self._populate_list)
        self.list_widget.itemActivated.connect(self.accept)
        
        # Add custom exe button
        self.btn_custom = QPushButton("Add Custom Executable")
        self.btn_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom.clicked.connect(self.accept)
        self.btn_custom.setVisible(False)
        layout.addWidget(self.btn_custom)

    def _populate_list(self, query: str):
        self.list_widget.clear()
        query = query.lower()
        
        has_match = False
        for app in self._apps:
            if query in app["name"].lower() or query in app["executable"].lower():
                has_match = True
                item = QListWidgetItem()
                item.setText(f"{app['name']}\n{app['executable']}")
                
                # Attempt to extract icon
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
#  App Prompt Card
# ═══════════════════════════════════════════════════════════════════════

class AppPromptCard(Card):
    """A card for editing a specific application's prompt and provider."""

    on_delete = Signal(str)
    on_save = Signal(str, dict)

    def __init__(self, process_name: str, app_data: dict, providers_cache: list, parent=None):
        super().__init__(parent=parent)
        self.process_name = process_name
        self.display_name = app_data.get("name", process_name)
        self._providers_cache = providers_cache
        
        self.setStyleSheet(f"""
            #Card {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 12px;
            }}
        """)
        
        layout = self.body_layout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Header (Icon, Name, Exe, Delete) ──
        header = QHBoxLayout()
        header.setSpacing(12)
        
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        from PySide6.QtWidgets import QFileIconProvider
        from PySide6.QtCore import QFileInfo
        # Attempt to find icon if it's a known exe or we can locate it
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
        title_col.setSpacing(2)
        name_lbl = QLabel(self.display_name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        exe_lbl = QLabel(self.process_name)
        exe_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-family: monospace;")
        title_col.addWidget(name_lbl)
        title_col.addWidget(exe_lbl)
        header.addLayout(title_col, 1)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {Colors.TEXT_MUTED};
                border: 1px solid {Colors.BORDER}; border-radius: 6px; padding: 4px 10px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 85, 85, 0.1); color: {Colors.ERROR}; border-color: {Colors.ERROR}; }}
        """)
        self.btn_delete.clicked.connect(lambda: self.on_delete.emit(self.process_name))
        header.addWidget(self.btn_delete)
        layout.addLayout(header)

        # ── Settings (Provider, Model) ──
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)
        
        prov_lbl = QLabel("Provider:")
        prov_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 600; font-size: 12px;")
        settings_row.addWidget(prov_lbl)
        
        self.provider_combo = QComboBox()
        self.provider_combo.setFixedHeight(30)
        self.provider_combo.setMinimumWidth(120)
        settings_row.addWidget(self.provider_combo)
        
        mod_lbl = QLabel("Model:")
        mod_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 600; font-size: 12px;")
        settings_row.addWidget(mod_lbl)
        
        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(30)
        self.model_combo.setMinimumWidth(180)
        settings_row.addWidget(self.model_combo, 1)
        
        layout.addLayout(settings_row)
        
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        
        # Populate providers
        self._update_provider_list()
        
        # Set initial values
        init_prov = app_data.get("provider")
        init_model = app_data.get("model")
        if init_prov:
            idx = self.provider_combo.findData(init_prov)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        if init_model:
            self.model_combo.setCurrentText(init_model)

        # ── Prompt Editor ──
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlainText(app_data.get("prompt", "Process normally.\\n\\n{{input}}"))
        self.prompt_input.setPlaceholderText("Enter the prompt template for this application...")
        self.prompt_input.setFixedHeight(80)
        self.prompt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_INPUT};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Consolas', monospace;
                font-size: 13px;
                padding: 10px;
            }}
            QTextEdit:focus {{ border: 1px solid {Colors.ACCENT}; }}
        """)
        layout.addWidget(self.prompt_input)

    def _update_provider_list(self):
        curr_prov = self.provider_combo.currentData()
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        
        for p in self._providers_cache:
            self.provider_combo.addItem(p["name"], p["id"])
            
        if curr_prov:
            idx = self.provider_combo.findData(curr_prov)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.blockSignals(False)
        self._on_provider_changed()

    def _on_provider_changed(self):
        prov_id = self.provider_combo.currentData()
        curr_model = self.model_combo.currentText()
        
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for p in self._providers_cache:
            if p["id"] == prov_id:
                self.model_combo.addItems(p.get("models", []))
                break
                
        if curr_model:
            idx = self.model_combo.findText(curr_model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        self.model_combo.blockSignals(False)

    def get_data(self) -> dict:
        return {
            "name": self.display_name,
            "prompt": self.prompt_input.toPlainText(),
            "provider": self.provider_combo.currentData(),
            "model": self.model_combo.currentText(),
        }


# ═══════════════════════════════════════════════════════════════════════
#  Inline Global Provider Panel (Unchanged design, kept global)
# ═══════════════════════════════════════════════════════════════════════

class _ProviderPanel(QFrame):
    """Compact, collapsible panel for global LLM credentials."""
    def __init__(
        self, provider: dict, on_test, on_key_changed, on_save, parent=None
    ):
        super().__init__(parent)
        self.provider_id = provider["id"]
        self._on_test = on_test
        self._on_key_changed = on_key_changed
        self._on_save = on_save
        self._expanded = False

        self.setObjectName("ProviderPanel")
        self.setStyleSheet(f"""
            #ProviderPanel {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 10px;
            }}
            #ProviderPanel[expanded="true"] {{
                border-color: {Colors.ACCENT}55;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(0)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(10)

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        name_lbl = QLabel(provider["name"])
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        desc_lbl = QLabel(provider.get("desc", ""))
        desc_lbl.setStyleSheet(f"font-size: 10.5px; color: {Colors.TEXT_MUTED};")
        info_col.addWidget(name_lbl)
        info_col.addWidget(desc_lbl)
        header.addLayout(info_col, 1)

        self.status_badge = StatusBadge(*reversed(CONN_META[provider.get("status", "untested")]))
        header.addWidget(self.status_badge)

        self._chevron = QPushButton("▸")
        self._chevron.setFixedSize(24, 24)
        self._chevron.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chevron.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {Colors.TEXT_MUTED}; font-size: 14px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background: {Colors.BG_CARD_HOVER}; }}
        """)
        self._chevron.clicked.connect(self.toggle_expanded)
        header.addWidget(self._chevron)

        root.addLayout(header)

        # ── Body ──
        self._body = QWidget()
        self._body.setVisible(False)
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(14, 10, 0, 4)
        body_lay.setSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {Colors.BORDER_SOFT}; max-height: 1px;")
        body_lay.addWidget(sep)

        if provider.get("requires_key", True):
            key_row = QHBoxLayout()
            key_row.setSpacing(8)
            key_lbl = QLabel("API Key")
            key_lbl.setFixedWidth(60)
            key_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-weight: 600;")
            key_row.addWidget(key_lbl)

            self.key_input = QLineEdit()
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_input.setPlaceholderText("sk-•••••••••••••••••••••••")
            self.key_input.setFixedHeight(32)
            if provider.get("key_set", False):
                self.key_input.setText("sk-" + "•" * 20)
            self.key_input.textChanged.connect(lambda text: self._on_key_changed(self.provider_id, text))
            key_row.addWidget(self.key_input, 1)
            
            test_btn = QPushButton("Test")
            test_btn.setFixedSize(60, 32)
            test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            test_btn.clicked.connect(lambda: self._on_test(self.provider_id))
            key_row.addWidget(test_btn)

            save_btn = QPushButton("Save")
            save_btn.setProperty("variant", "primary")
            save_btn.setFixedSize(60, 32)
            save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            save_btn.clicked.connect(lambda: self._on_save(self.provider_id))
            key_row.addWidget(save_btn)

            body_lay.addLayout(key_row)
        else:
            local_lbl = QLabel("No API key required — runs locally")
            local_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10.5px; font-style: italic;")
            body_lay.addWidget(local_lbl)

        root.addWidget(self._body)

    def toggle_expanded(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._chevron.setText("▾" if self._expanded else "▸")
        self.setProperty("expanded", "true" if self._expanded else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def collapse(self):
        if self._expanded:
            self.toggle_expanded()

    def set_connection_status(self, status: str):
        kind, label = CONN_META.get(status, ("neutral", "Unknown"))
        self.status_badge.set_status(kind, label)


class _SectionHeader(QWidget):
    """Clickable section label with a chevron."""
    toggled = Signal(bool)

    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._expanded = expanded
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._chevron = QLabel("▾" if expanded else "▸")
        self._chevron.setFixedWidth(16)
        self._chevron.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        lay.addWidget(self._chevron)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {Colors.TEXT_SECONDARY};"
            f" text-transform: uppercase; letter-spacing: 0.5px;"
        )
        lay.addWidget(lbl)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {Colors.BORDER_SOFT}; max-height: 1px;")
        lay.addWidget(line, 1)

    def mousePressEvent(self, event):
        self._expanded = not self._expanded
        self._chevron.setText("▾" if self._expanded else "▸")
        self.toggled.emit(self._expanded)
        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════════
#  Main Page
# ═══════════════════════════════════════════════════════════════════════

class PromptProcessorPage(QWidget):
    """Application-driven Prompt Processor + Global AI Credentials."""

    on_settings_changed = Signal(dict)
    
    # Bridge compatibility aliases (ignored internally for routing, but kept for signature)
    on_add_current_app = Signal()
    on_provider_selected = Signal(str)
    on_test_connection_clicked = Signal(str)
    on_api_key_changed = Signal(str, str)
    on_model_variant_changed = Signal(str, str)
    on_save_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PromptProcessorPage")
        self._app_prompts = {}
        self._provider_panels: dict[str, _ProviderPanel] = {}
        self._providers_cache = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setContentsMargins(32, 28, 32, 28)
        self._main_layout.setSpacing(0)

        scroll.setWidget(container)
        outer.addWidget(scroll)

        self._build_header()
        self._build_app_prompts_section()
        self._build_provider_section()
        self._build_save_bar()

        self._main_layout.addStretch(1)

    def _build_header(self):
        title = QLabel("Prompt Processor")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        self._main_layout.addWidget(title)
        
        subtitle = QLabel("Configure application-specific prompts and select AI models per app.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; margin-bottom: 6px;")
        self._main_layout.addWidget(subtitle)
        self._main_layout.addSpacing(16)

    def _build_app_prompts_section(self):
        hdr = _SectionHeader("Application Prompts")
        self._main_layout.addWidget(hdr)

        self._app_prompt_body = QWidget()
        body = QVBoxLayout(self._app_prompt_body)
        body.setContentsMargins(0, 6, 0, 0)
        body.setSpacing(12)

        top_row = QHBoxLayout()
        desc = QLabel("If no prompt exists for an application, AI processing is bypassed.")
        desc.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        top_row.addWidget(desc, 1)

        self.btn_add_app = QPushButton("+ Add Application")
        self.btn_add_app.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_app.setFixedHeight(30)
        self.btn_add_app.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_SURFACE_ALT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_CARD_HOVER}; }}
        """)
        self.btn_add_app.clicked.connect(self._show_add_app_dialog)
        top_row.addWidget(self.btn_add_app)
        body.addLayout(top_row)

        self._app_list_container = QWidget()
        self._app_list_container.setStyleSheet("background: transparent;")
        self.app_list_layout = QVBoxLayout(self._app_list_container)
        self.app_list_layout.setSpacing(16)
        self.app_list_layout.setContentsMargins(0, 0, 0, 0)
        self.app_list_layout.addStretch()
        body.addWidget(self._app_list_container)

        self._main_layout.addWidget(self._app_prompt_body)
        self._main_layout.addSpacing(16)
        hdr.toggled.connect(self._app_prompt_body.setVisible)

    def _build_provider_section(self):
        hdr = _SectionHeader("Global AI Credentials")
        self._main_layout.addWidget(hdr)

        self._provider_body = QWidget()
        body = QVBoxLayout(self._provider_body)
        body.setContentsMargins(0, 6, 0, 0)
        body.setSpacing(6)

        desc = QLabel("Configure credentials centrally. Individual apps reference these providers without duplicating keys.")
        desc.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        body.addWidget(desc)

        self._provider_list_container = QWidget()
        self._provider_list_container.setStyleSheet("background: transparent;")
        self.provider_list_layout = QVBoxLayout(self._provider_list_container)
        self.provider_list_layout.setSpacing(6)
        self.provider_list_layout.setContentsMargins(0, 0, 0, 0)
        body.addWidget(self._provider_list_container)

        self._main_layout.addWidget(self._provider_body)
        self._main_layout.addSpacing(12)
        hdr.toggled.connect(self._provider_body.setVisible)

    def _build_save_bar(self):
        row = QHBoxLayout()
        row.addStretch()
        self.btn_save_all = QPushButton("Save All Settings")
        self.btn_save_all.setProperty("variant", "primary")
        self.btn_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_all.setFixedHeight(36)
        self.btn_save_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: white; border: none; border-radius: 8px;
                padding: 0 24px; font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
        """)
        row.addWidget(self.btn_save_all)
        self._main_layout.addLayout(row)
        self.btn_save_all.clicked.connect(self._on_save_all)

    # ── API ──────────────────────────────────────────────────────────

    def set_config(self, config_dict):
        self._app_prompts = config_dict.get("app_prompts", {})
        self._render_app_list()

    def add_app_prompt(self, process_name: str, display_name: str):
        # Kept for bridge compatibility if needed
        if process_name not in self._app_prompts:
            self._app_prompts[process_name] = {
                "name": display_name,
                "prompt": "Process normally.\\n\\n{{input}}",
                "provider": "ollama",
                "model": "llama3"
            }
            self._render_app_list()

    def update_providers(self, providers: list):
        self._providers_cache = providers
        
        # Rebuild Global Credential panels
        for panel in self._provider_panels.values():
            panel.setParent(None)
        self._provider_panels.clear()
        while self.provider_list_layout.count() > 0:
            item = self.provider_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for prov in providers:
            panel = _ProviderPanel(
                prov,
                on_test=self.on_test_connection_clicked.emit,
                on_key_changed=self.on_api_key_changed.emit,
                on_save=self.on_save_clicked.emit,
            )
            self._provider_panels[prov["id"]] = panel
            self.provider_list_layout.addWidget(panel)

        # Notify app cards
        for i in range(self.app_list_layout.count() - 1):
            widget = self.app_list_layout.itemAt(i).widget()
            if isinstance(widget, AppPromptCard):
                widget._update_provider_list()

    def set_connection_status(self, provider_id: str, status: str):
        if provider_id in self._provider_panels:
            self._provider_panels[provider_id].set_connection_status(status)

    def set_active_provider(self, provider_id: str):
        pass # Ignored: provider selection is now per-app, not global radio buttons

    # ── Internal ─────────────────────────────────────────────────────

    def _show_add_app_dialog(self):
        dialog = AppPickerDialog(self)
        dialog.move(self.mapToGlobal(self.btn_add_app.pos()) + QSize(0, 30))
        if dialog.exec():
            app_data = dialog.get_selected_app()
            if app_data:
                exe = app_data["executable"]
                if exe not in self._app_prompts:
                    self._app_prompts[exe] = {
                        "name": app_data["name"],
                        "prompt": "Process normally.\\n\\n{{input}}",
                        "provider": "ollama",
                        "model": "llama3"
                    }
                    self._render_app_list()
                    self._on_save_all()

    def _render_app_list(self):
        while self.app_list_layout.count() > 1:
            item = self.app_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for process_name, data in self._app_prompts.items():
            card = AppPromptCard(process_name, data, self._providers_cache)
            card.on_delete.connect(self._on_delete_app)
            self.app_list_layout.insertWidget(self.app_list_layout.count() - 1, card)

    def _on_delete_app(self, process_name: str):
        if process_name in self._app_prompts:
            del self._app_prompts[process_name]
            self._render_app_list()
            self._on_save_all()

    def _on_save_all(self):
        # Gather data from all cards
        for i in range(self.app_list_layout.count() - 1):
            widget = self.app_list_layout.itemAt(i).widget()
            if isinstance(widget, AppPromptCard):
                self._app_prompts[widget.process_name] = widget.get_data()

        settings = {
            "enabled": True, # Always true in backend for schema compat, ignored by logic
            "default_prompt": "", # Removed from UI, pass empty to satisfy schema backward compat
            "app_prompts": self._app_prompts,
        }
        self.on_settings_changed.emit(settings)
