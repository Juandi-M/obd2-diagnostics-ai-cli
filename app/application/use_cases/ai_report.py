from __future__ import annotations

import json
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from app.application.state import AppState
from app.domain.ports import AiReportPort, PdfRendererPort, ReportRepository, VinCacheRepository, VinDecoderPort


@dataclass
class AiReportResult:
    report_path: str
    report_json: Optional[Dict[str, Any]]
    report_text: str
    response_raw: str
    language: str
    model: Optional[str]
    vehicle: Dict[str, Any]


def detect_report_language(
    customer_notes: str,
    default_language: str,
    *,
    mode: str = "cli",
) -> str:
    default = "es" if str(default_language).lower().startswith("es") else "en"
    if not customer_notes:
        return default
    text = customer_notes.lower()
    if mode == "gui":
        if any(ch in text for ch in ["á", "é", "í", "ó", "ú", "ñ", "ü"]):
            return "es"
        spanish_words = {
            "el",
            "la",
            "los",
            "las",
            "y",
            "pero",
            "porque",
            "falla",
            "ruido",
            "motor",
            "cliente",
            "síntoma",
            "sintoma",
            "fallo",
            "vibración",
            "vibracion",
            "encendido",
            "arranque",
        }
        english_words = {
            "the",
            "and",
            "but",
            "because",
            "engine",
            "noise",
            "customer",
            "symptom",
            "stall",
            "misfire",
            "start",
            "starting",
            "idle",
            "rough",
            "check",
            "light",
        }
        spanish_hits = sum(1 for word in spanish_words if f" {word} " in f" {text} ")
        english_hits = sum(1 for word in english_words if f" {word} " in f" {text} ")
        if spanish_hits > english_hits:
            return "es"
        if english_hits > spanish_hits:
            return "en"
        return default
    markers = [" el ", " la ", " los ", " las ", " de ", " que ", " para "]
    score = sum(1 for mark in markers if mark in text)
    return "es" if score >= 2 else default


