"""PHASE 0N-AH --- the computational story must not overclaim."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))

D = R / "research" / "phase0nah"


@pytest.fixture(scope="module")
def hier():
    return list(csv.DictReader((D / "model_hierarchy.csv").open()))


@pytest.fixture(scope="module")
def claims():
    return list(csv.DictReader((D / "computational_claim_matrix.csv").open()))


def test_thermal_and_mechanical_are_labelled_FEM(hier):
    """VERIFIED AGAINST HEAD: ccxio writes C3D8 / C3D8I and runs CalculiX."""
    by = {h["stage"]: h for h in hier}
    assert by["package thermal field"]["type"] == "FEM"
    assert by["global mechanics"]["type"] == "FEM"
    assert "nonlinear" in by["local solder"]["type"].lower()
    src = (R / "scripts/phase0b/etm/ccxio.py").read_text()
    assert "C3D8" in src and "C3D8I" in src


def test_no_stage_claims_analytical_when_it_runs_an_fe_solver(hier):
    for h in hier:
        if "thermal field" in h["stage"] or "mechanic" in h["stage"] or \
                "solder" in h["stage"]:
            assert "ANALYTICAL" not in h["type"]


ALLOWED_EVIDENCE = {
    "INDEPENDENT_NUMERICAL_VALIDATION",  # checked against a separate solver
    "SOURCE_REPRODUCTION",               # we recomputed the source's OWN inputs
    "CLOSED_FORM_VERIFICATION",          # checked against an exact expression
    "CONSERVATION_VERIFICATION",         # an identity closes, nothing external
    "MESH_CONVERGENCE",                  # self-refinement only
    "ITERATION_CONVERGENCE",             # fixed point settles, nothing external
    "UNVALIDATED",                       # no external reference at all
}


def test_evidence_classes_do_not_collapse_reproduction_into_validation(hier):
    """A bare 'VALIDATION' label hid three different strengths of evidence."""
    classes = {h["evidence_class"] for h in hier}
    assert classes <= ALLOWED_EVIDENCE, sorted(classes - ALLOWED_EVIDENCE)
    assert "VALIDATION" not in classes, (
        "bare VALIDATION is ambiguous: it covered independent-solver checks, "
        "closed-form checks and reproducing a paper's own arithmetic")

    # Reproducing DVPD Table III from the source's own rho/L/A is NOT
    # independent validation -- it validates nothing beyond internal
    # consistency of the published table.
    t3 = [h for h in hier if "Table III" in h["independent_reference"]]
    assert t3, "the Table III row disappeared"
    for h in t3:
        assert h["evidence_class"] == "SOURCE_REPRODUCTION"
        assert "OWN" in h["independent_reference"]

    # every stage with no external reference must say so in its class
    for h in hier:
        ref = h["independent_reference"].strip().lower()
        if ref in ("", "none") or ref.startswith("none "):
            assert h["evidence_class"] in {
                "UNVALIDATED", "MESH_CONVERGENCE", "ITERATION_CONVERGENCE",
                "CONSERVATION_VERIFICATION"}, h["stage"]

    # a self-convergence class may never also claim an external error figure
    for h in hier:
        if h["evidence_class"] in {"MESH_CONVERGENCE", "ITERATION_CONVERGENCE"}:
            assert "none" in h["independent_reference"].lower() or \
                not h["independent_reference"].strip(), h["stage"]


def test_no_commercial_speedup_is_claimed():
    s = json.loads((D / "model_hierarchy_summary.json").read_text())
    assert s["commercial_speedup"] is None
    assert "NOT ESTABLISHED" in s["commercial_status"]
    md = (D / "commercial_benchmark_status.md").read_text()
    assert "No controlled commercial speedup has been established" in md
    assert "No speedup against a higher-fidelity reference is claimed." in md


def test_the_speedup_claim_is_marked_unsupported(claims):
    by = {c["claim"]: c for c in claims}
    bad = [c for c in claims if "faster than commercial" in c["claim"]]
    assert bad and bad[0]["classification"] == "NOT_SUPPORTED"
    single = [c for c in claims if "single accuracy percentage" in c["claim"]]
    assert single and single[0]["classification"] == "NOT_SUPPORTED"


def test_literature_speedups_are_not_transferred(claims):
    lit = [c for c in claims if c["classification"] == "LITERATURE_CONTEXT"]
    assert lit
    for c in lit:
        assert "NOT transferred" in c["evidence"] or "not transferred" in c["evidence"]


def test_runtime_is_flagged_historical():
    rows = list(csv.DictReader((D / "runtime_breakdown.csv").open()))
    assert rows
    for r in rows:
        assert (r["provenance"] == "HISTORICAL_FROZEN_R3C_RUNTIME"
                or r["provenance"].startswith("DERIVED_SERIAL_SUM")), r["stage"]
    s = json.loads((D / "model_hierarchy_summary.json").read_text())
    assert "has NOT been re-benchmarked" in s["runtime_caveat"]


# --- runtime accounting: the ETM figure does NOT contain the local solder -----

ETM_WALL_S = {"Z1": 134.62, "Z2": 204.23}
LOCAL_WALL_S = {"Z1": 44.99, "Z2": 35.14}
LOCAL_CORES = 128
ETM_THREADS = 48


def _runtime_prose_findings(text):
    """Bad patterns in runtime prose. Whitespace is flattened FIRST, because a
    markdown line wrap between 'cost' and '**135 s' defeated earlier guards."""
    # spans explicitly marked as retracted are quoted evidence of a past error,
    # not live claims -- strip them, then bound how many may exist (below).
    text = re.sub(r"\[RETRACTED\].*?\[/RETRACTED\]", " ", text, flags=re.S)
    flat = " ".join(text.split())
    out = []

    # 1. the ETM-only figure attributed to a stage count that would sweep in
    #    the local solder submodel -- the actual DEFECT this guard exists for
    for m in re.finditer(r"(?:three|3|all|the)\s+FE\s+stages?[^.]{0,90}",
                         flat, re.I):
        if re.search(r"13[0-9]|20[0-9]", m.group(0)):
            out.append("FE-stage count carries the ETM-only runtime: "
                       + m.group(0))

    # 2. the ETM figure stated anywhere without the exclusion being stated
    if re.search(r"134\.62|\b135 s\b", flat) and "exclud" not in flat.lower():
        out.append("ETM runtime stated with no local-solder exclusion")

    # 3. an arithmetic total presented without the DERIVED_SERIAL_SUM label
    for tot in (ETM_WALL_S[c] + LOCAL_WALL_S[c] for c in ETM_WALL_S):
        if ("%.2f" % tot) in flat and "DERIVED_SERIAL_SUM" not in flat:
            out.append("arithmetic total %.2f lacks DERIVED_SERIAL_SUM" % tot)
    return out


def test_hierarchy_doc_runtime_prose_is_clean():
    assert _runtime_prose_findings((D / "MODEL_HIERARCHY.md").read_text()) == []


def test_retracted_spans_are_bounded_and_labelled_as_wrong():
    """[RETRACTED] blinds the prose guard, so it must not become a loophole."""
    md = (D / "MODEL_HIERARCHY.md").read_text()
    spans = re.findall(r"\[RETRACTED\](.*?)\[/RETRACTED\]", md, flags=re.S)
    assert len(spans) == 1, "a new retracted span appeared; justify it here"
    # the correction must sit next to the retraction, not elsewhere
    tail = " ".join(md.split("[/RETRACTED]", 1)[1].split())[:300].lower()
    assert "folded a third stage into a figure that does not contain it" in tail
    # and the live text must still carry the right numbers
    assert "135" in spans[0] and "134.62" not in spans[0]


def test_guard_catches_the_REAL_offending_sentence():
    """Permanent negative test. This is the exact text that shipped, including
    its line wrap -- not a paraphrase of it."""
    offending = (
        "Every analytical and reduced stage together costs **under 5 s**. "
        "The three FE stages cost\n"
        "**135 s (Z1) and 204 s (Z2)**. So the honest statement is not that "
        "the framework is\nanalytical, but:")
    found = _runtime_prose_findings(offending)
    assert found, "the guard does not catch the sentence it was written for"
    assert any("FE-stage count" in f for f in found)


def test_doc_runtime_numbers_match_their_source_artifacts():
    """MODEL_HIERARCHY.md restates numbers owned by results/phase0mr3c/.
    Tie them, so a change upstream breaks the build instead of going stale."""
    bench = {r["case"]: r for r in csv.DictReader(
        (R / "results/phase0mr3c/runtime_benchmark.csv").open())
        if r["stage"].startswith("full ETM")}
    loc = {r["case"]: r for r in csv.DictReader(
        (R / "results/phase0mr3c/final_local_response.csv").open())}
    md = " ".join((D / "MODEL_HIERARCHY.md").read_text().split())

    for case in ("Z1", "Z2"):
        assert float(bench[case]["wall_s"]) == ETM_WALL_S[case]
        assert float(loc[case]["wall_s"]) == LOCAL_WALL_S[case]
        assert int(bench[case]["threads"]) == ETM_THREADS
        assert int(loc[case]["n_core"]) == LOCAL_CORES
        assert ("%.2f" % ETM_WALL_S[case]) in md
        assert ("%.2f" % LOCAL_WALL_S[case]) in md
        assert ("%.2f" % (ETM_WALL_S[case] + LOCAL_WALL_S[case])) in md

    # the local stage ran on 128 cores; the doc previously implied 48
    assert "128" in md
    assert "DERIVED_SERIAL_SUM" in md


def test_runtime_breakdown_carries_the_local_stage_separately():
    rows = list(csv.DictReader((D / "runtime_breakdown.csv").open()))
    etm = [r for r in rows if r["stage"].startswith("full ETM")]
    loc = [r for r in rows if "local solder response" in r["stage"]]
    tot = [r for r in rows if "arithmetic total" in r["stage"]]
    assert len(etm) == 2 and len(loc) == 2 and len(tot) == 2

    for r in etm:
        assert "EXCLUDES the local solder" in r["stage"]
        assert float(r["wall_s"]) == ETM_WALL_S[r["case"]]
        # the ETM row must never carry the summed value
        assert float(r["wall_s"]) != pytest.approx(
            ETM_WALL_S[r["case"]] + LOCAL_WALL_S[r["case"]])
    for r in loc:
        assert float(r["wall_s"]) == LOCAL_WALL_S[r["case"]]
        assert int(r["threads"]) == LOCAL_CORES
    for r in tot:
        assert r["provenance"].startswith("DERIVED_SERIAL_SUM")
        assert "not a measured wall interval" in r["provenance"]
        assert float(r["wall_s"]) == pytest.approx(
            ETM_WALL_S[r["case"]] + LOCAL_WALL_S[r["case"]], abs=0.005)


def test_manuscript_keeps_the_local_stage_outside_the_etm_figure():
    """The manuscript was already correct -- assert it stays that way."""
    tex = " ".join((R / "manuscript"
                    / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex").read_text().split())
    assert "The local solder submodel is a further" in tex
    assert _runtime_prose_findings(tex) == []


def test_measured_claims_point_at_real_numbers(claims):
    for c in claims:
        if c["classification"] == "MEASURED":
            assert any(ch.isdigit() for ch in c["evidence"])


def test_generality_audit_separates_spec_from_hardcoding():
    rows = list(csv.DictReader((D / "architecture_generality_audit.csv").open()))
    kinds = {r["classification"] for r in rows}
    assert kinds <= {"SYSTEM_SPECIFICATION", "MODEL_LIMITATION",
                     "ACCIDENTAL_HARDCODING", "DERIVED"}
    hard = [r for r in rows if r["classification"] == "ACCIDENTAL_HARDCODING"]
    assert hard, "the audit must name what is actually hard-coded"
    lim = [r for r in rows if r["classification"] == "MODEL_LIMITATION"]
    assert any("topology" in r["note"] for r in lim), (
        "a different converter topology needs a new model, not a config change")


def test_the_framework_is_not_described_as_replacing_fem():
    import re as _re
    # markdown wraps, so a phrase can straddle a newline -- compare flattened, the same
    # trap the Phase-0N-V prose guards hit
    md = _re.sub(r"\s+", " ", (D / "MODEL_HIERARCHY.md").read_text().replace("**", ""))
    assert "not an analytical framework that replaces FEM" in md
    assert "Convergence is not accuracy" in md
    assert "no single framework accuracy percentage" in md.lower()
    assert "both are finite element" in md.lower()


def test_evidence_class_counts_in_prose_match_the_csv(hier):
    """The doc restates per-class counts. Re-derive them so a reclassification
    in the CSV cannot leave the prose a phase behind (DEFECT #57 pattern)."""
    import collections
    c = collections.Counter(h["evidence_class"] for h in hier)
    assert sum(c.values()) == len(hier) == 12
    md = (D / "MODEL_HIERARCHY.md").read_text()
    for cls, n in c.items():
        assert re.search(r"`%s`\s*\|\s*%d\b" % (re.escape(cls), n), md), \
            "prose table missing or stale for %s=%d" % (cls, n)
    # the headline sentence must quote the independent-validation count
    n_indep = c["INDEPENDENT_NUMERICAL_VALIDATION"]
    assert re.search(r"Only \*\*%d\*\* of twelve stages" % n_indep, md)
    # and must not silently revert to the overstated figure
    assert not re.search(r"Only \*\*6\*\* of twelve", md)
