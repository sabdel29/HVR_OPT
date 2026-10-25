"""PHASE 0N-AH --- model hierarchy, computational claims, and generality audit.

The framework is NOT "an analytical framework that replaces FEM/FVM". It is a
HIERARCHICAL analytical + reduced + numerical multiphysics framework: different physics
are solved at different fidelities, and the expensive solves are kept out of the inner
architecture loop rather than eliminated.

Verified against HEAD, not assumed: the production thermal path writes C3D8 elements and
runs CalculiX (scripts/phase0b/etm/ccxio.py:88), and the structural path writes C3D8I
(line 143). Both are FINITE ELEMENT. Calling either analytical would be wrong.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
OUT = R / "research" / "phase0nah"
OUT.mkdir(parents=True, exist_ok=True)

# stage, model, type, governing quantity, independent reference, error, evidence class
HIERARCHY = [
    ("converter synthesis", "closed-form HVR loss/ripple equations + enumeration",
     "ANALYTICAL", "device/passive loss ledger", "none", "", "VERIFICATION",
     "4.564", "1"),
    ("rail-aware power path", "terminal/segment graph with one owner per conductor",
     "NETWORK/ALGEBRAIC", "current ownership", "none", "", "VERIFICATION",
     "0.0001", "1"),
    ("BGA / pad / TSV bulk R", "rho L / A with parallel allocation",
     "ANALYTICAL", "conductor resistance",
     "DVPD Table III", "0.00 % pad, 3 % BGA, 1.6 % TSV", "VALIDATION", "<0.001", "1"),
    ("TSV transition", "bulk + two-ended constriction",
     "ANALYTICAL", "end/spreading resistance", "MOOSE", "0.25-0.73 %", "VALIDATION",
     "<0.001", "1"),
    ("package RDL", "2-D resistive sheet, G V = I",
     "REDUCED PDE / RESISTOR NETWORK", "R_eff, IR drop",
     "MOOSE (historical geometry)", "0.45-1.10 % power, 0.90-2.19 % IR",
     "VALIDATION", "~1", "1"),
    ("detailed current crowding", "cell-centred conservative finite volume",
     "FVM", "local current density", "rho L / A exact; MOOSE",
     "exact on uniform; +0.9 % spreading at 6 cells/radius", "VALIDATION", "", ""),
    ("homogenised materials", "explicit RVE homogenization",
     "REDUCED MATERIAL MODEL", "effective k, E, CTE", "numerical RVE",
     "k_z ~1 %, bump k_xy ~1.5 %", "VALIDATION", "", ""),
    ("cooling", "energy balance + fin efficiency + Nusselt correlation",
     "ANALYTICAL / COMPACT", "h, T_fluid", "MOOSE explicit fins",
     "3.78 % in-domain (10.11 % off-design REJECTED)", "VALIDATION", "0.01121", "1"),
    ("package thermal field", "CalculiX C3D8 conduction FE",
     "FEM", "T(x)", "none (commercial comparison not established)", "",
     "CONVERGENCE", "75.1 / 121.4", "48"),
    ("electrothermal coupling", "Picard fixed point",
     "ITERATIVE COUPLING", "self-consistent T and P", "none",
     "dT < 0.25 K in 3 iterations", "CONVERGENCE", "", "48"),
    ("global mechanics", "CalculiX C3D8I thermoelastic FE",
     "FEM", "warpage, joint displacement", "none", "0.50 % mesh convergence",
     "CONVERGENCE", "49.5 / 67.6", "48"),
    ("local solder", "displacement-driven viscoplastic FE submodel",
     "FEM (nonlinear)", "inelastic response", "none",
     "1.9 % mesh, 0.04-0.06 % cycle", "CONVERGENCE", "45.0 / 35.1", "48"),
]

CLAIMS = [
    ("analytical stages complete in milliseconds to a few seconds", "MEASURED",
     "runtime_benchmark.csv: 0.0001 s routing, 0.01121 s cooling, 4.564 s synthesis"),
    ("global thermal and mechanical FE dominate runtime", "MEASURED",
     "134.62 s (Z1) and 204.23 s (Z2) against <5 s for every analytical stage"),
    ("the framework is faster than commercial FEM/FVM", "NOT_SUPPORTED",
     "no controlled same-geometry same-hardware comparison has been run"),
    ("reduced-order models can lower repeated simulation cost", "LITERATURE_CONTEXT",
     "10.1109/SAPIW.2013.6558333, 10.1016/j.pedc.2024.100063 -- their speedups are "
     "NOT transferred"),
    ("mechanics is solved once after E-T convergence, not inside the loop", "MEASURED",
     "3 E-T iterations, 1 mechanical solve per architecture"),
    ("local nonlinear solder is solved only at the critical joint", "INFERENCE",
     "architectural choice; the avoided cost is not separately timed"),
    ("the framework has a single accuracy percentage", "NOT_SUPPORTED",
     "errors are model-specific and mix validation with convergence"),
    ("runtime scales as a known complexity in DOF", "NOT_SUPPORTED",
     "only a handful of empirical points exist; report measured scaling only"),
]

# constant, where, classification, note
GENERALITY = [
    ("49 cells / 7x7 grid", "configs + 15 scripts", "SYSTEM_SPECIFICATION",
     "comes from the architecture config; placement generator derives coordinates"),
    ("48 V input", "configs/phase0i/z_architectures.yaml", "SYSTEM_SPECIFICATION",
     "load block is config-driven"),
    ("1 V output / 1000 A", "configs/phase0i/z_architectures.yaml",
     "SYSTEM_SPECIFICATION", ""),
    ("N=3, K=3, K_A=2", "pinned HVR generator", "MODEL_LIMITATION",
     "the converter equations are specific to this topology family; another topology "
     "needs its own synthesis model, not just a config change"),
    ("30 mm substrate", "package_stack.yaml + 14 scripts", "SYSTEM_SPECIFICATION", ""),
    ("22.36 mm die", "package_stack.yaml", "SYSTEM_SPECIFICATION", ""),
    ("16 BGA supply balls", "pkg_rdl_network.N_SUPPLY_DEFAULT", "ACCIDENTAL_HARDCODING",
     "now an explicit argument with a module default; was previously derived from "
     "len(annulus)//2, which silently halved Z1's count"),
    ("0.8 mm BGA pitch / 14.4 mm half-span", "physical_coords", "SYSTEM_SPECIFICATION",
     "single source; lattice legality is testable"),
    ("architecture names Z1 / Z2", "power_path, interconnect_loss, gates",
     "ACCIDENTAL_HARDCODING",
     "graph builders are keyed by literal names; an ArchitectureSpec registry would "
     "remove this and has NOT been built"),
    ("cell pitch 3.165243 mm", "derived from the FE placement generator", "DERIVED",
     "no longer hard-coded anywhere after Phase 0N-AG"),
]


def write():
    with (OUT / "model_hierarchy.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["stage", "model", "type", "governing_quantity",
                    "independent_reference", "error", "evidence_class",
                    "historical_r3c_wall_s", "threads"])
        w.writerows(HIERARCHY)
    with (OUT / "computational_claim_matrix.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["claim", "classification", "evidence"])
        w.writerows(CLAIMS)
    with (OUT / "architecture_generality_audit.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["constant", "where", "classification", "note"])
        w.writerows(GENERALITY)
    # runtime, explicitly labelled historical
    src = list(csv.DictReader(
        (R / "results/phase0mr3c/runtime_benchmark.csv").open()))
    with (OUT / "runtime_breakdown.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(src[0]) + ["provenance"])
        w.writeheader()
        for row in src:
            row["provenance"] = "HISTORICAL_FROZEN_R3C_RUNTIME"
            w.writerow(row)
    summary = {
        "n_stages": len(HIERARCHY),
        "by_type": {t: sum(1 for h in HIERARCHY if h[2] == t)
                    for t in {h[2] for h in HIERARCHY}},
        "by_evidence": {e: sum(1 for h in HIERARCHY if h[6] == e)
                        for e in {h[6] for h in HIERARCHY}},
        "claims": {c: sum(1 for x in CLAIMS if x[1] == c)
                   for c in {x[1] for x in CLAIMS}},
        "generality": {g: sum(1 for x in GENERALITY if x[2] == g)
                       for g in {x[2] for x in GENERALITY}},
        "runtime_provenance": "HISTORICAL_FROZEN_R3C_RUNTIME",
        "runtime_caveat": ("these timings belong to the frozen R3C geometry. The "
                           "physical pair has changed substantially and has NOT been "
                           "re-benchmarked; they must not be presented as timing of "
                           "the corrected physical model"),
        "commercial_speedup": None,
        "commercial_status": ("NOT ESTABLISHED -- no controlled same-geometry, "
                              "same-hardware comparison against Icepak or Mechanical "
                              "has been run"),
    }
    (OUT / "model_hierarchy_summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True))
    return summary


if __name__ == "__main__":
    s = write()
    print("model stages:", s["n_stages"], "|", s["by_type"])
    print("evidence class:", s["by_evidence"])
    print("claims:", s["claims"])
    print("generality:", s["generality"])
    print("commercial speedup:", s["commercial_status"][:60])
