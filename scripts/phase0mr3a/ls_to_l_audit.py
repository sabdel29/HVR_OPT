#!/usr/bin/env python3
"""Phase-0M-R3A Section 4 --- what fabrication technology IS `ls_to_L`?

Phase 0M-R3 repaired the binding route by raising its via radius from 15 to 20 um and
justified 20 um as "inside the sourced range design_variables.tsv.radius_m". That range
governs THROUGH-SILICON VIAS. This module traces the net to its physical endpoints and
asks whether a TSV rule governs it at all.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0f",
          "scripts/phase0m", "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))

import routing_production as RP                                          # noqa: E402
OUT = R / "results" / "phase0mr3a"
DS = yaml.safe_load((R / "configs/phase0m/interconnect_design_space.yaml").read_text())


def main() -> int:
    tpl = "T1_EMBEDDED_4LAYER"
    e = next(x for x in RP.build_edges(tpl) if x.name == "ls_to_L")
    zs = RP.tier_z(tpl)
    t_src, t_dst = e.tiers

    rows = [
        {"step": "1 logical net", "value": "ls_to_L",
         "detail": "low-side switch node to inductor terminal",
         "source": "routing_production.build_edges", "provenance": "MODEL"},
        {"step": "2 physical endpoints", "value": f"{e.src} -> {e.dst}",
         "detail": f"tier {t_src} to tier {t_dst} of {tpl}",
         "source": "routing_production.TEMPLATES", "provenance": "MODEL"},
        {"step": "3 z span", "value": f"{e.length_mm*1e3:.0f} um",
         "detail": f"mid-plane {zs[t_src]:.1f} um to {zs[t_dst]:.1f} um, crossing the "
                   f"flying-capacitor tier",
         "source": "routing_production.tier_z", "provenance": "DERIVED"},
        {"step": "4 medium crossed", "value": "substrate power layers",
         "detail": "June-2026 Sec. II: low-side switches (bottom layer), flying capacitors "
                   "(middle layer) and inductors (top layer) are EMBEDDED WITHIN THE "
                   "SUBSEQUENT SUBSTRATE POWER LAYERS. The connection runs between "
                   "embedded-component layers, inside the cell.",
         "source": "June-2026 Sec. II via scripts/phase0f/geometry.py docstring",
         "provenance": "SOURCE_BACKED"},
        {"step": "5 is it the TSV field?", "value": "NO",
         "detail": "the framework states the TSV field 'runs BENEATH it from the substrate "
                   "underside'. For ARCH_Z1 that field spans h_sub - t_cell = 74 um; this "
                   "net spans 673 um in the opposite region of the stack. Two distinct "
                   "structures.",
         "source": "scripts/phase0f/geometry.py; configs/phase0mr2/architecture_geometry.yaml",
         "provenance": "SOURCE_BACKED"},
        {"step": "6 fabrication technology", "value": "INTRA-CONVERTER VERTICAL INTERCONNECT",
         "detail": "a stacked via through the embedded-component build-up layers of the "
                   "power substrate. Not a through-silicon via, not an RDL trace, not a "
                   "bump. Closest named class: package-substrate / stacked microvia.",
         "source": "classified in this phase from steps 4 and 5", "provenance": "DERIVED"},
        {"step": "7 sourced geometry rule for that class", "value": "NONE",
         "detail": "the design space holds tsv.* (through-silicon), rdl.* (trace width and "
                   "space only, no via), and bump.{bga,c4,microbump} (bumps, not vias "
                   "through dielectric). No entry governs a stacked via through substrate "
                   "power layers.",
         "source": "configs/phase0m/interconnect_design_space.yaml", "provenance": "OPEN"},
        {"step": "8 rule Phase 0M-R3 applied", "value": "tsv.radius_m {2.5, 15, 50} um",
         "detail": "a THROUGH-SILICON VIA range applied to a package-substrate via. The "
                   "two technologies differ in etch, liner, fill, aspect-ratio capability "
                   "and minimum spacing. Borrowing one for the other is not provenance.",
         "source": "results/phase0mr3/Z1_ROUTING_CLOSURE.md", "provenance": "INVALID"},
        {"step": "9 current-density rule", "value": "J_design = 1.0e8 A/m2",
         "detail": "DERIVED_FROM_SOURCE and applied to copper conductors generally, so it "
                   "does transfer. The GEOMETRY rule is what does not.",
         "source": "configs/phase0m/interconnect_design_space.yaml process_limits",
         "provenance": "DERIVED_FROM_SOURCE"},
        {"step": "10 status of the 15 -> 20 um repair", "value": "OPEN",
         "detail": "the repair remains geometrically and electrically self-consistent, and "
                   "its provenance claim does not hold. It is a design point in an "
                   "UNSOURCED process window, not a source-backed selection.",
         "source": "this audit", "provenance": "OPEN"},
    ]
    with open(OUT / "interconnect_technology_provenance.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["step", "value", "detail", "source",
                                           "provenance"])
        w.writeheader(); w.writerows(rows)

    md = f"""# PHASE 0M-R3A SECTION 4 --- WHAT IS `ls_to_L`?

