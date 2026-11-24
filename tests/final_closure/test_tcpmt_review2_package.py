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
    """The per-ball limit is a filter under BGA_POLICY 'hard' (the default: the authors adopted
    2 A per ball as the nominal limit) and a stated requirement under 'requirement'; every
    record carries its verdict under both, so a stored document is re-read under either
    (apply_bga_policy), and the site budget stays a filter under both."""
    import tcpmt_feasibility as F
    assert set(F.BGA_POLICIES) == {"hard", "requirement"}
    if not os.environ.get("TCPMT_BGA_POLICY"):
        assert F.BGA_POLICY == "hard"
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


def test_bga_check_applies_one_rule_and_reports_the_rms_bound(tmp_path, monkeypatch):
    """Review round 3 (the authors' decision of 2026-11-19): the per-ball check applies ONE rule
    to every integration, the DC peak x k against the 2-A target (Kuan et al. 2015), with 1.5 A
    as a conservative sensitivity. Z1's worst-ball RMS of the port model (scaled to the case's
    48-V current) is reported as an idealized bound and never decides the verdict; a reference
    state, or another ball count, has no bound."""
    import tcpmt_feasibility as F
    assert F.LIMITS["bga_A_per_ball"] == 2.0 and F.LIMITS["bga_A_per_ball_sensitivity"] == 1.5
    (tmp_path / "input_decoupling.json").write_text(json.dumps({"summary": {
        "ball_currents_recommended": {"n_per_rail": 220, "I_ball_rms_max_A": 2.0,
                                      "I_total_dc_A": 20.0}}}))
    monkeypatch.setattr(F, "TR", tmp_path)
    monkeypatch.setattr(F, "peak_fraction", lambda a, n, net=None: (0.03, "test"))
    case = {"scenario": F.TC.SCEN["SDEC"], "i_hv_avg_a": 22.0, "ledger_rows": [
        {"term": "P_BGA_supply", "conductor": "BGA supply balls (N=220)", "I_a": 58.0}]}
    _n, val, lim, ok, _basis, ex = {x[0]: x for x in F.bga_check("Z1", case)}["bga_current"]
    assert ex["I_ball_closure_rule_A"] == pytest.approx(0.03 * 58.0)
    assert val == pytest.approx(0.03 * 58.0) and lim == 2.0 and ok is True
    assert ex["ok_at_sensitivity_1p5A"] is False
    # the bound (2.2 A) exceeds the target, is reported, and does not decide the verdict
    assert ex["I_ball_rms_max_A"] == pytest.approx(2.0 * 22.0 / 20.0)
    assert ex["I_ball_rms_bound_ok_2A"] is False
    case["scenario"] = "HV_S0"
    _n, val0, _l, _o, _b, ex0 = {x[0]: x for x in F.bga_check("Z1", case)}["bga_current"]
    assert ex0["I_ball_rms_max_A"] is None and val0 == pytest.approx(0.03 * 58.0)
    case["scenario"] = F.TC.SCEN["SDEC"]
    case["ledger_rows"][0]["conductor"] = "BGA supply balls (N=218)"
    assert {x[0]: x for x in F.bga_check("Z1", case)}["bga_current"][5]["I_ball_rms_max_A"] is None


def test_bga_closure_caps_the_count_at_220_per_rail(tmp_path, monkeypatch):
    """Review round 3: at most 220 balls per rail everywhere in the count closure (legal
    counts and the re-scored screen)."""
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
    assert "220" in PN.CLOSURE_RULE and "220" in PN.RECLOSE_RULE


def _fake_network_pool(c):
    """A stand-in for the FV solves: the per-ball peak fraction c[arch] / n at every level, a
    uniform split, the loop resistance falling with the count."""
    def pool(jobs):
        return [{"arch": a, "rail": rail, "n_per_rail": n, "level": lv,
                 "terminal_mode": kw["mode"], "i_ball_max_a": c[a] / n,
                 "r_eff_ohm": 0.2 / n, "p_loss_w": 0.2 / n, "ball_imax_over_imean": 2.0,
                 "max_cell_drop_v": 1e-3, "n_cv": 1000 * lv, "energy_residual_rel": 0.0,
                 "i_ball_a": [1.0 / n] * n, "ball_xy": [[0.8 * j, 0.0] for j in range(n)]}
                for a, rail, n, lv, kw in jobs]
    return pool


