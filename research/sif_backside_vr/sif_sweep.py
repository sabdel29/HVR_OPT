#!/usr/bin/env python3
"""Si-IF backside VR study -- design-space sweep (current density x cell count x topology).

For V_in (48 or 12 V) -> V_out = 1 V at I_total = 1000 A, the system is M identical cells of
I_cell = 1000 / M, each a converter of the engine's family (plus the plain buck), all parts of a
cell side by side in ONE tier of the square cell of area I_cell / J_t on the wafer backside, so
J_t is the system current density (A per mm^2 of backside). For every (M, topology) the loss
table over (inductor, capacitor, HS body, LS body, f_sw) is built once (sif_core.build_table) and
scanned in ascending loss for every (packing mode, keep-out, J_t): the first entry that places is
the minimum-loss feasible design of that (M, topology, J_t). The reducer keeps, at every J_t,
the minimum total loss M * P_cell over all M and topologies.

Packing modes: "power"    N HS + K LS + K inductors + (N - 1) flying capacitors (engine parts)
               "overhead" plus ceil((N + K) / 2) half-bridge gate drivers (1.6 x 1.6 mm, the
                          uP1966E row of the EPC table), one 0402 bootstrap capacitor per HS
                          switch and two 0805 input capacitors per cell

    python sif_sweep.py --vin 48 --tag v48 [--procs 16]
Outputs (this folder): sweep_<tag>_cells.csv (best per J_t, mode, keep-out, M, topology),
sweep_<tag>_best.csv (best per J_t, mode, keep-out) and sweep_<tag>_best.json (full records).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import sif_core as S  # noqa: E402

I_TOTAL, V_OUT = 1000.0, 1.0
J_GRID = [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7,
          0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.4, 1.5, 1.6, 1.75, 2.0,
          2.25, 2.5, 3.0]
M_GRID = [4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40, 45, 50, 56, 63, 71,
          80, 90, 100, 112, 125, 140, 160, 180, 200, 250]
KO_UM = [50.0, 100.0, 200.0]
# f_sw: the engine's grid (43 kHz - 200 MHz, 50 log points) below 3 MHz, refined with a
# 1.1-ratio log grid from 100 kHz to 3 MHz; each inductor's f_max caps it further
F_ENGINE = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)
F_GRID = np.unique(np.round(np.concatenate([
    F_ENGINE[(F_ENGINE >= 0.1e6) & (F_ENGINE <= 3.0e6 * 1.0001)],
    np.logspace(np.log10(0.1e6), np.log10(3.0e6), 37)]), 1))
DRIVER = S.SimplePart("uP1966E-halfbridge-driver", 1.6, 1.6, 650.0)
CBOOT = S.SimplePart("0402-bootstrap", 1.0, 0.5, 650.0)
CIN = {48.0: S.SimplePart("GRM21BD72A225KE01-input", 2.0, 1.25, 1450.0),
       12.0: S.SimplePart("GRM21BC71E106KE01-input", 2.0, 1.25, 1450.0)}

_G = {}


def overhead_parts(arch, V_in):
    return ((math.ceil((arch.N + arch.K) / 2), DRIVER), (arch.N, CBOOT), (2, CIN[V_in]))


def mode_spec(mode, arch, V_in):
    """(extra parts, cell shape) of a packing mode: "power" (engine parts, square cell),
    "overhead" (plus drivers and decoupling, square), "rect" (engine parts, rectangular cell
    with aspect ratio up to S.ASPECT_MAX)."""
    if mode == "overhead":
        return overhead_parts(arch, V_in), "square"
    if mode == "rect":
        return (), "rect"
    return (), "square"


def cell_fits(cd, I_cell, J, shape):
    if shape == "rect":
        return S.fits_area(cd, I_cell / J)
    return S.fits_one_tier(cd, math.sqrt(I_cell / J))


def cell_min_area(cd, shape):
    """(minimum cell area mm^2, W, H) for the shape."""
    if shape == "rect":
        return S.min_rect(cd)
    s_ = S.min_side(cd)
    return s_ * s_, s_, s_


def _init(args_dict):
    os.nice(0)
    df, epc_price = S.load_devices()
    inds = S.build_inductor_library(args_dict["ind_lib"], dcr=args_dict["dcr"],
                                    isat=args_dict.get("isat", "vendor"))
    if args_dict.get("series"):
        keep = set(args_dict["series"].split(","))
        inds = [i for i in inds if i.series in keep]
    caps = S.build_capacitor_library()
    _G.update(df=df, inds=inds, caps=caps, args=args_dict,
              opts=S.Opts(peak_isat=args_dict["peak_isat"], irms=args_dict["irms"],
                          core_loss=args_dict["core_loss"],
                          ton_min_ns=args_dict.get("ton_min_ns", 0.0),
                          core_scale=args_dict.get("core_scale", 1.0)))


class Scanner:
    """Entries of one table in ascending loss, with their part bodies, for the placement scan."""

    def __init__(self, t):
        self.t = t
        a = t.arch
        L = t.loss
        flat = np.flatnonzero(np.isfinite(L))
        order = flat[np.argsort(L.flat[flat], kind="stable")]
        self.ii, self.jj, self.gh, self.gl = np.unravel_index(order, L.shape)
        self.loss = L.flat[order]
        hd = np.array([sorted(k) for k in t.hkeys])        # (min, max)
        ld = np.array([sorted(k) for k in t.lkeys])
        idm = np.array([sorted(S.H.part_dims_mm(i)) for i in t.inds])
        cdm = np.array([sorted(S.H.part_dims_mm(c)) for c in t.caps])
        self.dims = (hd, ld, idm, cdm)
        self.counts = (a.N, a.K, a.K, a.N - 1)

    def area_and_maxdim(self, ko_mm, extra):
        hd, ld, idm, cdm = self.dims
        nh, nl, ni, nc = self.counts
        ar = lambda d: (d[:, 0] + ko_mm) * (d[:, 1] + ko_mm)      # noqa: E731
        ea = sum(n * (p.pkg_x_mm + ko_mm) * (p.pkg_y_mm + ko_mm) for n, p in extra)
        em = max([max(p.pkg_x_mm, p.pkg_y_mm) + ko_mm for n, p in extra] or [0.0])
        area = (nh * ar(hd)[self.gh] + nl * ar(ld)[self.gl] + ni * ar(idm)[self.ii]
                + (nc * ar(cdm)[self.jj] if nc > 0 else 0.0) + ea)
        mx = np.maximum.reduce([hd[self.gh, 1], ld[self.gl, 1], idm[self.ii, 1]]
                               + ([cdm[self.jj, 1]] if nc > 0 else [])) + ko_mm
        return area, np.maximum(mx, em)

    def classes(self, k, ko_mm, extra):
        t = self.t
        hs_d = t.hkeys[self.gh[k]]
        ls_d = t.lkeys[self.gl[k]]
        cls = {}
        nh, nl, ni, nc = self.counts
        bodies = [(nh, hs_d), (nl, ls_d), (ni, S.H.part_dims_mm(t.inds[self.ii[k]])),
                  (nc, S.H.part_dims_mm(t.caps[self.jj[k]]))]
        bodies += [(n, (p.pkg_x_mm, p.pkg_y_mm)) for n, p in extra]
        for n, (x, y) in bodies:
            if n <= 0:
                continue
            d = (round(max(x, y) + ko_mm, 9), round(min(x, y) + ko_mm, 9))
            cls[d] = cls.get(d, 0) + n
        return tuple(sorted(cls.items()))


def scan_all(sc, I_cell, V_in, modes, kos, J_list, max_checks=200000):
    """Best entry index per (mode, ko, J): J ascending, the scan resumes where the previous
    (lower) J stopped -- an entry that does not place in a larger cell does not place in a
    smaller one (area and length bounds are monotone; the placement test is taken as such)."""
    out = {}
    for mode in modes:
        extra, shape = mode_spec(mode, sc.t.arch, V_in)
        for ko in kos:
            ko_mm = ko * 1e-3
            area, mx = sc.area_and_maxdim(ko_mm, extra)
            start = 0
            for J in sorted(J_list):
                A = I_cell / J
                lmax = math.sqrt(A * S.ASPECT_MAX) if shape == "rect" else math.sqrt(A)
                ok = np.flatnonzero((area[start:] <= A + 1e-9)
                                    & (mx[start:] <= lmax + 1e-9)) + start
                found, checks = None, 0
                for k in ok:
                    checks += 1
                    if cell_fits(sc.classes(k, ko_mm, extra), I_cell, J, shape):
                        found = int(k)
                        break
                    if checks >= max_checks:
                        break
                out[(mode, ko, J)] = (found, checks, checks >= max_checks and found is None)
                if found is None:
                    start = len(sc.loss)          # nothing places at this J: none at higher J
                else:
                    start = found
    return out


def density_scan(sc, I_cell, ko_mm, extra, shape="square", max_geoms=4000):
    """Largest current density at which ANY entry of the table places (one tier): over the
    distinct part-body combinations in decreasing order of their area/length bound, the
    smallest placeable square side by bisection (sif_core.min_side), until the bound falls
    below the best density found. Returns (J_max, entry index of a geometry achieving it)."""
    t = sc.t
    inds_d = [tuple(sorted(S.H.part_dims_mm(i))) for i in t.inds]
    caps_d = [tuple(sorted(S.H.part_dims_mm(c))) for c in t.caps]
    uid = {d: n for n, d in enumerate(sorted(set(inds_d)))}
    ucd = {d: n for n, d in enumerate(sorted(set(caps_d)))}
    idim = np.array([uid[d] for d in inds_d])[sc.ii]
    cdim = (np.array([ucd[d] for d in caps_d])[sc.jj] if sc.counts[3] > 0
            else np.zeros(len(sc.ii), dtype=int))
    geo = np.stack([sc.gh, sc.gl, idim, cdim], axis=1)
    _, first = np.unique(geo, axis=0, return_index=True)      # first = lowest-loss entry
    area, mx = sc.area_and_maxdim(ko_mm, extra)
    lb = mx[first] ** 2 / (S.ASPECT_MAX if shape == "rect" else 1.0)
    jub = I_cell / np.maximum(area[first], lb)
    best_J, best_k, n = 0.0, None, 0
    for g in np.argsort(-jub, kind="stable"):
        if jub[g] <= best_J * (1 + 1e-9) or n >= max_geoms:
            break
        n += 1
        k = int(first[g])
        a_min = cell_min_area(sc.classes(k, ko_mm, extra), shape)[0]
        if np.isfinite(a_min) and I_cell / a_min > best_J:
            best_J, best_k = I_cell / a_min, k
    return best_J, best_k, n


def achieved(sc, k, ko_mm, extra, shape="square"):
    """Smallest cell of entry k: (area mm^2, W, H) and its part classes."""
    cd = sc.classes(k, ko_mm, extra)
    return cell_min_area(cd, shape), cd


def design_record(sc, k, V_in, M, mode, ko, J):
    t = sc.t
    ii, jj, gh, gl = int(sc.ii[k]), int(sc.jj[k]), int(sc.gh[k]), int(sc.gl[k])
    fi = int(t.fidx[ii, jj, gh, gl])
    hs = t.hs[int(t.ah[ii][fi, gh])]
    ls = t.ls[int(t.al[ii][fi, gl])]
    ind, cap, f = t.inds[ii], t.caps[jj], float(t.fgrid[fi])
    a = t.arch
    ev = S.evaluate(a, hs, ls, ind, cap, t.I, V_in, V_OUT, f, _G["opts"])
    assert abs(ev["loss_cell_W"] - float(sc.loss[k])) <= 1e-7 * max(1.0, ev["loss_cell_W"]), \
        (ev["loss_cell_W"], float(sc.loss[k]))
    P_loss = M * ev["loss_cell_W"]
    rec = {
        "V_in": V_in, "mode": mode, "keepout_um": ko, "J_target": J, "M": M,
        "I_cell_A": t.I, "N": a.N, "K": a.K, "K_A": a.K_A, "B": list(a.B_array), "D": a.D,
        "topology": "buck" if a.N == 1 else f"N{a.N}K{a.K}KA{a.K_A}",
        "hs": hs.part_number, "ls": ls.part_number, "inductor": ind.name,
        "ind_L_nH": ind.l_nh, "ind_DCR_mohm": ind.r_dcr_mohm, "ind_Isat_A": ind.i_sat_a,
        "ind_Irms_A": ind.i_rms_a, "ind_dims_mm": [ind.pkg_x_mm, ind.pkg_y_mm, ind.height_um / 1e3],
        "capacitor": cap.name if a.N > 1 else "", "f_sw_Hz": f,
        "cell_area_mm2": t.I / J,
        "loss_cell_W": ev["loss_cell_W"], "loss_total_W": P_loss,
        "efficiency": I_TOTAL * V_OUT / (I_TOTAL * V_OUT + P_loss),
        "breakdown_total_W": {k2: M * v for k2, v in ev["breakdown_cell_W"].items()},
    }
    rec.update({k2: v for k2, v in ev.items() if k2 not in ("breakdown_cell_W",)})
    extra, shape = mode_spec(mode, a, V_in)
    (a_min, w_min, h_min), cd = achieved(sc, k, ko * 1e-3, extra, shape)
    rec["cell_shape"] = shape
    rec["cell_min_area_mm2"] = a_min
    rec["cell_min_WH_mm"] = [w_min, h_min]
    rec["J_achieved"] = t.I / a_min
    rec["parts_per_cell"] = {"hs": a.N, "ls": a.K, "inductor": a.K, "cap_fly": a.N - 1,
                             **({p.name: n for n, p in extra} if extra else {})}
    rec["placement_classes_mm"] = [[list(d), c] for d, c in cd]
    # which parts each placement class (body grown by the keep-out) holds
    ko_mm = ko * 1e-3
    bodies = [("HS " + hs.part_number, a.N, S.H.part_dims_mm(hs)),
              ("LS " + ls.part_number, a.K, S.H.part_dims_mm(ls)),
              ("L " + ind.name, a.K, S.H.part_dims_mm(ind)),
              ("C " + cap.name, a.N - 1, S.H.part_dims_mm(cap))]
    bodies += [(p_.name, n_, (p_.pkg_x_mm, p_.pkg_y_mm)) for n_, p_ in extra]
    cls_parts = []
    for d, c in cd:
        names = [f"{nm} x{n_}" for nm, n_, (x, y) in bodies if n_ > 0 and
                 (round(max(x, y) + ko_mm, 9), round(min(x, y) + ko_mm, 9)) == tuple(d)]
        cls_parts.append(names)
    rec["placement_class_parts"] = cls_parts
    pl = S.place_rect(cd, w_min, h_min) if np.isfinite(a_min) else None
    rec["placement_verified"] = bool(S.verify_placement(pl, cd, w_min + 1e-9, h_min + 1e-9))
    rec["placement_mm"] = ([[round(v, 4) for v in p_[:4]] + [int(p_[4])] for p_ in pl]
                           if pl is not None else None)
    return rec


def run_task(arg):
    """One (V_in, M, topology): build the loss table once, scan it for every scan set
    [(mode, keep-outs)]."""
    task, scan_sets = arg
    V_in, M, ai = task
    t0 = time.time()
    a = S.architectures(V_in, V_OUT, _G["args"]["nmax"])[ai]
    I_cell = I_TOTAL / M
    t = S.build_table(a, I_cell, V_in, V_OUT, _G["df"], _G["inds"], _G["caps"], F_GRID, _G["opts"])
    rows = []
    if t is None or t.n_valid_f == 0:
        return rows, (V_in, M, ai, round(time.time() - t0, 1), 0)
    sc = Scanner(t)
    if len(sc.loss) == 0:
        return rows, (V_in, M, ai, round(time.time() - t0, 1), 0)
    for mode, kos in scan_sets:
        res = scan_all(sc, I_cell, V_in, [mode], kos, _G["args"]["J"])
        for (md, ko, J), (k, checks, trunc) in res.items():
            if k is None:
                continue
            r = design_record(sc, k, V_in, M, md, ko, J)
            r["scan_checks"], r["scan_truncated"], r["kind"] = checks, trunc, "grid"
            rows.append(r)
        for ko in kos:
            extra, shape = mode_spec(mode, a, V_in)
            jmax, kg, ngeo = density_scan(sc, I_cell, ko * 1e-3, extra, shape)
            if kg is None:
                continue
            j_eval = jmax * (1 - 1e-7)                 # the loss scan at J_max (just inside)
            r2 = scan_all(sc, I_cell, V_in, [mode], [ko], [j_eval])[(mode, ko, j_eval)]
            k = r2[0] if r2[0] is not None else kg
            r = design_record(sc, k, V_in, M, mode, ko, jmax)
            r["scan_checks"], r["scan_truncated"], r["kind"] = r2[1], r2[2], "jmax"
            r["density_scan_geometries"] = ngeo
            rows.append(r)
    return rows, (V_in, M, ai, round(time.time() - t0, 1), len(sc.loss))


FLAT_KEYS = ["kind", "V_in", "mode", "keepout_um", "J_target", "J_achieved", "cell_shape", "M", "I_cell_A", "topology", "N", "K",
             "K_A", "D", "hs", "ls", "inductor", "ind_L_nH", "ind_DCR_mohm", "ind_Isat_A",
             "ind_Irms_A", "capacitor", "f_sw_Hz", "cell_area_mm2", "loss_cell_W",
             "loss_total_W", "efficiency", "dI_L_pp_A", "I_L_pk_A", "I_L_rms_A", "t_on_ns",
             "flying_cap_ripple_frac"]
BR_KEYS = ["cond_hs_W", "cond_ls_W", "cond_ind_dcr_W", "cond_cap_esr_W", "sw_overlap_W",
           "gate_W", "coss_W", "ind_core_W"]


def flat(r):
    d = {k: r.get(k) for k in FLAT_KEYS}
    d.update({k: r["breakdown_total_W"][k] for k in BR_KEYS})
    return d


def _pareto_candidates(rows):
    """Non-dominated (J_achieved up, loss down) records per (mode, keep-out)."""
    out = []
    for key in sorted({(r["mode"], r["keepout_um"]) for r in rows}):
        rr = sorted((r for r in rows if (r["mode"], r["keepout_um"]) == key),
                    key=lambda r: (-r["J_achieved"], r["loss_total_W"]))
        best = float("inf")
        for r in rr:
            if r["loss_total_W"] < best - 1e-12:
                out.append(r)
                best = r["loss_total_W"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vin", type=float, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--nmax", type=int, default=0, help="max N (default 8 at 48 V, 5 at 12 V)")
    ap.add_argument("--M", default=",".join(map(str, M_GRID)))
    ap.add_argument("--J", default=",".join(map(str, J_GRID)))
    ap.add_argument("--ko", default=",".join(f"{k:g}" for k in KO_UM))
    ap.add_argument("--modes", default="power,overhead,rect")
    ap.add_argument("--chunk", type=int, default=8, help="consecutive M of one topology per worker")
    ap.add_argument("--overhead-ko", type=float, default=100.0,
                    help="the overhead and rect modes run at this keep-out only")
    ap.add_argument("--ind-lib", default=os.path.join(HERE, "inductor_library.json"))
    ap.add_argument("--series", default="", help="restrict to these inductor series")
    ap.add_argument("--dcr", default="max", choices=["max", "typ"])
    ap.add_argument("--isat", default="vendor", choices=["vendor", "20"])
    ap.add_argument("--no-peak-isat", action="store_true")
    ap.add_argument("--no-irms", action="store_true")
    ap.add_argument("--no-core-loss", action="store_true")
    ap.add_argument("--ton-min-ns", type=float, default=0.0)
    ap.add_argument("--core-scale", type=float, default=1.0)
    args = ap.parse_args()
    nmax = args.nmax or (8 if args.vin >= 24 else 5)
    ad = dict(nmax=nmax, M=[int(x) for x in args.M.split(",")],
              J=[float(x) for x in args.J.split(",")], kos=[float(x) for x in args.ko.split(",")],
              modes=args.modes.split(","), ind_lib=args.ind_lib, series=args.series, dcr=args.dcr,
              isat=args.isat,
              peak_isat=not args.no_peak_isat, irms=not args.no_irms,
              core_loss=not args.no_core_loss, ton_min_ns=args.ton_min_ns,
              core_scale=args.core_scale)
    archs = S.architectures(args.vin, V_OUT, nmax)
    tasks = [(args.vin, M, ai) for M in ad["M"] for ai in range(len(archs))]
    # topology-major (heavier first), M consecutive: a worker gets consecutive M of one topology
    # and reuses its cached placement results (the geometry does not depend on the current)
    tasks.sort(key=lambda t: (-(archs[t[2]].N + archs[t[2]].K), t[2], t[1]))
    print(f"V_in={args.vin} archs={len(archs)} ({[('buck' if a.N == 1 else (a.N, a.K)) for a in archs]})"
          f" M={len(ad['M'])} tasks={len(tasks)} f_grid={len(F_GRID)} pts "
          f"[{F_GRID[0]/1e6:.3f}-{F_GRID[-1]/1e6:.3f} MHz]", flush=True)
    rows, t0 = [], time.time()
    scan_sets = ([("power", ad["kos"])] if "power" in ad["modes"] else []) + \
                ([("overhead", [args.overhead_ko])] if "overhead" in ad["modes"] else []) + \
                ([("rect", [args.overhead_ko])] if "rect" in ad["modes"] else [])
    with mp.Pool(args.procs, initializer=_init, initargs=(ad,)) as pool:
        done = 0
        for rr, info in pool.imap_unordered(run_task, [(t, scan_sets) for t in tasks],
                                            chunksize=args.chunk):
            rows.extend(rr)
            done += 1
            if done % 25 == 0 or done == len(tasks):
                print(f"  {done}/{len(tasks)} tasks, {len(rows)} rows, {time.time()-t0:.0f} s; "
                      f"last {info}", flush=True)
    best = {}
    for r in rows:
        if r.get("kind") != "grid":
            continue
        key = (r["mode"], r["keepout_um"], r["J_target"])
        if key not in best or r["loss_total_W"] < best[key]["loss_total_W"]:
            best[key] = r
    with open(os.path.join(HERE, f"sweep_{args.tag}_cells.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FLAT_KEYS + BR_KEYS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["mode"], r["keepout_um"], r["J_target"], r["M"],
                                             r["N"], r["K"])):
            w.writerow(flat(r))
    with open(os.path.join(HERE, f"sweep_{args.tag}_best.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FLAT_KEYS + BR_KEYS)
        w.writeheader()
        for key in sorted(best):
            w.writerow(flat(best[key]))
    meta = {"V_in": args.vin, "V_out": V_OUT, "I_total": I_TOTAL, "nmax": nmax,
            "architectures": [("buck" if a.N == 1 else f"N{a.N}K{a.K}KA{a.K_A}") for a in archs],
            "M": ad["M"], "J": ad["J"], "keepout_um": ad["kos"], "modes": ad["modes"],
            "overhead_keepout_um": args.overhead_ko, "f_grid_Hz": F_GRID.tolist(),
            "engine_env": S.ENGINE_ENV, "opts": {k: ad[k] for k in ("peak_isat", "irms",
                                                                    "core_loss", "dcr", "isat",
                                                                    "ton_min_ns", "core_scale")},
            "inductor_library": os.path.basename(args.ind_lib), "series": args.series,
            "n_inductors": None, "runtime_s": time.time() - t0}
    json.dump({"meta": meta, "best": [best[k] for k in sorted(best)],
               "jmax": [r for r in rows if r.get("kind") == "jmax"],
               "pareto_candidates": _pareto_candidates(rows)},
              open(os.path.join(HERE, f"sweep_{args.tag}_best.json"), "w"), indent=1,
              default=float)
    print("wrote", f"sweep_{args.tag}_*.csv/json", f"{time.time()-t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
