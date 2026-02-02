from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app_cli.reports import DATA_DIR, ensure_reports_dir


def build_report_pdf_filename(report_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"report_{timestamp}_{report_id}.pdf"


def report_pdf_path(report_id: str) -> Path:
    ensure_reports_dir()
    return DATA_DIR / build_report_pdf_filename(report_id)
