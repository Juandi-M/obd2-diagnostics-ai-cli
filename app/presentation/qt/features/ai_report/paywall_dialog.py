from __future__ import annotations

import webbrowser
from typing import Any, Optional, Tuple

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_info, ui_warn
from app.presentation.qt.utils.text import short_id
from app.presentation.qt.workers import Worker


class PaywallDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Paywall / Credits")
        self.paywall = get_vm().ai_report_vm
        self.thread_pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)
        self.api_label = QLabel()
        self.subject_label = QLabel()
        self.balance_label = QLabel()
        self.pending_label = QLabel()
        layout.addWidget(self.api_label)
        layout.addWidget(self.subject_label)
        layout.addWidget(self.balance_label)
        layout.addWidget(self.pending_label)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("primary")
        refresh_btn.clicked.connect(self._refresh)
        checkout_btn = QPushButton("Checkout")
        checkout_btn.clicked.connect(self._checkout)
        reset_btn = QPushButton("Reset Identity")
        reset_btn.clicked.connect(self._reset_identity)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(checkout_btn)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        api_base = self.paywall.paywall_api_base() or "-"
        self.api_label.setText(f"API Base: {api_base}")
        subject = short_id(self.paywall.paywall_subject_id() or "")
        self.subject_label.setText(f"Subject ID: {subject}")
        if not self.paywall.paywall_is_configured():
            cached = self.paywall.paywall_cached_balance()
            pending = self.paywall.paywall_pending_total()
            if cached:
                self.balance_label.setText(f"Cached balance: {cached[0]} free / {cached[1]} paid")
            else:
                self.balance_label.setText("Cached balance: -")
            self.pending_label.setText(f"Pending: {pending}")
            return
        self.balance_label.setText("Balance: …")
        self.pending_label.setText("Pending: …")

        def job():
            balance = self.paywall.paywall_get_balance()
            pending = self.paywall.paywall_pending_total()
            return balance, pending

        worker = Worker(job)
        worker.signals.finished.connect(self._refresh_done)
        self.thread_pool.start(worker)

    def _refresh_done(self, result: Optional[Tuple[Any, int]], exc: Optional[Exception]) -> None:
        if exc:
            ui_warn(self, "Paywall", f"Failed to refresh balance: {exc}")
            return
        if not result:
            self.balance_label.setText("Balance: -")
            self.pending_label.setText("Pending: -")
            return
        balance, pending = result
        self.balance_label.setText(f"Balance: {balance.free_remaining} free / {balance.paid_credits} paid")
        self.pending_label.setText(f"Pending: {pending}")

    def _checkout(self) -> None:
        if not self.paywall.paywall_is_configured():
            ui_warn(self, "Paywall", "Paywall API base not configured.")
            return

        def job():
            return self.paywall.paywall_checkout()

        worker = Worker(job)
        worker.signals.finished.connect(self._checkout_done)
        self.thread_pool.start(worker)

    def _checkout_done(self, result: Optional[str], exc: Optional[Exception]) -> None:
        if exc:
            ui_warn(self, "Paywall", f"Checkout failed: {exc}")
            return
        if result:
            webbrowser.open(result)

    def _reset_identity(self) -> None:
        self.paywall.paywall_reset_identity()
        ui_info(self, "Paywall", "Identity reset.")
        self._refresh()
