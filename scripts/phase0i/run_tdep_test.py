#!/usr/bin/env python3
"""Phase-0I Sec.17 -- does temperature-dependent material physics change the damage metric?

This is the experiment that isolates what Phase 0I ADDED. Every earlier phase already had
thermal expansion; what it did not have was temperature-dependent stiffness, temperature-
dependent yield and thermally activated creep. The test holds the loading identical and
changes only the constitutive description:

  A  TEMPERATURE-INDEPENDENT   properties frozen at 25 C, no creep. Thermal expansion is
                               still present, so this is exactly the Phase-0H class of model.
  B  T-DEPENDENT ELASTIC+PLASTIC  E(T) and yield(T), still no creep.
  C  FULL                      E(T), yield(T) and thermally activated creep.

Also swept: the mean temperature of the cycle at fixed swing, because an Arrhenius creep law
should care about it and a temperature-independent model cannot.
"""
from __future__ import annotations
import csv, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
from joint import build_joint, write_inp, run, read_dat, cycle_metric, BALL_H_UM   # noqa
from solder_model import (E_of_T, sigma0_of_T, sat_stress_of_T, norton_at,          # noqa
                          CTE_SAC305, NU, inp_material)

WD = R / "results" / "phase0i" / "tdep"
WD.mkdir(parents=True, exist_ok=True)
TEMPS = [-40., 0., 25., 50., 75., 100., 125.]
N_CYC, DWELL, GAMMA = 4, 300.0, 0.004


def material(kind: str) -> str:
    """A: frozen at 25 C, no creep.  B: T-dependent E and yield, no creep.  C: full."""
    if kind == "A":
        return ("*MATERIAL, NAME=SAC305\n*ELASTIC\n"
                f"{E_of_T(25.):.6g}, {NU}\n*PLASTIC\n"
                f"{sigma0_of_T(25.):.6g}, 0.0\n{sat_stress_of_T(25.):.6g}, 0.02\n"
                f"*EXPANSION, ZERO=25.\n{CTE_SAC305:.4g}\n")
    if kind == "B":
        L = ["*MATERIAL, NAME=SAC305", "*ELASTIC"]
        L += [f"{E_of_T(T):.6g}, {NU}, {T:.1f}" for T in TEMPS]
        L.append("*PLASTIC")
        for T in TEMPS:
            L.append(f"{sigma0_of_T(T):.6g}, 0.0, {T:.1f}")
            L.append(f"{sat_stress_of_T(T):.6g}, 0.02, {T:.1f}")
        L += ["*EXPANSION, ZERO=25.", f"{CTE_SAC305:.4g}"]
        return "\n".join(L) + "\n"
    return inp_material("SAC305", TEMPS)


def run_case(tag, kind, t_lo, t_hi, n_xy=6, n_z=8):
    m = build_joint(n_xy, n_z, 1)
    du = GAMMA * BALL_H_UM / 1e3
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}h", t_hi, du, DWELL)); t += DWELL
        cyc.append((f"c{k}c", t_lo, -du, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material(kind), cyc, cetol=1e-2,
              procedure=("VISCO" if kind == "C" else "STATIC"))
    t0 = time.time()
    run(p, threads=4)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 1000):
        return None
    inc, _ = cycle_metric(read_dat(d), [0.0] + ends)
    if not inc or not np.isfinite(inc[-1]) or inc[-1] <= 0:
        return None
    return {"tag": tag, "model": kind, "T_low_C": t_lo, "T_high_C": t_hi,
            "T_mean_C": 0.5 * (t_lo + t_hi), "dT_K": t_hi - t_lo,
            "d_eps_in_stab": inc[-1], "cycles": len(inc),
            "wall_s": round(time.time() - t0, 1)}


def main():
    rows = []
    print("A/B/C at a FIXED cycle 0 -> 100 C, identical loading")
    base = {}
    for kind, lab in (("A", "temperature-INDEPENDENT (Phase-0H class)"),
                      ("B", "T-dependent elastic + plastic, no creep"),
                      ("C", "FULL: T-dependent elastic + plastic + creep")):
        r = run_case(f"m{kind}", kind, 0.0, 100.0)
        if not r:
            print(f"  {kind}  FAILED"); continue
        rows.append(r); base[kind] = r["d_eps_in_stab"]
        print(f"  {kind}  {lab:46s} d_eps_in = {r['d_eps_in_stab']:.5e}  ({r['wall_s']:.0f} s)",
              flush=True)
    if "A" in base and "C" in base:
        print(f"\n  full physics vs temperature-independent: "
              f"{base['C']/base['A']:.2f}x  ({100*(base['C']-base['A'])/base['A']:+.1f} %)")
    if "B" in base and "C" in base:
        print(f"  creep alone contributes:                 "
              f"{base['C']/base['B']:.2f}x  ({100*(base['C']-base['B'])/base['B']:+.1f} %)")

    print("\nMEAN-TEMPERATURE SWEEP at a fixed 100 K swing "
          "(an Arrhenius law must care; a frozen model cannot)")
    for kind in ("A", "C"):
        for lo in (-25.0, 0.0, 25.0, 50.0):
            r = run_case(f"s{kind}{lo:+.0f}", kind, lo, lo + 100.0)
            if not r:
                print(f"  {kind} Tmean={lo+50:6.1f} C  FAILED"); continue
            rows.append(r)
            print(f"  {kind}  T_mean = {r['T_mean_C']:6.1f} C  d_eps_in = "
                  f"{r['d_eps_in_stab']:.5e}", flush=True)
    with open(R / "results/phase0i/temperature_dependent_damage_test.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    for kind in ("A", "C"):
        sel = sorted([r for r in rows if r["model"] == kind and r["dT_K"] == 100.0],
                     key=lambda r: r["T_mean_C"])
        if len(sel) > 1:
            lo, hi = sel[0]["d_eps_in_stab"], sel[-1]["d_eps_in_stab"]
            print(f"\n  model {kind}: d_eps_in across T_mean {sel[0]['T_mean_C']:.0f} -> "
                  f"{sel[-1]['T_mean_C']:.0f} C changes {100*(hi-lo)/lo:+.1f} %")
    print(f"\nwrote results/phase0i/temperature_dependent_damage_test.csv")


if __name__ == "__main__":
    main()
