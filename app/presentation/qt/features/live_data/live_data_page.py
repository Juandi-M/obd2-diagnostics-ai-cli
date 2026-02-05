from __future__ import annotations

from typing import Any, Callable, Dict

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.application.state import AppState
from app.domain.entities import NotConnectedError
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.dialogs.message_box import ui_warn
from app.presentation.qt.features.live_data.live_data_view import LiveDataView
from app.presentation.qt.workers import Worker


class LiveDataPage(QWidget):
    """Live telemetry page.

    The UI is split into LiveDataView + LiveDashboard; this class only manages
    start/stop + polling. Keep `_stop()` for MainWindow session reset.
    """

    def __init__(self, state: AppState, on_back: Callable[[], None], on_reconnect: Callable[[], None]) -> None:
        super().__init__()
        self.state = state
        self._uses_internal_scroll = True
        self.thread_pool = QThreadPool.globalInstance()

        self.timer = QTimer()
        self.timer.timeout.connect(self._schedule_poll)
        self.poll_in_flight = False

        self.view = LiveDataView(self.state, on_back=on_back, on_reconnect=on_reconnect)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        # Compatibility: some tests (and legacy code) expect direct access to these widgets.
        self.start_btn = self.view.start_btn
        self.stop_btn = self.view.stop_btn

        self.view.start_btn.clicked.connect(self._start)
        self.view.stop_btn.clicked.connect(self._stop)
        self.view.customize_btn.clicked.connect(self._customize)

        self.view.dashboard.set_running(False)

    def refresh_text(self) -> None:
        self.view.refresh_text()

    def _ensure_connected(self) -> bool:
        if not self.state.active_scanner():
            ui_warn(self, "Live Data", "No vehicle connected.")
            return False
        return True

    def _set_running_ui(self, running: bool, status_text: str = "") -> None:
        self.view.start_btn.setEnabled(not running)
        self.view.stop_btn.setEnabled(running)
        self.view.status_label.setText(status_text)
        self.view.dashboard.set_running(running)

    def _customize(self) -> None:
        self.view.dashboard.customize(self)

    def _start(self) -> None:
        if not self._ensure_connected():
            return
        self.state.monitor_interval = float(self.view.interval_spin.value())
        self.timer.setInterval(int(self.state.monitor_interval * 1000))
        self.timer.start()
        self._set_running_ui(True, "Live telemetry running…")
        self._schedule_poll()

    def _stop(self) -> None:
        # Kept for MainWindow session reset compatibility.
        self.timer.stop()
        self._set_running_ui(False, "")

    def _schedule_poll(self) -> None:
        if self.poll_in_flight or not self.timer.isActive():
            return
        self.poll_in_flight = True
        worker = Worker(self._poll_job)
        worker.signals.finished.connect(self._on_poll_done)
        self.thread_pool.start(worker)

    def _poll_job(self) -> Dict[str, Any]:
        if not self.state.active_scanner():
            raise NotConnectedError("Not connected")
        return get_vm().scan_vm.read_live_data(self.view.dashboard.pids())

    def _on_poll_done(self, result: Any, err: Any) -> None:
        self.poll_in_flight = False
        if err:
            ui_warn(self, "Live Data", f"{err}")
            self._stop()
            return
        self.view.dashboard.update_readings(result or {})
