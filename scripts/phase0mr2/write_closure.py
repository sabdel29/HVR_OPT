#!/usr/bin/env python3
"""Phase-0M-R2 --- the top-level closure document, open items and optimizer gate."""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
BASE = OUT / "_baseline_phase0mr"


def rd(p, n=None):
    q = Path(p) / n if n else Path(p)
    return list(csv.DictReader(q.open())) if q.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x)


NEW = rd(OUT, "architecture_replay_0mr2.csv")
OLD = rd(BASE, "production_architecture_replay.csv")


def n_(cid, k):
    return float(next(r for r in NEW if r["case"] == cid)[k])


def o_(a, k):
    for r in OLD:
        if (r["arch"] == a and r["mode"] == "AFTER" and "27" in r["cooler"]
                and r["template"] == "T1_EMBEDDED_4LAYER"):
            return float(r[k])
    return float("nan")


PRE = [
    ("interconnect geometry and crowding validated", "PARTIAL",
     "Delta_R cross-validated against MOOSE at 0.25-0.73 %, and the TSV span is now "
     "architecture-aware and consistent across all three domains. The electromigration "
     "current-density allowable is still OPEN."),
    ("routing scope physically correct", "PARTIAL",
     "all three levels are in production at analytic/sheet fidelity."),
    ("cooling boundary tied to physical hardware", "PARTIAL",
     "DOWNGRADED from YES by Phase 0M-R2. The production point is physical and inside its "
     "correlation domain, but the model has no validated correlation for 2300 < Re < 3000 "
     "and no conjugate CFD validation. An optimizer would be free to walk into that hole."),
    ("architecture templates realizable", "NO",
     "0 of 12 at any of 27 clearance-bound corners. Area blocks 9, height 8, routing and "
     "current density 6 each, clearances 11."),
    ("architecture geometry physically represented", "PARTIAL",
     "NEW precondition. ARCH_Z4's power die is real geometry now, but its construction is "
     "unsourced and its rank depends on which construction is real."),
    ("dominant mechanical physics closed", "NO",
     "high-stress SAC305 constitutive response is CONDITIONAL; cohesive-zone parameters "
     "are OPEN; 6 of 8 enumerated failure mechanisms remain uncomputed."),
    ("an admissible mechanical criterion exists", "NO",
     "nine candidates tested against six admissibility conditions; none passed."),
    ("a required life exists", "NO", "N_required is OPEN. Not published for this system."),
]


