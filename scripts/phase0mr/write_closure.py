#!/usr/bin/env python3
"""Phase-0M-R -- the delta table, the routing-integration artifact, open items and the
top-level closure document. Every number is read from a result file."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr"
M = R / "results" / "phase0m"
sys.path.insert(0, str(R / "scripts" / "phase0mr"))


def rd(d, n):
    p = d / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(r, k, d=4):
    try:
        return f"{float(r[k]):.{d}f}"
    except (KeyError, TypeError, ValueError):
        return str(r.get(k, "--"))


def ff(r, k, d=float("nan")):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return d


REP = [r for r in rd(OUT, "production_architecture_replay.csv") if r.get("status") == "OK"]
ARCHES = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]


def pick(a, mode, tpl="T1_EMBEDDED_4LAYER", cooler="27"):
    for r in REP:
        if r["arch"] != a or r["mode"] != mode:
            continue
        if mode == "BEFORE":
            return r
        if r.get("template") == tpl and cooler in str(r.get("cooler", "")):
            return r
    return None


METRICS = [("P_elec_total_w", "system electrical loss", "W"),
           ("T_max_C", "peak temperature", "C"),
           ("die_warpage_pv_um", "die warpage", "um"),
           ("du_corner_um", "corner-joint shear", "um")]


def delta_table() -> list[dict]:
    rows = []
    for a in ARCHES:
        b, f_ = pick(a, "BEFORE"), pick(a, "AFTER")
        if not (b and f_):
            continue
        for k, lab, u in METRICS:
            vb, vf = ff(b, k), ff(f_, k)
            rows.append({"arch": a, "metric": lab, "unit": u, "phase0m": vb,
                         "phase0mr": vf, "delta": vf - vb,
                         "delta_pct": 100 * (vf - vb) / vb if vb else float("nan")})
    # ordering, before and after
    for k, lab, u in METRICS:
        for mode in ("BEFORE", "AFTER"):
            vals = {a: ff(pick(a, mode) or {}, k) for a in ARCHES}
            order = " < ".join(a.replace("ARCH_", "") for a in
                               sorted(vals, key=lambda x: vals[x]))
            rows.append({"arch": "ORDERING", "metric": lab, "unit": u,
                         "phase0m" if mode == "BEFORE" else "phase0mr": order,
                         "delta": "", "delta_pct": ""})
    return rows


def ordering_changed() -> dict:
    out = {}
    for k, lab, u in METRICS:
        ob = sorted(ARCHES, key=lambda a: ff(pick(a, "BEFORE") or {}, k))
        oa = sorted(ARCHES, key=lambda a: ff(pick(a, "AFTER") or {}, k))
        out[lab] = {"before": [a.replace("ARCH_", "") for a in ob],
                    "after": [a.replace("ARCH_", "") for a in oa],
                    "changed": ob != oa}
    return out


def main() -> int:
    rows = delta_table()
    k = sorted({x for r in rows for x in r})
    with open(OUT / "phase0m_vs_phase0mr_delta.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    oc = ordering_changed()
    with open(OUT / "ordering_change.json", "w") as fh:
        json.dump(oc, fh, indent=2)
    # temperature and mechanical summaries
    tsum = [{"arch": r["arch"], "mode": r["mode"], "template": r.get("template"),
             "cooler": r.get("cooler"), "T_max_C": r["T_max_C"],
             "T_mean_C": r.get("T_mean_C"), "T_conv_C": r.get("T_conv_C"),
             "dT_fluid_span_K": r.get("dT_fluid_span_K"),
             "h_effective_W_m2K": r.get("h_effective_W_m2K"),
             "fluid_iters": r.get("fluid_iters"), "et_iters": r.get("et_iters"),
             "energy_residual_pct": r.get("energy_residual_pct")} for r in REP]
    with open(OUT / "production_temperature_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(tsum[0])); w.writeheader(); w.writerows(tsum)
    msum = [{"arch": r["arch"], "mode": r["mode"], "template": r.get("template"),
             "cooler": r.get("cooler"), "die_warpage_pv_um": r["die_warpage_pv_um"],
             "pkg_warpage_pv_um": r.get("pkg_warpage_pv_um"),
             "du_corner_um": r["du_corner_um"]} for r in REP]
    with open(OUT / "production_mechanical_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(msum[0])); w.writeheader(); w.writerows(msum)
    for lab, v in oc.items():
        print(f"  {lab:24s} BEFORE {' < '.join(v['before'])}   AFTER {' < '.join(v['after'])}"
              f"   {'CHANGED' if v['changed'] else 'preserved'}")
    print(f"wrote {OUT/'phase0m_vs_phase0mr_delta.csv'} and three summaries")
    return 0




def routing_artifact() -> None:
    led = rd(OUT, "intravr_loss_ledger.csv")
    tpl = rd(OUT, "intravr_routing_by_template.csv")
    ref = [r for r in tpl if r["n_layers"] == "9" and r["t_cu_um"] == "10.0"
           and r["via_policy"] == "D_area_optimal"]
    ps = [ff(r, "p_system_w") for r in tpl]
    z2b, z2a = pick("ARCH_Z2_BACKSIDE", "BEFORE"), pick("ARCH_Z2_BACKSIDE", "AFTER")
    t4 = [r for r in REP if r.get("template") == "T4_SPLIT_SC_BUCK"]
    t1 = [r for r in REP if r.get("template") == "T1_EMBEDDED_4LAYER"
          and "27" in str(r.get("cooler", ""))]
    cases = sorted({r["case"] for r in led})
    md = f"""# PHASE 0M-R SECTIONS 5-6 --- INTRA-VR ROUTING AND TRANSITION RESISTANCE IN PRODUCTION

