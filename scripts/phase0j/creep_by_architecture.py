#!/usr/bin/env python3
"""Phase-0J Sec.12 -- does the LIFE-LAW FAMILY change the interpretation of creep?

Phase 0I-R answered this for ONE representative trajectory (fully reversed, 0-100 C) and found
the strain metric falls 29.8 % while the energy metric rises 164.6 %. Sec.12 requires the
answer for the architectures actually being compared, whose cycle is unidirectional and much
milder. EP / EC / EPC are re-run at each architecture's electrical optimum.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0j"))
from native_metrics import run_case, OUT                               # noqa: E402

CASES = [("ARCH_Z1_EMBEDDED", 1.30, 2.7485664848789826, 82.8604875),
         ("ARCH_Z2_BACKSIDE", 0.30, 2.0796010434696357, 81.84530000000001),
         ("ARCH_Z4_POWER_DIE", 0.30, 2.984004758742853, 81.10178124999999)]


def main() -> int:
    rows = []
    for arch, h, du, th in CASES:
        for kind in ("EP", "EC", "EPC"):
            tag = f"{arch.replace('ARCH_','')}_{kind}"
            print(f"  {tag:26}", flush=True)
            q = run_case(tag, du, th, kind=kind)
            if q is None:
                print("      FAILED"); continue
            rows.append({"arch": arch, "h_sub_mm": h, "model": kind,
                         "description": {"EP": "elastic + plastic, NO creep",
                                         "EC": "elastic + creep, NO plasticity",
                                         "EPC": "elastic + plastic + creep (Phase 0I)"}[kind],
                         "M1_accum_inelastic_path": q["d_peeq_per_cycle"],
                         "M2_strain_range": q["range_eq_inelastic"],
                         "M3_inelastic_work_MJ_per_m3": q["inelastic_work_MJ_per_m3"],
                         "M1_over_M2": q["d_peeq_per_cycle"] / q["range_eq_inelastic"]})
            print(f"      M1={q['d_peeq_per_cycle']:.4e}  M2={q['range_eq_inelastic']:.4e}  "
                  f"M3={q['inelastic_work_MJ_per_m3']:.4f}", flush=True)
    # percentage effect of adding creep, per architecture, per metric
    by = {(r["arch"], r["model"]): r for r in rows}
    for r in rows:
        ep = by.get((r["arch"], "EP"))
        for m in ("M1_accum_inelastic_path", "M2_strain_range", "M3_inelastic_work_MJ_per_m3"):
            r[m + "_vs_EP_pct"] = (100 * (r[m] - ep[m]) / ep[m]) if ep else ""
    f = OUT / "creep_effect_by_architecture.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
