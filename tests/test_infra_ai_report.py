from __future__ import annotations

import json
import unittest
from unittest import mock

from app.infrastructure.ai.ai_report import decode_vin_with_ai, decode_vin_with_vpic, request_ai_report


class InfraAiReportTests(unittest.TestCase):
    def test_decode_vin_with_ai_parses_json(self) -> None:
        response = {
            "choices": [{"message": {"content": "{\"make\":\"Test\",\"model\":\"X\"}"}}],
        }
        with mock.patch("app.infrastructure.ai.ai_report.chat_completion", return_value=response):
            data = decode_vin_with_ai("VIN", "generic")
            self.assertEqual(data.get("make"), "Test")

    def test_decode_vin_with_vpic_parses(self) -> None:
        payload = {
            "Results": [
                {
                    "Make": "Jeep",
                    "Model": "Wrangler",
                    "ModelYear": "2020",
                    "Trim": "Sport",
                    "EngineModel": "V6",
                }
            ]
        }
        body = json.dumps(payload).encode("utf-8")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def read(self):
                return body

        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()):
            data = decode_vin_with_vpic("VIN123")
            self.assertEqual(data.get("make"), "Jeep")
            self.assertEqual(data.get("model"), "Wrangler")

    def test_request_ai_report_requires_choices(self) -> None:
        with mock.patch("app.infrastructure.ai.ai_report.chat_completion", return_value={"choices": []}):
            with self.assertRaises(Exception):
                request_ai_report({"scan": {}}, "en")

    def test_request_ai_report_returns_content(self) -> None:
        response = {"choices": [{"message": {"content": "OK"}}]}
        with mock.patch("app.infrastructure.ai.ai_report.chat_completion", return_value=response):
            result = request_ai_report({"scan": {}}, "en")
            self.assertEqual(result, "OK")
