from __future__ import annotations

from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError
from obd.utils import cr_timestamp

from app.actions.common import require_connected_scanner
from app.i18n import t
from app.state import AppState
from app.ui import print_header, print_subheader, handle_disconnection


def run_full_scan(state: AppState) -> None:
    scanner = require_connected_scanner(state.scanner)
    if not scanner:
        return

    print_header(t("scan_header"))
    print(f"  🕐 {t('report_time')}: {cr_timestamp()}")

    try:
        print_subheader(t("vehicle_connection"))
        info = scanner.get_vehicle_info()
        print(f"  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
        print(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
        print(f"  {t('mil_status')}: {info.get('mil_on', 'unknown')}")
        print(f"  {t('dtc_count')}: {info.get('dtc_count', 'unknown')}")

        print_subheader(t("dtc_header"))
        dtcs = scanner.read_dtcs()
        if dtcs:
            for dtc in dtcs:
                emoji = "🚨" if dtc.status == "stored" else "⚠️"
                status = f" ({dtc.status})" if dtc.status != "stored" else ""
                print(f"\n  {emoji} {dtc.code}{status}")
                print(f"     └─ {dtc.description}")
        else:
            print(f"\n  ✅ {t('no_codes')}")

        print_subheader(t("readiness_header"))
        readiness = scanner.read_readiness()
        if readiness:
            complete = incomplete = 0
            for name, status in readiness.items():
                if name == "MIL (Check Engine Light)":
                    continue
                if not status.available:
                    emoji = "➖"
                elif status.complete:
                    emoji = "✅"
                    complete += 1
                else:
                    emoji = "❌"
                    incomplete += 1
                print(f"  {emoji} {name}: {status.status_str}")
            print(f"\n  {t('summary')}: {complete} {t('complete')}, {incomplete} {t('incomplete')}")

        print_subheader(t("live_header"))
        readings = scanner.read_live_data()
        if readings:
            for reading in readings.values():
                print(f"\n  📈 {reading.name}")
                print(f"     └─ {reading.value} {reading.unit}")

                if reading.name == "Engine Coolant Temperature":
                    if reading.value > 105:
                        print(f"     🔥 {t('warning_high_temp')}")
                    elif reading.value < 70:
                        print(f"     ⚠️  {t('warning_low_temp')}")
                elif "Throttle" in reading.name and reading.value > 5:
                    print(f"     ⚠️  {t('warning_throttle')}")

        print("\n" + "=" * 60)
        print(f"  {t('report_time')}: {cr_timestamp()}")
        print("=" * 60)
    except ConnectionLostError:
        handle_disconnection(state)
    except NotConnectedError:
        print(f"\n  ❌ {t('not_connected')}")
    except ScannerError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
