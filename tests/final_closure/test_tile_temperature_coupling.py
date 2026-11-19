"""DEFECT #68: a conductor's resistance must be evaluated where its loss is deposited.

The converter devices deposit their loss only inside the 49 cell footprints (IN_TILE_KEYS),
but the E-T loop fed the loss model the node mean of the WHOLE converter tiers, encapsulant
included: 7.8 K below the in-cell mean for the direct-fed Z2 and 1.2 K above it for Z1 at
HV-S0 (research/final_closure/superseded_pre_tile_temperature/diagnostic_conv_mean.txt).
These tests pin the corrected coupling and run the guard on the real defective regions."""
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

#: which ledger temperature key controls each term's resistance
KEY_OF = {"P_conv_hs": "hs", "P_conv_ls": "ls", "P_conv_inductor_dcr": "ind",
          "P_conv_cap_esr": "caps", "P_intraVR_metal": "conv", "P_intraVR_vertical": "conv",
          "P_TSV_VDD": "sub", "P_TSV_GND": "sub", "P_pad_VDD": "interface",
          "P_pad_GND": "interface", "P_VR_attach_VDD": "attach", "P_VR_attach_GND": "attach",
          "P_pkg_RDL_HV_supply": "bga", "P_pkg_RDL_HV_return": "bga",
          "P_BGA_supply": "bga", "P_BGA_return": "bga"}
#: the regions the E-T loop used before the fix (verbatim from final_closure_physical_etm
#: at the start of the corrected lineage): whole layers, no cell restriction
_flat = lambda *v: [x for y in v for x in (y if isinstance(y, list) else [y])]  # noqa: E731
DEFECTIVE = lambda lay: {"conv": (list(dict.fromkeys(_flat(lay["hs"], lay["ls"], lay["caps"],
                                                           lay["ind"]))) + lay["rdl"], False),
                         "bga": ([lay["bga"]], False), "sub": ([lay["tsv"]], False),
                         "interface": ([lay["pads"]], False)}
TEMPS = {"conv": 100.0, "hs": 100.0, "ls": 100.0, "ind": 100.0, "caps": 100.0, "bga": 70.0,
         "sub": 100.0, "interface": 100.0, "attach": 100.0}


def mismatches(arch, regions):
    """Every ledger term whose temperature region is not its deposit region."""
    import final_closure_ledger as FL
    import final_closure_physical_etm as E
    lay = FL.LAYERS[arch]
    tile_layers = set()
    for k in E.IN_TILE_KEYS:
        if k in lay:
            tile_layers.update(lay[k] if isinstance(lay[k], list) else [lay[k]])
    bad = []
    for r in FL.ledger(arch, "HV_S0", TEMPS, 23.7)["rows"]:
        if r["term"] not in KEY_OF or r["P_w"] <= 0:
            continue
        dep = tuple(r["deposit_layer"].split(","))
        in_t = all(x in tile_layers for x in dep)
        key = KEY_OF[r["term"]]
        if key not in regions:
            bad.append(f"{r['term']}: no temperature region for key {key!r}")
            continue
        layers, t_in = regions[key]
        if not set(dep) <= set(layers) or bool(t_in) != in_t:
            bad.append(f"{r['term']}: deposited in {dep} (in cells: {in_t}) but its "
                       f"temperature is the mean of {layers} (in cells: {t_in})")
    return bad


@pytest.mark.parametrize("arch", ["Z1", "Z2", "Z2BF"])
def test_every_term_is_evaluated_where_its_loss_is_deposited(arch):
    import final_closure_physical_etm as E
    assert mismatches(arch, E.temperature_regions(arch)) == []


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_guard_catches_the_real_defective_regions(arch):
    import final_closure_ledger as FL
    bad = mismatches(arch, DEFECTIVE(FL.LAYERS[arch]))
    assert any(t.startswith("P_conv_ls") for t in bad), bad
    assert any(t.startswith("P_TSV_VDD") for t in bad), bad


def test_each_device_term_follows_its_own_tier_temperature():
    """Prove the per-tier degree of freedom is free: heating only the low-side tier must
    raise only the low-side loss."""
    import final_closure_ledger as FL
    base = {r["term"]: r["P_w"] for r in FL.ledger("Z2", "HV_S0", TEMPS, 23.7)["rows"]}
    hot = {r["term"]: r["P_w"] for r in FL.ledger("Z2", "HV_S0", dict(TEMPS, ls=120.0),
                                                  23.7)["rows"]}
    moved = {k for k in base if abs(hot[k] - base[k]) > 1e-12}
    assert moved == {"P_conv_ls"}, moved
    assert hot["P_conv_ls"] > base["P_conv_ls"]


def test_production_cases_record_the_in_cell_tier_temperatures():
    files = sorted(D.glob("etm_Z[12]_HV_S*_h1.1_r21.json"))
    if not files:
        pytest.skip("no production case files")
    for f in files:
        h = json.loads(f.read_text())["et_history"][-1]
        for k in ("T_hs_C", "T_ls_C", "T_ind_C", "T_caps_C", "T_conv_C"):
            assert k in h, (f.name, k)


def test_an_older_lineage_file_never_enters_a_comparison():
    """A case file keeps its name until a rerun overwrites it (the BGA-fed r31 ladder files
    sat beside the corrected r21 cases for hours). Readers decide by content: the REAL
    superseded files -- the BGA-fed lineage and the pre-fix direct-fed case -- are refused."""
    import final_closure_physical_etm as E
    for f in (D / "superseded_bga_fed_z2" / "etm_Z1_HV_S0_h1.1_r31.json",
              D / "superseded_bga_fed_z2" / "etm_Z2_HV_S0_h1.1_r31.json",
              D / "superseded_bga_fed_z2" / "etm_Z2_HV_S0_h1.1_r21.json",
              D / "superseded_pre_tile_temperature" / "etm_Z1_HV_S0_h1.1_r21.json",
              D / "superseded_pre_tile_temperature" / "etm_Z2_HV_S0_h1.1_r21.json"):
        assert not E.current_lineage(json.loads(f.read_text())), f.name
    for a in ("Z1", "Z2"):
        for s in ("HV_S0", "HV_S1", "HV_S2"):
            f = E.case_path(a, s)
            if f.exists():
                assert E.current_lineage(json.loads(f.read_text())), f.name
