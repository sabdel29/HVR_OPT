#!/usr/bin/env python3
"""Phase-0M-R3C Section 8 --- the ONE final ETM replay on the frozen repartitioned pair.

Exactly the Phase-0M-R3 production pipeline and settings. Two deliberate differences, both
frozen in configs/phase0mr3c/frozen_pair_*.yaml BEFORE this ran:

  * partition template T1C_REORDERED -- a permutation of T1_EMBEDDED_4LAYER that puts the
    low-side switch adjacent to the inductor;
  * PHASE0MR3B_PHYSICAL_SPANS=1 -- vertical links measured face to face instead of tier
    mid-plane to tier mid-plane, and the source-bounded via geometry.

No DOE, no sweep, no tuning. One solve per architecture.
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

OUT = R / "results" / "phase0mr3c"
TERMS = ["P_switch_hs_conduction", "P_switch_ls_conduction", "P_inductor_DCR",
         "P_cap_ESR", "P_switching_hard", "P_gate", "P_Coss",
         "P_intraVR_metal", "P_intraVR_vertical", "P_TSV", "P_bumps",
         "P_pkg_RDL", "P_other"]
CASES = [("Z1", "ARCH_Z1_EMBEDDED", 1.30), ("Z2", "ARCH_Z2_BACKSIDE", 0.30)]
HIST_D = 1.1943


def main() -> int:
    frozen = {t: yaml.safe_load(
        (R / f"configs/phase0mr3c/frozen_pair_{t}.yaml").read_text()) for t, _, _ in CASES}
    ic = frozen["Z1"]["interconnect"]
    tpl = frozen["Z1"]["partition"]["template"]
    # the frozen configuration reaches production through these hooks, set before import
    os.environ["PHASE0MR3B_PHYSICAL_SPANS"] = "1"
    os.environ["PHASE0MR3_R_VIA_UM"] = str(ic["microvia_diameter_um"] / 2.0)
    os.environ["PHASE0MR3_VIA_PITCH_UM"] = str(ic["microvia_pitch_um"])
    print(f"  frozen partition : {tpl}  "
          f"({' | '.join(frozen['Z1']['partition']['tiers_bottom_to_top'])})")
    print(f"  frozen via       : d = {ic['microvia_diameter_um']:.0f} um at "
          f"{ic['microvia_pitch_um']:.0f} um pitch, worst AR "
          f"{ic['worst_aspect_ratio']:.3f}")
    print(f"  physical spans   : ON\n", flush=True)

    import cooling_regime as CR                                          # noqa: E402
    import replay_production as RPX                                      # noqa: E402
    from ledger import FacilityLedger                                    # noqa: E402

    pump = CR.evaluate(27.0, strict=True)
    print(f"  cooler 27 g/s: Re={pump['Re']:.1f} {pump['regime']}, "
          f"h_eff={pump['h_effective_W_m2K']:.0f}, "
          f"pump={pump['P_pump_hydraulic_W']:.2f} W (FACILITY scope)\n", flush=True)

    rows, led = [], []
    for tag, arch, h in CASES:
        t0 = time.time()
        r = RPX.run_case(arch=arch, mode="AFTER", template=tpl,
                         cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
        fl = FacilityLedger(electronics_w=r["P_elec_total_w"])
        fl.add("P_pump_hydraulic", pump["P_pump_hydraulic_W"])
        led += fl.as_rows(tag)
        for t in TERMS:
            led.append({"case": tag, "term": t, "scope": "ELECTRONICS",
                        "watts": r.get("L_" + t), "in_thermal_mesh": True,
                        "owner": "phase0mr.ledger.OWNERS"})
        row = {"case": tag, "arch": arch, "template": tpl, "status": r["status"],
               "P_total_electronics_w": r["P_elec_total_w"],
               "P_pump_hydraulic_w": pump["P_pump_hydraulic_W"],
               "P_total_facility_w": fl.facility_total(),
               "T_max_C": r["T_max_C"], "T_mean_C": r["T_mean_C"],
               "T_conv_C": r["T_conv_C"],
               "die_warpage_pv_um": r["die_warpage_pv_um"],
               "pkg_warpage_pv_um": r.get("pkg_warpage_pv_um"),
               "response_driver_um": r["du_corner_um"],
               "energy_residual_pct": r["energy_residual_pct"],
               "et_iters": r["et_iters"], "wall_s": round(time.time() - t0, 1)}
        row.update({"L_" + t: r.get("L_" + t) for t in TERMS})
        rows.append(row)
        print(f"  {tag}  P_elec={r['P_elec_total_w']:8.3f} W  "
              f"Tmax={r['T_max_C']:7.2f} C  warp={r['die_warpage_pv_um']:7.3f} um  "
              f"response={r['du_corner_um']:.4f} um  ({time.time()-t0:.0f}s)", flush=True)

    z1 = next(r for r in rows if r["case"] == "Z1")
    z2 = next(r for r in rows if r["case"] == "Z2")
    d = z1["response_driver_um"] / z2["response_driver_um"]
    print(f"\n  D_driver_final = {d:.4f}   "
          f"({'Z2 lower response -- ordering HOLDS' if d > 1 else 'ORDERING REVERSED'})")
    print(f"  historical Phase-0M-R3 D_driver = {HIST_D:.4f}; "
          f"change {100*(d-HIST_D)/HIST_D:+.2f} %")
    print(f"  Z2 is {100*(z1['response_driver_um']-z2['response_driver_um'])/z1['response_driver_um']:.1f} % "
          f"below Z1; Z2 is {z2['T_max_C']-z1['T_max_C']:+.2f} K hotter")

    for nm, data in (("final_etm_replay.csv", rows),
                     ("final_loss_ledger.csv", led)):
        k = sorted({x for r in data for x in r})
        with (OUT / nm).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=k); w.writeheader(); w.writerows(data)
    print(f"\n  wrote {OUT.name}/final_etm_replay.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
