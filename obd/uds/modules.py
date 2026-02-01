from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .paths import uds_data_dir

DATA_DIR = uds_data_dir()

BRAND_FILES = {
    "jeep": "jeep_modules.json",
    "land_rover": "land_rover_modules.json",
}

# STANDARD_MODULES are generic diagnostic IDs used by many ECUs.
# Brand files still require reverse engineering to confirm specific module mappings.
STANDARD_MODULES = [
    {
        "name": "generic_engine",
        "tx_id": "7E0",
        "rx_id": "7E8",
        "status": "standard",
    },
    {
        "name": "generic_transmission",
        "tx_id": "7E1",
        "rx_id": "7E9",
        "status": "standard",
    },
]


def load_brand_modules(brand: str) -> List[Dict[str, Any]]:
    key = (brand or "").lower()
    filename = BRAND_FILES.get(key)
    if not filename:
        return []
    path = DATA_DIR / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_standard_modules() -> List[Dict[str, Any]]:
    return list(STANDARD_MODULES)


def module_map(brand: str, include_standard: bool = True) -> Dict[str, Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if include_standard:
        entries.extend(load_standard_modules())
    entries.extend(load_brand_modules(brand))
    return {entry["name"].lower(): entry for entry in entries if "name" in entry}


def find_module(brand: str, name: str) -> Optional[Dict[str, Any]]:
    """Find module definition by logical name (e.g. 'generic_engine', 'bcm')."""
    return module_map(brand).get((name or "").lower())
