from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout

from app.application.state import AppState
from app.presentation.qt.i18n import gui_t


class StatusLabel(QLabel):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.setObjectName("statusBadge")
        self.update_text()

    def update_text(self) -> None:
        connected = self.state.active_scanner() is not None
        protocol = "K-LINE" if self.state.kline_scanner and self.state.kline_scanner.is_connected else "OBD2"
        conn_status = (
            f"🟢 {gui_t(self.state, 'connected')}" if connected else f"🔴 {gui_t(self.state, 'disconnected')}"
        )
        profile = self.state.vehicle_profile or {}
        if profile.get("make"):
            vehicle = profile.get("make")
            if profile.get("model"):
                vehicle = f"{vehicle} {profile.get('model')}"
        else:
            vehicle = self.state.brand_label or self.state.manufacturer.capitalize()
        lang = str(self.state.language or "en").upper()
        vin_value = self.state.last_vin or ""
        vin_label = f" | {gui_t(self.state, 'vin_label')}: {vin_value}" if vin_value else ""
        self.setText(
            f"{gui_t(self.state, 'status')}: {conn_status} | {gui_t(self.state, 'vehicle')}: {vehicle}{vin_label} | "
            f"{gui_t(self.state, 'format')}: {self.state.log_format.upper()} | "
            f"{gui_t(self.state, 'protocol')}: {protocol} | {lang}"
        )


def add_status_badge(layout: QVBoxLayout, state: AppState) -> StatusLabel:
    badge = StatusLabel(state)
    layout.addWidget(badge)
    return badge