def main() -> int:
    ratio = n_("Z1", "du_corner_um") / n_("Z2", "du_corner_um")
    r_mr = o_("ARCH_Z1_EMBEDDED", "du_corner_um") / o_("ARCH_Z2_BACKSIDE", "du_corner_um")
    cool = rd(OUT, "cooling_regime_table.csv")
    g = rd(OUT, "tsv_geometry_by_architecture.csv")
    stale = rd(OUT, "stale_claims_before.csv")
    after = rd(OUT, "stale_claims_after.csv")

    md = f"""# PHASE 0M-R2 --- ARCHITECTURE REALIZABILITY, COOLING-REGIME AND CURRENT-STATE CLOSURE

**Verdict: H --- PRODUCTION MODEL STILL NOT PHYSICALLY CLOSED; NO ARCHITECTURE VERDICT
BEYOND Z1/Z2 IS DEFENSIBLE.**

The deciding ordering survives every correction made in this phase. Beyond that one pair,
three independent gaps each prevent a wider claim.

---

## The deciding question

**D_driver = driver_Z1 / driver_Z2 = {ratio:.4f}**

| | Phase 0M | Phase 0M-R | Phase 0M-R2 |
|---|---|---|---|
| driver Z1 (um) | {f(o_('ARCH_Z1_EMBEDDED','du_corner_um'),4) if False else '2.7447'} | {f(o_('ARCH_Z1_EMBEDDED','du_corner_um'),4)} | **{f(n_('Z1','du_corner_um'),4)}** |
| driver Z2 (um) | 2.0754 | {f(o_('ARCH_Z2_BACKSIDE','du_corner_um'),4)} | **{f(n_('Z2','du_corner_um'),4)}** |
| ratio | 1.3225 | {r_mr:.4f} | **{ratio:.4f}** |

It survives real ARCH_Z4 geometry, a corrected board material, architecture-aware TSV
spans, a regime-checked cooler and a promoted RDL thermal tensor. It narrows by
{100*(ratio-r_mr)/r_mr:+.1f} % against Phase 0M-R and does not approach unity.

### Uncertainty on the ratio

| source | effect on the ratio | basis |
|---|---|---|
| numerical | < 0.5 % | four graded mesh levels, die warpage converged to 0.50 % |
| geometry --- TSV span | 0 % | all three domains now use one source, enforced |
| geometry --- Z4 construction | 0 % on Z1/Z2 | Z4 is a separate comparison |
| RDL interface tensor | -0.105 % | measured directly: isotropic 1.1955 against anisotropic 1.1942. Almost pure common mode |
| cooling model | not separable at 27 g/s | the production point was already inside its correlation domain before this phase, so the regime audit changed no number there. The 50 g/s point is withdrawn rather than re-valued |
| material --- board FR4 vs the DEFECT #55 composite | **-4.9 %** | 1.2552 to 1.1942, the largest single contributor |
| constitutive | NOT QUANTIFIED | the creep card is Sn3.9Ag0.6Cu over 7.51-15.92 MPa and 99.8 % of the damage is outside it. This is why the MAGNITUDE is not validated |

**ROBUST ORDERING. NOT A VALIDATED MAGNITUDE.** Relative life is not validated, because
the constitutive transferability problem is untouched by this phase.

## Temperature and the fatigue driver do not track

ARCH_Z2 runs **{f(n_('Z2','T_max_C'),2)} C** against ARCH_Z1's **{f(n_('Z1','T_max_C'),2)} C** --- the hottest of the
two principal candidates --- and carries **{100*(n_('Z1','du_corner_um')-n_('Z2','du_corner_um'))/n_('Z1','du_corner_um'):.1f} % less** corner-joint driver.

This must not be read as a claim that temperature is irrelevant to fatigue, which would be false: temperature-
dependent constitutive behaviour is among the dominant physics here. The correct statement
is narrower --- **ranking architectures by package T_max is not equivalent to ranking them
by the current solder-fatigue driver**, because geometry- and CTE-induced deformation and
the local constitutive response are distinct mechanisms.

## The five questions this gate had to settle

**1. Was "0 stale current-facing claims" true?** No. **{len(stale)} stale findings across eight
claims**, in a report that passed 46 of 46 cross-report checks. DEFECT #54: the checker
matched each report as one flat string, could not detect an omission at all, and used
paraphrases rather than the report's real sentences as its forbidden patterns. After the
repair the section-scoped checker reports **{len(after)}**.

**2. Is ARCH_Z4 a real power die?** Yes --- 1921 um of sourced components between the
substrate top and the compute die, with the converter band 1.928 mm below the cooled face
instead of a 10 um underfill layer at 0.355 mm. **But it remains CONDITIONAL**, now on a
sourcing question rather than a modelling one: no source describes a monolithic power-die
process, and Z4 takes first place under the stacked construction ({f(n_('Z4_stacked','du_corner_um'),4)} um) and
second under the planar one ({f(n_('Z4_planar','du_corner_um'),4)} um).

**3. What vertical span does each TSV traverse?**

| architecture | h_sub | converter cell | TSV span | AR | on the limit |
|---|---|---|---|---|---|
""" + "".join(
        f"| {r['arch'].replace('ARCH_','')} | {f(r['h_sub_um'],0)} | "
        f"{f(r['converter_cell_um'],0)} | **{f(r['length_um'],0)} um** | "
        f"{f(r['aspect_ratio'],2)} | {'YES' if abs(float(r['aspect_ratio'])-10)<1e-9 else 'no'} |\n"
        for r in g) + f"""
No architecture traverses 1300 um. ARCH_Z1's vias traverse 74 um, not the 1.30 mm
substrate. Three of the four sit **exactly** on the 10:1 limit.

**4. Is the cooling model inside its correlation domain?** At the production point yes
(Re = 1264.8, laminar). At 50 g/s **no**: Re = 2342 lies between the laminar ceiling of
2300 and Gnielinski's floor of 3000, and the neighbouring correlations differ there by
2.76x. h = 166 000 W/m2K, dp = 1.46 MPa and 74 W are withdrawn.

**5. Does promoting the RDL thermal anisotropy change the Z1/Z2 result?** It changes
absolute temperature by about 7 K and the ratio by **0.105 %**. Promoted as the production
default for the absolute numbers; it changes no ordering.

## Two pre-existing defects found

**DEFECT #55** --- the TSV-field material override was keyed on in-plane FOOTPRINT, so the
PCB, the BGA field and ARCH_Z2's backside converter were all given `tsv_homog` inside every
tile. The PCB was a copper/silicon composite: k too high by 530x, E by 6.3x, CTE too low by
3.4x, in exactly the layers that set package warpage. 522 to 859 mm3 misassigned against 20
to 77 mm3 of real via field, architecture-dependent, so it did not cancel.

**DEFECT #54** --- the current-state propagation failure described above. Phase-0M-R's own
DEFECT #53 had also never been added to the numbered register, which stopped at 52; it is
registered retroactively here.

## Realizability: nothing is buildable

**0 of 12 template-architecture combinations, at any of 27 clearance-bound corners.** The
three package clearances remain OPEN --- searched in the framework's own sources, in
accessible foundry material, and in the literature reachable from this host, and found in
none of them --- but they are **not the binding constraint**. At their most favourable
values, area still blocks 9 of 12, height 8 of 12, and routing and current density 6 each.

**Neither architecture in the deciding comparison is presently buildable.** The mechanical
ordering is a statement about two designs that cannot yet be manufactured as specified, and
it is reported as such.

## Energy-ledger scope, now explicit

Phase-0M-R's "system loss" excluded hydraulic pumping and never said so. Pumping appeared
nowhere: not in the ledger, not in the replay total, not in the thermal mesh.

| scope | terms | in the loss objective | deposited as heat |
|---|---|---|---|
| ELECTRONICS | converter + package PDN + intra-VR routing | yes | yes |
| FACILITY | hydraulic pumping | no | **no** --- the pump is not in the package |

| architecture | P_electronics | P_pump | P_facility |
|---|---|---|---|
""" + "".join(
        f"| {r['case']} | {f(r['P_total_electronics_w'],3)} W | "
        f"{f(r['P_pump_hydraulic_w'],3)} W | {f(r['P_total_facility_w'],3)} W |\n"
        for r in NEW) + """
The two ledgers refuse each other's terms, and both directions are negative-tested.

## Optimizer gate

**FORBIDDEN.** One precondition was DOWNGRADED this phase and one was added.

| precondition | status | evidence |
|---|---|---|
""" + "".join(f"| {a} | **{b}** | {c} |\n" for a, b, c in PRE) + """
## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** geometry closed, ordering survives | the ordering half is true; geometry is not closed --- the Z4 construction is unsourced, three clearances are OPEN, nothing is realizable |
| **B** ordering survives, realizability open | true, and a strict SUBSET of H: it says nothing about Z4 remaining conditional or about the cooling correlation hole |
| **C** cooling validity changes absolute responses | the audit found a real defect, but it did NOT change the production point, which was already in domain. The largest absolute change this phase came from DEFECT #55 |
| **D** Z4 reordering was a substitution artifact | **contradicted by measurement.** With real geometry Z4 moves FURTHER ahead --- from second at 3.6681 um to FIRST at 3.5306 um stacked. Only the planar construction returns it to second |
| **E** ordering changes after geometry closure | the Z1/Z2 ordering does not change, and geometry is not closed |
| **F** realizability invalidates an architecture | too strong. Nothing is shown to be impossible; everything is shown to be not yet buildable against partly unsourced constraints |
| **G** cooling outside its domain, thermal magnitudes withdrawn | over-generalises. Only the 50 g/s point is out of domain and only its numbers are withdrawn; the production point stands |
"""
    (OUT / "PHASE0MR2_REALIZABILITY_COOLING_STATE_CLOSURE.md").write_text(md)

    with open(OUT / "optimizer_preconditions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["precondition", "status", "evidence"])
        w.writeheader()
        for a, b, c in PRE:
            w.writerow({"precondition": a, "status": b, "evidence": c})

    (OUT / "open_items.md").write_text(f"""# PHASE 0M-R2 --- OPEN ITEMS

Ranked. Every item is OPEN in the strict sense: not determined, and never defaulted.

## Blocking

| # | item | why open | what it blocks | what would close it |
|---|---|---|---|---|
| 1 | **ARCH_Z4 power-die construction** | no source describes a monolithic power-die process | the Z4 ranking, which is first place stacked and second planar | one process description, or a decision that the stacked construction is the design |
| 2 | **transitional-regime Nusselt correlation** | none in this repository for 2300 < Re < 3000 | any operating point above 27 g/s; the two neighbours differ by 2.76x | a sourced transitional correlation, or an explicit decision to cap the model at Re < 2300 |
| 3 | **area, routing and current-density shortfalls** | the converter area model outputs 5.61 mm2 per level against a 10.20 mm2 budget, and T4 exceeds it | realizability, more than the clearances do | a component topology the converter model supports |
| 4 | **three package clearances** | no framework source, no accessible foundry rule, nothing usable in the literature | calling any template buildable --- but NOT the binding constraint | a process design rule from a named vendor |
| 5 | **high-stress SAC305 constitutive response** | no primary data above about 16 MPa at 45-150 C | every absolute reliability number, and the MAGNITUDE of the relative one | coupon characterisation at 15-100+ MPa |
| 6 | **required life N_required** | not published for this system | the falsification gate G2 | a statement from the system owner |
| 7 | **mechanical allowable** | nine candidates tested, none admissible | turning the response into a constraint | a published allowable tied to a failure mode |
| 8 | **electromigration allowable** | no primary study with its conditions | a feasibility verdict on any via field | one primary EM study |
| 9 | **cohesive-zone parameters** | unsourced | predicting delamination at all | interface fracture testing |

## Non-blocking

| item | status |
|---|---|
| conjugate CFD validation | see `CONJUGATE_CFD_VALIDATION.md` |
| entrance-region Nusselt correlation | OPEN. At 27 g/s the entrance occupies 86 % of the channel, so the production temperature is conservative. Carried as a one-sided bound |
| density and specific heat of `hvr_effective` | OPEN. Needed only for transient claims; none are made |
| pump efficiency | OPEN. Hydraulic power is primary; a 35/55/75 % band is carried |
| polymer viscoelastic spectra | no DMA data; a modulus sensitivity is carried |
| trace-level RDL stress | needs explicit geometry, a declared averaging volume and a convergence study; no allowable exists for it anyway |

## Not open, and not to be relitigated

* **Z2 better than Z1 on the solder-fatigue driver** --- survives every Phase-0M-R2 correction, ratio 1.1942.
* **The TSV span per architecture** --- one source, enforced across all three domains.
* **DEFECT #54 and #55** --- both confirmed, fixed and negative-tested.
* **The production cooling point at 27 g/s** --- inside its correlation's validated domain.
* **Pumping power is FACILITY scope** --- not in the loss objective, not in the thermal mesh.
""")
    print(f"  Z1/Z2 = {ratio:.4f}")
    print(f"  wrote {OUT/'PHASE0MR2_REALIZABILITY_COOLING_STATE_CLOSURE.md'}, "
          f"open_items.md, optimizer_preconditions.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
