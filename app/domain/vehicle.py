from __future__ import annotations

from typing import List, Optional, Tuple

BrandOption = Tuple[str, str, str, str, Optional[str]]

BRAND_OPTIONS: Tuple[BrandOption, ...] = (
    ("0", "Generic (all makes)", "generic", "generic", None),
    ("1", "Land Rover", "landrover", "jlr", "Land Rover"),
    ("2", "Jaguar", "jaguar", "jlr", "Jaguar"),
    ("3", "Jeep", "chrysler", "chrysler", "Jeep"),
    ("4", "Dodge", "chrysler", "chrysler", "Dodge"),
    ("5", "Chrysler", "chrysler", "chrysler", "Chrysler"),
    ("6", "Ram", "chrysler", "chrysler", "Ram"),
)


def get_brand_options() -> List[BrandOption]:
    return list(BRAND_OPTIONS)
