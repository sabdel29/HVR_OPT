"""Why Z1 does not converge when Z2 does --- a controlled diagnostic.

Z1 has failed its convergence test in three successive phases while Z2 passed.
Previous phases recorded the symptom. This isolates a cause.

OBSERVATION. Z1 selects supply and return sites from the FULL lattice by
nearest-to-centroid, so some balls land directly beneath a VR cell tile. Z2
cannot: the 23.36 mm cutout removes exactly the central sites, pushing its
balls out to an annulus. A ball stamped onto the same sheet nodes as a cell
contact couples to that cell through the two contact conductances rather than
through the sheet, and the strength of that near-short is set by rho_c --- our
declared parameter --- and by how the overlap region is discretised.

TEST. Remove from Z1's candidate set every site whose contact would overlap a
cell tile, change NOTHING else, and re-run the identical grid sweep.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))
import pkg_rdl_network as K                                           # noqa: E402
import physical_coords as PCO                                         # noqa: E402

OUT = R / "research" / "phase0nai"
LEVELS = (401, 501, 601)          # same 501->601 step as the main study
R_BALL_MM = 0.2


def overlaps(p, cells, half):
    return any(abs(p[0] - cx) < half + R_BALL_MM and abs(p[1] - cy) < half + R_BALL_MM
               for cx, cy in cells)


def main():
    t0 = time.time()
    cells = PCO.physical_cell_coordinates()
    half = K.VR_TILE_SIDE_MM / 2
    base = json.loads((OUT / "voltage_fed_network.json").read_text())

    counts, clean = {}, {}
    for arch, cand in (("Z1", PCO.bga_lattice_sites()),
                       ("Z2", PCO.bga_lattice_sites(23.36))):
        sel = PCO.select_power_sites(cand, cells, 16, 16, "nearest_symmetric")
        counts[arch] = {rail: sum(1 for p in sel[rail] if overlaps(p, cells, half))
                        for rail in K.RAILS}
        clean[arch] = [p for p in cand if not overlaps(p, cells, half)]

    res = {
        "hypothesis": ("Z1's non-convergence is caused by supply/return balls "
                       "landing beneath VR cell tiles, which Z2's cutout "
                       "geometrically prevents"),
        "levels": list(LEVELS),
        "overlapping_balls_of_16": counts,
        "candidate_sites": {a: {"all": len(PCO.bga_lattice_sites()
                                           if a == "Z1"
                                           else PCO.bga_lattice_sites(23.36)),
                                "non_overlapping": len(clean[a])}
                            for a in ("Z1", "Z2")},
        "baseline": {k: {"worst_metric": v["worst_metric"],
                         "worst_delta": v["worst_delta"],
                         "converged": v["converged"]}
                     for k, v in base["convergence"].items()},
        "no_overlap": {},
    }
    for rail in K.RAILS:
        c = K.converge_rail_vf("Z1", rail, levels=LEVELS,
                               candidate_override=clean["Z1"])
        res["no_overlap"][f"Z1_{rail}"] = {
            "worst_metric": c["worst_metric"], "worst_delta": c["worst_delta"],
            "converged": c["converged"], "deltas": c["deltas"]}

    # The verdict wording is DERIVED. An earlier version hard-coded "crossing
    # the 1 % threshold" and "still failing"; after the lattice fix the two
    # rails swapped roles and the prose contradicted its own numbers.
    def verdict(rail):
        base = res["baseline"][f"Z1_{rail}"]
        new_ = res["no_overlap"][f"Z1_{rail}"]
        b0, n0 = base["worst_delta"], new_["worst_delta"]
        thr = K.VF_CONV_THRESH
        moved = "improves" if n0 < b0 else "worsens"
        crossed = (b0 >= thr) and (n0 < thr)
        if crossed:
            head = ("CAUSE CONFIRMED: removing only the overlapping candidate "
                    "sites takes this rail across the %.0f %% threshold"
                    % (100 * thr))
        elif n0 < b0:
            head = ("PARTIAL: removing the overlapping sites %s the worst "
                    "metric but does NOT reach the %.0f %% threshold, so "
                    "contact overlap is a contributing cause and not the whole "
                    "cause" % (moved, 100 * thr))
        else:
            head = ("NOT A CAUSE: removing the overlapping sites %s the worst "
                    "metric" % moved)
        return ("%s: %.4f %% -> %.4f %% at the identical %d->%d step; worst "
                "metric %s -> %s; converged %s -> %s"
                % (head, 100 * b0, 100 * n0, LEVELS[-2], LEVELS[-1],
                   base["worst_metric"], new_["worst_metric"],
                   base["converged"], new_["converged"]))

    still_open = [r for r in K.RAILS
                  if not res["no_overlap"][f"Z1_{r}"]["converged"]]
    res["finding"] = {
        "Z1_supply": verdict("supply"),
        "Z1_return": verdict("return"),
        "second_cause": (
            "A second, unidentified cause remains on: %s. Removing the ball/cell "
            "contact overlap does not bring %s under the threshold, so overlap "
            "is not a complete explanation and no further cause is claimed here."
            % (", ".join(still_open), ", ".join(still_open))
            if still_open else
            "No rail remains unconverged once the overlapping candidate sites "
            "are removed, so contact overlap accounts for the whole of Z1's "
            "non-convergence in this configuration."),
        "consequence": (
            "Z1 as CONFIGURED (nearest-to-centroid on the full lattice) is not "
            "converged, so no Z1 loop resistance and no Z1/Z2 ratio is "
            "reportable. Z2 is converged."),
    }
    res["wall_s"] = round(time.time() - t0, 1)
    (OUT / "z1_convergence_diagnostic.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res["finding"], indent=2))
    print("overlapping balls:", json.dumps(counts))


if __name__ == "__main__":
    main()
