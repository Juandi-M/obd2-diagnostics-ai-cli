from __future__ import annotations

import unittest

from app.application.state import AppState
from app.application.use_cases.settings import SettingsService
from tests.app_fakes import DummySettingsRepo


class SettingsServiceTests(unittest.TestCase):
    def test_load_applies_settings(self) -> None:
        repo = DummySettingsRepo(
            {
                "manufacturer": "chrysler",
                "log_format": "json",
                "monitor_interval": 2.5,
                "verbose": True,
                "last_ble_address": "AA:BB",
                "ble_notice_shown": True,
                "vehicle_group": "chrysler",
                "brand_id": "3",
                "brand_label": "Jeep",
                "vehicle_profiles_by_group": {"chrysler": {"make": "Jeep"}},
            }
        )
        state = AppState()
        svc = SettingsService(state, repo)
        settings = svc.load()
        self.assertEqual(settings["manufacturer"], "chrysler")
        self.assertEqual(state.manufacturer, "chrysler")
        self.assertEqual(state.log_format, "json")
        self.assertEqual(state.monitor_interval, 2.5)
        self.assertTrue(state.verbose)
        self.assertEqual(state.last_ble_address, "AA:BB")
        self.assertTrue(state.ble_notice_shown)
        self.assertEqual(state.vehicle_group, "chrysler")
        self.assertEqual(state.brand_id, "3")
        self.assertEqual(state.brand_label, "Jeep")
        self.assertIn("chrysler", state.vehicle_profiles_by_group)

    def test_save_persists_state(self) -> None:
        repo = DummySettingsRepo()
        state = AppState()
        state.manufacturer = "landrover"
        state.log_format = "csv"
        state.monitor_interval = 1.5
        state.verbose = True
        state.last_ble_address = "CC:DD"
        state.ble_notice_shown = True
        state.vehicle_group = "jlr"
        state.brand_id = "1"
        state.brand_label = "Land Rover"
        state.vehicle_profiles_by_group = {"jlr": {"make": "Land Rover"}}
        svc = SettingsService(state, repo)
        settings = svc.save()
        self.assertEqual(settings["manufacturer"], "landrover")
        self.assertEqual(repo.saved["manufacturer"], "landrover")
