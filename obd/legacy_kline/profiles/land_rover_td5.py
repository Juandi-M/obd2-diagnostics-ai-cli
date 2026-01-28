from __future__ import annotations

from typing import List

from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.profiles.iso9141_2 import ISO9141_2
from obd.legacy_kline.profiles.kwp2000_5baud import KWP2000_5BAUD
from obd.legacy_kline.profiles.kwp2000_fast import KWP2000_FAST


def td5_candidates() -> List[KLineProfile]:
    """
    Land Rover TD5 (y vehículos similares) pueden caer en:
    - ISO9141-2 (ATSP3)
    - KWP2000 5-baud (ATSP4)
    - KWP2000 fast (ATSP5)

    En vez de casarnos con uno, probamos.
    """
    return [
        KWP2000_5BAUD,
        KWP2000_FAST,
        ISO9141_2,
    ]
