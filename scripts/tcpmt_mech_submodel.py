"""Local interconnect submodel, v2 -- the production local model after the round-3 review.

Against the Phase-0I/0I-R harness (joint.write_inp, run_final_local_response, the step
patcher of final_closure_local_mesh) four things change, each configurable in
configs/tcpmt_mech/mechanics_revision.yaml (section `local`):

1. LAW (finding 1). The card comes from tcpmt_mech_laws: a zero-yield law (the solver
   integrates the applied von Mises stress it was fitted in), the production law's Norton
   surrogate refitted over the visited window. 'legacy' reproduces the round-2 card.
2. BOUNDARY CONDITIONS (finding 2). bc = 'global': both pad faces follow the global cut-
   boundary displacement field of their own surface at the site -- translation, in-plane
   stretch and shear, rotation -- linearised over the pad footprint
   (tcpmt_mech_kinematics). The frame is turned so that the in-plane du lies along local +x,
   as the legacy model imposed it (the equal-area square prism would otherwise see an
   artificial diagonal load). bc = 'uz': the legacy in-plane load with u_z of the top face
   released to the global du_z. bc = 'legacy': both faces at u_z = 0, |du_xy| on x, the top
   face pinned in y -- the round-1/2 model.
3. LOADING (finding 3). Every load change is a linear ramp (*STEP, AMPLITUDE=RAMP: CalculiX
   applies *VISCO loads as STEP functions by default, verified by probe) of ramp_s, followed by
   a dwell of dwell_s. ramp_s = 0 reproduces the legacy schedule (STEP load in a 3-s step,
   hold to 300 s).
4. GEOMETRY / ELEMENT (findings 4, 11). The joint is any pad / solder / (Cu post) / pad
   column of the configured geometries; element C3D8, C3D8I or C3D8R.

The extraction is the block-order one of final_closure_local_extract (DEFECT #65), with the
half-cycle = ramp_s + dwell_s; the response is d_peeq_per_cycle over the solder core
(fixed-width band of local_mesh_policy amendment 5).

    python tcpmt_mech_submodel.py --selftest     reproduce one legacy solve with v2
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0i", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import tcpmt_mech_laws as LAW                                       # noqa: E402
import final_closure_local_extract as X                             # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402

POLICY = json.loads((R / "research" / "final_closure" / "local_mesh_policy.json").read_text())
LEVELS = POLICY["levels"]
BAND_FRAC = float(next(a for a in POLICY["amendments"] if a.get("id") == 5)["band_frac"])
ROOT = "mech"
CCX = os.environ.get("CCX", "ccx")
SLOTS = int(os.environ.get("TCPMT_SOLDER_SLOTS", "3"))
THREADS = int(os.environ.get("LOCAL_THREADS", "2"))
QS = (0.05, 0.25, 0.50, 0.75, 0.95)


def lcfg() -> dict:
    return LAW.cfg()["local"]


def geometry(name: str) -> dict:
    return dict(LAW.cfg()["geometries"][name])


# --------------------------------------------------------------------------- mesh
class JointMesh:
    def __init__(self, nodes, elems, sets, unit):
        self.nodes, self.elems, self.sets, self.unit = nodes, elems, sets, unit

    @property
    def n_nodes(self):
        return len(self.nodes)


def _grid(lo, hi, n):
    return np.linspace(lo, hi, n + 1)


def build_mesh(geom: dict, n_xy=6, n_z_solder=8, n_z_pad=1, n_z_post=None,
               band_frac=BAND_FRAC, unit="mm") -> JointMesh:
    """pad / solder / (Cu post) / pad, the solder an equal-area square prism inset in the
    pads. For the BGA geometry (no post, mm) this is joint.build_joint node for node."""
    k = 1e-3 if unit == "mm" else 1.0                     # deck length per um
    hp, hs = float(geom["pad"]) / 2 * k, math.sqrt(math.pi / 4) * float(geom["solder_d"]) / 2 * k
    tp, hsol = float(geom["pad_t"]) * k, float(geom["solder_h"]) * k
    hpost = float(geom.get("cu_post_h") or 0.0) * k
    if not hp > hs:
        raise ValueError("the pad must overhang the solder")
    n_in = max(2, n_xy)
    n_out = max(1, n_xy // 3)
    b = band_frac * 2 * hs
    dx0 = 2 * hs / n_in
    n_b = max(1, int(np.ceil(b / dx0 - 1e-9)))
    n_c = max(2, int(round((2 * hs - 2 * b) / dx0)))
    xs = np.unique(np.concatenate([_grid(-hp, -hs, n_out), _grid(-hs, -hs + b, n_b),
                                   _grid(-hs + b, hs - b, n_c), _grid(hs - b, hs, n_b),
                                   _grid(hs, hp, n_out)]))
    ys = xs.copy()
    segs = [_grid(0.0, tp, n_z_pad), _grid(tp, tp + hsol, n_z_solder)]
    z_post0 = tp + hsol
    if hpost > 0:
        npz = n_z_post or max(1, int(round(n_z_solder * hpost / hsol)))
        segs.append(_grid(z_post0, z_post0 + hpost, npz))
    segs.append(_grid(z_post0 + hpost, z_post0 + hpost + tp, n_z_pad))
    zs = np.unique(np.concatenate(segs))
    nx, ny, nz = len(xs), len(ys), len(zs)
    nid = np.arange(1, nx * ny * nz + 1).reshape(nx, ny, nz)
    pts = np.zeros((nx * ny * nz, 3))
    for i in range(nx):
        for j in range(ny):
            for kk in range(nz):
                pts[nid[i, j, kk] - 1] = (xs[i], ys[j], zs[kk])
    elems, eid = [], 0
    for i in range(nx - 1):
        for j in range(ny - 1):
            xc, yc = .5 * (xs[i] + xs[i + 1]), .5 * (ys[j] + ys[j + 1])
            inside = abs(xc) < hs - 1e-12 and abs(yc) < hs - 1e-12
            for kk in range(nz - 1):
                zc = .5 * (zs[kk] + zs[kk + 1])
                if zc < tp:
                    s = "EPADB"
                elif zc < tp + hsol:
                    if not inside:
                        continue
                    s = "ESOL"
                elif zc < z_post0 + hpost:
                    if not inside:
                        continue
                    s = "ECUP"
                else:
                    s = "EPADT"
                eid += 1
                c = [nid[i, j, kk], nid[i + 1, j, kk], nid[i + 1, j + 1, kk], nid[i, j + 1, kk],
                     nid[i, j, kk + 1], nid[i + 1, j, kk + 1], nid[i + 1, j + 1, kk + 1],
                     nid[i, j + 1, kk + 1]]
                elems.append((eid, c, s))
    used = sorted({n for _, c, _ in elems for n in c})
    remap = {o: i + 1 for i, o in enumerate(used)}
    pts = pts[[o - 1 for o in used]]
    elems = [(e, [remap[n] for n in c], s) for e, c, s in elems]
    zb, zt = zs[0], zs[-1]
    sets = {"NBOT": [i + 1 for i in range(len(pts)) if abs(pts[i, 2] - zb) < 1e-12],
            "NTOP": [i + 1 for i in range(len(pts)) if abs(pts[i, 2] - zt) < 1e-12]}
    lim = hs - band_frac * 2 * hs
    sets["ESOLCORE"] = [e for e, c, s in elems if s == "ESOL"
                        and max(abs(pts[[n - 1 for n in c]].mean(axis=0)[0]),
                                abs(pts[[n - 1 for n in c]].mean(axis=0)[1])) < lim]
    return JointMesh(pts, elems, sets, unit)


# --------------------------------------------------------------------------- boundary
def frame(kin: dict) -> np.ndarray:
    """2x2 rotation global -> local that puts the in-plane du on local +x (of the hot
    state when a cold-state kinematics carries `_frame_du_mm`)."""
    du = np.asarray(kin.get("_frame_du_mm", kin["du_mm"]), float)
    phi = math.atan2(du[1], du[0]) if math.hypot(du[0], du[1]) > 0 else 0.0
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[c, s], [-s, c]])


def bc_values(m: JointMesh, kin: dict, mode: str) -> dict:
    """{node id: (ux, uy, uz)} in deck units at the full (hot) load, for every node of the
    two pad faces. Kinematics are in mm (global solve)."""
    k = 1.0 if m.unit == "mm" else 1e3
    du = np.asarray(kin["du_mm"], float)
    Q = frame(kin)
    R3 = np.eye(3)
    R3[:2, :2] = Q
    out = {}
    if mode in ("legacy", "uz"):
        dz = du[2] * k if mode == "uz" else 0.0
        if "_frame_du_mm" in kin:                 # a cold state in the hot state's frame
            dx, dy = (Q @ du[:2]) * k
        else:
            dx, dy = math.hypot(du[0], du[1]) * k, 0.0
        for n in m.sets["NBOT"]:
            out[n] = (0.0, 0.0, 0.0)
        for n in m.sets["NTOP"]:
            out[n] = (dx, dy, dz)
        return out
    if mode != "global":
        raise ValueError(f"unknown bc mode {mode!r}")
    Gb, Gt = np.asarray(kin["G_bot"], float), np.asarray(kin["G_top"], float)
    for face, G, u0 in (("NBOT", Gb, np.zeros(3)), ("NTOP", Gt, du)):
        for n in m.sets[face]:
            p_l = m.nodes[n - 1, :2] / k                   # local in-plane offset, mm
            p_g = Q.T @ p_l
            u_g = u0 + G @ p_g
            out[n] = tuple(float(v) for v in (R3 @ u_g) * k)
    return out


def site_temperature(kin: dict) -> float:
    v = [t for t in (kin.get("T_bot_C"), kin.get("T_top_C")) if t is not None]
    if not v:
        raise ValueError("kinematics carry no temperature")
    return float(np.mean(v))


# --------------------------------------------------------------------------- schedule
def schedule(T_hot, n_cyc, ramp_s, dwell_s, T_cold):
    """[(label, kind, duration_s, T_C, load_factor)] and the half-cycle length."""
    seg = []
    if ramp_s and ramp_s > 0:
        for k in range(n_cyc):
            seg += [(f"c{k}up", "ramp", ramp_s, T_hot, 1.0),
                    (f"c{k}hot", "dwell", dwell_s, T_hot, 1.0),
                    (f"c{k}down", "ramp", ramp_s, T_cold, 0.0),
                    (f"c{k}cold", "dwell", dwell_s, T_cold, 0.0)]
        return seg, ramp_s + dwell_s
    # legacy: the change as a STEP function inside a 3-s step, then a hold to dwell_s
    for k in range(n_cyc):
        seg += [(f"c{k}on", "step3", 3.0, T_hot, 1.0),
                (f"c{k}onh", "hold", dwell_s - 3.0, T_hot, 1.0),
                (f"c{k}off", "step3", 3.0, T_cold, 0.0),
                (f"c{k}offh", "hold", dwell_s - 3.0, T_cold, 0.0)]
    return seg, dwell_s


def write_deck(m: JointMesh, path: Path, card_text: str, segs, bcv: dict, etype="C3D8",
               cetol=0.05, t_ref=25.0, legacy_inc0=0.002, bcv_cold: dict | None = None) -> str:
    """`bcv` are the hot-state face displacements; `bcv_cold` (finding 6, a static clamp)
    the cold-state ones, imposed instead of zero in every cold half-cycle."""
    cu = lcfg()["copper"]
    inc = lcfg()["increments"]
    L = ["*NODE"] + [f"{i + 1}, {p[0]:.9g}, {p[1]:.9g}, {p[2]:.9g}"
                     for i, p in enumerate(m.nodes)]
    for s in ("EPADB", "ESOL", "ECUP", "EPADT"):
        el = [(e, c) for e, c, ss in m.elems if ss == s]
        if el:
            L.append(f"*ELEMENT, TYPE={etype}, ELSET={s}")
            L += [f"{e}, " + ", ".join(str(n) for n in c) for e, c in el]

    def nset(name, ids, kind="NSET"):
        out = [f"*{kind}, {kind}={name}"]
        for i in range(0, len(ids), 8):
            out.append(", ".join(str(x) for x in ids[i:i + 8]) + ("," if i + 8 < len(ids) else ""))
        return out
    L += nset("ESOLCORE", m.sets["ESOLCORE"], "ELSET")
    L += nset("NBOT", m.sets["NBOT"]) + nset("NTOP", m.sets["NTOP"])
    L += ["*NSET, NSET=NALL, GENERATE", f"1, {m.n_nodes}, 1"]
    L.append(card_text.rstrip())
    L += ["*MATERIAL, NAME=CU", "*ELASTIC", f"{float(cu['E_MPa']):.6g}, {float(cu['nu']):.4g}",
          f"*EXPANSION, ZERO={t_ref:g}", f"{float(cu['cte_per_K']):.6g}",
          "*SOLID SECTION, ELSET=ESOL, MATERIAL=SOLDER"]
    for s in ("EPADB", "ECUP", "EPADT"):
        if any(ss == s for _, _, ss in m.elems):
            L.append(f"*SOLID SECTION, ELSET={s}, MATERIAL=CU")
    L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL, {t_ref:g}", "*BOUNDARY"]
    nodes = sorted(bcv)
    L += [f"{n}, 1, 3" for n in nodes]
    for lab, kind, dur, T, s in segs:
        if kind == "ramp":
            hdr, ctl = "*STEP, INC=20000, AMPLITUDE=RAMP", inc["ramp"]
            dt0, dtmax = min(float(ctl["dt0_s"]), dur / 10), min(float(ctl["dt_max_s"]), dur)
        elif kind == "dwell":
            hdr, ctl = "*STEP, INC=20000", inc["dwell"]
            dt0, dtmax = float(ctl["dt0_s"]), min(float(ctl["dt_max_s"]), dur)
        elif kind == "step3":                    # legacy: STEP amplitude in a 3-s step
            hdr, ctl, dt0, dtmax = "*STEP, INC=5000", {"dt_min_s": 1e-9}, legacy_inc0, 3.0
        else:                                    # legacy hold
            hdr, ctl, dt0, dtmax = "*STEP, INC=5000", {"dt_min_s": 1e-9}, 0.5, 15.0
        L += [f"** ---- {lab}", hdr, f"*VISCO, CETOL={cetol:g}",
              f"{dt0:.6g}, {dur:.6g}, {float(ctl['dt_min_s']):.3g}, {dtmax:.6g}",
              "*TEMPERATURE", f"NALL, {T:.4f}", "*BOUNDARY"]
        for n in nodes:
            v = bcv[n]
            if bcv_cold:
                c = bcv_cold[n]
                L += [f"{n}, {d + 1}, {d + 1}, {s * v[d] + (1.0 - s) * c[d]:.10g}"
                      for d in range(3)]
            else:
                L += [f"{n}, {d + 1}, {d + 1}, {s * v[d]:.10g}" for d in range(3)]
        L += ["*EL PRINT, ELSET=ESOLCORE", "PEEQ, EVOL, S, E",
              "*NODE PRINT, NSET=NBOT", "NT", "*END STEP"]
    text = "\n".join(L) + "\n"
    path.write_text(text)
    return text


def run_ccx(path: Path, threads: int = THREADS, timeout: int = 7200):
    """CalculiX on the deck `path` in its own directory, by its bare stem: CalculiX refuses an
    input-deck name over 127 characters, which an absolute name under the campaign's scratch
    tree exceeds (rc 201, nothing written)."""
    env = {**os.environ, "OMP_NUM_THREADS": str(threads), "OPENBLAS_NUM_THREADS": "1"}
    return subprocess.run([CCX, "-i", path.stem], cwd=path.parent, env=env,
                          capture_output=True, text=True, timeout=timeout)


# --------------------------------------------------------------------------- results
def _vm(s):
    sxx, syy, szz, sxy, sxz, syz = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + sxz ** 2 + syz ** 2))


def stress_stats(incs, vols, n_cyc, half, t_hot, t_cold, qlo=0.05, qhi=0.95):
    """Where the last cycle's inelastic strain is deposited (d PEEQ x V weighting) and
    where the cycle is spent (dt x V), in core von Mises stress, per phase."""
    period = 2 * half
    i0 = X._first_at(incs, (n_cyc - 1) * period)
    if i0 is None:
        return None
    win = incs[i0:]
    ph = {p: ([], [], [], []) for p in ("hot", "cold")}
    peak = {"hot": 0.0, "cold": 0.0}
    for a, b in zip(win, win[1:]):
        p = "hot" if abs(b["T"] - t_hot) < abs(b["T"] - t_cold) else "cold"
        dt = max(0.0, b["t"] - a["t"])
        for e, v in vols.items():
            da, db = a["el"].get(e), b["el"].get(e)
            if not (da and db and "S" in db):
                continue
            s = _vm(db["S"])
            peak[p] = max(peak[p], s)
            if dt > 0:
                ph[p][2].append(s)
                ph[p][3].append(dt * v)
            dp = db["P"] - da["P"]
            if dp > 0:
                ph[p][0].append(s)
                ph[p][1].append(dp * v)
    tot = sum(sum(x[1]) for x in ph.values())
    vt = sum(vols.values())
    qs = (qlo,) + QS + (qhi,)
    names = ("lo",) + tuple(f"q{int(round(100 * q)):02d}" for q in QS) + ("hi",)
    out = {"d_peeq_vol_avg": tot / vt if vt else None,
           "weighting": "quantiles_MPa: d(PEEQ) x V; time_quantiles_MPa: dt x V; element-"
                        "mean tensors at increment end; lo/hi = the window quantiles"}
    for p, (sv, sw, tv, tw) in ph.items():
        out[p] = {"fraction_of_cycle_inelastic_strain": (sum(sw) / tot) if tot else None,
                  "quantiles_MPa": dict(zip(names, LAW.wquantiles(sv, sw, qs))),
                  "time_quantiles_MPa": dict(zip(names, LAW.wquantiles(tv, tw, qs))),
                  "peak_vm_MPa": peak[p], "n_samples": len(sv)}
    return out


def record_path(study, tag):
    return scratch(ROOT, "results", study) / f"{tag}.json"


def _compress(p):
    if not p.exists():
        return None
    gz = p.with_suffix(".dat.gz")
    with open(p, "rb") as fi, gzip.open(gz, "wb", compresslevel=1) as fo:
        shutil.copyfileobj(fi, fo, 1 << 22)
    p.unlink()
    return gz.name


def resolve_card(task) -> tuple:
    """(card text, law name, window, window status) of a task."""
    if task.get("card"):
        return task["card"], task.get("law", "explicit"), None, "explicit"
    law = task.get("law") or LAW.solder_cfg()["production_law"]
    if law == "legacy":
        return LAW.legacy_card(), "legacy", None, "round-2 production card"
    win, status = (task["window"], "task") if task.get("window") else LAW.stored_window(law)
    return LAW.card(law, win)[0], law, win, status


def deck_for(task, wd: Path):
    """Build the mesh and write the deck of one task; returns (deck path, mesh, info)."""
    lc = lcfg()
    geom = geometry(task.get("geometry", "bga"))
    lv = LEVELS[task.get("level", lc["level"])]
    unit = task.get("unit") or ("mm" if float(geom["solder_d"]) >= 50.0 else "um")
    m = build_mesh(geom, lv["n_xy"], lv["n_z_solder"], 1,
                   band_frac=float(task.get("band_frac") or BAND_FRAC), unit=unit)
    kin = task["kin"]
    T_hot = float(task["T_C"]) if task.get("T_C") is not None else site_temperature(kin)
    ramp = float(task.get("ramp_s", lc["ramp_s"]))
    dwell = float(task.get("dwell_s", lc["dwell_s"]))
    n_cyc = int(task.get("n_cyc", lc["n_cycles"]))
    segs, half = schedule(T_hot, n_cyc, ramp, dwell, float(lc["T_cold_C"]))
    card, law, win, wstat = resolve_card(task)
    bcm = task.get("bc", lc["bc_mode"])
    p = wd / f"{task['tag']}.inp"
    kc = task.get("kin_cold")
    if kc is not None:
        # the cold state carries its own kinematics (a static clamp): express it in the
        # HOT state's frame so both halves of the cycle share one local orientation
        kc = dict(kc)
        kc["_frame_du_mm"] = kin["du_mm"]
    text = write_deck(m, p, card, segs, bc_values(m, kin, bcm), task.get("element",
                                                                         lc["element"]),
                      float(task.get("cetol", lc["cetol"])), float(lc["T_stress_free_C"]),
                      legacy_inc0=float(task.get("legacy_inc0", 0.002)),
                      bcv_cold=bc_values(m, kc, bcm) if kc is not None else None)
    info = {"geometry": task.get("geometry", "bga"), "unit": unit, "level":
            task.get("level", lc["level"]), "n_elem": len(m.elems),
            "n_core": len(m.sets["ESOLCORE"]), "T_hot_C": T_hot, "ramp_s": ramp,
            "dwell_s": dwell, "half_cycle_s": half, "n_cycles": n_cyc, "bc": bcm,
            "element": task.get("element", lc["element"]), "law": law, "window_MPa": win,
            "window_status": wstat, "card_sha": LAW.card_sha(card),
            "deck_sha": hashlib.sha1(text.encode()).hexdigest()[:16]}
    return p, m, info


def solve(task):
    """One local solve; the record is restartable (keyed by the deck's own hash)."""
    study, tag = task["study"], task["tag"]
    f = record_path(study, tag)
    wd = scratch(ROOT, study, tag)
    # run_ccx passes the bare stem (cwd = the deck's directory): CalculiX's 127-character limit
    # applies to the tag, not to the scratch path (which exceeds it under the campaign tree)
    if len(tag) > 127:
        raise ValueError(f"CalculiX job name too long ({len(tag)} > 127 characters): {tag}")
    p, m, info = deck_for(task, wd)
    if f.exists():
        old = json.loads(f.read_text())
        if old.get("deck_sha") == info["deck_sha"] and old.get("d_peeq_per_cycle") is not None:
            return old
    for ext in (".dat", ".frd", ".sta", ".cvg", ".dat.gz"):
        (wd / f"{tag}{ext}").unlink(missing_ok=True)
    t0 = time.time()
    err = None
    try:
        r = run_ccx(p, int(task.get("threads", THREADS)))
        if r.returncode != 0:
            err = f"ccx rc={r.returncode}: {(r.stdout + r.stderr)[-300:]}"
    except subprocess.TimeoutExpired:
        err = "ccx timeout"
    wall = time.time() - t0
    dat = wd / f"{tag}.dat"
    x, stats = None, None
    if dat.exists() and dat.stat().st_size > 2000:
        try:
            incs, vols = X.parse_blocks(dat, set(m.sets["ESOLCORE"]))
            x = X.extract(dat, set(m.sets["ESOLCORE"]), info["n_cycles"], info["half_cycle_s"])
            if task.get("stress", True) and x.get("d_peeq_per_cycle"):
                w = LAW.solder_cfg()["window"]["quantiles"]
                stats = stress_stats(incs, vols, info["n_cycles"], info["half_cycle_s"],
                                     info["T_hot_C"], float(lcfg()["T_cold_C"]), *w)
        except Exception as e:                    # recorded, never silent
            err = (err or "") + f" extraction: {str(e)[-200:]}"
    done = bool(x and x.get("d_peeq_per_cycle"))
    if not done and err is None:
        err = f"incomplete: .dat ends at {X.end_time(dat) if dat.exists() else None}"
    rec = dict(info, study=study, tag=tag, wall_s=wall, error=err,
               d_peeq_per_cycle=x["d_peeq_per_cycle"] if done else None,
               per_cycle=[c["d_peeq_per_cycle"] if c else None for c in x["cycles"]]
               if x and x.get("cycles") else None,
               stab_change_pct=x.get("stab_change_pct") if done else None,
               inelastic_work_MJ_per_m3=x.get("inelastic_work_MJ_per_m3") if done else None,
               stress=stats, kin={k: task["kin"].get(k) for k in
                                  ("x_mm", "y_mm", "du_mm", "G_bot", "G_top", "T_bot_C",
                                   "T_top_C", "du_xy_um", "du_z_um")},
               meta=task.get("meta") or {}, threads=int(task.get("threads", THREADS)))
    if os.environ.get("TCPMT_KEEP_DAT") != "1":
        rec["dat_gz"] = _compress(dat)
    f.write_text(json.dumps(rec, indent=1, default=float))
    return rec


def run_tasks(tasks, procs=None):
    """Solve every task not yet recorded with the same deck; return {tag: record}."""
    todo = []
    for t in tasks:
        f = record_path(t["study"], t["tag"])
        if f.exists():
            r = json.loads(f.read_text())
            p, _m, info = deck_for(t, scratch(ROOT, t["study"], t["tag"]))
            if r.get("deck_sha") == info["deck_sha"] and r.get("d_peeq_per_cycle") is not None:
                continue
        todo.append(t)
    print(f"{len(tasks)} tasks, {len(todo)} to solve, {procs or SLOTS} parallel x "
          f"{THREADS} threads", flush=True)
    if todo:
        ctx = mp.get_context("fork")
        with ctx.Pool(min(len(todo), procs or SLOTS), maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(solve, todo, chunksize=1):
                print(f"  {r['study']}/{r['tag']}: d_eps = {r.get('d_peeq_per_cycle')} "
                      f"err={r.get('error')} wall={r.get('wall_s', 0):.0f}s", flush=True)
    out = {}
    for t in tasks:
        f = record_path(t["study"], t["tag"])
        if f.exists():
            out[t["tag"]] = json.loads(f.read_text())
    return out


def load_records(study):
    d = scratch(ROOT, "results", study)
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))}


