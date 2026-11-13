#!/usr/bin/env python3
"""Phase-0I Sec.13 -- explicit local solder-joint submodel.

GLOBAL -> LOCAL
The global package model supplies, at the critical joint location:
    du(t)   the relative in-plane displacement imposed across the joint standoff
    T(t)    the joint temperature history
The local model resolves the joint itself -- board pad, solder, package pad -- and integrates
the temperature-dependent elastic + plastic + creep response through several cycles.

GEOMETRY (June-2026 Table III BGA: d = 400 um, h = 300 um, pitch 800 um)
The ball is represented by an EQUAL-AREA SQUARE prism, side sqrt(pi/4)*400 = 354.5 um. This is
the same equal-area convention Phase 0G used to homogenise the ball array, so the local and
global models describe the same amount of solder. Pads are 400 um square and overhang the
solder, so the solder free edge is a genuine bimaterial corner -- which is exactly why the
metric is volume-averaged with a corner exclusion band rather than read at the peak.
"""
from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

BALL_D_UM = 400.0
BALL_H_UM = 300.0
PAD_UM = 400.0
PAD_T_UM = 20.0
SOLDER_SIDE_UM = math.sqrt(math.pi / 4.0) * BALL_D_UM      # 354.49 um, equal area


@dataclass
class JointMesh:
    nodes: np.ndarray                      # (N,3) in mm
    elems: list                            # list of (eid, [8 node ids], setname)
    sets: dict = field(default_factory=dict)

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)


def _grid(lo: float, hi: float, n: int) -> np.ndarray:
    return np.linspace(lo, hi, n + 1)


import os as _os

#: Fixed-width corner-exclusion band as a fraction of the solder side (TCPMT revision).
#: Unset (legacy): the band is ONE ELEMENT wide, so the averaging volume ESOLCORE grows with
#: refinement (128 -> 1600 core elements over L0..L3) and a mesh study of the metric cannot
#: converge in principle. Set JOINT_BAND_FRAC (e.g. 1/6 = one L0 element = 59.08 um) to make
#: the band a fixed PHYSICAL width: breakpoints are inserted at the band edge, so every level
#: averages exactly the same region. With n_xy = 6 the fixed band reproduces legacy L0 exactly.
BAND_FRAC = float(_os.environ["JOINT_BAND_FRAC"]) if _os.environ.get("JOINT_BAND_FRAC") else None


