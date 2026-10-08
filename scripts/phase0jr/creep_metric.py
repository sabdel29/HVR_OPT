#!/usr/bin/env python3
"""Phase-0J-R Sec.4/6/7 -- M4 (accumulated CREEP strain) and M5 (creep energy density).

Syed's epsilon_acc is ACCUMULATED CREEP STRAIN, taken from ANSYS `NL,CREQ`. It is NOT
plastic+creep. Our PEEQ is plastic+creep and CalculiX produces no separate creep field
(CEEQ/CE/PE are all aliased to PEEQ), so Sec.6 forbids feeding PEEQ into Syed's constant.

M4 is therefore RECONSTRUCTED, not estimated: the creep strain increment is integrated from
the SOLVER'S OWN Norton card, evaluated on the SOLVER'S OWN stress and temperature output,
using the SAME linear-in-temperature interpolation CalculiX applies to a *CREEP table.

    eps_dot_cr = A(T) * sigma_eq ^ n(T)          (LAW=NORTON, m = 0)
    M4 = <  sum_k  0.5*(rate_k + rate_k-1) * dt_k  >_V      over the stabilised cycle
    M5 = <  sum_k  sigma_eq,mid * d_eps_cr_k     >_V        (creep work only)

The reconstruction is VALIDATED against the creep-only (EC) deck, where there is no plastic
card at all and therefore M4 must equal d(PEEQ) exactly.
"""
from __future__ import annotations
import bisect, csv, math, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from solder_model import calculix_cards                                    # noqa: E402
from decompose import parse_temperature, parse_tensors                     # noqa: E402

OUT = R / "results" / "phase0jr"
TEMPS = [-40.0, 0.0, 25.0, 50.0, 75.0, 100.0, 125.0]
_CREEP = calculix_cards(TEMPS)["creep"]            # [(A, n, m, T), ...] exactly as written
_CT = [t for *_, t in _CREEP]
_CA = [a for a, *_ in _CREEP]
_CN = [c[1] for c in _CREEP]


def norton_at_T(T: float) -> tuple[float, float]:
    """A(T), n(T) by LINEAR interpolation of the card rows -- CalculiX's own convention.

    Not log-interpolation: CalculiX interpolates the tabulated values themselves, and A spans
    many decades, so the two differ materially. Matching the solver is the whole point.
    """
    if T <= _CT[0]:
        return _CA[0], _CN[0]
    if T >= _CT[-1]:
        return _CA[-1], _CN[-1]
    i = bisect.bisect_right(_CT, T) - 1
    f = (T - _CT[i]) / (_CT[i + 1] - _CT[i])
    return _CA[i] + f * (_CA[i + 1] - _CA[i]), _CN[i] + f * (_CN[i + 1] - _CN[i])


# *PLASTIC card, bilinear: (sigma0, 0) -> (sigma_sat, 0.02), tabulated at these temperatures.
_PL = calculix_cards(TEMPS)["plastic"]                 # [(stress, pstrain, T), ...]
_PT = sorted({t for *_, t in _PL})
_PY0 = {t: [s for s, e, tt in _PL if tt == t and e == 0.0][0] for t in _PT}
_PYS = {t: [s for s, e, tt in _PL if tt == t and e > 0.0][0] for t in _PT}
_PEP = {t: [e for s, e, tt in _PL if tt == t and e > 0.0][0] for t in _PT}


def yield_at(T: float, peeq: float) -> float:
    """Current yield stress sigma_y(T, PEEQ) from the bilinear card, linear in T.

    CalculiX holds the last tabulated point beyond the curve, so PEEQ is clamped at 0.02.
    """
    if T <= _PT[0]:
        i, f = 0, 0.0
    elif T >= _PT[-1]:
        i, f = len(_PT) - 2, 1.0
    else:
        i = bisect.bisect_right(_PT, T) - 1
        f = (T - _PT[i]) / (_PT[i + 1] - _PT[i])
    def sy(t):
        p = min(max(peeq, 0.0), _PEP[t])
        return _PY0[t] + (_PYS[t] - _PY0[t]) * p / _PEP[t]
    return sy(_PT[i]) + f * (sy(_PT[i + 1]) - sy(_PT[i]))


