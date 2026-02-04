from __future__ import annotations

from typing import Any, List, Tuple

from PySide6.QtCore import QObject

from app.application.state import AppState
from app.application.use_cases.settings import SettingsService
from app.application.use_cases.vehicle import VehicleService


class SettingsViewModel(QObject):
    def __init__(self, state: AppState, settings: SettingsService, vehicles: VehicleService) -> None:
        super().__init__()
        self.state = state
        self.settings = settings
        self.vehicles = vehicles

    def save(self) -> Any:
        return self.settings.save()

    def load(self) -> Any:
        return self.settings.load()

    def get_brand_options(self):
        return self.vehicles.get_brand_options()

    def apply_brand_selection(self, brand_id: str) -> bool:
        return self.vehicles.apply_brand_selection(brand_id)

    def save_profile_for_group(self) -> None:
        self.vehicles.save_profile_for_group()
