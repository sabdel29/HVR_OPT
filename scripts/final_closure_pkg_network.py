"""FINAL CLOSURE --- the production package HV network, at the count it will use.

Supersedes research/phase0nak for the paper lineage. Two things changed:

1. The sheet is solved on the aligned, graded finite-volume grid
   (pkg_rdl_refined), which converges where the uniform grid could not.
2. The cell terminal is the converter's own traced 0.2 mm VIN pad
   (routing.tile_layout), not the untraced full 2.3685 mm tile.

Both change the per-ball current fractions, so the exhaustive count screen is
re-run on this model rather than reused: a count closure computed on a model
the paper no longer uses would be a stale number with a current label.

Two analyses are kept apart, as the scope requires:
  A. ARCHITECTURE COMPARISON at one MATCHED count, legal and passing HV-S0 for
     both architectures, so count optimisation is not confounded with
     architecture.
  B. PROVISIONING SENSITIVITY: architecture-specific minima, non-monotonicity,
     and the dependence on the unsourced 1.5 A/ball engineering criterion.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_refined as RF                                         # noqa: E402
import pkg_rdl_network as K                                          # noqa: E402
import physical_coords as PCO                                        # noqa: E402

OUT = R / "research" / "final_closure"
OUT.mkdir(parents=True, exist_ok=True)
I_CRIT_A = 1.5
SCREEN_LEVEL, VERIFY_LEVEL, FINAL_LEVELS = 1, 2, (1, 2, 3)
SCEN = ("DC_AVERAGE", "HV_S0", "HV_S1", "HV_S2")
WORKERS = int(os.environ.get("FC_WORKERS", "32"))


def scenarios(arch):
    import interconnect_loss as IL
    rb = IL.rms_scenarios(arch)
    return {"DC_AVERAGE": rb["hv_avg_a"], "HV_S0": rb["hv_S0_a"],
            "HV_S1": rb["hv_S1_a"], "HV_S2": rb["hv_S2_a"]}


def legal_counts(arch, n_max=250):
    cells = PCO.physical_cell_coordinates()
    cand = PCO.bga_lattice_sites(K.architecture_cutout_mm(arch))
    ok = []
    for n in range(2, n_max + 1, 2):
        if 2 * n > len(cand):
            break
        try:
            s = PCO.select_power_sites(cand, cells, n, n, "nearest_symmetric")
        except Exception:
            continue
        if len(s["supply"]) == n and len(s["return"]) == n:
            ok.append(n)
    return ok


def _job(args):
    arch, rail, n, level, kw = args
    r = RF.solve_rail(arch, rail, n, level, **kw)
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items()
            if k not in ("cell_drop_v",)}


def run_pool(jobs):
    with Pool(min(WORKERS, len(jobs))) as p:
        return p.map(_job, jobs, chunksize=1)


def peak_rows(results):
    """Combine supply/return solves into one row per (arch, n, level)."""
    by = {}
    for r in results:
        key = (r["arch"], r["n_per_rail"], r["level"], r["terminal_mode"])
        by.setdefault(key, {})[r["rail"]] = r
    rows = []
    for (arch, n, lv, mode), d in sorted(by.items()):
        if set(d) != {"supply", "return"}:
            continue
        sc = scenarios(arch)
        row = {"arch": arch, "n_per_rail": n, "level": lv, "terminal_mode": mode}
        for rail in ("supply", "return"):
            x = d[rail]
            row[f"{rail}_peak_fraction"] = x["i_ball_max_a"]
            row[f"{rail}_r_eff_ohm"] = x["r_eff_ohm"]
            row[f"{rail}_imax_over_imean"] = x["ball_imax_over_imean"]
            row[f"{rail}_max_drop_per_A"] = x["max_cell_drop_v"]
        pk = max(row["supply_peak_fraction"], row["return_peak_fraction"])
        row["peak_fraction"] = pk
        for s, i in sc.items():
            row[f"i_ball_max_A__{s}"] = pk * i
            row[f"pass__{s}"] = bool(pk * i <= I_CRIT_A)
        rows.append(row)
    return rows


def main():
    t0 = time.time()
    counts = {a: legal_counts(a) for a in ("Z1", "Z2")}
    kw = {"mode": "VIN_PAD"}
    # ---- 1. exhaustive screen ------------------------------------------
    jobs = [(a, rail, n, SCREEN_LEVEL, kw) for a in counts for n in counts[a]
            for rail in ("supply", "return")]
    screen = peak_rows(run_pool(jobs))
    print(f"screen: {len(screen)} rows in {time.time()-t0:.0f}s", flush=True)

    # ---- 2. verify candidate minima on the resolved level ---------------
    closure, verify_jobs = {}, set()
    for a in counts:
        for s in SCEN:
            ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r[f"pass__{s}"]]
            if ok:
                n0 = min(ok)
                for n in (n0 - 2, n0, n0 + 2):
                    if n in counts[a]:
                        verify_jobs.add((a, n))
    vj = [(a, rail, n, VERIFY_LEVEL, kw) for a, n in sorted(verify_jobs)
          for rail in ("supply", "return")]
    verify = peak_rows(run_pool(vj)) if vj else []
    vby = {(r["arch"], r["n_per_rail"]): r for r in verify}
    for a in counts:
        for s in SCEN:
            ok = [r["n_per_rail"] for r in screen if r["arch"] == a and r[f"pass__{s}"]]
            if not ok:
                best = min(screen, key=lambda r: r[f"i_ball_max_A__{s}"]
                           if r["arch"] == a else 1e99)
                closure[f"{a}__{s}"] = {
                    "status": "NOT_SATISFIABLE_AT_ANY_LEGAL_COUNT",
                    "best_peak_A": best[f"i_ball_max_A__{s}"],
                    "best_at_n": best["n_per_rail"],
                    "largest_legal_count": counts[a][-1], "criterion_A": I_CRIT_A}
                continue
            n0 = min(ok)
            v = vby.get((a, n0))
            lo = vby.get((a, n0 - 2))
            passes = bool(v and v[f"pass__{s}"])
            lower_fails = (lo is None) or (not lo[f"pass__{s}"])
            fail_above = [r["n_per_rail"] for r in screen
                          if r["arch"] == a and r["n_per_rail"] > n0
                          and not r[f"pass__{s}"]]
            closure[f"{a}__{s}"] = {
                "status": ("CLOSED" if passes and lower_fails else
                           "SCREEN_ONLY_NOT_VERIFIED" if not passes else
                           "NOT_MINIMAL_LOWER_COUNT_ALSO_PASSES"),
                "n_min": n0, "verified_level": VERIFY_LEVEL,
                "peak_at_n_min_A": v[f"i_ball_max_A__{s}"] if v else None,
                "peak_at_lower_A": lo[f"i_ball_max_A__{s}"] if lo else None,
                "larger_counts_that_FAIL": fail_above,
                "criterion_A": I_CRIT_A}
    print("closure:", {k: (v["status"], v.get("n_min")) for k, v in closure.items()},
          flush=True)

    # ---- 3. matched count: smallest N passing HV-S0 for BOTH, verified ---
    common = sorted(set(counts["Z1"]) & set(counts["Z2"]))
    cand = [n for n in common
            if all(next((r[f"pass__HV_S0"] for r in screen
                         if r["arch"] == a and r["n_per_rail"] == n), False)
                   for a in ("Z1", "Z2"))]
    n_match = None
    for n in cand:
        vj = [(a, rail, n, VERIFY_LEVEL, kw) for a in ("Z1", "Z2")
              for rail in ("supply", "return")]
        v = {r["arch"]: r for r in peak_rows(run_pool(vj))}
        if all(v[a]["pass__HV_S0"] for a in ("Z1", "Z2")):
            n_match = n
            break
    print("matched count:", n_match, flush=True)

    # ---- 4. converged networks at the matched count ----------------------
    fj = [(a, rail, n_match, lv, kw) for a in ("Z1", "Z2")
          for rail in ("supply", "return") for lv in FINAL_LEVELS]
    fres = run_pool(fj)
    conv = {}
    for a in ("Z1", "Z2"):
        for rail in ("supply", "return"):
            rr = sorted([r for r in fres if r["arch"] == a and r["rail"] == rail],
                        key=lambda r: r["level"])
            fine, mid = rr[-1], rr[-2]
            d = {m: abs(fine[m] - mid[m]) / abs(fine[m]) for m in RF.CONV_METRICS}
            conv[f"{a}_{rail}"] = {
                "deltas": d, "worst_metric": max(d, key=d.get),
                "worst_delta": max(d.values()), "converged": max(d.values()) < RF.CONV_THRESH,
                "levels": [{k: v for k, v in r.items() if k not in ("i_ball_a",
                                                                     "ball_xy")}
                           for r in rr],
                "final": {k: fine[k] for k in ("r_eff_ohm", "max_cell_drop_v",
                                               "i_ball_max_a", "ball_imax_over_imean",
                                               "n_cv", "energy_residual_rel")},
                "i_ball_frac": fine["i_ball_a"], "ball_xy": fine["ball_xy"]}
    loop = {}
    for a in ("Z1", "Z2"):
        rs = conv[f"{a}_supply"]["final"]["r_eff_ohm"]
        rr = conv[f"{a}_return"]["final"]["r_eff_ohm"]
        sc = scenarios(a)
        loop[a] = {"n_per_rail": n_match, "r_supply_ohm": rs, "r_return_ohm": rr,
                   "r_loop_ohm": rs + rr,
                   "converged": conv[f"{a}_supply"]["converged"]
                                and conv[f"{a}_return"]["converged"],
                   "loss_w": {s: i ** 2 * (rs + rr) for s, i in sc.items()},
                   "i_scenario_a": sc}

    # ---- 5. controlled cutout experiment at the matched count -----------
    full, cut = PCO.bga_lattice_sites(), PCO.bga_lattice_sites(23.36)
    cj = []
    for tag, c, rule in (("CTRL_FULL", full, "nearest_symmetric"),
                         ("CTRL_CUTOUT", cut, "nearest_symmetric"),
                         ("CTRL_CUTOUT_OUTER", cut, "outer_perimeter")):
        for rail in ("supply", "return"):
            cj.append(("CTRL", rail, n_match, VERIFY_LEVEL,
                       dict(kw, candidate_override=c, allocation_rule=rule)))
    K.register_architecture("CTRL", None)
    cres = run_pool(cj)
    ctrl = {}
    for (tag, _, rule), i in zip((("CTRL_FULL", 0, 0), ("CTRL_CUTOUT", 0, 0),
                                  ("CTRL_CUTOUT_OUTER", 0, 0)), range(3)):
        s_, r_ = cres[2 * i], cres[2 * i + 1]
        ctrl[tag] = {"r_supply_ohm": s_["r_eff_ohm"], "r_return_ohm": r_["r_eff_ohm"],
                     "r_loop_ohm": s_["r_eff_ohm"] + r_["r_eff_ohm"]}
    ctrl["delta_R_cutout_ohm"] = (ctrl["CTRL_CUTOUT"]["r_loop_ohm"]
                                  - ctrl["CTRL_FULL"]["r_loop_ohm"])
    ctrl["delta_R_placement_ohm"] = (ctrl["CTRL_CUTOUT_OUTER"]["r_loop_ohm"]
                                     - ctrl["CTRL_CUTOUT"]["r_loop_ohm"])

    # ---- 6. sensitivities at the matched count --------------------------
    sens_jobs = []
    for a in ("Z1", "Z2"):
        for mode in ("HALF_TILE", "FULL_TILE"):
            for rail in ("supply", "return"):
                sens_jobs.append((a, rail, n_match, VERIFY_LEVEL, {"mode": mode}))
        for cname, rho in K.RHO_C_CASES.items():
            for rail in ("supply", "return"):
                sens_jobs.append((a, rail, n_match, VERIFY_LEVEL,
                                  {"mode": "VIN_PAD", "rho_c": rho}))
        for tc, oc in ((2e-3, 0.30), (5e-3, 0.80), (10e-3, 0.30), (10e-3, 0.80)):
            for rail in ("supply", "return"):
                sens_jobs.append((a, rail, n_match, VERIFY_LEVEL,
                                  {"mode": "VIN_PAD", "t_cu_mm": tc, "occupancy": oc}))
    sres = run_pool(sens_jobs)
    sens = {}
    for r in sres:
        key = (r["arch"], r["terminal_mode"], r["rho_c_ohm_mm2"], r["t_cu_mm"],
               r["occupancy"])
        sens.setdefault(key, {})[r["rail"]] = r["r_eff_ohm"]
    sens_rows = [{"arch": k[0], "terminal_mode": k[1], "rho_c_ohm_mm2": k[2],
                  "t_cu_mm": k[3], "occupancy": k[4],
                  "r_loop_ohm": v["supply"] + v["return"]}
                 for k, v in sorted(sens.items()) if len(v) == 2]

    res = {"meta": {"model": "pkg_rdl_refined aligned graded FV, traced VIN pad",
                    "terminal_status": RF.TERMINAL_MODES["VIN_PAD"],
                    "criterion_A_per_ball": I_CRIT_A,
                    "criterion_classification": "ENGINEERING_CRITERION",
                    "screen_level": SCREEN_LEVEL, "verify_level": VERIFY_LEVEL,
                    "final_levels": list(FINAL_LEVELS),
                    "levels_mm": {str(k): v for k, v in RF.LEVELS.items()},
                    "conv_threshold": RF.CONV_THRESH,
                    "conv_metrics": list(RF.CONV_METRICS),
                    "exhaustive": True, "monotonicity_assumed": False,
                    "wall_s": round(time.time() - t0, 1)},
           "counts_legal": {a: len(v) for a, v in counts.items()},
           "closure": closure, "matched_count": n_match,
           "convergence": conv, "loop": loop, "controlled": ctrl,
           "sensitivity": sens_rows}
    (OUT / "package_network.json").write_text(json.dumps(res, indent=1))
    with (OUT / "bga_count_screen.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(screen[0]))
        w.writeheader(); w.writerows(screen)
    print("done in %.0fs" % (time.time() - t0))
    for a, L in loop.items():
        print(a, "N=%d R_loop=%.4f mOhm conv=%s" % (L["n_per_rail"],
              L["r_loop_ohm"] * 1e3, L["converged"]))


if __name__ == "__main__":
    main()
