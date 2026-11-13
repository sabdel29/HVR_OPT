"""Local solder discretisation study under the DECLARED policy
(research/final_closure/local_mesh_policy.json, including its amendments).

Every level of the declared family is run with identical settings at the production
critical joint of each case, and the declared rule -- not a judgement made after seeing
the numbers -- decides whether the response is converged, bounded or unresolved and
which uncertainty U it carries.

The history matters and is kept:
  pass 1   harness steps as written (first increment 2e-3 s)  local_mesh_study_pass1.json
  amend 1  first increment 1e-4 s: rejected by its own control test (-10.24 %)
  amend 2  temporal study first                                local_time_study_amend2.json
  amend 3  both "temporal" effects were DEFECT #65, a parser collision of 7-digit output
           times (scripts/final_closure_local_extract.py); block-order extraction, the
           load change written as its own 3 s step (removes the cutback floor), and
           U = U_mesh + U_time + U_cyc

    python final_closure_local_mesh.py --temporal      -> local_time_study.json
    python final_closure_local_mesh.py --cycles        -> local_cycle_study.json
    python final_closure_local_mesh.py [ARCH:SCEN ...] -> local_mesh_study.json (pass 3)
"""
from __future__ import annotations

import json
import os
import multiprocessing as mp
import re
import sys
import time
from pathlib import Path

# Every pool worker would otherwise start a full-width OpenBLAS pool (64-96 idle threads);
# on this shared host that reached the per-user thread limit and killed CalculiX
# runs mid-solve (DEFECT #69). The solvers set their own thread counts.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

R = Path(__file__).resolve().parents[1]
# Amendment 5 (TCPMT revision): the fixed-width averaging band is read by joint.py at
# import time, so it is set from the policy before the harness is imported.
_A5 = next((a for a in json.loads((R / "research" / "final_closure" / "local_mesh_policy.json")
            .read_text()).get("amendments", []) if a.get("id") == 5), None)
if _A5:
    os.environ["JOINT_BAND_FRAC"] = repr(float(_A5["band_frac"]))
for _p in ("scripts/phase0mr3c", "scripts/phase0ir", "scripts/phase0i", "scripts"):
    sys.path.insert(0, str(R / _p))
import run_final_local_response as LR                                # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import final_closure_local_extract as X                             # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402

OUT = R / "research" / "final_closure"
POLICY = json.loads((OUT / "local_mesh_policy.json").read_text())
LEVELS = POLICY["levels"]
TOL = POLICY["tolerance_rel"]
AMEND = {a["id"]: a for a in POLICY.get("amendments") or []}
TEMPORAL = (AMEND.get(2) or {}).get("temporal_study")
TIME_STUDY = OUT / "local_time_study.json"
CYCLE_STUDY = OUT / "local_cycle_study.json"
HARNESS_INC0 = 2e-3
N_CYC_LONG = 16
STEP = re.compile(r"\*STEP, INC=5000\n\*VISCO, CETOL=(\S+)\n0\.002, 300, 1e-06, 15\n"
                  r"(\*TEMPERATURE\nNALL, \S+\n\*BOUNDARY\nNTOP,1,1,\S+\n)(.*?)\*END STEP", re.S)


# Local CalculiX solves run with LOCAL_THREADS threads (default 6, the harness value). The
# historical runner (phase0mr3c/run_final_local_response.py) is not edited: its module-
# level `run` is wrapped here. Thread count changes speed only; the control-reproduction
# acceptance check would expose any numerical difference.
_LT = int(os.environ.get("LOCAL_THREADS", "6"))
if _LT != 6 and not getattr(LR.run, "_wrapped", False):
    _orig_run = LR.run
    def _run(p, threads=6):
        return _orig_run(p, threads=_LT)
    _run._wrapped = True
    LR.run = _run

A4 = AMEND.get(4)
A5 = AMEND.get(5)
#: amendment 6 (TCPMT revision) extends pass 5 to the board-backside Z3; rules unchanged
A6 = AMEND.get(6)
PASS = 5 if A5 else (4 if A4 else 3)
#: each pass keeps its own scratch tree
SCR_MESH = "fc_localmesh_p5" if A5 else ("fc_localmesh_p4" if A4 else "fc_localmesh_p3")
SUPERSEDED = OUT / "superseded_bga_fed_z2"


