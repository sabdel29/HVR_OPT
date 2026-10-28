"""Block-order extraction of the local solder metrics from a CalculiX .dat file.

THE DEFECT THIS REPLACES (found 2026-10-27, final closure). CalculiX prints output times
with seven significant digits, so at t ~ 1e3 s two increments less than 1 ms apart print
the SAME time. The validated parser (scripts/phase0ir/decompose.py parse_tensors) keys
the output by printed time and AVERAGES every block that shares a key. When a load step
starts with sub-millisecond increments, the key of the step boundary therefore mixes the
state before the load jump with states after it. Interior cycles are biased identically
at both ends and the bias cancels, but the LAST cycle (whose end time is clean) is not:
its d_eps came out up to 17 % low, and a 16-cycle run showed cycles 3-15 unchanged to
0.05 % while only cycle 16 dropped. Production runs that start every step at 2e-3 s print
distinct boundary times, so their d_eps is unaffected; a run that cuts back below
~5e-4 s at a load step is not.

THE FIX. Every printed increment is kept as its own state, in FILE order. A cycle window
runs from the FIRST block printed at the cycle-start time (that block is the end of the
previous step: later blocks with the same printed time are the next step's first
increments) to the FIRST block printed at the cycle-end time (or the final block). The
tensor algebra (elastic/thermal/inelastic split, equivalent strain, work integral) is the
validated Phase-0I-R code, imported unchanged; only the bookkeeping changes. Collisions
are counted and reported, never silently merged.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0ir", "scripts/phase0i"):
    sys.path.insert(0, str(R / _p))
from decompose import decompose, eq_strain                          # noqa: E402

HDR = re.compile(r"\s*(equivalent plastic strain|volume|stresses|strains|temperatures)"
                 r".*for set (\S+) and time\s+([0-9.E+-]+)")


def parse_blocks(dat, core):
    """[(t_printed, {elem: {'P','S','E'}}, T, V)] in file order, one entry per increment.
    An increment starts at its 'equivalent plastic strain' block for the core set."""
    incs, cur, kind, vols, core = [], None, None, {}, set(core)
    with open(dat) as fh:
        for line in fh:
            h = HDR.match(line)
            if h:
                kind, sset, t = h.group(1), h.group(2), float(h.group(3))
                if kind == "equivalent plastic strain" and sset == "ESOLCORE":
                    cur = {"t": t, "el": {}, "T": None}
                    incs.append(cur)
                elif cur is not None and abs(t - cur["t"]) > 0:
                    raise ValueError(f"{dat}: block at t={t} inside increment t={cur['t']}")
                if sset != "ESOLCORE" and kind != "temperatures":
                    kind = None                     # ESOL tensors are not needed here
                continue
            p = line.split()
            if not (kind and cur is not None and p and p[0].isdigit()):
                continue
            if kind == "temperatures":
                if cur["T"] is None and len(p) >= 2:
                    cur["T"] = float(p[1])
                continue
            e = int(p[0])
            if e not in core:
                continue
            d = cur["el"].setdefault(e, {})
            if kind == "equivalent plastic strain" and len(p) >= 3:
                d.setdefault("P", []).append(float(p[2]))
            elif kind == "stresses" and len(p) >= 8:
                d.setdefault("S", []).append([float(x) for x in p[2:8]])
            elif kind == "strains" and len(p) >= 8:
                d.setdefault("E", []).append([float(x) for x in p[2:8]])
            elif kind == "volume" and len(p) >= 2:
                vols[e] = float(p[-1])
    for inc in incs:
        for d in inc["el"].values():
            d["P"] = float(np.mean(d["P"]))
            for k in ("S", "E"):
                if k in d:
                    d[k] = list(np.mean(np.array(d[k]), axis=0))
    return incs, vols


def collisions(incs, boundaries):
    """Printed times shared by more than one increment, split into step-boundary
    collisions (which corrupt a time-keyed parser's d_eps) and interior ones."""
    from collections import Counter
    c = Counter(round(i["t"], 6) for i in incs)
    dup = {t: n for t, n in c.items() if n > 1}
    b = {t: n for t, n in dup.items() if any(abs(t - x) < 1e-6 for x in boundaries)}
    return {"n_increments": len(incs), "n_distinct_times": len(c),
            "boundary_collisions": b, "interior_collisions": len(dup) - len(b)}


def _first_at(incs, t):
    for k, inc in enumerate(incs):
        if abs(inc["t"] - t) < 1e-6:
            return k
    return None


def cycle_metrics(incs, vols, t0, t1, last=False):
    """d_peeq, range of eq inelastic strain and inelastic work over one cycle window."""
    i0 = _first_at(incs, t0)
    i1 = (len(incs) - 1) if last else _first_at(incs, t1)
    if i0 is None or i1 is None or i1 - i0 < 3:
        return None
    win = incs[i0:i1 + 1]
    dpe = rng = wrk = den = 0.0
    for e, v in vols.items():
        rows = [w for w in win if e in w["el"] and "S" in w["el"][e] and "E" in w["el"][e]]
        if len(rows) < 3:
            continue
        d_p = rows[-1]["el"][e]["P"] - rows[0]["el"][e]["P"]
        eqs, inels = [], []
        for w in rows:
            _, _, inel = decompose(w["el"][e]["S"], w["el"][e]["E"], w["T"])
            inels.append(np.array(inel))
            eqs.append(eq_strain(inel))
        work = 0.0
        for k in range(1, len(rows)):
            s0, s1 = np.array(rows[k - 1]["el"][e]["S"]), np.array(rows[k]["el"][e]["S"])
            de, sm = inels[k] - inels[k - 1], 0.5 * (s0 + s1)
            work += float(sm[:3] @ de[:3] + 2 * (sm[3:] @ de[3:]))
        dpe += d_p * v
        rng += (max(eqs) - min(eqs)) * v
        wrk += work * v
        den += v
    if not den:
        return None
    return {"d_peeq_per_cycle": dpe / den, "range_eq_inelastic": rng / den,
            "inelastic_work_MJ_per_m3": wrk / den, "i0": i0, "i1": i1}


def extract(dat, core, n_cyc, dwell):
    """Every cycle's metrics plus the collision report, from one .dat file."""
    incs, vols = parse_blocks(dat, core)
    period = 2 * dwell
    bounds = [k * dwell for k in range(2 * n_cyc + 1)]
    out = {"collisions": collisions(incs, bounds), "cycles": [],
           "complete": bool(incs) and abs(incs[-1]["t"] - n_cyc * period) < 1e-6}
    if not out["complete"]:                 # a truncated run has no last cycle to report
        return out
    for k in range(n_cyc):
        out["cycles"].append(cycle_metrics(incs, vols, k * period, (k + 1) * period,
                                           last=(k == n_cyc - 1)))
    last, prev = out["cycles"][-1], out["cycles"][-2] if n_cyc > 1 else None
    if last and prev:
        out["d_peeq_per_cycle"] = last["d_peeq_per_cycle"]
        out["prev_cycle_d_eps"] = prev["d_peeq_per_cycle"]
        out["stab_change_pct"] = 100 * abs(last["d_peeq_per_cycle"] - prev["d_peeq_per_cycle"]) \
            / prev["d_peeq_per_cycle"]
        out["range_eq_inelastic"] = last["range_eq_inelastic"]
        out["inelastic_work_MJ_per_m3"] = last["inelastic_work_MJ_per_m3"]
    return out
