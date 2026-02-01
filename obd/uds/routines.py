from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"

BRAND_FILES = {
    "jeep": "jeep_routines.json",
    "land_rover": "land_rover_routines.json",
}


def load_brand_routines(brand: str) -> List[Dict[str, Any]]:
    key = (brand or "").lower()
    filename = BRAND_FILES.get(key)
    if not filename:
        return []
    path = DATA_DIR / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def routine_map(brand: str) -> Dict[str, Dict[str, Any]]:
    entries = load_brand_routines(brand)
    return {entry["name"].lower(): entry for entry in entries if "name" in entry}


def find_routine(brand: str, name: str) -> Optional[Dict[str, Any]]:
    return routine_map(brand).get(name.lower())
