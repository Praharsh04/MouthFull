"""
llms.py — LLM Providers Page
------------------------------
Configure and switch between LLM providers used for post-processing /
command interpretation (Docker Desktop "settings list" style layout).

Backend integration
---------------------
Signals (UI -> backend):
    llms_page.on_provider_selected(provider_id: str)
    llms_page.on_test_connection_clicked(provider_id: str)
    llms_page.on_api_key_changed(provider_id: str, key: str)
    llms_page.on_model_variant_changed(provider_id: str, model_name: str)
    llms_page.on_save_clicked(provider_id: str)

Methods (backend -> UI):
    llms_page.update_providers(providers: list[dict])
    llms_page.set_connection_status(provider_id, status)   # untested|testing|success|error
    llms_page.set_active_provider(provider_id)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QScrollArea, QFrame, QRadioButton, QButtonGroup
)

from voiceflow.ui.theme import Colors
from voiceflow.ui.widgets import Card, StatusBadge

CONN_META = {
    "untested": ("neutral", "Not Tested"),
    "testing": ("info", "Testing…"),
    "success": ("success", "Connected"),
    "error": ("error", "Connection Failed"),
}

AVAILABLE_PROVIDERS = [
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "desc": "Run open models locally — no API key required",
        "models": ["llama3", "llama3.1:8b", "mistral", "phi3"],
        "requires_key": False
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "desc": "GPT-4o / GPT-4o mini via API",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "requires_key": True
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "desc": "Claude Sonnet / Opus / Haiku via API",
        "models": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "requires_key": True
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "desc": "Gemini 1.5 Pro / Flash via API",
        "models": ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest"],
        "requires_key": True
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "desc": "Access multiple models (Llama 3, Claude, GPT) via single API",
        "models": ["meta-llama/llama-3-8b-instruct", "meta-llama/llama-3-70b-instruct", "anthropic/claude-3.5-sonnet"],
        "requires_key": True
    },
    {
        "id": "custom",
        "name": "Custom API Endpoint",
        "desc": "Use an OpenAI-compatible endpoint (e.g. vLLM, LMStudio)",
        "models": ["custom-model"],
        "requires_key": True
    }
]


class ProviderRow(Card):
    def __init__(self, provider: dict, group: QButtonGroup, on_select, on_test, on_key_changed,
                 on_model_changed, on_save, parent=None):
        super().__init__(parent=parent)
        self.provider_id = provider["id"]
        self._on_test = on_test
        self._on_key_changed = on_key_changed
        self._on_model_changed = on_model_changed
        self._on_save = on_save
        self.body_layout().setContentsMargins(16, 14, 16, 14)

        top = QHBoxLayout()
        self.radio = QRadioButton()
        self.radio.setChecked(provider.get("active", False))
        self.radio.toggled.connect(lambda checked: checked and on_select(self.provider_id))
        group.addButton(self.radio)
        top.addWidget(self.radio)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        name_lbl = QLabel(provider["name"])
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        desc_lbl = QLabel(provider["desc"])
        desc_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10.5px;")
        title_col.addWidget(name_lbl)
        title_col.addWidget(desc_lbl)
        top.addLayout(title_col, 1)

        self.status_badge = StatusBadge(*reversed(CONN_META[provider.get("status", "untested")]))
        top.addWidget(self.status_badge)
        self.body_layout().addLayout(top)

        # Config row: API key + model dropdown + test/save buttons
        config_row = QHBoxLayout()
        if provider["requires_key"]:
            self.key_input = QLineEdit()
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_input.setPlaceholderText("API key (sk-••••••••••••)")
            if provider.get("key_set", False):
                self.key_input.setText("sk-" + "•" * 20)
            self.key_input.textChanged.connect(lambda text: self._on_key_changed(self.provider_id, text))
            config_row.addWidget(self.key_input, 1)
        else:
            self.key_input = None
            local_lbl = QLabel("No API key required (local inference)")
            local_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10.5px; font-style: italic;")
            config_row.addWidget(local_lbl, 1)

        self.model_combo = QComboBox()
        self.model_combo.addItems(provider.get("models", []))
        if "current_model" in provider and provider["current_model"] in provider["models"]:
            self.model_combo.setCurrentText(provider["current_model"])
        self.model_combo.currentTextChanged.connect(lambda text: self._on_model_changed(self.provider_id, text))
        self.model_combo.setFixedWidth(180)
        config_row.addWidget(self.model_combo)

        test_btn = QPushButton("Test")
        test_btn.setFixedWidth(70)
        test_btn.clicked.connect(lambda: self._on_test(self.provider_id))
        config_row.addWidget(test_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("variant", "primary")
        save_btn.setFixedWidth(70)
        save_btn.clicked.connect(lambda: self._on_save(self.provider_id))
        config_row.addWidget(save_btn)

        self.body_layout().addLayout(config_row)

    def set_connection_status(self, status: str):
        kind, label = CONN_META.get(status, ("neutral", "Unknown"))
        self.status_badge.set_status(kind, label)

    def set_active(self, active: bool):
        self.radio.blockSignals(True)
        self.radio.setChecked(active)
        self.radio.blockSignals(False)


class LLMProvidersPage(QWidget):
    on_provider_selected = Signal(str)
    on_test_connection_clicked = Signal(str)
    on_api_key_changed = Signal(str, str)
    on_model_variant_changed = Signal(str, str)
    on_save_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("LLM Providers")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)
        add_btn = QPushButton("+ Add Custom Provider")
        header.addWidget(add_btn)
        outer.addLayout(header)

        subtitle = QLabel("Choose the language model used to clean up transcripts and interpret voice commands.")
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

        # Initial populate will be done by UIBridge
        # self.update_providers(AVAILABLE_PROVIDERS)

    def update_providers(self, providers: list):
        for row in self._rows.values():
            row.setParent(None)
        self._rows.clear()
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for provider in providers:
            row = ProviderRow(
                provider, self._group,
                on_select=self.on_provider_selected.emit,
                on_test=self.on_test_connection_clicked.emit,
                on_key_changed=self.on_api_key_changed.emit,
                on_model_changed=self.on_model_variant_changed.emit,
                on_save=self.on_save_clicked.emit,
            )
            self._rows[provider["id"]] = row
            self.list_layout.addWidget(row)
        self.list_layout.addStretch(1)

    def set_connection_status(self, provider_id: str, status: str):
        if provider_id in self._rows:
            self._rows[provider_id].set_connection_status(status)

    def set_active_provider(self, provider_id: str):
        for pid, row in self._rows.items():
            row.set_active(pid == provider_id)
