#!/usr/bin/env python3
"""
Controlled four-case comparison of system-level VR-count partitioning.

Cases
  A  fixed DSCH architecture  + continuous switch sizing
  B  architecture re-synthesis + continuous switch sizing
  C  fixed DSCH architecture  + discrete EPC device library
  D  architecture re-synthesis + discrete EPC device library

One optimizer call per (M, switch-model) returns every architecture, so A and B share a
continuous run and C and D share a discrete run. All four cases are then scored with the
SAME routing model at the SAME operating point, which is what makes the comparison
controlled.

Loss boundary for every number written here: CONVERSION + ROUTING ("matched").
The reference paper's end-to-end boundary is NOT reconstructed. See assumptions.md.
"""
import sys, os, json, math, time, csv, argparse
sys.path.insert(0, "/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine")
os.chdir("/home/beams0/SABDELZAHER/ETM_project/scratch/dse_engine")

import numpy as np
from HVR_FULL_OPT_sizing import run_hvr_optimization as run_continuous
from HVR_FULL_OPT_EPC_V2 import run_hvr_optimization as run_discrete
from Framework_w_HVR_OPT_sizing_v2 import DieConfig, DVPDRoutingModel
sys.path.insert(0, "/home/beams0/SABDELZAHER/Salma_Thesis/analysis/system_partitioning_comparison/scripts")
import paper_routing as PR

OUT = "/home/beams0/SABDELZAHER/ETM_project/scratch/dse_j35"

# ---- reference-paper operating point (assumptions.md Sec. 1) -------------------
V_IN, V_OUT      = 48.0, 1.0
P_LOAD           = 1000.0
I_SYS            = P_LOAD / V_OUT          # 1000 A
J_TARGET         = 3.5                     # A/mm2 (ETM paper specification)
DIE_AREA_MM2     = 500.0                   # paper load footprint
N_POL            = 100                     # paper POL segmentation
RHO_MOHM_PER_MM  = 50.0
TARGET_CC        = 15
V_GS             = 5.0
RIPPLE_FACTOR    = 0.5
V_RIPPLE_FRAC    = 0.25

# DSCH as identified in thesis Chapter 3 (Kirshenboim 2016). The reference paper does NOT
# state N for its DSCH, so this mapping is an assumption and is flagged in the report.
DSCH_NK = (3, 3)

ROUTING_ARCH = "A2"   # paper's 48/24/1 V placement style; same for all four cases


_RM_CACHE = {}
def routing_loss(m, f_sw_hz, die):
    """Reference-paper routing: Table III VIC chain + RDL-plane lateral path."""
    key = (m, round(f_sw_hz or 0.0, 3))
    if key in _RM_CACHE:
        return _RM_CACHE[key]
    rm = DVPDRoutingModel(die)
    pos = (DVPDRoutingModel.place_vrs_A1(m, die.die_side_mm) if ROUTING_ARCH == "A1"
           else DVPDRoutingModel.place_vrs_A2(m, die.die_side_mm))
    r = PR.total_routing_w(pos, rm.pols, die.i_out_total_a, f_sw_hz or 1e6,
                           die.die_side_mm, die.n_pol_segments)
    out = dict(total_ppdn_loss_w=r["total_routing_w"], vic_w=r["vic_w"],
               lateral_w=r["lateral_w"],
               avg_nearest_dist_mm=r["avg_nearest_dist_mm"],
               rho_ac_mohm_per_mm=r["rho_ac_mohm_per_mm"])
    _RM_CACHE[key] = out
    return out


AREA_PER_COMPONENT_MM2 = 0.48   # calibrated at the M=70 reference point (15 comps / 7.14 mm2)

def cc_candidates(area_budget_mm2):
    """Component count is area-driven: more per-VR area admits richer architectures.
    The optimizer still rejects anything that does not physically fit."""
    implied = area_budget_mm2 / AREA_PER_COMPONENT_MM2
    cands = {10, 15}
    for c in (22, 30):
        if implied > c * 0.75:
            cands.add(c)
    # Capped at 30. The M<32 points showed 40-component enumerations cost ~10 min each
    # and never won; the sweep now starts at M=32 where the optimum actually lives.
    return sorted(c for c in cands if c <= 30)


