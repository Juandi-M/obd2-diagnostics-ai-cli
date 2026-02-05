from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.state import AppState
from app.presentation.qt.features.connection.adapter_list import AdapterList
from app.presentation.qt.features.connection.status_card import ConnectionStatusCard
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import panel_layout
from app.presentation.qt.widgets.status import StatusLabel, add_status_badge


class ConnectView(QWidget):
    def __init__(
        self,
        state: AppState,
        *,
        on_bypass: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        # Keep the page tight; the shell already adds outer padding.
        layout.setSpacing(6)
        self.title = QLabel(gui_t(self.state, "connection"))
        self.title.setObjectName("title")
        layout.addWidget(self.title)

        self.panel, panel_layout_ = panel_layout()
        self.panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.panel.setMaximumWidth(16777215)  # fill available space on wide windows

        # Connection method selector: custom-styled as a segmented control via QSS.
        self.method_segment = QFrame()
        self.method_segment.setObjectName("methodSegment")
        method_row = QHBoxLayout(self.method_segment)
        method_row.setContentsMargins(0, 0, 0, 0)
        method_row.setSpacing(0)
        self.usb_radio = QRadioButton(gui_t(self.state, "usb"))
        self.usb_radio.setObjectName("methodRadio")
        self.ble_radio = QRadioButton(gui_t(self.state, "ble"))
        self.ble_radio.setObjectName("methodRadio")
        self.usb_radio.setChecked(True)
        method_row.addWidget(self.usb_radio)
        method_row.addWidget(self.ble_radio)
        self.method_segment.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        panel_layout_.addWidget(self.method_segment, alignment=Qt.AlignLeft)

        self.kline_checkbox = QCheckBox(gui_t(self.state, "kline"))
        self.kline_checkbox.setChecked(True)
        panel_layout_.addWidget(self.kline_checkbox)

        self.scan_controls = QWidget()
        scan_row = QHBoxLayout(self.scan_controls)
        scan_row.setContentsMargins(0, 0, 0, 0)
        self.scan_btn = QPushButton(gui_t(self.state, "scan"))
        self.scan_btn.setObjectName("primary")
        self.show_all_ble = QCheckBox(gui_t(self.state, "show_all_ble"))
        scan_row.addWidget(self.scan_btn)
        scan_row.addWidget(self.show_all_ble)
        scan_row.addStretch(1)
        panel_layout_.addWidget(self.scan_controls)

        self.hint_label = QLabel(gui_t(self.state, "connect_hint"))
        self.hint_label.setObjectName("hint")
        panel_layout_.addWidget(self.hint_label)

        status_row = QHBoxLayout()
        self.busy_bar = QProgressBar()
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setFixedHeight(10)
        self.busy_bar.setMaximumWidth(220)
        self.busy_bar.setVisible(False)
        self.status_label = QLabel("")
        self.status_label.setObjectName("hint")
        status_row.addWidget(self.busy_bar)
        status_row.addWidget(self.status_label, 1)
        self.stop_btn = QPushButton(gui_t(self.state, "stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setVisible(False)
        status_row.addWidget(self.stop_btn)
        panel_layout_.addLayout(status_row)

        self.list_widget = AdapterList()
        panel_layout_.addWidget(self.list_widget)

        connect_row = QHBoxLayout()
        connect_row.addStretch(1)
        self.connect_btn = QPushButton(gui_t(self.state, "connect"))
        self.connect_btn.setObjectName("primary")
        connect_row.addWidget(self.connect_btn)
        connect_row.addStretch(1)
        panel_layout_.addLayout(connect_row)

        self.status_card = ConnectionStatusCard(self.state)
        panel_layout_.addWidget(self.status_card)

        layout.addWidget(self.panel)

        bypass_row = QHBoxLayout()
        self.bypass_btn = QPushButton(gui_t(self.state, "bypass"))
        self.bypass_btn.setObjectName("secondary")
        self.bypass_btn.clicked.connect(on_bypass)
        bypass_row.addStretch(1)
        bypass_row.addWidget(self.bypass_btn)
        bypass_row.addStretch(1)
        layout.addLayout(bypass_row)

        self.status_badge: StatusLabel = add_status_badge(layout, self.state)
        # Absorb any extra vertical space so the title doesn't "float" with large gaps.
        layout.addStretch(1)
        self.update_method_ui()

    def refresh_text(self) -> None:
        self.title.setText(gui_t(self.state, "connection"))
        self.usb_radio.setText(gui_t(self.state, "usb"))
        self.ble_radio.setText(gui_t(self.state, "ble"))
        self.kline_checkbox.setText(gui_t(self.state, "kline"))
        self.scan_btn.setText(gui_t(self.state, "scan"))
        self.stop_btn.setText(gui_t(self.state, "stop"))
        self.show_all_ble.setText(gui_t(self.state, "show_all_ble"))
        self.update_method_ui()
        self.connect_btn.setText(gui_t(self.state, "connect"))
        self.bypass_btn.setText(gui_t(self.state, "bypass"))

    def set_busy(self, busy: bool, text: str, *, lock_list: bool = False) -> None:
        self.busy_bar.setVisible(busy)
        self.stop_btn.setVisible(busy)
        self.status_label.setText(text or "")

        self.scan_btn.setEnabled(not busy)
        self.connect_btn.setEnabled(not busy)
        self.usb_radio.setEnabled(not busy)
        self.ble_radio.setEnabled(not busy)
        self.show_all_ble.setEnabled(not busy)
        self.kline_checkbox.setEnabled(not busy and self.usb_radio.isChecked())
        # While scanning, keep the list scrollable/selectable; only lock it during connect.
        self.list_widget.setEnabled(not lock_list)

    def update_method_ui(self) -> None:
        usb = self.usb_radio.isChecked()
        ble = self.ble_radio.isChecked()

        # Keep the UI minimal: USB enumerates ports automatically; BLE needs an explicit scan.
        self.scan_controls.setVisible(ble)
        self.show_all_ble.setVisible(ble)
        self.kline_checkbox.setVisible(usb)

        if usb:
            self.hint_label.setText(gui_t(self.state, "usb_connect_hint"))
        else:
            self.hint_label.setText(gui_t(self.state, "connect_hint"))

    def selected_port(self) -> Optional[str]:
        return self.list_widget.selected_port()
