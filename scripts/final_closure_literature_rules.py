"""Literature-use rules for the listed sources: research/final_closure/literature_rules.*

DIRECT        same structure, material and conditions; a value or definition is taken.
CLOSE_ANALOG  similar structure; supports a MODELLING CHOICE, never a value or allowable.
CONTEXT_ONLY  qualitative background or a reason NOT to claim something; no number taken.
NOT_HELD      neither full text nor metadata exists in this environment (web search is
              unavailable here), so nothing -- value, choice or classification -- is drawn
              from it and it is not cited.
Each entry records what the repository actually holds, so a classification can be checked
against the held source rather than against memory.
"""
from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
OUT = R / "research" / "final_closure"

SOURCES = [
    {"doi": "10.1109/TCPMT.2026.3724907",
     "title": "A Comprehensive Design Framework for Vertical Power Delivery in HPC "
              "(Krishnakumar et al.)",
     "held": "FULL TEXT: research/phase0e/June2026_DVPD_arXiv2606.28837.pdf (arXiv 2606.28837)",
     "class": "DIRECT",
     "use": "the VPD/DVPD discriminator (spatial distribution of conversion and the residual "
            "low-voltage lateral path), quoted from the held text; also the style reference "
            "the manuscript audit checks for zero ten-word overlap",
     "caveat": "a definition, not a numerical input"},
    {"doi": "10.1109/TCPMT.2026.3716571", "title": None, "held": "NOTHING", "class": "NOT_HELD",
     "use": "none", "caveat": "no claim, value or classification is drawn from it; not cited"},
    {"doi": "10.1016/j.mtelec.2026.100211", "title": None, "held": "NOTHING",
     "class": "NOT_HELD", "use": "none",
     "caveat": "no claim, value or classification is drawn from it; not cited"},
    {"doi": "10.3390/ma14216394",
     "title": None,
     "held": "EXTRACTED CONDITIONS ONLY (Cu-Cu bump EM under accelerated stress): "
             "research/phase0naj/pad_count_closure.json",
     "class": "CONTEXT_ONLY",
     "use": "marks the ~1e6 A/cm2 regime in which accelerated Cu-Cu bump EM is observed, to "
            "flag the smallest pad counts",
     "caveat": "an accelerated test condition is failure-physics evidence, never a rating or "
               "an allowable"},
    {"doi": "10.1109/TED.2026.3724984",
     "title": "Research on Electromigration Failure Behavior of Redistribution Layer Based on "
              "Electrothermal Coupling",
     "held": "METADATA: research/phase0naa/doi_metadata.json (abstract not open)",
     "class": "CLOSE_ANALOG",
     "use": "supports evaluating the package RDL resistance at temperature inside the E-T "
            "fixed point (the ledger scales it with rho_Cu(T) at the package-layer "
            "temperature)",
     "caveat": "its accelerated current densities are NOT a design allowable"},
    {"doi": "10.1016/j.ijmecsci.2025.110758",
     "title": "TSV Electromigration Failure Prediction Using Multiphysics Coupled Energy Method",
     "held": "METADATA AND ABSTRACT: research/phase0naa/doi_metadata.json",
     "class": "CONTEXT_ONLY",
     "use": "reliability needs current density, temperature and stress together; the reason "
            "no TSV current-density allowable is claimed",
     "caveat": "qualitative only"},
    {"doi": "10.1109/ECTC.2004.1319419",
     "title": "Accumulated Creep Strain and Energy Density Based Thermal Fatigue Life "
              "Prediction Models for SnAgCu Solder Joints (Syed, ECTC 2004)",
     "held": "EXTRACTED RECORD: results/phase0jr/PRIMARY_SOURCE_INVENTORY.md",
     "class": "CONTEXT_ONLY",
     "use": "shows why a published life model does not transfer: SAC405/395 balls, creep-only "
            "metrics, volume averaging over a 25 um layer valid only for that thickness",
     "caveat": "no constant or life model is taken; the paper reports response, not life"},
    {"doi": "10.1115/1.1413764",
     "title": None,
     "held": "CITATION RECORD ONLY (Darveaux 2002, ASME, closed access): "
             "results/ETM_DVPD_FULL_TECHNICAL_REPORT.md",
     "class": "CONTEXT_ONLY",
     "use": "life correlations are calibrated to their own simulation procedure, so an "
            "absolute life from this procedure would not be admissible",
     "caveat": "the reason no cycles to failure are computed"},
]


def main():
    rules = {k: v for k, v in (
        ("DIRECT", "same structure, material and conditions; a value or definition is taken"),
        ("CLOSE_ANALOG", "similar structure; supports a modelling choice, never a value"),
        ("CONTEXT_ONLY", "qualitative background or a reason not to claim; no number taken"),
        ("NOT_HELD", "no full text or metadata in this environment; nothing drawn, not cited"))}
    (OUT / "literature_rules.json").write_text(json.dumps(
        {"rules": rules, "sources": SOURCES}, indent=1))
    lines = ["# Literature-use rules", "", "Generated by "
             "`scripts/final_closure_literature_rules.py`.", ""]
    lines += [f"- **{k}**: {v}" for k, v in rules.items()] + ["",
              "| DOI | class | held in repository | use | caveat |", "|---|---|---|---|---|"]
    lines += [f"| {s['doi']} | {s['class']} | {s['held']} | {s['use']} | {s['caveat']} |"
              for s in SOURCES]
    (OUT / "literature_rules.md").write_text("\n".join(lines) + "\n")
    print({c: sum(s["class"] == c for s in SOURCES) for c in rules})


if __name__ == "__main__":
    main()