def build_report_input(
    scan_payload: Dict[str, Any],
    customer_notes: str,
    state: AppState,
    language: str,
    *,
    vehicle_payload: Optional[Dict[str, Any]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
    mode: str = "cli",
) -> Dict[str, Any]:
    if mode == "gui":
        vehicle_info = scan_payload.get("vehicle_info") or {}
        dtcs = scan_payload.get("dtcs") or []
        readiness = scan_payload.get("readiness") or {}
        live_data = scan_payload.get("live_data") or {}

        mil_raw = str(vehicle_info.get("mil_on", "")).strip().lower()
        if mil_raw in {"yes", "on", "true"}:
            mil_status = "on"
        elif mil_raw in {"no", "off", "false"}:
            mil_status = "off"
        elif mil_raw:
            mil_status = mil_raw
        else:
            mil_status = None

        readiness_list = []
        for name, status in readiness.items():
            if isinstance(status, dict):
                readiness_list.append(
                    {
                        "monitor": name,
                        "available": status.get("available"),
                        "complete": status.get("complete"),
                        "status": status.get("status"),
                    }
                )

        live_list = []
        for pid, reading in live_data.items():
            if isinstance(reading, dict):
                live_list.append(
                    {
                        "pid": pid,
                        "name": reading.get("name"),
                        "value": reading.get("value"),
                        "unit": reading.get("unit"),
                    }
                )

        adapter = "kline" if state.kline_scanner and state.kline_scanner.is_connected else "elm327"
        locale_time = datetime.now().astimezone().isoformat(timespec="seconds")

        if vehicle_payload is None:
            vehicle_payload = {
                "make": vehicle_info.get("make"),
                "model": vehicle_info.get("model"),
                "year": vehicle_info.get("year"),
                "engine": vehicle_info.get("engine"),
                "trim": None,
                "vin": vehicle_info.get("vin"),
                "protocol": vehicle_info.get("protocol"),
            }

        return {
            "language": language,
            "vehicle": vehicle_payload,
            "complaint": customer_notes or None,
            "dtcs": dtcs,
            "mil_status": mil_status,
            "readiness": readiness_list,
            "freeze_frame": None,
            "live_data": live_list,
            "adapter": adapter,
            "notes": {
                "manufacturer_profile": state.manufacturer,
                "elm_version": vehicle_info.get("elm_version"),
                "headers_mode": vehicle_info.get("headers_mode"),
                "dtc_count": vehicle_info.get("dtc_count"),
                "vehicle_profiles": vehicle_profiles,
            },
            "locale_time": locale_time,
        }

    vehicle_payload = vehicle_payload or {}
    vehicle_profiles = vehicle_profiles or {}
    payload = {
        "vehicle": {
            "make": vehicle_payload.get("make") or "",
            "model": vehicle_payload.get("model") or "",
            "year": vehicle_payload.get("year") or "",
            "trim": vehicle_payload.get("trim") or "",
            "engine": vehicle_payload.get("engine") or "",
            "vin": vehicle_payload.get("vin") or "",
            "protocol": vehicle_payload.get("protocol") or "",
        },
        "vehicle_profiles": vehicle_profiles,
        "customer_notes": customer_notes or "",
        "scan_data": scan_payload,
        "language": language,
        "manufacturer": state.manufacturer,
    }
    return payload


def extract_report_parts(response: str, *, mode: str = "cli") -> Tuple[Optional[Dict[str, Any]], str]:
    if mode == "gui":
        if not response:
            return None, ""
        text = response.strip()
        json_obj: Optional[Dict[str, Any]] = None
        report_text = ""

        tagged = re.search(r"<json>(.*?)</json>", text, re.IGNORECASE | re.DOTALL)
        if tagged:
            json_str = tagged.group(1).strip()
            try:
                json_obj = json.loads(json_str)
            except json.JSONDecodeError:
                json_obj = None
            remainder = text[tagged.end() :].strip()
            report_block = re.search(r"<report>(.*?)</report>", remainder, re.IGNORECASE | re.DOTALL)
            if report_block:
                report_text = report_block.group(1).strip()
            else:
                report_text = remainder
            return json_obj, report_text or text

        decoder = json.JSONDecoder()
        brace_index = text.find("{")
        if brace_index != -1:
            try:
                json_obj, end = decoder.raw_decode(text[brace_index:])
                report_text = text[brace_index + end :].strip()
            except json.JSONDecodeError:
                json_obj = None

        if json_obj and not report_text:
            if isinstance(json_obj, dict):
                report_text = str(json_obj.get("report_text") or json_obj.get("texto") or "")

        if not report_text:
            report_text = text
        return json_obj, report_text

    json_match = re.search(r"<json>(.*?)</json>", response, re.DOTALL | re.IGNORECASE)
    report_match = re.search(r"<report>(.*?)</report>", response, re.DOTALL | re.IGNORECASE)
    report_json: Optional[Dict[str, Any]] = None
    if json_match:
        try:
            report_json = json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            report_json = None
    report_text = report_match.group(1).strip() if report_match else response.strip()
    return report_json, report_text


def _normalize_field(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).strip()


def prepare_vehicle_profile(
    scan_payload: Dict[str, Any],
    state: AppState,
    *,
    vin_cache: VinCacheRepository,
    ai_port: AiReportPort,
    vpic_port: VinDecoderPort,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    vehicle_info = scan_payload.get("vehicle_info") or {}
    vin = _normalize_field(vehicle_info.get("vin"))
    protocol = _normalize_field(vehicle_info.get("protocol"))

    payload: Dict[str, Any] = {
        "make": _normalize_field(state.vehicle_profile.get("make") if state.vehicle_profile else None),
        "model": _normalize_field(state.vehicle_profile.get("model") if state.vehicle_profile else None),
        "year": _normalize_field(state.vehicle_profile.get("year") if state.vehicle_profile else None),
        "trim": _normalize_field(state.vehicle_profile.get("trim") if state.vehicle_profile else None),
        "engine": "",
        "vin": vin,
        "protocol": protocol,
    }

    profiles = dict(state.vehicle_profiles_by_group or {})

    if not vin:
        return payload, profiles

    cached = vin_cache.get(vin)
    if cached:
        payload.update({k: _normalize_field(cached.get(k)) for k in ["make", "model", "year", "trim", "engine"]})
        return payload, profiles

    decoded_vpic = vpic_port.decode_vpic(vin, model_year=payload.get("year") or None)
    decoded_ai = ai_port.decode_vin(vin, state.manufacturer)
    decoded = decoded_vpic or decoded_ai or {}

    if decoded:
        payload.update({k: _normalize_field(decoded.get(k)) for k in ["make", "model", "year", "trim", "engine"]})
        vin_cache.set(vin, decoded)

    return payload, profiles


def update_report_status(
    repo: ReportRepository,
    report_path: str,
    *,
    status: str,
    response: Optional[str] = None,
    response_raw: Optional[str] = None,
    report_json: Optional[Dict[str, Any]] = None,
    language: Optional[str] = None,
    model: Optional[str] = None,
    error: Optional[str] = None,
    vehicle_payload: Optional[Dict[str, Any]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
) -> None:
    payload = repo.load_report(report_path)
    payload["status"] = status
    if response is not None:
        payload["ai_response"] = response
    if response_raw is not None:
        payload["ai_response_raw"] = response_raw
    if report_json is not None:
        payload["ai_report_json"] = report_json
    if language is not None:
        payload["report_language"] = language
    if model is not None:
        payload["model"] = model
    if error is not None:
        payload["error"] = error
    if vehicle_payload is not None:
        payload["vehicle"] = vehicle_payload
    if vehicle_profiles is not None:
        payload["vehicle_profiles"] = vehicle_profiles
    repo.write_report(report_path, payload)


class AiReportService:
    def __init__(
        self,
        ai_port: AiReportPort,
        vpic_port: VinDecoderPort,
        vin_cache: VinCacheRepository,
        reports: ReportRepository,
        pdf_renderer: PdfRendererPort,
    ) -> None:
        self.ai_port = ai_port
        self.vpic_port = vpic_port
        self.vin_cache = vin_cache
        self.reports = reports
        self.pdf_renderer = pdf_renderer

    def generate_report(
        self,
        scan_payload: Dict[str, Any],
        customer_notes: str,
        state: AppState,
        language: str,
        *,
        use_vin_decode: bool = True,
    ) -> AiReportResult:
        report_payload: Dict[str, Any] = {
            "status": "pending",
            "customer_notes": customer_notes,
            "scan_data": scan_payload,
        }
        report_path = self.reports.save_report(report_payload)

        vehicle_payload: Dict[str, Any] = {}
        vehicle_profiles: Dict[str, Any] = {}
        if use_vin_decode:
            vehicle_payload, vehicle_profiles = prepare_vehicle_profile(
                scan_payload,
                state,
                vin_cache=self.vin_cache,
                ai_port=self.ai_port,
                vpic_port=self.vpic_port,
            )
            update_report_status(
                self.reports,
                report_path,
                status="pending",
                vehicle_payload=vehicle_payload,
                vehicle_profiles=vehicle_profiles,
            )

        report_input = build_report_input(
            scan_payload,
            customer_notes,
            state,
            language,
            vehicle_payload=vehicle_payload,
            vehicle_profiles=vehicle_profiles,
        )
        response = self.ai_port.request_report(report_input, language)

        report_json, report_text = extract_report_parts(response)
        report_language = language
        if isinstance(report_json, dict):
            report_language = str(report_json.get("language") or report_language).lower()
        report_language = "es" if str(report_language).lower().startswith("es") else "en"

        update_report_status(
            self.reports,
            report_path,
            status="complete",
            response=report_text or response,
            response_raw=response,
            report_json=report_json,
            language=report_language,
            vehicle_payload=vehicle_payload,
            vehicle_profiles=vehicle_profiles,
        )

        return AiReportResult(
            report_path=report_path,
            report_json=report_json,
            report_text=report_text or response,
            response_raw=response,
            language=report_language,
            model=None,
            vehicle=vehicle_payload,
        )

    def prepare_vehicle_profile(self, scan_payload: Dict[str, Any], state: AppState) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        return prepare_vehicle_profile(
            scan_payload,
            state,
            vin_cache=self.vin_cache,
            ai_port=self.ai_port,
            vpic_port=self.vpic_port,
        )

    def decode_vin_ai(self, vin: str, manufacturer: str) -> Optional[Dict[str, Any]]:
        return self.ai_port.decode_vin(vin, manufacturer)

    def decode_vin_vpic(self, vin: str, model_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.vpic_port.decode_vpic(vin, model_year=model_year)

    def export_pdf(
        self,
        payload: Dict[str, Any],
        output_path: str,
        *,
        report_json: Optional[Dict[str, Any]] = None,
        report_text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        self.pdf_renderer.render(
            payload,
            output_path,
            report_json=report_json,
            report_text=report_text,
            language=language,
        )

    def request_report(self, report_input: Dict[str, Any], language: str) -> str:
        return self.ai_port.request_report(report_input, language)
