from __future__ import annotations

import time
from typing import Any, Callable, List, Optional, Tuple

from PySide6.QtCore import QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.features.connection.ble_burst_scanner import BleBurstScanner
from app.presentation.qt.features.connection.connect_view import ConnectView
from app.presentation.qt.features.connection.devices import DeviceEntry, format_selected_summary
from app.presentation.qt.features.connection.scan_handlers import handle_ble_scan, handle_usb_scan
from app.presentation.qt.i18n import gui_t


class ConnectPage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_connected: Callable[[], None],
        on_bypass: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state
        self.on_connected = on_connected
        self.on_bypass = on_bypass

        self.connection_vm = get_vm().connection_vm
        self.device_list: List[DeviceEntry] = []

        # Remember the last method the user picked during this app session.
        # Default to BLE if the user previously connected via BLE (persisted in settings/state).
        self._preferred_method: str = "usb"
        if self.state.last_ble_address and not str(self.state.last_seen_device or "").startswith("/dev/"):
            self._preferred_method = "ble"

        self._busy = False
        self._scan_request_id = 0
        self._connect_request_id = 0
        self._active_op: Optional[Tuple[str, int]] = None

        self._ble_scanner = BleBurstScanner()

        self.view = ConnectView(self.state, on_bypass=self.on_bypass)
        self.view.usb_radio.toggled.connect(self._toggle_kline)
        self.view.ble_radio.toggled.connect(self._toggle_kline)
        self.view.usb_radio.toggled.connect(self._on_usb_selected)
        self.view.ble_radio.toggled.connect(self._on_ble_selected)
        self.view.scan_btn.clicked.connect(self._scan)
        self.view.stop_btn.clicked.connect(self._stop)
        self.view.connect_btn.clicked.connect(self._connect)
        self.view.list_widget.currentItemChanged.connect(self._on_selection_changed)

        # Exposed for MainWindow status badge refresh.
        self.status_badge = self.view.status_badge

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self._toggle_kline()
        self._refresh_status_card()
        self.view.list_widget.adjust_height()

        # Apply preferred method after wiring signals so UI stays consistent.
        if self._preferred_method == "ble":
            self.view.ble_radio.setChecked(True)

        self.connection_vm.usb_scan_finished.connect(self._on_usb_scan)
        self.connection_vm.ble_scan_finished.connect(self._on_ble_scan)
        self.connection_vm.connect_finished.connect(self._on_connect)

    def refresh_text(self) -> None:
        self.view.refresh_text()
        self._refresh_status_card()

    def update_empty_state(self) -> None:
        self._refresh_status_card()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        # Keep the connection page "smart" on reconnect: USB ports show without clicking Scan.
        self.view.update_method_ui()
        changed_method = False
        if not self._busy:
            if self._preferred_method == "ble" and not self.view.ble_radio.isChecked():
                self.view.ble_radio.setChecked(True)
                changed_method = True
            elif self._preferred_method == "usb" and not self.view.usb_radio.isChecked():
                self.view.usb_radio.setChecked(True)
                changed_method = True
        if not changed_method and self.view.usb_radio.isChecked() and not self._busy and self.view.list_widget.count() <= 0:
            QTimer.singleShot(60, self._scan)

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802 - Qt naming
        super().hideEvent(event)
        # Stop any in-flight BLE scan loop when navigating away.
        self._ble_scanner.stop()
        self._active_op = None

    def _toggle_kline(self) -> None:
        self.view.kline_checkbox.setEnabled(self.view.usb_radio.isChecked() and not self._busy)
        if not self.view.usb_radio.isChecked():
            self.view.kline_checkbox.setChecked(False)
        self.view.update_method_ui()

    def _on_usb_selected(self, checked: bool) -> None:
        if not checked or self._busy:
            return
        self._preferred_method = "usb"
        # Switching methods: stop BLE loop and clear list to avoid mixing USB/BLE entries.
        self._ble_scanner.stop()
        self._active_op = None
        self.device_list = []
        self.view.list_widget.set_devices([], show_all=False, keep_selection=False)
        self.view.list_widget.adjust_height()
        self._refresh_status_card()
        QTimer.singleShot(60, self._scan)

    def _on_ble_selected(self, checked: bool) -> None:
        if not checked or self._busy:
            return
        self._preferred_method = "ble"
        # Switching methods: stop any scan loop and clear USB ports from the list.
        self._ble_scanner.stop()
        self._active_op = None
        self.device_list = []
        self.view.list_widget.set_devices([], show_all=True, keep_selection=False)
        self.view.list_widget.adjust_height()
        self._refresh_status_card()

    def _scan(self) -> None:
        if self._busy:
            return
        if self.view.usb_radio.isChecked():
            self._scan_request_id += 1
            req_id = self._scan_request_id
            self._active_op = ("scan_usb", req_id)
            self._set_busy(True, "Detecting USB adapters...")
            self.connection_vm.scan_usb(request_id=req_id)
            return

        self._set_busy(True, "Scanning adapters...")
        self._ble_scanner.start(self.view.show_all_ble.isChecked())
        self._ble_scan_next()

    def _ble_scan_next(self) -> None:
        if not self._ble_scanner.running:
            return
        iter_num = self._ble_scanner.next_iter()
        self._scan_request_id += 1
        req_id = self._scan_request_id
        self._active_op = ("scan_ble", req_id)
        self._set_busy(True, f"Scanning adapters... ({iter_num}/{self._ble_scanner.max_iters})")
        self.connection_vm.scan_ble(
            self._ble_scanner.include_all,
            request_id=req_id,
            timeout_s=self._ble_scanner.timeout_s,
        )

    def _on_usb_scan(self, result: Any, err: Any) -> None:
        handle_usb_scan(self, result, err)

    def _on_ble_scan(self, result: Any, err: Any) -> None:
        handle_ble_scan(self, result, err)

    def _connect(self) -> None:
        port = self.view.selected_port()
        if not port:
            # Avoid modal dialogs on macOS+BLE; keep feedback inline.
            self.view.status_label.setText("Select a device first.")
            return
        use_kline = self.view.kline_checkbox.isChecked()
        self._connect_request_id += 1
        req_id = self._connect_request_id
        self._active_op = ("connect", req_id)
        self._set_busy(True, "Connecting / handshaking...")
        self.connection_vm.connect_device(port, use_kline, request_id=req_id)

    def _on_connect(self, result: Any, err: Any) -> None:
        req_id, payload = (None, None)
        if isinstance(result, tuple) and len(result) == 2:
            req_id, payload = result
        else:
            payload = result
        if self._active_op != ("connect", req_id):
            return
        self._active_op = None
        self._set_busy(False, "")
        if err:
            self.view.status_label.setText(f"Connection error: {err}")
            self._refresh_status_card(extra_error=str(err))
            return

        mode = payload.get("mode") if isinstance(payload, dict) else None
        info = payload.get("info") if isinstance(payload, dict) else None
        exc = payload.get("error") if isinstance(payload, dict) else None
        if mode not in {"obd", "kline"}:
            self.view.status_label.setText(f"Failed: {exc}")
            self._refresh_status_card(extra_error=str(exc) if exc else "Failed")
            return

        port = self.view.selected_port() or ""
        if isinstance(port, str) and port.startswith("ble:"):
            self.state.last_ble_address = port.split(":", 1)[1]
            get_vm().settings_vm.save()
        if isinstance(info, dict):
            self.state.last_vin = info.get("vin") or self.state.last_vin
        self.state.last_seen_at = time.time()

        if mode == "kline":
            window = self.window()
            if hasattr(window, "show_toast"):
                window.show_toast(gui_t(self.state, "kline_connected"))

        self._refresh_status_card()
        self.on_connected()

    def _stop(self) -> None:
        op = self._active_op
        self._ble_scanner.stop()
        self._active_op = None
        if op and op[0] == "connect":
            try:
                self.state.disconnect_all()
            except Exception:
                pass
        self._set_busy(False, "Cancelled.")
        self._refresh_status_card()
        QTimer.singleShot(1600, self._sync_status_label)

    def _set_busy(self, busy: bool, text: str) -> None:
        self._busy = busy
        lock_list = bool(busy and self._active_op and self._active_op[0] == "connect")
        self.view.set_busy(busy, text, lock_list=lock_list)
        self._toggle_kline()
        if not busy and not text:
            self._sync_status_label()

    def _sync_status_label(self) -> None:
        port = self.view.selected_port()
        if port:
            self.view.status_label.setText(f"Selected: {format_selected_summary(port, self.device_list)}")
        else:
            self.view.status_label.setText("" if not self._busy else self.view.status_label.text())

    def _on_selection_changed(self, *_: Any) -> None:
        # Allow scrolling/selection while scanning; lock changes only during connect.
        if self._busy and self._active_op and self._active_op[0] == "connect":
            return
        # While scanning, keep the progress text in the status line; the status card shows selection.
        if self._busy and self._active_op and self._active_op[0].startswith("scan"):
            self._refresh_status_card()
            return
        self._sync_status_label()
        self._refresh_status_card()

    def _refresh_status_card(self, extra_error: Optional[str] = None) -> None:
        self.view.status_card.refresh(
            device_list=self.device_list,
            selected_port=self.view.selected_port(),
            extra_error=extra_error,
        )
