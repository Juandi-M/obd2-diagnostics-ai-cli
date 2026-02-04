from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject

from app.application.state import AppState
from app.application.use_cases.scans import ScanService
from app.application.use_cases.reports import FullScanReportsService


class ScanViewModel(QObject):
    def __init__(self, state: AppState, scans: ScanService, full_scan_reports: FullScanReportsService) -> None:
        super().__init__()
        self.state = state
        self.scans = scans
        self.full_scan_reports = full_scan_reports

    def get_vehicle_info(self) -> Dict[str, Any]:
        return self.scans.get_vehicle_info()

    def read_dtcs(self):
        return self.scans.read_dtcs()

    def read_readiness(self) -> Dict[str, Any]:
        return self.scans.read_readiness()

    def read_live_data(self, pids: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.scans.read_live_data(pids)

    def read_freeze_frame(self) -> Dict[str, Any]:
        return self.scans.read_freeze_frame()

    def clear_codes(self) -> bool:
        return self.scans.clear_codes()

    def collect_scan_report(self) -> Dict[str, Any]:
        return self.scans.collect_scan_report()

    def save_full_scan(self, lines: List[str]) -> str:
        return self.full_scan_reports.save(lines)

    def list_full_scans(self) -> List[str]:
        return self.full_scan_reports.list()

    def load_full_scan(self, path: str) -> str:
        return self.full_scan_reports.load(path)
