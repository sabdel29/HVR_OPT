#!/usr/bin/env python3
"""Phase-0M Parts 27-33 and 38 -- the missing-mechanics physics matrix and the model-addition gate.

Every row carries a MEASURED or DERIVED effect size where one could be obtained in this
phase, and says so plainly where one could not. "Probably matters" is not a classification.
"""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

# status: CURRENTLY MODELLED / PARTIALLY MODELLED / NOT MODELLED
# priority: P0 before architecture conclusions, P1 before absolute reliability,
#           P2 valuable refinement, P3 out of current scope
ROWS = [
    dict(id="A", physics="rate-independent solder plasticity",
         status="PARTIALLY MODELLED",
         detail="a *PLASTIC card exists but the selected model M1 sets sigma_y = 1e-6 MPa, "
                "so the response is pure overstress viscoplasticity with no rate-independent "
                "branch. The incumbent M0 had a full Chaboche card but was fitted in the "
                "wrong stress variable (DEFECT #40).",
         effect_size="NOT SEPARATELY IDENTIFIABLE. In a unified viscoplastic law there is no "
                     "distinct rate-independent part -- Anand and Norton both represent the "
                     "TOTAL inelastic strain. Adding a separate rate-independent term on top "
                     "would double-count.",
         parameters="available (Chaboche sigma0(T) from Yuan 2023 Table 10, SAC305)",
         validation="possible against the same tensile data",
         cost="none -- already in the solver",
         changes_ranking="NO -- it would change both architectures in the same direction; "
                         "the driver is upstream",
         priority="P2",
         verdict="LOW PRIORITY FOR CURRENT RANKING. Needed only if a life law is matched to "
                 "a model form that separates the two branches."),
    dict(id="B", physics="solder creep / unified viscoplasticity",
         status="CURRENTLY MODELLED",
         detail="*VISCO + *CREEP,LAW=NORTON overstress law; Anand can be parameterized but "
                "not integrated through the production solve above n = 9-10.",
         effect_size="dominant: 100 % of the modelled inelastic strain",
         parameters="Sn3.9Ag0.6Cu creep data over 7.51-15.92 MPa; SAC305 Anand (Yamin 2025)",
         validation="reproduces all 19 source points; 99.8 % of package damage is outside "
                    "the calibration window",
         cost="the whole local solve", changes_ranking="NO (ordering), YES (magnitude)",
         priority="P0", verdict="MODELLED; the high-stress domain remains the dominant blocker."),
    dict(id="C", physics="organic-substrate and board viscoelasticity",
         status="NOT MODELLED",
         detail="the board is linear elastic, E = 20 GPa, CTE 17 ppm/K, fixed. A laminate "
                "softens with temperature and relaxes over a 300 s dwell. The power "
                "substrate in this model is SILICON, so this is a BOARD and UNDERFILL "
                "question, not a substrate one.",
         effect_size="MEASURED IN THIS PHASE -- see polymer_modulus_screen.csv",
         parameters="a Prony series for the specific laminate is NOT sourced",
         validation="would need DMA data for the actual board",
         cost="moderate: *VISCO with a Prony series on one material",
         changes_ranking="see the measured ratio shift",
         priority="P1", verdict="see MISSING_MECHANICS_PHYSICS_AUDIT.md"),
    dict(id="D", physics="underfill / mold viscoelasticity",
         status="NOT MODELLED",
         detail="underfill is linear elastic, E = 8 GPa, PROVISIONAL. There is no mold "
                "compound in the model at all.",
         effect_size="MEASURED IN THIS PHASE for the modulus; the time dependence is not",
         parameters="not sourced", validation="would need DMA",
         cost="moderate", changes_ranking="see the measured ratio shift",
         priority="P1", verdict="see MISSING_MECHANICS_PHYSICS_AUDIT.md"),
    dict(id="E", physics="assembly / cure / reflow prestress",
         status="NOT MODELLED",
         detail="the operational model is stress-free at the cycle minimum. The real joint "
                "is stress-free near reflow, about 217 C.",
         effect_size="MEASURED IN THIS PHASE -- see assembly_prestress_test.csv",
         parameters="reflow profile is standard; the cure shrinkage of the underfill is not "
                    "sourced",
         validation="possible against warpage-versus-temperature measurements",
         cost="one extra step per solve",
         changes_ranking="see the measured ratio shift",
         priority="P1", verdict="see MISSING_MECHANICS_PHYSICS_AUDIT.md"),
    dict(id="F", physics="residual stress from process history",
         status="NOT MODELLED",
         detail="no plating, curing or singulation stress is carried.",
         effect_size="NOT ESTIMATED -- no process data exists in this repository",
         parameters="none available", validation="would need measurement",
         cost="high (a full process sequence)", changes_ranking="UNKNOWN",
         priority="P1",
         verdict="NEEDED FOR ABSOLUTE LIFE. Cannot be estimated from anything available."),
    dict(id="G", physics="moisture diffusion and hygroscopic swelling",
         status="NOT MODELLED",
         detail="no moisture field exists.",
         effect_size="OUT OF SCOPE at the declared mission",
         parameters="not sourced", validation="would need JEDEC MSL testing",
         cost="high (a second transport field)", changes_ranking="NO, at the declared scope",
         priority="P3",
         verdict="OUT OF CURRENT SCOPE. The publication claim is DRY STEADY OPERATING ETM, "
                 "stated explicitly. Moisture becomes P1 the moment humidity, storage or "
                 "MSL qualification enters the mission."),
    dict(id="H", physics="moisture-dependent modulus and adhesion",
         status="NOT MODELLED", detail="follows G.",
         effect_size="OUT OF SCOPE at the declared mission", parameters="not sourced",
         validation="--", cost="high", changes_ranking="NO, at the declared scope",
         priority="P3", verdict="OUT OF CURRENT SCOPE with G."),
    dict(id="I", physics="contact / sliding",
         status="NOT MODELLED",
         detail="every interface in the package is bonded; no pressure contact exists in "
                "either the power path or the heat path except the TIM bond line.",
         effect_size="ZERO for the intact package -- see etm_feedback_magnitudes.csv",
         parameters="n/a", validation="n/a", cost="high (nonlinear contact)",
         changes_ranking="NO", priority="P3",
         verdict="NOT APPLICABLE to this architecture. Would become P0 for a socketed or "
                 "clamped interface."),
    dict(id="J", physics="interface delamination / cohesive zone",
         status="NOT MODELLED",
         detail="named by the reference as one of three mechanisms; excluded since Phase 0C "
                "when the peel proxy failed convergence.",
         effect_size="25 % of the die delaminated is worth 12.5 K of junction rise "
                     "(etm_feedback_magnitudes.csv) -- large, but only once damage exists",
         parameters="traction-separation laws for these interfaces are NOT sourced",
         validation="would need interface fracture testing",
         cost="high", changes_ranking="UNKNOWN",
         priority="P1",
         verdict="NEEDED FOR FAILURE PROGRESSION AND FOR ABSOLUTE LIFE. The brief's own rule "
                 "applies: do not add cohesive zones until the failure mode and its material "
                 "parameters are sourced. They are not."),
    dict(id="K", physics="solder crack initiation and propagation",
         status="NOT MODELLED",
         detail="life is CORRELATED from an inelastic metric; no crack is propagated.",
         effect_size="the correlation ranks architectures without a crack; a crack is needed "
                     "only to predict crack PATH, area, or an electrical open",
         parameters="Paris-law constants for SAC305 are not sourced here",
         validation="would need cross-sectioning",
         cost="high", changes_ranking="NO for ranking",
         priority="P2",
         verdict="NOT NEEDED FOR RANKING. Needed if the framework must predict where and "
                 "when the joint opens rather than which architecture lasts longer."),
    dict(id="L", physics="TSV / RDL cracking or plasticity",
         status="NOT MODELLED",
         detail="the TSV region is a homogenized elastic block; the RDL is not in the "
                "mechanical mesh at all.",
         effect_size="NOT ESTIMATED. Phase 0M gives the RDL layer an anisotropic property "
                     "tensor for the first time, which is a prerequisite.",
         parameters="Cu fatigue data exists in the literature but was not retrieved here",
         validation="possible", cost="moderate",
         changes_ranking="PLAUSIBLY YES -- Z4 and Z5 load the RDL hardest",
         priority="P1",
         verdict="THE LARGEST UNMODELLED MECHANISM THAT COULD CHANGE RANKING. It is the one "
                 "the reference names and this project has never had."),
]


def main() -> int:
    with open(OUT / "PHYSICS_PRIORITY_MATRIX.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0])); w.writeheader(); w.writerows(ROWS)
    import collections
    c = collections.Counter(r["priority"] for r in ROWS)
    s = collections.Counter(r["status"] for r in ROWS)
    print("priority:", dict(sorted(c.items())))
    print("status:", dict(s))
    print(f"wrote {OUT/'PHYSICS_PRIORITY_MATRIX.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
