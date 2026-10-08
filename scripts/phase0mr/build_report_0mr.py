#!/usr/bin/env python3
"""Phase-0M-R Section 22 -- append the Phase-0M-R narrative to the HISTORICAL report and
re-splice every generated block.

The historical report is a HISTORY. Phase-0M-R does not rewrite what earlier phases said;
it adds its own section and refreshes the blocks that are explicitly generated from
`results/CURRENT_SCIENTIFIC_STATUS.yaml` and are designed to regenerate.
"""
from __future__ import annotations
import csv, json, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
MR = R / "results" / "phase0mr"
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
TAG = "phase0mr_narrative"


def rd(n):
    p = MR / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(r, k, d=4):
    try:
        return f"{float(r[k]):.{d}f}"
    except (KeyError, TypeError, ValueError):
        return str((r or {}).get(k, "--"))


def ff(r, k):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return float("nan")


REPL = [r for r in rd("production_architecture_replay.csv") if r.get("status") == "OK"]


def pick(a, mode, tpl="T1_EMBEDDED_4LAYER", cooler="27"):
    for r in REPL:
        if r["arch"] != a or r["mode"] != mode:
            continue
        if mode == "BEFORE" or (r.get("template") == tpl
                                and cooler in str(r.get("cooler", ""))):
            return r
    return None


