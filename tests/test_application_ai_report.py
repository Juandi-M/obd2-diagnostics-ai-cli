from __future__ import annotations

import unittest

from app.application.state import AppState
from app.application.use_cases.ai_report import (
    AiReportService,
    build_report_input,
    detect_report_language,
    extract_report_parts,
    prepare_vehicle_profile,
    update_report_status,
)
from tests.app_fakes import DummyAiPort, DummyReportRepo, DummyVinCache, DummyVinDecoder


class DummyPdfRenderer:
    def __init__(self) -> None:
        self.calls = []

    def render(self, payload, output_path, *, report_json=None, report_text=None, language=None):
        self.calls.append((payload, output_path, report_json, report_text, language))


class AiReportTests(unittest.TestCase):
    def test_detect_report_language(self) -> None:
        self.assertEqual(detect_report_language("falla de la bomba", "en"), "es")
        self.assertEqual(detect_report_language("Engine misfire", "en"), "en")

    def test_build_report_input_cli(self) -> None:
        state = AppState()
        scan_payload = {"vehicle_info": {"vin": "VIN"}, "dtcs": []}
        payload = build_report_input(scan_payload, "note", state, "en")
        self.assertIn("vehicle", payload)
        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["manufacturer"], state.manufacturer)

    def test_extract_report_parts(self) -> None:
        report_json, report_text = extract_report_parts("<json>{\"language\":\"en\"}</json><report>OK</report>")
        self.assertEqual(report_json.get("language"), "en")
        self.assertEqual(report_text, "OK")

    def test_prepare_vehicle_profile_uses_cache(self) -> None:
        state = AppState()
        vin_cache = DummyVinCache()
        vin_cache.set("VIN123", {"make": "Jeep", "model": "Wrangler"})
        scan_payload = {"vehicle_info": {"vin": "VIN123", "protocol": "CAN"}}
        payload, profiles = prepare_vehicle_profile(
            scan_payload,
            state,
            vin_cache=vin_cache,
            ai_port=DummyAiPort(),
            vpic_port=DummyVinDecoder(),
        )
        self.assertEqual(payload["make"], "Jeep")
        self.assertIsInstance(profiles, dict)

    def test_update_report_status(self) -> None:
        repo = DummyReportRepo()
        report_id = repo.save_report({"status": "pending"})
        update_report_status(repo, report_id, status="complete", response="done")
        payload = repo.load_report(report_id)
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["ai_response"], "done")

    def test_generate_report_service(self) -> None:
        state = AppState()
        scan_payload = {
            "vehicle_info": {"vin": "VIN123", "protocol": "CAN"},
            "dtcs": [],
            "readiness": {},
            "live_data": {},
        }
        repo = DummyReportRepo()
        vin_cache = DummyVinCache()
        ai_port = DummyAiPort()
        vpic = DummyVinDecoder()
        pdf = DummyPdfRenderer()
        service = AiReportService(ai_port, vpic, vin_cache, repo, pdf)
        result = service.generate_report(scan_payload, "note", state, "en", use_vin_decode=False)
        self.assertTrue(result.report_path)
        payload = repo.load_report(result.report_path)
        self.assertEqual(payload["status"], "complete")

    def test_export_pdf(self) -> None:
        repo = DummyReportRepo()
        pdf = DummyPdfRenderer()
        service = AiReportService(DummyAiPort(), DummyVinDecoder(), DummyVinCache(), repo, pdf)
        service.export_pdf({"report_id": "R1"}, "out.pdf", report_text="OK", language="en")
        self.assertTrue(pdf.calls)
