"""Run one AEDT / PyAEDT job as a tracked subprocess.

Another project on this host runs AEDT under the same account, so a left-over
ansysedt process can never be identified by name. The job's descendants are recorded
(PID plus kernel start time) while it runs, and after it exits or times out ONLY those
recorded processes are ever signalled. Output goes to a scratch log, never to the repo:
AEDT and PyAEDT logs carry licence-server details.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path


def _stat(pid):
    """(ppid, starttime) of a live process, or None."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            s = f.read()
    except OSError:
        return None
    rest = s[s.rfind(")") + 2:].split()
    return int(rest[1]), int(rest[19])


def descendants(root):
    kids = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            st = _stat(int(d))
            if st:
                kids.setdefault(st[0], []).append((int(d), st[1]))
    out, stack = {}, [root]
    while stack:
        p = stack.pop()
        for c, start in kids.get(p, []):
            if c not in out:
                out[c] = start
                stack.append(c)
    return out


def _alive(pid, start):
    st = _stat(pid)
    return bool(st and st[1] == start)


def _cmd(pid):
    try:
        return open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode()[:120]
    except OSError:
        return ""


def run_tracked(cmd, log, timeout_s, env=None, cwd=None, poll_s=3.0):
    """Run `cmd`; return a dict with rc, wall_s, timed_out and what was cleaned up."""
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    seen = {}
    t0 = time.time()
    with open(log, "w") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=cwd,
                             start_new_session=True)
        seen[p.pid] = _stat(p.pid)[1] if _stat(p.pid) else 0
        timed_out = False
        while p.poll() is None:
            seen.update(descendants(p.pid))
            if time.time() - t0 > timeout_s:
                timed_out = True
                break
            time.sleep(poll_s)
        wall = time.time() - t0
        killed = []
        if timed_out:
            for pid, start in sorted(seen.items(), reverse=True):
                if _alive(pid, start):
                    killed.append({"pid": pid, "cmd": _cmd(pid).split(" ")[0]})
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        pass
            time.sleep(10)
            for pid, start in seen.items():
                if _alive(pid, start):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
            try:
                p.wait(30)
            except subprocess.TimeoutExpired:
                pass
    # a job that exited normally can still leave its own AEDT behind
    time.sleep(5)
    leftovers = []
    for pid, start in seen.items():
        if pid != p.pid and _alive(pid, start):
            leftovers.append({"pid": pid, "cmd": _cmd(pid).split(" ")[0]})
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    if leftovers:
        time.sleep(10)
        for pid, start in seen.items():
            if pid != p.pid and _alive(pid, start):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
    return {"rc": p.returncode, "wall_s": wall, "timed_out": timed_out,
            "killed_on_timeout": killed, "leftovers_terminated": leftovers,
            "tracked_pids": sorted(seen)}


def scratch_env(work):
    """Environment for PyAEDT jobs: every temp file in the AEDT scratch tree."""
    work = Path(work)
    (work / "tmp").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(TMPDIR=str(work / "tmp"), TMP=str(work / "tmp"), TEMP=str(work / "tmp"),
               AEDT_WORK=str(work))
    env["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + env.get("PATH", "")
    return env
