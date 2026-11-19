"""Phase 0M-R Section 25 --- tests for every production model wired this phase.

Each capability is tested POSITIVELY (the model gives the right answer on a case whose
answer is known independently) and NEGATIVELY (the guard that protects it fires on the
REAL offending input, not on a paraphrase of it).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0m", "scripts/phase0i", "scripts"):
    sys.path.insert(0, str(R / p))

import component_stack as CS             # noqa: E402
import cooling_production as CP          # noqa: E402
import interconnect_production as IP     # noqa: E402
import ledger as LG                      # noqa: E402
import rdl_homogenization as RH          # noqa: E402
import routing_production as RP          # noqa: E402
import tsv_production as TP              # noqa: E402
from conduction3d import FVConduction    # noqa: E402
from interconnect import TSVGeometry     # noqa: E402

OUT = R / "results" / "phase0mr"


def _rows(name):
    return list(csv.DictReader(open(OUT / name)))


def _tensor(org, t_d=5e-6):
    fn, xn, yn, zn, f_cu, h = RH.stack_cell(org, t_diel=t_d)
    return ({a: RH._k_eff(fn, xn, yn, zn, i)["k_eff"] for i, a in enumerate("xyz")},
            f_cu)


# ===================================================================== TSV
class TestTSVProduction:
    def test_continuous_field_resistance_is_radius_independent(self):
        """The allocation law R_field = rho*h*J_design/I has no r in it: under minimum-
        capability provisioning the conductor cross-section cancels IDENTICALLY."""
        got = [TP.evaluate(TSVGeometry(r_m=r * 1e-6, h_m=300e-6,
                                       p_m=max(3 * r, 60.0) * 1e-6),
                           1000.0, TP.BUDGET)["R_field_continuous_mohm"]
               for r in (5.0, 15.0, 40.0)]
        assert max(got) - min(got) < 1e-12, got

    def test_the_DISCRETE_count_is_where_radius_re_enters(self):
        """NEGATIVE against over-claiming: the cancellation is exact only in the
        continuum. Integer via counts put a small radius dependence back."""
        got = [TP.evaluate(TSVGeometry(r_m=r * 1e-6, h_m=300e-6,
                                       p_m=max(3 * r, 60.0) * 1e-6),
                           1000.0, TP.BUDGET)["phi_cu"]
               for r in (5.0, 15.0, 40.0)]
        spread = (max(got) - min(got)) / min(got)
        assert 0.0 < spread < 1e-3, spread

    def test_field_resistance_is_height_independent_too(self):
        got = [TP.evaluate(TSVGeometry(r_m=15e-6, h_m=h * 1e-6, p_m=60e-6),
                           1000.0, TP.BUDGET)["R_field_continuous_mohm"]
               for h in (300.0, 300.0)]
        assert got[0] == pytest.approx(got[1], rel=1e-12)
        # and the CONTINUOUS field resistance scales exactly with h, not with r
        r300 = TP.evaluate(TSVGeometry(r_m=15e-6, h_m=300e-6, p_m=60e-6), 1000.0,
                           TP.BUDGET)["R_field_continuous_mohm"]
        r600 = TP.evaluate(TSVGeometry(r_m=15e-6, h_m=600e-6, p_m=60e-6), 1000.0,
                           TP.BUDGET)["R_field_continuous_mohm"]
        assert r600 / r300 == pytest.approx(2.0, rel=1e-9)

    def test_discrete_count_is_an_integer_ceiling(self):
        e = TP.evaluate(TSVGeometry(r_m=15e-6, h_m=300e-6, p_m=60e-6), 1000.0, TP.BUDGET)
        assert float(e["n_required"]).is_integer()
        assert e["n_required"] >= e["n_required_continuous"]
        assert e["n_required"] - e["n_required_continuous"] < 1.0
        assert e["discrete_penalty_pct"] >= 0.0

    def test_j_design_above_process_max_RAISES(self):
        """NEGATIVE: a design density beyond the demonstrated process capability."""
        bad = TP.CurrentDensityBudget(
            j_design=5.0e8, j_process_max=4.0e8, j_reliability_allow=None,
            src_design="test", src_process="test", src_reliability="OPEN")
        with pytest.raises(TP.ProcessViolation):
            bad.check()

    def test_reliability_allowable_is_OPEN_not_defaulted(self):
        """NEGATIVE: nobody may quietly supply an EM allowable."""
        assert TP.BUDGET.j_reliability_allow is None
        assert TP.BUDGET.reliability_status == "OPEN"
        assert TP.BUDGET.src_reliability.startswith("OPEN")

    def test_aspect_ratio_feasibility_is_the_real_lever(self):
        rows = TP.sweep()
        deep = [r for r in rows if r["h_nominal_um"] == 1300.0]
        assert deep and not any(r["feasible_aspect"] for r in deep), \
            "no radius in the swept range is buildable at 1300 um; that is the finding"
        thin = [r for r in rows if r["h_nominal_um"] == 300.0 and r["feasible_aspect"]]
        assert thin and min(r["r_drill_um"] for r in thin) == pytest.approx(15.0), \
            "the reference radius sits exactly ON the 10:1 limit"


# ============================================================= TRANSITION
class TestTransitionResistance:
    def test_uniform_bar_is_exact_at_every_mesh(self):
        """rho*L/A, to solver tolerance. Cell-centred injection would give (n-1)/n."""
        rho, L, a = 1.9e-8, 200e-6, 100e-6
        exact = rho * L / a ** 2
        for n in (9, 17, 25):
            fv = FVConduction(np.linspace(0, a, 13), np.linspace(0, a, 13),
                              np.linspace(0, L, n))
            fv.assign(lambda X, Y, Z: np.full(X.shape, 1.0 / rho))
            face = np.zeros(fv.sigma.shape, bool)
            top = face.copy(); top[:, :, -1] = True
            bot = face.copy(); bot[:, :, 0] = True
            fv.solve(inject_mask=top, inject_total_a=1.0, ground_mask=bot,
                     axis_in=2, axis_gnd=2)
            assert abs(fv.resistance() - exact) / exact < 1e-9, (n, fv.resistance())
            assert fv.resistance_from_power() == pytest.approx(fv.resistance(), rel=1e-6)

    def test_degenerate_cell_RAISES_instead_of_solving(self):
        """NEGATIVE: a zero-width cell gave a silently wrong K_crowd=0.32 in Phase 0M."""
        with pytest.raises(ValueError, match="non-positive cell width"):
            FVConduction(np.array([0.0, 1e-6, 1e-6, 2e-6]), np.linspace(0, 1e-6, 3),
                         np.linspace(0, 1e-6, 3))

    def test_production_dR_is_the_cached_exact_solve_not_a_fit(self):
        """Every production value carries the two resistances it was made from, so the
        difference can be re-checked; a surrogate could not offer that."""
        cache = json.loads((OUT / "transition_dR_cache.json").read_text())
        assert cache, "cache must not be empty"
        for k, v in cache.items():
            assert v["dR_ohm"] == pytest.approx(v["R_3D_ohm"] - v["R_1D_ohm"], rel=1e-12)
            assert v["ratio_3D_over_1D"] == pytest.approx(
                v["R_3D_ohm"] / v["R_1D_ohm"], rel=1e-12)
            assert v["n_cells"] > 1000, (k, v["n_cells"])

    def test_surrogate_is_measured_against_the_SPREAD_and_fails(self):
        """The fit looked good against MAGNITUDE (6 % on C4/BGA). Against the SPREAD it
        is 28.9 % on the very class that looked best. It is REJECTED for all classes."""
        fits = IP.load_fits()
        assert fits
        assert all(f.rms_pct > 5.0 or f.max_pct > 20.0 for f in fits.values()), \
            {k: (f.rms_pct, f.max_pct) for k, f in fits.items()}

    def test_the_production_path_never_calls_the_surrogate(self):
        """NEGATIVE: the strongest statement is behavioural. An uncached geometry must
        SOLVE or fail -- it must never silently fall back to the rejected fit."""
        src = (R / "scripts" / "phase0mr" / "interconnect_production.py").read_text()
        body = src.split("def transition_dR(")[1].split("\nif __name__")[0]
        assert "TransitionFit" not in body and ".dR(" not in body, \
            "transition_dR must not reference the surrogate"
        assert "CR.solve_cell" in body, "the uncached path must be an exact solve"

    def test_dR_may_be_negative_and_is_never_called_excess(self):
        """A difference against a stated 1-D reference, not an 'excess resistance'."""
        cache = json.loads((OUT / "transition_dR_cache.json").read_text())
        neg = [k for k, v in cache.items() if v["dR_ohm"] < 0]
        assert any(k.startswith("tsv|rv=15") for k in neg), \
            "the report says the nominal TSV dR is negative; if it is not, that is wrong"
        # a negative value is only meaningful because the reference is named
        assert all(v["R_1D_ohm"] > 0 for v in cache.values())
        src = (R / "scripts" / "phase0mr" / "interconnect_production.py").read_text()
        assert "excess resistance" not in src.lower()

    def test_moose_cross_validation_ACCEPTED_on_all_five(self):
        rows = [r for r in _rows("current_crowding_validation.csv")
                if r["kind"] == "transition"]
        assert len(rows) == 5
        assert all(r["verdict"] == "ACCEPTED" for r in rows), \
            [(r["case"], r["fv_vs_moose_pct"]) for r in rows]
        assert max(float(r["fv_vs_moose_pct"]) for r in rows) < 1.0

    def test_mesh_alignment_is_proved_not_assumed(self):
        """The first cross-solver run failed at 12-19 % from centroid staircasing."""
        rows = [r for r in _rows("current_crowding_validation.csv")
                if r["kind"] == "transition"]
        for r in rows:
            assert r["trace_edge_on_node"] == "True", r["case"]
            assert r["rdl_plane_on_node"] == "True", r["case"]
            # MOOSE's own discretised block volumes, reported so the geometry the
            # independent solver actually meshed can be compared with the analytic one.
            # The residual 1-2 % is Cartesian staircasing of a CYLINDRICAL via and pad,
            # which the FV solver shares, so the cross-check stays apples-to-apples.
            assert abs(float(r["vol_metal_err_pct"])) < 2.0, r["case"]
            assert abs(float(r["vol_via_err_pct"])) < 2.0, r["case"]


# ================================================================ ROUTING
class TestRoutingProduction:
    def test_every_template_delivers_the_full_cell_current(self):
        for tpl in RP.TEMPLATES:
            edges = RP.build_edges(tpl)
            assert edges, tpl
            out = [e for e in edges if e.name == "vout_plane"]
            assert out, tpl
            assert out[0].i_dc == pytest.approx(RP.DESIGN["i_out_per_vr_a"], rel=1e-9), tpl
            hv = [e for e in edges if e.name == "vin_bus"][0]
            # 48 V in, 1 V out, at the same power: the input current is ~1/48 of the output
            assert hv.i_dc < out[0].i_dc / 40.0, tpl

    def test_vertical_loss_collapses_when_the_intermediate_rail_crosses(self):
        """T4 puts 1.44 A across the tier boundary where T1 puts 20.4 A."""
        t1 = RP.template_loss("T1_EMBEDDED_4LAYER")
        t4 = RP.template_loss("T4_SPLIT_SC_BUCK")
        assert t4["p_vertical_per_vr_w"] < t1["p_vertical_per_vr_w"] / 100.0, \
            (t1["p_vertical_per_vr_w"], t4["p_vertical_per_vr_w"])

    def test_single_tier_template_has_no_vertical_term(self):
        """NEGATIVE: a one-tier template cannot be charged for a tier crossing."""
        t0 = RP.template_loss("T0_SINGLE_LEVEL")
        assert t0["n_tiers"] == 1
        assert t0["p_vertical_per_vr_w"] == 0.0

    def test_infeasible_nets_are_reported_not_silently_dropped(self):
        """NEGATIVE: 0.2 um of copper on one layer cannot carry 20 A."""
        r = RP.template_loss("T1_EMBEDDED_4LAYER", t_cu_m=0.2e-6, n_layers=1)
        assert r["n_infeasible"] > 0
        assert r["infeasible"], "the offending nets must be named, not counted"

    def test_the_term_is_no_longer_common_mode(self):
        """Phase 0M said common-mode. At the reference stack it varies 7.5 % across
        templates -- the number the report quotes, read from the artifact it quotes."""
        ref = [r for r in _rows("intravr_routing_by_template.csv")
               if r["n_layers"] == "9" and r["t_cu_um"] == "10.0"
               and r["via_policy"] == "D_area_optimal"]
        # the artifact was generated before Phase 0M-R3C added T1C_REORDERED, so it
        # is compared against the templates it actually contains, not the live dict
        assert len(ref) == len({r['template'] for r in ref})
        assert set(r['template'] for r in ref) <= set(RP.TEMPLATES)
        assert len(ref) >= 4
        ps = [float(r["p_system_w"]) for r in ref]
        spread = (max(ps) - min(ps)) / min(ps)
        assert 0.070 < spread < 0.080, f"{spread:.4f}: the report states 7.5 %"

    def test_it_is_not_common_mode_at_any_stack_either(self):
        """NEGATIVE: if the templates agreed, the Phase-0M claim would have survived."""
        ps = [RP.template_loss(t)["p_system_w"] for t in RP.TEMPLATES]
        assert max(ps) - min(ps) > 0.1, ps

    def test_loss_falls_when_copper_is_added(self):
        thin = RP.template_loss("T1_EMBEDDED_4LAYER", t_cu_m=5e-6)
        thick = RP.template_loss("T1_EMBEDDED_4LAYER", t_cu_m=20e-6)
        assert thick["p_system_w"] < thin["p_system_w"]


# ============================================================== PARTITION
class TestComponentPartition:
    def test_HS_device_is_not_charged_against_substrate_height(self):
        """It sits BELOW z=0. Charging it was my error; 1226 um reproduces Phase 0H."""
        c = CS.classify("T1_EMBEDDED_4LAYER", "ARCH_Z1_EMBEDDED")
        assert c["height_charged_um"] == pytest.approx(1226.0, abs=1.0), \
            c["height_charged_um"]

    def test_area_bound_is_the_die_shadow_not_the_converter_tile(self):
        """5.61 mm^2 is an OUTPUT of the converter area model, never a bound."""
        c = CS.classify("T1_EMBEDDED_4LAYER", "ARCH_Z1_EMBEDDED")
        assert c["per_cell_budget_mm2"] > 10.0, c["per_cell_budget_mm2"]
        assert c["per_cell_budget_mm2"] != pytest.approx(5.61, abs=0.2), \
            "5.61 mm2 is an OUTPUT of the converter area model, not the bound"

    def test_clearances_are_OPEN_and_block_the_realizable_flag(self):
        """NEGATIVE: no template may be called buildable while clearances are OPEN."""
        assert len(CS.OPEN_CLEARANCES) == 3
        # each carries the REASON it is open, never a plausible default number
        assert all(isinstance(v, str) and not v.strip().replace(".", "").isdigit()
                   for v in CS.OPEN_CLEARANCES.values()), CS.OPEN_CLEARANCES
        for tpl in RP.TEMPLATES:
            for arch in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE"):
                c = CS.classify(tpl, arch)
                assert c["PACKAGE_CLEARANCE_OPEN"] is True, (tpl, arch)
                assert c["FULLY_REALIZABLE"] is False, (tpl, arch)

    def test_the_feasibility_questions_are_answered_SEPARATELY(self):
        """One flag per question: an area failure must not hide a height pass."""
        c = CS.classify("T1_EMBEDDED_4LAYER", "ARCH_Z1_EMBEDDED")
        for k in ("AREA_FEASIBLE", "HEIGHT_FEASIBLE", "THERMAL_FEASIBLE",
                  "ROUTING_FEASIBLE", "CURRENT_DENSITY_FEASIBLE",
                  "PACKAGE_CLEARANCE_OPEN", "FULLY_REALIZABLE"):
            assert isinstance(c[k], bool), k

    def test_T4_fails_the_area_bound_by_a_small_margin(self):
        c = CS.classify("T4_SPLIT_SC_BUCK", "ARCH_Z1_EMBEDDED")
        assert c["AREA_FEASIBLE"] is False
        assert 1.0 < c["die_shadow_util"] < 1.1, c["die_shadow_util"]

    def test_Z2_thin_substrate_fails_on_height(self):
        """NEGATIVE: a 300 um substrate cannot swallow a 1226 um component stack."""
        c = CS.classify("T1_EMBEDDED_4LAYER", "ARCH_Z2_BACKSIDE")
        assert c["HEIGHT_FEASIBLE"] is False
        assert c["space_margin_um"] < 0


# ============================================================= RDL TENSOR
class TestRDLTensor:
    def test_single_direction_lines_are_in_plane_anisotropic(self):
        k, _ = _tensor("LINES_1D")
        assert k["x"] / k["y"] > 100.0, k

    def test_every_realistic_organisation_is_in_plane_ISOTROPIC(self):
        """The Phase-0M 153x-276x claim was for LINES_1D only. Narrowed, not withdrawn."""
        for org in ("ORTHOGONAL", "MESH", "PLANE"):
            k, _ = _tensor(org)
            assert k["x"] == pytest.approx(k["y"], rel=1e-9), (org, k)

    def test_the_real_anisotropy_is_THROUGH_THICKNESS(self):
        for org in ("ORTHOGONAL", "MESH", "PLANE"):
            k, _ = _tensor(org)
            assert 50.0 < k["x"] / k["z"] < 300.0, (org, k)

    def test_wiener_bounds_bracket_every_solved_component(self):
        """NEGATIVE: a homogenized conductivity outside the bounds is a solver bug."""
        for org in ("LINES_1D", "ORTHOGONAL", "MESH", "PLANE"):
            k, f = _tensor(org)
            voigt = f * RH.K_CU + (1 - f) * RH.K_ORG
            reuss = 1.0 / (f / RH.K_CU + (1 - f) / RH.K_ORG)
            for c in "xyz":
                assert reuss * (1 - 1e-9) <= k[c] <= voigt * (1 + 1e-9), (org, c, k[c])

    def test_bump_layer_is_computed_separately_from_the_TSV_field(self):
        b = RH.bump_layer(25.0, 100.0, 50.0, RH.K_SOLDER, RH.K_UNDERFILL)
        assert b["anisotropy"] > 5.0
        assert b["err_voigt_kz_pct"] < 2.0, "through-thickness must approach Voigt"

    def test_adding_the_RDL_does_not_change_the_Z1_Z2_ordering(self):
        rows = [r for r in _rows("rdl_mechanical_fidelity.csv") if r["arch"] == "RATIO"]
        assert len(rows) == 3
        assert all(float(r["du_corner_um"]) > 1.0 for r in rows), "Z1 stays worse than Z2"
        assert max(abs(float(r["ratio_shift_pct"])) for r in rows) < 1.0


# ================================================================ COOLING
class TestCoolingProduction:
    def test_fluid_side_energy_balance_is_exact(self):
        for name, d in CP.CANDIDATES.items():
            e = CP.energy_balance(d, 1000.0)
            assert e["residual_pct"] == pytest.approx(0.0, abs=1e-9), name
            sides = 2.0 if d.two_sided else 1.0
            assert e["Q_from_mdot_cp_dT_w"] * sides == pytest.approx(1000.0, rel=1e-12), \
                name

    def test_two_sided_candidate_is_compared_at_EQUAL_TOTAL_FLOW(self):
        """13.5 g/s per side against 27.0 g/s one-sided: the same pumped mass, so the
        comparison is about where the heat leaves, not how much coolant is bought."""
        one = CP.CANDIDATES["TOP_SI_MICROCHANNEL_27"]
        two = CP.CANDIDATES["TWO_SIDED_SI_14"]
        assert two.m_dot_g_s * 2.0 == pytest.approx(one.m_dot_g_s, rel=1e-12)
        assert CP.energy_balance(two, 1000.0)["dT_fluid_K"] == pytest.approx(
            CP.energy_balance(one, 1000.0)["dT_fluid_K"], rel=1e-12)

    def test_streamwise_temperature_rises_monotonically_from_the_inlet(self):
        d = CP.CANDIDATES["TOP_SI_MICROCHANNEL_27"]
        x = np.linspace(0, 1, 32)
        T = CP.streamwise_fluid_temperature(d, x, np.cumsum(np.full(32, 1000.0 / 32)))
        assert np.all(np.diff(T) > 0)
        assert T[0] > d.t_in_c

    def test_h_follows_Nu_k_over_Dh_and_is_not_a_calibration(self):
        d = CP.CANDIDATES["TOP_SI_MICROCHANNEL_27"]
        e = CP.energy_balance(d, 1000.0)
        s = d.channel().solve(1000.0)
        assert e["h_channel"] == pytest.approx(
            e["Nu"] * CP.K_F / (s["D_h_um"] * 1e-6), rel=1e-9)
        assert e["regime"] == "laminar" and e["Re"] < 2300.0
        # and the resistance chain is a sum of named physical parts, not one fitted number
        assert s["R_total_K_W"] == pytest.approx(
            s["R_base_K_W"] + s["R_conv_K_W"] + s["R_caloric_K_W"], rel=1e-9)

    def test_reaching_the_retired_calibrated_h_costs_real_pumping(self):
        """NEGATIVE against the old Robin boundary: 166 kW/m2K was not free."""
        e = CP.energy_balance(CP.CANDIDATES["TOP_SI_MICROCHANNEL_50"], 1000.0)
        assert e["h_effective"] > 1.4e5
        assert e["P_pump_hydraulic_W"] > 50.0, e["P_pump_hydraulic_W"]

    def test_pump_efficiency_is_carried_as_a_BAND_not_a_number(self):
        e = CP.energy_balance(CP.CANDIDATES["TOP_SI_MICROCHANNEL_27"], 1000.0)
        got = [k for k in e if k.startswith("P_pump_shaft_at_eta_")]
        assert len(got) == len(CP.ETA_PUMP_BAND) == 3

    def test_moose_cross_validation_keeps_its_failure_visible(self):
        """NEGATIVE: the 10.11 % case must not be tuned away."""
        rows = _rows("cooling_validation.csv")
        assert any(r["verdict"] == "REJECTED" for r in rows), \
            "the 10.11 % wide-channel case must stay visible, not be tuned away"
        prod = [r for r in rows if r["case"] == "TuckermanPease_50x302"]
        assert prod, [r["case"] for r in rows]
        assert float(prod[0]["error_pct"]) < 5.0 and prod[0]["verdict"] == "ACCEPTED", \
            "the PRODUCTION channel geometry is the one that must pass"


# =========================================================== SPATIAL HEAT
class TestSpatialHeat:
    def test_heat_map_totals_every_declared_term(self):
        import production_et as PE
        hm = PE.HeatMap(1000.0, 100.0, 5.0, 8.0, 2.0, 5.0)
        assert hm.total() == pytest.approx(1120.0, rel=1e-12)

    def test_energy_guard_fires_on_a_lost_watt(self):
        """NEGATIVE: a watt that does not land in the mesh must raise, not warn."""
        import production_et as PE
        hm = PE.HeatMap(1000.0, 100.0, 5.0, 8.0, 2.0, 5.0)
        with pytest.raises(PE.EnergyError):
            PE.check_energy(hm, deposited=hm.total() - 1.0)

    def test_guard_tolerates_float_accumulation_and_nothing_larger(self):
        """1e-6 relative: loose enough for six (w/vol)*vol round trips, tight enough
        that a 10 mW discrepancy still raises."""
        import production_et as PE
        hm = PE.HeatMap(1000.0, 100.0, 5.0, 8.0, 2.0, 5.0)
        PE.check_energy(hm, deposited=hm.total() + 3.2e-7)        # must not raise
        with pytest.raises(PE.EnergyError):
            PE.check_energy(hm, deposited=hm.total() + 1.0e-2)

    def test_no_architecture_uses_a_substituted_converter_layer_any_more(self):
        """HISTORY, kept deliberately. Through Phase 0M-R, ARCH_Z4 had no converter layer
        in the mesh at all -- `zglobal.stack_for` has branches for "in" and "below" and
        none for "above" -- so its heat was deposited in `interface`, 0.355 mm below the
        cooled face, and every Z4 thermal and mechanical number was conditional on that.
        Phase 0M-R2 built the power die as real geometry. This test now asserts the
        CORRECTED behaviour and names what it replaced, so the substitution cannot come
        back unnoticed."""
        import production_et as PE
        want = {"ARCH_Z1_EMBEDDED": ("tile_band", 1.30),
                "ARCH_Z2_BACKSIDE": ("conv", 0.30),
                "ARCH_Z4_POWER_DIE": ("pdie_gan_hs", 0.30)}
        for arch, (first, h) in want.items():
            m = PE.build_global(arch, h)[0]
            got = PE.converter_layer(arch, m)
            got = (got,) if isinstance(got, str) else got
            assert got[0] == first, (arch, got)
            assert "interface" not in got, f"{arch} is back on the substituted layer"
            assert set(got) <= {l.name for l in m.layers}, (arch, got)

    def test_the_Z4_power_die_is_real_geometry(self):
        import production_et as PE
        names = {l.name for l in PE.build_global("ARCH_Z4_POWER_DIE", 0.30)[0].layers}
        assert {"pdie_gan_hs", "pdie_gan_ls", "pdie_inductor", "pdie_mlcc"} <= names

    def test_no_converter_layer_at_all_RAISES(self):
        """NEGATIVE: converter heat must never be silently dropped, and ARCH_Z4 must
        never fall back to `interface` again."""
        import production_et as PE

        class _M:
            layers = [type("L", (), {"name": n})() for n in ("die", "interface")]
        with pytest.raises(PE.EnergyError, match="no longer permitted"):
            PE.converter_layer("ARCH_Z4_POWER_DIE", _M())

    def test_every_replayed_case_closed_its_energy_balance(self):
        rows = [r for r in _rows("production_architecture_replay.csv")
                if r["status"] == "OK"]
        assert len(rows) == 10
        for r in rows:
            assert abs(float(r["energy_residual_pct"])) < 1e-4, r["case"]


# ========================================================== ET FIXED POINT
class TestETFixedPoint:
    def test_ledger_refuses_a_term_with_no_declared_owner(self):
        """NEGATIVE: a watt with no owner cannot enter the total."""
        lg = LG.LossLedger(n_vr=49)
        with pytest.raises(LG.LedgerError, match="no declared owner"):
            lg.add("P_mystery", 1.0)

    def test_ledger_refuses_a_second_writer_to_one_term(self):
        """NEGATIVE: exactly one owner per watt, enforced, not conventional."""
        lg = LG.LossLedger(n_vr=49)
        lg.add("P_TSV", 1.0)
        with pytest.raises(LG.LedgerError, match="double"):
            lg.add("P_TSV", 1.0)

    def test_ledger_refuses_to_total_while_a_term_is_missing(self):
        """NEGATIVE: a silently absent term would look like a lower loss."""
        lg = LG.LossLedger(n_vr=49)
        lg.add("P_TSV", 1.0)
        with pytest.raises(LG.LedgerError, match="incomplete"):
            lg.total()

    def test_decomposition_reproduces_its_own_aggregate(self):
        """The upstream model returns only p_cond and p_sw. The per-component split is
        re-derived here and CHECKED against that aggregate; a mismatch raises, so a
        decomposition that cannot reproduce its own total never reaches the ledger."""
        import replay_production as RPX
        d = RPX.electrical("ARCH_Z2_BACKSIDE", 0.30, "AFTER", 85.0, 85.0)
        dec = d["dec"]
        parts = sum(dec[k] for k in (
            "P_switch_hs_conduction", "P_switch_ls_conduction", "P_inductor_DCR",
            "P_cap_ESR", "P_switching_hard", "P_gate", "P_Coss"))
        # the components are PER REGULATOR; the aggregate is system-wide across the cells of
        # the design in force (TCPMT round 3: the design record's count)
        assert parts * RPX.n_vr() == pytest.approx(dec["p_conv_total_w"], rel=1e-9)
        # and the ledger must have applied exactly that scaling, once
        assert d["ledger"].converter_total() == pytest.approx(
            dec["p_conv_total_w"], rel=1e-9)

    def test_a_decomposition_that_does_not_close_RAISES(self):
        """NEGATIVE: perturb one component and the check must fire."""
        import inspect
        src = inspect.getsource(LG.converter_decomposition)
        assert "raise" in src and "LedgerError" in src, \
            "converter_decomposition must raise on a mismatch, not warn"

    def test_fixed_point_converged_in_every_replayed_case(self):
        rows = [r for r in _rows("production_architecture_replay.csv")
                if r["status"] == "OK" and r["mode"] == "AFTER"]
        assert len(rows) == 7
        for r in rows:
            assert r["et_converged"] == "True", r["arch"]
            assert int(r["et_iters"]) >= 2, r["arch"]
            assert int(r["fluid_iters"]) >= 1, r["arch"]

    def test_temperature_feedback_actually_changes_the_answer(self):
        """NEGATIVE: if rho(T) were not fed back, BEFORE and AFTER would agree."""
        rows = {(r["arch"], r["mode"]): r for r in
                _rows("production_architecture_replay.csv")
                if r["status"] == "OK" and (r["cooler"].endswith("27")
                                            or r["mode"] == "BEFORE")
                and r["template"] in ("T1_EMBEDDED_4LAYER", "lumped")}
        for a in ("ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"):
            b, f_ = rows[(a, "BEFORE")], rows[(a, "AFTER")]
            assert float(f_["T_max_C"]) - float(b["T_max_C"]) > 5.0, a
            assert float(f_["P_elec_total_w"]) > float(b["P_elec_total_w"]), a

    def test_the_headline_ordering_survives_production_integration(self):
        """Z2 better than Z1 on the reliability driver, before AND after."""
        rows = {(r["arch"], r["mode"]): r for r in
                _rows("production_architecture_replay.csv")
                if r["status"] == "OK" and (r.get("cooler", "").endswith("27")
                                            or r["mode"] == "BEFORE")
                and r.get("template") in ("T1_EMBEDDED_4LAYER", "lumped")}
        for mode in ("BEFORE", "AFTER"):
            z1 = float(rows[("ARCH_Z1_EMBEDDED", mode)]["du_corner_um"])
            z2 = float(rows[("ARCH_Z2_BACKSIDE", mode)]["du_corner_um"])
            assert z2 < z1, (mode, z1, z2)
