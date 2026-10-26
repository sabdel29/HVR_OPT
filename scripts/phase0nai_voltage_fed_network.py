"""PHASE 0N-AI --- the package network, voltage-fed and closed.

Five things the previous package-RDL model got wrong, and what replaces each:

1. IMPOSED SHARING. Current was injected as i_total/n at every ball, so equal
   sharing was an input. Replaced by a rail node feeding each ball through its
   own Table III series resistance; sharing is now an output, and it is not
   equal even under a uniform load.
2. THE RETURN CONDUCTOR WAS DISCARDED. Return sites were selected and never
   used. Supply and return are now two separate sheets solved separately and
   added in series.
3. POINT INJECTION. Replaced by area-overlap stamping whose overlaps sum to
   the true contact area at every refinement.
4. AN UNRESOLVED CONTACT CALLED CONVERGED. A 400 um ball needs h <~ 50 um; the
   old study stopped at h = 0.3 mm and checked R_eff only. Convergence is now
   declared on five metrics including the peak ball current, which settles
   last, at grids that resolve the ball.
5. A DUPLICATE CONTROL. allocation_rule='inner_edge' ran the same ranking
   expression as 'nearest_symmetric' and returned identical sites on both
   candidate sets; it is withdrawn.
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
import pad_interface as PI                                            # noqa: E402
import physical_coords as PCO                                         # noqa: E402

OUT = R / "research" / "phase0nai"
OUT.mkdir(parents=True, exist_ok=True)


def asymmetry_demonstration(n_grid=401):
    """The test the imposed-current model could not fail.

    Under the old right-hand side every ball carried exactly i_total/16 by
    construction. Here a uniform load already produces unequal currents, and
    concentrating half the load on one corner cell widens the spread further.
    """
    cells = PCO.physical_cell_coordinates()
    out = {}
    for tag, i in (("UNIFORM", np.full(len(cells), 1.0 / len(cells))),
                   ("CORNER_HEAVY", None)):
        if i is None:
            i = np.full(len(cells), 0.5 / (len(cells) - 1))
            i[int(np.argmax([x * x + y * y for x, y in cells]))] = 0.5
        r = K.solve_rail_vf("Z1", "supply", n_grid, 5.0e-3, 0.30, i_cells=i)
        ib = np.asarray(r["i_ball_a"])
        out[tag] = {
            "i_ball_min_a": float(ib.min()), "i_ball_max_a": float(ib.max()),
            "i_ball_mean_a": float(ib.mean()),
            "spread_pct_of_mean": float(100 * (ib.max() - ib.min()) / ib.mean()),
            "imposed_value_would_be_a": 1.0 / len(ib),
            "r_eff_ohm": r["r_eff_ohm"],
            "kcl_residual_a": abs(r["i_ball_sum_a"] - r["i_total_a"]),
            "energy_residual_rel": r["energy_residual_rel"],
        }
    return out


def contact_sensitivity(n_grid=K.VF_RESOLVED_GRID):
    """rho_c is OUR parameter, not the source's -- so its leverage is reported."""
    rows = []
    for arch in ("Z1", "Z2"):
        for case, rho in K.RHO_C_CASES.items():
            legs = {r: K.solve_rail_vf(arch, r, n_grid, 5.0e-3, 0.30,
                                       rho_c_ball=rho, rho_c_cell=rho)
                    for r in K.RAILS}
            rows.append({
                "arch": arch, "contact_case": case, "rho_c_ohm_mm2": rho,
                "r_supply_ohm": legs["supply"]["r_eff_ohm"],
                "r_return_ohm": legs["return"]["r_eff_ohm"],
                "r_loop_ohm": (legs["supply"]["r_eff_ohm"]
                               + legs["return"]["r_eff_ohm"]),
            })
    return rows


def main():
    t0 = time.time()
    res = {
        "meta": {
            "phase": "0N-AI",
            "feed": "VOLTAGE_FED",
            "r_ball_ohm": PI.bga_ball_resistance_ohm(),
            "r_ball_provenance": ("DVPD Table III BGA column, rho_solder*h/A; "
                                  "the table's own 0.3 mOhm is pure bulk and "
                                  "carries NO contact term"),
            "rho_c_status": K.RHO_C_STATUS,
            "resolved_grid": K.VF_RESOLVED_GRID,
            "conv_metrics": list(K.VF_CONV_METRICS),
            "conv_threshold": K.VF_CONV_THRESH,
        },
        "asymmetry": asymmetry_demonstration(),
        "convergence": {},
        "loop": {},
    }
    for arch in ("Z1", "Z2"):
        for rail in K.RAILS:
            c = K.converge_rail_vf(arch, rail)
            res["convergence"][f"{arch}_{rail}"] = {
                "converged": c["converged"], "deltas": c["deltas"],
                "worst_metric": c["worst_metric"], "worst_delta": c["worst_delta"],
                "threshold_declared": c["threshold_declared"],
                "levels": [{k: v for k, v in L.items() if k != "i_ball_a"}
                           for L in c["levels"]],
            }
        res["loop"][arch] = {
            k: v for k, v in K.loop_resistance_vf(arch).items() if k != "legs"}
    res["controlled"] = K.controlled_cutout_experiment_vf()
    res["contact_sensitivity"] = contact_sensitivity()
    res["allocation_rule_withdrawn"] = {
        "rule": "inner_edge",
        "finding": ("ran sorted(candidate_sites, key=dist), the same expression "
                    "as nearest_symmetric, and returned identical supply AND "
                    "return sites on the full lattice and on the Z2 annulus"),
        "action": "raises NotImplementedError rather than silently duplicating",
    }
    res["meta"]["wall_s"] = round(time.time() - t0, 1)
    (OUT / "voltage_fed_network.json").write_text(json.dumps(res, indent=2))
    print("wrote", OUT / "voltage_fed_network.json", "in", res["meta"]["wall_s"], "s")
    for a in ("Z1", "Z2"):
        L = res["loop"][a]
        print("%s  R_supply=%.4f  R_return=%.4f  R_loop=%.4f mOhm"
              % (a, L["r_supply_ohm"] * 1e3, L["r_return_ohm"] * 1e3,
                 L["r_loop_ohm"] * 1e3))
    c = res["controlled"]
    print("dR_cutout=%+.4f  dR_placement=%+.4f mOhm  ratio=%.2f"
          % (c["delta_R_cutout_ohm"] * 1e3, c["delta_R_placement_ohm"] * 1e3,
             c["placement_over_cutout"]))


if __name__ == "__main__":
    main()
