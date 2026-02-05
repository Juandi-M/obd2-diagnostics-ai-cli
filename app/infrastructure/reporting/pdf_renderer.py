from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from app.domain.ports import PdfRendererPort
from app.infrastructure.reporting.pdf_engine import render_report_pdf


class PdfReportRenderer(PdfRendererPort):
    def render(
        self,
        payload: Dict[str, Any],
        output_path: str,
        *,
        report_json: Optional[Dict[str, Any]] = None,
        report_text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        render_report_pdf(
            payload,
            Path(output_path),
            report_json=report_json,
            report_text=report_text,
            language=language,
        )
