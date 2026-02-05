from __future__ import annotations

from typing import Dict, Optional

from app.application.state import AppState
from app.domain.vehicle import BRAND_OPTIONS, BrandOption, get_brand_options


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
