from __future__ import annotations

import unittest

from app.application.state import AppState
from app.application.use_cases.i18n import I18nService
from app.domain.ports import I18nRepository


class FakeI18nRepo(I18nRepository):
    def load_all(self):
        return {
            "en": {
                "name": "English",
                "strings": {"hello": "Hello {name}", "fallback": "Fallback"},
            },
            "es": {
                "name": "Espanol",
                "strings": {"hello": "Hola {name}"},
            },
        }


class I18nTests(unittest.TestCase):
    def test_language_selection_and_translation(self) -> None:
        state = AppState()
        svc = I18nService(state, FakeI18nRepo())
        self.assertTrue(svc.set_language("es"))
        self.assertEqual(state.language, "es")
        self.assertEqual(svc.t("hello", name="Ana"), "Hola Ana")

    def test_fallback_to_en(self) -> None:
        state = AppState()
        svc = I18nService(state, FakeI18nRepo())
        svc.set_language("es")
        self.assertEqual(svc.t("fallback"), "Fallback")
        self.assertEqual(svc.t("missing_key"), "missing_key")
