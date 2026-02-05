from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class KLineProfile:
    """
    Describe cómo configurar el ELM327 para hablar con un vehículo con protocolo legado (K-Line).

    Esta clase es intencionalmente conservadora:
    - Solo define 'AT commands' que suelen ser soportados por la mayoría de ELM/clones.
    - Evita knobs experimentales (ST/AT/AL/etc.) hasta que tengamos evidencia del carro/adaptador.

    NOTA:
    - El IO lo hace config/apply + runtime/routing
    """
    name: str
    family: str  # "iso9141_2" | "kwp2000_5baud" | "kwp2000_fast"

    # Secuencia base para activar protocolo, headers, etc.
    init_at: List[str] = field(default_factory=list)

    # Opciones adicionales (conservadoras)
    options_at: List[str] = field(default_factory=list)

    # Probes OBD para verificar comunicación
    verify_obd: List[str] = field(default_factory=lambda: ["0100", "0902"])

    # Timeouts/delays recomendados para ese perfil
    request_timeout_s: float = 4.0
    inter_command_delay_s: float = 0.08

    # Quirks (flags) para workarounds.
    # Se consumen en config/apply y luego se integrarán fuerte en runtime/routing.
    quirks: Dict[str, bool] = field(default_factory=dict)

    # Notas humanas para debugging
    notes: Optional[str] = None

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("KLineProfile.name is empty")
        if self.family not in {"iso9141_2", "kwp2000_5baud", "kwp2000_fast"}:
            raise ValueError(f"Unsupported K-Line family: {self.family}")

        # seguridad: no mandes comandos vacíos
        for seq in (self.init_at, self.options_at):
            for cmd in seq:
                if not isinstance(cmd, str) or not cmd.strip():
                    raise ValueError(f"Invalid AT command in profile '{self.name}': {cmd!r}")

        # probes básicos
        for p in self.verify_obd:
            if not isinstance(p, str) or not p.strip():
                raise ValueError(f"Invalid verify probe in profile '{self.name}': {p!r}")
