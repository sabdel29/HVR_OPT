#!/usr/bin/env python3
"""Append sections 4-13 to the full technical report (tables from source artifacts)."""
from __future__ import annotations
import csv, json, sys, textwrap
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RES = R / "results"
MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
FIGN = {"n": 1}   # figure 1 already used in the exec summary


def rd(p): return list(csv.DictReader((RES / p).open()))
def jd(p): return json.loads((RES / p).read_text())
def fl(v, n=3):
    try: return f"{float(v):.{n}f}"
    except (TypeError, ValueError): return str(v)


def tbl(hdr, body, src=None, align=None):
    a = align or ("l" + "r" * (len(hdr) - 1))
    out = ["| " + " | ".join(map(str, hdr)) + " |",
           "|" + "|".join({"l": ":--", "r": "--:", "c": ":-:"}[c] for c in a) + "|"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in body]
    if src: out += ["", f"Source: `{src}`"]
    return "\n".join(out) + "\n"


def figure(path, caption, phase, w="92%"):
    FIGN["n"] += 1
    return (f"\n![**Figure {FIGN['n']}.** {caption} *(Phase {phase}; data: `results/{path}`)*]"
            f"({RES/path}){{width={w}}}\n")


S = []
A = S.append

# ------------------------------------------------------------------ Phase 0B
A("\\newpage\n# Phase 0B --- First Mechanical Gate\n")
A("> **STATUS: HISTORICAL.** The mechanical machinery, mesh convergence and cooling calibration established here are still in use. The GEOMETRY is not: Phase 0F shows the 150 um tile and the 200/500 um substrates cannot contain the selected converter, so the absolute magnitudes in this chapter are superseded.\n")
A(textwrap.dedent("""\
**Question.** Does changing the DVPD architecture produce a mechanically *resolved* difference
--- larger than the numerical uncertainty --- at all?

**Implementation.** ANSYS was unavailable (S16.7), so the mechanical chain was built on
**CalculiX 2.23**: a graded structured hexahedral mesh conforming to every material boundary,
a steady-state thermal solve, and a Static Structural solve reading the temperature field
node-for-node on the *same* mesh, so the transfer carries zero interpolation error.
Silicon uses its cubic elastic tensor, not an isotropic approximation.

**Cooling was calibrated, not chosen.** The spec forbids picking a heat-transfer coefficient
because it looks reasonable, so $h_{top}$ was secant-solved until the reference architecture
reached the June-2026 cooled baseline junction temperature, then frozen for the entire study:
**17 521.6 W/m$^2$K**, achieving 83.514 $^\\circ$C against an 84 $^\\circ$C target (residual
$-0.49$ K).
"""))
conv = rd("phase0b/mesh_convergence.csv")
A("\n**Mesh convergence (C05, four graded levels).**\n\n")
A(tbl(["level", "elements", "T_max (°C)", "die warp (µm)", "pkg warp (µm)", "Si σ₁ p99 (MPa)"],
      [[r["level"], int(float(r["n_elems"])), fl(r["T_max_C"]), fl(r["die_warpage_pv_um"], 4),
        fl(r["pkg_warpage_pv_um"], 4), fl(r["si_principal_p99_MPa"])] for r in conv],
      src="results/phase0b/mesh_convergence.csv"))
A(textwrap.dedent("""
Final-step changes: die warpage **0.50 %**, package warpage 0.40 %, Si $\\sigma_1$ p99 4.43 %
--- all inside the acceptance targets (5 % / 10 %). Interface peel changed 19.24 % and
**failed**; it was withheld from every subsequent decision.

**Two solver findings that shaped everything after.** CalculiX's ITERATIVE CHOLESKY solver
disagreed with the direct solver by **35 % on package warpage** and was rejected. And the
C3D8I incompatible-mode element --- required because plain C3D8 shear-locks in bending ---
segfaults above ~40 k elements in this build. The mesh was therefore **graded** (fine at every
tile and die edge, coarse in the far field) with a hard guard that refuses to run above the
ceiling rather than silently falling back.
"""))
tc = rd("phase0b/three_case_comparison.csv")
A("\n**Result.**\n\n")
A(tbl(["metric", "C05 (4 distrib.)", "C07 (4 asym.)", "C13 (6 distrib.)", "S_m (%)", "2u_mesh (%)", "resolved"],
      [[r["metric"], r["C05"], r["C07"], r["C13"], r["S_m_pct"], r["u_mesh_pct"], r["resolved_vs_mesh"]]
       for r in tc], src="results/phase0b/three_case_comparison.csv"))
