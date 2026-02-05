from __future__ import annotations

from typing import List, Tuple

from app.bootstrap import get_container
from app.presentation.cli.i18n import t
from app.presentation.cli.ui import clear_screen, print_menu


BrandOption = Tuple[str, str]


def select_brand() -> None:
    while True:
        clear_screen()
        raw_options = get_container().vehicles.get_brand_options()
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
        if get_container().vehicles.apply_brand_selection(choice):
            return


def save_profile_for_group() -> None:
    get_container().vehicles.save_profile_for_group()
