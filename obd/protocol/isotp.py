from __future__ import annotations

from typing import List

def strip_isotp_pci_from_payload(payload: List[str]) -> List[str]:
    """
    Limpieza ISO-TP mínima pero más correcta:
    - Single Frame: 0x0L (drop 1 byte PCI)
    - First Frame:  0x1? + len byte (drop 2 bytes)
    - Consecutive:  0x2? (drop 1 byte)
    - Flow control: 0x3? (drop 3 bytes típicamente, pero aquí ignoramos el frame completo)
    """
    out: List[str] = []
    i = 0
    n = len(payload or [])

    while i < n:
        t = (payload[i] or "").upper()
        if len(t) != 2:
            # Si no es byte, lo dejamos pasar
            out.append(t)
            i += 1
            continue

        try:
            b = int(t, 16)
        except ValueError:
            out.append(t)
            i += 1
            continue

        frame_type = (b & 0xF0) >> 4  # high nibble

        # 0x0? Single frame (1 byte PCI)
        if frame_type == 0x0:
            i += 1
            continue

        # 0x1? First frame (2 bytes PCI: 1? + length)
        if frame_type == 0x1:
            i += 2
            continue

        # 0x2? Consecutive frame (1 byte PCI)
        if frame_type == 0x2:
            i += 1
            continue

        # 0x3? Flow control: generalmente no queremos esos bytes
        if frame_type == 0x3:
            # lo más seguro: saltar este byte y los siguientes 2 si existen
            i += 3
            continue

        out.append(t)
        i += 1

    return out
