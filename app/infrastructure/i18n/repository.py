from __future__ import annotations

from typing import Any, Dict

from app.domain.ports import I18nRepository
from app.infrastructure.i18n.loader import load_i18n
from app.infrastructure.persistence.data_paths import i18n_dir


class I18nRepositoryImpl(I18nRepository):
    def load_all(self) -> Dict[str, Dict[str, Any]]:
        base = i18n_dir()
        if not base.exists():
            return {}
        payloads: Dict[str, Dict[str, Any]] = {}
        for path in sorted(base.glob("*.json")):
            code = path.stem
            payloads[code] = load_i18n(code)
        return payloads
