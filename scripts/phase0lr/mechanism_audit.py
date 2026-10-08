#!/usr/bin/env python3
"""Phase-0L-R Parts 11 and 12 -- WHY does Z2 beat Z1, and where does each one's damage sit?

Part 11: aligned time histories of T, sigma_vm, hydrostatic stress, the creep-driving stress,
         the strain rate, and the running creep/energy accumulation through one stabilised
         cycle, so the advantage has a mechanical explanation and not just a ratio.
Part 12: the damage-weighted DISTRIBUTION of stress, not only its median, and the fraction of
         each architecture's damage generated in each stress bin -- which decides whether the
         two architectures occupy the same extrapolation region or different ones.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0i", "phase0ir", "phase0jr", "phase0l"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
from graded_joint import build_joint_graded                                 # noqa: E402
from decompose import parse_tensors, parse_temperature                      # noqa: E402

OUT = R / "results" / "phase0lr"
DWELL, STAB = 300.0, 5
BINS = [(0, 16), (16, 30), (30, 50), (50, 75), (75, 100), (100, 1e9)]
BINLAB = ["<16", "16-30", "30-50", "50-75", "75-100", ">100"]


def vm(S):
    sx, sy, sz, sxy, sxz, syz = S
    return math.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2)
                     + 3.0*(sxy**2 + sxz**2 + syz**2))


def hydro(S):
    return (S[0] + S[1] + S[2]) / 3.0


def series(dat: Path, ids: set):
    """Per-time, volume-averaged: T, sigma_vm, hydrostatic, PEEQ; plus per-element detail."""
    data = parse_tensors(dat, ids)
    temps = parse_temperature(dat)
    vols = {e: d["V"] for per in data.values() for e, d in per.items() if "V" in d}
    ts = sorted(data)
    out = []
    for t in ts:
        per = data[t]
        num_vm = num_h = num_p = den = 0.0
        for e, d in per.items():
            if "S" not in d or "P" not in d:
                continue
            v = vols.get(e, 1.0)
            num_vm += vm(d["S"]) * v; num_h += hydro(d["S"]) * v
            num_p += float(d["P"]) * v; den += v
        if den:
            out.append({"t": t, "T": temps.get(t, float("nan")),
                        "sigma_vm": num_vm/den, "hydro": num_h/den, "peeq": num_p/den})
    return out, data, vols


def elementwise_damage(data, vols, ids, t0, t1):
    """(sigma_vm, dPEEQ) pairs per element per increment inside the window.

    The weight is the SOLVER'S OWN PEEQ increment, never a reconstructed rate -- reconstructing
    a Norton rate at sigma^8 quadrature is exactly what corrupted an earlier damage weighting.
    """
    ts = [t for t in sorted(data) if t0 - 1e-9 < t <= t1 + 1e-9]
    pairs = []
    for e in ids:
        v = vols.get(e, 1.0)
        prev = None
        for t in ts:
            d = data[t].get(e)
            if not d or "S" not in d or "P" not in d:
                continue
            if prev is not None:
                dp = max(float(d["P"]) - prev[1], 0.0)
                pairs.append((0.5*(vm(d["S"]) + prev[0]), dp*v))
            prev = (vm(d["S"]), float(d["P"]))
    return pairs


def wq(pairs, q):
    """Damage-weighted quantile of stress."""
    s = sorted(pairs)
    tot = sum(w for _, w in s)
    if tot <= 0:
        return float("nan")
    acc = 0.0
    for x, w in s:
        acc += w
        if acc >= q * tot:
            return x
    return s[-1][0]


def main() -> int:
    m = build_joint_graded(6, 6)
    ids = set(m.sets["ESYED"])
    cases = {"Z1": R/"results/phase0l/wd/M1_Z1_BASE.dat",
             "Z2": R/"results/phase0l/wd/M1_Z2_BASE.dat"}
    hist_rows, dist_rows, frac_rows = [], [], []
    te = DWELL * 2 * STAB
    t0, t1 = te - 2*DWELL, te
    summary = {}
    for arch, dat in cases.items():
        if not dat.is_file():
            print(f"  {arch}: {dat} missing"); continue
        ser, data, vols = series(dat, ids)
        cyc = [r for r in ser if t0 - 1e-9 < r["t"] <= t1 + 1e-9]
        p0 = cyc[0]["peeq"] if cyc else 0.0
        for r in cyc:
            hist_rows.append({"arch": arch, "t_s": r["t"], "t_frac": (r["t"]-t0)/(2*DWELL),
                              "T_C": r["T"], "sigma_vm_MPa": r["sigma_vm"],
                              "hydrostatic_MPa": r["hydro"], "peeq": r["peeq"],
                              "peeq_accum_in_cycle": r["peeq"] - p0})
        pairs = elementwise_damage(data, vols, ids, t0, t1)
        tot = sum(w for _, w in pairs)
        row = {"arch": arch, "n_increment_element_pairs": len(pairs), "total_weight": tot}
        for q, lab in ((.10,"p10"), (.25,"p25"), (.50,"median"), (.75,"p75"),
                       (.90,"p90"), (.95,"p95")):
            row[f"sigma_vm_{lab}_MPa"] = wq(pairs, q)
        row["sigma_vm_max_MPa"] = max(x for x, _ in pairs) if pairs else float("nan")
        row["T_min_C"] = min(r["T"] for r in cyc); row["T_max_C"] = max(r["T"] for r in cyc)
        row["sigma_vm_peak_cycle_avg_MPa"] = max(r["sigma_vm"] for r in cyc)
        dist_rows.append(row)
        summary[arch] = row
        for (lo, hi), lab in zip(BINS, BINLAB):
            w = sum(wv for x, wv in pairs if lo <= x < hi)
            frac_rows.append({"arch": arch, "stress_bin_MPa": lab,
                              "damage_weight": w,
                              "damage_fraction": w/tot if tot else float("nan")})
    for name, rows in (("z1_z2_cycle_histories.csv", hist_rows),
                       ("high_stress_damage_fraction.csv", frac_rows),
                       ("damage_weighted_stress_distribution.csv", dist_rows)):
        p = OUT / name
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print(f"wrote {p}  ({len(rows)} rows)")
    print()
    print(f"{'':>26} " + " ".join(f"{a:>12}" for a in summary))
    for k in ("sigma_vm_p10_MPa","sigma_vm_p25_MPa","sigma_vm_median_MPa","sigma_vm_p75_MPa",
              "sigma_vm_p90_MPa","sigma_vm_p95_MPa","sigma_vm_max_MPa",
              "sigma_vm_peak_cycle_avg_MPa","T_min_C","T_max_C"):
        print(f"{k:>26} " + " ".join(f"{summary[a][k]:12.2f}" for a in summary))
    print()
    print(f"{'stress bin (MPa)':>18} " + " ".join(f"{a+' damage %':>14}" for a in summary))
    for lab in BINLAB:
        vals = [next(r["damage_fraction"] for r in frac_rows
                     if r["arch"] == a and r["stress_bin_MPa"] == lab) for a in summary]
        print(f"{lab:>18} " + " ".join(f"{100*v:14.2f}" for v in vals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
