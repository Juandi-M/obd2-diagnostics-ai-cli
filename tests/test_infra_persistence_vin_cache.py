from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.infrastructure.persistence import vin_cache


class InfraVinCacheTests(unittest.TestCase):
    def test_set_and_get_vin_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vin_cache_") as tmp_dir:
            path = Path(tmp_dir) / "vin_cache.json"
            old_path = vin_cache.CACHE_PATH
            vin_cache.CACHE_PATH = path
            try:
                vin_cache.set_vin_cache(" vin123 ", {"make": "Jeep"})
                data = vin_cache.get_vin_cache("VIN123")
                self.assertEqual(data.get("make"), "Jeep")
            finally:
                vin_cache.CACHE_PATH = old_path

    def test_empty_vin_returns_none(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vin_cache_") as tmp_dir:
            path = Path(tmp_dir) / "vin_cache.json"
            old_path = vin_cache.CACHE_PATH
            vin_cache.CACHE_PATH = path
            try:
                vin_cache.set_vin_cache("", {"make": "Jeep"})
                data = vin_cache.get_vin_cache("")
                self.assertIsNone(data)
            finally:
                vin_cache.CACHE_PATH = old_path
