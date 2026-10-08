#!/usr/bin/env python3
"""Phase-0I-R Sec.15 -- is the architecture damage difference RESOLVED against uncertainty?

Adding the RMS numbers blindly would be wrong, because most of the uncertainty is COMMON MODE:
the three architectures share the same material card, the same mesh, the same exclusion band
and the same solver tolerance. A common-mode error moves all three together and largely
cancels in a ratio.

So the uncertainty is measured on the RATIO directly: each perturbation is applied to two
architectures at once and the change in their damage RATIO is what is reported. That is the
quantity the architecture claim actually rests on.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from decompose import OUT                                              # noqa: E402
from joint import build_joint, cycle_metric, read_dat, run, write_inp  # noqa: E402
from solder_model import (CTE_SAC305, E_of_T, NU, inp_material,        # noqa: E402
                          norton_at, sat_stress_of_T, sigma0_of_T)

WD = OUT / "unc"
WD.mkdir(parents=True, exist_ok=True)
TEMPS = [-40., 0., 25., 50., 75., 100., 125.]
CASES = {"Z1": (2.749, 82.86), "Z2": (2.080, 81.85), "Z4": (2.984, 81.10)}
N_CYC, DWELL, T_OFF = 4, 300.0, 25.0


def card(a_scale=1.0, n_shift=0.0, e_scale=1.0, y_scale=1.0):
    L = ["*MATERIAL, NAME=SAC305", "*ELASTIC"]
    L += [f"{E_of_T(T)*e_scale:.6g}, {NU}, {T:.1f}" for T in TEMPS]
    L.append("*PLASTIC")
    for T in TEMPS:
        L.append(f"{sigma0_of_T(T)*y_scale:.6g}, 0.0, {T:.1f}")
        L.append(f"{sat_stress_of_T(T)*y_scale:.6g}, 0.02, {T:.1f}")
    L.append("*CREEP, LAW=NORTON")
    for T in TEMPS:
        f = norton_at(T)
        L.append(f"{f['A']*a_scale:.6e}, {f['n']+n_shift:.6g}, 0.0, {T:.1f}")
    L += ["*EXPANSION, ZERO=25.", f"{CTE_SAC305:.4g}"]
    return "\n".join(L) + "\n"


def damage(tag, du_um, t_hot, mat, n_xy=6, n_z=8, excl=1.0):
    m = build_joint(n_xy, n_z, 1)
    if excl != 1.0:
        hs, dx = 0.5 * 0.35449, m.sets["_dx_mm"] * excl
        m.sets["ESOLCORE"] = [e for e, c, s in m.elems if s == "ESOL"
                              and max(abs(m.nodes[[n - 1 for n in c]].mean(axis=0)[:2]))
                              < hs - dx * 0.999]
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", T_OFF, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, mat, cyc, cetol=1e-2, procedure="VISCO")
    run(p, threads=4)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 1000):
        return None
    inc, _ = cycle_metric(read_dat(d), [0.0] + ends)
    return inc[-1] if inc and np.isfinite(inc[-1]) and inc[-1] > 0 else None


PERTURB = [
    ("reference", {}, "the Phase-0I card"),
    ("creep_A_x1.12", dict(a_scale=1.12), "Norton A +12 % -- the worst per-temperature RMS fit residual"),
    ("creep_A_x0.88", dict(a_scale=0.88), "Norton A -12 %"),
    ("creep_n_+0.5", dict(n_shift=0.5), "Norton exponent +0.5"),
    ("E_x1.15", dict(e_scale=1.15), "E(T) +15 % -- the E slope is an ASSUMPTION"),
    ("E_x0.85", dict(e_scale=0.85), "E(T) -15 %"),
    ("yield_x1.10", dict(y_scale=1.10), "yield +10 %"),
    ("yield_x0.90", dict(y_scale=0.90), "yield -10 %"),
]


def main():
    rows, dmg = [], {}
    print("Damage under each perturbation, all three architectures (same perturbation each time)")
    print(f"{'perturbation':16s} " + " ".join(f"{k:>12s}" for k in CASES)
          + f" {'Z2/Z1':>8s} {'Z4/Z1':>8s}")
    for name, kw, _ in PERTURB:
        mat = card(**kw)
        vals = {}
        for k, (du, th) in CASES.items():
            v = damage(f"{name}_{k}".replace(".", "p"), du, th, mat)
            vals[k] = v
        if not all(vals.values()):
            print(f"{name:16s}  incomplete"); continue
        r2, r4 = vals["Z2"] / vals["Z1"], vals["Z4"] / vals["Z1"]
        dmg[name] = vals
        rows.append({"perturbation": name, "description": dict((a, c) for a, _, c in PERTURB)[name],
                     **{f"damage_{k}": v for k, v in vals.items()},
                     "ratio_Z2_over_Z1": r2, "ratio_Z4_over_Z1": r4})
        print(f"{name:16s} " + " ".join(f"{vals[k]:12.5e}" for k in CASES)
              + f" {r2:8.4f} {r4:8.4f}", flush=True)

    # mesh and exclusion-band perturbations, applied to all three
    for tag, kw2, desc in (("mesh_5x6", dict(n_xy=5, n_z=6), "coarser mesh"),
                           ("excl_2elem", dict(excl=2.0), "2-element corner exclusion band")):
        mat = card()
        vals = {k: damage(f"{tag}_{k}", du, th, mat, **kw2) for k, (du, th) in CASES.items()}
        if not all(vals.values()):
            print(f"{tag:16s}  incomplete"); continue
        r2, r4 = vals["Z2"] / vals["Z1"], vals["Z4"] / vals["Z1"]
        rows.append({"perturbation": tag, "description": desc,
                     **{f"damage_{k}": v for k, v in vals.items()},
                     "ratio_Z2_over_Z1": r2, "ratio_Z4_over_Z1": r4})
        print(f"{tag:16s} " + " ".join(f"{vals[k]:12.5e}" for k in CASES)
              + f" {r2:8.4f} {r4:8.4f}", flush=True)

    with open(OUT / "damage_uncertainty_resolution.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    r2 = [r["ratio_Z2_over_Z1"] for r in rows]
    r4 = [r["ratio_Z4_over_Z1"] for r in rows]
    print("\n=== RESOLUTION VERDICT ===")
    for nm, rr in (("Z2 / Z1", r2), ("Z4 / Z1", r4)):
        eff = 100 * (np.mean(rr) - 1.0)
        spread = 100 * (max(rr) - min(rr))
        v = ("RESOLVED" if abs(eff) > 3 * spread else
             "MARGINAL" if abs(eff) > spread else "UNRESOLVED")
        print(f"  {nm}: effect {eff:+.1f} %, spread across ALL perturbations {spread:.1f} pp, "
              f"ratio {abs(eff)/max(spread,1e-9):.1f}x  -> {v}")
    print(f"\nwrote damage_uncertainty_resolution.csv")


if __name__ == "__main__":
    main()
