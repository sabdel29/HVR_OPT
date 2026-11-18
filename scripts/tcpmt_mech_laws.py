"""Solder constitutive laws of the local submodel, from configs/tcpmt_mech (finding 1).

WHAT WAS WRONG (expert review, round 3; verified in code and data)
  * The production card (phase0i/solder_model.py -> decompose.material('EPC')) is a Norton
    law fitted to the APPLIED stress of 19 creep points, but CalculiX integrates the
    OVERSTRESS sigma_vm - sigma_y under *VISCO (*PLASTIC acts as a creep threshold;
    results/phase0l/CALCULIX_CREEP_IMPLEMENTATION_AUDIT.md). The card therefore does not
    reproduce its own calibration data.
  * The data are Sn3.9Ag0.6Cu (Xiao and Armstrong 2005), not SAC305.
  * A Chaboche KINEMATIC fit (Yuan 2023 Table 10) became ISOTROPIC hardening that saturates
    at an arbitrary 2 % inelastic strain; it is what made the responses drift for 48 cycles.
  * The rows below 45 C (25 C, the cold dwell) are extrapolated.
  * The joints creep at 26-208 MPa (strain-weighted window) against a 7.5-15.9 MPa
    calibration window.

WHAT THIS MODULE DOES
  Every law is written with a ZERO yield surface (flat *PLASTIC at yield_zero_MPa), so the
  solver integrates A sigma_vm^n, the variable the law was fitted in (self-consistent). A
  Garofalo law is carried as a temperature-dependent Norton surrogate, least-squares fitted
  in ln-ln at every card row over the stress window the joints visit at that temperature;
  the window is iterated to self-consistency by scripts/tcpmt_mech_law_band.py and stored in
  research/tcpmt_revision/solder_law_cards.json. The fit error and the visited window travel
  with the card. CalculiX 2.23 has no sinh creep law without a recompiled user subroutine.

    python tcpmt_mech_laws.py --record   -> research/tcpmt_revision/solder_law_record.json
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0ir", "scripts/phase0i", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import solder_model as SM                                           # noqa: E402

CFG_PATH = R / "configs" / "tcpmt_mech" / "mechanics_revision.yaml"
TR = R / "research" / "tcpmt_revision"
CARDS = TR / "solder_law_cards.json"
RECORD = TR / "solder_law_record.json"
R_GAS = 8.314462618


def _val(x):
    return x["value"] if isinstance(x, dict) and "value" in x else x


@lru_cache(maxsize=1)
def cfg() -> dict:
    return yaml.safe_load(CFG_PATH.read_text())


def solder_cfg() -> dict:
    return cfg()["solder"]


def law_cfg(name: str) -> dict:
    laws = solder_cfg()["laws"]
    if name not in laws:
        raise KeyError(f"unknown solder law {name!r}; configured: {sorted(laws)}")
    return laws[name]


def rows_C() -> list:
    a, b, s = solder_cfg()["card_rows_C"]
    n = int(round((b - a) / s)) + 1
    return [round(a + s * k, 6) for k in range(n)]


def E_of_T(T_c: float) -> float:
    e = solder_cfg()["elastic"]
    return max(float(e["E_floor_MPa"]), float(_val(e["E_ref_MPa"]))
               + float(_val(e["E_slope_MPa_per_K"])) * (T_c - float(e["T_ref_C"])))


def nu() -> float:
    return float(_val(solder_cfg()["elastic"]["nu"]))


def cte() -> float:
    return float(_val(solder_cfg()["cte_per_K"]))


# ------------------------------------------------------------------------------ rates
def _arrhenius(law: dict, T_c: float) -> float:
    q_r = law.get("Q_over_R_K")
    if q_r is None:
        q_r = float(law["Q_J_per_mol"]) / R_GAS
    return math.exp(-float(q_r) / (T_c + 273.15))


def rate(name: str, sigma_mpa, T_c: float):
    """Steady-state creep rate (1/s) of law `name` at von Mises stress sigma (MPa)."""
    law = law_cfg(name)
    s = np.asarray(sigma_mpa, dtype=float)
    if law["form"] == "garofalo":
        return (float(law["C1_per_s"]) * np.sinh(float(law["alpha_per_MPa"]) * s)
                ** float(law["n"]) * _arrhenius(law, T_c))
    if law["form"] == "measured_norton":
        f = SM.norton_at(float(T_c))
        return f["A"] * s ** f["n"]
    raise ValueError(f"law {name}: unknown form {law['form']!r}")


def fit(name: str, T_c: float, lo: float, hi: float, npt: int = 400,
        constrained: bool = True) -> dict:
    """Norton surrogate A sigma^n of law `name` at T_c, least squares in ln(rate) vs
    ln(sigma) over [lo, hi] MPa; with constrained=True subject to the incplas.f floor."""
    law = law_cfg(name)
    floor = float(solder_cfg()["norton_A_floor"])
    if law["form"] == "measured_norton":
        f = SM.norton_at(float(T_c))
        lnA, n = math.log(f["A"]), float(f["n"])
        below = lnA < math.log(floor)
        if constrained and below:
            lnA = math.log(floor)
        s = np.logspace(math.log10(lo), math.log10(hi), 50)
        err = np.exp(lnA + n * np.log(s)) / (f["A"] * s ** f["n"]) - 1.0
        return {"T_C": T_c, "window_MPa": [lo, hi], "A_MPa_units": math.exp(lnA), "n": n,
                "unconstrained_fit_below_floor": bool(below),
                "floor_constraint_applied": bool(constrained and below),
                "max_rate_err_rel": float(np.max(np.abs(err))), "rms_rate_err_rel":
                    float(np.sqrt(np.mean(err ** 2))),
                "basis": f.get("basis"), "extrapolated_T": bool(
                    T_c < min(SM.DATA_TEMPS) - 1e-9 or T_c > max(SM.DATA_TEMPS) + 1e-9)}
    s = np.logspace(math.log10(lo), math.log10(hi), npt)
    y = np.log(rate(name, s, T_c))
    n, lnA = np.polyfit(np.log(s), y, 1)
    below = bool(lnA < math.log(floor))
    if constrained and below:
        lnA = math.log(floor)
        x = np.log(s)
        n = float(np.sum(x * (y - lnA)) / np.sum(x * x))
    err = np.exp(lnA + n * np.log(s) - y) - 1.0
    k = int(np.argmax(np.abs(err)))
    a = float(law["alpha_per_MPa"])
    neff = float(law["n"]) * a * s / np.tanh(a * s)
    return {"T_C": T_c, "window_MPa": [lo, hi], "A_MPa_units": math.exp(lnA), "n": float(n),
            "unconstrained_fit_below_floor": below,
            "floor_constraint_applied": bool(constrained and below),
            "max_rate_err_rel": float(abs(err[k])), "max_rate_err_at_MPa": float(s[k]),
            "rms_rate_err_rel": float(np.sqrt(np.mean(err ** 2))),
            "garofalo_local_exponent_range": [float(neff[0]), float(neff[-1])]}


def window_at(T_c: float, win: dict) -> tuple:
    """Hot window at and above T_hot_assign, cold window at and below the cold dwell
    temperature, geometric blend between (temperatures visited only during the ramps)."""
    w = solder_cfg()["window"]
    t_cold = float(cfg()["local"]["T_cold_C"])
    t_hot = float(w["T_hot_assign_C"])
    if T_c <= t_cold:
        return tuple(win["cold"])
    if T_c >= t_hot:
        return tuple(win["hot"])
    f = (T_c - t_cold) / (t_hot - t_cold)
    return tuple(math.exp((1 - f) * math.log(c) + f * math.log(h))
                 for c, h in zip(win["cold"], win["hot"]))


def card(name: str, win: dict | None = None, constrained: bool = True,
         material: str = "SOLDER") -> tuple:
    """(CalculiX material block, per-row fits) of law `name` with ZERO yield. `win` is
    {'hot': [lo, hi], 'cold': [lo, hi]} MPa; None takes the iterated window from
    solder_law_cards.json, or the configured initial window when none is stored."""
    if win is None:
        win = stored_window(name)[0]
    rows = [fit(name, T, *window_at(T, win), constrained=constrained) for T in rows_C()]
    y0 = float(solder_cfg()["yield_zero_MPa"])
    L = [f"*MATERIAL, NAME={material}", "*ELASTIC"]
    L += [f"{E_of_T(T):.6g}, {nu():.4g}, {T:.1f}" for T in rows_C()]
    L += ["*PLASTIC"] + [f"{y0:g}, 0.0, {T:.1f}" for T in rows_C()]
    L += ["*CREEP, LAW=NORTON"] + [f"{r['A_MPa_units']:.10e}, {r['n']:.10g}, 0.0, "
                                    f"{r['T_C']:.1f}" for r in rows]
    L += ["*EXPANSION, ZERO=25.", f"{cte():.6g}"]
    return "\n".join(L) + "\n", rows


def legacy_card(material: str = "SOLDER") -> str:
    """The round-1/2 production card (overstress Norton + bilinear isotropic hardening),
    only to reproduce the published numbers."""
    import decompose as DEC
    return DEC.material("EPC").replace("NAME=SAC305", f"NAME={material}")


def card_sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def stored_window(name: str) -> tuple:
    """(window, status) of law `name`: the iterated window when solder_law_cards.json has
    one, else the configured initial window (status 'initial')."""
    if CARDS.is_file():
        d = json.loads(CARDS.read_text())
        e = (d.get("laws") or {}).get(name) or {}
        if e.get("window_MPa"):
            return e["window_MPa"], ("converged" if e.get("converged") else "iterated, not "
                                     "converged")
    return dict(solder_cfg()["window"]["initial_MPa"]), "initial (not iterated)"


def production_card(material: str = "SOLDER") -> tuple:
    """(text, law name, window status) of the configured production law."""
    name = solder_cfg()["production_law"]
    win, status = stored_window(name)
    text, _rows = card(name, win, material=material)
    return text, name, status


# ------------------------------------------------------------------------------ windows
def wquantiles(vals, wts, qs):
    order = np.argsort(vals)
    v, w = np.asarray(vals, float)[order], np.asarray(wts, float)[order]
    if not len(v) or w.sum() <= 0:
        return [None for _ in qs]
    c = np.cumsum(w) / w.sum()
    return [float(v[min(int(np.searchsorted(c, q - 1e-12)), len(v) - 1)]) for q in qs]


def window_from_records(recs, weighting: str | None = None) -> dict:
    """Union over joint records of the per-phase quantile window of the core von Mises
    stress ('stress' block of tcpmt_mech_submodel records)."""
    w = solder_cfg()["window"]
    weighting = weighting or w["weighting"]
    key = "quantiles_MPa" if weighting == "strain" else "time_quantiles_MPa"
    out = {}
    for ph in ("hot", "cold"):
        qs = [(r.get("stress") or {}).get(ph, {}).get(key) for r in recs]
        qs = [q for q in qs if q and None not in q.values()]
        if qs:
            out[ph] = [min(q["lo"] for q in qs), max(q["hi"] for q in qs)]
    return out


# ------------------------------------------------------------------------------ record
def data_agreement(name: str) -> dict:
    """Rate of law `name` against the 19 measured Sn3.9Ag0.6Cu points (inside their own
    window), as max/min ratio: how far the band laws are apart where data exist."""
    r = [float(rate(name, s, T)) / e for T, s, e in SM.CREEP_DATA]
    return {"ratio_min": min(r), "ratio_max": max(r),
            "ratio_geomean": float(math.exp(np.mean(np.log(r))))}


def law_record() -> dict:
    """For the paper: per law, the alloy, the calibration window, what the visited window
    and card rows extrapolate, and the surrogate's fit error over the visited window."""
    sc = solder_cfg()
    out = {"what": "constitutive laws of the local solder submodel (TCPMT round 3, finding 1)",
           "solver_form": "eps_dot = A(T) (sigma_vm - sigma_y)^n(T), sigma_y = "
                          f"{sc['yield_zero_MPa']:g} MPa (zero yield: the solver integrates "
                          "the applied von Mises stress the laws were fitted in)",
           "production_law": sc["production_law"], "band_laws": sc["band_laws"],
           "elastic": {"E_ref_MPa": _val(sc["elastic"]["E_ref_MPa"]),
                       "E_slope_MPa_per_K": _val(sc["elastic"]["E_slope_MPa_per_K"]),
                       "nu": nu(), "cte_per_K": cte(),
                       "status": "ASSUMPTION (room-temperature band, Paska 2024; slope "
                                 "assumed)"},
           "hardening": "none: the zero-yield laws carry no rate-independent hardening (the "
                        "round-2 card's isotropic 2 % saturation of a kinematic Chaboche fit "
                        "is retired)",
           "laws": {}}
    for name in sc["band_laws"]:
        law = law_cfg(name)
        win, status = stored_window(name)
        cal = law.get("calibration") or {}
        rows = [fit(name, T, *window_at(T, win)) for T in rows_C()]
        t_cal = cal.get("T_C")
        s_cal = cal.get("stress_MPa")
        visited_T = (json.loads(CARDS.read_text()).get("laws", {}).get(name, {})
                     .get("visited_T_C") if CARDS.is_file() else None)
        ext = {"stress_hot": None, "stress_cold": None, "rows_outside_T": None}
        if s_cal:
            ext["stress_hot"] = [max(0.0, s_cal[0] - win["hot"][0]),
                                 max(0.0, win["hot"][1] - s_cal[1])]
            ext["stress_cold"] = [max(0.0, s_cal[0] - win["cold"][0]),
                                  max(0.0, win["cold"][1] - s_cal[1])]
        if t_cal:
            ext["rows_outside_T"] = [T for T in rows_C() if T < t_cal[0] or T > t_cal[1]]
            ext["cold_dwell_25C_extrapolated"] = 25.0 < t_cal[0]
        out["laws"][name] = {
            "form": law["form"], "alloy": law["alloy"], "source": law["source"],
            "calibration_window": cal, "visited_window_MPa": win, "window_status": status,
            "visited_joint_T_C": visited_T,
            "extrapolation_MPa_beyond_calibration": ext,
            "surrogate_max_rate_err_rel_hot": max(
                r["max_rate_err_rel"] for r in rows if r["T_C"] >= 75.0),
            "surrogate_max_rate_err_rel_cold": max(
                r["max_rate_err_rel"] for r in rows if r["T_C"] <= 25.0),
            "rows_floor_constrained_C": [r["T_C"] for r in rows if r["floor_constraint_applied"]],
            "rate_vs_measured_Sn3.9Ag0.6Cu": data_agreement(name),
            "card_sha": card_sha(card(name, win)[0])}
    return out


def main():
    if "--record" in sys.argv:
        RECORD.parent.mkdir(parents=True, exist_ok=True)
        RECORD.write_text(json.dumps(law_record(), indent=1, default=float) + "\n")
        print("wrote", RECORD.relative_to(R))
    if "--card" in sys.argv:
        print(card(sys.argv[sys.argv.index("--card") + 1])[0])


if __name__ == "__main__":
    main()
