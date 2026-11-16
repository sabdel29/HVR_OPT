"""Task 4 -- constitutive sensitivity: an alternative, widely used SAC calibration.

ALTERNATIVE LAW (published calibration)
  Garofalo / hyperbolic-sine steady-state creep of Schubert et al., ECTC 2003
  (doi:10.1109/ECTC.2003.1216343):
        eps_dot = C1 [sinh(alpha sigma)]^n exp(-C4 / T),   T in K, sigma = von Mises (MPa)
        C1 = 277984 1/s, alpha = 0.02447 1/MPa, n = 6.41, C4 = Q/R = 6500 K (Q = 54.0 kJ/mol)
  The constants are reprinted in open-access form in Sci. Rep. 15 (2025), doi:10.1038/
  s41598-025-06902-0, Table 2 (as the SAC305 set, C4 = 6500 K), and in Materials 16 (2023)
  4291, doi:10.3390/ma16124291, Table 4 (C4 = 6489.7 K; 0.16 % lower Q, +2.8 % rate at 100 C).

HOW IT ENTERS CALCULIX
  CalculiX 2.23 integrates eps_dot = A (sigma_vm - sigma_y)^n (an overstress law; see
  results/phase0l/CALCULIX_CREEP_IMPLEMENTATION_AUDIT.md) and has no sinh law without a
  recompiled user subroutine. The Garofalo law is a law in sigma_vm, so it is written with a
  ZERO yield surface (an explicit flat *PLASTIC at 1e-6 MPa, the audit's rule) and a
  temperature-dependent Norton card A(T), n(T), least-squares fitted in ln-ln at each
  temperature to the Garofalo rate over the stress window the joints experience there.
  Elasticity and expansion are the production values (solder_model.E_of_T, NU, CTE_SAC305).
  Rows every 2.5 C from -40 to 150 C on *ELASTIC, *PLASTIC and *CREEP alike (the solver's
  linear-in-A interpolation between rows is checked and reported).

  Two solver limits shape the numerics, neither the physics:
  * incplas.f replaces any Norton prefactor below 1e-20 by 1e-20. A steep fit at 25 C can
    need A ~ 1e-27..1e-35 (MPa units). The primary cards stay in MPa units, as production
    does, with such rows CONSTRAINED to A = 1.05e-20 (n the constrained least-squares
    optimum, flagged per row, error reported). The converged window is also fitted without
    the constraint and solved in consistent kN-mm-s units (stress in GPa, A x 1000^n;
    tcpmt_solder_common.card_to_gpa). That unit change is not numerically neutral in
    CalculiX (a force threshold in the convergence check is absolute): on the PRODUCTION
    card it moves the response by -2.9..+0.4 %, which is recorded with the check.
  * the step load meets a creep rate ~1e5 x the production card's at the elastic spike; the
    first increment of each 3 s load step must converge without a cutback below CalculiX's
    floor (1e-6 x step period). The fitted cards start each load step at 1e-9 s (1e-6 s
    fails, 1e-8 s runs); 1e-8 s is run as the time-step check (a first increment below the
    declared 1e-9 s minimum is rejected at input). CalculiX prints a non-fatal
    '*ERROR in nonlingeo' notice for a first increment below the floor and proceeds.

THE STRESS WINDOW
  Step loading means creep happens at exactly two temperatures, T_joint (hot dwell) and
  25 C (cold dwell); each phase gets its own window, the union over the six tier joints of a
  5-95 % range of the core von Mises stress (tcpmt_solder_common.stress_stats).
  * Strain-weighted (d(PEEQ) x volume): where the inelastic strain is deposited. It is
    dominated by the near-instant relaxation of the elastic spike of the step load (up to
    300 MPa), so it spans more than a decade; read from the production solves it gives the
    'strain_weighted_production_window' variant. Re-read from those Garofalo solves it
    widens to 15-290 MPa: the refitted card (n ~ 12, rate error ~x15) cannot be integrated
    (tier-A solves stop on the second increment even from a 1e-9 s start) and that scheme
    stops there (strain_it1_attempt).
  * Time-weighted (dt x volume), PRIMARY: the stresses the joint spends the cycle at, i.e.
    where the rate law decides how much of the imposed strain is left unrelaxed. Iteration 0
    reads it from the production solves; it is then re-read from the alternative-law solves
    and the card refitted until self-consistent (endpoints within 10 %, responses within 1 %,
    at most 8 iterations).
  The converged window is also split at its geometric midpoint and the card refitted over
  each half ("low" and "high" brackets): the spread of the response across the brackets and
  the strain-weighted variant is the mapping uncertainty.

A secondary variant, M1 (the production calibration with the yield threshold removed, the
Phase-0L "NORTON-ZY" form), isolates the overstress formulation itself.

    python tcpmt_solder_constitutive.py --run | --summarize
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

STUDY = "constitutive"
SM = C.SM

SCHUBERT = {"C1_per_s": 277984.0, "alpha_per_MPa": 0.02447, "n": 6.41, "C4_K": 6500.0,
            "Q_J_per_mol": 6500.0 * SM.R_GAS,
            "form": "eps_dot = C1 [sinh(alpha sigma_vm)]^n exp(-C4/T)",
            "alloy": "SnAgCu (near-eutectic SAC); applied to SAC305 in the citing literature",
            "source": "Schubert, Dudek, Auerswald, Gollhardt, Michel, Reichl, 'Fatigue life "
                      "models for SnAgCu and SnPb solder joints evaluated by experiments and "
                      "simulation', Proc. 53rd ECTC, 2003, pp. 603-610, "
                      "doi:10.1109/ECTC.2003.1216343 (bib key Schubert2003ECTC)",
            "open_access_reprints": [
                "Sci. Rep. 15 (2025), doi:10.1038/s41598-025-06902-0, Table 2 (SAC305: "
                "A = 2.78e5 1/s, alpha = 0.02447 1/MPa, n = 6.41, Q/R = 6500)",
                "Materials 16 (2023) 4291, doi:10.3390/ma16124291, Table 4 (C1 = 277,984 "
                "1/s, C2 = 0.02447 1/MPa, C3 = 6.41, C4 = 6489.7 K), citing Schubert 2003"]}
T_GRID = [round(-40.0 + 2.5 * k, 2) for k in range(int((150.0 + 40.0) / 2.5) + 1)]
SIGMA_Y_ZERO = 1.0e-6
WINDOW_Q = ("q05", "q95")
MAX_IT, TOL_WIN, TOL_RESP = 8, 0.10, 0.01
INC0_ALT, INC0_ALT_CHECK = 1.0e-9, 1.0e-8
#: rows at and above this temperature carry the hot-dwell window; it lies below the coolest
#: tier joint (78.67 C), so every T_joint sits between two pure hot-window rows
T_HOT_ASSIGN = 75.0


def garofalo(s, T_c, p=SCHUBERT):
    s = np.asarray(s, dtype=float)
    return p["C1_per_s"] * np.sinh(p["alpha_per_MPa"] * s) ** p["n"] * \
        np.exp(-p["C4_K"] / (T_c + 273.15))


#: incplas.f:141-144 (CalculiX 2.23): xxa = A t^m; if (xxa < 1e-20) xxa = 1e-20. In MPa
#: units a fit that needs a smaller A is constrained to this bound (5 % margin) and n is the
#: constrained least-squares optimum; the flag travels with the row.
A_FLOOR = 1.05e-20


def fit(T_c, lo, hi, npt=400, constrained=True):
    """Least-squares Norton fit of the Garofalo rate in ln-ln over [lo, hi] MPa; with
    constrained=True subject to the solver's prefactor floor (MPa units)."""
    s = np.logspace(math.log10(lo), math.log10(hi), npt)
    y = np.log(garofalo(s, T_c))
    n, lnA = np.polyfit(np.log(s), y, 1)
    below = bool(lnA < math.log(A_FLOOR))
    if constrained and below:
        lnA = math.log(A_FLOOR)
        x = np.log(s)
        n = float(np.sum(x * (y - lnA)) / np.sum(x * x))
    err = np.exp(lnA + n * np.log(s) - y) - 1.0
    k = int(np.argmax(np.abs(err)))
    neff = SCHUBERT["n"] * SCHUBERT["alpha_per_MPa"] * s * \
        (1.0 / np.tanh(SCHUBERT["alpha_per_MPa"] * s))
    return {"T_C": T_c, "window_MPa": [lo, hi], "A_MPa_units": math.exp(lnA), "n": float(n),
            "unconstrained_fit_below_floor": below,
            "floor_constraint_applied": bool(constrained and below),
            "max_rate_err_rel": float(abs(err[k])), "max_rate_err_at_MPa": float(s[k]),
            "rms_rate_err_rel": float(np.sqrt(np.mean(err ** 2))),
            "max_equiv_stress_err_rel": float(np.max(np.abs(np.exp(
                (lnA + n * np.log(s) - y) / neff) - 1.0))),
            "garofalo_local_exponent_range": [float(neff[0]), float(neff[-1])]}