def synthetic_kin(du_um, T_C, du_z_um=0.0):
    """Kinematics of a pure-shear legacy probe (no stretch, no rotation)."""
    return {"du_mm": [du_um / 1e3, 0.0, du_z_um / 1e3], "G_bot": [[0, 0], [0, 0], [0, 0]],
            "G_top": [[0, 0], [0, 0], [0, 0]], "T_bot_C": T_C, "T_top_C": T_C,
            "x_mm": None, "y_mm": None, "du_xy_um": du_um, "du_z_um": du_z_um}


def selftest():
    """v2 with (legacy card, legacy BC, legacy schedule) must reproduce the round-2 harness
    on the Phase-0I control joint: d_eps = 0.00651488542578123 (pass-5 acceptance)."""
    t = dict(study="selftest", tag="control_legacy", kin=synthetic_kin(2.749, 82.86),
             law="legacy", bc="legacy", ramp_s=0.0, dwell_s=300.0, n_cyc=4,
             element="C3D8", stress=False)
    r = solve(t)
    ref = 0.00651488542578123
    print("v2 legacy reproduction:", r["d_peeq_per_cycle"], "ref", ref,
          "rel", (r["d_peeq_per_cycle"] - ref) / ref if r["d_peeq_per_cycle"] else None,
          "wall", round(r["wall_s"]), "s")
    return r


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
