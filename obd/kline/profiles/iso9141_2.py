from __future__ import annotations

from obd.kline.profiles.base import KLineProfile
from obd.kline.runtime.quirks import (
    QUIRK_RETRY_ON_NO_DATA,
    QUIRK_EXTRA_INTER_COMMAND_DELAY,
)

ISO9141_2 = KLineProfile(
    name="ISO9141-2 (ATSP3)",
    family="iso9141_2",
    init_at=[
        # Selección de protocolo
        "AT SP 3",
        # Salida limpia (muy compatible con clones)
        "AT E0",
        "AT L0",
        "AT S0",
        # Headers ON ayuda a parsing multi-ECU y debug
        "AT H1",
    ],
    options_at=[
        # Opcionales conservadores: por ahora dejamos vacío.
        # (Evitar AT ST/AT AT/AT AL hasta medir el TD5 real)
    ],
    verify_obd=[
        # Probes típicos:
        "0100",  # soporte mode01
        "010C",  # RPM (suele responder si mode01 vive)
        "0105",  # coolant temp
        "0902",  # VIN (si soporta mode09)
    ],
    request_timeout_s=4.0,
    inter_command_delay_s=0.07,
    quirks={
        # ISO9141 a veces responde lento o con NO DATA intermitente
        QUIRK_RETRY_ON_NO_DATA: True,
        QUIRK_EXTRA_INTER_COMMAND_DELAY: True,
    },
    notes="ISO9141-2 suele ser estable pero lento; usar probes 010C/0105 ayuda a confirmar vida real.",
)
