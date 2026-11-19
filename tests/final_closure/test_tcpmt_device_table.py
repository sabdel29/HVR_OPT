"""The GaN device table of the feasibility stage (tcpmt_feasibility.DEVICES): every part the
converter synthesis can select has a datasheet record, and the junction and R_DS(on)-fit checks
use each device's own limits.

Small tests: the synthesis summary is read, evaluate() runs on a synthetic case (no fields, no
solver, nothing written)."""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts", "scripts/phase0mr", "scripts/phase0d", "scripts/phase0nw"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
TR = R / "research" / "tcpmt_revision"
PART = re.compile(r"\bEPC\d{4}[A-Z]?\b")
CHECK_KEYS = {"value", "limit", "ok", "basis", "margin", "on_bound", "marginal"}


def selected_parts():
    """Every part of research/tcpmt_revision/dse_phase2_summary.json: the value of each 'hs' /
    'ls' key anywhere in the summary (and the parts of the tier stacks' 'gan_hs' / 'gan_ls',
    e.g. '1 x EPC2014C'), and the parts named in design_49_cell_full_set. A value without a
    part name is kept as it is (it then fails the table lookup)."""
    d = json.loads((TR / "dse_phase2_summary.json").read_text())
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("hs", "ls", "gan_hs", "gan_ls") and isinstance(v, str):
                    out.update(PART.findall(v) or [v])
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d)
    out |= set(PART.findall(json.dumps(d["design_49_cell_full_set"])))
    return out


def test_every_selected_part_has_a_datasheet_record():
    import tcpmt_feasibility as F
    parts = selected_parts()
    # the new design point and the 49-cell picks are among them (the scan is not vacuous)
    assert {"EPC2014C", "EPC2055", "EPC2057", "EPC2090"} <= parts
    assert not sorted(parts - set(F.DEVICES)), sorted(parts - set(F.DEVICES))
    for p in sorted(parts):
        d = F.DEVICES[p]
        for k in ("R_jc_K_W", "R_jb_K_W", "Tj_max_C", "V_DS_V", "I_D_A"):
            assert isinstance(d[k], (int, float)) and d[k] > 0, (p, k)
        assert len(d["die_mm"]) == 2 and min(d["die_mm"]) > 0, p
        assert isinstance(d.get("source"), str) and p in d["source"], p
        lo, hi = d["ron_fit_C"]
        assert lo < hi <= d["Tj_max_C"], p
        assert d["ron_curve_C"][0] <= lo and hi <= d["ron_curve_C"][1], p
        assert d["alpha_ron_per_K"] == pytest.approx((d["ron_norm_125C"] - 1.0) / 100.0), p


def test_epc2055_datasheet_values():
    """EPC2055 (the low side of the new design point), datasheet rev. June 20, 2025."""
    import tcpmt_feasibility as F
    d = F.DEVICES["EPC2055"]
    assert (d["V_DS_V"], d["I_D_A"], d["Tj_max_C"]) == (40.0, 29.0, 150.0)
    assert (d["R_jc_K_W"], d["R_jb_K_W"], d["R_ja_K_W"]) == (1.0, 2.5, 64.0)
    assert d["R_ds_on_max_mohm"] == 4.2 and d["die_mm"] == [2.5, 1.5]
    assert d["ron_curve_C"] == [0.0, 150.0] and d["ron_fit_C"] == [25.0, 125.0]
    assert d["ron_norm_125C"] == pytest.approx(1.60, abs=0.02)
    assert "June 20, 2025" in d["source"]


def test_production_parts_unchanged_and_match_the_model_coefficients():
    """EPC2014C / EPC2057 keep their datasheet values; the figure readings reproduce the
    coefficients scripts/phase0d/electrical.py sources from the same figures."""
    import electrical as EL
    import tcpmt_feasibility as F
    hs, ls = F.DEVICES["EPC2014C"], F.DEVICES["EPC2057"]
    assert (hs["Tj_max_C"], hs["R_jc_K_W"], hs["R_jb_K_W"], hs["die_mm"], hs["V_DS_V"],
            hs["I_D_A"]) == (150.0, 3.6, 9.3, [1.7, 1.1], 40.0, 10.0)
    assert (ls["Tj_max_C"], ls["R_jc_K_W"], ls["R_jb_K_W"], ls["die_mm"], ls["V_DS_V"],
            ls["I_D_A"]) == (150.0, 2.3, 7.0, [1.5, 1.2], 50.0, 9.6)
    assert hs["alpha_ron_per_K"] == pytest.approx(EL.ALPHA_GAN_HS, abs=2e-4)
    assert ls["alpha_ron_per_K"] == pytest.approx(EL.ALPHA_GAN_LS, abs=2e-4)


