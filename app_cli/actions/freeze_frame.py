from __future__ import annotations

from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError
from obd.utils import cr_timestamp

from app_cli.actions.common import require_connected_scanner
from app_core.scans import read_freeze_frame as read_freeze_frame_core
from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import handle_disconnection, print_header


def read_freeze_frame(state: AppState) -> None:
    scanner = require_connected_scanner(state)
    if not scanner:
        return

    print_header(t("freeze_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")

    try:
        freeze = read_freeze_frame_core(scanner)
        if freeze:
            print(f"  {t('dtc_triggered')}: {freeze.dtc_code}\n")
            for reading in freeze.readings.values():
                print(f"  {reading.name}: {reading.value} {reading.unit}")
        else:
            print(f"  {t('no_freeze_data')}")
            print(f"  {t('freeze_tip')}")
    except ConnectionLostError:
        handle_disconnection(state)
    except NotConnectedError:
        print(f"\n  ❌ {t('not_connected')}")
    except ScannerError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
