from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.entities import ReportMeta
from app.domain.ports import FullScanReportRepository, ReportRepository


class ReportsService:
    def __init__(self, repo: ReportRepository) -> None:
        self.repo = repo

    def save_report(self, payload: Dict[str, Any]) -> str:
        return self.repo.save_report(payload)

    def list_reports(self) -> List[ReportMeta]:
        return self.repo.list_reports()

    def load_report(self, path: str) -> Dict[str, Any]:
        return self.repo.load_report(path)

    def find_report_by_id(self, report_id: str) -> Optional[str]:
        return self.repo.find_report_by_id(report_id)

    def write_report(self, path: str, payload: Dict[str, Any]) -> None:
        self.repo.write_report(path, payload)


class FullScanReportsService:
    def __init__(self, repo: FullScanReportRepository) -> None:
        self.repo = repo

    def save(self, lines: List[str]) -> str:
        return self.repo.save(lines)

    def list(self) -> List[str]:
        return self.repo.list()

    def load(self, path: str) -> str:
        return self.repo.load(path)
