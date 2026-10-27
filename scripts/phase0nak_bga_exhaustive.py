"""PHASE 0N-AK --- exhaustive BGA count closure, screened then VERIFIED.

The Phase-0N-AJ sweep sampled {8,12,16,20,24,32,40,48,...}. A sampled first
passing point is not a minimum: if 32 fails and 40 passes, 34/36/38 were never
tried, and Z2's first passing sample of 24 never showed that 22 fails. It also
read its minima off the n=301 screening grid while declaring n=601 the resolved
one, so no adopted count was ever verified where the 400 um ball is resolved.

This enumerates EVERY legal mirror-symmetric even count, screens all of them on
a coarse grid, and then re-solves the candidate minimum and its neighbours on
the resolved grid. Monotonicity is NEVER assumed: changing N changes which
sites the placement rule selects, so the peak current is not required to fall
with N, and the artifact records the largest FAILING count above each candidate
minimum so non-monotonicity is visible rather than hidden.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_network as K                                          # noqa: E402
import pad_interface as PI                                           # noqa: E402
import physical_coords as PCO                                        # noqa: E402

OUT = R / "research" / "phase0nak"
OUT.mkdir(parents=True, exist_ok=True)

SCREEN_GRID = 201
VERIFY_GRID = K.VF_RESOLVED_GRID          # 601
I_CRIT_A = 1.5
A_BALL_MM2 = PI.BGA_A_UM2 * 1e-6
N_MAX = 250


def scenarios(arch):
    import interconnect_loss as IL
    rb = IL.rms_scenarios(arch)
    return {"DC_AVERAGE": rb["hv_avg_a"], "HV_S0": rb["hv_S0_a"],
            "HV_S1": rb["hv_S1_a"], "HV_S2": rb["hv_S2_a"]}


def legal_counts(cand, cells, n_max=N_MAX):
    out = []
    for N in range(2, n_max + 1, 2):
        if 2 * N > len(cand):
            break
        try:
            sel = PCO.select_power_sites(cand, cells, N, N, "nearest_symmetric")
        except Exception:
            continue
        if len(sel["supply"]) == N and len(sel["return"]) == N:
            out.append(N)
    return out


def solve_point(arch, N, grid, cells, half):
    row = {"arch": arch, "n_per_rail": N, "n_grid": grid}
    for rail in K.RAILS:
        r = K.solve_rail_vf(arch, rail, grid, 5.0e-3, 0.30,
                            n_supply=N, n_return=N)
        f = np.asarray(r["i_ball_a"])
        sel = PCO.select_power_sites(
            PCO.bga_lattice_sites(K.architecture_cutout_mm(arch)),
            cells, N, N, "nearest_symmetric")[rail]
        row.update({
            f"{rail}_peak_fraction": float(f.max()),
            f"{rail}_mean_fraction": float(f.mean()),
            f"{rail}_imax_over_imean": float(f.max() / f.mean()),
            f"{rail}_peak_over_equal_share": float(f.max() * N),
            f"{rail}_r_eff_ohm": r["r_eff_ohm"],
            f"{rail}_max_cell_drop_per_A": r["max_cell_drop_v"],
            f"{rail}_overlap_with_tiles": sum(
                1 for p in sel
                if any(abs(p[0] - cx) < half + 0.2 and abs(p[1] - cy) < half + 0.2
                       for cx, cy in cells)),
        })
    row["peak_fraction"] = max(row[f"{r}_peak_fraction"] for r in K.RAILS)
    return row


def annotate(row, sc):
    for name, i_tot in sc.items():
        ib = row["peak_fraction"] * i_tot
        row[f"i_ball_max_A__{name}"] = ib
        row[f"J_avg_A_cm2__{name}"] = ib / (A_BALL_MM2 * 1e-2)
        row[f"pass__{name}"] = bool(ib <= I_CRIT_A)
    return row


def main():
    t0 = time.time()
    cells = PCO.physical_cell_coordinates()
    half = K.VR_TILE_SIDE_MM / 2
    screen, verify, closure = [], [], {}

    for arch in ("Z1", "Z2"):
        cand = PCO.bga_lattice_sites(K.architecture_cutout_mm(arch))
        sc = scenarios(arch)
        counts = legal_counts(cand, cells)
        print("%s: %d legal even counts, %d..%d"
              % (arch, len(counts), counts[0], counts[-1]), flush=True)
        for N in counts:
            screen.append(annotate(solve_point(arch, N, SCREEN_GRID, cells, half), sc))
        print("  screened in %.0f s" % (time.time() - t0), flush=True)

        for name in sc:
            passing = [r["n_per_rail"] for r in screen
                       if r["arch"] == arch and r[f"pass__{name}"]]
            if not passing:
                closure[f"{arch}__{name}"] = {
                    "status": "NOT_SATISFIABLE_AT_ANY_LEGAL_COUNT",
                    "n_min_screen": None, "verified": False,
                    "largest_legal_count": counts[-1],
                    "best_peak_A": min(r[f"i_ball_max_A__{name}"] for r in screen
                                       if r["arch"] == arch),
                    "criterion_A": I_CRIT_A}
                continue
            n_cand = min(passing)
            failing_above = [n for n in counts if n > n_cand
                             and not next(r[f"pass__{name}"] for r in screen
                                          if r["arch"] == arch
                                          and r["n_per_rail"] == n)]
            # VERIFY on the resolved grid: the candidate and its neighbours
            probes = sorted({n for n in (n_cand - 2, n_cand, n_cand + 2)
                             if n in counts})
            vres = {}
            for n in probes:
                hit = [v for v in verify
                       if v["arch"] == arch and v["n_per_rail"] == n]
                row = hit[0] if hit else annotate(
                    solve_point(arch, n, VERIFY_GRID, cells, half), sc)
                if not hit:
                    verify.append(row)
                vres[n] = row
            ok = vres[n_cand][f"pass__{name}"]
            lower = n_cand - 2
            lower_fails = (lower not in vres) or (not vres[lower][f"pass__{name}"])
            closure[f"{arch}__{name}"] = {
                "status": ("CLOSED" if (ok and lower_fails)
                           else "SCREEN_ONLY_NOT_VERIFIED" if not ok
                           else "NOT_MINIMAL_LOWER_COUNT_ALSO_PASSES"),
                "n_min_screen": n_cand,
                "n_min_verified": n_cand if ok else None,
                "verified_at_grid": VERIFY_GRID,
                "verified": bool(ok),
                "lower_count_tested": lower if lower in vres else None,
                "lower_count_fails": bool(lower_fails),
                "peak_at_n_min_A": vres[n_cand][f"i_ball_max_A__{name}"],
                "peak_at_lower_A": (vres[lower][f"i_ball_max_A__{name}"]
                                    if lower in vres else None),
                "larger_counts_that_FAIL": failing_above,
                "monotone_above_minimum": not failing_above,
                "criterion_A": I_CRIT_A,
            }
            print("  %s %-11s -> %s N=%s (verified %s)"
                  % (arch, name, closure[f"{arch}__{name}"]["status"],
                     n_cand, ok), flush=True)

    res = {"meta": {"phase": "0N-AK", "screen_grid": SCREEN_GRID,
                    "verify_grid": VERIFY_GRID, "criterion_A_per_ball": I_CRIT_A,
                    "criterion_classification": "ENGINEERING_CRITERION",
                    "exhaustive": True,
                    "monotonicity_assumed": False,
                    "wall_s": round(time.time() - t0, 1)},
           "screen": screen, "verify": verify, "closure": closure}
    (OUT / "bga_exhaustive_closure.json").write_text(json.dumps(res, indent=2))
    with (OUT / "bga_exhaustive_screen.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(screen[0]))
        w.writeheader()
        w.writerows(screen)
    print("wall %.0f s" % res["meta"]["wall_s"])


if __name__ == "__main__":
    main()