def build_joint(n_xy: int = 6, n_z_solder: int = 8, n_z_pad: int = 1) -> JointMesh:
    """Structured hex mesh: pad / solder / pad, with the solder inset inside the pads."""
    hp, hs = PAD_UM / 2e3, SOLDER_SIDE_UM / 2e3            # mm
    tp, hsol = PAD_T_UM / 1e3, BALL_H_UM / 1e3
    # in-plane grid: solder edges are breakpoints so both regions share nodes
    n_in = max(2, n_xy)
    n_out = max(1, n_xy // 3)
    if BAND_FRAC:
        b = BAND_FRAC * 2 * hs
        dx0 = 2 * hs / n_in
        n_b = max(1, int(np.ceil(b / dx0 - 1e-9)))        # band elements never wider than dx0
        n_c = max(2, int(round((2 * hs - 2 * b) / dx0)))  # core refines with every level
        xs = np.unique(np.concatenate([_grid(-hp, -hs, n_out), _grid(-hs, -hs + b, n_b),
                                       _grid(-hs + b, hs - b, n_c), _grid(hs - b, hs, n_b),
                                       _grid(hs, hp, n_out)]))
    else:
        xs = np.unique(np.concatenate([_grid(-hp, -hs, n_out), _grid(-hs, hs, n_in),
                                       _grid(hs, hp, n_out)]))
    ys = xs.copy()
    zs = np.unique(np.concatenate([_grid(0.0, tp, n_z_pad),
                                   _grid(tp, tp + hsol, n_z_solder),
                                   _grid(tp + hsol, tp + hsol + tp, n_z_pad)]))
    nx, ny, nz = len(xs), len(ys), len(zs)
    nid = np.arange(1, nx * ny * nz + 1).reshape(nx, ny, nz)
    pts = np.zeros((nx * ny * nz, 3))
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                pts[nid[i, j, k] - 1] = (xs[i], ys[j], zs[k])
    elems, eid = [], 0
    for i in range(nx - 1):
        for j in range(ny - 1):
            xc, yc = .5 * (xs[i] + xs[i + 1]), .5 * (ys[j] + ys[j + 1])
            inside = abs(xc) < hs - 1e-12 and abs(yc) < hs - 1e-12
            for k in range(nz - 1):
                zc = .5 * (zs[k] + zs[k + 1])
                if zc < tp:
                    setname = "EPADB"
                elif zc < tp + hsol:
                    if not inside:
                        continue               # void outside the solder footprint
                    setname = "ESOL"
                else:
                    setname = "EPADT"
                eid += 1
                c = [nid[i, j, k], nid[i + 1, j, k], nid[i + 1, j + 1, k], nid[i, j + 1, k],
                     nid[i, j, k + 1], nid[i + 1, j, k + 1], nid[i + 1, j + 1, k + 1],
                     nid[i, j + 1, k + 1]]
                elems.append((eid, c, setname))
    used = sorted({n for _, c, _ in elems for n in c})
    remap = {o: i + 1 for i, o in enumerate(used)}
    pts = pts[[o - 1 for o in used]]
    elems = [(e, [remap[n] for n in c], s) for e, c, s in elems]
    zb, zt = zs[0], zs[-1]
    sets = {
        "NBOT": [remap[n] for n in used if abs(pts[remap[n] - 1, 2] - zb) < 1e-9],
        "NTOP": [remap[n] for n in used if abs(pts[remap[n] - 1, 2] - zt) < 1e-9],
    }
    m = JointMesh(pts, elems, sets)
    # corner exclusion: legacy = solder elements whose centroid is within one element of the
    # free edge (mesh dependent); fixed band = centroid within the physical band b
    dx = (2 * hs) / n_in
    lim = (hs - BAND_FRAC * 2 * hs) if BAND_FRAC else (hs - dx * 0.999)
    core = []
    for e, c, s in elems:
        if s != "ESOL":
            continue
        ctr = pts[[n - 1 for n in c]].mean(axis=0)
        if max(abs(ctr[0]), abs(ctr[1])) < lim:
            core.append(e)
    m.sets["ESOLCORE"] = core
    m.sets["_dx_mm"] = dx
    return m


def write_inp(m: JointMesh, path: Path, material_block: str, cycles: list,
              t_ref_c: float = 25.0, cetol: float = 1.0e-2,
              procedure: str = "VISCO") -> None:
    """`cycles` is a list of (label, T_celsius, du_mm, duration_s) segments."""
    L = ["*NODE"]
    L += [f"{i+1}, {p[0]:.6f}, {p[1]:.6f}, {p[2]:.6f}" for i, p in enumerate(m.nodes)]
    for s in ("EPADB", "ESOL", "EPADT"):
        el = [(e, c) for e, c, ss in m.elems if ss == s]
        if not el:
            continue
        L.append(f"*ELEMENT, TYPE=C3D8, ELSET={s}")
        L += [f"{e}, " + ", ".join(str(n) for n in c) for e, c in el]
    L.append("*ELSET, ELSET=ESOLCORE")
    core = m.sets["ESOLCORE"]
    for i in range(0, len(core), 8):
        L.append(", ".join(str(e) for e in core[i:i + 8]) + ("," if i + 8 < len(core) else ""))
    for nm in ("NBOT", "NTOP"):
        L.append(f"*NSET, NSET={nm}")
        v = m.sets[nm]
        for i in range(0, len(v), 8):
            L.append(", ".join(str(x) for x in v[i:i + 8]) + ("," if i + 8 < len(v) else ""))
    L.append("*NSET, NSET=NALL, GENERATE")
    L.append(f"1, {len(m.nodes)}, 1")
    L.append(material_block.rstrip())
    L += ["*MATERIAL, NAME=CU", "*ELASTIC", "117000., 0.34", "*EXPANSION, ZERO=25.", "16.6e-06",
          "*SOLID SECTION, ELSET=ESOL, MATERIAL=SAC305",
          "*SOLID SECTION, ELSET=EPADB, MATERIAL=CU",
          "*SOLID SECTION, ELSET=EPADT, MATERIAL=CU",
          "*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL, {t_ref_c}"]
    L.append("*BOUNDARY")
    L += ["NBOT,1,3", "NTOP,2,2", "NTOP,3,3"]
    for lab, T, du, dur in cycles:
        # A large first increment diverges: the imposed shear yields the solder immediately
        # and the Norton law (n ~ 7.6) is stiff on the first creep step. A small opening
        # increment plus a looser CETOL converges; CETOL sensitivity is checked in Sec.14.
        # Without a *CREEP card there is nothing for *VISCO to integrate and the
        # near-perfectly-plastic response diverges; those cases use *STATIC with fine
        # increments instead. This is a procedure choice, not a physics change.
        proc = (f"*VISCO, CETOL={cetol:g}" if procedure == "VISCO" else "*STATIC")
        L += [f"** ---- {lab}", "*STEP, INC=5000", proc,
              f"{min(0.002, dur/2000.0):.6g}, {dur:.6g}, {min(1e-6, dur/1e7):.3g}, "
              f"{max(dur/20.0, 0.05):.6g}",
              "*TEMPERATURE", f"NALL, {T:.4f}",
              "*BOUNDARY", f"NTOP,1,1,{du:.8f}",
              "*EL PRINT, ELSET=ESOLCORE", "PEEQ, EVOL",
              "*EL PRINT, ELSET=ESOL", "S, E",
              "*END STEP"]
    path.write_text("\n".join(L) + "\n")


def run(path: Path, threads: int = 4) -> None:
    subprocess.run(["ccx", "-i", str(path.with_suffix(""))], check=False,
                   capture_output=True, text=True, cwd=path.parent,
                   env={**__import__("os").environ, "OMP_NUM_THREADS": str(threads)})


def read_dat(path: Path) -> dict:
    """Parse per-element PEEQ / EVOL / S / E time series."""
    out = {"peeq": {}, "evol": {}, "svm": {}}
    kind = tm = None
    for l in path.read_text().splitlines():
        h = re.match(r"\s*(equivalent plastic strain|volume|stresses|strains).*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2)); continue
        p = l.split()
        if not (kind and p and p[0].isdigit()):
            continue
        if kind == "equivalent plastic strain" and len(p) >= 3:
            out["peeq"].setdefault(tm, {}).setdefault(int(p[0]), []).append(float(p[2]))
        elif kind == "volume" and len(p) >= 2:
            out["evol"][int(p[0])] = float(p[-1])
    return out


def cycle_metric(dat: dict, cycle_end_times: list) -> list:
    """Volume-averaged inelastic strain increment per cycle over ESOLCORE."""
    ev = dat["evol"]
    vals = []
    for t in cycle_end_times:
        near = min(dat["peeq"], key=lambda x: abs(x - t)) if dat["peeq"] else None
        if near is None:
            vals.append(float("nan")); continue
        per = dat["peeq"][near]
        num = den = 0.0
        for e, lst in per.items():
            v = ev.get(e, 1.0)
            num += float(np.mean(lst)) * v
            den += v
        vals.append(num / den if den else float("nan"))
    return [b - a for a, b in zip(vals, vals[1:])], vals
