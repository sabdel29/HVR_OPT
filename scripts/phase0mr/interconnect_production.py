#!/usr/bin/env python3
"""Phase-0M-R Section 5 -- geometry-specific transition resistance, in production.

WHAT IS REPLACED
    R_total = 1.326 * R_bulk          one global constant for BGA, C4, TSV and microbump
WHAT REPLACES IT
    R_total = R_bulk(geometry, T) + dR_transition(class, geometry, T)
with a SEPARATE dR per interconnect class, computed EXACTLY for that class's production
geometry by the finite-volume solver cross-validated against MOOSE in Section 4. No shared
multiplier anywhere, and no fitted surrogate.

`dR` IS A DIFFERENCE AGAINST A STATED 1-D REFERENCE, NOT AN "EXCESS".
Section 4 proved the two terminals of the 3-D solve are equipotential planes at the via
bottom and the trace exit. The 1-D reference is a series of named conductors with implicit
equipotential cross-sections EVERYWHERE, which is a different constraint. `dR` can therefore
be negative -- a generous landing pad really does lower the resistance below the 1-D series
of via plus full-length trace, because part of that trace is replaced by a wider pad. Calling
that an "excess" would be wrong, and Phase 0M did.

WHY THERE IS NO SURROGATE. A two-term logarithmic form, which is what constriction theory
suggests,

    dR * t_rdl / rho  =  a ln(r_pad/r_via) + b ln(2 r_pad/w_trace) + c

was fitted over 178 solved geometries and REJECTED. Measured against the SPREAD of the
dimensionless group rather than against its magnitude, the residual is 9.8 % (TSV), 9.0 %
(microbump), 13.6 % (BGA) and 28.9 % (C4) -- the last being the worst, not the best, even
though a naive relative-error metric made it look like 6 %. That metric was wrong in both
directions and is recorded here rather than quietly replaced.

The production path does not need a surrogate: the optimizer is forbidden, so only a handful
of geometries are ever evaluated. `transition_dR()` therefore SOLVES each one exactly and
caches it against a geometry fingerprint. The swept table is retained for sensitivity, and
the rejected fit is retained as a negative result.
"""
from __future__ import annotations
import csv, json, math, sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0e", "phase0dr"):
    sys.path.insert(0, str(R / "scripts" / d))
import crowding as CR                                                      # noqa: E402
from interconnect import rho_cu, rho_solder                                # noqa: E402

OUT = R / "results" / "phase0mr"
OUT.mkdir(parents=True, exist_ok=True)
T_C = 85.0
FIT_JSON = OUT / "transition_surrogate.json"

# geometry ranges the surrogate is fitted over and may be used within
RANGE = {"pad_over_via": (1.0, 2.5), "trace_over_pad": (0.15, 2.0),
         "r_via_um": (2.5, 60.0), "t_rdl_um": (2.5, 40.0)}


class OutOfRange(Exception):
    """The surrogate was asked for a geometry outside its fitted envelope."""


@dataclass(frozen=True)
class TransitionFit:
    cls: str
    a: float
    b: float
    c: float
    rms_pct: float
    max_pct: float
    n: int

    def dR(self, r_via: float, r_pad: float, w_trace: float, t_rdl: float,
           rho: float, strict: bool = True) -> float:
        pv, tp = r_pad / r_via, w_trace / (2 * r_pad)
        if strict:
            for nm, v, (lo, hi) in (("pad_over_via", pv, RANGE["pad_over_via"]),
                                    ("trace_over_pad", tp, RANGE["trace_over_pad"]),
                                    ("r_via_um", r_via * 1e6, RANGE["r_via_um"]),
                                    ("t_rdl_um", t_rdl * 1e6, RANGE["t_rdl_um"])):
                if not (lo * (1 - 1e-9) <= v <= hi * (1 + 1e-9)):
                    raise OutOfRange(f"{self.cls}: {nm} = {v:.4g} outside [{lo}, {hi}]")
        g = (self.a * math.log(r_pad / r_via)
             + self.b * math.log(2 * r_pad / w_trace) + self.c)
        return g * rho / t_rdl


def _cell(cls: str, r_via, r_pad, w, t_rdl, l_trace) -> CR.Cell:
    sig_m = 1.0 / rho_cu(T_C)
    sig_v = (1.0 / rho_solder(T_C)) if cls in ("bga", "c4") else sig_m
    h_via = {"tsv": 30e-6, "microbump": 10e-6, "c4": 70e-6, "bga": 300e-6}[cls]
    return CR.Cell(name=f"{cls}_fit", r_via=r_via, h_via=h_via, r_pad=r_pad,
                   w_trace=w, t_rdl=t_rdl, l_trace=l_trace,
                   sigma_via=sig_v, sigma_metal=sig_m)


CLASS_GRID = {
    "tsv": dict(r_via=[7.5e-6, 15e-6, 25e-6], pad=[1.0, 1.2, 1.6, 2.2],
                tp=[0.2, 0.35, 0.6, 1.0], t=[5e-6, 10e-6, 20e-6], l=100e-6),
    "microbump": dict(r_via=[2.5e-6, 5e-6, 10e-6], pad=[1.0, 1.2, 1.6, 2.2],
                      tp=[0.25, 0.5, 1.0], t=[2.5e-6, 5e-6], l=40e-6),
    "c4": dict(r_via=[25e-6, 50e-6], pad=[1.0, 1.2, 1.6], tp=[0.5, 1.0, 1.6],
               t=[10e-6, 15e-6], l=300e-6),
    "bga": dict(r_via=[100e-6, 200e-6], pad=[1.0, 1.2, 1.5], tp=[0.5, 1.0, 1.5],
                t=[20e-6, 40e-6], l=800e-6),
}


