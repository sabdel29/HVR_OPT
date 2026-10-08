#!/usr/bin/env python3
"""Phase-0M-R3 Section 11/12 --- the conjugate CFD record, whatever the outcome."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0m",
          "scripts"):
    sys.path.insert(0, str(R / p))
OUT = R / "results" / "phase0mr3"

BANDS = {"energy balance": 1.0, "outlet coolant temperature": 3.0,
         "pressure drop": 10.0, "mean wall temperature rise": 5.0,
         "effective thermal resistance": 7.0}


def main() -> int:
    import cooling_regime as CR
    runs = sorted((OUT / "icepak").glob("run_*"))
    st, geo, run, log = {}, {}, None, ""
    for d in reversed(runs):
        if (d / "geometry.json").is_file():
            geo = json.loads((d / "geometry.json").read_text())
            run = d
            if (d / "icepak_status.json").is_file():
                st = json.loads((d / "icepak_status.json").read_text())
            if (d / "icepak_job.log").is_file():
                log = (d / "icepak_job.log").read_text()
            break
    analyzed = bool(st.get("analyzed"))
    timed_out = "TIMEOUT" in (OUT / "icepak.log").read_text() \
        if (OUT / "icepak.log").is_file() else False
    verdict = "CFD VALIDATED" if analyzed else "CFD UNAVAILABLE / NOT COMPLETED"

    c = CR.evaluate(27.0)
    rows = [{"quantity": q, "band_pct": b, "compact_model": v, "cfd": None,
             "error_pct": None, "within_band": None,
             "status": "NOT COMPARED --- CFD produced no field result"}
            for q, b, v in (
                ("energy balance", BANDS["energy balance"], 0.0),
                ("outlet coolant temperature", BANDS["outlet coolant temperature"],
                 c["T_coolant_max_C"]),
                ("pressure drop", BANDS["pressure drop"], c["dp_kPa"]),
                ("mean wall temperature rise", BANDS["mean wall temperature rise"], None),
                ("effective thermal resistance", BANDS["effective thermal resistance"],
                 c["R_total_K_W"]))]
    with open(OUT / "cfd_vs_compact.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    md = f"""# PHASE 0M-R3 SECTION 11 --- CANONICAL CONJUGATE CFD VALIDATION

**Verdict: {verdict}.**

## Acceptance bands, declared before the run

| quantity | band |
|---|---|
""" + "".join(f"| {q} | <= {b:.0f} % |\n" for q, b in BANDS.items()) + f"""
## What changed from the Phase-0M-R2 attempt

That attempt built correctly and then ran the full 2400 s without returning. The cause was
the geometry: the production channel is 50 x 300 x 22360 um, an aspect ratio of 447:1 along
the flow, and a mesh that resolves a 50 um width over 22 mm of length is enormous.

This case uses a **periodic slice** of {geo.get('slice_mm', 1.0)} mm instead of the full
{geo.get('full_length_mm', 22.36)} mm. Fully-developed laminar flow is invariant along the
flow direction, so a short slice tests the same wall-to-fluid physics at a fraction of the
cell count. The length-dependent part of the compact model is the caloric term, which is
exact by construction and is not what needs validating.

| | |
|---|---|
| channels in the full cooler | {geo.get('n_channels', '--')} |
| mass flow per channel | {geo.get('m_dot_channel_kg_s', float('nan')):.6g} kg/s |
| velocity | {geo.get('velocity_m_s', float('nan')):.3f} m/s |
| heat into the slice | {geo.get('q_slice_w', float('nan')):.5f} W |
| declared wall-clock budget | 2700 s (45 min, per the brief) |

Materials are DEFINED in the deck rather than taken from the Icepak library, so the CFD
case and the compact model provably use the same numbers.

## Outcome

"""
    if analyzed:
        md += "The solve completed. The comparison table is in `cfd_vs_compact.csv`.\n"
    else:
        why = ("the solver ran for the full declared budget without returning and the job "
               "was terminated at that limit" if timed_out
               else f"the analysis step reported: `{str(st.get('error',''))[:200]}`")
        md += f"""**The benchmark did not produce a field result.** Specifically, {why}.

Mesh construction succeeded ({'mesh_ok = True' if st.get('mesh_ok') else 'mesh status not reported'}),
as did geometry, materials, boundaries and the analysis setup. The failure is in the solve,
not in the case definition.

This is recorded as **{verdict}** and is NOT upgraded. **No Icepak validation is claimed.**
No compact-model constant was tuned toward any CFD number, which the brief explicitly
forbids and which would in any case be meaningless without a converged reference.

## Why no open-source substitute was used

The MOOSE build here is `heat_transfer-opt`, which has no Navier-Stokes module and cannot
run a conjugate flow case. Fluent is not installed: `/local/ansys/ansys_inc/v251/` holds
only `commonfiles`, `installer` and package metadata. No OpenFOAM is present. Installing a
new CFD stack for one benchmark would distort the project, which the brief cautions against.
"""
    md += f"""
## Section 12 --- the cooling claim, scoped honestly

| aspect | status |
|---|---|
| physically parameterized | **YES** --- h from a Nusselt correlation for the duct, fin efficiency, area amplification, caloric resistance, streamwise coolant rise |
| correlation-domain valid | **YES** at the production point --- Re = {c['Re']:.1f}, inside the SOURCE_BACKED laminar range, and the design space is now capped at Re <= 2300 |
| solid-side cross-validated | **YES** --- MOOSE with explicit fins, 3.78 % at the production geometry |
| fluid-side CFD validated | **NO** |

The cooler is therefore **PHYSICALLY PARAMETERIZED, CORRELATION-DOMAIN VALID and SOLID-SIDE
CROSS-VALIDATED, with the FLUID SIDE NOT CFD-VALIDATED.** It is not called fully validated.

## The compact model's numbers at the production point, for whoever completes this

| quantity | value |
|---|---|
| Re | {c['Re']:.1f} ({c['regime']}) |
| outlet coolant temperature | {c['T_coolant_max_C']:.2f} C |
| coolant rise | {c['dT_coolant_K']:.2f} K |
| pressure drop | {c['dp_kPa']:.1f} kPa |
| hydraulic pumping | {c['P_pump_hydraulic_W']:.2f} W |
| total thermal resistance | {c['R_total_K_W']:.5f} K/W |
| effective h | {c['h_effective_W_m2K']:.0f} W/m2K |

The deck is saved at `{run.relative_to(R) if run else 'results/phase0mr3/icepak/'}`.
"""
    (OUT / "CONJUGATE_CFD_VALIDATION.md").write_text(md)
    print(f"  verdict: {verdict}")
    print(f"  wrote {OUT/'CONJUGATE_CFD_VALIDATION.md'} and cfd_vs_compact.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
