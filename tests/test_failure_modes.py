from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

from app.domain.entities import ConnectionLostError
from app.presentation.cli.actions.full_scan import run_full_scan
from app.bootstrap import container as container_module
from tests.fakes import build_fake_container
from tests.replay_transport import ReplayFixture, build_replay_scanner
from obd.obd2.base import ConnectionLostError as ObdConnectionLostError, ScannerError as ObdScannerError


class FailureModeTests(unittest.TestCase):
    def _scanner_with_steps(self, steps: List[Dict[str, object]]):
        fixture = ReplayFixture(steps=steps, meta={"headers_on": False}, expected={})
        scanner, _elm = build_replay_scanner(fixture)
        return scanner

    def test_readiness_no_data_returns_empty(self) -> None:
        steps = [
            {"command": "0101", "lines": ["NO DATA"]},
            {"command": "0101", "lines": ["NO DATA"]},
        ]
        scanner = self._scanner_with_steps(steps)
        readiness = scanner.read_readiness()
        self.assertEqual({}, readiness)

    def test_dtc_no_data_returns_empty(self) -> None:
        steps = [
            {"command": "03", "lines": ["NO DATA"]},
            {"command": "03", "lines": ["NO DATA"]},
            {"command": "07", "lines": ["NO DATA"]},
            {"command": "07", "lines": ["NO DATA"]},
            {"command": "0A", "lines": ["NO DATA"]},
            {"command": "0A", "lines": ["NO DATA"]},
        ]
        scanner = self._scanner_with_steps(steps)
        dtcs = scanner.read_dtcs()
        self.assertEqual([], dtcs)

    def test_vehicle_info_handles_missing_vin(self) -> None:
        steps = [
            {"command": "ATDPN", "lines": ["A6"]},
            {"command": "0902", "lines": ["NO DATA"]},
            {"command": "0902", "lines": ["NO DATA"]},
            {"command": "0101", "lines": ["41 01 00 00 00 00"]},
        ]
        scanner = self._scanner_with_steps(steps)
        info = scanner.get_vehicle_info()
        self.assertIn("mil_on", info)
        self.assertNotIn("vin", info)

    def test_readiness_retries_after_no_data(self) -> None:
        steps = [
            {"command": "0101", "lines": ["NO DATA"]},
            {"command": "0101", "lines": ["41 01 80 07 A0 13"]},
        ]
        scanner = self._scanner_with_steps(steps)
        readiness = scanner.read_readiness()
        self.assertTrue(readiness)

    def test_readiness_partial_frame_returns_empty(self) -> None:
        steps = [
            {"command": "0101", "lines": ["41 01 80 07"]},
        ]
        scanner = self._scanner_with_steps(steps)
        readiness = scanner.read_readiness()
        self.assertEqual({}, readiness)

    def test_timeout_raises_scanner_error(self) -> None:
        steps = [
            {"command": "0101", "error": "timeout"},
        ]
        scanner = self._scanner_with_steps(steps)
        with self.assertRaises(ObdScannerError):
            scanner.read_readiness()

    def test_disconnect_mid_scan_aborts(self) -> None:
        steps = [
            {"command": "03", "error": "disconnect"},
        ]
        scanner = self._scanner_with_steps(steps)
        with self.assertRaises(ObdConnectionLostError):
            scanner.read_dtcs()

    def test_cli_disconnect_clears_state(self) -> None:
        class DisconnectingScanner:
            def __init__(self) -> None:
                self._connected = True

            @property
            def is_connected(self) -> bool:
                return self._connected

            def set_manufacturer(self, manufacturer: str) -> None:
                return None

            def set_raw_logger(self, logger) -> None:
                return None

            def set_port(self, port: str) -> None:
                return None

            def connect(self) -> bool:
                self._connected = True
                return True

            def disconnect(self) -> None:
                self._connected = False

            def get_transport(self):
                return None

            def debug_snapshot(self):
                return {}

            def get_vehicle_info(self):
                return {"elm_version": "ELM327-FAKE", "protocol": "ISO 15765-4 (CAN)", "mil_on": "No", "dtc_count": 1}

            def read_dtcs(self):
                raise ConnectionLostError("Device disconnected")

            def read_readiness(self):
                return {}

            def read_live_data(self, pids=None):
                return {}

            def read_freeze_frame(self):
                return {}

            def clear_codes(self) -> bool:
                return False

        with tempfile.TemporaryDirectory(prefix="obd_cli_disconnect_") as tmp_dir:
            container = build_fake_container(Path(tmp_dir))
            state = container.state
            scanner = DisconnectingScanner()
            state.scanner = scanner

            class FailingScans:
                def __init__(self, scanner_obj):
                    self._scanner = scanner_obj

                def get_vehicle_info(self):
                    return self._scanner.get_vehicle_info()

                def read_dtcs(self):
                    return self._scanner.read_dtcs()

                def read_readiness(self):
                    return {}

                def read_live_data(self, pids=None):
                    return {}

            container.scans = FailingScans(scanner)
            container.full_scan_reports = type("Stub", (), {"save": lambda self, lines: "stub"})()

            old_container = container_module._container
            container_module._container = container
            try:
                run_full_scan(state)
            finally:
                container_module._container = old_container

            self.assertFalse(state.scanner.is_connected)
