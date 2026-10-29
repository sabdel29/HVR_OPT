"""Regression guards for the final-closure claims (decision report, n/a handling, mesh
wording, PAPER_READY). Every guard is also run NEGATIVELY on the real offending text a
past version shipped, so a guard that silently stops matching fails here."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
D = R / "research" / "final_closure"
sys.path.insert(0, str(R / "scripts"))
import final_closure_guards as G                                    # noqa: E402

TEX = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
DECK = R / "presentation" / "prelim_hvr"

#: the exact rows the pre-fix generator wrote (commit 185beb5, FINAL_PAPER_DECISION.md)
STALE_ROW = "| HV_S0 | Z2 lower | Z2 lower | Z1 lower | Z1 lower | Z1 lower |"
STALE_TMAX = ("- `T_max_C`: favoured architecture across scenarios = ['Z2'] -> ORDERING "
              "HOLDS IN EVERY SCENARIO")
STALE_LOCAL = ("- `d_eps_in_per_cycle`: favoured architecture across scenarios = "
               "['Z1', 'n/a'] -> ORDERING HOLDS IN EVERY SCENARIO")
#: the exact phrase the manuscript contribution list carried (commit 185beb5)
STALE_MESH = ("a displacement-driven, mesh- and\ncycle-converged local solder "
              "inelastic-response submodel")


def J(n):
    f = D / n
    if not f.exists():
        pytest.skip(f"{n} not generated")
    return json.loads(f.read_text())


def _texts():
    out = {"decision": (D / "FINAL_PAPER_DECISION.md").read_text(),
           "manuscript": TEX.read_text()}
    for f in ("index.html", "SPEAKER_NOTES.md"):
        if (DECK / f).exists():
            out[f] = (DECK / f).read_text()
    mac = R / "manuscript" / "final_lineage_macros.tex"
    if mac.exists():
        out["macros"] = mac.read_text()
    return out


# ------------------------------------------------- 1. decision report == ordering.json
def test_decision_report_equals_ordering_json():
    od = J("ordering.json")
    md = (D / "FINAL_PAPER_DECISION.md").read_text()
    assert G.decision_vs_ordering(md, od) == []


def test_decision_guard_catches_the_real_stale_report():
    od = J("ordering.json")
    if od["orderings"]["T_max_C"]["per_scenario"].get("HV_S0") != "unresolved":
        pytest.skip("HV-S0 thermal ordering is resolved; the stale row is not stale")
    md = (D / "FINAL_PAPER_DECISION.md").read_text()
    lines = md.splitlines()
    i = next(k for k, line in enumerate(lines) if line.startswith("| HV_S0 |"))
    bad = "\n".join(lines[:i] + [STALE_ROW] + lines[i + 1:])
    assert any("HV_S0 T_max_C" in v for v in G.decision_vs_ordering(bad, od))
    bad2 = md.replace("## Robustness\n", "## Robustness\n\n" + STALE_TMAX + "\n", 1)
    assert G.decision_vs_ordering(bad2, od)


def test_no_hv_s0_thermal_ranking_in_any_text():
    od = J("ordering.json")
    for name, txt in _texts().items():
        assert G.hv_s0_thermal_claims(txt, od) == [], name


def test_hv_s0_thermal_guard_negative():
    od = J("ordering.json")
    if od["orderings"]["T_max_C"]["per_scenario"].get("HV_S0") != "unresolved":
        pytest.skip("resolved")
    assert G.hv_s0_thermal_claims("At HV-S0, Z2 runs cooler than Z1 (peak temperature).", od)
    assert not G.hv_s0_thermal_claims(
        "HV-S0: the approximately 1 C difference lies within the measured discretization "
        "uncertainty; therefore no thermal architecture ranking is drawn for HV-S0.", od)


# ------------------------------------------------- 2. n/a is never favourable
def test_na_is_never_favourable():
    assert G.na_never_favourable(J("ordering.json")) == []


def test_na_guard_negative_and_generator_behaviour():
    import final_closure_results as FR
    md = (D / "FINAL_PAPER_DECISION.md").read_text()
    bad = md.replace("## Robustness\n", "## Robustness\n\n" + STALE_LOCAL + "\n", 1)
    assert any("n/a" in v for v in G.decision_vs_ordering(bad, J("ordering.json")))
    # the generator itself: a missing Z1 response is 'not rankable' and never favoured
    rows = []
    for s, (a, b, melt) in {"HV_S0": (1.0, 2.0, False), "HV_S1": (1.5, 2.5, False),
                            "HV_S2": (None, 3.0, True)}.items():
        for arch, v, m in (("Z1", a, melt), ("Z2", b, False)):
            rows.append({"arch": arch, "scenario": s, "P_loss_w": 1.0, "T_max_C": 1.0,
                         "die_warpage_pv_um": 1.0, "du_c_um": 1.0, "d_eps_in_per_cycle": v,
                         "T_joint_at_or_above_solder_solidus": m,
                         "T_joint_outside_norton_calibration": m})
    o = FR.ordering(rows, {"cases": {}})["orderings"]["d_eps_in_per_cycle"]
    assert o["per_scenario"]["HV_S2"] == "not rankable"
    assert "n/a" not in (o["favoured"] or []) and not o["robust_across_scenarios"]
    assert "not rankable because" in o["statement"]


# ------------------------------------------------- 3. mesh wording follows the policy
def test_no_mesh_converged_wording_unless_policy_passes():
    pol, lm = J("local_mesh_policy.json"), J("local_mesh_study.json")
    for name, txt in _texts().items():
        assert G.mesh_wording_violations(txt, lm, pol) == [], name


def test_mesh_wording_guard_negative():
    pol = J("local_mesh_policy.json")
    fake = {"cases": {f"{a}_{s}": {"status": "bounded"} for a, s in pol["cases"]}}
    assert G.mesh_wording_violations(STALE_MESH, fake, pol)
    ok = {"cases": {f"{a}_{s}": {"status": "converged"} for a, s in pol["cases"]}}
    assert G.mesh_wording_violations(STALE_MESH, ok, pol) == []


# ------------------------------------------------- 4. no PAPER_READY with a B1 open
def test_no_paper_ready_while_a_b1_gate_is_unresolved():
    cb = J("classB_resolution.json")
    dec = (D / "FINAL_PAPER_DECISION.md").read_text().split("## Decision")[-1]
    open_b1 = [g["gate"] for g in cb["gates"] if g["new_subtype"] == "B1" and not g["resolved"]]
    if "**PAPER_READY**" in dec:
        assert not open_b1, f"PAPER_READY with unresolved B1 gates {open_b1}"


def test_paper_ready_function_refuses_an_unresolved_b1():
    import final_closure_results as FR
    pol = J("local_mesh_policy.json")
    lm = {"acceptance": {"pass": True},
          "cases": {f"{a}_{s}": {"U": 0.01, "production_value": 1.0} for a, s in pol["cases"]}}
    cb = {"gates": [{"gate": "board.h1_meshed", "new_subtype": "B1", "resolved": True},
                    {"gate": "tsv.density_sensitivity_run", "new_subtype": "B1",
                     "resolved": False}]}
    final = [{"arch": "Z2", "architecture_variant": "Z2_DIRECT_FEED", "forbidden_terms": []}]
    ok, why = FR.paper_ready(True, True, True, True, True, cb, lm, final)
    assert not ok and any("tsv.density_sensitivity_run" in w for w in why)
    cb["gates"][1]["resolved"] = True
    ok, why = FR.paper_ready(True, True, True, True, True, cb, lm, final)
    assert ok, why
    lm["acceptance"]["pass"] = False
    assert not FR.paper_ready(True, True, True, True, True, cb, lm, final)[0]
    lm["acceptance"]["pass"] = True
    # NEGATIVE: the superseded BGA-fed primary Z2 (no direct-feed variant, package 48 V
    # ball term in its ledger) can never be paper-ready
    stale = [{"arch": "Z2", "architecture_variant": None, "forbidden_terms": ["P_BGA_supply"]}]
    ok, why = FR.paper_ready(True, True, True, True, True, cb, lm, stale)
    assert not ok
    assert any("direct-fed" in w for w in why) and any("package 48 V term" in w for w in why)


def test_every_open_b_gate_has_a_subtype_and_evidence():
    cb = J("classB_resolution.json")
    gc = J("paper_gate_classification.json")
    open_b = {r["id"] for r in gc["rows"] if r["class"] == "B"}
    have = {g["gate"] for g in cb["gates"]}
    assert open_b <= have, open_b - have
    for g in cb["gates"]:
        assert g["new_subtype"] in ("B1", "B2", "B3")
        assert g["evidence_path"] and g["final_status"]


# ------------------------------------------------- 5. no ranking in an inadmissible scenario
#: the exact text the pre-fix generator wrote while Z1 HV-S2 sat above the solder melting
#: onset (FINAL_PAPER_DECISION.md, manuscript abstract, deck appendix conclusion)
STALE_S2 = ("- loss: Z2 has lower loss in every named scenario.",
            "The mechanical ordering---lower joint displacement driver and die warpage for the "
            "embedded architecture---holds in every named scenario, reversing the ordering of an",
            "<li>Electrical loss: Z2 lower in every scenario.</li><li>Peak temperature: Z2 lower "
            "wherever resolved (HV-S0 unresolved, HV-S1 Z2 lower, HV-S2 Z2 lower; 'unresolved' "
            "= inside the discretisation uncertainty).</li>",
            "Z2 has lower peak temperature in HV-S1 and HV-S2, where the gap exceeds twice the "
            "measured discretisation uncertainty.")


def test_no_ranking_inside_an_inadmissible_scenario():
    od = J("ordering.json")
    for name, txt in _texts().items():
        assert G.inadmissible_ranking_claims(txt, od) == [], name


def test_inadmissible_guard_negative():
    od = J("ordering.json")
    if not any(c.get("inadmissible") for c in od["scenario_classes"].values()):
        pytest.skip("no inadmissible scenario in the current lineage")
    for stale in STALE_S2:
        assert G.inadmissible_ranking_claims(stale, od), stale
    for ok in ("Z2 has lower loss in every scenario for which a valid two-architecture "
               "comparison can be made; HV-S2 is not rankable because the Z1 operating point "
               "is physically inadmissible for the solid-solder model.",
               "the embedded architecture carries the lower die warpage and joint displacement "
               "driver in every scenario that admits a valid comparison",
               "RESOLVED -- scenario-conditioned: every named scenario is solved"):
        assert G.inadmissible_ranking_claims(ok, od) == [], ok


def test_inadmissible_scenario_is_not_rankable_for_every_observable():
    import final_closure_results as FR
    rows = []
    for s, melt in (("HV_S0", False), ("HV_S1", False), ("HV_S2", True)):
        for arch, v in (("Z1", 1.0), ("Z2", 2.0)):
            rows.append({"arch": arch, "scenario": s, "P_loss_w": v, "T_max_C": v,
                         "die_warpage_pv_um": v, "du_c_um": v, "d_eps_in_per_cycle": v,
                         "T_joint_at_or_above_solder_solidus": melt and arch == "Z1",
                         "T_joint_outside_norton_calibration": melt and arch == "Z1"})
    out = FR.ordering(rows, {"cases": {}})
    for k, o in out["orderings"].items():
        assert o["per_scenario"]["HV_S2"] == "not rankable", k
        assert not o["robust_across_scenarios"], k
        assert "every named scenario" not in o["statement"], k
        assert G.inadmissible_ranking_claims(o["statement"], out) == [], k
