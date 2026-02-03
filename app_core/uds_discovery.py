from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from obd.elm import ELM327, CommunicationError, DeviceDisconnectedError
from obd.protocol import group_by_ecu, merge_payloads
from obd.protocol.isotp import strip_isotp_pci_from_payload
from obd.protocol.ascii import extract_ascii_from_hex_tokens, is_valid_vin

from app_core.vin_cache import get_vin_cache, set_vin_cache
from obd.uds.modules import module_map
from obd.uds.brands import normalize_brand


@dataclass
class DiscoveryOptions:
    id_start: int = 0x700
    id_end: int = 0x7FF
    timeout_s: float = 0.12
    retries: int = 0
    try_250k: bool = True
    include_29bit: bool = False
    stop_on_first: bool = True
    confirm_vin: bool = True
    confirm_dtcs: bool = False
    brand_hint: Optional[str] = None


@dataclass
class DiscoveredModule:
    tx_id: str
    rx_id: str
    protocol: str
    addressing: str
    responses: List[str] = field(default_factory=list)
    confidence: int = 0
    module_type: Optional[str] = None
    fingerprint: Dict[str, Any] = field(default_factory=dict)
    requires_security: bool = False
    alt_tx_ids: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _hex_id(value: int, *, width: int = 3) -> str:
    return f"{value:0{width}X}"


def _get_protocol_code(elm: ELM327) -> Tuple[Optional[str], bool]:
    try:
        resp = elm.send_raw("ATDPN", timeout=1.0).strip().upper()
    except Exception:
        return None, False
    if not resp:
        return None, False
    auto = resp.startswith("A")
    code = resp[-1] if resp[-1] in "0123456789ABCDEF" else None
    return code, auto


def _configure_transport(elm: ELM327, protocol: str) -> None:
    elm.send_raw_lines(f"ATSP{protocol}", timeout=1.0)
    elm.send_raw_lines("ATE0", timeout=1.0)
    elm.send_raw_lines("ATL0", timeout=1.0)
    elm.send_raw_lines("ATS1", timeout=1.0)
    elm.send_raw_lines("ATH1", timeout=1.0)
    elm.headers_on = True


def _send_probe(
    elm: ELM327,
    tx_id: str,
    payload_hex: str,
    timeout_s: float,
) -> Dict[str, List[str]]:
    elm.send_raw_lines(f"ATSH{tx_id}", timeout=1.0)
    lines = elm.send_raw_lines(
        payload_hex,
        timeout=timeout_s,
        silence_timeout=0.05,
        min_wait_before_silence_break=max(0.05, timeout_s * 0.5),
    )
    grouped = group_by_ecu(lines, headers_on=True)
    merged = merge_payloads(grouped, headers_on=True)
    return merged


def _match_response(payload: List[str], request_sid: int) -> bool:
    if not payload:
        return False
    cleaned = strip_isotp_pci_from_payload(payload)
    if not cleaned:
        return False
    pos = f"{(request_sid + 0x40) & 0xFF:02X}"
    req = f"{request_sid:02X}"
    for idx, tok in enumerate(cleaned):
        if tok.upper() == pos:
            return True
        if tok.upper() == "7F" and idx + 1 < len(cleaned) and cleaned[idx + 1].upper() == req:
            return True
    return False


def _detect_security(payload: List[str], request_sid: int) -> bool:
    cleaned = strip_isotp_pci_from_payload(payload)
    if len(cleaned) < 3:
        return False
    for idx in range(0, len(cleaned) - 2):
        if cleaned[idx].upper() == "7F" and cleaned[idx + 1].upper() == f"{request_sid:02X}":
            # 0x33 = security access denied
            return cleaned[idx + 2].upper() == "33"
    return False


