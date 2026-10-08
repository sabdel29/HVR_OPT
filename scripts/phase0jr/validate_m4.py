#!/usr/bin/env python3
"""Phase-0J-R Sec.4 -- validate the M4 reconstruction on decks where the answer is known.

In the EC deck there is NO *PLASTIC card, so every increment of PEEQ is creep. The
reconstructed M4 must therefore equal d(PEEQ) to within integration error. If it does, the
identical reconstruction applied to the EPC deck isolates the creep part of a combined
plastic+creep response, which is what Syed's epsilon_acc requires.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from creep_metric import cycle_creep, creep_series, OUT                    # noqa: E402
from joint import build_joint                                             # noqa: E402

P0J = R / "results" / "phase0j" / "native"
DWELL = 300.0
CASES = [("Z1_EMBEDDED_EPC", "EPC"), ("Z1_EMBEDDED_EC", "EC"), ("Z1_EMBEDDED_EP", "EP"),
         ("Z2_BACKSIDE_EPC", "EPC"), ("Z2_BACKSIDE_EC", "EC"), ("Z2_BACKSIDE_EP", "EP"),
         ("Z4_POWER_DIE_EPC", "EPC"), ("Z4_POWER_DIE_EC", "EC"), ("Z4_POWER_DIE_EP", "EP")]


def main() -> int:
    m = build_joint(6, 8, 1)
    core = set(m.sets["ESOLCORE"])
    rows = []
    print(f"{'case':22} {'model':5} {'M4 (creep)':>12} {'d(PEEQ)':>12} {'M4/dPEEQ':>9} "
          f"{'M5 (MJ/m3)':>11}")
    for tag, kind in CASES:
        d = P0J / f"{tag}.dat"
        if not d.is_file():
            print(f"{tag:22} {kind:5}  MISSING"); continue
        ser, vols = creep_series(d, core)
        te = 8 * DWELL
        q = cycle_creep(ser, vols, te - 2 * DWELL, te, has_plastic=(kind != "EC"))
        if q is None:
            print(f"{tag:22} {kind:5}  NO WINDOW"); continue
        r = q["M4_creep_strain"] / q["d_peeq"] if q["d_peeq"] else float("nan")
        print(f"{tag:22} {kind:5} {q['M4_creep_strain']:12.5e} {q['d_peeq']:12.5e} "
              f"{r:9.4f} {q['M5_creep_energy_MJ_per_m3']:11.5f}")
        rows.append({"case": tag, "model": kind, "M4_creep_strain": q["M4_creep_strain"],
                     "M1_d_peeq": q["d_peeq"], "M4_over_M1": r,
                     "M5_creep_energy_MJ_per_m3": q["M5_creep_energy_MJ_per_m3"]})
    f = OUT / "m4_validation.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    ec = [r for r in rows if r["model"] == "EC"]
    print("\nVALIDATION -- creep-only decks, where M4 MUST equal d(PEEQ):")
    for r in ec:
        print(f"  {r['case']:22} M4/d(PEEQ) = {r['M4_over_M1']:.4f}  "
              f"({100*(r['M4_over_M1']-1):+.2f} %)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
