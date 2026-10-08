#!/usr/bin/env python3
"""Phase-0M-R3A Section 13, items A-P.

Every semantic item is negative-tested with the ACTUAL offending sentence taken from the
preserved Phase-0M-R3 baseline under results/phase0mr3a/_baseline_phase0mr3/, never a
paraphrase. DEFECT #31, #36, #54 and #56 all hid behind guards written against a
paraphrase of the claim rather than the claim, so a guard that has not rejected the real
sentence is not evidence of anything.

The numeric items (J-N) re-derive from sourced constants in this file and never import the
production interconnect model, so agreement is a cross-check and not a tautology.
"""
from __future__ import annotations
import csv, importlib.util, math, re, sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3a"
BASE = OUT / "_baseline_phase0mr3"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
STATUS = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"

# Derived, not pinned: this file asserted 0M-R3A and went stale the moment a later
# gate landed -- the same failure mode as DEFECT #57.
PHASE = yaml.safe_load(CONTRACT.read_text())["meta"]["gates"][-1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sa = _load("sa", R / "scripts" / "phase0mr3" / "semantic_audit.py")
fsa = _load("fsa", R / "scripts" / "phase0mr3a" / "final_state_audit.py")

# One definition of the offending sentences, shared with the artifact generator so the
# tests and results/phase0mr3a/semantic_negative_tests.csv cannot disagree.
CORPUS = fsa.NEGATIVE_CORPUS
CONTROL = fsa.POSITIVE_CONTROL


def corpus(item: str) -> list[str]:
    got = [c[3] for c in CORPUS if c[0] == item]
    assert got, f"no offending sentence recorded for Section 13 item {item}"
    return got


def rows(name: str, base: Path = OUT) -> list[dict]:
    return list(csv.DictReader((base / name).open()))


@pytest.fixture(scope="module")
def status() -> dict:
    return yaml.safe_load(STATUS.read_text())


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text())


@pytest.fixture(scope="module")
def reports() -> dict[str, str]:
    return {"historical": HIST.read_text(), "standalone": STAND.read_text()}


def fires(body: str, contract: dict) -> list[dict]:
    return sa.audit(body, contract)


def inject(body: str, sentence: str) -> str:
    """Put an offending sentence into a CURRENT-facing section of the report.

    It goes inside the executive summary, which no historical marker covers, so a guard
    that stays silent here is genuinely not looking.
    """
    anchor = "**Method.**"
    assert anchor in body, "executive summary anchor missing"
    return body.replace(anchor, sentence + "\n\n" + anchor, 1)


# ------------------------------------------------------------------ A, B: phase + verdict
def test_A_current_phase_is_0mr3a(status):
    assert status["meta"]["current_phase"] == PHASE
    assert status["current_state_contract"]["current_phase"]["state"] == f"{PHASE} complete"


def test_B_verdict_propagated_everywhere(status, reports):
    key = f"phase{PHASE.lower().replace('-', '')}"
    letter = status["verdict"][key + "_option_letter"]
    assert letter in "ABCDEFGH" and len(letter) == 1
    assert status["verdict"][key].strip()
    assert f"(option {letter})" in \
        status["current_state_contract"]["current_verdict"]["state"]
    for name, body in reports.items():
        assert PHASE in body, name
    # the standalone is a current-state document: it must NOT advertise an older phase as
    # the state of the framework
    assert "as it exists after Phase 0M-R3\"" not in reports["standalone"]
    assert f"| Phase completed | {PHASE}," in reports["standalone"]


