#!/usr/bin/env python3
"""Phase-0H Sec.2 -- replay every authoritative electrical result after DEFECT #30.

Two jobs:

  A. Replay the eleven Phase-0E 240-W candidates with the corrected, scope-guarded
     arithmetic and report whether any RANKING changes. Phase 0G fixed the 1-kW numbers but
     never asked whether the 240-W conclusions moved.

  B. Produce the full interconnect decomposition at the 1-kW reference for both
     architectures, per tier, with the scope of every column stated.

Historical artifacts are never touched: everything is written under results/phase0h/.
"""
from __future__ import annotations
import csv, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0h", "phase0e", "phase0dr", "phase0b", "phase0f"):
    sys.path.insert(0, str(R / "scripts" / p))

import run_phase0e as P0E                       # noqa: E402
OUT = R / "results" / "phase0h"
OUT.mkdir(parents=True, exist_ok=True)
P0E.OUT = OUT / "replay240"                     # redirect BEFORE any run
P0E.OUT.mkdir(parents=True, exist_ok=True)

from etm.config import load_doe, load_stack     # noqa: E402
from stack import stacks_from_cfg               # noqa: E402
from architecture0e import evaluate             # noqa: E402
from scope import Scope                         # noqa: E402


def replay_240w():
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0b/cooling_calibration.json").read_text())["h_top_W_m2K"]
    rdl = stacks_from_cfg()["ectc2024_primary"]
    wd = P0E.OUT / "runs"
    cases = [("ARCH_A", f, 2.0, 0.5) for f in ("distributed", "asymmetric", "edge", "compact")]
    cases += [(a, "distributed", 2.0, h) for a in ("ARCH_A", "ARCH_B") for h in (0.2, 0.5)]
    cases += [("ARCH_A", "distributed", j, h) for j in (1.5, 4.0) for h in (0.2, 0.5)]
    seen, rows = set(), []
    print("A. 240-W Phase-0E replay with corrected scope")
    for arch, fam, j, h in cases:
        if (arch, fam, j, h) in seen:
            continue
        seen.add((arch, fam, j, h))
        t0 = time.time()
        r = P0E.coupled(arch, fam, j, h, stack, doe, h_top, wd, rdl)
        if r is None:
            print(f"  {arch:7s} {fam:11s} j={j} h={h}  NO DESIGN"); continue
        rows.append(r)
        print(f"  {arch:7s} {fam:11s} j={j:4.1f} h={h:.1f}  "
              f"P_pdn={r['P_pdn_w']:8.4f} P_el={r['P_elec_total_w']:8.3f} "
              f"Tmax={r['T_max_C']:6.2f} w={r['die_warpage_pv_um']:7.3f} "
              f"({time.time()-t0:.0f}s)", flush=True)
    cols = [c for c in rows[0] if c != "history"]
    with open(OUT / "replay240_candidates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    return rows


def decomposition_1kw():
    import kw1
    stack, doe = load_stack(), load_doe()
    h_top = json.loads((R / "results/phase0f/cooling_1kw_calibration.json").read_text())["h_top_W_m2K"]
    wd = OUT / "runs_decomp"
    print("\nB. full interconnect decomposition at the 1-kW reference")
    rows = []
    for arch in ("ARCH_A", "ARCH_B"):
        for h in (0.80, 1.50, 2.00):
            r = kw1.coupled_1kw(arch, "uniform", h, h_top, stack, doe, wd,
                                bc="BC_A", tol=0.01, max_it=20)
            if not r["feasible"]:
                print(f"  {arch} h={h}: {r['reason']}"); continue
            e = r["evaluation"] if "evaluation" in r else {}
            row = {"arch": arch, "h_sub_mm": h, "scope": "SYSTEM",
                   "P_conv_w": r["P_conv_w"], "P_tsv_w": r["P_tsv_w"],
                   "P_rdl_w": r["P_rdl_w"], "P_bga_w": r["P_bga_w"],
                   "P_c4_w": r["P_c4_w"], "P_microbump_w": r["P_microbump_w"],
                   "P_pdn_w": r["P_pdn_w"], "P_elec_total_w": r["P_elec_total_w"],
                   "T_max_C": r["T_max_C"], "die_warpage_pv_um": r["die_warpage_pv_um"],
                   "n_vr": kw1.M_VR}
            rows.append(row)
            print(f"  {arch} h={h:.2f}  conv={row['P_conv_w']:8.3f} tsv={row['P_tsv_w']:7.4f} "
                  f"rdl={row['P_rdl_w']:7.4f} ubump={row['P_microbump_w']:7.4f} "
                  f"bga={row['P_bga_w']:7.4f}  total={row['P_elec_total_w']:8.3f}", flush=True)
    with open(OUT / "interconnect_decomposition_1kw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return rows


def compare(rows):
    """Did any Phase-0E ranking move?"""
    old = {}
    for r in csv.DictReader(open(R / "results/phase0e/phase0e_candidates.csv")):
        old[(r["arch"], r["fam"], float(r["j"]), float(r["h_sub_mm"]))] = r
    print("\n=== 240-W RANKING COMPARISON (Phase 0E as published vs corrected) ===")
    print(f"{'case':34s} {'P_el old':>10s} {'P_el new':>10s} {'delta mW':>10s} {'d%':>7s}")
    pairs = []
    for r in rows:
        k = (r["arch"], r["fam"], float(r["j"]), float(r["h_sub_mm"]))
        o = old.get(k)
        if not o:
            continue
        po, pn = float(o["P_elec_total_w"]), r["P_elec_total_w"]
        pairs.append((k, po, pn))
        print(f"{str(k):34s} {po:10.4f} {pn:10.4f} {(pn-po)*1e3:10.2f} "
              f"{100*(pn-po)/po:7.3f}")
    ro = [k for k, po, _ in sorted(pairs, key=lambda t: t[1])]
    rn = [k for k, _, pn in sorted(pairs, key=lambda t: t[2])]
    print(f"\n  ranking identical: {ro == rn}")
    if ro != rn:
        for i, (a, b) in enumerate(zip(ro, rn)):
            if a != b:
                print(f"    position {i}: was {a}  now {b}")
    return ro == rn


if __name__ == "__main__":
    rows = replay_240w()
    same = compare(rows)
    decomposition_1kw()
    (OUT / "replay240_ranking_stable.json").write_text(
        json.dumps({"ranking_unchanged": bool(same), "n_cases": len(rows)}, indent=2))
    print("\nwrote results/phase0h/replay240_candidates.csv, "
          "interconnect_decomposition_1kw.csv")
