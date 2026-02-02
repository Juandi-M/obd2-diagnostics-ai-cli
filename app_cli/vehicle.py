from __future__ import annotations

from typing import List, Tuple

from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import clear_screen, print_menu
from app_core.vehicle import apply_brand_selection, get_brand_options, save_profile_for_group


BrandOption = Tuple[str, str]


def select_brand(state: AppState) -> None:
    while True:
        clear_screen()
        raw_options = get_brand_options()
        menu_items: List[BrandOption] = []
        for opt_id, label, _, _, _ in raw_options:
            if opt_id == "0":
                menu_items.append((opt_id, t("generic_all")))
            else:
                menu_items.append((opt_id, label))
        print_menu(
            t("brand_header"),
            menu_items,
        )
        print(f"\n  {t('generic_note')}")
        choice = input(f"\n  {t('select_manufacturer')} (0-6): ").strip()
        if apply_brand_selection(state, choice):
            return
