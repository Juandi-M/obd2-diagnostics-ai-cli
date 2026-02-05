from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, panel_layout


class ModuleMapView(QWidget):
    def __init__(self, state: AppState, *, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        self.title = QLabel(gui_t(self.state, "module_map"))
        self.title.setObjectName("title")
        layout.addWidget(self.title)

        self.hint = QLabel(gui_t(self.state, "module_map_hint"))
        self.hint.setObjectName("subtitle")
        self.detail = QLabel(gui_t(self.state, "module_map_hint_detail"))
        self.detail.setObjectName("hint")
        self.detail.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addWidget(self.detail)

        panel, panel_layout_ = panel_layout()
        panel.setMaximumWidth(PAGE_MAX_WIDTH)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        discovery_row = QVBoxLayout()
        discovery_row.setSpacing(8)
        self.discover_btn = QPushButton(gui_t(self.state, "uds_discover"))
        self.discover_btn.setObjectName("primary")
        self.discover_quick = QCheckBox(gui_t(self.state, "uds_discover_range"))
        self.discover_29 = QCheckBox(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250 = QCheckBox(gui_t(self.state, "uds_discover_250"))
        self.discover_250.setChecked(True)
        self.discover_dtcs = QCheckBox(gui_t(self.state, "uds_discover_dtcs"))
        self.discover_timeout = QSpinBox()
        self.discover_timeout.setRange(50, 1000)
        self.discover_timeout.setValue(120)
        self.timeout_label = QLabel(gui_t(self.state, "uds_discover_timeout"))
        timeout_box = QHBoxLayout()
        timeout_box.setSpacing(6)
        timeout_box.addWidget(self.timeout_label)
        timeout_box.addWidget(self.discover_timeout)
        top_row = QHBoxLayout()
        top_row.addWidget(self.discover_btn)
        top_row.addStretch(1)
        top_row.addLayout(timeout_box)
        options_row = QHBoxLayout()
        options_row.setSpacing(10)
        options_row.addWidget(self.discover_quick)
        options_row.addWidget(self.discover_29)
        options_row.addWidget(self.discover_250)
        options_row.addWidget(self.discover_dtcs)
        options_row.addStretch(1)
        discovery_row.addLayout(top_row)
        discovery_row.addLayout(options_row)
        panel_layout_.addLayout(discovery_row)

        filter_row = QGridLayout()
        filter_row.setHorizontalSpacing(12)
        filter_row.setVerticalSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(gui_t(self.state, "module_map_search"))
        self.search_input.setMinimumWidth(360)
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(140)
        self.fav_only = QCheckBox(gui_t(self.state, "module_map_favorites"))
        self.security_only = QCheckBox(gui_t(self.state, "module_map_security"))
        filter_row.addWidget(self.search_input, 0, 0, 1, 3)
        filter_row.addWidget(self.type_combo, 0, 3)
        filter_row.addWidget(self.fav_only, 1, 0)
        filter_row.addWidget(self.security_only, 1, 1)
        filter_row.setColumnStretch(2, 1)
        panel_layout_.addLayout(filter_row)

        self.list_area = QScrollArea()
        self.list_area.setWidgetResizable(True)
        self.list_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(10)
        self.list_area.setWidget(self.list_container)
        panel_layout_.addWidget(self.list_area)

        layout.addWidget(panel)

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
        layout.addLayout(bottom_row)
        layout.addStretch(1)

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "module_map"))
        self.hint.setText(gui_t(self.state, "module_map_hint"))
        self.detail.setText(gui_t(self.state, "module_map_hint_detail"))
        self.discover_btn.setText(gui_t(self.state, "uds_discover"))
        self.discover_quick.setText(gui_t(self.state, "uds_discover_range"))
        self.discover_29.setText(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250.setText(gui_t(self.state, "uds_discover_250"))
        self.discover_dtcs.setText(gui_t(self.state, "uds_discover_dtcs"))
        self.timeout_label.setText(gui_t(self.state, "uds_discover_timeout"))
        self.search_input.setPlaceholderText(gui_t(self.state, "module_map_search"))
        self.fav_only.setText(gui_t(self.state, "module_map_favorites"))
        self.security_only.setText(gui_t(self.state, "module_map_security"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