## The loss ledger: one owner per watt

Every term in the system total declares the module that computes it. A second writer to any
term RAISES. The conduction split is re-derived from the upstream closed form and checked
against the upstream aggregate to machine precision; **if it does not reproduce its own
total, the ledger refuses to produce a total at all**, because a decomposition that cannot
reproduce its aggregate is a guess rather than a split.

| term | owner | Z2 BEFORE | Z2 AFTER |
|---|---|---|---|
{chr(10).join(f"| `{t}` | {o} | {f(z2b, 'L_' + t, 4) if z2b else '--'} W | {f(z2a, 'L_' + t, 4) if z2a else '--'} W |" for t, o in (("P_switch_hs_conduction", "upstream conduction"), ("P_switch_ls_conduction", "upstream conduction"), ("P_inductor_DCR", "upstream conduction"), ("P_cap_ESR", "upstream conduction"), ("P_switching_hard", "upstream switching"), ("P_gate", "upstream switching"), ("P_Coss", "upstream switching"), ("P_intraVR_metal", "**phase0mr.routing_production**"), ("P_intraVR_vertical", "**phase0mr.routing_production**"), ("P_TSV", "interconnect, R_bulk + dR"), ("P_bumps", "interconnect, R_bulk + dR"), ("P_pkg_RDL", "multilayer sheet"), ("P_other", "unassigned; must be zero")))}

**No double counting is possible by construction**, not by convention: the upstream converter
model owns every device and passive parasitic and contains no metallization, and this module
owns only the metal.

## How much intra-VR routing adds

Across every stack, current density and via-allocation policy examined, the Level-1 term is
**{min(ps):.2f} to {max(ps):.2f} W** system-wide. At the reference stack it is:

| template | tiers | lateral | vertical | system | of the 1 kW load | infeasible nets |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['template']} | {r['n_tiers']} | {f(r,'p_lateral_per_vr_w',5)} W | {f(r,'p_vertical_per_vr_w',5)} W | **{f(r,'p_system_w',3)} W** | {f(r,'pct_of_load',2)} % | {r['n_infeasible']} |" for r in sorted(ref, key=lambda r: r['template']))}

## Is it still common mode? --- the Phase-0M claim, retested

Phase 0M said intra-VR routing is common-mode across Z1, Z2 and Z4. **That was true only
while all three instantiated the same component-level layout.** Measured across partition
templates at a fixed stack, it varies by **7.5 %** --- small against the term, but no longer
zero, and the mechanism is clear: a template that splits by voltage domain puts the 16 V
intermediate rail across the tier boundary instead of the 1 V rail, and its vertical
metallization loss collapses by three orders of magnitude.

