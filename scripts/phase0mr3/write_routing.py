#!/usr/bin/env python3
"""Phase-0M-R3 Section 6 --- routing closure for the frozen realizable pair."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3"


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def main() -> int:
    routes = list(csv.DictReader((OUT / "routing_feasibility_candidates.csv").open()))
    for tag, arch in (("Z1", "ARCH_Z1_EMBEDDED"), ("Z2", "ARCH_Z2_BACKSIDE")):
        cfg = yaml.safe_load(
            (R / f"configs/phase0mr3/frozen_realizable_{tag}.yaml").read_text())
        rs = [r for r in routes if r["arch"] == arch]
        md = f"""# PHASE 0M-R3 SECTION 6 --- {tag} ({arch}) ROUTING CLOSURE

Routing is a HARD GATE in the frozen realizability contract. A candidate whose losses are
calculable but whose conductors do not physically fit is NOT realizable, and Phase 0M's
finding that the output plane needed 8.6x the available tile width was reported only as a
loss number.

## The frozen candidate

| | |
|---|---|
| cells | {cfg['converter']['m_vr']} |
| current per cell | {f(cfg['converter']['i_per_cell_a'],3)} A |
| inductor | `{cfg['converter']['inductor']}`, {f(cfg['converter']['inductor_height_um'],1)} um, i_sat {f(cfg['converter']['inductor_i_sat_a'],2)} A |
| high side / low side | {cfg['converter']['hs_device']} / {cfg['converter']['ls_device']} |
| switching frequency | {f(cfg['converter']['f_sw_hz']/1e3,1)} kHz |
| intra-VR via radius | **{f(cfg['repair_applied']['what'].split('-> ')[1].replace(' um',''),1)} um** at {f(cfg['repair_applied']['pitch_um'],1)} um pitch |

## Every route in the power path

| net | rail | geometry | I_dc | I_rms | required | available | ratio | fits |
|---|---|---|---|---|---|---|---|---|
""" + "".join(
            f"| `{r['net']}` | {r['rail']} | {r['geom']} | {f(r['i_dc'],3)} A | "
            f"{f(r['i_rms'],3)} A | "
            f"{(f(r['w_required_um'],1) + ' um width') if r['geom']=='lateral' else (str(r['n_via']) + ' vias')} | "
            f"{'tile side' if r['geom']=='lateral' else 'pad field'} | "
            f"**{f(r['ratio'],4)}** | {'yes' if r['feasible']=='True' else 'NO'} |\n"
            for r in rs) + f"""
The chain is continuous from package input to load: `vin_bus` (48 V in) ->
`hs_to_cf` (flying capacitors) -> `hs_to_ls` (the 16 V intermediate node) ->
`ls_to_L` (switch node to inductor) -> `L_to_cout` (output capacitor) ->
`vout_plane` (1 V to the package interconnect). No tier boundary is crossed without an
allocated via stack.

## What the repair changed, and why it was the only one needed

The binding net is **`ls_to_L`**, a vertical via stack carrying {f(next((r['i_rms'] for r in rs if r['net']=='ls_to_L'), 0),3)} A. At the
Phase-0M geometry it needed 1.236x the vias its pad provides.

Layers do not fix this: adding metal layers widens traces and adds no vias. Cells do not
fix it either -- splitting into more cells divides the current and the pad area together,
so the ratio is invariant. What does fix it is the via geometry, because the required
count goes as 1/r^2 while the available count goes as 1/p^2, and the framework's own
pitch rule `p = max(2r + s_min, 2r(1+koz))` with the SOURCE_BACKED `s_min = 30 um` makes
p grow more slowly than r:

| r | p | (p/r)^2 | ratio |
|---|---|---|---|
| 15 um | 60 um | 16.00 | 1.236 |
| **20 um** | **70 um** | **12.25** | **0.934** |
| 25 um | 80 um | 10.24 | 0.791 |

20 um is inside the sourced range `design_variables.tsv.radius_m = {{lo 2.5, nominal 15,
hi 50}} um`, so no new process is required. It is the smallest option in the enumeration
that clears the gate.

**Nothing else changed.** Same load, same package, same devices, same inductor, same cell
count, same substrate TSV geometry, same cooling, same RDL stack.
"""
        (OUT / f"{tag}_ROUTING_CLOSURE.md").write_text(md)
        print(f"  wrote {OUT / f'{tag}_ROUTING_CLOSURE.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