def build_fits(refine: float = 1.0) -> dict:
    fits, raw = {}, []
    for cls, g in CLASS_GRID.items():
        X, Y = [], []
        for rv in g["r_via"]:
            for pv in g["pad"]:
                for tp in g["tp"]:
                    for t in g["t"]:
                        rp, w = pv * rv, tp * 2 * pv * rv
                        if w < 1.5e-6 or w > 1.9 * rp:
                            continue
                        c = _cell(cls, rv, rp, w, t, g["l"])
                        try:
                            r = CR.solve_cell(c, refine=refine)
                        except Exception as e:                # noqa: BLE001
                            raw.append({"cls": cls, "status": f"FAIL {type(e).__name__}"})
                            continue
                        if r.get("status") != "OK":
                            raw.append({"cls": cls, "status": r.get("status")})
                            continue
                        rho = 1.0 / c.sigma_metal
                        dr = (r["R_3D_mohm"] - r["R_bulk_mohm"]) * 1e-3
                        X.append([math.log(rp / rv), math.log(2 * rp / w), 1.0])
                        Y.append(dr * t / rho)
                        raw.append({"cls": cls, "r_via_um": rv * 1e6, "pad_over_via": pv,
                                    "trace_over_pad": tp, "t_rdl_um": t * 1e6,
                                    "R_3D_mohm": r["R_3D_mohm"],
                                    "R_bulk_mohm": r["R_bulk_mohm"],
                                    "dR_mohm": dr * 1e3, "g_dimensionless": dr * t / rho,
                                    "status": "OK"})
        if len(X) < 6:
            print(f"  {cls}: only {len(X)} usable points, NOT FITTED")
            continue
        A = np.array(X); b = np.array(Y)
        coef, *_ = np.linalg.lstsq(A, b, rcond=None)
        pred = A @ coef
        den = np.maximum(np.abs(b), np.percentile(np.abs(b), 25))
        err = 100 * np.abs(pred - b) / den
        fits[cls] = TransitionFit(cls, float(coef[0]), float(coef[1]), float(coef[2]),
                                  float(np.sqrt((err ** 2).mean())), float(err.max()),
                                  len(X))
        print(f"  {cls:10s} n={len(X):3d}  a={coef[0]:+.5f} b={coef[1]:+.5f} "
              f"c={coef[2]:+.5f}  rms {fits[cls].rms_pct:.2f} %  max {fits[cls].max_pct:.2f} %",
              flush=True)
    with open(OUT / "transition_surrogate_fit_data.csv", "w", newline="") as fh:
        k = sorted({x for r in raw for x in r})
        w_ = csv.DictWriter(fh, fieldnames=k); w_.writeheader(); w_.writerows(raw)
    FIT_JSON.write_text(json.dumps(
        {c: {"a": f.a, "b": f.b, "c": f.c, "rms_pct": f.rms_pct, "max_pct": f.max_pct,
             "n": f.n} for c, f in fits.items()}, indent=2))
    return fits


def load_fits() -> dict:
    d = json.loads(FIT_JSON.read_text())
    return {c: TransitionFit(c, v["a"], v["b"], v["c"], v["rms_pct"], v["max_pct"], v["n"])
            for c, v in d.items()}




# ---------------------------------------------------------------------------
# the PRODUCTION entry point: exact, cached, never extrapolated
# ---------------------------------------------------------------------------
CACHE_JSON = OUT / "transition_dR_cache.json"
_CACHE: dict | None = None


def _key(cls, r_via, r_pad, w, t_rdl, l_trace, t_c) -> str:
    return ("%s|rv=%.4g|rp=%.4g|w=%.4g|t=%.4g|l=%.4g|T=%.4g"
            % (cls, r_via * 1e6, r_pad * 1e6, w * 1e6, t_rdl * 1e6, l_trace * 1e6, t_c))


def transition_dR(cls: str, r_via: float, r_pad: float, w_trace: float, t_rdl: float,
                  l_trace: float, t_c: float = T_C, refine: float = 1.3,
                  recompute: bool = False) -> dict:
    """dR = R_3D - R_1D for ONE class at ONE geometry, solved exactly and cached.

    The 1-D reference is `Cell.r_bulk()`, the same series of named conductors the production
    tier model uses, so the difference is well posed.
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(CACHE_JSON.read_text()) if CACHE_JSON.is_file() else {}
    k = _key(cls, r_via, r_pad, w_trace, t_rdl, l_trace, t_c)
    if k in _CACHE and not recompute:
        return _CACHE[k]
    c = _cell(cls, r_via, r_pad, w_trace, t_rdl, l_trace)
    r = CR.solve_cell(c, refine=refine)
    if r.get("status") != "OK":
        raise RuntimeError(f"transition solve failed for {k}: {r.get('status')}")
    rb = c.r_bulk()
    out = {"cls": cls, "R_3D_ohm": r["R_3D_mohm"] * 1e-3, "R_1D_ohm": rb,
           "dR_ohm": r["R_3D_mohm"] * 1e-3 - rb,
           "ratio_3D_over_1D": r["R_3D_mohm"] * 1e-3 / rb,
           "J_peak_over_avg": r["J_peak_over_avg"],
           "n_cells": r["n_cells"], "key": k}
    _CACHE[k] = out
    CACHE_JSON.write_text(json.dumps(_CACHE, indent=1))
    return out


if __name__ == "__main__":
    build_fits()
    print(f"wrote {FIT_JSON}")
