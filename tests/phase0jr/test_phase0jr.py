"""Phase-0J-R tests. Every number is re-derived from the CSV the phase actually wrote."""
from __future__ import annotations
import csv
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0jr"
C_PL, W_PL = 0.0468, 0.0015
SUPERSEDED = (0.0358, 0.0012, 0.0405, 0.0014)


def rows(n):
    return list(csv.DictReader(open(OUT / n)))


@pytest.fixture(scope="module")
def status():
    return yaml.safe_load((R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml").read_text())


@pytest.fixture(scope="module")
def syed():
    return {r["short"]: r for r in rows("syed_layer_metrics.csv") if r["n_mid"] == "10"}


# ------------------------------------------------------ Sec.1 version control

def test_author_corrected_constants_are_the_ones_used(status):
    ll = status["life_law_status_0jr"]["authoritative_constants"]
    assert "0.0468" in ll["total_accumulated_creep_strain"]
    assert "0.0015" in ll["creep_energy_density"]
    assert "AUTHOR-CORRECTED" in ll["source"]
    for v in ("0.0358", "0.0012", "0.0405", "0.0014"):
        assert v in ll["superseded_original_constants"]


def test_superseded_constants_never_used_in_a_computation():
    """A guard on the analysis code, not the prose."""
    for f in ("final_tables.py", "dwell_sensitivity.py", "syed_reproduction.py"):
        src = (R / "scripts" / "phase0jr" / f).read_text()
        import ast as A
        tree = A.parse(src)
        consts = [n.value for n in A.walk(tree)
                  if isinstance(n, A.Constant) and isinstance(n.value, float)]
        for bad in SUPERSEDED:
            # syed_reproduction.py legitimately defines the originals for the audit table
            if f == "syed_reproduction.py":
                continue
            assert not any(abs(c - bad) < 1e-9 for c in consts), (f, bad)


# ------------------------------------------------------ Sec.4/6 the metric identity

def test_M4_equals_M1_identically(syed):
    for s, r in syed.items():
        assert float(r["M4_over_M1"]) == pytest.approx(1.0, abs=1e-9), s


def test_overstress_model_is_recorded_as_proven_not_assumed(status):
    m = status["reliability_metrics_0jr"]["M4"]
    assert "PROVEN BY PROBE" in m["status"]
    assert "OVERSTRESS" in m["proof"]
    assert "1.52e-11" in m["proof"] and "5.16e-2" in m["proof"]


def test_creep_only_probe_validated_the_reconstruction():
    v = {r["case"]: r for r in rows("m4_validation.csv")}
    for k, r in v.items():
        if r["model"] == "EC":                       # no plastic card -> M4 must equal d(PEEQ)
            assert 0.85 < float(r["M4_over_M1"]) < 1.05, k
        if r["model"] == "EP":                       # no creep card  -> M4 must be zero
            assert float(r["M4_creep_strain"]) < 1e-20, k


# ------------------------------------------------------ Sec.5 averaging volume

def test_graded_mesh_reproduces_syeds_25um_extraction():
    import sys
    sys.path.insert(0, str(R / "scripts" / "phase0jr"))
    sys.path.insert(0, str(R / "scripts" / "phase0i"))
    from graded_joint import LAYER_UM, N_IN_LAYER, build_joint_graded, solder_z
    assert LAYER_UM == 25.0 and N_IN_LAYER == 2
    z = solder_z(6) * 1e3
    assert z[1] == pytest.approx(12.5) and z[2] == pytest.approx(25.0)
    assert z[-2] == pytest.approx(287.5) and z[-3] == pytest.approx(275.0)
    m = build_joint_graded(6, 6)
    assert len(m.sets["ESYED"]) == 144


def test_mesh_converged_and_stabilised(syed):
    allr = rows("syed_layer_metrics.csv")
    for s in ("Z1", "Z2", "Z4"):
        a = [r for r in allr if r["short"] == s and r["n_mid"] == "6"][0]
        b = [r for r in allr if r["short"] == s and r["n_mid"] == "10"][0]
        d = abs(float(b["M4_syed_layer"]) - float(a["M4_syed_layer"])) / float(a["M4_syed_layer"])
        assert d < 0.10, (s, d)                       # predeclared target
        assert float(b["stab_pct"]) < 5.0, s          # predeclared stabilisation criterion


def test_matching_the_volume_changes_the_metric_nonuniformly():
    cm = {r["short"]: r for r in rows("creep_only_metric_by_architecture.csv")
          if r["n_mid"] == "10"}
    ratios = [float(r["ratio_syedlayer_to_phase0I_core"]) for r in cm.values()]
    assert min(ratios) > 1.2 and max(ratios) < 1.7
    assert max(ratios) - min(ratios) > 0.2, "must NOT be a uniform scale factor"


# ------------------------------------------------------ Sec.8 reproduction

def test_reproduction_passes_both_declared_tolerances():
    val = [r for r in rows("syed_reproduction.csv") if r["set"] == "Table 3 VALIDATION"]
    assert len(val) == 4
    assert max(abs(float(r["err_powerlaw_creep_pct"])) for r in val) <= 25.0
    wo = [float(r["implied_w_over_eps_MPa"]) for r in val]
    assert 100 * (max(wo) - min(wo)) / (sum(wo) / len(wo)) <= 10.0


def test_no_digitisation_was_used():
    for r in rows("syed_reproduction.csv"):
        assert "no digitisation" in r["our_transcription"]


# ------------------------------------------------------ Sec.10/11 waveform and dwell

def test_waveform_is_a_step_with_a_real_dwell(status):
    cw = status["cycle_waveform_CORRECTED"]
    assert cw["dwell_at_each_extreme_s"] == 300
    assert "SQUARE WAVE" in cw["actual_waveform"]
    assert "0.002" in cw["actual_waveform"]
    assert "ZERO dwell" in cw["phase0j_error"]


def test_dwell_sensitivity_is_mild_and_relative_result_is_stable():
    dw = rows("dwell_sensitivity.csv")
    assert all("NOT a mission prediction" in r["label"] for r in dw)
    for s in ("Z1", "Z2"):
        d = sorted([r for r in dw if r["short"] == s], key=lambda r: float(r["dwell_s"]))
        assert float(d[0]["dwell_s"]) == 30.0 and float(d[-1]["dwell_s"]) == 900.0
        g = float(d[-1]["M4_creep_strain"]) / float(d[0]["M4_creep_strain"])
        assert 1.10 < g < 1.30, (s, g)                # 30x dwell -> only +17..+23 %
    z1 = {float(r["dwell_s"]): r for r in dw if r["short"] == "Z1"}
    z2 = {float(r["dwell_s"]): r for r in dw if r["short"] == "Z2"}
    rat = [float(z1[d]["M4_creep_strain"]) / float(z2[d]["M4_creep_strain"]) for d in z1]
    assert max(rat) - min(rat) < 0.08, rat            # relative result dwell-insensitive


# ------------------------------------------------------ Sec.9/19/20 transferability

def test_each_metric_interpolates_but_the_pair_does_not(syed):
    for s, r in syed.items():
        e, w = float(r["M4_syed_layer"]), float(r["M5_syed_layer_MJ_per_m3"])
        assert 0.00213 <= e <= 0.0777, s              # Syed's eps range
        assert 0.0665 <= w <= 2.4243, s               # Syed's w range
        assert w / e > 100, s                         # but the PAIR is far off his 28.8-30.0


def test_the_two_syed_models_disagree_on_absolute_life(syed):
    for s, r in syed.items():
        ns = 1 / (C_PL * float(r["M4_syed_layer"]))
        ne = 1 / (W_PL * float(r["M5_syed_layer_MJ_per_m3"]))
        assert 3.5 < ns / ne < 4.6, (s, ns / ne)


def test_relative_life_is_robust_across_every_admissible_law():
    lw = [r for r in rows("lifetime_by_primary_law.csv") if r["Z2_over_Z1"] != ""]
    assert len(lw) >= 4
    z2 = [float(r["Z2_over_Z1"]) for r in lw]
    z4 = [float(r["Z4_over_Z1"]) for r in lw]
    assert all(v > 1.0 for v in z2), z2
    assert all(v < 1.0 for v in z4), z4
    assert 1.19 <= min(z2) and max(z2) <= 1.40
    assert all(r["ranking"] == "Z2 > Z1 > Z4" for r in lw)


def test_phase0j_ratio_is_withdrawn_not_reused(status):
    al = status["architecture_life_0jr"]
    assert "WITHDRAWN" in al["supersedes_phase0j_ratio"]
    assert "1.558" in al["supersedes_phase0j_ratio"]
    assert "ALGEBRAIC RATIO" in al["supersedes_phase0j_ratio"]


def test_absolute_life_is_never_called_validated(status):
    al = status["architecture_life_0jr"]
    assert al["status"] == "RELATIVE LIFE VALIDATED; ABSOLUTE LIFE CONDITIONAL"
    assert "4.10x" in al["conditional_absolute_life"]["why_not_validated"]
    for r in rows("lifetime_by_primary_law.csv"):
        if r["Z1"] != "":
            v = r["absolute_or_relative"].upper()
            assert "CONDITIONAL" in v or "SENSITIVITY" in v, v


# ------------------------------------------------------ Sec.18 admissibility revision

def test_seven_entries_changed_after_primary_access():
    db = rows("LIFE_LAW_ADMISSIBILITY_REVISED.csv")
    assert len(db) == 10
    ch = [r for r in db if r["changed"].startswith(("CHANGED", "NEW"))]
    assert len(ch) == 7
    for r in db:
        assert r["primary_evidence"].strip()


def test_darveaux_still_inadmissible_on_alloy():
    d = [r for r in rows("LIFE_LAW_ADMISSIBILITY_REVISED.csv") if r["id"] == "L6_DARVEAUX"][0]
    assert d["PHASE_0JR_STATUS"] == "INADMISSIBLE"
    assert "62Sn36Pb2Ag" in d["reason"] and "60Sn40Pb" in d["reason"]


def test_vasudevan_is_not_treated_as_a_damage_model():
    v = [r for r in rows("LIFE_LAW_ADMISSIBILITY_REVISED.csv")
         if r["id"] == "L10_VASUDEVAN_FAN"][0]
    assert "SCALING ONLY" in v["PHASE_0JR_STATUS"]
    assert "NOT a damage model" in v["reason"]


# ------------------------------------------------------ Sec.21/27 mission and G2

def test_required_life_still_open_and_g2_not_tested(status):
    assert status["verdict"]["g2_status"] == "NOT_TESTED"
    assert status["mission_requirement"]["N_required"] == "OPEN"
    assert "SOLE blocker" in status["verdict"]["g2_note_phase0jr"]


def test_optimizer_still_not_built(status):
    assert status["meta"]["optimiser_built"] is False
    assert status["meta"]["optimiser_recommended"] is False


def test_phase0jr_discharged_the_access_blocker(status):
    """Phase 0J-R's durable conclusion: the blocker is no longer ACCESS.

    This deliberately does NOT pin next_gate.id. Phase 0J-R recommended
    'SYSTEM-OWNER MISSION DEFINITION'; Phase 0K tested that formally, found a calibration
    experiment to be independently necessary, and rescoped the gate. Asserting the old string
    would make a later phase's legitimate refinement look like a regression.
    """
    ng = status["next_gate"]
    assert "SUPERSEDED" in ng["supersedes_0k_framing"]
    assert "ACCESS" in ng["supersedes_0k_framing"] or "access" in ng["supersedes_0k_framing"]
    # the access blocker is discharged: four laws admitted, calibration reproduced
    ll = status["life_law_status_0jr"]
    assert ll["admissible_for_relative_life"] == 4
    assert ll["reproduction"]["status"] == "PASSED"


# ------------------------------------------------------ Sec.28/29 artifacts

@pytest.mark.parametrize("name", [
    "PHASE0JR_PRIMARY_LIFE_LAW_GATE.md", "PRIMARY_SOURCE_INVENTORY.md",
    "SYED_2004_VERSION_AUDIT.md", "CREEP_ONLY_METRIC_AUDIT.md",
    "creep_only_metric_by_architecture.csv", "syed_reproduction.csv",
    "SYED_TRANSFERABILITY_AUDIT.md", "POWER_CYCLE_TRANSFER_AUDIT.md",
    "SCHUBERT_2003_REPRODUCTION.md", "DARVEAUX_PRIMARY_SOURCE_AUDIT.md",
    "VASUDEVAN_FAN_2008_AUDIT.md", "LIFE_LAW_ADMISSIBILITY_REVISED.csv",
    "dwell_sensitivity.csv", "lifetime_by_primary_law.csv",
    "MISSION_INPUT_TEMPLATE.md", "G2_STATUS_REVISED.md"])
def test_required_artifact_exists(name):
    p = OUT / name
    assert p.is_file() and p.stat().st_size > 200, name


@pytest.mark.parametrize("fig", list("ABCDEFG"))
def test_required_figure_exists(fig):
    got = list(OUT.glob(f"FIG_0JR_{fig}_*.png"))
    assert len(got) == 1 and got[0].stat().st_size > 10000, fig


def test_all_six_supplied_papers_were_inventoried():
    txt = (OUT / "PRIMARY_SOURCE_INVENTORY.md").read_text()
    for k in ("Syed 2004 — IEEE ECTC original", "author-corrected", "Schubert 2003",
              "Darveaux 2000", "Syed 2001", "Vasudevan & Fan 2008"):
        assert k in txt, k
    assert "not supplied" in txt.lower(), "the two missing Darveaux files must be recorded"
    assert "Darveaux_2002" in txt
