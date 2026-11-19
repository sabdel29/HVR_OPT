#!/usr/bin/env python3
"""TCPMT round 3 -- the designs of the design record compared through the chain.

    python tcpmt_design_comparison.py            -> tcpmt_revision/design_comparison.json
    python tcpmt_design_comparison.py kcheck     -> tcpmt_revision/k_check.json

compare  the production state (implemented decoupling) of every design the campaign ran:
         the production m36 (campaign root), the 5-tier co-design comparison m36t5, the
         thin-capacitor sensitivity m36thin and the count neighbours m25 / m49 (design
         subroots <root>/designs/<key>). For each integration and cooling: package loss,
         peak and die temperature, convergence and energy residual; then the COUNT RANKING
         through the chain (Z1, both coolings) against the screen's ranking (the DSE's P_total
         at 25 C, design record entry `screen`).
kcheck   the k_eq the campaign's own decoupling chain derived (input_decoupling.json summary)
         against the committed production k the package network was closed at (the design
         record's `decoupling` block); |delta| above K_TOL flags a re-closure.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import design_record as DR                                          # noqa: E402

ROOT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research")
K_TOL = 0.02
ARCHS, TIERS = ("Z1", "Z2", "Z3"), ("A", "B")


def design_root(key):
    """The results root of a design: the campaign root for the production design, its
    subroot otherwise (a campaign subroot when ETM_RESULTS_ROOT is a design subroot)."""
    base = ROOT
    if base.parent.name == "designs":
        base = base.parent.parent
    return base if key == DR.production_key() else base / "designs" / key


def case_file(key, arch, tier):
    return (design_root(key) / "final_closure" / "sensitivity" /
            f"etm_{arch}_HV_SDEC__sdec_{tier}.json")


def summary(path):
    if not path.is_file():
        return None
    c = json.loads(path.read_text())
    th = c.get("thermal") or {}
    return {"file": str(path), "P_loss_W": c.get("P_loss_w"), "T_max_C": th.get("T_max_C"),
            "die_T_max_C": c.get("die_T_max_C"), "et_converged": c.get("et_converged"),
            "energy_residual_rel": th.get("energy_residual_rel"),
            "design": (c.get("design") or {}).get("design")}


def compare():
    out = {"what": __doc__.split("\n\n")[1].strip(), "designs": {}, "ranking": {}}
    for key in DR.keys():
        e = DR.get(key)
        rec = {"role": e["role"], "tag": e["tag"], "n_vr": e["n_vr"],
               "screen_P_total_W": e["screen"]["P_total_W"],
               "screen_conv_W": e["screen"]["conv_total_W"],
               "conversion_25C_W": e["conversion_25C_W"],
               "converter_stack_um": e.get("converter_stack_um"), "cases": {}}
        for a in ARCHS:
            for t in TIERS:
                s = summary(case_file(key, a, t))
                if s:
                    rec["cases"][f"{a}_{t}"] = s
        out["designs"][key] = rec
    for t in TIERS:
        rows = [(k, d["n_vr"], d["screen_P_total_W"], (d["cases"].get(f"Z1_{t}") or {})
                 .get("P_loss_W")) for k, d in out["designs"].items()
                if DR.get(k)["role"] in ("production", "count neighbour")]
        have = [r for r in rows if r[3] is not None]
        screen_rank = [r[0] for r in sorted(rows, key=lambda r: r[2])]
        chain_rank = [r[0] for r in sorted(have, key=lambda r: r[3])]
        out["ranking"][f"Z1_{t}"] = {
            "screen_order_by_P_total": screen_rank, "chain_order_by_P_loss": chain_rank,
            "complete": len(have) == len(rows),
            "same_ranking": bool(len(have) == len(rows) and screen_rank == chain_rank),
            "rows": [{"design": k, "M": m, "screen_P_total_W": ps, "chain_P_loss_W": pc}
                     for k, m, ps, pc in rows]}
    f = ROOT / "tcpmt_revision" / "design_comparison.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps(out["ranking"], indent=1, default=float))
    return out


def kcheck():
    e = DR.get()
    committed = (e.get("decoupling") or {}).get("k_eq")
    f = ROOT / "tcpmt_revision" / "input_decoupling.json"
    derived = None
    if f.is_file():
        rec = (json.loads(f.read_text()).get("summary") or {}).get("recommended") or {}
        derived = rec.get("k_eq")
    out = {"design": DR.name(), "k_eq_committed": committed, "k_eq_derived": derived,
           "tolerance": K_TOL,
           "delta": (derived - committed) if (derived is not None and committed) else None}
    out["within_tolerance"] = (out["delta"] is not None and abs(out["delta"]) <= K_TOL)
    out["note"] = ("the package network was closed at k_eq_committed (configs/design_points."
                   "yaml decoupling); a delta beyond the tolerance means the BGA count must be "
                   "re-closed at the derived k (final_closure_pkg_network.py)")
    g = ROOT / "tcpmt_revision" / "k_check.json"
    g.parent.mkdir(parents=True, exist_ok=True)
    g.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["kcheck"]:
        kcheck()
    else:
        compare()
