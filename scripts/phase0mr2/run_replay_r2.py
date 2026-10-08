#!/usr/bin/env python3
"""Phase-0M-R2 Section 9 --- the frozen architecture replay, with every Phase-0M-R2
correction active. No search, no new architectures, one control per correction.
"""
from __future__ import annotations
import csv, os, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0m",
          "scripts/phase0b", "scripts"):
    sys.path.insert(0, str(R / p))
os.environ["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + os.environ["PATH"]

import replay_production as RPX                                        # noqa: E402
import cooling_regime as CR                                            # noqa: E402
from ledger import FacilityLedger                                      # noqa: E402

OUT = R / "results" / "phase0mr2"

CASES = [
    ("Z1", "ARCH_Z1_EMBEDDED",  1.30, None),
    ("Z2", "ARCH_Z2_BACKSIDE",  0.30, None),
    ("Z4_stacked", "ARCH_Z4_POWER_DIE", 0.30, "Z4_STACKED"),
    ("Z4_planar",  "ARCH_Z4_POWER_DIE", 0.30, "Z4_PLANAR"),
]

LEDGER_TERMS = ["P_switch_hs_conduction", "P_switch_ls_conduction", "P_inductor_DCR",
                "P_cap_ESR", "P_switching_hard", "P_gate", "P_Coss",
                "P_intraVR_metal", "P_intraVR_vertical", "P_TSV", "P_bumps",
                "P_pkg_RDL", "P_other"]


def main() -> int:
    pump = CR.evaluate(27.0, strict=True)
    print("  cooler at 27 g/s: Re=%.1f %s  h_eff=%.0f  dp=%.3f MPa  pump=%.2f W (FACILITY)"
          % (pump["Re"], pump["regime"], pump["h_effective_W_m2K"], pump["dp_MPa"],
             pump["P_pump_hydraulic_W"]), flush=True)
    rows, led_rows = [], []
    for cid, arch, h, variant in CASES:
        if variant:
            os.environ["PHASE0MR2_Z4_VARIANT"] = variant
        else:
            os.environ.pop("PHASE0MR2_Z4_VARIANT", None)
        t0 = time.time()
        r = RPX.run_case(arch=arch, mode="AFTER", template="T1_EMBEDDED_4LAYER",
                         cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
        fl = FacilityLedger(electronics_w=r["P_elec_total_w"])
        fl.add("P_pump_hydraulic", pump["P_pump_hydraulic_W"])
        led_rows += fl.as_rows(cid)
        for t in LEDGER_TERMS:
            led_rows.append({"case": cid, "term": t, "scope": "ELECTRONICS",
                             "watts": r.get("L_" + t), "in_thermal_mesh": True,
                             "owner": "phase0mr.ledger.OWNERS"})
        row = {"case": cid, "arch": arch, "h_sub_mm": h, "z4_variant": variant or "",
               "status": r["status"],
               "P_total_electronics_w": r["P_elec_total_w"],
               "P_pump_hydraulic_w": pump["P_pump_hydraulic_W"],
               "P_total_facility_w": fl.facility_total(),
               "T_max_C": r["T_max_C"], "T_mean_C": r["T_mean_C"],
               "T_conv_C": r["T_conv_C"],
               "T_coolant_out_C": pump["T_coolant_max_C"],
               "dp_MPa": pump["dp_MPa"], "m_dot_g_s": 27.0,
               "cooler_regime": pump["regime"], "cooler_in_domain": pump["in_domain"],
               "die_warpage_pv_um": r["die_warpage_pv_um"],
               "pkg_warpage_pv_um": r.get("pkg_warpage_pv_um"),
               "du_corner_um": r["du_corner_um"],
               "energy_residual_pct": r["energy_residual_pct"],
               "et_iters": r["et_iters"], "wall_s": round(time.time() - t0, 1)}
        row.update({"L_" + t: r.get("L_" + t) for t in LEDGER_TERMS})
        rows.append(row)
        print("  %-12s %-22s P_elec=%8.3f W  P_fac=%8.3f W  Tmax=%7.2f C  "
              "warp=%7.3f um  du=%.4f um (%.0fs)"
              % (cid, arch, r["P_elec_total_w"], fl.facility_total(), r["T_max_C"],
                 r["die_warpage_pv_um"], r["du_corner_um"], time.time() - t0), flush=True)
    os.environ.pop("PHASE0MR2_Z4_VARIANT", None)

    z1 = next(r for r in rows if r["case"] == "Z1")
    z2 = next(r for r in rows if r["case"] == "Z2")
    ratio = z1["du_corner_um"] / z2["du_corner_um"]
    print("\n  DECIDING METRIC   driver_Z1 / driver_Z2 = %.4f  (%s)"
          % (ratio, "Z2 better -- ordering holds" if ratio > 1 else "ORDERING REVERSED"))

    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("architecture_replay_0mr2.csv", rows),
                       ("architecture_loss_ledger.csv", led_rows)):
        k = sorted({x for r in data for x in r})
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(data)
    print("wrote %s" % (OUT / "architecture_replay_0mr2.csv"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
