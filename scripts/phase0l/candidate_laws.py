#!/usr/bin/env python3
"""Phase-0L Parts VIII & X -- candidate SAC305 constitutive forms and their source-data tests.

Candidates (all expressed as uniaxial steady-state rate laws eps_dot(sigma, T)):

  M0  AS-BUILT     Norton on the OVERSTRESS, A,n from the sigma_applied fit, Chaboche sigma_y.
                   This is what the framework runs today.
  M1  NORTON-ZY    Same A(T), n(T), yield surface removed (sigma_y -> 0).  Fit variable then
                   equals solver variable.
  M2  GAROFALO-ZY  Hyperbolic-sine, Yuan 2023 Table 6, yield surface removed.
  M3  ANAND-ZY     Anand steady state, Yuan 2023 Tables 6/7/9 (EINN+BI), yield removed.

Provenance note carried through every result: M1 and M2 rest on Xiao & Armstrong (2005)
Sn3.9Ag0.6Cu data; only M3 rests on SAC305 (Motalab et al.) measurements.
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
import solder_model as sm                                                   # noqa: E402

RG = 8.314462618

GAROFALO = {                       # Yuan 2023 Table 6
    "xiao_armstrong": dict(C1=0.184, C2=0.221, C3=2.89, Q=62000.0),
    "einn":           dict(C1=0.539, C2=0.473, C3=1.055, Q=65000.0),
    "einn_bi":        dict(C1=0.443, C2=0.482, C3=1.073, Q=65000.0),
}
# Anand, Yuan 2023 Tables 7 and 9.  Q = 65 kJ/mol: Yuan section 4.2 states "The same
# activation energy as in the previous section is applied", the previous section being the
# Garofalo EINN extraction at Q = 65,000 J/mol.  Motalab's own column is NOT usable here
# because Yuan does not report Motalab's activation energy.
ANAND_EINN_BI = dict(A=1649.0, n=1.64e-4, m=0.53, beta=4.16, xi=17.66,
                     s0=57.45, a=2.26, h0=828822.0, Q=65000.0)


def garofalo_rate(sig, T_c, which="einn_bi"):
    p = GAROFALO[which]
    return p["C1"] * np.sinh(p["C2"] * np.asarray(sig, float)) ** p["C3"] \
        * np.exp(-p["Q"] / (RG * (T_c + 273.15)))


def anand_sigma_star(edot, T_c, p=ANAND_EINN_BI):
    """Yuan Eq.(10): the saturation (steady-state flow) stress at a given rate/temperature."""
    z = (edot / p["A"]) * math.exp(p["Q"] / (RG * (T_c + 273.15)))
    return p["beta"] * z ** p["n"] * math.asinh(z ** p["m"])


def anand_rate(sig, T_c, p=ANAND_EINN_BI):
    """Invert Eq.(10) for eps_dot at a given steady-state stress."""
    f = lambda le: anand_sigma_star(math.exp(le), T_c, p) - sig
    lo, hi = -80.0, 20.0
    try:
        if f(lo) > 0 or f(hi) < 0:
            return float("nan")
        return math.exp(brentq(f, lo, hi, xtol=1e-12, rtol=1e-13, maxiter=300))
    except Exception:
        return float("nan")


def norton_zy_rate(sig, T_c):
    A, n = (sm.fit_norton_data(T_c)["A"], sm.fit_norton_data(T_c)["n"]) \
        if T_c in sm.DATA_TEMPS else (sm.norton_at(T_c)["A"], sm.norton_at(T_c)["n"])
    return A * np.asarray(sig, float) ** n


def asbuilt_rate(sig, T_c):
    A, n = (sm.fit_norton_data(T_c)["A"], sm.fit_norton_data(T_c)["n"]) \
        if T_c in sm.DATA_TEMPS else (sm.norton_at(T_c)["A"], sm.norton_at(T_c)["n"])
    y = sm.sigma0_of_T(T_c)
    s = np.asarray(sig, float)
    return np.where(s > y, A * np.maximum(s - y, 0.0) ** n, 0.0)


MODELS = {
    "M0_ASBUILT":    asbuilt_rate,
    "M1_NORTON_ZY":  norton_zy_rate,
    "M2_GAROFALO_ZY": lambda s, T: garofalo_rate(s, T, "einn_bi"),
    "M3_ANAND_ZY":   lambda s, T: (np.array([anand_rate(float(x), T) for x in np.atleast_1d(s)])
                                   if np.ndim(s) else anand_rate(float(s), T)),
}
