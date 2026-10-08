"""Phase-0G Sec.17 -- DEFECT #29 guard.

The report used to state the same claim in five places and each phase updated only some of
them. Regex assertions could not catch it because every individual sentence was true when
written. The structural fix is that current-status sections are GENERATED from
results/CURRENT_SCIENTIFIC_STATUS.yaml. These tests enforce the two properties that make the
fix real:

  1. the generated text is a faithful, complete rendering of the YAML, and
  2. the report actually CONTAINS that generated text rather than a hand-edited copy of it.

Without (2) the generator is decorative: someone can edit the report and the YAML drifts.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
SRC = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
GEN = R / "results" / "phase0g" / "generated_status_sections.md"
REPORT = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
SCRIPT = R / "scripts" / "phase0g" / "generate_status_sections.py"


def flow(t) -> str:
    return " ".join(str(t).split())


@pytest.fixture(scope="module")
def status() -> dict:
    return yaml.safe_load(SRC.read_text())


@pytest.fixture(scope="module")
def generated() -> str:
    return GEN.read_text()


def test_generator_is_deterministic(generated):
    """Re-running the generator must reproduce the committed file byte for byte."""
    before = GEN.read_bytes()
    subprocess.run([sys.executable, str(SCRIPT)], check=True, capture_output=True)
    assert GEN.read_bytes() == before, (
        "generated_status_sections.md is stale -- regenerate it after editing the YAML")


ALLOWED_0G = {
    "ROBUST ASSEMBLY-STATE ETM REVERSAL VALIDATED",
    "ASSEMBLY-STATE REVERSAL IS SUPPORT-CONDITIONAL",
    "ASSEMBLY-STATE REVERSAL IS THERMAL-BOUNDARY-CONDITIONAL",
    "ELECTRICAL THICKNESS CROSSOVER IS NOT RESOLVED",
    "NO ACTIVE MECHANICAL CONSTRAINT -- RESPONSE COUPLING ONLY",
    "MECHANICAL CONSTRAINT VALIDATED",
}
ALLOWED_0H = {
    "MECHANICAL CRITERION ACQUIRED -- G2 PASSES",
    "MECHANICAL CRITERION ACQUIRED -- NON-BINDING",
    "LOCAL RELIABILITY METRIC REPLACES GLOBAL WARPAGE",
    "NO ADMISSIBLE MECHANICAL CRITERION FOUND -- RESPONSE COUPLING ONLY",
    "INSUFFICIENT MATERIAL / ASSEMBLY DATA TO TEST A CANDIDATE CRITERION",
}
ALLOWED_0I = {
    "RELIABILITY CONSTRAINT PROVEN -- MECHANICS ENTERS SYNTHESIS",
    "ARCHITECTURE-DEPENDENT RELIABILITY RESPONSE -- NO ACTIVE CONSTRAINT",
    "GLOBAL WARPAGE DOES NOT TRACK LOCAL DAMAGE",
    "NO MATERIAL RELIABILITY EFFECT FOUND",
    "INSUFFICIENT MATERIAL / MISSION DATA FOR RELIABILITY VERDICT",
}
ALLOWED_0IR = {
    "PHASE-0I LOCAL RELIABILITY METRIC VALIDATED -- READY FOR LIFE-LAW ACQUISITION",
    "PHASE-0I METRIC VALID AFTER REDEFINITION -- READY FOR LIFE-LAW ACQUISITION",
    "PHASE-0I DAMAGE METRIC OMITTED CREEP CONTRIBUTION -- RESULTS REQUIRE REPLAY",
    "PHASE-0I LOCAL RELIABILITY METRIC NOT PHYSICALLY CLOSED",
    "PHASE-0I ARCHITECTURE CLAIMS VALID BUT LIFE INTERPRETATION WITHDRAWN",
}
ALLOWED_0J = {
    "G2 PASSED -- RELIABILITY CONSTRAINT CHANGES THE FEASIBLE ARCHITECTURE SET",
    "LIFE LAW ACQUIRED -- ALL TESTED ARCHITECTURES PASS REQUIRED LIFE",
    "LIFE LAW ACQUIRED -- ALL TESTED ARCHITECTURES FAIL REQUIRED LIFE",
    "ARCHITECTURE-DEPENDENT FATIGUE LIFE PROVEN -- NO APPLICABLE REQUIRED LIFE FOUND",
    "FATIGUE-LIFE RANKING IS MODEL-FORM DEPENDENT",
    "NO ADMISSIBLE SAC305 LIFE LAW FOUND FOR THE CURRENT METRIC / REGIME",
    "LIFE LAW FOUND BUT PHASE-0I LOADING LIES OUTSIDE ITS VALID DOMAIN",
}
ALLOWED_0JR = {
    "SAC305 LIFE LAW ADMITTED -- ABSOLUTE FATIGUE LIFE PREDICTION VALIDATED",
    "SAC/SnAgCu LIFE LAW ADMITTED FOR RELATIVE LIFE ONLY",
    "PRIMARY SOURCES ACCESSED -- LIFE-LAW TRANSFER REMAINS CONDITIONAL",
    "PRIMARY SOURCES CONFIRM NO ADMISSIBLE LIFE LAW FOR CURRENT REGIME",
    "SAC LIFE-LAW FAMILIES DISAGREE -- MODEL-FORM UNCERTAINTY DOMINATES",
    "CURRENT ZERO-DWELL LOAD PROFILE IS INCOMPATIBLE WITH AVAILABLE CALIBRATIONS",
}
ALLOWED_0K = {
    "MISSION REQUIREMENT ACQUIRED -- CURRENT MODELS ROBUSTLY PASS G2",
    "MISSION REQUIREMENT ACQUIRED -- G2 ROBUSTLY NON-BINDING",
    "MISSION REQUIREMENT ACQUIRED -- MODEL-FORM UNCERTAINTY PREVENTS G2 DECISION",
    "ABSOLUTE-LIFE CALIBRATION REQUIRED BEFORE G2 CAN BE DECIDED",
    "MISSION REQUIREMENT STILL OPEN -- ABSOLUTE-LIFE CALIBRATION ALSO REQUIRED",
    "MISSION REQUIREMENT STILL OPEN -- CURRENT RELATIVE-LIFE RESULT IS THE MAXIMUM DEFENSIBLE CLAIM",
}
ALLOWED_0KR = {
    "EXPERIMENT DESIGN FROZEN -- CURRENT MATERIAL MODEL SUFFICIENT",
    "EXPERIMENT DESIGN FROZEN AFTER WITHIN-DOMAIN PROFILE REDESIGN",
    "LOW-TEMPERATURE SAC305 MODEL VALIDATED -- ORIGINAL PROFILE RETAINED",
    "LOW-TEMPERATURE DATA INSUFFICIENT -- ORIGINAL PROFILE WITHDRAWN",
    "STATISTICAL POWER INSUFFICIENT -- SAMPLE COUNT MUST INCREASE",
    "EXPERIMENT DESIGN NOT YET IDENTIFIABLE",
}
ALLOWED_0L = {
    "HIGH-STRESS SAC305 CONSTITUTIVE MODEL VALIDATED -- RELATIVE-LIFE RESULT CONFIRMED",
    "CONSTITUTIVE LAW CORRECTED -- RELATIVE-LIFE RESULT SURVIVES",
    "HIGH-STRESS MODEL-FORM UNCERTAINTY PRESENT BUT Z2/Z1 RANKING SURVIVES",
    "RELATIVE-LIFE MAGNITUDE CHANGES -- RANKING SURVIVES",
    "RELATIVE-LIFE CLAIM NOT ROBUST TO HIGH-STRESS CONSTITUTIVE MODEL",
    "AVAILABLE SAC305 DATA INSUFFICIENT TO CLOSE HIGH-STRESS CONSTITUTIVE RESPONSE",
}
ALLOWED_0LR = {
    "HIGH-STRESS SAC305 MODEL CLOSED -- RELATIVE-LIFE MAGNITUDE VALIDATED",
    "HIGH-STRESS MODEL IMPROVED -- Z2/Z1 MAGNITUDE NARROWED",
    "Z2>Z1 ORDERING ROBUST -- RELATIVE-LIFE MAGNITUDE REMAINS CONDITIONAL",
    "Z2>Z1 ORDERING ITSELF BECOMES MODEL-FORM DEPENDENT",
    "DIRECT MATERIAL CHARACTERIZATION REQUIRED BEFORE RELIABILITY QUANTIFICATION",
    "PRIMARY DATA ACCESS REQUIRED BEFORE CONSTITUTIVE CLOSURE",
}
ALLOWED_0M = {
    "GEOMETRY-RESOLVED ARCHITECTURE MODEL CLOSED -- NEW ETM DESIGN VARIABLES PROVEN",
    "INTERCONNECT GEOMETRY MATERIALLY CHANGES ARCHITECTURE RANKING",
    "COMPONENT-LEVEL STACK PARTITIONING MATERIALLY CHANGES ARCHITECTURE RANKING",
    "Z5 CONCLUSION CHANGES AFTER PHYSICAL ROUTING RE-AUDIT",
    "COOLING ARCHITECTURE IS A FIRST-ORDER ETM DESIGN VARIABLE",
    "CURRENT COMPACT MODELS REMAIN ADEQUATE -- NEW GEOMETRY VARIABLES ARE SECOND ORDER",
    "MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER -- OPTIMIZATION STILL PREMATURE",
}
# Phase 0M-R, Section 26. Exactly one of these seven may be the dominant verdict.
ALLOWED_0MR = {
    "PHYSICAL PRODUCTION ETM PATH CLOSED -- CONTROLLED ARCHITECTURE REPLAY AUTHORISED",
    "PRODUCTION COUPLING CHANGES ARCHITECTURE ORDERING -- FURTHER PHYSICS CLOSURE REQUIRED",
    "PRODUCTION COUPLING PRESERVES THE DECIDING ARCHITECTURE ORDERING -- ABSOLUTE RESPONSES CHANGE MATERIALLY",
    "THE COOLING MODEL DOMINATES CURRENT ARCHITECTURE UNCERTAINTY",
    "RDL AND ROUTING PHYSICS DOMINATE",
    "INDEPENDENT VALIDATION FAILED -- PRODUCTION MODELS NOT TRUSTWORTHY",
    "MULTIPLE FIRST-ORDER COUPLINGS REMAIN OPEN -- PRODUCTION FRAMEWORK STILL NOT CLOSED",
}
# Phase 0M-R2, Section 18. Exactly one of these eight may be the dominant verdict.
ALLOWED_0MR2 = {
    "PHYSICAL ARCHITECTURE GEOMETRY CLOSED; Z2 < Z1 ORDERING SURVIVES",
    "Z2 < Z1 ORDERING SURVIVES, BUT FULL ARCHITECTURE REALIZABILITY REMAINS OPEN",
    "COOLING-MODEL VALIDITY CHANGES ABSOLUTE RESPONSES BUT NOT THE DECIDING ORDERING",
    "Z4 REORDERING WAS A GEOMETRIC SUBSTITUTION ARTIFACT; Z1/Z2 RESULT SURVIVES",
    "ARCHITECTURE ORDERING CHANGES AFTER PHYSICAL-GEOMETRY CLOSURE",
    "TSV/PACKAGE REALIZABILITY INVALIDATES ONE OR MORE CURRENT ARCHITECTURES",
    "COOLING CORRELATION IS OUTSIDE ITS VALID DOMAIN; THERMAL MAGNITUDES MUST BE WITHDRAWN",
    "PRODUCTION MODEL STILL NOT PHYSICALLY CLOSED -- NO ARCHITECTURE VERDICT BEYOND Z1/Z2 IS DEFENSIBLE",
}
# Phase 0M-R3, Section 24. Exactly one of these seven may be the dominant verdict.
ALLOWED_0MR3 = {
    "REALIZABLE Z1/Z2 PAIR FOUND -- Z2 < Z1 LOCAL RELIABILITY-RESPONSE ORDERING SURVIVES",
    "REALIZABLE Z1/Z2 PAIR FOUND -- MECHANICAL ORDERING COLLAPSES AFTER FEASIBILITY REPAIR",
    "REALIZABLE Z1/Z2 PAIR FOUND -- MECHANICAL ORDERING REVERSES",
    "NO REALIZABLE Z1/Z2 PAIR EXISTS IN THE CURRENT CONVERTER/PACKAGE LIBRARY",
    "Z1/Z2 FEASIBILITY REMAINS CONDITIONAL ON OPEN PACKAGE RULES",
    "COOLING MODEL REMAINS INSUFFICIENTLY VALIDATED FOR TEMPERATURE CLAIMS",
    "MULTIPLE PHYSICAL-REALIZABILITY BLOCKERS REMAIN",
}
# Phase 0M-R3A, Section 15.
ALLOWED_0MR3A = {
    "FINAL REPORT STATE CLOSED; Z1/Z2 CONDITIONAL REALIZABILITY AND ORDERING SURVIVE",
    "Z1/Z2 ORDERING SURVIVES BUT INTRA-VR VIA TECHNOLOGY REMAINS UNSOURCED",
    "Z2 TSV PROCESS-MARGIN REPAIR VALID; ORDERING UNCHANGED",
    "PHASE-0M-R3 VIA REPAIR USED THE WRONG PROCESS TECHNOLOGY",
    "PHASE-0M-R3 TSV COUNT CLAIM WAS NUMERICALLY WRONG BUT ARCHITECTURE ORDERING SURVIVES",
    "REALIZABILITY STATUS MUST BE REOPENED",
}
ALLOWED_0MR3B = {
    "SUBSTRATE-VIA TECHNOLOGY AND PACKAGE RULES CLOSED; Z1/Z2 PROVEN_REALIZABLE",
    "SUBSTRATE-VIA TECHNOLOGY CLOSED; PACKAGE CLEARANCES STILL BLOCK",
    "SUBSTRATE-VIA TECHNOLOGY REMAINS UNSOURCED; Z1/Z2 REMAIN CONDITIONAL",
    "PHYSICAL ls_to_L TOPOLOGY MAKES THE FROZEN Z1/Z2 PAIR NOT_REALIZABLE UNDER SOURCED "
    "SUBSTRATE-VIA RULES",
    "PHYSICAL VIA-CHAIN MODEL CHANGES ELECTRICAL RESULTS MATERIALLY, ORDERING SURVIVES",
    "PHYSICAL VIA-CHAIN MODEL CHANGES THE DECIDING Z1/Z2 ORDERING",
}
ALLOWED_0MR3C = {
    "SOURCE-COMPATIBLE REPARTITION FOUND; FINAL Z1/Z2 ETM ORDERING SURVIVES",
    "PROCESS-CONDITIONAL REPARTITION FOUND; THE FINAL Z1/Z2 RESPONSE ORDERING SURVIVES",
    "REPARTITION FOUND; Z1/Z2 RESPONSE ORDERING CHANGES",
    "NO REALIZABLE REPARTITION EXISTS IN THE CURRENT COMPONENT LIBRARY",
    "GEOMETRY CLOSES BUT PROCESS DATA REMAIN INSUFFICIENT; ARCHITECTURE CLAIM STAYS "
    "CONDITIONAL",
}
ALLOWED = {"0G": ALLOWED_0G, "0H": ALLOWED_0H, "0I": ALLOWED_0I, "0I-R": ALLOWED_0IR,
           "0J": ALLOWED_0J, "0J-R": ALLOWED_0JR, "0K": ALLOWED_0K, "0K-R": ALLOWED_0KR,
           "0L": ALLOWED_0L, "0L-R": ALLOWED_0LR, "0M": ALLOWED_0M, "0M-R": ALLOWED_0MR,
           "0M-R2": ALLOWED_0MR2, "0M-R3": ALLOWED_0MR3, "0M-R3A": ALLOWED_0MR3A, "0M-R3B": ALLOWED_0MR3B, "0M-R3C": ALLOWED_0MR3C}


def _key(ph: str) -> str:
    """'0I-R' -> 'phase0ir'."""
    return "phase" + ph.lower().replace("-", "")


def current_verdict(status):
    ph = status["meta"]["current_phase"]
    return ph, status["verdict"][_key(ph)]


def test_verdict_is_exactly_one_of_the_allowed_set(status):
    """Each phase brief fixes a closed list of verdicts. The chosen one must be on it."""
    ph, v = current_verdict(status)
    assert ph in ALLOWED, f"no allowed verdict set registered for phase {ph}"
    assert v in ALLOWED[ph], v


def test_every_recorded_rejection_set_is_complete(status):
    """Historical rejection sets must stay complete too, not decay as phases are added."""
    for ph, allowed in ALLOWED.items():
        key = "rejected_verdicts_" + _key(ph)
        if key in status["verdict"]:
            assert len(status["verdict"][key]) == len(allowed) - 1, key


def test_earlier_phase_verdicts_are_retained(status):
    """A later phase refines the earlier verdict; it must not silently erase it."""
    for ph, allowed in ALLOWED.items():
        key = _key(ph)
        if key in status["verdict"]:
            assert status["verdict"][key] in allowed, key


def test_every_rejected_verdict_is_recorded(status):
    """Choosing one verdict requires saying why each alternative was not chosen.

    Each phase records its own rejection set; earlier phases' sets are kept as history, so the
    key is phase-scoped with the unsuffixed key as the fallback for the phase that introduced
    it.
    """
    ph, _ = current_verdict(status)
    rej = status["verdict"].get("rejected_verdicts_" + _key(ph)) \
        or status["verdict"]["rejected_verdicts"]
    assert len(rej) == len(ALLOWED[ph]) - 1, (
        f"phase {ph} has {len(ALLOWED[ph])} candidate verdicts, so exactly "
        f"{len(ALLOWED[ph]) - 1} rejections must be recorded; found {len(rej)}")
    for k, why in rej.items():
        assert why.strip().lower().startswith("rejected"), k


def test_verdict_appears_in_generated_text(status, generated):
    _, v = current_verdict(status)
    assert v in generated


@pytest.mark.parametrize("bucket", ["proven", "supported", "conditional", "superseded"])
def test_every_claim_reaches_the_generated_text(status, generated, bucket):
    for c in status["claims"].get(bucket) or []:
        assert c["id"] in generated, f"{bucket} claim {c['id']} missing from generated text"
        assert flow(c["statement"])[:60] in flow(generated), c["id"]


def test_every_open_and_not_tested_item_reaches_the_text(status, generated):
    for item in status["open"] + status["not_tested"]:
        assert item["id"] in generated, item["id"]


def test_every_defect_reaches_the_text(status, generated):
    for d in status["phase0g_defects"]:
        assert f"DEFECT #{d['id']}" in generated
        assert d["title"] in generated


def test_conditional_claims_name_their_condition(status):
    """CONDITIONAL means 'true only under a named open input'. The name is mandatory."""
    for c in status["claims"]["conditional"]:
        assert c.get("condition"), f"{c['id']} is CONDITIONAL but names no condition"


def test_superseded_claims_name_their_replacement(status):
    for c in status["claims"]["superseded"]:
        assert c.get("superseded_by"), c["id"]
        assert c.get("phases_asserted"), c["id"]


def test_proven_claims_cite_evidence(status):
    for c in status["claims"]["proven"]:
        assert c.get("evidence"), f"{c['id']} is PROVEN but cites no evidence"


def test_withdrawn_claims_are_not_still_asserted(status):
    """The exact DEFECT #29 failure mode: a superseded claim still stated as current."""
    current = " ".join(
        flow(c["statement"]) + " " + flow(c.get("quantitative", ""))
        for b in ("proven", "supported", "conditional")
        for c in status["claims"].get(b) or []
    ).lower()
    forbidden = [
        ("assembly-state", "reversal"),      # withdrawn in Sec. 6/7
        ("footprint", "oppose"),             # withdrawn in Sec. 14
        ("interior", "optimum near"),        # ARCH_B, withdrawn in Sec. 2/4
    ]
    for a, b in forbidden:
        assert not (a in current and b in current), (
            f"a withdrawn claim ('{a}' + '{b}') is still stated as current")