def pick(results, mode, m, die):
    """mode 'dsch' -> the fixed DSCH entry; 'best' -> feasible entry minimising TOTAL loss.

    Selection for 'best' is on conversion + routing, not conversion alone. Routing
    resistance carries a sqrt(f_sw) skin-effect term, so the architecture with the lowest
    conversion loss is not always the lowest at system level. Selecting on conversion
    alone was observed to pick N=4,K=4 at M=70 (lowest conversion, 1.35 MHz) over
    N=3,K=2 (0.68 MHz) and end up worse once routing was added, which would have made the
    architecture-free case look worse than the architecture-fixed one. That is a real
    cross-scale coupling and is reported, not hidden.
    """
    feas = [r for r in results
            if np.isfinite(r.optimized_loss) and r.ripple_satisfied and r.area_feasible]
    if mode == "best":
        if not feas:
            return None, "no feasible architecture"
        def tot(r):
            return (r.optimized_loss * m
                    + routing_loss(m, r.optimized_f_sw or 1e6, die)["total_ppdn_loss_w"])
        return min(feas, key=tot), None
    hits = [r for r in results if (r.architecture.N, r.architecture.K) == DSCH_NK]
    if not hits:
        return None, "DSCH not enumerated at this component budget"
    r = hits[0]
    if not np.isfinite(r.optimized_loss):
        return None, "DSCH infeasible: no finite loss"
    if not r.ripple_satisfied:
        return None, "DSCH infeasible: ripple constraint"
    if not r.area_feasible:
        return None, "DSCH infeasible: area/footprint constraint"
    return r, None


