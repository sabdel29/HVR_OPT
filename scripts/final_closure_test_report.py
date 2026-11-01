"""Run the full test suite on the CURRENT commit -- clean, and with --note also identical to
its pushed upstream -- and record the result OUTSIDE the tracked tree: a copy in
$HVR_SCRATCH and, with --note, a git note on the tested commit (refs/notes/test-reports).

A tracked report cannot name the commit that contains it: committing it creates a new SHA
whose own state was never tested, and a report on that commit would need another commit
(final brief Part 30). So nothing in the tree is written here, and
research/final_closure/final_test_report.txt only states where the result lives. The run
must also leave the tracked tree clean -- a test that rewrites a tracked file fails the
report.

    python scripts/final_closure_test_report.py           # run on HEAD, print, scratch copy
    python scripts/final_closure_test_report.py --note    # HEAD must equal its upstream;
                                                          # attaches the git note
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SCR = Path(os.environ.get("HVR_SCRATCH", Path.home() / "claude_scratch" / "hvr_work"))
NOTES_REF = "test-reports"


def git(*a):
    return subprocess.run(["git", *a], cwd=R, capture_output=True, text=True).stdout.strip()


def dirty():
    return [ln for ln in git("status", "--porcelain", "--untracked-files=no").splitlines()
            if not ln.endswith("Scalable_Integrated_VR")]


def ci_note():
    """What is true about CI for the tested tree: derived from git, never assumed."""
    tracked = git("ls-files", ".github/workflows")
    if tracked:
        return f"the workflow ({tracked}) is committed in the tested tree."
    return ("no workflow is committed in the tested tree (the push credential lacks the "
            "'workflow' scope), so no CI ran.")


def main():
    note = "--note" in sys.argv
    before = dirty()
    if before:
        raise SystemExit("tracked files modified -- commit first so the SHA names the tested "
                         "code:\n" + "\n".join(before))
    sha = git("rev-parse", "HEAD")
    upstream = git("rev-parse", "@{u}")
    if note and sha != upstream:
        raise SystemExit(f"HEAD {sha} is not its upstream {upstream}: push and fetch first")
    SCR.mkdir(parents=True, exist_ok=True)
    xml = SCR / "pytest_final.xml"
    cmd = [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
           f"--basetemp={SCR / 'pytest_final_tmp'}", f"--junitxml={xml}", "-rfE"]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=R, capture_output=True, text=True)
    wall = time.time() - t0
    after = dirty()
    root = ET.parse(xml).getroot()
    ts = root if root.tag == "testsuite" else root.find("testsuite")
    n = {k: int(ts.get(k, 0)) for k in ("tests", "failures", "errors", "skipped")}
    xfailed = 0
    failed_ids = []
    for tc in ts.iter("testcase"):
        sk = tc.find("skipped")
        if sk is not None and "xfail" in (sk.get("type", "") + sk.get("message", "")).lower():
            xfailed += 1
        if tc.find("failure") is not None or tc.find("error") is not None:
            failed_ids.append(f"{tc.get('classname')}::{tc.get('name')}")
    passed = n["tests"] - n["failures"] - n["errors"] - n["skipped"]
    tail = "\n".join(p.stdout.strip().splitlines()[-3:])
    lines = [
        "HVR_OPT final test report (scripts/final_closure_test_report.py)",
        "",
        f"tested commit   : {sha}",
        f"upstream        : {upstream} ({'identical' if sha == upstream else 'DIFFERENT'})",
        "tracked tree    : clean before the run; "
        + ("clean after it" if not after else "MODIFIED by the run: " + "; ".join(after)),
        f"command         : {' '.join(cmd[1:]).replace(str(SCR), '$HVR_SCRATCH')}",
        f"python          : {platform.python_version()} ({sys.executable})",
        f"platform        : {platform.platform()}",
        f"started         : {time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(t0))}",
        f"duration        : {wall:.1f} s",
        "",
        f"collected       : {n['tests']}",
        f"passed          : {passed}",
        f"failed          : {n['failures']}",
        f"errors          : {n['errors']}",
        f"skipped         : {n['skipped'] - xfailed}",
        f"xfailed         : {xfailed}",
        "",
        "pytest summary  :",
        tail,
        "",
        "failing tests   : " + (", ".join(failed_ids) if failed_ids else "none"),
        "",
        "CI: " + ci_note() + " This report is a local run.",
    ]
    text = "\n".join(lines) + "\n"
    out = SCR / f"final_test_report_{sha[:12]}.txt"
    out.write_text(text)
    print(text)
    print("wrote", out)
    ok = n["failures"] == 0 and n["errors"] == 0 and not after
    if note:
        subprocess.run(["git", "notes", f"--ref={NOTES_REF}", "add", "-f", "-F", str(out),
                        sha], cwd=R, check=True)
        print(f"attached as git note refs/notes/{NOTES_REF} on {sha}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
