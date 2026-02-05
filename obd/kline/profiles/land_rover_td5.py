from __future__ import annotations

from typing import List

from obd.kline.profiles.base import KLineProfile
from obd.kline.profiles.iso9141_2 import ISO9141_2
from obd.kline.profiles.kwp2000_5baud import KWP2000_5BAUD
from obd.kline.profiles.kwp2000_fast import KWP2000_FAST
from obd.kline.runtime.quirks import (
    QUIRK_RETRY_ON_NO_DATA,
    QUIRK_EXTRA_INTER_COMMAND_DELAY,
)


def _clone_with(profile: KLineProfile, *, name_suffix: str, verify_obd: List[str], quirks_extra: dict) -> KLineProfile:
    """
    Como KLineProfile es frozen, hacemos “clone” limpio con overrides.
    """
    return KLineProfile(
        name=f"{profile.name} {name_suffix}",
        family=profile.family,
        init_at=list(profile.init_at),
        options_at=list(profile.options_at),
        verify_obd=verify_obd,
        request_timeout_s=profile.request_timeout_s,
        inter_command_delay_s=profile.inter_command_delay_s,
        quirks={**profile.quirks, **quirks_extra},
        notes=profile.notes,
    )


def td5_candidates() -> List[KLineProfile]:
    """
    TD5 (y otros Land Rover de esa era) pueden responder por ISO9141 o KWP.
    El orden acá es intencional: muchos TD5 terminan en KWP (pero no apostamos a ciegas).
    """
    # Probes recomendados para “vida real”
    # 010C/0105 suelen confirmar si hay comunicación, más que 0100 solo.
    td5_probes = ["0100", "010C", "0105", "0902"]

    # Algunos ECUs TD5 pueden dar NO DATA intermitente al principio → retry
    td5_quirks = {
        QUIRK_RETRY_ON_NO_DATA: True,
        QUIRK_EXTRA_INTER_COMMAND_DELAY: True,
    }

    return [
        _clone_with(KWP2000_5BAUD, name_suffix="[TD5]", verify_obd=td5_probes, quirks_extra=td5_quirks),
        _clone_with(KWP2000_FAST, name_suffix="[TD5]", verify_obd=td5_probes, quirks_extra=td5_quirks),
        _clone_with(ISO9141_2, name_suffix="[TD5]", verify_obd=td5_probes, quirks_extra=td5_quirks),
    ]
