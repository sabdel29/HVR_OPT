"""Z2_DIRECT_FEED guards (research/final_closure/Z2_DIRECT_FEED_ARCHITECTURE.md).

The primary Z2 takes its 48 V through a dedicated external connection on the cutout side,
so no package 48 V BGA or RDL term may ever appear in its ledger. Each guard also runs on
the REAL rows the superseded BGA-fed Z2 carried at commit abba03e, never a paraphrase."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
D = R / "research" / "final_closure"
sys.path.insert(0, str(R / "scripts"))
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m"):
    sys.path.insert(0, str(R / _p))

#: the exact package 48 V rows the superseded primary Z2 carried at abba03e
#: (research/final_closure/etm_Z2_HV_S0_h1.1_r21.json)
STALE_Z2_ROWS = [
    {"term": "P_pkg_RDL_HV_supply", "conductor": "package HV RDL supply sheet",
     "P_w": 0.5884961152545829, "deposit_layer": "bga"},
    {"term": "P_BGA_supply", "conductor": "BGA supply balls (N=54)",
     "P_w": 0.0060798000925994435, "deposit_layer": "bga"},
    {"term": "P_pkg_RDL_HV_return", "conductor": "package HV RDL return sheet",
     "P_w": 0.5555838854970473, "deposit_layer": "bga"},
    {"term": "P_BGA_return", "conductor": "BGA return balls (N=54)",
     "P_w": 0.00524727647578143, "deposit_layer": "bga"},
]
TEMPS = {"conv": 100.0, "bga": 70.0, "sub": 100.0, "interface": 100.0, "attach": 100.0}


def _spec():
    return json.loads((D / "z2_direct_feed_architecture.json").read_text())


def test_direct_feed_ledger_has_no_package_48v_term_and_every_required_term():
    import final_closure_ledger as FL
    L = FL.ledger("Z2", "HV_S0", TEMPS, 23.7)
    terms = {r["term"] for r in L["rows"]}
    spec = _spec()["architectures"]["Z2"]
    assert not terms & set(spec["forbidden_ledger_terms"]), terms
    assert set(spec["required_ledger_terms"]) <= terms, set(spec["required_ledger_terms"]) - terms
    assert L["architecture_variant"] == "Z2_DIRECT_FEED" and L["hv_feed"] == "DIRECT_FEED"
    assert L["external_feed"]["in_package_internal_total"] is False


def test_direct_feed_guard_refuses_the_real_stale_rows():
    import final_closure_ledger as FL
    L = FL.ledger("Z2", "HV_S0", TEMPS, 23.7)
    with pytest.raises(RuntimeError, match="package 48 V terms"):
        FL.check_direct_feed("Z2", L["rows"] + STALE_Z2_ROWS)
    for row in STALE_Z2_ROWS:                       # each one alone is refused
        with pytest.raises(RuntimeError):
            FL.check_direct_feed("Z2", L["rows"] + [row])
    FL.check_direct_feed("Z2BF", L["rows"] + STALE_Z2_ROWS)   # the control may carry them
    FL.check_direct_feed("Z1", STALE_Z2_ROWS)


def test_control_and_z1_keep_their_package_48v_path():
    import final_closure_ledger as FL
    for arch in ("Z1", "Z2BF"):
        terms = {r["term"] for r in FL.ledger(arch, "HV_S0", TEMPS, 23.7)["rows"]}
        assert {"P_pkg_RDL_HV_supply", "P_BGA_supply"} <= terms, arch
    assert FL.VARIANT["Z2BF"] == "Z2_BGA_FED_CONTROL"


def test_every_final_artifact_names_its_architecture():
    files = sorted(D.glob("etm_Z2_*_h1.1_r21.json")) + sorted(D.glob("etm_Z2BF_*_r21.json"))
    if not files:
        pytest.skip("no production case files")
    for f in files:
        j = json.loads(f.read_text())
        want = "Z2_BGA_FED_CONTROL" if j["arch"] == "Z2BF" else "Z2_DIRECT_FEED"
        assert j.get("architecture_variant") == want, f.name
        if want == "Z2_DIRECT_FEED":
            bad = {r["term"] for r in j["ledger_rows"]} & {r["term"] for r in STALE_Z2_ROWS}
            assert not bad, (f.name, bad)
            assert j["hv_feed"] == "DIRECT_FEED" and j["external_feed"], f.name


def test_loader_refuses_a_direct_feed_config_without_its_defining_features(tmp_path):
    import physical_package as PP
    src = (R / "configs/phase0nt/z2_2p4mm_cutout.yaml").read_text()
    cfg = PP.load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    assert cfg.variant == "Z2_DIRECT_FEED" and cfg.attach_um == 30.0
    assert cfg.clearance_void and cfg.out_of_cell_primary == "F1_clearance"
    for old, new in (("sidewall_content: VOID", "sidewall_content: FILLED"),
                     ("mode: DIRECT_FEED", "mode: BGA_FED"),
                     ("primary: F1_clearance", "primary: F1_encapsulated"),
                     ("  thickness_um: 30.0           # the clearance",
                      "  thickness_um: 0.0           # the clearance")):
        bad = tmp_path / "z2.yaml"
        bad.write_text(src.replace(old, new, 1))
        assert src.count(old) == 1, old
        with pytest.raises(PP.PhysicalConfigError):
            PP.load_physical_package_config(bad)


def test_mesh_carries_the_attach_and_a_void_clearance_ring():
    import numpy as np
    import final_closure_physical_etm as E
    m, _mats, st, tiles, _info = E.build("Z2", 1.1, (1, 1))
    lay = np.array(m.elem_layer, dtype=object)
    mat = np.array(m.elem_material, dtype=object)
    cen = m.elem_centroids()
    att = lay == "conv_attach_vr_substrate"
    assert att.any() and set(mat[att]) == {"vr_attach", "underfill_homog"}
    zl = {L.name: (L.z0, L.z1) for L in m.layers}
    assert abs(zl["conv_attach_vr_substrate"][1]) < 1e-12
    assert abs(zl["conv_attach_vr_substrate"][0] + 0.030) < 1e-9
    assert abs(zl["conv_0_land_side_attach_rdl"][1] + 0.030) < 1e-9
    x1 = max(t.x1 for t in tiles)
    conv = np.array([str(x).startswith("conv") for x in lay])
    ring = conv & ((np.abs(cen[:, 0]) > x1 + 1e-9) | (np.abs(cen[:, 1]) > x1 + 1e-9))
    assert not ring.any(), int(ring.sum())
    k = st["materials"]["vr_attach"]["k_ortho"]["value"]
    assert k[2] > 10 * k[0]                          # columns conduct through, not across


def test_every_class_b_variant_and_gate_agree():
    """A variant that names a gate classB does not know (or a classB case that is not a
    variant) would be silently skipped by the resolution table."""
    import final_closure_classB as C
    import final_closure_sensitivity as S
    named = {g for v in S.VARIANTS.values() for g in v["gates"]}
    assert named <= set(C.GATES), sorted(named - set(C.GATES))
    run_cases = {c for g in C.GATES.values() if g[3] == "runs" for c in g[4]}
    assert run_cases <= set(S.VARIANTS), sorted(run_cases - set(S.VARIANTS))
    for v in ("f1_sidewall_filled", "attach_h20", "attach_h40", "attach_sn",
              "attach_stiff", "attach_uf_soft", "attach_uf_stiff", "feed_heat_at_crossover",
              "icepak_equivalent", "z2_cooled_tim", "bga_depop"):
        assert v in S.VARIANTS, v
    assert "f1_clearance" not in S.VARIANTS        # the clearance is the baseline now


def test_crossover_is_a_requirement_not_a_value():
    import math
    cx = json.loads((D / "direct_feed_crossover.json").read_text())
    assert cx["assumed_value"] is None
    for s, c in cx["scenarios"].items():
        for p in c["sweep"]:                     # every feasible point closes the balance
            if p.get("feasible", True):
                assert abs(p["energy_residual_w"]) < 1e-6, (s, p)
        if c["Z1_operating_point_inadmissible"]:
            assert c["requirement"] is None, s
        elif c["R_star_mohm"]:
            assert c["advantage_at_zero_feed_w"] > 0, s
            assert "R_Z2_direct_feed_loop <" in c["requirement"], s
            # around R* the platform-inclusive Z2 loss crosses Z1's
            near = min(c["sweep"], key=lambda p: abs(math.log(p["R_mohm"] / c["R_star_mohm"])))
            assert (near["P_total_w"] - c["P_Z1_w"]) * (near["R_mohm"] - c["R_star_mohm"]) >= 0
        else:                                    # Z2 not ahead even with a lossless feed
            assert c["advantage_at_zero_feed_w"] <= 0, s
            assert c["requirement"].startswith("none:"), s
            assert all(p["P_total_w"] >= c["P_Z1_w"] for p in c["sweep"]
                       if p.get("feasible", True)), s


def test_infeasible_feed_points_are_flagged_not_extrapolated():
    """Above R_max = V^2/(4 k^2 (P_load + P_int)) the feed cannot deliver the load; the
    fixed-point iteration used to diverge to an OverflowError there."""
    import final_closure_direct_feed as DF
    temps = DF.converged_temps(json.loads((D / "etm_Z2_HV_S1_h1.1_r21.json").read_text()))
    p = DF.platform_point("HV_S1", temps, 1.0)
    assert p["feasible"] is False and p["P_total_w"] is None and p["R_max_mohm"] < 1000.0
    q = DF.platform_point("HV_S1", temps, 1e-3)
    assert q["feasible"] is True and abs(q["energy_residual_w"]) < 1e-6


def test_omelet_crosscheck_states_which_package_rdl_still_exists():
    """Part 31: the cross-check must say that the primary Z2 has no package 48 V RDL and
    that the BGA-fed sheet belongs to the control, and keep HF physics out of the DC Z2."""
    t = (D / "RDL_OMELET_CROSSCHECK.md").read_text()
    assert "## 0. Which package RDL structures still exist" in t
    assert "| Z2_DIRECT_FEED 48 V input | **no package RDL**" in t
    assert "**control only**" in t and "Z2_BGA_FED_CONTROL" in t
    assert "No high-frequency physics migrates into the DC Z2 model." in t
