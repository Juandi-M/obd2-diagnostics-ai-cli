from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.presentation.cli.actions.common import require_connected_scanner
from app.presentation.cli.actions.scan_report import collect_scan_report
from app.presentation.cli.i18n import t
from app.bootstrap import get_container
from app.application.use_cases.ai_report import (
    detect_report_language as _detect_report_language,
    build_report_input as _build_report_input,
    extract_report_parts as _extract_report_parts,
    prepare_vehicle_profile as _prepare_vehicle_profile,
    update_report_status as _update_report_status,
)
from app.application.state import AppState
from app.presentation.cli.ui import press_enter, print_header, print_menu
from app.domain.entities import ConnectionLostError, ExternalServiceError, NotConnectedError, ScannerError


def ai_report_menu(state: AppState) -> None:
    while True:
        print_menu(
            t("ai_report_menu"),
            [
                ("1", t("ai_report_new")),
                ("0", t("back")),
            ],
        )
        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            run_ai_report(state)
            press_enter()
        elif choice == "0":
            break


def run_ai_report(state: AppState) -> None:
    if not get_container().ai_config.is_configured():
        print(f"\n  ❌ {t('ai_report_missing_key')}")
        return
    paywall_service = get_container().paywall
    if not paywall_service.is_bypass_enabled() and not paywall_service.is_configured():
        print(f"\n  ❌ {t('paywall_not_configured')}")
        return

    scanner = require_connected_scanner(state)
    if not scanner:
        return

    print_header(t("ai_report_header"))
    customer_notes = input(f"\n  {t('ai_report_prompt')}: ").strip()
    report_language = detect_report_language(customer_notes, state.language)

    try:
        scan_payload = collect_scan_report(scanner)
    except ConnectionLostError:
        print(f"\n  ❌ {t('not_connected')}")
        return
    except NotConnectedError:
        print(f"\n  ❌ {t('not_connected')}")
        return
    except ScannerError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
        return

    if not _ensure_report_credit(paywall_service):
        return

    report_payload: Dict[str, Any] = {
        "status": "pending",
        "customer_notes": customer_notes,
        "scan_data": scan_payload,
    }
    report_path = get_container().reports.save_report(report_payload)
    print(f"\n  ✅ {t('ai_report_saved', path=str(report_path))}")

    vehicle_payload, vehicle_profiles = prepare_vehicle_profile(scan_payload, state)
    _update_report_vehicle(report_path, vehicle_payload, vehicle_profiles)

    print(f"  {t('ai_report_wait')}")

    spinner = Spinner()
    spinner.start()
    error: Optional[ExternalServiceError] = None
    response: Optional[str] = None
    try:
        report_input = build_report_input(
            scan_payload,
            customer_notes,
            state,
            report_language,
            vehicle_payload=vehicle_payload,
            vehicle_profiles=vehicle_profiles,
        )
        response = request_ai_report(report_input, report_language)
    except ExternalServiceError as exc:
        error = exc
    finally:
        spinner.stop()

    if error:
        update_report_status(report_path, status="error", error=str(error))
        print(f"\n  ❌ {t('ai_report_error')}: {error}")
        return

    if response is None:
        update_report_status(report_path, status="error", error="empty response")
        print(f"\n  ❌ {t('ai_report_error')}: {t('ai_report_empty')}")
        return

    report_json, report_text = extract_report_parts(response)
    if isinstance(report_json, dict):
        report_language = str(report_json.get("language") or report_language).lower()
    report_language = "es" if str(report_language).lower().startswith("es") else "en"

    update_report_status(
        report_path,
        status="complete",
        response=report_text or response,
        response_raw=response,
        report_json=report_json,
        language=report_language,
        model=get_container().ai_config.get_model(),
    )
    print(f"\n  ✅ {t('ai_report_complete')}")
    vin_value = vehicle_payload.get("vin") if isinstance(vehicle_payload, dict) else None
    if vin_value:
        print(f"\n  {t('vin_label')}: {vin_value}")
    print_report_full(report_text or response)
    _export_ai_pdf_to_documents(
        report_path,
        report_json=report_json,
        report_text=report_text or response,
        language=report_language,
    )