def t_hot_lo():
    tj = min(C.critical(case)["T_C"] for _, _, case in C.tier_cases())
    assert tj >= T_HOT_ASSIGN + 2.5, tj
    return T_HOT_ASSIGN


def window_at(T_c, win):
    """Hot window at and above T_HOT_ASSIGN, cold window at and below 25 C, geometric blend
    in between (temperatures the step loading never visits)."""
    th = t_hot_lo()
    if T_c <= C.T_COLD:
        return tuple(win["cold"])
    if T_c >= th:
        return tuple(win["hot"])
    w = (T_c - C.T_COLD) / (th - C.T_COLD)
    return tuple(math.exp((1 - w) * math.log(c) + w * math.log(h))
                 for c, h in zip(win["cold"], win["hot"]))


def card(win, constrained=True):
    """The CalculiX block (MPa units) and its per-row fits."""
    rows = [fit(T, *window_at(T, win), constrained=constrained) for T in T_GRID]
    L = ["*MATERIAL, NAME=SAC305", "*ELASTIC"]
    L += [f"{SM.E_of_T(T):.6g}, {SM.NU}, {T:.1f}" for T in T_GRID]
    L += ["*PLASTIC"] + [f"{SIGMA_Y_ZERO:g}, 0.0, {T:.1f}" for T in T_GRID]
    L += ["*CREEP, LAW=NORTON"] + [f"{r['A_MPa_units']:.10e}, {r['n']:.10g}, 0.0, "
                                    f"{r['T_C']:.1f}" for r in rows]
    L += ["*EXPANSION, ZERO=25.", f"{SM.CTE_SAC305:.4g}"]
    return "\n".join(L) + "\n", rows


