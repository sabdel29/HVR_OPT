"""PHASE 0N-AB --- recomputed interconnect resistance and loss (brief 24, 27, 28, 39)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / p))

import interconnect_loss as IL  # noqa: E402


@pytest.fixture(scope="module")
def led():
    return {a: IL.ledger(a) for a in ("Z1", "Z2")}


# ------------------------------------------------------------------ brief 39: scalings
def test_bga_resistance_scales_as_rho_h_over_area():
    a = IL.bga_resistance(1)["r_one_ohm"]
    assert IL.bga_resistance(2)["r_total_ohm"] == pytest.approx(a / 2, rel=1e-12)
    assert IL.bga_resistance(10)["r_total_ohm"] == pytest.approx(a / 10, rel=1e-12)


def test_resistivity_rises_with_temperature():
    assert IL.rho_solder(120.0) > IL.rho_solder(20.0) * 1.3
    assert IL.rho_cu(120.0) > IL.rho_cu(20.0) * 1.3
    hot = IL.bga_resistance(16, T_c=120.0)["r_total_ohm"]
    cold = IL.bga_resistance(16, T_c=20.0)["r_total_ohm"]
    assert hot > cold


def test_tsv_resistance_scales_inversely_with_count():
    a = IL.tsv_loss(100.0, 100, 100, 49)["r_vdd_ohm"]
    b = IL.tsv_loss(100.0, 200, 200, 49)["r_vdd_ohm"]
    assert b < a and b == pytest.approx(a / 2, rel=0.01)


# ------------------------------------------------------- brief 24: the BGA is solder
def test_bga_uses_the_sourced_solder_resistivity_not_copper():
    assert IL.RHO_SOLDER_20C == pytest.approx(130.0e-9)
    assert IL.RHO_SOLDER_20C / IL.RHO_CU_20C > 7.0, "solder must not be modelled as Cu"
    assert IL.bga_resistance(16)["rho_ohm_m"] == pytest.approx(IL.rho_solder(20.0))


def test_bga_alloy_name_is_not_asserted():
    """The design source's abstract does not state an alloy; the RESISTIVITY is sourced."""
    assert "OPEN" in IL.BGA_ALLOY_STATUS
    assert IL.BGA_RHO_STATUS.startswith("SOURCE_BACKED")


def test_equal_current_sharing_is_declared_a_lower_bound(led):
    for a in ("Z1", "Z2"):
        s = IL.bga_resistance(16)
        assert s["sharing"].startswith("EQUAL")
        assert "lower bound" in s["sharing_status"]


# ------------------------------------- brief 2 and 26: no imported crowding factor
def test_no_local_current_density_is_imported(led):
    for a in ("Z1", "Z2"):
        b = led[a]["bga"]
        assert b["j_local_A_cm2"] is None
        assert "OPEN" in b["j_local_status"]
        assert b["j_nominal_A_cm2"] > 0


def test_our_local_j_is_never_22x_our_nominal(led):
    """NEGATIVE: the transferred crowding factor must not come back.

    An earlier phase reported j_local = 22 * j_nominal for OUR package, importing a
    factor measured for a different pad/UBM/trace geometry.
    """
    for a in ("Z1", "Z2"):
        b = led[a]["bga"]
        assert b["j_local_A_cm2"] is None, (
            f"{a} reports a local J of {b['j_local_A_cm2']}; it can only come from this "
            f"package's own pad/RDL solve, which does not exist")
    for f in ("scripts/phase0nw/interconnect_loss.py",
              "scripts/phase0naa_literature_matrix.py"):
        src = (R / f).read_text()
        assert "* 22.0" not in src and "22.0 *" not in src, (
            f"{f} applies a 22x multiplier")


# --------------------------------------------- brief 8 and 27: microbump ladder
def test_microbump_contact_is_a_bound_not_a_claim_of_zero():
    m = IL.microbump_loss(1000.0)
    assert "IDEAL-CONTACT LOWER BOUND" in m["contact_status"]
    assert m["cases"]["MB_L"]["r_contact_one_ohm"] == 0.0
    assert m["status"].startswith("BRACKETED")
    assert "OPEN" in m["geometry_status"]


def test_microbump_contact_resistance_raises_the_loss():
    base = IL.microbump_loss(1000.0, r_contact_ohm=0.0)["p_high_w"]
    with_c = IL.microbump_loss(1000.0, r_contact_ohm=1e-3)["p_high_w"]
    assert with_c > base, "a nonzero contact term must raise the loss"


def test_microbump_bracket_spans_a_real_range():
    m = IL.microbump_loss(1000.0)
    assert m["p_high_w"] > m["p_low_w"] * 5


# ------------------------------------------- brief 28: no double-counted transition
def test_tsv_transition_term_is_open_not_silently_added(led):
    for a in ("Z1", "Z2"):
        t = led[a]["tsv"]
        assert t["transition_term"] is None
        assert "double-count" in t["transition_status"]
        assert "10.1145/3698364.3705353" in t["transition_status"]


