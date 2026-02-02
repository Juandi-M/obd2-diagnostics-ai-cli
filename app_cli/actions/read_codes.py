from __future__ import annotations

from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError
from obd.utils import cr_timestamp

from app_cli.actions.common import require_connected_scanner
from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import handle_disconnection, print_header


def read_codes(state: AppState) -> None:
    scanner = require_connected_scanner(state)
    if not scanner:
        return

    print_header(t("dtc_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")

    try:
        dtcs = scanner.read_dtcs()
        if dtcs:
            for dtc in dtcs:
                status = f" [{dtc.status}]" if dtc.status != "stored" else ""
                print(f"  {dtc.code}{status}: {dtc.description}")
        else:
            print(f"  ✅ {t('no_codes')}")
    except ConnectionLostError:
        handle_disconnection(state)
    except NotConnectedError:
        print(f"\n  ❌ {t('not_connected')}")
    except ScannerError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
