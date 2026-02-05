from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.infrastructure.persistence import settings_store


class InfraSettingsStoreTests(unittest.TestCase):
    def test_load_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory(prefix="settings_store_") as tmp_dir:
            path = Path(tmp_dir) / "settings.json"
            old_path = settings_store.SETTINGS_PATH
            settings_store.SETTINGS_PATH = path
            try:
                data = settings_store.load_settings()
                self.assertEqual(data, {})
            finally:
                settings_store.SETTINGS_PATH = old_path

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory(prefix="settings_store_") as tmp_dir:
            path = Path(tmp_dir) / "settings.json"
            old_path = settings_store.SETTINGS_PATH
            settings_store.SETTINGS_PATH = path
            try:
                payload = {"manufacturer": "generic", "log_format": "csv"}
                settings_store.save_settings(payload)
                data = settings_store.load_settings()
                self.assertEqual(data["manufacturer"], "generic")
            finally:
                settings_store.SETTINGS_PATH = old_path

    def test_invalid_json_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory(prefix="settings_store_") as tmp_dir:
            path = Path(tmp_dir) / "settings.json"
            path.write_text("{bad json", encoding="utf-8")
            old_path = settings_store.SETTINGS_PATH
            settings_store.SETTINGS_PATH = path
            try:
                data = settings_store.load_settings()
                self.assertEqual(data, {})
            finally:
                settings_store.SETTINGS_PATH = old_path