def card_m1():
    """M1: the production card with the yield threshold removed (flat 1e-6 MPa)."""
    s = C.DEC.material("EPC")
    head, rest = s.split("*PLASTIC\n")
    plast, tail = rest.split("*CREEP")
    temps = sorted({float(l.split(",")[2]) for l in plast.strip().splitlines()})
    flat = "".join(f"{SIGMA_Y_ZERO:g}, 0.0, {T:.1f}\n" for T in temps)
    return head + "*PLASTIC\n" + flat + "*CREEP" + tail


def interp_error(rows, temps, win):
    """Rate the solver evaluates (A and n linear between rows, creeps.f/materialdata_me.f)
    against the intended fit at the joint's own temperature, over its window."""
    Ts = np.array([r["T_C"] for r in rows])
    As = np.array([r["A_MPa_units"] for r in rows])
    ns = np.array([r["n"] for r in rows])
    worst = 0.0
    for T in temps:
        f = fit(T, *window_at(T, win))
        a, n = float(np.interp(T, Ts, As)), float(np.interp(T, Ts, ns))
        s = np.logspace(math.log10(f["window_MPa"][0]), math.log10(f["window_MPa"][1]), 50)
        worst = max(worst, float(np.max(np.abs(a * s ** n / (f["A_MPa_units"] * s ** f["n"])
                                               - 1))))
    return worst


