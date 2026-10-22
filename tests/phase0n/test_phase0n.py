"""Phase 0N --- physical-stack, topology and terminology guards.

Every hard guard is negative-tested: the failure it exists to catch is injected with the
REAL offending value or text and the guard must fire.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0m", "scripts/phase0i", "scripts/phase0h",
          "scripts/phase0g", "scripts/phase0f", "scripts/phase0e", "scripts/phase0dr",
          "scripts/phase0b", "scripts/phase0d", "scripts"):
    sys.path.insert(0, str(R / p))

AUDIT = R / "research" / "PHYSICAL_ARCHITECTURE_AUDIT_Z1_Z2.md"
TERMS = R / "research" / "VPD_DVPD_TERMINOLOGY_AUDIT.md"
PHASES = R / "research" / "HVR_PHASE_COUNT_AUDIT.md"
RECON = R / "research" / "phase0n" / "stack_reconstruction.json"
EXPT = R / "research" / "phase0n" / "conv_extent_experiment.json"
TEX = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
GEOM = R / "configs" / "phase0mr2" / "architecture_geometry.yaml"


# ----------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def recon():
    assert RECON.exists(), "run scripts/phase0n_reconstruct_stack.py first"
    return json.loads(RECON.read_text())


@pytest.fixture(scope="module")
def design():
    import kw1
    d, _g, why = kw1.design_1kw()
    assert d is not None, why
    return d


def layers(rec, tag):
    """Distinct (layer, z0, z1) bands, bottom-up."""
    seen, out = set(), []
    for L in rec[tag]["layers"]:
        k = (L["layer"], L["z0_mm"], L["z1_mm"])
        if k not in seen:
            seen.add(k); out.append(L)
    return sorted(out, key=lambda L: L["z0_mm"])


# ============================================================ STACK CLOSURE
def test_z1_substrate_closes_exactly(recon):
    """74 um TSV span + 1226 um embedded cell == the 1300 um substrate."""
    bands = {L["layer"]: L for L in layers(recon, "Z1")}
    tsv_t = bands["sub_lower"]["t_um"]
    cell_t = bands["tile_band"]["t_um"]
    h_sub = recon["Z1"]["h_sub_mm"] * 1e3
    assert tsv_t + cell_t == pytest.approx(h_sub, abs=1e-6), (
        f"Z1 substrate does not close: {tsv_t} + {cell_t} != {h_sub}")


def test_z1_substrate_closure_negative(recon):
    """NEGATIVE: the real pre-audit misreading -- a 1921 um cell in a 1300 um substrate."""
    h_sub = recon["Z1"]["h_sub_mm"] * 1e3
    bad_cell = 1921.0                      # the manuscript's "converter stack height"
    tsv_t = 74.0
    assert tsv_t + bad_cell != pytest.approx(h_sub, abs=1e-6)
    assert bad_cell > h_sub, "the guard must see 1921 um as not fitting in 1300 um"


def test_layers_are_ordered_and_non_overlapping(recon):
    for tag in ("Z1", "Z2"):
        bands = layers(recon, tag)
        for a, b in zip(bands, bands[1:]):
            assert a["z1_mm"] == pytest.approx(b["z0_mm"], abs=1e-9), (
                f"{tag}: gap or overlap between {a['layer']} (top {a['z1_mm']}) "
                f"and {b['layer']} (bottom {b['z0_mm']})")
            assert a["z1_mm"] > a["z0_mm"], f"{tag}: {a['layer']} has non-positive height"


def test_layers_non_overlap_negative():
    """NEGATIVE: an overlapping pair must be rejected."""
    bands = [{"layer": "bga", "z0_mm": -1.526, "z1_mm": -1.226},
             {"layer": "conv", "z0_mm": -1.300, "z1_mm": 0.0}]   # overlaps by 74 um
    with pytest.raises(AssertionError):
        for a, b in zip(bands, bands[1:]):
            assert a["z1_mm"] == pytest.approx(b["z0_mm"], abs=1e-9)


def test_substrate_datum_is_zero(recon):
    """z = 0 is the substrate underside in BOTH architectures."""
    for tag in ("Z1", "Z2"):
        sub = [L for L in layers(recon, tag) if L["layer"] == "sub_lower"][0]
        assert sub["z0_mm"] == pytest.approx(0.0, abs=1e-9), (
            f"{tag}: substrate underside is not the z = 0 datum")


# ====================================================== Z2 BOARD CLEARANCE
def test_z2_converter_does_not_intersect_pcb(recon):
    bands = {L["layer"]: L for L in layers(recon, "Z2")}
    assert bands["conv"]["z0_mm"] >= bands["bga"]["z1_mm"] - 1e-9
    assert bands["bga"]["z0_mm"] >= bands["board"]["z1_mm"] - 1e-9


def test_z2_backside_protrusion_exceeds_sourced_bga(recon):
    """The clearance Z2 actually needs, and does not have.

    Read as the manuscript describes it -- discrete cells on the underside with a
    surrounding BGA field -- the sourced 300 um ball cannot clear a 1226 um cell.
    This guard PINS that shortfall so it cannot be quietly forgotten.
    """
    import board as BRD
    bands = {L["layer"]: L for L in layers(recon, "Z2")}
    cell_um = bands["conv"]["t_um"]
    ball_um = BRD.BALL_H_MM * 1e3
    shortfall = cell_um - ball_um
    assert ball_um == pytest.approx(300.0), "sourced BGA height changed"
    assert shortfall > 0, (
        "If the backside cell ever becomes shorter than the ball, revisit "
        "research/PHYSICAL_ARCHITECTURE_AUDIT_Z1_Z2.md section 5")
    assert shortfall == pytest.approx(926.0, abs=1.0), (
        f"backside protrusion shortfall moved to {shortfall:.1f} um; the audit "
        f"documents 926 um and must be updated with it")


def test_no_cavity_is_silently_introduced(recon):
    """No layer may claim to be a cavity/standoff: none is sourced."""
    for tag in ("Z1", "Z2"):
        for L in layers(recon, tag):
            assert not re.search(r"cavit|standoff|clearance", L["layer"], re.I), (
                f"{tag}: layer {L['layer']!r} implies a cavity, which no source supports")


def test_clearance_ledger_still_declares_the_open_items():
    cfg = yaml.safe_load((R / "configs/phase0mr2/package_clearances.yaml").read_text())
    for k in ("die_to_component_gap_um", "cavity_sidewall_um", "cooler_standoff_um"):
        assert cfg["clearances"][k]["sourcing"] == "OPEN", f"{k} silently became sourced"


# ============================================== CONVERTER LATERAL EXTENT
def test_converter_volume_asymmetry_is_recorded(recon):
    """Z1 and Z2 do NOT carry the same converter volume. Pin it until it is fixed."""
    def conv_vol(tag, layer):
        return sum(L["vol_mm3"] for L in recon[tag]["layers"]
                   if L["layer"] == layer and L["material"] == "hvr_effective")
    z1 = conv_vol("Z1", "tile_band")
    z2 = conv_vol("Z2", "conv")
    assert z1 == pytest.approx(337.02, abs=0.5)
    assert z2 == pytest.approx(1103.40, abs=0.5)
    assert z2 / z1 == pytest.approx(3.27, abs=0.05), (
        "the Z1/Z2 converter-volume asymmetry changed; the frozen comparison is not "
        "placement-only and research/PHYSICAL_ARCHITECTURE_AUDIT_Z1_Z2.md section 6 "
        "must be updated")


def test_conv_fill_option_restores_symmetry():
    """With the correction the two architectures carry IDENTICAL converter volume."""
    import os
    import production_et as PE
    os.environ["PHASE0N_Z2_CONV_FILL"] = "underfill_homog"
    try:
        m, _mats, _st, _tiles = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
    finally:
        os.environ.pop("PHASE0N_Z2_CONV_FILL", None)
    V = m.elem_volumes()
    vol = sum(V[i] for i, (lay, mat) in
              enumerate(zip(m.elem_layer, m.elem_material))
              if lay == "conv" and mat == "hvr_effective")
    assert vol == pytest.approx(337.02, abs=0.5), (
        f"corrected Z2 converter volume {vol:.2f} mm3 != Z1's 337.02 mm3")


def test_default_build_is_unchanged():
    """The audit instrumentation must not perturb the frozen geometry."""
    import os
    import production_et as PE
    assert "PHASE0N_Z2_CONV_FILL" not in os.environ
    m, _mats, _st, _tiles = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
    V = m.elem_volumes()
    vol = sum(V[i] for i, (lay, mat) in
              enumerate(zip(m.elem_layer, m.elem_material))
              if lay == "conv" and mat == "hvr_effective")
    assert vol == pytest.approx(1103.40, abs=0.5), (
        "the default (frozen) backside converter is no longer full-area")


# ============================================================== TOPOLOGY
# Phase 0N-R. The earlier guards here asserted "K = buck phase count", which is WRONG.
# K counts PARALLEL INDUCTOR BRANCHES; the buck stage has TWO switching phases, with
# K_A branches driven in phase A and K - K_A freewheeling. See
# research/HVR_PHASE_COUNT_AUDIT.md.
N_SWITCHING_PHASES = 2


def test_K_is_the_branch_count_not_the_phase_count(design):
    """K multiplies LS devices and inductors -- hardware, not time."""
    from HVR_FULL_OPT_EPC_V2 import compute_component_count
    a = design.arch
    cc = compute_component_count(a.N, a.K, 1, 1, 1, 1)
    assert cc == a.component_count == a.N + 2 * a.K + (a.N - 1)
    assert a.K == 3 and a.N == 3 and a.K_A == 2
    # K is NOT the number of switching phases
    assert a.K != N_SWITCHING_PHASES, (
        "K coincided with the phase count; the distinction this guard protects is "
        "that they are different quantities")


def test_component_count_cannot_distinguish_phases_negative(design):
    """NEGATIVE: the component-count identity holds for ANY phase count, so it can
    never be evidence about phases. Re-deriving it must not resurrect the old claim."""
    from HVR_FULL_OPT_EPC_V2 import compute_component_count
    a = design.arch
    base = compute_component_count(a.N, a.K, 1, 1, 1, 1)
    # the identity is blind to how the K branches are grouped in time
    for hypothetical_phase_count in (2, 3, 5, 7):
        assert compute_component_count(a.N, a.K, 1, 1, 1, 1) == base, (
            "component count varied with an assumed phase count, which it cannot do")


def test_two_switching_phases_from_the_ripple_equation(design):
    """The ripple expression IS K_A driven + (K - K_A) freewheeling. Two states."""
    a = design.arch
    N, K, KA, D = a.N, a.K, a.K_A, a.D
    L = design.inductor.l_nh * 1e-9
    f = design.f_sw_hz
    v_mid = design.v_in / N
    code = (D / (f * L)) * (design.v_in / N * KA - design.v_out * K)
    driven = KA * (v_mid - design.v_out)          # phase-A branches on the mid rail
    free = (K - KA) * (-design.v_out)             # the rest freewheel
    recon = (driven + free) / L * (D / f)
    assert code == pytest.approx(recon, rel=1e-12), (
        "the ripple equation no longer decomposes into K_A driven + (K-K_A) "
        "freewheeling; the two-phase reading in HVR_PHASE_COUNT_AUDIT.md is stale")


def test_phase_group_sizes(design):
    a = design.arch
    assert a.K_A == 2, "phase-A branch count changed"
    assert a.K - a.K_A == 1, "phase-B branch count changed"


def test_K_B_is_K_minus_K_A_in_the_generator():
    src = (R / "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py").read_text()
    assert re.search(r"K_B\s*=\s*K\s*-\s*K_A", src), (
        "generate_B_array no longer defines K_B = K - K_A")


def test_sc_branches_split_ceil_floor_between_the_two_groups():
    """The N SC branches are split ceil(N/2) / floor(N/2) -- a TWO-group split."""
    import math
    from HVR_FULL_OPT_EPC_V2 import generate_B_array, distribute_branches
    for N, K, KA in ((3, 3, 2), (4, 3, 2), (5, 3, 2), (6, 4, 2)):
        B = generate_B_array(N, K, KA)
        assert len(B) == K, f"B_array length must equal the branch count K for N={N}"
        assert sum(B) == N, (
            f"sum(B) must equal N (every SC branch lands on one inductor); "
            f"N={N} K={K} gave {sum(B)}")
        assert sorted(distribute_branches(math.ceil(N / 2), KA)
                      + distribute_branches(math.floor(N / 2), K - KA)) == sorted(B)


def test_K_A_is_a_search_restriction_not_a_topology_property():
    """generate_B_array accepts any K_A; only the SEARCH fixes K_A = ceil(K/2)."""
    import math
    from HVR_FULL_OPT_EPC_V2 import generate_B_array
    free = generate_B_array(6, 4, 1)          # K_A = 1, not ceil(4/2) = 2
    assert sum(free) == 6 and len(free) == 4, (
        "the formulation no longer accepts a free K_A; update the audit's section 6")
    src = (R / "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py").read_text()
    assert re.search(r"K_A\s*=\s*math\.ceil\(K\s*/\s*2\)", src), (
        "the search no longer fixes K_A = ceil(K/2); the audit says it does")


def test_branch_current_is_I_over_sum_B_not_I_over_K(design):
    """6.8027 A is a BRANCH current, I_cell*B_i/N -- equal to I/K only by coincidence."""
    a = design.arch
    i_branch = design.i_out_a * a.B_array[0] / sum(a.B_array)
    assert i_branch == pytest.approx(6.8027, abs=1e-3)
    assert sum(a.B_array) == a.N
    assert i_branch < design.ls.ID_A, (
        f"branch current {i_branch:.3f} A exceeds the {design.ls.part_number} "
        f"{design.ls.ID_A} A rating")
    # and the two formulas must be shown to diverge in general
    from HVR_FULL_OPT_EPC_V2 import generate_B_array
    B = generate_B_array(4, 3, 2)                     # [1, 2, 1]
    cur = [design.i_out_a * b / sum(B) for b in B]
    assert len({round(c, 6) for c in cur}) > 1, (
        "branch currents are equal for N=4,K=3; the counterexample in the audit is void")
    assert not any(c == pytest.approx(design.i_out_a / 3, abs=1e-6) for c in cur), (
        "a branch happened to carry I/K; pick a different counterexample")


def test_duty_ratio_follows_N(design):
    a = design.arch
    assert a.D == pytest.approx(design.v_out * a.N / design.v_in)


def test_no_interleaving_is_modelled():
    """No phase-shift construct exists, so 'interleaved' may not be claimed."""
    src = (R / "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for pat in (r"phase_shift", r"phase_offset", r"dead_?time", r"interleav"):
        assert not re.search(pat, code, re.I), (
            f"{pat!r} now appears in code -- re-audit "
            f"research/HVR_PHASE_COUNT_AUDIT.md section 9")


def test_baseline_AR_depends_on_the_low_side_height():
    """The 5.05 headline is device-height dependent; pin the corrected 5.32."""
    import sys as _s
    _s.path.insert(0, str(R / "presentations/SK_hynix_2026/SK_HYNIX_HVR_TRANSIENT_ETM_2026_SOURCE"))
    import sources as S
    base = S.NETS["baseline_T1"]["hs_to_cf"]
    assert base["depth"] == pytest.approx(606.0), "baseline hs_to_cf no longer crosses the LS tier"
    assert base["ar"] == pytest.approx(5.05, abs=1e-3)
    d_via = base["depth"] / base["ar"]
    assert d_via == pytest.approx(120.0, abs=0.5)
    assert 638.0 / d_via == pytest.approx(5.317, abs=2e-3), (
        "the corrected baseline AR moved; update research/DEVICE_GEOMETRY_AUDIT.md")
    # the repartitioned value must NOT move: it crosses the 100 um capacitor tier
    rep = S.NETS["repartition_C1"]["hs_to_ls"]
    assert rep["depth"] == pytest.approx(100.0) and rep["ar"] == pytest.approx(0.833, abs=1e-3)


# ================================================== Z2-CUTOUT CANDIDATE
Z2GEO = R / "research" / "phase0nr" / "z2_cutout_geometry.json"
Z2DOC = R / "research" / "Z2_CUTOUT_GEOMETRY.md"


@pytest.fixture(scope="module")
def z2():
    assert Z2GEO.exists(), "run scripts/phase0nr_z2_cutout_geometry.py first"
    return json.loads(Z2GEO.read_text())


def test_z2_stack_includes_the_high_side(z2):
    """Z2 has no bottom substrate, so it cannot offload the HS. 1258 um is incomplete."""
    names = [L["layer"] for L in z2["stack"]]
    assert any("HS GaN" in n for n in names), "the Z2 cell stack lost its high-side device"
    hs = next(L["t_um"] for L in z2["stack"] if "HS GaN" in L["layer"])
    assert hs == 685.0
    assert z2["four_tier_um"] == pytest.approx(1953.0), "four-tier stack is not 1953 um"
    assert z2["serial_um"] == pytest.approx(1963.0)


def test_1258_is_never_used_as_the_z2_total():
    """The embedded-cell quantity may not stand in for the Z2 backside protrusion."""
    for p_ in (Z2DOC, R / "research" / "Z1_Z2_PACKAGE_CONSTRUCTIONS.md"):
        t = p_.read_text()
        for m in re.finditer(r"1258", t):
            w = t[max(0, m.start() - 420): m.end() + 420]
            assert re.search(r"wrong|exclud\w*|embedded[- ]cell|CORRECTION|incomplete",
                             w, re.I), (
                f"{p_.name}: 1258 um used near offset {m.start()} without saying it "
                f"excludes the high-side device")


def test_z2_height_closure_arithmetic(z2):
    assert z2["bga_h_um"] == pytest.approx(300.0), "sourced BGA height changed"
    assert z2["pcb_um"] == pytest.approx(1600.0), "PCB assumption changed"
    assert z2["cutout_depth_um"] == pytest.approx(1900.0)
    assert z2["protrusion_um"] == pytest.approx(63.0, abs=1.0), (
        "the cutout closure moved; update research/Z2_CUTOUT_GEOMETRY.md")
    # without a cutout the shortfall must be the FULL stack minus the ball
    assert z2["serial_um"] - z2["bga_h_um"] == pytest.approx(1663.0, abs=1.0)


def test_z2_cutout_removes_bga_sites_but_keeps_enough_for_power(z2):
    for o in z2["cutout_options"]:
        assert o["bga_sites"] < z2["bga_sites_full"], "the cutout removed no BGA sites"
    worst = min(o["bga_sites"] for o in z2["cutout_options"])
    need = 2 * z2["balls_needed_conservative"]
    assert need < worst, (
        f"power+return needs {need} balls but only {worst} sites remain")
    assert z2["balls_needed_conservative"] == 16 and z2["balls_needed_jdesign"] == 2


def test_z2_cells_are_resolved_laterally(z2):
    assert z2["n_cells"] == 49
    area = z2["n_cells"] * z2["cell_side_mm"] ** 2
    assert area == pytest.approx(274.89, abs=0.1), "cell inventory changed"
    bbox = z2["grid_bbox_mm"][0] * z2["grid_bbox_mm"][1]
    assert area < bbox, "cells fill their whole bbox -- that is a full-area layer again"


def test_z2_lateral_offset_is_small_but_recorded(z2):
    assert z2["lateral_offset_max_mm"] == pytest.approx(0.123, abs=5e-3)
    assert z2["lateral_offset_max_mm"] * 1e3 < 0.1 * z2["serial_um"], (
        "residual LV lateral run exceeded 10 % of the vertical stack; re-evaluate "
        "Xu 2019's pin-misalignment caution for this geometry")


def test_z2_is_not_called_a_pmic_or_a_cavity():
    for name in ("Z2_CUTOUT_SOURCE_AUDIT.md", "Z2_CUTOUT_GEOMETRY.md",
                 "Z2_CUTOUT_BGA_POWER_RETURN.md", "Z2_CUTOUT_THERMOMECH_PLAN.md"):
        t = (R / "research" / name).read_text()
        for m in re.finditer(r"PMIC", t, re.I):
            w = t[max(0, m.start() - 200): m.end() + 200]
            assert re.search(r"not|never|reject", w, re.I), (
                f"{name}: PMIC asserted rather than rejected")


def test_patents_are_never_called_demonstrated():
    t = (R / "research" / "Z2_CUTOUT_SOURCE_AUDIT.md").read_text()
    assert "patent" in t.lower()
    assert re.search(r"not demonstrated|industry construction precedent|not hardware",
                     t, re.I), "the patent/hardware distinction was dropped"
    assert re.search(r"neither patent gives", t, re.I), (
        "the 'no dimensions in either patent' limit was dropped")


def test_no_new_pair_frozen_before_closure():
    """Task G gate: no corrected ETM pair may be frozen while closure is open."""
    assert not (R / "results" / "phase0nr").exists(), (
        "a Phase-0N-R results directory appeared; closure gates are still open")
    t = (R / "research" / "Z2_CUTOUT_GEOMETRY.md").read_text()
    assert re.search(r"not yet closed|still open|plausible, not yet closed", t, re.I)


# ============================================ Z1 CANDIDATE PACKAGE CLOSURE
CONSTR = R / "research" / "Z1_Z2_PACKAGE_CONSTRUCTIONS.md"


def _candidate_rows():
    rows = []
    for line in CONSTR.read_text().splitlines():
        if re.match(r"^\| *\d+ *\|", line):
            c = [x.strip() for x in line.split("|")]
            rows.append((c[2], float(c[3]), c[4]))
    return rows


def test_z1_candidate_is_contiguous_and_closes():
    rows = _candidate_rows()
    assert len(rows) == 15, f"candidate layer count changed: {len(rows)}"
    z = -1600.0
    for name, t, span in rows:
        lo, hi = [float(x) for x in span.replace("−", "-").split("→")]
        assert lo == pytest.approx(z, abs=1e-6), f"{name}: gap/overlap at {lo} vs {z}"
        assert hi - lo == pytest.approx(t, abs=1e-6), f"{name}: thickness mismatch"
        assert t > 0, f"{name}: non-positive thickness"
        z = hi
    assert z == pytest.approx(2933.0), f"candidate top is {z}, audit says 2933 um"


def test_z1_candidate_contains_the_high_side():
    """The whole point: unlike the frozen Z1, the candidate HAS a high-side device."""
    names = [n for n, _t, _s in _candidate_rows()]
    assert any("HS GaN" in n for n in names), "the candidate lost its high-side device"
    hs = next(t for n, t, _ in _candidate_rows() if "HS GaN" in n)
    ls = next(t for n, t, _ in _candidate_rows() if "LS GaN" in n)
    assert hs == 685.0 and ls == 638.0, "candidate does not use the selected-device heights"


def test_z1_candidate_does_not_interfere_with_the_bga():
    rows = _candidate_rows()
    bga = next(r for r in rows if "BGA" in r[0])
    hs = next(r for r in rows if "HS GaN" in r[0])
    bga_hi = float(bga[2].replace("−", "-").split("→")[1])
    hs_lo = float(hs[2].replace("−", "-").split("→")[0])
    assert hs_lo >= bga_hi, (
        "the high-side device re-entered the ball gap; the frozen Z1's 385 um "
        "interference is supposed to be resolved in the candidate")


def test_z2_candidate_is_source_classified_and_still_open():
    """Phase 0N-R: a Z2 candidate now EXISTS. It must carry its evidence class and
    must not be declared closed."""
    t = CONSTR.read_text()
    assert "Z2-CUTOUT" in t or "Z2_CUTOUT" in t, "the Z2 candidate vanished"
    assert re.search(r"patent-precedented|patent precedent", t, re.I), (
        "the Z2 candidate no longer states that the cutout is patent-precedented")
    assert re.search(r"still not closed|not yet closed", t, re.I), (
        "Z2 was declared closed; the protrusion, attach stack, sidewall clearance and "
        "return geometry are all still open")
    assert "1653" in t, "the corrected no-cutout shortfall is no longer stated"
    # and the superseded figure must be marked as such wherever it survives
    assert re.search(r"958.{0,80}(wrong|were wrong)", t, re.I) or \
           re.search(r"(wrong|CORRECTION).{0,200}958", t, re.I | re.S), (
        "the withdrawn 958 um figure is present without being marked wrong")


# ===================================================== SELECTED-DEVICE GEOMETRY
def test_device_heights_match_the_selected_parts(design):
    """The geometry must use the heights of the devices the electrical model picks."""
    import yaml
    cfg = yaml.safe_load((R / "configs/phase0nr/device_geometry.yaml").read_text())
    assert cfg["devices"]["high_side"]["part"] == design.hs.part_number == "EPC2014C"
    assert cfg["devices"]["low_side"]["part"] == design.ls.part_number == "EPC2057"
    assert cfg["devices"]["high_side"]["height_um"]["nominal"] == 685.0
    assert cfg["devices"]["low_side"]["height_um"]["nominal"] == 638.0


def test_low_side_height_is_die_plus_bump():
    import yaml
    d = yaml.safe_load((R / "configs/phase0nr/device_geometry.yaml").read_text())
    ls = d["devices"]["low_side"]
    assert (ls["die_thickness_um"]["nominal"] + ls["terminal_um"]["nominal"]
            == ls["height_um"]["nominal"]), "EPC2057 638 um must equal 518 + 120"


def test_corrected_geometry_is_opt_in_and_default_is_frozen():
    """Default must reproduce the frozen cell; the flag must give the corrected one."""
    import importlib, os, sys
    sys.path.insert(0, str(R / "scripts" / "phase0i"))
    os.environ.pop("PHASE0NR_DEVICE_GEOM", None)
    import zarch
    importlib.reload(zarch)
    assert zarch.embedded_cell_um() == pytest.approx(1226.0), "frozen default drifted"
    os.environ["PHASE0NR_DEVICE_GEOM"] = "selected"
    try:
        importlib.reload(zarch)
        assert zarch.embedded_cell_um() == pytest.approx(1258.0)
        r = zarch.realizable("ARCH_Z1_EMBEDDED", 1.30)
        assert not r.feasible, (
            "Z1 at 1.30 mm became feasible with the corrected low-side height; "
            "research/DEVICE_GEOMETRY_AUDIT.md says it is 8 um short")
        assert r.h_sub_min_um == pytest.approx(1308.0)
        assert zarch.realizable("ARCH_Z1_EMBEDDED", 1.308).feasible
    finally:
        os.environ.pop("PHASE0NR_DEVICE_GEOM", None)
        importlib.reload(zarch)
    assert zarch.embedded_cell_um() == pytest.approx(1226.0), "flag leaked"


# =================================================== CONNECTIVITY CONTINUITY
def test_power_path_is_continuous(design):
    """PCB -> 48 V -> converter -> 1 V -> die, with a return accounted for."""
    import zarch as ZA
    for arch, hv_first in (("ARCH_Z1_EMBEDDED", True), ("ARCH_Z2_BACKSIDE", True)):
        segs = ZA.path_for(arch, 1000.0)
        tiers = [s.tier for s in segs]
        assert tiers[0] == "bga", f"{arch}: path does not start at the board"
        assert "converter" in tiers, f"{arch}: no conversion segment"
        assert tiers[-1] == "rdl", f"{arch}: path does not end under the die"
        ci = tiers.index("converter")
        assert all(s.rail == "HV" for s in segs[:ci]), f"{arch}: pre-conversion rail is not HV"
        assert all(s.rail == "LV" for s in segs[ci + 1:]), f"{arch}: post-conversion rail is not LV"
        assert segs[ci].v_volt == pytest.approx(48.0)


def test_return_is_accounted_as_a_loop_factor():
    """There is no return GEOMETRY; the model uses R_loop = 2 * R_field. Pin that."""
    src = (R / "scripts/phase0mr/replay_production.py").read_text()
    assert '"R_loop_ohm": 2 * r_field' in src, (
        "the loop-resistance convention changed; the audit states return is accounted "
        "as a factor of two and has no geometry")


def test_z1_high_side_has_no_geometry(recon):
    """The 685 um high-side device is NOT in the Z1 mesh. Pin it until it is."""
    names = {L["layer"] for L in recon["Z1"]["layers"]}
    assert not any("hs" in n or "gan" in n for n in names), (
        "a high-side layer appeared in Z1 -- the audit's section 3 finding is stale "
        "and the 695 um deficit may now be closed")
    below = [L for L in layers(recon, "Z1") if L["z1_mm"] <= 0.0]
    assert {L["layer"] for L in below} == {"board", "bga"}, (
        f"Z1 below z=0 is {[L['layer'] for L in below]}; the audit records board+bga only")


# ============================================================ TERMINOLOGY
BAD_TOPOLOGY_WORDING = [
    (r"3-phase buck", "the buck stage is two-phase with K=3 branches"),
    (r"three-phase buck", "the buck stage is two-phase with K=3 branches"),
    (r"phase count \$?K", "K is the branch count, not the phase count"),
    (r"per-phase (?:inductor )?current", "I_cell*B_i/N is a BRANCH current"),
    (r"auxiliary-branch count", "K_A is the phase-A branch count"),
]


@pytest.mark.parametrize("pat,why", BAD_TOPOLOGY_WORDING)
def test_manuscript_topology_wording(pat, why):
    assert not re.search(pat, TEX.read_text(), re.I), f"{pat!r}: {why}"


@pytest.mark.parametrize("pat,why", BAD_TOPOLOGY_WORDING)
def test_manuscript_topology_wording_negative(pat, why):
    """NEGATIVE: each probe is the real pre-correction wording."""
    real = ("Topology 3:1 SC + 3-phase buck. The search enumerates hybrid architectures "
            "over the stage count $N$, the phase count $K$, the auxiliary-branch count "
            "$K_{A}$. The per-phase inductor current ripple, with a three-phase buck "
            "stage, is")
    assert re.search(pat, real, re.I), (
        f"the negative fixture no longer exercises {pat!r}")


def test_repo_docs_use_the_corrected_topology():
    """README / CURRENT_STATUS must not carry the withdrawn 3-phase wording."""
    for name in ("README.md", "CURRENT_STATUS.md"):
        t = (R / name).read_text()
        assert not re.search(r"3-phase buck|three-phase buck", t, re.I), (
            f"{name} still says 3-phase buck")
        assert re.search(r"two-phase", t, re.I), (
            f"{name} does not state the corrected two-phase topology")


def test_phase_audit_records_the_correction():
    t = (R / "research" / "HVR_PHASE_COUNT_AUDIT.md").read_text()
    assert "supersedes" in t and "WRONG" in t, (
        "the topology audit no longer records that the earlier conclusion was wrong")
    assert "two-phase" in t.lower()


_NEG = re.compile(r"\b(no|not|never|cannot|neither|nor|without|non-)\b", re.I)


def _clause(text, pos):
    lo = max(text.rfind(".", 0, pos), text.rfind(";", 0, pos),
             text.rfind("\n\n", 0, pos)) + 1
    m = re.compile(r"[^.;!?]*").match(text, pos)
    return text[lo:(m.end() if m else len(text))]


def _interleaving_claims(text):
    """Occurrences of 'interleav' that are ASSERTED rather than denied."""
    return [m.group(0) for m in re.finditer(r"interleav\w*", text, re.I)
            if not _NEG.search(_clause(text, m.start()))]


def test_manuscript_does_not_claim_interleaving():
    """A denial ('no claim of interleaving is made') is allowed; an assertion is not."""
    bad = _interleaving_claims(TEX.read_text())
    assert not bad, f"the manuscript asserts interleaving, which is not modelled: {bad}"


@pytest.mark.parametrize("injected", [
    r"Topology 3:1 SC + 3-phase interleaved buck",
    r"The two phases are interleaved at 180 degrees.",
])
def test_manuscript_interleaving_negative(injected):
    """NEGATIVE: real offending phrasings must be caught, denials must not."""
    assert _interleaving_claims(injected), f"guard went blind to {injected!r}"
    assert not _interleaving_claims(
        "The implementation contains no time-domain model, so no claim of "
        "interleaving is made."), "guard now rejects a legitimate denial"


def test_manuscript_does_not_put_1921_inside_the_substrate():
    """The pre-audit defect: '1921 um converter' + 'built into the 1.30 mm substrate'."""
    tex = TEX.read_text()
    for m in re.finditer(r"built into the \$?1\.30\\?,?\\?\s*mm\$?\\?,?\s*substrate", tex):
        window = tex[max(0, m.start() - 400): m.end() + 400]
        assert "1921" not in window, (
            "the manuscript again places the 1921 um converter stack inside the "
            "1.30 mm substrate; only 1226 um is embedded")


def test_manuscript_states_the_embedded_split():
    """Positive guard: the corrected split must be present, not merely the defect absent."""
    tex = TEX.read_text()
    assert "1226" in tex, "the manuscript no longer states what is actually embedded"
    assert re.search(r"outside the modelled domain", tex), (
        "the manuscript no longer discloses that the high-side device is unmodelled")
    assert re.search(r"sec:backside-limit", tex), (
        "the backside lateral-extent limitation section was removed")


def test_manuscript_does_not_assert_the_temperature_ordering():
    """The +8.14 K ordering was withdrawn; it may be reported only as conditional."""
    tex = TEX.read_text()
    for m in re.finditer(r"8\.14", tex):
        w = tex[max(0, m.start() - 320): m.end() + 320]
        assert re.search(r"condition|not established|bracket|frozen representation|"
                         r"reverses|changes sign", w, re.I), (
            "an unqualified 8.14 K claim reappeared at offset "
            f"{m.start()}; it must be reported as conditional")


def test_manuscript_1921_claim_negative():
    """NEGATIVE: the real offending sentence from the pre-audit Fig. 2 caption."""
    offending = (r"the converter cells are built into the $1.30$\,mm substrate and the "
                 r"through-substrate field carries the 48\,V input rail. Converter stack "
                 r"height 1921\,\textmu m")
    hits = [m for m in re.finditer(r"built into the \$?1\.30\$?\\?,?\s*mm substrate", offending)]
    assert hits, "the negative fixture no longer matches the guard's pattern"
    window = offending[max(0, hits[0].start() - 400): hits[0].end() + 400]
    assert "1921" in window, "the guard would not have caught the real defect"


def test_vpd_dvpd_wording_is_not_the_simplification():
    """'VPD is far, DVPD is near' is refuted by two sources held in full."""
    tex = TEX.read_text()
    bad = re.compile(r"VPD[^.]{0,120}\bfar from\b[^.]{0,120}load", re.I)
    assert not bad.search(tex), (
        "the manuscript describes VPD as placing conversion far from the load; see "
        "research/VPD_DVPD_TERMINOLOGY_AUDIT.md")


def test_audit_documents_exist_and_state_a_verdict():
    for p in (AUDIT, TERMS, PHASES):
        assert p.exists(), f"missing {p.name}"
        assert len(p.read_text()) > 2000, f"{p.name} is a stub"
    assert "physically inconsistent as currently" in AUDIT.read_text()


def test_experiment_shows_the_result_is_conditional():
    """The recorded sensitivity must not be quietly dropped."""
    rows = {r["variant"]: r for r in json.loads(EXPT.read_text())}
    assert rows["Z2_frozen"]["D_u_vs_Z1"] == pytest.approx(1.1947, abs=5e-4)
    assert rows["Z2_frozen"]["dT_vs_Z1_K"] == pytest.approx(8.14, abs=0.02)
    # the correction must still be on record as changing the answer materially
    assert rows["Z2_cellonly_silicon"]["dT_vs_Z1_K"] < 0.0, (
        "the temperature-ordering reversal is no longer reproduced")
    spread = (rows["Z2_cellonly_underfill"]["du_reduction_pct_vs_Z1"]
              - rows["Z2_cellonly_silicon"]["du_reduction_pct_vs_Z1"])
    assert spread > 50.0, "the du_c magnitude spread collapsed; re-examine the audit"


def test_all_three_fills_preserve_the_ordering_direction():
    rows = json.loads(EXPT.read_text())
    for r in rows:
        if r["variant"] == "Z1":
            continue
        assert r["D_u_vs_Z1"] > 1.0, (
            f"{r['variant']}: ordering direction lost (D_u = {r['D_u_vs_Z1']})")


def test_geometry_config_matches_the_measured_mesh(recon):
    cfg = yaml.safe_load(GEOM.read_text())["architectures"]
    z1 = cfg["ARCH_Z1_EMBEDDED"]
    assert z1["converter_cell_um"] == pytest.approx(1226.0)
    assert z1["tsv_z_end_um"] == pytest.approx(74.0)
    bands = {L["layer"]: L for L in layers(recon, "Z1")}
    assert bands["sub_lower"]["t_um"] == pytest.approx(z1["tsv_z_end_um"], abs=1e-6)
    assert bands["tile_band"]["t_um"] == pytest.approx(z1["converter_cell_um"], abs=1e-6)
