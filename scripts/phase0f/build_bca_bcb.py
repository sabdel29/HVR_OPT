#!/usr/bin/env python3
"""Phase-0F Sec.7: report the two assembly states separately and test each ordering."""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0f"
F = lambda r, k: float(r[k])
U_M_PCT = 0.5


def key(r):
    return (r["arch"], r["fam"], str(r["m_vr"]), f"{float(r['j']):.2f}",
            f"{float(r['h_sub_mm']):.3f}")


def main():
    bca = {key(r): r for r in csv.DictReader(open(OUT / "1kw_candidates.csv"))
           if str(r.get("feasible")).lower() in ("true", "1")}
    bcb = {key(r): r for r in csv.DictReader(open(OUT / "bcb_pairs_1kw.csv"))}
    rows = []
    for k, b in bcb.items():
        a = bca.get(k)
        if not a:
            continue
        rows.append({"group": b["group"], "arch": k[0], "fam": k[1], "m_vr": k[2],
                     "j": k[3], "h_sub_mm": k[4],
                     "P_elec_w": F(a, "P_elec_total_w"),
                     "T_max_C": F(a, "T_max_C"),
                     "BCA_warpage_um": F(a, "die_warpage_pv_um"),
                     "BCB_warpage_um": F(b, "die_warpage_pv_um"),
                     "BCA_curvature": F(a, "curvature_um_per_mm2"),
                     "BCB_curvature": F(b, "curvature_um_per_mm2"),
                     "BCB_shear_p99_MPa": F(b, "interface_shear_p99_MPa"),
                     "suppression_ratio": F(a, "die_warpage_pv_um") / F(b, "die_warpage_pv_um")})
    with open(OUT / "bca_bcb_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote bca_bcb_comparison.csv ({len(rows)} rows)\n")

    print("PACKAGE-LEVEL (BC-A) and BOARD-MOUNTED (BC-B), reported separately")
    print(f"{'group':10s} {'arch':7s} {'fam':10s} {'h':>5s} {'P_el':>8s} "
          f"{'BCA w':>8s} {'BCB w':>8s} {'suppr':>7s}")
    for r in rows:
        print(f"{r['group']:10s} {r['arch']:7s} {r['fam']:10s} {float(r['h_sub_mm']):5.2f} "
              f"{r['P_elec_w']:8.2f} {r['BCA_warpage_um']:8.4f} {r['BCB_warpage_um']:8.4f} "
              f"{r['suppression_ratio']:7.1f}x")

    # The same physical case can belong to more than one group, so levers are addressed by
    # their (arch, fam, m_vr, j, h) key rather than by group label.
    by = {(r["arch"], r["fam"], r["m_vr"], r["j"], r["h_sub_mm"]): r for r in rows}
    def get(arch, fam, m, j, h):
        return by.get((arch, fam, str(m), f"{j:.2f}", f"{h:.3f}"))
    print("\nDoes each lever keep its SIGN between assembly states?")
    print(f"{'lever':30s} {'BC-A':>12s} {'BC-B':>12s}  verdict")
    LEVERS = [("thickness ARCH_A 0.8->1.5",
               get("ARCH_A", "uniform", 49, 3.5, 0.8), get("ARCH_A", "uniform", 49, 3.5, 1.5)),
              ("thickness ARCH_B 0.8->2.0",
               get("ARCH_B", "uniform", 49, 3.5, 0.8), get("ARCH_B", "uniform", 49, 3.5, 2.0)),
              ("footprint 259->329 mm2",
               get("ARCH_A", "uniform", 36, 3.0, 1.5), get("ARCH_A", "uniform", 49, 3.0, 1.5)),
              ("placement uniform->compact",
               get("ARCH_A", "uniform", 49, 3.5, 1.5), get("ARCH_A", "compact", 49, 3.5, 1.5))]
    for grp, a0, a1 in LEVERS:
        s = [x for x in (a0, a1) if x]
        if len(s) < 2:
            print(f"{grp:30s} {'--':>12s} {'--':>12s}  incomplete"); continue
        da = 100 * (s[-1]["BCA_warpage_um"] - s[0]["BCA_warpage_um"]) / s[0]["BCA_warpage_um"]
        db = 100 * (s[-1]["BCB_warpage_um"] - s[0]["BCB_warpage_um"]) / s[0]["BCB_warpage_um"]
        res = abs(db) > 2 * U_M_PCT
        if not res:
            v = "LOST under BC-B (below resolution)"
        elif da * db < 0:
            v = "**SIGN REVERSES**"
        else:
            v = "preserved"
        print(f"{grp:22s} {da:+11.2f}% {db:+11.2f}%  {v}")


if __name__ == "__main__":
    main()
