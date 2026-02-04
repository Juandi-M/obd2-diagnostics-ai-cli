from __future__ import annotations

import unittest
from dataclasses import fields
from typing import List

from app.domain.entities import ModuleEntry, ReportMeta, ScanData, VehicleProfile
from app.infrastructure.ai.adapters import AiConfigAdapter, AiReportAdapter, VinDecoderAdapter
from app.infrastructure.billing.paywall_adapter import PaywallAdapter
from app.infrastructure.obd.ports_scanner import PortsScannerImpl
from app.infrastructure.obd.scanner_adapter import (
    DtcDatabaseAdapter,
    DtcDatabaseFactoryImpl,
    KLineScannerAdapter,
    KLineScannerFactoryImpl,
    OBDScannerAdapter,
    OBDScannerFactory,
)
from app.infrastructure.obd.telemetry_logger import TelemetryLoggerAdapter, TelemetryLoggerFactoryImpl
from app.infrastructure.obd.uds_client import UdsClientAdapter, UdsClientFactoryImpl
from app.infrastructure.obd.uds_discovery import UdsDiscoveryService
from app.infrastructure.persistence.data_path_adapter import DataPathAdapter
from app.infrastructure.persistence.document_paths import DocumentPathAdapter
from app.infrastructure.persistence.reports import ReportRepositoryImpl, FullScanReportRepositoryImpl
from app.infrastructure.persistence.settings_store import SettingsRepositoryImpl
from app.infrastructure.persistence.vin_cache import VinCacheRepositoryImpl
from app.infrastructure.reporting.pdf_paths import PdfPathAdapter
from app.infrastructure.reporting.pdf_renderer import PdfReportRenderer
from app.infrastructure.i18n.repository import I18nRepositoryImpl


class PortContractTests(unittest.TestCase):
    def _assert_methods(self, cls: type, methods: List[str]) -> None:
        for name in methods:
            with self.subTest(cls=cls.__name__, method=name):
                self.assertTrue(hasattr(cls, name), f"{cls.__name__} missing {name}")

    def test_adapter_contracts(self) -> None:
        contracts = [
            (OBDScannerAdapter, [
                "is_connected",
                "set_manufacturer",
                "set_raw_logger",
                "set_port",
                "connect",
                "disconnect",
                "get_transport",
                "debug_snapshot",
                "get_vehicle_info",
                "read_dtcs",
                "read_readiness",
                "read_live_data",
                "read_freeze_frame",
                "clear_codes",
            ]),
            (KLineScannerAdapter, [
                "is_connected",
                "is_kline",
                "set_raw_logger",
                "set_manufacturer",
                "disconnect",
                "read_dtcs",
                "clear_dtcs",
                "read_pid",
            ]),
            (OBDScannerFactory, ["create"]),
            (KLineScannerFactoryImpl, ["create", "detect"]),
            (DtcDatabaseAdapter, ["lookup", "search", "set_manufacturer"]),
            (DtcDatabaseFactoryImpl, ["create"]),
            (PortsScannerImpl, ["scan_usb_ports", "scan_ble_devices", "try_connect"]),
            (AiReportAdapter, ["decode_vin", "request_report"]),
            (VinDecoderAdapter, ["decode_vpic"]),
            (AiConfigAdapter, ["get_api_key", "get_model"]),
            (PaywallAdapter, [
                "is_configured",
                "is_bypass_enabled",
                "api_base",
                "set_api_base",
                "subject_id",
                "cached_balance",
                "get_balance",
                "pending_total",
                "ensure_identity",
                "consume",
                "checkout",
                "wait_for_balance",
                "reset_identity",
            ]),
            (PdfReportRenderer, ["render"]),
            (PdfPathAdapter, ["report_pdf_path"]),
            (DocumentPathAdapter, ["ai_report_pdf_path"]),
            (DataPathAdapter, ["raw_log_path"]),
            (ReportRepositoryImpl, ["save_report", "list_reports", "load_report", "find_report_by_id", "write_report"]),
            (FullScanReportRepositoryImpl, ["save", "list", "load"]),
            (SettingsRepositoryImpl, ["load", "save"]),
            (VinCacheRepositoryImpl, ["get", "set"]),
            (I18nRepositoryImpl, ["load_all"]),
            (UdsDiscoveryService, ["discover"]),
            (UdsClientAdapter, ["read_did", "send_raw"]),
            (UdsClientFactoryImpl, ["create", "module_map"]),
            (TelemetryLoggerAdapter, ["start_session", "log_readings", "end_session"]),
            (TelemetryLoggerFactoryImpl, ["create"]),
        ]
        for cls, methods in contracts:
            self._assert_methods(cls, methods)

    def test_dto_shapes(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ReportMeta)],
            ["report_id", "created_at", "status", "model", "file_path"],
        )
        self.assertEqual(
            [field.name for field in fields(VehicleProfile)],
            ["make", "model", "year", "trim", "vin", "protocol", "source"],
        )
        self.assertEqual(
            [field.name for field in fields(ScanData)],
            ["vehicle_info", "dtcs", "readiness", "live_data"],
        )
        self.assertEqual(
            [field.name for field in fields(ModuleEntry)],
            ["tx_id", "rx_id", "module_type", "responses", "requires_security", "fingerprint"],
        )
