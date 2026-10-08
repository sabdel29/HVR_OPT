#!/usr/bin/env python3
"""Phase-0M-R2 --- generate every audit artifact from the result files."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
CFGD = R / "configs" / "phase0mr2"
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def z4_provenance() -> None:
    cfg = yaml.safe_load((CFGD / "z4_stack.yaml").read_text())
    rows = []
    for L in cfg["layers"]:
        rows.append({"parameter": L["name"] + ".thickness_um",
                     "value": L["thickness_um"], "unit": "um",
                     "provenance": L["provenance"], "source": L["source"],
                     "bound": str(L.get("bound_um", "")), "role": L["role"],
                     "material": L["material"]})
    em = cfg["effective_material"]
    rows.append({"parameter": "component_layers.material",
                 "value": em["component_layers"], "unit": "-",
                 "provenance": em["provenance"], "source": em["source"],
                 "bound": "", "role": em["properties_note"], "material": "-"})
    rows.append({"parameter": "density_and_heat_capacity", "value": "OPEN", "unit": "-",
                 "provenance": "OPEN", "source": em["density_note"], "bound": "",
                 "role": "needed only for transient claims; none are made", "material": "-"})
    for v in cfg["variants"]:
        rows.append({"parameter": "variant." + v["id"] + ".total_thickness_um",
                     "value": v["total_thickness_um"], "unit": "um",
                     "provenance": v["provenance"], "source": v["rationale"],
                     "bound": "primary" if v.get("primary") else "bound",
                     "role": v["rule"], "material": "-"})
    for o in cfg["open_items"]:
        rows.append({"parameter": "OPEN: " + o["item"], "value": "OPEN", "unit": "-",
                     "provenance": "OPEN", "source": o["consequence"], "bound": "",
                     "role": "", "material": "-"})
    with open(OUT / "z4_parameter_provenance.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    n = {}
    for r in rows:
        n[r["provenance"]] = n.get(r["provenance"], 0) + 1
    print(f"  z4_parameter_provenance.csv: {len(rows)} parameters, {n}")


def tsv_audit() -> None:
    g = rd("tsv_geometry_by_architecture.csv")
    md = """# PHASE 0M-R2 SECTION 3 --- TSV VERTICAL-SPAN AUDIT

## The question

Phase 0M-R reported that at a 300 um span and a 10:1 aspect limit only r >= 15 um is
buildable, and that at 1300 um no radius in the swept range works. The 1300 um rung was
read as a warning about the 1.30 mm substrate that ARCH_Z1 uses.

**No architecture traverses 1300 um.** ARCH_Z1 has a 1.30 mm substrate, but 1226 um of it
is the embedded converter cell, and the cell sits ON TOP of the via field. Its TSVs
traverse the remaining 74 um.

## What each architecture actually traverses

| architecture | h_sub | converter cell | TSV start | TSV end | **span** | d | AR | d_min at AR 10 | rail | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
"""
    for r in g:
        md += (f"| {r['arch'].replace('ARCH_','')} | {f(r['h_sub_um'],0)} um | "
               f"{f(r['converter_cell_um'],0)} um | {f(r['z_start_um'],0)} um | "
               f"{f(r['z_end_um'],0)} um | **{f(r['length_um'],0)} um** | "
               f"{f(r['diameter_um'],0)} um | {f(r['aspect_ratio'],2)} | "
               f"{f(r['d_min_at_ar_max_um'],1)} um | {r['rail']} | "
               f"{'yes' if r['feasible_aspect']=='True' else 'NO'} |\n")
    md += """
The rule for each span is the architecture's own declared power path:

"""
    for r in g:
        md += f"* **{r['arch'].replace('ARCH_','')}** --- {r['rule']}\n"
    md += """
## Three domains, three answers --- the inconsistency that was there

The TSV length was being decided independently in three places:

| domain | where | ARCH_Z2 length |
|---|---|---|
| electrical | `zpower.evaluate_z` | 300 um |
| mechanical / thermal | `etm.mesh`, the meshed `tsv_homog` region | **280 um** |
| feasibility | `tsv_production.sweep` | a hard-coded 100 / 300 / 1300 ladder tied to no architecture |

The mechanical model gave the field only `sub_lower` = h_sub - t_tile. For ARCH_Z2 and
ARCH_Z4 a 20 um band is reserved at the substrate top even though those architectures put
no converter in the substrate, so 20 um of the via field was missing: a 6.67 %
disagreement between the domains, on the same physical via.

