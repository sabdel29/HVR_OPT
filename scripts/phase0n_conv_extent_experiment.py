#!/usr/bin/env python3
"""PHASE 0N SECTION K -- is the Z1/Z2 mechanical ordering an artifact of the
backside converter's LATERAL EXTENT?

The frozen model lays ARCH_Z2's converter down as a FULL-AREA 1226 um band of
`hvr_effective` (1103.40 mm3) while ARCH_Z1's converter exists only inside the 49
VR-cell footprints (337.02 mm3). The two architectures therefore do not carry the
same amount of converter material, so the comparison is not purely one of PLACEMENT.

This script reruns the frozen replay unchanged, then reruns ARCH_Z2 with the
out-of-cell area of the backside band filled with a non-converter medium, so that
both architectures carry an identical 337.02 mm3 of converter. Z1 is unaffected by
the switch and is run once.
"""
from __future__ import annotations
import csv, json, os, sys, time
from pathlib import Path
import yaml

R = Path(__file__).resolve().parent.parent
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i",
          "scripts/phase0f", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))
os.environ["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + os.environ["PATH"]

OUT = R / "research" / "phase0n"
OUT.mkdir(parents=True, exist_ok=True)

# the frozen hooks, exactly as run_final_replay.py sets them
FZ = {t: yaml.safe_load((R / f"configs/phase0mr3c/frozen_pair_{t}.yaml").read_text())
      for t in ("Z1", "Z2")}
IC = FZ["Z1"]["interconnect"]
TPL = FZ["Z1"]["partition"]["template"]
os.environ["PHASE0MR3B_PHYSICAL_SPANS"] = "1"
os.environ["PHASE0MR3_R_VIA_UM"] = str(IC["microvia_diameter_um"] / 2.0)
os.environ["PHASE0MR3_VIA_PITCH_UM"] = str(IC["microvia_pitch_um"])

VARIANTS = [
    ("Z1", "ARCH_Z1_EMBEDDED", 1.30, None,
     "frozen; converter exists only inside the 49 cell footprints"),
    ("Z2_frozen", "ARCH_Z2_BACKSIDE", 0.30, None,
     "frozen; backside band is FULL-AREA converter medium"),
    ("Z2_cellonly_underfill", "ARCH_Z2_BACKSIDE", 0.30, "underfill_homog",
     "corrected; out-of-cell backside area is underfill (E = 8 GPa)"),
    ("Z2_cellonly_silicon", "ARCH_Z2_BACKSIDE", 0.30, "silicon",
     "corrected; out-of-cell backside area is substrate silicon (E = 130 GPa)"),
]


def main() -> int:
    import replay_production as RPX
    # Use a Phase-0N scratch directory. Sharing replay_production.WD would leave the
    # LAST variant's solver output where extract_die_field.py reads the frozen field,
    # which is exactly how this script once broke
    # tests/phase0mr3c::test_plotted_die_field_reproduces_the_frozen_warpage.
    RPX.WD = R / "results" / "phase0n" / "replay"
    RPX.WD.mkdir(parents=True, exist_ok=True)
    rows = []
    for tag, arch, h, fill, note in VARIANTS:
        if fill:
            os.environ["PHASE0N_Z2_CONV_FILL"] = fill
        else:
            os.environ.pop("PHASE0N_Z2_CONV_FILL", None)
        t0 = time.time()
        r = RPX.run_case(arch=arch, mode="AFTER", template=TPL,
                         cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
        rows.append({"variant": tag, "arch": arch, "h_sub_mm": h,
                     "conv_fill": fill or "(none -- full-area converter)",
                     "note": note,
                     "P_elec_w": r["P_elec_total_w"], "T_max_C": r["T_max_C"],
                     "T_mean_C": r["T_mean_C"], "T_conv_C": r["T_conv_C"],
                     "die_warpage_pv_um": r["die_warpage_pv_um"],
                     "pkg_warpage_pv_um": r.get("pkg_warpage_pv_um"),
                     "du_corner_um": r["du_corner_um"],
                     "energy_residual_pct": r["energy_residual_pct"],
                     "wall_s": round(time.time() - t0, 1)})
        print(f"  {tag:26} P={r['P_elec_total_w']:8.3f} W  "
              f"Tmax={r['T_max_C']:7.2f} C  warp={r['die_warpage_pv_um']:7.3f} um  "
              f"du_c={r['du_corner_um']:.4f} um  ({time.time()-t0:.0f}s)", flush=True)
    os.environ.pop("PHASE0N_Z2_CONV_FILL", None)

    z1 = next(r for r in rows if r["variant"] == "Z1")
    print(f"\n{'variant':28}{'D_u = Z1/Z2':>13}{'Z2 vs Z1 du':>14}{'dT (K)':>10}")
    for r in rows:
        if r["variant"] == "Z1":
            continue
        d = z1["du_corner_um"] / r["du_corner_um"]
        red = 100 * (z1["du_corner_um"] - r["du_corner_um"]) / z1["du_corner_um"]
        print(f"{r['variant']:28}{d:>13.4f}{red:>13.2f} %"
              f"{r['T_max_C'] - z1['T_max_C']:>10.2f}")
        r["D_u_vs_Z1"] = round(d, 6)
        r["du_reduction_pct_vs_Z1"] = round(red, 4)
        r["dT_vs_Z1_K"] = round(r["T_max_C"] - z1["T_max_C"], 4)

    (OUT / "conv_extent_experiment.json").write_text(json.dumps(rows, indent=1))
    with (OUT / "conv_extent_experiment.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {OUT/'conv_extent_experiment.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
