#!/usr/bin/env python3
"""Phase-0G Sec.6/7: is the reversal caused by board STIFFNESS or by CLAMPING KINEMATICS?

The compact BC-B foundation fixes ALL THREE degrees of freedom on the underside plane. A BGA
field does not: solder balls are compliant in shear, so a mounted package can still expand
in-plane relative to the board. Two diagnostics separate the two effects:

  BC_B   clamped plane  (all 3 DOF)          -- what Phases 0C-0F used
  BC_BZ  vertical-only foundation + 3-2-1    -- a true Winkler support
  BC_A   3-2-1 only                          -- free package

If the reversal is a stiffness effect it must vanish as k -> 0 in BOTH BC_B and BC_BZ. The
support sweep already showed BC_B never reaches the free limit (0.739 um against 8.287 um for
BC_A on the identical mesh), so this run asks the same question of the kinematically correct
foundation.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0g"))
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from run_support_sweep import thermal_once, structural, K_LIST, K_LABEL
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0g"
P0F = R / "results" / "phase0f"


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((P0F / "cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_kin"
    rows = []
    for h_sub in (0.80, 1.50, 2.00):
        st, m, mats, Tnode, tiles, tm, cs = thermal_once(h_sub, h_top, stack, doe, wd)
        print(f"  h={h_sub:.2f}  T_max={tm['T_max_C']:.4f} C ({len(m.elems)} el)", flush=True)
        rfree = structural(st, m, Tnode, 1.0, wd, bc="BC_A")
        rows.append({"h_sub_mm": h_sub, "restraint": "BC_A", "k_z_N_per_mm3": None,
                     "regime": "free package (3-2-1)", **rfree})
        print(f"      BC_A  (free)                 w={rfree['die_warpage_pv_um']:9.5f} um",
              flush=True)
        for bc in ("BC_BZ", "BC_B"):
            for k in K_LIST:
                r = structural(st, m, Tnode, k, wd, bc=bc)
                rows.append({"h_sub_mm": h_sub, "restraint": bc, "k_z_N_per_mm3": k,
                             "regime": K_LABEL[k], **r})
                print(f"      {bc:6s} k_z={k:>9.4g}  w={r['die_warpage_pv_um']:9.5f} um",
                      flush=True)
        for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
            for f in wd.glob(pat):
                f.unlink(missing_ok=True)

    with open(OUT / "restraint_kinematics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    print("\n=== S_h = [W(thick) - W(thin)] / W(thin), by restraint ===")
    for thin, thick in ((0.80, 1.50), (0.80, 2.00)):
        print(f"\n  pair {thin} -> {thick} mm")
        a = next(r for r in rows if r["h_sub_mm"] == thin and r["restraint"] == "BC_A")
        b = next(r for r in rows if r["h_sub_mm"] == thick and r["restraint"] == "BC_A")
        S = (b["die_warpage_pv_um"] - a["die_warpage_pv_um"]) / a["die_warpage_pv_um"]
        print(f"    {'BC_A free':32s} S_h = {S:+8.4f}   "
              f"({'thicker better' if S < 0 else 'thicker worse'})")
        for bc in ("BC_BZ", "BC_B"):
            prev = None
            for k in K_LIST:
                aa = next((r for r in rows if r["h_sub_mm"] == thin and r["restraint"] == bc
                           and r["k_z_N_per_mm3"] == k), None)
                bb = next((r for r in rows if r["h_sub_mm"] == thick and r["restraint"] == bc
                           and r["k_z_N_per_mm3"] == k), None)
                if not (aa and bb):
                    continue
                S = (bb["die_warpage_pv_um"] - aa["die_warpage_pv_um"]) / aa["die_warpage_pv_um"]
                print(f"    {bc+' k_z='+f'{k:.4g}':32s} S_h = {S:+8.4f}")
                if prev is not None and prev * S < 0:
                    print(f"      --> SIGN CHANGE between the previous point and k_z = {k:.4g}")
                prev = S
    print(f"\nwrote {OUT/'restraint_kinematics.csv'}")


if __name__ == "__main__":
    main()