# ------------------------------------------------------------------ C: no 0M-R2 block
def test_C_no_phase0mr2_current_state_block(status, reports, contract):
    """DEFECT #57. The rendered table said 0M-R2 while meta said 0M-R3."""
    for key, field in status["current_state_contract"].items():
        if not isinstance(field, dict):
            continue
        val = str(field.get("state", ""))
        assert not val.startswith("0M-R2 complete"), key
        assert "ZERO OF TWELVE REALIZABLE" not in val, key
    # The phrase itself is allowed where the record DESCRIBES the defect. What must not
    # survive is its assertion as a current-state table cell, which is the form it shipped
    # in: "| component partition status | **ZERO OF TWELVE REALIZABLE, AT ANY CORNER ...**".
    asserted = re.compile(r"(?m)^\|[^|]*\|\s*\*\*(?:ZERO OF TWELVE REALIZABLE|0M-R2 complete)")
    for name, body in reports.items():
        assert "| phase | **0M-R2 complete** |" not in body, name
        assert not asserted.search(body), (name, asserted.search(body).group(0))

    # negative test: the guard must reject the two real baseline rows
    base = (BASE / "ETM_DVPD_FULL_TECHNICAL_REPORT.md").read_text()
    stale = ("| phase | **0M-R2 complete** | "
             "`results/phase0mr2/PHASE0MR2_REALIZABILITY_COOLING_STATE_CLOSURE.md` |")
    assert stale in base, \
        "the baseline no longer contains the sentence this test exists to reject"
    assert asserted.search(base), "the row form is not detected in the baseline that had it"
    assert asserted.search(stale + "\n"), "guard does not reject the phase row"


# ------------------------------------------------------------------ D, E: next work
def test_D_exactly_one_current_next_work_source(status):
    ng = status["next_gate"]
    field = status["current_state_contract"]["current_next_work"]["state"]
    blob = (yaml.safe_dump(ng) + " " + field).lower()
    for done in ("adopt the phase-0m physical cooling model",
                 "put the rdl in the mechanical mesh"):
        assert done not in blob, done
    # both sources must name the SAME next action
    assert "intra" in blob and "0n is not authorised" in field.lower()
    assert "complete and not to be relisted" in field.lower(), \
        "the completed actions must be named as completed, not merely omitted"


@pytest.mark.parametrize("sentence", corpus("E"))
def test_E_completed_task_never_listed_as_future_work(reports, contract, sentence):
    """Both sentences are verbatim from results/.../_baseline_phase0mr3/ lines 4276-4277."""
    for name, body in reports.items():
        assert sentence not in body, f"{name} still lists a completed action as next work"
    hits = fires(inject(reports["historical"], sentence), contract)
    assert any(f["rule_id"] == "single_next_work" for f in hits), \
        f"guard single_next_work did not reject: {sentence[:60]}"


# ------------------------------------------------------------------ F: terminology
@pytest.mark.parametrize("sentence", corpus("F"))
def test_F_response_is_not_damage_or_life(reports, contract, sentence):
    for name, body in reports.items():
        cur = body.split("# Phase 0I")[0]
        assert sentence not in cur, name
    hits = fires(inject(reports["historical"], sentence), contract)
    assert any(f["rule_id"] == "response_not_damage_life_failure" for f in hits), \
        f"terminology guard did not reject: {sentence[:60]}"


def test_F_positive_current_wording_is_response(reports):
    assert "local fatigue-relevant inelastic response" in reports["standalone"]


# ------------------------------------------------------------------ G: 35.8 % historical
def test_G_358_never_the_current_repaired_pair_result(reports, contract):
    for sentence in corpus("G"):
        hits = fires(inject(reports["historical"], sentence), contract)
        assert any(f["rule_id"] == "historical_358_not_current" for f in hits), sentence
    # and the number that IS current
    assert "16.3" in reports["historical"]


# ------------------------------------------------------------------ H, I: provenance
def test_H_ls_to_L_provenance_exists():
    pr = rows("interconnect_technology_provenance.csv")
    assert len(pr) >= 5
    chain = " ".join(r["value"] + " " + r["detail"] for r in pr)
    assert "ls_to_L" in chain
    assert any(r["provenance"] in ("MODEL", "SOURCE_BACKED", "OPEN") for r in pr)
    assert any(r["provenance"] == "OPEN" for r in pr), \
        "DEFECT #58: the governing process rule is OPEN and must be recorded as OPEN"


