#!/usr/bin/env python3
"""Append the Phase-0F chapter. Runs after build_report_0e.py, before build_full_report4.py."""
from __future__ import annotations
import csv, json, re, sys, textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "results"
P0F = RES / "phase0f"
MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"

S: list[str] = []
A = S.append
F = lambda r, k: float(r[k])


def figure(path, caption, w="92%"):
    n = len(re.findall(r"!\[\*\*Figure ", MD.read_text())) + sum(
        1 for x in S if x.startswith("\n![**Figure")) + 1
    return (f"\n![**Figure {n}.** {caption} *(Phase 0F; data: `results/phase0f/`)*]"
            f"({P0F / path})" + "{width=" + w + "}\n")


def rd(n, feas=False):
    p = P0F / n
    if not p.exists():
        return None
    if p.suffix == ".json":
        return json.loads(p.read_text())
    out = list(csv.DictReader(open(p)))
    return [r for r in out if str(r.get("feasible")).lower() in ("true", "1")] if feas else out


cal = rd("cooling_1kw_calibration.json")
calsub = rd("cooling_1kw_calibration_substrate.json")
kw = rd("1kw_candidates.csv", True)
th = rd("thickness_crossover.csv")
fp = rd("footprint_1kw.csv")
pl = rd("placement_1kw.csv")
verd = rd("bcb_metric_verdicts.csv")
pairs = rd("bcb_pairs_1kw.csv")
eps = rd("mechanical_epsilon_sweep.csv")
geo = rd("geometry_recheck.csv")
tsv = rd("tsv_1kw_feasibility.csv")

A("\\newpage\n# Phase 0F --- 1-kW Reference-Scale ETM Gate (current authoritative)\n")
A(textwrap.dedent("""
Phase 0E closed the physical stack and concluded that the ETM novelty weakens. It also left
one question open that no amount of modelling at 240 W could answer: at 240 W every warpage
number is a few microns, so no mechanical constraint can bind and the question of whether
thermo-mechanics belongs inside DVPD synthesis is really a question about **scale**. Phase 0F
scales the validated model to the June 1 kW / 500 mm2 reference and asks it.

Two things had to be repaired before the question could even be posed.
"""))

A("## The geometry was not buildable\n")
A(textwrap.dedent("""
Phase 0E recorded that the selected converter contains a 500 um inductor while the mechanical
tile is 150 um, and added that this *"does not affect trends"*. That was an assumption, and
testing it is the first thing Phase 0F did.

The converter's cell needs **720 um** of substrate. A 200 um substrate cannot contain it under
any height bound, and a 500 um substrate cannot under the nominal or pessimistic bound.
**Both endpoints of the thickness sweep that produced "thicker is win/win/win" across four
phases are unbuildable with the converter that sweep assumed.** Under the most generous bound
a 500 um substrate does admit a converter, but the best one available costs 27.4 W per
regulator at 25 C against 4.2 W --- 6.4x worse. The realizable range starts near 800 um.
"""))
A(figure("FIG_0F_A_realizable_stack.png",
         "The height rule. Left: the converter cell must fit inside the substrate with a via "
         "field beneath it; the two thicknesses used in Phases 0B-0E cannot contain it. Right: "
         "how much of the inductor library each substrate thickness admits."))
if geo:
    sim = [g for g in geo if str(g.get("simulated")).lower() == "true"]
    gv = lambda t, k: next((F(x, k) for x in sim if x["case"] == t), float("nan"))
    A("Re-run on realizable geometry, the three decisive 240 W comparisons behave as follows:\n")
    A("| comparison | Phases 0B-0E (unbuildable) | Phase 0F (realizable) |")
    A("|---|---:|---:|")
    A(f"| thickness, thin -> thick | -56.5 % | **{100*(gv('real_thick','die_warpage_pv_um')-gv('real_thin','die_warpage_pv_um'))/gv('real_thin','die_warpage_pv_um'):+.1f} %** |")
    A(f"| footprint, small -> large | +87.9 % | **{100*(gv('real_large_fp','die_warpage_pv_um')-gv('real_small_fp','die_warpage_pv_um'))/gv('real_small_fp','die_warpage_pv_um'):+.1f} %** |")
    A(f"| placement, distributed -> edge | -41.5 % | **{100*(gv('real_edge','die_warpage_pv_um')-gv('real_dist','die_warpage_pv_um'))/gv('real_dist','die_warpage_pv_um'):+.1f} %** |")
    A("\nThe **directions all survive** and in fact strengthen. The Phase-0E remark was "
      "therefore half right --- but it was an assumption about a geometry that could not be "
      "built, and the magnitudes it produced were wrong by tens of percent.\n")

