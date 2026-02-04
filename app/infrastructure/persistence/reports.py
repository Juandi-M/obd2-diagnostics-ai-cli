from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


from .data_paths import reports_dir, logs_dir
from app.domain.entities import ReportMeta
from app.domain.ports import ReportRepository, FullScanReportRepository

DATA_DIR = reports_dir()
LOG_DIR = logs_dir()
FULL_SCAN_DIR = LOG_DIR / ".full_scan_reports"


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


def ensure_logs_dir() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def ensure_full_scan_dir() -> Path:
    ensure_logs_dir()
    FULL_SCAN_DIR.mkdir(parents=True, exist_ok=True)
    return FULL_SCAN_DIR


def build_full_scan_txt_filename(timestamp: Optional[datetime] = None) -> str:
    stamp = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"full_scan_{stamp}.txt"


def full_scan_txt_path(timestamp: Optional[datetime] = None) -> Path:
    ensure_full_scan_dir()
    return FULL_SCAN_DIR / build_full_scan_txt_filename(timestamp=timestamp)


def save_full_scan_txt(lines: List[str], timestamp: Optional[datetime] = None) -> Path:
    path = full_scan_txt_path(timestamp=timestamp)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def list_full_scan_reports() -> List[Path]:
    ensure_full_scan_dir()
    return sorted(FULL_SCAN_DIR.glob("full_scan_*.txt"), reverse=True)


def load_full_scan_report(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
                status=str(payload.get("status", "unknown")),
                model=payload.get("model"),
                file_path=str(path),
            )
        )
    return reports


def find_report_by_id(report_id: str) -> Optional[Path]:
    ensure_reports_dir()
    for path in DATA_DIR.glob(f"*{report_id}*.json"):
        return path
    return None


class ReportRepositoryImpl(ReportRepository):
    def save_report(self, payload: Dict[str, Any]) -> str:
        path = save_report(payload)
        return str(path)

    def list_reports(self) -> List[ReportMeta]:
        return list_reports()

    def load_report(self, path: str) -> Dict[str, Any]:
        return load_report(Path(path))

    def find_report_by_id(self, report_id: str) -> Optional[str]:
        found = find_report_by_id(report_id)
        return str(found) if found else None

    def write_report(self, path: str, payload: Dict[str, Any]) -> None:
        target = Path(path)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class FullScanReportRepositoryImpl(FullScanReportRepository):
    def save(self, lines: List[str]) -> str:
        path = save_full_scan_txt(lines)
        return str(path)

    def list(self) -> List[str]:
        return [str(path) for path in list_full_scan_reports()]

    def load(self, path: str) -> str:
        return load_full_scan_report(Path(path))
