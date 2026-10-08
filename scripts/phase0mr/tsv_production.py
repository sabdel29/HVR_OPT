#!/usr/bin/env python3
"""Phase-0M-R Section 3 -- TSV geometry in production, with the three current densities
separated and the discrete count preserved.

PHASE-0M RESULT, RETAINED:
    R_single = rho(T) h / A_c ,   n_alloc ~ I / (J_design A_c)
    =>  R_field ~ rho(T) h J_design / I ,  the area cancels.

PHASE-0M WORDING, CORRECTED. The permitted conclusion is NOT "TSV radius is irrelevant". It is:

    the TSV cross-section is not an independent FIELD-LOSS lever under minimum-capability
    provisioning WHEN J_design is geometry-independent.

Three quantities that Phase 0M ran together are now separate, because conflating them is how
a process bound becomes an optimizer variable:

    J_design            what the design actually provisions to
    J_process_max       the manufacturing capability bound, if source-backed
    J_reliability_allow the EM/lifetime allowable -- OPEN, no primary source retrieved

`J_design <= J_process_max` is enforced. `J_process_max` is NEVER swept as a free variable:
it is a bound, and a design that moves it is a different technology, not a different design.
"""
from __future__ import annotations
import csv, math, sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / d))
from interconnect import TSVGeometry, rho_cu, K_CU, K_SI, K_SIO2           # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)

DIE_MM = 22.36
FOOT_M2 = (DIE_MM * 1e-3) ** 2
T_C = 85.0


class ProcessViolation(Exception):
    """J_design exceeds the process capability bound. Not clipped, raised."""


@dataclass(frozen=True)
class CurrentDensityBudget:
    """The three current densities, kept apart on purpose."""
    j_design: float
    j_process_max: float
    j_reliability_allow: float | None = None      # None == OPEN
    src_design: str = "DERIVED_FROM_SOURCE: June-2026 Table III provisioning"
    src_process: str = "DERIVED_FROM_SOURCE: ECTC-2024 Table I is the most aggressive " \
                       "density any source in this repository demonstrates"
    src_reliability: str = "OPEN -- no primary EM study with its T, t_life and geometry " \
                           "was retrievable; feasibility is a MAP over J, never a verdict"

    def check(self) -> None:
        if self.j_design > self.j_process_max * (1 + 1e-12):
            raise ProcessViolation(
                f"J_design = {self.j_design:.3e} exceeds J_process_max = "
                f"{self.j_process_max:.3e} A/m2. A process bound is not a design variable.")
        if (self.j_reliability_allow is not None
                and self.j_design > self.j_reliability_allow * (1 + 1e-12)):
            raise ProcessViolation(
                f"J_design = {self.j_design:.3e} exceeds J_reliability_allow = "
                f"{self.j_reliability_allow:.3e} A/m2.")

    @property
    def reliability_status(self) -> str:
        return "OPEN" if self.j_reliability_allow is None else "BOUNDED"


# the sourced envelope: June-2026 is what the reference design provisions to, ECTC-2024 is
# the most aggressive density any available source demonstrates
BUDGET = CurrentDensityBudget(j_design=1.0e8, j_process_max=4.0e8, j_reliability_allow=None)


def evaluate(g: TSVGeometry, current_a: float, budget: CurrentDensityBudget,
             footprint_m2: float = FOOT_M2, policy: str = "A_min_capability",
             pg_ratio: float = 0.5, n_fixed: int | None = None,
             t_c: float = T_C) -> dict:
    """One TSV field, with DISCRETE counts. ceil() and int() are never smoothed."""
    budget.check()
    rho = rho_cu(t_c)
    a_c = g.a_cu_m2
    i_max = budget.j_design * a_c
    n_req = max(1, math.ceil(abs(current_a) / i_max))          # DISCRETE
    n_avail = max(1, int(footprint_m2 * pg_ratio / g.pitch_m ** 2))   # DISCRETE
    if policy == "A_min_capability":
        n_alloc = n_req
    elif policy == "B_fixed_count":
        n_alloc = int(n_fixed if n_fixed else n_req)
    elif policy in ("C_fixed_pitch", "D_area_optimal"):
        n_alloc = n_avail
    else:
        raise ValueError(policy)
    r_single = rho * g.h_m / a_c
    r_field = r_single / max(n_alloc, 1)
    # the continuous idealisation, for comparison only -- never used in production
    n_cont = abs(current_a) / i_max if policy == "A_min_capability" else float(n_alloc)
    r_field_cont = r_single / max(n_cont, 1e-30)
    m = g.mech_eff(n_alloc, footprint_m2)
    area_used = n_alloc * g.pitch_m ** 2
    return {
        "r_drill_um": g.r_m * 1e6, "t_liner_um": g.t_liner_m * 1e6,
        "r_cu_um": g.r_cu_m * 1e6, "h_um": g.h_m * 1e6, "pitch_um": g.pitch_m * 1e6,
        "pitch_min_um": g.pitch_min_m * 1e6, "koz_ratio": g.koz_ratio,
        "aspect_ratio": g.aspect_ratio, "A_Cu_um2": a_c * 1e12,
        "policy": policy, "J_design": budget.j_design,
        "J_process_max": budget.j_process_max,
        "J_reliability_allow": ("OPEN" if budget.j_reliability_allow is None
                                else budget.j_reliability_allow),
        "I_max_per_via_mA": i_max * 1e3,
        "n_required": n_req, "n_available": n_avail, "n_allocated": n_alloc,
        "n_required_continuous": n_cont,
        "discrete_penalty_pct": 100.0 * (n_req - n_cont) / max(n_cont, 1e-30),
        "packing_utilisation": n_alloc / max(n_avail, 1),
        "area_used_frac": area_used / footprint_m2,
        "phi_cu": m["f_cu"], "k_z": m["k_z"], "k_xy": m["k_xy"],
        "E_xy_MPa": m["E_xy_MPa"], "CTE_eff": m["CTE_eff"],
        "R_single_mohm": r_single * 1e3, "R_field_mohm": r_field * 1e3,
        "R_field_continuous_mohm": r_field_cont * 1e3,
        "R_loop_mohm": 2 * r_field * 1e3,
        "IR_drop_mV": current_a * 2 * r_field * 1e3,
        "P_joule_W": current_a ** 2 * 2 * r_field,
        "J_actual": abs(current_a) / max(n_alloc * a_c, 1e-30),
        "feasible_count": n_req <= n_avail,
        "feasible_aspect": g.ar_ok, "feasible_pitch": g.pitch_legal,
        "feasible": (n_req <= n_avail) and g.ar_ok and g.pitch_legal,
        "binding": ("aspect_ratio" if not g.ar_ok else
                    "pitch_rule" if not g.pitch_legal else
                    "n_req>n_avail" if n_req > n_avail else "none"),
        "current_a": current_a,
    }


