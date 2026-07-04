"""
theme.py
--------
Central design system for the application: colors, typography, spacing and
the global Qt stylesheet (QSS). Every widget/page pulls its look from here so
the whole app stays visually consistent (PowerToys / Docker Desktop style
"fluent-ish" dark UI with a single accent color).

Nothing here talks to a backend. It's pure presentation.
"""

from PySide6.QtGui import QColor, QFont



class LightColors:
    BG_APP = "#F5F5F5"
    BG_SURFACE = "#FFFFFF"
    BG_SURFACE_ALT = "#F9F9F9"
    BG_CARD = "#F0F0F0"
    BG_CARD_HOVER = "#E8E8E8"
    BG_INPUT = "#FFFFFF"
    BORDER = "#E0E0E0"
    BORDER_SOFT = "#EEEEEE"

    TEXT_PRIMARY = "#1e1f22"
    TEXT_SECONDARY = "#55565a"
    TEXT_MUTED = "#75767a"
    TEXT_DISABLED = "#a7a8ac"

    ACCENT = "#D4AF37"
    ACCENT_HOVER = "#E5C07B"
    ACCENT_PRESSED = "#B3922D"
    ACCENT_SOFT = "#D4AF3726"

    SUCCESS = "#36B359"
    WARNING = "#E69500"
    ERROR = "#CC4444"
    INFO = "#3388EE"

    ORB_IDLE = "#A89A80"
    ORB_LISTENING = "#D4AF37"
    ORB_PROCESSING = "#3388EE"
    ORB_SPEAKING = "#36B359"
    ORB_ERROR = "#CC4444"

class DarkColors:
    BG_APP = "#1e1f22"
    BG_SURFACE = "#242528"
    BG_SURFACE_ALT = "#2a2b2f"
    BG_CARD = "#28292d"
    BG_CARD_HOVER = "#2f3034"
    BG_INPUT = "#1b1c1e"
    BORDER = "#36373b"
    BORDER_SOFT = "#2d2e32"

    TEXT_PRIMARY = "#f2f2f3"
    TEXT_SECONDARY = "#a7a8ac"
    TEXT_MUTED = "#75767a"
    TEXT_DISABLED = "#55565a"

    ACCENT = "#D4AF37"
    ACCENT_HOVER = "#E5C07B"
    ACCENT_PRESSED = "#B3922D"
    ACCENT_SOFT = "#D4AF3726"

    SUCCESS = "#50C878"
    WARNING = "#F5A623"
    ERROR = "#E06666"
    INFO = "#4DA6FF"

    ORB_IDLE = "#8A795D"
    ORB_LISTENING = "#D4AF37"
    ORB_PROCESSING = "#4DA6FF"
    ORB_SPEAKING = "#50C878"
    ORB_ERROR = "#E06666"


class Colors(DarkColors):
    pass

class Metrics:
    RADIUS_SM = 6
    RADIUS_MD = 10
    RADIUS_LG = 16
    RADIUS_PILL = 999
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    NAV_WIDTH = 220
    NAV_WIDTH_COLLAPSED = 64


FONT_FAMILY = "Segoe UI"


def base_font(size=10, weight=QFont.Weight.Normal):
    f = QFont(FONT_FAMILY, size)
    f.setWeight(weight)
    return f


def qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)


