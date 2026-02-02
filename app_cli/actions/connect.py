from __future__ import annotations

from obd import ELM327
from obd.obd2.base import ConnectionLostError
from obd.utils import cr_timestamp
from obd.legacy_kline.adapter import LegacyKLineAdapter
from obd.legacy_kline.session import LegacyKLineSession
from obd.legacy_kline.profiles import ISO9141_2, KWP2000_5BAUD, KWP2000_FAST, td5_candidates
from obd.legacy_kline.config.errors import KLineDetectError, KLineError

from app_cli.i18n import t
from obd.bluetooth.ports import is_bluetooth_port_info
from app_cli.state import AppState
from app_cli.settings_store import save_settings, settings_from_state
from app_cli.ui import print_header, handle_disconnection
import platform


def connect_vehicle(state: AppState, *, auto: bool = False, mode: str = "auto") -> bool:
    if auto:
        print(f"\n  {t('auto_connecting')}")
    else:
        print_header(t("connect_header"))
        print(f"  {t('time')}: {cr_timestamp()}")
        if state.verbose:
            print(f"  🧪 {t('verbose_logging')}: {t('on')}")
            print(f"  {t('raw_log_file')}: logs/obd_raw.log")

    scanner = state.ensure_scanner()
    if state.active_scanner():
        if auto:
            return True
        print(f"\n  ⚠️  {t('already_connected')}")
        confirm = input(f"  {t('disconnect_reconnect')} (y/n): ").strip().lower()
        if confirm not in ["y", "s"]:
            return False
        state.disconnect_all()

    print(f"\n🔍 {t('searching_adapter')}")
    if platform.system().lower() == "darwin" and not state.ble_notice_shown:
        print(f"\n  ℹ️  {t('ble_pairing_notice')}")
        state.ble_notice_shown = True
        save_settings(settings_from_state(state))

    usb_ports = ELM327.find_ports() if mode != "ble" else []
    if mode == "usb" and not usb_ports:
        print(f"\n  ⚪ {t('no_usb_ports')}")
        return False
    if mode != "ble" and not usb_ports:
        print(f"\n  ⚪ {t('no_usb_ports')}")
        print(f"  {t('skip_usb_scan')}")

    bt_ports = []
    bt_devices = []
    scan_ble = "n"
    if mode == "ble":
        scan_ble = "y"
    elif mode == "auto":
        scan_ble = input(f"\n  {t('scan_ble_prompt')} ").strip().lower()
    if scan_ble in {"y", "yes", "s", "si"}:
        show_all = input(f"  {t('ble_show_all_prompt')} ").strip().lower()
        include_all = show_all in {"y", "yes", "s", "si"}
        from obd.ble.ports import scan_ble_devices

        bt_devices, ble_err = scan_ble_devices(include_all=include_all)
        bt_ports = [port for port, _ in bt_devices]
        if ble_err == "ble_unavailable":
            print(f"\n  ❌ {t('ble_unavailable')}")
        elif ble_err == "ble_error":
            print(f"\n  ❌ {t('ble_scan_failed')}")
        if not bt_devices and not include_all:
            retry_all = input(f"\n  {t('ble_none_found_obd_retry')} ").strip().lower()
            if retry_all in {"y", "yes", "s", "si"}:
                bt_devices, ble_err = scan_ble_devices(include_all=True)
                bt_ports = [port for port, _ in bt_devices]
                if ble_err == "ble_unavailable":
                    print(f"\n  ❌ {t('ble_unavailable')}")
                elif ble_err == "ble_error":
                    print(f"\n  ❌ {t('ble_scan_failed')}")

    selected_ble = None
    if bt_devices:
        print(f"\n  🔵 {t('bluetooth_ports_found', count=len(bt_devices))}")
        print(f"  {t('ble_devices_header')}:")
        for idx, (port, name) in enumerate(bt_devices, start=1):
            suffix = ""
            if state.last_ble_address and port.endswith(state.last_ble_address):
                suffix = f" ({t('ble_last_used')})"
            print(f"    {idx}. {name} [{port}]{suffix}")
        default_choice = ""
        if state.last_ble_address:
            for idx, (port, _) in enumerate(bt_devices, start=1):
                if port.endswith(state.last_ble_address):
                    default_choice = str(idx)
                    break
        while True:
            choice = input(f"\n  {t('ble_select_prompt')} ").strip()
            if not choice and default_choice:
                choice = default_choice
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(bt_devices):
                    selected_ble = bt_devices[idx][0]
                    break
                print(f"  ❌ {t('ble_select_invalid')}")
                continue
            if choice == "":
                break
            print(f"  ❌ {t('ble_select_invalid')}")
    else:
        if scan_ble in {"y", "yes", "s", "si"}:
            if show_all in {"y", "yes", "s", "si"}:
                print(f"\n  ⚪ {t('ble_none_found')}")
            else:
                print(f"\n  ⚪ {t('ble_none_found_obd')}")

    ports = list(usb_ports)
    if selected_ble and selected_ble not in ports:
        ports.append(selected_ble)

    if not ports:
        if not usb_ports and scan_ble not in {"y", "yes", "s", "si"}:
            print(f"\n  ❌ {t('no_ports_skipped_ble')}")
            return
        if scan_ble in {"y", "yes", "s", "si"} and not bt_devices:
            print(f"\n  ❌ {t('no_ports_ble_empty')}")
            return
        print(f"\n  ❌ {t('no_ports_found')}")
        print(f"  💡 {t('adapter_tip')}")
        return

    if bt_ports and selected_ble:
        print(f"\n  🔵 {t('bluetooth_ports_found', count=1)}")

    print(f"  {t('found_ports', count=len(ports))}")
    if state.verbose:
        if usb_ports:
            print(f"  {t('port')}: {', '.join(usb_ports)}")
        if bt_ports:
            print(f"  {t('available_bluetooth_ports')}: {', '.join(bt_ports)}")

    for port in ports:
        retried_ble = False
        try:
            print(f"\n  {t('trying_port', port=port)}")
            scanner.elm.port = port
            scanner.elm.raw_logger = state.raw_logger()
            scanner.connect()
            print(f"  ✅ {t('connected_on', port=port)}")
            is_bt = port.lower().startswith("ble:") or port in bt_ports or is_bluetooth_port_info(port, None, None)
            transport = _transport_label(port, is_bt)
            print(f"  {t('transport')}: {transport}")
            if transport != t("transport_serial"):
                print(f"  ✅ {t('bluetooth_ok')}")
            if port.lower().startswith("ble:"):
                state.last_ble_address = port.split(":", 1)[1]
                save_settings(settings_from_state(state))
            state.clear_legacy_scanner()

            try:
                info = scanner.get_vehicle_info()
                print(f"\n  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
                print(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
                mil_status = f"🔴 {t('on')}" if info.get("mil_on") == "Yes" else f"🟢 {t('off')}"
                print(f"  {t('mil_status')}: {mil_status}")
                print(f"  {t('dtc_count')}: {info.get('dtc_count', '?')}")
            except ConnectionLostError:
                handle_disconnection(state)
            return True
        except Exception as exc:
            print(f"  ❌ {t('connection_failed', error=str(exc))}")
            _print_connect_debug(state, scanner.elm, exc, port)
            if port.lower().startswith("ble:") and not retried_ble:
                if "no response from vehicle ecu" in str(exc).lower():
                    retried_ble = True
                    print(f"  🔁 {t('ble_retry')}")
                    try:
                        scanner.disconnect()
                    except Exception:
                        pass
                    scanner.elm.timeout = max(scanner.elm.timeout, 5.0)
                    try:
                        scanner.connect()
                        print(f"  ✅ {t('connected_on', port=port)}")
                        is_bt = True
                        transport = _transport_label(port, is_bt)
                        print(f"  {t('transport')}: {transport}")
                        print(f"  ✅ {t('bluetooth_ok')}")
                        if port.lower().startswith("ble:"):
                            state.last_ble_address = port.split(":", 1)[1]
                            save_settings(settings_from_state(state))
                        state.clear_legacy_scanner()
                        return True
                    except Exception:
                        pass
            try:
                scanner.disconnect()
            except Exception:
                pass

            if port.lower().startswith("ble:"):
                continue
            if _try_kline(state, port):
                return True

    print(f"\n  ❌ {t('no_vehicle_response')}")
    print(f"  💡 {t('adapter_tip')}")
    return False


def disconnect_vehicle(state: AppState) -> None:
    if not state.active_scanner():
        print(f"\n  ⚠️  {t('disconnected')}")
        return
    state.disconnect_all()
    print(f"\n  🔌 {t('disconnected_at', time=cr_timestamp())}")


def _try_kline(state: AppState, port: str) -> bool:
    print(f"\n  ⚙️  {t('kline_trying')}")
    try:
        elm = ELM327(port=port, raw_logger=state.raw_logger())
        elm.connect()
    except Exception:
        return False

    candidates = [KWP2000_5BAUD, KWP2000_FAST, ISO9141_2]
    if state.manufacturer == "landrover":
        candidates = candidates + td5_candidates()
    try:
        session = LegacyKLineSession.auto(elm, candidates=candidates)
        adapter = LegacyKLineAdapter(
            session,
            manufacturer=state.manufacturer if state.manufacturer != "generic" else None,
        )
        state.set_legacy_scanner(adapter)
        info = session.info
        print(f"  ✅ {t('kline_detected')}")
        print(f"  {t('kline_profile')}: {info.profile_name}")
        print(f"  {t('kline_reason')}: {info.reason}")
        return True
    except KLineDetectError as exc:
        if state.verbose:
            print(f"  🧾 {t('kline_error')}: {exc}")
        try:
            elm.close()
        except Exception:
            pass
        return False
    except KLineError as exc:
        if state.verbose:
            print(f"  🧾 {t('kline_error')}: {exc}")
        try:
            elm.close()
        except Exception:
            pass
        return False
    except Exception as exc:
        if state.verbose:
            print(f"  🧾 {t('kline_error')}: {exc}")
        try:
            elm.close()
        except Exception:
            pass
        return False


def _print_connect_debug(state: AppState, elm: ELM327, exc: Exception, port: str) -> None:
    if not state.verbose:
        return
    print(f"  🧾 {t('debug_details')}")
    print(f"     {t('error')}: {type(exc).__name__}: {exc}")
    print(
        f"     {t('port')}: {port} | {t('baudrate')}: {elm.baudrate} | "
        f"{t('timeout')}: {elm.timeout}s"
    )
    if elm.elm_version:
        print(f"     {t('elm_version')}: {elm.elm_version}")
    if elm.protocol:
        print(f"     {t('protocol')}: {elm.protocol}")
    if elm.last_command:
        print(f"     {t('last_command')}: {elm.last_command}")
    if elm.last_lines:
        preview = " | ".join(elm.last_lines[:4])
        if len(elm.last_lines) > 4:
            preview += " | ..."
        print(f"     {t('last_response')}: {preview}")
    if elm.last_error:
        print(f"     {t('last_error')}: {elm.last_error}")
    if elm.last_duration_s is not None:
        print(f"     {t('duration')}: {elm.last_duration_s:.2f} {t('seconds')}")


def _transport_label(port: str, bluetooth_mode: bool) -> str:
    port_lower = port.lower()
    if port_lower.startswith("ble:"):
        return t("transport_ble")
    if bluetooth_mode or is_bluetooth_port_info(port, None, None):
        return t("transport_bt_classic")
    return t("transport_serial")
