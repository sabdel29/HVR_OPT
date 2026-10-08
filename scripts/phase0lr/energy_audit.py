#!/usr/bin/env python3
"""Phase-0L-R Part 4 -- independent reproduction and convergence of the cycle inelastic energy.

The production post-processor (scripts/phase0ir/cycle_audit.py :: cycle_quantities) computes

    W_in = sum_k  0.5*(S_k + S_{k-1}) : (eps_in,k - eps_in,k-1)

with eps_in RECONSTRUCTED in Python as  E_total - eps_elastic(Hooke, E(T)) - alpha*(T - T_REF).

Two things make that worth auditing rather than trusting:
  * the inelastic strain is reconstructed, not read from the solver -- the same class of
    Python-side-versus-solver-side mismatch as DEFECT #40;
  * the integral is sampled at OUTPUT points, so it inherits whatever the time stepping did.

This module recomputes W_in a second way:
  * eps_in = ME - eps_elastic, where ME is the solver's OWN mechanical strain
    (total minus thermal). No thermal reconstruction, no T_REF, no alpha.
  * three quadrature rules instead of one.
and then refines the time step and the output frequency until the answer stops moving.

Probed conventions (results/phase0lr/probe/shear.inp, run for this audit):
  * CalculiX .dat strain output uses the TENSOR shear convention -- ME_xy = sigma_xy/(2G) --
    so the double contraction needs a factor 2 on the off-diagonals. The production factor 2
    is correct.
  * ME = E - alpha*(T - T_zero) to 7 significant figures, confirming ME is the mechanical
    strain and that asking for it removes the thermal reconstruction entirely.
"""
from __future__ import annotations
import csv, math, re, subprocess, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0i", "phase0ir", "phase0jr", "phase0l"):
    sys.path.insert(0, str(R / "scripts" / d))
import solder_model as sm                                                   # noqa: E402
from graded_joint import build_joint_graded                                 # noqa: E402
from joint import run as run_ccx, write_inp                                 # noqa: E402
from decompose import decompose                                             # noqa: E402
import replay as RP                                                         # noqa: E402

OUT = R / "results" / "phase0lr"
WD = OUT / "wd"
WD.mkdir(parents=True, exist_ok=True)
DWELL, N_CYC, STAB = 300.0, 6, 5


def parse(dat: Path, elems: set):
    """{time: {elem: {'S':6, 'ME':6, 'E':6, 'P':float, 'V':float}}}, IP-averaged."""
    out, kind, tm = {}, None, None
    for l in dat.read_text().splitlines():
        h = re.match(r"\s*(stresses|strains|mechanical strains|equivalent plastic strain|volume)"
                     r".*time\s+([0-9.E+-]+)", l)
        if h:
            kind, tm = h.group(1), float(h.group(2)); out.setdefault(tm, {}); continue
        p = l.split()
        if not (kind and p and p[0].isdigit()):
            continue
        e = int(p[0])
        if e not in elems:
            continue
        d = out[tm].setdefault(e, {})
        if kind == "stresses" and len(p) >= 8:
            d.setdefault("S", []).append([float(x) for x in p[2:8]])
        elif kind == "strains" and len(p) >= 8:
            d.setdefault("E", []).append([float(x) for x in p[2:8]])
        elif kind == "mechanical strains" and len(p) >= 8:
            d.setdefault("ME", []).append([float(x) for x in p[2:8]])
        elif kind == "equivalent plastic strain" and len(p) >= 3:
            d.setdefault("P", []).append(float(p[2]))
        elif kind == "volume" and len(p) >= 2:
            d["V"] = float(p[-1])
    for tm, per in out.items():
        for e, d in per.items():
            for k in ("S", "E", "ME"):
                if k in d:
                    d[k] = list(np.mean(np.array(d[k]), axis=0))
            if "P" in d:
                d["P"] = float(np.mean(d["P"]))
    return out


def ddot(S, dE):
    """sigma : d(eps), tensor shear convention -> factor 2 on the off-diagonals."""
    return float(S[0]*dE[0] + S[1]*dE[1] + S[2]*dE[2]
                 + 2.0*(S[3]*dE[3] + S[4]*dE[4] + S[5]*dE[5]))


