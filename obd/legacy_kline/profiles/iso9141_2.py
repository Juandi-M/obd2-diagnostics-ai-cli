from __future__ import annotations

from obd.legacy_kline.profiles.base import KLineProfile


ISO9141_2 = KLineProfile(
    name="ISO9141-2 (ATSP3)",
    family="iso9141_2",
    init_at=[
        # NO hacemos ATZ aquí; initialize_elm() ya hace init global del adaptador
        "AT SP 3",
        "AT H1",   # headers on (tu ELM ya lo tiene como default)
        "AT L0",   # linefeeds off (limpia output)
        "AT S0",   # spaces off
    ],
    options_at=[
        # Opcionales; si te da problemas con ciertos ELM clones, se pueden togglear
        "AT E0",   # echo off
    ],
    verify_obd=["0100", "0902"],
    request_timeout_s=3.5,
    inter_command_delay_s=0.05,
)
