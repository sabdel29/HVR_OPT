#!/usr/bin/env python3
"""Extract the die-surface out-of-plane displacement field of the FROZEN pair.

Nothing is solved. The displacement field written by the frozen replay is read back, the
die-top plane is selected by the same named-layer rule the production metric uses, and the
peak-to-valley is asserted against the frozen result before anything is written. The figure
generator reads only the CSV this produces, so the plotted field cannot drift from the
number the paper reports.
"""
from __future__ import annotations
import csv, importlib.util, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
REPLAY = R / "results" / "phase0mr" / "replay"
TPL = "T1C_REORDERED"
COOLER = "TOP_SI_MICROCHANNEL_27"
CASES = {"Z1": "ARCH_Z1_EMBEDDED", "Z2": "ARCH_Z2_BACKSIDE"}


def _load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main() -> int:
    rp = _load("rp", R / "scripts" / "phase0mr" / "replay_production.py")
    PE = rp.PE
    frozen = {r["case"]: r for r in
              csv.DictReader((OUT / "final_etm_replay.csv").open())}
    rc = 0
    for case, arch in CASES.items():
        d = REPLAY / f"{arch}_AFTER_{TPL}_{COOLER}" / "structural.frd"
        if not d.exists():
            print(f"  MISSING  {d.relative_to(R)} -- run scripts/phase0mr3c/run_final_replay.py")
            return 1
        msh = PE.build_global(arch, rp.H_SUB[arch], h_xy=0.80)
        msh = msh[0] if isinstance(msh, tuple) else msh
        U = PE.ccxio.read_frd(d)["DISP"]
        ids = msh.node_ids_at_z(msh.layer("die").z1)
        p = msh.node_xyz(ids) if hasattr(msh, "node_xyz") else msh.nodes[ids]
        uz = U[ids, 2] * 1000.0                                   # mm -> um
        pv = float(np.nanmax(uz) - np.nanmin(uz))
        want = float(frozen[case]["die_warpage_pv_um"])
        if abs(pv - want) > 1e-6:
            print(f"  FAIL  {case}: field p-v {pv:.6f} um against frozen {want:.6f} um")
            rc = 1; continue
        f = OUT / f"die_surface_field_{case}.csv"
        with f.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["x_mm", "y_mm", "uz_um"])
            for (x, y, _z), v in zip(p, uz):
                w.writerow([f"{x:.6f}", f"{y:.6f}", f"{v:.9f}"])
        # the driver band, so the figure can show where the corner metric is read
        r = np.hypot(p[:, 0] - p[:, 0].mean(), p[:, 1] - p[:, 1].mean())
        print(f"  ok    {case}: {len(ids)} die-top nodes, p-v {pv:.4f} um "
              f"= frozen, r_max {r.max():.3f} mm -> {f.name}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
