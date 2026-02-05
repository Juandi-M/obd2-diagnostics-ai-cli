from __future__ import annotations

import time
from typing import Any, List, Optional, Protocol, Tuple

from PySide6.QtCore import QTimer

from app.application.state import AppState
from app.presentation.qt.features.connection.ble_burst_scanner import BleBurstScanner
from app.presentation.qt.features.connection.devices import DeviceEntry, sort_devices


class _ScanPage(Protocol):
    state: AppState
    device_list: List[DeviceEntry]
    _active_op: Optional[Tuple[str, int]]
    _ble_scanner: BleBurstScanner
    view: Any

    def _set_busy(self, busy: bool, text: str) -> None: ...
    def _refresh_status_card(self, extra_error: Optional[str] = None) -> None: ...
    def _ble_scan_next(self) -> None: ...


def handle_usb_scan(page: _ScanPage, result: Any, err: Any) -> None:
    req_id, ports = (None, None)
    if isinstance(result, tuple) and len(result) == 2:
        req_id, ports = result
    else:
        ports = result
    if page._active_op != ("scan_usb", req_id):
        return
    page._active_op = None
    if err:
        page._set_busy(False, f"USB scan error: {err}")
        return
    page._set_busy(False, "")

    ports = ports or []
    page.device_list = [(port, port, None) for port in ports]
    page.view.list_widget.set_devices(page.device_list, show_all=False)
    page.view.list_widget.adjust_height()

    if ports:
        page.state.last_seen_at = time.time()
        page.state.last_seen_device = ports[0]
        page.state.last_seen_rssi = None
    else:
        page._set_busy(False, "No USB adapters detected.")
        QTimer.singleShot(2000, lambda: page._set_busy(False, ""))  # restore selection label if any

    page._refresh_status_card()


def handle_ble_scan(page: _ScanPage, result: Any, err: Any) -> None:
    req_id, payload = (None, None)
    if isinstance(result, tuple) and len(result) == 2:
        req_id, payload = result
    else:
        payload = result
    if page._active_op != ("scan_ble", req_id):
        return
    page._active_op = None

    if err:
        page._ble_scanner.stop()
        page._set_busy(False, f"Bluetooth scan error: {err}")
        return

    devices, ble_err = payload
    if ble_err:
        # Some macOS scans can fail transiently; keep scanning but surface it.
        page.view.status_label.setText(f"Bluetooth scan warning: {ble_err}")

    merged = page._ble_scanner.merge(list(devices or []))
    page.device_list = sort_devices(merged)
    page.view.list_widget.set_devices(
        page.device_list,
        show_all=page._ble_scanner.include_all,
        keep_selection=True,
    )
    page.view.list_widget.adjust_height()

    if page.device_list:
        best = page.device_list[0]
        page.state.last_seen_at = time.time()
        page.state.last_seen_device = best[1]
        page.state.last_seen_rssi = best[2]

    page._refresh_status_card()

    if page._ble_scanner.should_stop(page.device_list):
        page._ble_scanner.stop()
        page._set_busy(False, "")
        if not page.device_list:
            page._set_busy(False, "No BLE adapters detected.")
            QTimer.singleShot(2000, lambda: page._set_busy(False, ""))  # restore selection label if any
        return

    QTimer.singleShot(120, page._ble_scan_next)