if cal:
    A("## The cooling boundary was not transferable\n")
    A(textwrap.dedent(f"""
    Phase 0B solved for h_top = 17 521.6 W/m2K so a ~282 W vehicle reached the June junction
    temperature. At 1 kW the package rejects four times the heat through the same die. Carrying
    that coefficient over would have put the package near 130 C instead of 84 C and overstated
    converter loss by roughly 25 W.

    Recalibrated against the June 1-kW reference (T_j,max = 84 C):
    **h_top = {cal['h_top_W_m2K']:,.0f} W/m2K, {cal['ratio_vs_phase0b']:.2f}x the Phase-0B
    value**, achieving {cal['achieved_T_max_C']:.2f} C.

    June actually cools with substrate-embedded micro-channels *adjacent to the GaN switch
    layer*. That topology was calibrated too and **cannot reach the target at all**: it
    flattens at {calsub['achieved_T_max_C']:.1f} C even at
    {calsub['h_top_W_m2K']:,.0f} W/m2K, because the die holds 1000 W of the ~1100 W total and
    sits on the far side of the package from the coolant. A 1-kW DVPD package cannot be cooled
    from the substrate side alone.
    """))
A(figure("FIG_0F_B_scaling_chain.png",
         "Every element of the 240 W vehicle had to be rebuilt for the 1-kW reference rather "
         "than scaled."))

if th:
    A("## The result: an architecture-dependent thickness conflict appears\n")
    A(textwrap.dedent("""
    Phase 0E found that ARCH_B's thickness margin was 1.46x against ARCH_A's 67.7x and
    predicted the sign would flip at scale. It does.
    """))
    A("| arch | h_sub (mm) | P_elec (W) | P_TSV (mW) | warpage (um) | |")
    A("|---|---:|---:|---:|---:|---|")
    for r in th:
        star = " <- electrical optimum" if r["is_electrical_optimum"] == "True" else ""
        A(f"| {r['arch']} | {F(r,'h_sub_mm'):.2f} | {F(r,'P_elec_total_w'):.3f} | "
          f"{F(r,'P_tsv_w')*1e3:.2f} | {F(r,'die_warpage_pv_um'):.3f} |{star} |")
    b = [r for r in th if r["arch"] == "ARCH_B"]
    i = next(k for k, r in enumerate(b) if r["is_electrical_optimum"] == "True")
    dP = F(b[-1], "P_elec_total_w") - F(b[i], "P_elec_total_w")
    dW = F(b[i], "die_warpage_pv_um") - F(b[-1], "die_warpage_pv_um")
    A(textwrap.dedent(f"""

    **ARCH_A's electrical optimum is the thickest substrate --- no conflict. ARCH_B's is
    INTERIOR, at h = {F(b[i],'h_sub_mm'):.2f} mm.** Its LV rail drives the whole output current
    through the substrate, so the TSV field loss grows fast enough with thickness to turn the
    electrical curve around while warpage keeps falling. That is a genuine three-domain
    conflict and it is architecture-specific.

    It is also nearly free. Overruling the electrical optimum to take the thickest substrate
    costs **{dP:+.4f} W** --- {100*dP/F(b[i],'P_elec_total_w'):.2f} % of system loss --- and
    buys **{dW:.3f} um**, an exchange rate of **{abs(dP/dW):.4f} W/um**. Set against the
    footprint lever's 12.9 W/um, this is a tradeoff no designer would deliberate over: they
    would simply thicken the substrate.
    """))
    A(figure("FIG_0F_C_thickness_margin.png",
             "The LV-TSV architecture develops an interior electrical optimum at 1 kW while "
             "the mechanical preference stays monotone. The conflict is real in sign and "
             "negligible in magnitude."))

if verd:
    q = [r for r in verd if r["QUALIFIED"] == "True"]
    A("## A mounted metric had to be qualified before it could be used\n")
    A(textwrap.dedent(f"""
    Phase 0E showed board restraint converts warpage into interface shear, but Phase 0B/0C had
    already found interface shear only marginally converged and material-sensitive. Using it
    without a dedicated study would have repeated the interface-peel mistake. So every
    candidate mounted metric was put through convergence (interface mesh 1/2/4) and robustness
    (nine material corners) before any mounted conclusion was drawn.

    **{len(q)} of {len(verd)} metrics qualify.** The two rejected are the p99 and p95
    percentiles of relative interface displacement: superbly converged, but their ordering
    flips between material corners.

    The important row is the first. **Free die warpage itself qualifies as a mounted metric at
    1 kW**, converging to 0.0 % and separating thin from thick by 72.3 % in the worst corner.
    At 240 W it did not: Phase 0E measured -56 % free collapsing to -0.14 % mounted, below the
    resolution floor. The difference is purely scale --- at 1 kW the residual mounted warpage
    stays far above the numerical floor.
    """))
    A(figure("FIG_0F_E_bcb_metric_qualification.png",
             "Qualifying a board-mounted metric: ordering stability across nine material "
             "corners, and convergence under interface refinement."))