#: cap on concurrent solver processes (shared host); unset = the previous behaviour
POOL_MAX = int(os.environ.get("FC_POOL_MAX", "10000"))


def policy_cases(optional=True):
    """The cases of the CURRENT pass: amendment 4 re-declares them for the corrected
    lineage (direct-fed Z2, explicit attach, sidewall clearance)."""
    for A in (A6, A5, A4):
        if A:
            c = [tuple(x) for x in A["cases"]]
            return c + ([tuple(x) for x in A.get("optional_cases", [])] if optional else [])
    c = [tuple(x) for x in POLICY["cases"]]
    return c + ([tuple(x) for x in POLICY["optional_cases"]["cases"]] if optional else [])


def keep_previous(path):
    """Before pass 4 first overwrites a pass-3 file, keep it with the superseded lineage."""
    if not (A4 and path.exists()):
        return
    j = json.loads(path.read_text())
    if j.get("pass", 3) == 4 or j.get("corrected_lineage"):
        return
    SUPERSEDED.mkdir(exist_ok=True)
    dst = SUPERSEDED / path.name.replace(".json", "_pass3.json")
    if not dst.exists():
        dst.write_text(path.read_text())


def _use_steps(inc0, split):
    """Rewrite the harness's *VISCO steps. split=False: start each 300 s step at inc0
    (amendment-2 study). split=True (amendment 3): the load change in a 3 s step
    (first increment inc0, minimum 1e-9 s, maximum 3 s) and a 297 s hold at the same loads
    (first increment 0.5 s, maximum 15 s). Asserted to touch every step."""
    key = (inc0, split)
    if getattr(LR.write_inp, "_key", None) == key:
        return
    orig = getattr(LR.write_inp, "_orig", LR.write_inp)
    if key == (HARNESS_INC0, False):
        LR.write_inp = orig
        return

    def rep(g):
        if not split:
            return (f"*STEP, INC=5000\n*VISCO, CETOL={g.group(1)}\n{inc0:g}, 300, 1e-06, 15\n"
                    f"{g.group(2)}{g.group(3)}*END STEP")
        return (f"*STEP, INC=5000\n*VISCO, CETOL={g.group(1)}\n{inc0:g}, 3, 1e-09, 3\n"
                f"{g.group(2)}{g.group(3)}*END STEP\n"
                f"*STEP, INC=5000\n*VISCO, CETOL={g.group(1)}\n0.5, 297, 1e-09, 15\n"
                f"{g.group(2)}{g.group(3)}*END STEP")

    def write_inp(m, p, *a, **k):
        orig(m, p, *a, **k)
        s = p.read_text()
        n_step = s.count("*VISCO")
        s2, n = STEP.subn(rep, s)
        if n != n_step or n == 0:
            raise RuntimeError(f"steps rewritten in {n} of {n_step}")
        p.write_text(s2)
    write_inp._orig, write_inp._key = orig, key
    LR.write_inp = write_inp


def critical(arch, scen):
    import final_closure_physical_etm as E
    f = E.case_path(arch, scen)
    c = json.loads(f.read_text())["mechanics"]["joint_search"]["critical"]
    return c["du_um"], c["T_C"], f.name