def svm(S) -> float:
    sx, sy, sz, sxy, sxz, syz = S
    return math.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                     + 3.0 * (sxy * sxy + sxz * sxz + syz * syz))


def creep_series(dat: Path, core: set):
    """{elem: [(t, T, sigma_eq, PEEQ)]} for elements with a full history."""
    data = parse_tensors(dat, core)
    temps = parse_temperature(dat)
    vols = {e: d["V"] for per in data.values() for e, d in per.items() if "V" in d}
    ser = {}
    for t in sorted(data):
        T = temps.get(t)
        if T is None:
            continue
        for e, d in data[t].items():
            if "S" in d and "P" in d:
                ser.setdefault(e, []).append((t, T, svm(d["S"]), d["P"]))
    return {e: v for e, v in ser.items() if len(v) > 8}, vols


NSUB = 24            # sub-intervals per output interval for the stiff Norton integral


def driving_stress(sig: float, T: float, peeq: float, has_plastic: bool) -> float:
    """The stress the solver's creep law actually sees.

    PROVEN BY PROBE, not assumed (scripts/phase0jr/probe_viscoplastic.py): with no *PLASTIC
    card CalculiX integrates A*sigma^n; with a *PLASTIC card present it integrates the
    OVERSTRESS form A*(sigma - sigma_y)^n. A single C3D8 under constant load reproduces the
    measured rate to 4-5 significant figures without plasticity and to 3 with it.
    """
    return sig if not has_plastic else max(sig - yield_at(T, peeq), 0.0)


def cycle_creep(ser, vols, t0, t1, elems=None, has_plastic=True):
    """Volume-averaged M4, M5 and d(PEEQ) over the window (t0, t1]."""
    m4n = m5n = dpn = den = 0.0
    for e, rows in ser.items():
        if elems is not None and e not in elems:
            continue
        w = [r for r in rows if t0 - 1e-9 < r[0] <= t1 + 1e-9]
        if len(w) < 3:
            continue
        v = vols.get(e, 1.0)
        ecr = wcr = 0.0
        for k in range(1, len(w)):
            (ta, Ta, sa, pa), (tb, Tb, sb, pb) = w[k - 1], w[k]
            dt = tb - ta
            if dt <= 0:
                continue
            # SUB-STEP: the Norton rate goes as sigma^8, so a trapezoid across a 15 s output
            # interval over-weights the high-stress end badly. Sigma, T and PEEQ are
            # interpolated linearly and the rate is integrated on NSUB sub-intervals.
            acc = 0.0; wk = 0.0
            for j in range(NSUB):
                f0, f1 = j / NSUB, (j + 1) / NSUB
                fm = 0.5 * (f0 + f1)
                Tm = Ta + fm * (Tb - Ta)
                sm = sa + fm * (sb - sa)
                pm = pa + fm * (pb - pa)
                dr = driving_stress(sm, Tm, pm, has_plastic)
                Am, nm = norton_at_T(Tm)
                rm = Am * (dr ** nm) if dr > 0 else 0.0
                de_j = rm * dt / NSUB
                acc += de_j
                wk += sm * de_j          # sigma_eq : d_eps_cr -- full stress does the work
            de = acc
            ecr += de
            wcr += wk
        m4n += ecr * v; m5n += wcr * v
        dpn += (w[-1][3] - w[0][3]) * v; den += v
    if not den:
        return None
    return {"M4_creep_strain": m4n / den, "M5_creep_energy_MJ_per_m3": m5n / den,
            "d_peeq": dpn / den, "vol_mm3": den}