## What was done

`configs/phase0mr2/architecture_geometry.yaml` is now the single source, and
`scripts/phase0mr2/arch_geometry.py::assert_consistent` fails if any two domains disagree
by more than 0.5 %. For the architectures that do not embed their converter, the band at
the substrate top is a routing layer that the field passes THROUGH, so it is marked as a
TSV host and the meshed field spans the full substrate.

| architecture | contract | electrical | mechanical | agreement |
|---|---|---|---|---|
"""
    for r in g:
        if r.get("consistency") == "OK":
            md += (f"| {r['arch'].replace('ARCH_','')} | {f(r['contract_um'],1)} um | "
                   f"{f(r['electrical_um'],1)} um | {f(r['mechanical_um'],1)} um | "
                   f"OK ({f(r['mechanical_delta_pct'],3)} %) |\n")
        else:
            md += (f"| {r['arch'].replace('ARCH_','')} | {f(r['contract_um'],1)} um | "
                   f"-- | -- | {r.get('consistency','')[:60]} |\n")
    md += """
## Is the 30 um reference TSV valid everywhere it is used?

**Yes, and two of the three sit exactly on the limit.**

* ARCH_Z1 at 74 um: AR = 2.47, with large margin. A 30 um via is comfortable here, and
  the smallest diameter the span would permit is 7.4 um.
* ARCH_Z2, ARCH_Z4 and ARCH_Z5 at 300 um: AR = 10.00, **exactly** the demonstrated
  capability. There is no margin: any increase in substrate thickness, or any reduction
  in via diameter, makes these architectures unbuildable at the sourced capability.

That is a tighter statement than Phase 0M-R's. The alarming 1300 um case does not exist;
the real exposure is that three of the four architectures sit ON the limit rather than
near it.
"""
    (OUT / "TSV_VERTICAL_SPAN_AUDIT.md").write_text(md)
    print(f"  wrote {OUT/'TSV_VERTICAL_SPAN_AUDIT.md'}")


def cooling_audit() -> None:
    t = rd("cooling_regime_table.csv")
    md = """# PHASE 0M-R2 SECTION 5 --- COOLING CORRELATION REGIME AUDIT

## The finding

**The Phase-0M-R 50 g/s operating point is outside the domain of every correlation this
framework has.** Its reported numbers -- h = 166 000 W/m2K, dp = 1.46 MPa, 74 W of
pumping -- must be withdrawn as model outputs.

`scripts/phase0m/cooling.py` switched from the laminar correlation to Gnielinski at
Re = 2300 and labelled the result `transitional`. Gnielinski is validated from Re = 3000.
The 50 g/s point sits at **Re = 2342**, which is 42 above the laminar ceiling and 658
below Gnielinski's floor. The framework was extrapolating a turbulent correlation into a
regime it does not cover, and the choice is not a detail: at that Reynolds number the
laminar correlation gives Nu = 4.603 and Gnielinski gives Nu = 12.699, a factor of
**2.76**. The reported h was set by the choice of correlation, not by the flow.

## Every operating point, with its correlation and that correlation's domain

