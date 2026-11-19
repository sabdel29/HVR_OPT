"""Regulator-count screen, TCPMT revision phase 2: datasheet gate resistance, capacitor body
footprints, mixed tiers with a tier limit, counts extended down to 16.

Runs (case D, research/tcpmt_revision/dse_j35/data/), written by scripts/tcpmt_dse_phase2_runs.sh
with the sweep driver research/tcpmt_revision/dse_j35/sweep_etm.py:
  etm35_p2_legacycheck  the six legacy flags, 17 counts           must equal etm35 (published)
  etm35_p2_t4           (i)   full set, at most 4 tiers (the current stack depth)
  etm35_p2_tinf         (ii)  full set, no tier limit
  etm35_p2_t5           (iii) full set, at most 5 tiers
Full set: corrected capacitor rule, switch rule (derating 0.9), corrected C_OSS, packing with a
50-um keep-out, datasheet R_G, capacitor body footprints, mixed tiers. Tier count and stack height
of each pick come from the engine's stack_plan (minimum tiers, then minimum height; tier height =
tallest part; RDL_UM between tiers).

    python tcpmt_dse_phase2_summary.py -> research/tcpmt_revision/dse_phase2_summary.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"  # campaign hook
D = TR / "dse_j35" / "data"
SIVR = R / "Scalable_Integrated_VR"
sys.path.insert(0, str(SIVR / "src"))
import HVR_FULL_OPT_EPC_V2 as H  # noqa: E402

V_IN, V_OUT, P_LOAD, J = 48.0, 1.0, 1000.0, 3.5
SQUARES = (16, 25, 36, 49, 64, 81)
RUNS = {"etm35_p2_t4": ("i", "full set, at most 4 tiers", 4),
        "etm35_p2_tinf": ("ii", "full set, no tier limit", 0),
        "etm35_p2_t5": ("iii", "full set, at most 5 tiers", 5)}
FULL_ENV = ("HVR_CAP_RULE=stress HVR_SW_RULE=stress HVR_SW_DERATING=0.9 HVR_COSS_RULE=corrected "
            "HVR_PACK_RULE=on HVR_PACK_KEEPOUT_UM=50 HVR_RG_RULE=datasheet "
            "HVR_FOOTPRINT_RULE=body HVR_TIER_RULE=mixed")
LEGACY_ENV = ("HVR_CAP_RULE=legacy HVR_SW_RULE=legacy HVR_COSS_RULE=legacy HVR_PACK_RULE=off "
              "HVR_RG_RULE=legacy HVR_FOOTPRINT_RULE=legacy")
#: the engine snapshot the sweeps ran (its md5 goes into the record): the campaign's
#: HVR_DSE_ENGINE (prep.dse_engine), else the phase-2 snapshot of the development runs
ENGINE = Path(os.environ.get("HVR_DSE_ENGINE")
              or "/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine_phase2")
KEEP_UM = 50.0

DEV = {r["PartNumber"]: H.row_to_device(r) for _, r in
       H.load_epc_devices(str(SIVR / "EPC-Product-Table.csv"), V_gs_op=5.0).iterrows()}
IND = {i.name: i for i in H.INDUCTOR_LIBRARY}
CAP = {c.name: c for c in H.default_capacitor_library("stress")}


def load(tag):
    p = D / f"case_D_{tag}.csv"
    return {int(float(r["M"])): r for r in csv.DictReader(p.open())} if p.exists() else {}


def arch_of(label):
    n, k, ka = (int(x.split("=")[1]) for x in label.split(","))
    return H.VRArchitecture(N=n, K=k, K_A=ka, B_array=H.generate_B_array(n, k, ka),
                            D=n * V_OUT / V_IN, component_count=0)


def parts_of(r):
    return DEV[r["hs"]], DEV[r["ls"]], IND[r["inductor"]], CAP[r["capacitor"]]


def side_of(m):
    return math.sqrt(P_LOAD / m / J)


def stack_of(r, m, placement=False):
    hs, ls, ind, cap = parts_of(r)
    return H.stack_plan(arch_of(r["arch"]), hs, ls, ind, cap, side_of(m), KEEP_UM,
                        placement=placement)


def row_summary(r, m):
    if r is None or r.get("feasible") != "True":
        return None
    st = stack_of(r, m)
    hs, ls, ind, cap = parts_of(r)
    return {"square": m in SQUARES, "arch": r["arch"], "hs": r["hs"], "ls": r["ls"],
            "inductor": r["inductor"], "capacitor": r["capacitor"],
            "f_sw_kHz": round(float(r["f_sw_Hz"]) / 1e3, 2),
            "conv_per_cell_W": round(float(r["conv_loss_per_vr_W"]), 5),
            "conv_total_W": round(float(r["conv_loss_total_W"]), 3),
            "routing_W": round(float(r["routing_loss_W"]), 3),
            "P_total_W": round(float(r["total_loss_W"]), 3),
            "cell_side_mm": round(side_of(m), 4), "component_count": int(float(r["component_count"])),
            "tiers": st["tiers"], "stack_height_um": round(st["height_um"], 1),
            "height_known": st["height_known"],
            "part_heights_um": {"hs": H.part_height_um(hs)[0], "ls": H.part_height_um(ls)[0],
                                "inductor": H.part_height_um(ind)[0],
                                "capacitor": H.part_height_um(cap)[0]},
            "tiers_plan": st["plan"]}


def tier_margins(r, m):
    """Per tier of the pick: parts, coordinates (grown by the keep-out), the largest keep-out at
    which the tier still places, and the smallest cell side that holds it at 50 um."""
    st = stack_of(r, m, placement=True)
    a = arch_of(r["arch"])
    hs, ls, ind, cap = parts_of(r)
    raw = {"gan_hs": (hs, a.N), "gan_ls": (ls, a.K), "inductor": (ind, a.K),
           "cap_fly": (cap, a.N - 1)}
    side = round(side_of(m), 9)
    out = []
    for t in st["plan"]:
        comp = {c: n for c, n in t.items() if c in raw}

        def fits(k_mm, s=side):
            cd = []
            for c, n in comp.items():
                x, y = H.part_dims_mm(raw[c][0])
                cd.append(((round(max(x, y) + k_mm, 9), round(min(x, y) + k_mm, 9)), n))
            return H._multiset_fits(tuple(sorted(cd)), round(s, 9))
        lo, hi = KEEP_UM * 1e-3, 3.0
        if fits(hi):
            kmax = hi
        else:
            while hi - lo > 1e-4:
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if fits(mid) else (lo, mid)
            kmax = lo
        s_lo, s_hi = 0.0, side
        while s_hi - s_lo > 1e-4:
            mid = 0.5 * (s_lo + s_hi)
            s_lo, s_hi = (s_lo, mid) if fits(KEEP_UM * 1e-3, mid) else (mid, s_hi)
        out.append({"parts": {c: f"{n} x {raw[c][0].part_number if c.startswith('gan') else raw[c][0].name}"
                              for c, n in comp.items()},
                    "part_dims_mm": {c: H.part_dims_mm(raw[c][0]) for c in comp},
                    "tier_height_um": t["height_um"],
                    "placement_mm_grown_by_keepout": [
                        (round(x, 4), round(y, 4), round(w, 4), round(h, 4), tag)
                        for x, y, w, h, tag in (t.get("placement_mm") or [])],
                    "keepout_headroom_um": round(1e3 * kmax - KEEP_UM, 1),
                    "max_keepout_um": round(1e3 * kmax, 1),
                    "min_cell_side_mm": round(s_hi, 4), "cell_side_mm": round(side, 4),
                    "side_slack_mm": round(side - s_hi, 4)})
    return {"tiers": st["tiers"], "stack_height_um": st["height_um"],
            "height_known": st["height_known"], "rdl_um_per_interface": H.RDL_UM, "per_tier": out}


def legacy_check(tag="etm35_p2_legacycheck", ref="etm35"):
    out = {}
    for stem in ("case_A", "case_B", "case_C", "case_D", "all_architectures"):
        a, b = D / f"{stem}_{tag}.csv", D / f"{stem}_{ref}.csv"
        if not a.exists():
            out[stem] = None
            continue
        ra, rb = list(csv.DictReader(a.open())), list(csv.DictReader(b.open()))
        cols = list(rb[0].keys())
        out[stem] = {"rows_equal_on_reference_columns":
                     len(ra) == len(rb) and all(x.get(c) == y[c] for x, y in zip(ra, rb)
                                                for c in cols),
                     "extra_columns": sorted(set(ra[0]) - set(cols))}
    return {"env": LEGACY_ENV, "reference": ref, "files": out,
            "reproduces_reference": all(v and v["rows_equal_on_reference_columns"]
                                        for v in out.values())}


def run_block(tag, label, what, mt):
    rows = load(tag)
    per = {m: row_summary(rows[m], m) for m in sorted(rows)}
    feas = {m: s for m, s in per.items() if s}
    opt = min(feas, key=lambda m: feas[m]["P_total_W"]) if feas else None
    sq = {m: (feas[m]["P_total_W"] if m in feas else None) for m in SQUARES}
    sq_ok = {m: v for m, v in sq.items() if v is not None}
    best_sq = min(sq_ok, key=sq_ok.get) if sq_ok else None
    return {"label": label, "what": what, "max_tiers": mt or None,
            "env": FULL_ENV + f" HVR_MAX_TIERS={mt}",
            "optimum": None if opt is None else {"M": opt, **feas[opt]},
            "square_grid_P_total_W": sq, "best_square_grid": best_sq,
            "best_square_grid_stack": (None if best_sq is None else
                                       tier_margins(rows[best_sq], best_sq)),
            "M49": per.get(49), "feasible_counts": sorted(feas), "per_count": per}


def stats_rerun():
    """The conservative cases of the tier checks (mixed tiers that no exact test settles) at
    two counts, from a fresh synthesis under (i)."""
    old = {k: getattr(H, k) for k in ("MAX_TIERS", "TIER_RULE", "PACK_RULE")}
    H.PACK_STATS.clear()
    H.PACK_STATS.update(exact_searches=0, undecided=0)
    H._COMP_CACHE.clear()
    H._STACK_CACHE.clear()
    cwd = os.getcwd()
    try:
        H.MAX_TIERS, H.TIER_RULE, H.PACK_RULE = 4, "mixed", "on"
        os.chdir(SIVR)
        for m in (36, 49):
            for cc in (10, 15):
                H.run_hvr_optimization(target_component_count=cc, V_in=V_IN, V_out=V_OUT,
                                       I_out=P_LOAD / m, V_gs_drive=5.0, ripple_factor=0.5,
                                       v_ripple_frac=0.25, I_target_density=J, verbose=False)
    finally:
        os.chdir(cwd)
        for k, v in old.items():
            setattr(H, k, v)
    return dict(H.PACK_STATS)


def robustness_check():
    """Picks of (i) and (iii) at M = 36 and 49 again with far larger exact-placement budgets
    (400k nodes, exact search up to 6 parts, guillotine frontier up to 9): unchanged picks mean
    the conservative tier checks did not decide them."""
    keys = ("PLACE_NODE_LIMIT", "MIXED_EXACT_MAX_ITEMS", "FRONTIER_MAX_ITEMS", "MAX_TIERS",
            "TIER_RULE", "PACK_RULE")
    old = {k: getattr(H, k) for k in keys}
    out = {}
    cwd = os.getcwd()
    try:
        H.PLACE_NODE_LIMIT, H.MIXED_EXACT_MAX_ITEMS, H.FRONTIER_MAX_ITEMS = 400000, 6, 9
        H.TIER_RULE, H.PACK_RULE = "mixed", "on"
        H._COMP_CACHE.clear()
        H._STACK_CACHE.clear()
        os.chdir(SIVR)
        for mt in (4, 5):
            H.MAX_TIERS = mt
            for m in (36, 49):
                budget = P_LOAD / m / J
                ccs = sorted(c for c in ({10, 15} | {c for c in (22, 30) if budget / 0.48 > c * 0.75})
                             if c <= 30)
                best = None
                for cc in ccs:
                    for r in H.run_hvr_optimization(target_component_count=cc, V_in=V_IN,
                                                    V_out=V_OUT, I_out=P_LOAD / m, V_gs_drive=5.0,
                                                    ripple_factor=0.5, v_ripple_frac=0.25,
                                                    I_target_density=J, verbose=False):
                        if np.isfinite(r.optimized_loss) and r.area_feasible and (
                                best is None or r.optimized_loss < best.optimized_loss):
                            best = r
                a = best.architecture
                out[f"max_tiers_{mt}_M{m}"] = {
                    "arch": f"N={a.N},K={a.K},K_A={a.K_A}",
                    "hs": best.optimized_hs_device.part_number,
                    "ls": best.optimized_ls_device.part_number,
                    "f_sw_kHz": round(best.optimized_f_sw / 1e3, 2),
                    "conv_per_cell_W": best.optimized_loss, "tiers": best.n_tiers}
    finally:
        os.chdir(cwd)
        for k, v in old.items():
            setattr(H, k, v)
        H._COMP_CACHE.clear()
        H._STACK_CACHE.clear()
    return out


def main():
    out = {"what": __doc__.split("\n\n")[0],
           "driver": "research/tcpmt_revision/dse_j35/sweep_etm.py",
           "launcher": "scripts/tcpmt_dse_phase2_runs.sh",
           "engine_snapshot": {"path": str(ENGINE), "md5": {
               f.name: hashlib.md5(f.read_bytes()).hexdigest()
               for f in sorted(ENGINE.glob("*")) if f.is_file()} if ENGINE.exists() else None},
           "assumptions": {
               "R_G": "datasheet RG (typ) of the high-side part, 81 of 90 parts; the other 9 "
                      "(EPC7xxx, EPC210x) take the median 0.4 Ohm (HVR_epc_device_data.json)",
               "Q_OSS_test_voltage": "datasheet test V_DS where it differs from V_DS,max/2 and the "
                                     "datasheet Q_OSS equals the table (9 parts, e.g. 50 V for "
                                     "EPC2204A/2218A/2202/2252/2203)",
               "capacitor_footprints": "body area: 0603 1.28, 0805 2.5, 1206 5.12 mm2",
               "tiers": "a tier may hold parts of different classes; placement with a 50-um "
                        "keep-out (25 um to the cell edge) in the square cell of side sqrt(I/J)",
               "heights_um": "EPC parts: datasheet Side View nominal mounted height incl. the "
                             "terminal (HVR_epc_device_data.json); inductor tier 500 (library); "
                             "flying capacitor 1000 = 0603 body 0.8 mm + 0.2 mm tolerance margin",
               "rdl_um": f"{H.RDL_UM} per inter-tier interface (production-cell convention)",
               "placement_exactness": "one class per tier: exact; mixed tiers up to 3 parts "
                                      "exact (guillotine), 4-6 parts exact for guillotine "
                                      "layouts plus a budgeted search for pinwheels at 4, more "
                                      "than 6 parts constructive (MaxRects); unresolved cases "
                                      "count as not placeable (tier counts can only be high)"},
           "legacy_reproduction": legacy_check(),
           "runs": {tag: run_block(tag, *v) for tag, v in RUNS.items()}}
    # the 49-cell design under the full set (one design, not a selection)
    a49 = arch_of("N=3,K=3,K_A=2")
    st = H.stack_plan(a49, DEV["EPC2014C"], DEV["EPC2057"], IND["Shared_Core_UIC_250_nH"],
                      CAP["Murata-GRM188D72A105KE01-1uF-100V"], side_of(49), KEEP_UM)
    lr = H.compute_total_loss(a49, H.LossModelInputs(
        DEV["EPC2014C"], DEV["EPC2057"], IND["Shared_Core_UIC_250_nH"],
        CAP["Murata-GRM188D72A105KE01-1uF-100V"], P_LOAD / 49, V_OUT, V_IN, 805170.3343770516))
    out["design_49_cell_full_set"] = {
        "design": "N3K3K_A2 EPC2014C/EPC2057 805 kHz, Shared_Core_UIC_250_nH, GRM188 0603",
        "tiers": st["tiers"], "stack_height_um": st["height_um"], "plan": st["plan"],
        "conv_per_cell_W_at_fixed_fsw_esr_library": lr.total_loss}
    out["tier_check_conservative_cases_M36_M49"] = stats_rerun()
    rb = robustness_check()
    for key, v in rb.items():
        mt, m = int(key.split("_")[2]), int(key.split("M")[-1])
        tag = {4: "etm35_p2_t4", 5: "etm35_p2_t5"}[mt]
        s_ = out["runs"][tag]["per_count"].get(m)
        v["same_as_sweep_pick"] = bool(bool(s_) and (s_["arch"], s_["hs"], s_["ls"]) == (
            v["arch"], v["hs"], v["ls"]) and abs(s_["conv_per_cell_W"] - v["conv_per_cell_W"]) < 1e-5)
    out["robustness_larger_placement_budgets"] = rb
    (TR / "dse_phase2_summary.json").write_text(json.dumps(out, indent=1, default=float))
    brief = {}
    for tag, v in out["runs"].items():
        brief[tag] = {"opt": v["optimum"] and (v["optimum"]["M"], v["optimum"]["arch"],
                                               v["optimum"]["hs"], v["optimum"]["ls"],
                                               v["optimum"]["P_total_W"], v["optimum"]["tiers"],
                                               v["optimum"]["stack_height_um"]),
                      "sq": v["square_grid_P_total_W"], "best_sq": v["best_square_grid"],
                      "feasible": v["feasible_counts"]}
    print(json.dumps({"legacy": out["legacy_reproduction"]["reproduces_reference"],
                      "runs": brief}, indent=1, default=str))


if __name__ == "__main__":
    main()
