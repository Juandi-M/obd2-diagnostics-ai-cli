from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union, Callable, List

from obd import OBDScanner, DTCDatabase
from obd.rawlog import RawLogger
from obd.legacy_kline.adapter import LegacyKLineAdapter


@dataclass
class AppState:
    scanner: Optional[OBDScanner] = None
    dtc_db: Optional[DTCDatabase] = None
    legacy_scanner: Optional[LegacyKLineAdapter] = None
    manufacturer: str = "generic"
    log_format: str = "csv"
    monitor_interval: float = 1.0
    language: str = "en"
    stop_monitoring: bool = False
    demo: bool = False
    verbose: bool = False

    def raw_logger(self) -> Optional[Callable[[str, str, List[str]], None]]:
        if not self.verbose:
            return None
        return RawLogger("logs/obd_raw.log")

    def set_verbose(self, enabled: bool) -> None:
        self.verbose = enabled
        logger = self.raw_logger()
        if self.scanner:
            self.scanner.elm.raw_logger = logger
        if self.legacy_scanner:
            self.legacy_scanner.elm.raw_logger = logger

    def ensure_scanner(self) -> OBDScanner:
        if not self.scanner:
            self.scanner = OBDScanner(
                manufacturer=self.manufacturer if self.manufacturer != "generic" else None,
                raw_logger=self.raw_logger(),
            )
        return self.scanner

    def set_legacy_scanner(self, legacy: LegacyKLineAdapter) -> None:
        if self.scanner and self.scanner.is_connected:
            self.scanner.disconnect()
        self.legacy_scanner = legacy

    def clear_legacy_scanner(self) -> None:
        if self.legacy_scanner:
            try:
                self.legacy_scanner.disconnect()
            except Exception:
                pass
        self.legacy_scanner = None

    def disconnect_all(self) -> None:
        if self.scanner and self.scanner.is_connected:
            try:
                self.scanner.disconnect()
            except Exception:
                pass
        self.clear_legacy_scanner()

    def ensure_dtc_db(self) -> DTCDatabase:
        if not self.dtc_db:
            self.dtc_db = DTCDatabase(
                manufacturer=self.manufacturer if self.manufacturer != "generic" else None
            )
        return self.dtc_db

    def set_manufacturer(self, manufacturer: str) -> None:
        self.manufacturer = manufacturer
        if self.dtc_db:
            self.dtc_db.set_manufacturer(manufacturer)
        if self.scanner:
            self.scanner.set_manufacturer(manufacturer)
        if self.legacy_scanner:
            self.legacy_scanner.set_manufacturer(manufacturer)

    def active_scanner(self) -> Optional[Union[OBDScanner, LegacyKLineAdapter]]:
        if self.legacy_scanner and self.legacy_scanner.is_connected:
            return self.legacy_scanner
        if self.scanner and self.scanner.is_connected:
            return self.scanner
        return None