def elastic(S, T):
    E, nu = sm.E_of_T(T), sm.NU
    return [(S[0] - nu*(S[1]+S[2]))/E, (S[1] - nu*(S[0]+S[2]))/E, (S[2] - nu*(S[0]+S[1]))/E,
            (1+nu)*S[3]/E, (1+nu)*S[4]/E, (1+nu)*S[5]/E]


def energies(data, temps, elems, t0, t1):
    """Return the production value and three independent ones, volume-averaged."""
    vols = {e: d["V"] for per in data.values() for e, d in per.items() if "V" in d}
    acc = {k: 0.0 for k in ("prod", "indep_trap", "indep_mid", "indep_simpson")}
    den = 0.0
    for e in elems:
        rows = []
        for t in sorted(data):
            d = data[t].get(e)
            if d and all(k in d for k in ("S", "E", "ME", "P")):
                rows.append((t, temps.get(t, 25.0), d["S"], d["E"], d["ME"], d["P"]))
        w = [r for r in rows if t0 - 1e-9 < r[0] <= t1 + 1e-9]
        if len(w) < 3:
            continue
        v = vols.get(e, 1.0)
        # PRODUCTION: inelastic reconstructed from TOTAL strain with a Python thermal term
        inel_p = [np.array(decompose(r[2], r[3], r[1])[2]) for r in w]
        # INDEPENDENT: inelastic from the solver's OWN mechanical strain; no thermal term
        inel_i = [np.array(r[4]) - np.array(elastic(r[2], r[1])) for r in w]
        Ss = [np.array(r[2]) for r in w]
        wp = sum(ddot(0.5*(Ss[k-1]+Ss[k]), inel_p[k]-inel_p[k-1]) for k in range(1, len(w)))
        wt = sum(ddot(0.5*(Ss[k-1]+Ss[k]), inel_i[k]-inel_i[k-1]) for k in range(1, len(w)))
        wm = sum(ddot(Ss[k-1], inel_i[k]-inel_i[k-1]) for k in range(1, len(w)))
        # Simpson over pairs of intervals where the count allows; trapezoid on any remainder
        ws = 0.0
        k = 1
        while k + 1 < len(w):
            dE = inel_i[k+1] - inel_i[k-1]
            ws += ddot((Ss[k-1] + 4.0*Ss[k] + Ss[k+1]) / 6.0, dE)
            k += 2
        while k < len(w):
            ws += ddot(0.5*(Ss[k-1]+Ss[k]), inel_i[k]-inel_i[k-1]); k += 1
        acc["prod"] += wp*v; acc["indep_trap"] += wt*v
        acc["indep_mid"] += wm*v; acc["indep_simpson"] += ws*v
        den += v
    return {k: (x/den if den else float("nan")) for k, x in acc.items()}, den


def build_deck(tag, model, arch, dt0, dtmax, freq, cetol):
    a = RP.ARCH[arch]
    tmin, tmax, du = RP.T_OFF, a["t_hot"], a["du"]
    m = build_joint_graded(6, 6)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", tmax, du/1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", tmin, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, RP.material(model), cyc, t_ref_c=tmin, cetol=cetol, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", f"*VISCO, CETOL={cetol:g}", s)
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % DWELL,
               f"{dt0:g}, {DWELL:g}, 1e-14, {dtmax:g}", s, flags=re.M)
    # ask the solver for the MECHANICAL strain as well, so the audit needs no thermal model
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  f"*EL PRINT, ELSET=ESYED, FREQUENCY={freq}\nPEEQ, EVOL, S, E, ME")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E", "*NODE PRINT, NSET=NBOT\nNT")
    ids = m.sets["ESYED"]
    blk = ["*ELSET, ELSET=ESYED"] + [", ".join(map(str, ids[i:i+8]))
                                     for i in range(0, len(ids), 8)]
    s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    return p, set(ids), ends


