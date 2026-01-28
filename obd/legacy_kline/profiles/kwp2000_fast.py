from __future__ import annotations

from obd.legacy_kline.profiles.base import KLineProfile


KWP2000_FAST = KLineProfile(
    name="KWP2000 fast init (ATSP5)",
    family="kwp2000_fast",
    init_at=[
        "AT SP 5",
        "AT H1",
        "AT L0",
        "AT S0",
        "AT E0",
    ],
    verify_obd=["0100", "0902"],
    request_timeout_s=4.0,
    inter_command_delay_s=0.08,
)
