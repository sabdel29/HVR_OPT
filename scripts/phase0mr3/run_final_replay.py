#!/usr/bin/env python3
"""Phase-0M-R3 Section 14 --- the ETM replay on the FROZEN realizable pair.

Exactly the Phase-0M-R2 production pipeline. The only difference is the one repair the
feasibility search found: the intra-VR via radius is 20 um at the framework's own legal
pitch instead of 15 um at 60 um. Nothing is tuned per architecture, and nothing was
changed after any mechanical result was seen.
"""
from __future__ import annotations
import csv, os, sys, time
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i",
          "scripts/phase0f", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))
os.environ["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + os.environ["PATH"]

import cooling_regime as CR                                            # noqa: E402
import replay_production as RPX                                        # noqa: E402
from ledger import FacilityLedger                                      # noqa: E402

OUT = R / "results" / "phase0mr3"
TERMS = ["P_switch_hs_conduction", "P_switch_ls_conduction", "P_inductor_DCR",
         "P_cap_ESR", "P_switching_hard", "P_gate", "P_Coss",
         "P_intraVR_metal", "P_intraVR_vertical", "P_TSV", "P_bumps",
         "P_pkg_RDL", "P_other"]
CASES = [("Z1", "ARCH_Z1_EMBEDDED", 1.30), ("Z2", "ARCH_Z2_BACKSIDE", 0.30)]


def main() -> int:
    frozen = {t: yaml.safe_load((R / f"configs/phase0mr3/frozen_realizable_{t}.yaml")
                                .read_text()) for t, _, _ in CASES}
    rv = frozen["Z1"]["repair_applied"]["what"]
    print(f"  frozen repair, identical for both: {rv}")
    # the repair reaches the production routing model through this env hook
    os.environ["PHASE0MR3_R_VIA_UM"] = "20.0"
    os.environ["PHASE0MR3_VIA_PITCH_UM"] = str(
        frozen["Z1"]["repair_applied"]["pitch_um"])

    pump = CR.evaluate(27.0, strict=True)
    print(f"  cooler 27 g/s: Re={pump['Re']:.1f} {pump['regime']}, "
          f"h_eff={pump['h_effective_W_m2K']:.0f}, pump={pump['P_pump_hydraulic_W']:.2f} W "
          f"(FACILITY scope)\n", flush=True)

    rows, led = [], []
    for tag, arch, h in CASES:
        t0 = time.time()
        r = RPX.run_case(arch=arch, mode="AFTER", template="T1_EMBEDDED_4LAYER",
                         cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
        fl = FacilityLedger(electronics_w=r["P_elec_total_w"])
        fl.add("P_pump_hydraulic", pump["P_pump_hydraulic_W"])
        led += fl.as_rows(tag)
        for t in TERMS:
            led.append({"case": tag, "term": t, "scope": "ELECTRONICS",
                        "watts": r.get("L_" + t), "in_thermal_mesh": True,
                        "owner": "phase0mr.ledger.OWNERS"})
        row = {"case": tag, "arch": arch, "status": r["status"],
               "P_total_electronics_w": r["P_elec_total_w"],
               "P_pump_hydraulic_w": pump["P_pump_hydraulic_W"],
               "P_total_facility_w": fl.facility_total(),
               "T_max_C": r["T_max_C"], "T_mean_C": r["T_mean_C"],
               "T_conv_C": r["T_conv_C"],
               "T_coolant_out_C": pump["T_coolant_max_C"],
               "dp_MPa": pump["dp_MPa"], "cooler_regime": pump["regime"],
               "cooler_in_domain": pump["in_domain"],
               "die_warpage_pv_um": r["die_warpage_pv_um"],
               "pkg_warpage_pv_um": r.get("pkg_warpage_pv_um"),
               "response_driver_um": r["du_corner_um"],
               "energy_residual_pct": r["energy_residual_pct"],
               "et_iters": r["et_iters"], "wall_s": round(time.time() - t0, 1)}
        row.update({"L_" + t: r.get("L_" + t) for t in TERMS})
        rows.append(row)
        print(f"  {tag}  P_elec={r['P_elec_total_w']:8.3f} W  "
              f"P_fac={fl.facility_total():8.3f} W  Tmax={r['T_max_C']:7.2f} C  "
              f"warp={r['die_warpage_pv_um']:7.3f} um  "
              f"driver={r['du_corner_um']:.4f} um  ({time.time()-t0:.0f}s)", flush=True)

    z1 = next(r for r in rows if r["case"] == "Z1")
    z2 = next(r for r in rows if r["case"] == "Z2")
    ratio = z1["response_driver_um"] / z2["response_driver_um"]
    print(f"\n  D_driver_realizable = {ratio:.4f}  "
          f"({'Z2 better -- ordering holds' if ratio > 1 else 'ORDERING REVERSED'})")
    print(f"  Phase 0M-R2 was 1.1942; change {100*(ratio-1.1942)/1.1942:+.2f} %")

    OUT.mkdir(parents=True, exist_ok=True)
    for nm, data in (("final_Z1_Z2_comparison.csv", rows),
                     ("final_loss_ledger.csv", led)):
        k = sorted({x for r in data for x in r})
        with open(OUT / nm, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(data)
    with open(OUT / "final_thermal_metrics.csv", "w", newline="") as fh:
        kk = ["case", "arch", "T_max_C", "T_mean_C", "T_conv_C", "T_coolant_out_C",
              "dp_MPa", "cooler_regime", "cooler_in_domain", "P_pump_hydraulic_w",
              "energy_residual_pct"]
        w = csv.DictWriter(fh, fieldnames=kk, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    with open(OUT / "final_mechanical_metrics.csv", "w", newline="") as fh:
        kk = ["case", "arch", "die_warpage_pv_um", "pkg_warpage_pv_um",
              "response_driver_um"]
        w = csv.DictWriter(fh, fieldnames=kk, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**{k: r[k] for k in kk}})
    print(f"wrote {OUT/'final_Z1_Z2_comparison.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
