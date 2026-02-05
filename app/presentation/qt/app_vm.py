from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.application.state import AppState
from app.bootstrap import get_container
from app.presentation.qt.viewmodels import (
    AiReportViewModel,
    ConnectionViewModel,
    LiveMonitorViewModel,
    ReportsViewModel,
    ScanViewModel,
    SettingsViewModel,
)


class MainViewModel(QObject):
    status_changed = Signal()

    def __init__(self, container) -> None:
        super().__init__()
        self.container = container
        self.state: AppState = container.state

        # Services (composition root wiring; keep presentation imports clean).
        self.settings = container.settings
        self.connection = container.connection
        self.uds_discovery = container.uds_discovery
        self.uds_tools = container.uds_tools
        self.vin_cache = container.vin_cache

        # ViewModels (MVVM).
        self.connection_vm = ConnectionViewModel(container.state, container.connection)
        self.scan_vm = ScanViewModel(container.state, container.scans, container.full_scan_reports)
        self.live_monitor_vm = LiveMonitorViewModel(container.state, container.scans)
        self.reports_vm = ReportsViewModel(container.reports, container.pdf_paths)
        self.ai_report_vm = AiReportViewModel(
            container.ai_reports,
            container.ai_config,
            container.paywall,
            container.reports,
            container.pdf_paths,
            container.document_paths,
            container.scans,
        )
        self.settings_vm = SettingsViewModel(container.state, container.settings, container.vehicles)


_VM: Optional[MainViewModel] = None


def set_vm(vm: MainViewModel) -> None:
    global _VM
    _VM = vm


def get_vm() -> MainViewModel:
    global _VM
    if _VM is None:
        _VM = MainViewModel(get_container())
    return _VM

