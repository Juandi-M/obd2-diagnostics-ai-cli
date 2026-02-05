from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThreadPool, Signal

from app.application.state import AppState
from app.application.use_cases.connection import ConnectionService
from app.presentation.qt.workers import Worker


class ConnectionViewModel(QObject):
    usb_scan_finished = Signal(object, object)
    ble_scan_finished = Signal(object, object)
    connect_finished = Signal(object, object)

    def __init__(self, state: AppState, connection: ConnectionService) -> None:
        super().__init__()
        self.state = state
        self.connection = connection
        self.thread_pool = QThreadPool.globalInstance()

    def scan_usb(self, request_id: int = 0) -> None:
        worker = Worker(self.connection.scan_usb_ports)
        worker.signals.finished.connect(
            lambda result, err, rid=request_id: self.usb_scan_finished.emit((rid, result), err)
        )
        self.thread_pool.start(worker)

    def scan_ble(self, include_all: bool = False, request_id: int = 0, timeout_s: Optional[float] = None) -> None:
        worker = Worker(self.connection.scan_ble_devices, include_all=include_all, timeout_s=timeout_s)
        worker.signals.finished.connect(
            lambda result, err, rid=request_id: self.ble_scan_finished.emit((rid, result), err)
        )
        self.thread_pool.start(worker)

    def connect_device(self, port: str, use_kline: bool, request_id: int = 0) -> None:
        worker = Worker(self._connect_job, port, use_kline)
        worker.signals.finished.connect(
            lambda result, err, rid=request_id: self.connect_finished.emit((rid, result), err)
        )
        self.thread_pool.start(worker)

    def _connect_job(self, port: str, use_kline: bool) -> Dict[str, Any]:
        scanner = self.state.ensure_scanner()
        ok, info, exc = self.connection.try_connect(port)
        if ok:
            return {"mode": "obd", "info": info, "error": None}
        if use_kline and not str(port).lower().startswith("ble:"):
            kline_scanner, kline_info, kline_err = self.connection.try_kline(port)
            if kline_scanner:
                payload = dict(kline_info or {})
                payload.setdefault("protocol", "K-LINE")
                return {"mode": "kline", "info": payload, "error": None}
            return {"mode": "kline_failed", "info": {}, "error": kline_err or exc}
        return {"mode": "obd_failed", "info": {}, "error": exc}