def narrative() -> str:
    oc = json.loads((MR / "ordering_change.json").read_text())
    val = [r for r in rd("current_crowding_validation.csv") if r["kind"] == "transition"]
    coolv = rd("cooling_validation.csv")
    tpl = [r for r in rd("intravr_routing_by_template.csv")
           if r["n_layers"] == "9" and r["t_cu_um"] == "10.0"
           and r["via_policy"] == "D_area_optimal"]
    rdlm = [r for r in rd("rdl_mechanical_fidelity.csv") if r["arch"] == "RATIO"]
    A = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]
    z1a, z2a, z4a = (pick(x, "AFTER") for x in A)
    z1b, z2b, z4b = (pick(x, "BEFORE") for x in A)
    c50 = pick("ARCH_Z2_BACKSIDE", "AFTER", cooler="50")
    c2s = pick("ARCH_Z2_BACKSIDE", "AFTER", cooler="TWO_SIDED")
    FIG = str(MR)

    def drow(a):
        b, u = pick(a, "BEFORE"), pick(a, "AFTER")
        return (f"| {a.replace('ARCH_','')} "
                f"| {f(b,'P_elec_total_w',2)} -> **{f(u,'P_elec_total_w',2)}** "
                f"({100*(ff(u,'P_elec_total_w')-ff(b,'P_elec_total_w'))/ff(b,'P_elec_total_w'):+.1f} %) "
                f"| {f(b,'T_max_C',2)} -> **{f(u,'T_max_C',2)}** "
                f"({ff(u,'T_max_C')-ff(b,'T_max_C'):+.1f} K) "
                f"| {f(b,'die_warpage_pv_um',2)} -> **{f(u,'die_warpage_pv_um',2)}** "
                f"({100*(ff(u,'die_warpage_pv_um')-ff(b,'die_warpage_pv_um'))/ff(b,'die_warpage_pv_um'):+.1f} %) "
                f"| {f(b,'du_corner_um',4)} -> **{f(u,'du_corner_um',4)}** "
                f"({100*(ff(u,'du_corner_um')-ff(b,'du_corner_um'))/ff(b,'du_corner_um'):+.1f} %) |")

    return f"""<!-- BEGIN GENERATED: {TAG} -->

\\newpage

# Phase 0M-R --- production-coupling closure

Phase 0M ended by naming five first-order models that existed as validated SCREENING tools
and drove nothing. Phase 0M-R wired them into the production path and replayed a small frozen
architecture set through it, to ask one question: **which Phase-0M conclusions survive when
those models actually set P_elec, T(x,y,z) and M(x,y,z)?**

This is an integration and falsification gate, not a search. No optimizer was started and no
architecture DOE was run.

## What changed in the production path

| model | Phase 0M | Phase 0M-R |
|---|---|---|
| intra-VR routing | measured in Phase 0M, not yet summed | in the Phase-0M-R total, template-aware |
| transition resistance | one global constant, 1.326 | per class, solved exactly, cross-validated |
| cooling | inverse-calibrated Robin coefficient | physical microchannel with a streamwise coolant rise |
| heat deposition | one lumped load | per layer, energy-checked |
| temperature feedback | package maximum | the converter's own layer temperature |

## What integration did to the answers

| architecture | system loss (W) | peak temperature (C) | die warpage (um) | corner-joint shear (um) |
|---|---|---|---|---|
{chr(10).join(drow(a) for a in A)}

![FIG-0MR-I]({FIG}/FIG_0MR_I_before_after.png)

*FIG-0MR-I. The same three architectures through the Phase-0M production path and the
Phase-0M-R one. The bars that matter are the last pair: the reliability driver.*

## Orderings: two survive, two change, and only one change is physics

| metric | before | after | changed |
|---|---|---|---|
{chr(10).join(f"| {k} | {' < '.join(v['before'])} | {' < '.join(v['after'])} | **{'YES' if v['changed'] else 'no'}** |" for k, v in oc.items())}

Telling the two changes apart required the depth of each converter layer below the cooled
face: Z1 `tile_band` at 0.973 mm, Z2 `conv` at 1.273 mm, Z4 `interface` at 0.355 mm.

**The temperature reordering is REAL.** Z2's backside converter sits 0.3 mm deeper than Z1's.
Against a calibrated Robin boundary --- a near-isothermal sink over the whole top face ---
that depth was almost free and Z2 came out 1.56 K cooler than Z1. Against a physical cooler
with finite `h` and a caloric rise it costs 6.78 K at the peak. The signature confirms the
mechanism: 6.78 K at the peak against only 1.44 K in the mean is a depth penalty, not an
offset.

**The corner-shear reordering is CONDITIONAL and says nothing about Z4.** `zglobal.stack_for`
gives the Z4 power-die architecture no converter layer --- the Phase-0I global model never
represented that die geometrically --- so its heat lands in the `interface` layer only
0.355 mm below the cooler, far closer than a real Z4 power die would sit. Z4 heats by 13 K
where Z1 heats by 39 K, and overtakes it. Recorded as conditional.

**What survives is the ordering the project's claim rests on:** Z2 carries less corner-joint
shear than Z1 before integration ({f(z2b,'du_corner_um',4)} against {f(z1b,'du_corner_um',4)} um)
and after it ({f(z2a,'du_corner_um',4)} against {f(z1a,'du_corner_um',4)} um).

And one result that neither ordering shows on its own: **Z2 becomes the hottest architecture
and remains the best on the reliability driver.** Peak temperature and the fatigue driver do
not track, because the driver is set by CTE mismatch across a thin substrate rather than by
absolute temperature. A screening study that ranked on `T_max` alone would have ordered these
architectures wrongly for the metric that decides the design.

## Cooling is a design variable, not a boundary condition

| cooler | total flow | Z2 peak | Z2 driver | hydraulic pumping |
|---|---|---|---|---|
| single-sided microchannel | 27 g/s | {f(z2a,'T_max_C',2)} C | {f(z2a,'du_corner_um',4)} um | 14.7 W |
| single-sided microchannel | 50 g/s | {f(c50,'T_max_C',2)} C | {f(c50,'du_corner_um',4)} um | 74 W (7.4 % of load) |
| two-sided, equal total flow | 27 g/s | {f(c2s,'T_max_C',2)} C | {f(c2s,'du_corner_um',4)} um | 14.7 W |

Buying flow works: 27 to 50 g/s is worth {ff(z2a,'T_max_C')-ff(c50,'T_max_C'):.1f} K and
{100*(ff(z2a,'du_corner_um')-ff(c50,'du_corner_um'))/ff(z2a,'du_corner_um'):.1f} % of the driver. **Two-sided cooling at equal total flow is
worse, not better** ({ff(c2s,'T_max_C')-ff(z2a,'T_max_C'):+.1f} K): the second side faces the board rather than the die, so
diverting half the heat into a thermally remote path costs more than the added area returns.

The retired calibrated boundary was not a neutral simplification. Reaching its
h = 166 000 W/m2K needs 50 g/s and 1.46 MPa, and it hid roughly 40 K of optimism and 7.4 % of
the load in uncharged pumping.

![FIG-0MR-F]({FIG}/FIG_0MR_F_cooling.png)

*FIG-0MR-F. The physical cooling model: resistance chain, streamwise coolant temperature, and
what each candidate costs to pump.*

## Independent validation

| what | against | result |
|---|---|---|
| transition resistance, 5 geometries | MOOSE, independent mesher / formulation / solver | {f(min(val, key=lambda r: ff(r,'fv_vs_moose_pct')),'fv_vs_moose_pct',2)} to {f(max(val, key=lambda r: ff(r,'fv_vs_moose_pct')),'fv_vs_moose_pct',2)} %, **5/5 ACCEPTED** |
| uniform bar | analytic | exact at every mesh, in both codes |
| spreading resistance | analytic `rho/(4a)` | within 0.9 % |
| cooling solid side | MOOSE with explicit fins | {sum(1 for r in coolv if r['verdict']=='ACCEPTED')}/{len(coolv)} ACCEPTED; one REJECTED at 10.11 %; production geometry {f(coolv[0],'error_pct',2)} % |
| cooling fluid side | analytic energy balance | exact |
| loss decomposition | the upstream aggregate | machine precision, or the ledger refuses to total |

The first cross-solver run **failed**, at 12.1 % and 18.7 % on the narrow-trace cases. The
cause was MOOSE's centroid-based subdomain assignment staircasing the trace, and the
disagreement tracked trace width and changed sign in the predicted direction each time. Mesh
alignment is now part of every case definition and each run reports the block volumes the
independent solver actually meshed.

![FIG-0MR-C]({FIG}/FIG_0MR_C_transition_decomposition.png)

*FIG-0MR-C. Transition resistance per class, and the cross-solver agreement.*

## Four Phase-0M statements are narrowed; none is withdrawn

* **"intra-VR routing is common mode across architectures"** --- true only at fixed component
  topology. Across partition templates it varies **7.5 %**, because a template that splits by
  voltage domain puts the 16 V intermediate rail across the tier boundary instead of the 1 V
  rail and its vertical metallization loss collapses by three orders of magnitude.
* **"the RDL is 153x to 276x anisotropic"** --- that is IN-PLANE, for a single-direction line
  layer. Every realistic organisation --- orthogonal, mesh, plane --- is in-plane isotropic to
  solver precision. The real anisotropy is **through-thickness, 57x to 270x**, in the opposite
  sense. Adding the RDL to the mechanical mesh moves the Z1/Z2 ratio from
  {f(rdlm[0],'du_corner_um',4)} to {f(rdlm[2],'du_corner_um',4)}, at most {max(abs(ff(r,'ratio_shift_pct')) for r in rdlm):.2f} %.
* **"`dR` is the excess resistance"** --- it is a **difference against a stated 1-D reference**
  with identical terminals, and at the nominal TSV geometry it is NEGATIVE. The retired
  constant was inflating that tier by 32.6 %.
* **"TSV radius is not a lever"** --- not a FIELD-LOSS lever under minimum-capability
  provisioning with a geometry-independent `J_design`. It is decisively a **feasibility**
  variable: at 300 um only r >= 15 um is buildable at a 10:1 aspect limit, and 15 um is the
  reference radius, so the source geometry sits exactly ON the limit.

![FIG-0MR-E]({FIG}/FIG_0MR_E_rdl_tensor.png)

*FIG-0MR-E. The RDL effective tensor by stack organisation. The in-plane ratio is 1.00
everywhere except single-direction lines.*

## Verdict

Of the seven candidates, **C** is the one the evidence supports as dominant: **production
coupling preserves the deciding architecture ordering; absolute responses change materially.**
**A** is not earned --- six items remain OPEN and blocking and no partition template is
realizable. **B** would report a modelling substitution as a physical reordering. **D** is
largely true and is the single largest contributor, but the question this gate had to settle
was what integration does to the ordering. **E** fails on measurement. **F** is contradicted
by 5/5 acceptance against an independent solver. **G** was Phase 0M's verdict and this phase
closed five of the models it named.

The optimizer remains **FORBIDDEN**. One precondition moved from NO to YES and two to PARTIAL;
four remain NO, and any one of them is sufficient.

![FIG-0MR-K]({FIG}/FIG_0MR_K_closure_ladder.png)

*FIG-0MR-K. What is closed, what is conditional and what is open, after Phase 0M-R.*

<!-- END GENERATED: {TAG} -->
"""


def main() -> int:
    s = REP.read_text()
    body = narrative()
    pat = rf"<!-- BEGIN GENERATED: {TAG} -->\n.*?<!-- END GENERATED: {TAG} -->\n"
    if re.search(pat, s, re.S):
        s = re.sub(pat, lambda _m: body, s, count=1, flags=re.S)
        print("  ok  phase0mr narrative: replaced in place")
    else:
        anchor = "<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml"
        i = s.index(anchor)
        s = s[:i] + body + "\n" + s[i:]
        print("  ok  phase0mr narrative: inserted before the generated status block")

    gs = (R / "results" / "phase0g" / "generated_status_sections.md").read_text()
    start = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    m = re.search(r"\n+\\newpage\n+# References", s[start:])
    assert m, "generated status block boundary not found"
    s = s[:start] + gs.rstrip("\n") + s[start + m.start():]
    print("  ok  generated status block: refreshed")

    s = s.replace("## Current scientific status (Phase 0M)\n",
                  "## Current scientific status (Phase 0M-R)\n")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
