#!/usr/bin/env python3
"""Phase-0M-R2 Section 2 --- the frozen architecture set, with controls that separate the
two corrections made in this phase.

Two independent model corrections landed together, so neither may be reported without a
control that isolates it:

  DEFECT #55  the TSV-field material override was painted into the PCB, the BGA field and
              (for Z2) the backside converter layer. Affects ALL THREE architectures.
  Z4 GEOMETRY the power die now exists instead of the heat being deposited in `interface`.
              Affects Z4 ONLY.
"""
from __future__ import annotations
import csv, os, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr", "scripts/phase0i", "scripts/phase0m", "scripts/phase0b",
          "scripts"):
    sys.path.insert(0, str(R / p))
os.environ["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + os.environ["PATH"]

import replay_production as RPX          # noqa: E402

OUT = R / "results" / "phase0mr2"

CASES = [
    # id,                    arch,                  h_sub, z4 variant
    ("Z1_d55fix",            "ARCH_Z1_EMBEDDED",    1.30, None),
    ("Z2_d55fix",            "ARCH_Z2_BACKSIDE",    0.30, None),
    ("Z4_d55fix_stacked",    "ARCH_Z4_POWER_DIE",   0.30, "Z4_STACKED"),
    ("Z4_d55fix_planar",     "ARCH_Z4_POWER_DIE",   0.30, "Z4_PLANAR"),
]

KEYS = ("P_elec_total_w", "T_max_C", "T_mean_C", "T_conv_C", "die_warpage_pv_um",
        "pkg_warpage_pv_um", "du_corner_um", "energy_residual_pct", "et_iters",
        "h_effective_W_m2K", "dT_fluid_span_K")


def main() -> int:
    rows = []
    for cid, arch, h, variant in CASES:
        t0 = time.time()
        if variant:
            os.environ["PHASE0MR2_Z4_VARIANT"] = variant
        else:
            os.environ.pop("PHASE0MR2_Z4_VARIANT", None)
        r = RPX.run_case(arch=arch, mode="AFTER", template="T1_EMBEDDED_4LAYER",
                         cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
        row = {"case": cid, "arch": arch, "h_sub_mm": h, "z4_variant": variant or "",
               "status": r.get("status"), "wall_s": round(time.time() - t0, 1)}
        row.update({k: r.get(k) for k in KEYS})
        rows.append(row)
        print("  %-20s %-22s P=%8.3f W Tmax=%7.2f C warp=%7.3f um du=%.4f um (%.0fs)"
              % (cid, arch, r.get("P_elec_total_w", float("nan")),
                 r.get("T_max_C", float("nan")), r.get("die_warpage_pv_um", float("nan")),
                 r.get("du_corner_um", float("nan")), time.time() - t0), flush=True)
    with open(OUT / "z4_before_after.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'z4_before_after.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