def score(res, m, die, cc):
    """Attach routing loss and build one output record. Matched boundary."""
    i_vr = I_SYS / m
    conv_tot = res.optimized_loss * m
    rl = routing_loss(m, res.optimized_f_sw or 1e6, die)
    route = rl["total_ppdn_loss_w"]
    vic_w, lat_w = rl.get("vic_w", float("nan")), rl.get("lateral_w", float("nan"))
    total = conv_tot + route
    a = res.architecture
    hs, ls = res.optimized_hs_device, res.optimized_ls_device
    def dev(d):
        if d is None: return ""
        for attr in ("name", "part_number", "width_mm", "w"):
            if hasattr(d, attr): return str(getattr(d, attr))
        return str(d)
    return dict(
        M=m, I_vr_A=i_vr, component_count=cc,
        arch=f"N={a.N},K={a.K},K_A={a.K_A}", N=a.N, K=a.K, K_A=a.K_A, D=a.D,
        conv_loss_per_vr_W=res.optimized_loss, conv_loss_total_W=conv_tot,
        routing_loss_W=route, routing_vic_W=vic_w, routing_lateral_W=lat_w,
        total_loss_W=total,
        efficiency_pct=100.0 * P_LOAD / (P_LOAD + total),
        f_sw_Hz=res.optimized_f_sw,
        hs=dev(hs), ls=dev(ls),
        p_cond_W=getattr(res, "p_cond_opt", float("nan")),
        p_sw_W=getattr(res, "p_sw_opt", float("nan")),
        area_mm2=res.total_area_mm2, area_budget_mm2=res.area_budget_mm2,
        area_util=(res.total_area_mm2 / res.area_budget_mm2
                   if res.area_budget_mm2 and np.isfinite(res.area_budget_mm2) else float("nan")),
        delta_i=getattr(res, "delta_i_out_opt", float("nan")),
        avg_nearest_dist_mm=rl["avg_nearest_dist_mm"],
        rho_ac_mohm_per_mm=rl["rho_ac_mohm_per_mm"],
        feasible=True, reason="",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts", default="")
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    if args.counts:
        counts = [int(x) for x in args.counts.split(",")]
    else:
        counts = sorted(set(
            [10,12,14,16,20,24,28,32,36,40,44,48,52,56,60,64,70,76,80,88,96,
             104,112,120,130,140,150,160,170,180,190,200]))

    die = DieConfig(die_area_mm2=DIE_AREA_MM2, die_side_mm=math.sqrt(DIE_AREA_MM2),
                    n_pol_segments=N_POL, rho_mohm_per_mm=RHO_MOHM_PER_MM,
                    i_out_total_a=I_SYS, v_out=V_OUT)

    rows = {c: [] for c in "ABCD"}
    allarch = []   # every architecture at every M, for diagnostics

    for m in counts:
        i_vr = I_SYS / m
        t0 = time.time()
        common = dict(target_component_count=TARGET_CC, V_in=V_IN, V_out=V_OUT, I_out=i_vr,
                      V_gs_drive=V_GS, ripple_factor=RIPPLE_FACTOR,
                      v_ripple_frac=V_RIPPLE_FRAC, I_target_density=J_TARGET, verbose=False)

        ccs = cc_candidates(i_vr / J_TARGET)
        for switch_mode, runner, (fixed_case, var_case) in (
                ("continuous", run_continuous, ("A", "B")),
                ("discrete",   run_discrete,   ("C", "D"))):
            res, used_cc, errs = [], None, []
            best_by_case = {fixed_case: None, var_case: None}
            for cc in ccs:
                kw = dict(common); kw["target_component_count"] = cc
                try:
                    rr = runner(**kw)
                except Exception as e:
                    errs.append(f"cc={cc}: {e}"); continue
                for case, mode in ((fixed_case, "dsch"), (var_case, "best")):
                    ch, _why = pick(rr, mode, m, die)
                    if ch is None:
                        continue
                    rec = score(ch, m, die, cc)
                    if (best_by_case[case] is None
                            or rec["total_loss_W"] < best_by_case[case]["total_loss_W"]):
                        best_by_case[case] = rec
                res.extend(rr); used_cc = cc
                for r in rr:
                    a = r.architecture
                    allarch.append(dict(M=m, switch_mode=switch_mode, cc=cc,
                                        N=a.N, K=a.K, K_A=a.K_A,
                                        loss=r.optimized_loss if np.isfinite(r.optimized_loss) else "",
                                        ripple_ok=r.ripple_satisfied, area_ok=r.area_feasible,
                                        f_sw=r.optimized_f_sw or "",
                                        area=r.total_area_mm2, budget=r.area_budget_mm2))
            for case in (fixed_case, var_case):
                if best_by_case[case] is None:
                    why = ("optimizer error: " + "; ".join(errs)) if errs and not res else (
                        "DSCH infeasible at every component count tried"
                        if case in ("A", "C") else "no feasible architecture at any component count")
                    rows[case].append(dict(M=m, I_vr_A=i_vr, feasible=False, reason=why))
                else:
                    rows[case].append(best_by_case[case])
            continue

            for r in res:
                a = r.architecture
                allarch.append(dict(M=m, switch_mode=switch_mode, N=a.N, K=a.K, K_A=a.K_A,
                                    loss=r.optimized_loss if np.isfinite(r.optimized_loss) else "",
                                    ripple_ok=r.ripple_satisfied, area_ok=r.area_feasible,
                                    f_sw=r.optimized_f_sw or "",
                                    area=r.total_area_mm2, budget=r.area_budget_mm2))

            for case, mode in ((fixed_case, "dsch"), (var_case, "best")):
                chosen, why = pick(res, mode, m, die)
                if chosen is None:
                    rows[case].append(dict(M=m, I_vr_A=i_vr, feasible=False, reason=why))
                else:
                    rows[case].append(score(chosen, m, die))

        print(f"M={m:4d}  I_vr={i_vr:7.2f} A  "
              + "  ".join(f"{c}:{(rows[c][-1].get('total_loss_W') or float('nan')):8.2f}W"
                          if rows[c][-1]["feasible"] else f"{c}:    INFEAS" for c in "ABCD")
              + f"   [{time.time()-t0:.1f}s]", flush=True)

    os.makedirs(f"{OUT}/data", exist_ok=True)
    for c in "ABCD":
        keys = sorted({k for r in rows[c] for k in r})
        with open(f"{OUT}/data/case_{c}_{args.tag}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows[c])
    keys = sorted({k for r in allarch for k in r})
    with open(f"{OUT}/data/all_architectures_{args.tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(allarch)

    meta = dict(V_in=V_IN, V_out=V_OUT, P_load=P_LOAD, I_sys=I_SYS, J_target=J_TARGET,
                die_area_mm2=DIE_AREA_MM2, n_pol=N_POL, rho_mohm_per_mm=RHO_MOHM_PER_MM,
                target_component_count=TARGET_CC, ripple_factor=RIPPLE_FACTOR,
                v_ripple_frac=V_RIPPLE_FRAC, dsch_NK=list(DSCH_NK),
                routing_arch=ROUTING_ARCH, boundary="conversion+routing (matched)",
                counts=counts)
    json.dump(meta, open(f"{OUT}/data/meta_{args.tag}.json", "w"), indent=2)
    print("\nwrote", f"{OUT}/data/")


if __name__ == "__main__":
    main()