def _stub_reclose(tmp_path, monkeypatch, c, k, i_avg, counts):
    import design_record as DR
    import final_closure_pkg_network as PN
    i_sdec = k * i_avg
    (tmp_path / "bga_count_screen.csv").write_text(
        "arch,n_per_rail,level,terminal_mode,peak_fraction\n" + "".join(
            f"{a},{n},1,VIN_PAD,{c[a] / n!r}\n" for a in ("Z1", "Z2") for n in counts))
    pn = {"matched_count": 220, "meta": {"design": DR.design_identity()},
          "loop": {a: {"n_per_rail": 220, "r_supply_ohm": 0.2 / 220, "r_return_ohm": 0.2 / 220,
                       "r_loop_ohm": 0.4 / 220} for a in ("Z1", "Z2")}}
    (tmp_path / "package_network.json").write_text(json.dumps(pn))
    monkeypatch.setattr(PN, "OUT", tmp_path)
    monkeypatch.setattr(PN, "PRODUCTION_OUT", tmp_path / "bga_count_production.json")
    monkeypatch.setattr(PN, "ADOPTED_OUT", tmp_path / "package_network_adopted.json")
    monkeypatch.setattr(PN, "run_pool", _fake_network_pool(c))
    monkeypatch.setattr(PN, "production_k", lambda: (k, [2.60, 2.70]))
    monkeypatch.setattr(PN, "chain_k", lambda: (k, [2.60, 2.70]))
    monkeypatch.setattr(PN, "production_i_avg", lambda a: i_avg)
    monkeypatch.setattr(PN, "scenarios", lambda a: {"HV_S0": i_avg, "HV_SDEC": i_sdec})
    monkeypatch.setattr(PN, "port_model_ball_rms",
                        lambda n, crit=None: {"I_ball_rms_max_A": 2.2, "option": "test",
                                              "k_eq": 2.5})
    monkeypatch.setattr(PN, "production_cases", lambda: {})
    monkeypatch.setattr(PN, "_CRIT_A", None)            # restored after the test
    monkeypatch.setattr(PN, "_K_FROM_CHAIN", False)
    return PN, pn