def get_app_qss():
    return f"""
* {{
    font-family: "{FONT_FAMILY}";
    outline: none;
}}

QWidget {{
    background-color: transparent;
    color: {Colors.TEXT_PRIMARY};
}}

QMainWindow, #AppRoot {{
    background-color: {Colors.BG_APP};
}}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {Colors.BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_MUTED};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.BORDER};
    border-radius: 4px;
}}

/* ---------- Buttons ---------- */
QPushButton {{
    background-color: {Colors.BG_SURFACE_ALT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Metrics.RADIUS_MD}px;
    padding: 8px 16px;
}}
QPushButton:hover {{
    background-color: {Colors.BG_CARD_HOVER};
    border-color: {Colors.TEXT_MUTED};
}}
QPushButton:pressed {{
    background-color: {Colors.BG_INPUT};
}}
QPushButton:disabled {{
    color: {Colors.TEXT_DISABLED};
    background-color: {Colors.BG_SURFACE};
}}

QPushButton[variant="primary"] {{
    background-color: {Colors.ACCENT};
    border: 1px solid {Colors.ACCENT};
    color: white;
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}
QPushButton[variant="primary"]:pressed {{
    background-color: {Colors.ACCENT_PRESSED};
}}

QPushButton[variant="danger"] {{
    background-color: transparent;
    border: 1px solid {Colors.ERROR};
    color: {Colors.ERROR};
}}
QPushButton[variant="danger"]:hover {{
    background-color: #f0506e22;
}}

QPushButton[variant="ghost"] {{
    background-color: transparent;
    border: 1px solid transparent;
}}
QPushButton[variant="ghost"]:hover {{
    background-color: {Colors.BG_CARD_HOVER};
}}

/* ---------- Inputs ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background-color: {Colors.BG_INPUT};
    border: 1px solid {Colors.BORDER};
    border-radius: {Metrics.RADIUS_MD}px;
    padding: 6px 10px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {Colors.ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_SURFACE_ALT};
    border: 1px solid {Colors.BORDER};
    selection-background-color: {Colors.ACCENT_SOFT};
    outline: none;
    padding: 4px;
}}

/* ---------- Tabs ---------- */
QTabWidget::pane {{
    border: 1px solid {Colors.BORDER_SOFT};
    border-radius: {Metrics.RADIUS_MD}px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {Colors.TEXT_SECONDARY};
    padding: 8px 18px;
    margin-right: 4px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {Colors.TEXT_PRIMARY};
    border-bottom: 2px solid {Colors.ACCENT};
}}
QTabBar::tab:hover {{
    color: {Colors.TEXT_PRIMARY};
}}

/* ---------- Progress ---------- */
QProgressBar {{
    background-color: {Colors.BG_INPUT};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 5px;
}}

/* ---------- Sliders ---------- */
QSlider::groove:horizontal {{
    background: {Colors.BG_INPUT};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {Colors.ACCENT};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {Colors.ACCENT};
    border-radius: 3px;
}}

/* ---------- Lists / Tables ---------- */
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {Colors.BG_SURFACE};
    border: 1px solid {Colors.BORDER_SOFT};
    border-radius: {Metrics.RADIUS_MD}px;
    padding: 4px;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 6px;
    border-radius: {Metrics.RADIUS_SM}px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {Colors.ACCENT_SOFT};
    color: {Colors.TEXT_PRIMARY};
}}
QHeaderView::section {{
    background-color: {Colors.BG_SURFACE_ALT};
    color: {Colors.TEXT_SECONDARY};
    padding: 6px;
    border: none;
    border-bottom: 1px solid {Colors.BORDER};
}}

/* ---------- Checkboxes ---------- */
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {Colors.BORDER};
    background: {Colors.BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
}}

QToolTip {{
    background-color: {Colors.BG_SURFACE_ALT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    padding: 6px 8px;
    border-radius: 6px;
}}

QMenu {{
    background-color: {Colors.BG_SURFACE_ALT};
    border: 1px solid {Colors.BORDER};
    border-radius: {Metrics.RADIUS_MD}px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: {Metrics.RADIUS_SM}px;
}}
QMenu::item:selected {{
    background-color: {Colors.ACCENT_SOFT};
}}
QMenu::separator {{
    height: 1px;
    background: {Colors.BORDER};
    margin: 6px 4px;
}}
"""

APP_QSS = get_app_qss()

def apply_theme(theme_name: str, app=None):
    source = LightColors if theme_name == "light" else DarkColors
    for k, v in source.__dict__.items():
        if not k.startswith("__"):
            setattr(Colors, k, v)
    global APP_QSS
    APP_QSS = get_app_qss()
    if app:
        app.setStyleSheet(APP_QSS)
