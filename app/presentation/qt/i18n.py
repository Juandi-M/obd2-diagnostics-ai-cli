from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

from app.application.state import AppState


_I18N_DIR = Path(__file__).with_name("resources") / "i18n"


@lru_cache(maxsize=2)
def _load_lang(lang: str) -> Dict[str, str]:
    path = _I18N_DIR / f"{lang}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def gui_t(state: AppState, key: str) -> str:
    lang = "es" if str(state.language).lower().startswith("es") else "en"
    table = _load_lang(lang)
    fallback = _load_lang("en")
    return table.get(key) or fallback.get(key) or key

