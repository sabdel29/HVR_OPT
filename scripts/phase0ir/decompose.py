#!/usr/bin/env python3
"""Phase-0I-R Sec.3/5/6/7 -- strain decomposition, creep-inclusion test and energy diagnostic
on the ACTUAL Phase-0I joint submodel.

The single-element probes established that CalculiX's PEEQ equals the equivalent inelastic
strain exactly, creep included. That is necessary but not sufficient: the Phase-0I joint is
multiaxial, temperature-varying and cyclic, so the same identity is re-established there
before any Phase-0I number is allowed to stand.

Three material variants under IDENTICAL loading:
    EP   elastic + plastic, no creep      (*STATIC)   -- the Phase-0H class
    EC   elastic + creep, no plasticity   (*VISCO)
    EPC  elastic + plastic + creep        (*VISCO)    -- what Phase 0I actually ran
"""
from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from joint import build_joint, run, write_inp, BALL_H_UM              # noqa: E402
from solder_model import (CTE_SAC305, NU, E_of_T, inp_material,        # noqa: E402
                          norton_at, sat_stress_of_T, sigma0_of_T)

OUT = R / "results" / "phase0ir"
WD = OUT / "decomp"
WD.mkdir(parents=True, exist_ok=True)
TEMPS = [-40., 0., 25., 50., 75., 100., 125.]
N_CYC, DWELL, GAMMA = 4, 300.0, 0.004
T_HOT, T_COLD, T_REF = 100.0, 0.0, 25.0


def material(kind: str) -> str:
    if kind == "EPC":
        return inp_material("SAC305", TEMPS)
    L = ["*MATERIAL, NAME=SAC305", "*ELASTIC"]
    L += [f"{E_of_T(T):.6g}, {NU}, {T:.1f}" for T in TEMPS]
    if kind in ("EP", "EPC"):
        L.append("*PLASTIC")
        for T in TEMPS:
            L.append(f"{sigma0_of_T(T):.6g}, 0.0, {T:.1f}")
            L.append(f"{sat_stress_of_T(T):.6g}, 0.02, {T:.1f}")
    if kind in ("EC", "EPC"):
        L.append("*CREEP, LAW=NORTON")
        for T in TEMPS:
            f = norton_at(T)
            L.append(f"{f['A']:.6e}, {f['n']:.6g}, 0.0, {T:.1f}")
    L += ["*EXPANSION, ZERO=25.", f"{CTE_SAC305:.4g}"]
    return "\n".join(L) + "\n"


def cycles():
    du = GAMMA * BALL_H_UM / 1e3
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}h", T_HOT, du, DWELL)); t += DWELL
        cyc.append((f"c{k}c", T_COLD, -du, DWELL)); t += DWELL
        ends.append(t)
    return cyc, ends