def test_I_process_rule_source_matches_interconnect_class(status):
    """The TSV range must not be silently reused for the intra-VR stacked via."""
    reg = {int(x["id"]): x for x in status["phase0g_defects"]}
    for n in (57, 58, 59):
        assert n in reg, f"DEFECT #{n} not registered"
    txt = yaml.safe_dump(reg[58]).lower()
    assert "tsv" in txt and ("673" in txt or "intra" in txt)
    assert "22.8 % fewer" in yaml.safe_dump(reg[59]).lower()


def test_I_span_separates_the_two_structures():
    pr = {r["step"]: r for r in rows("interconnect_technology_provenance.csv")}
    blob = " ".join(r["detail"] + r["value"] for r in pr.values())
    assert "673" in blob, "the ls_to_L span must be stated"
    assert "74" in blob, "the Z1 TSV span must be stated alongside it"


# ------------------------------------------------------------------ J-N: the arithmetic
# Sourced constants, re-stated here so these tests do not import the production model.
I_CELL_A = 1000.0 / 49.0
I_TOTAL_A = 1000.0
J_DESIGN = 1.0e8          # A/m2
T_LINER_UM = 0.5
S_MIN_UM = 30.0           # SOURCE_BACKED minimum spacing
PACKING = 0.5
FOOTPRINT_MM2 = 1.8       # via-field pad area for ls_to_L
KOZ = 0.0
L_Z2_UM = 300.0
AR_MAX = 10.0


def n_req(i_a: float, r_um: float) -> int:
    a_cu = math.pi * ((r_um - T_LINER_UM) * 1e-6) ** 2
    return max(1, math.ceil(i_a / (J_DESIGN * a_cu)))


def pitch_um(r_um: float) -> float:
    return max(2 * r_um + S_MIN_UM, 2 * r_um * (1 + KOZ))


def n_avail(area_mm2: float, r_um: float) -> int:
    p = pitch_um(r_um) * 1e-6
    return max(1, int(area_mm2 * 1e-6 * PACKING / p ** 2))


@pytest.mark.parametrize("row", rows("ls_to_L_via_check.csv"))
def test_J_independent_n_required(row):
    assert n_req(I_CELL_A, float(row["r_um"])) == int(row["n_required"])


@pytest.mark.parametrize("row", rows("ls_to_L_via_check.csv"))
def test_K_independent_n_available(row):
    r = float(row["r_um"])
    assert pitch_um(r) == pytest.approx(float(row["pitch_um"]))
    assert n_avail(FOOTPRINT_MM2, r) == int(row["n_available"])


def test_K_ratio_reproduces_production():
    for row in rows("ls_to_L_via_check.csv"):
        assert float(row["ratio"]) == pytest.approx(
            float(row["production_ratio"]), abs=5e-5), row["r_um"]
    at = {float(r["r_um"]): float(r["ratio"]) for r in rows("ls_to_L_via_check.csv")}
    assert at[15.0] == pytest.approx(1.2360, abs=5e-5)
    assert at[20.0] == pytest.approx(0.9344, abs=5e-5)
    assert at[15.0] > 1.0 > at[20.0], "the repair must actually change feasibility"


def test_L_30_to_34_um_reduces_the_required_count():
    """DEFECT #59. Phase 0M-R3 said 22.8 % MORE vias. n_required scales as 1/A_cu."""
    z = {float(r["d_um"]): r for r in rows("z2_tsv_diameter_sweep.csv")}
    a, b = int(z[30.0]["n_required"]), int(z[34.0]["n_required"])
    assert a == n_req(I_TOTAL_A, 15.0) and b == n_req(I_TOTAL_A, 17.0)
    assert b < a, "enlarging the via cannot increase the required count"
    assert 100 * (a - b) / a == pytest.approx(22.8, abs=0.1)


def test_L_copper_fraction_is_radius_independent():
    phi = [float(r["phi_cu"]) for r in rows("z2_tsv_diameter_sweep.csv")]
    assert max(phi) - min(phi) < 1e-3 * phi[0], \
        "phi_Cu = I/(J*A_field) must not depend on the via radius"


def test_M_counts_are_ordered():
    for r in rows("z2_tsv_diameter_sweep.csv"):
        nr, na, nv = (int(r["n_required"]), int(r["n_allocated"]),
                      int(r["n_available"]))
        assert nr <= na <= nv, r["d_um"]


