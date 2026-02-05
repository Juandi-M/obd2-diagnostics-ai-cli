from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info, ui_warn
from app.presentation.qt.features.ai_report.ai_report_viewer import AIReportViewer
from app.presentation.qt.features.ai_report.report_presenters import build_preview_package, list_report_items
from app.presentation.qt.utils.ai_report import documents_pdf_path, extract_report_parts


class _AIReportPage(Protocol):
    state: AppState
    view: Any
    current_report_path: Optional[Path]


def refresh_reports(page: _AIReportPage, *_: Any) -> None:
    selected_id = None
    cur = page.view.report_list.currentItem()
    if isinstance(cur, QListWidgetItem):
        selected_id = cur.data(Qt.UserRole)

    page.view.report_list.clear()
    items = list_report_items(
        page.state,
        query=page.view.search_input.text(),
        status_filter=page.view.status_filter.currentText(),
        date_filter=page.view.date_filter.currentText(),
    )
    for report_id, label in items:
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, report_id)
        page.view.report_list.addItem(item)

    if selected_id is None:
        return
    for i in range(page.view.report_list.count()):
        it = page.view.report_list.item(i)
        if it and it.data(Qt.UserRole) == selected_id:
            page.view.report_list.setCurrentRow(i)
            return


def load_selected_report(page: _AIReportPage, *_: Any) -> None:
    item = page.view.report_list.currentItem()
    if not item:
        return
    report_id = item.data(Qt.UserRole)
    path = get_vm().reports_vm.find_report_by_id(report_id)
    if not path:
        return
    payload = get_vm().reports_vm.load_report(str(path))
    page.current_report_path = Path(path)
    pkg = build_preview_package(
        page.state,
        report_id=str(report_id),
        report_path=str(path),
        payload=payload,
    )
    page.view.preview.setPlainText(pkg["preview_text"])
    page.view.preview_meta.setText(pkg["preview_meta"])
    page.view.dtc_chip.setText(pkg["dtc_chip"])
    page.view.readiness_chip.setText(pkg["readiness_chip"])


def toggle_favorite(page: _AIReportPage, *_: Any) -> None:
    item = page.view.report_list.currentItem()
    if not item:
        return
    report_id = item.data(Qt.UserRole)
    path = get_vm().reports_vm.find_report_by_id(report_id)
    if not path:
        return
    payload = get_vm().reports_vm.load_report(str(path))
    payload["favorite"] = not bool(payload.get("favorite"))
    get_vm().reports_vm.write_report(str(path), payload)
    refresh_reports(page)


def export_pdf(page: _AIReportPage, *_: Any) -> None:
    item = page.view.report_list.currentItem()
    if not item:
        ui_info(page, "Export", "Select a report first.")
        return
    report_id = item.data(Qt.UserRole)
    path = get_vm().reports_vm.find_report_by_id(report_id)
    if not path:
        ui_warn(page, "Export", "Report not found.")
        return
    payload = get_vm().reports_vm.load_report(str(path))
    report_json = payload.get("ai_report_json")
    report_text = payload.get("ai_response")
    if not report_json:
        raw_text = payload.get("ai_response_raw") or payload.get("ai_response") or ""
        report_json, parsed_text = extract_report_parts(raw_text)
        if not report_text:
            report_text = parsed_text
    language = payload.get("report_language")
    vehicle_payload = payload.get("vehicle") or {}
    output_path = payload.get("pdf_path") or str(documents_pdf_path(vehicle_payload))
    try:
        get_vm().ai_report_vm.export_pdf(
            payload,
            str(output_path),
            report_json=report_json,
            report_text=report_text,
            language=language,
        )
    except RuntimeError as exc:
        ui_warn(page, "Export", f"PDF failed: {exc}")
        return
    payload["pdf_path"] = str(output_path)
    get_vm().reports_vm.write_report(str(path), payload)
    window = page.view.window()
    if hasattr(window, "show_toast"):
        window.show_toast(f"PDF saved: {output_path}")
    else:
        ui_info(page, "Export", f"PDF saved at:\n{output_path}")


def open_viewer(page: _AIReportPage, *_: Any) -> None:
    item = page.view.report_list.currentItem()
    if not item:
        ui_info(page, "Viewer", "Select a report first.")
        return
    report_id = item.data(Qt.UserRole)
    path = get_vm().reports_vm.find_report_by_id(report_id)
    if not path:
        ui_warn(page, "Viewer", "Report not found.")
        return
    viewer = AIReportViewer(path, page.view)
    viewer.exec()