def test_g2_is_still_not_tested(status):
    ids = {n["id"] for n in status["not_tested"]}
    assert "G2" in ids, "G2 must remain NOT_TESTED until an admissible criterion exists"
    claims = " ".join(flow(c["statement"]) for b in ("proven", "supported", "conditional")
                      for c in status["claims"].get(b) or [])
    assert "mechanical constraint" not in claims.lower()


def test_optimiser_is_not_recommended_while_either_condition_fails(status):
    """Phase-0G gate. Kept for as long as the gate is recorded."""
    g = status["verdict"].get("optimiser_gate")
    if g is None:
        pytest.skip("optimiser gate not recorded in this phase's verdict")
    c1, c2 = g["condition_1_assembly_response_survives"], \
        g["condition_2_criterion_or_epsilon_alters_feasible_set"]
    if c1 is not True or c2 is not True:
        assert g["recommended"] is False
        assert status["meta"]["optimiser_built"] is False


def test_optimiser_is_neither_built_nor_recommended(status):
    """The standing stop condition, independent of how any phase words its gate."""
    assert status["meta"]["optimiser_built"] is False
    assert status["meta"].get("optimiser_recommended") is False


def test_g2_status_is_consistent_with_the_claims(status):
    """G2 may only be anything other than NOT_TESTED if an admissible criterion exists."""
    if status["verdict"].get("g2_status") == "NOT_TESTED":
        blob = " ".join(flow(c.get("statement", "")) for b in ("proven", "supported",
                                                               "conditional")
                        for c in status["claims"].get(b) or []).lower()
        assert "admissible criterion exists" not in blob
        assert "criterion binds" not in blob


def test_next_gate_is_not_the_optimiser(status):
    ng = status["next_gate"]
    assert "optimi" in ng["explicitly_not_next"].lower()
    assert "optimi" not in ng["id"].lower()


@pytest.mark.skipif(not REPORT.exists(), reason="report not built yet")
def test_report_contains_the_generated_block(generated):
    """Guards against someone hand-editing the status text back into drift."""
    body = REPORT.read_text()
    anchors = [ln for ln in generated.splitlines()
               if ln.startswith("### ") or ln.startswith("#### ")]
    assert anchors, "generated text has no headings to anchor on"
    missing = [a for a in anchors if a not in body]
    assert not missing, f"report is missing generated headings: {missing[:3]}"
