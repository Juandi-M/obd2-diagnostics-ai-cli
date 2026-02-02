from __future__ import annotations

from typing import Dict, Optional, Tuple

from app_cli.i18n import t
from app_cli.state import AppState
from app_cli.ui import clear_screen, print_menu


BrandOption = Tuple[str, str, str, str, Optional[str]]

BRAND_OPTIONS: Tuple[BrandOption, ...] = (
    ("0", t("generic_all"), "generic", "generic", None),
    ("1", "Land Rover", "landrover", "jlr", "Land Rover"),
    ("2", "Jaguar", "jaguar", "jlr", "Jaguar"),
    ("3", "Jeep", "chrysler", "chrysler", "Jeep"),
    ("4", "Dodge", "chrysler", "chrysler", "Dodge"),
    ("5", "Chrysler", "chrysler", "chrysler", "Chrysler"),
    ("6", "Ram", "chrysler", "chrysler", "Ram"),
)


def select_brand(state: AppState) -> None:
    while True:
        clear_screen()
        print_menu(
            t("brand_header"),
            [(opt[0], opt[1]) for opt in BRAND_OPTIONS],
        )
        print(f"\n  {t('generic_note')}")
        choice = input(f"\n  {t('select_manufacturer')} (0-6): ").strip()
        for brand_id, label, manufacturer, group, make in BRAND_OPTIONS:
            if choice != brand_id:
                continue
            _apply_brand_selection(state, brand_id, label, manufacturer, group, make)
            return


def _apply_brand_selection(
    state: AppState,
    brand_id: str,
    label: str,
    manufacturer: str,
    group: str,
    make: Optional[str],
) -> None:
    state.set_manufacturer(manufacturer)
    state.vehicle_group = group
    state.brand_id = brand_id
    state.brand_label = label

    if group == "generic":
        state.vehicle_profile = {}
        return

    profile = state.vehicle_profiles_by_group.get(group, {}) or {}
    state.vehicle_profile = dict(profile)
    if make and not state.vehicle_profile.get("make"):
        state.vehicle_profile["make"] = make


def save_profile_for_group(state: AppState) -> None:
    if state.vehicle_group == "generic":
        return
    if not state.vehicle_profile:
        return
    state.vehicle_profiles_by_group[state.vehicle_group] = dict(state.vehicle_profile)
