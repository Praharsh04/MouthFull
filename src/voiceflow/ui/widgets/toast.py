"""
Toast / ToastManager
---------------------
In-app notification toasts (bottom-right stack), plus the OS-level
notification hook point for QSystemTrayIcon messages.

Backend integration:
    toast_manager.notify("Model installed", "Whisper Large v3 is ready", "success")
    toast_manager.notify("Connection lost", "Retrying...", "error", duration_ms=6000)
"""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsOpacityEffect

from voiceflow.ui.theme import Colors
from voiceflow.ui.widgets.status_badge import StatusDot




class Toast(QWidget):
    def __init__(self, title: str, message: str, kind: str = "info", parent=None):
        super().__init__(parent)
        self.setFixedWidth(340)
        color = {"success": Colors.SUCCESS, "warning": Colors.WARNING,
                 "error": Colors.ERROR, "info": Colors.INFO}.get(kind, Colors.INFO)

        self.setObjectName("Toast")
        self.setStyleSheet(f"""
            #Toast {{
                background-color: {Colors.BG_SURFACE_ALT};
                border: 1px solid {Colors.BORDER};
                border-left: 3px solid {color};
                border-radius: 10px;
            }}
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 10, 12)
        outer.setSpacing(10)

        import qtawesome as qta
        qta_icons = {"success": "fa5s.check-circle", "warning": "fa5s.exclamation-triangle",
                     "error": "fa5s.times-circle", "info": "fa5s.info-circle"}
        
        icon = QLabel()
        icon.setPixmap(qta.icon(qta_icons.get(kind, "fa5s.info-circle"), color=color).pixmap(16, 16))
        outer.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: 600; color: {Colors.TEXT_PRIMARY}; font-size: 12px;")
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        text_box.addWidget(title_lbl)
        text_box.addWidget(msg_lbl)
        outer.addLayout(text_box, 1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#888"))
        close_btn.setProperty("variant", "ghost")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("border: none;")
        close_btn.clicked.connect(self.dismiss)
        outer.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)
        self._fade_in = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()

    def dismiss(self):
        fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        fade_out.setDuration(180)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(self._remove)
        fade_out.start()
        self._fade_out_ref = fade_out  # keep alive

    def _remove(self):
        parent = self.parent()
        self.setParent(None)
        self.deleteLater()
        if parent and hasattr(parent, "_reflow"):
            parent._reflow()


class ToastManager(QWidget):
    """Overlay container anchored to bottom-right of the host window."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self._host = host
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 16, 16)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        self.setFixedSize(host.size())
        host.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._host and event.type() == event.Type.Resize:
            self.setFixedSize(self._host.size())
        return False

    def notify(self, title: str, message: str, kind: str = "info", duration_ms: int = 4000):
        """Primary backend-facing entry point for showing a toast."""
        toast = Toast(title, message, kind, self)
        self._layout.addWidget(toast)
        self.raise_()
        self.show()
        QTimer.singleShot(duration_ms, toast.dismiss)
        return toast

    def _reflow(self):
        pass  # layout handles it automatically as children are removed
