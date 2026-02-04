from __future__ import annotations

import unittest
from typing import Any, Dict

from app.application.state import AppState
from app.application.use_cases.ai_config import AiConfigService
from app.application.use_cases.connection import ConnectionService
from app.application.use_cases.reports import FullScanReportsService, ReportsService
from app.application.use_cases.scans import ScanService
from app.application.use_cases.uds_discovery import UdsDiscoveryService
from app.application.use_cases.uds_tools import UdsToolsService
from app.domain.entities import NotConnectedError, UdsError
from app.domain.ports import UdsDiscoveryPort
from tests.app_fakes import (
    DummyAiConfig,
    DummyDtcFactory,
    DummyKLineFactory,
    DummyKLineScanner,
    DummyPortsScanner,
    DummyReportRepo,
    DummyFullScanRepo,
    DummyScanner,
    DummyScannerFactory,
    DummyUdsFactory,
)


class DummyDiscovery(UdsDiscoveryPort):
    def __init__(self) -> None:
        self.last_options: Dict[str, Any] = {}

    def discover(self, scanner, options: Dict[str, Any]) -> Dict[str, Any]:
        self.last_options = dict(options)
        return {"modules": [], "protocol": None}


class ApplicationServicesTests(unittest.TestCase):
    def test_connection_try_connect(self) -> None:
        state = AppState(scanner_factory=DummyScannerFactory())
        ports = DummyPortsScanner()
        svc = ConnectionService(state, ports, DummyKLineFactory())
        ok, info, err = svc.try_connect("/dev/ttyFAKE")
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(ports.last_port, "/dev/ttyFAKE")

    def test_connection_try_kline_sets_state(self) -> None:
        state = AppState()
        svc = ConnectionService(state, DummyPortsScanner(), DummyKLineFactory())
        scanner, info, err = svc.try_kline("/dev/ttyFAKE")
        self.assertIsNotNone(scanner)
        self.assertIsNone(err)
        self.assertIs(state.kline_scanner, scanner)

    def test_scan_service_requires_scanner(self) -> None:
        state = AppState()
        svc = ScanService(state)
        with self.assertRaises(NotConnectedError):
            svc.get_vehicle_info()

    def test_scan_service_reads(self) -> None:
        state = AppState()
        scanner = DummyScanner()
        scanner.is_connected = True
        state.scanner = scanner
        svc = ScanService(state)
        info = svc.get_vehicle_info()
        self.assertIn("elm_version", info)

    def test_reports_services(self) -> None:
        reports = ReportsService(DummyReportRepo())
        report_id = reports.save_report({"status": "pending"})
        payload = reports.load_report(report_id)
        self.assertEqual(payload.get("status"), "pending")

        full_scans = FullScanReportsService(DummyFullScanRepo())
        path = full_scans.save(["line1"])
        self.assertTrue(path)

    def test_ai_config_service(self) -> None:
        svc = AiConfigService(DummyAiConfig(api_key="key"))
        self.assertTrue(svc.is_configured())
        self.assertEqual(svc.get_model(), "fake-model")

    def test_uds_tools_requires_connection(self) -> None:
        state = AppState()
        svc = UdsToolsService(state, DummyUdsFactory())
        with self.assertRaises(NotConnectedError):
            svc.build_client("generic", {})

    def test_uds_tools_kline_block(self) -> None:
        state = AppState()
        kline = DummyKLineScanner()
        kline.is_connected = True
        state.kline_scanner = kline
        svc = UdsToolsService(state, DummyUdsFactory())
        with self.assertRaises(UdsError):
            svc.build_client("generic", {})

    def test_uds_tools_build_client(self) -> None:
        state = AppState()
        scanner = DummyScanner()
        scanner.is_connected = True
        state.scanner = scanner
        factory = DummyUdsFactory()
        svc = UdsToolsService(state, factory)
        client = svc.build_client("generic", {"tx_id": "7E0", "rx_id": "7E8"})
        self.assertTrue(factory.created)
        self.assertIsNotNone(client)

    def test_uds_discovery_uses_scanner_factory(self) -> None:
        factory = DummyScannerFactory()
        state = AppState(scanner_factory=factory, dtc_db_factory=DummyDtcFactory())
        discovery = DummyDiscovery()
        svc = UdsDiscoveryService(state, discovery)
        result = svc.discover({"confirm_vin": False})
        self.assertIn("modules", result)
