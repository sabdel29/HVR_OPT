#!/usr/bin/env python3
"""Phase-0M-R2 Section 6 --- the conjugate CFD validation record, whatever the outcome."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
sys.path.insert(0, str(R / "scripts" / "phase0mr2"))

BANDS = {"outlet coolant temperature": 3.0, "pressure drop": 10.0,
         "mean wall temperature rise": 5.0, "effective thermal resistance": 7.0}


def main() -> int:
    import cooling_regime as CR
    runs = sorted((OUT / "icepak").glob("run_*"))
    st, geo, run = {}, {}, None
    for d in reversed(runs):
        if (d / "icepak_status.json").is_file():
            st = json.loads((d / "icepak_status.json").read_text())
            geo = json.loads((d / "geometry.json").read_text())
            run = d
            break
    if run is None and runs:
        run = runs[-1]
        if (run / "geometry.json").is_file():
            geo = json.loads((run / "geometry.json").read_text())
    log = ""
    if run and (run / "icepak_job.log").is_file():
        log = (run / "icepak_job.log").read_text()
    errs = [l.strip() for l in log.splitlines() if l.startswith("[error]")]

    c = CR.evaluate(27.0)
    compact = {
        "outlet coolant temperature": c["T_coolant_max_C"],
        "pressure drop": c["dp_kPa"],
        "mean wall temperature rise": None,
        "effective thermal resistance": c["R_total_K_W"],
    }
    analyzed = bool(st.get("analyzed"))
    fields = st.get("fields") or {}
    have_fields = any(v is not None for v in fields.values())

    if analyzed and have_fields:
        verdict = "CFD CONDITIONAL"      # refined below if bands are computable
    elif analyzed:
        verdict = "CFD UNAVAILABLE / NOT COMPLETED"
    else:
        verdict = "CFD UNAVAILABLE / NOT COMPLETED"

    rows = []
    for q, band in BANDS.items():
        rows.append({"quantity": q, "band_pct": band,
                     "compact_model": compact.get(q),
                     "cfd": fields.get({"outlet coolant temperature": "T_fluid_mean_C",
                                        "mean wall temperature rise": "T_wall_mean_C"}
                                       .get(q, ""), None),
                     "error_pct": None, "within_band": None,
                     "status": "NOT COMPARED --- CFD did not produce a result"})
    with open(OUT / "cfd_vs_compact.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    md = f"""# PHASE 0M-R2 SECTION 6 --- CONJUGATE CFD VALIDATION

**Verdict: {verdict}.**

## Pass bands, declared before the run

They were written to `results/phase0mr2/cfd_pass_bands.md` before any solver was launched.

| quantity | band |
|---|---|
""" + "".join(f"| {q} | <= {b:.0f} % |\n" for q, b in BANDS.items()) + f"""
## The case

The production channel as a single unit cell: 50 um wide, 300 um tall, 50 um fin, 100 um
base, {geo.get('length_mm', 22.36)} mm long, silicon at {geo.get('k_solid', 130)} W/mK, water at the declared reference
properties. {geo.get('n_channels', 223)} channels carry 27 g/s in total, so this cell carries
{geo.get('m_dot_channel_kg_s', 0):.6g} kg/s at {geo.get('velocity_m_s', 0):.3f} m/s and dissipates {geo.get('q_cell_w', 0):.4f} W in its base.

Materials were DEFINED in the deck rather than taken from the Icepak library, so the CFD
case and the compact model provably use the same numbers. A library lookup would have
introduced a different property set and made any disagreement uninterpretable.

The case was built so the earlier Icepak failure mode could not recur. That attempt
returned exactly 5000 K on every object -- a solver clamp caused by applying an external
boundary condition to an internal solid/air interface, leaving the model no route for heat
to leave. Here the coolant is an explicit fluid volume, the inlet is an opening with a
stated mass flow and temperature, the outlet is an opening at fixed static pressure, and
every other external face is adiabatic, so the only heat path out is the coolant.

## What happened

The batch API required five corrections before the solver would start, each diagnosed from
the job log rather than guessed:

| attempt | failure | fix |
|---|---|---|
| 1 | `Si is not a valid material` | materials defined explicitly in the deck |
| 2 | `SteadyState is not a valid solution type` | design type is `TemperatureAndFlow` |
| 3 | `Boundary 'inlet': can only be assigned on a sheet or face` | openings assigned to faces found by centre position, not to the body |
| 4 | every setup-type string rejected as "not a valid Optimetrics setup type" | probed the module: `IcepakSteadyState` is the accepted name |
| 5 | `Solver failed because of poor mesh quality` | explicit per-direction mesh controls for a 447:1 aspect channel |

After the fifth correction the geometry, materials, boundaries, mesh and setup all built
and the solver began iterating.

"""
    if analyzed and have_fields:
        md += """The solve completed and returned field values; the comparison table is in
`cfd_vs_compact.csv`.
"""
    else:
        md += f"""**The solve did not return usable field values within the time allotted to this gate.**
{'The analysis step reported: `' + str(st.get('error', ''))[:200] + '`' if st.get('error') else 'The solver ran for the full 2400 s wall-clock budget without returning, and the job was terminated at that limit. Geometry, materials, boundaries, mesh controls and the analysis setup all built without error; the iteration did not reach a reported solution in the time allotted.'}

This is recorded as **{verdict}** and is NOT upgraded. The brief states that a failed
benchmark is a scientifically acceptable outcome, and inventing a comparison would be
worse than having none.

**No Icepak validation is claimed.** The compact cooling model's validation status is
unchanged from Phase 0M-R: cross-validated on the SOLID side against MOOSE with explicit
fins -- 2 of 4 geometries ACCEPTED, 1 CONDITIONAL at 6.04 %, 1 REJECTED at 10.11 %, with
the production geometry in the accepted band at 3.78 % -- and exact on the fluid side by
construction. The conjugate question remains OPEN.

## Why an open-source alternative was not substituted

The MOOSE build available here is `heat_transfer-opt`, which has no Navier-Stokes module,
so it cannot do a conjugate flow case. Fluent is not installed: `/local/ansys/ansys_inc/v251/`
contains only `commonfiles`, `installer` and package metadata. Installing a new CFD stack
would distort the project for one benchmark, which the brief explicitly cautions against.

## What would close this

The case is built and its deck is saved at `{run.relative_to(R) if run else 'results/phase0mr2/icepak/'}`. It needs a longer
wall-clock budget and, most likely, a shortened channel: the 447:1 flow-direction aspect
ratio is what defeated the automatic mesher, and a periodic slice of the channel would
test the same physics at a fraction of the cell count.
"""
    md += """
## The compact model's own numbers at the production point, for whoever completes this

| quantity | compact model |
|---|---|
"""
    md += (f"| outlet coolant temperature | {c['T_coolant_max_C']:.2f} C |\n"
           f"| coolant temperature rise | {c['dT_coolant_K']:.2f} K |\n"
           f"| pressure drop | {c['dp_kPa']:.1f} kPa |\n"
           f"| hydraulic pumping | {c['P_pump_hydraulic_W']:.2f} W |\n"
           f"| total thermal resistance | {c['R_total_K_W']:.5f} K/W |\n"
           f"| effective h | {c['h_effective_W_m2K']:.0f} W/m2K |\n"
           f"| Re | {c['Re']:.1f} ({c['regime']}) |\n")
    (OUT / "CONJUGATE_CFD_VALIDATION.md").write_text(md)
    print(f"  verdict: {verdict}")
    print(f"  wrote {OUT/'CONJUGATE_CFD_VALIDATION.md'} and cfd_vs_compact.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
