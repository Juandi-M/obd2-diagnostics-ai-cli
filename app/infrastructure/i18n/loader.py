from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from app.infrastructure.persistence.data_paths import i18n_dir


def load_language(lang: str) -> Dict[str, str]:
    base = i18n_dir()
    path = base / f"{lang}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_i18n(preferred: str, fallback: str = "en") -> Dict[str, str]:
    payload = load_language(preferred)
    if payload:
        return payload
    return load_language(fallback)