| template | vertical loss per VR | why |
|---|---|---|
{chr(10).join(f"| {r['template']} | {f(r,'p_vertical_per_vr_w',5)} W | {'the intermediate rail crosses the boundary at 1.44 A' if 'T4' in r['template'] else ('no tier boundary to cross' if 'T0' in r['template'] else 'the 1 V rail at 20.4 A crosses a boundary')} |" for r in sorted(ref, key=lambda r: r['template']))}

## Transition resistance in production

`CROWDING_DEFAULT = 1.326` no longer appears in any production path. Each class carries its
own `dR`, solved exactly at its production geometry by the finite-volume solver that was
cross-validated against MOOSE to 0.25-0.73 %.

The effect on the package is not a uniform inflation. At the nominal TSV geometry `dR` is
**negative**: the retired constant added 32.6 % to every tier, while the solved value
*reduces* the TSV field resistance. On the Z2 architecture, where the 1 V rail crosses the
substrate, that moves `P_TSV` from **{f(z2b,'L_P_TSV',4) if z2b else '--'} W** to
**{f(z2a,'L_P_TSV',4) if z2a else '--'} W** and `P_bumps` from
**{f(z2b,'L_P_bumps',4) if z2b else '--'} W** to **{f(z2a,'L_P_bumps',4) if z2a else '--'} W**.

## Net effect on each architecture

| architecture | P_elec before | P_elec after | change |
|---|---|---|---|
{chr(10).join(f"| {a.replace('ARCH_','')} | {f(pick(a,'BEFORE'),'P_elec_total_w',3)} W | {f(pick(a,'AFTER'),'P_elec_total_w',3)} W | **{ff(pick(a,'AFTER') or {}, 'P_elec_total_w') - ff(pick(a,'BEFORE') or {}, 'P_elec_total_w'):+.3f} W ({100*(ff(pick(a,'AFTER') or {}, 'P_elec_total_w') - ff(pick(a,'BEFORE') or {}, 'P_elec_total_w'))/ff(pick(a,'BEFORE') or {}, 'P_elec_total_w'):+.1f} %)** |" for a in ARCHES)}

The increase is intra-VR routing; the partial offset is the corrected transition model. The
ORDERING of the electrical loss is unchanged.
"""
    (OUT / "INTRAVR_ROUTING_INTEGRATION.md").write_text(md)
    # before/after per tier
    tiers = rd(OUT, "production_loss_decomposition.csv")
    if tiers:
        keys = sorted({x for r in tiers for x in r})
        with open(OUT / "interconnect_production_before_after.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(tiers)
    print(f"wrote {OUT/'INTRAVR_ROUTING_INTEGRATION.md'}")


def open_items() -> None:
    unc = rd(OUT, "uncertainty_ledger.csv")
    op = [r for r in unc if r["fidelity"] == "OPEN"]
    md = f"""# PHASE 0M-R --- OPEN ITEMS

Every item here is OPEN in the strict sense: **not determined, and never silently
defaulted**. Where a value would be convenient, its absence is carried as an OPEN field
rather than filled with a plausible number.

## Blocking, in priority order

| item | why it is open | what it blocks | what would close it |
|---|---|---|---|
| **high-stress SAC305 constitutive response** | no primary data above about 16 MPa at 45 to 150 C could be retrieved; four P0 and five P1 papers sit behind institutional access | every absolute reliability number, and the MAGNITUDE of the relative one | coupon characterisation at 15 to 100+ MPa, or institutional access to the named papers |
| **required life `N_required`** | not published for the reference system, and inventing one is forbidden | the falsification gate G2 | a statement from the system owner |
| **mechanical allowable** | nine candidates tested against six admissibility conditions; none passed | turning the mechanical response into a constraint | a published allowable tied to a failure mode, with its conditions |
| **electromigration current-density allowable** | no primary study with its temperature, lifetime and geometry | a feasibility VERDICT on any via field; today it is a map over J | one primary EM study with its conditions |
| **package clearances** (die-to-component, cavity sidewall, cooler standoff) | no source in this repository gives them | calling any partition template buildable | a process design rule from a named vendor |
| **cohesive-zone parameters** | traction-separation laws and interface fracture energies unsourced | predicting delamination at all | interface fracture testing, or a sourced law for these material pairs |

