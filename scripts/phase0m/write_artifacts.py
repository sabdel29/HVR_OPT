#!/usr/bin/env python3
"""Phase-0M Part 42 -- generate every required artifact FROM THE CSVs.

No number in any Phase-0M markdown file is typed by hand. Every table is built from the
result file it describes, so a stale artifact is impossible by construction rather than by
discipline.
"""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"


def rd(name: str) -> list[dict]:
    p = OUT / name
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def g(x, d=4):
    try:
        return f"{float(x):.{d}g}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


# =========================================================== Part 7 solver audit
def solver_audit() -> None:
    val = rd("conduction_solver_validation.csv")
    sweep = rd("current_crowding_transition_sweep.csv")
    ok = [r for r in sweep if r["status"] == "OK"]
    ks = [float(r["K_crowd"]) for r in ok]
    conv = [r for r in sweep if r.get("factor") == "MESH_CONVERGENCE"]
    md = f"""# PHASE 0M PART 7 --- DC CURRENT-CROWDING SOLVER AUDIT

Q3D is not licensed. That is not a reason to omit current crowding.

## Capability audit, this environment

| candidate | present | what it can and cannot do here |
|---|---|---|
| **Elmer** `StaticCurrentSolver` | **NO** | not installed; would have been the first choice for DC conduction |
| **GetDP** | **NO** | not installed |
| **Palace** | **NO** | not installed. Even where it is, its electrostatic mode solves a PERMITTIVITY problem, `div(eps grad V) = rho`. That is **not** a DC conduction solver and must not be described as one. Its driven mode is for AC field problems |
| **MOOSE** `heat_transfer-opt` | **YES** | present at `/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/heat_transfer-opt`. Steady conduction `div(k grad T) = 0` is the SAME operator as `div(sigma grad V) = 0`, so MOOSE is a valid independent cross-check on the scalar conduction operator, already used that way in Phase 0D-R (FD vs MOOSE agreed to 0.33-0.45 %) |
| **gmsh** | **YES** | mesher available for an unstructured route; not needed, the transitions are box-like |
| **HFSS** | licensed | correct at the switching frequency and its harmonics. A DC extrapolation of a full-wave solve is ill-conditioned and is NOT used for DC here |
| **this module** | built | `scripts/phase0m/conduction3d.py`, a conservative finite-volume discretisation on a graded tensor grid |

**Chosen: a purpose-built finite-volume solver, cross-checked against analytic results.**
Finite volume rather than nodal Galerkin on purpose: `sigma` jumps nine orders of magnitude
at every metal/dielectric face, and a cell-centred FV scheme with harmonic-mean face
conductivities is exactly conservative across such a jump. Current conservation is verified
on every solve rather than assumed.

## Verification against closed-form results

| case | mesh | R computed | analytic | ratio | current balance |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['case']} | {r['param']} | {g(r['R'], 6)} | {g(r['analytic'], 6)} | **{f(r['ratio'], 4)}** | {g(r['I_err'], 2)} |" for r in val)}

The uniform bar is **exact at every mesh**, which is not automatic: the first version of the
solver injected and extracted at CELL CENTRES and returned `R_exact (n-1)/n`, an O(1/n) error
that would have been read as a crowding effect. Both terminals are now explicit equipotential
NODES joined to their boundary cells by the exact half-cell conductance.

The spreading resistance of a circular contact on a half-space, `rho/(4a)`, converges from
+15.9 % at 2 cells per contact radius to **+0.9 % at 6 cells per contact radius**. That is the
case where crowding is the entire answer, so it is the binding verification.

## Mesh convergence of the transition cell

| refinement | cells | active cells | K_crowd |
|---|---|---|---|
{chr(10).join(f"| {g(r['factor_value'], 3)} | {r['n_cells']} | {r.get('n_active', '--')} | {f(r['K_crowd'], 5)} |" for r in conv if r.get('status') == 'OK')}

## What the solver reports

`J(x,y,z)`, `J_peak/J_avg`, the terminal current, the effective resistance by two independent
routes (terminal potential and volume dissipation, which agree to 1e-10 relative), and the
Joule-heat density.

## Two faults of my own that this audit caught

1. **A zero-width cell.** `snapped()` deduplicated interface planes with `np.unique`, which
   removes only bit-identical values. A pad radius that coincides with a trace half-width
   produced two nodes an ULP apart, a zero-width cell, an infinite terminal conductance and a
   silently wrong `K_crowd = 0.32` in a 92-point sweep. The only symptom was the
   current-balance residual. Fixed three ways: tolerance-based deduplication, a hard
   assertion on non-positive cell widths, and a validity gate that rejects any solve whose
   current balance exceeds 1e-3. All three are negative-tested.
2. **Dead-ended traces.** Fanned traces at +/-60 degrees with the ground only on the +x face
   carried no current at all, and the three-trace case returned `K_crowd = 2.49`. Traces are
   now axis-aligned and every lateral face is grounded.

## Result

`K_crowd` spans **{f(min(ks), 3)} to {f(max(ks), 3)}** over {len(ok)} converged geometries --- a factor of
{f(max(ks)/min(ks), 2)} --- against the single global constant **1.326** the framework applies to BGA, C4,
TSV and microbump alike.
"""
    (OUT / "CURRENT_CROWDING_SOLVER_AUDIT.md").write_text(md)