def _ensure_report_credit(service) -> bool:
    decision = service.ensure_credit("generate_report", cost=1)
    if decision.bypass:
        print(f"\n  {t('paywall_bypass_enabled')}")
        return True
    if decision.ok:
        return True
    if decision.checkout_url:
        print(f"\n  {t('paywall_checkout_url')}: {decision.checkout_url}")
        print(f"  {t('paywall_checkout_hint')}")
        webbrowser.open(decision.checkout_url)
        print(f"\n  {t('paywall_polling')}")

        balance = service.wait_for_balance(min_paid=1, timeout_seconds=180)
        if balance.paid_credits < 1 and balance.free_remaining < 1:
            print(f"\n  ❌ {t('paywall_payment_required')}")
            return False
        try:
            service.consume("generate_report", cost=1)
            return True
        except Exception as exc:
            print(f"\n  ❌ {t('paywall_error')}: {exc}")
            return False
    if decision.error:
        print(f"\n  ❌ {t('paywall_error')}: {decision.error}")
    return False


def show_reports() -> None:
    print_header(t("ai_report_list"))
    reports = get_container().reports.list_reports()
    if not reports:
        print(f"\n  {t('report_none')}")
        return
    for idx, report in enumerate(reports, start=1):
        model = report.model or "-"
        print(f"  {idx}. {report.report_id} | {report.created_at} | {report.status} | {model}")


def view_report() -> None:
    print_header(t("ai_report_view"))
    report_id = input(f"\n  {t('report_select')}: ").strip()
    if not report_id:
        return
    path = get_container().reports.find_report_by_id(report_id)
    if not path:
        print(f"\n  ❌ {t('report_not_found')}")
        return
    payload = get_container().reports.load_report(path)
    print(f"\n  {t('report_id')}: {payload.get('report_id')}")
    print(f"  {t('report_created')}: {payload.get('created_at')}")
    print(f"  {t('report_status')}: {payload.get('status')}")
    print(f"  {t('report_model')}: {payload.get('model', '-')}")
    print(f"\n  {t('report_customer_notes')}:\n  {payload.get('customer_notes', '')}")
    print(f"\n  {t('report_ai_response')}:\n")
    ai_text = payload.get("ai_response") or payload.get("ai_response_raw") or ""
    print(ai_text)


def export_report_pdf() -> None:
    print_header(t("ai_report_export_pdf"))
    report_id = input(f"\n  {t('report_select')}: ").strip()
    if not report_id:
        return
    path = get_container().reports.find_report_by_id(report_id)
    if not path:
        print(f"\n  ❌ {t('report_not_found')}")
        return
    payload = get_container().reports.load_report(path)
    report_json = payload.get("ai_report_json")
    report_text = payload.get("ai_response")
    if not report_json:
        raw_text = payload.get("ai_response_raw") or payload.get("ai_response") or ""
        report_json, parsed_text = extract_report_parts(raw_text)
        if not report_text:
            report_text = parsed_text
    report_language = None
    if isinstance(report_json, dict):
        report_language = report_json.get("language")
    if not report_language:
        report_language = payload.get("report_language")
    vehicle_payload = payload.get("vehicle") or {}
    output_path = _documents_pdf_path(vehicle_payload)
    try:
        get_container().ai_reports.export_pdf(
            payload,
            str(output_path),
            report_json=report_json,
            report_text=report_text,
            language=report_language,
        )
    except RuntimeError as exc:
        print(f"\n  ❌ {t('ai_report_pdf_error')}: {exc}")
        return
    print(f"\n  ✅ {t('ai_report_pdf_saved', path=str(output_path))}")



def detect_report_language(customer_notes: str, default_language: str) -> str:
    return _detect_report_language(customer_notes, default_language)