def temps_from(dat: Path):
    """Use the PRODUCTION temperature parser.

    An earlier version of this audit rolled its own parser, which averaged the wrong node set
    and returned 37.83/11.42 C for a cycle that actually runs 82.86/25.00 C. Fed into
    decompose(), that wrong temperature produced a spurious VOLUMETRIC inelastic strain and made
    the production energy look 8.8 % low. The production parser is correct -- the temperature it
    returns reproduces the solver's own thermal strain (E - ME) exactly -- so the audit must use
    it rather than compete with it. The independent arm of the comparison stays independent by
    using the solver's ME directly, which needs no temperature at all.
    """
    from decompose import parse_temperature
    return parse_temperature(dat)


def main() -> int:
    CASES = [
        # tag,           dt0,    dtmax, freq, cetol   -- what is being refined
        ("base",        1e-5,   10.0,   1,   5e-2),   # the pre-0L production control
        ("tight",       1e-8,   10.0,   1,   5e-2),   # the Phase-0L control
        ("dtmax_5",     1e-8,    5.0,   1,   5e-2),   # time-step refinement
        ("dtmax_2",     1e-8,    2.0,   1,   5e-2),
        ("dtmax_1",     1e-8,    1.0,   1,   5e-2),
        ("cetol_1e3",   1e-8,    2.0,   1,   1e-3),   # tolerance refinement
        ("freq_2",      1e-8,    1.0,   2,   5e-2),   # OUTPUT-frequency coarsening
        ("freq_4",      1e-8,    1.0,   4,   5e-2),
    ]
    model, arch = "M1", "Z1"
    rows = []
    print(f"{'case':>11} {'dt_max':>7} {'freq':>5} {'CETOL':>7} {'n_out':>6} "
          f"{'W prod':>10} {'W indep':>10} {'prod/indep':>11} {'mid':>10} {'Simpson':>10} "
          f"{'dPEEQ':>10}")
    for tag, dt0, dtmax, freq, cetol in CASES:
        p, ids, ends = build_deck(f"E_{tag}", model, arch, dt0, dtmax, freq, cetol)
        t0 = time.time()
        run_ccx(p, threads=6)
        dat = WD / f"E_{tag}.dat"
        if not (dat.is_file() and dat.stat().st_size > 5000):
            print(f"{tag:>11}   SOLVER FAILED"); continue
        data = parse(dat, ids)
        temps = temps_from(dat)
        te = ends[STAB-1]
        en, den = energies(data, temps, ids, te - 2*DWELL, te)
        # dPEEQ for the same window, volume-averaged
        vols = {e: d["V"] for per in data.values() for e, d in per.items() if "V" in d}
        num = 0.0
        for e in ids:
            ts = [t for t in sorted(data) if te - 2*DWELL - 1e-9 < t <= te + 1e-9
                  and e in data[t] and "P" in data[t][e]]
            if len(ts) >= 3:
                num += (data[ts[-1]][e]["P"] - data[ts[0]][e]["P"]) * vols.get(e, 1.0)
        dpeeq = num / den if den else float("nan")
        nout = len([t for t in data if te - 2*DWELL - 1e-9 < t <= te + 1e-9])
        r = dict(case=tag, dt0=dt0, dt_max=dtmax, output_frequency=freq, cetol=cetol,
                 n_output_points_in_cycle=nout, W_production=en["prod"],
                 W_independent_trapezoid=en["indep_trap"], W_independent_midpoint=en["indep_mid"],
                 W_independent_simpson=en["indep_simpson"],
                 prod_over_indep=en["prod"]/en["indep_trap"] if en["indep_trap"] else float("nan"),
                 d_peeq_per_cycle=dpeeq, wall_s=time.time()-t0)
        rows.append(r)
        print(f"{tag:>11} {dtmax:7.1f} {freq:5d} {cetol:7.0e} {nout:6d} "
              f"{en['prod']:10.5f} {en['indep_trap']:10.5f} {r['prod_over_indep']:11.6f} "
              f"{en['indep_mid']:10.5f} {en['indep_simpson']:10.5f} {dpeeq:10.6f}")
        for ext in (".frd", ".12d"):
            f = WD / f"E_{tag}{ext}"
            if f.is_file():
                f.unlink()
    p = OUT / "energy_integration_convergence.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
