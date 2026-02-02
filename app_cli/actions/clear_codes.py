from __future__ import annotations

from obd.obd2.base import ConnectionLostError, ScannerError
from obd.utils import cr_timestamp

from app_cli.actions.common import require_connected_scanner
from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import handle_disconnection, print_header


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
            if scanner.clear_dtcs():
                print(f"\n  ✅ {t('clear_success', time=cr_timestamp())}")
            else:
                print(f"\n  ❌ {t('clear_failed')}")
        except ConnectionLostError:
            handle_disconnection(state)
        except ScannerError as exc:
            print(f"\n  ❌ {t('error')}: {exc}")
    else:
        print(f"\n  {t('cancelled')}")
