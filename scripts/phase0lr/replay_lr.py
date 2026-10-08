#!/usr/bin/env python3
"""Phase-0L-R replay: the Phase-0L harness plus the Anand family.

Phase-0L's scripts/phase0l/replay.py is imported, not edited, so every Phase-0L artifact stays
reproducible. Only the material card is extended.

Models:
  M1            Norton, Sn3.9Ag0.6Cu creep points, yield removed        (Phase-0L, unchanged)
  M2_ANAND      Anand (Yamin/Motalab SAC305) reduced to a Norton card over a stated stress
                window, yield removed. The window is ITERATED: an initial guess is run, the
                damage-weighted stress of that run is measured, and the card is refitted around
                it, because a power-law reduction of a sinh-type law is only good over about a
                3x stress window.
"""
from __future__ import annotations
import csv, math, re, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for d in ("phase0i", "phase0ir", "phase0jr", "phase0l", "phase0lr"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
import replay as RP                                                         # noqa: E402
from candidate_families import norton_from_anand                            # noqa: E402
from graded_joint import build_joint_graded                                 # noqa: E402
from joint import run as run_ccx, write_inp                                 # noqa: E402
from cycle_audit import cycle_quantities, per_element_series                # noqa: E402
from decompose import parse_tensors, parse_temperature                      # noqa: E402

OUT = R / "results" / "phase0lr"
WD = OUT / "wd"
WD.mkdir(parents=True, exist_ok=True)
FINE = RP.FINE
ANAND_WINDOW = {"lo": 20.0, "hi": 70.0}      # mutable: set by the window iteration


def material(model: str) -> str:
    if not model.startswith("M2_ANAND"):
        return RP.material(model)
    L = ["*MATERIAL, NAME=SAC305", "*ELASTIC"]
    L += [f"{sm.E_of_T(T):.6g}, {sm.NU}, {T:.1f}" for T in FINE]
    L.append("*PLASTIC")
    for T in FINE:                       # explicit flat near-zero yield (DEFECT #43 rule)
        L += [f"1.E-6, 0.0, {T:.1f}", f"1.E-6, 0.02, {T:.1f}"]
    L.append("*CREEP, LAW=NORTON")
    for T in FINE:
        f = norton_from_anand(T, ANAND_WINDOW["lo"], ANAND_WINDOW["hi"])
        L.append(f"{f['A']:.6e}, {f['n']:.6g}, 0.0, {T:.1f}")
    L += ["*EXPANSION, ZERO=25.", f"{sm.CTE_SAC305:.4g}"]
    return "\n".join(L) + "\n"


def run_case(model, arch, profile, tight=True, tag_extra=""):
    a = RP.ARCH[arch]
    if profile is None:
        tmin, tmax, du = RP.T_OFF, a["t_hot"], a["du"]
    else:
        tmin, tmax = profile
        du = a["du"] * (tmax - tmin) / (a["t_hot"] - RP.T_OFF)
    prof = "BASE" if profile is None else f"{tmin:g}_{tmax:g}"
    # the Anand card depends on its reduction window, so the window MUST be in the tag --
    # otherwise two different cards write to the same .dat and the later one silently wins
    win = (f"_w{ANAND_WINDOW['lo']:g}_{ANAND_WINDOW['hi']:g}"
           if model.startswith("M2_ANAND") else "")
    tag = f"{model}{tag_extra}{win}_{arch}_{prof}"
    m = build_joint_graded(6, 6)
    cyc, ends, t = [], [], 0.0
    for k in range(RP.N_CYC):
        cyc.append((f"c{k}on", tmax, du / 1000.0, RP.DWELL)); t += RP.DWELL
        cyc.append((f"c{k}off", tmin, 0.0, RP.DWELL)); t += RP.DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material(model), cyc, t_ref_c=tmin, cetol=5e-2, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    start = (RP.TIGHT_START if tight else RP.LOOSE_START) % RP.DWELL
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % RP.DWELL, start, s, flags=re.M)
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
    base = {"model": model, "arch": arch, "profile": prof, "wall_s": wall,
            "solver_control": "TIGHT" if tight else "DEFAULT",
            "anand_window_lo": ANAND_WINDOW["lo"], "anand_window_hi": ANAND_WINDOW["hi"]}
    if not (d.is_file() and d.stat().st_size > 5000):
        return {**base, "status": "SOLVER FAILED"}
    data = parse_tensors(d, set(ids))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, parse_temperature(d))
    te = ends[RP.STAB - 1]
    q = cycle_quantities(ser, vols, te - 2 * RP.DWELL, te)
    qp = cycle_quantities(ser, vols, te - 4 * RP.DWELL, te - 2 * RP.DWELL)
    if not q:
        return {**base, "status": "NO CYCLE DATA"}
    q.update(base); q["status"] = "OK"; q["du_um"] = du
    q["T_min_C"] = tmin; q["T_max_C"] = tmax
    q["stab_pct"] = (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                     / qp["d_peeq_per_cycle"]) if qp and qp["d_peeq_per_cycle"] else float("nan")
    return q


if __name__ == "__main__":
    mdl, arch, prof = sys.argv[1], sys.argv[2], sys.argv[3]
    if len(sys.argv) > 5:
        ANAND_WINDOW["lo"], ANAND_WINDOW["hi"] = float(sys.argv[4]), float(sys.argv[5])
    r = run_case(mdl, arch, RP.PROFILES[prof])
    print({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