pairs = rd("bcb_pairs_1kw.csv")
bcab = rd("bca_bcb_comparison.csv")
if bcab:
    A("## The assembly state decides the sign of the thickness lever\n")
    A(textwrap.dedent("""
    Phase 0E established that the discriminating mechanical response changes under board
    restraint. Phase 0F asks the sharper question at the reference scale: does the DIRECTION
    of the correct design move survive mounting? For the dominant lever it does not.
    """))
    A("| lever | BC-A free package | BC-B board-mounted | |")
    A("|---|---:|---:|---|")
    rowsx = [("thickness ARCH_A 0.8 -> 1.5 mm", "ARCH_A", "uniform", "49", "3.50", 0.8, 1.5),
             ("thickness ARCH_B 0.8 -> 2.0 mm", "ARCH_B", "uniform", "49", "3.50", 0.8, 2.0)]
    by = {(r["arch"], r["fam"], r["m_vr"], r["j"], r["h_sub_mm"]): r for r in bcab}
    for lab, arch, fam, m, j, h0, h1 in rowsx:
        a = by.get((arch, fam, m, j, f"{h0:.3f}")); b = by.get((arch, fam, m, j, f"{h1:.3f}"))
        if not (a and b):
            continue
        da = 100 * (F(b, "BCA_warpage_um") - F(a, "BCA_warpage_um")) / F(a, "BCA_warpage_um")
        db = 100 * (F(b, "BCB_warpage_um") - F(a, "BCB_warpage_um")) / F(a, "BCB_warpage_um")
        A(f"| {lab} | {da:+.2f} % | {db:+.2f} % | "
          f"{'**SIGN REVERSES**' if da*db < 0 else 'preserved'} |")
    fa = by.get(("ARCH_A", "uniform", "36", "3.00", "1.500"))
    fb = by.get(("ARCH_A", "uniform", "49", "3.00", "1.500"))
    if fa and fb:
        da = 100 * (F(fb, "BCA_warpage_um") - F(fa, "BCA_warpage_um")) / F(fa, "BCA_warpage_um")
        db = 100 * (F(fb, "BCB_warpage_um") - F(fa, "BCB_warpage_um")) / F(fa, "BCB_warpage_um")
        A(f"| footprint 259 -> 329 mm2 | {da:+.2f} % | {db:+.2f} % | "
          f"{'**SIGN REVERSES**' if da*db < 0 else 'preserved'} |")
    ua = by.get(("ARCH_A", "uniform", "49", "3.50", "1.500"))
    ca = by.get(("ARCH_A", "compact", "49", "3.50", "1.500"))
    if ua and ca:
        da = 100 * (F(ca, "BCA_warpage_um") - F(ua, "BCA_warpage_um")) / F(ua, "BCA_warpage_um")
        db = 100 * (F(ca, "BCB_warpage_um") - F(ua, "BCB_warpage_um")) / F(ua, "BCB_warpage_um")
        A(f"| placement uniform -> compact | {da:+.2f} % | {db:+.2f} % | "
          f"{'**SIGN REVERSES**' if da*db < 0 else 'preserved'} |")
    A(textwrap.dedent("""

    **Only thickness reverses.** Footprint and placement keep their sign in both states,
    merely compressed by the restraint. The reversal is specific to the one lever that acts
    through the substrate's bending stiffness -- exactly the quantity a board foundation
    overrides. A thicker substrate resists bending when it is free and transmits more
    differential deformation into the die when it is held flat.

    This is the Phase-0F verdict in one sentence: **the mechanical preference for substrate
    thickness is not a property of the design, it is a property of the design and its assembly
    state.** A DVPD framework that optimises free-package warpage and then mounts the result
    will move the substrate thickness the wrong way.
    """))
    A(figure("FIG_0F_D_footprint_free_vs_mounted.png",
             "Footprint response in both assembly states at 1 kW. Unlike thickness, the "
             "footprint opposition keeps its sign when the package is mounted."))

A("## Verdict\n")
A("```\nASSEMBLY-STATE-DEPENDENT ETM CONSTRAINT\n```\n")
A(textwrap.dedent("""
Warpage grew fourfold at the reference scale, and growth alone does not license a positive
verdict. What does is that the mechanical and electrical preferences change places depending
on how the package is mounted, in a signal that is qualified rather than noise.

Mechanics is **not** a synthesis constraint at 1 kW: nothing binds, because no source-backed
criterion exists, and in the free state the mechanical improvement costs 0.016 W/um -- a
tradeoff no designer would deliberate. But it is **not** merely a signoff quantity either,
because the direction of the correct thickness move depends on an assembly-state choice that
an electrical/thermal framework does not represent at all.

What would settle it is a calibrated board foundation -- the BC-B stiffness is still
PROVISIONAL and the entire reversal rests on it -- and one source-backed mechanical criterion,
which would let the epsilon band 1.27-3.04 um be turned into a real feasibility statement.
"""))
A(figure("FIG_0F_H_crossover_map.png",
         "Where mechanics becomes decision-relevant. Left: at 1 kW mechanics improves ~90 % "
         "across the realizable thickness range while electrics move under 0.15 %. Right: the "
         "cost of buying mechanics, against the Phase-0E levers at 240 W."))

MD.write_text(MD.read_text() + "".join(x if x.endswith("\n") else x + "\n" for x in S))
print(f"appended Phase-0F chapter; now {len(MD.read_text().splitlines())} lines")
