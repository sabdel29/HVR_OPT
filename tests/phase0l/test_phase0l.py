"""Phase-0L regression tests.

These assert the FINDINGS against the artifacts, so that a future change which silently
reverses one of them fails the build rather than quietly rewriting the conclusion.
"""
from __future__ import annotations
import csv, hashlib, math, re, sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0l"
sys.path.insert(0, str(R / "scripts" / "phase0i"))
sys.path.insert(0, str(R / "scripts" / "phase0l"))


def rows(name):
    p = OUT / name
    if not p.is_file():
        pytest.skip(f"{name} not generated yet")
    return list(csv.DictReader(open(p)))


F = lambda r, k: float(r[k])


# --------------------------------------------------------------------------- solver law ----
def test_solver_law_is_overstress_not_von_mises():
    """TEST B: the overstress form must beat the total-stress form by orders of magnitude."""
    rs = [r for r in rows("calculix_creep_probe.csv")
          if r["test"] == "B" and F(r, "rate_meas_1_per_s") > 1e-18]
    assert rs, "no live TEST B increments"
    def med(key):
        v = [abs(math.log10(F(r, key))) for r in rs
             if r[key] not in ("", "inf", "nan") and F(r, key) > 0]
        return sorted(v)[len(v) // 2]
    assert med("ratio_H3") < 1e-3, "the overstress law no longer reproduces the solver"
    assert med("ratio_H1") > 0.5, "the total-stress law is no longer refuted"


def test_no_creep_below_yield():
    """TEST C: sub-yield states must give IDENTICALLY zero, not merely small."""
    rs = [r for r in rows("calculix_creep_probe.csv") if r["test"] == "C"]
    assert rs, "no TEST C rows"
    assert all(F(r, "peeq1") == 0.0 for r in rs), \
        "creep now occurs below yield -- the overstress threshold has changed"


def test_no_time_hardening():
    """TEST H: PEEQ must not depend on elapsed total analysis time (m = 0)."""
    rs = [r for r in rows("calculix_creep_probe.csv") if r["test"] == "H"]
    assert rs, "no TEST H rows"
    by = {}
    for r in rs:
        by.setdefault(r["tag"], []).append(F(r, "peeq1"))
    finals = [v[-1] for v in by.values()]
    assert max(finals) == min(finals), "a total-time dependence has appeared; m is no longer 0"


# ------------------------------------------------------------------- DEFECT #40 / the fit ---
def test_card_cannot_reproduce_its_own_source_data():
    """DEFECT #40: this is the finding. If it ever passes, the card was changed."""
    rs = rows("original_19point_fit.csv")
    assert len(rs) == 19
    nonpos = [r for r in rs if F(r, "overstress_MPa") <= 0]
    assert len(nonpos) == 16, f"expected 16 non-positive-overstress points, got {len(nonpos)}"
    reproduced = [r for r in rs
                  if 0.2 < (F(r, "edot_solver_would_give") / F(r, "edot_measured_1_per_s")) < 5.0]
    assert not reproduced, "the card now reproduces source points -- DEFECT #40 state changed"


def test_fit_and_solver_variables_still_differ():
    rs = rows("original_19point_fit.csv")
    assert all(r["variables_match"] == "False" for r in rs)
    assert all("sigma_applied" in r["fit_variable"] for r in rs)
    assert all("sigma_y" in r["solver_variable"] for r in rs)


def test_fitB_is_not_constructible():
    """Part VI: a Norton law needs two positive-overstress points per temperature."""
    rs = rows("refit_comparison.csv")
    ok = [r for r in rs if r["fitB_constructible"] == "True"]
    assert len(ok) <= 1, "FIT-B has become constructible at more than one temperature"
    assert any(r["fitB_status"] == "IMPOSSIBLE" for r in rs)


# ---------------------------------------------------------------------------- provenance ----
def test_creep_data_provenance_is_recorded_and_not_sac305():
    rs = rows("original_19point_fit.csv")
    assert all("Table 5" in r["source_table"] for r in rs), "source table citation changed"
    assert all("Sn3.9Ag0.6Cu" in r["source_alloy"] for r in rs), "alloy claim changed"


def test_solder_model_no_longer_cites_nonexistent_tables():
    src = (R / "scripts" / "phase0i" / "solder_model.py").read_text()
    # A mention is allowed only on a line that says the table does NOT exist; a mention on any
    # other line is a live citation to a table the paper does not have.
    for bad in ("Table 26", "Table 27", "Table 31"):
        live = [l.strip() for l in src.splitlines()
                if bad in l and not re.search(r"no Table 26|eleven tables", l)]
        assert not live, f"solder_model.py still cites {bad}: {live[:2]}"
    assert "Table 5" in src and "Table 6" in src and "Table 10" in src
    assert "Sn3.9Ag0.6Cu" in src, "the alloy warning has been removed"


def test_creep_data_values_unchanged():
    """The citation fix must not have moved a single measurement."""
    import solder_model as sm
    assert len(sm.CREEP_DATA) == 19
    assert sm.CREEP_DATA[0] == (45.0, 10.54, 1.4e-9)
    assert sm.CREEP_DATA[-1] == (150.0, 11.52, 810.0e-9)
    f = sm.fit_norton_data(45.0)
    assert abs(f["A"] - 4.1131e-18) / 4.1131e-18 < 1e-3
    assert abs(f["n"] - 8.295) < 1e-2


# ------------------------------------------------------------------------- predeclaration ---
def test_part12_tolerance_was_predeclared_and_is_unmodified():
    doc = OUT / "PART12_PREDECLARED_TOLERANCE.md"
    rec = OUT / "PART12_PREDECLARED_TOLERANCE.sha256"
    assert doc.is_file() and rec.is_file()
    want = rec.read_text().split()[0]
    got = hashlib.sha256(doc.read_bytes()).hexdigest()
    assert got == want, "the predeclared tolerance document has been edited after the fact"
    body = doc.read_text()
    assert "0.0525" in body and "0.21" in body


def test_common_mode_classification_follows_the_predeclared_rule():
    """The verdict must be derivable from the numbers, not asserted."""
    rs = rows("common_mode_verdict.csv")
    for r in rs:
        S, allpos = F(r, "spread_S"), r["all_ratios_above_1"] == "True"
        rob, par = F(r, "threshold_robust"), F(r, "threshold_partial")
        want = ("ROBUST COMMON-MODE CANCELLATION" if (S <= rob and allpos)
                else "PARTIAL CANCELLATION" if (S <= par and allpos)
                else "RELATIVE-LIFE RESULT MODEL-FORM DEPENDENT")
        assert r["classification"] == want, (
            f"{r['profile']}/{r['quantity']}: classification does not follow the rule")


def test_ranking_survives_every_admitted_model():
    rs = rows("common_mode_cancellation_test.csv")
    assert rs
    bad = [r for r in rs if F(r, "life_Syed2004_Eq14_strain") <= 1.0]
    assert not bad, f"an admitted model reverses the Z2/Z1 ranking: {bad[:2]}"


# ----------------------------------------------------------------------- solver settings ----
def test_replay_solver_control_is_uniform():
    """A mixed set would inject a numerical difference into the model-form spread."""
    rs = [r for r in rows("package_model_replay_tight.csv") if r["status"] == "OK"]
    if not rs:
        pytest.skip("tight matrix not complete")
    assert {r["solver_control"] for r in rs} == {"TIGHT"}


# ------------------------------------------------------------------------------- domain -----
def test_no_profile_is_within_domain_for_the_whole_card():
    rs = rows("complete_constitutive_domain.csv")
    for prof in {r["profile"] for r in rs}:
        sub = [r for r in rs if r["profile"] == prof]
        assert any(r["domain_class"].startswith("SEVERE") for r in sub), \
            f"{prof} is now fully within domain -- check the constitutive sources"


# -------------------------------------------------------------------------------- status ----
def test_status_yaml_records_the_phase0l_contract():
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    if "sac305_constitutive" not in d:
        pytest.skip("Phase-0L YAML block not written yet")
    c = d["sac305_constitutive"]
    for k in ("exact_solver_law", "stress_variable", "experimental_fit_variable",
              "temperature_domain", "stress_domain", "high_stress_status",
              "selected_model", "model_form_uncertainty"):
        assert k in c and c[k], f"sac305_constitutive.{k} missing or empty"
    assert c["variables_match"] is False
    assert d["optimizer"]["allowed"] is False
    ids = {e["id"] for e in d["phase0g_defects"]}
    assert {40, 41, 42, 43} <= ids


def test_every_defect_has_a_status():
    d = yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())
    for e in d["phase0g_defects"]:
        assert e.get("status"), f"defect {e['id']} has no status"
        assert e.get("fix"), f"defect {e['id']} has no fix"
