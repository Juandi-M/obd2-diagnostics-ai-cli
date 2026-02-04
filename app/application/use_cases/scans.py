from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.application.scans import (
    clear_codes as _clear_codes,
    get_vehicle_info as _get_vehicle_info,
    read_dtcs as _read_dtcs,
    read_freeze_frame as _read_freeze_frame,
    read_live_data as _read_live_data,
    read_readiness as _read_readiness,
)
from app.application.scan_report import collect_scan_report
from app.application.state import AppState
from app.domain.entities import NotConnectedError


class ScanService:
    def __init__(self, state: AppState) -> None:
        self.state = state

    def require_scanner(self):
        scanner = self.state.active_scanner()
        if not scanner:
            raise NotConnectedError("Not connected to vehicle")
        return scanner

    def get_vehicle_info(self) -> Dict[str, Any]:
        return _get_vehicle_info(self.require_scanner())

    def read_dtcs(self):
        return _read_dtcs(self.require_scanner())

    def read_readiness(self):
        return _read_readiness(self.require_scanner())

    def read_live_data(self, pids: Optional[List[str]] = None):
        return _read_live_data(self.require_scanner(), pids)

    def read_freeze_frame(self):
        return _read_freeze_frame(self.require_scanner())

    def clear_codes(self) -> bool:
        return _clear_codes(self.require_scanner())

    def collect_scan_report(self) -> Dict[str, Any]:
        return collect_scan_report(self.require_scanner())
