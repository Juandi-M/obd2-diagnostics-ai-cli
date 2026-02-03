from __future__ import annotations

from typing import Dict, Any, List, Optional

from obd.uds.client import UdsClient
from obd.uds.exceptions import UdsNegativeResponse, UdsResponseError
from obd.uds.modules import module_map

from app_cli.actions.common import require_connected_scanner
from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import press_enter, print_header, print_menu
from app_core.uds_discovery import DiscoveryOptions, discover_uds_modules
from app_core.vin_cache import get_vin_cache


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


def _select_module(state: AppState, brand: str) -> Optional[Dict[str, Any]]:
    modules: Dict[str, Dict[str, str]] = module_map(brand)
    names = sorted(modules.keys())
    if not names:
        return None

    entries: List[Dict[str, Any]] = []
    cached = _cached_map_for_state(state)
    if cached:
        proto = cached.get("protocol") or "6"
        for mod in cached.get("modules", []):
            tx = mod.get("tx_id")
            rx = mod.get("rx_id")
            mtype = mod.get("module_type") or ""
            suffix = f" · {mtype}" if mtype else ""
            label = f"{t('uds_cached_tag')} · {tx}->{rx}{suffix}"
            entries.append(
                {
                    "kind": "cached",
                    "label": label,
                    "tx_id": tx,
                    "rx_id": rx,
                    "protocol": proto,
                }
            )

    for name in names:
        entries.append({"kind": "named", "label": name, "name": name})

    print(f"\n  {t('uds_select_module')}:")
    for idx, entry in enumerate(entries, start=1):
        print(f"    {idx}. {entry['label']}")

    choice = input(f"\n  {t('select_option')}: ").strip()
    if not choice.isdigit():
        return None
    index = int(choice)
    if 1 <= index <= len(entries):
        return entries[index - 1]
    return None


