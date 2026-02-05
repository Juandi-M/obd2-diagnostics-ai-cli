from __future__ import annotations

import unittest
from pathlib import Path
from typing import List

from app.infrastructure.obd.uds_discovery import discover_uds_modules
from app.infrastructure.obd.uds_client import UdsClientFactoryImpl
from tests.replay_transport import ReplayFixture, build_replay_scanner, load_fixture


REPLAY_DIR = Path(__file__).resolve().parent / "fixtures" / "replay"


def _iter_fixtures() -> List[Path]:
    return sorted(REPLAY_DIR.glob("uds_*.json"))


@unittest.skipIf(not _iter_fixtures(), "No UDS replay fixtures found in tests/fixtures/replay")
class UdsReplayTests(unittest.TestCase):
    def test_uds_replays(self) -> None:
        for path in _iter_fixtures():
            with self.subTest(fixture=path.name):
                fixture = load_fixture(path)
                mode = str(fixture.meta.get("mode") or "").lower()
                if not mode:
                    if fixture.expected.get("modules"):
                        mode = "discovery"
                    elif fixture.expected.get("did"):
                        mode = "did"

                if mode == "discovery":
                    self._run_discovery(fixture)
                elif mode == "did":
                    self._run_did(fixture)
                else:
                    self.skipTest(f"Unknown fixture mode for {path.name}")

    def _run_discovery(self, fixture: ReplayFixture) -> None:
        if not fixture.expected:
            self.skipTest("Fixture missing expected outputs")
        _scanner, elm = build_replay_scanner(fixture)
        options = fixture.meta.get("options") or {}
        results = discover_uds_modules(elm, options)
        expected_modules = fixture.expected.get("modules", [])
        if not expected_modules:
            self.skipTest("Fixture missing expected modules")

        discovered = {(m.tx_id.upper(), m.rx_id.upper()) for m in results.get("modules", [])}
        for entry in expected_modules:
            tx_id = str(entry.get("tx_id", "")).upper()
            rx_id = str(entry.get("rx_id", "")).upper()
            self.assertIn((tx_id, rx_id), discovered)

    def _run_did(self, fixture: ReplayFixture) -> None:
        if not fixture.expected:
            self.skipTest("Fixture missing expected outputs")
        _scanner, elm = build_replay_scanner(fixture)

        brand = str(fixture.meta.get("brand") or "generic")
        module_entry = fixture.meta.get("module_entry") or {}
        if not module_entry:
            tx_id = fixture.meta.get("tx_id")
            rx_id = fixture.meta.get("rx_id")
            if tx_id and rx_id:
                module_entry = {"tx_id": tx_id, "rx_id": rx_id, "protocol": fixture.meta.get("protocol", "6")}

        if not module_entry:
            self.skipTest("Fixture missing module entry for DID replay")

        did_value = fixture.expected.get("did")
        if not did_value:
            self.skipTest("Fixture missing expected DID output")

        factory = UdsClientFactoryImpl()
        client = factory.create(elm, brand, module_entry)
        result = client.read_did(brand, did_value.get("did", "F190"))

        for key, value in did_value.items():
            self.assertEqual(result.get(key), value)
