from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.features.live_data.live_dashboard import LiveDashboard
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, panel_layout
from app.presentation.qt.widgets.scroll import VerticalScrollArea


class LiveDataView(QWidget):
    def __init__(self, state: AppState, *, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = VerticalScrollArea()
        layout.addWidget(self.scroll_area)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        self.scroll_area.setWidget(content)

        self.title = QLabel(gui_t(self.state, "live_title"))
        self.title.setObjectName("title")
        content_layout.addWidget(self.title)

        controls = QHBoxLayout()
        self.start_btn = QPushButton(gui_t(self.state, "start"))
        self.start_btn.setObjectName("primary")
        self.stop_btn = QPushButton(gui_t(self.state, "stop"))
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.setEnabled(False)
        self.customize_btn = QPushButton(gui_t(self.state, "customize"))
        self.customize_btn.setObjectName("secondary")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 10)
        self.interval_spin.setValue(int(self.state.monitor_interval))
        self.interval_spin.setMinimumWidth(96)
        self.interval_label = QLabel(gui_t(self.state, "interval"))
        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.interval_label)
        controls.addWidget(self.interval_spin)
        controls.addWidget(self.customize_btn)
        controls.addStretch(1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("hint")

        controls_panel, controls_layout = panel_layout(padding=16)
        controls_panel.setMaximumWidth(PAGE_MAX_WIDTH)
        controls_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        controls_layout.addLayout(controls)
        controls_layout.addWidget(self.status_label)
        content_layout.addWidget(controls_panel)

        self.dashboard = LiveDashboard(self.state)
        content_layout.addWidget(self.dashboard)

        bottom_row = QHBoxLayout()
        self.reconnect_btn = QPushButton(gui_t(self.state, "reconnect"))
        self.reconnect_btn.setObjectName("secondary")
        self.reconnect_btn.clicked.connect(on_reconnect)
        self.back_btn = QPushButton(gui_t(self.state, "back"))
        self.back_btn.setObjectName("primary")
        self.back_btn.clicked.connect(on_back)
        bottom_row.addWidget(self.reconnect_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.back_btn)
        content_layout.addLayout(bottom_row)

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "live_title"))
        self.start_btn.setText(gui_t(self.state, "start"))
        self.stop_btn.setText(gui_t(self.state, "stop"))
        self.interval_label.setText(gui_t(self.state, "interval"))
        self.customize_btn.setText(gui_t(self.state, "customize"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))
        self.dashboard.refresh_text()