def uds_tools_menu(state: AppState) -> None:
    scanner = require_connected_scanner(state)
    if not scanner:
        return
    if getattr(scanner, "is_legacy", False):
        print(f"\n  ❌ {t('uds_not_supported')}")
        press_enter()
        return

    print_header(t("uds_header"))
    brand = _select_brand(state)
    module_entry = _select_module(state, brand)
    if not module_entry:
        print(f"\n  ❌ {t('uds_no_module')}")
        press_enter()
        return

    try:
        client = _build_client(scanner.elm, brand, module_entry)
    except UdsResponseError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
        press_enter()
        return

    cached = _cached_map_for_state(state)
    if cached:
        vin = state.last_vin or ""
        choice = input(f"\n  {t('uds_discovery_cached_prompt')} {vin} (y/N): ").strip().lower()
        if choice in {"y", "yes", "s", "si"}:
            _print_cached_map(cached)

    while True:
        print_menu(
            t("uds_menu"),
            [
                ("1", t("uds_read_vin")),
                ("2", t("uds_read_did")),
                ("3", t("uds_send_raw")),
                ("4", t("uds_read_dtcs")),
                ("5", t("uds_discover_modules")),
                ("6", t("uds_discover_cached")),
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
        elif choice == "4":
            _read_dtcs(client)
            press_enter()
        elif choice == "5":
            _discover_modules(state)
            press_enter()
        elif choice == "6":
            cached = _cached_map_for_state(state)
            if not cached:
                print(f"\n  ❌ {t('uds_discovery_cached_none')}")
            else:
                _print_cached_map(cached)
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


def _read_dtcs(client: UdsClient) -> None:
    try:
        response = client.send_raw(0x19, bytes([0x02, 0xFF]), raise_on_negative=True)
    except (UdsNegativeResponse, UdsResponseError) as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
        return

    if not response:
        print(f"\n  ❌ {t('uds_no_dtcs')}")
        return

    if len(response) < 3 or response[0] != 0x59 or response[1] != 0x02:
        print(f"\n  {t('uds_response')}: {response.hex().upper()}")
        return

    status_mask = response[2]
    payload = response[3:]
    if not payload:
        print(f"\n  {t('uds_no_dtcs')}")
        return

    print(f"\n  {t('uds_dtc_header')}:")
    print(f"    {t('uds_dtc_status_mask')}: 0x{status_mask:02X}")
    for idx in range(0, len(payload), 4):
        if idx + 4 > len(payload):
            break
        dtc_bytes = payload[idx : idx + 3]
        status = payload[idx + 3]
        dtc_hex = dtc_bytes.hex().upper()
        print(f"    - 0x{dtc_hex} | status 0x{status:02X}")


def _print_did_response(info: Dict[str, str]) -> None:
    print(f"\n  {t('uds_response')}:")
    print(f"    DID: {info.get('did')}")
    if info.get("name"):
        print(f"    Name: {info.get('name')}")
    if info.get("value"):
        print(f"    Value: {info.get('value')}")
    print(f"    Raw: {info.get('raw')}")


def _build_client(elm, brand: str, module_entry: Dict[str, Any]) -> UdsClient:
    if module_entry.get("kind") == "cached":
        return UdsClient(
            elm,
            tx_id=str(module_entry.get("tx_id")),
            rx_id=str(module_entry.get("rx_id")),
            protocol=str(module_entry.get("protocol") or "6"),
        )
    return UdsClient.from_module(elm, brand, module_entry.get("name") or "")


def _discover_modules(state: AppState) -> None:
    scanner = state.active_scanner()
    if not scanner:
        print(f"\n  ❌ {t('not_connected')}")
        return
    if getattr(scanner, "is_legacy", False):
        print(f"\n  ❌ {t('uds_not_supported')}")
        return

    print_header(t("uds_discovery_header"))
    print(f"  {t('uds_discovery_hint')}")

    range_choice = input(f"\n  {t('uds_discovery_range_prompt')}: ").strip() or "2"
    if range_choice == "1":
        id_start, id_end = 0x7E0, 0x7EF
    else:
        id_start, id_end = 0x700, 0x7FF

    try_250 = input(f"  {t('uds_discovery_try_250')} ").strip().lower()
    include_29 = input(f"  {t('uds_discovery_29bit')} ").strip().lower()
    probe_dtcs = input(f"  {t('uds_discovery_dtcs')} ").strip().lower()
    timeout_raw = input(f"  {t('uds_discovery_timeout')} ").strip()

    options = DiscoveryOptions(
        id_start=id_start,
        id_end=id_end,
        timeout_s=_parse_timeout(timeout_raw),
        try_250k=try_250 not in {"n", "no"},
        include_29bit=include_29 in {"y", "yes", "s", "si"},
        confirm_vin=True,
        confirm_dtcs=probe_dtcs in {"y", "yes", "s", "si"},
        brand_hint=state.manufacturer,
    )

    try:
        result = discover_uds_modules(scanner.elm, options)
    except Exception as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
        return

    modules: List[Any] = result.get("modules") or []
    if not modules:
        print(f"\n  ❌ {t('uds_discovery_none')}")
        return

    proto = result.get("protocol") or "?"
    addressing = result.get("addressing") or "?"
    vin = result.get("vin") or ""

    print(f"\n  {t('uds_discovery_found')}: {len(modules)}")
    print(f"  {t('uds_discovery_protocol')}: {proto} ({addressing})")
    if vin:
        print(f"  {t('uds_discovery_vin')}: {vin}")

    for mod in modules:
        print(f"\n  - TX {mod.tx_id} -> RX {mod.rx_id}")
        if mod.responses:
            print(f"    {t('uds_discovery_responses')}: {', '.join(mod.responses)}")
        if mod.alt_tx_ids:
            print(f"    {t('uds_discovery_alt_tx')}: {', '.join(mod.alt_tx_ids)}")
        if mod.fingerprint.get("vin"):
            print(f"    VIN: {mod.fingerprint.get('vin')}")
        if mod.module_type:
            print(f"    {t('uds_discovery_type')}: {mod.module_type}")
        if mod.fingerprint.get("dtc_summary"):
            summary = mod.fingerprint.get("dtc_summary") or {}
            counts = " ".join(f"{k}:{v}" for k, v in summary.items())
            print(f"    {t('uds_discovery_dtcs_summary')}: {counts}")
        if mod.requires_security:
            print(f"    {t('uds_discovery_security')}")
        print(f"    {t('uds_discovery_confidence')}: {mod.confidence}")


def _parse_timeout(value: str) -> float:
    try:
        ms = int(value)
        if ms <= 0:
            return 0.12
        return max(0.05, min(ms / 1000.0, 2.0))
    except Exception:
        return 0.12


def _cached_map_for_state(state: AppState) -> Optional[Dict[str, Any]]:
    vin = state.last_vin or ""
    if not vin:
        return None
    cached = get_vin_cache(vin) or {}
    return cached.get("uds_modules")


def _print_cached_map(cached: Dict[str, Any]) -> None:
    modules = cached.get("modules") or []
    if not modules:
        print(f"\n  ❌ {t('uds_discovery_cached_none')}")
        return
    print_header(t("uds_discovery_cached_header"))
    proto = cached.get("protocol") or "?"
    addressing = cached.get("addressing") or "?"
    print(f"  {t('uds_discovery_protocol')}: {proto} ({addressing})")
    for mod in modules:
        tx = mod.get("tx_id")
        rx = mod.get("rx_id")
        print(f"\n  - TX {tx} -> RX {rx}")
        if mod.get("module_type"):
            print(f"    {t('uds_discovery_type')}: {mod.get('module_type')}")
        if mod.get("fingerprint", {}).get("dtc_summary"):
            summary = mod.get("fingerprint", {}).get("dtc_summary") or {}
            counts = " ".join(f"{k}:{v}" for k, v in summary.items())
            print(f"    {t('uds_discovery_dtcs_summary')}: {counts}")
        if mod.get("responses"):
            print(f"    {t('uds_discovery_responses')}: {', '.join(mod.get('responses'))}")
        if mod.get("requires_security"):
            print(f"    {t('uds_discovery_security')}")
