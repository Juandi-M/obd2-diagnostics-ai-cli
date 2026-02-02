from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "vin_cache.json"


def _normalize_vin(vin: str) -> str:
    return vin.strip().upper()


def _load_cache() -> Dict[str, Any]:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def get_vin_cache(vin: str) -> Optional[Dict[str, Any]]:
    if not vin:
        return None
    cache = _load_cache()
    return cache.get(_normalize_vin(vin))


def set_vin_cache(vin: str, profile: Dict[str, Any]) -> None:
    if not vin:
        return
    cache = _load_cache()
    entry = dict(profile)
    entry.setdefault("cached_at", datetime.now(timezone.utc).isoformat())
    cache[_normalize_vin(vin)] = entry
    _save_cache(cache)
