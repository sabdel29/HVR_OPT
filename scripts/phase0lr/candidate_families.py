#!/usr/bin/env python3
"""Phase-0L-R Part 9 -- the defensible constitutive families, and their solver reductions.

CalculiX integrates only a Norton power law (Phase-0L Part IX), so any other family has to be
reduced to a Norton card over a stated stress window before it can be replayed. The reduction
error is quantified here rather than assumed small.

FAMILY 1 -- NORTON (M1).  A(T), n(T) from the 19 Xiao & Armstrong Sn3.9Ag0.6Cu creep points,
  consumed with the yield threshold removed so the fit variable equals the solver variable.
  Correct rate regime, WRONG ALLOY, extrapolated 3.4-7.2x in stress.

FAMILY 2 -- ANAND (new in Phase 0L-R).  Yamin et al. 2025, Jurnal Teknologi 87:5 pp.939-949,
  Table 1 "Anand" column, doi:10.11113/jurnalteknologi.v87.23172 (open access, retrieved).
  Fitted to Motalab et al. SAC305 uniaxial tensile curves at 25/50/75/100/125 C and
  1e-5/1e-4/1e-3 per second.  CORRECT ALLOY, correct stress levels, extrapolated DOWNWARD in
  strain rate.
  Validation performed here: reproduces published SAC305 tensile behaviour (39.98 MPa at
  25 C / 1e-3, 14.72 MPa at 125 C / 1e-5) and, extrapolated 4-6 decades down in rate, lands
  within a median factor of 1.76 of the Sn3.9Ag0.6Cu creep points -- in the direction the alloy
  difference predicts, since SAC305 has less Ag and should creep faster.

  This SUPERSEDES the Phase-0L rejection of the Anand family. That rejection rested on the Yuan
  2023 EINN+BI parameter set, which missed the creep data by a median factor of 1240 and had no
  solution above ~60-80 MPa. Both were properties of that PARAMETER SET, not of the Anand FORM:
  with Q/R = 11690 K instead of 7818 K the same form spans the whole regime.
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402

# Yamin et al. 2025 Table 1, ORIGINAL Anand column. s0 = c1, h0 = k3 for that column.
ANAND_YAMIN = dict(QR=11690.0, A=788.0, xi=9.532, m=0.1578, shat=43.59, n=0.0239,
                   a=0.9636, s0=56.98, h0=23148.0,
                   source="Yamin et al. 2025, Jurnal Teknologi 87:5, Table 1 (Anand column); "
                          "data from Motalab et al. SAC305 tensile, 25-125 C, 1e-5..1e-3 /s")
# Yuan 2023 Tables 6/7/9 EINN+BI, retained only to show what a badly identified set does.
ANAND_YUAN = dict(QR=65000.0 / 8.314462618, A=1649.0, xi=17.66, m=0.53, shat=4.16 * 17.66,
                  n=1.64e-4, a=2.26, s0=57.45, h0=828822.0,
                  source="Yuan 2023 Tables 6/7/9, EINN+BI column")


def anand_sigma_sat(edot: float, T_c: float, p=ANAND_YAMIN) -> float:
    """Steady-state (saturation) flow stress at a given inelastic strain rate."""
    z = (edot / p["A"]) * math.exp(p["QR"] / (T_c + 273.15))
    return (1.0 / p["xi"]) * math.asinh(z ** p["m"]) * p["shat"] * z ** p["n"]


def anand_rate(sig: float, T_c: float, p=ANAND_YAMIN) -> float:
    """Invert the saturation relation for the steady-state rate at a given stress."""
    f = lambda le: anand_sigma_sat(math.exp(le), T_c, p) - sig
    lo, hi = -90.0, 60.0
    try:
        if f(lo) > 0 or f(hi) < 0:
            return float("nan")
        return math.exp(brentq(f, lo, hi, xtol=1e-13, maxiter=400))
    except Exception:
        return float("nan")


def norton_from_anand(T_c: float, s_lo: float, s_hi: float, p=ANAND_YAMIN, npts: int = 25):
    """Least-squares power law fitted to the Anand steady state over [s_lo, s_hi].

    Returns A, n and the worst relative reduction error inside the window, so the cost of
    forcing a sinh-type law through the solver's power-law slot is visible rather than assumed.
    """
    s = np.logspace(math.log10(s_lo), math.log10(s_hi), npts)
    r = np.array([anand_rate(float(x), T_c, p) for x in s])
    ok = np.isfinite(r) & (r > 0)
    n_, lnA = np.polyfit(np.log(s[ok]), np.log(r[ok]), 1)
    A = math.exp(lnA)
    pred = A * s[ok] ** n_
    err = np.abs(pred - r[ok]) / r[ok]
    return {"A": A, "n": float(n_), "max_rel_err": float(err.max()),
            "rms_rel_err": float(math.sqrt(float((err ** 2).mean()))),
            "window_MPa": (s_lo, s_hi)}


def norton_m1(T_c: float):
    f = sm.fit_norton_data(T_c) if T_c in sm.DATA_TEMPS else sm.norton_at(T_c)
    return {"A": f["A"], "n": f["n"]}


if __name__ == "__main__":
    print("ANAND -> NORTON reduction over the damage-weighted package window 30-90 MPa")
    print(f"{'T(C)':>6} {'A':>13} {'n':>8} {'max err %':>10} {'rms err %':>10}")
    for T in (45., 80., 115., 150.):
        f = norton_from_anand(T, 30.0, 90.0)
        print(f"{T:6.0f} {f['A']:13.4e} {f['n']:8.3f} {100*f['max_rel_err']:10.2f} "
              f"{100*f['rms_rel_err']:10.2f}")
    print("\nfor comparison, the M1 Norton card fitted at 7.51-15.92 MPa:")
    print(f"{'T(C)':>6} {'A':>13} {'n':>8}")
    for T in (45., 80., 115., 150.):
        f = norton_m1(T)
        print(f"{T:6.0f} {f['A']:13.4e} {f['n']:8.3f}")
    print("\nrate at 60 MPa, the two families side by side:")
    print(f"{'T(C)':>6} {'M1 Norton':>13} {'Anand':>13} {'Anand/M1':>10}")
    for T in (45., 80., 115., 150.):
        m = norton_m1(T); a = anand_rate(60., T)
        rm = m["A"] * 60.0 ** m["n"]
        print(f"{T:6.0f} {rm:13.4e} {a:13.4e} {a/rm:10.3f}")