def _solve(name, du, tj, wd, level, inc0, split, n_cyc=4):
    """One local solve, extracted in BLOCK ORDER (DEFECT #65). The harness's own
    time-keyed value is kept beside it; a failure is a recorded result."""
    lv = LEVELS[level]
    _use_steps(inc0, split)
    LR.N_XY, LR.N_Z_SOL, LR.N_CYC = lv["n_xy"], lv["n_z_solder"], n_cyc
    LR.CETOL = 5.0e-2
    LR.WD = wd
    LR.WD.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    dat = wd / f"{name}.dat"
    for ext in (".dat", ".frd", ".sta", ".cvg"):     # an old .dat never stands in (DEFECT #69)
        (wd / f"{name}{ext}").unlink(missing_ok=True)
    try:
        r = LR.run_case(name, du, tj)
        err = None
    except Exception as e:
        r, err = None, str(e)[-300:]
    wall = time.time() - t0
    x = None
    if dat.exists() and dat.stat().st_size > 5000:
        try:
            m = LR.build_joint(lv["n_xy"], lv["n_z_solder"], LR.N_Z_PAD)
            x = X.extract(dat, set(m.sets["ESOLCORE"]), n_cyc, LR.DWELL)
        except Exception as e:
            err = (err or "") + f" extraction: {str(e)[-200:]}"
    done = bool(x and x.get("d_peeq_per_cycle")) and bool(r)
    if not done and err is None:
        t_last = X.end_time(dat) if dat.exists() else None
        err = (f"solve did not complete: the .dat ends at t = {t_last} s of "
               f"{2 * n_cyc * LR.DWELL:g} s")
    return {"level": level, **lv, "initial_increment_s": inc0, "split_steps": split,
            "n_cycles": n_cyc, "du_um": du, "T_joint_C": tj, "wall_s": wall, "error": err,
            "d_peeq_per_cycle": x["d_peeq_per_cycle"] if done else None,
            "d_peeq_time_keyed": (r or {}).get("d_peeq_per_cycle"),
            "stab_change_pct": x.get("stab_change_pct") if done else None,
            "range_eq_inelastic": x.get("range_eq_inelastic") if done else None,
            "inelastic_work_MJ_per_m3": x.get("inelastic_work_MJ_per_m3") if done else None,
            "per_cycle": [c["d_peeq_per_cycle"] if c else None for c in x["cycles"]]
            if x else None,
            "collisions": (x or {}).get("collisions"),
            "n_core": (r or {}).get("n_core"), "n_elem": (r or {}).get("n_elem")}


def _inputs(case):
    if case == "CONTROL":
        return LR.CONTROL["du_um"], LR.CONTROL["T_hot_C"], "Phase-0I control"
    a, s = case.split(":")
    return critical(a, s)


# ----------------------------------------------------------------- temporal study
def _time_task(t):
    case, inc0 = t
    du, tj, src = _inputs(case)
    tag = f"{case.replace(':', '_')}_dt{inc0:g}_tmax15_ce0.05"
    return dict(_solve(tag, du, tj, scratch("fc_localtime", tag), "L0", inc0, False),
                case=case, source=src)


def _richardson(v, h):
    """Observed order and extrapolated value from three levels with h1 > h2 > h3."""
    d1, d2 = v[1] - v[0], v[2] - v[1]
    if d1 == 0 or d2 == 0 or d1 * d2 < 0:
        return None
    f = lambda p: (h[0] ** p - h[1] ** p) / (h[1] ** p - h[2] ** p) - d1 / d2
    lo, hi = 0.05, 12.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    p = 0.5 * (lo + hi)
    c = d1 / (h[1] ** p - h[0] ** p)
    return {"order": p, "extrapolated": v[0] - c * h[0] ** p}


def temporal_rule(rows):
    """The declared amendment-2 criterion, applied mechanically to one case."""
    done = sorted([r for r in rows if r["d_peeq_per_cycle"]],
                  key=lambda r: -r["initial_increment_s"])
    out = {"dt0_completed": [r["initial_increment_s"] for r in done],
           "dt0_failed": [r["initial_increment_s"] for r in rows if not r["d_peeq_per_cycle"]]}
    if done:
        v = [r["d_peeq_per_cycle"] for r in done]
        out["spread_all_completed_rel"] = (max(v) - min(v)) / abs(v[-1])
    for a, b in zip(done, done[1:]):
        ch = abs(b["d_peeq_per_cycle"] - a["d_peeq_per_cycle"]) / abs(b["d_peeq_per_cycle"])
        if ch < 0.01 and abs(a["initial_increment_s"] / b["initial_increment_s"] - 2) < 1e-9:
            return dict(out, status="converged", dt0=a["initial_increment_s"], U_time=ch,
                        value_at_dt0=a["d_peeq_per_cycle"], rule="halving below 1 %")
    if len(done) < 3:
        return dict(out, status="unresolved", dt0=None, U_time=None,
                    note="fewer than three completed increments")
    a, b, c = done[-3:]
    v = [a["d_peeq_per_cycle"], b["d_peeq_per_cycle"], c["d_peeq_per_cycle"]]
    h = [a["initial_increment_s"], b["initial_increment_s"], c["initial_increment_s"]]
    rich = _richardson(v, h)
    if rich and 0.5 <= rich["order"] <= 4.0:
        return dict(out, status="bounded", dt0=h[2], richardson=rich,
                    U_time=1.25 * abs(v[2] - rich["extrapolated"]) / abs(rich["extrapolated"]),
                    value_at_dt0=v[2], rule="Richardson in dt0")
    return dict(out, status="bounded", dt0=h[2], richardson=rich,
                U_time=(max(v) - min(v)) / abs(v[2]), value_at_dt0=v[2],
                rule="range of the three finest")


