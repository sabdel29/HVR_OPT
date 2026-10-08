#!/usr/bin/env python3
"""Phase-0F: the 1-kW candidate sweep (Sec. 4, 8, 9, 12, 14).

Every case passes the geometry gate first, uses the 1-kW cooling calibration, and runs a full
ET fixed point with per-VR local temperature.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from placement0f import build as build0f, max_compaction
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0f"
DIE, KEEP, GAP = 22.36, 0.5, 0.5


def placeable(n_vr, side):
    try:
        build0f("uniform", n_vr, side, DIE, KEEP, GAP); return True
    except Exception:
        return False


def main():
    stack, doe = load_stack(), load_doe()
    cal = json.loads((OUT / "cooling_1kw_calibration.json").read_text())
    h_top = cal["h_top_W_m2K"]
    wd = OUT / "runs_1kw"
    rows = []

    cases = []
    # --- Sec.4: thickness x architecture, the crossover test -----------------------------
    for arch in ("ARCH_A", "ARCH_B"):
        for h in (0.8, 1.0, 1.25, 1.5, 2.0):
            cases.append(("thickness", arch, "uniform", kw1.M_VR, kw1.J_TARGET, h))
    # --- Sec.8: footprint, swept by total HVR area ---------------------------------------
    for M, j in ((25, 4.0), (36, 3.0), (49, 3.0), (49, 3.5)):
        cases.append(("footprint", "ARCH_A", "uniform", M, j, 1.5))
    # --- Sec.9: placement ------------------------------------------------------------------
    for fam in ("uniform", "compact", "asymmetric"):
        cases.append(("placement", "ARCH_A", fam, kw1.M_VR, kw1.J_TARGET, 1.5))

    seen = set()
    for grp, arch, fam, M, j, h in cases:
        key = (arch, fam, M, j, h)
        if key in seen:
            rows.append({**next(r for r in rows if r.get("_key") == str(key)), "group": grp})
            continue
        seen.add(key)
        des, g, why = kw1.design_1kw(M, j, h)
        if des is None:
            rows.append({"group": grp, "arch": arch, "fam": fam, "m_vr": M, "j": j,
                         "h_sub_mm": h, "feasible": False, "reason": why, "_key": str(key)})
            print(f"  {grp:10s} {arch} {fam:10s} M={M:3d} j={j:.1f} h={h:.2f}  "
                  f"GEOMETRY INFEASIBLE: {why}", flush=True)
            continue
        side = math.sqrt(des.area_mm2)
        if not placeable(M, side):
            rows.append({"group": grp, "arch": arch, "fam": fam, "m_vr": M, "j": j,
                         "h_sub_mm": h, "feasible": False,
                         "reason": f"{M} tiles of {side:.3f} mm cannot be placed",
                         "_key": str(key)})
            print(f"  {grp:10s} {arch} {fam:10s} M={M:3d} j={j:.1f} h={h:.2f}  "
                  f"NOT PLACEABLE (side {side:.3f} mm)", flush=True)
            continue
        t0 = time.time()
        r = kw1.coupled_1kw(arch, fam, h, h_top, stack, doe, wd, m_vr=M, j=j, bc="BC_A")
        meta = kw1.placement_meta(fam, side, stack, doe, M)
        r.update({"group": grp, "_key": str(key), "placement_scale": meta["scale"],
                  "compaction_headroom_pct": meta["compaction_headroom_pct"]})
        rows.append(r)
        print(f"  {grp:10s} {arch} {fam:10s} M={M:3d} j={j:.1f} h={h:.2f}  "
              f"P_conv={r['P_conv_w']:7.2f} P_pdn={r['P_pdn_w']:6.3f} "
              f"P_el={r['P_elec_total_w']:7.2f} eta={r['efficiency_pct']:5.2f}% "
              f"Tmax={r['T_max_C']:6.2f} w={r['die_warpage_pv_um']:7.3f}um "
              f"n_alloc={r.get('n_tsv_alloc')} ({time.time()-t0:.0f}s)", flush=True)

    for r in rows:
        r.pop("_key", None); r.pop("history", None)
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "1kw_candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'1kw_candidates.csv'} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
