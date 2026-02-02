from __future__ import annotations

from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import print_header


def search_codes(state: AppState) -> None:
    dtc_db = state.ensure_dtc_db()

    print_header(t("search_header"))
    query = input(f"  {t('search_prompt')}: ").strip()
    if not query:
        return

    results = dtc_db.search(query)
    if results:
        print(f"\n  {t('found_codes', count=len(results))}\n")
        for info in results[:20]:
            print(f"  {info.code}: {info.description}")
        if len(results) > 20:
            print(f"\n  ... +{len(results) - 20} more")
    else:
        print(f"\n  {t('no_codes_found', query=query)}")
