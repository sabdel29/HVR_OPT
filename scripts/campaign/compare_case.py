#!/usr/bin/env python3
"""Compare a campaign ETM case file with the frozen one of the same name (smoke tests).

    python scripts/campaign/compare_case.py CAMPAIGN_ROOT REL [REL ...]
      REL = path below the results root, e.g. final_closure/etm_Z1_HV_S0_h1.1.json

Walks both JSON trees and reports every numeric leaf that differs (absolute and relative),
ignoring wall-clock and host fields; prints the headline observables side by side.
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKIP = ("wall_s", "et_wall_s", "threads", "structural_threads", "hardware", "load_average")
HEAD = [("P_loss_w", ("P_loss_w",)), ("T_max_C", ("thermal", "T_max_C")),
        ("energy_residual_rel", ("thermal", "energy_residual_rel")),
        ("E-T iterations", None),
        ("die_warpage_pv_um", ("mechanics", "die_warpage_pv_um")),
        ("pkg_warpage_pv_um", ("mechanics", "pkg_warpage_pv_um")),
        ("du_c_um", ("mechanics", "joint_search", "critical", "du_um")),
        ("T_joint_C", ("mechanics", "joint_search", "critical", "T_C")),
        ("n_elems", ("thermal", "n_elems"))]


def get(d, path):
    for k in path:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in SKIP:
                continue
            if k not in a or k not in b:
                out.append((path + "/" + k, "only in " + ("campaign" if k in a else "frozen"), None))
                continue
            walk(a[k], b[k], path + "/" + k, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"length {len(a)} vs {len(b)}", None))
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and \
            not isinstance(a, bool):
        if a != b and not (math.isnan(a) and math.isnan(b)):
            rel = abs(a - b) / max(abs(b), 1e-300)
            out.append((path, f"{a!r} vs {b!r}", rel))
    elif a != b:
        out.append((path, f"{str(a)[:40]!r} vs {str(b)[:40]!r}", None))


def main():
    root = Path(sys.argv[1])
    for rel in sys.argv[2:]:
        a = json.loads((root / rel).read_text())
        b = json.loads((REPO / "research" / rel).read_text())
        print(f"== {rel}\n   {'observable':22s} {'campaign':>18s} {'frozen':>18s}")
        for name, p in HEAD:
            va = len(a["et_history"]) if p is None else get(a, p)
            vb = len(b["et_history"]) if p is None else get(b, p)
            print(f"   {name:22s} {va!s:>18.18} {vb!s:>18.18}")
        diffs = []
        walk(a, b, "", diffs)
        num = [d for d in diffs if d[2] is not None]
        oth = [d for d in diffs if d[2] is None]
        print(f"   numeric leaves differing: {len(num)}; max rel diff "
              f"{max((d[2] for d in num), default=0.0):.3e}; non-numeric differences: {len(oth)}")
        for d in sorted(num, key=lambda d: -d[2])[:8]:
            print(f"     {d[0]}: {d[1]} (rel {d[2]:.2e})")
        for d in oth[:8]:
            print(f"     {d[0]}: {d[1]}")


if __name__ == "__main__":
    main()
