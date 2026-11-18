#!/usr/bin/env python3
"""Build the DSE engine directory a campaign sweep runs against (HVR_DSE_ENGINE).

The published sweeps ran against hand-copied engine folders (scratch/dse_engine,
scratch/dse_engine_caprule) that no script built. This makes the copy reproducible: the
five modules research/tcpmt_revision/dse_j35/sweep_etm.py actually loads (relative to the
engine directory, which it chdirs into) are copied from THIS checkout, and ENGINE.json
records their md5 and the git commit. With HVR_CAP_RULE=legacy the HEAD engine reproduces
the published etm35 sweep byte for byte (inventory, 2026-11-18).

    python scripts/campaign/build_dse_engine.py DEST
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FILES = ["Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py",
         "Scalable_Integrated_VR/src/HVR_FULL_OPT_sizing.py",
         "Scalable_Integrated_VR/src/Framework_w_HVR_OPT_sizing_v2.py",
         "Scalable_Integrated_VR/src/HVR_capacitor_vendor_data.json",
         "Scalable_Integrated_VR/EPC-Product-Table.csv"]
#: imported by sweep_etm.py from outside the repository (not vendored): recorded, not copied
EXTERNAL = "/home/beams0/SABDELZAHER/Salma_Thesis/analysis/system_partitioning_comparison/scripts/paper_routing.py"


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def main():
    dest = Path(sys.argv[1])
    dest.mkdir(parents=True, exist_ok=True)
    rec = {}
    for rel in FILES:
        src = REPO / rel
        shutil.copy2(src, dest / src.name)
        if md5(src) != md5(dest / src.name):
            raise SystemExit(f"copy of {rel} differs")
        rec[src.name] = {"from": rel, "md5": md5(src)}
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                              text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "Scalable_Integrated_VR"],
                               cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        head, dirty = None, None
    ext = Path(EXTERNAL)
    (dest / "ENGINE.json").write_text(json.dumps(
        {"repo": str(REPO), "commit": head, "engine_tree_dirty": bool(dirty), "files": rec,
         "external_paper_routing": {"path": EXTERNAL,
                                    "md5": md5(ext) if ext.exists() else None}}, indent=1))
    print(f"engine at {dest} from {head} ({'dirty' if dirty else 'clean'}): "
          + ", ".join(f"{k} {v['md5'][:8]}" for k, v in rec.items()))


if __name__ == "__main__":
    main()
