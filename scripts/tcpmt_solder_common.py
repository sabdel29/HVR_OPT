"""Shared harness for the TCPMT-revision solder studies (critical joint, stabilisation,
averaging band, constitutive law).

ROUND-2 HARNESS. Since the round-3 review the production local model is v2
(scripts/tcpmt_mech_submodel.py; configs/tcpmt_mech/mechanics_revision.yaml local.harness):
zero-yield laws refitted over the visited window, full global cut-boundary kinematics on both
pad faces, ramped loading. Its drivers are tcpmt_mech_law_band (replaces the constitutive
study), tcpmt_mech_critical (replaces tcpmt_solder_critical) and tcpmt_mech_local_checks.
This module and its drivers are kept to reproduce the round-2 numbers only.

Nothing here re-implements the local model. Every solve goes through the production entry
point final_closure_local_mesh._solve (block-order extraction, split 3 s + 297 s steps,
first increment from local_time_study.json, CETOL 5e-2, Phase-0I/0I-R joint and card), i.e.
the same call final_closure_sensitivity._local_task makes. A study changes at most:

  du, T_joint        the joint whose response is computed
  level / n_cyc      mesh level (policy L0..L3) and number of cycles
  band_frac          the fixed averaging band (joint.BAND_FRAC, read at call time)
  card               the SAC305 material block (run_final_local_response.material)
  inc0               first increment of each 3 s load step (default: the time study's)
  units, controls    checks only: a consistent stress unit of k MPa, and an extra
                     *CONTROLS, PARAMETERS=FIELD card (equilibrium tolerances)

The overrides are applied inside a fresh worker process per solve (maxtasksperchild=1), so
nothing leaks between tasks, and the production defaults are restored explicitly when a
task does not set them.

Concurrency: the host is shared. A global semaphore of TCPMT_SOLDER_SLOTS (default 6) flock
slot files under the scratch tree caps the number of concurrent CalculiX solves across every
driver process, each solve running LOCAL_THREADS (=2) threads.

Every solve writes its own result record under $HVR_SCRATCH/tcpmt_solder/results/<study>/,
so the drivers are restartable and the collector reads records, never re-solves.
"""
from __future__ import annotations

import fcntl
import gzip
import json
import math
import multiprocessing as mp
import os
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_local_mesh as LM                               # noqa: E402

LR = LM.LR                       # phase0mr3c/run_final_local_response (the harness)
X = LM.X                         # final_closure_local_extract (block order)
import joint as JOINT            # noqa: E402  the module object LR.build_joint reads
import decompose as DEC          # noqa: E402  production material() lives here
import solder_model as SM        # noqa: E402  production constitutive source
from hvr_scratch import path as scratch                             # noqa: E402

FC = R / "research" / "final_closure"
OUT = R / "research" / "tcpmt_revision"
ROOT = "tcpmt_solder"
INC0 = json.loads(LM.TIME_STUDY.read_text())["production_dt0_s"]
BAND_PROD = float(LM.A5["band_frac"])
SLOTS = int(os.environ.get("TCPMT_SOLDER_SLOTS", "6"))
T_COLD = LR.T_OFF

assert JOINT.BAND_FRAC == BAND_PROD, "JOINT_BAND_FRAC must equal the amendment-5 band"

#: case files. A Z1/Z2 are the production S0 cases; A Z3 is Z3 under the top plate alone;
#: B adds the identical bottom plate through the 50-um TIM (manuscript_v2 Table II).
CASES = {
    "Z1_S0": FC / "etm_Z1_HV_S0_h1.1_r21.json",
    "Z2_S0": FC / "etm_Z2_HV_S0_h1.1_r21.json",
    "Z3_S0": FC / "etm_Z3_HV_S0_h1.1_r21.json",
    "Z1_S1": FC / "etm_Z1_HV_S1_h1.1_r21.json",
    "Z2_S1": FC / "etm_Z2_HV_S1_h1.1_r21.json",
    # review round 2: Z3 is the coupled land-side case (the uncoupled z3_top_only /
    # z3_plate_tim are superseded; tcpmt_cases)
    "A_Z3": FC / "sensitivity" / "etm_Z3_HV_S0__z3_land_t40_A_fvmap.json",
    "B_Z1": FC / "sensitivity" / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
    "B_Z2": FC / "sensitivity" / "etm_Z2_HV_S0__z2_cooled_tim.json",
    "B_Z3": FC / "sensitivity" / "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json",
}
TIERS = {"A": {"Z1": "Z1_S0", "Z2": "Z2_S0", "Z3": "A_Z3"},
         "B": {"Z1": "B_Z1", "Z2": "B_Z2", "Z3": "B_Z3"}}
