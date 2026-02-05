from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.infrastructure.reporting import pdf_paths


class InfraPdfPathsTests(unittest.TestCase):
    def test_report_pdf_path_uses_reports_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pdf_paths_") as tmp_dir:
            base = Path(tmp_dir)
            with mock.patch("app.infrastructure.reporting.pdf_paths.ensure_reports_dir", return_value=base):
                with mock.patch("app.infrastructure.reporting.pdf_paths.reports_dir", return_value=base):
                    path = pdf_paths.report_pdf_path("R1")
            self.assertTrue(str(path).startswith(str(base)))
            self.assertIn("R1", str(path))
