from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info, ui_warn
from app.presentation.qt.features.uds import uds_jobs
from app.presentation.qt.features.uds.uds_presenters import format_cached_map
from app.presentation.qt.features.uds.uds_tools_view import UdsToolsView
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.workers import Worker


class UdsToolsPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.thread_pool = QThreadPool.globalInstance()

        self.view = UdsToolsView(self.state, on_back=on_back, on_reconnect=on_reconnect)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.view.brand_combo.currentIndexChanged.connect(self._refresh_modules)
        self.view.cached_btn.clicked.connect(self._show_cached_map)
        self.view.read_vin_btn.clicked.connect(self._read_vin)
        self.view.read_did_btn.clicked.connect(self._read_did)
        self.view.read_dtcs_btn.clicked.connect(self._read_dtcs)
        self.view.send_raw_btn.clicked.connect(self._send_raw)
        self.view.discover_btn.clicked.connect(self._discover_modules)

        self._refresh_modules()
        self._refresh_cached_map()

    def refresh_text(self) -> None:
        self.view.refresh_text()
        self._refresh_cached_map()
        self._refresh_modules()

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            ui_warn(self, "UDS", "No vehicle connected.")
            return False
        if self.state.kline_scanner and self.state.kline_scanner.is_connected:
            ui_warn(self, "UDS", gui_t(self.state, "uds_not_supported"))
            return False
        return True

    def _validate_ready(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        if not self._ensure_connected():
            return None
        brand = str(self.view.brand_combo.currentData() or "jeep")
        module_entry = self.view.module_combo.currentData()
        if not isinstance(module_entry, dict):
            ui_warn(self, "UDS", gui_t(self.state, "uds_no_module"))
            return None
        return brand, module_entry

    def _run_job(self, fn: Callable[..., str], *args: Any) -> None:
        worker = Worker(fn, *args)
        worker.signals.finished.connect(self._on_job_done)
        self.thread_pool.start(worker)

    def _on_job_done(self, result: Any, err: Any) -> None:
        if err:
            ui_warn(self, "UDS", f"{err}")
            return
        if isinstance(result, str):
            self.view.output.setPlainText(result)
        self._refresh_cached_map()
        self._refresh_modules()

    def _get_cached_map(self) -> Optional[Dict[str, Any]]:
        vin = self.state.last_vin or ""
        if not vin:
            return None
        cached = get_vm().vin_cache.get(vin) or {}
        return cached.get("uds_modules")

    def _refresh_cached_map(self) -> None:
        vin = self.state.last_vin or ""
        cached = get_vm().vin_cache.get(vin) if vin else None
        has_map = bool(cached and cached.get("uds_modules"))
        if vin:
            label = f"{gui_t(self.state, 'uds_discover_cached_label')}: {vin}"
        else:
            label = gui_t(self.state, "uds_discover_cached_none")
        self.view.cached_label.setText(label)
        self.view.cached_btn.setEnabled(has_map)

    def _refresh_modules(self) -> None:
        brand = str(self.view.brand_combo.currentData() or "jeep")
        modules = get_vm().uds_tools.module_map(brand)
        self.view.module_combo.clear()

        cached_map = self._get_cached_map()
        if cached_map:
            cached_modules = cached_map.get("modules") or []
            proto = cached_map.get("protocol") or "6"
            for mod in cached_modules:
                tx = mod.get("tx_id")
                rx = mod.get("rx_id")
                mtype = mod.get("module_type") or ""
                suffix = f" · {mtype}" if mtype else ""
                label = f"[{gui_t(self.state, 'uds_discover_cached_label')}] {tx}->{rx}{suffix}"
                user = {
                    "tx_id": tx,
                    "rx_id": rx,
                    "protocol": proto,
                    "module_type": mod.get("module_type"),
                }
                self.view.module_combo.addItem(label, userData=user)

        for name in sorted(modules.keys()):
            entry = dict(modules[name] or {})
            entry.setdefault("name", name)
            self.view.module_combo.addItem(name, userData=entry)

    def _show_cached_map(self) -> None:
        cached_map = self._get_cached_map()
        if not cached_map:
            ui_info(self, "UDS", gui_t(self.state, "uds_discover_cached_none"))
            return
        self.view.output.setPlainText(format_cached_map(self.state, cached_map))

    def _read_vin(self) -> None:
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready
        self._run_job(uds_jobs.read_vin, self.state, brand, module_entry)

    def _read_did(self) -> None:
        did = self.view.did_input.text().strip()
        if not did:
            ui_info(self, "UDS", gui_t(self.state, "uds_read_did"))
            return
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready
        self._run_job(uds_jobs.read_did, self.state, brand, module_entry, did)

    def _send_raw(self) -> None:
        service_hex = self.view.service_input.text().strip()
        data_hex = self.view.data_input.text().strip()
        if not service_hex:
            ui_info(self, "UDS", gui_t(self.state, "uds_service_id"))
            return
        try:
            int(service_hex, 16)
            bytes.fromhex(data_hex) if data_hex else b""
        except ValueError:
            ui_warn(self, "UDS", "Invalid hex input.")
            return
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready
        self._run_job(uds_jobs.send_raw, self.state, brand, module_entry, service_hex, data_hex)

    def _read_dtcs(self) -> None:
        ready = self._validate_ready()
        if not ready:
            return
        brand, module_entry = ready
        self._run_job(uds_jobs.read_dtcs, self.state, brand, module_entry)

    def _discover_modules(self) -> None:
        if not self._ensure_connected():
            return
        id_start, id_end = (0x7E0, 0x7EF) if self.view.discover_quick.isChecked() else (0x700, 0x7FF)
        options = {
            "id_start": id_start,
            "id_end": id_end,
            "timeout_s": max(0.05, self.view.discover_timeout.value() / 1000.0),
            "try_250k": self.view.discover_250.isChecked(),
            "include_29bit": self.view.discover_29.isChecked(),
            "confirm_vin": True,
            "confirm_dtcs": self.view.discover_dtcs.isChecked(),
            "brand_hint": self.state.manufacturer,
        }
        self._run_job(uds_jobs.discover_modules, self.state, options)