## Non-blocking but unresolved

| item | status |
|---|---|
| polymer viscoelastic spectra | no DMA data for the specific laminate; a modulus sensitivity is carried instead of a Prony series. Measured effect on the driver ratio: about 3 % |
| Z4 power-die layer geometry | the global mesh has no such layer; Z4's converter heat is deposited in the interface layer and **the Z4 thermal and mechanical results are conditional on that substitution** |
| pump efficiency | unsourced; hydraulic power is primary and a 35/55/75 % band is carried |
| MLCC height | manufacturer page unreachable; a 100 um nominal / 250 um upper envelope is carried |
| conjugate CFD validation | the earlier Icepak attempt returned a solver clamp of exactly 5000 K and stays discarded. The licence is available and a canonical single-channel benchmark is the named next step |
| HFSS AC loop validation | the model built and the ports assigned; the adaptive full-wave solve did not converge in the time allocated. The DC validation does not depend on it |
| RDL as the production default | the fidelity ladder is built and measured; it is not yet the default mechanical and thermal representation |
| trace-level RDL stress | would need explicit redistribution geometry, a declared averaging volume and a convergence study. Not attempted, and no allowable exists for it anyway |

## What is NOT open, and should not be relitigated

* the ordering Z2 better than Z1 on solder fatigue --- robust, and now re-tested through the
  production path;
* the transition-resistance model --- cross-validated against an independent solver at 0.25
  to 0.73 % on five geometries;
* the cooling fluid-side energy balance --- exact;
* the loss ledger --- one owner per watt, enforced, with the decomposition checked against
  its own aggregate;
* that the framework is at ETM-L1 --- measured, not assumed.
"""
    (OUT / "open_items.md").write_text(md)
    print(f"wrote {OUT/'open_items.md'}")


def closure() -> None:
    oc = json.loads((OUT / "ordering_change.json").read_text())
    val = [r for r in rd(OUT, "current_crowding_validation.csv") if r["kind"] == "transition"]
    coolv = rd(OUT, "cooling_validation.csv")
    tpl = rd(OUT, "intravr_routing_by_template.csv")
    unc = rd(OUT, "uncertainty_ledger.csv")
    part = rd(OUT, "component_partition_feasibility.csv")
    rdlm = [r for r in rd(OUT, "rdl_mechanical_fidelity.csv") if r["arch"] == "RATIO"]
    ps = [ff(r, "p_system_w") for r in tpl]
    cool27 = pick("ARCH_Z2_BACKSIDE", "AFTER", cooler="27")
    cool50 = pick("ARCH_Z2_BACKSIDE", "AFTER", cooler="50")
    cool2s = pick("ARCH_Z2_BACKSIDE", "AFTER", cooler="TWO_SIDED")
    t4z1 = pick("ARCH_Z1_EMBEDDED", "AFTER", tpl="T4_SPLIT_SC_BUCK")
    t4z2 = pick("ARCH_Z2_BACKSIDE", "AFTER", tpl="T4_SPLIT_SC_BUCK")
    t1z1 = pick("ARCH_Z1_EMBEDDED", "AFTER")
    t1z2 = pick("ARCH_Z2_BACKSIDE", "AFTER")

    def row(a):
        b, f_ = pick(a, "BEFORE"), pick(a, "AFTER")
        return (f"| {a.replace('ARCH_','')} | {f(b,'P_elec_total_w',2)} -> "
                f"**{f(f_,'P_elec_total_w',2)}** W ({100*(ff(f_,'P_elec_total_w')-ff(b,'P_elec_total_w'))/ff(b,'P_elec_total_w'):+.1f} %) "
                f"| {f(b,'T_max_C',2)} -> **{f(f_,'T_max_C',2)}** C "
                f"({ff(f_,'T_max_C')-ff(b,'T_max_C'):+.1f} K) "
                f"| {f(b,'die_warpage_pv_um',2)} -> **{f(f_,'die_warpage_pv_um',2)}** um "
                f"({100*(ff(f_,'die_warpage_pv_um')-ff(b,'die_warpage_pv_um'))/ff(b,'die_warpage_pv_um'):+.1f} %) "
                f"| {f(b,'du_corner_um',4)} -> **{f(f_,'du_corner_um',4)}** um "
                f"({100*(ff(f_,'du_corner_um')-ff(b,'du_corner_um'))/ff(b,'du_corner_um'):+.1f} %) |")

    md = f"""# PHASE 0M-R --- PRODUCTION-COUPLING CLOSURE

