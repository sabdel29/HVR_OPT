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
def test_K_is_the_buck_phase_count(design):
    """K multiplies BOTH the low-side device count and the inductor count."""
    from HVR_FULL_OPT_EPC_V2 import compute_component_count
    a = design.arch
    cc = compute_component_count(a.N, a.K, 1, 1, 1, 1)
    assert cc == a.component_count == a.N + 2 * a.K + (a.N - 1)
    assert a.K == 3 and a.N == 3 and a.K_A == 2


def test_K_phase_count_negative(design):
    """NEGATIVE: if K stopped driving the inductor count the identity must break."""
    from HVR_FULL_OPT_EPC_V2 import compute_component_count
    a = design.arch
    wrong = compute_component_count(a.N, a.K, 1, 1, 0, 1)   # inductor_weight = 0
    assert wrong != a.component_count


def test_K_A_is_derived_not_free(design):
    import math
    a = design.arch
    assert a.K_A == math.ceil(a.K / 2)


def test_branches_per_inductor_match_K(design):
    a = design.arch
    assert len(a.B_array) == a.K, "B_array length must equal the inductor/phase count"
    assert sum(a.B_array) == a.N, "every high-side branch must land on an inductor"


def test_per_phase_current_matches_network(design):
    i_phase = design.i_out_a / design.arch.K
    assert i_phase == pytest.approx(6.8027, abs=1e-3)
    assert i_phase < design.ls.ID_A, (
        f"per-phase {i_phase:.3f} A exceeds the {design.ls.part_number} "
        f"{design.ls.ID_A} A rating")


def test_duty_ratio_follows_N(design):
    a = design.arch
    assert a.D == pytest.approx(design.v_out * a.N / design.v_in)


def test_no_interleaving_is_modelled():
    """'interleaved' may not be claimed: no phase-shift construct exists."""
    src = (R / "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for pat in (r"phase_shift", r"phase_offset", r"interleav"):
        assert not re.search(pat, code, re.I), (
            f"{pat!r} now appears in code -- re-audit "
            f"research/HVR_PHASE_COUNT_AUDIT.md section 4")


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
def test_manuscript_does_not_claim_interleaving():
    assert not re.search(r"interleav", TEX.read_text(), re.I), (
        "the manuscript claims interleaving, which the implementation does not model")


def test_manuscript_interleaving_negative():
    """NEGATIVE: the real offending phrase must be caught."""
    injected = r"Topology 3:1 SC + 3-phase interleaved buck"
    assert re.search(r"interleav", injected, re.I)


def test_manuscript_does_not_put_1921_inside_the_substrate():
    """The pre-audit defect: '1921 um converter' + 'built into the 1.30 mm substrate'."""
    tex = TEX.read_text()
    for m in re.finditer(r"built into the \$?1\.30\\?,?\\?\s*mm\$?\\?,?\s*substrate", tex):
        window = tex[max(0, m.start() - 400): m.end() + 400]
        assert "1921" not in window, (
            "the manuscript again places the 1921 um converter stack inside the "
            "1.30 mm substrate; only 1226 um is embedded")


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
