#!/usr/bin/env python3
"""Phase-0L Part XIII -- re-audit the experiment design under the corrected constitutive models.

Uses the SAME statistics as Phase 0K-R Sec.15/17 (scripts/phase0kr/final_design.py) so that any
change is attributable to the constitutive model and not to a change of method:

    D            = max(w/eps) / min(w/eps) over the two profiles        [law discrimination]
    eff_by_cond  = min(strain ratio, energy ratio) at each condition    [architecture effect]
    Z_Q1 = ln(D) / sqrt(2/(beta^2 n) + SIM_SE_D^2)
    Z_Q2 = sum_c ln(eff_c) / sqrt(2/(beta^2 n) + SIM_SE_A^2) / sqrt(2)  [Stouffer over the two]
    ADEQUATE at Z >= 3; n is the smallest integer reaching it at the worst observed beta.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0l"
SIM_SE_D, SIM_SE_A, BETA_WORST, ZTARGET = 0.08, 0.06, 5.1, 3.0
A, B = "EXP_45_125", "EXP_110_150"


def load():
    rows = []
    for f in ("package_model_replay.csv", "package_model_replay_tight.csv"):
        p = OUT / f
        if p.is_file():
            rows += [r for r in csv.DictReader(open(p)) if r.get("status") == "OK"]
    best = {}
    for r in rows:
        k = (r["model"], r["arch"], r["profile_tag"])
        if k not in best or r.get("solver_control") == "TIGHT":
            best[k] = r
    # Solver settings must not vary across the models being compared. The control runs showed
    # the strain metric is insensitive to them (<= 0.41 %) but the inelastic ENERGY metric is
    # not (+11 to +24 % under tighter control), so a mixed set would inject a numerical
    # difference into the model-form spread and read as physics.
    ctrls = {v.get("solver_control", "DEFAULT") for v in best.values()}
    if len(ctrls) > 1:
        import sys as _s
        by = {}
        for k, v in best.items():
            by.setdefault(v.get("solver_control", "DEFAULT"), []).append(k)
        for c, ks in sorted(by.items()):
            print(f"  {c}: {len(ks)} runs", file=_s.stderr)
        _s.exit("REFUSING TO COMPARE: solver control is not uniform across the replay set. "
                "Complete the TIGHT matrix (scripts/phase0l/run_replay_tight_rest.py) first.")
    return best


def n_for(effect_log, sim_se, beta=BETA_WORST, combine=1.0):
    for n in range(4, 20001):
        se = math.sqrt(2.0 / (beta ** 2 * n) + sim_se ** 2)
        if effect_log / se / combine >= ZTARGET:
            return n
    return None


def main() -> int:
    d = load()
    models = sorted({k[0] for k in d})
    out = []
    print(f"{'model':>11} {'w/eps A':>9} {'w/eps B':>9} {'D':>8} {'effA':>7} {'effB':>7} "
          f"{'n_Q1':>6} {'n_Q2':>6} {'n_req':>6} {'pkgs':>6}  verdict")
    for m in models:
        need = [(m, a, c) for a in ("Z1", "Z2") for c in (A, B)]
        if not all(k in d for k in need):
            print(f"{m:>11}   incomplete -- skipped")
            continue
        we, eff = {}, {}
        for c in (A, B):
            z1, z2 = d[(m, "Z1", c)], d[(m, "Z2", c)]
            we[c] = float(z1["inelastic_work_MJ_per_m3"]) / float(z1["d_peeq_per_cycle"])
            r_s = float(z1["d_peeq_per_cycle"]) / float(z2["d_peeq_per_cycle"])
            r_e = (float(z1["inelastic_work_MJ_per_m3"])
                   / float(z2["inelastic_work_MJ_per_m3"]))
            eff[c] = min(r_s, r_e)
        D = max(we.values()) / min(we.values())
        nq1 = n_for(math.log(D), SIM_SE_D)
        # Q2 combines the two conditions; solve directly
        nq2 = None
        for n in range(4, 20001):
            se = math.sqrt(2.0 / (BETA_WORST ** 2 * n) + SIM_SE_A ** 2)
            if sum(math.log(eff[c]) for c in (A, B)) / se / math.sqrt(2.0) >= ZTARGET:
                nq2 = n; break
        nreq = max(nq1 or 0, nq2 or 0) if (nq1 and nq2) else None
        ceil_q1 = math.log(D) / SIM_SE_D
        ceil_q2 = sum(math.log(eff[c]) for c in (A, B)) / SIM_SE_A / math.sqrt(2.0)
        verdict = ("REACHABLE" if nreq else
                   "UNREACHABLE at any n -- simulation-uncertainty ceiling binds")
        print(f"{m:>11} {we[A]:9.2f} {we[B]:9.2f} {D:8.4f} {eff[A]:7.4f} {eff[B]:7.4f} "
              f"{str(nq1):>6} {str(nq2):>6} {str(nreq):>6} "
              f"{str(4*nreq) if nreq else '--':>6}  {verdict}")
        out.append({"model": m, "w_over_eps_45_125": we[A], "w_over_eps_110_150": we[B],
                    "D_discrimination": D, "pct_law_separation": 100 * (D - 1),
                    "eff_45_125": eff[A], "eff_110_150": eff[B],
                    "n_Q1_law": nq1, "n_Q2_arch": nq2, "n_required_per_cell": nreq,
                    "total_packages_4_cells": 4 * nreq if nreq else "",
                    "ceiling_Z_Q1": ceil_q1, "ceiling_Z_Q2": ceil_q2,
                    "beta_used": BETA_WORST, "Z_target": ZTARGET, "verdict": verdict})

    print()
    print("Phase-0K-R reference (pre-0L): D = 1.4395, 44.0 % separation, n = 34 per cell, "
          "136 packages.")
    if out:
        ds = [o["D_discrimination"] for o in out]
        ns = [o["n_required_per_cell"] for o in out if o["n_required_per_cell"]]
        print(f"Phase-0L: D spans {min(ds):.4f} to {max(ds):.4f} across the admitted models.")
        if ns:
            print(f"          n spans {min(ns)} to {max(ns)} per cell "
                  f"({4*min(ns)} to {4*max(ns)} packages).")
            print(f"          DESIGN VALUE = the worst case = n = {max(ns)}, "
                  f"{4*max(ns)} packages.")
    p = OUT / "experiment_reaudit.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