def test_N_tsv_ar_margin():
    z = {float(r["d_um"]): r for r in rows("z2_tsv_diameter_sweep.csv")}
    for d, r in z.items():
        assert float(r["AR"]) == pytest.approx(L_Z2_UM / d, rel=1e-9)
        assert float(r["M_AR"]) == pytest.approx(AR_MAX / float(r["AR"]), rel=1e-9)
    assert float(z[30.0]["M_AR"]) == pytest.approx(1.0, abs=1e-9)
    assert z[30.0]["passes_modest_bound"] == "False"
    assert z[32.0]["passes_modest_bound"] == "True", \
        "32 um passes and was never evaluated by the 0M-R3 grid"
    assert 32.0 == min(d for d, r in z.items() if r["passes_modest_bound"] == "True")


# ------------------------------------------------------------------ O: wording
@pytest.mark.parametrize("sentence", corpus("O"))
def test_O_sourced_range_not_exact_source(reports, contract, sentence):
    hits = fires(inject(reports["historical"], sentence), contract)
    assert any(f["rule_id"] == "via_provenance_precise" for f in hits), \
        f"via provenance guard did not reject: {sentence[:60]}"


@pytest.mark.parametrize("rule_id,sentence", CONTROL)
def test_O_record_is_not_mistaken_for_the_claim(reports, contract, rule_id, sentence):
    """A guard that rejects the retraction of a claim is over-firing, not working."""
    hits = fires(inject(reports["historical"], sentence), contract)
    assert not any(f["rule_id"] == rule_id for f in hits), \
        f"{rule_id} rejected the record that withdraws the claim: {sentence[:60]}"


# ------------------------------------------------------------------ P: report consistency
def test_P_reports_are_semantically_clean(reports, contract):
    for name, body in reports.items():
        assert fires(body, contract) == [], name


def test_P_gate_count_agrees(contract, reports):
    gates = contract["meta"]["gates"]
    assert gates[-1] == PHASE
    for name, body in reports.items():
        m = re.search(r"([\w-]+) sequential falsification gates\s*\(([^)]*)\)",
                      re.sub(r"\s+", " ", body))
        assert m, name
        assert m.group(1) == sa.NUMWORD[len(gates)], (name, m.group(1))
        assert [x.strip() for x in m.group(2).split(",")] == gates, name


def test_P_baseline_artifacts_are_untouched():
    """Phase 0M-R3 artifacts must survive this phase byte-identically."""
    ok = bad = 0
    for line in (BASE / "MD5SUMS.txt").read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        import hashlib
        p = R / name.strip().lstrip("*")
        got = hashlib.md5(p.read_bytes()).hexdigest()
        ok, bad = (ok + 1, bad) if got == digest else (ok, bad + 1)
    assert bad == 0 and ok >= 10, f"{bad} baseline files changed"


def test_P_negative_test_artifact_is_complete():
    rws = rows("semantic_negative_tests.csv")
    neg = [r for r in rws if r["kind"] == "negative"]
    assert len(neg) == len(CORPUS)
    assert all(r["guard_fired"] == "True" for r in neg), \
        [r["sentence"][:50] for r in neg if r["guard_fired"] != "True"]
    ctl = [r for r in rws if r["kind"] == "control"]
    assert ctl and all(r["guard_fired"] == "False" for r in ctl)
    # every Section-13 semantic item must have at least one real sentence behind it
    assert {c[0] for c in CORPUS} >= {"C", "E", "F", "G", "O", "P"}


def test_P_before_after_delta():
    before, after = rows("stale_claims_before.csv"), rows("stale_claims_after.csv")
    assert len(before) >= 10, "the baseline is supposed to be dirty"
    assert after == [], after


def test_P_sentinel_blocks_unique(reports):
    from collections import Counter
    for name, body in reports.items():
        dup = [k for k, n in Counter(
            re.findall(r"<!-- BEGIN GENERATED: (\w+) -->", body)).items() if n > 1]
        assert not dup, (name, dup)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