| point | m_dot | per channel | Re | regime | Nu | correlation | validity | h_eff | dp | pump | status |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""
    for r in t:
        md += (f"| {r['point_id']} | {f(r['m_dot_total_g_s'],1)} g/s | "
               f"{f(r['m_dot_per_channel_g_s'],5)} g/s | {f(r['Re'],1)} | {r['regime']} | "
               f"{f(r['Nu'],3)} | {r['nu_correlation']} | {r['nu_validity']} | "
               f"{f(r['h_effective_W_m2K'],0)} | {f(r['dp_MPa'],3)} MPa | "
               f"{f(r['P_pump_hydraulic_W'],2)} W | "
               f"{'IN DOMAIN' if r['in_domain']=='True' else '**OUT_OF_MODEL_DOMAIN**'} |\n")
    md += """
Geometry and fluid state at every point, as required:

| point | D_h | flow area | velocity | rho | mu | k | cp | Pr | coolant rise | coolant max |
|---|---|---|---|---|---|---|---|---|---|---|
"""
    for r in t:
        md += (f"| {r['point_id']} | {f(r['D_h_um'],1)} um | {f(r['flow_area_mm2'],4)} mm2 | "
               f"{f(r['velocity_m_s'],3)} m/s | {f(r['rho_kg_m3'],1)} | "
               f"{f(r['mu_Pa_s'],3)} | {f(r['k_W_mK'],4)} | {f(r['cp_J_kgK'],1)} | "
               f"{f(r['Pr'],3)} | {f(r['dT_coolant_K'],2)} K | "
               f"{f(r['T_coolant_max_C'],2)} C |\n")
    md += """
## The second finding: the production point is thermally DEVELOPING

The laminar Nusselt number used is the FULLY DEVELOPED value. The thermal entrance length
is `L_t = 0.05 Re Pr D_h`:

| point | L_thermal | channel length | L_t / L | fully developed? |
|---|---|---|---|---|
"""
    for r in t:
        md += (f"| {r['point_id']} | {f(r['L_thermal_entry_mm'],2)} mm | "
               f"{f(r['L_channel_mm'],2)} mm | {f(r['entry_fraction'],2)} | "
               f"{'yes' if r['fully_developed']=='True' else '**no**'} |\n")
    md += """
At the production flow the entrance region occupies **86 %** of the channel. A developing
thermal boundary layer has a HIGHER Nusselt number than the fully-developed value, so the
production model UNDERSTATES h and therefore OVERSTATES temperature. The direction
matters: the production result is conservative, not optimistic. It is carried as a
one-sided bounded uncertainty rather than corrected, because no entrance-region
correlation for this duct family is sourced in this repository.

## What this does and does not change

**Withdrawn.** The 50 g/s point and every number derived from it: h = 166 000 W/m2K,
dp = 1.46 MPa, P_pump = 74 W, and the statement that 7.4 % of the load is needed to reach
the retired calibrated boundary. What can still be said is that the retired calibrated
h = 166 000 W/m2K is **not reachable by any correlation this framework can validate**,
which is a stronger statement about the retired boundary and a weaker one about 50 g/s.

**Unchanged.** The production cooler at 27 g/s sits at Re = 1264.8, comfortably laminar
and inside the correlation's domain. Every Phase-0M-R conclusion that rests on the
production point stands: the physical cooler changes absolute responses strongly, and it
makes ARCH_Z2 the hottest of the principal candidates.
"""
    (OUT / "COOLING_REGIME_AUDIT.md").write_text(md)
    print(f"  wrote {OUT/'COOLING_REGIME_AUDIT.md'}")


