"""PHASE 0N-AJ --- BGA count as a SOLVED integer design variable.

THE LOOP THAT WAS NEVER CLOSED. The 16+16 count was obtained from
I_total / N_ball <= 1.5 A/ball. That criterion divides the total current by the
ball count, which presumes equal sharing -- and the voltage-fed network
DISPROVES equal sharing for this geometry. So the count was sized by an
assumption its own network contradicts, and the real peak ball current is
several times I_total/N.

The dependency is circular and must be iterated rather than evaluated once:

    N_BGA -> legal lattice sites -> placement rule -> network -> sharing
          -> I_ball,max -> required N_BGA

so this sweeps N, re-selects real lattice sites at each N, re-solves the
voltage-fed network, and reads the PEAK ball current out of the solution.

WHAT 1.5 A/ball IS. Searched across the repository: every occurrence
(phase0nr_z2_cutout_geometry, phase0nt_annular_pcb, tsv_fields.I_BALL_MAX_A,
the Z2 cutout notes) introduces it as "a conservative engineering
electromigration-style bound" or "BOUNDED provisioning rule, NOT an EM-safe
limit". No vendor datasheet, no DVPD source statement, no qualified allowable
for this alloy/geometry/temperature/waveform backs it. It is therefore
classified ENGINEERING_CRITERION and swept, and the solder-EM literature stays
CONTEXT_ONLY: those papers exist to show that an allowable depends on alloy,
temperature, waveform, joint geometry, grain orientation and crowding, which is
precisely why a single universal A/ball figure cannot be imported.

LINEARITY. The network is linear, so one unit-current solve per (arch, rail, N)
gives per-ball FRACTIONS; the actual peak current for any scenario is
fraction_max * I_scenario. Scenarios are kept apart and never merged into a
bracket.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_network as K                                           # noqa: E402
import pad_interface as PI                                           # noqa: E402
import physical_coords as PCO                                        # noqa: E402

OUT = R / "research" / "phase0naj"
OUT.mkdir(parents=True, exist_ok=True)

SWEEP_GRID = 301              # fractions are grid-stable to ~1.6 % vs n=601
VERIFY_GRID = K.VF_RESOLVED_GRID
COUNTS = (8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 200, 240)

I_BALL_CRITERION_A = 1.5
CRITERION_CLASS = "ENGINEERING_CRITERION"
CRITERION_PROVENANCE = (
    "no source. Introduced repo-wide as a 'conservative engineering "
    "electromigration-style bound' / 'BOUNDED provisioning rule, NOT an EM-safe "
    "limit'. Not a SOURCE_REQUIREMENT and not a VENDOR_REQUIREMENT; swept here "
    "rather than trusted, and no lifetime claim is attached to it")
A_BALL_MM2 = PI.BGA_A_UM2 * 1e-6


def scenarios(arch):
    import interconnect_loss as IL
    rb = IL.rms_scenarios(arch)
    return {"DC_AVERAGE": rb["hv_avg_a"], "HV_S0": rb["hv_S0_a"],
            "HV_S1": rb["hv_S1_a"], "HV_S2": rb["hv_S2_a"]}


def overlap_count(sites, cells, half, r_ball=0.2):
    return sum(1 for p in sites
               if any(abs(p[0] - cx) < half + r_ball and abs(p[1] - cy) < half + r_ball
                      for cx, cy in cells))


def sweep(n_grid=SWEEP_GRID):
    cells = PCO.physical_cell_coordinates()
    half = K.VR_TILE_SIDE_MM / 2
    rows = []
    for arch, cand in (("Z1", PCO.bga_lattice_sites()),
                       ("Z2", PCO.bga_lattice_sites(23.36))):
        sc = scenarios(arch)
        for N in COUNTS:
            # legality: mirror-symmetric pairs for BOTH rails out of one set
            if 2 * N > len(cand):
                rows.append({"arch": arch, "n_per_rail": N, "legal": False,
                             "reject": "not enough candidate sites for "
                                       "%d supply + %d return" % (N, N),
                             "n_candidates": len(cand)})
                continue
            try:
                sel = PCO.select_power_sites(cand, cells, N, N,
                                             "nearest_symmetric")
            except Exception as exc:                       # pragma: no cover
                rows.append({"arch": arch, "n_per_rail": N, "legal": False,
                             "reject": f"selection failed: {exc}"})
                continue
            if len(sel["supply"]) != N or len(sel["return"]) != N:
                rows.append({"arch": arch, "n_per_rail": N, "legal": False,
                             "reject": "lattice could not supply %d mirror pairs"
                                       % N})
                continue
            for rail in K.RAILS:
                r = K.solve_rail_vf(arch, rail, n_grid, 5.0e-3, 0.30,
                                    n_supply=N, n_return=N)
                frac = np.asarray(r["i_ball_a"])            # unit total current
                row = {
                    "arch": arch, "rail": rail, "n_per_rail": N, "legal": True,
                    "n_candidates": len(cand), "n_grid": n_grid,
                    "peak_fraction": float(frac.max()),
                    "mean_fraction": float(frac.mean()),
                    "imax_over_imean": float(frac.max() / frac.mean()),
                    "equal_share_fraction": 1.0 / N,
                    "peak_over_equal_share": float(frac.max() * N),
                    "r_eff_ohm": r["r_eff_ohm"],
                    "max_cell_drop_per_amp_v": r["max_cell_drop_v"],
                    "overlap_with_cell_tiles":
                        overlap_count(sel[rail], cells, half),
                }
                for name, i_tot in sc.items():
                    ib = frac.max() * i_tot
                    row[f"i_ball_max_A__{name}"] = ib
                    row[f"J_avg_A_per_cm2__{name}"] = ib / (A_BALL_MM2 * 1e-2)
                    row[f"pass_1p5A__{name}"] = bool(ib <= I_BALL_CRITERION_A)
                    row[f"drop_V__{name}"] = r["max_cell_drop_v"] * i_tot
                rows.append(row)
    return rows


def close(rows):
    """Smallest legal N meeting the criterion, PER SCENARIO. Never merged."""
    out = {}
    for arch in ("Z1", "Z2"):
        for name in ("DC_AVERAGE", "HV_S0", "HV_S1", "HV_S2"):
            ok = None
            for N in COUNTS:
                legs = [r for r in rows if r.get("legal") and r["arch"] == arch
                        and r["n_per_rail"] == N]
                if len(legs) != 2:
                    continue
                if all(r[f"pass_1p5A__{name}"] for r in legs):
                    ok = N
                    break
            # best achievable across the whole legal sweep, and where it occurs
            legal_rows = [r for r in rows if r.get("legal") and r["arch"] == arch]
            per_n = {}
            for r in legal_rows:
                per_n.setdefault(r["n_per_rail"], []).append(
                    r[f"i_ball_max_A__{name}"])
            per_n = {k: max(v) for k, v in per_n.items() if len(v) == 2}
            best_n = min(per_n, key=per_n.get) if per_n else None
            worst = per_n.get(best_n)
            largest_n = max(per_n) if per_n else None
            out[f"{arch}__{name}"] = {
                "required_n_per_rail": ok,
                "criterion_A": I_BALL_CRITERION_A,
                "status": "CLOSED" if ok else "NOT_SATISFIABLE_IN_SWEPT_RANGE",
                "note": ("" if ok else
                         "no swept count up to %d per rail brings the SOLVED peak "
                         "ball current under %.1f A; the deficit is not a counting "
                         "error but the sharing non-uniformity"
                         % (max(COUNTS), I_BALL_CRITERION_A)),
                "best_achievable_peak_A": None if worst is None else float(worst),
                "best_achievable_at_n_per_rail": best_n,
                "largest_legal_n_per_rail": largest_n,
                "peak_at_adopted_16": (None if per_n.get(16) is None
                                       else float(per_n[16])),
                "adopted_16_passes": bool(per_n.get(16) is not None
                                          and per_n[16] <= I_BALL_CRITERION_A),
            }
    return out


def main():
    t0 = time.time()
    rows = sweep()
    res = {
        "meta": {
            "phase": "0N-AJ",
            "criterion_A_per_ball": I_BALL_CRITERION_A,
            "criterion_classification": CRITERION_CLASS,
            "criterion_provenance": CRITERION_PROVENANCE,
            "em_literature_status": (
                "CONTEXT_ONLY -- solder EM reviews establish that an allowable "
                "depends on alloy, temperature, waveform, joint geometry, grain "
                "orientation, crowding and thermomigration, which is the reason "
                "no universal A/ball figure is imported here"),
            "sweep_grid": SWEEP_GRID,
            "verify_grid": VERIFY_GRID,
            "ball_area_mm2": A_BALL_MM2,
            "why_not_I_over_N": (
                "I_total/N_ball presumes equal sharing, which the voltage-fed "
                "network disproves; peak/equal-share ratios are reported per row"),
            "crowding": (
                "OPEN. J reported here is the AVERAGE over the ball cross "
                "section. Local peak current density at the pad/UBM transition "
                "is NOT modelled and no crowding multiplier is invented"),
        },
        "rows": rows,
        "closure": close(rows),
    }
    res["meta"]["wall_s"] = round(time.time() - t0, 1)
    (OUT / "bga_count_closure.json").write_text(json.dumps(res, indent=2))

    import csv
    legal = [r for r in rows if r.get("legal")]
    with (OUT / "bga_count_closure.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(legal[0]))
        w.writeheader()
        w.writerows(legal)
    for k, v in res["closure"].items():
        print("%-18s -> %-28s %s" % (k, v["status"],
                                     v["required_n_per_rail"] or ""))
    print("wall %.0f s" % res["meta"]["wall_s"])


if __name__ == "__main__":
    main()
