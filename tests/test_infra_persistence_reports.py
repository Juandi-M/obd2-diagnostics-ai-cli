from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.infrastructure.persistence import reports


class InfraReportsTests(unittest.TestCase):
    def test_save_and_list_reports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="reports_") as tmp_dir:
            base = Path(tmp_dir)
            old_data = reports.DATA_DIR
            old_log = reports.LOG_DIR
            old_full = reports.FULL_SCAN_DIR
            reports.DATA_DIR = base / "reports"
            reports.LOG_DIR = base / "logs"
            reports.FULL_SCAN_DIR = reports.LOG_DIR / ".full_scan_reports"
            try:
                path = reports.save_report({"status": "pending"})
                self.assertTrue(Path(path).exists())
                items = reports.list_reports()
                self.assertTrue(items)
                found = reports.find_report_by_id(items[0].report_id)
                self.assertIsNotNone(found)
            finally:
                reports.DATA_DIR = old_data
                reports.LOG_DIR = old_log
                reports.FULL_SCAN_DIR = old_full

    def test_full_scan_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="reports_") as tmp_dir:
            base = Path(tmp_dir)
            old_data = reports.DATA_DIR
            old_log = reports.LOG_DIR
            old_full = reports.FULL_SCAN_DIR
            reports.DATA_DIR = base / "reports"
            reports.LOG_DIR = base / "logs"
            reports.FULL_SCAN_DIR = reports.LOG_DIR / ".full_scan_reports"
            try:
                path = reports.save_full_scan_txt(["line1", "line2"])
                content = reports.load_full_scan_report(path)
                self.assertIn("line1", content)
                items = reports.list_full_scan_reports()
                self.assertTrue(items)
            finally:
                reports.DATA_DIR = old_data
                reports.LOG_DIR = old_log
                reports.FULL_SCAN_DIR = old_full
