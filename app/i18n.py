from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "i18n"

LANGUAGES: Dict[str, Dict[str, str]] = {}
LANGUAGE_NAMES: Dict[str, str] = {}
_current_language = "en"


def _load_languages() -> None:
    LANGUAGES.clear()
    LANGUAGE_NAMES.clear()
    if not DATA_DIR.exists():
        return
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        code = path.stem
        name = payload.get("name", code)
        strings = payload.get("strings", {})
        if isinstance(strings, dict):
            LANGUAGES[code] = {str(k): str(v) for k, v in strings.items()}
            LANGUAGE_NAMES[code] = str(name)


_load_languages()


def set_language(code: str) -> bool:
    global _current_language
    if code in LANGUAGES:
        _current_language = code
        return True
    return False


def get_language() -> str:
    return _current_language


def get_language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def get_available_languages() -> Dict[str, str]:
    return dict(LANGUAGE_NAMES)


def t(key: str, **kwargs: str) -> str:
    lang_table = LANGUAGES.get(_current_language, LANGUAGES.get("en", {}))
    fallback = LANGUAGES.get("en", {})
    text = lang_table.get(key) or fallback.get(key) or key
    if kwargs:
        return text.format(**kwargs)
    return text
