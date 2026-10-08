#!/usr/bin/env python3
"""Phase-0I Sec.14 -- validate the local joint submodel BEFORE any architecture comparison.

Six checks, in the order the brief lists them. If the constitutive model is not numerically
credible here, the architecture comparison does not run.
"""
from __future__ import annotations
import json, math, subprocess, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0i"))
from joint import build_joint, write_inp, run, read_dat, cycle_metric, BALL_H_UM  # noqa
from solder_model import (E_of_T, garofalo_rate, inp_material, norton_at,          # noqa
                          sigma0_of_T, CTE_SAC305)

WD = R / "results" / "phase0i" / "joint_val"
WD.mkdir(parents=True, exist_ok=True)
TEMPS = [-40., 0., 25., 50., 75., 100., 125.]
MAT = inp_material("SAC305", TEMPS)


def _solve(tag, m, cycles, t_ref=25.0):
    p = WD / f"{tag}.inp"
    write_inp(m, p, MAT, cycles, t_ref_c=t_ref)
    run(p)
    d = WD / f"{tag}.dat"
    return read_dat(d) if d.is_file() and d.stat().st_size else None


def free_expansion():
    """A SOLDER-ONLY block on 3-2-1 supports must expand by exactly alpha*dT.

    The first version of this test heated the full pad/solder/pad joint with the bottom face
    clamped. That is not a free-expansion test: the clamp restrains it and the Cu pads have a
    different CTE, so inelastic strain is the CORRECT answer there, not an error. The check is
    only meaningful on unconstrained solder.
    """
    L, dT, aref = 0.3, 100.0, CTE_SAC305
    inp = WD / "free_exp.inp"
    nodes = [(0, 0, 0), (L, 0, 0), (L, L, 0), (0, L, 0),
             (0, 0, L), (L, 0, L), (L, L, L), (0, L, L)]
    txt = ["*NODE"] + [f"{i+1}, {x}, {y}, {z}" for i, (x, y, z) in enumerate(nodes)]
    txt += ["*ELEMENT, TYPE=C3D8, ELSET=EALL", "1, 1,2,3,4,5,6,7,8",
            "*NSET, NSET=NALL, GENERATE", "1, 8, 1", MAT.rstrip(),
            "*SOLID SECTION, ELSET=EALL, MATERIAL=SAC305",
            "*INITIAL CONDITIONS, TYPE=TEMPERATURE", "NALL, 25.",
            "*BOUNDARY", "1,1,3", "2,2", "2,3", "4,1", "4,3", "5,1", "5,2",
            "*STEP, INC=200", "*VISCO, CETOL=1.0E-2", "0.01, 1.0",
            "*TEMPERATURE", f"NALL, {25.0+dT}",
            "*NODE PRINT, NSET=NALL", "U", "*EL PRINT, ELSET=EALL", "PEEQ", "*END STEP"]
    inp.write_text("\n".join(txt) + "\n")
    run(inp)
    d = WD / "free_exp.dat"
    if not (d.is_file() and d.stat().st_size > 100):
        return {"check": "free thermal expansion", "ok": False, "detail": "no output"}
    import re
    ux = None; peeq = None; kind = None
    for l in d.read_text().splitlines():
        if "displacements" in l: kind = "u"; continue
        if "equivalent plastic strain" in l: kind = "p"; continue
        q = l.split()
        if kind == "u" and len(q) >= 4 and q[0] == "7": ux = float(q[1])
        if kind == "p" and len(q) >= 3 and q[0] == "1": peeq = float(q[2])
    exp = aref * dT * L
    err = abs(ux - exp) / exp * 100 if ux else float("nan")
    ok = ux is not None and err < 1.0 and (peeq or 0) < 1e-8
    return {"check": "free thermal expansion", "ok": bool(ok),
            "detail": f"u_x at the far corner = {ux:.6e} mm against alpha*dT*L = {exp:.6e} mm "
                      f"({err:.3f} % error); PEEQ = {peeq:.2e} (must be ~0 -- free expansion "
                      f"generates no inelastic strain)"}