def test_bga_reclose_adopts_the_smallest_passing_count(tmp_path, monkeypatch):
    """Review round 3 (the authors' decision of 2026-11-22), the re-closure with the solver
    stubbed: each architecture ADOPTS the smallest legal count whose verified DC peak x k_eq
    meets the feasibility stage's 2-A target across the k_eq band (at its upper end, here 2.70
    against the nominal 2.64) within the site budget (Z2's ring of 528 sites: at most 198 per
    rail), the network is solved there (package_network_adopted.json), 1.5 A is reported as
    the sensitivity by the same rule (here: no legal count closes it), Z1's port-model RMS is
    an idealized bound only, the modelled arrangement is recorded beside it, and a network of
    another design is refused."""
    import design_record as DR
    k, i_avg = 2.64, 23.6
    i_sdec = k * i_avg
    c = {"Z1": 1.73 * 220 / i_sdec, "Z2": 1.63 * 220 / i_sdec}    # peak fraction = c / n
    PN, pn = _stub_reclose(tmp_path, monkeypatch, c, k, i_avg, range(160, 221, 2))
    assert PN.site_budget("Z2")["cap_per_rail"] == 198            # 0.75 x 528 / 2
    assert PN.site_budget("Z1")["cap_per_rail"] == 220            # the 220-per-rail cap binds
    PN.reclose()
    out = json.loads((tmp_path / "bga_count_production.json").read_text())
    assert out["criterion_A_per_ball"] == 2.0 and out["criterion_sensitivity_A_per_ball"] == 1.5
    # across the band (k 2.70 / 2.64): 1.73 A x 220 / n x 2.70 / 2.64 <= 2 A -> n >= 194.6;
    # 1.63 A x 220 / n x 2.70 / 2.64 <= 2 A -> n >= 183.4 (at the nominal k: 192 and 180)
    kf = 2.70 / 2.64
    assert out["adopted_count"] == {"Z1": 196, "Z2": 184}
    assert out["k_eq_count_rule"] == pytest.approx(2.70)
    assert out["modelled_count"] == 220 and out["matched_count_dc_rule"] == 192
    assert out["count_rule"] == PN.ADOPT_RULE
    bc = out["ball_currents_at_count"]
    assert bc["n_per_rail"] == {"Z1": 196, "Z2": 184} and bc["rule"] == PN.RECLOSE_RULE
    assert bc["status"] == "CLOSED" and bc["status_at_sensitivity"] == "NOT_CLOSED"
    z1, z2 = bc["per_arch"]["Z1"], bc["per_arch"]["Z2"]
    assert z1["I_ball_A"] == pytest.approx(1.73 * 220 / 196)
    assert z2["I_ball_A"] == pytest.approx(1.63 * 220 / 184)
    assert z1["I_ball_at_band_A"] == pytest.approx(1.73 * 220 / 196 * kf) and z1["passes_band"]
    assert z1["margin_at_band_A"] == pytest.approx(2.0 - 1.73 * 220 / 196 * kf)
    assert z2["site_fraction"] == pytest.approx(368 / 528) and z2["site_budget_ok"]
    assert z1["passes"] and z2["passes"] and not z1["passes_sensitivity"]
    assert z1["I_ball_rms_max_A"] == pytest.approx(2.2) and z1["rms_bound_within_target"] is False
    assert z2["I_ball_rms_max_A"] is None and out["match_fallback"] is None
    ad1 = out["adoption"]["Z1"]
    assert ad1["lower_count"] == 194 and ad1["peak_at_lower_A"] < 2.0        # nominal k: passes
    assert ad1["peak_at_lower_at_band_A"] > 2.0                             # the band: fails
    for a in ("Z1", "Z2"):                                   # 1.5 A: needs n >= 260 / 245
        assert out["sensitivity_count"][a]["n_per_rail"] is None
        assert "cannot close" in out["sensitivity_count"][a]["statement"]
    mo = out["modelled_arrangement"]["per_arch"]
    assert mo["Z2"]["site_fraction"] == pytest.approx(440 / 528) and not mo["Z2"]["site_budget_ok"]
    assert mo["Z1"]["I_ball_closure_rule_A"] == pytest.approx(1.73)
    ad = json.loads((tmp_path / "package_network_adopted.json").read_text())
    assert ad["adopted_count"] == {"Z1": 196, "Z2": 184}
    assert ad["loop"]["Z1"]["n_per_rail"] == 196 and len(ad["convergence"]["Z2_supply"]["i_ball_frac"]) == 184
    assert ad["meta"]["design"]["design"] == DR.name()
    # another design's network never stands in
    pn["meta"]["design"]["design"] = "not_" + DR.name()
    (tmp_path / "package_network.json").write_text(json.dumps(pn))
    with pytest.raises(SystemExit):
        PN.reclose()


def test_bga_reclose_site_budget_binds(tmp_path, monkeypatch):
    """When no legal count within the site budget meets the target, the count of least peak
    within it is adopted and flagged NOT_CLOSED; the sensitivity reports a count beyond the
    budget as such."""
    k, i_avg = 2.64, 23.6
    i_sdec = k * i_avg
    c = {"Z1": 1.73 * 220 / i_sdec, "Z2": 1.0 * 200 / i_sdec * 2.0}   # Z2 needs 200 at 2 A
    PN, _pn = _stub_reclose(tmp_path, monkeypatch, c, k, i_avg, range(160, 221, 2))
    PN.reclose()
    out = json.loads((tmp_path / "bga_count_production.json").read_text())
    assert out["adoption"]["Z2"]["status"] == "NOT_CLOSED"
    assert out["adopted_count"]["Z2"] == 198                       # least peak within the budget
    assert out["ball_currents_at_count"]["status"] == "NOT_CLOSED"
    assert out["match_fallback"]["status"] == "NOT_CLOSED"
    assert out["adopted_count"]["Z1"] == 196


