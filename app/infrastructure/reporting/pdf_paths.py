from __future__ import annotations

from datetime import datetime, timezone

from app.domain.ports import PdfPathPort
from app.infrastructure.persistence.reports import ensure_reports_dir
from app.infrastructure.persistence.data_paths import reports_dir


def build_report_pdf_filename(report_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"report_{timestamp}_{report_id}.pdf"


def report_pdf_path(report_id: str):
    ensure_reports_dir()
    return reports_dir() / build_report_pdf_filename(report_id)


class PdfPathAdapter(PdfPathPort):
    def report_pdf_path(self, report_id: str) -> str:
        return str(report_pdf_path(report_id))
