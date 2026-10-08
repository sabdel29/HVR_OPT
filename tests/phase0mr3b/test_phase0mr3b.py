#!/usr/bin/env python3
"""Phase-0M-R3B Section 12.

Every semantic guard is negative-tested with the ACTUAL offending sentence, recovered from
the shipped Phase-0M-R3A documents rather than written alongside the guard. The numeric
tests re-derive from sourced constants and never import the production routing model, so
agreement is a cross-check and not a tautology.
"""
from __future__ import annotations
import csv, importlib.util, math, os, re, subprocess, sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"
BASE = OUT / "_baseline_phase0mr3a"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
STATUS = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
# Derived, not pinned: pinning is what made this file stale at the next gate.
PHASE = yaml.safe_load(CONTRACT.read_text())["meta"]["gates"][-1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sa = _load("sa", R / "scripts" / "phase0mr3" / "semantic_audit.py")


def rows(name, base=OUT):
    return list(csv.DictReader((Path(base) / name).open()))


@pytest.fixture(scope="module")
def status():
    return yaml.safe_load(STATUS.read_text())


@pytest.fixture(scope="module")
def contract():
    return yaml.safe_load(CONTRACT.read_text())


@pytest.fixture(scope="module")
def reports():
    return {"historical": HIST.read_text(), "standalone": STAND.read_text()}


def inject(body: str, sentence: str) -> str:
    """Put an offending sentence into a CURRENT-facing section."""
    anchor = "**Method.**"
    assert anchor in body
    return body.replace(anchor, sentence + "\n\n" + anchor, 1)


# The real sentences, verbatim from the Phase-0M-R3A documents this phase corrected.
DAMAGE_CORPUS = [
    "the joint's damage-weighted median stress is about 82 MPa and 99.8 % of its damage "
    "lies outside that window",
    "while 99.8 % of package damage is generated outside that window",
    "Temperature enters the damage physics through more than thermal expansion",
    "a convergent local solder viscoplastic damage metric (M2) added in Phase 0I",
]


# ------------------------------------------------------------------ phase / provenance
def test_current_phase_and_provenance_are_0mr3b(status, contract, reports):
    assert status["meta"]["current_phase"] == PHASE
    assert status["current_state_contract"]["current_phase"]["state"] == f"{PHASE} complete"
    assert contract["meta"]["gates"][-1] == PHASE
    m = re.search(r"\|\s*Phase completed\s*\|\s*([^|]+)\|", reports["historical"])
    assert m and m.group(1).strip().startswith(PHASE), m.group(1) if m else "no row"


def test_provenance_guard_rejects_a_stale_row(reports, contract):
    """The real row that shipped: the table froze at 0M-R3 while 0M-R3A was current."""
    stale = "| Phase completed | 0M-R3, 2026-09-19 |"
    assert stale in (BASE / "ETM_DVPD_FULL_TECHNICAL_REPORT.md").read_text(), \
        "the baseline no longer carries the row this test exists to reject"
    body = re.sub(r"\|\s*Phase completed\s*\|[^|]*\|", stale, reports["historical"], count=1)
    hits = sa.audit(body, contract)
    assert any(f["rule_id"] == "provenance_is_current" for f in hits)


def test_provenance_guard_rejects_a_report_predating_its_phase(reports, contract):
    body = re.sub(r"\|\s*Report generated\s*\|[^|]*\|",
                  "| Report generated | 2026-01-01 |", reports["historical"], count=1)
    assert any(f["rule_id"] == "provenance_is_current" for f in sa.audit(body, contract))


# ------------------------------------------------------------------ terminology
@pytest.mark.parametrize("sentence", DAMAGE_CORPUS)
def test_no_current_damage_wording_for_the_fe_response(reports, contract, sentence):
    for name, body in reports.items():
        assert sentence not in body, f"{name} still asserts: {sentence[:50]}"
    hits = sa.audit(inject(reports["historical"], sentence), contract)
    assert any(f["rule_id"] == "weighting_is_response_not_damage" for f in hits), \
        f"guard did not reject: {sentence[:60]}"


def test_the_weighting_is_what_the_code_actually_computes():
    """The weight is dPEEQ * V. If that ever becomes a damage law, this test must fail."""
    src = (R / "scripts" / "phase0lr" / "mechanism_audit.py").read_text()
    fn = src[src.index("def elementwise_damage"):src.index("def wq(")]
    assert "float(d[\"P\"]) - prev[1]" in fn and "dp*v" in fn, \
        "the weight is no longer dPEEQ * V; the licensed wording must be re-derived"
    for law in ("coffin", "manson", "darveaux", "cycles_to_fail", "N_f"):
        assert law not in fn.lower(), f"a damage law appeared in the weight: {law}"


def test_the_record_may_still_quote_the_forbidden_wording(reports, contract):
    """A defect register that cannot name what it forbids is useless."""
    notice = ("DEFECT #60: current-facing text said `damage-weighted median stress`, "
              "which is withdrawn.")
    hits = sa.audit(inject(reports["historical"], notice), contract)
    assert not any(f["rule_id"] == "weighting_is_response_not_damage" for f in hits)


def test_response_damage_life_failure_ladder_intact(reports, contract):
    for sentence in ("Z2 outlives Z1 at the operating baseline.",
                     "Z2 accumulates less solder-fatigue damage than Z1"):
        hits = sa.audit(inject(reports["historical"], sentence), contract)
        assert any(f["rule_id"] == "response_not_damage_life_failure" for f in hits)


def test_apostrophe_does_not_exonerate(contract, reports):
    """DEFECT #61: 'the joint's X' was read as quoted because of the possessive."""
    s = "the joint's damage-weighted median stress is about 82 MPa"
    hits = sa.audit(inject(reports["historical"], s), contract)
    assert any(f["rule_id"] == "weighting_is_response_not_damage" for f in hits), \
        "an intra-word apostrophe is exonerating matches again"


# ------------------------------------------------------------------ interconnect class
def test_every_vertical_net_has_a_recorded_interconnect_class():
    sp = rows("vertical_span_correction.csv")
    assert {r["edge"] for r in sp} >= {"ls_to_L", "hs_to_ls", "hs_to_cf"}
    for r in sp:
        assert r["basis_modelled"] and r["basis_physical"]
        assert float(r["physical_span_um"]) > 0


def test_the_tsv_rule_is_not_applied_to_the_substrate_via_class():
    m = {r["parameter"]: r for r in rows("substrate_via_source_matrix.csv")}
    cls = m["interconnect class"]
    assert "Chip-in-Polymer" in cls["value_in_source"] or "chip-in-substrate" in cls["value_in_source"]
    assert "through-silicon" not in cls["design_point"].lower()
    # the diameter must NOT be claimed source-backed from a TSV range
    assert m["microvia diameter"]["provenance"] == "OPEN"
    blob = yaml.safe_dump(m).lower()
    assert "tsv.radius_m" not in blob, "a TSV range is being quoted for this class again"


def test_every_source_matrix_row_has_a_provenance_status():
    for r in rows("substrate_via_source_matrix.csv"):
        assert r["provenance"] in ("SOURCE_BACKED", "SOURCE_BOUNDED", "OPEN"), r
        if r["provenance"] != "OPEN":
            assert r["source"].strip() and r["source"] != "-", r["parameter"]


# ------------------------------------------------------------------ geometry / feasibility
T_LINER_UM, J_DESIGN, S_MIN_UM, PACKING = 0.5, 1.0e8, 30.0, 0.5
I_CELL = 1000.0 / 49.0
A_FREE_MM2 = 1.61


def n_req(d_um):
    return max(1, math.ceil(I_CELL / (J_DESIGN * math.pi *
                                      ((d_um / 2 - T_LINER_UM) * 1e-6) ** 2)))


def test_AR_is_checked_per_segment_not_over_the_total_span():
    seg = rows("ls_to_L_layer_by_layer_geometry.csv")
    total = sum(float(s["thickness_um"]) for s in seg)
    assert total == pytest.approx(120.0)
    assert len(seg) == 3, "three build-up layers, so three microvia levels"
    for r in rows("ls_to_L_feasibility.csv"):
        d = float(r["d_um"])
        worst = max(float(s["thickness_um"]) for s in seg) / d
        # the CSV stores AR rounded to 4 dp
        assert float(r["AR_worst"]) == pytest.approx(worst, abs=5e-5), \
            "AR must be per segment; the 120 um total would give a different number"
        assert float(r["AR_worst"]) < total / d


@pytest.mark.parametrize("row", rows("ls_to_L_feasibility.csv"))
def test_counts_are_ordered_and_independently_reproduced(row):
    d, pitch, pen = float(row["d_um"]), float(row["pitch_um"]), float(row["area_penalty"])
    assert int(row["n_required"]) == n_req(d)
    av = max(1, int(A_FREE_MM2 * 1e-6 * PACKING / ((pitch * 1e-6) ** 2 * pen)))
    assert int(row["n_available"]) == av
    assert int(row["n_required"]) >= 1 and int(row["n_available"]) >= 1
    if row["feasible"] == "True":
        assert int(row["n_required"]) <= int(row["n_available"])


def test_landing_area_is_the_binding_layer_not_the_die_footprint():
    for r in rows("ls_to_L_feasibility.csv"):
        assert float(r["landing_area_mm2"]) == pytest.approx(A_FREE_MM2), \
            "the die footprint 1.80 mm2 is back; DEFECT #63 has regressed"


def test_the_0mr3_design_point_is_infeasible_at_the_corrected_area():
    dp = [r for r in rows("ls_to_L_feasibility.csv")
          if float(r["pitch_um"]) == 70.0 and r["stack"] == "fully_stacked"
          and float(r["d_um"]) == 40.0][0]
    assert float(dp["routing_ratio"]) > 1.0
    assert dp["feasible"] == "False"


def test_no_configuration_satisfies_both_sourced_bounds():
    ok = [r for r in rows("ls_to_L_feasibility.csv")
          if r["feasible"] == "True" and float(r["pitch_um"]) >= 100.0
          and r["stack"] == "semi_stacked"]
    assert ok == [], f"a sourced-legal configuration appeared: {ok}"


def test_pad_and_pitch_geometry_is_legal():
    for r in rows("ls_to_L_feasibility.csv"):
        d, p = float(r["d_um"]), float(r["pitch_um"])
        assert (r["d_legal_at_pitch"] == "True") == (d <= p - S_MIN_UM)


def test_current_continuity_and_loss_ledger():
    res = rows("ls_to_L_resistance_breakdown.csv")
    assert len({r["n_parallel"] for r in res}) == 1, "current must not change along a chain"
    for r in rows("ls_to_L_feasibility.csv"):
        n = min(int(r["n_required"]), int(r["n_available"]))
        assert float(r["P_chain_w"]) == pytest.approx(
            I_CELL ** 2 * float(r["R_chain_ohm"]), rel=1e-9), "P = I^2 R must close"


def test_dc_validation_converged_against_an_exact_control():
    dc = rows("substrate_via_dc_validation.csv")
    ctrl = [r for r in dc if r["case"] == "control_uniform_bar"][0]
    assert abs(float(ctrl["error_pct"])) < 0.01, "the uniform-bar control is not exact"
    for case in sorted({r["case"] for r in dc if r["case"] != "control_uniform_bar"}):
        g = [r for r in dc if r["case"] == case]
        f1, f2 = g[-2], g[-1]
        drift = abs(float(f2["R_fv_ohm"]) - float(f1["R_fv_ohm"])) / float(f2["R_fv_ohm"])
        assert drift < 0.01, f"{case} is not mesh-converged: {100*drift:.2f} %"
        ratio = float(f2["R_fv_ohm"]) / float(f2["R_analytical_ohm"])
        assert 1.10 < ratio < 1.25, ratio
        assert float(f2["current_error_pct"]) < 1e-6


# ------------------------------------------------------------------ clearances / tolerance
def test_clearance_provenance_is_recorded_per_clearance():
    cl = rows("package_clearance_provenance.csv")
    assert len(cl) == 3
    for r in cl:
        assert r["status_0mr3b"] in ("SOURCE_BACKED", "SOURCE_BOUNDED", "OPEN")
        assert r["searched_this_phase"].strip()
        if r["status_0mr3b"] != "OPEN":
            assert r["source"].strip() and r["same_feature"].strip()
    assert sum(1 for r in cl if r["status_0mr3b"] == "OPEN") == 2


def test_a_parametric_tolerance_is_never_labelled_sourced():
    tol = rows("z2_tsv_sourced_tolerance_sweep.csv")
    for r in tol:
        assert r["tolerance_provenance"].startswith("OPEN")
        assert "NOT process-qualified" in r["licensed_wording"]
    blob = " ".join(
        (OUT / n).read_text() for n in ("Z2_TSV_PROCESS_TOLERANCE_AUDIT.md",
                                        "PHASE0MR3B_SUBSTRATE_VIA_AND_PACKAGE_RULE_CLOSURE.md"))
    # the phrase may be QUOTED while being forbidden; what must not appear is an
    # assertion of it
    for m in re.finditer(r"process margin closed", blob, re.I):
        win = blob[max(0, m.start() - 90):m.end() + 90]
        assert re.search(r'"|`|not available|never|is not', win), \
            f"'process margin closed' asserted: ...{win}..."
    assert "NOT process-qualified" in blob


def test_tsv_tolerance_inversion_is_arithmetically_right():
    for r in rows("z2_tsv_sourced_tolerance_sweep.csv"):
        d, L = float(r["d_um"]), float(r["L_um"])
        want = 100.0 * (10.0 * d - L) / (10.0 * d + L)
        assert float(r["max_absorbable_tolerance_pct"]) == pytest.approx(want, abs=5e-3)
    t = {float(r["d_um"]): float(r["max_absorbable_tolerance_pct"])
         for r in rows("z2_tsv_sourced_tolerance_sweep.csv")}
    assert t[30.0] == pytest.approx(0.0, abs=1e-9)
    assert t[32.0] < t[34.0] < t[36.0]


# ------------------------------------------------------------------ span correction
def test_physical_spans_are_opt_in_and_default_off():
    src = (R / "scripts" / "phase0mr" / "routing_production.py").read_text()
    assert 'environ.get("PHASE0MR3B_PHYSICAL_SPANS", "0")' in src, \
        "the correction must default OFF so prior results stay bit-identical"
    code = (
        "import sys,os;"
        f"sys.path[:0]=[r'{R}/scripts/phase0mr',r'{R}/scripts/phase0m',r'{R}/scripts'];"
        "import routing_production as RP;"
        "print(round([e for e in RP.build_edges('T1_EMBEDDED_4LAYER')"
        " if e.name=='ls_to_L'][0].length_mm*1000,1))")
    for flag, want in (("0", 673.0), ("1", 120.0)):
        env = dict(os.environ, PHASE0MR3B_PHYSICAL_SPANS=flag)
        got = subprocess.run([sys.executable, "-c", code], capture_output=True,
                             text=True, env=env, cwd=str(R))
        assert got.returncode == 0, got.stderr[-800:]
        assert float(got.stdout.strip()) == want, (flag, got.stdout)


# ------------------------------------------------------------------ reports
def test_reports_are_semantically_clean(reports, contract):
    for name, body in reports.items():
        assert sa.audit(body, contract) == [], name


def test_gate_roll_agrees_everywhere(reports, contract):
    gates = contract["meta"]["gates"]
    for name, body in reports.items():
        m = re.search(r"([\w-]+) sequential falsification gates\s*\(([^)]*)\)",
                      re.sub(r"\s+", " ", body))
        assert m, name
        assert m.group(1) == sa.NUMWORD[len(gates)], (name, m.group(1))
        assert [x.strip() for x in m.group(2).split(",")] == gates, name


def test_exactly_one_chapter_claims_current_authority(reports):
    for name, body in reports.items():
        n = len(re.findall(r"(?m)^# .*\(current authoritative\)", body))
        assert n <= 1, (name, n)
    assert re.search(rf"(?m)^# Phase {re.escape(PHASE)} .*\(current authoritative\)",
                     reports["historical"])


def test_reports_regenerate_idempotently():
    """Run the chain TWICE and compare the two outputs.

    Comparing one run against whatever happened to be on disk measures the previous
    test's side effects, not idempotency: the PDF builders repair the Markdown in place,
    so the first run after any other builder legitimately settles it.
    """
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PHASE0MR3_", "PHASE0MR3B_"))}

    def run():
        p = subprocess.run([sys.executable,
                            str(R / "scripts/phase0mr3b/rebuild_reports.py")],
                           capture_output=True, text=True, cwd=str(R), env=env)
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-1500:]
        return HIST.read_text(), STAND.read_text()

    first = run()
    assert run() == first, "the rebuild chain is not idempotent"


def test_phase0mr3a_artifacts_are_untouched():
    import hashlib
    bad = ok = 0
    for line in (BASE / "MD5SUMS.txt").read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        f = BASE / name.strip().lstrip("*")
        got = hashlib.md5(f.read_bytes()).hexdigest()
        ok, bad = (ok + 1, bad) if got == digest else (ok, bad + 1)
    assert bad == 0 and ok >= 14, f"{bad} baseline files changed"


def test_verdict_and_defects_registered(status):
    v = status["verdict"]
    assert v["phase0mr3b_option_letter"] == "D"
    assert "NOT_REALIZABLE" in v["phase0mr3b"]
    reg = {int(x["id"]): x for x in status["phase0g_defects"]}
    for n in (60, 61, 62, 63):
        assert n in reg, f"DEFECT #{n} not registered"
    assert "673" in yaml.safe_dump(reg[62])
    assert "1.61" in yaml.safe_dump(reg[63])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