#: the L0 responses the manuscript currently prints (results_macros.tex, x1e-3 / cycle)
PAPER_L0 = {"A": {"Z1": 5.80, "Z2": 8.03, "Z3": 13.47},
            "B": {"Z1": 2.08, "Z2": 4.15, "Z3": 2.52}}
#: production pass-5 uncertainties (local_mesh_study.json), relative
MESH_STUDY = FC / "local_mesh_study.json"
CYCLE_STUDY = FC / "local_cycle_study.json"


def tier_cases():
    """[(tier, arch, case)] in a fixed order."""
    return [(t, a, c) for t in ("A", "B") for a, c in TIERS[t].items()]


def ranked(case):
    return json.loads(CASES[case].read_text())["mechanics"]["joint_search"]["ranked"]


def critical(case):
    js = json.loads(CASES[case].read_text())["mechanics"]["joint_search"]
    c = js["critical"]
    top = max(js["ranked"], key=lambda s: s["du_um"])
    assert (top["x_mm"], top["y_mm"]) == (c["x_mm"], c["y_mm"]), case
    return c


def rel(x):
    return Path(x).resolve().relative_to(R).as_posix()


# ----------------------------------------------------------------------- concurrency
@contextmanager
def solver_slot(poll_s=None):
    """One of SLOTS exclusive flock slots, shared by every driver process on the host. A
    driver that polls faster (TCPMT_SLOT_POLL, s) wins freed slots first: a priority knob
    only, the cap is unchanged."""
    poll_s = float(os.environ.get("TCPMT_SLOT_POLL", "5")) if poll_s is None else poll_s
    d = scratch(ROOT, "slots")
    while True:
        for i in range(SLOTS):
            fh = open(d / f"slot{i}.lock", "w")
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                fh.close()
                continue
            try:
                yield i
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
                fh.close()
            return
        time.sleep(poll_s)


# ----------------------------------------------------------------------- stresses
def von_mises(s):
    sxx, syy, szz, sxy, sxz, syz = s
    return math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                     + 3.0 * (sxy ** 2 + sxz ** 2 + syz ** 2))


def wquantiles(vals, wts, qs):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    tot = sum(wts)
    if not tot:
        return [None for _ in qs]
    out, acc, k = [], 0.0, 0
    targets = [q * tot for q in qs]
    for i in order:
        acc += wts[i]
        while k < len(targets) and acc >= targets[k] - 1e-15 * tot:
            out.append(vals[i])
            k += 1
    while len(out) < len(qs):
        out.append(vals[order[-1]])
    return out


QS = (0.05, 0.25, 0.50, 0.75, 0.95)


