#!/usr/bin/env python3
"""Phase-0M Parts 34-38 -- the ETM coupling matrix, with FIRST-ORDER MAGNITUDES.

Every absent arrow is given a number before it is given a priority. "Probably negligible"
is not a finding; a ratio against the uncertainty already in the model is.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

# operating point (Phase-0F/0I 1 kW)
DT_CYCLE = 82.8604875 - 25.0
ALPHA_CU_R = 3.93e-3          # resistivity TCR, 1/K
CTE_CU = 16.66e-6
NU_CU = 0.34
A_DIE_M2 = 500e-6
Q_W = 1125.0
K_TIM, T_TIM_M = 3.0, 50e-6
H_TOP = 166000.0
K_SOLDER = 57.0
CROWD_SPREAD = 1.483 / 0.606   # measured K_crowd spread, Part 8


def m_to_e() -> list[dict]:
    rows = []
    # 1. elastic geometry change of a conductor
    eps = CTE_CU * DT_CYCLE
    dr_geom = eps * (1 + 2 * NU_CU)
    dr_rho = ALPHA_CU_R * DT_CYCLE
    rows.append(dict(
        mechanism="elastic deformation changes conductor geometry",
        quantity="dR/R", value=dr_geom,
        reference="dR/R from resistivity, which IS modelled", ref_value=dr_rho,
        ratio=dr_geom / dr_rho,
        verdict="NEGLIGIBLE",
        note=f"a free-expansion strain of {eps:.3e} changes R by {100*dr_geom:.3f} %, "
             f"against {100*dr_rho:.1f} % from rho(T) in the same excursion -- "
             f"{dr_rho/dr_geom:.0f}x smaller, and far below the "
             f"{CROWD_SPREAD:.1f}x spread in the crowding factor alone"))
    # 2. contact-pressure-dependent contact resistance
    rows.append(dict(
        mechanism="contact pressure changes contact resistance",
        quantity="applicability", value=0.0, reference="n/a", ref_value=0.0, ratio=0.0,
        verdict="NOT APPLICABLE (intact package)",
        note="every current-carrying interface in this package is metallurgical -- solder, "
             "IMC, plated Cu. There is no pressure contact in the power path. This arrow "
             "becomes real only for a socketed or clamped interface, which this "
             "architecture does not have"))
    # 3. crack area reduces conducting cross-section
    for area_loss in (0.05, 0.25, 0.50):
        rows.append(dict(
            mechanism="crack reduces conducting cross-section",
            quantity=f"dR/R at {100*area_loss:.0f} % joint area lost",
            value=area_loss / (1 - area_loss),
            reference="dR/R from resistivity", ref_value=dr_rho,
            ratio=(area_loss / (1 - area_loss)) / dr_rho,
            verdict="MATERIAL ONLY WITH DAMAGE",
            note="requires a damage model; zero in the intact package by construction"))
    # 4. electromigration / voiding
    rows.append(dict(
        mechanism="electromigration voiding changes resistance",
        quantity="applicability", value=float("nan"), reference="n/a",
        ref_value=float("nan"), ratio=float("nan"), verdict="OPEN -- NO DATA",
        note="the EM current-density limit itself is recorded OPEN in "
             "configs/phase0e/physical_stack.yaml; no primary source with its temperature, "
             "lifetime and geometry was retrievable. Cannot be estimated, must not be invented"))
    return rows


def m_to_t() -> list[dict]:
    rows = []
    r_tim = T_TIM_M / (K_TIM * A_DIE_M2)
    r_conv = 1.0 / (H_TOP * A_DIE_M2)
    r_tot = r_tim + r_conv
    for dbl_change in (0.02, 0.04, 0.10):
        dr = dbl_change * r_tim
        rows.append(dict(
            mechanism="warpage changes the TIM bond line",
            quantity=f"dT_j at {100*dbl_change:.0f} % bond-line change",
            value=Q_W * dr, reference="junction rise over the whole path",
            ref_value=Q_W * r_tot, ratio=dr / r_tot,
            verdict="SECOND ORDER BUT NOT ZERO",
            note=f"R_TIM = {r_tim:.5f} K/W is LARGER than the convective "
                 f"R = {r_conv:.5f} K/W at the calibrated h, so the compliant layer "
                 f"dominates the path and a small thickness change is not free"))
    rows.append(dict(
        mechanism="contact pressure changes interface thermal conductance",
        quantity="applicability", value=0.0, reference="n/a", ref_value=0.0, ratio=0.0,
        verdict="NOT APPLICABLE (intact package)",
        note="bonded interfaces throughout; no pressure contact in the heat path except "
             "the TIM, which is treated above as a bond-line thickness effect"))
    for frac in (0.05, 0.25):
        rows.append(dict(
            mechanism="delamination removes interface thermal conductance",
            quantity=f"local dT_j at {100*frac:.0f} % of the die area delaminated",
            value=Q_W * frac * r_tim / max(1 - frac, 1e-9),
            reference="junction rise over the whole path", ref_value=Q_W * r_tot,
            ratio=(frac * r_tim / max(1 - frac, 1e-9)) / r_tot,
            verdict="MATERIAL ONLY WITH DAMAGE", note="requires a cohesive-zone model"))
    return rows


def coupling_levels() -> list[dict]:
    return [
        dict(level="ETM-L1", definition="E <-> T -> M",
             description="electrical loss depends on temperature and temperature on loss, "
                         "iterated to a fixed point; the converged temperature field then "
                         "drives thermal strain. Mechanics does not feed back.",
             status="THE CURRENT FRAMEWORK",
             sufficient_for="architecture RANKING on electrical, thermal and relative "
                            "solder-fatigue response",
             insufficient_for="anything in which the mechanical state changes a conductance"),
        dict(level="ETM-L2", definition="E <-> T <-> M",
             description="the mechanical state updates electrical or thermal contact or "
                         "geometry and the loop is re-solved.",
             status="NOT BUILT",
             sufficient_for="packages with pressure contacts, sockets, or a "
                            "deformation-sensitive bond line",
             insufficient_for="failure progression"),
        dict(level="ETM-L3", definition="E <-> T <-> M <-> DAMAGE",
             description="damage evolves and feeds back into conductivity, thermal contact "
                         "and stiffness.",
             status="NOT BUILT",
             sufficient_for="predicting failure PROGRESSION, electrical opens, thermal "
                            "runaway after delamination",
             insufficient_for="--"),
    ]


def main() -> int:
    rows = ([{**r, "direction": "M->E"} for r in m_to_e()]
            + [{**r, "direction": "M->T"} for r in m_to_t()])
    k = sorted({x for r in rows for x in r})
    with open(OUT / "etm_feedback_magnitudes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    with open(OUT / "etm_coupling_levels.csv", "w", newline="") as fh:
        lv = coupling_levels()
        w = csv.DictWriter(fh, fieldnames=list(lv[0])); w.writeheader(); w.writerows(lv)
    for r in rows:
        print(f"  {r['direction']} {r['mechanism'][:46]:46s} {r['quantity'][:38]:38s} "
              f"{r['value']:.4g}  ratio={r['ratio']:.4g}  {r['verdict']}")
    print(f"wrote {OUT/'etm_feedback_magnitudes.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