def sweep() -> list[dict]:
    rows = []
    cur = {"Z2_LV_1000A": 1000.0, "Z1_HV_23p4A": 23.434570678665168,
           "per_phase_6p8A": 6.802721088435374}
    radii = [2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5, 20.0, 25.0, 30.0, 40.0, 50.0]
    for label, I in cur.items():
        for h_um in (100.0, 300.0, 1300.0):
            for r_um in radii:
                for pol in ("A_min_capability", "B_fixed_count", "C_fixed_pitch"):
                    g = TSVGeometry(r_m=r_um * 1e-6, h_m=h_um * 1e-6)
                    try:
                        e = evaluate(g, I, BUDGET, policy=pol, n_fixed=15140)
                    except ProcessViolation as exc:
                        rows.append({"rail": label, "policy": pol, "r_drill_um": r_um,
                                     "h_um": h_um, "binding": f"PROCESS: {exc}"})
                        continue
                    e.update(rail=label, h_nominal_um=h_um)
                    rows.append(e)
    # liner sweep at fixed drilled radius: the liner is the only geometry term that does NOT
    # cancel, because it changes the copper fraction without changing the pitch
    for t_ox in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0):
        for r_um in (5.0, 15.0, 30.0):
            g = TSVGeometry(r_m=r_um * 1e-6, h_m=300e-6, t_liner_m=t_ox * 1e-6)
            e = evaluate(g, 1000.0, BUDGET, policy="C_fixed_pitch")
            e.update(rail="Z2_LV_1000A", h_nominal_um=300.0, policy="C_liner_sweep")
            rows.append(e)
    # keep-out sweep
    for koz in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0):
        for r_um in (5.0, 15.0, 30.0):
            g = TSVGeometry(r_m=r_um * 1e-6, h_m=300e-6, koz_ratio=koz)
            e = evaluate(g, 1000.0, BUDGET, policy="C_fixed_pitch")
            e.update(rail="Z2_LV_1000A", h_nominal_um=300.0, policy="C_koz_sweep")
            rows.append(e)
    return rows


def decision_relevance(rows) -> dict:
    """Where does the radius stop being irrelevant?"""
    a = [r for r in rows if r.get("policy") == "A_min_capability"
         and r.get("rail") == "Z2_LV_1000A" and r.get("h_nominal_um") == 300.0]
    feas = [r for r in a if r["feasible"]]
    infeas = [r for r in a if not r["feasible"]]
    rf = [r["R_field_mohm"] for r in a]
    disc = [abs(r["discrete_penalty_pct"]) for r in a]
    small = [r for r in a if r["n_required"] < 50]
    return {
        "R_field_spread_pct_all_radii": 100 * (max(rf) - min(rf)) / min(rf),
        "n_feasible": len(feas), "n_infeasible": len(infeas),
        "radius_range_feasible_um": (min(r["r_drill_um"] for r in feas),
                                     max(r["r_drill_um"] for r in feas)) if feas else None,
        "binding_constraints": sorted({r["binding"] for r in infeas}),
        "max_discrete_penalty_pct": max(disc),
        "discrete_penalty_at_small_n": max((abs(r["discrete_penalty_pct"]) for r in small),
                                           default=0.0),
        "n_required_at_small_n": [r["n_required"] for r in small],
    }


def main() -> int:
    rows = sweep()
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "tsv_geometry_production_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    d = decision_relevance(rows)
    for k, v in d.items():
        print(f"  {k:36s} {v}")
    # the process-bound guard must actually fire
    try:
        CurrentDensityBudget(j_design=5e8, j_process_max=4e8).check()
        print("  PROCESS GUARD DID NOT FIRE")
        return 1
    except ProcessViolation as e:
        print(f"  process guard fires: {str(e)[:90]}")
    print(f"wrote {OUT/'tsv_geometry_production_audit.csv'} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
