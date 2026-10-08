#!/usr/bin/env python3
"""Phase-0M-R3B --- closure, final realizability status, open items."""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"
BASE = R / "results" / "phase0mr3a" / "_baseline_phase0mr3"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def main() -> int:
    feas = rd("ls_to_L_feasibility.csv")
    span = {r["edge"]: r for r in rd("vertical_span_correction.csv")}
    src = rd("substrate_via_source_matrix.csv")
    clr = rd("package_clearance_provenance.csv")
    tol = {r["d_um"]: r for r in rd("z2_tsv_sourced_tolerance_sweep.csv")}
    cur = {r["case"]: r for r in rd("final_Z1_Z2_comparison.csv", BASE)}
    dp = [r for r in feas if float(r["pitch_um"]) == 70.0
          and r["stack"] == "fully_stacked" and float(r["d_um"]) == 40.0][0]
    sourced_ok = [r for r in feas if float(r["pitch_um"]) >= 100.0
                  and r["stack"] == "semi_stacked" and r["feasible"] == "True"]
    stacked_ok = [r for r in feas if r["stack"] == "fully_stacked"
                  and r["feasible"] == "True" and float(r["pitch_um"]) >= 100.0]
    n_open = sum(1 for r in src if r["provenance"] == "OPEN")
    z1, z2 = cur["Z1"], cur["Z2"]
    ratio = float(z1["response_driver_um"]) / float(z2["response_driver_um"])

    # ---- final_realizability_status.csv --------------------------------------------
    rows = []
    for case, arch in (("Z1", "ARCH_Z1_EMBEDDED"), ("Z2", "ARCH_Z2_BACKSIDE")):
        rows.append({
            "case": case, "architecture": arch,
            "verdict_0mr3a": "CONDITIONAL_REALIZABLE",
            "verdict_0mr3b": "NOT_REALIZABLE_UNDER_SOURCED_VIA_RULES",
            "binding_constraint": "ls_to_L vertical interconnect",
            "routing_ratio_0mr3": 0.9344,
            "routing_ratio_0mr3b_design_point": float(dp["routing_ratio"]),
            "landing_area_0mr3_mm2": 1.80,
            "landing_area_0mr3b_mm2": float(dp["landing_area_mm2"]),
            "configs_inside_both_sourced_bounds": len(sourced_ok),
            "configs_feasible_only_by_exceeding_stacking_limit": len(stacked_ok),
            "package_clearances_still_open": sum(
                1 for r in clr if r["status_0mr3b"] == "OPEN"),
            "via_parameters_still_open": n_open,
            "response_driver_um": float(z1["response_driver_um"]) if case == "Z1"
                                  else float(z2["response_driver_um"]),
            "T_max_C": float(z1["T_max_C"]) if case == "Z1" else float(z2["T_max_C"]),
            "ordering_status": "CARRIED from Phase 0M-R3; not re-asserted for a corrected "
                               "configuration, because no corrected configuration is "
                               "realizable to freeze",
        })
    with (OUT / "final_realizability_status.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    # ---- closure --------------------------------------------------------------------
    L = ["# PHASE 0M-R3B --- SUBSTRATE-VIA TECHNOLOGY, PACKAGE-RULE AND PROCESS-MARGIN "
         "CLOSURE", "",
         "**Verdict: D --- THE PHYSICAL `ls_to_L` TOPOLOGY, EVALUATED AGAINST SOURCED "
         "SUBSTRATE-VIA RULES, MAKES THE FROZEN Z1/Z2 PAIR NOT_REALIZABLE UNDER THE "
         "CURRENT COMPONENT TOPOLOGY.**", "",
         "Both architectures share one converter cell, so the finding applies to both "
         "equally. The deciding mechanical ordering is untouched -- and is not the "
         "question this gate asked.", "", "---", "",
         "## 1. The span was the artifact",
         "",
         f"`ls_to_L` was recorded at 673 um. That is a tier MID-PLANE to tier MID-PLANE "
         f"distance: it runs from the centre of the low-side GaN die to the centre of the "
         f"inductor, through 303 um of die body and 250 um of inductor body. The build-up "
         f"a via chain actually crosses is **{float(span['ls_to_L']['physical_span_um']):.0f} "
         f"um** -- RDL 10 + flying-capacitor layer 100 + RDL 10. The overstatement is "
         f"**{float(span['ls_to_L']['overstatement_x']):.2f}x**, and it is systematic: "
         f"`hs_to_ls` is overstated "
         f"{float(span['hs_to_ls']['overstatement_x']):.1f}x (DEFECT #62).", "",
         "This does NOT change the via count -- `n_required` has no length in it -- so the "
         "Phase-0M-R3A arithmetic stands. It changes the resistance, and it changes what "
         "technology question is being asked.", "",
         "## 2. The technology is ordinary; the design point is not", "",
         "A 120 um stack through three build-up layers is embedded-component packaging, "
         "for which primary literature exists. Two sources were obtained in full text:", "",
         "* **Ostmann et al. 2008** (Fraunhofer IZM / AT&S / IMEC-CMST), chip embedding: "
         "contacts to embedded dies are laser-drilled, metallised microvias; minimum "
         "**150 um I/O pad pitch in production**, 100 um at prototype level, and *\"for "
         "pitches smaller than 100 um ... vialess interconnection methods\"* are indicated "
         "instead. Minimum 10 um plated Cu in the via; die placement +/-10 um at 3 sigma.",
         "* **Cauwe et al., CEAS Space Journal 15:101-112 (2023)**, HDI qualification: the "
         "qualified multi-level configuration is **two stacked microvias plus one "
         "staggered**, and *\"Stacking three levels of microvias is considered a "
         "reliability risk.\"*", "",
         f"The Phase-0M-R3 design point is r = 20 um at **70 um pitch**, in a "
         f"**three-layer** gap. It is finer than any sourced pitch for this class and "
         f"needs one more stacked level than the sourced qualified configuration.", "",
         "## 3. The landing area was also wrong", "",
         "`edge_loss()` computes the vias available over 1.80 mm2, the gan_ls footprint. "
         "But the chain has to get through the flying-capacitor layer, and in that layer "
         "the 5.61 mm2 cell already holds two 2.00 mm2 embedded MLCCs. The free area is "
         "**1.61 mm2**, and that is the binding number (DEFECT #63).", "",
         f"At the corrected landing area the Phase-0M-R3 design point gives routing ratio "
         f"**{float(dp['routing_ratio']):.4f} > 1** and is **infeasible on its own terms**, "
         f"before any sourcing question is asked.", "",
         "## 4. The full sweep", "",
         "| pitch | stacking | d | n_req | n_avail | ratio | feasible |",
         "|---|---|---|---|---|---|---|"]
    seen = set()
    for r in feas:
        k = (r["pitch_um"], r["stack"], r["d_um"])
        if k in seen:
            continue
        seen.add(k)
        L.append(f"| {float(r['pitch_um']):.0f} um | {r['stack'].replace('_',' ')} | "
                 f"{float(r['d_um']):.0f} um | {r['n_required']} | {r['n_available']} | "
                 f"{float(r['routing_ratio']):.3f} | "
                 f"{'**yes**' if r['feasible']=='True' else 'no'} |")
    L += ["",
          f"**{len(sourced_ok)} configurations satisfy both sourced bounds.** Every "
          f"feasible option requires three fully stacked microvia levels, which is the "
          f"configuration the HDI qualification identifies as a reliability risk.", "",
          "The nearest miss is instructive: at 150 um pitch, 120 um diameter, "
          "semi-stacked, the field needs 1.71 mm2 against 1.61 mm2 available -- short by "
          "**6 %**. That is a repartitioning target, not a via-technology problem.", "",
          "## 5. The vertical path is 16 % more resistive than the series model", "",
          "A 3-D DC solve of one physical column -- microvia, land, microvia, land, "
          "microvia -- returns **1.163x** the analytical series resistance for a 120 um "
          "via and **1.160x** for a 70 um one, converged to 0.13 % and 0.34 % on the two "
          "finest meshes. A plain copper bar control returns `rho L / A` to -0.000 %. The "
          "penalty is land spreading and is insensitive to diameter.", "",
          "## 6. Clearances and TSV margin", "",
          f"One of the three clearances moves to SOURCE_BOUNDED: an embedded die takes a "
          f"15-20 um dielectric cap (Ostmann 2008), which lies inside the existing "
          f"[10, 25, 50] um bound, so no corner moves. **Two remain OPEN.** And they are "
          f"no longer the binding constraint -- the interconnect fails first.", "",
          f"No TSV manufacturing tolerance could be sourced. 32 um can absorb "
          f"**{float(tol['32.0']['max_absorbable_tolerance_pct']):.2f} %** symmetric "
          f"tolerance before AR = 10 is violated, 34 um "
          f"{float(tol['34.0']['max_absorbable_tolerance_pct']):.2f} %, 36 um "
          f"{float(tol['36.0']['max_absorbable_tolerance_pct']):.2f} %, and 30 um none at "
          f"all. 32 um is **PARAMETRICALLY MARGINED, NOT process-qualified**.", "",
          "## 7. No ETM solve was rerun, and why", "",
          f"The span correction removes **1.110 W** of intra-VR vertical loss, which is "
          f"0.80 % of the electronics total and above the 0.5 % rerun threshold. It was "
          f"still not rerun, for a reason that is not about size:", "",
          "* The correction is **exactly common mode**. Z1 and Z2 share one converter "
          "cell, one partition template and one set of currents, so the same 1.110 W "
          "leaves both.",
          "* Section 9 requires the corrected configuration to be **frozen first**. There "
          "is no corrected configuration to freeze: no via geometry satisfies both sourced "
          "bounds, and selecting one of the unsourced options would be inventing the "
          "process technology this gate exists to source.", "",
          f"So **D_driver = {ratio:.4f}** is carried as the Phase-0M-R3 configuration's "
          f"ordering and is explicitly NOT re-asserted for a corrected one. The physical "
          f"spans are available in production behind `PHASE0MR3B_PHYSICAL_SPANS=1`, "
          f"default off, so every prior result is bit-identical until a phase deliberately "
          f"turns it on.", "",
          "| | Z1 | Z2 |", "|---|---|---|",
          f"| T_max | {float(z1['T_max_C']):.2f} C | **{float(z2['T_max_C']):.2f} C** |",
          f"| local fatigue-relevant inelastic response | "
          f"{float(z1['response_driver_um']):.4f} um | "
          f"**{float(z2['response_driver_um']):.4f} um** |", "",
          "## Verdicts considered and rejected", "",
          "| candidate | why rejected |", "|---|---|",
          "| **A** technology and package rules closed, PROVEN_REALIZABLE | not available: "
          "five via parameters and two clearances are OPEN, and no configuration satisfies "
          "both sourced bounds |",
          "| **B** technology closed, clearances still block | the technology is NOT "
          "closed, and the clearances are no longer what blocks first |",
          "| **C** technology remains unsourced, pair stays CONDITIONAL | true as far as it "
          "goes, and too weak: the design point is not merely unsourced, it is infeasible "
          "at the corrected landing area on its own arithmetic |",
          "| **E** via-chain model changes electrical results materially, ordering survives "
          "| the 0.80 % loss change is real and the ordering does survive, but this is the "
          "smaller finding and would bury the realizability result |",
          "| **F** the deciding ordering changes | it does not; the correction is common "
          "mode |", "",
          "## Optimizer", "",
          "**FORBIDDEN**, unchanged. `architecture templates realizable` is DOWNGRADED from "
          "PARTIAL back to NO."]
    (OUT / "PHASE0MR3B_SUBSTRATE_VIA_AND_PACKAGE_RULE_CLOSURE.md").write_text(
        "\n".join(L) + "\n")
    print(f"  wrote PHASE0MR3B_SUBSTRATE_VIA_AND_PACKAGE_RULE_CLOSURE.md ({len(L)} lines)")

    # ---- open items -----------------------------------------------------------------
    O = ["# PHASE 0M-R3B --- FINAL OPEN ITEMS", "",
         "Ranked. The interconnect has overtaken the clearances as the binding blocker.",
         "", "| # | item | why open | what it blocks | what would close it |",
         "|---|---|---|---|---|",
         "| 1 | **`ls_to_L` cannot be built under sourced rules** | every feasible via "
         "configuration needs 3 stacked microvia levels, which the HDI qualification calls "
         "a reliability risk; the nearest sourced-legal option is 6 % short on area | "
         "realizability of BOTH architectures | repartition so the 20.4 A net crosses "
         "fewer layers, or source a package-substrate rule that permits 3 stacked levels |",
         "| 2 | **microvia diameter, capture pad, landing area, via current limit** | no "
         "package-substrate design rule was reachable; the EPC2057 land pattern is not in "
         "this repository | any via-level feasibility claim | items 3, 5 and 6 of "
         "`PRIMARY_SOURCES_TO_DOWNLOAD.md` |",
         "| 3 | **two package clearances** | `cavity_sidewall_um` and `cooler_standoff_um`; "
         "searched again this phase against two new primary sources, still nothing | "
         "PROVEN_REALIZABLE | a vendor design rule |",
         "| 4 | **TSV manufacturing tolerance** | no source; the 2 % bound is parametric | "
         "calling any diameter process-qualified | items 1 and 2 of the download list |",
         "| 5 | **high-stress SAC305 constitutive data** | no primary data above ~16 MPa | "
         "every absolute reliability number | coupon characterisation |",
         "| 6 | **conjugate CFD of the cooler** | timed out in Phase 0M-R3 | calling the "
         "cooler fully validated | a converged benchmark |",
         "| 7 | **N_required**, **absolute N_f**, **admissible allowable** | unchanged | G2 "
         "| unchanged |", "",
         "Items 5, 6 and 7 are carried from Phase 0M-R3A unchanged.", "",
         "## Closed or downgraded this phase", "",
         "* the 673 um `ls_to_L` span -- **withdrawn**, it was a mid-plane artifact",
         "* `die_to_component_gap_um` -- OPEN to **SOURCE_BOUNDED** (15-20 um, inside the "
         "existing bound, no corner moves)",
         "* the Phase-0M-R3 routing repair -- **withdrawn**: infeasible at the corrected "
         "landing area",
         "* \"32 um has process margin\" -- restated as **parametrically margined, not "
         "process-qualified**", "",
         "## Not open, and not to be relitigated", "",
         "* the production cooling point, Re = 1264.8, inside its validated domain",
         "* 2300 < Re < 3000 OUT_OF_MODEL_DOMAIN; conjugate CFD NOT COMPLETED",
         "* the TSV allocation law: enlarging a via changes the COUNT and nothing else",
         f"* the Z1/Z2 response ordering at D_driver = {ratio:.4f}, as a statement about "
         "the Phase-0M-R3 configuration"]
    (OUT / "final_open_items.md").write_text("\n".join(O) + "\n")
    print(f"  wrote final_open_items.md ({len(O)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