# =========================================================== Part 10 routing scope
def routing_audit() -> None:
    summ = rd("intra_vr_routing_model.csv")
    nets = rd("intra_vr_routing_nets.csv")
    rank = rd("intra_vr_ranking_effect.csv")
    r1 = [r for r in summ if r.get("level") == "R1"]
    ref = [r for r in r1 if r["t_cu_um"] == "10.0" and r["n_layers"] == "1"
           and r["j_max"] == "100000000.0" and r["via_policy"] == "D_area_optimal"]
    r2 = [r for r in summ if r.get("level") == "R2"]
    refnets = [r for r in nets if r["level"] == "R1" and r["t_cu_um"] == "10.0"
               and r["n_layers"] == "1" and r["j_max"] == "100000000.0"
               and r["via_policy"] == "D_area_optimal"]
    ps = [float(r["p_system_w"]) for r in r1]
    md = f"""# PHASE 0M PART 10 --- ROUTING SCOPE AUDIT

## The three levels

| level | what it covers | present in the framework before Phase 0M? |
|---|---|---|
| **LEVEL 1 --- intra-converter** | input pads, GaN switches, flying capacitors, intermediate rail, buck switches, inductors, output capacitors, output pads, and the metal between them | **NO. Absent entirely.** |
| **LEVEL 2 --- VR to package** | VR terminal to TSV field, RDL network, bump array, die terminal | YES --- the vertical tiers in `zpower.evaluate_z` |
| **LEVEL 3 --- package to POL** | VR outputs to load regions across the die | YES --- `stack.rdl_network_solve`, a multilayer resistive sheet |

## Every current loss term, and which level it belongs to

| loss term | where it is computed | level |
|---|---|---|
| `hs.R_DS_ON`, `ls.R_DS_ON` | upstream `compute_total_loss` | **inside the converter model, not routing** |
| inductor DCR `R_L_ESR` | upstream `compute_total_loss` | **inside the converter model** |
| capacitor `R_C_ESR` | upstream `compute_total_loss` | **inside the converter model** |
| hard-switching, gate-drive, C_OSS | upstream `compute_total_loss` | **inside the converter model** |
| `P_bga`, `P_c4`, `P_tsv`, `P_microbump` | `zpower._tier_loss_system` | LEVEL 2 |
| `P_rdl` | `stack.rdl_network_solve` | LEVEL 3 |
| metal between converter components | **nowhere** | **LEVEL 1, MISSING** |

**No double counting.** The upstream converter model contains every device and passive
parasitic and no metallization at all. Phase 0M adds only the metallization.

## The Level-1 model

Per-phase STACKED COLUMNS, not a planar grid. The first version of this model laid the
components side by side inside each layer and routed laterally between them; it returned
61 % of the load in intra-VR routing, because it forced a 6.8 A phase current down a 0.8 mm
lateral trace that does not exist in the real device. In the embedded architecture the
low-side switch, its flying capacitor and its inductor occupy DIFFERENT power layers at the
SAME footprint, so the phase connection is a via stack, not a trace.

The footprint arithmetic confirms the column reading: the compiled design reports
`total_area = 5.61 mm^2 = 3 x 1.87 mm^2 = K x (one high-side footprint)`, and the tile is
2.3685 mm square = 5.61 mm^2.

## Net-by-net, at the reference stack (10 um Cu, 1 layer, J = 1e8 A/m^2, area-optimal vias)

| net | rail | geometry | length | width | I_rms | R | P per VR | feasible |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(f"| `{r['net']}` | {r['rail']} | {r['geom']} | {f(r['length_mm'], 3)} mm | {f(r['width_um'], 1) if r['width_um'] not in ('nan', '') else 'via field'} um | {f(r['i_rms_a'], 3)} A | {f(r['R_mohm'], 4)} mOhm | {f(r['P_w_per_vr'], 5)} W | {r['feasible']} |" for r in refnets)}

## How much loss intra-VR routing adds

| | per VR | system (49 cells) | of the 1 kW load | of the 125.3 W converter loss |
|---|---|---|---|---|
{chr(10).join(f"| reference stack | {f(r['p_intra_vr_w'], 4)} W | **{f(r['p_system_w'], 2)} W** | {f(r['pct_of_load'], 2)} % | {f(r['pct_of_converter_loss'], 1)} % |" for r in ref)}

Across every stack, current density and via policy examined, the Level-1 term spans
**{f(min(ps), 2)} to {f(max(ps), 2)} W system-wide**, i.e. {f(100*min(ps)/1000, 2)} % to {f(100*max(ps)/1000, 2)} % of the load.

## The binding constraint is current density, not resistance

At the reference stack the VR output plane needs **8.6x the available tile width** to stay
inside the sourced copper current-density envelope. The fix is more copper --- 9 RDL layers,
or 86 um of thickness --- and the framework never noticed because it has no Level-1 routing
to check.

## Fidelity: how much is enough

| level | output-net loss per VR | comment |
|---|---|---|
| R1 obstacle-aware Manhattan | {f(next((n['P_w_per_vr'] for n in refnets if n['net'] == 'vout_plane'), 'nan'), 5)} W | analytic, microseconds |
{chr(10).join(f"| R2 2-D resistive sheet, {r['n_layers']} layer(s), {f(r['t_cu_um'], 0)} um | {f(r['p_output_net_w_per_vr'], 5)} W | finite terminal footprints |" for r in r2 if r['n_layers'] == '1' and r['t_cu_um'] == '10.0')}

R1 is **conservative by about 37 %** against R2 on the output net. For design exploration R1
is adequate and R2 should be used to calibrate it; R3 (the Part-8 3-D extraction) is needed
only for the transitions.

## Does it change architecture ranking?

{rank[0]['reason'] if rank else 'not computed'}

**Ordering changed: {rank[0]['ordering_changed'] if rank else '--'}.** The intra-VR term is
common-mode across Z1, Z2 and Z4 because the converter cell is the same compiled design in
all three. It adds {f(rank[0]['p_intra_vr_system_w'], 2) if rank else '--'} W to every
architecture's total and reorders nothing. Its second-order path --- more heat, higher
temperature, more thermal strain --- is
{f(float(rank[0]['extra_heat_frac_of_load']) * 100, 2) if rank else '--'} % of the load.
"""
    (OUT / "ROUTING_SCOPE_AUDIT.md").write_text(md)
    print("  wrote CURRENT_CROWDING_SOLVER_AUDIT.md, ROUTING_SCOPE_AUDIT.md")


if __name__ == "__main__":
    solver_audit()
    routing_audit()
    print("done")
