from __future__ import annotations

from datetime import datetime, timezone

from app.application.time_utils import cr_timestamp
from app.domain.entities import ConnectionLostError, NotConnectedError, ScannerError

from app.presentation.cli.actions.common import require_connected_scanner
from app.bootstrap import get_container
from app.presentation.cli.i18n import t
from app.application.state import AppState
from app.presentation.cli.ui import print_header, print_subheader, handle_disconnection


def run_full_scan(state: AppState) -> None:
    scanner = require_connected_scanner(state)
    if not scanner:
        return

    lines = []

    def emit(line: str = "") -> None:
        print(line)
        lines.append(line)

    def subheader(title: str) -> None:
        print_subheader(title)
        lines.append("-" * 40)
        lines.append(f"  {title}")
        lines.append("-" * 40)

    print_header(t("scan_header"))
    lines.append("=" * 60)
    lines.append(f"  {t('scan_header')}")
    lines.append("=" * 60)
    emit("")
    emit(f"  🕐 {t('report_time')}: {cr_timestamp()}")
    emit("")

    scan_timestamp = datetime.now(timezone.utc)

    scan_service = get_container().scans
    full_scan_reports = get_container().full_scan_reports
    try:
        subheader(t("vehicle_connection"))
        info = scan_service.get_vehicle_info()
        emit(f"  {t('elm_version')}: {info.get('elm_version', 'unknown')}")
        emit(f"  {t('protocol')}: {info.get('protocol', 'unknown')}")
        emit(f"  {t('mil_status')}: {info.get('mil_on', 'unknown')}")
        emit(f"  {t('dtc_count')}: {info.get('dtc_count', 'unknown')}")

        subheader(t("dtc_header"))
        dtcs = scan_service.read_dtcs()
        if dtcs:
            for dtc in dtcs:
                emoji = "🚨" if dtc.status == "stored" else "⚠️"
                status = f" ({dtc.status})" if dtc.status != "stored" else ""
                emit(f"")
                emit(f"  {emoji} {dtc.code}{status}")
                emit(f"     └─ {dtc.description}")
        else:
            emit(f"")
            emit(f"  ✅ {t('no_codes')}")

        subheader(t("readiness_header"))
        readiness = scan_service.read_readiness()
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
                emit(f"  {emoji} {name}: {status.status_str}")
            emit(f"")
            emit(f"  {t('summary')}: {complete} {t('complete')}, {incomplete} {t('incomplete')}")

        subheader(t("live_header"))
        readings = scan_service.read_live_data()
        if readings:
            for reading in readings.values():
                emit(f"")
                emit(f"  📈 {reading.name}")
                emit(f"     └─ {reading.value} {reading.unit}")

                if reading.name == "Engine Coolant Temperature":
                    if reading.value > 105:
                        emit(f"     🔥 {t('warning_high_temp')}")
                    elif reading.value < 70:
                        emit(f"     ⚠️  {t('warning_low_temp')}")
                elif "Throttle" in reading.name and reading.value > 5:
                    emit(f"     ⚠️  {t('warning_throttle')}")

        emit("")
        emit("=" * 60)
        emit(f"  {t('report_time')}: {cr_timestamp()}")
        emit("=" * 60)

        full_scan_reports.save(lines)
        emit(f"\n  ✅ {t('full_scan_saved_hidden')}")
    except ConnectionLostError:
        handle_disconnection(state)
    except NotConnectedError:
        print(f"\n  ❌ {t('not_connected')}")
    except ScannerError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
