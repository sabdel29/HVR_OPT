#!/usr/bin/env python3
"""Phase-0M-R3B Section 11 --- the report chapter, and demote its predecessor."""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"
BASE = R / "results" / "phase0mr3a" / "_baseline_phase0mr3"
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
TAG = "phase0mr3b_narrative"
FIG = R / "results" / "phase0mr3b" / "FIG_0MR3B_ls_to_L_cross_section.png"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def narrative() -> str:
    span = {r["edge"]: r for r in rd("vertical_span_correction.csv")}
    seg = rd("ls_to_L_layer_by_layer_geometry.csv")
    feas = rd("ls_to_L_feasibility.csv")
    dc = [r for r in rd("substrate_via_dc_validation.csv")
          if r["case"] != "control_uniform_bar"]
    tol = {r["d_um"]: r for r in rd("z2_tsv_sourced_tolerance_sweep.csv")}
    clr = rd("package_clearance_provenance.csv")
    cur = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv", BASE)}
    ls = span["ls_to_L"]
    dp = [r for r in feas if float(r["pitch_um"]) == 70.0
          and r["stack"] == "fully_stacked" and float(r["d_um"]) == 40.0][0]
    sourced_ok = [r for r in feas if float(r["pitch_um"]) >= 100.0
                  and r["stack"] == "semi_stacked" and r["feasible"] == "True"]
    conv = {}
    for r in dc:
        conv[r["case"]] = float(r["R_fv_ohm"]) / float(r["R_analytical_ohm"])
    z1, z2 = cur["Z1"], cur["Z2"]

    rows = []
    seen = set()
    for r in feas:
        k = (r["pitch_um"], r["stack"], r["d_um"])
        if k in seen:
            continue
        seen.add(k)
        rows.append(f"| {float(r['pitch_um']):.0f} um | {r['stack'].replace('_',' ')} | "
                    f"{float(r['d_um']):.0f} um | {r['n_required']} | {r['n_available']} | "
                    f"{float(r['routing_ratio']):.3f} | "
                    f"{'**yes**' if r['feasible']=='True' else 'no'} |")

    return f"""<!-- BEGIN GENERATED: {TAG} -->

\\newpage

# Phase 0M-R3B --- Substrate-Via Technology, Package Rules and Process Margin (current authoritative)

Phase 0M-R3A asked what technology spans the 673 um `ls_to_L` net. The span turned out to
be the artifact.

## The 673 um was measured through the middle of two components --- DEFECT #62

`build_edges()` addresses every component at its tier MID-PLANE, so the vertical link from
the low-side GaN switch to the inductor was measured centre-to-centre: a line through
303 um of GaN die body and 250 um of inductor body. Components are contacted at their
terminal faces. The build-up a via chain crosses is the gap between them.

| edge | I_rms | as modelled | physical | overstatement |
|---|---|---|---|---|
""" + "".join(
        f"| `{r['edge']}` | {float(r['i_rms_a']):.3f} A | "
        f"{float(r['modelled_span_um']):.1f} um | {float(r['physical_span_um']):.1f} um | "
        f"**{float(r['overstatement_x']):.2f}x** |\n" for r in span.values()) + f"""
The defect is systematic. `hs_to_ls` is the extreme case: two dies in adjacent tiers,
separated physically by one 10 um RDL, modelled as 655.5 um of copper.

`n_required = ceil(I / (J * A_cu))` contains no length, so **no Phase-0M-R3A count or ratio
changes**. What changes is the resistance, and what technology question is being asked.

![FIG-0MR3B]({FIG})

*Left: the modelled span against the physical one. Right: the 120 um resolved into the
three build-up layers the chain actually crosses.*

## The technology is ordinary. The design point is not.

A {ls['physical_span_um']} um stack through three build-up layers is embedded-component
packaging, and there is primary literature for it. Two sources were obtained in full text:

* **Ostmann et al., 2008** (Fraunhofer IZM / AT&S / IMEC-CMST). Contacts to embedded dies
  are laser-drilled, metallised microvias. Minimum **150 um I/O pad pitch in production**,
  100 um at prototype level, and *"for pitches smaller than 100 um ... vialess
  interconnection methods"* are indicated instead.
* **Cauwe et al., CEAS Space Journal 15:101-112 (2023)**. The qualified multi-level
  configuration is **two stacked microvias plus one staggered**, and *"Stacking three
  levels of microvias is considered a reliability risk."*

Phase 0M-R3 used r = 20 um at **70 um pitch** across **three** layers: finer than any
sourced pitch for this class, and one stacked level beyond the sourced qualification.

## The vias available were counted over the wrong area --- DEFECT #63

`edge_loss()` counts vias over 1.80 mm2, the gan_ls footprint. But the chain has to get
through the flying-capacitor layer, where two 2.00 mm2 embedded MLCCs leave **1.61 mm2**
free in a 5.61 mm2 cell. At the corrected area the Phase-0M-R3 design point gives
**{float(dp['routing_ratio']):.4f} > 1** and is infeasible before any sourcing question is
asked.

| pitch | stacking | d | n_req | n_avail | ratio | feasible |
|---|---|---|---|---|---|---|
""" + "".join(r + "\n" for r in rows) + f"""
**{len(sourced_ok)} configurations satisfy both sourced bounds.** Every feasible option
needs three fully stacked levels. The nearest sourced-legal option --- 150 um pitch,
120 um diameter, semi-stacked --- needs 1.71 mm2 against 1.61 mm2 available, short by
**6 %**. That is a repartitioning target, not a via-technology problem.

## The vertical path is 16 % more resistive than the series model

A 3-D DC solve of one physical column (microvia, land, microvia, land, microvia) returns
**{conv.get('via_chain_d120_pad180', 0):.3f}x** the analytical series resistance for a
120 um via and **{conv.get('via_chain_d70_pad110', 0):.3f}x** for a 70 um one, converged on
the two finest meshes. A plain copper-bar control returns `rho L / A` exactly. The penalty
is land spreading and is insensitive to diameter --- a measured correction for one
structure, not a global crowding multiplier.

## Clearances and TSV margin

One of the three clearances moves: an embedded die takes a 15-20 um dielectric cap
(Ostmann 2008), which lies inside the existing [10, 25, 50] um bound, so no corner moves.
**Two remain OPEN**, and they are no longer what blocks first.

No TSV manufacturing tolerance could be sourced from this host, so the question is
inverted: 30 um can absorb **0 %** symmetric tolerance before AR = 10 is violated, 32 um
**{float(tol['32.0']['max_absorbable_tolerance_pct']):.2f} %**, 34 um
**{float(tol['34.0']['max_absorbable_tolerance_pct']):.2f} %**, 36 um
**{float(tol['36.0']['max_absorbable_tolerance_pct']):.2f} %**. 32 um is
**parametrically margined, NOT process-qualified**.

## No ETM solve was rerun

The correction removes 1.110 W, 0.80 % of the electronics total, above the 0.5 % rerun
threshold. It was still not rerun, for a reason that is not about size: the change is
exactly common mode --- Z1 and Z2 share one converter cell, one template and one set of
currents --- and there is no corrected configuration to freeze, because none is realizable.
The physical spans are available behind `PHASE0MR3B_PHYSICAL_SPANS=1`, default off.

| | Z1 | Z2 |
|---|---|---|
| T_max | {float(z1['T_max_C']):.2f} C | **{float(z2['T_max_C']):.2f} C** |
| local fatigue-relevant inelastic response | {float(z1['response_driver_um']):.4f} um | **{float(z2['response_driver_um']):.4f} um** |

**D_driver = {float(z1['response_driver_um'])/float(z2['response_driver_um']):.4f}**,
carried for the Phase-0M-R3 configuration and not re-asserted for a corrected one.

## Verdict

**D --- THE PHYSICAL `ls_to_L` TOPOLOGY, EVALUATED AGAINST SOURCED SUBSTRATE-VIA RULES,
MAKES THE FROZEN Z1/Z2 PAIR NOT_REALIZABLE UNDER THE CURRENT COMPONENT TOPOLOGY.**

Both architectures share one converter cell, so it applies to both equally. The optimizer
remains **FORBIDDEN**, with `architecture templates realizable` downgraded from PARTIAL
back to NO.

<!-- END GENERATED: {TAG} -->
"""


def main() -> int:
    s = REP.read_text()
    done = []
    old = ("# Phase 0M-R3A --- Final State, Via-Technology and TSV-Margin Closure "
           "(current authoritative)")
    new = ("# Phase 0M-R3A --- Final State, Via-Technology and TSV-Margin Closure "
           "(superseded by Phase 0M-R3B)")
    if old in s:
        s = s.replace(old, new); done.append("Phase 0M-R3A -> historical")
    body = narrative()
    pat = rf"<!-- BEGIN GENERATED: {TAG} -->\n.*?<!-- END GENERATED: {TAG} -->\n"
    if re.search(pat, s, re.S):
        s = re.sub(pat, lambda _m: body, s, count=1, flags=re.S)
        done.append("chapter replaced")
    else:
        k = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
        s = s[:k] + body + "\n" + s[k:]
        done.append("chapter inserted")
    s = s.replace("## Current scientific status (Phase 0M-R3A)\n",
                  "## Current scientific status (Phase 0M-R3B)\n")
    REP.write_text(s)
    for d in done:
        print("  " + d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