def build_report_input(
    scan_payload: Dict[str, Any],
    customer_notes: str,
    state: AppState,
    language: str,
    *,
    vehicle_payload: Optional[Dict[str, Any]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _build_report_input(
        scan_payload,
        customer_notes,
        state,
        language,
        vehicle_payload=vehicle_payload,
        vehicle_profiles=vehicle_profiles,
    )


def extract_report_parts(response: str) -> Tuple[Optional[Dict[str, Any]], str]:
    return _extract_report_parts(response)


def _normalize_field(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def decode_vin_with_ai(vin: str, state: AppState) -> Optional[Dict[str, Any]]:
    return get_container().ai_reports.decode_vin_ai(vin, state.manufacturer)


def decode_vin_with_vpic(vin: str, state: AppState, model_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return get_container().ai_reports.decode_vin_vpic(vin, model_year=model_year)


def prepare_vehicle_profile(
    scan_payload: Dict[str, Any],
    state: AppState,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    vehicle_info = scan_payload.get("vehicle_info") or {}
    user_profile = state.vehicle_profile or {}
    vin = str(vehicle_info.get("vin") or user_profile.get("vin") or "").strip()

    if not vin and not user_profile:
        print(f"\n  {t('vin_decode_no_vin')}")
        from app.presentation.cli.actions.settings import prompt_vehicle_profile_manual

        prompt_vehicle_profile_manual(state)

    vehicle_payload, vehicle_profiles = get_container().ai_reports.prepare_vehicle_profile(scan_payload, state)

    if user_profile and vehicle_payload:
        mismatches = {}
        for field in ["make", "model", "year", "trim"]:
            user_val = user_profile.get(field)
            vin_val = vehicle_payload.get(field)
            if user_val and vin_val and _normalize_field(str(user_val)) != _normalize_field(str(vin_val)):
                mismatches[field] = {"manual": user_val, "vin": vin_val}
        if mismatches:
            vehicle_profiles = dict(vehicle_profiles or {})
            vehicle_profiles["vin_validation"] = {"mismatches": mismatches}
            print(f"  ⚠️  {t('vin_mismatch_warning')}")

    return vehicle_payload, vehicle_profiles


def request_ai_report(report_input: Dict[str, Any], language: str) -> str:
    return get_container().ai_reports.request_report(report_input, language)


def update_report_status(
    path: Any,
    *,
    status: str,
    response: Optional[str] = None,
    response_raw: Optional[str] = None,
    report_json: Optional[Dict[str, Any]] = None,
    language: Optional[str] = None,
    model: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    _update_report_status(
        get_container().reports,
        str(path),
        status=status,
        response=response,
        response_raw=response_raw,
        report_json=report_json,
        language=language,
        model=model,
        error=error,
    )


def print_report_full(response: str) -> None:
    print("\n" + "-" * 60)
    print("  AI REPORT")
    print("-" * 60)
    for line in response.strip().splitlines():
        print(f"  {line}")


def _documents_pdf_path(vehicle_payload: Dict[str, Any]) -> Path:
    return Path(get_container().document_paths.ai_report_pdf_path(vehicle_payload))


def _update_report_vehicle(path: Any, vehicle_payload: Dict[str, Any], vehicle_profiles: Dict[str, Any]) -> None:
    payload = get_container().reports.load_report(str(path))
    payload["vehicle"] = vehicle_payload
    payload["vehicle_profiles"] = vehicle_profiles
    get_container().reports.write_report(str(path), payload)


def _export_ai_pdf_to_documents(
    report_path: Any,
    *,
    report_json: Optional[Dict[str, Any]],
    report_text: str,
    language: str,
) -> None:
    payload = get_container().reports.load_report(str(report_path))
    vehicle_payload = payload.get("vehicle") or {}
    output_path = _documents_pdf_path(vehicle_payload)
    try:
        get_container().ai_reports.export_pdf(
            payload,
            str(output_path),
            report_json=report_json,
            report_text=report_text,
            language=language,
        )
    except RuntimeError as exc:
        print(f"\n  ❌ {t('ai_report_pdf_error')}: {exc}")
        return
    print(f"\n  ✅ {t('ai_report_pdf_saved', path=str(output_path))}")


class Spinner:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frames = ["⏳", "⌛", "🔄"]

    def start(self) -> None:
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
        print("\r", end="")

    def _spin(self) -> None:
        idx = 0
        while not self._stop.is_set():
            frame = self._frames[idx % len(self._frames)]
            print(f"\r  {frame} {t('ai_report_wait')}", end="", flush=True)
            time.sleep(0.4)
            idx += 1
