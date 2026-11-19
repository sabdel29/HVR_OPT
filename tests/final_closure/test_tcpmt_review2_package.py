"""TCPMT review round 2 -- the package chain: production converter rules, production input state,
BGA count at the production waveform, static drop, feed crossover and the feasibility stage.

Small tests (no solver runs): the converter is compiled (seconds), the ledger re-evaluated once,
and the committed artifacts are read."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts", "scripts/phase0mr", "scripts/phase0d", "scripts/phase0f", "scripts/phase0nw"):
    sys.path.insert(0, str(R / _p))
FC = R / "research" / "final_closure"
TR = R / "research" / "tcpmt_revision"


@pytest.fixture
def clean_env(monkeypatch):
    import electrical as EL
    for k in EL.PRODUCTION_ENV:
        monkeypatch.delenv(k, raising=False)
    import replay_production as RPX
    RPX._DESIGN_CACHE.clear()
    yield monkeypatch
    RPX._DESIGN_CACHE.clear()


# ------------------------------------------------------------------ production converter rules
def test_production_rules_default_corrected_packing_on(clean_env):
    """Corrected capacitor, switch (0.9), C_oss, R_g and footprint rules; packing ON since the
    design point moved to the design record's M = 36 (TCPMT round 3,
    electrical.PRODUCTION_PACKING)."""
    import electrical as EL
    r = EL.production_rules()
    assert r == EL.PRODUCTION_DEFAULTS
    assert {k: r[k] for k in ("CAP_RULE", "SW_RULE", "SW_V_DERATING", "COSS_RULE", "RG_RULE",
                              "FOOTPRINT_RULE", "PACK_RULE")} == {
        "CAP_RULE": "stress", "SW_RULE": "stress", "SW_V_DERATING": 0.9,
        "COSS_RULE": "corrected", "RG_RULE": "datasheet", "FOOTPRINT_RULE": "body",
        "PACK_RULE": EL.PRODUCTION_PACKING}
    assert EL.PRODUCTION_PACKING == "on"


def test_legacy_reachable_by_environment(clean_env):
    import electrical as EL
    clean_env.setenv("HVR_PRODUCTION_RULES", "legacy")
    assert EL.production_rules() == EL.LEGACY_RULES
    clean_env.setenv("HVR_PRODUCTION_CAP_RULE", "stress")     # a single rule back
    assert EL.production_rules()["CAP_RULE"] == "stress"


def test_rules_of_reads_the_converter_stamp():
    import electrical as EL
    assert EL.rules_of({"ledger_rows": [{"term": "P_conv_hs"}]}) == EL.LEGACY_RULES
    stamp = {"rules": {"CAP_RULE": "stress", "SW_RULE": "stress", "COSS_RULE": "corrected",
                       "PACK_RULE": "off"}}
    rec = {"ledger_rows": [{"term": "P_conv_hs", "converter": stamp}]}
    assert EL.rules_of(rec) == stamp["rules"]


def test_production_converter_is_the_rated_part(clean_env):
    """The package chain's converter carries the rated flying capacitor and its ESR at f_sw;
    the legacy lineage keeps the published 25-V part."""
    import replay_production as RPX
    import electrical as EL
    d = RPX.compiled_design()
    assert d.capacitor.name == "Murata-GRM188D72A105KE01-1uF-100V"
    assert 7.0 < d.capacitor.esr_mohm < 8.6
    assert d.rules["CAP_RULE"] == "stress" and d.rules["PACK_RULE"] == "on"
    # the design record re-synthesizes its entry under the process rules: the legacy lineage
    # selects another converter and is refused, never silently substituted
    import design_record as DR
    with EL.pinned_rules(EL.LEGACY_RULES):
        import pytest as _pt
        with _pt.raises(DR.DesignRecordError):
            RPX.compiled_design()
    assert RPX.compiled_design().capacitor.name == d.capacitor.name     # cache re-keyed


@pytest.mark.skip(reason="TCPMT round 3: the committed S0 ledger is the frozen 49-cell legacy "
                         "lineage; the chain now takes its count and converter from the design "
                         "record (M = 36), which refuses the legacy synthesis. Reproducible at "
                         "31a846c; the campaign regenerates the S0 cases for the record")
def test_legacy_lineage_reproduces_the_committed_S0_ledger(clean_env):
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    import electrical as EL
    c = json.loads((FC / "etm_Z1_HV_S0_h1.1_r21.json").read_text())
    temps = E.temps_from_history(c["et_history"][-2])
    with EL.pinned_rules(EL.rules_of(c)):
        L = FL.self_consistent("Z1", "HV_S0", temps)
    assert abs(L["P_loss_w"] / c["P_loss_w"] - 1.0) < 1e-9
    assert L["rows"][0]["converter"]["rules"] == EL.LEGACY_RULES


def test_table_ii_artifact_from_the_production_converter():
    d = json.loads((TR / "production_converter.json").read_text())
    p, lg = d["production"], d["legacy_lineage"]
    assert p["flying_capacitors"]["vendor_part"] == "GRM188D72A105KE01"
    assert p["loss_25C_per_cell_W"]["total"] > lg["loss_25C_per_cell_W"]["total"]
    split = p["loss_25C_per_cell_W"]["split"]
    assert abs(sum(split.values()) - p["loss_25C_per_cell_W"]["total"]) < 1e-9
    assert d["macros"]["ConvCapEsr"] == "7.8" and d["macros"]["ConvCapEsrLegacy"] == "2.5"


# ------------------------------------------------------------------ production input state
def test_production_state_is_the_implemented_decoupling():
    import tcpmt_cases as TC
    assert TC.PRODUCTION_STATE == "SDEC" and TC.SCEN["SDEC"] == "HV_SDEC"
    for t in TC.TIERS:
        for a in TC.ARCHS:
            assert TC.expected_path("SDEC", t, a).name == f"etm_{a}_HV_SDEC__sdec_{t}.json"
    assert TC.COOLING_BASE[("Z3", "A")] == "z3_land_t40_A_fvmap"
    assert TC.COOLING_BASE[("Z3", "B")] == "z3_land_t40_B_fvmap"


def test_uncoupled_z3_is_superseded_and_refused():
    import tcpmt_cases as TC
    f = FC / "sensitivity" / "etm_Z3_HV_S0__z3_plate_tim.json"
    assert TC.is_superseded(f)
    with pytest.raises(RuntimeError):
        TC.guard("Z3", json.loads(f.read_text()), f)
    ok = FC / "sensitivity" / "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json"
    TC.guard("Z3", json.loads(ok.read_text()), ok)
    assert TC.case_path("S0", "B", "Z3") == ok


def test_review_variants_build_on_the_coupled_z3():
    import tcpmt_review_variants as RV
    assert RV.TIER_BASE[("Z3", "A")].startswith("z3_land")
    assert RV.TIER_BASE[("Z3", "B")].startswith("z3_land")


# ------------------------------------------------------------------ BGA count, feeds, drop
def test_bga_count_reclosed_at_the_production_waveform():
    d = json.loads((FC / "bga_count_production.json").read_text())
    cl = d["closure"]
    assert cl["Z1__HV_S0"]["n_min"] == 54                      # the committed S0 closure
    assert cl["Z1__HV_SDEC"]["status"] == "CLOSED"
    assert cl["Z1__HV_SDEC"]["n_min"] > 54
    assert cl["Z1__HV_SDEC"]["peak_at_n_min_A"] <= 1.5
    assert cl["Z1__HV_SDEC"]["peak_at_lower_A"] > 1.5
    assert d["matched_count"] >= max(cl["Z1__HV_SDEC"]["n_min"], cl["Z2__HV_SDEC"]["n_min"])
    pn = json.loads((FC / "package_network.json").read_text())
    if pn["matched_count"] == 54:                    # the S0 network still committed: 2.4 A
        f = max(pn["convergence"]["Z1_supply"]["final"]["i_ball_max_a"],
                pn["convergence"]["Z1_return"]["final"]["i_ball_max_a"])
        assert 2.2 < f * d["currents_A"]["Z1"]["HV_SDEC"] < 2.6


def test_z2_ring_feed_is_counted_and_documented():
    d = json.loads((TR / "platform_inclusive.json").read_text())
    ring = d["feed_design"]["Z2_bga_ring"]
    assert ring["sites"] == 2 * ring["n_per_rail"] > 0 and ring["in_table_V"]
    assert d["feed_design"]["Z2_flex_alternative"]["in_table_V"] is False
    assert set(ring["I_ball_peak_A"]) == {"S0", "SDEC", "S1"}


def test_static_drop_is_a_per_rail_maximum():
    import tcpmt_ir_drop as IR
    z3 = json.loads((FC / "sensitivity" / "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json").read_text())
    d = IR.static_drop(z3)
    zl = z3["z3_land"]
    assert d["VDD_mV"] > zl["land"]["dV_static_one_rail_mV"] + zl["board"]["dV_static_VDD_mV"]
    assert d["max_mV"] > IR.LIMIT_MV_PER_RAIL
    assert d["max_mV"] > d["mean_loss_over_I_mV"]       # the old loss/current understates it
    z1 = json.loads((FC / "etm_Z1_HV_S0_h1.1_r21.json").read_text())
    assert IR.static_drop(z1)["max_mV"] < IR.LIMIT_MV_PER_RAIL


def test_z3_feed_limit_is_none_on_the_coupled_case():
    d = json.loads((TR / "tier_feed_crossover.json").read_text())
    rec = d["states"]["S0"]["B"]["Z3"]
    assert rec["case"] == "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json"
    assert rec["R_star_mohm"] == 0.0 and rec["R_star_label"] == "none"
    assert abs(rec["reproduction_w"]) < 0.05


# ------------------------------------------------------------------ the feasibility stage
def test_filter_catches_the_rigid_plate_feedback_case():
    """The Z1 interface-feedback case under one top plate: critical joint at 129.5 C, beyond the
    125-C solder law -- infeasible (evaluated without fields: the joints are in the case)."""
    import tcpmt_feasibility as F
    p = FC / "sensitivity" / "etm_Z1_HV_S0__tim_warp_fb_A.json"
    r = F.evaluate(p, json.loads(p.read_text()), use_fields=False)
    assert r["joints"]["T_critical_C"] > 125.0
    assert r["checks"]["solder_law"]["ok"] is False
    assert r["verdict"] == "infeasible"


def test_failing_candidates_are_never_ranked():
    d = json.loads((TR / "feasibility.json").read_text())
    by_case = {r["path"]: r for r in d["records"]}
    import tcpmt_cases as TC
    for key, rk in d["rankings"].items():
        st, t = key.split("_")
        for a in rk["ranked"]:
            rec = by_case[str(TC.case_path(st, t, a).relative_to(R))]
            assert rec["verdict"] == "feasible", (key, a)
        assert not set(rk["ranked"]) & {e["arch"] for e in rk["excluded"]}


def test_junction_is_per_device_tier_not_the_field_peak():
    d = json.loads((TR / "feasibility.json").read_text())
    c = d["cases"]["S0_B_Z3"]
    assert c["region_source"].startswith("converged deck")
    assert max(c["junction_C"].values()) < c["T_max_C"] - 10.0


def test_z3_cooling_b_is_not_ranked():
    d = json.loads((TR / "feasibility.json").read_text())
    rk = d["rankings"]["S0_B"]
    assert "Z3" not in rk["ranked"]
    ex = {e["arch"]: e for e in rk["excluded"]}
    assert {"bga_sites", "ir_drop"} <= set(ex["Z3"]["fails"])


# ------------------------------------------------------------------ review round 3: BGA policy
def test_bga_policy_switch_applies_without_rerun():
    """The 1.5-A per-ball target is a filter under BGA_POLICY 'hard' and a stated requirement
    under 'requirement' (the default until the authors decide); every record carries its
    verdict under both, so a stored document is re-read under either (apply_bga_policy), and
    the site budget stays a filter under both."""
    import tcpmt_feasibility as F
    assert set(F.BGA_POLICIES) == {"hard", "requirement"}
    if not os.environ.get("TCPMT_BGA_POLICY"):
        assert F.BGA_POLICY == "requirement"
    checks = {"die": {"ok": True}, "bga_sites": {"ok": True},
              "bga_current": {"ok": False, "value": 2.2, "limit": 1.5}}
    assert F.verdict_under(checks, "hard") == {"verdict": "infeasible",
                                               "fails": ["bga_current"], "unresolved": []}
    assert F.verdict_under(checks, "requirement")["verdict"] == "feasible"
    req = F.bga_requirement("Z1", checks)
    assert req["I_ball_A"] == 2.2 and req["meets_target"] is False and "2.20 A" in req["statement"]
    checks["bga_sites"]["ok"] = False
    assert F.verdict_under(checks, "requirement")["fails"] == ["bga_sites"]
    p = FC / "sensitivity" / "etm_Z1_HV_S0__tim_warp_fb_A.json"
    r = F.evaluate(p, json.loads(p.read_text()), use_fields=False)
    assert set(r["by_bga_policy"]) == set(F.BGA_POLICIES)
    assert r["checks"]["bga_current"]["policy_switched"]
    assert r["verdict"] == r["by_bga_policy"][F.BGA_POLICY]["verdict"]
    doc = {"records": [r], "cases": {"x": dict(r)}, "bga_policy": {"in_force": F.BGA_POLICY},
           "rankings_by_bga_policy": {q: {"marker": q} for q in F.BGA_POLICIES}}
    for q in F.BGA_POLICIES:
        d = F.apply_bga_policy(doc, q)
        assert d["records"][0]["verdict"] == r["by_bga_policy"][q]["verdict"]
        assert d["cases"]["x"]["fails"] == r["by_bga_policy"][q]["fails"]
        assert d["rankings"] == {"marker": q} and d["bga_policy"]["in_force"] == q


def test_bga_check_takes_the_worse_of_the_two_currents(tmp_path, monkeypatch):
    """Z1 in the production state: the per-ball check takes the worse of the DC peak x k rule
    and the port model's worst-ball RMS (scaled to the case's 48-V current) and reports both;
    a reference state, or another ball count, keeps the closure rule alone."""
    import tcpmt_feasibility as F
    (tmp_path / "input_decoupling.json").write_text(json.dumps({"summary": {
        "ball_currents_recommended": {"n_per_rail": 220, "I_ball_rms_max_A": 2.0,
                                      "I_total_dc_A": 20.0}}}))
    monkeypatch.setattr(F, "TR", tmp_path)
    monkeypatch.setattr(F, "peak_fraction", lambda a, n, net=None: (0.025, "test"))
    case = {"scenario": F.TC.SCEN["SDEC"], "i_hv_avg_a": 22.0, "ledger_rows": [
        {"term": "P_BGA_supply", "conductor": "BGA supply balls (N=220)", "I_a": 58.0}]}
    _n, val, lim, ok, _basis, ex = {x[0]: x for x in F.bga_check("Z1", case)}["bga_current"]
    assert ex["I_ball_closure_rule_A"] == pytest.approx(0.025 * 58.0)
    assert ex["I_ball_rms_max_A"] == pytest.approx(2.0 * 22.0 / 20.0)
    assert val == pytest.approx(2.2) and lim == 1.5 and ok is False
    case["scenario"] = "HV_S0"
    _n, val0, _l, _o, _b, ex0 = {x[0]: x for x in F.bga_check("Z1", case)}["bga_current"]
    assert ex0["I_ball_rms_max_A"] is None and val0 == pytest.approx(0.025 * 58.0)
    case["scenario"] = F.TC.SCEN["SDEC"]
    case["ledger_rows"][0]["conductor"] = "BGA supply balls (N=218)"
    assert {x[0]: x for x in F.bga_check("Z1", case)}["bga_current"][5]["I_ball_rms_max_A"] is None


def test_bga_closure_caps_the_count_at_220_per_rail(tmp_path, monkeypatch):
    """Review round 3: at most 220 balls per rail everywhere in the count closure (legal
    counts and the re-scored screen), and the re-closure judges the worse of the DC peak x k
    rule and Z1's worst-ball RMS of the port model."""
    import inspect
    import final_closure_pkg_network as PN
    assert PN.N_MAX_PER_RAIL == 220
    assert inspect.signature(PN.legal_counts).parameters["n_max"].default == 220
    f = tmp_path / "screen.csv"
    f.write_text("arch,n_per_rail,level,terminal_mode,peak_fraction\n"
                 "Z1,218,1,VIN_PAD,0.03\nZ1,220,1,VIN_PAD,0.03\nZ1,222,1,VIN_PAD,0.02\n"
                 "Z2,250,1,VIN_PAD,0.02\n")
    monkeypatch.setattr(PN, "scenarios", lambda a: {"HV_SDEC": 60.0})
    assert sorted(r["n_per_rail"] for r in PN.screen_from_csv(f)) == [218, 220]
    assert "worst-ball RMS" in PN.CLOSURE_RULE and "220" in PN.CLOSURE_RULE
    src = inspect.getsource(PN.reclose)
    assert "port_model_ball_rms" in src and "ball_currents_at_count" in src
