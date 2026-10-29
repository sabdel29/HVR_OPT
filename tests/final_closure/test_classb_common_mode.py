"""The converter-rescaling judge (elec.individual_branch_waveforms) states on which side of
k_flip the modelled ordering holds. With the in-cell temperatures (DEFECT #68) the direct-fed
Z2's converter rows came out 0.011 W ABOVE Z1's while everything else favours Z2 by 1.03 W,
and the judge printed 'Z2 lower for every k > 91.230' -- the ordering actually holds for
every k BELOW 91.23. The ledger values here are the real HV-S0 rows of that run."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))

#: the exact verdict the sign-blind judge wrote (FINAL_PAPER_DECISION.md, 2026-10-28 22:21)
STALE = "Z2 lower for every k > 91.230"
#: converter + intra-VR rows and the remainder, HV-S0, electrical_ledger.json 2026-10-28 22:20
REAL = {"Z1": {"P_conv_hs": 21.404333422832043, "P_conv_ls": 105.73192375006936,
               "P_conv_inductor_dcr": 14.375559617654783, "P_conv_cap_esr": 1.4402242934280696,
               "P_intraVR_metal": 1.8952559059241034, "P_intraVR_vertical": 2.3459067004363363,
               "rest": 1.8639613927526568},
        "Z2": {"P_conv_hs": 21.43833021360111, "P_conv_ls": 105.4177299389499,
               "P_conv_inductor_dcr": 14.634588568660597, "P_conv_cap_esr": 1.4402242934280696,
               "P_intraVR_metal": 1.909763121591693, "P_intraVR_vertical": 2.363863417696996,
               "rest": 0.833435013328824}}


def _judge(monkeypatch, led):
    import final_closure_classB as C
    rows = [{"arch": a, "scenario": "HV_S0", "term": t, "P_w": v}
            for a, terms in led.items() for t, v in terms.items()]
    monkeypatch.setattr(C, "J", lambda p: {"rows": rows})
    return C.judge_common_mode()[0]


def _delta(led, k):
    conv = lambda a: sum(v for t, v in led[a].items() if t != "rest")
    return (k * conv("Z1") + led["Z1"]["rest"]) - (k * conv("Z2") + led["Z2"]["rest"])


def test_the_real_ledger_reads_below_the_flip(monkeypatch):
    r = _judge(monkeypatch, REAL)
    assert r["verdict"] != STALE
    assert r["verdict"] == "Z2 lower for every k < 91.230", r["verdict"]
    assert _delta(REAL, 1.0) > 0 and _delta(REAL, 90.0) > 0 and _delta(REAL, 92.0) < 0
    assert r["robust"] is False             # the sign does not hold for every k >= 0.5


def test_every_sign_combination_names_the_side_that_holds(monkeypatch):
    def led(c1, c2, r1, r2):
        return {"Z1": {"P_conv_ls": c1, "rest": r1}, "Z2": {"P_conv_ls": c2, "rest": r2}}
    for case in (led(101, 100, 0.0, 0.5), led(100, 101, 2.0, 0.0),    # flip below / above 1
                 led(100, 101, 0.0, 0.5), led(101, 100, 0.0, 2.0),
                 led(101, 100, 1.0, 0.0), led(100, 101, 0.0, 1.0)):  # no flip at all
        r = _judge(monkeypatch, case)
        lead, rest = r["verdict"].split(" lower for every k ")
        assert (lead == "Z2") == (_delta(case, 1.0) > 0), r
        side, k = rest.split(" ")
        k = float(k)
        for kk in (k * 0.5, k * 2.0) if k > 0 else (0.5, 2.0):
            holds = (kk > k) if side == ">" else (kk < k)
            if holds:                       # wherever the verdict says it holds, it does
                assert (_delta(case, kk) > 0) == (lead == "Z2"), (r, kk)
