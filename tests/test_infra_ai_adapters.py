from __future__ import annotations

import unittest
from unittest import mock

from app.domain.entities import ExternalServiceError
from app.infrastructure.ai import adapters as ai_adapters
from app.infrastructure.ai.openai_client import OpenAIError


class InfraAiAdaptersTests(unittest.TestCase):
    def test_ai_config_adapter_reads_env(self) -> None:
        with mock.patch("app.infrastructure.ai.adapters.get_api_key", return_value="key"):
            with mock.patch("app.infrastructure.ai.adapters.get_model", return_value="model-x"):
                adapter = ai_adapters.AiConfigAdapter()
                self.assertEqual(adapter.get_api_key(), "key")
                self.assertEqual(adapter.get_model(), "model-x")

    def test_ai_report_adapter_wraps_errors(self) -> None:
        adapter = ai_adapters.AiReportAdapter()
        with mock.patch(
            "app.infrastructure.ai.ai_report.decode_vin_with_ai",
            side_effect=OpenAIError("boom"),
        ):
            with self.assertRaises(ExternalServiceError):
                adapter.decode_vin("VIN", "generic")

        with mock.patch(
            "app.infrastructure.ai.ai_report.request_ai_report",
            side_effect=OpenAIError("boom"),
        ):
            with self.assertRaises(ExternalServiceError):
                adapter.request_report({"scan": {}}, "en")

    def test_vin_decoder_adapter(self) -> None:
        adapter = ai_adapters.VinDecoderAdapter()
        with mock.patch(
            "app.infrastructure.ai.adapters.decode_vin_with_vpic",
            return_value={"make": "Test"},
        ):
            result = adapter.decode_vpic("VIN")
            self.assertEqual(result.get("make"), "Test")
