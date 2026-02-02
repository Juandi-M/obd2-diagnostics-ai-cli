from __future__ import annotations

from typing import Dict, Optional, Tuple, List

from app_core.state import AppState


BrandOption = Tuple[str, str, str, str, Optional[str]]

BRAND_OPTIONS: Tuple[BrandOption, ...] = (
    ("0", "Generic (all makes)", "generic", "generic", None),
    ("1", "Land Rover", "landrover", "jlr", "Land Rover"),
    ("2", "Jaguar", "jaguar", "jlr", "Jaguar"),
    ("3", "Jeep", "chrysler", "chrysler", "Jeep"),
    ("4", "Dodge", "chrysler", "chrysler", "Dodge"),
    ("5", "Chrysler", "chrysler", "chrysler", "Chrysler"),
    ("6", "Ram", "chrysler", "chrysler", "Ram"),
)


def get_brand_options() -> List[BrandOption]:
    return list(BRAND_OPTIONS)


def apply_brand_selection(state: AppState, brand_id: str) -> bool:
    for opt in BRAND_OPTIONS:
        opt_id, label, manufacturer, group, make = opt
        if opt_id != brand_id:
            continue
        _apply_brand_selection(state, opt_id, label, manufacturer, group, make)
        return True
    return False


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
