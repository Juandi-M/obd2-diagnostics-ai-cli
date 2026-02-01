from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from obd import OBDScanner, DTCDatabase


@dataclass
class AppState:
    scanner: Optional[OBDScanner] = None
    dtc_db: Optional[DTCDatabase] = None
    manufacturer: str = "generic"
    log_format: str = "csv"
    monitor_interval: float = 1.0
    language: str = "en"
    stop_monitoring: bool = False
    demo: bool = False
    report_requests: int = 0
    report_limit: int = 4

    def ensure_scanner(self) -> OBDScanner:
        if not self.scanner:
            self.scanner = OBDScanner(
                manufacturer=self.manufacturer if self.manufacturer != "generic" else None
            )
        return self.scanner

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