A(textwrap.dedent("""
**Verdict: GATE PASSED --- resolved mechanical signal.** Placement asymmetry changes die
warpage by **+60.6 %** against 0.50 % mesh uncertainty, and the ordering survives nine material
corners and both boundary-condition families.

**But the mechanism was not the expected one.** Regulator count, at constant footprint and
heat, changed die warpage by **+0.02 %**. The DVPD-specific variable the novelty argument
rested on was inert; the effect came entirely from placement, which is generic floorplanning.

Only die warpage was trusted. Interface shear and peel fell below twice their own uncertainty,
and the homogenised model's local stresses were later shown invalid (S11).
"""))
A(figure("phase0b/PHASE0B_DECISIVE_FIGURE_BC_A.png",
         "Phase-0B decisive figure. Identical converter heat and footprint; only placement "
         "differs. C05 and C13 are visually indistinguishable while C07's asymmetry produces a "
         "displaced warpage bowl.", "0B"))

# ------------------------------------------------------------------ Phase 0C
A("\\newpage\n# Phase 0C --- DVPD-Specific Mechanical Lever Gate\n")
A("> **STATUS: HISTORICAL.** The lever ranking and its robustness study stand as trends. The absolute magnitudes rest on the same unbuildable geometry corrected in Phase 0F.\n")
A(textwrap.dedent("""\
**Question.** Phase 0B proved mechanics responds to *placement* --- occupied territory. Does
any genuinely DVPD-specific variable produce a robust mechanical effect?

A frozen 20-case DOE (C01--C20) held the functional-die load at 240 W, total HVR heat at 42 W
and total HVR footprint at 96 mm$^2$, varying only count, placement, thickness, aspect ratio,
footprint and converter heat. Holding heat and footprint constant is what makes an $N_{VR}$
effect attributable to count rather than to more embedded material.
"""))
ve = rd("phase0c/variable_effects.csv")
A("\n**Variable-level effects, ranked by die-warpage response.**\n\n")
body = []
for r in sorted(ve, key=lambda x: -abs(float(x["die_warpage_pv_um_S_pct"]))):
    body.append([r["variable"], r["cases"], r["T_max_C_S_pct"], r["die_warpage_pv_um_S_pct"],
                 r["si_principal_p99_MPa_S_pct"], r["die_warpage_pv_um_band"],
                 "YES" if r["dvpd_specific"] == "True" else "generic"])
A(tbl(["variable", "cases", "ΔT_max %", "Δdie warp %", "ΔSi σ₁ %", "band", "DVPD?"], body,
      src="results/phase0c/variable_effects.csv"))
mech = jd("phase0c/mechanism_analysis.json")
sc = mech["thickness_scaling"]
A(textwrap.dedent(f"""
**Substrate thickness obeys a clean law.** Across three placement families,
$w_{{pv}} \\propto h_{{total}}^{{{sc['mean_exponent']:.3f} \\pm {sc['std_exponent']:.3f}}}$,
with the thickness effect identical to within
**{mech['interactions']['thickness_x_placement_family']['spread_pp']} percentage points** ---
i.e. no thickness x placement interaction. Two competing mechanisms explain the exponent:
plate stiffness grows as $D \\sim Eh^3$, while the fixed-thickness HVR/TSV inclusion sits
further from the shifted neutral axis so its thermal moment arm grows as $\\sim h$; net
$w \\sim h^{{-2}}$.

**Homogenisation validation (H0 vs H1).** The smeared TSV block was checked two ways: a
unit-cell numerical homogenisation (E, $\\nu$, $k$ within 0.5 %; **in-plane CTE off by
12.59 %**) and a package-scale discrete-inclusion model at equal copper volume. The
architectural spread was preserved to within **1.7 percentage points**, but local silicon
stress rose **+82 to +97 %** when the copper was resolved. **H0 is therefore valid for
architectural screening on warpage and invalid for local stress**, and no local-stress claim
is made anywhere in this project.

**Mechanism.** Die warpage correlates negatively with the inclusion field's polar second
moment ($r=-0.62$; spreading the inclusion lowers peak deflection) and positively with its
first moment ($r=+0.48$; asymmetry raises it). Shape-only anisotropy correlates at exactly
$r=0.000$ --- the quantitative statement of the aspect-ratio null. A three-descriptor physical
model reaches adjusted $R^2 = {mech['mechanism_fits']['I_polar + |M1| + A']['adj_r2']:.3f}$.
These are interpretation aids, not surrogates; no machine learning was trained.

**Verdict: DVPD-SPECIFIC MECHANICAL LEVER PROVEN** --- thickness ($-57$ %), footprint
($\\pm 21$ %) and converter loss ($\\pm 10.8$ %), with count and aspect ratio confirmed inert.
All results are BC-A (free warpage); under a board-restrained support every architecture
effect, DVPD-specific and generic alike, falls toward the numerical floor.
"""))
A(figure("phase0c/PHASE0C_DVPD_LEVER_FIGURE.png",
         "Phase-0C lever ranking. Red = DVPD-specific, blue = generic floorplanning, grey = "
         "below the materiality band. Substrate thickness is the largest DVPD-specific lever; "
         "VR count and aspect ratio are inert.", "0C"))

MD.write_text(MD.read_text() + "".join(S))
print(f"appended sections 4-5; now {len(MD.read_text().splitlines())} lines")
