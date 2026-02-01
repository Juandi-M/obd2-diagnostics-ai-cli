from __future__ import annotations

from obd.obd2.base import ConnectionLostError, NotConnectedError, ScannerError
from obd.utils import cr_timestamp

from app.actions.common import require_connected_scanner
from app.i18n import t
from app.state import AppState
from app.ui import handle_disconnection, print_header


def read_readiness(state: AppState) -> None:
    scanner = require_connected_scanner(state.scanner)
    if not scanner:
        return

    print_header(t("readiness_header"))
    print(f"  {t('time')}: {cr_timestamp()}\n")

    try:
        readiness = scanner.read_readiness()
        if not readiness:
            print(f"  ❌ {t('unable_read_readiness')}")
            return

        complete = incomplete = na = 0
        for name, status in readiness.items():
            if not status.available:
                emoji = "➖"
                na += 1
            elif status.complete:
                emoji = "✅"
                complete += 1
            else:
                emoji = "❌"
                incomplete += 1
            print(f"  {emoji} {name}: {status.status_str}")

        print(f"\n  {t('summary')}:")
        print(f"    ✅ {t('complete')}: {complete}")
        print(f"    ❌ {t('incomplete')}: {incomplete}")
        print(f"    ➖ {t('not_available')}: {na}")

        if incomplete > 0:
            print(f"\n  💡 {t('readiness_tip')}")
            print(f"     {t('readiness_tip2')}")
    except ConnectionLostError:
        handle_disconnection(state)
    except NotConnectedError:
        print(f"\n  ❌ {t('not_connected')}")
    except ScannerError as exc:
        print(f"\n  ❌ {t('error')}: {exc}")
