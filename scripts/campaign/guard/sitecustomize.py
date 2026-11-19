"""Campaign write guard, loaded through PYTHONPATH by `scripts/campaign/run.py exec-job`.

Active only when ETM_RESULTS_ROOT is set (a campaign job). It makes the output-root hooks
fail-safe instead of trusting that every producer was hooked:

  * a write into the FROZEN result trees of the repository -- research/, results/,
    manuscript_v2/ and presentation/ (except the campaign root itself, which may live inside
    research/) -- raises PermissionError: open for writing, os.remove/unlink/rmdir/truncate,
    rename/replace onto or out of them. Creating an empty directory is allowed (several
    modules mkdir solver scratch under results/ at import; that overwrites nothing);
  * every read of a frozen research/ or results/ file is appended to
    $ETM_RESULTS_ROOT/_campaign/frozen_reads/<ETM_JOB_ID>.txt, so the runner can tell a
    static input (expected) from a computed artifact the campaign should have produced
    itself (a missing dependency or an unhooked reader).

It changes no computation; a job that never touches the frozen trees behaves identically.
Child Python processes (multiprocessing, subprocess) inherit PYTHONPATH and the guard.
"""
import os
import sys


def _install():
    root = os.environ.get("ETM_RESULTS_ROOT", "").strip()
    repo = os.environ.get("ETM_REPO", "").strip()
    if not root or not repo:
        return
    repo = os.path.realpath(repo)
    root = os.path.realpath(root if os.path.isabs(root) else os.path.join(repo, root))
    frozen = tuple(os.path.join(repo, d) + os.sep
                   for d in ("research", "results", "manuscript_v2", "presentation"))
    readlog_prefixes = frozen[:2]
    allow = (root + os.sep,)
    job = os.environ.get("ETM_JOB_ID", "adhoc").replace(os.sep, "_")
    # a design-subroot job (TCPMT round 3) logs into the campaign's own state directory
    state = os.environ.get("ETM_CAMPAIGN_STATE", "").strip()
    log_dir = os.path.join(state or os.path.join(root, "_campaign"), "frozen_reads")
    seen = set()
    W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def _abs(p):
        try:
            s = os.fsdecode(p)
        except TypeError:
            return None
        return os.path.realpath(s) if s else None

    def _frozen(s):
        return s is not None and (s + os.sep).startswith(frozen) and \
            not (s + os.sep).startswith(allow)

    def _note_read(s):
        if s in seen or not (s + os.sep).startswith(readlog_prefixes):
            return
        if (s + os.sep).startswith(allow) or s.endswith((".py", ".pyc")):
            return
        seen.add(s)
        try:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, job + ".txt"), "a") as f:
                f.write(os.path.relpath(s, repo) + "\n")
        except OSError:
            pass

    def hook(event, args):
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            if isinstance(path, int) or path is None:
                return
            s = _abs(path)
            w = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                (isinstance(flags, int) and bool(flags & W))
            if _frozen(s):
                if w:
                    raise PermissionError(
                        f"[campaign guard] refusing to write {s}: frozen results tree "
                        f"(ETM_RESULTS_ROOT={root}); the producer needs an output-root hook")
                _note_read(s)
        elif event in ("os.remove", "os.rmdir", "os.truncate"):
            s = _abs(args[0]) if args else None
            if _frozen(s):
                raise PermissionError(f"[campaign guard] refusing {event} on {s}")
        elif event in ("os.rename", "os.link", "os.symlink"):
            for p in args[:2]:
                s = _abs(p)
                if event != "os.rename" and p is args[0]:
                    continue                     # link source may be frozen (read-only use)
                if _frozen(s):
                    raise PermissionError(f"[campaign guard] refusing {event} onto {s}")

    sys.addaudithook(hook)


_install()