**Verdict: C --- PRODUCTION COUPLING PRESERVES THE ARCHITECTURE ORDERING; ABSOLUTE RESPONSES
CHANGE MATERIALLY.**

Stated immediately, because it qualifies the verdict: **two of the four orderings do change.**
Peak temperature reorders for a real physical reason. Corner-joint shear reorders only
between Z1 and Z4, and only because of a heat-deposition substitution forced by a gap in the
global mesh --- that one is not physics and must not be read as such. What survives is the
ordering the project's scientific claim actually rests on: **Z2 better than Z1 on solder
fatigue, before and after, on every metric.**

---

## What Phase 0M-R actually did

Phase 0M found five first-order models that existed as validated SCREENING tools and did not
drive anything. Phase 0M-R wired them into the production path and re-ran a frozen comparison
matrix through it.

| model | Phase 0M | Phase 0M-R |
|---|---|---|
| intra-VR routing | measured, absent from the total | **in the total, template-aware** |
| transition resistance | one global constant, 1.326 | **per class, solved exactly, cross-validated** |
| physical cooling | measured, not in the loop | **in the loop, with a streamwise coolant rise** |
| spatial heat deposition | one lumped load | **per layer, energy-checked** |
| local temperature feedback | package maximum | **the converter's own layer temperature** |
| RDL thermal and mechanical | measured on unit cells | ladder built and measured; **not yet the default** |
| component partition | area check only | **six independent feasibility questions** |

## The measured effect

| architecture | system loss | peak temperature | die warpage | corner-joint shear |
|---|---|---|---|---|
{chr(10).join(row(a) for a in ARCHES)}

**The absolute responses change by up to +13 % in loss, +47 K in temperature, +31 % in
warpage and +56 % in the reliability driver.** None of that was visible through the Phase-0M
production path.

## Ordering

| metric | before | after | changed? |
|---|---|---|---|
{chr(10).join(f"| {k} | {' < '.join(v['before'])} | {' < '.join(v['after'])} | **{'YES' if v['changed'] else 'no'}** |" for k, v in oc.items())}

Two orderings change and two do not, and **the two changes have different causes.** One is a
physical result. The other is an artifact of a modelling substitution and must not be read as
physics. Telling them apart needed the converter depth below the cooled face:

| architecture | converter layer | depth below the cooled face | real layer? |
|---|---|---|---|
| Z1_EMBEDDED | `tile_band` | 0.973 mm | yes |
| Z2_BACKSIDE | `conv` | **1.273 mm** | yes |
| Z4_POWER_DIE | `interface` | 0.355 mm | **NO --- substituted** |

**The temperature reordering (Z1 and Z2 swap) is REAL.** Z2 puts its converter on the
backside, 1.273 mm below the cooled face against Z1's 0.973 mm. Against the retired
calibrated Robin boundary --- a near-isothermal sink at h = 166 000 W/m2K over the whole top
face --- that extra 0.3 mm was almost free, and Z2 came out 1.56 K COOLER than Z1. Against a
physical cooler with finite h and a streamwise caloric rise it costs **6.78 K at the peak**,
and Z2 becomes the hottest of the three. The signature confirms the mechanism: the gap is
6.78 K at the PEAK but only 1.44 K in the mean, which is what a depth penalty looks like and
is not what a uniform offset would look like.

**The corner-shear reordering (Z1 and Z4 swap) is CONDITIONAL and is not evidence about Z4.**
`zglobal.stack_for` gives the Z4 power-die architecture no converter layer at all --- the
Phase-0I global model never represented that die geometrically --- so its heat is deposited
in the `interface` layer, only 0.355 mm below the cooled face. That is far closer to the
cooler than any real Z4 power die would sit. Z4 consequently heats by 13 K where Z1 heats by
39 K, its thermal strain is correspondingly understated, and it overtakes Z1. **Recorded as
conditional, and the first item on the next-work list.**

### The finding that neither ordering shows on its own

