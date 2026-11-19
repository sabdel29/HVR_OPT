"""Direct-feed crossover R* of the backside integrations within each cooling tier.

final_closure_direct_feed.py solves R* on the production cases. In the three-tier comparison
each tier has its own cases (tcpmt_cases): the crossover of a backside integration b against
Z1 within tier t uses b's converged temperatures in that tier and Z1's package-internal loss in
the same tier, with the same self-consistent platform model
(final_closure_direct_feed.platform_point/crossover).

Review round 2:
  * the cases come from tcpmt_cases, for the PRODUCTION state (implemented decoupling; the feed
    carries k_eq x the average current) and the S0 / S1 references;
  * Z3 is the COUPLED land-side case: its land-side and board-plane rows are put back into the
    re-evaluated ledger (tcpmt_z3land_variants, at the case's own t_Cu and plane allocation and
    the converged land/board temperatures) -- without them the re-evaluation would be the
    superseded uncoupled ledger;
  * every case is re-evaluated in its own converter lineage (electrical.rules_of), and the
    zero-feed re-evaluation must reproduce the case's loss;
  * R* = 0 means b is behind Z1 even with a lossless feed: reported as "none".

    python tcpmt_tier_feed.py   -> research/tcpmt_revision/tier_feed_crossover.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_direct_feed as DF                              # noqa: E402
import tcpmt_cases as TC                                            # noqa: E402

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "tier_feed_crossover.json"
#: the zero-feed re-evaluation must reproduce the case's package-internal loss to this (W)
REPRO_TOL_W = 0.05


def _prepare(arch, case):
    """Hooks the case's ledger needs: the implemented-decoupling scenario, and Z3's coupled
    land-side rows at the case's own configuration."""
    if case.get("scenario") == TC.SCEN["SDEC"]:
        import tcpmt_decap_framework as DFW
        rk = DFW.recommended_k()
        DFW._register(rk["k_eq"], DFW.k_open(), rk["P_ring_esr_W"], key=TC.SCEN["SDEC"])
    if arch == "Z3":
        zl = case.get("z3_land") or {}
        if not zl:
            raise RuntimeError("an uncoupled Z3 case cannot enter the comparison")
        import tcpmt_z3land_variants as ZL
        ZL.configure(zl["t_land_um"], zl.get("board_planes_in_ledger", True),
                     zl.get("deposit") == "fv_map")
        ZL.patch_ledger()
        ZL.patch_regions()


def crossover_record(state, tier, arch):
    import replay_production as RPX                       # (puts scripts/phase0d on the path)
    import electrical as EL
    p1, z1 = TC.load(state, tier, "Z1")
    pb, cb = TC.load(state, tier, arch)
    if z1 is None or cb is None:
        return None
    _prepare(arch, cb)
    scen = cb["scenario"]
    with EL.pinned_rules(EL.rules_of(cb)):
        RPX._DESIGN_CACHE.clear()
        temps = DF.converged_temps(cb)
        base = DF.platform_point(scen, temps, 0.0, arch=arch)
        r = DF.crossover(scen, temps, z1["P_loss_w"], arch=arch)
    RPX._DESIGN_CACHE.clear()
    dp = base["P_total_w"] - cb["P_loss_w"]
    if abs(dp) > REPRO_TOL_W:
        raise RuntimeError(f"{pb.name}: the zero-feed re-evaluation gives {base['P_total_w']:.3f} W "
                           f"against the case's {cb['P_loss_w']:.3f} W")
    return {"P_Z1_w": z1["P_loss_w"], "P_internal_w": cb["P_loss_w"],
            "P_internal_recomputed_w": base["P_total_w"], "reproduction_w": dp,
            "advantage_at_zero_feed_w": z1["P_loss_w"] - cb["P_loss_w"],
            "k_feed": DF.FL.SCEN_RATIO[scen], "I_48_rms_a": base["I_48_rms_a"],
            "R_star_mohm": None if r is None else r * 1e3,
            "R_star_label": ("none" if r == 0.0 else "beyond 1 Ohm" if r is None
                             else f"{r * 1e3:.1f} mOhm"),
            "case": pb.name, "Z1_case": p1.name,
            "converter_rules": EL.rules_of(cb)}


def main():
    out = {"rule": "R* of backside integration b against Z1 within one cooling tier, from b's "
                   "converged temperatures in that tier; 0 ('none') = behind at zero feed",
           "production_state": TC.PRODUCTION_STATE, "states": {}}
    for st in TC.STATES:
        for t in TC.TIERS:
            for b in ("Z2", "Z3"):
                try:
                    rec = crossover_record(st, t, b)
                except Exception as e:                       # noqa: BLE001 -- recorded
                    rec = {"error": str(e)[-400:]}
                if rec is None:
                    continue
                out["states"].setdefault(st, {}).setdefault(t, {})[b] = rec
                print(st, t, b, {k: rec.get(k) for k in ("P_Z1_w", "P_internal_w",
                                                         "R_star_label", "error")}, flush=True)
    out["tiers"] = out["states"].get(TC.PRODUCTION_STATE, {})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
