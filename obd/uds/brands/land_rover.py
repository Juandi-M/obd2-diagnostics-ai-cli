from __future__ import annotations

from ..dids import load_brand_dids
from ..routines import load_brand_routines

BRAND = "land_rover"


def dids():
    return load_brand_dids(BRAND)


def routines():
    return load_brand_routines(BRAND)
