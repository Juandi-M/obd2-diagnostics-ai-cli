from __future__ import annotations

from obd.kline.profiles.base import KLineProfile
from obd.kline.runtime.quirks import (
    QUIRK_RETRY_ON_NO_DATA,
    QUIRK_EXTRA_INTER_COMMAND_DELAY,
)

KWP2000_FAST = KLineProfile(
    name="KWP2000 fast init (ATSP5)",
    family="kwp2000_fast",
    init_at=[
        "AT SP 5",
        "AT E0",
        "AT L0",
        "AT S0",
        "AT H1",
    ],
    verify_obd=[
        "0100",
        "010C",
        "0105",
        "0902",
    ],
    request_timeout_s=4.5,
    inter_command_delay_s=0.09,
    quirks={
        QUIRK_RETRY_ON_NO_DATA: True,
        QUIRK_EXTRA_INTER_COMMAND_DELAY: True,
    },
    notes="KWP fast init puede ser más rápido que 5-baud, pero igual requiere delay para no 'spamear' al ECU.",
)
