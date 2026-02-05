from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.application.state import AppState
from app.domain.ports import KLineScannerFactory, PortsScanner, ScannerPort


class ConnectionService:
    def __init__(
        self,
        state: AppState,
        ports_scanner: PortsScanner,
        kline_factory: KLineScannerFactory,
    ) -> None:
        self.state = state
        self.ports_scanner = ports_scanner
        self.kline_factory = kline_factory

    def scan_usb_ports(self) -> List[str]:
        return self.ports_scanner.scan_usb_ports()

    def scan_ble_devices(
        self, include_all: bool = False, timeout_s: Optional[float] = None
    ) -> Tuple[List[Tuple[str, str, int]], Optional[str]]:
        return self.ports_scanner.scan_ble_devices(include_all=include_all, timeout_s=timeout_s)

    def try_connect(
        self,
        port: str,
    ) -> Tuple[bool, Dict[str, Any], Optional[Exception]]:
        scanner = self.state.ensure_scanner()
        scanner.set_raw_logger(self.state.raw_logger())
        return self.ports_scanner.try_connect(scanner, port)

    def try_kline(
        self,
        port: str,
    ) -> Tuple[Optional[ScannerPort], Optional[Dict[str, Any]], Optional[Exception]]:
        kline_scanner, info, err = self.kline_factory.detect(
            port,
            self.state.manufacturer if self.state.manufacturer != "generic" else None,
            raw_logger=self.state.raw_logger(),
        )
        if kline_scanner:
            self.state.set_kline_scanner(kline_scanner)
        return kline_scanner, info, err
