#!/usr/bin/env python3
"""Phase-0L Part XI -- replay Z1/Z2/Z4 and the two candidate experiment profiles under every
admissible constitutive model.

Models (all Norton cards, the only form CalculiX can integrate -- see Part IX):

  M0_COARSE  the incumbent, verbatim: A,n from the sigma_applied fit, full Chaboche *PLASTIC
             card, *CREEP rows on the production grid -40..125 C.
  M0_FINE    identical law, but *CREEP/*PLASTIC rows on a grid that spans each profile.
             Isolates the card-grid defect from the constitutive defect.
  M1         yield surface removed (sigma_y = 1e-6 MPa), so the solver's driving variable
             equals the variable the card was fitted in.  Reproduces all 19 source points.
  M1_NLO     M1 with n -> n - 2*SE(n), A re-anchored so the rate at 10 MPa is unchanged.
  M1_NHI     M1 with n -> n + 2*SE(n), likewise.

M1_NLO/M1_NHI span the exponent uncertainty of the source regression itself (+/-9.8% on n,
which is 0.09x to 11x on rate at 90 MPa).  The Garofalo and Anand candidates are NOT replayed:
Part X rejected both for this stress regime (Garofalo reaches 4e15 1/s at 120 MPa; Anand has
no solution above ~60-80 MPa).
"""
from __future__ import annotations
import csv, math, re, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0i", "phase0ir", "phase0jr", "phase0kr"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
from graded_joint import build_joint_graded                                 # noqa: E402
from joint import run as run_ccx, write_inp                                 # noqa: E402
from cycle_audit import cycle_quantities, per_element_series                # noqa: E402
from decompose import parse_temperature, parse_tensors                      # noqa: E402

OUT = R / "results" / "phase0l"
WD = OUT / "wd"
WD.mkdir(parents=True, exist_ok=True)
N_CYC, STAB, DWELL, T_OFF = 6, 5, 300.0, 25.0

ARCH = {"Z1": dict(du=2.7485664848789826, t_hot=82.8604875),
        "Z2": dict(du=2.0796010434696357, t_hot=81.8453000000000),
        "Z4": dict(du=2.9840047587428530, t_hot=81.1017812499999)}
PROFILES = {"OP_BASELINE": None, "EXP_45_125": (45.0, 125.0), "EXP_110_150": (110.0, 150.0)}

COARSE = [-40., 0., 25., 50., 75., 100., 125.]
FINE = [-40., -20., 0., 20., 40., 45., 55., 65., 75., 80., 90., 100., 110.,
        115., 125., 135., 145., 150.]


def se_n(T):
    """Standard error of the Norton exponent from the per-temperature regression."""
    pts = [(s, e) for (t, s, e) in sm.CREEP_DATA if t == T]
    x = np.log([p[0] for p in pts]); y = np.log([p[1] for p in pts])
    b, a = np.polyfit(x, y, 1)
    dof = len(pts) - 2
    s2 = float(((y - (a + b * x)) ** 2).sum() / dof)
    return math.sqrt(s2 / float(((x - x.mean()) ** 2).sum()))


SE = {T: se_n(T) for T in sm.DATA_TEMPS}


def se_at(T):
    return float(np.interp(T, sm.DATA_TEMPS, [SE[t] for t in sm.DATA_TEMPS]))


