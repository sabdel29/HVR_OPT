"""Direct-feed crossover R* of the backside integrations within each cooling tier.

final_closure_direct_feed.py solves R* on the production cases. In the three-tier
comparison of the TCPMT revision each tier has its own cases (tcpmt_manuscript_macros.TIERS):
the crossover of a backside integration b against Z1 within tier t uses b's converged
temperatures in that tier and Z1's package-internal loss in the same tier, with the same
self-consistent platform model (final_closure_direct_feed.platform_point/crossover).

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
import tcpmt_manuscript_macros as TM                                 # noqa: E402

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "tier_feed_crossover.json"


def case_json(kind, arch, variant):
    f = (TM.D / f"etm_{arch}_HV_S0_h1.1_r21.json" if kind == "prod"
         else TM.D / "sensitivity" / f"etm_{arch}_HV_S0__{variant}.json")
    return json.loads(f.read_text()) if f.exists() else None


def main():
    out = {"rule": "R* of backside integration b against Z1 within one cooling tier, from b's "
                   "converged temperatures in that tier (S0); 0 = behind at zero feed",
           "tiers": {}}
    for t in ("A", "B"):
        row = TM.TIERS[t]
        z1 = case_json(*row["Z1"][:1], "Z1", row["Z1"][1])
        if z1 is None:
            continue
        p_z1 = z1["P_loss_w"]
        for b in ("Z2", "Z3"):
            kind, v = row[b]
            cb = case_json(kind, b, v)
            if cb is None:
                continue
            temps = DF.converged_temps(cb)
            base = DF.platform_point("HV_S0", temps, 0.0, arch=b)
            r = DF.crossover("HV_S0", temps, p_z1, arch=b)
            out["tiers"].setdefault(t, {})[b] = {
                "P_Z1_w": p_z1, "P_internal_w": cb["P_loss_w"],
                "P_internal_recomputed_w": base["P_total_w"],
                "R_star_mohm": None if r is None else r * 1e3,
                "case": (f"etm_{b}_HV_S0__{v}.json" if kind == "sens"
                         else f"etm_{b}_HV_S0_h1.1_r21.json")}
            print(t, b, out["tiers"][t][b], flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
