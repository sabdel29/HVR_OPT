"""Phase-0E tests: sourced stack, multilayer RDL, and TSV allocation separation."""
from __future__ import annotations
import math, sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0e"))
sys.path.insert(0, str(R / "scripts" / "phase0d"))

from stack import (RDLStack, stacks_from_cfg, load_cfg, allocate, i_max_per_via,
                   n_required, n_available, Infeasible, multilayer_sheet_solve,
                   rdl_network_solve, rho_cu, r_field)
import hvr_material as HM


# ----------------------------------------------------------------- sourced stack
def test_occupancy_is_derived_from_line_space_not_assumed():
    st = stacks_from_cfg()["ectc2024_primary"]
    assert st.occupancy == pytest.approx(10.0 / 12.0, rel=1e-12)


def test_ectc_table1_rdl_row_reproduces_the_paper():
    """R/l = rho/(W t) must give the printed 170 Ohm/m and R'_Heff the printed 0.046."""
    st = stacks_from_cfg()["ectc2024_primary"]
    r_per_l = rho_cu(20.0) / (st.width_m * st.t_cu_m)
    assert r_per_l == pytest.approx(170.0, rel=1e-3)
    assert st.ectc_r_h_eff(500e-6, 20.0) == pytest.approx(0.046, rel=0.02)


def test_ectc_table1_pcb_row_also_reproduces_the_paper():
    """The PCB row is what decides that 'P/G layers' counts layers PER NETWORK."""
    pcb = RDLStack("pcb", t_cu_m=35e-6, n_vdd=1, n_gnd=1, width_m=152e-6, space_m=456e-6)
    assert rho_cu(20.0) / (pcb.width_m * pcb.t_cu_m) == pytest.approx(3.2, rel=0.01)
    assert pcb.ectc_r_h_eff(500e-6, 20.0) == pytest.approx(0.087, rel=0.02)


def test_phase0e_stack_is_5p56x_more_conductive_than_phase0dr():
    s = stacks_from_cfg()
    ratio = s["ectc2024_primary"].sigma_s_net("vdd") / s["phase0dr_legacy"].sigma_s_net("vdd")
    assert ratio == pytest.approx(5.5556, rel=1e-3)


def test_legacy_stack_still_reproduces_the_phase0dr_sheet():
    """Regression: the superseded stack must still give the Phase-0D-R number."""
    st = stacks_from_cfg()["phase0dr_legacy"]
    assert st.r_sheet_net("vdd", 20.0) * 1e3 == pytest.approx(5.667, rel=1e-3)


def test_current_density_envelope_parses_as_floats():
    """YAML 1.1 needs a signed exponent; '1.00e8' silently parses as a string."""
    cd = load_cfg()["current_density"]
    for mat in ("cu", "solder"):
        for src in cd[mat].values():
            assert isinstance(src["value"], float)
    assert cd["cu"]["june2026"]["value"] == pytest.approx(1.0e8)
    assert cd["cu"]["ectc2024"]["value"] == pytest.approx(4.0e8)


# ----------------------------------------------------- multilayer / VDD-GND network
def test_ideal_stitching_collapses_to_one_sheet_of_summed_conductance():
    src, ld = [(-4.0, 0.0)], [(4.0, 0.0)]
    a = multilayer_sheet_solve([500.0, 500.0], src, [10.0], ld, [10.0], span_mm=20.0,
                               n=41, src_size_mm=2.0, load_size_mm=2.0)
    b = multilayer_sheet_solve([1000.0], src, [10.0], ld, [10.0], span_mm=20.0,
                               n=41, src_size_mm=2.0, load_size_mm=2.0)
    assert a["p_w"] == pytest.approx(b["p_w"], rel=2e-3)


def test_finite_stitching_costs_more_than_ideal():
    src, ld = [(-4.0, 0.0)], [(4.0, 0.0)]
    ideal = multilayer_sheet_solve([500.0, 500.0], src, [10.0], ld, [10.0], span_mm=20.0,
                                   n=31, src_size_mm=2.0, load_size_mm=2.0)
    poor = multilayer_sheet_solve([500.0, 500.0], src, [10.0], ld, [10.0], span_mm=20.0,
                                  n=31, src_size_mm=2.0, load_size_mm=2.0,
                                  stitch_s_per_node=1e-3)
    assert poor["p_w"] > ideal["p_w"]


