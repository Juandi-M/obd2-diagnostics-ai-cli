from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from app.presentation.qt.style import apply_shadow


class Toast(QFrame):
    def __init__(self, message: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        label = QLabel(message)
        layout.addWidget(label)
        apply_shadow(self, blur=18, y=8)

    def show_at(self, parent: QWidget, duration_ms: int = 2200) -> None:
        self.adjustSize()
        x = parent.width() - self.width() - 24
        y = 24
        self.move(x, y)
        self.show()
        QTimer.singleShot(duration_ms, self.close)

