from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """
    Locate repository root (packaging-safe-ish):
    Walk up until we find a 'data' folder.
    """
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "data").exists():
            return parent
    # Fallback to 3 levels up (app/infrastructure/persistence)
    return current.parents[3]


def data_dir() -> Path:
    return project_root() / "data"


def logs_dir() -> Path:
    return project_root() / "logs"


def raw_log_path() -> Path:
    return logs_dir() / "obd_raw.log"


def reports_dir() -> Path:
    return data_dir() / "reports"


def ensure_runtime_dirs() -> None:
    logs_dir().mkdir(parents=True, exist_ok=True)
    reports_dir().mkdir(parents=True, exist_ok=True)


def i18n_dir() -> Path:
    return data_dir() / "i18n"


def vin_cache_path() -> Path:
    return data_dir() / "vin_cache.json"


def settings_path() -> Path:
    return data_dir() / "cli_settings.json"
