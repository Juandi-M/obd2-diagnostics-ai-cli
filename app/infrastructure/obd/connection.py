from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from obd import ELM327
from obd.obd2.base import ConnectionLostError as OBDConnectionLostError

from app.domain.entities import AppError, ConnectionLostError, ScannerError
from app.domain.ports import ScannerPort


def scan_usb_ports() -> list[str]:
    return ELM327.find_ports()


def scan_ble_devices(include_all: bool = False, timeout_s: Optional[float] = None):
    from obd.ble.ports import scan_ble_devices

    return scan_ble_devices(include_all=include_all, timeout_s=timeout_s)


def try_connect(scanner: ScannerPort, port: str, raw_logger=None) -> Tuple[bool, Dict[str, Any], Optional[Exception]]:
    try:
        scanner.set_port(port)
        scanner.set_raw_logger(raw_logger)
        scanner.connect()
        try:
            info = scanner.get_vehicle_info()
        except ConnectionLostError:
            return False, {}, ConnectionLostError("Device disconnected")
        return True, info, None
    except OBDConnectionLostError as exc:
        return False, {}, ConnectionLostError(str(exc))
    except AppError as exc:
        return False, {}, exc
    except Exception as exc:
        return False, {}, ScannerError(str(exc))