def stress_stats(dat, core, n_cyc, dwell, t_hot, t_cold=T_COLD, cycle=None, scale=1.0):
    """Where the inelastic strain of one cycle is deposited, in stress.

    Block order (same windows as final_closure_local_extract.cycle_metrics). Every core
    element's PEEQ increment over every printed increment is a sample at the von Mises
    stress of the element-mean tensor at the END of that increment (the solver's implicit
    update evaluates the flow rule there), weighted by d(PEEQ) * V. Reported per phase
    (hot dwell at T_joint, cold dwell at 25 C) as weighted quantiles, with the fraction of
    the cycle's inelastic strain each phase carries and the peak core stress."""
    incs, vols = X.parse_blocks(dat, core)
    period = 2 * dwell
    k = (n_cyc - 1) if cycle is None else cycle
    i0 = X._first_at(incs, k * period)
    i1 = (len(incs) - 1) if k == n_cyc - 1 else X._first_at(incs, (k + 1) * period)
    if i0 is None or i1 is None:
        return None
    win = incs[i0:i1 + 1]
    ph = {"hot": ([], []), "cold": ([], [])}
    tw = {"hot": ([], []), "cold": ([], [])}
    peak = {"hot": 0.0, "cold": 0.0}
    vtot = sum(vols.values())
    for a, b in zip(win, win[1:]):
        p = "hot" if abs(b["T"] - t_hot) < abs(b["T"] - t_cold) else "cold"
        dt = max(0.0, b["t"] - a["t"])
        for e, v in vols.items():
            da, db = a["el"].get(e), b["el"].get(e)
            if not (da and db and "S" in db):
                continue
            s = scale * von_mises(db["S"])
            peak[p] = max(peak[p], s)
            if dt > 0:
                tw[p][0].append(s)
                tw[p][1].append(dt * v)
            dp = db["P"] - da["P"]
            if dp > 0:
                ph[p][0].append(s)
                ph[p][1].append(dp * v)
    tot = sum(sum(w) for _, w in ph.values())
    out = {"cycle": k + 1, "weighting": "quantiles_MPa: d(PEEQ) x element volume (where the "
                                        "inelastic strain is deposited); time_quantiles_MPa: "
                                        "dt x element volume (where the cycle is spent); "
                                        "element-mean tensors, stress at increment end",
           "d_peeq_vol_avg": tot / vtot if vtot else None}
    for p, (sv, w) in ph.items():
        q = wquantiles(sv, w, QS)
        out[p] = {"fraction_of_cycle_inelastic_strain": (sum(w) / tot) if tot else None,
                  "quantiles_MPa": dict(zip([f"q{int(100 * x):02d}" for x in QS], q)),
                  "time_quantiles_MPa": dict(zip([f"q{int(100 * x):02d}" for x in QS],
                                                 wquantiles(tw[p][0], tw[p][1], QS))),
                  "peak_vm_MPa": peak[p], "n_samples": len(sv)}
    allv = ph["hot"][0] + ph["cold"][0]
    allw = ph["hot"][1] + ph["cold"][1]
    out["all"] = {"quantiles_MPa": dict(zip([f"q{int(100 * x):02d}" for x in QS],
                                            wquantiles(allv, allw, QS)))}
    return out


# ----------------------------------------------------------------------- the solve
def _card_fn(card):
    return (lambda kind, _c=card: _c) if card else DEC.material


#: the copper block exactly as joint.write_inp writes it (MPa)
CU_MPA = "*MATERIAL, NAME=CU\n*ELASTIC\n117000., 0.34\n"
UNIT_SCALE = {"MPa": 1.0, "10MPa": 10.0, "100MPa": 100.0, "GPa": 1000.0}


def card_to_units(text, k):
    """A SAC305 block in consistent units whose stress unit is k MPa (force unit k N, mm,
    s): E and every yield stress / k, Norton A x k^n (eps_dot = A sigma^n is invariant).
    Used where an MPa-based Norton prefactor would fall below CalculiX's internal floor of
    1e-20 (incplas.f)."""
    out, sec = [], None
    for line in text.splitlines():
        if line.startswith("*"):
            sec = line[1:].split(",")[0].strip().upper()
            out.append(line)
            continue
        v = [float(x) for x in line.split(",")]
        if sec == "ELASTIC":
            v[0] /= k
        elif sec == "PLASTIC":
            v[0] /= k
        elif sec == "CREEP":
            v[0] *= k ** v[1]
        out.append(", ".join(f"{x:.10g}" for x in v))
    return "\n".join(out) + "\n"


def card_to_gpa(text):
    return card_to_units(text, 1000.0)


def _use_copper_units(k):
    """Wrap the harness write_inp so the copper block is written in the same units (the
    harness hard-codes it in MPa); final_closure_local_mesh._use_steps wraps on top."""
    base = LR.write_inp
    cu = f"*MATERIAL, NAME=CU\n*ELASTIC\n{117000.0 / k:.10g}, 0.34\n"

    def write_inp(m, p, *a, **kw):
        base(m, p, *a, **kw)
        s = p.read_text()
        if s.count(CU_MPA) != 1:
            raise RuntimeError("copper block not found exactly once")
        p.write_text(s.replace(CU_MPA, cu))
    LR.write_inp = write_inp


