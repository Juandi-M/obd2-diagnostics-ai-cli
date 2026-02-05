from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.domain.ports import DocumentPathPort


def _sanitize_filename(value: Optional[str]) -> str:
    if not value:
        return "Unknown"
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_")
    return cleaned or "Unknown"


class DocumentPathAdapter(DocumentPathPort):
    def ai_report_pdf_path(self, vehicle_payload: Dict[str, Any]) -> str:
        docs = Path.home() / "Documents" / "OBDIIAI"
        docs.mkdir(parents=True, exist_ok=True)
        make = _sanitize_filename(vehicle_payload.get("make"))
        model = _sanitize_filename(vehicle_payload.get("model"))
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Report_{make}_{model}_{stamp}.pdf"
        return str(docs / filename)
