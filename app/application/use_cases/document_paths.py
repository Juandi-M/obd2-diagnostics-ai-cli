from __future__ import annotations

from typing import Any, Dict

from app.domain.ports import DocumentPathPort


class DocumentPathService:
    def __init__(self, port: DocumentPathPort) -> None:
        self.port = port

    def ai_report_pdf_path(self, vehicle_payload: Dict[str, Any]) -> str:
        return self.port.ai_report_pdf_path(vehicle_payload)
