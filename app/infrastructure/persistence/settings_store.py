from __future__ import annotations

import json
from typing import Any, Dict

from app.domain.ports import SettingsRepository
from .data_paths import settings_path


SETTINGS_PATH = settings_path()


def load_settings() -> Dict[str, Any]:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_settings(settings: Dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class SettingsRepositoryImpl(SettingsRepository):
    def load(self) -> Dict[str, Any]:
        return load_settings()

    def save(self, settings: Dict[str, Any]) -> None:
        save_settings(settings)