def test_bga_coupled_effect_of_the_adopted_count():
    """The change of a production case's BGA feed terms from the count it was solved at (its
    own ledger terms) to the adopted network, at the case's own 48-V current and BGA
    temperature (final_closure_ledger.package_hv_terms), with the modelled arrangement's terms
    recorded beside it; Z2 has no coupled term (direct feed), its ring feed is reported. A
    case solved at the modelled arrangement changes by the adopted-minus-modelled terms; a
    case solved at a count next to the adopted one changes by little and is not re-run."""
    import final_closure_ledger as FL
    import final_closure_pkg_network as PN

    def net(n, r):
        return {"loop": {a: {"n_per_rail": n, "r_supply_ohm": r, "r_return_ohm": r / 2}
                         for a in ("Z1", "Z2")},
                "convergence": {f"{a}_{rail}": {"i_ball_frac": [1.0 / n] * n}
                                for a in ("Z1", "Z2") for rail in ("supply", "return")}}
    mod, ado = net(220, 4.5e-4), net(168, 6.0e-4)

    def case(n, terms):
        rows = [{"term": t, "P_w": v["P_w"], "I_a": 62.5,
                 "conductor": f"BGA supply balls (N={n})"} for t, v in terms.items()]
        return {"ledger_rows": rows, "et_history": [{"T_bga_C": 110.0}], "i_hv_avg_a": 23.7,
                "P_loss_w": 135.0}
    tm = FL.package_hv_terms(mod, "Z1", 62.5, 110.0)
    p_a = sum(v["P_w"] for v in FL.package_hv_terms(ado, "Z1", 62.5, 110.0).values())
    p_m = sum(v["P_w"] for v in tm.values())
    z2 = (Path("etm_Z2.json"), {"ledger_rows": [], "et_history": [{"T_bga_C": 89.0}],
                                "i_hv_avg_a": 23.6, "P_loss_w": 134.0})
    orig = PN.production_cases
    try:
        PN.production_cases = lambda: {("Z1", "A"): (Path("etm_Z1.json"), case(220, tm)),
                                       ("Z2", "A"): z2}
        ce = PN.coupled_effect(ado, mod, 2.64)
        # the case solved on a network 1 % off the adopted one (a neighbouring count)
        near = net(166, 6.06e-4)
        PN.production_cases = lambda: {("Z1", "A"): (Path("etm_Z1.json"), case(
            166, FL.package_hv_terms(near, "Z1", 62.5, 110.0)))}
        ce2 = PN.coupled_effect(ado, mod, 2.64)
    finally:
        PN.production_cases = orig
    z1, z2r = ce["per_case"]["A_Z1"], ce["per_case"]["A_Z2"]
    assert z1["dP_W"] == pytest.approx(p_a - p_m) and z1["dP_W"] > 0.1
    assert z1["dP_vs_modelled_W"] == pytest.approx(p_a - p_m)
    assert z1["n_case"] == 220 and z1["case_carries_adopted_count"] is False
    assert z2r["coupled"] is False and z2r["dP_W"] == 0.0 and z2r["ring_feed_dP_W"] is not None
    assert ce["exceeds_threshold"] and ce["cases_on_another_count"] == ["A_Z1"]
    assert "re-run" in ce["action"] and "below" not in ce["action"]
    n1 = ce2["per_case"]["A_Z1"]
    assert n1["n_case"] == 166 and abs(n1["dP_W"]) < 0.1 and n1["dP_vs_modelled_W"] > 0.1
    assert not ce2["exceeds_threshold"] and ce2["cases_on_another_count"] == ["A_Z1"]
    assert ce2["action"].startswith("below the threshold") and "accepted_count" in ce2["action"]


