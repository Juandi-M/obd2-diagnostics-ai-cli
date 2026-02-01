from __future__ import annotations

from obd import ELM327
from obd.obd2.base import ConnectionLostError
from obd.utils import cr_timestamp

from app.i18n import t
from app.state import AppState
from app.ui import print_header, handle_disconnection


def connect_vehicle(state: AppState) -> None:
    print_header(t("connect_header"))
    print(f"  {t('time')}: {cr_timestamp()}")

    scanner = state.ensure_scanner()
    if scanner.is_connected:
        print(f"\n  ⚠️  {t('already_connected')}")
        confirm = input(f"  {t('disconnect_reconnect')} (y/n): ").strip().lower()
        if confirm not in ["y", "s"]:
            return
        scanner.disconnect()

    print(f"\n🔍 {t('searching_adapter')}")
    ports = ELM327.find_ports()
    if not ports:
        print(f"\n  ❌ {t('no_ports_found')}")
        print(f"  💡 {t('adapter_tip')}")
        return

    print(f"  {t('found_ports', count=len(ports))}")

    for port in ports:
        try:
            print(f"\n  {t('trying_port', port=port)}")
            scanner.elm.port = port
            scanner.connect()
            print(f"  ✅ {t('connected_on', port=port)}")

            try:
                info = scanner.get_vehicle_info()
                print(f"\n  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
                print(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
                mil_status = f"🔴 {t('on')}" if info.get("mil_on") == "Yes" else f"🟢 {t('off')}"
                print(f"  {t('mil_status')}: {mil_status}")
                print(f"  {t('dtc_count')}: {info.get('dtc_count', '?')}")
            except ConnectionLostError:
                handle_disconnection(state)
            return
        except Exception as exc:
            print(f"  ❌ {t('connection_failed', error=str(exc))}")
            try:
                scanner.disconnect()
            except Exception:
                pass

    print(f"\n  ❌ {t('no_vehicle_response')}")
    print(f"  💡 {t('adapter_tip')}")


def disconnect_vehicle(state: AppState) -> None:
    scanner = state.scanner
    if not scanner or not scanner.is_connected:
        print(f"\n  ⚠️  {t('disconnected')}")
        return
    scanner.disconnect()
    print(f"\n  🔌 {t('disconnected_at', time=cr_timestamp())}")
