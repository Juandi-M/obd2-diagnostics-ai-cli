from __future__ import annotations

import builtins
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List

from app.bootstrap import container as container_module
from app.presentation.cli.actions import ai_report as ai_report_actions
from app.presentation.cli.actions.connect import connect_vehicle
from app.presentation.cli.actions.full_scan import run_full_scan
from tests.fakes import build_fake_container


class InputPatcher:
    def __init__(self, responses: List[str]) -> None:
        self._responses = iter(responses)
        self._original = None

    def __enter__(self) -> None:
        self._original = builtins.input

        def _fake_input(prompt: str = "") -> str:
            try:
                return next(self._responses)
            except StopIteration as exc:
                raise AssertionError("Unexpected input prompt") from exc

        builtins.input = _fake_input

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._original is not None:
            builtins.input = self._original


class NoOpSpinner:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class CliSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_container = container_module._container
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="obd_cli_smoke_"))
        container_module._container = build_fake_container(self._tmp_dir)
        self._orig_spinner = ai_report_actions.Spinner
        ai_report_actions.Spinner = NoOpSpinner

    def tearDown(self) -> None:
        ai_report_actions.Spinner = self._orig_spinner
        container_module._container = self._old_container
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_cli_help_flag(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-m", "app_cli", "--help"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_cli_flow_smoke(self) -> None:
        state = container_module.get_container().state
        connected = connect_vehicle(state, auto=True, mode="usb")
        self.assertTrue(connected)

        run_full_scan(state)

        with InputPatcher(["", "Test", "Model", "2020", "Trim", ""]):
            ai_report_actions.run_ai_report(state)

        reports = container_module.get_container().reports.list_reports()
        self.assertTrue(reports)
        report_id = reports[0].report_id

        with InputPatcher([report_id]):
            ai_report_actions.export_report_pdf()

        pdfs = list(self._tmp_dir.glob("*.pdf"))
        self.assertTrue(pdfs)