def clearance_audit() -> None:
    pr = rd("clearance_provenance.csv")
    rows = rd("component_partition_feasibility_r2.csv")
    DIM = ["AREA_FEASIBLE", "HEIGHT_FEASIBLE", "THERMAL_FEASIBLE", "ROUTING_FEASIBLE",
           "CURRENT_DENSITY_FEASIBLE", "PACKAGE_CLEARANCE_SATISFIED"]
    tpls = sorted({r["template"] for r in rows})
    arcs = sorted({r["arch"] for r in rows})
    md = """# PHASE 0M-R2 SECTION 4 --- PACKAGE CLEARANCE AUDIT

## The three clearances

| clearance | definition | where | sourcing | bound swept | anchor |
|---|---|---|---|---|---|
"""
    for r in pr:
        md += (f"| `{r['clearance']}` | {r['definition']} | {r['where']} | "
               f"**{r['sourcing_status']}** | {r['bound_um']} um | "
               f"{r['bound_anchor'][:150]} |\n")
    md += """
## What was searched

In the order the brief specifies:

1. **the exact package/process source used by this framework** --- NOT AVAILABLE. The
   June-2026 DVPD source describes embedded components and names stacking as a
   fabrication challenge, but publishes no cavity or clearance design rule.
2. **foundry / OSAT / substrate-vendor design rules** --- NOT ACCESSIBLE. These are
   released under NDA; no public copy was reachable from this host.
3. **directly comparable peer-reviewed implementations** --- SEARCHED, NOTHING USABLE.
   Crossref and OpenAlex were reachable and returned no paper giving a numeric
   embedded-component cavity clearance. WebSearch is blocked in this environment.
4. **explicit bounded engineering envelope** --- ADOPTED. Each bound is anchored to a
   length the framework already sources, and the anchor is named. These are ANALOGIES,
   NOT SOURCES, and they are labelled BOUNDED.
5. **OPEN** --- retained as the sourcing status of all three.

No single "reasonable" value was adopted. Every template was evaluated at all 27 corners
of the three-way bound.

## The result: 0 of 12 combinations are realizable, at ANY corner

| template | architecture | FULLY_REALIZABLE | dimensions that fail at EVERY corner |
|---|---|---|---|
"""
    for tpl in tpls:
        for ar in arcs:
            sub = [r for r in rows if r["template"] == tpl and r["arch"] == ar]
            if not sub:
                continue
            bad = [d for d in DIM if {r[d] for r in sub} == {"False"}]
            vals = {r["FULLY_REALIZABLE"] for r in sub}
            v = ("ALWAYS" if vals == {"True"} else "NEVER" if vals == {"False"}
                 else "BOUND_DEPENDENT")
            md += (f"| {tpl} | {ar.replace('ARCH_','')} | **{v}** | "
                   f"{', '.join(d.replace('_FEASIBLE','').replace('_SATISFIED','') for d in bad) or 'none'} |\n")
    cnt = {}
    for tpl in tpls:
        for ar in arcs:
            sub = [r for r in rows if r["template"] == tpl and r["arch"] == ar]
            for d in DIM:
                if sub and {r[d] for r in sub} == {"False"}:
                    cnt[d] = cnt.get(d, 0) + 1
    md += """
## How often each dimension blocks

| dimension | blocks at every corner |
|---|---|
"""
    for d in DIM:
        md += f"| {d} | {cnt.get(d,0)} of 12 |\n"
    md += """
## The Phase-0M-R claim, narrowed

Phase 0M-R said all twelve templates fail FULLY_REALIZABLE **because** three package
clearances are OPEN. That is not right. Even if all three clearances were sourced at
their most favourable values, area would still block 9 of 12, height 8 of 12, and routing
and current density 6 of 12 each. **Closing the clearances would make nothing realizable.**
They are a necessary condition, not the binding one.

## T4, specifically

Phase 0M-R reported T4 as about 2 % outside its area bound, with no cavity sidewall
allowance charged at all. Charging the SMALLEST sidewall in the bound, T4 is **3.83 %**
over. T4 does not get closer to feasible once clearances are represented; it gets further
away. And because the 5.61 mm2 per-level area is an OUTPUT of the converter area model,
the shortfall cannot be closed by repacking: it would require changing the component
topology, which the converter model does not currently support.

## Does any architecture in the Z1/Z2 comparison fail on clearance?

Both do, at most corners. ARCH_Z1 with T1 has only 24 um of height slack, so its clearance
is satisfiable at just 3 of 27 corners and only when the die-to-component gap plus the
cooler standoff together stay at or below 10 um. ARCH_Z2 with T1 fails height at every
corner. **Neither architecture in the deciding comparison is presently buildable**, and
that is stated plainly rather than folded into the mechanical result.
"""
    (OUT / "PACKAGE_CLEARANCE_AUDIT.md").write_text(md)
    print(f"  wrote {OUT/'PACKAGE_CLEARANCE_AUDIT.md'}")


