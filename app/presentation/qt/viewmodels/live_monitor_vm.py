from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject

from app.application.state import AppState
from app.application.use_cases.scans import ScanService


class LiveMonitorViewModel(QObject):
    def __init__(self, state: AppState, scans: ScanService) -> None:
        super().__init__()
        self.state = state
        self.scans = scans

    def read_live_data(self, pids: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.scans.read_live_data(pids)