def temperature_at(t: float) -> float:
    """The step schedule is deterministic, so the joint temperature at any time is known."""
    k = int(t // DWELL)
    return T_HOT if k % 2 == 0 else T_COLD


def parse_temperature(dat: Path) -> dict:
    """{time: T} from the solver's own nodal temperature output. The field is uniform in this
    submodel, so the first node is representative."""
    out, kind, tm = {}, None, None
    for l in dat.read_text().splitlines():
        h = re.match(r"\s*(temperatures).*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2)); continue
        p = l.split()
        # DEFECT #46: this used to keep the FIRST block at a given time key, while
        # parse_tensors() keeps the LAST. At a step boundary CalculiX prints the same nominal
        # time twice -- end of step k and start of step k+1 -- so the tensors and the
        # temperature were taken from OPPOSITE sides of every boundary. The thermal strain was
        # then subtracted with a temperature wrong by ~55 K at exactly the 11 instants where
        # the joint deposits most of its damage, inflating the inelastic-ENERGY metric by
        # 18.5 %. PEEQ was unaffected because it is read from the solver, not reconstructed.
        # Both parsers now keep the LAST block, so they agree.
        if kind == "temperatures" and len(p) >= 2 and p[0].isdigit():
            if tm not in out or True:
                out[tm] = float(p[1])
        elif p and not p[0].isdigit():
            kind = None
    return out


def parse_tensors(dat: Path, elems: set | None = None) -> dict:
    """{time: {elem: {'S': [...], 'E': [...], 'PEEQ': v}}} averaged over integration points."""
    out, kind, tm = {}, None, None
    acc: dict = {}
    for l in dat.read_text().splitlines():
        h = re.match(r"\s*(stresses|strains|equivalent plastic strain|volume)"
                     r".*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2))
            out.setdefault(tm, {})
            continue
        p = l.split()
        if not (kind and p and p[0].isdigit()):
            continue
        e = int(p[0])
        if elems is not None and e not in elems:
            continue
        d = out[tm].setdefault(e, {})
        if kind == "stresses" and len(p) >= 8:
            d.setdefault("S", []).append([float(x) for x in p[2:8]])
        elif kind == "strains" and len(p) >= 8:
            d.setdefault("E", []).append([float(x) for x in p[2:8]])
        elif kind == "equivalent plastic strain" and len(p) >= 3:
            d.setdefault("P", []).append(float(p[2]))
        elif kind == "volume" and len(p) >= 2:
            d["V"] = float(p[-1])
    for tm, per in out.items():
        for e, d in per.items():
            for k in ("S", "E"):
                if k in d:
                    d[k] = list(np.mean(np.array(d[k]), axis=0))
            if "P" in d:
                d["P"] = float(np.mean(d["P"]))
    return out


def eq_strain(e) -> float:
    exx, eyy, ezz, exy, exz, eyz = e
    m = (exx + eyy + ezz) / 3.0
    dx, dy, dz = exx - m, eyy - m, ezz - m
    return math.sqrt(2.0 / 3.0 * (dx * dx + dy * dy + dz * dz
                                  + 2 * (exy * exy + exz * exz + eyz * eyz)))


def decompose(S, Etot, T_c):
    """elastic from Hooke at E(T); thermal from alpha*(T - Tref); inelastic = the remainder."""
    E, nu, a = E_of_T(T_c), NU, CTE_SAC305
    th = a * (T_c - T_REF)
    el = [(S[0] - nu * (S[1] + S[2])) / E, (S[1] - nu * (S[0] + S[2])) / E,
          (S[2] - nu * (S[0] + S[1])) / E,
          (1 + nu) * S[3] / E, (1 + nu) * S[4] / E, (1 + nu) * S[5] / E]
    therm = [th, th, th, 0.0, 0.0, 0.0]
    inel = [Etot[i] - el[i] - therm[i] for i in range(6)]
    return el, therm, inel


def solve(kind: str):
    m = build_joint(6, 8, 1)
    cyc, ends = cycles()
    p = WD / f"{kind}.inp"
    write_inp(m, p, material(kind), cyc, cetol=1e-2,
              procedure=("STATIC" if kind == "EP" else "VISCO"))
    # ask for the tensors on the CORE set too, so decomposition uses the metric's own region
    # Also request the NODAL TEMPERATURE. CalculiX RAMPS *TEMPERATURE linearly across a step
    # unless AMPLITUDE=STEP is given, so reconstructing T analytically from the step schedule
    # is wrong mid-step and corrupts the thermal-strain subtraction. Read the solver's own T.
    s = p.read_text().replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                              "*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E",
                  "*EL PRINT, ELSET=ESOL\nS, E\n*NODE PRINT, NSET=NBOT\nNT")
    p.write_text(s)
    run(p, threads=6)
    d = WD / f"{kind}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None, m, ends
    return (parse_tensors(d, set(m.sets["ESOLCORE"])), m, ends,
            parse_temperature(d))


def vol_avg(per, key_fn, vols):
    num = den = 0.0
    for e, d in per.items():
        v = vols.get(e, 1.0)
        val = key_fn(d)
        if val is None or not np.isfinite(val):
            continue
        num += val * v
        den += v
    return num / den if den else float("nan")


def main():
    results, series = {}, {}
    for kind in ("EP", "EC", "EPC"):
        data, m, ends, temps = solve(kind)
        if data is None:
            print(f"  {kind}: SOLVER PRODUCED NO USABLE OUTPUT"); continue
        vols = {e: d.get("V", 1.0) for per in data.values() for e, d in per.items() if "V" in d}
        ts = sorted(data)
        rows = []
        for t in ts:
            per = data[t]
            T = temps.get(t, temperature_at(t))
            def peeq(d): return d.get("P")
            def eqin(d):
                if "S" not in d or "E" not in d: return None
                _, _, inel = decompose(d["S"], d["E"], T)
                return eq_strain(inel)
            def eqtot(d): return eq_strain(d["E"]) if "E" in d else None
            def eqel(d):
                if "S" not in d: return None
                el, _, _ = decompose(d["S"], d["E"], T); return eq_strain(el)
            rows.append({"time_s": t, "T_C": T,
                         "eq_total": vol_avg(per, eqtot, vols),
                         "eq_elastic": vol_avg(per, eqel, vols),
                         "eq_thermal": abs(CTE_SAC305 * (T - T_REF)),
                         "eq_inelastic_from_decomposition": vol_avg(per, eqin, vols),
                         "PEEQ_solver": vol_avg(per, peeq, vols)})
        series[kind] = rows
        results[kind] = (data, ends, vols)
        good = [r for r in rows if np.isfinite(r["eq_inelastic_from_decomposition"])
                and r["eq_inelastic_from_decomposition"] > 1e-9]
        if good:
            rat = [r["PEEQ_solver"] / r["eq_inelastic_from_decomposition"] for r in good]
            print(f"  {kind}: {len(ts)} output times; PEEQ / eq(inelastic) = "
                  f"{np.mean(rat):.4f} +/- {np.std(rat):.4f} "
                  f"(min {min(rat):.4f}, max {max(rat):.4f})", flush=True)

    with open(OUT / "strain_component_decomposition.csv", "w", newline="") as f:
        allrows = [{"model": k, **r} for k, rs in series.items() for r in rs]
        w = csv.DictWriter(f, fieldnames=list(allrows[0])); w.writeheader(); w.writerows(allrows)
    print(f"\nwrote strain_component_decomposition.csv ({sum(len(v) for v in series.values())} rows)")
    return results, series


if __name__ == "__main__":
    main()
