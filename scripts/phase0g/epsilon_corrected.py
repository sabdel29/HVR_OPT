#!/usr/bin/env python3
"""Phase-0G Sec.13 -- recompute the mechanical epsilon sweep on corrected numbers.

This is a PARAMETRIC PREFERENCE SENSITIVITY, not a feasibility study. Sec.12 established that
no admissible mechanical criterion exists, so epsilon is a USER-SET PREFERENCE on warpage and
carries no physical authority whatsoever. The question asked is only: if a designer chose to
cap warpage at epsilon, what would it cost electrically?

Two things force a recomputation rather than a reuse of the Phase-0F sweep:
  * DEFECT #30 -- every vertical-tier loss was understated by n_vr = 49, so P(h) is wrong.
  * Sec.7 -- BC_B is not a valid mounted model, so the warpage column is wrong as well.

The sweep is therefore run in BOTH assembly states so that the dependence of the answer on
the assembly model is visible rather than hidden behind one choice.
"""
from __future__ import annotations
import csv, json
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0g"


def load(fn, key="die_warpage_pv_um"):
    rows = list(csv.DictReader(open(OUT / fn)))
    return {round(float(r["h_sub_mm"]), 2): (float(r["P_elec_total_w"]), float(r[key]))
            for r in rows}


def board_w():
    """BC_BOARD (FR-4 1.6 mm) warpage at the three thicknesses actually simulated."""
    w = {}
    for r in csv.DictReader(open(OUT / "explicit_board_crosscheck.csv")):
        if r["restraint"] == "BC_BOARD" and r["board_case"] == "fr4_1p6mm":
            w[round(float(r["h_sub_mm"]), 2)] = float(r["die_warpage_pv_um"])
    return w


def sweep(cand, label, rows):
    """cand: {h: (P_w, W_um)} -> minimum-power design under each warpage preference."""
    if not cand:
        return
    p_unc = min(p for p, _ in cand.values())
    h_unc = min(cand, key=lambda h: cand[h][0])
    w_all = sorted(w for _, w in cand.values())
    for eps in (float("inf"), 30.0, 25.0, 20.0, 15.0, 12.0, 11.0, 10.0, 8.0, 5.0,
                3.0, 2.0, 1.5, 1.3, 1.0):
        ok = {h: v for h, v in cand.items() if v[1] <= eps}
        etxt = "inf" if eps == float("inf") else f"{eps:g}"
        if not ok:
            rows.append({"assembly": label, "epsilon_um": etxt, "feasible_designs": 0,
                         "h_opt_mm": "", "P_at_h_opt_w": "", "warpage_um": "",
                         "penalty_mW": "", "binds": "NO DESIGN SATISFIES PREFERENCE"})
            continue
        h = min(ok, key=lambda k: ok[k][0])
        p, w = ok[h]
        rows.append({"assembly": label, "epsilon_um": etxt, "feasible_designs": len(ok), "h_opt_mm": f"{h:.2f}",
                     "P_at_h_opt_w": f"{p:.6f}", "warpage_um": f"{w:.5f}",
                     "penalty_mW": f"{(p - p_unc)*1000:.3f}",
                     "binds": "yes" if h != h_unc else "no"})
    return h_unc, p_unc, w_all


def main():
    rows = []
    for arch, fn in (("ARCH_B", "crossover_hires_ARCH_B_fixedB.csv"),
                     ("ARCH_A", "crossover_hires_ARCH_A_fixedA.csv")):
        cand = load(fn)
        r = sweep(cand, f"{arch} / BC_A free package", rows)
        print(f"{arch} free:   unconstrained h={r[0]:.2f} mm P={r[1]:.5f} W  "
              f"warpage range {min(r[2]):.2f}-{max(r[2]):.2f} um")
        bw = board_w()
        cb = {h: (cand[h][0], bw[h]) for h in bw if h in cand}
        r = sweep(cb, f"{arch} / BC_BOARD FR-4 1.6 mm", rows)
        print(f"{arch} board:  unconstrained h={r[0]:.2f} mm P={r[1]:.5f} W  "
              f"warpage range {min(r[2]):.2f}-{max(r[2]):.2f} um")

    f = OUT / "mechanical_epsilon_corrected.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print(f"\n{'assembly':32s} {'eps':>6s} {'n':>3s} {'h_opt':>6s} {'P (W)':>11s} "
          f"{'W (um)':>9s} {'penalty':>10s}  binds")
    for r in rows:
        print(f"{r['assembly']:32s} {r['epsilon_um']:>6s} {r['feasible_designs']:>3d} "
              f"{r['h_opt_mm']:>6s} {r['P_at_h_opt_w']:>11s} {r['warpage_um']:>9s} "
              f"{r['penalty_mW']:>10s}  {r['binds']}")
    print(f"\nwrote {f}")


if __name__ == "__main__":
    main()