def temporal():
    incs = TEMPORAL["initial_increments_s"]
    cases = ["CONTROL"] + [f"{a}:{s}" for a, s in policy_cases()]
    tasks = [(c, i) for c in cases for i in incs]
    with mp.Pool(min(len(tasks), 24, POOL_MAX)) as pool:
        rows = pool.map(_time_task, tasks, chunksize=1)
    study = {"policy": "local_mesh_policy.json amendments 2 and 3",
             "extraction": "block order (scripts/final_closure_local_extract.py, DEFECT #65)",
             "level": "L0", "cases": {}}
    for c in cases:
        rr = [r for r in rows if r["case"] == c]
        study["cases"][c] = {"runs": rr, **temporal_rule(rr)}
    per = [c["dt0"] for k, c in study["cases"].items()
           if k != "CONTROL" and tuple(k.split(":")) in policy_cases(optional=False)]
    prod = max(per) if per and all(x is not None for x in per) and len(set(per)) == 1 \
        else (min(per) if per and all(x is not None for x in per) else None)
    study["production_dt0_s"] = prod
    study["production_dt0_rule"] = ("the policy cases' common converged first increment; the "
                                    "optional case (not rankable) does not set it")
    for k, c in study["cases"].items():
        v = {r["initial_increment_s"]: r["d_peeq_per_cycle"] for r in c["runs"]}
        a, b = v.get(prod), v.get(prod / 2.0) if prod else None
        c["U_time_at_production"] = abs(b - a) / abs(b) if (a and b) else c.get("U_time")
        c["value_at_production"] = a
    pub = LR.CONTROL["d_eps_in_stab"]
    ctl = study["cases"]["CONTROL"]
    fine = [r for r in ctl["runs"] if r["d_peeq_per_cycle"]]
    if fine:
        f = min(fine, key=lambda r: r["initial_increment_s"])
        study["historical_control_vs_finest_dt0_rel"] = (pub - f["d_peeq_per_cycle"]) / \
            f["d_peeq_per_cycle"]
    keep_previous(TIME_STUDY)
    study["corrected_lineage"] = bool(A4)
    TIME_STUDY.write_text(json.dumps(study, indent=1, default=float))
    for k, c in study["cases"].items():
        print(k, c["status"], c.get("dt0"), c.get("U_time"), c.get("spread_all_completed_rel"),
              flush=True)
    print("production dt0:", prod, flush=True)


# ----------------------------------------------------------------- cycle count
def _cycle_task(case):
    du, tj, src = _inputs(case)
    inc0 = json.loads(TIME_STUDY.read_text())["production_dt0_s"]
    tag = f"{case.replace(':', '_')}_N{N_CYC_LONG}_split_dt{inc0:g}"
    return dict(_solve(tag, du, tj, scratch("fc_localcyc", tag), "L0", inc0, True,
                       N_CYC_LONG), case=case, source=src)


def cycles():
    cases = ["CONTROL"] + [f"{a}:{s}" for a, s in policy_cases()]
    with mp.Pool(min(len(cases), POOL_MAX)) as pool:
        rows = pool.map(_cycle_task, cases, chunksize=1)
    study = {"policy": "local_mesh_policy.json amendment 3 (d)", "level": "L0",
             "n_cycles": N_CYC_LONG, "cases": {}}
    for r in rows:
        pc = r["per_cycle"] or []
        ok = len(pc) == N_CYC_LONG and pc[3] and pc[-1]
        study["cases"][r["case"]] = dict(
            r, U_cyc=abs(pc[-1] - pc[3]) / abs(pc[-1]) if ok else None,
            d_eps_cycle4=pc[3] if ok else None, d_eps_cycle16=pc[-1] if ok else None)
    pol = [c["U_cyc"] for k, c in study["cases"].items()
           if k != "CONTROL" and tuple(k.split(":")) in policy_cases(optional=False)]
    study["U_cyc_max_policy"] = max(pol) if pol and None not in pol else None
    keep_previous(CYCLE_STUDY)
    study["corrected_lineage"] = bool(A4)
    CYCLE_STUDY.write_text(json.dumps(study, indent=1, default=float))
    for k, c in study["cases"].items():
        print(k, c.get("U_cyc"), c.get("d_eps_cycle4"), c.get("d_eps_cycle16"), flush=True)


