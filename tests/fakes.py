from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.bootstrap.container import AppContainer
from app.application.state import AppState
from app.application.use_cases import (
    AiConfigService,
    AiReportService,
    ConnectionService,
    DataPathService,
    DocumentPathService,
    FullScanReportsService,
    I18nService,
    PaywallService,
    PdfPathService,
    ReportsService,
    ScanService,
    SettingsService,
    TelemetryLogService,
    UdsDiscoveryService,
    UdsToolsService,
    VehicleService,
    VinCacheService,
)
from app.domain.entities import ReportMeta
from app.domain.ports import (
    AiConfigPort,
    AiReportPort,
    DataPathPort,
    DocumentPathPort,
    DtcDatabaseFactory,
    DtcLookupPort,
    FullScanReportRepository,
    KLineScannerFactory,
    KLineScannerPort,
    PaywallPort,
    PdfPathPort,
    PdfRendererPort,
    PortsScanner,
    RawLoggerFactory,
    ReportRepository,
    ScannerFactory,
    ScannerPort,
    SettingsRepository,
    TelemetryLoggerFactory,
    TelemetryLoggerPort,
    UdsClientFactory,
    UdsClientPort,
    UdsDiscoveryPort,
    VinCacheRepository,
    VinDecoderPort,
)
from app.infrastructure.i18n.repository import I18nRepositoryImpl
from obd.obd2.models import DiagnosticCode, ReadinessStatus, SensorReading


class FakeScanner(ScannerPort):
    def __init__(self) -> None:
        self.is_connected = False
        self._port: Optional[str] = None
        self._manufacturer: str = "generic"
        self._raw_logger = None

    def set_manufacturer(self, manufacturer: str) -> None:
        self._manufacturer = manufacturer

    def set_raw_logger(self, logger: Optional[Any]) -> None:
        self._raw_logger = logger

    def set_port(self, port: str) -> None:
        self._port = port

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def get_transport(self) -> Any:
        return "FAKE_TRANSPORT"

    def debug_snapshot(self) -> Dict[str, Any]:
        return {
            "elm_version": "FAKE",
            "last_command": None,
            "last_response": "",
            "last_error": None,
            "last_duration_s": None,
            "timeout": 1.0,
        }

    def get_vehicle_info(self) -> Dict[str, Any]:
        return {
            "elm_version": "ELM327-FAKE",
            "protocol": "ISO 15765-4 (CAN)",
            "mil_on": "No",
            "dtc_count": 1,
            "vin": "",
            "make": "Test",
            "model": "Mock",
            "year": "2020",
            "engine": "2.0L",
        }

    def read_dtcs(self) -> List[DiagnosticCode]:
        return [
            DiagnosticCode(
                code="P0420",
                description="Catalyst System Efficiency Below Threshold",
                status="stored",
            )
        ]

    def read_readiness(self) -> Dict[str, ReadinessStatus]:
        return {
            "MIL (Check Engine Light)": ReadinessStatus("MIL", True, True),
            "Misfire": ReadinessStatus("Misfire", True, True),
            "Fuel System": ReadinessStatus("Fuel System", True, False),
        }

    def read_live_data(self, pids: Optional[List[str]] = None) -> Dict[str, SensorReading]:
        return {
            "0C": SensorReading(name="Engine RPM", value=850.0, unit="rpm", pid="0C", raw_hex="0A00"),
            "05": SensorReading(name="Engine Coolant Temperature", value=88.0, unit="C", pid="05", raw_hex="7B"),
        }

    def read_freeze_frame(self) -> Dict[str, Any]:
        return {}

    def clear_codes(self) -> bool:
        return True


class FakeScannerFactory(ScannerFactory):
    def create(self, manufacturer: Optional[str]) -> ScannerPort:
        scanner = FakeScanner()
        if manufacturer:
            scanner.set_manufacturer(manufacturer)
        return scanner


class FakeKLineScanner(KLineScannerPort):
    def __init__(self) -> None:
        self.is_connected = False
        self.is_kline = True

    def set_manufacturer(self, manufacturer: str) -> None:
        return None

    def set_raw_logger(self, logger: Optional[Any]) -> None:
        return None

    def disconnect(self) -> None:
        self.is_connected = False

    def read_dtcs(self, mode: str = "stored") -> Dict[str, Any]:
        return {"mode": mode, "dtcs": []}

    def clear_dtcs(self) -> Tuple[bool, Dict[str, Any]]:
        return True, {}

    def read_pid(self, pid: str) -> Dict[str, Any]:
        return {"pid": pid, "value": None}


class FakeKLineScannerFactory(KLineScannerFactory):
    def create(self, port: str, manufacturer: Optional[str]) -> KLineScannerPort:
        return FakeKLineScanner()

    def detect(
        self,
        port: str,
        manufacturer: Optional[str],
        raw_logger: Optional[Any] = None,
    ) -> Tuple[Optional[KLineScannerPort], Optional[Dict[str, Any]], Optional[Exception]]:
        return None, None, None


