from __future__ import annotations

from typing import Dict

from app.application.state import AppState
from app.domain.ports import I18nRepository


class I18nService:
    def __init__(self, state: AppState, repo: I18nRepository) -> None:
        self.state = state
        self.repo = repo
        self._languages: Dict[str, Dict[str, str]] = {}
        self._names: Dict[str, str] = {}
        self._loaded = False

    def _load_languages(self) -> None:
        self._languages.clear()
        self._names.clear()
        payloads = self.repo.load_all()
        for code, payload in payloads.items():
            if not isinstance(payload, dict):
                continue
            name = payload.get("name", code)
            strings = payload.get("strings", {})
            if isinstance(strings, dict):
                self._languages[code] = {str(k): str(v) for k, v in strings.items()}
                self._names[code] = str(name)
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load_languages()

    def set_language(self, code: str) -> bool:
        self._ensure_loaded()
        if code in self._languages:
            self.state.language = code
            return True
        return False

    def get_language(self) -> str:
        return self.state.language or "en"

    def get_language_name(self, code: str) -> str:
        self._ensure_loaded()
        return self._names.get(code, code)

    def get_available_languages(self) -> Dict[str, str]:
        self._ensure_loaded()
        return dict(self._names)

    def t(self, key: str, **kwargs: str) -> str:
        self._ensure_loaded()
        lang = self.get_language()
        lang_table = self._languages.get(lang, self._languages.get("en", {}))
        fallback = self._languages.get("en", {})
        text = lang_table.get(key) or fallback.get(key) or key
        if kwargs:
            return text.format(**kwargs)
        return text
