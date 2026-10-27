"""PHASE 0N-AJ --- the source-pad count as an ADMISSIBLE REGION.

The old selector was the tautology min(n_geom, max(n_drop, n_geom)) == n_geom,
so it always chose maximum density and called it closed. It was withdrawn and
nothing replaced it, leaving a 1227x loss span between the voltage-drop floor
(4 pads/rail/cell) and the geometric ceiling (4908).

No single count can be justified here, and this does not pretend otherwise.
Minimising loss drives the count to the geometric ceiling; satisfying voltage
drop alone permits the floor. Choosing between them needs a lifetime or
current-density allowable for THIS pad metallurgy, geometry, temperature and
waveform, and no such allowable is transferable from the literature available:
Cu-Cu bump studies operate near 1e6 A/cm^2 as an ACCELERATED STRESS condition,
which is a regime marker and not a rating. The defensible output is therefore
a constraint-bounded admissible region plus the Pareto trade, with the
current-density axis reported and flagged rather than silently resolved.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pad_interface as PAD                                          # noqa: E402
import rms_currents as RMS                                           # noqa: E402

OUT = R / "research" / "phase0naj"
OUT.mkdir(parents=True, exist_ok=True)

#: declared current-density constraint cases, A/cm^2. NONE is an allowable.
J_CASES = {
    "J_NONE": None,
    "J_1e4": 1.0e4,
    "J_1e5": 1.0e5,
    "J_1e6": 1.0e6,     # the Cu-Cu ACCELERATED-STRESS regime, a marker not a limit
}
J_STATUS = ("DECLARED ENGINEERING CONSTRAINT CASES. J_1e6 is where "
            "10.3390/ma14216394 observes Cu-Cu bump electromigration under "
            "ACCELERATED stress; an accelerated test condition is evidence about "
            "failure physics, not a safe operating limit, so it is used here to "
            "mark a regime and never as a rating. CONTEXT_ONLY.")
DROP_BUDGET_FRAC = 0.01


def main():
    cc = RMS.cell_currents()
    i_cell = cc["i_cell_out_rms_a"]
    base = PAD.size_for_cell(i_cell)
    n_lo = base["PAD_DROP"]["n_per_rail"]
    n_hi = base["PAD_GEOM_MAX"]["n_per_rail"]
    r_one = PAD.pad_bulk_resistance_ohm(20.0)
    cells, rails = 49, 2
    a_pad_cm2 = PAD.PAD_A_UM2 * 1e-8

    counts = sorted({n_lo, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048,
                     4096, n_hi})
    counts = [n for n in counts if n_lo <= n <= n_hi]
    rows = []
    for n in counts:
        r_rail = r_one / n
        i_pad = i_cell / n
        p_sys = rails * cells * i_cell ** 2 * r_rail
        rows.append({
            "n_per_rail": n,
            "r_rail_ohm": r_rail,
            "i_per_pad_a": i_pad,
            "j_per_pad_A_cm2": i_pad / a_pad_cm2,
            "v_drop_v": i_cell * r_rail,
            "v_drop_pct_of_1V": 100 * i_cell * r_rail,
            "p_system_both_rails_w": p_sys,
            "area_utilisation_frac": n / n_hi,
            "meets_drop_budget": bool(i_cell * r_rail <= DROP_BUDGET_FRAC),
            "at_drop_floor": n == n_lo,
            "at_geometric_ceiling": n == n_hi,
        })

    admissible = {}
    for name, jmax in J_CASES.items():
        ok = [r["n_per_rail"] for r in rows
              if r["meets_drop_budget"]
              and (jmax is None or r["j_per_pad_A_cm2"] <= jmax)]
        admissible[name] = {
            "j_max_A_cm2": jmax,
            "n_min": min(ok) if ok else None,
            "n_max": max(ok) if ok else None,
            "n_admissible_count": len(ok),
            "status": "NON_EMPTY" if ok else "EMPTY",
            "loss_at_n_min_w": next((r["p_system_both_rails_w"] for r in rows
                                     if ok and r["n_per_rail"] == min(ok)), None),
            "loss_at_n_max_w": next((r["p_system_both_rails_w"] for r in rows
                                     if ok and r["n_per_rail"] == max(ok)), None),
        }

    lo_w = rows[0]["p_system_both_rails_w"]
    hi_w = rows[-1]["p_system_both_rails_w"]
    res = {
        "meta": {
            "phase": "0N-AJ",
            "i_cell_rms_a": i_cell,
            "pad_area_um2": PAD.PAD_A_UM2,
            "r_one_pad_ohm": r_one,
            "drop_budget_frac_of_1V": DROP_BUDGET_FRAC,
            "n_drop_floor": n_lo,
            "n_geometric_ceiling": n_hi,
            "loss_span_factor": lo_w / hi_w,
            "j_cases_status": J_STATUS,
            "selection_status": "ADMISSIBLE_REGION_ONLY",
            "why_no_single_count": (
                "loss is monotonically decreasing in N and voltage drop is "
                "satisfied from N = %d upward, so every criterion available "
                "here is one-sided: nothing bounds N from above except geometry. "
                "A unique optimum would require a lifetime or current-density "
                "allowable for this pad metallurgy, geometry, temperature and "
                "waveform, which no accessible source provides. Reporting a "
                "single adopted count would be reinstating the withdrawn "
                "tautology under a new name." % n_lo),
            "drop_floor_current_density_A_cm2": rows[0]["j_per_pad_A_cm2"],
            "drop_floor_verdict": (
                "NON-PHYSICAL. At the voltage-drop floor N = %d each pad carries "
                "%.3f A through %.0f um^2, i.e. %.2e A/cm^2 -- about %.0fx the "
                "~1e6 A/cm^2 at which Cu-Cu bump electromigration is studied under "
                "ACCELERATED stress. The drop budget is therefore not the binding "
                "constraint anywhere in this design space: current density is. The "
                "old 'voltage-drop floor of 4 pads/rail/cell' was never a candidate "
                "design point, only an artefact of applying one criterion in "
                "isolation." % (n_lo, rows[0]["i_per_pad_a"], PAD.PAD_A_UM2,
                                rows[0]["j_per_pad_A_cm2"],
                                rows[0]["j_per_pad_A_cm2"] / 1e6)),
            "crowding": ("OPEN -- j_per_pad is the AVERAGE over the pad area. "
                         "Local crowding at the pad/UBM transition is not "
                         "modelled and no multiplier is invented"),
        },
        "rows": rows,
        "admissible_region": admissible,
    }
    (OUT / "pad_count_closure.json").write_text(json.dumps(res, indent=2))
    with (OUT / "pad_count_closure.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("i_cell_rms = %.4f A ; floor N=%d ; ceiling N=%d ; loss span %.0fx"
          % (i_cell, n_lo, n_hi, lo_w / hi_w))
    for k, v in admissible.items():
        print("  %-8s jmax=%-8s -> N in [%s, %s]  (%d counts)"
              % (k, v["j_max_A_cm2"], v["n_min"], v["n_max"],
                 v["n_admissible_count"]))


if __name__ == "__main__":
    main()
