from __future__ import annotations

from app.domain.ports import PdfPathPort


class PdfPathService:
    def __init__(self, port: PdfPathPort) -> None:
        self.port = port

    def report_pdf_path(self, report_id: str) -> str:
        return self.port.report_pdf_path(report_id)
