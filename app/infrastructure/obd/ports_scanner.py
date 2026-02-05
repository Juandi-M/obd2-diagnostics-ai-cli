from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.domain.ports import PortsScanner, ScannerPort
from app.infrastructure.obd.connection import scan_ble_devices, scan_usb_ports, try_connect


class PortsScannerImpl(PortsScanner):
    def scan_usb_ports(self) -> List[str]:
        return scan_usb_ports()

    def scan_ble_devices(
        self, include_all: bool = False, timeout_s: Optional[float] = None
    ) -> Tuple[List[Tuple[str, str, int]], Optional[str]]:
        return scan_ble_devices(include_all=include_all, timeout_s=timeout_s)

    def try_connect(self, scanner: ScannerPort, port: str) -> Tuple[bool, Dict[str, Any], Optional[Exception]]:
        return try_connect(scanner, port)
