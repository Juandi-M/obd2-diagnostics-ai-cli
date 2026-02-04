from __future__ import annotations

from app.application.time_utils import cr_timestamp
from app.domain.entities import ConnectionLostError, NotConnectedError, ScannerError

from app.presentation.cli.actions.common import require_connected_scanner
from app.bootstrap import get_container
from app.presentation.cli.i18n import t
from app.application.state import AppState
from app.presentation.cli.ui import handle_disconnection, print_header


def read_codes(state: AppState) -> None:
    scanner = require_connected_scanner(state)
    if not scanner:
        return

    print_header(t("dtc_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")

    try:
        dtcs = get_container().scans.read_dtcs()
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
