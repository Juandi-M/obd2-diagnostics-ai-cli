from __future__ import annotations

from typing import Any, Dict

from app.application.state import AppState
from app.domain.ports import SettingsRepository


class SettingsService:
    def __init__(self, state: AppState, repo: SettingsRepository) -> None:
        self.state = state
        self.repo = repo

    def load(self) -> Dict[str, Any]:
        settings = self.repo.load()
        self._apply_settings(settings)
        return settings

    def save(self) -> Dict[str, Any]:
        settings = self._settings_from_state()
        self.repo.save(settings)
        return settings

    def _settings_from_state(self) -> Dict[str, Any]:
        return {
            "manufacturer": self.state.manufacturer,
            "log_format": self.state.log_format,
            "monitor_interval": self.state.monitor_interval,
            "verbose": self.state.verbose,
            "last_ble_address": self.state.last_ble_address,
            "ble_notice_shown": self.state.ble_notice_shown,
            "vehicle_group": self.state.vehicle_group,
            "brand_id": self.state.brand_id,
            "brand_label": self.state.brand_label,
            "vehicle_profiles_by_group": self.state.vehicle_profiles_by_group,
        }

    def _apply_settings(self, settings: Dict[str, Any]) -> None:
        manufacturer = settings.get("manufacturer")
        if isinstance(manufacturer, str):
            self.state.set_manufacturer(manufacturer)

        log_format = settings.get("log_format")
        if isinstance(log_format, str):
            self.state.log_format = log_format

        monitor_interval = settings.get("monitor_interval")
        if isinstance(monitor_interval, (int, float)):
            self.state.monitor_interval = float(monitor_interval)

        verbose = settings.get("verbose")
        if isinstance(verbose, bool):
            self.state.set_verbose(verbose)

        last_ble_address = settings.get("last_ble_address")
        if isinstance(last_ble_address, str) and last_ble_address.strip():
            self.state.last_ble_address = last_ble_address.strip()

        ble_notice_shown = settings.get("ble_notice_shown")
        if isinstance(ble_notice_shown, bool):
            self.state.ble_notice_shown = ble_notice_shown

        vehicle_group = settings.get("vehicle_group")
        if isinstance(vehicle_group, str) and vehicle_group:
            self.state.vehicle_group = vehicle_group

        brand_id = settings.get("brand_id")
        if isinstance(brand_id, str):
            self.state.brand_id = brand_id

        brand_label = settings.get("brand_label")
        if isinstance(brand_label, str):
            self.state.brand_label = brand_label

        vehicle_profiles_by_group = settings.get("vehicle_profiles_by_group")
        if isinstance(vehicle_profiles_by_group, dict):
            cleaned: Dict[str, Dict[str, Any]] = {}
            for key, val in vehicle_profiles_by_group.items():
                if isinstance(val, dict):
                    cleaned[str(key)] = val
            self.state.vehicle_profiles_by_group = cleaned
