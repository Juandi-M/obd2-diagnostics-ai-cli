from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject

from app.application.use_cases.reports import ReportsService
from app.application.use_cases.pdf_paths import PdfPathService
from app.domain.entities import ReportMeta


class ReportsViewModel(QObject):
    def __init__(self, reports: ReportsService, pdf_paths: PdfPathService) -> None:
        super().__init__()
        self.reports = reports
        self.pdf_paths = pdf_paths

    def list_reports(self) -> List[ReportMeta]:
        return self.reports.list_reports()

    def load_report(self, path: str) -> Dict[str, Any]:
        return self.reports.load_report(path)

    def find_report_by_id(self, report_id: str) -> Optional[str]:
        return self.reports.find_report_by_id(report_id)

    def write_report(self, path: str, payload: Dict[str, Any]) -> None:
        self.reports.write_report(path, payload)

    def save_report(self, payload: Dict[str, Any]) -> str:
        return self.reports.save_report(payload)

    def report_pdf_path(self, report_id: str) -> str:
        return self.pdf_paths.report_pdf_path(report_id)
