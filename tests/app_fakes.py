from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.domain.entities import ExternalServiceError, PaymentRequiredError
from app.domain.ports import (
    AiConfigPort,
    AiReportPort,
    DtcDatabaseFactory,
    DtcLookupPort,
    KLineScannerFactory,
    KLineScannerPort,
    PaywallPort,
    PortsScanner,
    ReportRepository,
    FullScanReportRepository,
    ScannerFactory,
    ScannerPort,
    SettingsRepository,
    UdsClientFactory,
    UdsClientPort,
    VinCacheRepository,
    VinDecoderPort,
)


@dataclass
class SimpleDtc:
    code: str
    status: str
    description: str


@dataclass
class SimpleReadiness:
    available: bool
    complete: bool
    status_str: str


@dataclass
class SimpleReading:
    name: str
    value: float
    unit: str


class DummyScanner(ScannerPort):
    def __init__(self) -> None:
        self.is_connected = False
        self.manufacturer = None
        self.raw_logger = None

    def set_manufacturer(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer

    def set_raw_logger(self, logger: Optional[Any]) -> None:
        self.raw_logger = logger

    def set_port(self, port: str) -> None:
        return None

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def get_transport(self) -> Any:
        return "TRANSPORT"

    def debug_snapshot(self) -> Dict[str, Any]:
        return {}

    def get_vehicle_info(self) -> Dict[str, Any]:
        return {
            "elm_version": "ELM327-FAKE",
            "protocol": "ISO 15765-4 (CAN)",
            "mil_on": "No",
            "dtc_count": "1",
        }

    def read_dtcs(self) -> List[SimpleDtc]:
        return [SimpleDtc(code="P0420", status="stored", description="Test DTC")]

    def read_readiness(self) -> Dict[str, SimpleReadiness]:
        return {
            "Misfire": SimpleReadiness(available=True, complete=True, status_str="Complete"),
        }

    def read_live_data(self, pids: Optional[List[str]] = None) -> Dict[str, SimpleReading]:
        return {
            "0C": SimpleReading(name="RPM", value=800.0, unit="rpm"),
        }

    def read_freeze_frame(self) -> Dict[str, Any]:
        return {}

    def clear_codes(self) -> bool:
        return True


class DummyScannerFactory(ScannerFactory):
    def __init__(self) -> None:
        self.created = 0
        self.last_manufacturer: Optional[str] = None

    def create(self, manufacturer: Optional[str]) -> ScannerPort:
        self.created += 1
        self.last_manufacturer = manufacturer
        scanner = DummyScanner()
        if manufacturer:
            scanner.set_manufacturer(manufacturer)
        return scanner


class DummyKLineScanner(KLineScannerPort):
    def __init__(self) -> None:
        self.is_connected = False
        self.is_kline = True
        self.manufacturer = None
        self.raw_logger = None

    def set_manufacturer(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer

    def set_raw_logger(self, logger: Optional[Any]) -> None:
        self.raw_logger = logger

    def disconnect(self) -> None:
        self.is_connected = False

    def read_dtcs(self, mode: str = "stored") -> Dict[str, Any]:
        return {"mode": mode, "dtcs": []}

    def clear_dtcs(self) -> Tuple[bool, Dict[str, Any]]:
        return True, {}

    def read_pid(self, pid: str) -> Dict[str, Any]:
        return {"pid": pid, "value": None}


class DummyKLineFactory(KLineScannerFactory):
    def __init__(self) -> None:
        self.detect_called = False

    def create(self, port: str, manufacturer: Optional[str]) -> KLineScannerPort:
        return DummyKLineScanner()

    def detect(
        self,
        port: str,
        manufacturer: Optional[str],
        raw_logger: Optional[Any] = None,
    ) -> Tuple[Optional[KLineScannerPort], Optional[Dict[str, Any]], Optional[Exception]]:
        self.detect_called = True
        return DummyKLineScanner(), {"profile_name": "test"}, None


class DummyDtcDb(DtcLookupPort):
    def __init__(self) -> None:
        self.manufacturer = None

    def lookup(self, code: str) -> Optional[Dict[str, Any]]:
        return {"code": code, "description": "Test"} if code else None

    def search(self, text: str) -> List[Dict[str, Any]]:
        return [{"code": "P0001", "description": "Test"}] if text else []

    def set_manufacturer(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer


class DummyDtcFactory(DtcDatabaseFactory):
    def __init__(self) -> None:
        self.created = 0

    def create(self, manufacturer: Optional[str]) -> DtcLookupPort:
        self.created += 1
        return DummyDtcDb()


class DummyPortsScanner(PortsScanner):
    def __init__(self) -> None:
        self.last_port = None
        self.last_scanner = None

    def scan_usb_ports(self) -> List[str]:
        return ["/dev/ttyFAKE"]

    def scan_ble_devices(self, include_all: bool = False) -> Tuple[List[Tuple[str, str, int]], Optional[str]]:
        return [], None

    def try_connect(self, scanner: ScannerPort, port: str) -> Tuple[bool, Dict[str, Any], Optional[Exception]]:
        self.last_port = port
        self.last_scanner = scanner
        scanner.set_port(port)
        ok = scanner.connect()
        return ok, {"elm_version": "ELM327-FAKE"}, None


class DummySettingsRepo(SettingsRepository):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.payload = payload or {}
        self.saved: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        return dict(self.payload)

    def save(self, settings: Dict[str, Any]) -> None:
        self.saved = dict(settings)


class DummyReportRepo(ReportRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    def save_report(self, payload: Dict[str, Any]) -> str:
        self._seq += 1
        key = f"R{self._seq:04d}"
        stored = dict(payload)
        stored.setdefault("report_id", key)
        self._store[key] = stored
        return key

    def list_reports(self):
        return []

    def load_report(self, path: str) -> Dict[str, Any]:
        return dict(self._store.get(path, {}))

    def find_report_by_id(self, report_id: str) -> Optional[str]:
        return report_id if report_id in self._store else None

    def write_report(self, path: str, payload: Dict[str, Any]) -> None:
        self._store[path] = dict(payload)


class DummyFullScanRepo(FullScanReportRepository):
    def __init__(self) -> None:
        self.saved: List[List[str]] = []

    def save(self, lines: List[str]) -> str:
        self.saved.append(list(lines))
        return "full_scan.txt"

    def list(self) -> List[str]:
        return ["full_scan.txt"]

    def load(self, path: str) -> str:
        return "\n".join(self.saved[0]) if self.saved else ""


class DummyVinCache(VinCacheRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, vin: str) -> Optional[Dict[str, Any]]:
        return self._store.get(vin)

    def set(self, vin: str, profile: Dict[str, Any]) -> None:
        self._store[vin] = dict(profile)


class DummyAiPort(AiReportPort):
    def __init__(self, response: str = "<json>{\"language\":\"en\"}</json><report>OK</report>") -> None:
        self.response = response

    def decode_vin(self, vin: str, manufacturer: str) -> Optional[Dict[str, Any]]:
        return None

    def request_report(self, report_input: Dict[str, Any], language: str) -> str:
        return self.response


class DummyVinDecoder(VinDecoderPort):
    def __init__(self, result: Optional[Dict[str, Any]] = None) -> None:
        self.result = result

    def decode_vpic(self, vin: str, model_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.result


class DummyAiConfig(AiConfigPort):
    def __init__(self, api_key: Optional[str] = None, model: str = "fake-model") -> None:
        self.api_key = api_key
        self.model = model

    def get_api_key(self) -> Optional[str]:
        return self.api_key

    def get_model(self) -> str:
        return self.model


class DummyPaywall(PaywallPort):
    def __init__(
        self,
        *,
        configured: bool = True,
        bypass: bool = False,
        consume_error: Optional[Exception] = None,
    ) -> None:
        self._configured = configured
        self._bypass = bypass
        self.consume_error = consume_error

    def is_configured(self) -> bool:
        return self._configured

    def is_bypass_enabled(self) -> bool:
        return self._bypass

    def api_base(self) -> Optional[str]:
        return "http://localhost"

    def set_api_base(self, api_base: str) -> None:
        return None

    def subject_id(self) -> Optional[str]:
        return "test"

    def cached_balance(self) -> Optional[Tuple[int, int]]:
        return 1, 0

    def get_balance(self) -> Any:
        return {"paid_credits": 1, "free_remaining": 0}

    def pending_total(self) -> int:
        return 0

    def ensure_identity(self) -> Any:
        return {"subject_id": "test"}

    def consume(self, action: str, cost: int = 1) -> Any:
        if self.consume_error:
            raise self.consume_error
        return {"ok": True}

    def checkout(self) -> str:
        return "http://checkout"

    def wait_for_balance(self, *, min_paid: int = 1, timeout_seconds: int = 120) -> Any:
        return {"paid_credits": min_paid, "free_remaining": 0}

    def reset_identity(self) -> None:
        return None


class DummyUdsClient(UdsClientPort):
    def read_did(self, brand: str, did: str) -> Dict[str, Any]:
        return {"did": did}

    def send_raw(self, service_id: int, data: bytes, *, raise_on_negative: bool = False) -> bytes:
        return b""


class DummyUdsFactory(UdsClientFactory):
    def __init__(self) -> None:
        self.created = False

    def create(self, transport: Any, brand: str, module_entry: Dict[str, Any]) -> UdsClientPort:
        self.created = True
        return DummyUdsClient()

    def module_map(self, brand: str) -> Dict[str, Dict[str, str]]:
        return {"generic_engine": {"tx_id": "7E0", "rx_id": "7E8"}}

