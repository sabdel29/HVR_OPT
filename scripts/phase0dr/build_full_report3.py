#!/usr/bin/env python3
"""Append Phase 0D, Phase 0D-R, equations and validation sections."""
from __future__ import annotations
import csv, json, textwrap
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RES = R / "results"
MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
FIGN = {"n": 3}


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


S, A = [], None
S = []
A = S.append

# ------------------------------------------------------------------ Phase 0D
A("\\newpage\n# Phase 0D --- First Electrical Coupling\n")
A("> **STATUS: SUPERSEDED.** Every quantitative result in this chapter was overturned by the "
  "Phase-0D-R current-path correction and again by the Phase-0E stack closure. It is retained "
  "because the corrections are only intelligible against what they replaced. For the current "
  "authoritative values see the Phase-0E and Phase-0F chapters.\n")
A(textwrap.dedent("""\
**Question.** Does including mechanics change which architecture is preferred, relative to an
electrical/thermal-only design?

Phase 0C had left the strongest mechanical lever, substrate thickness, with **no path into the
electrical objective**: the PDN model carried two hard-coded floats, `r_bump_ohm = 0.08 m`$\\Omega$
and `r_tsv_ohm = 0.04 m`$\\Omega$, with no diameter, height, pitch or count. Closing that was
the critical-path task.

**What was built.** A geometry-derived TSV model $R = \\rho(T)h/A$ with parallel-count sizing,
validated against June Table III to **+1.62 %**; temperature dependence for GaN $R_{DS(on)}$,
inductor DCR and copper resistivity; and an electrical--thermal fixed point with the validated
FE thermal model inside the loop, converging in 4--5 iterations with energy balance
$\\pm 0.000$ %.

**A defect found by running the objective.** The upstream lateral resistance default,
`rho_mohm_per_mm = 50`, is unphysical: it puts ~2100 % IR drop on a 1 V / 60 A branch and drove
one fixed point to 569 $^\\circ$C. It was replaced by a first-order geometry-derived plane
resistance, $R/\\mathrm{mm} = \\rho/(t_{Cu}W_{eff}) = 0.155$ m$\\Omega$/mm. **Phase 0D-R shows
that replacement was still wrong**, for a different reason (S7).
"""))
rev0d = jd("phase0d/reversal_analysis.json")
cc = rd("phase0d/coupled_candidates.csv")
feas = [r for r in cc if r.get("converged") == "True"]
feas.sort(key=lambda r: float(r["p_elec_total_w"]))
A("\n**Phase-0D ETM Pareto set (6 members).**\n\n")
body = []
for c in rev0d["etm_pareto"]:
    r = next(x for x in feas if x["cand"] == c)
    body.append([c, int(float(r["n_vr"])), r["j_target"], f"{float(r['h_sub_mm'])*1000:.0f}",
                 r["placement"], fl(r["p_elec_total_w"], 2), fl(r["T_max_C"], 2),
                 fl(r["die_warpage_pv_um"])])
A(tbl(["candidate", "N", "J", "h_sub (µm)", "placement", "P_elec (W)", "T_max (°C)", "warpage (µm)"],
      body, src="results/phase0d/coupled_candidates.csv"))
A(textwrap.dedent("""
**Phase-0D conclusions, as reported at the time:** substrate thickness improves all three
domains ($-0.62$ % electrical, $-2.83$ K, $-57$ % warpage); HVR footprint is a genuine
opposition; and *placement is nearly free electrically (1.08 % spread) while spanning 240 % in
warpage*, so mechanics decides what electrical analysis cannot. The ETM front expanded from 1
architecture to 6, at an exchange rate of 2.03 W/um.

**Why "conditional reversal" was the wrong label.** With warpage entering as a *pure additional
objective*, the minimum-loss design holds minimum $P_{elec}$ by construction and therefore
**can never be Pareto-dominated**. What Phase 0D observed was a **Pareto-front expansion**
priced by an unsourced scalar exchange rate --- not a reversal in any decision-theoretic sense.
Phase 0D-R adopts the stricter terminology throughout.
"""))
A(figure("phase0d/PHASE0D_ET_VS_ETM_PARETO.png",
         "Phase-0D ET vs ETM Pareto fronts. Superseded by Figure 7: the lateral RDL model "
         "underlying these electrical values was wrong by ~65x.", "0D"))

# ------------------------------------------------------------------ Phase 0D-R
A("\\newpage\n# Phase 0D-R --- Architecture-Aware Correction\n")
A("> **STATUS: SUPERSEDED for all magnitudes; its structural corrections stand.** The "
  "rail-aware power path, the ground return and the hard feasibility gate introduced here are "
  "still in force. Its numbers are not: the RDL stack was unsourced (Phase 0E: 5.56x too "
  "resistive), the placement spread of 188.8 % becomes 46.7 %, the exchange rate of 16.2 W/um "
  "becomes 11.48 W/um, and the ARCH_B infeasibility verdict is withdrawn. Values below are "
  "**historical**.\n")
