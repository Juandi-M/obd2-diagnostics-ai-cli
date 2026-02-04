from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from app.infrastructure.reporting.pdf_renderer import PdfReportRenderer


class InfraPdfRendererTests(unittest.TestCase):
    def test_render_delegates(self) -> None:
        renderer = PdfReportRenderer()
        payload = {"report_id": "R1"}
        with mock.patch("app.infrastructure.reporting.pdf_renderer.render_report_pdf") as render_pdf:
            renderer.render(payload, "out.pdf", report_text="OK", language="en")
            args, kwargs = render_pdf.call_args
            self.assertIsInstance(args[1], Path)
