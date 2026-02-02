from __future__ import annotations

from obd import ELM327
from obd.obd2.base import ConnectionLostError
from obd.utils import cr_timestamp
from obd.legacy_kline.adapter import LegacyKLineAdapter
from obd.legacy_kline.session import LegacyKLineSession
from obd.legacy_kline.profiles import ISO9141_2, KWP2000_5BAUD, KWP2000_FAST, td5_candidates
from obd.legacy_kline.config.errors import KLineDetectError, KLineError

from app.i18n import t
from app.state import AppState
from app.ui import print_header, handle_disconnection


def connect_vehicle(state: AppState) -> None:
    print_header(t("connect_header"))
    print(f"  {t('time')}: {cr_timestamp()}")
    if state.verbose:
        print(f"  🧪 {t('verbose_logging')}: {t('on')}")
        print(f"  {t('raw_log_file')}: logs/obd_raw.log")

    scanner = state.ensure_scanner()
    if state.active_scanner():
        print(f"\n  ⚠️  {t('already_connected')}")
        confirm = input(f"  {t('disconnect_reconnect')} (y/n): ").strip().lower()
        if confirm not in ["y", "s"]:
            return
        state.disconnect_all()

    print(f"\n🔍 {t('searching_adapter')}")
    ports = ELM327.find_ports()
    if not ports:
        bt_ports = ELM327.find_bluetooth_ports()
        if not bt_ports:
            print(f"\n  ❌ {t('no_ports_found')}")
            print(f"  💡 {t('adapter_tip')}")
            return
        print(f"\n  🔵 {t('bluetooth_ports_found', count=len(bt_ports))}")
        ports = bt_ports

    print(f"  {t('found_ports', count=len(ports))}")

    for port in ports:
        try:
            print(f"\n  {t('trying_port', port=port)}")
            scanner.elm.port = port
            scanner.elm.raw_logger = state.raw_logger()
            scanner.connect()
            print(f"  ✅ {t('connected_on', port=port)}")
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
            return
        except Exception as exc:
            print(f"  ❌ {t('connection_failed', error=str(exc))}")
            _print_connect_debug(state, scanner.elm, exc, port)
            try:
                scanner.disconnect()
            except Exception:
                pass

            if _try_kline(state, port):
                return

    print(f"\n  ❌ {t('no_vehicle_response')}")
    print(f"  💡 {t('adapter_tip')}")


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
