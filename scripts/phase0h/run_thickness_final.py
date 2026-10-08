#!/usr/bin/env python3
"""Phase-0H Sec.13 -- the final thickness response over the REALIZABLE range.

Sec.12 sourced the GaN device heights and moved the minimum realizable substrate from
0.770 mm to 1.176-1.426 mm. The Phase-0G thickness conclusion was drawn over 0.80-2.00 mm, so
most of that range is now unbuildable and the electrical optimum at the 0.80 mm thin boundary
is not a design.

This script fills in the mounted mechanical response at the thicknesses inside the realizable
band that Phase 0G did not simulate (it ran 0.80 / 1.50 / 2.00 only), then assembles
thickness_response_final.csv: dP_elec, dT and the mounted mechanical metric across the band.

No new electrical runs are needed -- the Phase-0G corrected sweeps already cover
1.20-2.00 mm at 0.10 mm resolution.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0h", "phase0g", "phase0f", "phase0b"):
    sys.path.insert(0, str(R / "scripts" / p))
import run_explicit_board as REB                      # noqa: E402
REB.THREADS = 8
from etm.config import load_doe, load_stack           # noqa: E402

OUT = R / "results" / "phase0h"
G = R / "results" / "phase0g"
CASE = "fr4_1p6mm"
NEW_H = (1.20, 1.30, 1.40, 1.75)      # 0.80 / 1.50 / 2.00 already exist from Phase 0G


def main():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_thickfinal"

    mech = {}
    for r in csv.DictReader(open(G / "explicit_board_crosscheck.csv")):
        if r["restraint"] == "BC_BOARD" and r["board_case"] == CASE:
            mech[round(float(r["h_sub_mm"]), 2)] = {
                "die_warpage_pv_um": float(r["die_warpage_pv_um"]),
                "interface_shear_p99_MPa": float(r["interface_shear_p99_MPa"]),
                "rel_disp_max_um": float(r["rel_disp_max_um"]),
                "T_max_C": float(r["T_max_C"]), "provenance": "phase0g"}

    print(f"Sec.13  mounted mechanical response, missing thicknesses (BC_BOARD, {CASE})")
    for h in NEW_H:
        t0 = time.time()
        try:
            r = REB.run_case(h, "BC_BOARD", CASE, stack, doe, h_top, wd)
        except Exception as e:
            print(f"  h={h:.2f}  FAILED: {str(e)[:70]}", flush=True); continue
        mech[round(h, 2)] = {"die_warpage_pv_um": r["die_warpage_pv_um"],
                             "interface_shear_p99_MPa": r["interface_shear_p99_MPa"],
                             "rel_disp_max_um": r["rel_disp_max_um"],
                             "T_max_C": r["T_max_C"], "provenance": "phase0h"}
        print(f"  h={h:.2f}  w={r['die_warpage_pv_um']:9.4f} tau99={r['interface_shear_p99_MPa']:7.4f} "
              f"rel={r['rel_disp_max_um']:8.5f} Tmax={r['T_max_C']:7.3f} ({time.time()-t0:.0f}s)",
              flush=True)

    elec = {}
    for arch, fn in (("ARCH_A", "crossover_hires_ARCH_A_fixedA.csv"),
                     ("ARCH_B", "crossover_hires_ARCH_B_fixedB.csv")):
        for r in csv.DictReader(open(G / fn)):
            elec.setdefault(round(float(r["h_sub_mm"]), 2), {})[arch] = {
                "P_elec_total_w": float(r["P_elec_total_w"]),
                "T_max_C": float(r["T_max_C"])}

    HMIN = {"mlcc_optimistic": 1.176, "mlcc_nominal": 1.276, "mlcc_pessimistic": 1.426}
    rows = []
    for h in sorted(set(elec) | set(mech)):
        e, m = elec.get(h, {}), mech.get(h)
        row = {"h_sub_mm": h,
               "realizable_mlcc_optimistic": h >= HMIN["mlcc_optimistic"],
               "realizable_mlcc_nominal": h >= HMIN["mlcc_nominal"],
               "realizable_mlcc_pessimistic": h >= HMIN["mlcc_pessimistic"],
               "P_ARCH_A_w": e.get("ARCH_A", {}).get("P_elec_total_w"),
               "P_ARCH_B_w": e.get("ARCH_B", {}).get("P_elec_total_w"),
               "T_max_C_free": e.get("ARCH_B", {}).get("T_max_C")}
        if m:
            row.update({k: m[k] for k in ("die_warpage_pv_um", "interface_shear_p99_MPa",
                                          "rel_disp_max_um")})
            row["T_max_C_mounted"] = m["T_max_C"]
            row["mech_provenance"] = m["provenance"]
        rows.append(row)
    with open(OUT / "thickness_response_final.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)

    print("\n=== thickness response over the REALIZABLE band ===")
    print(f"{'h mm':>6s} {'buildable?':>22s} {'P_A (W)':>10s} {'P_B (W)':>10s} "
          f"{'w mounted um':>13s} {'tau99':>8s}")
    for r in rows:
        b = ("opt+nom+pes" if r["realizable_mlcc_pessimistic"] else
             "opt+nom" if r["realizable_mlcc_nominal"] else
             "opt only" if r["realizable_mlcc_optimistic"] else "NOT BUILDABLE")
        pa = f"{r['P_ARCH_A_w']:10.4f}" if r.get("P_ARCH_A_w") else " " * 10
        pb = f"{r['P_ARCH_B_w']:10.4f}" if r.get("P_ARCH_B_w") else " " * 10
        ww = f"{r['die_warpage_pv_um']:13.4f}" if r.get("die_warpage_pv_um") else " " * 13
        tt = f"{r['interface_shear_p99_MPa']:8.4f}" if r.get("interface_shear_p99_MPa") else " " * 8
        print(f"{r['h_sub_mm']:6.2f} {b:>22s} {pa} {pb} {ww} {tt}")

    for tag, hmin in HMIN.items():
        sel = [r for r in rows if r["h_sub_mm"] >= hmin and r.get("P_ARCH_B_w")
               and r.get("die_warpage_pv_um")]
        if len(sel) < 2:
            continue
        a, b = sel[0], sel[-1]
        print(f"\n  {tag}: realizable band {a['h_sub_mm']:.2f} -> {b['h_sub_mm']:.2f} mm")
        print(f"    dP_elec ARCH_B = {(b['P_ARCH_B_w']-a['P_ARCH_B_w'])*1000:+9.1f} mW  "
              f"(thinner is better by this much)")
        print(f"    dP_elec ARCH_A = {(b['P_ARCH_A_w']-a['P_ARCH_A_w'])*1000:+9.1f} mW")
        print(f"    dT_max        = {b['T_max_C_free']-a['T_max_C_free']:+9.3f} K")
        print(f"    d warpage     = {b['die_warpage_pv_um']-a['die_warpage_pv_um']:+9.3f} um "
              f"({100*(b['die_warpage_pv_um']-a['die_warpage_pv_um'])/a['die_warpage_pv_um']:+.1f} %, "
              f"thicker is better)")
        print(f"    d tau99       = {b['interface_shear_p99_MPa']-a['interface_shear_p99_MPa']:+9.3f} MPa")
    print(f"\nwrote {OUT/'thickness_response_final.csv'}")


if __name__ == "__main__":
    main()