def _extract_vin_from_payload(payload: List[str]) -> Optional[str]:
    cleaned = strip_isotp_pci_from_payload(payload)
    if not cleaned:
        return None
    # Find 62 F1 90
    for i in range(0, len(cleaned) - 2):
        if cleaned[i : i + 3] == ["62", "F1", "90"]:
            ascii_tail = extract_ascii_from_hex_tokens(cleaned[i + 3 :])
            if is_valid_vin(ascii_tail):
                return ascii_tail
    return None


def _parse_dtc_summary(payload: List[str]) -> Dict[str, int]:
    cleaned = strip_isotp_pci_from_payload(payload)
    if len(cleaned) < 3:
        return {}
    if cleaned[0].upper() != "59" or cleaned[1].upper() != "02":
        return {}
    # status_mask = cleaned[2]
    dtc_tokens = cleaned[3:]
    if not dtc_tokens:
        return {}
    counts = {"P": 0, "C": 0, "B": 0, "U": 0}
    for idx in range(0, len(dtc_tokens), 4):
        if idx + 3 > len(dtc_tokens):
            break
        try:
            b0 = int(dtc_tokens[idx], 16)
        except Exception:
            continue
        letter_idx = (b0 & 0xC0) >> 6
        letter = ["P", "C", "B", "U"][letter_idx]
        counts[letter] = counts.get(letter, 0) + 1
    return counts


def _classify_from_dtcs(counts: Dict[str, int]) -> Optional[str]:
    if not counts:
        return None
    dominant = max(counts.items(), key=lambda kv: kv[1])
    if dominant[1] == 0:
        return None
    letter = dominant[0]
    if letter == "C":
        return "ABS/ESC (chassis)"
    if letter == "P":
        return "Powertrain / Engine"
    if letter == "B":
        return "Body / BCM"
    if letter == "U":
        return "Network / Gateway"
    return None


def _brand_hint_from_vin(vin: str) -> Optional[str]:
    if not vin:
        return None
    wmi = vin[:3].upper()
    if wmi in {"1C4", "1C6", "1C3", "1C8", "2C4", "3C4"}:
        return "jeep"
    if wmi in {"SAL", "SAJ"}:
        return "land_rover"
    return None


def _module_type_from_name(name: str) -> str:
    key = (name or "").lower()
    mapping = {
        "generic_engine": "Powertrain / Engine",
        "pcm": "Powertrain / Engine",
        "generic_transmission": "Transmission",
        "tcm": "Transmission",
        "bcm": "Body / BCM",
        "airbag": "Airbag / SRS",
        "ipcm": "Cluster / IPC",
        "evic": "Cluster / IPC",
        "hvac": "HVAC",
        "tcase": "Transfer case",
        "scm": "Steering",
        "rf": "RF / Keyless",
        "radio": "Infotainment",
    }
    return mapping.get(key, name)


def _apply_signature_matches(modules: List[DiscoveredModule], brand_hint: Optional[str]) -> None:
    brand = normalize_brand(brand_hint) if brand_hint else "generic"
    catalog = module_map(brand, include_standard=True)
    by_pair: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for name, entry in catalog.items():
        tx = (entry.get("tx_id") or "").upper()
        rx = (entry.get("rx_id") or "").upper()
        if not tx or not rx:
            continue
        by_pair[(tx, rx)] = entry

    for mod in modules:
        key = (mod.tx_id.upper(), mod.rx_id.upper())
        entry = by_pair.get(key)
        if entry:
            mod.module_type = mod.module_type or _module_type_from_name(entry.get("name") or "Module")
            mod.notes.append(f"signature:{entry.get('name')}")
            mod.confidence = max(mod.confidence, 2)

        if not mod.module_type:
            # Generic fallback by diagnostic IDs
            if mod.tx_id.upper() == "7E0":
                mod.module_type = "Powertrain / Engine"
                mod.confidence = max(mod.confidence, 1)
            elif mod.tx_id.upper() == "7E1":
                mod.module_type = "Transmission"
                mod.confidence = max(mod.confidence, 1)