def test_power_balances_against_iv_product():
    src, ld = [(-4.0, 0.0)], [(4.0, 0.0)]
    r = multilayer_sheet_solve([980.0], src, [20.0], ld, [20.0], span_mm=20.0, n=51,
                               src_size_mm=2.0, load_size_mm=2.0)
    assert r["balance_err_pct"] < 1.0


def test_symmetric_pg_stack_gives_exactly_twice_the_supply_loss():
    st = stacks_from_cfg()["ectc2024_primary"]
    r = rdl_network_solve(st, [(-4.0, 0.0)], [20.0], [(4.0, 0.0)], [20.0], span_mm=20.0,
                          n=41, src_size_mm=2.0, load_size_mm=2.0)
    assert r["p_gnd_w"] == pytest.approx(r["p_vdd_w"], rel=1e-9)
    assert r["p_loop_w"] == pytest.approx(r["symmetric_return_would_give_w"], rel=1e-9)


def test_asymmetric_pg_stack_is_not_just_twice_the_supply():
    """The whole point of solving VDD and GND separately."""
    st = RDLStack("asym", t_cu_m=10e-6, n_vdd=2, n_gnd=1, width_m=10e-6, space_m=2e-6)
    r = rdl_network_solve(st, [(-4.0, 0.0)], [20.0], [(4.0, 0.0)], [20.0], span_mm=20.0,
                          n=41, src_size_mm=2.0, load_size_mm=2.0)
    assert r["p_gnd_w"] == pytest.approx(2.0 * r["p_vdd_w"], rel=1e-2)
    assert r["p_loop_w"] > r["symmetric_return_would_give_w"]


def test_finite_area_ground_removes_the_single_node_pin():
    """A one-node reference discards that node's current; a footprint reference does not."""
    st = stacks_from_cfg()["ectc2024_primary"]
    lds = [(2.0, 0.0), (4.0, 0.0), (6.0, 0.0)]
    pt = multilayer_sheet_solve([st.sigma_s_net("vdd")], [(-4.0, 0.0)], [30.0], lds,
                                [10.0] * 3, span_mm=20.0, n=61, src_size_mm=2.0,
                                load_size_mm=2.0)
    ar = multilayer_sheet_solve([st.sigma_s_net("vdd")], [(-4.0, 0.0)], [30.0], lds,
                                [10.0] * 3, span_mm=20.0, n=61, src_size_mm=2.0,
                                load_size_mm=2.0, ground_xy=lds[1], ground_size_mm=2.0)
    assert ar["p_w"] > 0 and pt["p_w"] > 0
    assert ar["dv_span_v"] < pt["dv_span_v"]      # no point singularity


# -------------------------------------------------- n_req / n_alloc / n_avail
def test_i_max_per_via_is_j_times_area():
    assert i_max_per_via(707e-12, 1.0e8) == pytest.approx(0.0707, rel=1e-6)
    assert i_max_per_via(707e-12, 4.0e8) == pytest.approx(0.2828, rel=1e-6)


def test_allocation_invariant_n_req_le_n_alloc_le_n_avail():
    for policy in ("A_min_capability", "B_geometric", "C_area_optimal"):
        al = allocate("tsv", 60.0, 707e-12, 60e-6, (4.9e-3) ** 2, 1.0e8, policy=policy)
        assert al.n_required <= al.n_allocated <= al.n_available, policy


def test_resistance_uses_n_allocated_not_n_required():
    """Phase 0D-R divided by n_required, which is only right for policy A."""
    a = allocate("tsv", 60.0, 707e-12, 60e-6, (4.9e-3) ** 2, 1.0e8, policy="A_min_capability")
    b = allocate("tsv", 60.0, 707e-12, 60e-6, (4.9e-3) ** 2, 1.0e8, policy="C_area_optimal")
    assert b.n_allocated > a.n_allocated
    assert r_field(7.2e-3, b) < r_field(7.2e-3, a)


