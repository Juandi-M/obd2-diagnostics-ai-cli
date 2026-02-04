from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.infrastructure.i18n.repository import I18nRepositoryImpl


class InfraI18nRepositoryTests(unittest.TestCase):
    def test_load_all(self) -> None:
        with tempfile.TemporaryDirectory(prefix="i18n_") as tmp_dir:
            base = Path(tmp_dir)
            (base / "en.json").write_text(json.dumps({"name": "English", "strings": {"hello": "Hello"}}))
            (base / "es.json").write_text(json.dumps({"name": "Espanol", "strings": {"hello": "Hola"}}))
            with mock.patch("app.infrastructure.i18n.repository.i18n_dir", return_value=base):
                repo = I18nRepositoryImpl()
                payload = repo.load_all()
            self.assertIn("en", payload)
            self.assertIn("es", payload)
