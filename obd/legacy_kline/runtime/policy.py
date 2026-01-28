from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KLinePolicy:
    """
    Policy runtime para retries/timeout/delays.
    """
    retries: int = 1
    timeout_s: float = 3.0

    # Delay pequeño entre requests (ayuda con K-Line, algunos ECUs odian spam)
    inter_request_delay_s: float = 0.05

    # Si un ECU se duerme o el init requiere aire, esto ayuda
    initial_settle_delay_s: float = 0.10
