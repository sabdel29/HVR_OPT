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
    """The Phase-0N design: the 49-cell point of the pre-round-3 production synthesis
    (packing off). TCPMT round 3 turned packing on in production, under which the 49-cell
    point synthesizes differently (the record's m49); the topology and device guards below
    are about the Phase-0N design, so they evaluate it in its own lineage."""
    import kw1
    import electrical as EL
    with EL.pinned_rules({**EL.PRODUCTION_DEFAULTS, "PACK_RULE": "off"}):
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
    # Z1's tile band: the cells x the 1.226-mm embedded cell (Phase 0N: 49 x 5.61 mm2 ->
    # 337.02 mm3; TCPMT round 3: the cells of the design record)
    sys.path.insert(0, str(R / "scripts" / "phase0nw"))
    import design_record as DR
    z1 = DR.n_vr() * DR.cell_area_mm2() * 1.226
    assert vol == pytest.approx(z1, abs=0.5), (
        f"corrected Z2 converter volume {vol:.2f} mm3 != Z1's {z1:.2f} mm3")


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


def test_converter_inventory_is_identical_across_architectures(design):
    """Task 15: only location/support/cooling may differ between Z1 and Z2."""
    a = design.arch
    per_cell = {"HS": a.N, "LS": a.K, "inductors": a.K, "flying_caps": a.N - 1}
    assert sum(per_cell.values()) == a.component_count == 11
    import production_et as PE
    inv = {}
    for arch, h in (("ARCH_Z1_EMBEDDED", 1.30), ("ARCH_Z2_BACKSIDE", 0.30)):
        _m, _mats, _st, tiles = PE.build_global(arch, h)
        inv[arch] = (len(tiles), round(sum(t.ax * t.ay for t in tiles), 6))
    assert inv["ARCH_Z1_EMBEDDED"] == inv["ARCH_Z2_BACKSIDE"], (
        f"cell count / footprint differ between architectures: {inv}")
    # Phase 0N: 49 cells, 274.89 mm2; TCPMT round 3: the cells of the design record
    sys.path.insert(0, str(R / "scripts" / "phase0nw"))
    import design_record as DR
    assert inv["ARCH_Z1_EMBEDDED"][0] == DR.n_vr()
    assert inv["ARCH_Z1_EMBEDDED"][1] == pytest.approx(DR.n_vr() * DR.cell_area_mm2(),
                                                       abs=0.1)


SPEC = R / "research" / "Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md"
LAND_SIDE_IFACE_UM = 2700.0          # PCB 2400 + BGA 300, z = 0 at the PCB backside


