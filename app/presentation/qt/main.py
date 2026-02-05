"""Backward-compatible entrypoint for the Qt GUI.

This repo originally implemented the entire Qt UI inside this module.
It has been refactored into feature modules under `app.presentation.qt.features`
plus a small app runner in `app.presentation.qt.app`.

Keep `run()` here because `python3 -m app_gui` imports it.
"""

from __future__ import annotations

from app.presentation.qt.app import main, run

# Legacy re-export used by tests (and potentially external imports).
from app.presentation.qt.features.live_data.live_data_page import LiveDataPage

__all__ = ["LiveDataPage", "main", "run"]