def rdl_audit() -> None:
    rows = rd("rdl_isotropic_vs_anisotropic.csv")
    t = rd("rdl_production_tensor.csv")
    if not rows:
        print("  rdl: no data yet")
        return
    t0 = t[0] if t else {}
    md = f"""# PHASE 0M-R2 SECTION 8 --- RDL PRODUCTION THERMAL AUDIT

## What the production model was using

The `interface` layer sits directly between the compute die and the substrate. Every watt
the package removes crosses it. It was modelled as **isotropic underfill, k = 0.70 W/mK**.

## What its own sourced geometry gives

The layer is a microbump field in underfill: r = 5 um, pitch 20 um, height 10 um, solder
inclusions. Homogenising that geometry with the method Phase 0M-R validated gives

| | k_x | k_y | k_z | anisotropy | bound check |
|---|---|---|---|---|---|
| derived tensor | {f(t0.get('k_x'),4)} | {f(t0.get('k_y'),4)} | **{f(t0.get('k_z'),4)}** | {f(t0.get('anisotropy_z_over_xy'),1)}x | Voigt {f(t0.get('err_voigt_kz_pct'),2)} %, Maxwell {f(t0.get('err_maxwell_kxy_pct'),2)} % |
| production, before | 0.70 | 0.70 | 0.70 | 1.0x | --- |

The production value was **{f(t0.get('kz_over_production_iso'),1)}x too resistive through thickness**, in the one layer
every watt must cross. This is a different quantity from the Phase-0M-R RDL result: that
one was about the in-plane anisotropy of a redistribution stack, and it moved the Z1/Z2
ratio by at most 0.11 %. This is the bump layer in the primary heat path.

## Measured effect on the frozen architectures

| architecture | interface model | T_max | die warpage | corner driver |
|---|---|---|---|---|
"""
    for r in rows:
        md += (f"| {r['arch'].replace('ARCH_','')} | {r['interface_model']} | "
               f"{f(r['T_max_C'],2)} C | {f(r['die_warpage_pv_um'],3)} um | "
               f"{f(r['du_corner_um'],4)} um |\n")
    def g(a, m, k):
        return float(next(r for r in rows if r["arch"] == a and r["interface_model"] == m)[k])
    dT1 = g("ARCH_Z1_EMBEDDED", "anisotropic_derived", "T_max_C") - g("ARCH_Z1_EMBEDDED", "isotropic_0p70", "T_max_C")
    dT2 = g("ARCH_Z2_BACKSIDE", "anisotropic_derived", "T_max_C") - g("ARCH_Z2_BACKSIDE", "isotropic_0p70", "T_max_C")
    ri = g("ARCH_Z1_EMBEDDED", "isotropic_0p70", "Z1_over_Z2_driver_ratio")
    ra = g("ARCH_Z1_EMBEDDED", "anisotropic_derived", "Z1_over_Z2_driver_ratio")
    md += f"""
| quantity | isotropic | anisotropic | change |
|---|---|---|---|
| Z1 peak temperature | {f(g('ARCH_Z1_EMBEDDED','isotropic_0p70','T_max_C'),2)} C | {f(g('ARCH_Z1_EMBEDDED','anisotropic_derived','T_max_C'),2)} C | **{dT1:+.2f} K** |
| Z2 peak temperature | {f(g('ARCH_Z2_BACKSIDE','isotropic_0p70','T_max_C'),2)} C | {f(g('ARCH_Z2_BACKSIDE','anisotropic_derived','T_max_C'),2)} C | **{dT2:+.2f} K** |
| Z1 corner driver | {f(g('ARCH_Z1_EMBEDDED','isotropic_0p70','du_corner_um'),4)} um | {f(g('ARCH_Z1_EMBEDDED','anisotropic_derived','du_corner_um'),4)} um | {100*(g('ARCH_Z1_EMBEDDED','anisotropic_derived','du_corner_um')/g('ARCH_Z1_EMBEDDED','isotropic_0p70','du_corner_um')-1):+.2f} % |
| Z2 corner driver | {f(g('ARCH_Z2_BACKSIDE','isotropic_0p70','du_corner_um'),4)} um | {f(g('ARCH_Z2_BACKSIDE','anisotropic_derived','du_corner_um'),4)} um | {100*(g('ARCH_Z2_BACKSIDE','anisotropic_derived','du_corner_um')/g('ARCH_Z2_BACKSIDE','isotropic_0p70','du_corner_um')-1):+.2f} % |
| **Z1/Z2 driver ratio** | **{ri:.4f}** | **{ra:.4f}** | **{100*(ra-ri)/ri:+.3f} %** |

## Decision: PROMOTED to the production default

The tensor is derived from the layer's own sourced geometry by a method already validated
against the Voigt and Maxwell-Garnett bounds to under 1 %, and it moves peak temperature
by about 7 K. Both conditions the brief sets for promotion are met, so it is now the
production default. `PHASE0MR2_INTERFACE_KORTHO=iso` recovers the retired behaviour for
comparison.

**It changes no ordering.** The effect is almost exactly common mode: the ratio moves
{100*(ra-ri)/ri:+.3f} %. The promotion matters for absolute temperature and for nothing else, and
that is how it is reported.
"""
    (OUT / "RDL_PRODUCTION_THERMAL_AUDIT.md").write_text(md)
    print(f"  wrote {OUT/'RDL_PRODUCTION_THERMAL_AUDIT.md'}")


if __name__ == "__main__":
    z4_provenance(); tsv_audit(); cooling_audit(); clearance_audit(); rdl_audit()