class FakePortsScanner(PortsScanner):
    def scan_usb_ports(self) -> List[str]:
        return ["/dev/ttyFAKE"]

    def scan_ble_devices(self, include_all: bool = False) -> Tuple[List[Tuple[str, str, int]], Optional[str]]:
        return [], None

    def try_connect(self, scanner: ScannerPort, port: str) -> Tuple[bool, Dict[str, Any], Optional[Exception]]:
        scanner.set_port(port)
        ok = scanner.connect()
        info = {
            "elm_version": "ELM327-FAKE",
            "protocol": "ISO 15765-4 (CAN)",
            "mil_on": "No",
            "dtc_count": 1,
            "vin": "",
        }
        return ok, info, None


class FakeDtcDatabase(DtcLookupPort):
    def __init__(self) -> None:
        self._manufacturer = "generic"
        self._codes = {"P0420": "Catalyst System Efficiency Below Threshold"}

    @property
    def count(self) -> int:
        return len(self._codes)

    @property
    def loaded_files(self) -> List[str]:
        return ["dtc_generic.csv"]

    def lookup(self, code: str) -> Optional[Dict[str, Any]]:
        desc = self._codes.get(code.upper())
        if not desc:
            return None
        return {"code": code.upper(), "description": desc}

    def search(self, text: str) -> List[Dict[str, Any]]:
        text = text.lower()
        return [
            {"code": code, "description": desc}
            for code, desc in self._codes.items()
            if text in code.lower() or text in desc.lower()
        ]

    def set_manufacturer(self, manufacturer: str) -> None:
        self._manufacturer = manufacturer


class FakeDtcDatabaseFactory(DtcDatabaseFactory):
    def create(self, manufacturer: Optional[str]) -> DtcLookupPort:
        return FakeDtcDatabase()


class FakeRawLoggerFactory(RawLoggerFactory):
    def create(self, enabled: bool) -> Optional[Any]:
        return None


class FakeSettingsRepository(SettingsRepository):
    def load(self) -> Dict[str, Any]:
        return {}

    def save(self, settings: Dict[str, Any]) -> None:
        return None


class FakeReportRepository(ReportRepository):
    def __init__(self) -> None:
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    def _new_id(self) -> str:
        self._seq += 1
        return f"R{self._seq:04d}"

    def save_report(self, payload: Dict[str, Any]) -> str:
        report_id = payload.get("report_id") or self._new_id()
        stored = dict(payload)
        stored["report_id"] = report_id
        stored.setdefault("created_at", "2026-01-01T00:00:00Z")
        stored.setdefault("status", payload.get("status", "pending"))
        self._reports[report_id] = stored
        return report_id

    def list_reports(self) -> List[ReportMeta]:
        items = []
        for report_id, payload in self._reports.items():
            items.append(
                ReportMeta(
                    report_id=report_id,
                    created_at=str(payload.get("created_at", "")),
                    status=str(payload.get("status", "unknown")),
                    model=payload.get("model"),
                    file_path=report_id,
                )
            )
        return list(reversed(items))

    def load_report(self, path: str) -> Dict[str, Any]:
        return dict(self._reports.get(path, {}))

    def find_report_by_id(self, report_id: str) -> Optional[str]:
        return report_id if report_id in self._reports else None

    def write_report(self, path: str, payload: Dict[str, Any]) -> None:
        self._reports[path] = dict(payload)


class FakeFullScanReportRepository(FullScanReportRepository):
    def __init__(self) -> None:
        self._reports: List[str] = []

    def save(self, lines: List[str]) -> str:
        content = "\n".join(lines)
        self._reports.append(content)
        return f"FULLSCAN-{len(self._reports):04d}"

    def list(self) -> List[str]:
        return list(self._reports)

    def load(self, path: str) -> str:
        try:
            idx = int(path.split("-")[-1]) - 1
        except Exception:
            idx = 0
        if 0 <= idx < len(self._reports):
            return self._reports[idx]
        return ""


class FakeAiReportPort(AiReportPort):
    def decode_vin(self, vin: str, manufacturer: str) -> Optional[Dict[str, Any]]:
        return None

    def request_report(self, report_input: Dict[str, Any], language: str) -> str:
        report_json = {"language": language, "summary": "ok"}
        return f"<json>{json.dumps(report_json)}</json>\n<report>Diagnostics summary OK.</report>"