A(textwrap.dedent("""\
**This section supersedes Section 6 wherever they disagree.**

Phase 0D applied a *global* rule --- the thickness-dependent TSV carries converter input
current. That is a property of one stack ordering, not of DVPD. Three architectures were
therefore traced segment by segment.
"""))
A(figure("phase0dr/FIG_A_power_paths.png",
         "Architecture-aware power paths. Which rail traverses each interconnect is set by "
         "where conversion sits in the stack. The Phase-0D assumption is correct for ARCH_A "
         "and wrong for ARCH_B.", "0D-R"))
A(textwrap.dedent("""
**Rail-aware currents.** At 60 A/VR, 48 -> 1 V, $P_{conv}\\approx5$ W: the LV rail carries
60.0 A and the HV rail 1.354 A --- a factor **44.3**, hence about **1960x** in $I^2R$ for an
identical segment. Which side of the converter a segment sits on is the single most important
electrical fact about it.

**Interconnect library.** Every tier is modelled separately with its own geometry, material,
temperature dependence and **cross-section shape**. Validating against June Table III recovered
a detail worth stating: BGA (125 663 um$^2$) and TSV (707 um$^2$) are **circular**, but the
chiplet pad's 100 um$^2$ is a **square** 10x10 um. Assuming it circular would overstate that
tier by 27 %; the square reproduces June's 1.7 m$\\Omega$ **exactly**.
"""))
A(tbl(["tier", "shape", "model R (20 °C)", "June Table III", "error", "status"],
      [["BGA", "circular", "0.3104 mΩ", "0.3 mΩ", "+3.45 %", "SOURCE_BACKED"],
       ["TSV @300 µm", "circular", "7.2150 mΩ", "7.1 mΩ", "+1.62 %", "SOURCE_BACKED"],
       ["micro-bump", "**square**", "**1.7000 mΩ**", "1.7 mΩ", "**−0.00 %**", "SOURCE_BACKED"],
       ["C4", "circular", "1.1586 mΩ", "absent", "—", "ASSUMPTION"],
       ["RDL", "2-D sheet", "5.667 mΩ/sq", "absent", "—", "ASSUMPTION"]],
      src="configs/phase0dr/power_path_graphs.yaml"))
A(textwrap.dedent("""
**Ground return.** Phase 0D modelled supply only. $R_{loop}=R_{supply}+R_{ground}$; modelled
symmetric, so **every Phase-0D interconnect loss was understated by 2x**.

**Feasibility is now a hard gate.** $n_{req}=\\lceil I/I_{max}\\rceil$; if it exceeds what the
pitch allows in the footprint the architecture is INFEASIBLE, never clipped with `min()`. This
immediately produces an architecture-dependent result: at the conservative per-via limit
(4.8 mA) **ARCH_B needs 12 501 vias where the tile holds 6 666 and is not buildable**, while
ARCH_A remains feasible.

## The dominant correction: the RDL model

Phase 0D's $R/\\mathrm{mm} = \\rho/(t_{Cu}W_{die})$ inside a parallel-branch network gives every
source--load pair its own full-die-width conductor and no current sharing. It was replaced by a
**2-D resistive sheet**, $\\nabla\\!\\cdot\\!(\\sigma_s\\nabla V) = -J$ with
$\\sigma_s = t_{Cu}\\,\\mathrm{occ}/\\rho(T)$, sources injecting over the tile footprint and loads
extracting over each POL segment.

Two numerical points materially affect the answer. A **point** source in a 2-D sheet is
logarithmically singular, so point injection overstates the loss by **776 %**; a real VR injects
over its footprint. And assigning a footprint to the nearest grid cell destroys convergence ---
**exact cell-overlap area weighting** was required, after which the solve converges to
$\\le 0.72$ % over $n=41\\to121$.
"""))
rv = jd("phase0dr/rdl_validation.json")
best = min(rv["fd_grid_study"].values(), key=lambda x: x["err_P_pct"])
A("\n**Independent validation against MOOSE** (DC conduction and heat conduction are the same "
  "operator, $\\nabla\\!\\cdot\\!\\sigma\\nabla V \\equiv \\nabla\\!\\cdot\\!k\\nabla T$):\n\n")
A(tbl(["check", "reference", "this model", "agreement"],
      [["analytic uniform-strip conductance", "173.0704 S", "MOOSE 173.0704 S", "5.8e-12 %"],
       ["distributed 4-source / 100-load sheet dissipation",
        f"MOOSE {rv['moose']['P_supply_w']:.4f} W", f"FD {best['P_fd']:.4f} W",
        f"**{best['err_P_pct']:.2f} %**"],
       ["peak potential", f"{rv['moose']['Vmax']:.5f} V", f"{best['vmax_fd']:.5f} V",
        f"{best['err_v_pct']:.2f} %"]],
      src="results/phase0dr/rdl_validation.json"))
A(textwrap.dedent("""
**Consequence.** Lateral RDL loss rises from 0.17 W to **12.13 W** (best placement) and
**73.00 W** (worst) --- a 71x to 365x correction. Package distribution is **37--77 %** of total
electrical loss, not 0.25--1.15 %. Lateral RDL, not the TSV, is the dominant term.
"""))
cor = rd("phase0dr/coupled_candidates_corrected.csv")


