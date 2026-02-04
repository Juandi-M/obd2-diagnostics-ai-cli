from __future__ import annotations

import unittest

from app.application.state import AppState
from app.application.vehicle import apply_brand_selection, save_profile_for_group
from app.domain.vehicle import get_brand_options


class VehicleTests(unittest.TestCase):
    def test_get_brand_options(self) -> None:
        options = get_brand_options()
        self.assertTrue(options)
        self.assertEqual(options[0][0], "0")

    def test_apply_brand_selection_valid(self) -> None:
        state = AppState()
        ok = apply_brand_selection(state, "3")
        self.assertTrue(ok)
        self.assertEqual(state.manufacturer, "chrysler")
        self.assertEqual(state.vehicle_group, "chrysler")
        self.assertEqual(state.brand_id, "3")
        self.assertEqual(state.brand_label, "Jeep")

    def test_apply_brand_selection_invalid(self) -> None:
        state = AppState()
        state.manufacturer = "generic"
        ok = apply_brand_selection(state, "99")
        self.assertFalse(ok)
        self.assertEqual(state.manufacturer, "generic")

    def test_save_profile_for_group(self) -> None:
        state = AppState()
        state.vehicle_group = "chrysler"
        state.vehicle_profile = {"make": "Jeep", "model": "Wrangler"}
        save_profile_for_group(state)
        self.assertIn("chrysler", state.vehicle_profiles_by_group)
