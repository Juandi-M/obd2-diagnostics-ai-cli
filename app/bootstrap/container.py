from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.application.state import AppState
from app.application.use_cases import (
    AiConfigService,
    AiReportService,
    ConnectionService,
    FullScanReportsService,
    PaywallService,
    ReportsService,
    ScanService,
    SettingsService,
    TelemetryLogService,
    PdfPathService,
    DocumentPathService,
    DataPathService,
    I18nService,
    UdsDiscoveryService,
    UdsToolsService,
    VehicleService,
    VinCacheService,
)
from app.domain.ports import PortsScanner
from app.infrastructure.ai.adapters import AiConfigAdapter, AiReportAdapter, VinDecoderAdapter
from app.infrastructure.billing.paywall_adapter import PaywallAdapter
from app.infrastructure.obd.ports_scanner import PortsScannerImpl
from app.infrastructure.obd.scanner_adapter import (
    DtcDatabaseFactoryImpl,
    KLineScannerFactoryImpl,
    OBDScannerFactory,
)
from app.infrastructure.obd.raw_logger import RawLoggerFactoryImpl
from app.infrastructure.obd.telemetry_logger import TelemetryLoggerFactoryImpl
from app.infrastructure.obd.uds_client import UdsClientFactoryImpl
from app.infrastructure.obd.uds_discovery import UdsDiscoveryService as UdsDiscoveryImpl
from app.infrastructure.persistence.reports import ReportRepositoryImpl, FullScanReportRepositoryImpl
from app.infrastructure.persistence.settings_store import SettingsRepositoryImpl
from app.infrastructure.persistence.vin_cache import VinCacheRepositoryImpl
from app.infrastructure.reporting.pdf_renderer import PdfReportRenderer
from app.infrastructure.reporting.pdf_paths import PdfPathAdapter
from app.infrastructure.persistence.document_paths import DocumentPathAdapter
from app.infrastructure.persistence.data_path_adapter import DataPathAdapter
from app.infrastructure.persistence.data_paths import ensure_runtime_dirs
from app.infrastructure.i18n.repository import I18nRepositoryImpl


@dataclass
class AppContainer:
    state: AppState
    ports_scanner: PortsScanner
    connection: ConnectionService
    scans: ScanService
    settings: SettingsService
    vehicles: VehicleService
    reports: ReportsService
    full_scan_reports: FullScanReportsService
    ai_reports: AiReportService
    ai_config: AiConfigService
    telemetry_log: TelemetryLogService
    pdf_paths: PdfPathService
    document_paths: DocumentPathService
    data_paths: DataPathService
    i18n: I18nService
    paywall: PaywallService
    uds_discovery: UdsDiscoveryService
    uds_tools: UdsToolsService
    vin_cache: VinCacheService


def build_container() -> AppContainer:
    ensure_runtime_dirs()
    raw_logger_factory = RawLoggerFactoryImpl()
    telemetry_logger_factory = TelemetryLoggerFactoryImpl()
    scanner_factory = OBDScannerFactory(raw_logger_factory=raw_logger_factory)
    kline_factory = KLineScannerFactoryImpl()
    dtc_factory = DtcDatabaseFactoryImpl()
    state = AppState(
        scanner_factory=scanner_factory,
        kline_scanner_factory=kline_factory,
        dtc_db_factory=dtc_factory,
        raw_logger_factory=raw_logger_factory,
    )

    ports_scanner = PortsScannerImpl()
    settings_repo = SettingsRepositoryImpl()
    reports_repo = ReportRepositoryImpl()
    full_scan_repo = FullScanReportRepositoryImpl()
    vin_cache_repo = VinCacheRepositoryImpl()
    ai_port = AiReportAdapter()
    vpic_port = VinDecoderAdapter()
    ai_config_port = AiConfigAdapter()
    paywall_port = PaywallAdapter()
    pdf_renderer = PdfReportRenderer()
    pdf_paths = PdfPathAdapter()
    document_paths = DocumentPathAdapter()
    data_paths = DataPathAdapter()
    i18n_repo = I18nRepositoryImpl()
    uds_discovery_port = UdsDiscoveryImpl()
    uds_client_factory = UdsClientFactoryImpl()

    return AppContainer(
        state=state,
        ports_scanner=ports_scanner,
        connection=ConnectionService(state, ports_scanner, kline_factory),
        scans=ScanService(state),
        settings=SettingsService(state, settings_repo),
        vehicles=VehicleService(state),
        reports=ReportsService(reports_repo),
        full_scan_reports=FullScanReportsService(full_scan_repo),
        ai_reports=AiReportService(ai_port, vpic_port, vin_cache_repo, reports_repo, pdf_renderer),
        ai_config=AiConfigService(ai_config_port),
        telemetry_log=TelemetryLogService(telemetry_logger_factory),
        pdf_paths=PdfPathService(pdf_paths),
        document_paths=DocumentPathService(document_paths),
        data_paths=DataPathService(data_paths),
        i18n=I18nService(state, i18n_repo),
        paywall=PaywallService(paywall_port),
        uds_discovery=UdsDiscoveryService(state, uds_discovery_port),
        uds_tools=UdsToolsService(state, uds_client_factory),
        vin_cache=VinCacheService(vin_cache_repo),
    )


_container: Optional[AppContainer] = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = build_container()
    return _container
