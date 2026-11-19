"""Stabilized local solder response at the critical joints of the coupled Z3 land-side cases
(40-um land-side copper, board planes in the ledger, FV-map deposit; cooling A and B), with the
same harness, level (L0), settings and 48-cycle rule as the tier study (tcpmt_solder_cycles.py),
so the Z3 entries of the comparison rest on the coupled loss accounting.

    HVR_SCRATCH=... JOINT_BAND_FRAC=0.16666666666666666 LOCAL_THREADS=2 \
        python tcpmt_solder_z3land.py   -> research/tcpmt_revision/solder_z3land.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

R = Path(__file__).resolve().parents[1]
SENS = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "sensitivity"
OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "solder_z3land.json"
CASES = {"A": "z3_land_t40_A_fvmap", "B": "z3_land_t40_B_fvmap"}
N = 48


def main():
    tasks = []
    for tier, v in CASES.items():
        f = SENS / f"etm_Z3_HV_S0__{v}.json"
        js = json.loads(f.read_text())["mechanics"]["joint_search"]
        c = js["critical"]
        tasks.append(dict(study="z3land", tag=f"{tier}_Z3land_N{N}", du_um=c["du_um"],
                          T_C=c["T_C"], n_cyc=N,
                          meta={"tier": tier, "arch": "Z3", "case": v, "x_mm": c["x_mm"],
                                "y_mm": c["y_mm"]}))
    rec = C.run_tasks(tasks, procs=2)
    stab = json.loads((OUT.parent / "solder_studies.json").read_text())
    st = stab["stabilization"]["cases"]
    out = {"rule": "48-cycle L0 last-cycle increment at the coupled Z3 land-side critical joint",
           "cases": {}}
    for t in tasks:
        r = rec.get(t["tag"], {})
        per = r.get("per_cycle") or []
        v48 = r.get("d_peeq_per_cycle")
        # uncertainty: the tier study's Z3 numerical U (mesh + time + cycle + card grid) for the
        # same tier, applied to the new joint (same harness, same level)
        base = st.get(f"{t['meta']['tier']}_Z3", {})
        out["cases"][t["meta"]["tier"]] = {
            "case": t["meta"]["case"], "du_um": t["du_um"], "T_C": t["T_C"],
            "stabilised": v48, "per_cycle": per, "U_stab_num": base.get("U_stab_num"),
            "error": r.get("error")}
        print(t["tag"], v48, r.get("error"))
    OUT.write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