class FakeVinDecoderPort(VinDecoderPort):
    def decode_vpic(self, vin: str, model_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return None


class FakeAiConfigPort(AiConfigPort):
    def get_api_key(self) -> Optional[str]:
        return "fake-key"

    def get_model(self) -> str:
        return "fake-model"


class FakePaywallPort(PaywallPort):
    def is_configured(self) -> bool:
        return True

    def is_bypass_enabled(self) -> bool:
        return True

    def api_base(self) -> Optional[str]:
        return "http://localhost"

    def set_api_base(self, api_base: str) -> None:
        return None

    def subject_id(self) -> Optional[str]:
        return "test-subject"

    def cached_balance(self) -> Optional[Tuple[int, int]]:
        return 10, 0

    def get_balance(self) -> Any:
        return {"paid_credits": 10, "free_remaining": 0}

    def pending_total(self) -> int:
        return 0

    def ensure_identity(self) -> Any:
        return {"subject_id": "test-subject"}

    def consume(self, action: str, cost: int = 1) -> Any:
        return {"action": action, "cost": cost}

    def checkout(self) -> str:
        return "http://localhost/checkout"

    def wait_for_balance(self, *, min_paid: int = 1, timeout_seconds: int = 120) -> Any:
        return {"paid_credits": 10, "free_remaining": 0}

    def reset_identity(self) -> None:
        return None


class FakePdfRenderer(PdfRendererPort):
    def render(
        self,
        payload: Dict[str, Any],
        output_path: str,
        *,
        report_json: Optional[Dict[str, Any]] = None,
        report_text: Optional[str] = None,
        language: Optional[str] = None,
    ) -> None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = f"PDF PLACEHOLDER\nlang={language}\n"
        target.write_text(content, encoding="utf-8")


class FakePdfPathPort(PdfPathPort):
    def __init__(self, root: Path) -> None:
        self._root = root

    def report_pdf_path(self, report_id: str) -> str:
        return str(self._root / f"report_{report_id}.pdf")


class FakeDocumentPathPort(DocumentPathPort):
    def __init__(self, root: Path) -> None:
        self._root = root

    def ai_report_pdf_path(self, vehicle_payload: Dict[str, Any]) -> str:
        stamp = datetime(2026, 1, 1, 0, 0)
        filename = f"Report_{stamp.strftime('%Y%m%d_%H%M')}.pdf"
        return str(self._root / filename)


class FakeDataPathPort(DataPathPort):
    def __init__(self, root: Path) -> None:
        self._root = root

    def raw_log_path(self) -> str:
        return str(self._root / "obd_raw.log")


class FakeTelemetryLogger(TelemetryLoggerPort):
    def start_session(self, format: str = "csv") -> str:
        return "session-0001"

    def log_readings(self, readings: Dict[str, Any]) -> None:
        return None

    def end_session(self) -> Dict[str, Any]:
        return {"rows": 0}


class FakeTelemetryLoggerFactory(TelemetryLoggerFactory):
    def create(self) -> TelemetryLoggerPort:
        return FakeTelemetryLogger()


class FakeUdsDiscoveryPort(UdsDiscoveryPort):
    def discover(self, scanner: ScannerPort, options: Dict[str, Any]) -> Dict[str, Any]:
        return {"modules": [], "protocol": None, "addressing": None, "elapsed_s": 0.0}


class FakeUdsClient(UdsClientPort):
    def read_did(self, brand: str, did: str) -> Dict[str, Any]:
        return {"did": did, "value": None}

    def send_raw(self, service_id: int, data: bytes, *, raise_on_negative: bool = False) -> bytes:
        return b""


class FakeUdsClientFactory(UdsClientFactory):
    def create(self, transport: Any, brand: str, module_entry: Dict[str, Any]) -> UdsClientPort:
        return FakeUdsClient()

    def module_map(self, brand: str) -> Dict[str, Dict[str, str]]:
        return {}


class FakeVinCacheRepository(VinCacheRepository):
    def get(self, vin: str) -> Optional[Dict[str, Any]]:
        return None

    def set(self, vin: str, profile: Dict[str, Any]) -> None:
        return None


def build_fake_container(tmp_dir: Path) -> AppContainer:
    raw_logger_factory = FakeRawLoggerFactory()
    scanner_factory = FakeScannerFactory()
    kline_factory = FakeKLineScannerFactory()
    dtc_factory = FakeDtcDatabaseFactory()
    state = AppState(
        scanner_factory=scanner_factory,
        kline_scanner_factory=kline_factory,
        dtc_db_factory=dtc_factory,
        raw_logger_factory=raw_logger_factory,
    )

    ports_scanner = FakePortsScanner()
    settings_repo = FakeSettingsRepository()
    reports_repo = FakeReportRepository()
    full_scan_repo = FakeFullScanReportRepository()
    vin_cache_repo = FakeVinCacheRepository()
    ai_port = FakeAiReportPort()
    vpic_port = FakeVinDecoderPort()
    ai_config_port = FakeAiConfigPort()
    paywall_port = FakePaywallPort()
    pdf_renderer = FakePdfRenderer()
    pdf_paths = FakePdfPathPort(tmp_dir)
    document_paths = FakeDocumentPathPort(tmp_dir)
    data_paths = FakeDataPathPort(tmp_dir)
    i18n_repo = I18nRepositoryImpl()
    uds_discovery_port = FakeUdsDiscoveryPort()
    uds_client_factory = FakeUdsClientFactory()
    telemetry_logger_factory = FakeTelemetryLoggerFactory()

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
