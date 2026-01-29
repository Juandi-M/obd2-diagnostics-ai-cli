from __future__ import annotations

from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.runtime.quirks import (
    QUIRK_RETRY_ON_NO_DATA,
    QUIRK_EXTRA_INTER_COMMAND_DELAY,
)

KWP2000_5BAUD = KLineProfile(
    name="KWP2000 5-baud init (ATSP4)",
    family="kwp2000_5baud",
    init_at=[
        "AT SP 4",
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
    # 5-baud init puede tardar más
    request_timeout_s=4.5,
    inter_command_delay_s=0.10,
    quirks={
        QUIRK_RETRY_ON_NO_DATA: True,
        QUIRK_EXTRA_INTER_COMMAND_DELAY: True,
    },
    notes="KWP 5-baud init suele necesitar más paciencia; timeouts/delays más altos.",
)