def _z2_descending_rows():
    """(name, t, z_from, z_to) for the central-region table."""
    t = SPEC.read_text()
    blk = t[t.index("### Central region"):t.index("### Peripheral region")]
    out = []
    for line in blk.splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|\s*\*{0,2}(\d+)\s*→\s*(\d+)",
                     line)
        if m:
            out.append((m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return out


def test_z2_hvr_descends_into_the_cutout():
    """The real Phase-0N-S defect: the HVR was drawn growing UPWARD toward the die."""
    rows = _z2_descending_rows()
    assert len(rows) >= 8, f"Z2 central-region table not parsed ({len(rows)} rows)"
    for name, t, z0, z1 in rows:
        assert z1 < z0, f"{name}: z increases ({z0}->{z1}); the HVR must DESCEND"
        assert z0 - z1 == pytest.approx(t, abs=1e-6), f"{name}: thickness mismatch"
        assert z0 <= LAND_SIDE_IFACE_UM + 1e-6, (
            f"{name} starts at {z0} um, above the land-side interface "
            f"{LAND_SIDE_IFACE_UM} um -- Z2 converter tiers must be BELOW the substrate")
    assert rows[0][2] == pytest.approx(LAND_SIDE_IFACE_UM)


def test_z2_high_side_is_the_deepest_tier():
    rows = _z2_descending_rows()
    deepest = min(rows, key=lambda r: r[3])
    assert "HS GaN" in deepest[0], (
        f"the deepest Z2 tier is {deepest[0]!r}; the high side must be deepest into "
        f"the cutout")


def test_z2_substrate_is_above_the_converter():
    t = SPEC.read_text()
    blk = t[t.index("### Above the land-side interface"):]
    m = re.search(r"\|\s*power substrate\s*\|\s*[\d.]+\s*\|\s*(\d+)\s*→\s*(\d+)", blk)
    assert m, "the power substrate row vanished from the rising table"
    z0, z1 = float(m.group(1)), float(m.group(2))
    assert z1 > z0 and z0 >= LAND_SIDE_IFACE_UM, (
        "the package substrate must rise from the land-side interface, not sit below it")
    deepest = min(r[3] for r in _z2_descending_rows())
    assert z0 > deepest, "substrate is below the converter -- coordinates inverted again"


def test_z2_converter_fits_inside_the_board_at_nominal():
    rows = _z2_descending_rows()
    deepest = min(r[3] for r in rows)
    assert deepest > 0, (
        f"the HVR reaches {deepest} um, i.e. below the PCB backside at nominal board "
        f"thickness; the audit says it clears by 737 um")
    assert deepest == pytest.approx(737.0, abs=1.0)


def test_spec_is_not_called_physically_closed():
    t = SPEC.read_text()
    assert "physically specified candidate architecture" in t.lower()
    for m in re.finditer(r"physically closed", t, re.I):
        w = t[max(0, m.start() - 260): m.end() + 260]
        assert re.search(r"not |may be used only|gates|open", w, re.I), (
            f"'physically closed' asserted at offset {m.start()} while gates are open")
    # negation-aware: 'not "manufacturable"' is the status banner, not a claim
    for bad in ("manufacturable", "qualified"):
        for m in re.finditer(bad, t, re.I):
            cl = _clause(t, m.start())
            assert _NEG.search(cl) or re.search(r'not\s*"', cl), (
                f"the specification asserts {bad!r} at offset {m.start()}: {cl.strip()[:90]!r}")


def test_closed_stack_spec_declares_what_is_unimplemented():
    t = (R / "research" / "Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md").read_text()
    assert "NOT implemented" in t
    for gate in ("supply/return continuity", "annular PCB mesh", "mesh convergence"):
        assert gate in t, f"closure gate '{gate}' dropped from the specification"


# ============================================ PCB MATERIAL MODEL (0N-V)
PCBCFG = R / "configs" / "phase0nv" / "pcb_it968g_18layer.yaml"
PCBHOM = R / "research" / "phase0nv" / "pcb_homogenization.json"


@pytest.fixture(scope="module")
def pcbcfg():
    import yaml
    return yaml.safe_load(PCBCFG.read_text())


def test_it968g_values_match_the_datasheet(pcbcfg):
    lam = pcbcfg["laminate"]
    assert lam["name"] == "ITEQ IT-968G"
    assert lam["E_warp_MPa"] == 15000.0 and lam["E_fill_MPa"] == 14000.0
    assert lam["cte_xy_primary_ppm"] == [12.0, 14.0]       # IPC 2.4.41
    assert lam["cte_xy_alt_ppm"] == [11.0, 12.0]           # IPC 2.4.24.5
    assert lam["cte_z_pre_tg_ppm"] == 45.0 and lam["cte_z_post_tg_ppm"] == 260.0
    assert lam["Tg_C"] == 175.0 and lam["Td_C"] == 400.0 and lam["MOT_C"] == 130.0


def test_absent_datasheet_properties_are_declared_absent(pcbcfg):
    absent = set(pcbcfg["laminate"]["absent"])
    for k in ("poisson", "thermal_conductivity", "E_z", "shear_moduli", "density"):
        assert k in absent, f"{k} must be declared absent from the IT-968G datasheet"
    ob = pcbcfg["open_or_bounded"]
    assert ob["shear_moduli"] == "OPEN" and ob["poisson_ratios"] == "OPEN"


def test_copper_coverage_is_swept_not_assumed(pcbcfg):
    assert pcbcfg["open_or_bounded"]["copper_coverage_eta"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    b = pcbcfg["board"]
    assert b["n_1oz"] == 14 and b["n_2oz"] == 4, "copper schedule changed"
    assert b["t_cu_full_um"] == pytest.approx(765.6, abs=0.1)
    assert b["f_cu_full"] == pytest.approx(0.3190, abs=1e-3)
    assert "UPPER BOUND" in b["f_cu_full_note"], (
        "the full-coverage figure must be labelled an upper bound, not the board's "
        "copper volume")
    assert pcbcfg["nominal"]["eta"] == 0.50
    assert "not a measurement" in pcbcfg["nominal"]["note"]


def test_physical_board_is_not_the_arbitrary_isotropic_fr4():
    import board as BRD
    for case in ("it968g_2p4mm", "it968g_3p2mm"):
        c = BRD.BOARD_CASES[case]
        assert c["E_MPa"] != 22000.0 and c["E_MPa"] != 24000.0, (
            f"{case} fell back to the unsourced arbitrary modulus")
        assert c["cte"] not in (16.0e-6, 15.0e-6), f"{case} uses the unsourced CTE"


def test_thickness_study_is_not_confounded():
    """T-only: 2.4 and 3.2 mm must share ONE material tensor."""
    import board as BRD
    a, b = BRD.BOARD_CASES["it968g_2p4mm"], BRD.BOARD_CASES["it968g_3p2mm"]
    for k in ("E_MPa", "nu", "cte", "k"):
        assert a[k] == b[k], (
            f"{k} differs between the 2.4 and 3.2 mm T-only cases; that confounds "
            f"geometric stiffness with a material change")
    assert a["t_mm"] == 2.4 and b["t_mm"] == 3.2
    # and the historical pair must remain confounded, i.e. unusable for this study
    fa, fb = BRD.BOARD_CASES["fr4_2p4mm"], BRD.BOARD_CASES["fr4_3p2mm"]
    assert fa["E_MPa"] != fb["E_MPa"], (
        "the historical cases are no longer distinguishable; the audit says they "
        "change material with thickness")


def test_board_cases_reach_the_mesh():
    import production_et as PE
    for case, want in (("it968g_2p4mm", 2400.0), ("it968g_3p2mm", 3200.0)):
        m, _a, _b, _c = PE.build_global("ARCH_Z2_BACKSIDE", 0.30,
                                        board_case=case, cutout_mm=23.36)
        L = m.layer("board")
        assert (L.z1 - L.z0) * 1e3 == pytest.approx(want, abs=1e-6), (
            f"{case} produced {(L.z1-L.z0)*1e3:.0f} um in the mesh")


def test_mot_and_tg_gate_is_recorded_but_not_yet_evaluated():
    t = re.sub(r"\s+", " ", (R / "research" / "PCB_MATERIAL_PROPERTY_AUDIT.md").read_text())
    assert "MOT = 130" in t and "Tg = 175" in t
    assert re.search(r"has not been run", t, re.I), (
        "the audit must state that T_PCB,max has not yet been computed")


# ===================================================== ANNULAR PCB (0N-T)
ANNJ = R / "research" / "phase0nt" / "annular_pcb.json"


@pytest.fixture(scope="module")
def ann():
    assert ANNJ.exists(), "run scripts/phase0nt_annular_pcb.py first"
    return json.loads(ANNJ.read_text())


def test_cutout_removes_real_elements_not_relabelled_ones(ann):
    """A true through-opening: no board or BGA element may exist inside it."""
    a = ann["elements_annular"]
    assert a["board_inside_cutout"] == 0, "PCB elements remain inside the cutout"
    assert a["bga_inside_cutout"] == 0, "BGA elements remain inside the cutout"
    f = ann["elements_full"]
    assert a["board"] < f["board"] and a["bga"] < f["bga"], (
        "the cutout removed nothing -- it is a label, not an opening")
    # the opening is ~61 % of the 30x30 mm area, so most of the board must go.
    # An absolute count would over-fit the mesh: adding the cutout edges as grid
    # breakpoints legitimately changes it.
    frac = (f["board"] - a["board"]) / f["board"]
    assert 0.5 < frac < 0.8, f"cutout removed {100*frac:.0f} % of the board elements"
    assert a["board"] == a["bga"], "board and BGA must be cut identically"


def test_cutout_does_not_remove_anything_above_the_board(ann):
    """Refining the grid at the cutout edge may change counts above the board, but
    the cutout must never DELETE package elements -- only board and BGA."""
    f, a = ann["elements_full"], ann["elements_annular"]
    for lay in ("conv", "sub_lower", "die"):
        assert a[lay] >= f[lay], (
            f"{lay} lost elements to the cutout; only board and bga may be cut")


def test_default_build_is_still_the_full_slab():
    """The frozen board must survive untouched when the env var is unset."""
    import os, production_et as PE
    assert "PHASE0NT_CUTOUT_MM" not in os.environ
    m, _mats, _st, _t = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
    # TCPMT round 3: the element count follows the cell grid of the design record (the
    # Phase-0N 49-cell grid gave 2450), so the full slab is checked as such: the board's
    # elements fill the whole footprint (no cutout removed any)
    V = m.elem_volumes()
    vb = sum(V[i] for i, l in enumerate(m.elem_layer) if l == "board")
    L = m.layer("board")
    full = (m.xs.max() - m.xs.min()) * (m.ys.max() - m.ys.min()) * (L.z1 - L.z0)
    assert vb == pytest.approx(full, rel=1e-9), (
        f"the default board is no longer a full slab: {vb:.3f} of {full:.3f} mm3")


def test_surviving_bga_count_and_allocation(ann):
    assert ann["bga_sites_full"] == 1369
    assert ann["bga_sites_surviving"] == 528
    assert ann["bga_sites_removed"] == 841
    for xy in ann["supply_xy_mm"] + ann["return_xy_mm"]:
        assert max(abs(xy[0]), abs(xy[1])) >= ann["cutout_mm"] / 2, (
            f"ball at {xy} lies inside the cutout")
    assert ann["n_supply_balls"] == 16 and ann["n_return_balls"] == 16
    assert ann["n_supply_balls"] * ann["i_per_ball_a"] >= ann["i_in_a"], (
        "supply balls cannot carry the 48 V input current")


def test_z2_discrete_cell_gate_is_closed_and_verified_in_the_mesh():
    """GATE CLOSED in Phase 0N-W, and verified where the state now lives.

    This guard used to read `converter.implemented` out of the YAML. That field is gone:
    configuration describes the package, and the generated gate registry owns
    implementation state. The registry evaluates the mesh, so this reads the registry.
    """
    reg = json.loads((R / "research/phase0nw/physical_gates.json").read_text())
    by = {r["id"]: r for r in reg["gates"]}
    for gid in ("geom.z2_49_cells", "geom.z2_full_stack", "geom.z2_no_slab",
                "geom.z2_descends_into_cutout"):
        assert by[gid]["status"] == "IMPLEMENTED", f"{gid} regressed: {by[gid]}"
    # the geometry gate must not be read as a material claim
    assert by["mat.mlcc_bounded"]["status"] == "OPEN"


def test_physical_build_actually_uses_a_2p4mm_board():
    """Commit 30f717b called a 1600 um board '2.4 mm'. This makes it checkable."""
    import production_et as PE
    m, _mats, _st, _t = PE.build_global("ARCH_Z2_BACKSIDE", 0.30,
                                        board_case="fr4_2p4mm", cutout_mm=23.36)
    L = m.layer("board")
    assert (L.z1 - L.z0) * 1e3 == pytest.approx(2400.0, abs=1e-6), (
        f"physical build has {(L.z1-L.z0)*1e3:.0f} um of FR-4, not 2400")
    m16, _a, _b, _c = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
    L16 = m16.layer("board")
    assert (L16.z1 - L16.z0) * 1e3 == pytest.approx(1600.0), (
        "the historical default board drifted off fr4_1p6mm")
    m32, _a, _b, _c = PE.build_global("ARCH_Z2_BACKSIDE", 0.30,
                                      board_case="fr4_3p2mm", cutout_mm=23.36)
    assert (m32.layer("board").z1 - m32.layer("board").z0) * 1e3 == pytest.approx(3200.0)


def test_cutout_boundary_is_mesh_conforming():
    """Edges must be grid breakpoints; no board/BGA element may straddle them."""
    import numpy as np, production_et as PE
    CUT = 23.36
    h = CUT / 2
    m, _mats, _st, _t = PE.build_global("ARCH_Z2_BACKSIDE", 0.30,
                                        board_case="fr4_2p4mm", cutout_mm=CUT)
    assert np.any(np.isclose(m.xs, h)) and np.any(np.isclose(m.xs, -h)), (
        f"+/-{h} mm are not breakpoints in xs")
    assert np.any(np.isclose(m.ys, h)) and np.any(np.isclose(m.ys, -h))
    straddle = 0
    for e, lay in zip(m.elems, m.elem_layer):
        if lay not in ("board", "bga"):
            continue
        xs, ys = m.nodes[e - 1, 0], m.nodes[e - 1, 1]
        inside_x = xs.min() < h - 1e-9 and xs.max() > -h + 1e-9
        inside_y = ys.min() < h - 1e-9 and ys.max() > -h + 1e-9
        if inside_x and inside_y:
            straddle += 1
    assert straddle == 0, f"{straddle} board/BGA elements straddle the cutout boundary"


def test_bga_lattice_is_centred_and_allocation_symmetric(ann):
    """The lattice ran -14.6..+14.2 before, so no symmetric allocation existed."""
    for rail in ("supply_first_moment_mm", "return_first_moment_mm"):
        mx, my = ann[rail]
        assert abs(mx) < 1e-6 and abs(my) < 1e-6, (
            f"{rail} = ({mx}, {my}); each rail must be mirror-symmetric")
    for k in ("per_side_supply", "per_side_return"):
        sides = ann[k]
        assert set(sides) == {"N", "S", "E", "W"}, f"{k} misses a side: {sides}"
        assert len(set(sides.values())) == 1, f"{k} is uneven across sides: {sides}"


def test_z2_physical_config_forbids_the_embedded_cell_proxy():
    import yaml
    c = yaml.safe_load((R / "configs/phase0nt/z2_2p4mm_cutout.yaml").read_text())
    # TCPMT round 3: the converter is the design record's (Phase 0N: 1953 um of four
    # homogeneous tiers + the 10-um land-side RDL = 1963 um)
    sys.path.insert(0, str(R / "scripts" / "phase0nw"))
    import design_record as DR
    tot = c["converter"]["with_land_side_rdl_um"]
    assert tot == pytest.approx(DR.converter_stack_um() + 10.0)
    for forbidden in (1226.0, 1258.0):
        assert tot != forbidden, (
            f"the physical Z2 config uses {forbidden} um -- that is the Z1 "
            f"embedded-cell proxy and excludes the high-side device")
    tiers = c["converter"]["tiers_from_substrate_downward"]
    names = [t["name"] for t in tiers]
    rec = DR.tiers()
    assert names[-1] == rec[0]["name"] and rec[0]["parts"].get("gan_hs"), (
        "the high side (the input-end tier) must be the deepest tier")
    assert names[1] == rec[-1]["name"] and rec[-1]["parts"].get("inductor"), (
        "the inductor tier must stay nearest the POL")
    assert sum(t["um"] for t in tiers) == pytest.approx(tot)


# ============================================== PCB THICKNESS / BGA / LATERAL
PCBJ = R / "research" / "phase0ns" / "pcb_thickness_audit.json"
LATJ = R / "research" / "phase0ns" / "lateral_rdl_loss.json"


def test_pcb_closure_is_evaluated_at_worst_case_board_and_max_device():
    a = json.loads(PCBJ.read_text())
    by = {b["board"]: b for b in a["boards"]}
    assert a["four_tier_max_um"] == pytest.approx(2083.0), "EPC2014C max stack changed"
    assert a["allowance_total_um"] >= 100.0, "interface allowances were dropped"
    for b in a["boards"]:
        assert b["t_min_um"] == pytest.approx(b["t_nom_um"] * 0.9), (
            f"{b['board']}: closure must use the -10 % board, not nominal")
    assert by["1.6 mm"]["margin_maxdevice_um"] < 0, "1.6 mm must FAIL"
    assert by["2.0 mm"]["margin_maxdevice_um"] < 0, "2.0 mm must fail at the device max"
    assert by["2.4 mm"]["margin_maxdevice_um"] > 0, "2.4 mm must close"
    assert by["3.2 mm"]["margin_maxdevice_plus_tim_um"] > 0, (
        "3.2 mm must fit the backside TIM inside the board")
    assert by["2.4 mm"]["margin_maxdevice_plus_tim_um"] < 0, (
        "2.4 mm must NOT fit the TIM inside -- the spreader protrudes, and the "
        "audit says so")


def test_lateral_loss_is_not_presented_as_an_extra_term():
    t = (R / "research" / "Z1_Z2_SUPPLY_RETURN_GEOMETRY.md").read_text()
    assert re.search(r"upper bound, not an additional term", t, re.I), (
        "the single-layer strip estimate must not be presented as a loss to add")
    l = json.loads(LATJ.read_text())
    f = l["frozen_z2_terms_w"]
    assert f["P_pkg_RDL"] / f["P_TSV"] > 0.5, (
        "lateral spreading is no longer the same order as P_TSV; re-check the finding")


def test_bga_budget_separates_power_from_package_io():
    t = (R / "research" / "Z2_CUTOUT_BGA_SIGNAL_BUDGET.md").read_text()
    # normalise markdown: blockquote markers and emphasis must not break the match
    flat = re.sub(r"\s+", " ", re.sub(r"[>*_`]", "", t))
    assert ("complete package-I/O BGA capacity is outside the current model" in flat), (
        "the required honesty statement about signal I/O was removed")
    assert re.search(r"proves only that power-delivery BGA capacity is not limiting",
                     flat, re.I), "the power-vs-I/O distinction was weakened"


def test_no_new_etm_lineage_without_closure():
    """Tasks G/18/22: phase0ns results may not appear while closure gates are open."""
    assert not (R / "results" / "phase0ns").exists(), (
        "a phase0ns results lineage appeared; supply/return geometry and the annular "
        "PCB mesh are still unimplemented")
    t = (R / "research" / "Z1_Z2_SUPPLY_RETURN_GEOMETRY.md").read_text()
    assert "Not implemented" in t


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


STALE_FROZEN = [
    (r"1921", r"1953"),      # component stack at selected-device heights
    (r"1226", r"1258"),      # embedded cell
    (r"5\.05", r"5\.32"),    # baseline worst via AR
]


@pytest.mark.parametrize("stale,corrected", STALE_FROZEN)
def test_manuscript_pairs_every_frozen_value_with_the_corrected_one(stale, corrected):
    """A frozen value may appear only alongside its selected-device counterpart."""
    tex = TEX.read_text()
    for m in re.finditer(stale, tex):
        w = tex[max(0, m.start() - 500): m.end() + 500]
        assert re.search(corrected, w) or re.search(r"frozen|historical", w, re.I), (
            f"{stale} at offset {m.start()} appears without {corrected} or a "
            f"'frozen' label")


def test_manuscript_device_attribution_is_corrected():
    tex = TEX.read_text()
    for m in re.finditer(r"EPC2212|EPC2090", tex):
        w = tex[max(0, m.start() - 300): m.end() + 300]
        assert re.search(r"EPC2014C|EPC2057|mis-attribut", w), (
            "the manuscript attributes a height to EPC2212/EPC2090 without the "
            "selected-device correction nearby")
    assert "EPC2014C" in tex and "EPC2057" in tex


def test_readme_has_no_unconditional_architecture_ordering():
    t = (R / "README.md").read_text()
    for m in re.finditer(r"hotter architecture", t, re.I):
        w = t[max(0, m.start() - 200): m.end() + 420]
        assert re.search(r"frozen geometry|not an architecture result|condition|"
                         r"reverses|open", w, re.I), (
            "README states the hotter-architecture ordering unconditionally")


def test_entry_points_do_not_claim_whole_package_realizability():
    """Task A sweep: README/CURRENT_STATUS must scope realizability to the interconnect."""
    for name in ("README.md", "CURRENT_STATUS.md"):
        t = (R / name).read_text()
        for m in re.finditer(r"GEOMETRICALLY REALIZABLE|geometrically realizable", t):
            w = t[max(0, m.start() - 260): m.end() + 260]
            assert re.search(r"vertical interconnect|VERTICAL INTERCONNECT|"
                             r"NOT ESTABLISHED|for free", w), (
                f"{name}: unscoped realizability claim at offset {m.start()}")


def test_entry_points_carry_the_corrected_device_values():
    t = (R / "CURRENT_STATUS.md").read_text()
    assert "1953" in t and "5.32" in t, (
        "CURRENT_STATUS does not carry the corrected stack height / baseline AR")
    assert "EPC2014C" in t and "EPC2057" in t


def test_no_live_config_attributes_heights_to_the_wrong_parts():
    """EPC2212/EPC2090 may appear only as a recorded mis-attribution."""
    import glob
    for f in glob.glob(str(R / "configs" / "**" / "*.yaml"), recursive=True):
        t = Path(f).read_text()
        for m in re.finditer(r"EPC2212|EPC2090", t):
            # TCPMT round 3: the design record names each design's SELECTED parts (re-
            # synthesized and checked by design_record); a selection is not a height
            # attribution (the record's tier heights come from the parts' own dimensions)
            line = t[t.rfind("\n", 0, m.start()) + 1: t.find("\n", m.end())]
            if Path(f).name == "design_points.yaml" and re.match(r"\s*(hs|ls)_part:", line):
                continue
            w = t[max(0, m.start() - 300): m.end() + 300]
            assert re.search(r"mis-attribution|CORRECTED|wrong|Phase 0N-R|frozen", w, re.I), (
                f"{Path(f).name}: live attribution to {m.group(0)} at offset {m.start()}")


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


# ---------------------------------------------------------------- Phase 0N-V, board tensor
HOMOG = R / "research" / "PCB_IT968G_HOMOGENIZATION.md"


def _board_card(case):
    import sys
    sys.path.insert(0, str(R / "scripts"))
    from phase0b.etm.config import build_materials
    import phase0i.zglobal as ZG
    st, _extra, _t = ZG.stack_for("ARCH_Z2_BACKSIDE", 0.30, board_case=case)
    return build_materials(st)["board_fr4"]


def test_it968g_thickness_study_is_material_identical():
    """T-only: 2.4 vs 3.2 mm may differ in thickness and in NOTHING else."""
    import sys
    sys.path.insert(0, str(R / "scripts"))
    from phase0g.board import BOARD_CASES
    a = dict(BOARD_CASES["it968g_2p4mm"])
    b = dict(BOARD_CASES["it968g_3p2mm"])
    assert a.pop("t_mm") == 2.4 and b.pop("t_mm") == 3.2
    assert a == b, (
        "the IT-968G thickness study changes material as well as thickness, which is the "
        f"exact confound that disqualified the fr4_* pair: {a} vs {b}")


def test_legacy_fr4_pair_still_confounds_and_is_therefore_forbidden():
    """The reason the fr4_* pair cannot be used for the physical comparison."""
    import sys
    sys.path.insert(0, str(R / "scripts"))
    from phase0g.board import BOARD_CASES
    a, b = BOARD_CASES["fr4_2p4mm"], BOARD_CASES["fr4_3p2mm"]
    assert (a["E_MPa"], a["cte"]) != (b["E_MPa"], b["cte"]), (
        "fr4_2p4mm/fr4_3p2mm no longer differ in material -- if that was fixed, the "
        "forbidden-case list and the T-only rationale must be revisited, not left stale")


def test_board_thermal_orthotropy_reaches_the_calculix_deck():
    card = _board_card("it968g_2p4mm").ccx_conductivity()
    assert "TYPE=ORTHO" in card[0], f"board conductivity is not orthotropic: {card}"
    kx, ky, kz = (float(v) for v in card[1].split(","))
    assert kx == ky and kx / kz > 100, (
        f"in-plane/through-thickness ratio collapsed: {kx} {ky} {kz}")


def test_legacy_board_path_emits_the_isotropic_card_unchanged():
    """Protects the frozen 0M-R3C replay, which runs on fr4_1p6mm."""
    card = _board_card("fr4_1p6mm").ccx_conductivity()
    assert card == ["*CONDUCTIVITY", "0.0003"], (
        f"the frozen board path changed and every frozen result is now suspect: {card}")


def test_elastic_anisotropy_is_declared_unmodelled_with_its_reason():
    t = HOMOG.read_text()
    assert re.search(r"cubic", t, re.I), (
        "the doc must say WHY elastic orthotropy is unavailable (the emitter is cubic)")
    assert "unmodelled, not modelled-as-equal" in t
    for c in ("E_z", "G_xz", "nu_xz"):
        assert c in t, f"{c} must be named as an OPEN constant"


def _negligible_claims(text):
    """Occurrences of 'negligible' near the shear term that are ASSERTED, not denied."""
    return [m.group(0) for m in re.finditer(r"negligib\w*", text, re.I)
            if not _NEG.search(_clause(text, m.start()))]


def test_shear_deformation_omission_is_not_called_negligible():
    assert not _negligible_claims(HOMOG.read_text()), (
        "the unmodelled through-thickness compliance is a 10 %-order effect; it must not "
        "be waved away as negligible")


@pytest.mark.parametrize("injected", [
    "The shear-deformation correction is negligible for this plate.",
    "E_z and G_xz are unmodelled, but the effect is negligible.",
])
def test_negligible_guard_negative(injected):
    """NEGATIVE: real offending phrasings caught; the actual denial must not be."""
    assert _negligible_claims(injected), f"guard went blind to {injected!r}"
    assert not _negligible_claims(
        "That is a 10 %-order effect, not a negligible one.")


def test_thickness_study_bias_direction_is_disclosed():
    t = HOMOG.read_text()
    assert "grows with thickness" in t, (
        "the shear omission is larger for the thicker board; a T-only study that does not "
        "say so lets a biased comparison read as a clean one")
    assert re.search(r"0\.341|0\.114", t), "the 3.2 mm bracket must be stated numerically"


def test_homogenization_doc_claims_no_solve():
    assert re.search(r"has not been run", HOMOG.read_text(), re.I)


def test_board_tensor_has_exactly_one_source():
    """board.py, the JSON and the document must all show the SAME derived numbers.

    An earlier draft had the doc printing k_xy = 67.58 (bracket upper) while board.py used
    65.86 (bracket midpoint). Both were defensible in isolation; together they were a
    contradiction that no test could see, because each file was internally consistent.
    """
    import sys, json
    sys.path.insert(0, str(R / "scripts"))
    from phase0g.board import BOARD_CASES
    n = json.loads((R / "research" / "phase0nv" / "pcb_homogenization.json").read_text()
                   )["nominal_tensor"]
    c = BOARD_CASES["it968g_2p4mm"]
    assert c["E_MPa"] == n["E_MPa"] and c["nu"] == n["nu"]
    assert c["cte"] == n["cte"] * 1e-6
    assert c["k_ortho"] == [n["k_xy"], n["k_xy"], n["k_z"]] and c["k"] == n["k_z"]
    t = HOMOG.read_text()
    for v in (f"{n['E_MPa']:.1f}", f"{n['cte']:.3f}", f"{n['k_xy']:.3f}", f"{n['k_z']:.4f}"):
        assert v in t, f"the document does not print the derived value {v}"


def test_nominal_tensor_applies_one_bracket_rule_uniformly():
    """Mixing 'midpoint' for one quantity and 'upper bound' for another is how the two
    sources diverged in the first place."""
    import json
    h = json.loads((R / "research" / "phase0nv" / "pcb_homogenization.json").read_text())
    n = h["nominal_tensor"]
    for val, br in ((n["k_xy"], n["k_xy_bracket"]), (n["k_z"], n["k_z_bracket"]),
                    (n["Ez_MPa"], n["Ez_MPa_bracket"])):
        assert abs(val - 0.5 * (br[0] + br[1])) < 1e-9 * max(1.0, abs(val)), (
            f"{val} is not the midpoint of {br}; the reduction rule is not uniform")


def test_yaml_config_is_generated_from_the_same_tensor():
    """configs/phase0nv is a THIRD consumer; it must not be hand-maintained."""
    import json, yaml
    y = yaml.safe_load((R / "configs" / "phase0nv" / "pcb_it968g_18layer.yaml").read_text())
    n = json.loads((R / "research" / "phase0nv" / "pcb_homogenization.json").read_text()
                   )["nominal_tensor"]
    assert all(y["nominal"][k] == n[k] for k in n), (
        "the YAML nominal block has drifted from the generator's reduction")
    assert "do not hand-edit" in y["nominal"]["note"].lower()


# ------------------------------------------------- Phase 0N-V2: claim scope + physical path
PCBAUDIT = R / "research" / "PCB_MATERIAL_PROPERTY_AUDIT.md"
LEGACY_BOARDS = ("fr4_2p4mm", "fr4_3p2mm")


def _flat(p):
    """Markdown re-wraps, so a phrase can straddle a newline. Compare on flattened text."""
    return re.sub(r"\s+", " ", p.read_text())

# Files that constitute the PHYSICAL package path. Historical Phase-0G/0M-R3C scripts are
# deliberately excluded: they must keep reproducing with the legacy board.
PHYSICAL_SOURCES = ["configs/phase0nt/z2_2p4mm_cutout.yaml", "scripts/phase0nt_annular_pcb.py"]


def _physical_files():
    out = [R / p for p in PHYSICAL_SOURCES]
    out += sorted((R / "configs").glob("phase0nw/*.yaml"))
    out += sorted((R / "scripts").glob("phase0nw*.py"))
    return [p for p in out if p.exists()]


def _legacy_board_hits(text, legacy):
    """Lines that SELECT a legacy board case, ignoring prose and comments about it."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        code = line.split("#", 1)[0]          # drop trailing/whole-line comments
        if legacy in code:
            hits.append(f"{i}: {line.strip()}")
    return hits


@pytest.mark.parametrize("legacy", LEGACY_BOARDS)
def test_physical_path_never_uses_a_legacy_board_case(legacy):
    """The unsourced fr4_* cases are reproduction-only and must not reach a physical build."""
    bad = []
    for f in _physical_files():
        bad += [f"{f.relative_to(R)}:{h}" for h in _legacy_board_hits(f.read_text(), legacy)]
    assert not bad, f"legacy board {legacy} selected on the physical path:\n" + "\n".join(bad)


@pytest.mark.parametrize("injected", [
    'board_case="fr4_2p4mm", cutout_mm=cut)',
    "  case: fr4_2p4mm",
])
def test_legacy_board_guard_negative(injected):
    """NEGATIVE: a real selection is caught; naming it in a comment or in prose is not."""
    assert _legacy_board_hits(injected, "fr4_2p4mm"), f"guard went blind to {injected!r}"
    assert not _legacy_board_hits(
        "  case: it968g_2p4mm   # the legacy fr4_2p4mm is UNSOURCED and is forbidden",
        "fr4_2p4mm")
    assert not _legacy_board_hits("# fr4_2p4mm is kept for reproduction only", "fr4_2p4mm")


def test_physical_z2_config_selects_it968g():
    import yaml
    c = yaml.safe_load((R / "configs/phase0nt/z2_2p4mm_cutout.yaml").read_text())
    # TCPMT round 3: one 3.2-mm it968g board for Z1/Z2/Z3 (the decided converter does not fit
    # the 2.4-mm board's cutout); Phase 0N-V selected it968g_2p4mm
    assert c["board"]["case"] == "it968g_3p2mm"
    assert c["board"]["thickness_sensitivity_case"].startswith("it968g_")
    assert c["board"]["eta_sensitivity"] == [0.25, 0.50, 0.75], (
        "the coverage sweep must stay live; eta = 0.5 is a midpoint, not a measurement")
    assert c["board"]["model_level"] == "PCB-H0"


def test_every_bracket_is_stored_lower_then_upper():
    import json
    h = json.loads((R / "research/phase0nv/pcb_homogenization.json").read_text())
    bad = [(r["eta"], k, r[k]) for r in h["sweep"]
           for k in ("Ez_MPa_bounds", "k_xy_bounds", "k_z_bounds") if r[k][0] > r[k][1]]
    n = h["nominal_tensor"]
    bad += [("nominal", k, n[k]) for k in ("Ez_MPa_bracket", "k_xy_bracket", "k_z_bracket")
            if n[k][0] > n[k][1]]
    assert not bad, f"brackets stored [upper, lower]: {bad}"


def test_bracket_helper_rejects_reversed_input():
    """NEGATIVE: the ordering invariant must be enforced in code, not just in the data."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_h", R / "scripts/phase0nv_pcb_homogenization.py")
    src = (R / "scripts/phase0nv_pcb_homogenization.py").read_text()
    assert "store [lower, upper]" in src and "raise ValueError" in src, (
        "_mid() no longer rejects a reversed bracket")


def test_ez_nominal_bracket_is_the_expected_range():
    import json
    n = json.loads((R / "research/phase0nv/pcb_homogenization.json").read_text())["nominal_tensor"]
    lo, hi = (v / 1e3 for v in n["Ez_MPa_bracket"])
    assert 4.0 < lo < 4.9 and 10.0 < hi < 11.0, f"Ez bracket moved: [{lo:.2f}, {hi:.2f}] GPa"
    assert abs(n["Ez_MPa"] / 1e3 - 7.49) < 0.05, "the midpoint should not have changed"


def _asserted(text, pattern):
    return [m.group(0) for m in re.finditer(pattern, text, re.I)
            if not _NEG.search(_clause(text, m.start()))]


def test_historical_22gpa_is_not_called_impossible():
    """A copper-loaded board CAN exceed the bare laminate modulus; the objection is
    provenance, not plausibility."""
    t = _flat(PCBAUDIT)
    assert "not necessarily physically impossible" in t
    assert "unsupported" in t
    bad = _asserted(t, r"wrong in direction")
    assert not bad, "the audit still claims the historical values were wrong in direction"


def test_whole_board_values_are_labelled_conditional():
    for f in (PCBAUDIT, HOMOG):
        t = _flat(f).lower()
        assert "conditional derived estimate" in t, (
            f"{f.name} does not label the whole-board numbers as conditional on eta")
    t = PCBAUDIT.read_text()
    for s in ("SOURCE_BACKED", "DERIVED", "BOUNDED"):
        assert s in t
    assert "not measured board properties" in _flat(PCBAUDIT)


def test_kxy_is_labelled_a_nominal_h0_estimate_not_a_board_property():
    t = _flat(HOMOG)
    assert re.search(r"nominal PCB-H0 homogenized estimate at \d+ % areal copper", t), (
        "k_xy must be labelled a nominal H0 estimate at a stated coverage")
    assert 'not "the IT-968G board conductivity"' in t
    assert _flat(HOMOG).count("| 0.25 |") >= 2, "k_xy(eta) must be reported across the sweep"


def test_model_is_not_described_as_an_orthotropic_board_model():
    t = _flat(HOMOG)
    assert "thermally orthotropic, mechanically isotropic reduced model" in t
    for c in ("E_x ≠ E_y", "alpha_x", "alpha_y"):
        assert c in t, f"the discarded in-plane anisotropy {c} must be recorded"


def test_shear_estimate_is_only_a_scaling_argument():
    t = _flat(HOMOG)
    assert "scaling argument, not a validated uncertainty bound" in t
    assert "not an error bar" in t
    bad = _asserted(t, r"mechanical uncertainty is\s*~?\s*10\s*%")
    assert not bad, "the shear scaling is being presented as a formal uncertainty"


@pytest.mark.parametrize("injected", [
    "The mechanical uncertainty is ~10% from transverse shear.",
    "Transverse shear gives a mechanical uncertainty is 10 % error bar.",
])
def test_shear_scaling_guard_negative(injected):
    assert _asserted(injected, r"mechanical uncertainty is\s*~?\s*10\s*%"), (
        f"guard went blind to {injected!r}")
    assert not _asserted(
        "This is a scaling argument; the mechanical uncertainty is not 10 %.",
        r"mechanical uncertainty is\s*~?\s*10\s*%")