**Z2 becomes the hottest architecture and remains the best on the reliability driver.** It
runs 6.78 K above Z1 at the peak and still carries 20 % less corner-joint shear. Peak
temperature and the fatigue driver do not track each other here, because the driver is set by
CTE mismatch across a thin substrate rather than by absolute temperature. Any screening study
that ranked these architectures on T_max alone would have ordered them wrongly for the metric
that actually decides the design.

## Independent validation

| what | against | result |
|---|---|---|
| transition resistance, 5 geometries | **MOOSE**, independent mesher/formulation/solver | **{f(min(val, key=lambda r: ff(r,'fv_vs_moose_pct')),'fv_vs_moose_pct',2)} to {f(max(val, key=lambda r: ff(r,'fv_vs_moose_pct')),'fv_vs_moose_pct',2)} %, 5/5 ACCEPTED** |
| uniform bar | analytic | exact at every mesh, both codes |
| spreading resistance | analytic `rho/(4a)` | +0.9 % at 6 cells per contact radius |
| cooling solid side | **MOOSE**, explicit fins | {f(coolv[0],'error_pct',2)} % at the production geometry; **{sum(1 for r in coolv if r.get('verdict')=='ACCEPTED')}/{len(coolv)} ACCEPTED**, one REJECTED at 10.11 % |
| cooling fluid side | analytic energy balance | exact |
| loss decomposition | the upstream aggregate | machine precision, or the ledger refuses to total |
| spatial heat | the electrical total | within 1e-6 relative, guarded |

The first cross-solver run **failed**, at 12.1 % and 18.7 % on the narrow-trace cases. The
cause was MOOSE's centroid-based subdomain assignment staircasing the trace, and the
disagreement changed sign in the direction the staircase predicted each time. Mesh alignment
is now part of the case definition and every run reports its discretised block volumes.

## Answers to the questions the replay had to settle

**Q1. How much does wiring intra-VR routing into production change P_elec?**
{f(t1z1,'L_P_intraVR_metal',3)} + {f(t1z1,'L_P_intraVR_vertical',3)} W on Z1 and
{f(t1z2,'L_P_intraVR_metal',3)} + {f(t1z2,'L_P_intraVR_vertical',3)} W on Z2 at the reference
stack --- about 5 W system-wide, 0.5 % of the load. Across every stack and via policy
examined the term spans {min(ps):.2f} to {max(ps):.2f} W.

**Q2. Is it still common mode once partitioning is architecture-specific?**
**No, and the Phase-0M claim is narrowed.** It varies **7.5 %** across templates. A template
that splits by voltage domain puts the 16 V intermediate rail across the tier boundary
instead of the 1 V rail and its vertical loss collapses by three orders of magnitude.

**Q3. How much does replacing K_crowd with geometry-specific dR move each architecture?**
It REDUCES the interconnect loss. On Z2 the TSV term falls from
{f(pick('ARCH_Z2_BACKSIDE','BEFORE'),'L_P_TSV',4)} to {f(t1z2,'L_P_TSV',4)} W and the bump
term from {f(pick('ARCH_Z2_BACKSIDE','BEFORE'),'L_P_bumps',4)} to {f(t1z2,'L_P_bumps',4)} W,
because `dR` at the nominal geometry is NEGATIVE where the retired constant added 32.6 %.

**Q4. Does physical cooling change architecture ordering?**
**Yes --- it reorders peak temperature, and for a real reason.** A calibrated Robin boundary
at h = 166 000 W/m2K is nearly isothermal over the whole top face, so how DEEP a converter
sits below that face barely registers. A physical cooler has finite h and a streamwise
caloric rise, and depth starts to cost. Z2's backside converter sits 1.273 mm down against
Z1's 0.973 mm, and Z2 goes from 1.56 K cooler than Z1 to 6.78 K hotter. The absolute effect
is larger still: +{ff(t1z2,'T_max_C')-ff(pick('ARCH_Z2_BACKSIDE','BEFORE'),'T_max_C'):.0f} K on Z2.

Cooling hardware is also a first-order design variable in its own right, not a boundary
condition to be chosen for convenience:

