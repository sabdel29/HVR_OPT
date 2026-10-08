#!/usr/bin/env python3
"""Phase-0I-R Sec.5/6/7 -- per-cycle audit of the Phase-0I metric.

Establishes, for the actual joint, the difference between three quantities that are easy to
conflate:

  PEEQ                     accumulated equivalent inelastic strain -- a monotone PATH LENGTH
  d(PEEQ) per cycle        the Phase-0I metric: path length traversed in one cycle
  range of eq(eps_in)      max minus min of the INSTANTANEOUS equivalent inelastic strain

and adds the energy diagnostic Sec.6 asks for: the cycle integral of sigma : d(eps_in).
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0ir"))
from decompose import (CTE_SAC305, DWELL, N_CYC, OUT, T_REF, decompose,   # noqa: E402
                       eq_strain, solve, temperature_at, vol_avg)


def per_element_series(data, vols, temps=None):
    """{elem: [(t, T, S, Etot, PEEQ)]} sorted in time, for elements with full tensors."""
    ser = {}
    for t in sorted(data):
        T = (temps or {}).get(t, temperature_at(t))
        for e, d in data[t].items():
            if "S" in d and "E" in d and "P" in d:
                ser.setdefault(e, []).append((t, T, d["S"], d["E"], d["P"]))
    return {e: v for e, v in ser.items() if len(v) > 8}


def cycle_quantities(ser, vols, t0, t1):
    """Volume-averaged per-cycle quantities over the window (t0, t1]."""
    dpeeq_n = rng_n = work_n = den = 0.0
    for e, rows in ser.items():
        w = [r for r in rows if t0 - 1e-9 < r[0] <= t1 + 1e-9]
        if len(w) < 3:
            continue
        v = vols.get(e, 1.0)
        # accumulated path length traversed in this cycle
        dpeeq = w[-1][4] - w[0][4]
        # instantaneous equivalent inelastic strain, and its range
        eqs, inels = [], []
        for (t, T, S, Et, P) in w:
            _, _, inel = decompose(S, Et, T)
            inels.append(np.array(inel)); eqs.append(eq_strain(inel))
        rng = max(eqs) - min(eqs)
        # inelastic work: sum sigma : d(eps_in) with the engineering shear factor of 2
        work = 0.0
        for k in range(1, len(w)):
            S0 = np.array(w[k - 1][2]); S1 = np.array(w[k][2])
            dE = inels[k] - inels[k - 1]
            Sm = 0.5 * (S0 + S1)
            work += float(Sm[0] * dE[0] + Sm[1] * dE[1] + Sm[2] * dE[2]
                          + 2 * (Sm[3] * dE[3] + Sm[4] * dE[4] + Sm[5] * dE[5]))
        dpeeq_n += dpeeq * v; rng_n += rng * v; work_n += work * v; den += v
    if not den:
        return None
    return {"d_peeq_per_cycle": dpeeq_n / den, "range_eq_inelastic": rng_n / den,
            "inelastic_work_MJ_per_m3": work_n / den}   # MPa * strain = MJ/m^3


def main():
    ends = [DWELL * 2 * (k + 1) for k in range(N_CYC)]
    rows, summary = [], {}
    for kind in ("EP", "EC", "EPC"):
        data, m, _, temps = solve(kind)
        if data is None:
            print(f"  {kind}: no output"); continue
        vols = {e: d["V"] for per in data.values() for e, d in per.items() if "V" in d}
        ser = per_element_series(data, vols, temps)
        print(f"\n{kind}: {len(ser)} core elements with full tensor history")
        print(f"  {'cycle':>5s} {'window (s)':>16s} {'d(PEEQ)':>12s} "
              f"{'range eq(e_in)':>15s} {'ratio':>7s} {'W_in MJ/m3':>12s}")
        prev = None
        for k, te in enumerate(ends, 1):
            q = cycle_quantities(ser, vols, te - 2 * DWELL, te)
            if not q:
                continue
            chg = (100 * abs(q["d_peeq_per_cycle"] - prev) / prev) if prev else float("nan")
            rows.append({"model": kind, "cycle": k, "t_start_s": te - 2 * DWELL,
                         "t_end_s": te, **q,
                         "ratio_dpeeq_over_range": q["d_peeq_per_cycle"] / q["range_eq_inelastic"]
                         if q["range_eq_inelastic"] > 1e-12 else float("nan"),
                         "cycle_to_cycle_change_pct": chg})
            print(f"  {k:5d} {te-2*DWELL:7.0f}-{te:<8.0f} {q['d_peeq_per_cycle']:12.5e} "
                  f"{q['range_eq_inelastic']:15.5e} "
                  f"{q['d_peeq_per_cycle']/max(q['range_eq_inelastic'],1e-12):7.3f} "
                  f"{q['inelastic_work_MJ_per_m3']:12.5e}", flush=True)
            prev = q["d_peeq_per_cycle"]
        last = [r for r in rows if r["model"] == kind][-1]
        summary[kind] = last

    with open(OUT / "stabilized_cycle_audit.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(OUT / "strain_vs_energy_damage_diagnostic.csv", "w", newline="") as f:
        out = []
        base = summary.get("EP")
        for k, s in summary.items():
            out.append({"model": k,
                        "description": {"EP": "elastic + plastic, NO creep (Phase-0H class)",
                                        "EC": "elastic + creep, NO plasticity",
                                        "EPC": "elastic + plastic + creep (Phase 0I)"}[k],
                        "d_peeq_per_cycle": s["d_peeq_per_cycle"],
                        "range_eq_inelastic": s["range_eq_inelastic"],
                        "inelastic_work_MJ_per_m3": s["inelastic_work_MJ_per_m3"],
                        "d_peeq_vs_EP_pct": (100 * (s["d_peeq_per_cycle"] - base["d_peeq_per_cycle"])
                                             / base["d_peeq_per_cycle"]) if base else None,
                        "work_vs_EP_pct": (100 * (s["inelastic_work_MJ_per_m3"]
                                                  - base["inelastic_work_MJ_per_m3"])
                                           / abs(base["inelastic_work_MJ_per_m3"])) if base else None})
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print("\n=== Sec.5/6 DIAGNOSTIC: strain-based vs energy-based, against EP ===")
    print(f"{'model':5s} {'d(PEEQ)/cyc':>13s} {'vs EP':>9s} {'W_in MJ/m3':>13s} {'vs EP':>9s}")
    for o in out:
        print(f"{o['model']:5s} {o['d_peeq_per_cycle']:13.5e} "
              f"{(o['d_peeq_vs_EP_pct'] or 0):+8.1f}% {o['inelastic_work_MJ_per_m3']:13.5e} "
              f"{(o['work_vs_EP_pct'] or 0):+8.1f}%")
    print(f"\nwrote stabilized_cycle_audit.csv and strain_vs_energy_damage_diagnostic.csv")


if __name__ == "__main__":
    main()