def material(model: str) -> str:
    grid = COARSE if model == "M0_COARSE" else FINE
    L = ["*MATERIAL, NAME=SAC305", "*ELASTIC"]
    L += [f"{sm.E_of_T(T):.6g}, {sm.NU}, {T:.1f}" for T in grid]
    L.append("*PLASTIC")
    if model.startswith("M0"):
        for T in grid:
            L.append(f"{sm.sigma0_of_T(T):.6g}, 0.0, {T:.1f}")
            L.append(f"{sm.sat_stress_of_T(T):.6g}, 0.02, {T:.1f}")
    else:
        # sigma_y = 1e-6 MPa: a flat, effectively zero yield surface.  An explicit card is
        # used rather than omitting *PLASTIC, because omitting it routes incplas.f through
        # the empty uhardening() stub and leaves fiso uninitialised (Part III section 10a).
        for T in grid:
            L.append(f"1.E-6, 0.0, {T:.1f}")
            L.append(f"1.E-6, 0.02, {T:.1f}")
    L.append("*CREEP, LAW=NORTON")
    for T in grid:
        f = sm.norton_at(T)
        A, n = f["A"], f["n"]
        if model in ("M1_NLO", "M1_NHI"):
            dn = 2.0 * se_at(T) * (-1.0 if model == "M1_NLO" else 1.0)
            A = A * sm.SIGMA_REF_MPA ** (-dn)       # keep the rate at 10 MPa fixed
            n = n + dn
        L.append(f"{A:.6e}, {n:.6g}, 0.0, {T:.1f}")
    L += ["*EXPANSION, ZERO=25.", f"{sm.CTE_SAC305:.4g}"]
    return "\n".join(L) + "\n"


# M1_NHI (n + 2 SE) is stiffer than the other cards and diverges on the FIRST increment with
# the default start: incplas returns pnewdt, the increment is cut once, and ccx stops.  The fix
# is solver control only -- a smaller starting increment and a lower floor.  It is applied to
# every model in the TIGHT re-run so that the settings cannot be confounded with the model.
TIGHT_START = "1e-8, %g, 1e-14, 10"
LOOSE_START = "1e-5, %g, 1e-12, 10"


def run_case(model, arch, profile, n_mid=6, tight=False):
    a = ARCH[arch]
    if profile is None:
        tmin, tmax, du = T_OFF, a["t_hot"], a["du"]
    else:
        tmin, tmax = profile
        du = a["du"] * (tmax - tmin) / (a["t_hot"] - T_OFF)
    prof_label = "BASE" if profile is None else f"{tmin:g}_{tmax:g}"
    tag = f"{model}_{arch}_{prof_label}" + ("_T" if tight else "")
    m = build_joint_graded(6, n_mid)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", tmax, du / 1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", tmin, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material(model), cyc, t_ref_c=tmin, cetol=5e-2, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    start = (TIGHT_START if tight else LOOSE_START) % DWELL
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % DWELL, start, s, flags=re.M)
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  "*EL PRINT, ELSET=ESYED\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E", "*NODE PRINT, NSET=NBOT\nNT")
    ids = m.sets["ESYED"]
    blk = ["*ELSET, ELSET=ESYED"] + [", ".join(map(str, ids[i:i + 8]))
                                     for i in range(0, len(ids), 8)]
    s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    t0 = time.time()
    run_ccx(p, threads=6)
    wall = time.time() - t0
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return {"model": model, "arch": arch, "profile": prof_label,
                "status": "SOLVER FAILED", "wall_s": wall,
                "solver_control": "TIGHT" if tight else "DEFAULT"}
    data = parse_tensors(d, set(ids))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, parse_temperature(d))
    te = ends[STAB - 1]
    q = cycle_quantities(ser, vols, te - 2 * DWELL, te)
    qp = cycle_quantities(ser, vols, te - 4 * DWELL, te - 2 * DWELL)
    if not q:
        return {"model": model, "arch": arch, "profile": prof_label,
                "status": "NO CYCLE DATA", "wall_s": wall,
                "solver_control": "TIGHT" if tight else "DEFAULT"}
    q.update({"model": model, "arch": arch, "profile": prof_label,
              "status": "OK", "wall_s": wall, "du_um": du, "T_min_C": tmin, "T_max_C": tmax,
              "solver_control": "TIGHT" if tight else "DEFAULT",
              "stab_pct": (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                           / qp["d_peeq_per_cycle"])
              if qp and qp["d_peeq_per_cycle"] else float("nan")})
    return q


if __name__ == "__main__":
    model = sys.argv[1]; arch = sys.argv[2]; prof = sys.argv[3]
    r = run_case(model, arch, PROFILES[prof])
    print({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
