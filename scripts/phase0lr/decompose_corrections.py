#!/usr/bin/env python3
"""Phase-0L-R Part 3 -- separate the NUMERICAL correction from the CONSTITUTIVE correction.

Phase 0L changed two things at once and the brief is right that they must never be conflated:

  A. integration / solver control -- the inelastic-ENERGY integral was under-resolved, because
     most inelastic work is deposited in the fast transient at the start of each half-cycle and
     the pre-0L starting increment stepped over it.
  B. the constitutive model -- the old card drove creep with a stress variable it was never
     fitted in, and is extrapolated far above its source stress window.

The decomposition is a 2x2: hold the model fixed and change only the control, then hold the
control fixed and change only the model. Nothing is labelled "same model" if the model id moved.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
L = R / "results" / "phase0l"
OUT = R / "results" / "phase0lr"
SIM_SE_D, SIM_SE_A, BETA, ZT = 0.08, 0.06, 5.1, 3.0
A, B = "EXP_45_125", "EXP_110_150"
F = lambda r, k: float(r[k])


def load(path, control):
    rows = [r for r in csv.DictReader(open(path)) if r["status"] == "OK"]
    return {(r["model"], r["arch"], r["profile_tag"]): r for r in rows
            if r.get("solver_control", "DEFAULT") == control}


def design(d, model):
    need = [(model, a, c) for a in ("Z1", "Z2") for c in (A, B)]
    if not all(k in d for k in need):
        return None
    we, eff = {}, {}
    for c in (A, B):
        z1, z2 = d[(model, "Z1", c)], d[(model, "Z2", c)]
        we[c] = F(z1, "inelastic_work_MJ_per_m3") / F(z1, "d_peeq_per_cycle")
        eff[c] = min(F(z1, "d_peeq_per_cycle") / F(z2, "d_peeq_per_cycle"),
                     F(z1, "inelastic_work_MJ_per_m3") / F(z2, "inelastic_work_MJ_per_m3"))
    D = max(we.values()) / min(we.values())
    nq1 = next((n for n in range(4, 40001)
                if math.log(D) / math.sqrt(2/(BETA**2*n) + SIM_SE_D**2) >= ZT), None)
    nq2 = next((n for n in range(4, 40001)
                if sum(math.log(eff[c]) for c in (A, B))
                / math.sqrt(2/(BETA**2*n) + SIM_SE_A**2) / math.sqrt(2) >= ZT), None)
    b = d.get((model, "Z1", "OP_BASELINE")), d.get((model, "Z2", "OP_BASELINE"))
    out = {"D": D, "n_Q1": nq1, "n_Q2": nq2, "n_per_cell": max(nq1 or 0, nq2 or 0) or None,
           "w_over_eps_45_125": we[A], "w_over_eps_110_150": we[B]}
    if all(b):
        out["strain_metric_Z1"] = F(b[0], "d_peeq_per_cycle")
        out["energy_metric_Z1"] = F(b[0], "inelastic_work_MJ_per_m3")
        out["Z2_Z1_strain"] = F(b[0], "d_peeq_per_cycle") / F(b[1], "d_peeq_per_cycle")
        out["Z2_Z1_energy"] = (F(b[0], "inelastic_work_MJ_per_m3")
                               / F(b[1], "inelastic_work_MJ_per_m3"))
    return out


def main() -> int:
    dflt = load(L / "package_model_replay.csv", "DEFAULT")
    tght = load(L / "package_model_replay_tight.csv", "TIGHT")
    cells = {}
    for model in ("M0_COARSE", "M0_FINE", "M1", "M1_NLO", "M1_NHI"):
        for ctrl, d in (("DEFAULT", dflt), ("TIGHT", tght)):
            r = design(d, model)
            if r:
                cells[(model, ctrl)] = r

    rows = []
    for (model, ctrl), r in sorted(cells.items()):
        rows.append({"case": f"{model}/{ctrl}", "constitutive_model": model,
                     "integration_control": ctrl,
                     "time_step": ("dt0=1e-5, dtmax=10 s" if ctrl == "DEFAULT"
                                   else "dt0=1e-8, dtmax=10 s"),
                     "energy_metric_Z1_MJ_per_m3": r.get("energy_metric_Z1", ""),
                     "strain_metric_Z1": r.get("strain_metric_Z1", ""),
                     "D": r["D"], "Z2_Z1_strain": r.get("Z2_Z1_strain", ""),
                     "Z2_Z1_energy": r.get("Z2_Z1_energy", ""),
                     "n_per_cell": r["n_per_cell"],
                     "difference_due_to_numerics": "", "difference_due_to_constitutive_model": ""})

    def get(m, c, k):
        return cells.get((m, c), {}).get(k)

    # PURE NUMERICS: same model (M0_COARSE), control DEFAULT -> TIGHT
    num = {k: (get("M0_COARSE", "TIGHT", k), get("M0_COARSE", "DEFAULT", k))
           for k in ("D", "n_per_cell", "Z2_Z1_strain", "Z2_Z1_energy", "energy_metric_Z1",
                     "strain_metric_Z1")}
    # PURE CONSTITUTIVE: same control (TIGHT), model M0_COARSE -> M1
    con = {k: (get("M1", "TIGHT", k), get("M0_COARSE", "TIGHT", k))
           for k in ("D", "n_per_cell", "Z2_Z1_strain", "Z2_Z1_energy", "energy_metric_Z1",
                     "strain_metric_Z1")}
    for r in rows:
        if r["case"] == "M0_COARSE/TIGHT":
            r["difference_due_to_numerics"] = (
                f"vs M0_COARSE/DEFAULT: D {num['D'][1]:.4f} -> {num['D'][0]:.4f} "
                f"({100*(num['D'][0]/num['D'][1]-1):+.1f} %); "
                f"n {num['n_per_cell'][1]} -> {num['n_per_cell'][0]}")
        if r["case"] == "M1/TIGHT":
            r["difference_due_to_constitutive_model"] = (
                f"vs M0_COARSE/TIGHT: D {con['D'][1]:.4f} -> {con['D'][0]:.4f} "
                f"({100*(con['D'][0]/con['D'][1]-1):+.1f} %); "
                f"n {con['n_per_cell'][1]} -> {con['n_per_cell'][0]}")

    p = OUT / "numerics_vs_constitutive_decomposition.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    print(f"{'case':>20} {'D':>9} {'n/cell':>7} {'Z2/Z1 eps':>10} {'Z2/Z1 W':>9} "
          f"{'W_Z1':>9} {'eps_Z1':>10}")
    for r in rows:
        f = lambda k: (f"{float(r[k]):.4f}" if r[k] != "" else "--")
        print(f"{r['case']:>20} {r['D']:9.4f} {str(r['n_per_cell']):>7} "
              f"{f('Z2_Z1_strain'):>10} {f('Z2_Z1_energy'):>9} "
              f"{f('energy_metric_Z1_MJ_per_m3'):>9} {f('strain_metric_Z1'):>10}")
    print()
    print("=" * 96)
    print("DECOMPOSITION -- one factor changed at a time")
    print("=" * 96)
    print("A. NUMERICS ONLY  (model held at M0_COARSE; control DEFAULT -> TIGHT)")
    for k, lab in (("D", "D"), ("Z2_Z1_strain", "Z2/Z1 strain"), ("Z2_Z1_energy", "Z2/Z1 energy"),
                   ("energy_metric_Z1", "energy metric"), ("strain_metric_Z1", "strain metric")):
        a, b = num[k]
        if a and b:
            print(f"   {lab:>14}: {b:10.5f} -> {a:10.5f}   ({100*(a/b-1):+7.2f} %)")
    print(f"   {'n per cell':>14}: {num['n_per_cell'][1]:10d} -> {num['n_per_cell'][0]:10d}")
    print()
    print("B. CONSTITUTIVE ONLY  (control held at TIGHT; model M0_COARSE -> M1)")
    for k, lab in (("D", "D"), ("Z2_Z1_strain", "Z2/Z1 strain"), ("Z2_Z1_energy", "Z2/Z1 energy"),
                   ("energy_metric_Z1", "energy metric"), ("strain_metric_Z1", "strain metric")):
        a, b = con[k]
        if a and b:
            print(f"   {lab:>14}: {b:10.5f} -> {a:10.5f}   ({100*(a/b-1):+7.2f} %)")
    print(f"   {'n per cell':>14}: {con['n_per_cell'][1]:10d} -> {con['n_per_cell'][0]:10d}")
    print()
    d0 = get("M0_COARSE", "DEFAULT", "D"); d1 = get("M0_COARSE", "TIGHT", "D")
    d2 = get("M1", "TIGHT", "D")
    print(f"ANSWER: of the move in D from {d0:.4f} (the Phase-0K-R value) to {d2:.4f},")
    print(f"        {100*(d1-d0)/(d2-d0) if d2 != d0 else float('nan'):.0f} % is energy-integration "
          f"resolution and {100*(d2-d1)/(d2-d0) if d2 != d0 else float('nan'):.0f} % is the "
          f"material-model correction.")
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
