from __future__ import annotations


def normalize_brand(brand: str) -> str:
    cleaned = (brand or "").strip().lower().replace(" ", "_")
    if cleaned in {"landrover", "land_rover", "land-rover"}:
        return "land_rover"
    if cleaned in {"jeep", "chrysler", "dodge", "ram"}:
        return "jeep"
    return cleaned
