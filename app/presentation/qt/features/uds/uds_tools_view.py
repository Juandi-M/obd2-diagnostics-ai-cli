from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import PAGE_MAX_WIDTH, panel_layout


class UdsToolsView(QWidget):
    def __init__(self, state: AppState, *, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        self.title = QLabel(gui_t(self.state, "uds_title"))
        self.title.setObjectName("title")
        layout.addWidget(self.title)

        panel, panel_layout_ = panel_layout()
        panel.setMaximumWidth(PAGE_MAX_WIDTH)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        form = QFormLayout()
        self.brand_label = QLabel(gui_t(self.state, "uds_brand"))
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("Jeep / Chrysler", userData="jeep")
        self.brand_combo.addItem("Land Rover", userData="land_rover")
        if self.state.manufacturer == "landrover":
            self.brand_combo.setCurrentIndex(1)
        form.addRow(self.brand_label, self.brand_combo)

        self.module_label = QLabel(gui_t(self.state, "uds_module"))
        self.module_combo = QComboBox()
        form.addRow(self.module_label, self.module_combo)
        panel_layout_.addLayout(form)

        action_row = QGridLayout()
        action_row.setHorizontalSpacing(10)
        action_row.setVerticalSpacing(8)
        self.read_vin_btn = QPushButton(gui_t(self.state, "uds_read_vin"))
        self.read_vin_btn.setObjectName("secondary")
        self.read_did_btn = QPushButton(gui_t(self.state, "uds_read_did"))
        self.read_did_btn.setObjectName("secondary")
        self.read_dtcs_btn = QPushButton(gui_t(self.state, "uds_read_dtcs"))
        self.read_dtcs_btn.setObjectName("secondary")
        self.send_raw_btn = QPushButton(gui_t(self.state, "uds_send_raw"))
        self.send_raw_btn.setObjectName("secondary")
        action_row.addWidget(self.read_vin_btn, 0, 0)
        action_row.addWidget(self.read_did_btn, 0, 1)
        action_row.addWidget(self.read_dtcs_btn, 1, 0)
        action_row.addWidget(self.send_raw_btn, 1, 1)
        panel_layout_.addLayout(action_row)

        inputs_row = QGridLayout()
        inputs_row.setHorizontalSpacing(10)
        inputs_row.setVerticalSpacing(8)
        self.did_label = QLabel(gui_t(self.state, "uds_read_did"))
        self.did_input = QLineEdit()
        self.did_input.setPlaceholderText("F190")
        self.service_label = QLabel(gui_t(self.state, "uds_service_id"))
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText(gui_t(self.state, "uds_service_id"))
        self.data_label = QLabel(gui_t(self.state, "uds_data_hex"))
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText(gui_t(self.state, "uds_data_hex"))
        inputs_row.addWidget(self.did_label, 0, 0)
        inputs_row.addWidget(self.did_input, 0, 1)
        inputs_row.addWidget(self.service_label, 0, 2)
        inputs_row.addWidget(self.service_input, 0, 3)
        inputs_row.addWidget(self.data_label, 1, 0)
        inputs_row.addWidget(self.data_input, 1, 1, 1, 3)
        inputs_row.setColumnStretch(1, 1)
        inputs_row.setColumnStretch(3, 1)
        panel_layout_.addLayout(inputs_row)

        discovery_row = QVBoxLayout()
        discovery_row.setSpacing(8)
        self.discover_btn = QPushButton(gui_t(self.state, "uds_discover"))
        self.discover_btn.setObjectName("secondary")
        self.discover_quick = QCheckBox(gui_t(self.state, "uds_discover_range"))
        self.discover_29 = QCheckBox(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250 = QCheckBox(gui_t(self.state, "uds_discover_250"))
        self.discover_250.setChecked(True)
        self.discover_dtcs = QCheckBox(gui_t(self.state, "uds_discover_dtcs"))
        self.discover_timeout = QSpinBox()
        self.discover_timeout.setRange(50, 1000)
        self.discover_timeout.setValue(120)
        self.timeout_label = QLabel(gui_t(self.state, "uds_discover_timeout"))
        timeout_row = QHBoxLayout()
        timeout_row.setSpacing(6)
        timeout_row.addWidget(self.timeout_label)
        timeout_row.addWidget(self.discover_timeout)
        top_row = QHBoxLayout()
        top_row.addWidget(self.discover_btn)
        top_row.addStretch(1)
        top_row.addLayout(timeout_row)
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

        self.discover_hint = QLabel(gui_t(self.state, "uds_discover_hint"))
        self.discover_hint.setObjectName("subtitle")
        panel_layout_.addWidget(self.discover_hint)

        cached_row = QHBoxLayout()
        self.cached_label = QLabel("")
        self.cached_label.setObjectName("subtitle")
        self.cached_btn = QPushButton(gui_t(self.state, "uds_discover_cached"))
        self.cached_btn.setObjectName("secondary")
        cached_row.addWidget(self.cached_label)
        cached_row.addStretch(1)
        cached_row.addWidget(self.cached_btn)
        panel_layout_.addLayout(cached_row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(280)
        panel_layout_.addWidget(self.output)

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
        self.title.setText(gui_t(self.state, "uds_title"))
        self.brand_label.setText(gui_t(self.state, "uds_brand"))
        self.module_label.setText(gui_t(self.state, "uds_module"))
        self.read_vin_btn.setText(gui_t(self.state, "uds_read_vin"))
        self.read_did_btn.setText(gui_t(self.state, "uds_read_did"))
        self.read_dtcs_btn.setText(gui_t(self.state, "uds_read_dtcs"))
        self.send_raw_btn.setText(gui_t(self.state, "uds_send_raw"))
        self.did_label.setText(gui_t(self.state, "uds_read_did"))
        self.service_label.setText(gui_t(self.state, "uds_service_id"))
        self.service_input.setPlaceholderText(gui_t(self.state, "uds_service_id"))
        self.data_label.setText(gui_t(self.state, "uds_data_hex"))
        self.data_input.setPlaceholderText(gui_t(self.state, "uds_data_hex"))
        self.discover_btn.setText(gui_t(self.state, "uds_discover"))
        self.discover_quick.setText(gui_t(self.state, "uds_discover_range"))
        self.discover_29.setText(gui_t(self.state, "uds_discover_29bit"))
        self.discover_250.setText(gui_t(self.state, "uds_discover_250"))
        self.discover_dtcs.setText(gui_t(self.state, "uds_discover_dtcs"))
        self.timeout_label.setText(gui_t(self.state, "uds_discover_timeout"))
        self.discover_hint.setText(gui_t(self.state, "uds_discover_hint"))
        self.cached_btn.setText(gui_t(self.state, "uds_discover_cached"))
        self.reconnect_btn.setText(gui_t(self.state, "reconnect"))
        self.back_btn.setText(gui_t(self.state, "back"))