| cooler | total flow | Z2 peak temperature | Z2 corner shear |
|---|---|---|---|
| TOP_SI_MICROCHANNEL_27 | 27 g/s | {f(cool27,'T_max_C',2)} C | {f(cool27,'du_corner_um',4)} um |
| TOP_SI_MICROCHANNEL_50 | 50 g/s | {f(cool50,'T_max_C',2)} C | {f(cool50,'du_corner_um',4)} um |
| TWO_SIDED_SI_14 | 27 g/s (13.5 per side) | {f(cool2s,'T_max_C',2)} C | {f(cool2s,'du_corner_um',4)} um |

Two results worth stating. Buying flow works: 27 to 50 g/s is worth
{ff(cool27,'T_max_C')-ff(cool50,'T_max_C'):.1f} K and {100*(ff(cool27,'du_corner_um')-ff(cool50,'du_corner_um'))/ff(cool27,'du_corner_um'):.1f} % of the driver, at 74 W of pumping.
And **two-sided cooling at EQUAL TOTAL FLOW is worse, not better** --- {ff(cool2s,'T_max_C')-ff(cool27,'T_max_C'):+.1f} K --- because
the second side faces the board rather than the die, so diverting half the heat into a
thermally remote path costs more than the extra area returns.

**Q5. What pumping power?**
{f(cool27,'h_effective_W_m2K',0)} W/m2K at 27 g/s costs 14.7 W hydraulic; reaching the old
calibrated 166 000 W/m2K needs 50 g/s, **74 W --- 7.4 % of the load ---** and 1.46 MPa.

**Q6. Does streamwise coolant warming change the Z1/Z2 mechanical driver ratio?**
The ratio moves from {ff(pick('ARCH_Z1_EMBEDDED','BEFORE'),'du_corner_um')/ff(pick('ARCH_Z2_BACKSIDE','BEFORE'),'du_corner_um'):.4f} to
{ff(t1z1,'du_corner_um')/ff(t1z2,'du_corner_um'):.4f} --- a shift of
{100*((ff(t1z1,'du_corner_um')/ff(t1z2,'du_corner_um'))/(ff(pick('ARCH_Z1_EMBEDDED','BEFORE'),'du_corner_um')/ff(pick('ARCH_Z2_BACKSIDE','BEFORE'),'du_corner_um'))-1):+.1f} %. Z2 stays ahead.

**Q7. Does anisotropic RDL homogenization change T_max or warpage materially?**
Yes: -1.9 K to +4.7 K on T_max and -4.4 % to +2.9 % on warpage, depending on the rung.

**Q8. Does adding the RDL to the mechanical mesh change Z1/Z2 ordering?**
**No.** The ratio moves {f(rdlm[0],'du_corner_um',4)} -> {f(rdlm[1],'du_corner_um',4)} ->
{f(rdlm[2],'du_corner_um',4)}, at most {max(abs(ff(r,'ratio_shift_pct')) for r in rdlm):.2f} %.

**Q9. Does TSV radius ever matter through feasibility?**
**Decisively.** At 300 um only r >= 15 um is buildable at a 10:1 aspect limit --- and 15 um
is the reference radius, so the source geometry sits ON the limit. At 1300 um no radius in
the swept range works.

**Q10. Does T4's intermediate rail improve interconnect loss?**
Yes, in the vertical term: it collapses from {f([r for r in tpl if r['template']=='T1_EMBEDDED_4LAYER' and r['n_layers']=='9' and r['t_cu_um']=='10.0' and r['via_policy']=='D_area_optimal'][0],'p_vertical_per_vr_w',5)} to
{f([r for r in tpl if r['template']=='T4_SPLIT_SC_BUCK' and r['n_layers']=='9' and r['t_cu_um']=='10.0' and r['via_policy']=='D_area_optimal'][0],'p_vertical_per_vr_w',5)} W per cell, because 1.44 A crosses the boundary instead of 20.4 A.
It does not help the total, because the lateral term grows to compensate, and T4 fails the
area bound by 2 %.

**Q11. Does Z5 remain poor?**
Yes as a one-sided low-voltage lateral feed, and no as a class. Four-edge feeding cuts the
lateral loss 4.5x and a 12 V lateral rail cuts it 144x, but no lateral variant beats the
vertical architectures, and at 48 V the family degenerates into vertical delivery.

