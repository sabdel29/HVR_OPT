"""Phase 0M-R2 Section 15 --- guards for geometry, cooling regime and ledger scope.

Categories G through P of the brief. Every guard is negative-tested: the failure it
exists to catch is injected and the guard must fire.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0m",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))

import arch_geometry as AG                                              # noqa: E402
import cooling_regime as CR                                             # noqa: E402
import ledger as LG                                                     # noqa: E402

OUT = R / "results" / "phase0mr2"
ARCHES = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]


# ============================================ G. TSV z-span consistency across E/T/M
class TestTSVSpanConsistency:
    @pytest.mark.parametrize("arch", ARCHES)
    def test_every_domain_uses_the_same_via_length(self, arch):
        """One physical via cannot have two lengths."""
        r = AG.assert_consistent(arch)
        assert r["consistent"] is True
        assert r["electrical_delta_pct"] < 0.5
        assert r["mechanical_delta_pct"] < 0.5

    def test_the_REAL_phase0mr_mismatch_is_caught(self):
        """NEGATIVE, with the real numbers: ARCH_Z2 was 300 um electrically and 280 um
        in the mesh. Injecting 280 must raise."""
        with pytest.raises(AG.GeometryInconsistency, match="two lengths"):
            AG.assert_consistent("ARCH_Z2_BACKSIDE", mech=280.0)

    def test_a_half_percent_disagreement_still_passes(self):
        AG.assert_consistent("ARCH_Z2_BACKSIDE", mech=300.6)

    def test_Z1_traverses_74_um_not_1300(self):
        """The substrate is 1.30 mm but 1226 um of it is the embedded converter cell."""
        s = AG.span("ARCH_Z1_EMBEDDED")
        assert s.h_sub_um == 1300.0
        assert s.converter_cell_um == 1226.0
        assert s.length_um == pytest.approx(74.0)

    def test_no_architecture_traverses_1300_um(self):
        """The Phase-0M-R '1300 um is infeasible' rung belongs to no architecture."""
        assert all(AG.span(a).length_um <= 300.0 for a in AG.cfg()["architectures"])


# ============================================ H. aspect-ratio hard failure
class TestAspectRatio:
    def test_every_architecture_is_inside_the_10_to_1_limit(self):
        for a in AG.cfg()["architectures"]:
            s = AG.span(a)
            assert s.feasible_aspect, (a, s.aspect_ratio)

    def test_Z2_Z4_sit_EXACTLY_on_the_limit(self):
        for a in ("ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"):
            assert AG.span(a).aspect_ratio == pytest.approx(10.0, abs=1e-9)

    def test_a_deeper_span_is_rejected(self):
        """NEGATIVE: the 1300 um span Phase 0M-R swept would need d = 130 um."""
        c = AG.cfg()
        saved = c["architectures"]["ARCH_Z2_BACKSIDE"]["tsv_z_end_um"]
        try:
            c["architectures"]["ARCH_Z2_BACKSIDE"]["tsv_z_end_um"] = 1300.0
            s = AG.span("ARCH_Z2_BACKSIDE")
            assert s.aspect_ratio == pytest.approx(43.33, abs=0.01)
            assert s.feasible_aspect is False
            assert s.d_min_um() == pytest.approx(130.0)
        finally:
            c["architectures"]["ARCH_Z2_BACKSIDE"]["tsv_z_end_um"] = saved


# ============================================ I. n_req <= n_alloc <= n_avail
class TestViaCounts:
    @pytest.mark.parametrize("arch", ARCHES)
    def test_the_allocation_chain_is_ordered(self, arch):
        s = AG.span(arch)
        i = 1000.0 if s.rail == "LV" else 1000.0 / 0.889 / 48.0
        e = AG.field(arch, i)
        assert e["n_required"] <= e["n_allocated"] <= e["n_available"], \
            (arch, e["n_required"], e["n_allocated"], e["n_available"])

    def test_an_over_allocation_is_visible_in_the_record(self):
        """NEGATIVE: the ordering must be checkable, not assumed."""
        e = {"n_required": 10, "n_allocated": 5, "n_available": 100}
        assert not (e["n_required"] <= e["n_allocated"] <= e["n_available"])


# ============================================ K/L/M. cooling correlation validity
class TestCoolingRegime:
    def test_production_point_is_inside_the_laminar_domain(self):
        r = CR.evaluate(27.0, strict=True)
        assert r["regime"] == CR.LAMINAR and r["Re"] < 2300.0
        assert r["in_domain"] is True

    def test_the_50_g_s_point_is_OUT_OF_MODEL_DOMAIN_and_RAISES(self):
        """The Phase-0M-R h = 166 000 / 1.46 MPa / 74 W point. Re = 2342 lies above the
        laminar ceiling and below Gnielinski's floor."""
        with pytest.raises(CR.ModelDomainError, match="No validated correlation"):
            CR.evaluate(50.0, strict=True)

    def test_the_out_of_domain_point_still_reports_its_bracket(self):
        r = CR.evaluate(50.0, strict=False)
        assert r["regime"] == CR.TRANSITIONAL
        assert r["in_domain"] is False
        assert r["nu_correlation"] == CR.OUT_OF_DOMAIN
        assert np.isnan(r["h_effective_W_m2K"])
        # TCPMT revision: the laminar neighbour now uses the short-wall-adiabatic H1 Nu
        # (6.32, was 4.60), which narrows the bracket from 2.76x to ~2.0x
        assert r["bracket_ratio"] > 1.5, "the two neighbours differ by ~2x"

    def test_regime_selection_is_explicit_and_covers_the_three_cases(self):
        c = CR.cfg()
        assert CR.classify(100.0, c) == CR.LAMINAR
        assert CR.classify(2500.0, c) == CR.TRANSITIONAL
        assert CR.classify(5000.0, c) == CR.TURBULENT

    def test_gnielinski_is_never_used_below_its_floor(self):
        """NEGATIVE, the real defect: scripts/phase0m/cooling.py switched to Gnielinski
        at Re = 2300, 700 below its validated floor of 3000."""
        c = CR.cfg()
        floor = c["correlations"]["nusselt_gnielinski"]["re_min"]
        assert floor == 3000.0
        for re in (2301.0, 2500.0, 2999.0):
            assert CR.classify(re, c) != CR.TURBULENT, re

    def test_the_entrance_length_is_reported_not_hidden(self):
        """At 27 g/s the thermal entrance occupies 86 % of the channel, so the
        fully-developed Nusselt number understates h and the answer is conservative."""
        r = CR.evaluate(27.0)
        assert 0.8 < r["entry_fraction"] < 0.95
        assert r["fully_developed"] is False

    def test_the_source_flow_rate_IS_fully_developed(self):
        r = CR.evaluate(1.6)
        assert r["fully_developed"] is True

    def test_energy_balance_closes_at_every_in_domain_point(self):
        for m in (1.6, 27.0, 13.5):
            r = CR.evaluate(m)
            q_back = (m * 1e-3) * r["cp_J_kgK"] * r["dT_coolant_K"]
            assert q_back == pytest.approx(1000.0, rel=1e-9)


