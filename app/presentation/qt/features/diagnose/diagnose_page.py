from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, List, Optional

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QListWidgetItem, QVBoxLayout, QWidget

from app.application.state import AppState
from app.presentation.qt.dialogs.message_box import ui_confirm, ui_warn
from app.presentation.qt.features.diagnose import diagnose_jobs
from app.presentation.qt.features.diagnose.diagnose_view import DiagnoseView
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.workers import Worker


class DiagnosePage(QWidget):
    def __init__(
        self,
        state: AppState,
        on_back: Callable[[], None],
        on_reconnect: Callable[[], None],
        on_ai: Callable[[], None],
    ) -> None:
        super().__init__()
        self.state = state
        self.thread_pool = QThreadPool.globalInstance()
        self.last_output: List[str] = []
        self._pending_label: Optional[str] = None

        self.view = DiagnoseView(state, on_back=on_back, on_reconnect=on_reconnect, on_ai=on_ai)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.view.full_scan_btn.clicked.connect(self._handle_action)
        self.view.read_codes_btn.clicked.connect(self._handle_action)
        self.view.readiness_btn.clicked.connect(self._handle_action)
        self.view.freeze_btn.clicked.connect(self._handle_action)
        self.view.quick_clear_btn.clicked.connect(self._run_clear_codes)

        self.view.lookup_btn.clicked.connect(self._lookup_code)
        self.view.lookup_clear_btn.clicked.connect(self._clear_lookup)
        self.view.search_btn.clicked.connect(self._search_codes)
        self.view.search_input.returnPressed.connect(self._search_codes)

        self.view.clear_btn.clicked.connect(self._clear_output)
        self.view.copy_btn.clicked.connect(self._copy_output)

    def refresh_text(self) -> None:
        self.view.refresh_text()

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            ui_warn(self, "Diagnose", "No vehicle connected.")
            return False
        return True

    def _set_busy(self, busy: bool) -> None:
        self.view.set_busy(busy)

    def _run_clear_codes(self) -> None:
        if not self._ensure_connected():
            return
        title = gui_t(self.state, "confirm_clear_title")
        body = gui_t(self.state, "confirm_clear_body")
        ui_confirm(
            self,
            title,
            body,
            on_yes=lambda: self._run_job(diagnose_jobs.clear_codes, gui_t(self.state, "clear_codes_action")),
        )

    def _run_job(self, job: Callable[[AppState], str], label: str) -> None:
        if not self._ensure_connected():
            return
        self._pending_label = label
        self._set_busy(True)
        worker = Worker(job, self.state)
        worker.signals.finished.connect(self._on_job_done)
        self.thread_pool.start(worker)

    def _handle_action(self) -> None:
        if not self._ensure_connected():
            return
        sender = self.sender()
        if sender == self.view.full_scan_btn:
            job = diagnose_jobs.full_scan
            label = gui_t(self.state, "full_scan")
        elif sender == self.view.read_codes_btn:
            job = diagnose_jobs.read_codes
            label = gui_t(self.state, "read_codes")
        elif sender == self.view.readiness_btn:
            job = diagnose_jobs.readiness
            label = gui_t(self.state, "readiness")
        else:
            job = diagnose_jobs.freeze_frame
            label = gui_t(self.state, "freeze_frame")
        self._run_job(job, label)

    def _on_job_done(self, result: Any, err: Any) -> None:
        self._set_busy(False)
        if err:
            ui_warn(self, "Diagnose", f"Failed: {err}")
            return
        if isinstance(result, str):
            self.view.set_output_text(result)
            self.last_output = result.splitlines()
            self._store_session_result(self._pending_label or "Scan", result)
        self._pending_label = None

    def _store_session_result(self, label: str, output: str) -> None:
        entry = {"title": label, "output": output, "timestamp": datetime.now().isoformat(timespec="seconds")}
        self.state.session_results = [entry]

    def _clear_output(self) -> None:
        self.view.output.clear()
        self.last_output = []
        self._pending_label = None

    def _copy_output(self) -> None:
        self.view.copy_output()

    def _lookup_code(self) -> None:
        code = self.view.lookup_input.text().strip().upper()
        self.view.lookup_input.setText(code)
        self.view.lookup_error.setText("")
        if not code:
            self.view.lookup_error.setText(gui_t(self.state, "code_missing"))
            self.view.lookup_result_body.setText(gui_t(self.state, "code_hint"))
            return
        if not re.match(r"^[PBUC][0-3][0-9A-F]{3}$", code):
            self.view.lookup_error.setText(gui_t(self.state, "code_invalid"))
            self.view.lookup_result_body.setText(gui_t(self.state, "code_hint"))
            return
        dtc_db = self.state.ensure_dtc_db()
        info = dtc_db.lookup(code)
        if not info:
            self.view.lookup_result_body.setText(f"{code}: not found in library.")
            self.view.set_output_text(f"Code {code} not found in library.")
            return
        details = [f"{code} — {info.description}"]
        if info.system:
            details.append(f"System: {info.system}")
        if info.subsystem:
            details.append(f"Subsystem: {info.subsystem}")
        self.view.lookup_result_body.setText(" | ".join(details))
        lines: List[str] = []
        lines.append(f"{code} — {info.description}")
        if info.system:
            lines.append(f"System: {info.system}")
        if info.subsystem:
            lines.append(f"Subsystem: {info.subsystem}")
        self.view.set_output_text("\n".join(lines))

    def _clear_lookup(self) -> None:
        self.view.lookup_input.clear()
        self.view.lookup_error.setText("")
        self.view.lookup_result_body.setText(gui_t(self.state, "code_hint"))

    def _search_codes(self) -> None:
        query = self.view.search_input.text().strip()
        self.view.search_results.clear()
        if not query:
            self.view.search_results.addItem(gui_t(self.state, "search_prompt"))
            return
        dtc_db = self.state.ensure_dtc_db()
        results = dtc_db.search(query)
        if not results:
            self.view.search_results.addItem(gui_t(self.state, "search_none"))
            return
        for info in results[:20]:
            item = QListWidgetItem(f"{info.code}: {info.description}")
            self.view.search_results.addItem(item)
        if len(results) > 20:
            self.view.search_results.addItem(f"... +{len(results) - 20} more")