# ----------------------------------------------------------------- mesh family
def run_level(task):
    arch, scen, tag, inc0 = task
    du, tj, src = critical(arch, scen)
    r = _solve(f"{arch}_{scen}_{tag}", du, tj,
               scratch(SCR_MESH, f"{arch}_{scen}_{tag}"), tag, inc0, True)
    return dict(r, arch=arch, scenario=scen, source=src)


def char_size(n_xy):
    """Amendment 5: largest in-plane solder element width divided by the fixed band."""
    import math
    f = float(A5["band_frac"])
    dx = 1.0 / n_xy
    n_b = max(1, math.ceil(f / dx - 1e-9))
    n_c = max(2, round((1.0 - 2 * f) / dx))
    return max(f / n_b, (1.0 - 2 * f) / n_c) / f


def apply_policy(rows):
    """The declared rule, applied mechanically to the completed levels of one case."""
    done = [r for r in sorted(rows, key=lambda r: r["n_xy"]) if r["d_peeq_per_cycle"]]
    out = {"levels_completed": [r["level"] for r in done],
           "levels_failed": [r["level"] for r in rows if not r["d_peeq_per_cycle"]]}
    if len(done) < 3:
        return dict(out, status="unresolved", U=None, production_level=None,
                    production_value=None, note="fewer than three completed levels")
    a, b, c = done[-3:]
    v = [a["d_peeq_per_cycle"], b["d_peeq_per_cycle"], c["d_peeq_per_cycle"]]
    h = ([char_size(r["n_xy"]) for r in (a, b, c)] if A5 else
         [6.0 / a["n_xy"], 6.0 / b["n_xy"], 6.0 / c["n_xy"]])
    last = abs(v[2] - v[1]) / abs(v[2])
    out.update(production_level=c["level"], production_value=v[2],
               finest_change_rel=last, finest_three=[r["level"] for r in (a, b, c)])
    if last < TOL and c["level"] == "L3":
        return dict(out, status="converged", U=last, rule="A")
    monotone = (v[1] - v[0]) * (v[2] - v[1]) > 0
    if monotone:
        rich = _richardson(v, h)
        out["richardson"] = rich
        if rich and 0.5 <= rich["order"] <= 4.0:
            U = 1.25 * abs(v[2] - rich["extrapolated"]) / abs(rich["extrapolated"])
            return dict(out, status="bounded", U=U, rule="B (Richardson)")
        return dict(out, status="bounded", U=abs(v[2] - v[0]) / abs(v[2]),
                    rule="B (pre-asymptotic: range of the finest three)")
    return dict(out, status="unresolved", U=(max(v) - min(v)) / abs(v[2]),
                rule="C (non-monotone: range of the finest three)")