def _scan_11bit_range(
    elm: ELM327,
    options: DiscoveryOptions,
    protocol: str,
) -> List[DiscoveredModule]:
    modules_by_rx: Dict[str, DiscoveredModule] = {}
    for tx in range(options.id_start, options.id_end + 1):
        tx_hex = _hex_id(tx, width=3)
        found = False
        for _ in range(options.retries + 1):
            merged = _send_probe(elm, tx_hex, "10 03", options.timeout_s)
            for rx_id, payload in merged.items():
                if _match_response(payload, 0x10):
                    entry = modules_by_rx.get(rx_id)
                    if not entry:
                        entry = DiscoveredModule(
                            tx_id=tx_hex,
                            rx_id=rx_id,
                            protocol=protocol,
                            addressing="11-bit",
                            responses=["10 03"],
                            confidence=1,
                        )
                        modules_by_rx[rx_id] = entry
                    else:
                        if tx_hex != entry.tx_id and tx_hex not in entry.alt_tx_ids:
                            entry.alt_tx_ids.append(tx_hex)
                        if "10 03" not in entry.responses:
                            entry.responses.append("10 03")
                            entry.confidence += 1
                    found = True
            if found:
                break

        if found:
            continue

        for _ in range(options.retries + 1):
            merged = _send_probe(elm, tx_hex, "3E 00", options.timeout_s)
            for rx_id, payload in merged.items():
                if _match_response(payload, 0x3E):
                    entry = modules_by_rx.get(rx_id)
                    if not entry:
                        entry = DiscoveredModule(
                            tx_id=tx_hex,
                            rx_id=rx_id,
                            protocol=protocol,
                            addressing="11-bit",
                            responses=["3E 00"],
                            confidence=1,
                        )
                        modules_by_rx[rx_id] = entry
                    else:
                        if tx_hex != entry.tx_id and tx_hex not in entry.alt_tx_ids:
                            entry.alt_tx_ids.append(tx_hex)
                        if "3E 00" not in entry.responses:
                            entry.responses.append("3E 00")
                            entry.confidence += 1
            break

    return list(modules_by_rx.values())


def _scan_29bit_functional(
    elm: ELM327,
    options: DiscoveryOptions,
    protocol: str,
) -> List[DiscoveredModule]:
    modules_by_rx: Dict[str, DiscoveredModule] = {}
    # Functional addressing (UDS): 18DB33F1
    functional = "18DB33F1"
    for payload_hex, req_sid in (("10 03", 0x10), ("3E 00", 0x3E)):
        merged = _send_probe(elm, functional, payload_hex, options.timeout_s)
        for rx_id, payload in merged.items():
            if not _match_response(payload, req_sid):
                continue
            rx_upper = rx_id.upper()
            tx_id = rx_upper
            if rx_upper.startswith("18DAF1") and len(rx_upper) == 8:
                ecu_addr = rx_upper[-2:]
                tx_id = f"18DA{ecu_addr}F1"
            entry = modules_by_rx.get(rx_upper)
            if not entry:
                entry = DiscoveredModule(
                    tx_id=tx_id,
                    rx_id=rx_upper,
                    protocol=protocol,
                    addressing="29-bit",
                    responses=[payload_hex],
                    confidence=1,
                )
                modules_by_rx[rx_upper] = entry
            else:
                if payload_hex not in entry.responses:
                    entry.responses.append(payload_hex)
                    entry.confidence += 1
    return list(modules_by_rx.values())