def temperature_monotonicity():
    """Creep rate and yield must move the right way with temperature."""
    rates = [garofalo_rate(10.0, T) for T in (25., 75., 125.)]
    ys = [sigma0_of_T(T) for T in (25., 75., 125.)]
    es = [E_of_T(T) for T in (25., 75., 125.)]
    return {"check": "monotonic temperature dependence",
            "ok": all(b > a for a, b in zip(rates, rates[1:]))
                  and all(b < a for a, b in zip(ys, ys[1:]))
                  and all(b < a for a, b in zip(es, es[1:])),
            "detail": f"creep rate at 10 MPa rises {rates[0]:.2e} -> {rates[-1]:.2e} "
                      f"({rates[-1]/rates[0]:.0f}x); yield falls {ys[0]:.1f} -> {ys[-1]:.1f} MPa; "
                      f"E falls {es[0]:.0f} -> {es[-1]:.0f} MPa"}


def creep_relaxation():
    """Hold a shear displacement at temperature: stress must decay."""
    m = build_joint(4, 6, 1)
    du = 0.002 * BALL_H_UM / 1e3
    dat = _solve("relax", m, [("hold", 100.0, du, 600.0)])
    txt = (WD / "relax.dat").read_text() if (WD / "relax.dat").is_file() else ""
    import re
    sv = []
    kind = tm = None
    for l in txt.splitlines():
        h = re.match(r"\s*(stresses).*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2)); continue
        p = l.split()
        if kind == "stresses" and p and p[0].isdigit() and len(p) >= 8:
            sv.append((tm, abs(float(p[6]))))
    if len(sv) < 4:
        return {"check": "creep relaxation at constant strain", "ok": False,
                "detail": "insufficient stress output"}
    early = np.mean([v for t, v in sv if t < 30]) or 1e-9
    late = np.mean([v for t, v in sv if t > 500]) or 0.0
    drop = 100 * (late - early) / early
    return {"check": "creep relaxation at constant strain", "ok": drop < -10,
            "detail": f"mean |sxz| {early:.3f} -> {late:.3f} MPa over a 600 s hold "
                      f"({drop:+.1f} %). Negative and material means creep is active."}


def cycle_stabilisation(n_cyc=5):
    """Delta-eps_in per cycle must settle."""
    m = build_joint(5, 6, 1)
    du = 0.004 * BALL_H_UM / 1e3
    cyc, ends, t = [], [], 0.0
    for k in range(n_cyc):
        cyc.append((f"c{k}_hot", 100.0, du, 300.0)); t += 300.0
        cyc.append((f"c{k}_cold", 0.0, -du, 300.0)); t += 300.0
        ends.append(t)
    dat = _solve("stab", m, cyc)
    if not dat or not dat["peeq"]:
        return {"check": "cycle stabilisation", "ok": False, "detail": "no output"}, []
    inc, vals = cycle_metric(dat, [0.0] + ends)
    ok = len(inc) >= 3 and abs(inc[-1] - inc[-2]) / max(inc[-2], 1e-12) < 0.15
    return ({"check": "cycle stabilisation", "ok": bool(ok),
             "detail": "per-cycle d(eps_in) = " + ", ".join(f"{v:.4e}" for v in inc)
                       + f"; last-to-previous change "
                       f"{100*abs(inc[-1]-inc[-2])/max(inc[-2],1e-12):.1f} %"}, inc)


def main():
    res = []
    print("Phase-0I Sec.14 -- local submodel validation\n")
    for fn in (free_expansion, temperature_monotonicity, creep_relaxation):
        r = fn(); res.append(r)
        print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['check']}\n         {r['detail']}",
              flush=True)
    r, inc = cycle_stabilisation()
    res.append(r)
    print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['check']}\n         {r['detail']}")
    (R / "results/phase0i/joint_validation.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\n{sum(1 for x in res if x['ok'])}/{len(res)} checks passed")


if __name__ == "__main__":
    main()
