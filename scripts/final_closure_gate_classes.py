"""Classify every OPEN physical gate by what it blocks.

The standing rule "no physical ETM until every OPEN gate closes" had become
self-defeating: several OPEN gates concern qualification quantities -- an
EM-safe allowable, a vendor microvia rating, an absolute solder life -- that no
academic architecture comparison can supply, so the rule would freeze the paper
forever. This replaces it with three classes:

  A  PAPER-CRITICAL     must close before the final Z1/Z2 comparison, because
                        it can move loss, heat map, temperature, warpage, the
                        joint driver, or the ordering
  B  PAPER-SENSITIVITY  no single value exists; the paper proceeds over a
                        declared range and must show the ordering is robust
  C  QUALIFICATION      cannot block an academic comparison; it limits which
                        CLAIMS may be made, not whether results may be computed

Every OPEN gate must receive exactly one class; an unclassified OPEN gate fails.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
OUT = R / "research" / "final_closure"
OUT.mkdir(parents=True, exist_ok=True)

CLASSES = {
    # ---------------- A: must close --------------------------------------
    "elec.intravr_horizontal_recomputed": ("A", "intra-VR metal was ~3.6 W historically -- "
        "a few percent of total loss deposited in the converter tier"),
    "elec.intravr_vertical_recomputed": ("A", "a physical conductor with no owner value; "
        "closed alongside the horizontal term"),
    "elec.package_rdl_lv_recomputed": ("A", "1 V spreading at ~20 A per cell; I^2R on the "
        "highest-current rail cannot be left unowned"),
    "elec.bga_loss_recomputed": ("A", "closes per named HV scenario now that network sharing "
        "is solved; needed by the ledger"),
    "elec.energy_conservation_verified": ("A", "the heat map must deposit exactly the "
        "electrical loss; without it temperatures inherit any bookkeeping error"),
    "elec.loss_audit_frozen": ("A", "the frozen physical ledger IS the electrical result"),
    "elec.tsv_resistance_temperature_dependent": ("A", "Z2 carries ~1000 A through its "
        "TSV field; rho(T) belongs inside the E-T fixed point"),
    "tsv.fe_copper_representation": ("A", "the FE substrate must hold the same Cu as the "
        "electrical TSV field or the two models describe different packages"),
    "mat.rdl_tensor_transfer_validated": ("A", "a four-layer stack tensor was applied to a "
        "single 10 um tier; it sits in every heat path"),
    "therm.tier_aware_heat_map": ("A", "converter loss placed in the tiers that produce it"),
    "therm.bc_selected": ("A", "one declared physical boundary for the comparison"),
    "therm.et_fixed_point_converged": ("A", "the physical temperature result"),
    "mech.mesh_convergence": ("A", "convergence of the final warpage and joint driver"),
    "mech.bga_528_site_search": ("A", "the critical joint must be found, not assumed"),
    "local.solder_rerun_at_new_critical_site": ("A", "local response at the actual critical "
        "joint of the physical lineage"),
    "results.physical_etm_lineage": ("A", "the paper's active result"),
    # ---------------- B: sensitivity -------------------------------------
    "elec.hv_input_waveform": ("B", "not derivable from the pinned converter model; carried "
        "as named scenarios HV-S0/S1/S2, each solved"),
    "elec.hv_waveform_determination": ("B", "determined unresolvable from available sources; "
        "the paper is scenario-conditioned"),
    "elec.z1_hv_rms_current": ("B", "scenario-conditioned, see elec.hv_input_waveform"),
    "elec.bga_rms_current": ("B", "scenario-conditioned, see elec.hv_input_waveform"),
    "elec.individual_branch_waveforms": ("B", "branch ripple needs the switch schedule; the "
        "HV side is carried per scenario and the LV side uses the output-ripple RMS"),
    "elec.pad_count_criterion": ("B", "no transferable EM allowable; bounded by a terminal "
        "footprint sweep anchored on the DVPD source's own VIC count"),
    "elec.pad_loss_closed": ("B", "bounded over the footprint sweep"),
    "elec.contact_resistance_bounded": ("B", "rho_c swept over three declared decades"),
    "elec.rdl10um_electrical_model": ("B", "Cu thickness and occupancy swept over declared "
        "cases; the source defers trace dimensions to process technology"),
    "tsv.density_sensitivity_run": ("B", "electrical minimum vs adopted vs high density"),
    "board.eta_sensitivity_run": ("B", "board Cu coverage sensitivity"),
    "board.h1_meshed": ("B", "H0 homogenised board is the production board; H1 is the "
        "check of that choice"),
    "board.h1_thermal_validated": ("B", "see board.h1_meshed"),
    "therm.h0_h1_compared": ("B", "see board.h1_meshed"),
    "board.t_only_comparison_run": ("B", "2.4 vs 3.2 mm board thickness"),
    "mech.t_only_mechanical": ("B", "2.4 vs 3.2 mm board thickness, mechanics"),
    "mech.f1_f2_bracket_run": ("B", "out-of-cell fill: encapsulated vs void"),
    "therm.z2_passive": ("B", "an alternative Z2 boundary; the comparison uses one declared "
        "boundary for both architectures"),
    "therm.z2_cooled": ("B", "see therm.z2_passive"),
    "mat.gan_bounded": ("B", "GaN epi thermal contribution, material range"),
    "mat.mlcc_bounded": ("B", "flying-cap tier material, material range"),
    "mat.inductor_tier_bounded": ("B", "inductor/Cout tier material, material range"),
    # ---------------- C: qualification -----------------------------------
    "lit.tsv_allowable": ("C", "an EM-safe TSV current density is a qualification quantity; "
        "no transferable value exists and none is claimed"),
    "elec.microbump_loss_recomputed": ("C", "microbump is the ALTERNATIVE interface "
        "technology; the primary path is the source Cu pad"),
    "elec.microbump_geometry_closed": ("C", "alternative interface technology only"),
    "lit.microbump_contact_bounded": ("C", "alternative interface technology only"),
    "therm.mot_tg_evaluated": ("C", "board maximum-operating-temperature check is a "
        "qualification screen; reported if computed, never used to rank"),
}


def classify(gates):
    """Every OPEN gate gets A/B/C; a B gate also carries its subtype (B1 ordering-
    relevant, B2 magnitude-only, B3 reclassify to C) and resolution status from
    classB_resolution.json, the single record of how each B gate was run or bounded."""
    cb = OUT / "classB_resolution.json"
    sub = {g["gate"]: g for g in json.loads(cb.read_text())["gates"]} if cb.exists() else {}
    rows = []
    for g in gates:
        if g["status"] != "OPEN":
            continue
        cls, why = CLASSES.get(g["id"], (None, None))
        b = sub.get(g["id"], {})
        rows.append({"id": g["id"], "area": g["area"], "gate": g["gate"],
                     "class": cls, "rationale": why,
                     "b_subtype": b.get("new_subtype") if cls == "B" else None,
                     "b_resolved": b.get("resolved") if cls == "B" else None,
                     "b_status": b.get("final_status") if cls == "B" else None})
    return rows


def main():
    gates = json.loads((R / "research/phase0nw/physical_gates.json").read_text())["gates"]
    rows = classify(gates)
    missing = [r["id"] for r in rows if r["class"] is None]
    if missing:
        raise SystemExit(f"UNCLASSIFIED OPEN gates: {missing}")
    stale = sorted(set(CLASSES) - {r["id"] for r in rows})
    with (OUT / "paper_gate_classification.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    summary = {k: sum(1 for r in rows if r["class"] == k) for k in "ABC"}
    (OUT / "paper_gate_classification.json").write_text(json.dumps(
        {"summary": summary, "n_open": len(rows),
         "classified_but_no_longer_open": stale, "rows": rows}, indent=2))
    print("OPEN gates:", len(rows), summary, "| closed since classification:", stale)


if __name__ == "__main__":
    main()
