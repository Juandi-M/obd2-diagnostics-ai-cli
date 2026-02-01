from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "reports"


@dataclass
class ReportMeta:
    report_id: str
    created_at: str
    file_path: Path
    status: str
    model: Optional[str] = None


def ensure_reports_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def new_report_id() -> str:
    return uuid4().hex[:8]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_report_filename(report_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"report_{timestamp}_{report_id}.json"


def save_report(payload: Dict[str, Any]) -> Path:
    ensure_reports_dir()
    report_id = payload.get("report_id") or new_report_id()
    payload["report_id"] = report_id
    payload.setdefault("created_at", utc_now())
    filename = build_report_filename(report_id)
    path = DATA_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_report(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_reports() -> List[ReportMeta]:
    ensure_reports_dir()
    reports: List[ReportMeta] = []
    for path in sorted(DATA_DIR.glob("report_*.json"), reverse=True):
        try:
            payload = load_report(path)
        except json.JSONDecodeError:
            continue
        reports.append(
            ReportMeta(
                report_id=str(payload.get("report_id", path.stem)),
                created_at=str(payload.get("created_at", "")),
                file_path=path,
                status=str(payload.get("status", "unknown")),
                model=payload.get("model"),
            )
        )
    return reports


def find_report_by_id(report_id: str) -> Optional[Path]:
    ensure_reports_dir()
    for path in DATA_DIR.glob(f"*{report_id}*.json"):
        return path
    return None
