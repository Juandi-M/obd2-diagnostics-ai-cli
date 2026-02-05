from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QVBoxLayout, QWidget


PAGE_MAX_WIDTH = 1400


@lru_cache(maxsize=1)
def app_stylesheet() -> str:
    path = Path(__file__).with_name("resources") / "app.qss"
    return path.read_text(encoding="utf-8")


def apply_shadow(widget: QWidget, blur: int = 18, y: int = 6) -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y)
    shadow.setColor(QColor(109, 108, 255, 50))
    widget.setGraphicsEffect(shadow)
    return shadow


def panel_layout(padding: int = 16) -> Tuple[QFrame, QVBoxLayout]:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(10)
    apply_shadow(panel, blur=16, y=5)
    return panel, layout

