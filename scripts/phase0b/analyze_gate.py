#!/usr/bin/env python3
"""Phase-0B materiality analysis.

Spec quantities:
    S_m = (m_max - m_min) / m_median      architectural spread across cases
    resolved iff S_m > 2 u_m              with u_m from mesh / model / BC sensitivity
    bands: weak 10-15%, moderate 15-25%, strong >=25%

METHODOLOGICAL POINT. A material perturbation (e.g. HVR-tile CTE 4 -> 10 ppm/K) is a
SYSTEMATIC uncertainty: it moves every architecture in the same direction. Folding its
full magnitude into u_m as if it were random noise on the *difference* would be wrong -
it would make essentially any architecture study unresolvable, because the absolute
warpage of this package is far more sensitive to an unknown tile CTE than to placement.

The question that actually matters is whether the ARCHITECTURAL SPREAD survives each
perturbation. So every perturbation is applied to every case, S_m is recomputed under
that perturbation, and we report:

    S_m(reference)          the headline spread
    min/max S_m over all material corners
    ordering stability      does the case ranking ever flip?

u_m then combines the mesh uncertainty with the *variation in S_m* across corners,
not the variation in the absolute value. An effect is declared resolved only if the
WORST-CASE S_m across every corner still exceeds 2 u_mesh, and the ordering never flips.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0b"

METRIC_LABELS = {
    "T_max_C": "T_max (C)",
    "die_warpage_pv_um": "die warpage p-v (um)",
    "pkg_warpage_pv_um": "package warpage p-v (um)",
    "si_principal_p99_MPa": "Si max principal p99 (MPa)",
    "tsv_vm_p99_MPa": "TSV-region vonMises p99 (MPa)",
    "interface_shear_p99_MPa": "interface shear p99 (MPa)",
    "interface_peel_p99_MPa": "interface peel p99 (MPa)",
}
MESH_KEY = {
    "T_max_C": "d_T_max_C_pct",
    "die_warpage_pv_um": "d_die_warpage_pv_um_pct",
    "pkg_warpage_pv_um": "d_pkg_warpage_pv_um_pct",
    "si_principal_p99_MPa": "d_si_principal_p99_MPa_pct",
    "tsv_vm_p99_MPa": "d_tsv_vm_p99_MPa_pct",
    "interface_shear_p99_MPa": "d_interface_shear_p99_MPa_pct",
    "interface_peel_p99_MPa": "d_interface_peel_p99_MPa_pct",
}


def band(s):
    a = abs(s)
    return "STRONG" if a >= .25 else "MODERATE" if a >= .15 else "WEAK" if a >= .10 else "BELOW-BAND"


def load_runs():
    with (OUT / "gate_runs.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if k not in ("case", "variant", "bc"):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    r[k] = float("nan")
    return rows


def mesh_u():
    conv = OUT / "mesh_convergence.csv"
    if not conv.exists():
        return {}
    last = list(csv.DictReader(conv.open()))[-1]
    out = {}
    for m, k in MESH_KEY.items():
        try:
            out[m] = abs(float(last[k])) / 100.0
        except (KeyError, TypeError, ValueError):
            out[m] = float("nan")
    return out


def spread(vals):
    vals = [v for v in vals if v == v]
    if len(vals) < 2:
        return float("nan")
    med = float(np.median(vals))
    return (max(vals) - min(vals)) / abs(med) if med else float("nan")


def main(cases):
    rows = load_runs()
    um = mesh_u()
    variants = sorted({r["variant"] for r in rows if r["variant"].startswith("sens_")})
    get = lambda c, v: next((r for r in rows if r["case"] == c and r["variant"] == v), None)

    # ---------- headline: BC-A, production mesh -------------------------------
    print(f"\n{'='*118}\nHEADLINE - BC-A, converged production mesh, controlled DOE "
          f"(42 W HVR heat and 96 mm2 footprint held constant)\n{'='*118}")
    head = [f"{'metric':32s}"] + [f"{c:>12s}" for c in cases] + \
           [f"{'S_m %':>9s}", f"{'2u_mesh %':>11s}", f"{'resolved':>10s}", f"{'band':>11s}"]
    print("".join(head)); print("-" * 118)

    table = []
    for m, label in METRIC_LABELS.items():
        vals = [get(c, "baseline_BC_A")[m] for c in cases]
        S = spread(vals)
        u = um.get(m, float("nan"))
        res = (S > 2 * u) if (S == S and u == u) else None
        row = {"metric": label, "key": m}
        row.update({c: round(v, 4) for c, v in zip(cases, vals)})
        row.update({"range": round(max(vals) - min(vals), 4), "S_m_pct": round(100 * S, 2),
                    "u_mesh_pct": round(100 * u, 2), "resolved_vs_mesh": res, "band": band(S)})
        table.append(row)
        print(f"{label:32s}" + "".join(f"{v:12.3f}" for v in vals) +
              f"{100*S:9.2f}{200*u:11.2f}{str(res):>10s}{band(S):>11s}")

    # ---------- does the spread survive every material corner? ----------------
    print(f"\n{'='*118}\nROBUSTNESS OF THE ARCHITECTURAL SPREAD ACROSS MATERIAL/MODEL CORNERS "
          f"(sensitivity mesh)\n{'='*118}")
    hdr = (f"{'metric':32s}{'S_ref %':>9s}{'S_min %':>9s}{'S_max %':>9s}"
           f"{'worst corner':>16s}{'order stable':>14s}{'verdict':>14s}")
    print(hdr); print("-" * len(hdr))

    robust = {}
    for m, label in METRIC_LABELS.items():
        s_by_variant, order_ok = {}, True
        ref_order = None
        for v in ["sens_ref"] + [x for x in variants if x != "sens_ref"]:
            vals, ok = [], True
            for c in cases:
                r = get(c, v)
                if r is None or r[m] != r[m]:
                    ok = False; break
                vals.append(r[m])
            if not ok:
                continue
            s_by_variant[v] = spread(vals)
            order = tuple(np.argsort(vals))
            if v == "sens_ref":
                ref_order = order
            elif ref_order is not None and order != ref_order:
                order_ok = False
        if not s_by_variant:
            continue
        s_ref = s_by_variant.get("sens_ref", float("nan"))
        s_min = min(s_by_variant.values()); s_max = max(s_by_variant.values())
        worst = min(s_by_variant, key=lambda k: s_by_variant[k])
        u = um.get(m, float("nan"))
        verdict = ("RESOLVED" if (s_min > 2 * u and order_ok)
                   else "ORDER FLIPS" if not order_ok else "NOT RESOLVED")
        robust[m] = {"S_ref": s_ref, "S_min": s_min, "S_max": s_max,
                     "worst_corner": worst, "order_stable": order_ok,
                     "verdict": verdict, "by_variant": s_by_variant}
        print(f"{label:32s}{100*s_ref:9.2f}{100*s_min:9.2f}{100*s_max:9.2f}"
              f"{worst.replace('sens_',''):>16s}{str(order_ok):>14s}{verdict:>14s}")

    # ---------- BC-A vs BC-B --------------------------------------------------
    print(f"\n{'='*118}\nBOUNDARY-CONDITION SENSITIVITY - BC-A (free warpage) vs "
          f"BC-B (compliant support, board-restrained)\n{'='*118}")
    bc_tab = []
    for m, label in METRIC_LABELS.items():
        va = [get(c, "bcsens_BC_A")[m] for c in cases if get(c, "bcsens_BC_A")]
        vb = [get(c, "bcsens_BC_B")[m] for c in cases if get(c, "bcsens_BC_B")]
        if len(va) != len(cases) or len(vb) != len(cases):
            continue
        sa, sb = spread(va), spread(vb)
        oa, ob = tuple(np.argsort(va)), tuple(np.argsort(vb))
        bc_tab.append({"metric": label, "key": m,
                       "S_BC_A_pct": round(100 * sa, 2), "S_BC_B_pct": round(100 * sb, 2),
                       "order_same": oa == ob,
                       "BC_A_vals": [round(v, 4) for v in va],
                       "BC_B_vals": [round(v, 4) for v in vb]})
        print(f"{label:32s} S(BC-A)={100*sa:7.2f}%  S(BC-B)={100*sb:7.2f}%   "
              f"ordering {'PRESERVED' if oa == ob else 'CHANGED'}   "
              f"BC-A {['%.3f' % v for v in va]}  BC-B {['%.3f' % v for v in vb]}")

    p = OUT / "three_case_comparison.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys())); w.writeheader(); w.writerows(table)
    (OUT / "materiality_analysis.json").write_text(json.dumps(
        {"cases": cases, "headline": table, "robustness": robust,
         "bc_sensitivity": bc_tab, "u_mesh_rel": um}, indent=2, default=str))
    print(f"\nwrote {p}\nwrote {OUT/'materiality_analysis.json'}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["C05", "C07", "C13"])
