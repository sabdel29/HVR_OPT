#!/usr/bin/env python3
"""Phase-0M-R Section 14 -- run the frozen comparison matrix."""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
import replay_production as RPX                                            # noqa: E402

OUT = R / "results" / "phase0mr"

MATRIX = [
    # (arch, mode, template, cooler)
    ("ARCH_Z1_EMBEDDED", "BEFORE", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_27"),
    ("ARCH_Z2_BACKSIDE", "BEFORE", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_27"),
    ("ARCH_Z4_POWER_DIE", "BEFORE", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_27"),
    ("ARCH_Z1_EMBEDDED", "AFTER", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_27"),
    ("ARCH_Z2_BACKSIDE", "AFTER", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_27"),
    ("ARCH_Z4_POWER_DIE", "AFTER", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_27"),
    # cooling sensitivity: does the cooler, not the model, set the temperature?
    ("ARCH_Z2_BACKSIDE", "AFTER", "T1_EMBEDDED_4LAYER", "TOP_SI_MICROCHANNEL_50"),
    ("ARCH_Z2_BACKSIDE", "AFTER", "T1_EMBEDDED_4LAYER", "TWO_SIDED_SI_14"),
    # component-partition sensitivity: is intra-VR routing still common mode?
    ("ARCH_Z1_EMBEDDED", "AFTER", "T4_SPLIT_SC_BUCK", "TOP_SI_MICROCHANNEL_27"),
    ("ARCH_Z2_BACKSIDE", "AFTER", "T4_SPLIT_SC_BUCK", "TOP_SI_MICROCHANNEL_27"),
]


def main() -> int:
    rows, ledger_rows, tier_rows = [], [], []
    t0 = time.time()
    for i, (a, m, tpl, cl) in enumerate(MATRIX, 1):
        try:
            r = RPX.run_case(a, m, template=tpl, cooler_name=cl)
        except Exception as e:                                   # noqa: BLE001
            import traceback
            rows.append({"arch": a, "mode": m, "template": tpl, "cooler": cl,
                         "status": f"FAILED {type(e).__name__}: {e}"})
            print(f"[{i}/{len(MATRIX)}] {a} {m} {tpl} {cl} FAILED: {e}", flush=True)
            traceback.print_exc()
            continue
        ledger_rows += r.pop("ledger_rows", [])
        tier_rows += r.pop("tiers", [])
        r.pop("hist", None)
        rows.append(r)
        print(f"[{i}/{len(MATRIX)}] {a:20s} {m:6s} {tpl:20s} {cl:24s} "
              f"P={r.get('P_elec_total_w', float('nan')):8.3f} W  "
              f"Tmax={r.get('T_max_C', float('nan')):7.2f} C  "
              f"warp={r.get('die_warpage_pv_um', float('nan')):7.3f} um  "
              f"du={r.get('du_corner_um', float('nan')):6.4f} um  "
              f"({r.get('wall_s', 0):.0f}s)", flush=True)
        _write(rows, ledger_rows, tier_rows)
    print(f"\n{len(rows)} cases in {time.time()-t0:.0f}s")
    return 0


def _write(rows, ledger_rows, tier_rows):
    k = sorted({x for r in rows for x in r})
    with open(OUT / "production_architecture_replay.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    if ledger_rows:
        k2 = sorted({x for r in ledger_rows for x in r})
        with open(OUT / "intravr_loss_ledger.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k2); w.writeheader(); w.writerows(ledger_rows)
    if tier_rows:
        k3 = sorted({x for r in tier_rows for x in r})
        with open(OUT / "production_loss_decomposition.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k3); w.writeheader(); w.writerows(tier_rows)


if __name__ == "__main__":
    raise SystemExit(main())
