from __future__ import annotations

from typing import Any, Dict

from app.application.state import AppState
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.features.uds.uds_presenters import (
    format_discovery_result,
    format_read_did,
    format_read_dtcs,
    format_send_raw,
)


def read_vin(state: AppState, brand: str, module_entry: Dict[str, Any]) -> str:
    client = get_vm().uds_tools.build_client(brand, module_entry)
    info = client.read_did(brand, "F190")
    return format_read_did(state, "uds_read_vin", info)


def read_did(state: AppState, brand: str, module_entry: Dict[str, Any], did: str) -> str:
    client = get_vm().uds_tools.build_client(brand, module_entry)
    info = client.read_did(brand, did)
    return format_read_did(state, "uds_read_did", info)


def send_raw(state: AppState, brand: str, module_entry: Dict[str, Any], service_hex: str, data_hex: str) -> str:
    client = get_vm().uds_tools.build_client(brand, module_entry)
    service_id = int(service_hex, 16)
    data = bytes.fromhex(data_hex) if data_hex else b""
    response = client.send_raw(service_id, data)
    return format_send_raw(state, response)


def read_dtcs(state: AppState, brand: str, module_entry: Dict[str, Any]) -> str:
    client = get_vm().uds_tools.build_client(brand, module_entry)
    response = client.send_raw(0x19, bytes([0x02, 0xFF]), raise_on_negative=True)
    return format_read_dtcs(state, response)


def discover_modules(state: AppState, options: Dict[str, Any]) -> str:
    result = get_vm().uds_discovery.discover(options)
    return format_discovery_result(state, result or {})