# ------------------------------------------------------------------ the checks use the table
def _case(hs="EPC2014C", ls="EPC2055", t_hs=100.0, t_ls=110.0):
    """A minimal resolved case: tier maxima recorded by the chain, 1 W per device."""
    n_vr, n, k = 49, 3, 3
    return {"arch": "Z1", "scenario": "HV_S0", "tier": "A", "et_converged": True,
            "design": {"n_vr": n_vr, "hs_part": hs, "ls_part": ls,
                       "topology": {"N": n, "K": k}},
            "thermal": {"T_max_C": 140.0,
                        "region_T_max_C": {"hs_in_cells": t_hs, "ls_in_cells": t_ls}},
            "ledger_rows": [{"term": "P_conv_hs", "P_w": 1.0 * n_vr * n},
                            {"term": "P_conv_ls", "P_w": 1.0 * n_vr * k}]}


def _evaluate(F, tmp_path, **kw):
    return F.evaluate(tmp_path / "etm_Z1_HV_S0__device_table_unit.json", _case(**kw),
                      use_fields=False)


def test_ron_fit_uses_each_devices_own_range(tmp_path, monkeypatch):
    import tcpmt_feasibility as F
    # junctions: hs 100 + 1 W x 3.6 K/W = 103.6 C, ls 110 + 1 W x 1.0 K/W = 111.0 C
    c = _evaluate(F, tmp_path)["checks"]["ron_fit"]
    assert set(c) == CHECK_KEYS
    assert c["limit"] == 125.0 and c["value"] == pytest.approx(111.0) and c["ok"] is True
    devs = copy.deepcopy(F.DEVICES)
    devs["EPC2014C"]["ron_fit_C"] = [25.0, 100.0]
    monkeypatch.setattr(F, "DEVICES", devs)
    c = _evaluate(F, tmp_path)["checks"]["ron_fit"]
    # the cooler high side is outside ITS fit range: it binds, the check fails
    assert set(c) == CHECK_KEYS
    assert c["limit"] == 100.0 and c["value"] == pytest.approx(103.6)
    assert c["ok"] is False and c["margin"] == pytest.approx(-3.6)
    assert "hs EPC2014C" in c["basis"] and "binding: hs" in c["basis"]
    # no fit range recorded: the declared LIMITS value
    for p in ("EPC2014C", "EPC2055"):
        devs[p].pop("ron_fit_C")
    c = _evaluate(F, tmp_path)["checks"]["ron_fit"]
    assert c["limit"] == F.LIMITS["ron_fit_max_C"] and c["value"] == pytest.approx(111.0)


def test_gan_junction_uses_each_devices_own_maximum(tmp_path, monkeypatch):
    import tcpmt_feasibility as F
    ch = _evaluate(F, tmp_path)["checks"]
    assert ch["gan_Tj_hs"]["limit"] == F.DEVICES["EPC2014C"]["Tj_max_C"]
    assert ch["gan_Tj_ls"]["value"] == pytest.approx(111.0)
    devs = copy.deepcopy(F.DEVICES)
    devs["EPC2055"]["Tj_max_C"] = 105.0
    monkeypatch.setattr(F, "DEVICES", devs)
    r = _evaluate(F, tmp_path)
    assert r["checks"]["gan_Tj_ls"]["limit"] == 105.0 and r["checks"]["gan_Tj_ls"]["ok"] is False
    assert r["checks"]["gan_Tj_hs"]["ok"] is True and "gan_Tj_ls" in r["fails"]
    # a part without a record: unresolved against the declared limit
    r = _evaluate(F, tmp_path, ls="EPC9999")
    c = r["checks"]["gan_Tj_ls"]
    assert c["value"] is None and c["ok"] is None and c["limit"] == F.LIMITS["gan_Tj_C"]
