"""PHASE 0N-AA --- DOI-backed provenance for every interconnect electrical assumption.

THE RULE THIS ENFORCES: an accelerated electromigration stress condition is evidence
about failure physics. It is NOT a safe operating limit. A paper that drives a joint to
failure at 2300 A/cm^2 and 160 C in a few hundred hours tells you where the mechanism
lives; it does not tell you that 2299 A/cm^2 is qualified for ten years.

Applicability is classified explicitly:

  DIRECT        same structure, material, geometry and regime -- may set a parameter
  CLOSE_ANALOG  near-matching; may set a parameter only with the mismatch stated
  CONTEXT_ONLY  informs a bound or a caveat; may NEVER set an allowable

Operating points are computed from the live model so the comparison column cannot go
stale against the power path.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts/phase0nw"))
OUT = R / "research" / "phase0naa"
OUT.mkdir(parents=True, exist_ok=True)

D_BALL_MM = 0.400          # Krishnakumar 2026 Table III
A_BALL_CM2 = math.pi * (D_BALL_MM / 2 / 10) ** 2


def operating_points() -> dict:
    import power_path as PP
    rc = PP.rail_currents()
    out = {}
    for a in ("Z1", "Z2"):
        i_hv = rc[a]["hv_total_a"]
        i_ball = i_hv / 16
        out[a] = {"i_hv_a": i_hv, "i_ball_a": i_ball,
                  "j_ball_A_cm2": i_ball / A_BALL_CM2,
                  "j_ball_local_A_cm2": i_ball / A_BALL_CM2 * 22.0}
    return out


# parameter, structure, current value/status, doi, paper geometry/material, conditions,
# applicability, what it actually establishes, resulting status
ROWS = [
    ("I_ball_max = 1.5 A", "BGA ball, 400 um", "BOUNDED engineering provisioning rule",
     "10.1016/j.jmrt.2023.12.187",
     "500 um BGA solder joints, Cu UBM 16 um / 68 um",
     "accelerated EM: 130 C-3000, 160 C-2300, 160 C-3000, 160 C-4600 A/cm2",
     "CLOSE_ANALOG",
     "Establishes the accelerated-stress regime for a BGA of comparable size and the "
     "existence of ~22x current crowding at the UBM contact. Does NOT establish an "
     "allowable: every listed condition is a deliberate failure-inducing stress.",
     "BOUNDED -- 1.5 A/ball retained as a provisioning rule, NOT an EM-safe limit"),
    ("BGA current density context", "BGA ball, 400 um", "derived from I_ball_max",
     "10.1108/SSMT-08-2025-0041",
     "Cu/SAC305/Cu microscale BGA, several joint heights",
     "6.0e3 to 1.1e4 A/cm2 under shear + current stressing",
     "CONTEXT_ONLY",
     "Shows shear strength and fracture depend on joint height and current crowding. "
     "Our geometry and loading differ; informs caution, sets nothing.",
     "CONTEXT_ONLY"),
    ("SAC305 void/EM behaviour", "BGA solder", "n/a -- failure physics",
     "10.1016/j.matchar.2024.114227",
     "SAC305 BGA joints, betaSn grain orientation study", "EM-induced void evolution",
     "CONTEXT_ONLY",
     "Grain-orientation dependence means a single scalar EM allowable is not "
     "well-defined for SAC305 at joint scale.",
     "CONTEXT_ONLY"),
    ("SAC305 lifetime vs stress", "BGA solder", "n/a",
     "10.1108/SSMT-04-2021-0012", "Sn3.0Ag0.5Cu joints",
     "electrical and thermal stressing, void formation and migration lifetime",
     "CONTEXT_ONLY",
     "Lifetime is a function of combined electrical and thermal stress; supports "
     "refusing a current-only allowable.", "CONTEXT_ONLY"),
    ("TSV J allowable", "substrate TSV, 30 um x 300 um", "none asserted",
     "10.1016/j.microrel.2015.05.019",
     "3-D interconnect / high-density TSV, in-operando EM",
     "~1 MA/cm2 at elevated temperature (accelerated)", "CONTEXT_ONLY",
     "1 MA/cm2 is an accelerated stress condition used to force failure in observable "
     "time. Treating it as a design allowable would be a category error.",
     "OPEN -- no TSV current-density allowable is asserted"),
    ("TSV EM vs roughness", "substrate TSV", "n/a",
     "10.1109/TED.2023.3307505", "TSV with rough Cu/SiO2 interface, W-M fractal model",
     "increasing J reduces high-temperature reliability", "CONTEXT_ONLY",
     "Current and stress concentrate at interface roughness, so a smooth-via J estimate "
     "understates local stress. Supports keeping the allowable OPEN.", "CONTEXT_ONLY"),
    ("TSV reliability metric", "substrate TSV", "n/a",
     "10.1016/j.ijmecsci.2025.110758", "TSV multiphysics coupled energy method",
     "J, T and sigma jointly", "CONTEXT_ONLY",
     "Reliability needs J, T and stress together; a current-density number alone is not "
     "a sufficient criterion.", "CONTEXT_ONLY"),
    ("Microbump contact resistance", "microbump / UBM / IMC", "R_contact = 0, status OPEN",
     "10.1109/EPTC.2015.7412351", "Cu pillar + Sn microbump, fine pitch",
     "3e5 A/cm2 at 150 C; resistance rises abruptly as voids form and solder converts "
     "to Cu6Sn5 then Cu3Sn", "CLOSE_ANALOG",
     "Demonstrates that microbump resistance is NOT constant and NOT zero: it evolves "
     "with IMC conversion. Confirms R_contact = 0 is 'not modelled', not 'negligible'. "
     "Gives no transferable room-temperature contact resistance for our geometry.",
     "OPEN -- must become a sourced bracket before any 'non-dominant' claim"),
    ("Cu pillar/Sn electrical reliability", "microbump", "n/a",
     "10.1007/s11664-010-1345-7", "Cu pillar / Sn bumps, interfacial reaction",
     "electrical reliability vs interfacial reaction", "CONTEXT_ONLY",
     "Interfacial reaction changes electrical behaviour over time.", "CONTEXT_ONLY"),
    ("Microbump R_contact under ETM", "microbump", "R_contact = 0, status OPEN",
     "10.1109/ICEPT71373.2026.11690046",
     "chiplet micro-bump, electro-thermo-mechanical coupling",
     "contact resistance evolution vs real contact area, softening, stress",
     "CLOSE_ANALOG",
     "Directly on point for whether contact resistance belongs in the model. Abstract "
     "not retrievable through Crossref or OpenAlex in this environment, so it is "
     "recorded as a lead, not as a numerical source.",
     "OPEN -- abstract not retrievable here"),
    ("UBM/IMC scaling", "microbump UBM", "n/a",
     "10.1109/TCPMT.2026.3728725", "scaled Cu/Sn microbumps, IMC in UBM layers",
     "IMC formation observation", "CONTEXT_ONLY",
     "IMC fraction grows as bumps scale, so a bulk-Cu microbump resistance is a lower "
     "bound. Abstract not retrievable here.", "CONTEXT_ONLY"),
    ("Microbump background", "microbump", "n/a", "10.1557/mrs.2015.29",
     "review: vertical interconnects of microbumps in 3-D integration", "review",
     "CONTEXT_ONLY", "Background on UBM, IMC and EM failure modes.", "CONTEXT_ONLY"),
    ("RDL Cu resistance vs microstructure", "10 um converter RDL",
     "electrical model OPEN", "10.1016/j.jmrt.2023.11.011",
     "fine-pitch RDL Cu, nanotwinned vs coarse grain",
     "surface roughening after seed etch; q-time oxidation", "CLOSE_ANALOG",
     "Establishes that fine-pitch RDL resistance and EM lifetime depend on "
     "microstructure, surface roughness and oxidation -- so a bulk-Cu resistivity is a "
     "lower bound on RDL resistance, not a nominal value.",
     "BOUNDED -- bulk Cu rho is a floor; the realized value is higher by an unquantified "
     "factor"),
    ("RDL R(T)", "package RDL", "no T dependence implemented",
     "10.1109/TED.2026.3724984", "RDL under electrothermal coupling",
     "strong temperature-dependent degradation under high-J stressing", "CLOSE_ANALOG",
     "Supports making R_RDL a function of temperature inside the ET fixed point. Its "
     "accelerated J is NOT a design allowable.",
     "OPEN -- R_RDL(T) not yet implemented"),
    ("Electroplated Cu RDL resistance", "package RDL", "n/a",
     "10.15344/2455-2372/2015/116", "electroplated Cu RDL on Si interposer",
     "resistance evolution", "CONTEXT_ONLY",
     "Electroplated RDL resistance evolves; supports a bounded rather than fixed value.",
     "CONTEXT_ONLY"),
    ("RDL process/warpage", "package RDL", "n/a", "10.1016/j.matdes.2025.114732",
     "electroplating current density and post-annealing effects",
     "warpage and reliability", "CONTEXT_ONLY",
     "Thermomechanical/process evidence; justifies a bounded RDL material treatment.",
     "CONTEXT_ONLY"),
]

COLS = ["parameter", "architecture", "physical_structure", "current_value_status",
        "paper_title", "doi", "paper_geometry_material", "paper_conditions",
        "applicability", "what_it_establishes", "final_status",
        "our_operating_point", "transferability_caveat"]


def build():
    meta = {m["doi"]: m for m in
            json.loads((OUT / "doi_metadata.json").read_text())}
    op = operating_points()
    ours = (f"BGA average J = {op['Z1']['j_ball_A_cm2']:.0f} A/cm2 (Z1) / "
            f"{op['Z2']['j_ball_A_cm2']:.0f} (Z2) at 400 um ball, 1.48 A/ball")
    rows = []
    for (param, struct, cur, doi, geom, cond, appl, establishes, status) in ROWS:
        m = meta.get(doi, {})
        rows.append({
            "parameter": param, "architecture": "Z1+Z2", "physical_structure": struct,
            "current_value_status": cur,
            "paper_title": m.get("title") or "(title not resolved)",
            "doi": doi, "paper_geometry_material": geom, "paper_conditions": cond,
            "applicability": appl, "what_it_establishes": establishes,
            "final_status": status,
            "our_operating_point": ours if "BGA" in struct else "",
            "transferability_caveat": (
                "accelerated stress condition; NOT a design allowable"
                if "accelerated" in cond.lower() or "A/cm2" in cond else
                "qualitative evidence only"),
        })
    p = OUT / "interconnect_literature_matrix.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    json.dump({"operating_points": op, "a_ball_cm2": A_BALL_CM2,
               "n_rows": len(rows),
               "by_applicability": {k: sum(1 for r in rows if r["applicability"] == k)
                                    for k in ("DIRECT", "CLOSE_ANALOG", "CONTEXT_ONLY")}},
              (OUT / "literature_summary.json").open("w"), indent=1)
    return p, rows, op


if __name__ == "__main__":
    p, rows, op = build()
    from collections import Counter
    print(f"wrote {p.relative_to(R)}  ({len(rows)} rows)")
    print("applicability:", dict(Counter(r["applicability"] for r in rows)))
    print("final status: ", dict(Counter(r["final_status"].split(" --")[0] for r in rows)))
    for a in ("Z1", "Z2"):
        print(f"  {a}: J_ball {op[a]['j_ball_A_cm2']:.0f} A/cm2 "
              f"(local ~{op[a]['j_ball_local_A_cm2']:.0f} with 22x crowding)")
