from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError

from app_cli.actions.common import require_connected_scanner
from app_cli.actions.scan_report import collect_scan_report
from app_cli.i18n import t
from openai.client import OpenAIError, chat_completion, get_api_key, get_model
from app_cli.vin_cache import get_vin_cache, set_vin_cache
from app_cli.reports import find_report_by_id, list_reports, save_report
from pdf_gen.paths import report_pdf_path
from pdf_gen.reports_pdf import render_report_pdf
from app_cli.state import AppState
from app_cli.ui import press_enter, print_header, print_menu
from paywall.client import PaywallClient, PaywallError, PaymentRequired
from paywall.config import is_bypass_enabled


def ai_report_menu(state: AppState) -> None:
    while True:
        print_menu(
            t("ai_report_menu"),
            [
                ("1", t("ai_report_new")),
                ("2", t("ai_report_list")),
                ("3", t("ai_report_view")),
                ("4", t("ai_report_export_pdf")),
                ("0", t("back")),
            ],
        )
        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            run_ai_report(state)
            press_enter()
        elif choice == "2":
            show_reports()
            press_enter()
        elif choice == "3":
            view_report()
            press_enter()
        elif choice == "4":
            export_report_pdf()
            press_enter()
        elif choice == "0":
            break


def run_ai_report(state: AppState) -> None:
    if not get_api_key():
        print(f"\n  ❌ {t('ai_report_missing_key')}")
        return

    paywall_client = None
    if not is_bypass_enabled():
        paywall_client = PaywallClient()
        if not paywall_client.is_configured:
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

    if not _ensure_report_credit(paywall_client):
        return

    report_payload: Dict[str, Any] = {
        "status": "pending",
        "customer_notes": customer_notes,
        "scan_data": scan_payload,
    }
    report_path = save_report(report_payload)
    print(f"\n  ✅ {t('ai_report_saved', path=str(report_path))}")

    vehicle_payload, vehicle_profiles = prepare_vehicle_profile(scan_payload, state)

    print(f"  {t('ai_report_wait')}")

    spinner = Spinner()
    spinner.start()
    error: Optional[OpenAIError] = None
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
    except OpenAIError as exc:
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
        model=get_model(),
    )
    print(f"\n  ✅ {t('ai_report_complete')}")
    print_report_summary(report_text or response)


def _ensure_report_credit(client: Optional[PaywallClient]) -> bool:
    if is_bypass_enabled():
        print(f"\n  {t('paywall_bypass_enabled')}")
        return True
    if client is None:
        print(f"\n  ❌ {t('paywall_not_configured')}")
        return False
    try:
        client.consume("generate_report", cost=1)
        return True
    except PaymentRequired:
        try:
            url = client.checkout()
        except PaywallError as exc:
            print(f"\n  ❌ {t('paywall_error')}: {exc}")
            return False

        print(f"\n  {t('paywall_checkout_url')}: {url}")
        print(f"  {t('paywall_checkout_hint')}")
        webbrowser.open(url)
        print(f"\n  {t('paywall_polling')}")

        balance = client.wait_for_balance(min_paid=1, timeout_seconds=180)
        if balance.paid_credits < 1 and balance.free_remaining < 1:
            print(f"\n  ❌ {t('paywall_payment_required')}")
            return False
        try:
            client.consume("generate_report", cost=1)
            return True
        except PaywallError as exc:
            print(f"\n  ❌ {t('paywall_error')}: {exc}")
            return False
    except PaywallError as exc:
        print(f"\n  ❌ {t('paywall_error')}: {exc}")
        return False


def show_reports() -> None:
    print_header(t("ai_report_list"))
    reports = list_reports()
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
    path = find_report_by_id(report_id)
    if not path:
        print(f"\n  ❌ {t('report_not_found')}")
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
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
    path = find_report_by_id(report_id)
    if not path:
        print(f"\n  ❌ {t('report_not_found')}")
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
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
    output_path = report_pdf_path(report_id)
    try:
        render_report_pdf(
            payload,
            output_path,
            report_json=report_json,
            report_text=report_text,
            language=report_language,
        )
    except RuntimeError as exc:
        print(f"\n  ❌ {t('ai_report_pdf_error')}: {exc}")
        return
    print(f"\n  ✅ {t('ai_report_pdf_saved', path=str(output_path))}")



def detect_report_language(customer_notes: str, default_language: str) -> str:
    default = "es" if str(default_language).lower().startswith("es") else "en"
    if not customer_notes:
        return default
    text = customer_notes.lower()
    if re.search(r"[áéíóúñü]", text):
        return "es"

    spanish_words = {
        "el", "la", "los", "las", "y", "pero", "porque", "falla", "ruido", "motor", "cliente",
        "síntoma", "sintoma", "fallo", "vibración", "vibracion", "encendido", "arranque",
    }
    english_words = {
        "the", "and", "but", "because", "engine", "noise", "customer", "symptom", "stall",
        "misfire", "start", "starting", "idle", "rough", "check", "light",
    }

    spanish_hits = sum(1 for word in spanish_words if re.search(rf"\\b{re.escape(word)}\\b", text))
    english_hits = sum(1 for word in english_words if re.search(rf"\\b{re.escape(word)}\\b", text))

    if spanish_hits > english_hits:
        return "es"
    if english_hits > spanish_hits:
        return "en"
    return default


