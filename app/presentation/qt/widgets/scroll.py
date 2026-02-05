from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget


class VerticalScrollArea(QScrollArea):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignTop)

    def setWidget(self, widget: QWidget) -> None:  # noqa: N802 - Qt naming
        super().setWidget(widget)
        if widget is None:
            return
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = widget.layout()
        if layout:
            layout.setAlignment(Qt.AlignTop)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        widget = self.widget()
        if widget:
            width = self.viewport().width()
            widget.setMinimumWidth(width)
            widget.setMaximumWidth(width)

