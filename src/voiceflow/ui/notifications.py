"""
notifications.py — Notification Center
------------------------------------------
A slide-out panel (opened from the header bell icon) listing historical
notifications, distinct from the transient toast popups in widgets/toast.py.
Toasts are for "just happened" events; this panel is the persistent log of
them, similar to the Windows Action Center.

Backend integration
---------------------
Signals (UI -> backend):
    center.on_notification_dismissed(notification_id: str)
    center.on_mark_all_read_clicked()

Methods (backend -> UI):
    center.add_notification(notification: dict)  # {"id","title","message","kind","timestamp"}
    center.set_notifications(list[dict])          # full refresh
    center.set_unread_count(n)                    # updates the bell badge externally (see app.py)
"""
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame

from voiceflow.ui.theme import Colors
from voiceflow.ui.widgets.status_badge import StatusDot


KIND_COLOR = {"success": Colors.SUCCESS, "warning": Colors.WARNING, "error": Colors.ERROR, "info": Colors.INFO}


class NotificationItem(QFrame):
    dismissed = Signal(str)

    def __init__(self, notification: dict, parent=None):
        super().__init__(parent)
        self.notification_id = notification.get("id", "")
        self.setObjectName("NotifItem")
        color = KIND_COLOR.get(notification.get("kind", "info"), Colors.INFO)
        self.setStyleSheet(f"""
            #NotifItem {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_SOFT};
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 8, 10)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(notification.get("title", ""))
        title.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Colors.TEXT_PRIMARY};")
        msg = QLabel(notification.get("message", ""))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 10.5px; color: {Colors.TEXT_SECONDARY};")
        ts = QLabel(notification.get("timestamp", ""))
        ts.setStyleSheet(f"font-size: 9.5px; color: {Colors.TEXT_MUTED};")
        text_col.addWidget(title)
        text_col.addWidget(msg)
        text_col.addWidget(ts)
        layout.addLayout(text_col, 1)

        import qtawesome as qta
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#888"))
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("border: none;")
        close_btn.clicked.connect(lambda: self.dismissed.emit(self.notification_id))
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)


class NotificationCenter(QWidget):
    on_notification_dismissed = Signal(str)
    on_mark_all_read_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setStyleSheet(f"background-color: {Colors.BG_SURFACE}; border-left: 1px solid {Colors.BORDER};")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Notifications")
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch(1)
        mark_btn = QPushButton("Mark all read")
        mark_btn.setProperty("variant", "ghost")
        mark_btn.clicked.connect(self.on_mark_all_read_clicked.emit)
        header.addWidget(mark_btn)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setSpacing(8)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.empty_label = QLabel("You're all caught up.")
        self.empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.insertWidget(0, self.empty_label)

        self._seed_dummy()

    def _seed_dummy(self):
        self.set_notifications([
            {"id": "n1", "title": "Model Installed", "message": "Whisper Medium finished downloading.",
             "kind": "success", "timestamp": "3 min ago"},
            {"id": "n2", "title": "High Latency Detected", "message": "LLM responses are averaging 610ms.",
             "kind": "warning", "timestamp": "22 min ago"},
            {"id": "n3", "title": "Provider Connected", "message": "Anthropic Claude is ready to use.",
             "kind": "success", "timestamp": "1 hr ago"},
        ])

    # ---------------------------------------------------------------- backend API
    def add_notification(self, notification: dict):
        self.empty_label.hide()
        item = NotificationItem(notification)
        item.dismissed.connect(self._remove_item)
        self.list_layout.insertWidget(0, item)

    def set_notifications(self, notifications: list):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        if not notifications:
            self.empty_label.show()
        else:
            self.empty_label.hide()
            for n in notifications:
                item = NotificationItem(n)
                item.dismissed.connect(self._remove_item)
                self.list_layout.insertWidget(self.list_layout.count() - 1, item)

    def _remove_item(self, notification_id: str):
        self.on_notification_dismissed.emit(notification_id)
        for i in range(self.list_layout.count()):
            w = self.list_layout.itemAt(i).widget()
            if isinstance(w, NotificationItem) and w.notification_id == notification_id:
                w.setParent(None)
                break
        if self.list_layout.count() <= 1:
            self.empty_label.show()
