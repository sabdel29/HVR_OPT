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
    {"doi": "10.1109/TCPMT.2026.3716571",
     "title": "Towards 10kAmp AI Chip: A System Perspective from Lateral to Vertical Power "
              "Delivery (Ye et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_TCPMT.2026.3716571.json",
     "class": "CONTEXT_ONLY", "use": "positioning: a system view of the lateral-to-vertical move",
     "caveat": "cited for context only; no value, choice or claim is drawn from it"},
    {"doi": "10.1109/TCPMT.2026.3716987",
     "title": "Integrated Vertical Power Delivery -- Review & Challenges (Swaminathan et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_TCPMT.2026.3716987.json",
     "class": "CONTEXT_ONLY", "use": "positioning in the VPD literature",
     "caveat": "cited for context only; no value is drawn from it"},
    {"doi": "10.1109/SOCC58585.2023.10256973",
     "title": "Vertical Power Delivery for Emerging Packaging and Integration Platforms "
              "(Krishnakumar and Partin-Vaisband)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_SOCC58585.2023.10256973.json (the arXiv version was read earlier)",
     "class": "CONTEXT_ONLY", "use": "the vertical-integration family of the two architectures",
     "caveat": "no numerical input"},
    {"doi": "10.1109/ISCAS58744.2024.10558456",
     "title": "Design Considerations for DC-DC Voltage Regulators in DVPD (Krishnakumar et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_ISCAS58744.2024.10558456.json",
     "class": "CONTEXT_ONLY", "use": "positioning of the regulator design question",
     "caveat": "no numerical input"},
    {"doi": "10.1109/ECTC51529.2024.00364",
     "title": "VPD for HPC Systems with Buck-Derived Regulators (Krishnakumar et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_ECTC51529.2024.00364.json",
     "class": "CONTEXT_ONLY", "use": "positioning; vertical routing models",
     "caveat": "the interlayer RDL and via dimensions cited in Table I predate this phase"},
    {"doi": "10.1109/ITherm55375.2024.10709419",
     "title": "Thermal Analysis of High Current VPD with Embedded Microchannel Cooling "
              "(Choi et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_ITherm55375.2024.10709419.json",
     "class": "CONTEXT_ONLY", "use": "context for the cooling model-form sensitivity",
     "caveat": "not a replacement of the production cooling model; no value taken"},
    {"doi": "10.1109/TCPMT.2025.3636391",
     "title": "Self-Consistent Electrothermal Modeling of DVPD with Substrate-Embedded "
              "Microfluidic Cooling (Choi et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_TCPMT.2025.3636391.json",
     "class": "CONTEXT_ONLY", "use": "context for the electrothermal fixed point and cooling",
     "caveat": "no value taken"},
    {"doi": "US20260059645A1 (patent)",
     "title": "Vertical Integrated Voltage Regulator with Circuit Board Cutout (Arm Ltd.)",
     "held": "TEXT: research/final_closure/literature_metadata/US20260059645A1.json; quotes in "
             "z2_direct_feed_architecture.json",
     "class": "DIRECT",
     "use": "construction precedent of the direct-fed Z2: VR on the substrate side opposite the "
            "die, in a board cutout, fed by a separate wire, bumps dedicated to the output",
     "caveat": "no dimension, performance number or qualification is taken from it"},
    {"doi": "US20210249384A1 (patent family)",
     "title": "Backside Integrated Voltage Regulator for Integrated Circuits (Google LLC)",
     "held": "TEXT: research/final_closure/literature_metadata/US20210249384A1.json and family",
     "class": "CLOSE_ANALOG",
     "use": "the backside-RDL-to-TSV output path of a backside regulator",
     "caveat": "its input is fed through the package: not a direct-feed precedent"},
    {"doi": "10.1109/ECTC.2016.127",
     "title": "Thermal Compression Bonding of 30um Pitch Cu Pillar Microbump on Organic "
              "Substrate (Au et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/oa_10.1109_ECTC.2016.127.json;"
             " abstract quote in z2_direct_feed_architecture.json",
     "class": "CLOSE_ANALOG",
     "use": "the attach geometry (15 um Cu pillars, 30 um pitch, solder cap) as a modelling "
            "choice: the production attach and the dense endpoint of geom.vr_attach_density",
     "caveat": "not this package; no current or reliability limit is transferred. The "
               "abstract prints the cap height as '16mm', a unit error for a 30 um-pitch "
               "bump; it is read as 16 um (cap) on a 14 um pillar in the 30 um envelope, and "
               "the height bounds and the all-solder bound cover that reading"},
    {"doi": "10.3390/electronics12010144",
     "title": "Fabrication of 30 um Sn Microbumps by Electroplating and Investigation of IMC "
              "Characteristics on Shear Strength (Na et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.3390_electronics12010144.json; quote in z2_direct_feed_architecture.json",
     "class": "CLOSE_ANALOG",
     "use": "the sparse endpoint of geom.vr_attach_density (30 um bumps, 50 um space, i.e. "
            "80 um pitch) held in the production material and height; its pure-Sn cap on a "
            "Cu post/Ni barrier gives the all-solder resistive bound; the 40 um height bound",
     "caveat": "a bound, not a value of this design; Electronics 12(1), 2023 (online "
               "December 2022); its post/cap split is not in the accessible text"},
    {"doi": "10.1109/EPTC.2015.7412351",
     "title": "Electromigration Reliability and Morphologies of Cu Pillar with Microbump under "
              "High Current Density Stressing (Hsiao and Lin, EPTC 2015)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_EPTC.2015.7412351.json",
     "class": "CONTEXT_ONLY",
     "use": "Cu-pillar microbump electromigration is studied under accelerated stress: the "
            "reason the attach current density is reported as an output only",
     "caveat": "no current density, rating or allowable is taken; no electromigration-safe "
               "attach current is claimed"},
    {"doi": "10.3390/ma16031134",
     "title": "Interfacial Reaction and Electromigration Failure of Cu Pillar/Ni/Sn-Ag/Cu "
              "Microbumps under Bidirectional Current Stressing (Fu et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/oa_10.3390_ma16031134.json",
     "class": "CONTEXT_ONLY",
     "use": "Cu-pillar microbump electromigration failure physics: the reason no "
            "electromigration-safe attach current is claimed",
     "caveat": "an accelerated test condition is failure-physics evidence, never a rating"},
    {"doi": "10.3390/ma10101220",
     "title": "Effect of Wafer Level Underfill on the Microbump Reliability of Ultrathin-Chip "
              "Stacking Type 3D-IC Assembly during Thermal Cycling Tests (Lee)",
     "held": "METADATA: research/final_closure/literature_metadata/oa_10.3390_ma10101220.json",
     "class": "CONTEXT_ONLY",
     "use": "the underfill affects microbump reliability (title-level record only): context "
            "for carrying the attach mechanics as two bounds (underfill-dominated, "
            "column-stiffened) rather than one card",
     "caveat": "no property, stiffness or life is taken; only the bibliographic record is "
               "held"},
    {"doi": "10.1109/TCPMT.2025.3628798",
     "title": "Challenges and Mitigations of Microbumps Pitch Scaling for Chiplet Applications "
              "(Derakhshandeh et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_TCPMT.2025.3628798.json",
     "class": "CONTEXT_ONLY",
     "use": "microbump pitch is a process choice with its own constraints: context for treating "
            "the attach density as a sensitivity",
     "caveat": "no geometry, value or allowable is taken from it"},
    {"doi": "10.1109/TCPMT.2016.2641040",
     "title": "Cu Pillar/Sn-Ag Microbumps with Nonconductive Films (Lee et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_TCPMT.2016.2641040.json",
     "class": "CONTEXT_ONLY", "use": "fine-pitch Cu-pillar construction", "caveat": "no value"},
    {"doi": "10.1109/ICEPT.2018.8480482",
     "title": "Material Systems of 30 um Pitch Micro Bumps (Dai et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1109_ICEPT.2018.8480482.json",
     "class": "CONTEXT_ONLY", "use": "fine-pitch microbump material systems",
     "caveat": "its single-bump resistance is not available here and is not used"},
    {"doi": "10.1016/j.mssp.2026.110744",
     "title": "Advances in Copper Pillar Bumps for High-Density Electronic Packaging (Xu et al.)",
     "held": "METADATA: research/final_closure/literature_metadata/"
             "oa_10.1016_j.mssp.2026.110744.json",
     "class": "CONTEXT_ONLY", "use": "Cu-pillar review", "caveat": "no value"},
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
