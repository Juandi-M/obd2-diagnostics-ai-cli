from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.application.state import AppState
from app.domain.entities import ExternalServiceError, NotConnectedError, PaymentRequiredError
from app.presentation.qt.app_vm import get_vm


def documents_pdf_path(vehicle_payload: Dict[str, Any]) -> Path:
    return Path(get_vm().ai_report_vm.document_pdf_path(vehicle_payload))


def detect_report_language(customer_notes: str, default_language: str) -> str:
    return get_vm().ai_report_vm.detect_report_language(customer_notes, default_language, mode="gui")


def extract_report_parts(response: str) -> Tuple[Optional[Dict[str, Any]], str]:
    return get_vm().ai_report_vm.extract_report_parts(response, mode="gui")


def format_report_summary(response: str) -> str:
    lines = ["-" * 60]
    body_lines = response.strip().splitlines()
    for line in body_lines[:20]:
        lines.append(f"  {line}")
    if len(body_lines) > 20:
        lines.append("  ... (more)")
    return "\n".join(lines)


def build_report_input(
    scan_payload: Dict[str, Any],
    customer_notes: str,
    state: AppState,
    language: str,
    *,
    vehicle_payload: Optional[Dict[str, Any]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return get_vm().ai_report_vm.build_report_input(
        scan_payload,
        customer_notes,
        state,
        language,
        vehicle_payload=vehicle_payload,
        vehicle_profiles=vehicle_profiles,
        mode="gui",
    )


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
    get_vm().ai_report_vm.update_report_status(
        str(path),
        status=status,
        response=response,
        response_raw=response_raw,
        report_json=report_json,
        language=language,
        model=model,
        error=error,
    )


def prepare_vehicle_payload(
    scan_payload: Dict[str, Any],
    state: AppState,
    *,
    use_vin_decode: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
    vehicle_info = scan_payload.get("vehicle_info") or {}
    user_profile = state.vehicle_profile or {}
    vin = str(vehicle_info.get("vin") or user_profile.get("vin") or "").strip()

    vin_profile: Optional[Dict[str, Any]] = None
    if vin and use_vin_decode:
        cached = get_vm().vin_cache.get(vin)
        if cached:
            vin_profile = cached
        else:
            model_year = user_profile.get("year") or vehicle_info.get("year")
            vin_profile = get_vm().ai_report_vm.decode_vin_vpic(vin, model_year=model_year)
            if vin_profile:
                get_vm().vin_cache.set(vin, vin_profile)
            if not vin_profile:
                try:
                    vin_profile = get_vm().ai_report_vm.decode_vin_ai(vin, state.manufacturer)
                except ExternalServiceError:
                    vin_profile = None
                if vin_profile:
                    get_vm().vin_cache.set(vin, vin_profile)

    def pick(field: str) -> Optional[str]:
        if vin_profile and vin_profile.get(field):
            return vin_profile.get(field)
        if user_profile and user_profile.get(field):
            return user_profile.get(field)
        return vehicle_info.get(field)

    vehicle_payload = {
        "make": pick("make"),
        "model": pick("model"),
        "year": pick("year"),
        "engine": pick("engine"),
        "trim": pick("trim"),
        "vin": vin or vehicle_info.get("vin"),
        "protocol": vehicle_info.get("protocol"),
    }

    mismatch = False
    if vin_profile and user_profile:
        for field in ["make", "model", "year", "trim"]:
            user_val = user_profile.get(field)
            vin_val = vin_profile.get(field)
            if user_val and vin_val and str(user_val).strip().lower() != str(vin_val).strip().lower():
                mismatch = True
                break

    profiles = {
        "manual": user_profile or None,
        "vin_decoded": vin_profile or None,
    }
    return vehicle_payload, profiles, mismatch


def generate_report_job(notes: str, state: AppState, *, use_vin_decode: bool) -> Dict[str, Any]:
    scanner = state.active_scanner()
    if not scanner:
        raise NotConnectedError("Not connected")

    scan_payload = get_vm().scan_vm.collect_scan_report()
    report_payload = {
        "status": "pending",
        "customer_notes": notes,
        "scan_data": scan_payload,
    }
    report_path = get_vm().reports_vm.save_report(report_payload)

    try:
        vehicle_payload, vehicle_profiles, mismatch = prepare_vehicle_payload(
            scan_payload,
            state,
            use_vin_decode=use_vin_decode,
        )
        report_snapshot = get_vm().reports_vm.load_report(str(report_path))
        report_snapshot["vehicle"] = vehicle_payload
        report_snapshot["vehicle_profiles"] = vehicle_profiles
        get_vm().reports_vm.write_report(str(report_path), report_snapshot)

        report_language = detect_report_language(notes, state.language)
        report_input = build_report_input(
            scan_payload,
            notes,
            state,
            report_language,
            vehicle_payload=vehicle_payload,
            vehicle_profiles=vehicle_profiles,
        )

        paywall = get_vm().ai_report_vm
        if not paywall.paywall_is_bypass_enabled():
            if not paywall.paywall_is_configured():
                raise RuntimeError("Paywall API base not configured")
            paywall.paywall_consume("generate_report", cost=1)

        response = get_vm().ai_report_vm.request_report(report_input, report_language)
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
            model=get_vm().ai_report_vm.get_model(),
        )

        pdf_path = documents_pdf_path(vehicle_payload)
        try:
            get_vm().ai_report_vm.export_pdf(
                get_vm().reports_vm.load_report(str(report_path)),
                str(pdf_path),
                report_json=report_json,
                report_text=report_text or response,
                language=report_language,
            )
            report_snapshot = get_vm().reports_vm.load_report(str(report_path))
            report_snapshot["pdf_path"] = str(pdf_path)
            get_vm().reports_vm.write_report(str(report_path), report_snapshot)
        except Exception:
            pdf_path = None

        return {
            "path": report_path,
            "text": report_text or response,
            "mismatch": mismatch,
            "vin": vehicle_payload.get("vin"),
            "pdf_path": str(pdf_path) if pdf_path else None,
        }
    except PaymentRequiredError:
        update_report_status(report_path, status="error", error="Payment required")
        raise
    except Exception as exc:
        update_report_status(report_path, status="error", error=str(exc))
        raise