def test_case_on_another_count_stands_for_the_adopted_one(tmp_path, monkeypatch):
    """A BGA-fed case solved at another 48-V count than the re-closure's adopted one stands for
    it only when the re-closure recorded the change of the production cases' BGA feed terms
    from that count below its threshold (final_closure_ledger.accepted_count); the feasibility
    stage then checks its balls at the adopted count with the case's own 48-V current, and the
    mechanics guard accepts the case."""
    import design_record as DR
    import final_closure_ledger as FL
    import tcpmt_feasibility as F
    import tcpmt_mech_production as MP
    ident = DR.design_identity()
    conv = lambda f: {f"Z1_{r}": {"final": {"i_ball_max_a": f}} for r in ("supply", "return")}
    (tmp_path / "package_network.json").write_text(json.dumps(
        {"matched_count": 220, "meta": {"design": ident, "final_levels": [1, 2, 3]},
         "convergence": conv(0.0277)}))
    (tmp_path / FL.ADOPTED_NETWORK_NAME).write_text(json.dumps(
        {"meta": {"design": ident, "final_levels": [1, 2, 3]}, "adopted_count": {"Z1": 170},
         "loop": {"Z1": {"n_per_rail": 170}}, "convergence": conv(0.0316)}))
    rec = {"design": ident, "adopted_count": {"Z1": 170},
           "coupled_effect": {"threshold_W": 0.1, "exceeds_threshold": False, "per_case": {
               "A_Z1": {"coupled": True, "n_case": 168, "n_adopted": 170, "dP_W": -0.045},
               "A_Z2": {"coupled": False, "dP_W": 0.0}}}}
    (tmp_path / FL.RECLOSE_RECORD_NAME).write_text(json.dumps(rec))
    n, note = FL.accepted_count("Z1", 168, tmp_path)
    assert n == 170 and "0.1" in note and "-0.045" in note
    assert FL.accepted_count("Z1", 170, tmp_path) == (170, None)
    assert FL.accepted_count("Z1", 166, tmp_path)[0] is None       # no recorded change from 166
    assert FL.accepted_count("Z2", 166, tmp_path)[0] is None       # no adopted Z2 count here
    case = {"arch": "Z1", "scenario": "HV_S0", "design": {},
            "ledger_rows": [{"term": "P_BGA_supply", "I_a": 62.5,
                             "conductor": "BGA supply balls (N=168)"},
                            {"term": "P_pkg_RDL_HV_supply", "conductor": "",
                             "model": "voltage-fed refined FV sheet, N=168/rail"}]}
    monkeypatch.setattr(F, "FC", tmp_path)
    monkeypatch.setattr(F, "_NET", {})
    monkeypatch.setattr(MP, "FC", tmp_path)
    chk = {c[0]: c for c in F.bga_check("Z1", case)}
    _, val, _lim, ok, basis, extra = chk["bga_current"]
    assert val == pytest.approx(0.0316 * 62.5) and ok and "adopted 170" in basis
    assert extra["n_per_rail"] == 170 and extra["n_per_rail_case"] == 168
    assert chk["bga_sites"][1] == pytest.approx(340 / 1369)
    assert MP.input_issue("Z1", case) is None
    rec["coupled_effect"]["exceeds_threshold"] = True             # above it: re-run, not accepted
    (tmp_path / FL.RECLOSE_RECORD_NAME).write_text(json.dumps(rec))
    assert FL.accepted_count("Z1", 168, tmp_path)[0] is None
    assert "re-run has not landed" in MP.input_issue("Z1", case)
    monkeypatch.setattr(F, "_NET", {})
    _, val, _lim, ok, basis, extra = {c[0]: c for c in F.bga_check("Z1", case)}["bga_current"]
    assert extra["n_per_rail"] == 168                               # its own count (screen)


