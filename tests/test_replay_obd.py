from __future__ import annotations

import unittest
from pathlib import Path

from tests.replay_transport import build_replay_scanner, load_fixture


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "replay" / "obd_scan.json"


@unittest.skipIf(not FIXTURE_PATH.exists(), "Replay fixture missing: tests/fixtures/replay/obd_scan.json")
class ObdReplayTests(unittest.TestCase):
    def test_obd_replay_scan(self) -> None:
        fixture = load_fixture(FIXTURE_PATH)
        if not fixture.expected:
            self.skipTest("Replay fixture missing expected outputs")

        scanner, _elm = build_replay_scanner(fixture)

        vehicle_info = scanner.get_vehicle_info()
        dtcs = scanner.read_dtcs()
        readiness = scanner.read_readiness()

        expected_info = fixture.expected.get("vehicle_info", {})
        for key, value in expected_info.items():
            self.assertEqual(vehicle_info.get(key), value, msg=f"vehicle_info[{key}] mismatch")

        expected_dtcs = fixture.expected.get("dtcs", [])
        if expected_dtcs:
            dtc_codes = sorted(dtc.code for dtc in dtcs)
            self.assertEqual(sorted(expected_dtcs), dtc_codes)

        expected_readiness = fixture.expected.get("readiness", {})
        for monitor, expected in expected_readiness.items():
            status = readiness.get(monitor)
            self.assertIsNotNone(status, msg=f"Missing readiness monitor {monitor}")
            if status is None:
                continue
            if "available" in expected:
                self.assertEqual(expected["available"], status.available)
            if "complete" in expected:
                self.assertEqual(expected["complete"], status.complete)
