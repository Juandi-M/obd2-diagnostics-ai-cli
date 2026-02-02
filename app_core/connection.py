from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from obd import ELM327
from obd.obd2.base import ConnectionLostError


def scan_usb_ports() -> list[str]:
    return ELM327.find_ports()


def scan_ble_devices(include_all: bool = False):
    from obd.ble.ports import scan_ble_devices

    return scan_ble_devices(include_all=include_all)


def try_connect(scanner, port: str, raw_logger=None) -> Tuple[bool, Dict[str, Any], Optional[Exception]]:
    try:
        scanner.elm.port = port
        scanner.elm.raw_logger = raw_logger
        scanner.connect()
        try:
            info = scanner.get_vehicle_info()
        except ConnectionLostError:
            return False, {}, ConnectionLostError("Device disconnected")
        return True, info, None
    except Exception as exc:
        return False, {}, exc
