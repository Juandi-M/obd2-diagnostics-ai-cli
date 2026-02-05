from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from app.presentation.qt.features.connection.devices import DeviceEntry, format_device_label, preferred_row


class AdapterList(QListWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.ElideRight)

    def selected_port(self) -> Optional[str]:
        item = self.currentItem()
        if isinstance(item, QListWidgetItem):
            port = item.data(Qt.UserRole)
            if isinstance(port, str):
                return port
        return None

    def select_port(self, port: str) -> bool:
        for i in range(self.count()):
            item = self.item(i)
            if item and item.data(Qt.UserRole) == port:
                self.setCurrentRow(i)
                return True
        return False

    def set_devices(self, devices: List[DeviceEntry], *, show_all: bool, keep_selection: bool = True) -> None:
        selected = self.selected_port() if keep_selection else None
        self.clear()
        for port, name, rssi in devices:
            item = QListWidgetItem(format_device_label(port, name, rssi))
            item.setData(Qt.UserRole, port)
            self.addItem(item)

        if selected and self.select_port(selected):
            return

        row = preferred_row(devices, show_all=show_all)
        self.setCurrentRow(row if row is not None else -1)

    def adjust_height(self, max_rows: int = 8) -> None:
        count = self.count()
        if count <= 0:
            self.setMaximumHeight(120)
            return
        row_h = self.sizeHintForRow(0) or 28
        visible_rows = min(count, max_rows)
        extra = 2 * self.frameWidth() + 6
        self.setMaximumHeight(row_h * visible_rows + extra)