def test_ledger_takes_the_adopted_network(tmp_path, monkeypatch):
    """The BGA-fed ledger's package network is the re-closure's adopted one when it exists
    beside package_network.json for the same design (per architecture key, its own count);
    another design's adopted network never stands in."""
    import design_record as DR
    import final_closure_ledger as FL
    import z1_design as Z1D
    ident = DR.design_identity()
    pn = {"matched_count": 220, "meta": {"design": ident},
          "loop": {"Z1": {"n_per_rail": 220}, "Z2": {"n_per_rail": 220}},
          "convergence": {"Z1_supply": {"i_ball_frac": [1 / 220] * 220}}}
    pa = {"meta": {"design": ident}, "adopted_count": {"Z1": 168, "Z2": 166},
          "loop": {"Z1": {"n_per_rail": 168}, "Z2": {"n_per_rail": 166}},
          "convergence": {"Z1_supply": {"i_ball_frac": [1 / 168] * 168}}}
    (tmp_path / "package_network.json").write_text(json.dumps(pn))
    monkeypatch.setattr(Z1D, "package_network_file", lambda path=None: tmp_path / "package_network.json")
    FL.package_network.cache_clear()
    try:
        assert FL.package_network()["loop"]["Z1"]["n_per_rail"] == 220
        (tmp_path / FL.ADOPTED_NETWORK_NAME).write_text(json.dumps(pa))
        FL.package_network.cache_clear()
        got = FL.package_network()
        assert got["loop"]["Z1"]["n_per_rail"] == 168 and got["adopted_count"]["Z2"] == 166
        assert len(got["convergence"]["Z1_supply"]["i_ball_frac"]) == 168
        assert got["modelled_count"] == 220
        pa["meta"]["design"] = dict(ident, design="not_" + ident["design"])
        (tmp_path / FL.ADOPTED_NETWORK_NAME).write_text(json.dumps(pa))
        FL.package_network.cache_clear()
        assert FL.package_network()["loop"]["Z1"]["n_per_rail"] == 220
    finally:
        FL.package_network.cache_clear()


def test_feasibility_peak_fraction_at_the_adopted_count(tmp_path, monkeypatch):
    """The feasibility stage takes a case's per-ball peak fraction from the adopted-count
    network when the case carries that count (else the network build's, else the screen)."""
    import design_record as DR
    import tcpmt_feasibility as F
    ident = DR.design_identity()
    conv = lambda f: {f"{a}_{r}": {"final": {"i_ball_max_a": f}} for a in ("Z1", "Z2")
                      for r in ("supply", "return")}
    (tmp_path / "package_network.json").write_text(json.dumps(
        {"matched_count": 220, "meta": {"design": ident, "final_levels": [1, 2, 3]},
         "convergence": conv(0.0277)}))
    (tmp_path / "package_network_adopted.json").write_text(json.dumps(
        {"meta": {"design": ident, "final_levels": [1, 2, 3]}, "adopted_count": {"Z1": 168},
         "loop": {"Z1": {"n_per_rail": 168}}, "convergence": conv(0.0320)}))
    monkeypatch.setattr(F, "FC", tmp_path)
    monkeypatch.setattr(F, "_NET", {})
    assert F.peak_fraction("Z1", 168) == (0.0320, "adopted-count network (level 3)")
    assert F.peak_fraction("Z1", 220) == (0.0277, "package network (level 3)")