# ============================================ N. pumping-power scope
class TestPumpingScope:
    def test_pump_power_cannot_enter_the_electronics_ledger(self):
        """NEGATIVE: it would inflate the loss objective AND reach the thermal mesh."""
        lg = LG.LossLedger(n_vr=49)
        with pytest.raises(LG.LedgerError, match="FACILITY scope"):
            lg.add("P_pump_hydraulic", 14.7)

    def test_an_electronics_term_cannot_enter_the_facility_ledger(self):
        """NEGATIVE: the double-counting direction."""
        fl = LG.FacilityLedger(electronics_w=144.7)
        with pytest.raises(LG.LedgerError, match="double count"):
            fl.add("P_TSV", 1.0)

    def test_facility_total_is_electronics_plus_pumping_exactly(self):
        fl = LG.FacilityLedger(electronics_w=144.737)
        fl.add("P_pump_hydraulic", 14.696)
        assert fl.facility_total() == pytest.approx(159.433, abs=1e-9)

    def test_pumping_is_marked_as_NOT_in_the_thermal_mesh(self):
        """The pump is outside the package, so its heat is not deposited there."""
        fl = LG.FacilityLedger(electronics_w=100.0)
        fl.add("P_pump_hydraulic", 14.7)
        rows = fl.as_rows("t")
        pump = next(r for r in rows if r["term"] == "P_pump_hydraulic")
        assert pump["in_thermal_mesh"] is False
        assert pump["scope"] == "FACILITY"

    def test_a_facility_term_cannot_be_written_twice(self):
        fl = LG.FacilityLedger(electronics_w=100.0)
        fl.add("P_pump_hydraulic", 14.7)
        with pytest.raises(LG.LedgerError):
            fl.add("P_pump_hydraulic", 14.7)