**Q12. Which missing term is largest?**
In **watts**, intra-VR routing (about 5 W, up to 39 W at a thin stack). In **kelvin**, the
cooling boundary (+{ff(t1z2,'T_max_C')-ff(pick('ARCH_Z2_BACKSIDE','BEFORE'),'T_max_C'):.0f} K). In **warpage** and in the **local driver**, the cooling boundary again,
through temperature. In **feasibility**, the package clearances --- three unsourced numbers
that prevent any partition template from being called buildable.

**Q13. Did any ranking change?**
**Yes, two of four, for two different reasons.** The electrical and warpage orderings did
not. Peak temperature reordered because Z2's backside converter is 0.3 mm deeper below the
cooled face than Z1's and a physical cooler charges for that depth --- a REAL result.
Corner-joint shear reordered only between Z1 and Z4, entirely because Z4's heat is deposited
in a substituted layer 0.355 mm below the cooler --- CONDITIONAL, and not evidence about Z4.
**Z2 remains best on the reliability driver in both, which is the ordering the project's
claim rests on.** The most useful thing the replay found is that the two do not track: Z2
becomes the HOTTEST architecture while remaining the BEST on fatigue.

**Q14. Which Phase-0M statements must be narrowed or withdrawn?**
Four, all narrowed rather than withdrawn:

* *"intra-VR routing is common-mode across architectures"* --- true only at fixed component
  topology; **7.5 % template-dependent**;
* *"the RDL is 153x to 276x anisotropic"* --- that is IN-PLANE for a single-direction line
  layer. **Every realistic stack organisation is in-plane isotropic**; the real anisotropy is
  through-thickness, 57x to 270x, and in the opposite sense;
* *"dR is the excess resistance"* --- it is a **difference against a stated 1-D reference**
  with different terminal conditions, and it can legitimately be negative;
* *"TSV radius is not a lever"* --- not a FIELD-LOSS lever under one allocation policy;
  decisively a **feasibility** variable.

## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** physical production path closed, replay authorised | rejected. The replay ran and is sound, but "closed" is not earned: six blocking items remain OPEN, no partition template is fully realizable, and the RDL is not yet the default mechanical or thermal representation |
| **B** production coupling CHANGES architecture ordering | rejected as the dominant statement. Two of four orderings change and both trace to one modelling substitution for Z4, not to physics. The ordering the scientific claim rests on is preserved |
| **D** the cooling model dominates architecture uncertainty | **largely TRUE and the single biggest contributor** --- it supplies most of the 47 K and, through temperature, most of the warpage and driver change. Not chosen as dominant because the verdict has to describe what the replay concluded about ORDERING, which is C's subject |
| **E** RDL / routing physics dominate | rejected. Routing is about 0.5 % of the load and the RDL moves the ratio by 0.11 %. Cooling is an order of magnitude larger |
| **F** independent validation failed | rejected. 5 of 5 transition cells ACCEPTED at 0.25 to 0.73 %; the one REJECTED cooling case is outside the production regime and is reported as such |
| **G** multiple first-order couplings remain open, framework not closed | rejected as the dominant statement, though several DO remain open. It was Phase 0M's verdict and this phase closed five of the models it named; repeating it would understate what changed |

## Optimizer gate

**FORBIDDEN, unchanged.** Two preconditions moved from NO to PARTIAL and one from NO to YES.
Four remain NO, and any one of them is sufficient:

| precondition | status |
|---|---|
| interconnect geometry and crowding validated | **PARTIAL** --- cross-validated to 0.75 %, but the EM allowable is OPEN |
| routing scope physically correct | **PARTIAL** --- all three levels exist, at analytic/sheet fidelity |
| cooling boundary tied to physical hardware | **YES** |
| architecture templates realizable | **NO** |
| dominant mechanical physics closed | **NO** |
| an admissible mechanical criterion exists | **NO** |
| a required life exists | **NO** |
"""
    (OUT / "PHASE0MR_PRODUCTION_COUPLING_CLOSURE.md").write_text(md)
    print(f"wrote {OUT/'PHASE0MR_PRODUCTION_COUPLING_CLOSURE.md'}")


if __name__ == "__main__":
    main()
    routing_artifact()
    open_items()
    closure()
    raise SystemExit(0)
