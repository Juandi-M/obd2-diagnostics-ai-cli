from __future__ import annotations

from typing import List

def payload_from_tokens(tokens: List[str], headers_on: bool = True) -> List[str]:
    """
    CAN típico con headers:
      <ECU> <LEN?> <DATA...>
    Sin headers:
      <DATA...>

    Heurística de LEN:
    - Solo intenta si rest[0] parece byte hex válido
    - Y si "encaja" con la cantidad de bytes que vienen después
    """
    if not tokens:
        return []

    rest = tokens[1:] if headers_on else tokens[:]
    if not rest:
        return []

    # drop "LEN" si encaja
    ln_tok = rest[0]
    if len(ln_tok) in (1, 2):
        try:
            ln = int(ln_tok, 16)
            remaining = len(rest) - 1
            # Heurística conservadora:
            # - ln > 0
            # - ln <= remaining (encaja exacto o al menos plausible)
            if 0 < ln <= remaining:
                return rest[1:]
        except ValueError:
            pass

    return rest
