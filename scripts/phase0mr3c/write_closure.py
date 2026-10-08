#!/usr/bin/env python3
"""Phase-0M-R3C --- final pair status and the phase closure document."""
from __future__ import annotations
import csv, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
HIST_D = 1.1943


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def main() -> int:
    etm = {r["case"]: r for r in rd("final_etm_replay.csv")}
    feas = rd("routing_feasibility.csv")
    fz = yaml.safe_load((R / "configs/phase0mr3c/frozen_pair_Z1.yaml").read_text())
    sel = [r for r in feas if r["candidate"] == "repartition_C1" and r["pitch_um"] == "150.0"]
    base = [r for r in feas if r["candidate"] == "baseline_T1" and r["pitch_um"] == "150.0"]
    z1, z2 = etm["Z1"], etm["Z2"]
    d = float(z1["response_driver_um"]) / float(z2["response_driver_um"])

    rows = []
    for tag, arch in (("Z1", "ARCH_Z1_EMBEDDED"), ("Z2", "ARCH_Z2_BACKSIDE")):
        e = etm[tag]
        rows.append({
            "case": tag, "architecture": arch,
            "partition": fz["partition"]["template"],
            "verdict": "GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL",
            "geometry_status": "CLOSES at a source-bounded microvia pitch",
            "process_status": "OPEN -- microvia current allowable, capture pad, vendor rule",
            "proven_realizable": False,
            "worst_via_levels": max(int(r["via_levels"]) for r in sel),
            "worst_aspect_ratio": max(float(r["AR_worst"]) for r in sel),
            "worst_routing_ratio_framework": max(float(r["routing_ratio"]) for r in sel),
            "P_total_electronics_w": float(e["P_total_electronics_w"]),
            "T_max_C": float(e["T_max_C"]), "T_mean_C": float(e["T_mean_C"]),
            "die_warpage_pv_um": float(e["die_warpage_pv_um"]),
            "response_driver_um": float(e["response_driver_um"]),
            "energy_residual_pct": float(e["energy_residual_pct"]),
            "D_driver_final": round(d, 4), "D_driver_0MR3_historical": HIST_D,
            "ordering_survives": d > 1.0,
        })
    with (OUT / "final_pair_status.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    L = ["# PHASE 0M-R3C --- COMPONENT REPARTITIONING, PHYSICAL REALIZABILITY AND PAPER "
         "FREEZE", "",
         "**Verdict: B --- A PROCESS-CONDITIONAL REPARTITION EXISTS, AND THE FINAL Z1/Z2 "
         "RESPONSE ORDERING SURVIVES.**", "",
         f"D_driver_final = **{d:.4f}** against the historical {HIST_D:.4f}: "
         f"**{100*(d-HIST_D)/HIST_D:+.2f} %**. The entire interconnect correction -- a "
         f"re-derived conductor-plane topology, a repartitioned stack, corrected physical "
         f"spans and a source-bounded via geometry -- moves the deciding ratio by four "
         f"hundredths of a percent.", "", "---", "",
         "## 1. The three-level via count was wrong --- DEFECT #64", "",
         "Phase 0M-R3B counted three MATERIAL layers across the 120 um gap and concluded "
         "three stacked microvia levels, then measured that against a sourced stacking "
         "limit and reported zero feasible configurations. `RDL_UM = 10 um` is an "
         "interlayer REDISTRIBUTION layer -- patterned copper, which is precisely what a "
         "microvia lands on. Counting conductor planes instead of material layers:", "",
         "| # | z | structure | via? |", "|---|---|---|---|",
         "| 0 | 1301 um | gan_ls terminal face | no |",
         "| 1 | 1301-1311 | interlayer RDL --- CONDUCTOR PLANE, a capture land | no |",
         "| 2 | 1311-1411 | flying-capacitor power layer, no conductor plane inside | "
         "**yes, one level** |",
         "| 3 | 1411-1421 | interlayer RDL --- CONDUCTOR PLANE | no |",
         "| 4 | 1421 um | inductor terminal face | no |", "",
         "**One via level, not three.** The stacking-limit objection dissolves, and the "
         "Phase-0M-R3B conclusion that no configuration satisfies both sourced bounds is "
         "**withdrawn**: the baseline already passes at a sourced pitch "
         f"({float(base[0]['routing_ratio']):.3f} at 150 um for ls_to_L).", "",
         "## 2. What the baseline's real problem was", "",
         "Not `ls_to_L`. Re-counted properly, the binding net is **`hs_to_cf`**, which in "
         "the Phase-0M-R3 tier order crosses the entire 606 um low-side GaN tier in one "
         "via level:", "",
         "| net | baseline depth | baseline AR | repartitioned depth | repartitioned AR |",
         "|---|---|---|---|---|"]
    bm = {r["net"]: r for r in base}
    sm = {r["net"]: r for r in sel}
    for n in ("ls_to_L", "hs_to_ls", "hs_to_cf"):
        L.append(f"| `{n}` | {float(bm[n]['dielectric_depth_um']):.0f} um | "
                 f"{float(bm[n]['AR_worst']):.2f} | "
                 f"{float(sm[n]['dielectric_depth_um']):.0f} um | "
                 f"**{float(sm[n]['AR_worst']):.2f}** |")
    L += ["", f"Worst aspect ratio falls from **{max(float(r['AR_worst']) for r in base):.2f}** "
          f"to **{max(float(r['AR_worst']) for r in sel):.2f}**.", "",
          "## 3. The repartition", "",
          f"`{fz['partition']['template']}`: "
          f"**{' / '.join(fz['partition']['tiers_bottom_to_top'])}**", "",
          f"{fz['partition']['what_moved']}. {fz['partition']['why']}.", "",
          f"It is a PERMUTATION: {fz['partition']['invariants']}. "
          f"{fz['partition']['source_compatibility']}.", "",
          "144 of the enumerated partitions satisfy the per-tier area budget and 8 keep "
          "both sourced stack ends; this is the best of those 8 on the brief's hierarchy.",
          "", "## 4. Framework provisioning is not a process qualification", "",
          "Both statuses are carried separately everywhere, as they must be:", "",
          "| net | n_req (framework, J_design) | n_avail | ratio | AR | process |",
          "|---|---|---|---|---|---|"]
    for n in ("ls_to_L", "hs_to_ls", "hs_to_cf"):
        r = sm[n]
        L.append(f"| `{n}` | {r['n_required_framework']} | {r['n_available']} | "
                 f"{float(r['routing_ratio']):.3f} | {float(r['AR_worst']):.3f} | **OPEN** |")
    L += ["", "`n_required` is a CONSERVATIVE DESIGN-SIDE ALLOCATION at J_design = 1e8 "
          "A/m2. No sourced current allowable exists for this microvia technology, so it "
          "is never a statement about what manufacturing requires.", "",
          "Two facts from primary sources obtained this phase sharpen the picture:", "",
          "* the **EPC2057 datasheet** shows the part is a bare die with FOUR solder bars "
          "(pad 1 gate, pads 2 and 4 source, pad 3 drain) on 1500 x 1200 um, so the "
          "switch-node landing area is at most a quarter of the die, not its whole "
          "footprint;",
          "* the `ls_to_L` edge is an **aggregate over K = 3 phases**. Per device the "
          "switch node carries 6.803 A, inside the EPC2057's 9.6 A continuous rating, and "
          "there are three such dies each with their own drain bar.", "",
          "## 5. The one final ETM replay", "",
          "Both configurations were frozen in `configs/phase0mr3c/frozen_pair_*.yaml` "
          "before solving. One solve each, identical settings, no sweep.", "",
          "| | Z1 | Z2 |", "|---|---|---|",
          f"| P_electronics | {float(z1['P_total_electronics_w']):.3f} W | "
          f"{float(z2['P_total_electronics_w']):.3f} W |",
          f"| T_max | {float(z1['T_max_C']):.2f} C | **{float(z2['T_max_C']):.2f} C** |",
          f"| T_mean | {float(z1['T_mean_C']):.2f} C | {float(z2['T_mean_C']):.2f} C |",
          f"| die warpage P-V | {float(z1['die_warpage_pv_um']):.3f} um | "
          f"{float(z2['die_warpage_pv_um']):.3f} um |",
          f"| local fatigue-relevant inelastic response | "
          f"{float(z1['response_driver_um']):.4f} um | "
          f"**{float(z2['response_driver_um']):.4f} um** |",
          f"| energy residual | {float(z1['energy_residual_pct']):.3f} % | "
          f"{float(z2['energy_residual_pct']):.3f} % |", "",
          f"**D_driver_final = {d:.4f}.** Z2 carries "
          f"{100*(float(z1['response_driver_um'])-float(z2['response_driver_um']))/float(z1['response_driver_um']):.1f} % "
          f"less response while running "
          f"{float(z2['T_max_C'])-float(z1['T_max_C']):+.2f} K hotter. The ordering "
          f"survives, and the temperature/response decoupling survives with it.", "",
          "## 6. What is still not earned", "",
          "Neither architecture is PROVEN_REALIZABLE. Geometry closes; the microvia "
          "current allowable, the capture-pad diameter, a vendor design rule and two "
          "package clearances remain OPEN. The licensed verdict is "
          "**GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL**.", "",
          "## Verdicts considered and rejected", "",
          "| candidate | why rejected |", "|---|---|",
          "| **A** source-compatible repartition, ordering survives | 'source-compatible' "
          "would claim the process rules are closed. Four are OPEN |",
          "| **C** repartition found, ordering CHANGES | it does not: +0.04 % |",
          "| **D** no realizable repartition exists | contradicted. 144 partitions meet the "
          "area budget, 8 keep the sourced stack ends, and the best has worst AR 0.83 |",
          "| **E** geometry closes but process data insufficient | true, and it omits the "
          "result the gate was opened to get: the replay ran and the ordering held. B "
          "states both |", "",
          "## Framework status", "",
          "**DEVELOPMENT STOPS HERE.** No fundamental contradiction was found. G2 remains "
          "NOT TESTED, the optimizer remains FORBIDDEN, and the next action is manuscript "
          "freeze."]
    (OUT / "PHASE0MR3C_REPARTITION_AND_PAPER_FREEZE.md").write_text("\n".join(L) + "\n")
    print(f"  wrote PHASE0MR3C_REPARTITION_AND_PAPER_FREEZE.md ({len(L)} lines)")
    print(f"  D_driver_final = {d:.4f}  ({100*(d-HIST_D)/HIST_D:+.2f} % vs historical)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
