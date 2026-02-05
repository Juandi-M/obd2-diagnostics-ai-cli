from __future__ import annotations

from typing import Dict, Optional, Set

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from app.presentation.qt.features.live_data.metrics import ALL_METRICS


def choose_metrics(parent: QWidget, selected_pids: Set[str]) -> Optional[Set[str]]:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Telemetry Dashboard")
    dlg_layout = QVBoxLayout(dialog)
    dlg_layout.addWidget(QLabel("Select metrics to display"))
    checks: Dict[str, QCheckBox] = {}
    for pid, name, _, _, _ in ALL_METRICS:
        cb = QCheckBox(name)
        cb.setChecked(pid in selected_pids)
        checks[pid] = cb
        dlg_layout.addWidget(cb)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    dlg_layout.addWidget(buttons)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    if dialog.exec() != QDialog.Accepted:
        return None
    return {pid for pid, cb in checks.items() if cb.isChecked()}