def sig(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def tasks_for(label, card_text, card_name, units="MPa", inc0=None, stress=True,
              cases=None):
    t = []
    for tier, arch, case in C.tier_cases():
        if cases and f"{tier}_{arch}" not in cases:
            continue
        c = C.critical(case)
        t.append(dict(study=STUDY, tag=f"{tier}_{arch}_{label}", du_um=c["du_um"],
                      T_C=c["T_C"], card=card_text, card_name=card_name, stress=stress,
                      units=units, inc0=inc0,
                      sig=(None if (card_text is None and units == "MPa" and inc0 is None)
                           else sig(card_text, units, inc0)),
                      meta={"tier": tier, "arch": arch, "case": case, "law": label}))
    return t


def windows_from(recs, weighting="strain"):
    """Union over the joints of the per-phase 5-95 % stress window. weighting='strain':
    where the cycle's inelastic strain is deposited; 'time': where the cycle is spent."""
    key = "quantiles_MPa" if weighting == "strain" else "time_quantiles_MPa"
    w = {"hot": [None, None], "cold": [None, None]}
    for p in ("hot", "cold"):
        qs = [r["stress"][p][key] for r in recs.values()
              if r.get("stress") and key in r["stress"][p]]
        if qs:
            w[p] = [min(q[WINDOW_Q[0]] for q in qs), max(q[WINDOW_Q[1]] for q in qs)]
    return w


def halves(win):
    lo, hi = {}, {}
    for p, (a, b) in win.items():
        m = math.sqrt(a * b)
        lo[p], hi[p] = [a, m], [m, b]
    return lo, hi


def responses(recs, label):
    return {f"{t}_{a}": (recs.get(f"{t}_{a}_{label}") or {}).get("d_peeq_per_cycle")
            for t, a, _ in C.tier_cases()}


def plan(execute):
    """The whole study in dependency order. execute=False replays it from the records
    (same cards, same signatures) without solving."""
    def run(tasks):
        if execute:
            C.run_tasks(tasks)
        recs = C.load_records(STUDY)
        return {t["tag"]: recs[t["tag"]] for t in tasks
                if t["tag"] in recs and recs[t["tag"]].get("sig") == t["sig"]}

    def restat(recs):
        if execute:
            for tag in recs:
                C.restat(STUDY, tag)
        allr = C.load_records(STUDY)
        return {t: allr[t] for t in recs}

    def fits_for(win):
        return {f"{t}_{a}": fit(C.critical(c)["T_C"], *window_at(C.critical(c)["T_C"], win))
                for t, a, c in C.tier_cases()}

    log = {}
    log["production"] = restat(run(tasks_for("production", None, None)))
    prod_text = C.DEC.material(C.LR.MATKIND)
    log["gpa_check"] = run(tasks_for("production_GPa", prod_text, "production card in GPa "
                                     "units (unit-system validation)", units="GPa",
                                     cases=("A_Z1", "A_Z3", "B_Z1")))
    # variant: Garofalo fitted over the PRODUCTION strain-weighted window (iteration 0 of the
    # strain-weighted scheme) and the record of why that scheme cannot continue
    sw0 = windows_from(log["production"], "strain")
    s0text, s0rows = card(sw0)
    log["strain_it0"] = {"window_fit_MPa": sw0, "fits_at_joint_T": fits_for(sw0),
                         "fit_25C": fit(C.T_COLD, *window_at(C.T_COLD, sw0)),
                         "records": restat(run(tasks_for(
                             "schubert_it0", s0text, "Schubert 2003 Garofalo -> Norton, "
                             "iteration 0", inc0=INC0_ALT)))}
    sw1 = windows_from(log["strain_it0"]["records"], "strain")
    s1text, _ = card(sw1)
    s1 = {t["tag"]: C.load_records(STUDY).get(t["tag"]) for t in
          tasks_for("schubert_it1", s1text, "", inc0=INC0_ALT)}
    log["strain_it1_attempt"] = {
        "window_fit_MPa": sw1, "fits_at_joint_T": fits_for(sw1),
        "fit_25C": fit(C.T_COLD, *window_at(C.T_COLD, sw1)),
        "errors": {k: (v or {}).get("error") for k, v in s1.items()},
        "outcome": "not continued: the tier-A solves stop on the second increment of the "
                   "first load step even from a 1e-9 s start (creep rates ~1e7-1e9 1/s at "
                   "the 200-300 MPa elastic spike), and the fit misses the Garofalo rate by "
                   "a factor of ~15 over a window this wide"}
    # PRIMARY: the time-weighted window (the stresses the joints spend the cycle at),
    # iteration 0 from the production solves, iterated to self-consistency
    win = windows_from(log["production"], "time")
    its, prev_v = [], None
    for k in range(MAX_IT):
        text, rows = card(win)
        lab = f"schubert_t{k}"
        recs = restat(run(tasks_for(lab, text, f"Schubert 2003 Garofalo -> Norton, "
                                    f"time-weighted window, iteration {k}", inc0=INC0_ALT)))
        new = windows_from(recs, "time")
        v = responses(recs, lab)
        ok = None not in v.values() and None not in sum(new.values(), [])
        dw = max(abs(math.log(new[p][i] / win[p][i])) for p in ("hot", "cold")
                 for i in (0, 1)) if ok else None
        dv = max(abs(v[x] / prev_v[x] - 1) for x in v) if (ok and prev_v) else None
        its.append({"iteration": k, "label": lab, "window_fit_MPa": win,
                    "window_observed_MPa": new, "window_change_max_log": dw,
                    "response_change_max_rel": dv, "card_sha": sig(text),
                    "fits_at_joint_T": fits_for(win),
                    "fit_25C": fit(C.T_COLD, *window_at(C.T_COLD, win)),
                    "interp_error_max_rel": interp_error(
                        rows, [C.critical(c)["T_C"] for _, _, c in C.tier_cases()]
                        + [C.T_COLD], win),
                    "responses": v, "records": recs})
        if not ok:
            break
        if dw < math.log(1 + TOL_WIN) and dv is not None and dv < TOL_RESP:
            break
        win, prev_v = new, v
    log["iterations"] = its
    final = its[-1]
    ftext, frows = card(final["window_fit_MPa"])
    log["time_check"] = run(tasks_for("sch_tf_dt1e-8", ftext,
                                      "final card, first increment 1e-8 s",
                                      inc0=INC0_ALT_CHECK))
    visited = [C.T_COLD] + [C.critical(c)["T_C"] for _, _, c in C.tier_cases()]
    floor_rows = [r["T_C"] for r in frows if r["floor_constraint_applied"]
                  and any(abs(r["T_C"] - T) < 2.5 for T in visited)]
    log["floor_rows_near_visited_T"] = floor_rows
    if floor_rows:                   # only then is an unconstrained (GPa-unit) solve needed
        utext, _ = card(final["window_fit_MPa"], constrained=False)
        log["unconstrained_gpa"] = {
            "fit_25C": fit(C.T_COLD, *window_at(C.T_COLD, final["window_fit_MPa"]),
                           constrained=False),
            "records": run(tasks_for("schubert_t_final_GPa_unconstrained", utext,
                                     "final window, unconstrained fit, GPa units",
                                     units="GPa", inc0=INC0_ALT))}
    lo, hi = halves(final["window_fit_MPa"])
    log["brackets"] = {}
    for name, w in (("low", lo), ("high", hi)):
        t_, _ = card(w)
        log["brackets"][name] = {"window_fit_MPa": w, "fits_at_joint_T": fits_for(w),
                                 "fit_25C": fit(C.T_COLD, *window_at(C.T_COLD, w)),
                                 "records": run(tasks_for(f"schubert_t_{name}", t_,
                                                          f"Schubert, {name}-half of the "
                                                          "time-weighted window",
                                                          inc0=INC0_ALT))}
    m1 = card_m1()
    rec = run(tasks_for("M1", m1, "M1: production calibration, yield threshold removed"))
    if None in responses(rec, "M1").values():            # fall back to the small increment
        rec = run(tasks_for("M1_dt1e-9", m1, "M1, first increment 1e-9 s", inc0=INC0_ALT))
        log["M1_label"] = "M1_dt1e-9"
    else:
        log["M1_label"] = "M1"
    log["M1"] = rec
    return log


def ranking(vals):
    """{arch: v} -> order string 'Z1 < Z3 < Z2'."""
    if None in vals.values():
        return None
    return " < ".join(sorted(vals, key=vals.get))


def tier_rank(v):
    return {t: ranking({a: v.get(f"{t}_{a}") for a in ("Z1", "Z2", "Z3")})
            for t in ("A", "B")}


def _iteration_view(it):
    recs = it.pop("records")
    it["per_cycle"] = {k: (recs.get(f"{k}_{it['label']}") or {}).get("per_cycle")
                       for k in it["responses"]}
    it["stress"] = {k: (recs.get(f"{k}_{it['label']}") or {}).get("stress")
                    for k in it["responses"]}
    it["errors"] = {k: (recs.get(f"{k}_{it['label']}") or {}).get("error")
                    for k in it["responses"]}
    it["rankings"] = tier_rank(it["responses"])
    return it


def summarize():
    log = plan(execute=False)
    out = {"what": "constitutive sensitivity (task 4)", "alternative_law": SCHUBERT,
           "mapping": {"solver_form": "eps_dot = A(T) (sigma_vm - sigma_y)^n(T), sigma_y = "
                                      f"{SIGMA_Y_ZERO:g} MPa flat (zero yield, audit rule)",
                       "rows_C": [T_GRID[0], T_GRID[-1], 2.5],
                       "fit": "least squares in ln(rate) vs ln(sigma), 400 log-spaced points "
                              "over the window",
                       "window_primary": "time-weighted: 5-95 % quantiles of the von Mises "
                                         "stress weighted by dt x volume (the stresses the "
                                         "joint spends the cycle at), per phase (hot dwell at "
                                         "T_joint, cold dwell at 25 C), union over the six "
                                         "tier joints; iteration 0 from the production solves,"
                                         " then re-read from the alternative-law solves",
                       "window_variant": "strain-weighted (d(PEEQ) x volume) window of the "
                                         "production solves (iteration 0 of a strain-weighted "
                                         "scheme that cannot continue, see strain_it1_attempt)",
                       "temperature_assignment": f"cold window at T <= 25 C, hot window at T "
                                                 f">= {T_HOT_ASSIGN:.0f} C (below the coolest "
                                                 "tier joint, 78.7 C), geometric blend "
                                                 "between (never visited)",
                       "iteration": f"until endpoints change < {100 * TOL_WIN:.0f} % and "
                                    f"responses < {100 * TOL_RESP:.0f} % (max {MAX_IT})",
                       "brackets": "the converged window split at its geometric midpoint; "
                                   "the card refitted over each half",
                       "units": "MPa (as production); a row whose least-squares A falls below "
                                "the incplas.f floor of 1e-20 is constrained to A = 1.05e-20 "
                                "and flagged",
                       "first_increment_s": INC0_ALT, "time_check_first_increment_s":
                           INC0_ALT_CHECK,
                       "elastic_and_expansion": "production (solder_model.E_of_T, NU, "
                                                "CTE_SAC305)"},
           "settings": {"level": "L0", "split_steps": True, "n_cycles": 4,
                        "production_first_increment_s": C.INC0}}
    prod = log["production"]
    out["production_card"] = {
        f"{t}_{a}": {"d_eps": (prod.get(f"{t}_{a}_production") or {}).get("d_peeq_per_cycle"),
                     "paper_L0_x1e3": C.PAPER_L0[t][a],
                     "per_cycle": (prod.get(f"{t}_{a}_production") or {}).get("per_cycle"),
                     "stress": (prod.get(f"{t}_{a}_production") or {}).get("stress")}
        for t, a, _ in C.tier_cases()}
    out["production_window_strain_weighted_MPa"] = windows_from(prod, "strain")
    out["production_window_time_weighted_MPa"] = windows_from(prod, "time")
    out["production_card_calibration_window_MPa"] = list(SM.DATA_STRESS_RANGE_MPA)
    g = log["gpa_check"]
    out["unit_system_check"] = {
        k: {"MPa": (prod.get(f"{k}_production") or {}).get("d_peeq_per_cycle"),
            "GPa": (g.get(f"{k}_production_GPa") or {}).get("d_peeq_per_cycle")}
        for k in ("A_Z1", "A_Z3", "B_Z1")}
    allr = C.load_records(STUDY)
    for k, v in out["unit_system_check"].items():
        for u in ("10MPa", "100MPa"):
            v[u] = (allr.get(f"{k}_production_{u}") or {}).get("d_peeq_per_cycle")
        for u in ("10MPa", "100MPa", "GPa"):
            v[f"{u}_rel_diff"] = ((v[u] - v["MPa"]) / v["MPa"]) if (v.get(u) and v["MPa"]) \
                else None
    s0 = log["strain_it0"]
    v0 = responses(s0["records"], "schubert_it0")
    out["strain_weighted_production_window"] = {
        "window_fit_MPa": s0["window_fit_MPa"], "fits_at_joint_T": s0["fits_at_joint_T"],
        "fit_25C": s0["fit_25C"], "d_eps": v0, "rankings": tier_rank(v0),
        "per_cycle": {k: (s0["records"].get(f"{k}_schubert_it0") or {}).get("per_cycle")
                      for k in v0},
        "stress": {k: (s0["records"].get(f"{k}_schubert_it0") or {}).get("stress")
                   for k in v0},
        "window_observed_MPa": windows_from(s0["records"], "strain")}
    out["strain_it1_attempt"] = log["strain_it1_attempt"]
    its = [_iteration_view(it) for it in log["iterations"]]
    out["iterations"] = its
    last = its[-1] if its else None
    out["converged"] = bool(last) and last["window_change_max_log"] is not None and \
        last["window_change_max_log"] < math.log(1 + TOL_WIN) and \
        (last["response_change_max_rel"] if last["response_change_max_rel"] is not None
         else 1.0) < TOL_RESP
    final_v = last["responses"] if last else {}
    out["final"] = {"label": last["label"] if last else None, "d_eps": final_v,
                    "window_fit_MPa": last["window_fit_MPa"] if last else None,
                    "rankings": tier_rank(final_v)}
    tc = responses(log["time_check"], "sch_tf_dt1e-8")
    out["time_check"] = {k: {"dt1e-9": final_v.get(k), "dt1e-8": tc.get(k),
                             "rel_diff": ((tc[k] - final_v[k]) / final_v[k])
                             if (tc.get(k) and final_v.get(k)) else None} for k in tc}
    out["floor_rows_near_visited_T"] = log["floor_rows_near_visited_T"]
    ug = None
    if log.get("unconstrained_gpa"):
        ug = responses(log["unconstrained_gpa"]["records"],
                       "schubert_t_final_GPa_unconstrained")
        out["unconstrained_fit_in_GPa_units"] = {
            "fit_25C": log["unconstrained_gpa"]["fit_25C"], "d_eps": ug,
            "rel_diff_vs_final": {k: ((ug[k] - final_v[k]) / final_v[k])
                                  if (ug.get(k) and final_v.get(k)) else None for k in ug},
            "rankings": tier_rank(ug)}
    br = {}
    for name, b in log["brackets"].items():
        v = responses(b["records"], f"schubert_t_{name}")
        br[name] = {"window_fit_MPa": b["window_fit_MPa"], "responses": v,
                    "fits_at_joint_T": b["fits_at_joint_T"], "fit_25C": b["fit_25C"],
                    "rankings": tier_rank(v)}
    out["brackets"] = br
    if br and final_v and all(br[n]["responses"].get(k) for n in br for k in final_v):
        out["mapping_spread_rel"] = {
            k: (max(final_v[k], br["low"]["responses"][k], br["high"]["responses"][k]) -
                min(final_v[k], br["low"]["responses"][k], br["high"]["responses"][k]))
            / final_v[k] for k in final_v if final_v[k]}
    m1 = responses(log["M1"], log["M1_label"])
    out["M1_no_yield_production_calibration"] = {
        "what": "production A(T), n(T) rows with the yield threshold removed (Phase-0L M1)",
        "label": log["M1_label"], "d_eps": m1, "rankings": tier_rank(m1),
        "per_cycle": {k: (log["M1"].get(f"{k}_{log['M1_label']}") or {}).get("per_cycle")
                      for k in m1}}
    pv = {k: v["d_eps"] for k, v in out["production_card"].items()}
    pr = tier_rank(pv)
    out["rankings_production"] = pr
    variants = {"schubert_time_final": final_v,
                "schubert_time_low_half": br.get("low", {}).get("responses"),
                "schubert_time_high_half": br.get("high", {}).get("responses"),
                "schubert_time_dt1e-8": tc,
                "schubert_strain_production_window": v0, "M1_no_yield": m1}
    if ug:
        variants["schubert_unconstrained_GPa"] = ug
    pf = {f"{t}_{a}": (allr.get(f"{t}_{a}_production_finegrid") or {}).get("d_peeq_per_cycle")
          for t, a, _ in C.tier_cases()}
    out["production_card_on_2p5C_grid"] = {
        "what": "the production card rebuilt by solder_model.inp_material on 2.5 C rows, so "
                "the solver's linear-in-A interpolation follows the intended Arrhenius "
                "construction (tcpmt_solder_units_check.py)", "d_eps": pf,
        "rel_diff_vs_production": {
            k: ((pf[k] - out["production_card"][k]["d_eps"]) / out["production_card"][k]["d_eps"])
            if (pf.get(k) and out["production_card"][k]["d_eps"]) else None for k in pf}}
    variants["production_card_on_2p5C_grid"] = pf
    variants.update({it["label"]: it["responses"] for it in its})
    variants = {k: v for k, v in variants.items() if v and None not in v.values()}
    out["rankings_by_variant"] = {k: tier_rank(v) for k, v in variants.items()}
    out["rankings_hold"] = {k: {t: r[t] == pr[t] for t in ("A", "B")}
                            for k, r in out["rankings_by_variant"].items()}
    out["rankings_hold_all_variants"] = all(x for r in out["rankings_hold"].values()
                                            for x in r.values())
    out["ratio_to_production"] = {k: {kk: (v[kk] / pv[kk]) if (v.get(kk) and pv.get(kk))
                                      else None for kk in pv} for k, v in variants.items()}
    gaps = {}
    for k, v in dict(variants, production=pv).items():
        for t in ("A", "B"):
            vals = sorted((v[f"{t}_{a}"], a) for a in ("Z1", "Z2", "Z3"))
            gaps.setdefault(k, {})[t] = {f"{lo_[1]}<{hi_[1]}": (hi_[0] - lo_[0]) / hi_[0]
                                         for lo_, hi_ in zip(vals, vals[1:])}
    out["adjacent_gaps_rel"] = gaps
    return out


def main():
    if "--run" in sys.argv:
        plan(execute=True)
    if "--summarize" in sys.argv:
        from tcpmt_solder_collect import merge
        s = summarize()
        merge("constitutive", s)
        print(json.dumps({k: s[k] for k in ("production_window_time_weighted_MPa", "rankings_production",
                                             "rankings_by_variant", "converged",
                                             "unit_system_check")}, indent=1, default=str))
        for it in s["iterations"]:
            print(it["iteration"], it["window_fit_MPa"], it["window_observed_MPa"],
                  it["responses"], it["rankings"])


if __name__ == "__main__":
    main()
