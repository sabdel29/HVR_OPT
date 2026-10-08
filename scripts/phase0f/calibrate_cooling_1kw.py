#!/usr/bin/env python3
"""Phase-0F Sec.2: calibrate the cooling boundary at the ACTUAL 1-kW reference.

Phase 0B solved for h_top = 17 521.6 W/m2K so a ~282 W controlled vehicle reached the June
cooled-baseline junction temperature. That was a deliberate choice for a controlled mechanical
experiment. Phase 0F simulates the real 1-kW reference, where the package must reject roughly
4x the heat through the same area, so carrying that number over would put the package tens of
degrees off the reference and corrupt every temperature-dependent loss.

JUNE-2026 1-kW REFERENCE (Sec. IV-D), quoted:
  * "substrate-embedded micro-channel cooling is employed, with cooling channels positioned
     adjacent to the GaN switch layer"
  * "a coolant flow rate of 1.6 g/s, limiting the maximum junction temperature to
     approximately 84 C"
  * "the total system loss converges to 210 W ... end-to-end efficiency of 82.6%"
  * without thermal management the junction exceeds 110 C and loss rises to 225 W

The target reproduced here is T_j,max = 84 C at the 1-kW load with the ET loop converged.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0f"))
import kw1
from etm.config import load_doe, load_stack

OUT = R / "results" / "phase0f"
TARGET_TJ_C = 84.0
TOL_K = 0.5


def main():
    stack, doe = load_stack(), load_doe()
    wd = OUT / "runs_cal"
    topology = sys.argv[1] if len(sys.argv) > 1 else "top"
    if topology == "top":
        h_lo, h_hi, h = 100000.0, 400000.0, 166000.0     # bracket set by the first sweep
        h_bot = None
    else:
        # substrate-side proxy for June's embedded micro-channels: the cooled surface is the
        # substrate underside and the TIM top reverts to natural convection.
        h_lo, h_hi, h = 20000.0, 400000.0, 60000.0
        h_bot = None
    hist = []
    prev = None
    for it in range(9):
        t0 = time.time()
        if topology == "top":
            r = kw1.coupled_1kw("ARCH_A", "distributed", 1.5, h, stack, doe, wd,
                                tol=0.1, max_it=8)
        else:
            r = kw1.coupled_1kw("ARCH_A", "distributed", 1.5, 10.0, stack, doe, wd,
                                tol=0.1, max_it=8, h_bottom=h)
        if not r["feasible"]:
            raise RuntimeError(r["reason"])
        T = r["T_max_C"]
        q_tot = kw1.P_LOAD_W + r["P_pdn_w"] + r["P_conv_w"]
        hist.append({"iter": it, "h_top_W_m2K": h, "T_max_C": T, "residual_K": T - TARGET_TJ_C,
                     "P_conv_w": r["P_conv_w"], "P_pdn_w": r["P_pdn_w"], "Q_total_w": q_tot,
                     "efficiency_pct": r["efficiency_pct"],
                     "energy_residual_pct": r["energy_residual_pct"],
                     "et_iters": r["et_iters"], "wall_s": time.time() - t0})
        print(f"  it{it}  h={h:9.1f}  T_max={T:7.3f} C  resid={T-TARGET_TJ_C:+7.3f} K  "
              f"P_conv={r['P_conv_w']:6.2f} P_pdn={r['P_pdn_w']:6.2f} Q={q_tot:7.1f} W  "
              f"eta={r['efficiency_pct']:5.2f}%  ({time.time()-t0:.0f}s)", flush=True)
        if abs(T - TARGET_TJ_C) < TOL_K:
            break
        if T > TARGET_TJ_C:
            h_lo = h
        else:
            h_hi = h
        # secant on 1/h, which is nearly linear in temperature rise for a Robin boundary
        if prev is not None and abs(prev[1] - T) > 1e-9:
            inv = 1.0 / prev[0] + (1.0 / h - 1.0 / prev[0]) * \
                  (TARGET_TJ_C - prev[1]) / (T - prev[1])
            cand = 1.0 / inv if inv > 0 else None
            if cand and h_lo < cand < h_hi:
                prev = (h, T); h = cand; continue
        prev = (h, T)
        h = 0.5 * (h_lo + h_hi)

    fin = hist[-1]
    out = {"h_top_W_m2K": fin["h_top_W_m2K"], "target_T_max_C": TARGET_TJ_C,
           "achieved_T_max_C": fin["T_max_C"], "residual_K": fin["residual_K"],
           "converged": abs(fin["residual_K"]) < TOL_K,
           "load_w": kw1.P_LOAD_W, "Q_total_w": fin["Q_total_w"],
           "P_conv_w": fin["P_conv_w"], "P_pdn_w": fin["P_pdn_w"],
           "efficiency_pct": fin["efficiency_pct"],
           "m_vr": kw1.M_VR, "j_target": kw1.J_TARGET, "h_sub_mm": 1.5,
           "phase0b_h_top_W_m2K": 17521.63541738819,
           "ratio_vs_phase0b": fin["h_top_W_m2K"] / 17521.63541738819,
           "iterations": hist,
           "june_reference": {
               "T_j_max_C": 84.0, "total_system_loss_w": 210.0,
               "efficiency_pct": 82.6, "coolant_flow_g_s": 1.6,
               "cooling": "substrate-embedded micro-channel, channels adjacent to the GaN "
                          "switch layer (June-2026 Sec. IV-D)",
               "no_cooling_T_j_C": ">110", "no_cooling_loss_w": 225.0},
           "model_form_caveat": (
               "June places micro-channels INSIDE the substrate adjacent to the GaN switch "
               "layer. This model applies an equivalent Robin boundary at the TIM top surface, "
               "as every earlier phase did, so that Phase-0F results stay comparable with "
               "0B-0E. The calibration matches the junction temperature, not the internal "
               "temperature field; a substrate-side boundary would cool the converter layer "
               "more directly and the die less."),
           "status": "DERIVED"}
    out["cooling_topology"] = topology
    name = ("cooling_1kw_calibration.json" if topology == "top"
            else "cooling_1kw_calibration_substrate.json")
    (OUT / name).write_text(json.dumps(out, indent=2))
    print(f"\nh_top(1 kW) = {out['h_top_W_m2K']:.1f} W/m2K   "
          f"({out['ratio_vs_phase0b']:.2f}x the Phase-0B value)")
    print(f"T_max = {out['achieved_T_max_C']:.3f} C (target {TARGET_TJ_C}), "
          f"residual {out['residual_K']:+.3f} K, converged={out['converged']}")
    print(f"wrote {OUT/name}")


if __name__ == "__main__":
    main()
