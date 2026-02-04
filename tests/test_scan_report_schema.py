from __future__ import annotations

import unittest

from app.application.scan_report import collect_scan_report
from tests.fakes import FakeScanner


class ScanReportSchemaTests(unittest.TestCase):
    def test_scan_report_schema(self) -> None:
        report = collect_scan_report(FakeScanner())
        self.assertIsInstance(report, dict)
        self.assertTrue({"vehicle_info", "dtcs", "readiness", "live_data"}.issubset(report.keys()))

        vehicle_info = report.get("vehicle_info")
        self.assertIsInstance(vehicle_info, dict)

        dtcs = report.get("dtcs")
        self.assertIsInstance(dtcs, list)
        for item in dtcs:
            self.assertIsInstance(item, dict)
            self.assertIn("code", item)
            self.assertIn("status", item)
            self.assertIn("description", item)
            self.assertIsInstance(item["code"], str)
            self.assertIsInstance(item["status"], str)
            self.assertIsInstance(item["description"], str)

        readiness = report.get("readiness")
        self.assertIsInstance(readiness, dict)
        for name, status in readiness.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(status, dict)
            self.assertIn("available", status)
            self.assertIn("complete", status)
            self.assertIn("status", status)
            self.assertIsInstance(status["available"], bool)
            self.assertIsInstance(status["complete"], bool)
            self.assertIsInstance(status["status"], str)

        live_data = report.get("live_data")
        self.assertIsInstance(live_data, dict)
        for pid, reading in live_data.items():
            self.assertIsInstance(pid, str)
            self.assertIsInstance(reading, dict)
            self.assertIn("name", reading)
            self.assertIn("value", reading)
            self.assertIn("unit", reading)
            self.assertIsInstance(reading["name"], str)
            self.assertIsInstance(reading["unit"], str)
