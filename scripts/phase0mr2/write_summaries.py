#!/usr/bin/env python3
"""Phase-0M-R2 --- the three-phase comparison table and the per-domain metric tables."""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr2"
BASE = OUT / "_baseline_phase0mr"
M0 = R / "results" / "phase0m"


def rd(p, n=None):
    q = Path(p) / n if n else Path(p)
    return list(csv.DictReader(q.open())) if q.is_file() else []


def ff(r, k):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return float("nan")


ARCH = [("ARCH_Z1_EMBEDDED", "Z1"), ("ARCH_Z2_BACKSIDE", "Z2"),
        ("ARCH_Z4_POWER_DIE", "Z4_stacked")]
METRICS = ["P_elec_total_w", "T_max_C", "T_mean_C", "T_conv_C",
           "die_warpage_pv_um", "du_corner_um"]


def main() -> int:
    old = rd(BASE, "production_architecture_replay.csv")
    new = rd(OUT, "architecture_replay_0mr2.csv")

    def phase0m(a, k):
        for r in old:
            if r["arch"] == a and r["mode"] == "BEFORE":
                return ff(r, k)
        return float("nan")

    def phase0mr(a, k):
        for r in old:
            if (r["arch"] == a and r["mode"] == "AFTER" and "27" in r.get("cooler", "")
                    and r.get("template") == "T1_EMBEDDED_4LAYER"):
                return ff(r, k)
        return float("nan")

    def phase0mr2(cid, k):
        return next((ff(r, k) for r in new if r["case"] == cid), float("nan"))

    rows = []
    for arch, cid in ARCH:
        for k in METRICS:
            a, b, c = phase0m(arch, k), phase0mr(arch, k), phase0mr2(cid, k)
            rows.append({"architecture": arch, "case": cid, "metric": k,
                         "phase0M": a, "phase0MR": b, "phase0MR2": c,
                         "delta_MR_to_MR2": c - b,
                         "pct_MR_to_MR2": 100 * (c - b) / b if b else float("nan")})
    # orderings
    for k in METRICS:
        for lab, fn in (("phase0M", phase0m), ("phase0MR", phase0mr)):
            vals = {s: fn(a, k) for a, s in ARCH}
            rows.append({"architecture": "ORDERING", "case": lab, "metric": k,
                         lab: " < ".join(sorted(vals, key=lambda x: vals[x])),
                         "phase0MR2": "", "delta_MR_to_MR2": "", "pct_MR_to_MR2": ""})
        vals = {s: phase0mr2(c, k) for _, s in ARCH for c in [s]}
        rows.append({"architecture": "ORDERING", "case": "phase0MR2", "metric": k,
                     "phase0MR2": " < ".join(sorted(vals, key=lambda x: vals[x])),
                     "phase0M": "", "phase0MR": "", "delta_MR_to_MR2": "",
                     "pct_MR_to_MR2": ""})
    with open(OUT / "architecture_replay_0m_0mr_0mr2.csv", "w", newline="") as fh:
        k = ["architecture", "case", "metric", "phase0M", "phase0MR", "phase0MR2",
             "delta_MR_to_MR2", "pct_MR_to_MR2"]
        w = csv.DictWriter(fh, fieldnames=k, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

    th = [{"case": r["case"], "arch": r["arch"], "T_max_C": r["T_max_C"],
           "T_mean_C": r["T_mean_C"], "T_conv_C": r["T_conv_C"],
           "T_coolant_out_C": r["T_coolant_out_C"], "dp_MPa": r["dp_MPa"],
           "m_dot_g_s": r["m_dot_g_s"], "cooler_regime": r["cooler_regime"],
           "cooler_in_domain": r["cooler_in_domain"],
           "energy_residual_pct": r["energy_residual_pct"]} for r in new]
    with open(OUT / "architecture_thermal_metrics.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(th[0])); w.writeheader(); w.writerows(th)

    me = [{"case": r["case"], "arch": r["arch"],
           "die_warpage_pv_um": r["die_warpage_pv_um"],
           "pkg_warpage_pv_um": r["pkg_warpage_pv_um"],
           "du_corner_um": r["du_corner_um"]} for r in new]
    z1 = next(r for r in new if r["case"] == "Z1")
    z2 = next(r for r in new if r["case"] == "Z2")
    ratio = ff(z1, "du_corner_um") / ff(z2, "du_corner_um")
    for r in me:
        r["Z1_over_Z2_driver_ratio"] = ratio
    with open(OUT / "architecture_mechanical_metrics.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(me[0])); w.writeheader(); w.writerows(me)

    # realizability, per architecture, from the clearance sweep
    fe = rd(OUT, "component_partition_feasibility_r2.csv")
    import arch_geometry as AG
    sys.path.insert(0, str(R / "scripts" / "phase0mr2"))
    rz = []
    for arch, cid in ARCH:
        sub = [r for r in fe if r["arch"] == arch
               and r["template"] == "T1_EMBEDDED_4LAYER"]
        s = AG.span(arch)
        e = AG.field(arch, 1000.0 if s.rail == "LV" else 1000.0 / 0.889 / 48.0)
        def st(d):
            v = {r[d] for r in sub}
            return "ALWAYS" if v == {"True"} else "NEVER" if v == {"False"} \
                else "BOUND_DEPENDENT"
        rz.append({"architecture": arch, "template": "T1_EMBEDDED_4LAYER",
                   "AREA": st("AREA_FEASIBLE"), "HEIGHT": st("HEIGHT_FEASIBLE"),
                   "THERMAL_PATH": st("THERMAL_FEASIBLE"),
                   "ROUTING": st("ROUTING_FEASIBLE"),
                   "CURRENT_DENSITY": st("CURRENT_DENSITY_FEASIBLE"),
                   "PACKAGE_CLEARANCE": st("PACKAGE_CLEARANCE_SATISFIED"),
                   "clearance_sourcing": "OPEN",
                   "tsv_span_um": s.length_um, "tsv_aspect_ratio": s.aspect_ratio,
                   "tsv_aspect_ok": s.feasible_aspect,
                   "n_required": e["n_required"], "n_allocated": e["n_allocated"],
                   "n_available": e["n_available"],
                   "FULLY_REALIZABLE": st("FULLY_REALIZABLE")})
    with open(OUT / "architecture_realizability.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rz[0])); w.writeheader(); w.writerows(rz)

    print(f"  Z1/Z2 driver ratio = {ratio:.4f}")
    for r in rz:
        print(f"  {r['architecture']:22s} FULLY_REALIZABLE={r['FULLY_REALIZABLE']:16s} "
              f"AR={r['tsv_aspect_ratio']:.2f} n_req={r['n_required']:.0f} "
              f"<= n_alloc={r['n_allocated']:.0f} <= n_avail={r['n_available']:.0f}")
    print("wrote the three-phase table and the three metric tables")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(R / "scripts" / "phase0mr2"))
    sys.exit(main())
