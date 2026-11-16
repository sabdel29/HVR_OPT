"""TCPMT REVISION --- the Z1 chain generalized to another regulator count and topology.

Two promises are tested, in the style of test_z3_board_backside.py (every guard reads the mesh
and the ledger the solver uses, never the YAML alone):

1. THE 49-CELL RESULTS ARE UNCHANGED. The fingerprint of the Z1, Z2 and Z3 production builds
   (mesh, materials, ledgers S0/S1/S2, deposits, temperature regions, thermal and structural
   decks; research/tcpmt_revision/countopt/fingerprint_49.py) equals the one recorded on the
   tree before the change, and every derived rule reproduces the production literal it
   replaces off the production path.
2. A NON-DEFAULT DESIGN IS CARRIED CONSISTENTLY. With HVR_Z1_CONFIG naming the M = 64
   candidate, the mesh, the tiles, the tier order, the TSV lattice, the intra-VR routing, the
   converter terms and the energy balance all follow it, and no other architecture can run.
   Those checks run in a subprocess, because the design is fixed per process at import.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
CO = R / "research" / "tcpmt_revision" / "countopt"
CFG64 = R / "configs" / "phase0nx" / "z1_physical_m64.yaml"
sys.path.insert(0, str(R / "scripts"))
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m", "scripts/phase0i",
           "scripts/phase0g", "scripts/phase0b", "scripts/phase0f", "scripts/phase0d",
           str(CO.relative_to(R))):
    sys.path.insert(0, str(R / _p))

pytestmark = pytest.mark.skipif(bool(os.environ.get("HVR_Z1_CONFIG")),
                                reason="the production-path tests need HVR_Z1_CONFIG unset")


# ------------------------------------------------------------------ 1. 49 cells unchanged
def test_49_cell_fingerprint_equals_the_pre_change_record():
    import fingerprint_49 as F
    before = json.loads((CO / "fingerprint_49_before.json").read_text())["cases"]
    now = {}
    for arch in ("Z1", "Z2", "Z3"):
        for rf in ((1, 1), (2, 1)):
            now[f"{arch}_h1.1_r{rf[0]}{rf[1]}"] = F.fingerprint(arch, 1.1, rf)
    assert set(now) == set(before)
    assert F.compare_fingerprints(before, now) == []


def test_the_committed_after_record_equals_the_before_record():
    import fingerprint_49 as F
    before = json.loads((CO / "fingerprint_49_before.json").read_text())
    after = json.loads((CO / "fingerprint_49_after.json").read_text())
    assert after["env"]["HVR_Z1_CONFIG"] is None
    assert F.compare_fingerprints(before["cases"], after["cases"]) == []


def test_production_path_reads_no_derived_value():
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    import production_et as PE
    import replay_production as RP
    import z1_design as Z1D
    assert Z1D.is_default() and Z1D.n_vr() == 49 and Z1D.tag() == ""
    assert FL.N_VR == 49 == RP.n_vr() == PE.N_VR
    assert FL.SCEN_RATIO["HV_S1"] == 4.0
    assert E.TSV_N_PER_CELL == 1444 and E.DESIGN_TAG == ""
    assert E.case_path("Z1", "HV_S0") == R / "research/final_closure/etm_Z1_HV_S0_h1.1_r21.json"
    assert Z1D.package_network_file() == R / "research/final_closure/package_network.json"
    import routing as RT
    assert FL.routing_design() is RT.DESIGN


def test_derived_rules_reproduce_the_production_literals():
    """Each rule the candidate path uses, applied to the production design, gives the
    production constant it replaces."""
    import final_closure_ledger as FL
    import kw1
    import routing as RT
    import z1_design as Z1D
    assert Z1D.z1_layers(Z1D.DEFAULT_CFG) == FL.LAYERS["Z1"]
    assert list(Z1D.z1_layers(Z1D.DEFAULT_CFG)) == list(FL.LAYERS["Z1"])
    assert Z1D.tsv_n_per_cell(Z1D.DEFAULT_CFG) == 1444
    d = Z1D.design_dict(kw1.design_1kw()[0], 49, RT.DESIGN)
    for k, v in RT.DESIGN.items():
        if k == "f_sw_hz":              # the literal was typed from a printed value (1 ulp)
            assert d[k] == pytest.approx(v, rel=1e-15)
        else:
            assert d[k] == v, k
    assert 1.0 / math.sqrt(3 * 1.0 / 48.0) == FL.SCEN_RATIO["HV_S1"]


def test_kw1_takes_count_and_topology():
    import kw1
    d49, _, _ = kw1.design_1kw()
    assert d49.label == "N3K3KA2_J3.5"
    assert kw1.design_1kw(topology=(3, 3, 2))[0].f_sw_hz == d49.f_sw_hz
    d64, _, why = kw1.design_1kw(m_vr=64, topology=(2, 2, 1))
    c = yaml.safe_load(CFG64.read_text())["design"]
    assert (d64.hs.part_number, d64.ls.part_number, d64.inductor.name, d64.capacitor.name) == (
        c["hs_part"], c["ls_part"], c["inductor"], c["capacitor"])
    assert d64.f_sw_hz == pytest.approx(c["f_sw_hz"], rel=1e-12)
    assert d64.loss_25c_w * 64 == pytest.approx(c["conversion_25C_W"], rel=1e-12)
    assert kw1.design_1kw(m_vr=64, topology=(3, 3, 2))[0] is None   # N3K3 does not fit 4.46 mm2


# ------------------------------------------------------------------ physical cell
def test_physical_cell_method_reproduces_the_paper_and_selects_the_configured_order():
    cell = json.loads((CO / "physical_cell.json").read_text())
    v = cell["validation_49"]
    assert v["n_area_feasible"] == 144
    assert round(v["reference_order_worst_ar"], 2) == 5.32
    assert round(v["repartitioned_worst_ar"], 2) == 0.83
    c = cell["cells"]["64"]
    assert c["cell_side_mm"] == pytest.approx(math.sqrt(3.74))
    ch = c["chosen"]
    assert ch["realizable"] and ch["worst_ar"] <= 1.0
    # no two classes share a tier at 3.74 mm2: every area-feasible order has five tiers
    assert {r["n_tiers"] for r in c["assignments"]} == {5}
    assert c["n_realizable_hs_at_bottom"] == 1
    tiers = yaml.safe_load(CFG64.read_text())["converter"]["tiers_from_substrate_upward"]
    comp = [t for t in tiers if not t["name"].endswith("_rdl")]
    cls = {"gan_hs": "gan_hs", "flying_caps": "cap_fly", "gan_ls": "gan_ls",
           "inductor": "inductor", "output_caps": "cap_out"}
    order = [next(v for k, v in cls.items() if t["name"].startswith(k)) for t in comp]
    assert " | ".join(order) == ch["partition"]
    assert [t["um"] for t in comp] == ch["tier_um"]
    assert sum(float(t["um"]) for t in tiers) == ch["stack_um"] == 2083.0
    assert all(t["um"] == 10.0 for t in tiers if t["name"].endswith("_rdl"))


def test_a_non_default_config_without_a_design_block_is_refused(tmp_path):
    import z1_design as Z1D
    c = yaml.safe_load(CFG64.read_text())
    c.pop("design")
    p = tmp_path / "z1_nodesign.yaml"
    p.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(Z1D.DesignError):
        Z1D.declared(p)
    c = yaml.safe_load(CFG64.read_text())
    c["design"]["hs_part"] = "EPC2057"
    p2 = tmp_path / "z1_wrongpart.yaml"
    p2.write_text(yaml.safe_dump(c, sort_keys=False))
    with pytest.raises(Z1D.DesignError):
        Z1D.compiled(p2)


# ------------------------------------------------------------------ 2. the candidate
_PROBE = r"""
import json, math, sys, tempfile
from pathlib import Path
import numpy as np
R = Path(sys.argv[1])
for p in ("scripts", "scripts/phase0nw", "scripts/phase0mr", "scripts/phase0m",
          "scripts/phase0i", "scripts/phase0g", "scripts/phase0b"):
    sys.path.insert(0, str(R / p))
