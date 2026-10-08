#!/usr/bin/env python3
"""Phase-0G Sec.15 -- recompute the 1 kW placement comparison with DEFECT #30 fixed.

The Phase-0F placement table understated every vertical tier by n_vr = 49. The shift is
expected to be near-identical across the three lattices, so the ordering should survive --
but "expected" is not "verified", and this phase does not carry forward numbers it has not
recomputed. Warpage is additionally reported under the explicit assembly, since Sec.7
withdrew BC_B and Sec.14 showed the footprint sign is assembly-state dependent.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0g"))
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0g"


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd, rows = OUT / "runs_place", []
    print("Sec.15  PLACEMENT at 1 kW, ARCH_A, M = 49, j = 3.5, h_sub = 1.50 mm (corrected)")
    print(f"{'lattice':12s} {'P_total W':>11s} {'P_rdl W':>9s} {'P_tsv W':>9s} "
          f"{'Tmax C':>8s} {'die w um':>9s}")
    for fam in ("uniform", "compact", "asymmetric"):
        t0 = time.time()
        r = kw1.coupled_1kw("ARCH_A", fam, 1.50, h_top, stack, doe, wd,
                            bc="BC_A", tol=0.01, max_it=20)
        if not r["feasible"]:
            print(f"{fam:12s} INFEASIBLE {r['reason']}"); continue
        rows.append({"lattice": fam, "P_elec_total_w": r["P_elec_total_w"],
                     "P_rdl_w": r["P_rdl_w"], "P_tsv_w": r["P_tsv_w"],
                     "P_pdn_w": r["P_pdn_w"], "T_max_C": r["T_max_C"],
                     "die_warpage_pv_um": r["die_warpage_pv_um"],
                     "wall_s": time.time() - t0})
        print(f"{fam:12s} {r['P_elec_total_w']:11.5f} {r['P_rdl_w']:9.5f} "
              f"{r['P_tsv_w']:9.5f} {r['T_max_C']:8.3f} {r['die_warpage_pv_um']:9.4f}",
              flush=True)
    f = OUT / "placement_corrected_1kw.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    if len(rows) == 3:
        u = rows[0]["P_elec_total_w"]
        print(f"\n  spread uniform -> asymmetric = "
              f"{(rows[2]['P_elec_total_w']-u)*1000:+.1f} mW")
        best_p = min(rows, key=lambda r: r["P_elec_total_w"])["lattice"]
        best_w = min(rows, key=lambda r: r["die_warpage_pv_um"])["lattice"]
        print(f"  lowest loss = {best_p}   lowest warpage = {best_w}   "
              f"{'AGREE' if best_p == best_w else 'DISAGREE'}")
    print(f"\nwrote {f}")


if __name__ == "__main__":
    main()
