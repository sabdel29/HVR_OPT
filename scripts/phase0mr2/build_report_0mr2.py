#!/usr/bin/env python3
"""Phase-0M-R2 Section 14 --- repair the current-facing report and append this phase.

The eight stale claims recovered in Section 1 are fixed AT THEIR SOURCE, and the gate
count is DERIVED from the claim contract rather than retyped. Historical chapters keep
what they said; only current-facing sections are rewritten.
"""
from __future__ import annotations
import csv, re, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
BASE = OUT / "_baseline_phase0mr"
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
CONTRACT = R / "configs" / "phase0mr2" / "current_state_claims.yaml"
TAG = "phase0mr2_narrative"
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))


def rd(p, n=None):
    q = Path(p) / n if n else Path(p)
    return list(csv.DictReader(q.open())) if q.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


def ff(r, k):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return float("nan")


NEW = rd(OUT, "architecture_replay_0mr2.csv")
OLD = rd(BASE, "production_architecture_replay.csv")


def n_(cid, k):
    return next((ff(r, k) for r in NEW if r["case"] == cid), float("nan"))


def o_(arch, k):
    for r in OLD:
        if (r["arch"] == arch and r["mode"] == "AFTER" and "27" in r.get("cooler", "")
                and r.get("template") == "T1_EMBEDDED_4LAYER"):
            return ff(r, k)
    return float("nan")


