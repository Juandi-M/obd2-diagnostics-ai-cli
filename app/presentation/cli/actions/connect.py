from __future__ import annotations

from app.application.time_utils import cr_timestamp
from app.domain.entities import ConnectionLostError

from app.presentation.cli.i18n import t
from app.bootstrap import get_container
from app.application.state import AppState
from app.presentation.cli.ui import print_header, handle_disconnection
import platform


def connect_vehicle(state: AppState, *, auto: bool = False, mode: str = "auto") -> bool:
    if auto:
        print(f"\n  {t('auto_connecting')}")
    else:
        print_header(t("connect_header"))
        print(f"  {t('time')}: {cr_timestamp()}")
        if state.verbose:
            print(f"  🧪 {t('verbose_logging')}: {t('on')}")
            print(f"  {t('raw_log_file')}: {get_container().data_paths.raw_log_path()}")

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
        get_container().settings.save()

    connection = get_container().connection
    usb_ports = connection.scan_usb_ports() if mode != "ble" else []
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
        bt_devices, ble_err = connection.scan_ble_devices(include_all=include_all)
        bt_devices = [(_port, _name, _rssi) for _port, _name, _rssi in bt_devices]
        bt_ports = [port for port, _, _ in bt_devices]
        if ble_err == "ble_unavailable":
            print(f"\n  ❌ {t('ble_unavailable')}")
        elif ble_err == "ble_error":
            print(f"\n  ❌ {t('ble_scan_failed')}")
        if not bt_devices and not include_all:
            retry_all = input(f"\n  {t('ble_none_found_obd_retry')} ").strip().lower()
            if retry_all in {"y", "yes", "s", "si"}:
                bt_devices, ble_err = connection.scan_ble_devices(include_all=True)
                bt_devices = [(_port, _name, _rssi) for _port, _name, _rssi in bt_devices]
                bt_ports = [port for port, _, _ in bt_devices]
                if ble_err == "ble_unavailable":
                    print(f"\n  ❌ {t('ble_unavailable')}")
                elif ble_err == "ble_error":
                    print(f"\n  ❌ {t('ble_scan_failed')}")

    selected_ble = None
    if bt_devices:
        print(f"\n  🔵 {t('bluetooth_ports_found', count=len(bt_devices))}")
        print(f"  {t('ble_devices_header')}:")
        for idx, (port, name, rssi) in enumerate(bt_devices, start=1):
            suffix = ""
            if state.last_ble_address and port.endswith(state.last_ble_address):
                suffix = f" ({t('ble_last_used')})"
            rssi_label = f" | {rssi} dBm" if isinstance(rssi, int) and rssi > -999 else ""
            print(f"    {idx}. {name} [{port}]{suffix}{rssi_label}")
        default_choice = ""
        if state.last_ble_address:
            for idx, (port, _, _) in enumerate(bt_devices, start=1):
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
            ok, info, err = connection.try_connect(port)
            if not ok:
                raise err or ConnectionError("Connection failed")
            print(f"  ✅ {t('connected_on', port=port)}")
            is_bt = port.lower().startswith("ble:") or port in bt_ports
            transport = _transport_label(port, is_bt)
            print(f"  {t('transport')}: {transport}")
            if transport != t("transport_serial"):
                print(f"  ✅ {t('bluetooth_ok')}")
            if port.lower().startswith("ble:"):
                state.last_ble_address = port.split(":", 1)[1]
                get_container().settings.save()
            state.clear_kline_scanner()

            if info:
                print(f"\n  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
                print(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
                vin_value = info.get("vin")
                state.last_vin = vin_value if vin_value else None
                if vin_value:
                    print(f"  {t('vin_label')}: {vin_value}")
                else:
                    print(f"  {t('vin_label')}: {t('not_available')}")
                mil_status = f"🔴 {t('on')}" if info.get("mil_on") == "Yes" else f"🟢 {t('off')}"
                print(f"  {t('mil_status')}: {mil_status}")
                print(f"  {t('dtc_count')}: {info.get('dtc_count', '?')}")
            return True
        except Exception as exc:
            print(f"  ❌ {t('connection_failed', error=str(exc))}")
            _print_connect_debug(state, scanner, exc, port)
            if isinstance(exc, ConnectionLostError):
                handle_disconnection(state)
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
                        ok, info, err = connection.try_connect(port)
                        if not ok:
                            raise err or ConnectionError("Connection failed")
                        print(f"  ✅ {t('connected_on', port=port)}")
                        is_bt = True
                        transport = _transport_label(port, is_bt)
                        print(f"  {t('transport')}: {transport}")
                        print(f"  ✅ {t('bluetooth_ok')}")
                        if port.lower().startswith("ble:"):
                            state.last_ble_address = port.split(":", 1)[1]
                            get_container().settings.save()
                        state.clear_kline_scanner()
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
    kline_scanner, info, err = get_container().connection.try_kline(port)
    if kline_scanner:
        print(f"  ✅ {t('kline_detected')}")
        if info:
            print(f"  {t('kline_profile')}: {info.get('profile_name')}")
            print(f"  {t('kline_reason')}: {info.get('reason')}")
        return True
    if err and state.verbose:
        print(f"  🧾 {t('kline_error')}: {err}")
    return False


def _print_connect_debug(state: AppState, scanner, exc: Exception, port: str) -> None:
    if not state.verbose:
        return
    print(f"  🧾 {t('debug_details')}")
    print(f"     {t('error')}: {type(exc).__name__}: {exc}")
    snapshot = {}
    try:
        snapshot = scanner.debug_snapshot()
    except Exception:
        snapshot = {}
    timeout = snapshot.get("timeout")
    baud = getattr(scanner.get_transport(), "baudrate", None)
    if baud is not None and timeout is not None:
        print(f"     {t('port')}: {port} | {t('baudrate')}: {baud} | {t('timeout')}: {timeout}s")
    elif timeout is not None:
        print(f"     {t('port')}: {port} | {t('timeout')}: {timeout}s")
    else:
        print(f"     {t('port')}: {port}")
    elm_version = snapshot.get("elm_version")
    if elm_version:
        print(f"     {t('elm_version')}: {elm_version}")
    last_command = snapshot.get("last_command")
    if last_command:
        print(f"     {t('last_command')}: {last_command}")
    last_response = snapshot.get("last_response") or ""
    if last_response:
        preview = last_response
        print(f"     {t('last_response')}: {preview}")
    last_error = snapshot.get("last_error")
    if last_error:
        print(f"     {t('last_error')}: {last_error}")
    last_duration = snapshot.get("last_duration_s")
    if last_duration is not None:
        print(f"     {t('duration')}: {last_duration:.2f} {t('seconds')}")


def _transport_label(port: str, bluetooth_mode: bool) -> str:
    port_lower = port.lower()
    if port_lower.startswith("ble:"):
        return t("transport_ble")
    if bluetooth_mode:
        return t("transport_bt_classic")
    return t("transport_serial")
