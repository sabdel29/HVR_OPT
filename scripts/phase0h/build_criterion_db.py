#!/usr/bin/env python3
"""Phase-0H Sec.6/15 -- the mechanical-criterion literature database.

Two tiers, kept strictly apart:

  EXAMINED  -- full text retrieved and read. Every field is from the text.
  METADATA  -- discovered through OpenAlex but the full text is behind a paywall in this
               environment. Only bibliographic fields are filled; every physical field is
               NOT_RETRIEVED and applicability is UNDETERMINED. These rows are evidence that
               the search was broad, NOT evidence about any threshold.

Nothing here is inferred from a title. A criterion may only be admitted by Sec.15 if all six
conditions are met, and the reason for every rejection is recorded.
"""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0h"

COLS = ["tier", "source", "year", "doi_or_url", "package_architecture", "package_dimensions",
        "interconnect_type", "assembly_state", "temperature_load_history", "failure_mechanism",
        "metric", "threshold_value", "experimental_or_simulated", "criterion_category",
        "applicability", "reason_accepted_or_rejected"]

EXAMINED = [
 dict(tier="EXAMINED", source="IPC-9641, High Temperature Printed Board Flatness Guideline",
      year=2013, doi_or_url="https://www.ipc.org/TOC/IPC-9641.pdf",
      package_architecture="printed board (not package)", package_dimensions="local land area, e.g. FCBGA land",
      interconnect_type="n/a - board flatness", assembly_state="bare printed board during SMT build",
      temperature_load_history="simulated reflow profile, ambient to peak",
      failure_mechanism="solder joint formation defects: opens, bridging",
      metric="full-field flatness / dynamic warpage (ambient to reflow difference)",
      threshold_value="NONE - it is a test method, not a limit",
      experimental_or_simulated="measurement method",
      criterion_category="1 manufacturing/solderability",
      applicability="REJECTED",
      reason_accepted_or_rejected="Governs the printed BOARD, not the package; references its "
      "metric to reflow temperature; contains no allowable at all. Fails package state, "
      "temperature state, metric definition and failure mechanism."),
 dict(tier="EXAMINED", source="Warpage Analysis of Lidded Flip Chip CSP (IMAPSource)",
      year=2025, doi_or_url="https://imapsource.org/article/147117.pdf",
      package_architecture="lidded flip-chip CSP, organic substrate",
      package_dimensions="21 x 21 mm body", interconnect_type="BGA + copper pillar",
      assembly_state="package as supplied, before board attach",
      temperature_load_history="25 C coplanarity; 245 C peak reflow",
      failure_mechanism="SMT yield: uneven solder joint formation",
      metric="ball-plane coplanarity (JESD22-B108B); package warpage at reflow (JESD22-B112C method)",
      threshold_value="80 um coplanarity at 25 C (JEP95 Table I); -120 to +170 um warpage at "
      "245 C reflow (SPP-024 Table II)",
      experimental_or_simulated="experimental (100 coplanarity / 10 warpage samples) + FEA",
      criterion_category="1 manufacturing/solderability",
      applicability="REJECTED",
      reason_accepted_or_rejected="Body size matches this project (21 vs 22.36 mm) but nothing "
      "else does. Package is unmounted; state is reflow or room-temperature coplanarity, not "
      "84 C steady operation; mechanism is assembly yield, not operational reliability; metric "
      "is ball-plane coplanarity referenced ambient-to-reflow, not die-surface P-V referenced "
      "to a 25 C stress-free state. 1 of 6 admissibility conditions met."),
 dict(tier="EXAMINED", source="Warpage in wafer-level packaging: a review of causes, modelling "
      "and mitigation (Frontiers in Electronics)", year=2025,
      doi_or_url="https://doi.org/10.3389/felec.2024.1515860",
      package_architecture="wafer-level / fan-out packaging, reconstituted wafer",
      package_dimensions="wafer and individual package scale",
      interconnect_type="RDL / fan-out", assembly_state="during wafer-level packaging, pre-assembly",
      temperature_load_history="process history: mould cure, post-mould cure, cooldown",
      failure_mechanism="manufacturability and YIELD; handling, subsequent assembly",
      metric="package warpage (total, process-induced)",
      threshold_value="wafer < 0.5 mm for high yield; individual package max allowable 0.2 mm, "
      "0.1 mm preferred for high yield (review citing Lau 2018b/2019b)",
      experimental_or_simulated="review of experimental and simulated work",
      criterion_category="1 manufacturing/solderability",
      applicability="REJECTED",
      reason_accepted_or_rejected="The only numeric package-level warpage allowables found "
      "anywhere in this search, but explicitly framed 'for high yields' during wafer-level "
      "packaging. Process state, not operational; total process-induced warpage, not "
      "incremental operational; mechanism is yield, not service life. The same review names "
      "'Need for Materials Data and Failure Criteria' as an open challenge for the field."),
 dict(tier="EXAMINED", source="Thermal Fatigue Evaluation of Pb-Free Solder Joints: Results, "
      "Lessons Learned (JOM)", year=2015,
      doi_or_url="https://doi.org/10.1007/s11837-015-1595-1",
      package_architecture="CTBGA84 and CABGA192 chip-scale BGA on FR-4",
      package_dimensions="chip-scale, pad diameter 0.254-0.356 mm",
      interconnect_type="BGA, 12 Pb-free alloys",
      assembly_state="board-mounted", temperature_load_history="accelerated thermal cycling, "
      "0/100 C and other profiles, 10-min and longer dwells",
      failure_mechanism="solder joint thermal fatigue, daisy-chain open",
      metric="characteristic life N63.2 (two-parameter Weibull)",
      threshold_value="alloy- and profile-dependent cycles-to-failure; no design allowable",
      experimental_or_simulated="experimental",
      criterion_category="2 component qualification test",
      applicability="REJECTED as a design constraint; RELEVANT as calibration evidence",
      reason_accepted_or_rejected="Correct mechanism (B) and correct assembly state, but the "
      "load is ACCELERATED THERMAL CYCLING and the output is cycles-to-failure, not a "
      "steady-state design threshold. Using it would require a discrete-joint viscoplastic "
      "model this project does not have (Sec. 3, Sec. 9), plus a field mission profile that "
      "does not exist for the reference system."),
 dict(tier="EXAMINED", source="Thermal fatigue life of BGA solder joints made from different "
      "alloy compositions (J. Electron. Mater.)", year=2021,
      doi_or_url="https://doi.org/10.1007/s11664-020-08525-9",
      package_architecture="BGA", package_dimensions="NOT_RETRIEVED",
      interconnect_type="BGA, Sn63Pb37 and SAC alloys",
      assembly_state="board-mounted", temperature_load_history="thermal cycling",
      failure_mechanism="solder joint thermal fatigue",
      metric="strain energy density Ed dissipated per cycle; von Mises stress; creep strain",
      threshold_value="comparative between alloys; no absolute allowable",
      experimental_or_simulated="simulated (FEA) with Weibull comparison",
      criterion_category="3 material failure criterion",
      applicability="REJECTED as a design constraint; RELEVANT as a metric definition",
      reason_accepted_or_rejected="Defines exactly the category-3 quantity that could become a "
      "category-4 allowable given a calibration, and confirms the required fidelity: creep, "
      "temperature-dependent constitutive behaviour and cyclic loading. The present M0 model "
      "has none of these and the BGA is a single homogenised elastic layer, so the metric is "
      "not computable here (Sec. 9)."),
 dict(tier="EXAMINED", source="Methodology for Predicting BGA Warpage by Incorporating Metal "
      "Layer Design (IMAPSource)", year=2014,
      doi_or_url="https://imapsource.org/article/57023.pdf",
      package_architecture="BGA, organic substrate", package_dimensions="NOT_RETRIEVED",
      interconnect_type="BGA", assembly_state="package as supplied",
      temperature_load_history="reflow heating per JESD22-B112",
      failure_mechanism="warpage prediction for assembly", metric="package warpage",
      threshold_value="NONE quoted", experimental_or_simulated="experimental + simulated",
      criterion_category="1 manufacturing/solderability",
      applicability="REJECTED",
      reason_accepted_or_rejected="Confirms JESD22-B112 is applied as a MEASUREMENT "
      "specification ('heaters as per JEDEC Spec JESD22B112'), not as a source of allowables. "
      "Useful only to establish what the standard is for."),
]


