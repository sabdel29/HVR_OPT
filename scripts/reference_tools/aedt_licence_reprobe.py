"""One-time licence re-probe of the AEDT solvers that matter to the reference programme.

Runs the EXISTING probe scripts unchanged, once each, on their tiny models:
  Q3D Extractor DC          scripts/reference_tools/q3d_smoke.py           (Cu bar, DCR)
  Icepak                    scripts/reference_tools/aedt_licence_probe2.py (1 W Al block)
probe2 also runs its Maxwell 3D DC branch first; it is recorded for what it is.
aedt_licence_probe.py's Icepak branch calls create_source_block, which PyAEDT 1.1 no
longer has, so probe2's Icepak branch (assign_solid_block) is the one re-run.

Raw logs stay in the scratch tree (they carry licence-server details). The JSON written
here holds only booleans, timings and an error class in our own words, derived from
keyword flags over (a) the PyAEDT stdout log and (b) AEDT's own batch.log in the probe's
project folder -- AEDT reports licence failures only in (b).

    python aedt_licence_reprobe.py               run the probes once, classify, write JSON
    python aedt_licence_reprobe.py --reclassify  re-derive the classes from the SAME scratch
                                                 logs and the recorded run (no probe re-run)

If Q3D solves, q3d_dc_reference.py is run as designed; otherwise its status stays
READY_NOT_EXECUTED -- LICENSE UNAVAILABLE.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from aedt_proc import run_tracked, scratch_env                       # noqa: E402

R = HERE.parents[1]
OUT = R / "research" / "final_closure" / "aedt_licence_reprobe.json"
WORK = Path(os.environ.get("AEDT_WORK", Path.home() / "claude_scratch" / "aedt_work"))
PROBE = WORK / "reprobe"


def _lines(path):
    try:
        return Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return None


def flags(pyaedt_log, batch_log, project=None, pyaedt_segment=None):
    """Keyword flags; no log text leaves this function.

    project: AEDT project name whose batch.log lines are kept ('Project:<name>').
    pyaedt_segment: 'before' / 'after' the first PyAEDT line naming the Icepak design
    (probe2 runs Maxwell first, then Icepak, in one process).
    Python traceback lines (which quote file names such as aedt_licence_probe2.py) are
    excluded from the licence keyword scan."""
    py = _lines(pyaedt_log)
    ba = _lines(batch_log)
    out = {"pyaedt_log_present": py is not None, "batch_log_present": ba is not None}
    py = py or []
    if pyaedt_segment:
        k = next((i for i, ln in enumerate(py) if "of type icepak" in ln.lower()), None)
        py = py[:k] if (pyaedt_segment == "before" and k is not None) else \
            py[k:] if (pyaedt_segment == "after" and k is not None) else py
        out["pyaedt_segment_split_found"] = k is not None
    ba = ba or []
    if project:
        own = [ln for ln in ba if f"project:{project}" in ln.lower()]
        # FlexNet detail lines carry no project tag; keep them only if this project
        # itself reported an AEDT error
        fx = [ln for ln in ba if ln.lower().startswith(("feature:", "flexnet"))]
        ba = own + (fx if any("[error]" in ln.lower() for ln in own) else [])
    aedt_err = [ln.lower() for ln in ba if "[error]" in ln.lower() or
                ln.lower().startswith("flexnet")]
    tb = [ln for ln in py if 'file "' in ln.lower() or ln.strip().startswith("^")]
    py_err = [ln.lower() for ln in py if "error" in ln.lower() and ln not in tb]
    out.update({
        "aedt_error_lines": len(aedt_err),
        "no_such_feature": any("no such feature" in ln for ln in aedt_err),
        "terminated_by_licence_error": any("terminated by license error" in ln
                                          or "terminated by licence error" in ln
                                          for ln in aedt_err),
        "flexnet_error_line": any(ln.startswith("flexnet") for ln in aedt_err),
        "aedt_execution_error": any("execution error" in ln for ln in aedt_err),
        "aedt_normal_completion": any("normal completion of simulation" in ln.lower()
                                      for ln in ba),
        "pyaedt_solve_started": any("solving design setup" in ln.lower() for ln in py),
        "pyaedt_solve_error": any("error in solving setup" in ln for ln in py_err),
        "python_exception_in_probe": bool(tb),
        "pyaedt_api_mismatch": any(("unexpected keyword argument" in ln
                                    or "keyerror" in ln) for ln in py_err)
        or any("default_setup" in ln for ln in py)})
    return out


def error_class(f, solved, timed_out):
    if solved:
        return None
    if timed_out:
        return "probe exceeded its time limit; no solve result"
    if f.get("no_such_feature") or f.get("terminated_by_licence_error"):
        return ("FlexNet: feature not available -- the solver's licence feature does not "
                "exist on the licence server, so AEDT terminated the solve with a licence "
                "error; desktop launch and model build were unaffected")
    if f.get("python_exception_in_probe") and not f.get("pyaedt_solve_started"):
        return ("not a licence result: the existing probe script raised an exception before "
                "reaching the solve (PyAEDT 1.1 API mismatch in that branch); no licence "
                "request for this solver was made")
    if f.get("aedt_execution_error"):
        return "solver execution error without a licence message"
    return "no solve result and no classifiable message"


def classify(out):
    q = out["probes"]["q3d_extractor_dc"]
    fq = flags(PROBE / "q3d_smoke.log", PROBE / "q3d" / "batch.log", project="smoke")
    q["flags"] = fq
    q["error_class"] = error_class(fq, q["solved"], q.get("timed_out"))
    p2 = {}
    if (PROBE / "probe2" / "probe2.json").exists():
        p2 = json.loads((PROBE / "probe2" / "probe2.json").read_text())
    for key, tag, proj, seg in (("maxwell_dc", "maxwell3d_dc_conduction", "mx2", "before"),
                                ("icepak", "icepak", "ip2", "after")):
        e = out["probes"][tag]
        f = flags(PROBE / "probe2.log", PROBE / "probe2" / "batch.log", project=proj,
                  pyaedt_segment=seg)
        e["flags"] = f
        e["solved"] = bool(p2.get(key, {}).get("solved"))
        e["error_class"] = error_class(f, e["solved"], out["probe2_run"]["timed_out"])
    m = out["probes"]["maxwell3d_dc_conduction"]
    m["note"] = ("Not asked for by this re-probe; probe2 simply runs it before Icepak. Its "
                 "result here is not a licence result (see error_class). The Maxwell DC "
                 "licence status therefore rests on the earlier probe recorded in "
                 "aedt_common.py / tool_evidence/README.md and was not re-tested now.")
    return out


def run_probes():
    PROBE.mkdir(parents=True, exist_ok=True)
    env = scratch_env(WORK)
    py = "/home/beams0/MGHARIB/envs/etm/bin/python"
    out = {"date": dt.date.today().isoformat(),
           "started_local": dt.datetime.now().isoformat(timespec="seconds"),
           "aedt_version": "2026.1 (AEDT 2026 R1)", "pyaedt": "ansys.aedt.core 1.1.0",
           "host_os": platform.platform(), "probes": {}}
    qd = PROBE / "q3d"
    qd.mkdir(exist_ok=True)
    run = run_tracked([py, str(HERE / "q3d_smoke.py"), str(qd)], PROBE / "q3d_smoke.log",
                      timeout_s=1200, env=env, cwd=str(qd))
    res = json.loads((qd / "smoke_result.json").read_text()) \
        if (qd / "smoke_result.json").exists() else {}
    val = res.get("value")
    solved = isinstance(val, (int, float)) and math.isfinite(val) and val > 0
    out["probes"]["q3d_extractor_dc"] = {
        "script": "scripts/reference_tools/q3d_smoke.py (unchanged)",
        "model": "copper bar 1 x 0.1 x 0.01 mm, source/sink on the end faces, DC only",
        "desktop_launched_and_project_written": (qd / "smoke.aedt").exists(),
        "solved": bool(solved), "dcr_value": val if solved else None,
        "dcr_units": res.get("units") if solved else None,
        "build_s": res.get("build_s"), "solve_call_s": res.get("solve_s"),
        "wall_s": round(run["wall_s"], 1), "exit_code": run["rc"],
        "timed_out": run["timed_out"],
        "own_processes_cleaned_up": len(run["leftovers_terminated"]) + len(run["killed_on_timeout"])}
    pd = PROBE / "probe2"
    pd.mkdir(exist_ok=True)
    run2 = run_tracked([py, str(HERE / "aedt_licence_probe2.py"), str(pd)],
                       PROBE / "probe2.log", timeout_s=1800, env=env, cwd=str(pd))
    p2 = json.loads((pd / "probe2.json").read_text()) if (pd / "probe2.json").exists() else {}
    for key, tag, model in (("maxwell_dc", "maxwell3d_dc_conduction",
                             "copper bar 1 x 0.1 x 0.01 mm, current/voltage on the end faces"),
                            ("icepak", "icepak",
                             "10 x 10 x 1 mm Al-Extruded block, 1 W solid block, steady, "
                             "conduction only (flow and gravity off)")):
        r = p2.get(key, {})
        out["probes"][tag] = {
            "script": "scripts/reference_tools/aedt_licence_probe2.py (unchanged)",
            "model": model, "solved": bool(r.get("solved")),
            "licence_messages_counted_by_probe": r.get("licence_errors"),
            "build_s": r.get("build_s"), "solve_s": r.get("solve_s")}
    out["probe2_run"] = {"wall_s": round(run2["wall_s"], 1), "exit_code": run2["rc"],
                         "timed_out": run2["timed_out"],
                         "own_processes_cleaned_up": len(run2["leftovers_terminated"])
                         + len(run2["killed_on_timeout"])}
    out["finished_local"] = dt.datetime.now().isoformat(timespec="seconds")
    return out


def finish(out):
    out["policy"] = ("Each probe ran once, as an unchanged existing script, in a tracked "
                     "subprocess. Raw AEDT/PyAEDT logs are kept in scratch only because they "
                     "contain licence-server details; error classes are paraphrased from "
                     "keyword flags over the PyAEDT log and AEDT's batch.log, never copied.")
    if out["probes"]["q3d_extractor_dc"]["solved"]:
        if "q3d_dc_reference" not in out or out["q3d_dc_reference"].get("status", "").startswith("READY"):
            env = scratch_env(WORK)
            rd = WORK / "q3d_ref"
            rd.mkdir(exist_ok=True)
            r3 = run_tracked(["/home/beams0/MGHARIB/envs/etm/bin/python",
                              str(HERE / "q3d_dc_reference.py"), "tsv", str(rd)],
                             PROBE / "q3d_dc_reference.log", timeout_s=2400, env=env,
                             cwd=str(rd))
            last = None
            for ln in (_lines(PROBE / "q3d_dc_reference.log") or []):
                if ln.startswith("{") and '"case"' in ln:
                    last = json.loads(ln)
            out["q3d_dc_reference"] = {
                "status": "EXECUTED" if last else "FAILED",
                "script": "scripts/reference_tools/q3d_dc_reference.py tsv", "result": last,
                "rho_L_over_A_ohm_at_5.8e7_S_per_m": 300e-6 / (5.8e7 * math.pi * 15e-6 ** 2),
                "wall_s": round(r3["wall_s"], 1), "exit_code": r3["rc"]}
    else:
        out["q3d_dc_reference"] = {
            "status": "READY_NOT_EXECUTED — LICENSE UNAVAILABLE",
            "script": "scripts/reference_tools/q3d_dc_reference.py",
            "reason": "the Q3D probe did not solve (licence feature not available)"}
    out["summary"] = {k: {"solved": v["solved"], "error_class": v["error_class"]}
                      for k, v in out["probes"].items()}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["summary"], indent=1))
    print("q3d_dc_reference:", out["q3d_dc_reference"]["status"])


def main():
    if "--reclassify" in sys.argv:
        out = json.loads(OUT.read_text())
        out["reclassified_local"] = dt.datetime.now().isoformat(timespec="seconds")
        out["reclassification_note"] = (
            "Classes re-derived from the same scratch logs after the run; no probe was "
            "re-run. The first pass scanned only the PyAEDT stdout log (AEDT's licence "
            "message is written to batch.log) and miscounted the probe's own file name, "
            "aedt_licence_probe2.py, as a licence keyword.")
    else:
        out = run_probes()
    finish(classify(out))


if __name__ == "__main__":
    main()
