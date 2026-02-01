from __future__ import annotations

import signal
import time

from obd.logger import SessionLogger
from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError
from obd.utils import cr_timestamp, cr_time_only

from app.actions.common import require_connected_scanner
from app.i18n import t
from app.state import AppState
from app.ui import handle_disconnection, print_header


def _signal_handler(sig, frame, state: AppState) -> None:
    state.stop_monitoring = True
    print("\n\n⏹️  " + t("cancelled"))


def live_monitor(state: AppState) -> None:
    scanner = require_connected_scanner(state.scanner)
    if not scanner:
        return

    state.stop_monitoring = False
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda sig, frame: _signal_handler(sig, frame, state))

    try:
        print(f"\n  📊 {t('live_telemetry')}")
        log_choice = input(f"  {t('save_log_prompt')} (y/n): ").strip().lower()

        logger = None
        if log_choice in ["y", "s"]:
            logger = SessionLogger("logs")
            log_file = logger.start_session(format=state.log_format)
            print(f"  📝 {t('logging_to')}: {log_file}")

        print_header(t("live_telemetry"))
        print(f"  {t('started')}: {cr_timestamp()}")
        print(f"  {t('refresh')}: {state.monitor_interval}s")
        print(f"\n  {t('press_ctrl_c')}\n")
        print("-" * 70)
        print(
            f"{t('time'):<10} {t('coolant'):<10} {'RPM':<8} {t('speed'):<8} "
            f"{t('throttle'):<10} {t('pedal'):<8} {t('volts'):<8}"
        )
        print("-" * 70)

        pids = ["05", "0C", "0D", "11", "49", "42"]
        while not state.stop_monitoring:
            try:
                readings = scanner.read_live_data(pids)
                if logger:
                    logger.log_readings(readings)

                coolant = readings.get("05")
                rpm = readings.get("0C")
                speed = readings.get("0D")
                throttle = readings.get("11")
                pedal = readings.get("49")
                volts = readings.get("42")

                time_str = cr_time_only()
                coolant_str = f"{coolant.value:.0f}°C" if coolant else "---"
                rpm_str = f"{rpm.value:.0f}" if rpm else "---"
                speed_str = f"{speed.value:.0f}km/h" if speed else "---"
                throttle_str = f"{throttle.value:.1f}%" if throttle else "---"
                pedal_str = f"{pedal.value:.1f}%" if pedal else "---"
                volts_str = f"{volts.value:.1f}V" if volts else "---"

                print(
                    f"{time_str:<10} {coolant_str:<10} {rpm_str:<8} {speed_str:<8} "
                    f"{throttle_str:<10} {pedal_str:<8} {volts_str:<8}"
                )
                time.sleep(state.monitor_interval)
            except ConnectionLostError:
                handle_disconnection(state)
                break
            except NotConnectedError:
                print(f"\n  ❌ {t('not_connected')}")
                break
            except ScannerError as exc:
                print(f"\n  ❌ {t('error')}: {exc}")
                break

        print("-" * 70)
        if logger:
            summary = logger.end_session()
            print(f"\n📊 {t('session_summary')}:")
            print(f"   {t('file')}: {summary.get('file', 'N/A')}")
            print(f"   {t('duration')}: {summary.get('duration_seconds', 0):.1f} {t('seconds')}")
            print(f"   {t('readings')}: {summary.get('reading_count', 0)}")
    finally:
        signal.signal(signal.SIGINT, original_sigint)