def main():
    raw = list(csv.DictReader(open(OUT / "literature_candidates_raw.csv")))
    seen = {r["doi_or_url"].lower() for r in EXAMINED}
    rows = list(EXAMINED)
    for r in raw:
        doi = (r["doi"] or r["oa_url"] or "").lower()
        if not doi or doi in seen:
            continue
        seen.add(doi)
        rows.append(dict(
            tier="METADATA", source=r["title"], year=r["year"],
            doi_or_url=r["doi"] or r["oa_url"],
            package_architecture="NOT_RETRIEVED", package_dimensions="NOT_RETRIEVED",
            interconnect_type="NOT_RETRIEVED",
            assembly_state="NOT_RETRIEVED", temperature_load_history="NOT_RETRIEVED",
            failure_mechanism=f"search target: {r['target_mechanism']}",
            metric="NOT_RETRIEVED", threshold_value="NOT_RETRIEVED",
            experimental_or_simulated="NOT_RETRIEVED",
            criterion_category="NOT_RETRIEVED",
            applicability="UNDETERMINED",
            reason_accepted_or_rejected="full text not retrievable in this environment "
            f"(open access: {r['is_oa']}); bibliographic evidence of search breadth only"))
    with open(OUT / "MECHANICAL_CRITERION_LITERATURE_DATABASE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    ex = [r for r in rows if r["tier"] == "EXAMINED"]
    print(f"{len(rows)} rows: {len(ex)} EXAMINED, {len(rows)-len(ex)} METADATA")
    print(f"{'category':34s} {'applicability':52s} source")
    for r in ex:
        print(f"  {r['criterion_category']:32s} {r['applicability']:50s} {r['source'][:44]}")
    acc = [r for r in ex if r["applicability"].startswith("ACCEPTED")]
    print(f"\nADMITTED AS DESIGN CONSTRAINT: {len(acc)}")


if __name__ == "__main__":
    main()