# -------------------------------------------- the architectural distinction, recomputed
def test_z2_substrate_tsv_loss_vastly_exceeds_z1(led):
    z1, z2 = led["Z1"]["tsv"], led["Z2"]["tsv"]
    assert led["Z1"]["tsv_rail_v"] == 48.0 and led["Z2"]["tsv_rail_v"] == 1.0
    ratio = z2["p_total_w"] / z1["p_total_w"]
    assert ratio > 1000, f"Z2/Z1 substrate TSV loss ratio is only {ratio:.0f}"
    # and it must equal the current ratio squared
    assert ratio == pytest.approx((z2["i_total_a"] / z1["i_total_a"]) ** 2, rel=1e-6)


def test_bga_loss_is_nearly_equal_between_architectures(led):
    """Both feed 48 V through the same ring at nearly the same current."""
    a, b = led["Z1"]["bga"]["p_total_w"], led["Z2"]["bga"]["p_total_w"]
    assert abs(a - b) / a < 0.01


#: Phase 0N-AI gave the package HV RDL a solved physical network, so its loss
#: maturity now follows CONVERGENCE per architecture: Z2's two networks pass
#: the 1 % test and Z1's do not. Pinned per-architecture rather than relaxed,
#: so neither a regression nor Z1 starting to converge can pass unnoticed.
PKG_RDL_LOSS = {"Z1": "OPEN", "Z2": "SCENARIO"}
N_LOSS_OPEN = {"Z1": 6, "Z2": 4}


def test_ledger_marks_open_terms_open_not_zero(led):
    for a in ("Z1", "Z2"):
        t = led[a]["terms"]
        for k in ("P_intraVR_metal", "P_intraVR_vertical"):
            assert t[k]["w"] is None and t[k]["maturity"]["loss"] == "OPEN", (
                f"{k} must be OPEN, not a zero that reads as 'no loss'")
        for k in ("P_pkg_RDL_HV_supply", "P_pkg_RDL_HV_return"):
            m = t[k]["maturity"]
            assert t[k]["w"] is None, f"{k} must never carry a single value"
            assert m["geometry"] == "CLOSED", f"{k} geometry is now solved"
            assert m["loss"] == PKG_RDL_LOSS[a], (a, k, m)
            if m["loss"] == "OPEN":
                # an OPEN term must not smuggle a number out via scenario_w
                assert t[k]["scenario_w"] is None
                assert t[k]["converged"] is False
            else:
                assert t[k]["converged"] is True
                assert set(t[k]["scenario_w"]) == {"HV_S0", "HV_S1", "HV_S2"}
                assert all(v > 0 for v in t[k]["scenario_w"].values())
        assert led[a]["n_loss_open"] == N_LOSS_OPEN[a]


def test_pkg_rdl_loss_is_I_rms_squared_times_the_solved_resistance(led):
    """The scenario losses must be derivable from the network resistance and
    the named RMS scenarios -- not an independently typed number."""
    import json
    vf = json.loads((R / "research/phase0nai"
                     / "voltage_fed_network.json").read_text())
    a = "Z2"
    t = led[a]["terms"]["P_pkg_RDL_HV_supply"]
    rb = led[a]["rms"]
    r_ohm = vf["loop"][a]["r_supply_ohm"]
    assert t["r_ohm"] == r_ohm
    for s in ("S0", "S1", "S2"):
        expect = rb[f"hv_{s}_a"] ** 2 * r_ohm
        assert t["scenario_w"][f"HV_{s}"] == pytest.approx(expect, rel=1e-12)
    # the source Cu pad replaced the arbitrary microbump bracket as the primary term,
    # but its FIELD COUNT has no criterion, so its loss is a scenario not a value
    pad = led["Z1"]["terms"]["P_pad_VDD"]
    assert pad["maturity"] == {"geometry": "CLOSED", "current": "CLOSED",
                               "loss": "SCENARIO"}
    assert pad["w"] is None and pad["scenario_w"]
    assert "microbump_arbitrary_bracket" in led["Z1"]["legacy_sensitivity"]


def test_ledger_main_runs_to_completion():
    """It did not. main() printed sc['HV_S0'] for every scenario term, and the
    pad terms are keyed PAD_DROP / PAD_GEOM_MAX, so it raised KeyError before
    reaching the end -- a generator that cannot finish cannot be trusted to
    have written what it claims."""
    import io as _io
    import contextlib as _c
    buf = _io.StringIO()
    with _c.redirect_stdout(buf):
        IL.main()
    out = buf.getvalue()
    assert "P_pad_VDD" in out and "PAD_DROP" in out
    assert "P_pkg_RDL_HV_supply" in out
    for a in ("Z1", "Z2"):
        assert f"=== {a}" in out
