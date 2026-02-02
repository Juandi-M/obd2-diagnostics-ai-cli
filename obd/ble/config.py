from __future__ import annotations

import os
from typing import Optional


def ble_address() -> Optional[str]:
    return os.environ.get("OBD_BLE_ADDRESS")


def ble_name() -> Optional[str]:
    return os.environ.get("OBD_BLE_NAME")


def ble_service_uuid() -> Optional[str]:
    return os.environ.get("OBD_BLE_SERVICE_UUID")


def ble_rx_uuid() -> Optional[str]:
    return os.environ.get("OBD_BLE_RX_UUID")


def ble_tx_uuid() -> Optional[str]:
    return os.environ.get("OBD_BLE_TX_UUID")


def ble_scan_timeout_s() -> float:
    try:
        return float(os.environ.get("OBD_BLE_SCAN_TIMEOUT", "6.0"))
    except ValueError:
        return 6.0
