#!/usr/bin/env python3
"""Phase-0L Part V -- audit of the original 19-point Norton fit in solder_model.py.

Establishes, from the source of the fit rather than from prose:
  * which variable the regression was performed in;
  * which variable the solver consumes (Part III: the overstress);
  * the quality of the fit in its own variable;
  * what the solver actually does when handed the resulting card at the calibration points.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402

# Provenance established in Part V by retrieving the cited paper itself
# (PMC10381129 / Europe PMC full-text XML, cached under results/phase0l/lit/).
# Yuan 2023 has ELEVEN tables; there is no Table 26.  The 19 points are its Table 5, and
# Yuan section 4.1 states "The experimental dataset is drawn from Xiao and Armstrong [10]",
# whose title is "Tensile creep and microstructural characterization of bulk Sn3.9Ag0.6Cu
# lead-free solder".
SRC_TABLE = "Yuan 2023, Materials 16(14):4922, Table 5"
SRC_PRIMARY = ("Xiao & Armstrong 2005, J. Electron. Mater. 34:196-211, "
               "doi:10.1007/s11664-005-0233-z")
SRC_ALLOY = "Sn3.9Ag0.6Cu"
STRESS_DEF = "total applied uniaxial stress (constant-load tensile creep test)"
RATE_DEF = "steady-state plastic strain rate; Yuan Table 5 column is in units of 1e-9 1/s"

rows = []
for (T, sig, edot) in sm.CREEP_DATA:
    f = sm.fit_norton_data(T)
    A, n = f["A"], f["n"]
    y0 = sm.sigma0_of_T(T)
    over = sig - y0
    rows.append({
        "T_C": T, "sigma_applied_MPa": sig, "edot_measured_1_per_s": edot,
        "A_fitted": A, "n_fitted": n,
        "edot_fit_in_sigma_applied": A * sig ** n,
        "resid_pct_in_sigma_applied": 100.0 * (A * sig ** n - edot) / edot,
        "sigma_y0_MPa": y0, "overstress_MPa": over,
        "edot_solver_would_give": A * over ** n if over > 0 else 0.0,
        "solver_over_measured": (A * over ** n / edot) if over > 0 else 0.0,
        "source_table": SRC_TABLE, "source_primary": SRC_PRIMARY,
        "source_alloy": SRC_ALLOY, "stress_definition": STRESS_DEF,
        "rate_definition": RATE_DEF,
        "fit_variable": "sigma_applied (no yield subtraction)",
        "solver_variable": "sigma_vm - sigma_y(eps_in)",
        "variables_match": False,
    })

out = R / "results" / "phase0l" / "original_19point_fit.csv"
with out.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print(f"{'T':>5} {'sigma':>7} {'edot meas':>11} {'edot fit':>11} {'res%':>7} "
      f"{'sig_y0':>7} {'overstr':>8} {'solver edot':>12} {'solver/meas':>12}")
for r in rows:
    print(f"{r['T_C']:5.0f} {r['sigma_applied_MPa']:7.2f} {r['edot_measured_1_per_s']:11.3e} "
          f"{r['edot_fit_in_sigma_applied']:11.3e} {r['resid_pct_in_sigma_applied']:+7.1f} "
          f"{r['sigma_y0_MPa']:7.2f} {r['overstress_MPa']:+8.2f} "
          f"{r['edot_solver_would_give']:12.3e} {r['solver_over_measured']:12.3e}")

neg = [r for r in rows if r["overstress_MPa"] <= 0]
pos = [r for r in rows if r["overstress_MPa"] > 0]
print()
print(f"points with NON-POSITIVE overstress (solver gives exactly zero creep): "
      f"{len(neg)} of {len(rows)}")
print(f"points with positive overstress: {len(pos)}; solver/measured ratios: "
      + ", ".join(f"{r['solver_over_measured']:.2e}" for r in pos))
print()
errs = [abs(r["resid_pct_in_sigma_applied"]) for r in rows]
print(f"fit quality IN ITS OWN VARIABLE (sigma_applied): max {max(errs):.1f} %, "
      f"rms {math.sqrt(sum(e*e for e in errs)/len(errs)):.1f} %")
print(f"fit quality IN THE SOLVER'S VARIABLE            : undefined -- "
      f"{len(neg)}/{len(rows)} points predict identically zero")
print(f"\nwrote {out}")
print()
print(f"source table      : {SRC_TABLE}")
print(f"primary source    : {SRC_PRIMARY}")
print(f"alloy MEASURED    : {SRC_ALLOY}   <-- NOT SAC305 (Sn3.0Ag0.5Cu)")
print(f"stress definition : {STRESS_DEF}")
print(f"fit variable      : sigma_applied (no yield subtraction)")
print(f"solver variable   : sigma_vm - sigma_y(eps_in)")
print(f"variables match   : NO  -> DEFECT #40 CONFIRMED")