import final_closure_ledger as FL
import final_closure_physical_etm as E
import production_et as PE
import z1_design as Z1D
from physical_package import measure_layers, load_z1_package_config
out = {"n_vr": FL.N_VR, "layers": FL.LAYERS["Z1"], "tiers": FL.cell_tiers("Z1"),
       "s1": FL.SCEN_RATIO["HV_S1"], "tsv": E.TSV_N_PER_CELL,
       "case": str(E.case_path("Z1", "HV_S0")), "tag": E.DESIGN_TAG}
m, mats, st, tiles, info = E.build("Z1", 1.1, (1, 1))
out.update(n_tiles=len(tiles), side=[t.ax for t in tiles][:1] + [t.ay for t in tiles][:1],
           sides=sorted({round(t.ax, 12) for t in tiles}), info=info,
           layers_mesh=measure_layers(m), z_min=float(m.zs.min()) * 1e3,
           z_max=float(m.zs.max()) * 1e3)
cfg = load_z1_package_config()
out["cfg"] = {"cells": cfg.cells, "tiers": list(cfg.tiers), "top": cfg.package_top_um}
T = {"conv": 101.0, "hs": 103.0, "ls": 99.0, "ind": 97.0, "caps": 95.0, "bga": 70.0,
     "sub": 90.0, "interface": 88.0}
L = FL.self_consistent("Z1", "HV_S0", T)
out["rows"] = {r["term"]: [r["P_w"], r["deposit_layer"]] for r in L["rows"]}
out["P_loss"] = L["P_loss_w"]
out["energy_residual_rel"] = L["energy"]["residual_rel"]
dep = E.deposits_from_ledger("Z1", L)
top = PE.ccxio.top_film_faces(m)
with tempfile.TemporaryDirectory() as td:
    th = E.write_thermal(m, mats, st, dep, np.full(len(top), 1e4), np.full(len(top), 30.0),
                         Path(td) / "th.inp", tiles, arch="Z1")
