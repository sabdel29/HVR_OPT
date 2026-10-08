#!/usr/bin/env python3
"""Phase-0M-R2 Section 8 --- should the measured RDL/bump anisotropy become the
production thermal default?

The production `interface` layer -- the layer directly between the compute die and the
substrate, i.e. IN the main heat path -- uses `underfill_homog` with an ISOTROPIC
k = 0.70 W/mK. Phase 0M-R measured the same physical layer as a microbump field in
underfill and obtained kz = 11.74 and kxy = 0.89 W/mK: anisotropic by 13.2x and, through
thickness, 16.8x more conductive than the isotropic value in use.

That is a large discrepancy in the one layer every watt must cross, so it is tested
rather than argued. Promotion is earned only if the tensor is validated AND materially
changes the answer.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0m",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))
os.environ["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + os.environ["PATH"]

import rdl_homogenization as RH                                         # noqa: E402

OUT = R / "results" / "phase0mr2"


def production_interface_tensor() -> dict:
    """Re-derive the interface-layer tensor from the PRODUCTION geometry.

    The interface layer is the microbump field in underfill. Its geometry is sourced:
    r = 5 um, pitch 20 um, height 10 um (the sourced interface_layer thickness), solder
    inclusions in underfill.
    """
    b = RH.bump_layer(r_um=5.0, p_um=20.0, h_um=10.0,
                      k_incl=RH.K_SOLDER, k_mat=RH.K_UNDERFILL)
    return {"organisation": "microbump field in underfill",
            "r_um": 5.0, "pitch_um": 20.0, "h_um": 10.0,
            "f_inclusion": b["f_inclusion"],
            "k_x": b["RVE_kxy"], "k_y": b["RVE_kxy"], "k_z": b["RVE_kz"],
            "anisotropy_z_over_xy": b["anisotropy"],
            "err_voigt_kz_pct": b["err_voigt_kz_pct"],
            "err_maxwell_kxy_pct": b["err_maxwell_kxy_pct"],
            "production_isotropic_k": 0.70,
            "kz_over_production_iso": b["RVE_kz"] / 0.70}


def main() -> int:
    import replay_production as RPX

    t = production_interface_tensor()
    print("  production interface tensor, re-derived from sourced geometry:")
    print(f"    f_incl={t['f_inclusion']:.4f}  kx=ky={t['k_x']:.4f}  kz={t['k_z']:.4f} "
          f"W/mK   anisotropy {t['anisotropy_z_over_xy']:.1f}x")
    print(f"    the production model uses isotropic k = 0.70, i.e. "
          f"{t['kz_over_production_iso']:.1f}x too low through thickness")
    print(f"    Voigt bound err {t['err_voigt_kz_pct']:.2f} %, "
          f"Maxwell err {t['err_maxwell_kxy_pct']:.2f} %", flush=True)

    rows = []
    for arch, h in (("ARCH_Z1_EMBEDDED", 1.30), ("ARCH_Z2_BACKSIDE", 0.30)):
        for mode, env in (("isotropic_0p70", None),
                          ("anisotropic_derived",
                           f"{t['k_x']},{t['k_y']},{t['k_z']}")):
            if env:
                os.environ["PHASE0MR2_INTERFACE_KORTHO"] = env
            else:
                os.environ.pop("PHASE0MR2_INTERFACE_KORTHO", None)
            t0 = time.time()
            r = RPX.run_case(arch=arch, mode="AFTER", template="T1_EMBEDDED_4LAYER",
                             cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
            rows.append({"arch": arch, "interface_model": mode,
                         "k_x": t["k_x"] if env else 0.70,
                         "k_z": t["k_z"] if env else 0.70,
                         "T_max_C": r["T_max_C"], "T_mean_C": r["T_mean_C"],
                         "T_conv_C": r["T_conv_C"],
                         "die_warpage_pv_um": r["die_warpage_pv_um"],
                         "du_corner_um": r["du_corner_um"],
                         "P_elec_total_w": r["P_elec_total_w"],
                         "wall_s": round(time.time() - t0, 1)})
            print(f"  {arch:22s} {mode:20s} Tmax={r['T_max_C']:7.2f} C  "
                  f"warp={r['die_warpage_pv_um']:7.3f} um  du={r['du_corner_um']:.4f} um",
                  flush=True)
    os.environ.pop("PHASE0MR2_INTERFACE_KORTHO", None)

    # the decision metric: does the Z1/Z2 driver ratio move?
    def get(a, m):
        return next(r for r in rows if r["arch"] == a and r["interface_model"] == m)
    for m in ("isotropic_0p70", "anisotropic_derived"):
        z1, z2 = get("ARCH_Z1_EMBEDDED", m), get("ARCH_Z2_BACKSIDE", m)
        ratio = z1["du_corner_um"] / z2["du_corner_um"]
        for r in (z1, z2):
            r["Z1_over_Z2_driver_ratio"] = ratio
        print(f"  Z1/Z2 driver ratio, {m:20s} = {ratio:.4f}")
    r_i = get("ARCH_Z1_EMBEDDED", "isotropic_0p70")["Z1_over_Z2_driver_ratio"]
    r_a = get("ARCH_Z1_EMBEDDED", "anisotropic_derived")["Z1_over_Z2_driver_ratio"]
    print(f"  ratio shift = {100*(r_a-r_i)/r_i:+.3f} %")

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "rdl_isotropic_vs_anisotropic.csv", "w", newline="") as fh:
        k = sorted({x for r in rows for x in r})
        w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(rows)
    with open(OUT / "rdl_production_tensor.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(t)); w.writeheader(); w.writerow(t)
    print(f"wrote {OUT/'rdl_isotropic_vs_anisotropic.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