def test_omitted_losses_raise_the_48v_ball_current(tmp_path, monkeypatch):
    """The omitted converter losses (with their feedback, dP) add to the 48-V input current:
    the per-ball check of a 48-V ball field scales by 1 + dP / (48 V x I_avg) at the adopted
    count (k_eq kept), at the nominal k and at the upper end of the band, and for the
    production state the re-closure's count rule is applied at that current (solver stubbed:
    peak fraction c / n). Z3's 1-V balls carry the load current and are not shifted; a
    reference state gets the shifted current without a count search; the bundle's fails
    follow the BGA policy."""
    import tcpmt_feasibility as F
    k, i_avg = 2.64, 23.6
    c = {"Z1": 1.73 * 220 / (k * i_avg), "Z2": 1.63 * 220 / (k * i_avg)}
    _stub_reclose(tmp_path, monkeypatch, c, k, i_avg, range(160, 221, 2))
    (tmp_path / "bga_count_production.json").write_text(json.dumps(
        {"k_eq": k, "k_eq_count_rule": 2.70}))
    monkeypatch.setattr(F, "FC", tmp_path)
    monkeypatch.setattr(F, "_NET", {})
    monkeypatch.setattr(F, "_COUNT_SEARCH", {})
    v0 = c["Z1"] / 196 * k * i_avg                       # 196 per rail: the adopted count
    rec = {"arch": "Z1", "state": F.TC.PRODUCTION_STATE, "tier": "A",
           "checks": {"bga_current": {"value": v0, "limit": 2.0, "ok": True, "n_per_rail": 196,
                                      "I_rms_48V_A": k * i_avg}}}
    case = {"i_hv_avg_a": i_avg, "P_loss_w": 48.0 * i_avg - 1000.0}
    dp = 24.0
    s = 1.0 + dp / (48.0 * i_avg)
    b = F.omitted_ball_current(rec, case, dp)
    assert b["current_scale"] == pytest.approx(s) and b["value"] == pytest.approx(v0 * s)
    assert b["value_at_band"] == pytest.approx(v0 * s * 2.70 / k)
    assert b["ok"] is (v0 * s <= 2.0) and b["I_rms_48V_A"] == pytest.approx(k * i_avg * s)
    # the count rule at the band's current: 1.73 A x 220 / n x s x 2.70 / 2.64 <= 2 A
    need = 1.73 * 220 * s * 2.70 / k / 2.0
    cnt = b["count_across_band"]
    assert cnt["status"] == "CLOSED" and cnt["n_per_rail"] == min(
        n for n in range(160, 221, 2) if n >= need) == 200
    assert cnt["I_ball_at_count_A"] <= 2.0 < cnt["I_ball_at_lower_count_A"]
    assert cnt["lower_count"] == 198
    assert F.omitted_ball_current(dict(rec, arch="Z3"), case, dp) is None
    assert "count_across_band" not in F.omitted_ball_current(dict(rec, state="S0"), case, dp)
    # the bundle's fails follow the policy: the ball check filters only under 'hard'
    case.update(et_history=[{"P_loss_w": 100.0, "T_hs_C": 80.0, "T_die_mean_C": 70.0,
                             "T_max_C": 90.0},
                            {"P_loss_w": 110.0, "T_hs_C": 82.0, "T_die_mean_C": 71.0,
                             "T_max_C": 92.0}])
    omit = {"cases": {"A_Z1": {"omitted": {"nominal": {"total_w": 30.0},
                                           "high": {"total_w": 60.0}}}}}
    rec["checks"]["bga_current"]["value"] = 1.99
    m = F.omitted_margins(rec, case, omit)
    hb = m["bundles"]["high"]
    assert hb["checks"]["bga_current"]["value"] > 2.0
    assert hb["fails_by_bga_policy"] == {"hard": ["bga_current"], "requirement": []}
    assert hb["fails"] == hb["fails_by_bga_policy"][F.BGA_POLICY]


def test_converged_field_skips_stale_files_of_an_earlier_run(tmp_path, monkeypatch):
    """A re-run in a re-used work tree can leave higher-numbered thermal files of the earlier
    run beside its own: the converged field is the newest-numbered file whose T_max matches the
    case's, not simply the last one."""
    import tcpmt_cases as TC
    wd = tmp_path / "wd"
    (wd / "et1").mkdir(parents=True)
    for name, t in (("th_0.frd", 90.0), ("th_1.frd", 100.0), ("th_2.frd", 184.9)):  # th_2 stale
        (wd / "et1" / name).write_text(str(t))
    (wd / "structural.frd").write_text("s")
    monkeypatch.setattr(TC, "_frd_tmax", lambda p: float(Path(p).read_text()))
    monkeypatch.setattr(TC, "_work_dirs", lambda path, case: [wd])
    case = {"thermal": {"T_max_C": 100.0}, "et_history": [{}, {}]}
    f = TC.converged_field(tmp_path / "case.json", case)
    assert Path(f["thermal"]).name == "th_1.frd" and f["structural"] == wd / "structural.frd"
    case["thermal"]["T_max_C"] = 120.0
    assert TC.converged_field(tmp_path / "case.json", case) is None