def _compress(p):
    """gzip a finished .dat (kept for traceability, ~6x smaller)."""
    if not p.exists():
        return None
    gz = p.with_suffix(".dat.gz")
    with open(p, "rb") as fi, gzip.open(gz, "wb", compresslevel=1) as fo:
        shutil.copyfileobj(fi, fo, 1 << 22)
    p.unlink()
    return gz.name


def _use_controls(inc0, line):
    """Insert '*CONTROLS, PARAMETERS=FIELD' with `line` after every *VISCO data line of the
    deck AFTER final_closure_local_mesh._use_steps has split the steps (the wrapper carries
    the step patcher's _key/_orig, so _solve's own _use_steps call leaves it in place)."""
    import re as _re
    LM._use_steps(inc0, True)
    inner = LR.write_inp

    def write_inp(m, p, *a, **kw):
        inner(m, p, *a, **kw)
        s = p.read_text()
        n_v = s.count("*VISCO")
        s2, n = _re.subn(r"(\*VISCO, CETOL=\S+\n[^\n]+\n)",
                         lambda g: g.group(1) + "*CONTROLS, PARAMETERS=FIELD\n" + line + "\n",
                         s)
        if n != n_v or n == 0:
            raise RuntimeError(f"controls inserted in {n} of {n_v} steps")
        p.write_text(s2)
    write_inp._key, write_inp._orig = inner._key, inner._orig
    LR.write_inp = write_inp


def record_path(study, tag):
    return scratch(ROOT, "results", study) / f"{tag}.json"


def restat(study, tag, force=False):
    """Recompute a solved record's stress statistics (both weightings) from its kept
    .dat.gz, e.g. after stress_stats gained the time weighting. Updates the record."""
    f = record_path(study, tag)
    r = json.loads(f.read_text())
    st = r.get("stress") or {}
    if not force and "time_quantiles_MPa" in (st.get("hot") or {}):
        return r
    wd = Path(r["workdir"])
    gz = wd / f"{tag}.dat.gz"
    if r.get("d_peeq_per_cycle") is None or not gz.exists():
        return r
    tmp = wd / f"{tag}.restat.dat"
    with gzip.open(gz, "rb") as fi, open(tmp, "wb") as fo:
        shutil.copyfileobj(fi, fo, 1 << 22)
    try:
        lv = LM.LEVELS[r.get("level", "L0")]
        bf = float(r.get("band_frac") or BAND_PROD)
        old_band, JOINT.BAND_FRAC = JOINT.BAND_FRAC, bf
        m = LR.build_joint(lv["n_xy"], lv["n_z_solder"], LR.N_Z_PAD)
        JOINT.BAND_FRAC = old_band
        r["stress"] = stress_stats(tmp, set(m.sets["ESOLCORE"]), int(r["n_cycles"]),
                                   LR.DWELL, float(r["T_joint_C"]),
                                   scale=UNIT_SCALE[r.get("units", "MPa")])
    finally:
        tmp.unlink(missing_ok=True)
    f.write_text(json.dumps(r, indent=1, default=float))
    return r