> **It is not a TSV, and the TSV process range does not govern it.**
> Phase 0M-R3's claim that the 15 -> 20 um repair is source-backed **does not hold**.

## The provenance chain

| step | finding | provenance |
|---|---|---|
""" + "".join(f"| {r['step']} | **{r['value']}** | {r['provenance']} |\n" for r in rows) + f"""
## The geometry, traced

`ls_to_L` connects the **low-side GaN switch node** on tier {t_src} to the **inductor
terminal** on tier {t_dst} of `{tpl}`, crossing the flying-capacitor tier in between.

| | |
|---|---|
| source tier mid-plane | {zs[t_src]:.1f} um |
| destination tier mid-plane | {zs[t_dst]:.1f} um |
| **vertical span** | **{e.length_mm*1e3:.0f} um** |
| current | {e.i_rms:.3f} A |
| rail | {e.rail} (switch node) |

## Why it is not the TSV field

The framework states both structures explicitly and they are in different places:

| | TSV field | `ls_to_L` |
|---|---|---|
| where | beneath the cell, from the substrate underside | between embedded-component layers, inside the cell |
| span, ARCH_Z1 | 74 um (h_sub - t_cell) | 673 um |
| medium | through silicon | through substrate power-layer build-up |
| carries | the 48 V HV rail into the cell | the switch node to the inductor |

`scripts/phase0f/geometry.py` records the source picture directly: the components are
"embedded within the subsequent substrate power layers", and "the TSV field runs beneath
it from the substrate underside". One sentence describes each, and they are not the same
structure.

## What the design space actually contains

| entry | governs | applies to `ls_to_L`? |
|---|---|---|
| `tsv.radius_m` {{2.5, 15, 50}} um | through-silicon vias | **NO** --- wrong medium and wrong region |
| `rdl.width_m`, `rdl.space_m` | in-plane traces | no --- these are trace rules, not via rules |
| `bump.microbump.diameter_m` {{5, 10, 40}} um | microbumps | no --- a bump joins two surfaces, it is not a via through dielectric |
| **a stacked substrate via rule** | what this net needs | **ABSENT** |

## Consequence

Phase 0M-R3 reported the realizability repair as using "only existing/sourced
technologies", with 20 um justified as inside the TSV radius range. That justification is
**withdrawn**. The correct statement is:

> The repair sets the intra-converter vertical interconnect to r = 20 um at a 70 um pitch.
> Both values are **self-consistent with the framework's own current-density and spacing
> arithmetic**, and **neither is governed by a sourced process rule for this interconnect
> class, because no such rule exists in this repository.**

The repair is therefore **OPEN on process provenance**, not source-backed. It is not shown
to be wrong -- 20 um vias on a 70 um pitch through 673 um of build-up is not an
extraordinary structure -- but it is not demonstrated to be manufacturable either.

**This changes the realizability verdict.** Package clearances are no longer the sole
reason the repaired pair falls short of PROVEN_REALIZABLE; the via technology is now a
second, independent unsourced manufacturing assumption.
"""
    (OUT / "LS_TO_L_INTERCONNECT_AUDIT.md").write_text(md)
    print(f"  ls_to_L: {e.src} -> {e.dst}, tiers {e.tiers}, span {e.length_mm*1e3:.0f} um, "
          f"{e.i_rms:.3f} A")
    print("  technology: INTRA-CONVERTER VERTICAL INTERCONNECT (stacked substrate via)")
    print("  TSV radius range applicable: NO")
    print("  sourced rule for this class: NONE -> repair provenance is OPEN")
    print(f"wrote {OUT/'LS_TO_L_INTERCONNECT_AUDIT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
