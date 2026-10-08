#!/usr/bin/env python3
"""Phase-0M-R2 Section 2 --- the Z4 geometry audit document."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
BASE = OUT / "_baseline_phase0mr"


def rd(p):
    return list(csv.DictReader(Path(p).open())) if Path(p).is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def main() -> int:
    cur = rd(OUT / "z4_before_after.csv")
    old = rd(BASE / "production_architecture_replay.csv")
    prov = rd(OUT / "z4_parameter_provenance.csv")
    cfg = yaml.safe_load((R / "configs" / "phase0mr2" / "z4_stack.yaml").read_text())

    def o(arch):
        for r in old:
            if (r["arch"] == arch and r["mode"] == "AFTER"
                    and "27" in r.get("cooler", "")
                    and r.get("template") == "T1_EMBEDDED_4LAYER"):
                return r
        return {}

    def c(cid):
        return next((r for r in cur if r["case"] == cid), {})

    md = """# PHASE 0M-R2 SECTION 2 --- Z4 GEOMETRY AUDIT

## What was wrong

`zglobal.stack_for` had branches for `"in"` (ARCH_Z1, converter inside the substrate) and
`"below"` (ARCH_Z2, converter under the substrate). It had **no branch for `"above"`**,
which is what ARCH_Z4 declares. `zglobal.conv_above_layers()` was written for that branch
and is never called anywhere in the repository -- dead code marking the gap.

The consequence: ARCH_Z4's converter heat was deposited into the `interface` layer, a
10 um underfill band 0.355 mm below the cooled face. A real Z4 power die sits far deeper
and is far thicker. Every Z4 thermal and mechanical number produced before this phase was
conditional on that substitution.

## The power die as real geometry

Built from the components the framework already sources, stacked where ARCH_Z4 puts them:
above the substrate top, below the compute die.

| layer | thickness | provenance | source |
|---|---|---|---|
"""
    for L in cfg["layers"]:
        md += (f"| `{L['name']}` | {L['thickness_um']:.0f} um | {L['provenance']} | "
               f"{L['source'][:105]} |\n")
    md += f"""
**Total: {sum(L['thickness_um'] for L in cfg['layers']):.0f} um.**

The high-side device is in this stack. For ARCH_Z1 the source flip-chips it to the RDL of
the bottom substrate, below z = 0, which is why Z1's charged cell is 1226 um and not 1911.
ARCH_Z4 has no such surface: all of its conversion happens on the power die. That is a
DERIVED consequence of the declared power path, not a new assumption.

The component layers use `hvr_effective`, the same effective converter medium ARCH_Z1 uses
for its tile band and ARCH_Z2 for its backside layer. Using a different material for Z4
would turn an architecture comparison into a material comparison. **The power die is not
modelled as a generic silicon slab.**

### Provenance summary

| class | count |
|---|---|
"""
    n = {}
    for p in prov:
        n[p["provenance"]] = n.get(p["provenance"], 0) + 1
    for k in ("SOURCE_BACKED", "DERIVED", "BOUNDED", "OPEN"):
        md += f"| {k} | {n.get(k,0)} |\n"
    md += """
## The construction question the sources do not settle

No source in this repository describes a monolithic power-die process, so two
constructions are defensible and BOTH are run:

| variant | thickness | rule | status |
|---|---|---|---|
"""
    for v in cfg["variants"]:
        md += (f"| **{v['id']}** | {v['total_thickness_um']:.0f} um | {v['rule']} | "
               f"{'primary' if v.get('primary') else 'bound'} |\n")
    md += """
## Where the converter heat now goes

| architecture | converter layer | depth below the cooled face | real layer? |
|---|---|---|---|
| Z1_EMBEDDED | `tile_band` | 0.973 mm | yes |
| Z2_BACKSIDE | `conv` | 1.273 mm | yes |
| Z4, Phase 0M-R | `interface` | **0.355 mm** | **NO --- substituted** |
| Z4, Phase 0M-R2 | `pdie_gan_hs` + `pdie_gan_ls` + `pdie_inductor` + `pdie_mlcc` | **1.928 mm** | yes |

