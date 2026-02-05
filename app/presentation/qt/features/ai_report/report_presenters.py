from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.utils.text import header_lines


def list_report_items(
    state: AppState,
    *,
    query: str,
    status_filter: str,
    date_filter: str,
) -> List[Tuple[str, str]]:
    vm = get_vm()
    query_l = (query or "").lower().strip()
    now = datetime.now().astimezone()
    items: List[Tuple[str, str]] = []
    for report in vm.reports_vm.list_reports():
        if status_filter != "All" and report.status != status_filter:
            continue

        if date_filter != "All":
            created = None
            try:
                created = datetime.fromisoformat(str(report.created_at).replace("Z", "+00:00"))
            except Exception:
                created = None
            if created:
                delta_days = (now - created).days
                if date_filter == "Today" and delta_days != 0:
                    continue
                if date_filter == "Last 7 days" and delta_days > 7:
                    continue
                if date_filter == "Last 30 days" and delta_days > 30:
                    continue

        payload: Dict[str, Any] = {}
        if report.file_path:
            try:
                payload = vm.reports_vm.load_report(str(report.file_path))
            except Exception:
                payload = {}

        if query_l and query_l not in str(report.report_id).lower():
            notes = str(payload.get("customer_notes", "")).lower()
            if query_l not in notes:
                continue

        fav = "★" if payload.get("favorite") else "☆"
        label = f"{fav} {report.report_id} | {report.created_at} | {report.status}"
        items.append((str(report.report_id), label))
    return items


def build_preview_package(
    state: AppState,
    *,
    report_id: str,
    report_path: str,
    payload: Dict[str, Any],
) -> Dict[str, str]:
    text = payload.get("ai_response") or payload.get("ai_response_raw") or ""
    lines: List[str] = []
    lines.extend(header_lines("AI DIAGNOSTIC REPORT"))
    lines.append(f"  Report ID: {payload.get('report_id', '-')}")
    lines.append(f"  Created: {payload.get('created_at', '-')}")
    lines.append(f"  Status: {payload.get('status', '-')}")
    lines.append(f"  Model: {payload.get('model', '-')}")

    vin_value = ""
    if isinstance(payload.get("vehicle"), dict):
        vin_value = payload.get("vehicle", {}).get("vin") or ""
    if vin_value:
        lines.append(f"  {gui_t(state, 'vin_label')}: {vin_value}")

    notes = payload.get("customer_notes", "") or ""
    lines.append("")
    lines.append("  Customer Notes:")
    for line in str(notes).splitlines():
        lines.append(f"    {line}")
    lines.append("")
    lines.append("  AI Response:")
    lines.append("")
    for line in str(text).splitlines():
        lines.append(f"  {line}")

    vehicle = payload.get("vehicle", {}) or {}
    vehicle_label = ", ".join(
        [v for v in [vehicle.get("make"), vehicle.get("model"), vehicle.get("year"), vehicle.get("trim")] if v]
    )
    pdf_path = payload.get("pdf_path") or get_vm().reports_vm.report_pdf_path(payload.get("report_id", report_id))
    meta = f"File: {Path(report_path).name} | Vehicle: {vehicle_label or '—'} | PDF: {pdf_path}"

    dtc_chip = f"DTCs: {len((payload.get('scan_data') or {}).get('dtcs') or [])}"
    readiness_chip = _readiness_chip(payload)

    return {
        "preview_text": "\n".join(lines),
        "preview_meta": meta,
        "dtc_chip": dtc_chip,
        "readiness_chip": readiness_chip,
    }


def _readiness_chip(payload: Dict[str, Any]) -> str:
    scan_data = payload.get("scan_data") or {}
    readiness = scan_data.get("readiness") or {}
    complete = 0
    incomplete = 0
    for _, status in readiness.items():
        if not isinstance(status, dict):
            continue
        if status.get("available") is False:
            continue
        if status.get("complete") is True:
            complete += 1
        else:
            incomplete += 1
    return f"Readiness: {complete} complete / {incomplete} incomplete"

