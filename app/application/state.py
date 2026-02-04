from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union, Callable, List, Dict, Any

from app.domain.ports import (
    ScannerPort,
    KLineScannerPort,
    ScannerFactory,
    KLineScannerFactory,
    DtcLookupPort,
    DtcDatabaseFactory,
    RawLoggerFactory,
)


@dataclass
class AppState:
    scanner: Optional[ScannerPort] = None
    dtc_db: Optional[DtcLookupPort] = None
    kline_scanner: Optional[KLineScannerPort] = None
    scanner_factory: Optional[ScannerFactory] = None
    kline_scanner_factory: Optional[KLineScannerFactory] = None
    dtc_db_factory: Optional[DtcDatabaseFactory] = None
    raw_logger_factory: Optional[RawLoggerFactory] = None
    manufacturer: str = "generic"
    log_format: str = "csv"
    monitor_interval: float = 1.0
    language: str = "en"
    stop_monitoring: bool = False
    demo: bool = False
    verbose: bool = False
    vehicle_profile: Optional[Dict[str, Any]] = None
    last_ble_address: Optional[str] = None
    ble_notice_shown: bool = False
    last_seen_at: Optional[float] = None
    last_seen_rssi: Optional[int] = None
    last_seen_device: Optional[str] = None
    last_vin: Optional[str] = None
    vehicle_group: str = "generic"
    brand_id: Optional[str] = None
    brand_label: Optional[str] = None
    vehicle_profiles_by_group: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    session_results: List[Dict[str, Any]] = field(default_factory=list)

    def raw_logger(self) -> Optional[Callable[[str, str, List[str]], None]]:
        if not self.raw_logger_factory:
            return None
        return self.raw_logger_factory.create(self.verbose)

    def set_verbose(self, enabled: bool) -> None:
        self.verbose = enabled
        logger = self.raw_logger()
        if self.scanner:
            self.scanner.set_raw_logger(logger)
        if self.kline_scanner:
            self.kline_scanner.set_raw_logger(logger)

    def ensure_scanner(self) -> ScannerPort:
        if not self.scanner:
            if not self.scanner_factory:
                raise RuntimeError("Scanner factory not configured")
            self.scanner = self.scanner_factory.create(
                self.manufacturer if self.manufacturer != "generic" else None
            )
        return self.scanner

    def set_kline_scanner(self, kline_scanner: KLineScannerPort) -> None:
        if self.scanner and self.scanner.is_connected:
            self.scanner.disconnect()
        self.kline_scanner = kline_scanner

    def clear_kline_scanner(self) -> None:
        if self.kline_scanner:
            try:
                self.kline_scanner.disconnect()
            except Exception:
                pass
        self.kline_scanner = None

    def disconnect_all(self) -> None:
        if self.scanner and self.scanner.is_connected:
            try:
                self.scanner.disconnect()
            except Exception:
                pass
        self.clear_kline_scanner()

    def ensure_dtc_db(self) -> DtcLookupPort:
        if not self.dtc_db:
            if not self.dtc_db_factory:
                raise RuntimeError("DTC DB factory not configured")
            self.dtc_db = self.dtc_db_factory.create(
                self.manufacturer if self.manufacturer != "generic" else None
            )
        return self.dtc_db

    def set_manufacturer(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer
        if self.dtc_db:
            self.dtc_db.set_manufacturer(manufacturer)
        if self.scanner:
            self.scanner.set_manufacturer(manufacturer)
        if self.kline_scanner:
            self.kline_scanner.set_manufacturer(manufacturer)

    def active_scanner(self) -> Optional[Union[ScannerPort, KLineScannerPort]]:
        if self.kline_scanner and self.kline_scanner.is_connected:
            return self.kline_scanner
        if self.scanner and self.scanner.is_connected:
            return self.scanner
        return None
