from __future__ import annotations

import builtins
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import List

from app.application.state import AppState
from app.bootstrap import container as container_module
from app.presentation.cli.actions.live_monitor import live_monitor
from tests.fakes import build_fake_container, FakeScanner


class InputPatcher:
    def __init__(self, responses: List[str]) -> None:
        self._responses = iter(responses)
        self._original = None

    def __enter__(self) -> None:
        self._original = builtins.input

        def _fake_input(prompt: str = "") -> str:
            try:
                return next(self._responses)
            except StopIteration as exc:
                raise AssertionError("Unexpected input prompt") from exc

        builtins.input = _fake_input

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._original is not None:
            builtins.input = self._original


class TrackingLogger:
    def __init__(self) -> None:
        self.started = False
        self.ended = False
        self.logged = 0

    def start_session(self, format: str = "csv") -> str:
        self.started = True
        return "session-0001"

    def log_readings(self, readings):
        self.logged += 1

    def end_session(self):
        self.ended = True
        return {"file": "session-0001", "duration_seconds": 0, "reading_count": self.logged}


class TrackingTelemetryService:
    def __init__(self, logger: TrackingLogger) -> None:
        self._logger = logger

    def create_logger(self):
        return self._logger


class CancellationTests(unittest.TestCase):
    def test_cli_cancel_live_monitor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obd_cli_cancel_") as tmp_dir:
            container = build_fake_container(Path(tmp_dir))
            state = container.state
            scanner = FakeScanner()
            scanner.is_connected = True
            state.scanner = scanner
            state.monitor_interval = 0.0

            def _read_live_data(pids=None):
                state.stop_monitoring = True
                return {}

            container.scans.read_live_data = _read_live_data  # type: ignore[assignment]

            tracker = TrackingLogger()
            container.telemetry_log = TrackingTelemetryService(tracker)

            old_container = container_module._container
            container_module._container = container
            old_sleep = time.sleep
            time.sleep = lambda _: None
            try:
                with InputPatcher(["y"]):
                    live_monitor(state)
            finally:
                time.sleep = old_sleep
                container_module._container = old_container

            self.assertTrue(tracker.started)
            self.assertTrue(tracker.ended)
            self.assertTrue(state.stop_monitoring)

    def test_gui_cancel_live_monitor(self) -> None:
        try:
            from PySide6.QtWidgets import QApplication
            from app.presentation.qt.main import LiveDataPage
        except Exception:
            self.skipTest("PySide6 not available")

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication([])

        state = AppState()
        scanner = FakeScanner()
        scanner.is_connected = True
        state.scanner = scanner

        page = LiveDataPage(state, on_back=lambda: None, on_reconnect=lambda: None)
        page._schedule_poll = lambda: None  # type: ignore[assignment]

        page._start()
        self.assertTrue(page.timer.isActive())

        page._stop()
        self.assertFalse(page.timer.isActive())
        self.assertTrue(page.start_btn.isEnabled())
        self.assertFalse(page.stop_btn.isEnabled())
