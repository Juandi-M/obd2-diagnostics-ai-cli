from __future__ import annotations

import json

from obd.elm.elm327 import ELM327
from obd.legacy_kline.profiles.land_rover_td5 import td5_candidates
from obd.legacy_kline.session import LegacyKLineSession
from obd.legacy_kline.scanner import LegacyKLineScanner


def main() -> None:
    with ELM327() as elm:
        candidates = td5_candidates()

        session = LegacyKLineSession.auto(elm, candidates=candidates)

        print("\n=== K-LINE SESSION INFO ===")
        print(f"profile: {session.info.profile_name}")
        print(f"family : {session.info.family}")
        print(f"reason : {session.info.reason}")

        if session.detect_report:
            print("\n=== DETECT REPORT ===")
            rep = session.detect_report
            print(rep.summary())
            for i, att in enumerate(rep.attempts, 1):
                print(f"\n-- Candidate {i}: {att.profile_name} ({att.family})")
                print(f"   apply_ok: {att.apply_ok} err: {att.apply_error}")
                print(f"   verify_ok: {att.verify_ok}")
                print(f"   reason: {att.verify_reason}")
                print(f"   elapsed_ms: {att.elapsed_ms}")
                for p in att.probes:
                    print(f"     probe={p.probe} ok={p.ok} lines={p.lines_preview} :: {p.query_summary}")

        scanner = LegacyKLineScanner(session, manufacturer="land_rover")

        print("\n=== LIVE BASIC ===")
        live = scanner.live_basic()
        live_json = {
            k: {
                "pid": v.pid,
                "name": v.name,
                "unit": v.unit,
                "value": v.value,
                "raw_hex": v.raw_hex[:48],
            }
            for k, v in live.items()
        }
        print(json.dumps(live_json, indent=2, ensure_ascii=False))

        print("\n=== DTCs (MODE 03) ===")
        dtc_res = scanner.read_dtcs("03")
        if not dtc_res.dtcs:
            print("No DTCs 👍")
        else:
            for d in dtc_res.dtcs:
                print(f"{d.code} - {d.description}")

        print("\nDONE ✅")


if __name__ == "__main__":
    main()
