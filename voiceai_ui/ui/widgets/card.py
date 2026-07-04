"""
Card
----
A rounded surface container used to group content (Dashboard tiles, settings
sections, model rows, etc). Purely presentational.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QWidget
from PySide6.QtCore import Qt

from ui.theme import Colors


class Card(QFrame):
    def __init__(self, title: str = None, subtitle: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            #Card {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_SOFT};
                border-radius: 14px;
            }}
        """)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 16, 18, 16)
        self._root.setSpacing(10)

        if title:
            header = QHBoxLayout()
            header.setSpacing(4)
            title_wrap = QVBoxLayout()
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
            title_wrap.addWidget(title_lbl)
            if subtitle:
                sub_lbl = QLabel(subtitle)
                sub_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
                title_wrap.addWidget(sub_lbl)
            header.addLayout(title_wrap)
            header.addStretch(1)
            self._header_layout = header
            self._root.addLayout(header)
        else:
            self._header_layout = None

    def add_header_widget(self, widget: QWidget):
        """Add an action widget (button, badge) to the top-right of the card header."""
        if self._header_layout is not None:
            self._header_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight)

    def body_layout(self) -> QVBoxLayout:
        return self._root