out["deposited"] = th["deposited_w"]
out["total"] = FL.P_LOAD_W + L["P_loss_w"]
import rms_currents as RMS
out["i_cell_avg"] = RMS.cell_currents()["i_cell_out_avg_a"]
regs = E.temperature_regions("Z1")
out["conv_region"] = regs["conv"][0]
hot = {r["term"]: r["P_w"] for r in FL.ledger("Z1", "HV_S0", dict(T, ls=130.0), 23.7)["rows"]}
base = {r["term"]: r["P_w"] for r in FL.ledger("Z1", "HV_S0", T, 23.7)["rows"]}
out["moved_by_ls"] = sorted(k for k in base if abs(hot[k] - base[k]) > 1e-12)
try:
    E.build("Z2", 1.1, (1, 1))
    out["guard"] = False
except RuntimeError:
    out["guard"] = True
print("JSON" + json.dumps(out, default=float))
"""


@pytest.fixture(scope="module")
def cand():
    env = dict(os.environ, HVR_Z1_CONFIG=str(CFG64.relative_to(R)), PYTHONDONTWRITEBYTECODE="1",
               OPENBLAS_NUM_THREADS="1")
    r = subprocess.run([sys.executable, "-B", "-c", _PROBE, str(R)], env=env, cwd=str(R),
                       capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, r.stderr[-3000:]
    line = next(x for x in r.stdout.splitlines() if x.startswith("JSON"))
    return json.loads(line[4:])


def test_candidate_constants_follow_its_config(cand):
    c = yaml.safe_load(CFG64.read_text())
    assert cand["n_vr"] == c["design"]["n_vr"] == c["converter"]["cells"] == 64
    assert cand["s1"] == pytest.approx(1.0 / math.sqrt(2.0 / 48.0))
    assert cand["tsv"] == 31 * 31
    assert cand["tag"] == c["design"]["tag"]
    assert cand["case"].endswith(f"research/tcpmt_revision/countopt/etm_Z1_{cand['tag']}"
                                 "_HV_S0_h1.1_r21.json")
    assert cand["i_cell_avg"] == pytest.approx(1000.0 / 64)


def test_candidate_mesh_carries_its_cells_and_tiers(cand):
    c = yaml.safe_load(CFG64.read_text())
    assert cand["n_tiles"] == 64 and cand["sides"] == [round(math.sqrt(3.74), 12)]
    # every tier at its configured z, measured on the mesh, from the substrate top upward
    z = 300.0
    for i, t in enumerate(c["converter"]["tiers_from_substrate_upward"]):
        lay = cand["layers_mesh"][f"z1conv_{i}_{t['name']}"]
        assert lay["z0_um"] == pytest.approx(z, abs=1e-6)
        assert lay["t_um"] == pytest.approx(t["um"], abs=1e-6)
        z += t["um"]
    assert z == pytest.approx(300.0 + c["converter"]["total_um"])
    assert cand["z_max"] - cand["z_min"] == pytest.approx(c["expected"]["package_top_um"])
    # the ledger's layer map names meshed tiers only, the output capacitor tier included
    for k in ("hs", "ls", "caps", "ind", "cout", "lv"):
        assert cand["layers"][k] in cand["layers_mesh"], k
    assert all(n in cand["layers_mesh"] for n in cand["layers"]["rdl"])
    assert cand["layers"]["cout"] in cand["conv_region"]
    assert [x[0] for x in cand["tiers"]] == ["rdl", "gan_hs", "rdl", "cap_fly", "rdl",
                                             "gan_ls", "rdl", "inductor", "rdl", "cap_out",
                                             "rdl"]
    assert cand["info"]["tsv_tile_cu_fraction"] == pytest.approx(
        961 * math.pi * 0.015 ** 2 / 3.74, rel=1e-9)


def test_candidate_energy_balance_and_regions(cand):
    assert cand["deposited"] == pytest.approx(cand["total"], rel=1e-6)
    assert abs(cand["energy_residual_rel"]) < 1e-9
    rows = cand["rows"]
    # every conductor of the production Z1 ledger is present (BGA-fed: package 48 V terms)
    for t in ("P_conv_hs", "P_conv_ls", "P_conv_inductor_dcr", "P_conv_cap_esr",
              "P_intraVR_metal", "P_intraVR_vertical", "P_pkg_RDL_HV_supply",
              "P_pkg_RDL_HV_return", "P_BGA_supply", "P_BGA_return", "P_TSV_VDD", "P_TSV_GND",
              "P_pad_VDD", "P_pad_GND"):
        assert rows[t][0] > 0, t
    assert rows["P_conv_cap_esr"][1] == cand["layers"]["caps"]
    assert rows["P_conv_inductor_dcr"][1] == cand["layers"]["ind"]
    # the low-side tier temperature moves only the low-side term (each device term is
    # evaluated where its loss is deposited, final_closure_physical_etm.temperature_regions)
    assert cand["moved_by_ls"] == ["P_conv_ls"]


def test_candidate_process_refuses_other_architectures(cand):
    assert cand["guard"] is True