def pick(**kw):
    for r in cor:
        if all(str(r[k]) == str(v) for k, v in kw.items()):
            return r


A("\n## Placement re-audit --- a Phase-0D claim withdrawn\n\n"
  "Identical converter, footprint and thickness; only placement differs.\n\n")
body = []
for fam in ("distributed", "edge", "compact", "asymmetric"):
    r = pick(fam=fam, arch="ARCH_A", j="2.0", h_sub_mm="0.5")
    body.append([r["placement"], fl(r["P_rdl_w"], 2), fl(r["P_elec_total_w"], 2),
                 fl(r["efficiency_pct"], 2), fl(r["T_max_C"], 2), fl(r["die_warpage_pv_um"])])
A(tbl(["placement", "P_RDL (W)", "P_elec (W)", "η (%)", "T_max (°C)", "warpage (µm)"], body,
      src="results/phase0dr/coupled_candidates_corrected.csv"))
A(textwrap.dedent("""
The electrical spread across placements is **188.8 %**, not 1.08 %. **"ET is blind to
placement" is withdrawn.** The electrical objective discriminates placement strongly and
largely *agrees* with mechanics --- compact and asymmetric are bad on both counts and are
Pareto-dominated. The one genuine disagreement, distributed (electrically best) versus
edge-biased (mechanically best), now costs **+24.45 W (+75 %) for -1.157 um (-39 %) =
21.1 W/um**.

## Thickness re-audit --- the decisive architecture test
"""))
body = []
for arch in ("ARCH_A", "ARCH_B"):
    for h in ("0.2", "0.5"):
        r = pick(fam="distributed", arch=arch, j="2.0", h_sub_mm=h)
        body.append([arch, "48 V" if arch == "ARCH_A" else "**1 V**",
                     f"{float(h)*1000:.0f}", f"{float(r['P_tsv_w'])*1e3:.2f}",
                     fl(r["P_rdl_w"], 2), fl(r["P_elec_total_w"], 2), fl(r["efficiency_pct"], 2),
                     fl(r["T_max_C"], 2), fl(r["die_warpage_pv_um"])])
A(tbl(["arch", "TSV rail", "h_sub (µm)", "P_TSV (mW)", "P_RDL (W)", "P_elec (W)", "η (%)",
       "T_max (°C)", "warpage (µm)"], body,
      src="results/phase0dr/coupled_candidates_corrected.csv"))
A(textwrap.dedent("""
**The hypothesis this phase was built to test is NOT confirmed.** The LV-rail TSV penalty is
**45x larger** than the HV-rail one (+34.2 vs +0.76 mW), exactly as the rail argument predicts
--- but it stays an order of magnitude below the thermal benefit, so total electrical loss
still *falls* with thickness in **both** architectures. The reason is structural: sizing vias by
current density makes $P_{TSV} = I\\rho h I_{via,max}/A$, **linear** in current rather than
quadratic, so provisioning enough vias caps the penalty.

Architecture-dependence appears in **feasibility**, not in the loss tradeoff.
"""))
A(figure("phase0dr/FIG_C_hv_lv_thickness.png",
         "HV-TSV vs LV-TSV thickness chain. The LV penalty is 45x larger yet total electrical "
         "loss still falls with thickness in both architectures.", "0D-R"))
A(figure("phase0dr/FIG_B_loss_decomposition.png",
         "Interconnect loss decomposition. Lateral RDL, not the TSV, dominates; per-tier losses "
         "span five decades.", "0D-R"))
A(figure("phase0dr/FIG_F_footprint.png",
         "Footprint tradeoff after the PPDN correction. Larger footprint now improves converter "
         "loss, RDL spreading loss and temperature while worsening warpage.", "0D-R"))
A(figure("phase0dr/FIG_G_pareto_corrected.png",
         "Corrected ET vs ETM Pareto. ET front is a single point; the ETM front has four "
         "members, all at h_sub = 500 um. The mechanical option costs 16.2 W/um, 8x the "
         "Phase-0D estimate.", "0D-R", w="72%"))
rc = jd("phase0dr/reversal_corrected.json")
A(textwrap.dedent(f"""
## Corrected rankings

**ET Pareto front: a single point** --- `{rc['et_best']}`, which simultaneously minimises loss
and temperature. **ETM Pareto front: {len(rc['etm_pareto'])} members, all at $h_{{sub}}=500$ um.**

Moving from the ET optimum to the minimum-warpage design costs
**+32.07 W (+127.7 %) for -1.985 um (-51.8 %) = {rc['tradeoff_W_per_um']:.1f} W/um** ---
**{rc['ratio']:.1f}x more expensive** than Phase 0D's 2.03 W/um.

**Verdict: PHASE-0D CONCLUSION CHANGED BY CURRENT-PATH AND PPDN CORRECTION.** In the stricter
terminology: **ROBUST ETM PARETO TRADEOFF, NO UNIQUE REVERSAL.**
"""))

MD.write_text(MD.read_text() + "".join(S))
print(f"appended sections 6-7; now {len(MD.read_text().splitlines())} lines")