def narrative() -> str:
    g = rd(OUT, "tsv_geometry_by_architecture.csv")
    cool = rd(OUT, "cooling_regime_table.csv")
    rdl = rd(OUT, "rdl_isotropic_vs_anisotropic.csv")
    stale = rd(OUT, "stale_claims_before.csv")
    FIG = str(OUT)
    ratio = n_("Z1", "du_corner_um") / n_("Z2", "du_corner_um")
    r_mr = o_("ARCH_Z1_EMBEDDED", "du_corner_um") / o_("ARCH_Z2_BACKSIDE", "du_corner_um")

    def row(cid, lab):
        return (f"| {lab} | {f(n_(cid,'P_total_electronics_w'),3)} | "
                f"{f(n_(cid,'P_pump_hydraulic_w'),3)} | {f(n_(cid,'P_total_facility_w'),3)} | "
                f"{f(n_(cid,'T_max_C'),2)} | {f(n_(cid,'T_conv_C'),2)} | "
                f"{f(n_(cid,'die_warpage_pv_um'),3)} | {f(n_(cid,'du_corner_um'),4)} |")

    return f"""<!-- BEGIN GENERATED: {TAG} -->

\\newpage

# Phase 0M-R2 --- Architecture Realizability, Cooling-Regime and Current-State Closure (current authoritative)

Phase 0M-R2 is a falsification gate. It asked five questions that could each have
undermined the physical interpretation of Phase 0M-R, and four of them returned a defect.

## 1. Was "0 stale current-facing claims" true? --- No

**{len(stale)} stale findings across eight claims**, in a report that had passed 46 of 46
cross-report checks. The checker matched each report as one flat string, so a required
phrase found anywhere satisfied the check for the whole document; it could not detect an
omission at all; and its forbidden patterns were paraphrases rather than the report's real
sentences. Registered as **DEFECT #54**. Phase-0M-R's own DEFECT #53 was also never added
to the numbered register, which stopped at 52; it is registered retroactively here.

The fix is a section-scoped claim contract: every claim names the sections that must carry
its CURRENT wording and the sections where HISTORICAL wording is allowed, and the gate
count is derived from the contract rather than typed.

## 2. Is ARCH_Z4 a real power die now? --- Yes, and it is still conditional

`zglobal.stack_for` had branches for "in" and "below" and **none for "above"**, which is
what ARCH_Z4 declares. Its converter heat was being deposited in the `interface` layer
0.355 mm below the cooled face. The power die is now explicit geometry --- 1921 um of
sourced components between the substrate top and the compute die --- and its converter
band sits 1.928 mm below the cooled face.

Z4 nevertheless **remains conditional**, for a different reason. No source describes a
monolithic power-die process, so two constructions are defensible, and Z4's rank depends
on which one is real: stacked gives a corner driver of {f(n_('Z4_stacked','du_corner_um'),4)} um and
best place, planar gives {f(n_('Z4_planar','du_corner_um'),4)} um and second place, and the die warpage differs
by roughly a factor of two between them.

## 3. DEFECT #55, found while building the Z4 geometry

The TSV-field material override was keyed on a layer's in-plane FOOTPRINT. Every assembly
layer added below z = 0 in Phase 0G --- the PCB, the BGA field and ARCH_Z2's backside
converter --- spans the substrate extent, so all of them had their material overwritten
with `tsv_homog` inside every tile. **The PCB was being modelled as a copper/silicon
composite**: k too high by 530x, E by 6.3x, CTE too low by 3.4x, in the layers that set
package warpage. The misassigned volume was 522 to 859 mm3 against 20 to 77 mm3 of real
via field, and it was architecture-dependent, so it did not cancel. Fixing it moved Z1's
die warpage by +75 % and its corner driver by +16.4 %.

## 4. What span does each TSV actually traverse?

| architecture | h_sub | converter cell | **TSV span** | AR at d = 30 um | on the limit? |
|---|---|---|---|---|---|
""" + "".join(
        f"| {r['arch'].replace('ARCH_','')} | {f(r['h_sub_um'],0)} um | "
        f"{f(r['converter_cell_um'],0)} um | **{f(r['length_um'],0)} um** | "
        f"{f(r['aspect_ratio'],2)} | {'YES, exactly' if abs(ff(r,'aspect_ratio')-10)<1e-9 else 'no'} |\n"
        for r in g) + f"""
**No architecture traverses 1300 um.** ARCH_Z1 has a 1.30 mm substrate, but 1226 um of it
is the embedded converter cell sitting on top of the via field; its vias traverse 74 um at
an aspect ratio of 2.47. The Phase-0M-R "1300 um is infeasible" rung corresponds to no
real geometry. The real exposure is the opposite of what that suggested: three of the four
architectures sit **exactly on** the 10:1 limit, with no margin at all.

Three domains had been using three different lengths for the same via --- 300 um
electrically, 280 um in the mesh, and a hard-coded ladder in the feasibility checker.
`configs/phase0mr2/architecture_geometry.yaml` is now the single source and a guard fails
if any two disagree by more than 0.5 %.

## 5. Is the cooling model inside its correlation domain?

| point | flow | Re | regime | Nu | h_eff | pumping | status |
|---|---|---|---|---|---|---|---|
""" + "".join(
        f"| {r['point_id']} | {f(r['m_dot_total_g_s'],1)} g/s | {f(r['Re'],1)} | "
        f"{r['regime']} | {f(r['Nu'],3)} | {f(r['h_effective_W_m2K'],0)} | "
        f"{f(r['P_pump_hydraulic_W'],2)} W | "
        f"{'in domain' if r['in_domain']=='True' else '**OUT_OF_MODEL_DOMAIN**'} |\n"
        for r in cool) + """
**The 50 g/s point is outside the domain of every correlation this framework has.**
`scripts/phase0m/cooling.py` switched to Gnielinski at Re = 2300; Gnielinski is validated
from Re = 3000. The 50 g/s point sits at Re = 2342, in the gap. The two neighbouring
correlations differ by a factor of 2.76 there, so the reported h was set by the choice and
not by the flow. The Phase-0M-R numbers h = 166 000 W/m2K, dp = 1.46 MPa and 74 W of
pumping are **withdrawn**. What survives, and is stronger, is that the retired calibrated
boundary is not reachable by any correlation this framework can validate.

**The production point at 27 g/s is inside the laminar domain**, at Re = 1264.8, so every
Phase-0M-R conclusion resting on it stands. One caveat is now recorded: the thermal
entrance length occupies 86 % of the channel there, so the fully-developed Nusselt number
understates h and the production temperature is conservative rather than optimistic.

## 6. Does promoting the RDL thermal anisotropy change the answer?

The `interface` layer --- the one layer every watt crosses --- was isotropic underfill at
k = 0.70 W/mK. Homogenising its own sourced microbump geometry gives kxy = 0.891 and
kz = 11.739 W/mK: **16.8x more conductive through thickness** than the value in use. It is
now the production default.

| quantity | isotropic | anisotropic | change |
|---|---|---|---|
""" + "".join(
        f"| {r['arch'].replace('ARCH_','')} {k.replace('_',' ')} | " for r in [] for k in []) + "".join(
        f"| {a} peak temperature | {f(next(x['T_max_C'] for x in rdl if x['arch']==ar and x['interface_model']=='isotropic_0p70'),2)} C | "
        f"{f(next(x['T_max_C'] for x in rdl if x['arch']==ar and x['interface_model']=='anisotropic_derived'),2)} C | "
        f"{float(next(x['T_max_C'] for x in rdl if x['arch']==ar and x['interface_model']=='anisotropic_derived')) - float(next(x['T_max_C'] for x in rdl if x['arch']==ar and x['interface_model']=='isotropic_0p70')):+.2f} K |\n"
        for ar, a in (("ARCH_Z1_EMBEDDED", "Z1"), ("ARCH_Z2_BACKSIDE", "Z2"))) + f"""| **Z1/Z2 driver ratio** | **1.1955** | **1.1942** | **-0.105 %** |

It moves absolute temperature by about 7 K and the driver by about 6.7 %, and the ORDERING
by 0.105 %. It matters for absolute numbers and for nothing else.

## The frozen replay

| architecture | P_electronics | P_pump | P_facility | T_max | T_conv | die warpage | corner driver |
|---|---|---|---|---|---|---|---|
{row("Z1", "Z1_EMBEDDED")}
{row("Z2", "Z2_BACKSIDE")}
{row("Z4_stacked", "Z4_POWER_DIE stacked")}
{row("Z4_planar", "Z4_POWER_DIE planar")}

Pumping power is **FACILITY** scope: it is spent outside the package, it is not in the
loss objective, and it is not deposited into the thermal mesh. Phase 0M-R's "system loss"
excluded it and never said so; the two ledgers now refuse each other's terms.

![FIG-0MR2-A]({FIG}/FIG_0MR2_A_zstacks.png)

*FIG-0MR2-A. The three architecture z-stacks with the real TSV span and the cooled face.*

![FIG-0MR2-E]({FIG}/FIG_0MR2_E_three_phases.png)

*FIG-0MR2-E. The frozen architectures through three successive production paths.*

## The deciding question

**D_driver = driver_Z1 / driver_Z2 = {ratio:.4f}** ({f(n_('Z1','du_corner_um'),4)} um against
{f(n_('Z2','du_corner_um'),4)} um).

The Phase-0M-R value was {r_mr:.4f}. The ordering survives physical Z4 geometry, the
corrected board material, architecture-aware TSV spans, a regime-checked cooler and a
promoted RDL tensor. It narrows by {100*(ratio-r_mr)/r_mr:+.1f} %, and it does not approach unity.

**This is a ROBUST ORDERING, not a VALIDATED MAGNITUDE.** The constitutive
transferability problem is untouched: the creep card is Sn3.9Ag0.6Cu fitted over
7.51-15.92 MPa, and 99.8 % of the damage is generated outside that window. Relative life
is not validated and absolute life remains OPEN.

## Temperature and the fatigue driver do not track

{f(n_('Z2','T_max_C'),2)} C against {f(n_('Z1','T_max_C'),2)} C: **ARCH_Z2 is the hottest of the principal
candidates and still carries {100*(n_('Z1','du_corner_um')-n_('Z2','du_corner_um'))/n_('Z1','du_corner_um'):.1f} % less corner-joint driver than ARCH_Z1.**

This must not be read as a claim that temperature is irrelevant to fatigue. It is not:
temperature-dependent constitutive behaviour is one of the dominant physics in this
framework. The narrower and correct statement is that **ranking architectures by package
T_max is not equivalent to ranking them by the current solder-fatigue driver**, because
geometry- and CTE-induced deformation and the local constitutive response are distinct
mechanisms.

![FIG-0MR2-F]({FIG}/FIG_0MR2_F_decoupling.png)

*FIG-0MR2-F. Peak temperature against the fatigue driver. Z2 is hotter and mechanically
preferable; Z4's two construction bounds straddle Z2.*

## Realizability

**0 of 12 template-architecture combinations are realizable, at any of the 27 corners of
the clearance bound.** The three package clearances remain OPEN --- no source, no foundry
rule, and nothing usable in the literature reachable from this host --- but they are not
the binding constraint. Even at their most favourable values, area still blocks 9 of 12,
height 8 of 12, and routing and current density 6 of 12 each. Closing the clearances would
make nothing buildable. T4 is 3.83 % over its area bound once the smallest sidewall
allowance is charged, not the 2 % Phase 0M-R reported with none.

**Neither architecture in the deciding comparison is presently buildable.** The mechanical
ordering is a statement about two designs that cannot yet be manufactured as specified.

<!-- END GENERATED: {TAG} -->
"""


