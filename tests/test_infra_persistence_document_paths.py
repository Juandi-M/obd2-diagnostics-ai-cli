from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.infrastructure.persistence.document_paths import DocumentPathAdapter


class InfraDocumentPathsTests(unittest.TestCase):
    def test_ai_report_pdf_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docs_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            adapter = DocumentPathAdapter()
            vehicle = {"make": "Land Rover", "model": "Defender 90"}
            with mock.patch("app.infrastructure.persistence.document_paths.Path.home", return_value=tmp_path):
                path = adapter.ai_report_pdf_path(vehicle)
            self.assertTrue(path.endswith(".pdf"))
            self.assertIn("Documents", path)
