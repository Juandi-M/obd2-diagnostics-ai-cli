from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class KLineProfile:
    """
    Describe cómo configurar el ELM327 para hablar con un vehículo legacy (K-Line).

    Importante:
    - Este objeto NO hace IO.
    - Solo define comandos AT, timeouts/delays y probes de verificación.
    """
    name: str

    # "iso9141_2" | "kwp2000_5baud" | "kwp2000_fast"
    family: str

    # Lista de comandos AT (strings completos, ej: "AT SP 3")
    init_at: List[str] = field(default_factory=list)

    # Opciones extra AT (se aplican después de init_at)
    options_at: List[str] = field(default_factory=list)

    # Probes para verificar comunicación con vehículo (OBD requests típicos)
    # Ej: ["0100", "0902"]
    verify_obd: List[str] = field(default_factory=lambda: ["0100"])

    # Timeouts/delays sugeridos
    request_timeout_s: float = 3.0
    inter_command_delay_s: float = 0.05

    # Flags para workarounds
    quirks: Dict[str, bool] = field(default_factory=dict)

    notes: Optional[str] = None

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("KLineProfile.name is empty")
        if self.family not in {"iso9141_2", "kwp2000_5baud", "kwp2000_fast"}:
            raise ValueError(f"Unsupported KLine family: {self.family}")