def _fingerprint_modules(
    elm: ELM327,
    modules: List[DiscoveredModule],
    options: DiscoveryOptions,
) -> Optional[str]:
    vin_found: Optional[str] = None
    if not options.confirm_vin and not options.confirm_dtcs:
        return None
    for entry in modules:
        if options.confirm_vin:
            merged = _send_probe(elm, entry.tx_id, "22 F1 90", max(0.2, options.timeout_s * 2))
            payload = merged.get(entry.rx_id) or next(iter(merged.values()), [])
            if payload:
                vin = _extract_vin_from_payload(payload)
                if vin:
                    entry.fingerprint["vin"] = vin
                    entry.confidence += 1
                    vin_found = vin_found or vin
                if _detect_security(payload, 0x22):
                    entry.requires_security = True
        if options.confirm_dtcs:
            merged = _send_probe(elm, entry.tx_id, "19 02 FF", max(0.2, options.timeout_s * 2))
            payload = merged.get(entry.rx_id) or next(iter(merged.values()), [])
            if payload:
                summary = _parse_dtc_summary(payload)
                if summary:
                    entry.fingerprint["dtc_summary"] = summary
                    entry.confidence += 1
                    entry.module_type = entry.module_type or _classify_from_dtcs(summary)
                else:
                    entry.fingerprint["dtc_probe"] = "response"
                    entry.confidence += 1
                if _detect_security(payload, 0x19):
                    entry.requires_security = True
    return vin_found


def _protocol_candidates(options: DiscoveryOptions) -> List[str]:
    protocols: List[str] = ["6"]
    if options.try_250k:
        protocols.append("8")
    if options.include_29bit:
        protocols.append("7")
        if options.try_250k:
            protocols.append("9")
    return protocols


def discover_uds_modules(
    elm: ELM327,
    options: Optional[DiscoveryOptions] = None,
) -> Dict[str, Any]:
    opts = options or DiscoveryOptions()
    start = datetime.now(timezone.utc)

    orig_code, orig_auto = _get_protocol_code(elm)
    orig_headers = getattr(elm, "headers_on", True)

    results: Dict[str, Any] = {
        "modules": [],
        "protocol": None,
        "addressing": None,
        "elapsed_s": 0.0,
    }
    try:
        for protocol in _protocol_candidates(opts):
            addressing = "29-bit" if protocol in {"7", "9"} else "11-bit"
            try:
                _configure_transport(elm, protocol)
            except (CommunicationError, DeviceDisconnectedError) as exc:
                results["error"] = str(exc)
                break

            if addressing == "11-bit":
                modules = _scan_11bit_range(elm, opts, protocol)
            else:
                modules = _scan_29bit_functional(elm, opts, protocol)

            if modules:
                results["modules"] = modules
                results["protocol"] = protocol
                results["addressing"] = addressing
                vin = _fingerprint_modules(elm, modules, opts)
                if vin:
                    results["vin"] = vin
                brand_hint = opts.brand_hint or _brand_hint_from_vin(vin or "")
                _apply_signature_matches(modules, brand_hint)
                if opts.stop_on_first:
                    break
            elif not opts.stop_on_first:
                continue
    finally:
        # Restore previous protocol/headers
        try:
            if orig_auto or not orig_code:
                elm.send_raw_lines("ATSP0", timeout=1.0)
            else:
                elm.send_raw_lines(f"ATSP{orig_code}", timeout=1.0)
            elm.send_raw_lines("ATH1" if orig_headers else "ATH0", timeout=1.0)
            elm.send_raw_lines("ATS1" if orig_headers else "ATS0", timeout=1.0)
            elm.headers_on = orig_headers
        except Exception:
            pass

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    results["elapsed_s"] = elapsed

    modules = results.get("modules") or []
    vin = results.get("vin")
    if vin and modules:
        cached = get_vin_cache(vin) or {}
        cached["uds_modules"] = {
            "protocol": results.get("protocol"),
            "addressing": results.get("addressing"),
            "modules": [
                {
                    "tx_id": m.tx_id,
                    "rx_id": m.rx_id,
                    "protocol": m.protocol,
                    "addressing": m.addressing,
                    "responses": m.responses,
                    "confidence": m.confidence,
                    "module_type": m.module_type,
                    "fingerprint": m.fingerprint,
                    "requires_security": m.requires_security,
                    "alt_tx_ids": m.alt_tx_ids,
                }
                for m in modules
            ],
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        set_vin_cache(vin, cached)

    return results