def main() -> int:
    c = yaml.safe_load(CONTRACT.read_text())
    gates = c["meta"]["gates"]
    words = {17: "Seventeen", 18: "Eighteen", 19: "Nineteen", 20: "Twenty"}
    s = REP.read_text()
    fixed = []

    # ---- A. gate count, DERIVED
    old_a = ("**Method.** Seventeen sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, "
             "0F, 0G, 0H, 0I,\n0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M), each designed")
    new_a = (f"**Method.** {words[len(gates)]} sequential falsification gates "
             f"({', '.join(gates)}), each designed")
    # idempotent: a re-run must not fail because the fix is already in place
    if old_a in s:
        s = s.replace(old_a, new_a); fixed.append("A gate count")
    else:
        # the sentence now comes from the generated exec_summary block, whose line
        # wrapping differs from this literal, so PARSE it instead of string-matching
        m = re.search(r"(\w+) sequential falsification gates\s*\(([^)]*)\)",
                      re.sub(r"\s+", " ", s))
        assert m, "no gate sentence at all"
        got = [x.strip() for x in m.group(2).split(",") if x.strip()]
        assert m.group(1) == words[len(gates)] and got == gates, \
            f"gate sentence wrong: {m.group(1)!r}, {got}"
        fixed.append("A gate count (correct, from the generator)")

    # ---- B. phase authority
    s = s.replace("# Phase 0M --- Geometry-Resolved Power Delivery, Component-Level "
                  "Architecture, Cooling and ETM-Coupling Audit (current authoritative)",
                  "# Phase 0M --- Geometry-Resolved Power Delivery, Component-Level "
                  "Architecture, Cooling and ETM-Coupling Audit (extended by Phase 0M-R)")
    fixed.append("B phase authority")

    # ---- C. next work: OWNED BY THE GENERATOR.
    # The Executive Summary is a GENERATED block spliced from
    # results/phase0h/generated_current_facing.md, which is emitted from
    # CURRENT_SCIENTIFIC_STATUS.yaml::current_facing.executive_summary.next_work.
    # Rewriting it here re-wraps the paragraph and breaks the verbatim-block check that
    # exists precisely to stop hand edits drifting from their source. The fix belongs in
    # the YAML; this only VERIFIES it arrived.
    assert "Phase 0M-R2 is the current authoritative phase" in s, \
        "the generator's next_work has not reached the report"
    fixed.append("C next work (verified, owned by the generator)")

    # ---- D. current crowding
    old_d = ("**No current-crowding correction was applied**, because none was "
             "demonstrated ---\nintroducing an empirical factor without evidence is "
             "precisely what the brief forbids.")
    new_d = ("**No AC current-crowding correction is applied**, because none is "
             "demonstrated at this frequency --- introducing an empirical factor without "
             "evidence is precisely what the brief forbids. A **DC** transition "
             "resistance IS applied: since Phase 0M-R each interconnect class carries its "
             "own `Delta_R = R_3D - R_1D`, solved exactly at its production geometry and "
             "cross-validated against MOOSE on five geometries at 0.25-0.73 %. The single "
             "global 1.326 multiplier that preceded it is retired from every production "
             "path. `Delta_R` is a difference against a stated 1-D reference, not an "
             "excess, and at the nominal TSV geometry it is negative.")
    if old_d in s:
        s = s.replace(old_d, new_d); fixed.append("D transition resistance")
    else:
        assert "Delta_R = R_3D - R_1D`, solved exactly" in s, "crowding fix missing"
        fixed.append("D transition resistance (already correct)")

    # ---- E. thermal validation: the OMISSION.
    # The `validation_status` GENERATED block lives inside Mechanical Model Validation and
    # is re-spliced from the YAML, so an insertion there is overwritten. The statement
    # belongs in the Thermal Model Validation section itself.
    anchor = "\n# Thermal Model Validation\n"
    add_e = (
        "**Production cooling boundary (Phase 0M-R, regime-audited in Phase 0M-R2).** The "
        "production ET loop no longer uses the inverse-calibrated Robin coefficient "
        "`h_top = 166 000 W/m2K`; that value is retained only as Phase-0B/0F historical "
        "context. The boundary is now a physical microchannel cooler: `h` from a "
        "regime-checked Nusselt correlation for the duct, corrected by fin efficiency and "
        "area amplification, a caloric resistance `1/(2 m_dot c_p)`, and a streamwise "
        "coolant temperature iterated to a fixed point against the wall flux. At the "
        "production flow of 27 g/s the channel is laminar at Re = 1264.8, inside the "
        "correlation's validated domain. The solid side is cross-validated against MOOSE "
        "with explicit fins: 2 of 4 geometries ACCEPTED, 1 CONDITIONAL at 6.04 %, 1 "
        "REJECTED at 10.11 %, with the production geometry in the accepted band at 3.78 %. "
        "Phase 0M-R2 additionally found that the 50 g/s operating point Phase 0M-R quoted "
        "lies at Re = 2342, between the laminar ceiling of 2300 and Gnielinski's floor of "
        "3000, where no validated correlation exists; the numbers derived from that point "
        "are withdrawn. Conjugate CFD validation is reported separately in "
        "`results/phase0mr2/CONJUGATE_CFD_VALIDATION.md`.\n")
    assert anchor in s
    if "Production cooling boundary (Phase 0M-R, regime-audited" not in s:
        s = s.replace(anchor, anchor + "\n" + add_e, 1)
        fixed.append("E cooling boundary")
    else:
        fixed.append("E cooling boundary (already present)")

    # ---- F/G. the defect register: point the reader at where 26+ actually render
    dsec = "\n# Model Defects Discovered and Fixed\n"
    if dsec in s and "Defects 26 onward" not in s:
        s = s.replace(dsec, dsec + (
            "\n**Scope of this section.** The table below is the Phase-0B..0F record. "
            "Defects 26 onward are carried in the generated current-status section near the "
            "end of this report, where each row states its status AT DISCOVERY together "
            "with the phase that superseded it. Two are worth naming here because they "
            "were current-facing for several phases: **DEFECT #51**, intra-VR routing "
            "modelled but not summed, CLOSED IN PHASE 0M-R, which put it into the "
            "production loss ledger as `P_intraVR_metal` and `P_intraVR_vertical`; and "
            "**DEFECT #52**, the calibrated cooling boundary, CLOSED IN PHASE 0M-R, which "
            "placed a physical microchannel cooler in the production ETM loop and whose "
            "correlation domain Phase 0M-R2 then audited.\n"), 1)
        fixed.append("F/G defect register pointer")

    # ---- H. thermal separation
    old_h = ("* The current Z-architectures nevertheless separate on MECHANICS, not "
             "temperature: their joint temperatures span only 81.10-83.21 C and the "
             "correlation between joint temperature and damage across all runs is "
             "r = +0.017. Both statements are true and must not be conflated -- "
             "temperature-dependent physics matters, and these particular architectures "
             "happen not to differ in temperature.")
    new_h = (
        "* Under the PHYSICAL cooler the Z-architectures DO separate in temperature, and "
        "ARCH_Z2 is the hottest of the principal candidates: "
        f"{f(n_('Z2','T_max_C'),2)} C against {f(n_('Z1','T_max_C'),2)} C for ARCH_Z1. It "
        f"nevertheless carries {100*(n_('Z1','du_corner_um')-n_('Z2','du_corner_um'))/n_('Z1','du_corner_um'):.1f} % LESS corner-joint driver. Under the retired "
        "calibrated boundary the joint temperatures spanned only 81.10-83.21 C and their "
        "correlation with damage was r = +0.017, which is why earlier phases described "
        "these architectures as separating on mechanics alone; that statement is "
        "historical and belongs to that boundary condition. Ranking by package T_max is "
        "NOT equivalent to ranking by the solder-fatigue driver, because geometry- and "
        "CTE-induced deformation and the local constitutive response are distinct "
        "mechanisms. Temperature-dependent physics matters and must not be dismissed.")
    if old_h in s:
        s = s.replace(old_h, new_h); fixed.append("H thermal separation")
    else:
        assert "DO separate in temperature" in s, "thermal-separation fix missing"
        fixed.append("H thermal separation (already correct)")

    # ---- date
    s = re.sub(r'^date: "\d{4}-\d{2}-\d{2}"$', 'date: "2026-09-17"', s, count=1,
               flags=re.M)
    fixed.append("date")

    # ---- Architecture Comparison must state the separation too
    ac = "\n# Architecture Comparison\n"
    if ac in s and "Current position (Phase 0M-R2)" not in s:
        s = s.replace(ac, ac + (
            "\n**Current position (Phase 0M-R2).** Under the physical cooler the "
            "architectures DO separate in temperature: ARCH_Z2 runs "
            f"{f(n_('Z2','T_max_C'),2)} C against ARCH_Z1's {f(n_('Z1','T_max_C'),2)} C and "
            f"ARCH_Z4's {f(n_('Z4_stacked','T_max_C'),2)} C, and ARCH_Z2 is the hottest of "
            "the two principal candidates while remaining the better of them on the "
            "solder-fatigue driver. The tables below this note are the Phase-0I/0M "
            "record and are retained as such.\n"), 1)
        fixed.append("Architecture Comparison")

    # ---- splice the Phase 0M-R2 chapter
    body = narrative()
    pat = rf"<!-- BEGIN GENERATED: {TAG} -->\n.*?<!-- END GENERATED: {TAG} -->\n"
    if re.search(pat, s, re.S):
        s = re.sub(pat, lambda _m: body, s, count=1, flags=re.S)
    else:
        k = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
        s = s[:k] + body + "\n" + s[k:]
    fixed.append("Phase 0M-R2 chapter")

    # ---- refresh the generated status block
    gs = (R / "results" / "phase0g" / "generated_status_sections.md").read_text()
    st = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    m = re.search(r"\n+\\newpage\n+# References", s[st:])
    assert m, "status block boundary not found"
    s = s[:st] + gs.rstrip("\n") + s[st + m.start():]
    s = s.replace("## Current scientific status (Phase 0M-R)\n",
                  "## Current scientific status (Phase 0M-R2)\n")
    fixed.append("status block")

    REP.write_text(s)
    for x in fixed:
        print(f"  fixed: {x}")
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
