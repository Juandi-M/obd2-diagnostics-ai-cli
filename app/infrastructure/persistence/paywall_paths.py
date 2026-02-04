from __future__ import annotations

from pathlib import Path


def paywall_config_dir() -> Path:
    return Path.home() / ".obdapp"


def paywall_config_path() -> Path:
    return paywall_config_dir() / "config.json"
