from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"

BRAND_FILES = {
    "jeep": "jeep_dids.json",
    "land_rover": "land_rover_dids.json",
}


def load_brand_dids(brand: str) -> List[Dict[str, Any]]:
    key = (brand or "").lower()
    filename = BRAND_FILES.get(key)
    if not filename:
        return []
    path = DATA_DIR / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def did_map(brand: str) -> Dict[str, Dict[str, Any]]:
    entries = load_brand_dids(brand)
    return {entry["did"].upper(): entry for entry in entries if "did" in entry}


def find_did(brand: str, did: str) -> Optional[Dict[str, Any]]:
    return did_map(brand).get(did.upper())


def find_did_by_name(brand: str, name: str) -> Optional[Dict[str, Any]]:
    target = (name or "").strip().lower()
    for entry in load_brand_dids(brand):
        if (entry.get("name") or "").strip().lower() == target:
            return entry
    return None
