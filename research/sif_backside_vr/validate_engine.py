#!/usr/bin/env python3
"""Si-IF backside VR study -- check of the overlay against the engine's own selection.

With the core loss and the two catalog gates (peak current, RMS current) switched off, the
overlay's selection (sif_core.build_table + one-tier scan of sif_sweep) must reproduce the
engine's optimize_architecture (mixed tiers, HVR_MAX_TIERS=1, same keep-out, area budget
I_cell / J) -- same loss, or lower only where the overlay's extra MaxRects orderings place a
design the engine's single placement attempt misses. Also checks that the buck reduces to the
textbook expressions.

    python validate_engine.py [--ind-lib inductor_library.json]
Writes validate_engine.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import sif_core as S  # noqa: E402
import sif_sweep as W  # noqa: E402

H = S.H


def engine_pick(arch, I, J, V_in, df, inds, caps):
    d0 = S.H.row_to_device(df.iloc[0])
    res = H.optimize_architecture(arch, df, inds, caps, W.F_GRID, d0, d0, inds[0], caps[0], 5e5,
                                  I_out=I, V_out=1.0, V_in=V_in, V_gs_drive=5.0,
                                  ripple_factor=0.5, v_ripple_frac=0.25,
                                  area_budget_mm2=I / J)
    if res.optimized_hs_device is None:
        return None
    return {"loss": res.optimized_loss, "hs": res.optimized_hs_device.part_number,
            "ls": res.optimized_ls_device.part_number, "ind": res.optimized_inductor.name,
            "cap": res.optimized_capacitor.name, "f": res.optimized_f_sw}


def overlay_pick(arch, I, J, V_in, df, inds, caps, ko):
    opts = S.Opts(peak_isat=False, irms=False, core_loss=False)
    W._G.update(opts=opts)
    t = S.build_table(arch, I, V_in, 1.0, df, inds, caps, W.F_GRID, opts)
    if t is None:
        return None
    sc = W.Scanner(t)
    res = W.scan_all(sc, I, V_in, ["power"], [ko], [J])
    k = res[("power", ko, J)][0]
    if k is None:
        return None
    r = W.design_record(sc, k, V_in, 1000.0 / I, "power", ko, J)
    return {"loss": r["loss_cell_W"], "hs": r["hs"], "ls": r["ls"], "ind": r["inductor"],
            "cap": r["capacitor"], "f": r["f_sw_Hz"]}


def buck_textbook(hs, ls, ind, I, V_in, f):
    D = 1.0 / V_in
    L = ind.l_nh * 1e-9
    dI = (V_in - 1.0) * D / (f * L)
    Irms2 = I ** 2 + dI ** 2 / 12
    cond = Irms2 * (D * hs.R_DS_ON + (1 - D) * ls.R_DS_ON + ind.r_dcr_mohm * 1e-3)
    Ig = (5.0 - 0.5 * (1.0 + 1.6)) / (H.gate_resistance(hs) + 0.7)
    ov = f * (V_in - 1.0) * math.sqrt(Irms2) * (hs.Q_GD + hs.Q_G) / Ig
    gate = f * (hs.Q_G + ls.Q_G) * 5.0
    coss = f * (H.e_oss_at(hs, V_in) + H.q_oss_at(ls, V_in) * V_in - H.e_oss_at(ls, V_in))
    return cond + ov + gate + coss


_CTX: dict = {}


def _case(case):
    """Engine and overlay picks of one case (the engine's optimize_architecture also takes the
    buck architecture, which its generator does not emit)."""
    V_in, a, I, J = case
    c = _CTX
    return (engine_pick(a, I, J, V_in, c["df"], c["inds"], c["caps"]),
            overlay_pick(a, I, J, V_in, c["df"], c["inds"], c["caps"], c["ko"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ind-lib", default=os.path.join(HERE, "inductor_library.json"))
    ap.add_argument("--procs", type=int, default=30)
    args = ap.parse_args()
    assert H.MAX_TIERS == 1 and H.pack_enabled() and H.TIER_RULE == "mixed"
    ko = H.PACK_KEEPOUT_UM
    df, _ = S.load_devices()
    inds = S.build_inductor_library(args.ind_lib)
    caps = S.build_capacitor_library()
    out = {"keepout_um": ko, "cases": []}
    cases = []
    for V_in in (48.0, 12.0):
        archs = S.architectures(V_in, 1.0, 4)
        for a in archs:
            if a.N >= 2 and (a.N, a.K) not in ((2, 2), (3, 2), (3, 3), (4, 2), (4, 4)):
                continue
            for I in (10.0, 25.0, 50.0):
                for J in (0.2, 0.5, 0.8):
                    cases.append((V_in, a, I, J))
    n_eq = n_lower = n_higher = n_both_none = n_mismatch_none = 0
    import multiprocessing as mp
    _CTX.update(df=df, inds=inds, caps=caps, ko=ko)
    with mp.Pool(args.procs) as pool:
        picks = pool.map(_case, cases, chunksize=1)
    for (V_in, a, I, J), (e, o) in zip(cases, picks):
        rec = {"V_in": V_in, "arch": f"N{a.N}K{a.K}", "I": I, "J": J, "engine": e, "overlay": o}
        if e is None and o is None:
            n_both_none += 1
            rec["verdict"] = "both infeasible"
        elif e is None or o is None:
            rec["verdict"] = "overlay feasible, engine not" if e is None else "ENGINE ONLY"
            n_mismatch_none += 1 if o is None else 0
            n_lower += 1 if e is None else 0
        elif abs(e["loss"] - o["loss"]) <= 1e-9 * e["loss"]:
            n_eq += 1
            rec["verdict"] = "equal"
        elif o["loss"] < e["loss"]:
            n_lower += 1
            rec["verdict"] = "overlay lower"
        else:
            n_higher += 1
            rec["verdict"] = "OVERLAY HIGHER"
        out["cases"].append(rec)
        print(rec["V_in"], rec["arch"], I, J, rec["verdict"],
              (round(e["loss"], 4) if e else None), (round(o["loss"], 4) if o else None), flush=True)
    # buck: engine expressions vs textbook
    a = S.arch_buck(12.0, 1.0)
    hs = H.row_to_device(df[df.PartNumber == "EPC2055"].iloc[0])
    ls = H.row_to_device(df[df.PartNumber == "EPC2066"].iloc[0])
    ind = inds[0]
    ev = S.evaluate(a, hs, ls, ind, caps[0], 20.0, 12.0, 1.0, 1e6, S.Opts(core_loss=False))
    tb = buck_textbook(hs, ls, ind, 20.0, 12.0, 1e6)
    out["buck_check"] = {"engine_W": ev["engine_loss_cell_W"], "textbook_W": tb,
                         "rel_diff": abs(ev["engine_loss_cell_W"] - tb) / tb}
    out["summary"] = {"cases": len(cases), "equal": n_eq, "overlay_lower": n_lower,
                      "overlay_higher": n_higher, "both_infeasible": n_both_none,
                      "engine_only_feasible": n_mismatch_none}
    print(json.dumps(out["summary"]), json.dumps(out["buck_check"]))
    json.dump(out, open(os.path.join(HERE, "validate_engine.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
