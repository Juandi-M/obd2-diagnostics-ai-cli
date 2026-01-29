from __future__ import annotations

import time
from typing import Optional, Sequence

from obd.elm.elm327 import ELM327
from obd.legacy_kline.config.errors import (
    KLineApplyError,
    KLineContext,
    KLineProfileError,
)
from obd.legacy_kline.profiles.base import KLineProfile
from obd.legacy_kline.runtime.routing import send_at_lines
from obd.legacy_kline.runtime.quirks import (
    QUIRK_FORCE_HEADERS_ON,
    QUIRK_FORCE_HEADERS_OFF,
    QUIRK_EXTRA_INTER_COMMAND_DELAY,
)


DEFAULT_RESET_AT: Sequence[str] = (
    # Reset suave sin ATZ duro (algunos clones se ponen raros con ATZ seguido)
    "AT D",   # defaults
    "AT E0",  # echo off
    "AT L0",  # linefeeds off
    "AT S0",  # spaces off
    "AT H1",  # headers on (tu driver prefiere headers ON por multi-ECU)
)


def _sleep(s: float) -> None:
    if s and s > 0:
        time.sleep(s)


def _effective_timeout(elm: ELM327, profile: KLineProfile) -> float:
    """
    elm.timeout puede ser None o no existir dependiendo del wrapper/clone.
    Siempre devolvemos algo seguro.
    """
    elm_to = float(getattr(elm, "timeout", 0) or 0)
    return max(elm_to, float(profile.request_timeout_s))


def apply_profile(
    elm: ELM327,
    profile: KLineProfile,
    *,
    delay_override_s: Optional[float] = None,
    reset_before_apply: bool = True,
    reset_at_commands: Sequence[str] = DEFAULT_RESET_AT,
) -> None:
    """
    Configura el ELM con el perfil K-Line.

    - Opcional: reset suave previo para evitar “estado pegado” entre candidatos.
    - Aplica quirks básicos (headers on/off, delay extra).
    - No hace verify (solo configura).
    """
    try:
        profile.validate()
    except Exception as e:
        raise KLineProfileError(
            f"Invalid K-Line profile: {e}",
            ctx=KLineContext(profile_name=profile.name),
            cause=e,
        ) from e

    base_delay = (
        profile.inter_command_delay_s
        if delay_override_s is None
        else delay_override_s
    )

    # Quirks que afectan timing
    extra_delay = 0.0
    if profile.quirks.get(QUIRK_EXTRA_INTER_COMMAND_DELAY, False):
        extra_delay = 0.08  # conservador

    final_delay = base_delay + extra_delay
    timeout_s = _effective_timeout(elm, profile)

    cmd = ""  # para contexto en caso de crash

    try:
        if reset_before_apply:
            for cmd in reset_at_commands:
                send_at_lines(elm, cmd, timeout_s=timeout_s)
                _sleep(final_delay)

        # Headers override por quirk
        if profile.quirks.get(QUIRK_FORCE_HEADERS_ON, False):
            cmd = "AT H1"
            send_at_lines(elm, cmd, timeout_s=timeout_s)
            _sleep(final_delay)

        if profile.quirks.get(QUIRK_FORCE_HEADERS_OFF, False):
            cmd = "AT H0"
            send_at_lines(elm, cmd, timeout_s=timeout_s)
            _sleep(final_delay)

        # Apply init sequence
        for cmd in profile.init_at:
            send_at_lines(elm, cmd, timeout_s=timeout_s)
            _sleep(final_delay)

        # Apply options
        for cmd in profile.options_at:
            send_at_lines(elm, cmd, timeout_s=timeout_s)
            _sleep(final_delay)

    except Exception as e:
        raise KLineApplyError(
            "Failed applying profile",
            ctx=KLineContext(
                profile_name=profile.name,
                at_or_obd_command=cmd,
            ),
            cause=e,
        ) from e
