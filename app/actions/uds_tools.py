from __future__ import annotations

from typing import Dict

from obd.uds.client import UdsClient
from obd.uds.exceptions import UdsNegativeResponse, UdsResponseError
from obd.uds.modules import module_map

from app.actions.common import require_connected_scanner
from app.i18n import t
from app.state import AppState
from app.ui import press_enter, print_header, print_menu


def _select_brand(state: AppState) -> str:
    default = "jeep"
    if state.manufacturer == "landrover":
        default = "land_rover"
    elif state.manufacturer == "chrysler":
        default = "jeep"

    print(f"\n  {t('uds_select_brand')}:")
    print("    1. Jeep / Chrysler")
    print("    2. Land Rover")
    choice = input(f"\n  {t('select_option')} (1-2): ").strip()
    if choice == "2":
        return "land_rover"
    if choice == "1":
        return "jeep"
    return default


def _select_module(brand: str) -> str:
    modules: Dict[str, Dict[str, str]] = module_map(brand)
    names = sorted(modules.keys())
    if not names:
        return ""

    print(f"\n  {t('uds_select_module')}:")
    for idx, name in enumerate(names, start=1):
        print(f"    {idx}. {name}")

    choice = input(f"\n  {t('select_option')}: ").strip()
    if not choice.isdigit():
        return ""
    index = int(choice)
    if 1 <= index <= len(names):
        return names[index - 1]
    return ""


def uds_tools_menu(state: AppState) -> None:
    scanner = require_connected_scanner(state.scanner)
    if not scanner:
        return

    print_header(t("uds_header"))
    brand = _select_brand(state)
    module_name = _select_module(brand)
    if not module_name:
        print(f"\n  ❌ {t('uds_no_module')}")
        press_enter()
        return

    try:
        client = UdsClient.from_module(scanner.elm, brand, module_name)
    except UdsResponseError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
        press_enter()
        return

    while True:
        print_menu(
            t("uds_menu"),
            [
                ("1", t("uds_read_vin")),
                ("2", t("uds_read_did")),
                ("3", t("uds_send_raw")),
                ("0", t("back")),
            ],
        )
        choice = input(f"\n  {t('select_option')}: ").strip()
        if choice == "1":
            _read_vin(client, brand)
            press_enter()
        elif choice == "2":
            _read_did(client, brand)
            press_enter()
        elif choice == "3":
            _send_raw(client)
            press_enter()
        elif choice == "0":
            break


def _read_vin(client: UdsClient, brand: str) -> None:
    try:
        info = client.read_did(brand, "F190")
        _print_did_response(info)
    except (UdsNegativeResponse, UdsResponseError) as exc:
        print(f"\n  ❌ {t('error')}: {exc}")


def _read_did(client: UdsClient, brand: str) -> None:
    did = input(f"\n  {t('uds_read_did')} (e.g., F190): ").strip()
    if not did:
        return
    try:
        info = client.read_did(brand, did)
        _print_did_response(info)
    except (UdsNegativeResponse, UdsResponseError) as exc:
        print(f"\n  ❌ {t('error')}: {exc}")


def _send_raw(client: UdsClient) -> None:
    service_hex = input(f"\n  {t('uds_service_id')}: ").strip()
    if not service_hex:
        return
    data_hex = input(f"  {t('uds_data_hex')}: ").strip()
    try:
        service_id = int(service_hex, 16)
        data = bytes.fromhex(data_hex) if data_hex else b""
    except ValueError:
        print(f"\n  ❌ {t('invalid_number')}")
        return
    try:
        response = client.send_raw(service_id, data)
        print(f"\n  {t('uds_response')}: {response.hex().upper()}")
    except (UdsNegativeResponse, UdsResponseError) as exc:
        print(f"\n  ❌ {t('error')}: {exc}")


def _print_did_response(info: Dict[str, str]) -> None:
    print(f"\n  {t('uds_response')}:")
    print(f"    DID: {info.get('did')}")
    if info.get("name"):
        print(f"    Name: {info.get('name')}")
    if info.get("value"):
        print(f"    Value: {info.get('value')}")
    print(f"    Raw: {info.get('raw')}")
