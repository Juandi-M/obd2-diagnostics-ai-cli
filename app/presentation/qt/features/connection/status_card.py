from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.application.state import AppState
from app.presentation.qt.features.connection.devices import DeviceEntry, format_port_short
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.style import apply_shadow


class ConnectionStatusCard(QFrame):
    def __init__(self, state: AppState, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.setObjectName("emptyCard")
        apply_shadow(self, blur=14, y=4)

        layout = QVBoxLayout(self)
        self.title = QLabel(gui_t(self.state, "connect_empty_title"))
        self.title.setObjectName("sectionTitle")
        self.body = QLabel(gui_t(self.state, "connect_empty_body"))
        self.body.setWordWrap(True)
        self.meta = QLabel("")
        self.meta.setObjectName("hint")
        self.meta.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        layout.addWidget(self.meta)

    def refresh(
        self,
        *,
        device_list: List[DeviceEntry],
        selected_port: Optional[str],
        extra_error: Optional[str] = None,
    ) -> None:
        connected = self.state.active_scanner() is not None
        if connected:
            self.title.setText(gui_t(self.state, "connected"))
            self.body.setText("Adapter connected. You can start scanning from Diagnose or Live Data.")
        else:
            self.title.setText(gui_t(self.state, "connect_empty_title"))
            self.body.setText(gui_t(self.state, "connect_empty_body"))

        last_seen = getattr(self.state, "last_seen_device", None) or "-"
        last_rssi = getattr(self.state, "last_seen_rssi", None)
        last_rssi_s = f"{last_rssi} dBm" if isinstance(last_rssi, int) and last_rssi > -999 else "-"
        vin = getattr(self.state, "last_vin", None) or "-"
        protocol = "K-LINE" if getattr(self.state, "kline_scanner", None) is not None else "OBD2"
        selected = format_port_short(selected_port) if selected_port else "-"
        meta_lines = [
            f"Selected: {selected}",
            f"Last seen: {last_seen} | Signal: {last_rssi_s}",
            f"Protocol: {protocol} | VIN: {vin}",
        ]
        if extra_error:
            meta_lines.append(f"Last error: {extra_error}")
            meta_lines.append("Tip: ignition ON, wait 10-15s after key-on, then reconnect.")
        self.meta.setText("\n".join(meta_lines))