def build_report_input(
    scan_payload: Dict[str, Any],
    customer_notes: str,
    state: AppState,
    language: str,
    *,
    vehicle_payload: Optional[Dict[str, Any]] = None,
    vehicle_profiles: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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

    adapter = "kline" if state.legacy_scanner and state.legacy_scanner.is_connected else "elm327"
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


def extract_report_parts(response: str) -> Tuple[Optional[Dict[str, Any]], str]:
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


def _normalize_field(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def decode_vin_with_ai(vin: str, state: AppState) -> Optional[Dict[str, Any]]:
    system_lines = [
        "You decode VINs into vehicle specs.",
        "Return ONLY valid JSON. No extra text.",
        "If unsure, leave fields empty.",
    ]
    user_lines = [
        f"VIN: {vin}",
        f"Brand selection: {state.manufacturer}",
        "Return JSON with this schema:",
        "{",
        '  "make": "",',
        '  "model": "",',
        '  "year": "",',
        '  "trim": "",',
        '  "engine": "",',
        '  "confidence": "high|medium|low",',
        '  "notes": ""',
        "}",
    ]
    messages = [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]
    response = chat_completion(
        messages,
        temperature=0.0,
        top_p=1.0,
        max_tokens=220,
        model="gpt-4o-mini",
    )
    choices = response.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None


def prepare_vehicle_profile(
    scan_payload: Dict[str, Any],
    state: AppState,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    vehicle_info = scan_payload.get("vehicle_info") or {}
    user_profile = state.vehicle_profile or {}
    vin = str(vehicle_info.get("vin") or user_profile.get("vin") or "").strip()

    vin_profile: Optional[Dict[str, Any]] = None
    vin_attempted = False
    vin_source = None
    if vin:
        cached = get_vin_cache(vin)
        if cached:
            vin_profile = cached
            vin_source = "vin_cache"
        else:
            vin_attempted = True
            print(f"\n  {t('vin_decode_start')}")
            try:
                vin_profile = decode_vin_with_ai(vin, state)
                if vin_profile:
                    set_vin_cache(vin, vin_profile)
                    vin_source = "vin_ai"
            except OpenAIError as exc:
                print(f"  ❌ {t('vin_decode_failed')}: {exc}")
                vin_profile = None
    else:
        print(f"\n  {t('vin_decode_no_vin')}")
        if not user_profile:
            from app_cli.actions.settings import prompt_vehicle_profile_manual

            prompt_vehicle_profile_manual(state)
            user_profile = state.vehicle_profile or {}

    if vin_attempted and (
        not vin_profile
        or not vin_profile.get("make")
        or not vin_profile.get("model")
        or not vin_profile.get("year")
    ):
        print(f"  ❌ {t('vin_decode_failed')}")
        vin_profile = None
        vin_source = None
        if not user_profile:
            from app_cli.actions.settings import prompt_vehicle_profile_manual

            prompt_vehicle_profile_manual(state)
            user_profile = state.vehicle_profile or {}

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

    source = vin_source or ("manual" if user_profile else "ecu")
    validation: Dict[str, Any] = {"source": source}

    if vin_profile and user_profile:
        mismatches = {}
        for field in ["make", "model", "year", "trim"]:
            user_val = user_profile.get(field)
            vin_val = vin_profile.get(field)
            if user_val and vin_val and _normalize_field(str(user_val)) != _normalize_field(str(vin_val)):
                mismatches[field] = {"manual": user_val, "vin": vin_val}
        if mismatches:
            validation["mismatches"] = mismatches
            print(f"  ⚠️  {t('vin_mismatch_warning')}")
        else:
            validation["match"] = True

    profiles = {
        "manual": user_profile or None,
        "vin_decoded": vin_profile or None,
        "validation": validation,
    }
    return vehicle_payload, profiles


def request_ai_report(report_input: Dict[str, Any], language: str) -> str:
    lang = "es" if str(language).lower().startswith("es") else "en"
    if lang == "es":
        system_lines = [
            "Eres un sistema de diagnóstico automotriz profesional.",
            "Escribes reportes técnicos estandarizados para talleres mecánicos.",
            "No uses emojis, jerga, ni menciones IA/ChatGPT.",
            "Mantén un tono formal, directo, y orientado a pruebas.",
            "Si falta evidencia, decláralo en 'Notas y limitaciones' y sugiere cómo confirmarlo.",
        ]
        user_lines = [
            "Genera un reporte en ESPAÑOL con la siguiente estructura fija:",
            "1) Identificación del vehículo",
            "2) Motivo de visita / Síntomas reportados",
            "3) Resultado del escaneo (DTCs, MIL, readiness)",
            "4) Evidencia en datos en vivo (si existe; si no, indicar 'No disponible')",
            "5) Interpretación técnica (basada en evidencia)",
            "6) Causas probables (priorizadas con Alta/Media/Baja)",
            "7) Pruebas recomendadas (pasos enumerados; incluir criterio de confirmación)",
            "8) Acciones recomendadas (solo si se confirma cada causa)",
            "9) Notas y limitaciones",
            "10) Timestamp",
            "",
            "Reglas:",
            "- No inventar datos. Si un dato no viene, indicar 'No especificado'.",
            "- No recomendar reemplazos hasta proponer pruebas de confirmación.",
            "- Máximo 1 página (aprox. 350-500 palabras).",
            "- Usar lenguaje técnico de taller.",
        ]
    else:
        system_lines = [
            "You are a professional automotive diagnostic system.",
            "You write standardized technical reports for auto repair shops.",
            "Do not use emojis, slang, or mention AI/ChatGPT.",
            "Keep a formal, direct, test-oriented tone.",
            "If evidence is missing, state it in 'Notes and limitations' and suggest how to confirm it.",
        ]
        user_lines = [
            "Generate a report in ENGLISH with the following fixed structure:",
            "1) Vehicle identification",
            "2) Reason for visit / reported symptoms",
            "3) Scan results (DTCs, MIL, readiness)",
            "4) Live data evidence (if available; otherwise say 'Not available')",
            "5) Technical interpretation (based on evidence)",
            "6) Probable causes (prioritized with High/Medium/Low)",
            "7) Recommended tests (numbered steps; include confirmation criteria)",
            "8) Recommended actions (only if each cause is confirmed)",
            "9) Notes and limitations",
            "10) Timestamp",
            "",
            "Rules:",
            "- Do not invent data. If a value is missing, write 'Not specified'.",
            "- Do not recommend part replacement until you propose confirmation tests.",
            "- Max 1 page (approx. 350-500 words).",
            "- Use shop-technical language.",
        ]

    output_lines = [
        "",
        "Salida requerida (obligatoria):" if lang == "es" else "Required output (mandatory):",
        "- Devuelve primero un objeto JSON válido." if lang == "es" else "- Return a valid JSON object first.",
        "- Encierra el JSON entre <json> y </json>." if lang == "es" else "- Wrap the JSON between <json> and </json>.",
        "- Luego, en una nueva línea, entrega el reporte en texto plano."
        if lang == "es"
        else "- Then, on a new line, provide the report in plain text.",
        "- Encierra el texto entre <report> y </report>."
        if lang == "es"
        else "- Wrap the text between <report> and </report>.",
        "- No agregues contenido fuera de esas etiquetas."
        if lang == "es"
        else "- Do not add content outside those tags.",
        "",
        "El JSON debe usar este esquema exacto (nombres de campos fijos):"
        if lang == "es"
        else "The JSON must use this exact schema (field names are fixed):",
        "{",
        f'  "language": "{lang}",',
        '  "sections": {',
        '    "1_identificacion_vehiculo": "...",',
        '    "2_motivo_visita": "...",',
        '    "3_resultado_escaneo": "...",',
        '    "4_evidencia_datos_en_vivo": "...",',
        '    "5_interpretacion_tecnica": "...",',
        '    "6_causas_probables": [',
        '      {"prioridad": "Alta|Media|Baja", "causa": "..."}',
        "    ],",
        '    "7_pruebas_recomendadas": [',
        '      {"paso": 1, "descripcion": "...", "criterio_confirmacion": "..."}',
        "    ],",
        '    "8_acciones_recomendadas": [',
        '      {"causa": "...", "accion": "..."}',
        "    ],",
        '    "9_notas_limitaciones": "...",',
        '    "10_timestamp": "..."',
        "  }",
        "}",
        "",
        "Datos de entrada:" if lang == "es" else "Input data:",
        json.dumps(report_input, ensure_ascii=False, indent=2),
    ]
    user_lines = user_lines + output_lines
    messages = [
        {
            "role": "system",
            "content": "\n".join(system_lines),
        },
        {
            "role": "user",
            "content": "\n".join(user_lines),
        },
    ]
    response = chat_completion(messages, temperature=0.2, top_p=0.9, max_tokens=900)
    choices = response.get("choices", [])
    if not choices:
        raise OpenAIError("No response choices returned.")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not content:
        raise OpenAIError("Empty response content.")
    return content


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
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = status
    if response is not None:
        payload["ai_response"] = response
    if response_raw is not None:
        payload["ai_response_raw"] = response_raw
    if report_json is not None:
        payload["ai_report_json"] = report_json
    if language:
        payload["report_language"] = language
    if model:
        payload["model"] = model
    if error:
        payload["error"] = error
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_report_summary(response: str) -> None:
    print("\n" + "-" * 60)
    lines = response.strip().splitlines()
    for line in lines[:20]:
        print(f"  {line}")
    if len(lines) > 20:
        print(f"  ... {t('report_more')}")


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
