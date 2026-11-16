#!/usr/bin/env python3
"""Count-optimal SQUARE candidate: the full part list behind the DSE pick (case D).

The regulator-count sweep (research/tcpmt_revision/dse_j35/sweep_etm.py) writes the topology,
the two GaN part numbers, f_sw and the losses, but not the passives or the per-term split
that a physical cell and the ETM ledger need. This script re-runs EXACTLY the sweep's case-D
selection (discrete 90-device library, architecture re-synthesis, the sweep's component-count
candidates and its conversion + routing pick) through the sweep's own functions, and records
every selected part for each count asked. For a count with no feasible design it records why:
how many device / passive combinations pass each gate of the optimizer.

    DSE_ENGINE=<private engine copy> python -B candidate_dse.py --counts 49,64,72,76,81

Writes research/tcpmt_revision/countopt/candidate_dse.json (no field is computed here that the
sweep does not compute; the gate census re-applies the optimizer's own filters).

--hs-stress 2vin_over_n (SENSITIVITY, unconfirmed reading of the generalized schematic):
the high-side filter requires V_DS,max >= 2 V_in / N (S2..SN blocking 2 V_in / N) instead of
the optimizer's V_in / N -- 48 V at N = 2 against the 40-V EPC2014C, 32 V at N = 3. Writes
candidate_dse_hs_2vin_over_n.json.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "candidate_dse.json"
sys.path.insert(0, str(HERE.parent / "dse_j35"))
import sweep_etm as SW                                        # noqa: E402  (chdir to engine)
import numpy as np                                            # noqa: E402
import HVR_FULL_OPT_EPC_V2 as EPC                             # noqa: E402


def _plain(obj):
    if dataclasses.is_dataclass(obj):
        d = dataclasses.asdict(obj)
        d.pop("source", None)
        return {k: _plain(v) for k, v in d.items()}
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (list, tuple)):
        return [_plain(x) for x in obj]
    return obj


def die_config():
    return SW.DieConfig(die_area_mm2=SW.DIE_AREA_MM2, die_side_mm=math.sqrt(SW.DIE_AREA_MM2),
                        n_pol_segments=SW.N_POL, rho_mohm_per_mm=SW.RHO_MOHM_PER_MM,
                        i_out_total_a=SW.I_SYS, v_out=SW.V_OUT)


def common_kwargs(i_vr):
    return dict(target_component_count=SW.TARGET_CC, V_in=SW.V_IN, V_out=SW.V_OUT, I_out=i_vr,
                V_gs_drive=SW.V_GS, ripple_factor=SW.RIPPLE_FACTOR,
                v_ripple_frac=SW.V_RIPPLE_FRAC, I_target_density=SW.J_TARGET, verbose=False)


def gate_census(arch, i_vr, budget):
    """Re-apply the optimizer's gates (device/passive filters, area, current and voltage
    ripple) to one architecture and count what survives each, so an infeasible count states
    the gate that empties it."""
    df = EPC.load_epc_devices("EPC-Product-Table.csv", V_gs_op=SW.V_GS)
    hs, ls = EPC.filter_candidate_devices(df, arch, SW.V_IN, SW.V_OUT, SW.V_GS, i_vr,
                                          max(arch.B_array))
    inds = EPC.filter_candidate_inductors(EPC.INDUCTOR_LIBRARY, arch, i_vr)
    caps = EPC.filter_candidate_capacitors(EPC.CAPACITOR_LIBRARY, arch, SW.V_IN)
    f_sw = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)
    n_area = n_ripple = 0
    min_area, min_area_parts = float("inf"), None
    for h in hs:
        for l_ in ls:
            for ind in inds:
                f_ok = f_sw[f_sw <= ind.f_max_mhz * 1e6]
                if len(f_ok) == 0:
                    continue
                for c in caps:
                    a = EPC._compute_area(arch, h, l_, ind, c)
                    if a < min_area:
                        min_area, min_area_parts = a, (h.part_number, l_.part_number,
                                                       ind.name, c.name)
                    if a > budget:
                        continue
                    n_area += 1
                    for f in f_ok:
                        lr = EPC.compute_total_loss(arch, EPC.LossModelInputs(
                            hs_device=h, ls_device=l_, inductor=ind, capacitor=c,
                            I_out=i_vr, V_out=SW.V_OUT, V_in=SW.V_IN, f_sw=f))
                        if (abs(lr.delta_i_out) < SW.RIPPLE_FACTOR * i_vr
                                and lr.delta_v_out < SW.V_RIPPLE_FRAC * SW.V_OUT):
                            n_ripple += 1
                            break
    # the smallest-footprint high-side device that passes the electrical filter
    hs_small = sorted(hs, key=lambda d: (d.footprint_mm2 if np.isfinite(d.footprint_mm2)
                                         else 2.0))[:5]
    return {"arch": f"N={arch.N},K={arch.K},K_A={arch.K_A}", "B_array": arch.B_array,
            "area_budget_mm2": budget,
            "n_hs_pass_filter": len(hs), "n_ls_pass_filter": len(ls),
            "n_inductors_pass_filter": len(inds), "n_caps_pass_filter": len(caps),
            "n_combos_within_area": n_area, "n_combos_within_area_and_ripple": n_ripple,
            "min_area_any_combo_mm2": min_area, "min_area_parts": min_area_parts,
            "smallest_hs_passing_filter": [(d.part_number, d.footprint_mm2, d.ID_A)
                                           for d in hs_small]}


def candidate(m, die):
    i_vr = SW.I_SYS / m
    best, best_res = None, None
    tried = []
    for cc in SW.cc_candidates(i_vr / SW.J_TARGET):
        kw = common_kwargs(i_vr)
        kw["target_component_count"] = cc
        rr = SW.run_discrete(**kw)
        ch, why = SW.pick(rr, "best", m, die)
        tried.append({"cc": cc, "n_arch": len(rr), "picked": None if ch is None else
                      f"N={ch.architecture.N},K={ch.architecture.K},K_A={ch.architecture.K_A}",
                      "why_none": why})
        if ch is None:
            continue
        rec = SW.score(ch, m, die, cc)
        if best is None or rec["total_loss_W"] < best["total_loss_W"]:
            best, best_res = rec, ch
    out = {"M": m, "I_vr_A": i_vr, "area_budget_mm2": i_vr / SW.J_TARGET,
           "component_count_candidates": tried}
    if best is None:
        out["feasible"] = False
        rr = SW.run_discrete(**common_kwargs(i_vr))
        out["gate_census"] = [gate_census(r.architecture, i_vr, i_vr / SW.J_TARGET)
                              for r in rr]
        return out
    r = best_res
    a = r.architecture
    out.update({
        "feasible": True, "sweep_record": {k: _plain(v) for k, v in best.items()},
        "topology": {"N": a.N, "K": a.K, "K_A": a.K_A, "B_array": list(a.B_array),
                     "D": a.D, "component_count": a.component_count,
                     "label": f"N{a.N}K{a.K}K_A{a.K_A}"},
        "hs_device": _plain(r.optimized_hs_device), "ls_device": _plain(r.optimized_ls_device),
        "inductor": _plain(r.optimized_inductor), "capacitor": _plain(r.optimized_capacitor),
        "f_sw_hz": float(r.optimized_f_sw),
        "loss_per_vr_25C_W": {"total": float(r.optimized_loss), "p_cond": float(r.p_cond_opt),
                              "p_sw": float(r.p_sw_opt), "p_sw_hs": float(r.p_sw_hs_opt),
                              "p_sw_gd": float(r.p_sw_gd_opt),
                              "p_sw_coss": float(r.p_sw_coss_opt)},
        "conversion_total_W": float(r.optimized_loss) * m,
        "routing_W": best["routing_loss_W"], "routing_vic_W": best["routing_vic_W"],
        "routing_lateral_W": best["routing_lateral_W"], "total_W": best["total_loss_W"],
        "delta_i_out_A": float(r.delta_i_out_opt), "delta_v_out_V": float(r.delta_v_out_opt),
        "area_mm2": float(r.total_area_mm2),
        "per_tier_area_mm2": {
            "gan_hs": a.N * r.optimized_hs_device.footprint_mm2,
            "gan_ls": a.K * r.optimized_ls_device.footprint_mm2,
            "inductor": a.K * r.optimized_inductor.footprint_mm2,
            "cap_fly": (a.N - 1) * r.optimized_capacitor.footprint_mm2},
    })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts", default="49,64,72,76,81")
    ap.add_argument("--hs-stress", default="vin_over_n", choices=("vin_over_n", "2vin_over_n"))
    args = ap.parse_args()
    out_path = OUT
    if args.hs_stress == "2vin_over_n":
        orig = EPC.filter_candidate_devices

        def strict(df, arch, V_in, V_out, V_gs_drive, I_out, max_B):
            hs, ls = orig(df, arch, V_in, V_out, V_gs_drive, I_out, max_B)
            return [d for d in hs if d.VDSmax >= 2.0 * V_in / arch.N], ls
        EPC.filter_candidate_devices = strict
        out_path = HERE / "candidate_dse_hs_2vin_over_n.json"
    die = die_config()
    res = {"settings": {"J_target": SW.J_TARGET, "ripple_factor": SW.RIPPLE_FACTOR,
                        "v_ripple_frac": SW.V_RIPPLE_FRAC, "routing_arch": SW.ROUTING_ARCH,
                        "selection": "case D: re-synthesized topology, discrete library, "
                                     "min conversion + routing over the sweep's cc set",
                        "engine": SW.ENGINE, "hs_stress_filter": args.hs_stress},
           "counts": {}}
    for m in [int(x) for x in args.counts.split(",")]:
        res["counts"][str(m)] = candidate(m, die)
        c = res["counts"][str(m)]
        print(m, "feasible" if c["feasible"] else "INFEASIBLE",
              c.get("topology", {}).get("label", ""), flush=True)
    out_path.write_text(json.dumps(res, indent=1, default=float))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
