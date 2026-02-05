from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import panel_layout
from app.presentation.qt.widgets.status import add_status_badge


class StartPage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_start: Callable[[], None],
        on_language_change: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state
        self.on_language_change = on_language_change
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        panel, panel_layout_ = panel_layout(padding=26)
        panel.setMaximumWidth(560)
        title = QLabel(gui_t(self.state, "app_title"))
        title.setObjectName("title")
        subtitle = QLabel(gui_t(self.state, "subtitle"))
        subtitle.setObjectName("subtitle")
        panel_layout_.addWidget(title)
        panel_layout_.addWidget(subtitle)

        lang_row = QHBoxLayout()
        lang_label = QLabel(gui_t(self.state, "language"))
        lang_label.setObjectName("chip")
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("langSelect")
        self.language_combo.addItem("🇺🇸 English", userData="en")
        self.language_combo.addItem("🇪🇸 Español", userData="es")
        self.language_combo.currentIndexChanged.connect(self._set_language)
        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch(1)
        panel_layout_.addLayout(lang_row)

        start_btn = QPushButton(gui_t(self.state, "start_session"))
        start_btn.setObjectName("primary")
        start_btn.setFixedWidth(260)
        start_btn.setFixedHeight(46)
        start_btn.clicked.connect(on_start)
        start_row = QHBoxLayout()
        start_row.addStretch(1)
        start_row.addWidget(start_btn)
        start_row.addStretch(1)
        panel_layout_.addLayout(start_row)

        layout.addWidget(panel, alignment=Qt.AlignCenter)
        layout.addStretch(2)
        self.status_badge = add_status_badge(layout, self.state)

        # Default language from state if set
        if str(self.state.language).lower().startswith("es"):
            self.language_combo.setCurrentIndex(1)
        self.title = title
        self.subtitle = subtitle
        self.lang_label = lang_label
        self.start_btn = start_btn

    def _set_language(self) -> None:
        code = self.language_combo.currentData()
        if isinstance(code, str):
            self.state.language = code
        self.refresh_text()
        self.on_language_change()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "app_title"))
        self.subtitle.setText(gui_t(self.state, "subtitle"))
        self.lang_label.setText(gui_t(self.state, "language"))
        self.start_btn.setText(gui_t(self.state, "start_session"))
        lang_idx = 1 if str(self.state.language).lower().startswith("es") else 0
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(lang_idx)
        self.language_combo.blockSignals(False)

