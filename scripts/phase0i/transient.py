#!/usr/bin/env python3
"""Phase-0I Sec.7 -- transient thermal capability, added WITHOUT touching shared code.

`etm.ccxio.write_thermal()` is used by every phase from 0B onward and by 189 tests, so it is
not modified. Instead the validated steady-state deck it produces is transformed here:

  * *DENSITY and *SPECIFIC HEAT are appended to each material,
  * *HEAT TRANSFER, STEADY STATE becomes a time-stepped *HEAT TRANSFER,
  * temperature is written at time points so T(x,y,z,t) is recoverable.

rho*cp is a declared handbook assumption (configs/phase0i/thermal_transient.yaml). It sets how
FAST the field arrives and never where it arrives, so the steady-state field the damage
assessment consumes is untouched by it. The transient exists to justify the dwell length of a
thermal cycle rather than to assume one.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np
import yaml

R = Path(__file__).resolve().parents[2]
CFG = R / "configs" / "phase0i" / "thermal_transient.yaml"


def rho_cp() -> dict:
    return yaml.safe_load(CFG.read_text())["materials"]


def make_transient(steady_inp: Path, out_inp: Path, t_end: float, dt0: float,
                   t_init: float, n_out: int = 40) -> Path:
    """Rewrite a steady-state thermal deck as a transient one."""
    s = steady_inp.read_text()
    cfg = rho_cp()

    # 1. append DENSITY / SPECIFIC HEAT to every *MATERIAL block we have data for
    lc = {k.lower(): v for k, v in cfg.items()}

    def add_props(mo):
        # CalculiX decks carry material names UPPERCASED; the config keys are lower case.
        name = mo.group(1).strip()
        c = lc.get(name.lower())
        if not c:
            return mo.group(0)
        # mm-tonne-s: density t/mm^3, specific heat mJ/(t.K)
        return (mo.group(0) + f"\n*DENSITY\n{c['rho_kg_m3']*1e-12:.6e}"
                f"\n*SPECIFIC HEAT\n{c['cp_J_kgK']*1e6:.6e}")
    s = re.sub(r"\*MATERIAL,\s*NAME=([A-Za-z0-9_]+)", add_props, s)

    # 2. steady -> transient step
    s = s.replace("*STEP", f"*STEP, INC=100000", 1)
    s = s.replace("*HEAT TRANSFER, STEADY STATE",
                  f"*HEAT TRANSFER\n{dt0:.6g}, {t_end:.6g}", 1)
    # 3. initial condition at the declared start temperature
    s = re.sub(r"(\*INITIAL CONDITIONS, TYPE=TEMPERATURE\n[A-Za-z0-9_]+,)\s*[-0-9.eE+]+",
               rf"\g<1>{t_init}", s, count=1)
    # 4. output on an explicit, logarithmically spaced time-point list. FREQUENCY counts
    #    INCREMENTS, not time, so with adaptive stepping it gives one frame at the end.
    tp = np.unique(np.round(np.geomspace(max(dt0 * 10, t_end / 5000.0), t_end, n_out), 6))
    lines = ["*TIME POINTS, NAME=TP"]
    for i in range(0, len(tp), 8):
        lines.append(", ".join(f"{v:.6g}" for v in tp[i:i + 8])
                     + ("," if i + 8 < len(tp) else ""))
    s = s.replace("*STEP, INC=100000", "\n".join(lines) + "\n*STEP, INC=100000", 1)
    s = s.replace("*NODE FILE", "*NODE FILE, TIME POINTS=TP", 1)
    out_inp.write_text(s)
    return out_inp


def run(inp: Path, threads: int = 8):
    import os
    # the bare stem in the deck's directory: CalculiX refuses a deck name over 127 characters
    subprocess.run(["ccx", "-i", inp.stem], cwd=inp.parent,
                   capture_output=True, text=True,
                   env={**os.environ, "OMP_NUM_THREADS": str(threads)})


def read_history(frd: Path) -> list:
    """[(time, Tmax, Tmin)] over the transient."""
    out, t, vals = [], None, []
    for line in frd.read_text(errors="ignore").splitlines():
        if line.startswith("  100CL"):
            if t is not None and vals:
                out.append((t, max(vals), min(vals)))
            m = re.search(r"100CL\s+\d+\s+([0-9.E+-]+)", line)
            t, vals = (float(m.group(1)) if m else None), []
        elif line.startswith(" -1") and t is not None:
            p = line.split()
            if len(p) >= 3:
                try:
                    vals.append(float(p[2]))
                except ValueError:
                    pass
    if t is not None and vals:
        out.append((t, max(vals), min(vals)))
    return out


def time_constant(hist: list) -> dict:
    """Fit the approach to steady state: T(t) = Tss - (Tss - T0) exp(-t/tau)."""
    if len(hist) < 4:
        return {"tau_s": float("nan"), "t_95_s": float("nan"), "n_points": len(hist)}
    ts = np.array([h[0] for h in hist])
    Tm = np.array([h[1] for h in hist])
    Tss, T0 = Tm[-1], Tm[0]
    if abs(Tss - T0) < 1e-9:
        return {"tau_s": float("nan"), "t_95_s": float("nan"), "n_points": len(hist)}
    frac = (Tss - Tm) / (Tss - T0)
    ok = (frac > 1e-3) & (frac < 0.999) & (ts > 0)
    if ok.sum() < 3:
        return {"tau_s": float("nan"), "t_95_s": float("nan"), "n_points": len(hist)}
    slope, _ = np.polyfit(ts[ok], np.log(frac[ok]), 1)
    tau = -1.0 / slope
    i95 = np.argmax(Tm >= T0 + 0.95 * (Tss - T0))
    return {"tau_s": float(tau), "t_95_s": float(ts[i95]), "T0_C": float(T0),
            "Tss_C": float(Tss), "n_points": len(hist)}