def solve(task):
    """One local solve. task: dict(study, tag, du_um, T_C, level='L0', n_cyc=4,
    band_frac=None, card=None, card_name=None, stress=False, meta={})."""
    study, tag = task["study"], task["tag"]
    f = record_path(study, tag)
    if f.exists():
        old = json.loads(f.read_text())
        if old.get("d_peeq_per_cycle") is not None and old.get("sig") == task.get("sig"):
            return old
    level, n_cyc = task.get("level", "L0"), int(task.get("n_cyc", 4))
    band = float(task.get("band_frac") or BAND_PROD)
    inc0 = float(task.get("inc0") or INC0)       # first increment of each 3 s load step
    units = task.get("units", "MPa")
    k_unit = UNIT_SCALE[units]
    JOINT.BAND_FRAC = band                       # read by build_joint at call time
    card = task.get("card")
    if k_unit != 1.0:
        card = card_to_units(card or DEC.material(LR.MATKIND), k_unit)
        _use_copper_units(k_unit)
    if task.get("controls"):
        _use_controls(inc0, task["controls"])
    LR.material = _card_fn(card)                 # read by run_case at call time
    wd = scratch(ROOT, study, tag)
    # joint.run passes the full path as the CalculiX job name; ccx 2.23 holds it in a
    # 132-character buffer and silently writes nothing when it is longer
    if len(str(wd / tag)) > 132:
        raise ValueError(f"CalculiX job name longer than 132 characters: {wd / tag}")
    t0 = time.time()
    with solver_slot() as slot:
        r = LM._solve(tag, float(task["du_um"]), float(task["T_C"]), wd, level, inc0, True,
                      n_cyc)
    r.update(study=study, tag=tag, band_frac=band, band_um=band * JOINT.SOLDER_SIDE_UM,
             material=task.get("card_name") or "production (decompose.material('EPC'))",
             slot=slot, wall_incl_wait_s=time.time() - t0, workdir=str(wd),
             first_increment_s=inc0, local_threads=int(os.environ.get("LOCAL_THREADS", 6)),
             sig=task.get("sig"), units=units, controls=task.get("controls"),
             **(task.get("meta") or {}))
    if k_unit != 1.0:
        # the elastic/thermal split behind these two secondary metrics assumes MPa
        r["range_eq_inelastic"] = r["inelastic_work_MJ_per_m3"] = None
        r["secondary_metrics_note"] = "range/work not valid outside MPa units; PEEQ is"
    dat = wd / f"{tag}.dat"
    if task.get("stress") and r.get("d_peeq_per_cycle") is not None and dat.exists():
        m = LR.build_joint(LM.LEVELS[level]["n_xy"], LM.LEVELS[level]["n_z_solder"],
                           LR.N_Z_PAD)
        try:
            r["stress"] = stress_stats(dat, set(m.sets["ESOLCORE"]), n_cyc, LR.DWELL,
                                       float(task["T_C"]), scale=k_unit)
        except Exception as e:                    # recorded, never silent
            r["stress_error"] = str(e)[-300:]
    if os.environ.get("TCPMT_KEEP_DAT") != "1":
        r["dat_gz"] = _compress(dat)
    f.write_text(json.dumps(r, indent=1, default=float))
    return r


def run_tasks(tasks, procs=None):
    """Solve every task not yet recorded, in a fresh process each; return all records."""
    def done(t):
        f = record_path(t["study"], t["tag"])
        if not f.exists():
            return False
        r = json.loads(f.read_text())
        return r.get("d_peeq_per_cycle") is not None and r.get("sig") == t.get("sig")

    todo = [t for t in tasks if not done(t)]
    print(f"{len(tasks)} tasks, {len(todo)} to solve, {SLOTS} global slots", flush=True)
    if todo:
        ctx = mp.get_context("fork")
        with ctx.Pool(min(len(todo), procs or SLOTS), maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(solve, todo, chunksize=1):
                print(f"  {r['study']}/{r['tag']}: d_eps = {r.get('d_peeq_per_cycle')} "
                      f"err={r.get('error')} wall={r.get('wall_s', 0):.0f}s", flush=True)
    return {t["tag"]: json.loads(record_path(t["study"], t["tag"]).read_text())
            for t in tasks if record_path(t["study"], t["tag"]).exists()}


def load_records(study):
    d = scratch(ROOT, "results", study)
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))}


def production_uncertainty():
    """Pass-5 U parts per production case (local_mesh_study.json)."""
    ms = json.loads(MESH_STUDY.read_text())["cases"]
    return {k: {"U": c["U"], "U_mesh": c["U_mesh"], "U_time": c["U_time"],
                "U_cyc": c["U_cyc"], "status": c["status"],
                "L0": c["levels"]["L0"]["d_peeq_per_cycle"],
                "L3": c["levels"]["L3"]["d_peeq_per_cycle"]} for k, c in ms.items()}
