"""PHASE 0N-AJ --- the intra-VR fidelity ladder, actually compared.

R2 was being COMPUTED (16 rows in results/phase0m/intra_vr_routing_model.csv)
and never compared with anything, so the ladder's own question -- "the cheapest
level that reproduces R2 is what the optimizer should use" -- had no answer in
any artifact. R0/R1 report the output net through a width-rule Manhattan
approximation; R2 solves the same net as a 2-D resistive sheet. Those are
directly comparable at matched Cu thickness and layer count, and that
comparison is what this emits.

R1 IS RETIRED. With the obstacle router repaired (it now detours on a
synthetic blocker, proven by test) not one of the 16 physical nets is
obstructed, so R1 reproduces R0 exactly. It is retired as a fidelity level
rather than having a difference manufactured for it.

R3 (3-D current crowding) is a separate module and is applied selectively to
critical transitions, not to every net; it is referenced here, not re-run.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0m", "scripts/phase0e", "scripts/phase0dr", "scripts"):
    sys.path.insert(0, str(R / _p))
import routing as RT                                                 # noqa: E402

SRC = R / "results" / "phase0m"
OUT = R / "research" / "phase0naj"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    nets = list(csv.DictReader((SRC / "intra_vr_routing_nets.csv").open()))
    model = list(csv.DictReader((SRC / "intra_vr_routing_model.csv").open()))

    # R0/R1 output-net power, keyed by the parameters R2 also varies
    lo = {}
    for r in nets:
        if r["net"] != "vout_plane":
            continue
        lo.setdefault((r["level"], r["t_cu_um"], r["n_layers"]), []).append(
            float(r["P_w_per_vr"]))
    r2 = {(r["t_cu_um"], r["n_layers"]): float(r["p_output_net_w_per_vr"])
          for r in model if r["level"] == "R2" and r["p_output_net_w_per_vr"]}

    rows = []
    for (t_cu, n_lay), p2 in sorted(r2.items(), key=lambda kv: (float(kv[0][0]),
                                                                int(kv[0][1]))):
        p0 = lo.get(("R0", t_cu, n_lay))
        p1 = lo.get(("R1", t_cu, n_lay))
        if not p0:
            continue
        p0 = sum(p0) / len(p0)
        p1 = sum(p1) / len(p1) if p1 else None
        rows.append({
            "net": "vout_plane", "t_cu_um": float(t_cu), "n_layers": int(n_lay),
            "R0_w_per_vr": p0,
            "R1_w_per_vr": p1,
            "R2_w_per_vr": p2,
            "R1_equals_R0": (p1 is not None and abs(p1 - p0) < 1e-12),
            "R0_over_R2": p0 / p2 if p2 else None,
            "R0_err_vs_R2_pct": 100 * (p0 - p2) / p2 if p2 else None,
        })

    # does R1 add anything, anywhere in the whole net table?
    r1_identical = all(
        abs(sum(lo.get(("R1", t, n), [0])) - sum(lo.get(("R0", t, n), [0]))) < 1e-12
        for (lvl, t, n) in lo if lvl == "R0")
    comps = RT.tile_layout(RT.DESIGN["tile_side_mm"])
    by = {c.name: c for c in comps}
    detoured = [nt.name for nt in RT.nets()
                if by.get(nt.src) and by.get(nt.dst)
                and abs(RT.obstacle_manhattan(by[nt.src], by[nt.dst], comps,
                                              nt.layer)
                        - RT.manhattan(by[nt.src], by[nt.dst])) > 1e-12]

    errs = [abs(r["R0_err_vs_R2_pct"]) for r in rows if r["R0_err_vs_R2_pct"]]
    res = {
        "meta": {
            "phase": "0N-AJ",
            "observable": "output-net conduction loss per VR (vout_plane)",
            "R2_reference_status": (
                "R2 is the HIGHER-FIDELITY MODEL HERE, not the truth. It solves "
                "the same 2-D sheet physics with real terminal footprints; it is "
                "not an independent solver and not an experiment, so agreement "
                "with it is CLOSED_FORM/MODEL_CONSISTENCY, never validation"),
            "R1_status": "RETIRED",
            "R1_retirement_reason": (
                "the obstacle router was repaired (it detours on a synthetic "
                "blocker, asserted by test) and still no physical net is "
                "obstructed: %s. R1 therefore reproduces R0 exactly and is not a "
                "distinct fidelity level for this layout."
                % (", ".join(detoured) if detoured else "zero of 16 detour")),
            "R3_status": (
                "SEPARATE MODULE -- 3-D current crowding, applied selectively to "
                "critical transitions. Not re-run here and not folded into every "
                "net, because doing so would turn a screening model into an "
                "expensive solve for no added fidelity on unobstructed routes"),
            "R0_vs_R2_max_abs_err_pct": max(errs) if errs else None,
            "R0_vs_R2_min_abs_err_pct": min(errs) if errs else None,
        },
        "rows": rows,
        "R1_identical_to_R0_everywhere": bool(r1_identical),
        "nets_detouring_after_router_fix": detoured,
    }
    (OUT / "fidelity_ladder.json").write_text(json.dumps(res, indent=2))
    with (OUT / "fidelity_ladder.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("R1 identical to R0 everywhere:", r1_identical,
          "| nets detouring:", detoured or "none")
    for r in rows:
        print("t=%-5.1f um n=%d  R0=%.5f  R2=%.5f  R0/R2=%.3f  err=%+.1f %%"
              % (r["t_cu_um"], r["n_layers"], r["R0_w_per_vr"],
                 r["R2_w_per_vr"], r["R0_over_R2"], r["R0_err_vs_R2_pct"]))


if __name__ == "__main__":
    main()