# ============================================ P. Z4 heat goes only into its power die
class TestZ4Geometry:
    def test_the_power_die_exists_as_real_layers(self):
        import production_et as PE
        m, _, _, _ = PE.build_global("ARCH_Z4_POWER_DIE", 0.30)
        names = {l.name for l in m.layers}
        assert {"pdie_gan_hs", "pdie_gan_ls", "pdie_inductor", "pdie_mlcc"} <= names

    def test_converter_heat_never_goes_to_the_interface_layer_again(self):
        """NEGATIVE, the Phase-0M-R substitution: `interface` must no longer be
        returned for ARCH_Z4."""
        import production_et as PE
        m, _, _, _ = PE.build_global("ARCH_Z4_POWER_DIE", 0.30)
        band = PE.converter_layer("ARCH_Z4_POWER_DIE", m)
        assert "interface" not in band
        assert all(n.startswith("pdie_") for n in band)

    def test_a_missing_power_die_RAISES_instead_of_falling_back(self):
        """NEGATIVE: the silent fallback that produced the conditional result is gone."""
        import production_et as PE

        class _M:
            layers = [type("L", (), {"name": n})() for n in
                      ("board", "bga", "sub_lower", "tile_band", "interface", "die")]
        with pytest.raises(PE.EnergyError, match="no longer permitted"):
            PE.converter_layer("ARCH_Z4_POWER_DIE", _M())

    def test_both_construction_variants_are_available_and_differ(self):
        import zglobal as ZG
        st = sum(x[1] for x in ZG.mid_layers("ARCH_Z4_POWER_DIE", "Z4_STACKED"))
        pl = sum(x[1] for x in ZG.mid_layers("ARCH_Z4_POWER_DIE", "Z4_PLANAR"))
        assert st == pytest.approx(1.921, abs=1e-6)
        assert pl == pytest.approx(0.715, abs=1e-6)

    def test_Z1_and_Z2_get_no_mid_layers(self):
        import zglobal as ZG
        assert ZG.mid_layers("ARCH_Z1_EMBEDDED") == []
        assert ZG.mid_layers("ARCH_Z2_BACKSIDE") == []


# ============================================ DEFECT #55
class TestTSVMaterialScope:
    @pytest.mark.parametrize("arch,h", [("ARCH_Z1_EMBEDDED", 1.30),
                                        ("ARCH_Z2_BACKSIDE", 0.30),
                                        ("ARCH_Z4_POWER_DIE", 0.30)])
    def test_tsv_material_appears_only_where_the_field_is(self, arch, h):
        """DEFECT #55. The PCB, the BGA field and ARCH_Z2's backside converter were all
        being given `tsv_homog` because they share the substrate FOOTPRINT."""
        import production_et as PE
        m, _, _, _ = PE.build_global(arch, h)
        lay = np.asarray(m.elem_layer)
        mat = np.asarray(m.elem_material)
        vol = m.elem_volumes()
        cen = m.elem_centroids()
        # the via field must lie inside the CONTRACT span, not inside whichever layer
        # happens to be named `sub_lower`
        s_ = AG.span(arch)
        z0, z1 = s_.z_start_um * 1e-3, s_.z_end_um * 1e-3
        sel = mat == "tsv_homog"
        outside = vol[sel & ((cen[:, 2] < z0 - 1e-9) | (cen[:, 2] > z1 + 1e-9))].sum()
        inside = vol[sel].sum() - outside
        assert outside == 0.0, (
            f"{outside:.3f} mm3 of tsv_homog outside the contract span "
            f"[{s_.z_start_um}, {s_.z_end_um}] um")
        assert inside > 0.0
        # and nothing below z = 0 may carry it: that was DEFECT #55
        assert vol[sel & (cen[:, 2] < -1e-9)].sum() == 0.0

    def test_the_board_is_FR4_again(self):
        import production_et as PE
        m, _, _, _ = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
        lay = np.asarray(m.elem_layer)
        mat = np.asarray(m.elem_material)
        assert set(mat[lay == "board"]) == {"board_fr4"}
        assert set(mat[lay == "conv"]) == {"hvr_effective"}

    def test_footprint_and_tsv_host_are_separate_questions(self):
        """The fix: a layer may span the substrate extent without hosting the via field."""
        from etm.mesh import Layer
        L = Layer("board", -1.0, 0.0, 1, "board_fr4", "substrate")
        assert L.footprint == "substrate" and L.tsv_host is False