def test_p_proportional_to_I_is_a_policy_not_a_law():
    """Under min-capability, P ~ I. Under geometric allocation it is P ~ I^2."""
    r1 = 7.2e-3
    for I in (30.0, 60.0):
        pass
    pa = {I: I ** 2 * r_field(r1, allocate("tsv", I, 707e-12, 60e-6, (4.9e-3) ** 2, 1.0e8,
                                           policy="A_min_capability")) for I in (30.0, 60.0)}
    pb = {I: I ** 2 * r_field(r1, allocate("tsv", I, 707e-12, 60e-6, (4.9e-3) ** 2, 1.0e8,
                                           policy="B_geometric")) for I in (30.0, 60.0)}
    assert pa[60.0] / pa[30.0] == pytest.approx(2.0, rel=0.02)      # linear
    assert pb[60.0] / pb[30.0] == pytest.approx(4.0, rel=0.02)      # quadratic


def test_infeasible_raises_and_is_never_clipped():
    with pytest.raises(Infeasible):
        allocate("tsv", 60.0, 707e-12, 60e-6, (0.5e-3) ** 2, 1.0e6, strict=True)


def test_archB_is_feasible_under_every_source_backed_current_density():
    for j in (load_cfg()["current_density"]["cu"]["june2026"]["value"],
              load_cfg()["current_density"]["cu"]["ectc2024"]["value"]):
        al = allocate("tsv", 60.0, 707e-12, 60e-6, (4.9e-3) ** 2, j)
        assert al.feasible, j
        assert al.utilisation < 0.5


def test_phase0dr_33ma_dropped_the_pg_factor_of_two():
    """1000 A / 30 202 vias = 33.1 mA ignores that half the field is ground."""
    naive = 1000.0 / 30202
    correct = 2 * 1000.0 / 30202
    assert naive == pytest.approx(0.0331, abs=1e-4)
    assert correct == pytest.approx(2 * naive, rel=1e-12)
    assert i_max_per_via(707e-12, 1.0e8) > correct


# ------------------------------------------------------------- Sec.12 material
def test_tile_area_follows_the_compilers_max_rule():
    class D:
        class arch: N, K = 3, 3
        class hs: footprint_mm2 = 3.75
        class ls: footprint_mm2 = 8.58
        class inductor: footprint_mm2, height_um = 1.0, 500.0
        class capacitor: footprint_mm2 = 4.5
    c = HM.compose(D, 2.0)
    assert c.a_hvr_mm2 == pytest.approx(max(3 * 3.75, 3 * 8.58, 3 * 1.0, 2 * 4.5))
    assert c.fill_by_group["ls_gan"] == pytest.approx(1.0)
    assert c.fill_by_group["inductor"] < 0.2


def test_composite_properties_lie_between_the_constituents():
    class D:
        class arch: N, K = 3, 3
        class hs: footprint_mm2 = 3.75
        class ls: footprint_mm2 = 8.58
        class inductor: footprint_mm2, height_um = 1.0, 500.0
        class capacitor: footprint_mm2 = 4.5
    c = HM.compose(D, 2.0)
    assert HM.CONSTITUENTS["mould"]["E"] < c.E_eff_mpa < HM.CONSTITUENTS["silicon"]["E"]
    assert HM.CONSTITUENTS["silicon"]["cte"] < c.cte_eff < HM.CONSTITUENTS["mould"]["cte"]
    assert sum(c.phi_by_material.values()) == pytest.approx(1.0, rel=1e-9)


def test_denser_packing_raises_stiffness():
    """A smaller bounding box holding the same parts is a stiffer tile, not a smaller one."""
    class Big:
        class arch: N, K = 4, 4
        class hs: footprint_mm2 = 3.75
        class ls: footprint_mm2 = 8.58
        class inductor: footprint_mm2, height_um = 1.0, 500.0
        class capacitor: footprint_mm2 = 4.5
    class Small:
        class arch: N, K = 4, 4
        class hs: footprint_mm2 = 3.75
        class ls: footprint_mm2 = 3.75
        class inductor: footprint_mm2, height_um = 1.0, 500.0
        class capacitor: footprint_mm2 = 4.5
    b, s = HM.compose(Big, 1.5), HM.compose(Small, 4.0)
    assert s.a_hvr_mm2 < b.a_hvr_mm2
    assert s.areal_fill > b.areal_fill
    assert s.E_eff_mpa > b.E_eff_mpa
    # the component material barely shrinks even though the bounding box does
    assert (b.a_hvr_mm2 / s.a_hvr_mm2) > 1.5 * (b.component_area_mm2 / s.component_area_mm2)