def main():
    if "--temporal" in sys.argv:
        return temporal()
    if "--cycles" in sys.argv:
        return cycles()
    ts = json.loads(TIME_STUDY.read_text())
    inc0 = ts["production_dt0_s"]
    if inc0 is None:
        raise SystemExit("the temporal study fixed no production first increment")
    cases = [tuple(c.split(":")) for c in sys.argv[1:]] or policy_cases()
    tasks = [(a, s, tag, inc0) for a, s in cases for tag in LEVELS]
    du, tj, _ = _inputs("CONTROL")
    with mp.Pool(min(len(tasks) + 1, 22, POOL_MAX)) as pool:
        ctl = pool.apply_async(_solve, ("CONTROL", du, tj, scratch(SCR_MESH, "control"),
                                        "L0", inc0, True))
        rows = pool.map(run_level, tasks, chunksize=1)
        ctl = ctl.get()
    cs = json.loads(CYCLE_STUDY.read_text())        # read late: may run concurrently
    _p1f = OUT / "local_mesh_study_pass1.json"
    p1 = json.loads(_p1f.read_text())["cases"] if _p1f.exists() else {}
    p3f = SUPERSEDED / "local_mesh_study_pass3.json"
    p3 = (json.loads(p3f.read_text())["cases"] if (A4 and p3f.exists()) else {})
    pub = LR.CONTROL["d_eps_in_stab"]
    acc = {"control": {f"pass{PASS}": ctl["d_peeq_per_cycle"], "published": pub,
                       "dev_rel": (abs(ctl["d_peeq_per_cycle"] - pub) / pub
                                   if ctl["d_peeq_per_cycle"] else None)}}
    keep_previous(OUT / "local_mesh_study.json")
    study = {"policy": "research/final_closure/local_mesh_policy.json",
             "pass": PASS, "corrected_lineage": bool(A4), "revised_lineage": bool(A5),
             "averaging_band_frac": (float(A5["band_frac"]) if A5 else None),
             "amendments_applied": sorted(AMEND),
             "initial_increment_s": inc0, "split_steps": True,
             "extraction": "block order (DEFECT #65)",
             "time_study": TIME_STUDY.name, "cycle_study": CYCLE_STUDY.name,
             "previous_passes": ["local_mesh_study_pass1.json"], "cases": {}}
    for a, s in cases:
        rr = [r for r in rows if r["arch"] == a and r["scenario"] == s]
        c = {"levels": {r["level"]: r for r in rr}, **apply_policy(rr)}
        t = ts["cases"].get(f"{a}:{s}", {})
        cy = cs["cases"].get(f"{a}:{s}", {})
        c["U_mesh"] = c["U"]
        c["U_time"] = t.get("U_time_at_production")
        c["U_cyc"] = cy.get("U_cyc") if cy.get("U_cyc") is not None else \
            cs.get("U_cyc_max_policy")
        c["U_cyc_basis"] = "own 16-cycle run" if cy.get("U_cyc") is not None else \
            "largest policy-case value"
        parts = (c["U_mesh"], c["U_time"], c["U_cyc"])
        c["U"] = sum(parts) if None not in parts else None
        old = (p1.get(f"{a}_{s}") or {}).get("levels", {})
        l0 = (c["levels"].get("L0") or {}).get("d_peeq_per_cycle")
        o0 = (old.get("L0") or {}).get("d_peeq_per_cycle")
        if A5:
            c["pass3_L0_crosscheck"] = None
        elif not A4:
            acc[f"{a}_{s}"] = {"pass3_L0": l0, "pass1_L0": o0,
                               "dev_rel": abs(l0 - o0) / o0 if (l0 and o0) else None}
        else:
            # NOT gating (not declared): a Z1 joint is unchanged by the Z2 correction, so
            # its pass-4 L0 must reproduce pass 3; a Z2 joint moved, so no comparison
            q = ((p3.get(f"{a}_{s}") or {}).get("levels", {}).get("L0") or {}).get(
                "d_peeq_per_cycle")
            c["pass3_L0_crosscheck"] = ({"pass3_L0": q, "pass4_L0": l0,
                                         "dev_rel": abs(l0 - q) / q} if (a == "Z1" and q and l0)
                                        else None)
        c["pass1_values"] = {t_: o["d_peeq_per_cycle"] for t_, o in old.items()}
        study["cases"][f"{a}_{s}"] = c
    devs = [v["dev_rel"] for v in acc.values()]
    rule = (A5 or A4 or AMEND[3])["acceptance"]
    study["acceptance"] = {"rule": rule, "checks": acc,
                           "pass": all(d is not None and d < 1e-3 for d in devs)}
    (OUT / "local_mesh_study.json").write_text(json.dumps(study, indent=1, default=float))
    print("acceptance:", study["acceptance"]["pass"], json.dumps(acc, default=float), flush=True)
    for k, c in study["cases"].items():
        print(k, c["status"], "U=%s" % (None if c["U"] is None else f"{100 * c['U']:.2f} %"),
              {t: (round(r["d_peeq_per_cycle"], 6) if r["d_peeq_per_cycle"] else None)
               for t, r in c["levels"].items()}, flush=True)


if __name__ == "__main__":
    main()
