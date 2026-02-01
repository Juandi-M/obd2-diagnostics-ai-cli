from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List, Optional

from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError

from app.actions.common import require_connected_scanner
from app.actions.scan_report import collect_scan_report
from app.i18n import t
from openai.client import OpenAIError, chat_completion, get_api_key, get_model
from app.reports import ReportMeta, find_report_by_id, list_reports, save_report
from app.state import AppState
from app.ui import press_enter, print_header, print_menu


def ai_report_menu(state: AppState) -> None:
    while True:
        print_menu(
            t("ai_report_menu"),
            [
                ("1", t("ai_report_new")),
                ("2", t("ai_report_list")),
                ("3", t("ai_report_view")),
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
        elif choice == "0":
            break


def run_ai_report(state: AppState) -> None:
    if state.report_requests >= state.report_limit:
        print(f"\n  ⚠️  {t('ai_report_limit')}")
        print(f"  {t('ai_report_paywall')}")
        return

    if not get_api_key():
        print(f"\n  ❌ {t('ai_report_missing_key')}")
        return

    scanner = require_connected_scanner(state.scanner)
    if not scanner:
        return

    print_header(t("ai_report_header"))
    customer_notes = input(f"\n  {t('ai_report_prompt')}: ").strip()

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

    report_payload: Dict[str, Any] = {
        "status": "pending",
        "customer_notes": customer_notes,
        "scan_data": scan_payload,
    }
    report_path = save_report(report_payload)
    print(f"\n  ✅ {t('ai_report_saved', path=str(report_path))}")

    state.report_requests += 1
    print(f"  {t('ai_report_wait')}")

    spinner = Spinner()
    spinner.start()
    error: Optional[OpenAIError] = None
    response: Optional[str] = None
    try:
        response = request_ai_report(scan_payload, customer_notes)
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

    update_report_status(report_path, status="complete", response=response, model=get_model())
    print(f"\n  ✅ {t('ai_report_complete')}")
    print_report_summary(response)


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
    print(payload.get("ai_response", ""))


def request_ai_report(scan_payload: Dict[str, Any], customer_notes: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an automotive diagnostic assistant. Review the scan data and "
                "customer notes. Provide a clear summary, likely causes, recommended "
                "next steps, and safety considerations. Use concise bullet points."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "customer_notes": customer_notes,
                    "scan_data": scan_payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]
    response = chat_completion(messages)
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
    model: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = status
    if response is not None:
        payload["ai_response"] = response
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
