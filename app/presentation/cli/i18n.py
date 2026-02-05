from __future__ import annotations

from typing import Dict

from app.bootstrap import get_container


def set_language(code: str) -> bool:
    return get_container().i18n.set_language(code)


def get_language() -> str:
    return get_container().i18n.get_language()


def get_language_name(code: str) -> str:
    return get_container().i18n.get_language_name(code)


def get_available_languages() -> Dict[str, str]:
    return get_container().i18n.get_available_languages()


def t(key: str, **kwargs: str) -> str:
    return get_container().i18n.t(key, **kwargs)
