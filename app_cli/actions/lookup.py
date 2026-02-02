from __future__ import annotations

from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import print_header


def lookup_code(state: AppState) -> None:
    dtc_db = state.ensure_dtc_db()

    print_header(t("code_lookup_header"))
    print(f"  {dtc_db.count} {t('codes_loaded')}")
    print(f"  {t('manufacturer')}: {state.manufacturer.capitalize()}\n")

    code = input(f"  {t('enter_code')}: ").strip().upper()
    if not code:
        return

    info = dtc_db.lookup(code)
    if info:
        print(f"\n  📋 {info.code}")
        print(f"     └─ {info.description}")
        print(f"     └─ {t('source')}: {info.source}")
    else:
        print(f"\n  ❌ {t('code_not_found', code=code)}")
        results = dtc_db.search(code)
        if results:
            print(f"\n  {t('similar_codes')}:")
            for result in results[:5]:
                print(f"    {result.code}: {result.description}")
