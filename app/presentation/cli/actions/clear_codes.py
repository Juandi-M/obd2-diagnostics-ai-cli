from __future__ import annotations

from app.application.time_utils import cr_timestamp
from app.domain.entities import ConnectionLostError, ScannerError

from app.presentation.cli.actions.common import require_connected_scanner
from app.bootstrap import get_container
from app.presentation.cli.i18n import t
from app.application.state import AppState
from app.presentation.cli.ui import handle_disconnection, print_header


def clear_codes(state: AppState) -> None:
    scanner = require_connected_scanner(state)
    if not scanner:
        return

    print_header(t("clear_header"))
    print(f"\n  ⚠️  {t('clear_warning')}")
    print(f"     - {t('clear_warn1')}")
    print(f"     - {t('clear_warn2')}")
    print(f"     - {t('clear_warn3')}")
    print(f"     - {t('clear_warn4')}\n")

    confirm = input(f"  {t('type_yes')}: ").strip().upper()
    if confirm in ["YES", "SI", "SÍ"]:
        try:
            if get_container().scans.clear_codes():
                print(f"\n  ✅ {t('clear_success', time=cr_timestamp())}")
            else:
                print(f"\n  ❌ {t('clear_failed')}")
        except ConnectionLostError:
            handle_disconnection(state)
        except ScannerError as exc:
            print(f"\n  ❌ {t('error')}: {exc}")
    else:
        print(f"\n  {t('cancelled')}")
