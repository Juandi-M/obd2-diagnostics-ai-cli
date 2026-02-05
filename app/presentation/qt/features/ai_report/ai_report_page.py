from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from app.application.state import AppState
from app.domain.entities import PaymentRequiredError
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info, ui_warn
from app.presentation.qt.features.ai_report.ai_report_view import AIReportView
from app.presentation.qt.features.ai_report.paywall_dialog import PaywallDialog
from app.presentation.qt.features.ai_report.report_handlers import (
    export_pdf,
    load_selected_report,
    open_viewer,
    refresh_reports,
    toggle_favorite,
)
from app.presentation.qt.i18n import gui_t
from app.presentation.qt.utils.ai_report import format_report_summary, generate_report_job
from app.presentation.qt.utils.text import header_lines
from app.presentation.qt.workers import Worker


class AIReportPage(QWidget):
    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self.thread_pool = QThreadPool.globalInstance()
        self.current_report_path: Optional[Path] = None

        self.view = AIReportView(self.state, on_back=on_back, on_reconnect=on_reconnect)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        # Compatibility: used by MainWindow session reset helper.
        self.preview = self.view.preview

        self.view.refresh_credits_btn.clicked.connect(self._refresh_balance)
        self.view.manage_credits_btn.clicked.connect(self._open_paywall)
        self.view.buy_credits_btn.clicked.connect(self._open_paywall)
        self.view.generate_btn.clicked.connect(self._generate_report)

        self.view.search_input.textChanged.connect(partial(refresh_reports, self))
        self.view.status_filter.currentIndexChanged.connect(partial(refresh_reports, self))
        self.view.date_filter.currentIndexChanged.connect(partial(refresh_reports, self))
        self.view.refresh_list_btn.clicked.connect(partial(refresh_reports, self))
        self.view.favorite_btn.clicked.connect(partial(toggle_favorite, self))
        self.view.export_btn.clicked.connect(partial(export_pdf, self))
        self.view.view_btn.clicked.connect(partial(open_viewer, self))
        self.view.report_list.itemSelectionChanged.connect(partial(load_selected_report, self))
        self.view.copy_report_btn.clicked.connect(self._copy_report)

        self._refresh_balance()
        refresh_reports(self)

    def refresh_text(self) -> None:
        self.view.refresh_text()
        self._refresh_balance()
        refresh_reports(self)

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            ui_warn(self, "AI Report", "No vehicle connected.")
            return False
        return True

    def _copy_report(self) -> None:
        QApplication.clipboard().setText(self.view.preview.toPlainText())
        window = self.window()
        if hasattr(window, "show_toast"):
            window.show_toast("Report copied.")

    def _set_generating(self, generating: bool, text: str = "") -> None:
        self.view.generate_btn.setEnabled(not generating)
        self.view.loading_bar.setVisible(generating)
        self.view.status_label.setText(text if generating else "")

    def _refresh_balance(self) -> None:
        paywall = get_vm().ai_report_vm
        if paywall.paywall_is_bypass_enabled():
            self.view.credits_label.setText("Credits: Superuser bypass enabled")
            return

        if not paywall.paywall_is_configured():
            cached = paywall.paywall_cached_balance()
            pending = paywall.paywall_pending_total()
            if cached:
                self.view.credits_label.setText(
                    f"Credits (cached): {cached[0]} free / {cached[1]} paid (pending {pending})"
                )
            else:
                self.view.credits_label.setText("Credits: Paywall not configured")
            return

        self.view.credits_label.setText("Credits: …")

        def job() -> Tuple[Any, int]:
            balance = paywall.paywall_get_balance()
            pending = paywall.paywall_pending_total()
            return balance, pending

        worker = Worker(job)
        worker.signals.finished.connect(self._on_balance_done)
        self.thread_pool.start(worker)

    def _on_balance_done(self, result: Any, err: Any) -> None:
        if err:
            self.view.credits_label.setText(f"Credits: Error ({err})")
            return
        if not result:
            self.view.credits_label.setText("Credits: -")
            return
        balance, pending = result
        self.view.credits_label.setText(
            f"Credits: {balance.free_remaining} free / {balance.paid_credits} paid (pending {pending})"
        )

    def _open_paywall(self) -> None:
        dialog = PaywallDialog(self)
        dialog.exec()
        self._refresh_balance()

    def _generate_report(self) -> None:
        if not self._ensure_connected():
            return
        if not get_vm().ai_report_vm.is_configured():
            ui_warn(self, "AI Report", "Missing OPENAI_API_KEY.")
            return

        notes = self.view.notes.toPlainText().strip()
        self._set_generating(True, "Generating report…")
        worker = Worker(generate_report_job, notes, self.state, use_vin_decode=self.view.use_vin_decode.isChecked())
        worker.signals.finished.connect(self._on_generate_done)
        self.thread_pool.start(worker)

    def _on_generate_done(self, result: Any, err: Any) -> None:
        self._set_generating(False)
        if err:
            if isinstance(err, PaymentRequiredError):
                ui_warn(self, "Paywall", "Payment required to generate report.")
                self._open_paywall()
            else:
                ui_warn(self, "AI Report", f"Failed: {err}")
            return

        refresh_reports(self)
        if isinstance(result, dict):
            preview_text = result.get("text") or ""
            summary = format_report_summary(preview_text)
            hdr = header_lines("AI DIAGNOSTIC REPORT")
            vin_value = result.get("vin")
            if vin_value:
                hdr.append(f"  {gui_t(self.state, 'vin_label')}: {vin_value}")
                self.state.last_vin = vin_value
            self.view.preview.setPlainText("\n".join(hdr) + "\n" + summary)
            if result.get("mismatch"):
                ui_info(self, "VIN mismatch", "VIN data differs from manual profile. Review vehicle details.")
            if result.get("pdf_path"):
                window = self.window()
                if hasattr(window, "show_toast"):
                    window.show_toast(f"PDF saved at: {result.get('pdf_path')}")
        self._refresh_balance()
