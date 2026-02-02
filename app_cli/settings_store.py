from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app_cli.state import AppState


SETTINGS_PATH = Path(__file__).resolve().parents[1] / "data" / "cli_settings.json"


def load_settings() -> Dict[str, Any]:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_settings(settings: Dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def settings_from_state(state: AppState) -> Dict[str, Any]:
    return {
        "manufacturer": state.manufacturer,
        "log_format": state.log_format,
        "monitor_interval": state.monitor_interval,
        "verbose": state.verbose,
        "last_ble_address": state.last_ble_address,
        "ble_notice_shown": state.ble_notice_shown,
        "vehicle_group": state.vehicle_group,
        "brand_id": state.brand_id,
        "brand_label": state.brand_label,
        "vehicle_profiles_by_group": state.vehicle_profiles_by_group,
    }


def apply_settings(state: AppState, settings: Dict[str, Any]) -> None:
    manufacturer = settings.get("manufacturer")
    if isinstance(manufacturer, str):
        state.set_manufacturer(manufacturer)

    log_format = settings.get("log_format")
    if isinstance(log_format, str):
        state.log_format = log_format

    monitor_interval = settings.get("monitor_interval")
    if isinstance(monitor_interval, (int, float)):
        state.monitor_interval = float(monitor_interval)

    verbose = settings.get("verbose")
    if isinstance(verbose, bool):
        state.set_verbose(verbose)

    last_ble_address = settings.get("last_ble_address")
    if isinstance(last_ble_address, str) and last_ble_address.strip():
        state.last_ble_address = last_ble_address.strip()

    ble_notice_shown = settings.get("ble_notice_shown")
    if isinstance(ble_notice_shown, bool):
        state.ble_notice_shown = ble_notice_shown

    vehicle_group = settings.get("vehicle_group")
    if isinstance(vehicle_group, str) and vehicle_group:
        state.vehicle_group = vehicle_group

    brand_id = settings.get("brand_id")
    if isinstance(brand_id, str):
        state.brand_id = brand_id

    brand_label = settings.get("brand_label")
    if isinstance(brand_label, str):
        state.brand_label = brand_label

    vehicle_profiles_by_group = settings.get("vehicle_profiles_by_group")
    if isinstance(vehicle_profiles_by_group, dict):
        cleaned: Dict[str, Dict[str, Any]] = {}
        for key, val in vehicle_profiles_by_group.items():
            if isinstance(val, dict):
                cleaned[str(key)] = val
        state.vehicle_profiles_by_group = cleaned
