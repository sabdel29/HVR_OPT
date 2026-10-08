#!/usr/bin/env python3
"""Phase-0M-R Section 19 -- the fidelity and uncertainty ledger.

Every new quantity carries a FIDELITY class and its uncertainty is attributed to a SOURCE.
Common-mode terms are never RMS-summed with independent ones: for an architecture RATIO the
cancellation is TESTED, not assumed, and the tested value is what appears.
"""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr"

FIDELITY = ("SOURCE_BACKED", "ANALYTICALLY_DERIVED", "NUMERICALLY_VALIDATED",
            "INDEPENDENTLY_CROSS_VALIDATED", "CONDITIONAL", "OPEN")
KIND = ("numerical", "material", "geometry", "model-form", "boundary-condition", "source")

ROWS = [
    dict(quantity="TSV field resistance R = rho h J / I",
         fidelity="ANALYTICALLY_DERIVED", uncertainty_kind="model-form",
         magnitude="exact under the stated allocation policy; 0.07 % over a 20x radius range",
         common_mode="YES across architectures -- same tier model",
         cancels_in_ratio="TESTED: yes", evidence="tsv_geometry_production_audit.csv"),
    dict(quantity="J_design", fidelity="SOURCE_BACKED", uncertainty_kind="source",
         magnitude="1.0e8 A/m2 (June-2026); envelope to 4.0e8 (ECTC-2024), a factor of 4",
         common_mode="YES", cancels_in_ratio="TESTED: yes",
         evidence="configs/phase0e/physical_stack.yaml"),
    dict(quantity="J_reliability_allow", fidelity="OPEN", uncertainty_kind="source",
         magnitude="UNBOUNDED -- no primary EM study retrievable",
         common_mode="n/a", cancels_in_ratio="n/a",
         evidence="results/phase0mr/TSV_GEOMETRY_INTERPRETATION.md"),
    dict(quantity="transition resistance dR per class",
         fidelity="INDEPENDENTLY_CROSS_VALIDATED", uncertainty_kind="numerical",
         magnitude="0.25 to 0.73 % against MOOSE on 5 geometries; FV mesh drift 0.03-0.26 %",
         common_mode="PARTIAL -- same classes appear in every architecture but with "
                     "different currents",
         cancels_in_ratio="TESTED: largely", evidence="current_crowding_validation.csv"),
    dict(quantity="intra-VR routing loss", fidelity="NUMERICALLY_VALIDATED",
         uncertainty_kind="geometry",
         magnitude="4.97 to 5.34 W across templates at a fixed stack, 7.5 %; 4.06 to 39.31 W "
                   "across stacks",
         common_mode="MOSTLY -- 7.5 % template-dependent, measured not assumed",
         cancels_in_ratio="TESTED: 7.5 % residual",
         evidence="intravr_routing_by_template.csv"),
    dict(quantity="RDL in-plane conductivity", fidelity="NUMERICALLY_VALIDATED",
         uncertainty_kind="geometry",
         magnitude="92 to 335 W/m.K depending on stack organisation; the production model "
                   "uses 0.7",
         common_mode="YES", cancels_in_ratio="TESTED: yes",
         evidence="rdl_effective_tensor.csv"),
    dict(quantity="RDL mechanical contribution", fidelity="NUMERICALLY_VALIDATED",
         uncertainty_kind="geometry",
         magnitude="-3.6 % to +6.8 % on corner shear; <= 0.11 % on the Z1/Z2 ratio",
         common_mode="YES -- both architectures move the same way",
         cancels_in_ratio="TESTED: yes, to 0.11 %",
         evidence="rdl_mechanical_fidelity.csv"),
    dict(quantity="cooling: fluid side", fidelity="ANALYTICALLY_DERIVED",
         uncertainty_kind="boundary-condition",
         magnitude="energy balance exact; Nu correlation used only inside its Re range",
         common_mode="YES", cancels_in_ratio="TESTED: yes",
         evidence="cooling_energy_balance.csv"),
    dict(quantity="cooling: solid side", fidelity="NUMERICALLY_VALIDATED",
         uncertainty_kind="model-form",
         magnitude="3.78 % at the production geometry; 10.11 % for short thick fins, which "
                   "is REJECTED against the predeclared band",
         common_mode="YES", cancels_in_ratio="TESTED: yes",
         evidence="cooling_validation.csv"),
    dict(quantity="pump efficiency", fidelity="OPEN", uncertainty_kind="source",
         magnitude="not sourced; hydraulic power is primary and a 35/55/75 % band is carried",
         common_mode="YES", cancels_in_ratio="n/a",
         evidence="cooling_energy_balance.csv"),
    dict(quantity="high-stress SAC305 constitutive response",
         fidelity="CONDITIONAL", uncertainty_kind="material",
         magnitude="DOMINANT. Fitted on Sn3.9Ag0.6Cu over 7.51-15.92 MPa; 99.8 % of package "
                   "damage lies outside",
         common_mode="PARTIAL -- medians 1.5 % apart, peaks differ",
         cancels_in_ratio="TESTED: partially; the envelope is 1.19 to 1.22",
         evidence="results/phase0lr/ALLOY_TRANSFERABILITY_MATRIX.md"),
    dict(quantity="package clearances", fidelity="OPEN", uncertainty_kind="source",
         magnitude="three clearances unsourced; no template may be called buildable",
         common_mode="n/a", cancels_in_ratio="n/a",
         evidence="component_partition_feasibility.csv"),
    dict(quantity="Z4 power-die layer geometry", fidelity="OPEN",
         uncertainty_kind="geometry",
         magnitude="the global mesh has no Z4 converter layer; its heat is deposited in the "
                   "interface layer and the Z4 thermal result is conditional on that",
         common_mode="NO -- affects Z4 only", cancels_in_ratio="NO",
         evidence="scripts/phase0mr/production_et.py::converter_layer"),
    dict(quantity="mechanical allowable", fidelity="OPEN", uncertainty_kind="source",
         magnitude="none admitted since Phase 0H; G2 stays untestable",
         common_mode="n/a", cancels_in_ratio="n/a",
         evidence="results/phase0k/G2_DECISION_REGIONS.md"),
]


def main() -> int:
    for r in ROWS:
        assert r["fidelity"] in FIDELITY, r["quantity"]
        assert r["uncertainty_kind"] in KIND, r["quantity"]
    with open(OUT / "uncertainty_ledger.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0])); w.writeheader(); w.writerows(ROWS)
    import collections
    print(dict(collections.Counter(r["fidelity"] for r in ROWS)))
    print(dict(collections.Counter(r["uncertainty_kind"] for r in ROWS)))
    print(f"wrote {OUT/'uncertainty_ledger.csv'} ({len(ROWS)} quantities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