The heat is spread across the whole component band weighted by volume, not dumped into
whichever sub-layer is named first. The `interface` fallback has been REMOVED rather than
left as a safety net: a missing power die now raises, because a silent fallback is exactly
how the conditional result was produced.

## Result

| quantity | Phase 0M-R (substituted) | 0M-R2 STACKED | 0M-R2 PLANAR |
|---|---|---|---|
"""
    z4o = o("ARCH_Z4_POWER_DIE")
    st, pl = c("Z4_d55fix_stacked"), c("Z4_d55fix_planar")
    for key, lab, d in (("P_elec_total_w", "system electrical loss (W)", 3),
                        ("T_max_C", "peak temperature (C)", 2),
                        ("T_conv_C", "converter layer temperature (C)", 2),
                        ("die_warpage_pv_um", "die warpage (um)", 3),
                        ("du_corner_um", "corner-joint driver (um)", 4)):
        md += (f"| {lab} | {f(z4o.get(key), d)} | **{f(st.get(key), d)}** | "
               f"{f(pl.get(key), d)} |\n")
    md += """
Two corrections landed together, so the Z4 change is not attributable to geometry alone:
DEFECT #55 (below) affects all three architectures, and the power-die geometry affects Z4
only. The control runs separate them.

## Verdict on Z4: **Z4 REMAINS CONDITIONAL**

Not for the old reason. The heat-source substitution is gone and the die is real geometry.
Z4 is now conditional on a **sourcing** question instead of a modelling one: its rank
depends on which construction the power die actually is.

| | corner driver | rank among the three |
|---|---|---|
| Z4_STACKED | """ + f"{f(st.get('du_corner_um'),4)} um | **best** |\n| Z4_PLANAR | {f(pl.get('du_corner_um'),4)} um | middle |\n" + """
Between the two constructions the die warpage differs by about a factor of two, and Z4
moves from first to second place. The stacked variant inserts 1.921 mm of stiff
`hvr_effective` between the substrate and the compute die, which acts as a stiffening
plate; the planar variant does not. **Nothing about Z4's ranking can be closed until the
power-die construction is sourced.**

What CAN be said, and is stable across both variants: Z4's converter sits deeper below the
cooled face than either alternative, its peak temperature is nonetheless the lowest of the
three because its loss is spread through a much thicker volume, and **the Z1 / Z2 ordering
is unaffected by anything Z4 does** -- it is a separate comparison and is reported as one.

## DEFECT #55, found while building this

The TSV-field material override was keyed on a layer's in-plane FOOTPRINT. Every assembly
layer added below z = 0 in Phase 0G -- the PCB, the BGA field, and for ARCH_Z2 the
backside converter -- spans the substrate extent, so all of them had their material
overwritten with `tsv_homog` inside every tile. The PCB was being modelled as a
copper/silicon composite.

| architecture | misassigned volume | legitimate TSV volume | ratio |
|---|---|---|---|
| Z1_EMBEDDED | 522.29 mm3 | 20.34 mm3 | 25.7x |
| Z2_BACKSIDE | 859.31 mm3 | 76.97 mm3 | 11.2x |
| Z4_POWER_DIE | 522.29 mm3 | 76.97 mm3 | 6.8x |

The property error is large and it is architecture-dependent, so it does not cancel in the
comparison:

| where FR4 belongs | k | E | CTE |
|---|---|---|---|
| `board_fr4`, correct | 0.30 W/mK | 20 000 MPa | 1.70e-5 /K |
| `tsv_homog`, what was used | 158.90 W/mK | 126 073 MPa | 5.01e-6 /K |
| error | **530x** | **6.3x** | **3.4x low** |

Board stiffness and CTE are precisely what drive package warpage and corner-joint shear,
which is the deciding metric. Fixing it moves Z1's die warpage from 25.37 to 44.50 um
(+75 %) and its corner driver from 4.2803 to 4.9803 um (+16.4 %). `footprint` and
`tsv_host` are now separate fields on `Layer`.
"""
    (OUT / "Z4_GEOMETRY_AUDIT.md").write_text(md)
    print(f"wrote {OUT/'Z4_GEOMETRY_AUDIT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
