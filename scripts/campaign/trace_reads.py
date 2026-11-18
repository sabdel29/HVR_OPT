"""Record every file a Python script opens, stats, lists or globs (inventory tool).

    python scripts/campaign/trace_reads.py --out trace.jsonl [--keep PREFIX ...] -- \
        SCRIPT.py [ARGS ...]

The script runs unchanged in this interpreter (runpy, __name__ == "__main__"); an audit hook
records ``open`` / ``os.listdir`` / ``os.scandir`` / ``glob.glob`` events and a wrapper on
``os.stat`` records existence probes (Path.exists / is_file / os.path.exists all go
through it), including probes of files that do not exist. One JSON line per distinct
(kind, path):  {"kind": "read"|"write"|"stat"|"list"|"glob", "path": ..., "exists": bool}.

Only paths under a --keep prefix are recorded (default: the repository and the project
scratch tree); interpreter, site-packages and bytecode files never are. Used to build the
artifact inventory behind scripts/campaign/manifest.yaml; it does not change what the
traced script computes or writes.
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_KEEP = (str(REPO), "/home/beams0/SABDELZAHER/ETM_project")
SKIP_SUFFIX = (".py", ".pyc", ".pyi", ".so", ".pth")
SKIP_PART = ("__pycache__", "site-packages", "/.git/", "/envs/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", action="append", default=None)
    ap.add_argument("script")
    ap.add_argument("args", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    keep = tuple(a.keep or DEFAULT_KEEP)
    seen: dict = {}
    real_stat = os.stat

    def _probe(p, want_dir=False):
        import stat as st
        try:
            m = real_stat(p).st_mode
        except (OSError, TypeError, ValueError):
            return False
        return st.S_ISDIR(m) if want_dir else True

    def note(kind, p, exists=None):
        try:
            s = os.fsdecode(p) if not isinstance(p, int) else None
        except TypeError:
            return
        if not s:
            return
        s = os.path.abspath(s)
        if not s.startswith(keep) or s.endswith(SKIP_SUFFIX) or any(x in s for x in SKIP_PART):
            return
        k = (kind, s)
        if k not in seen or (exists and not seen[k]):
            seen[k] = exists

    def hook(event, args):
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            w = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
            if isinstance(path, (str, bytes, os.PathLike)):
                note("write" if w else "read", path, None if w else _probe(path))
        elif event in ("os.listdir", "os.scandir") and args and args[0] is not None:
            note("list", args[0], _probe(args[0], True))
        elif event == "glob.glob" and args:
            note("glob", args[0], None)

    def stat(path, *args, **kw):
        try:
            r = real_stat(path, *args, **kw)
        except OSError:
            if not isinstance(path, int):
                note("stat", path, False)
            raise
        if not isinstance(path, int):
            note("stat", path, True)
        return r

    sys.addaudithook(hook)
    os.stat = stat
    script = os.path.abspath(a.script)
    sys.argv = [script] + [x for x in a.args if x != "--"]
    sys.path.insert(0, os.path.dirname(script))
    rc = 0
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as e:                     # the traced script's own exit code
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException as e:                  # noqa: BLE001 - record and keep the trace
        print(f"[trace_reads] {script} raised {type(e).__name__}: {e}", file=sys.stderr)
        rc = 1
    finally:
        os.stat = real_stat
        with open(a.out, "w") as f:
            for (kind, p), ex in sorted(seen.items()):
                f.write(json.dumps({"kind": kind, "path": p, "exists": ex}) + "\n")
    sys.exit(rc)


if __name__ == "__main__":
    main()
