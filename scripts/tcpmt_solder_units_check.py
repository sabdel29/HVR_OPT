"""Numerical and card-construction checks of the production local model (tasks 2, 4, 5).

1. Equilibrium tolerance. The two most sensitive tier joints are re-solved with the
   CalculiX equilibrium tolerances tightened 100x (*CONTROLS, PARAMETERS=FIELD 5e-5, 1e-4,
   ...). The response does not move (< 1e-5): the production solves are converged.
2. Unit basis. A consistent change of the force unit (stress unit k MPa: E, yield / k,
   Norton A x k^n, copper rescaled) leaves the boundary-value problem unchanged, yet the
   response moves by up to ~6 %. The cause is the production card, not the solver
   tolerance: its rows are 25 C apart (-40, 0, 25, ..., 125 C) with n changing between rows,
   and CalculiX interpolates A LINEARLY between rows (creeps.f / materialdata_me.f, see
   results/phase0l/CALCULIX_CREEP_IMPLEMENTATION_AUDIT.md Sec. 7). Linear interpolation of
   A k^n is not k^n times the linear interpolation of A, so the effective creep law at a
   joint temperature between rows depends on the unit basis (effective_A_at_T_joint below).
3. Card as intended. The production card rebuilt by the same function
   (solder_model.inp_material) on a 2.5 C row grid, so the solver's interpolation follows
   the intended Arrhenius-in-rate construction of solder_model.norton_at to < 1 %. Its
   difference from the 7-row production card is the card-construction sensitivity.

    python tcpmt_solder_units_check.py --run | --summarize
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

STUDY = "constitutive"
UNITS = ("10MPa", "100MPa")
#: R_n, C_n, q_0, q_u, R_P, eps, C_eps, R_l (CalculiX defaults 0.005, 0.01, 0.01, -, 0.02,
#: 1e-5, 1e-3, 1e-8); R_n, C_n, R_P and C_eps tightened 100x
TIGHT = "5.e-5,1.e-4,0.01,,2.e-4,1.e-5,1.e-5,1.e-8"
TIGHT_CASES = ("B_Z1", "A_Z1")
FINE_GRID = [round(-40.0 + 2.5 * k, 2) for k in range(int((150.0 + 40.0) / 2.5) + 1)]


def fine_card():
    return C.SM.inp_material("SAC305", FINE_GRID)


def tasks():
    prod = C.DEC.material(C.LR.MATKIND)
    fine = fine_card()
    t = []
    for tier, arch, case in C.tier_cases():
        k = f"{tier}_{arch}"
        c = C.critical(case)
        base = dict(du_um=c["du_um"], T_C=c["T_C"], study=STUDY,
                    meta={"tier": tier, "arch": arch, "case": case, "law": "production"})
        t.append(dict(base, tag=f"{k}_production_finegrid", card=fine,
                      card_name="production card rebuilt on a 2.5 C row grid "
                                "(solder_model.inp_material)", sig="production|finegrid"))
        if k in TIGHT_CASES:
            t.append(dict(base, tag=f"{k}_production_tight", card=None,
                          card_name="production card, equilibrium tolerances 100x tighter",
                          controls=TIGHT, sig=f"production|MPa|{TIGHT}"))
        for u in UNITS:
            t.append(dict(base, tag=f"{k}_production_{u}", card=prod, units=u,
                          card_name=f"production card in {u} units",
                          sig=f"production|{u}"))
    return sorted(t, key=lambda x: "finegrid" not in x["tag"])


def effective_A(T, k):
    """A (MPa units) the solver uses at T when the 7-row production card is written in a
    stress unit of k MPa (linear interpolation of A k^n and of n between rows)."""
    rows = []
    sec = None
    for line in C.DEC.material(C.LR.MATKIND).splitlines():
        if line.startswith("*"):
            sec = line[1:].split(",")[0].strip().upper()
            continue
        if sec == "CREEP":
            a, n, _, tt = (float(x) for x in line.split(","))
            rows.append((tt, a, n))
    Ts = np.array([r[0] for r in rows])
    Ak = np.array([r[1] * k ** r[2] for r in rows])
    ns = np.array([r[2] for r in rows])
    a, n = float(np.interp(T, Ts, Ak)), float(np.interp(T, Ts, ns))
    return a / k ** n, n


def summarize():
    recs = C.load_records(STUDY)
    out = {"what": "equilibrium-tolerance, unit-basis and card-grid checks of the production "
                   "local model (production card, L0, production settings)",
           "tight_controls": TIGHT, "fine_grid_C": [FINE_GRID[0], FINE_GRID[-1], 2.5],
           "mechanism": "CalculiX interpolates the Norton A linearly between card rows; the "
                        "production rows are 25 C apart with n varying, so the effective law "
                        "at a joint temperature between rows depends on the unit basis and "
                        "differs from the intended Arrhenius construction", "cases": {}}
    for tier, arch, case in C.tier_cases():
        k = f"{tier}_{arch}"
        base = (recs.get(f"{k}_production") or {}).get("d_peeq_per_cycle")
        T = C.critical(case)["T_C"]
        row = {"T_joint_C": T, "MPa": base}
        for u in ("10MPa", "100MPa", "GPa", "tight", "finegrid"):
            v = (recs.get(f"{k}_production_{u}") or {}).get("d_peeq_per_cycle")
            row[u] = v
            row[f"{u}_rel_diff"] = ((v - base) / base) if (v and base) else None
        vals = [row[u] for u in ("MPa", "10MPa", "100MPa", "GPa") if row.get(u)]
        row["unit_basis_spread_rel"] = ((max(vals) - min(vals)) / base) \
            if (base and len(vals) > 1) else None
        row["effective_A_at_T_joint"] = {u: effective_A(T, C.UNIT_SCALE[u])[0]
                                         for u in ("MPa", "10MPa", "100MPa", "GPa")}
        row["intended_A_at_T_joint"] = C.SM.norton_at(T)["A"]
        row["card_grid_sensitivity_rel"] = (abs(row["finegrid"] - base) / row["finegrid"]
                                            if (row.get("finegrid") and base) else None)
        out["cases"][k] = row
    sp = [r["unit_basis_spread_rel"] for r in out["cases"].values()
          if r.get("unit_basis_spread_rel")]
    cg = [r["card_grid_sensitivity_rel"] for r in out["cases"].values()
          if r.get("card_grid_sensitivity_rel") is not None]
    tt = [abs(r["tight_rel_diff"]) for r in out["cases"].values()
          if r.get("tight_rel_diff") is not None]
    out["unit_basis_spread_max_rel"] = max(sp) if sp else None
    out["card_grid_sensitivity_max_rel"] = max(cg) if cg else None
    out["equilibrium_tolerance_effect_max_rel"] = max(tt) if tt else None
    return out


if __name__ == "__main__":
    if "--run" in sys.argv:
        C.run_tasks(tasks())
    if "--summarize" in sys.argv:
        import json
        print(json.dumps(summarize(), indent=1))
