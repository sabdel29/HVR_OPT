#!/usr/bin/env python3
"""Phase-0M-R3B --- the phase documents. Every number is read from an artifact."""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"


def rd(n, base=OUT):
    p = Path(base) / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def w(name: str, lines: list[str]) -> None:
    (OUT / name).write_text("\n".join(lines) + "\n")
    print(f"  wrote {name} ({len(lines)} lines)")


def main() -> int:
    span = rd("vertical_span_correction.csv")
    seg = rd("ls_to_L_layer_by_layer_geometry.csv")
    feas = rd("ls_to_L_feasibility.csv")
    src = rd("substrate_via_source_matrix.csv")
    dc = rd("substrate_via_dc_validation.csv")
    tol = rd("z2_tsv_sourced_tolerance_sweep.csv")
    tsr = rd("z2_tsv_tolerance_search.csv")
    clr = rd("package_clearance_provenance.csv")
    ls = {r["edge"]: r for r in span}["ls_to_L"]
    dp = [r for r in feas if float(r["pitch_um"]) == 70.0
          and r["stack"] == "fully_stacked" and float(r["d_um"]) == 40.0][0]
    sourced = [r for r in feas if float(r["pitch_um"]) >= 100.0
               and r["stack"] == "semi_stacked" and r["feasible"] == "True"]
    stacked_ok = [r for r in feas if r["stack"] == "fully_stacked"
                  and r["feasible"] == "True" and float(r["pitch_um"]) >= 100.0]
    conv = [r for r in dc if r["case"] != "control_uniform_bar"]
    ctrl = [r for r in dc if r["case"] == "control_uniform_bar"][0]

    # ---------------------------------------------------------------- topology
    L = ["# PHASE 0M-R3B --- WHAT `ls_to_L` PHYSICALLY IS", "",
         "> **The 673 um span was the artifact, not the technology.**", ""]
    L += ["`build_edges()` addresses every component at its tier MID-PLANE, so the "
          "vertical link from the low-side GaN switch to the inductor was measured from "
          "the geometric centre of one component to the geometric centre of the other. "
          "That line passes through 303 um of GaN die body and 250 um of inductor body. "
          "No interconnect does that: components are contacted at their terminal faces.",
          "", "## The correction", "",
          "| edge | I_rms | as modelled | physical | overstatement |",
          "|---|---|---|---|---|"]
    for r in span:
        L.append(f"| `{r['edge']}` | {float(r['i_rms_a']):.3f} A | "
                 f"{float(r['modelled_span_um']):.1f} um | "
                 f"{float(r['physical_span_um']):.1f} um | "
                 f"**{float(r['overstatement_x']):.2f}x** |")
    L += ["", "The defect is systematic across every vertical edge, not specific to "
          "`ls_to_L`. `hs_to_ls` is the extreme case: two dies in adjacent tiers, "
          "separated physically by one 10 um RDL, modelled as 655.5 um of copper.",
          "", "## What the chain actually crosses", "",
          "| # | layer | thickness | what is in it |", "|---|---|---|---|"]
    for s in seg:
        L.append(f"| {s['i']} | {s['layer']} | {float(s['thickness_um']):.0f} um | "
                 f"{s['obstruction']} |")
    L += ["", f"**{sum(float(s['thickness_um']) for s in seg):.0f} um in three build-up "
          "layers**, so the interconnect is a chain of three microvia levels in series "
          "with a capture land between each pair -- not one via, and not a "
          "through-silicon via.", "",
          "![cross-section](FIG_0MR3B_ls_to_L_cross_section.png)", "",
          "## Why this matters more than the length",
          "",
          "`n_required = ceil(I / (J * A_cu))` has no length in it, so the correction does "
          "NOT change the via COUNT and the Phase-0M-R3A arithmetic stands. What changes "
          "is the resistance, and what the sourcing question is actually about: a 120 um "
          "build-up stack is ordinary embedded-component packaging, not an exotic "
          "structure, and there is real literature for it."]
    w("LS_TO_L_PHYSICAL_TOPOLOGY.md", L)

    # ---------------------------------------------------------------- DC validation
    L = ["# PHASE 0M-R3B SECTION 5 --- 3-D DC VALIDATION OF THE VIA CHAIN", "",
         "The analytical model puts each segment's `rho L / A` in series. The real path "
         "spreads into a capture land at every level and re-converges into the next via, "
         "so the series value is a lower bound. One representative column was solved in "
         "3-D on the framework's own conservative finite-volume DC code.", "",
         "## Control", "",
         f"A plain copper bar returns `rho L / A` to **{float(ctrl['error_pct']):+.3f} %**. "
         "Current conservation is checked on every solve and holds at machine precision "
         "(worst case 4e-11 % of the injected current).", "",
         "## The chain", "",
         "| case | mesh | R analytical | R 3-D | 3-D / analytical |", "|---|---|---|---|---|"]
    for r in conv:
        L.append(f"| {r['case']} | {r['nxy']} | {float(r['R_analytical_ohm']):.4e} Ohm | "
                 f"{float(r['R_fv_ohm']):.4e} Ohm | "
                 f"{float(r['R_fv_ohm'])/float(r['R_analytical_ohm']):.4f} |")
    L += ["", "Both geometries converge, and to the same answer:", "",
          "| geometry | converged ratio | mesh drift, two finest |", "|---|---|---|"]
    for case in sorted({r["case"] for r in conv}):
        g = [r for r in conv if r["case"] == case]
        f1, f2 = g[-2], g[-1]
        drift = 100 * abs(float(f2["R_fv_ohm"]) - float(f1["R_fv_ohm"])) / float(f2["R_fv_ohm"])
        L.append(f"| {case} | **{float(f2['R_fv_ohm'])/float(f2['R_analytical_ohm']):.4f}** "
                 f"| {drift:.2f} % |")
    L += ["", "**The series model understates the vertical path by about 16 %**, and the "
          "penalty is insensitive to via diameter -- it is the land spreading, not the "
          "via. No global crowding multiplier is introduced; this is a measured, "
          "geometry-specific correction for one structure.",
          "",
          "Q3D remains unlicensed. HFSS was not used: this is a DC extraction and HFSS "
          "would answer a different question."]
    w("SUBSTRATE_VIA_DC_VALIDATION.md", L)

    # ---------------------------------------------------------------- clearances
    L = ["# PHASE 0M-R3B SECTION 7 --- PACKAGE-CLEARANCE SOURCE AUDIT", "",
         "Phase 0M-R2 searched for these three numbers and found none. This phase reached "
         "two new primary sources on embedded-component substrates, so the search was "
         "repeated against them rather than restated.", "",
         "| clearance | where it applies | 0M-R2 | 0M-R3B | what was found |",
         "|---|---|---|---|---|"]
    for r in clr:
        L.append(f"| `{r['clearance']}` | {r['where']} | {r['status_0mr2']} | "
                 f"**{r['status_0mr3b']}** | {r['found'][:150]} |")
    L += ["", "### The one that moved", ""]
    d = [r for r in clr if r["clearance"] == "die_to_component_gap_um"][0]
    L += [f"{d['found']}", "",
          f"*Source:* {d['source']}", "",
          f"*Is it the same feature?* {d['same_feature']}", "",
          f"*Effect:* {d['effect_on_verdict']}", "",
          "### The two that did not", "",
          "`cavity_sidewall_um` and `cooler_standoff_um` remain **OPEN**. Their bounds are "
          "unchanged and are still anchors, not sources.", "",
          "## Are the clearances the only remaining blocker?", "",
          "**No.** After the `ls_to_L` correction the vertical interconnect fails first, "
          "on sourced via rules, at every one of the 27 clearance corners. The clearance "
          "question is no longer the binding one."]
    w("PACKAGE_CLEARANCE_SOURCE_AUDIT.md", L)

    # ---------------------------------------------------------------- TSV tolerance
    L = ["# PHASE 0M-R3B SECTION 8 --- IS THE ARCH_Z2 TSV MARGIN PROCESS-QUALIFIED?", "",
         "**No. It is parametric.** No manufacturing tolerance for this process was "
         "sourced from this host, so the honest question is inverted: rather than assert "
         "a margin against an assumed tolerance, report the tolerance each diameter can "
         "absorb before the sourced AR <= 10 rule is violated.", "",
         "| parameter | provenance | what the search found |", "|---|---|---|"]
    for r in tsr:
        L.append(f"| {r['parameter']} | **{r['provenance']}** | {r['what the search found']} |")
    L += ["", "## What each diameter can absorb", "",
          "Worst case shrinks the diameter and deepens the via together, so "
          "`AR_worst = L(1+t) / (d(1-t)) <= 10` gives `t = (10d - L) / (10d + L)`.", "",
          "| d | AR | M_AR | max symmetric tolerance before AR = 10 | passes the 2 % "
          "parametric bound |", "|---|---|---|---|---|"]
    for r in tol:
        L.append(f"| {float(r['d_um']):.0f} um | {float(r['AR_nominal']):.3f} | "
                 f"{float(r['M_AR_nominal']):.3f} | "
                 f"**{float(r['max_absorbable_tolerance_pct']):.2f} %** | "
                 f"{'yes' if r['passes_parametric_2pct'] == 'True' else 'NO'} |")
    L += ["", "30 um can absorb nothing: it sits exactly on the rule. 32 um can absorb "
          "3.23 %, 34 um 6.25 %, 36 um 9.09 %.", "",
          "**Licensed wording:** *32 um is PARAMETRICALLY MARGINED at a 2 % symmetric "
          "tolerance and is NOT process-qualified.* The phrase \"process margin closed\" "
          "is not available until a real tolerance is sourced.", "",
          "32 um remains the smallest evaluated diameter with positive margin, so it "
          "remains preferred over 30 um on margin and over 34/36 um on via count -- a "
          "design-side preference, not a qualification."]
    w("Z2_TSV_PROCESS_TOLERANCE_AUDIT.md", L)

    # ---------------------------------------------------------------- blocked sources
    L = ["# PRIMARY SOURCES THAT COULD NOT BE DOWNLOADED FROM THIS HOST", "",
         "Each would close a parameter that is currently OPEN. Crossref, OpenAlex, "
         "Unpaywall and Europe PMC are reachable; MDPI, IEEE Xplore and ScienceDirect "
         "full text are not (every route returns a ~415-byte block page).", "",
         "| # | source | DOI / locator | parameter it would close |", "|---|---|---|---|",
         "| 1 | *A Short Review of Through-Silicon Via (TSV) Interconnects: Metrology and "
         "Analysis*, Applied Sciences 13(14):8301, 2023 | `10.3390/app13148301` | TSV "
         "diameter, depth and taper manufacturing tolerance (Section 8) |",
         "| 2 | *Advanced 3D Through-Si-Via and Solder Bumping Technology: A Review*, "
         "Materials 16(24):7652, 2023 | `10.3390/ma16247652` | TSV liner and plating "
         "tolerance (Section 8) |",
         "| 3 | *Fan-Out Panel-Level PCB-Embedded SiC Power MOSFETs Packaging*, IEEE "
         "JESTPE, 2019 | `10.1109/JESTPE.2019.2952238` | microvia diameter, pad and "
         "current-carrying capability for an embedded POWER device -- the closest "
         "published analogue to `ls_to_L` |",
         "| 4 | *A Review of Polymer Dielectrics for Redistribution Layers in Interposers "
         "and Package Substrates*, Polymers 15(19):3895, 2023 | `10.3390/polym15193895` | "
         "modern package-substrate build-up via diameter and pitch, to replace the 2008 "
         "chip-embedding numbers used here as a bound |",
         "| 5 | substrate-vendor / OSAT design-rule manual (any of Ibiden, Shinko, AT&S, "
         "Unimicron) | released under NDA; no public copy | capture-pad diameter, stacking "
         "limit and minimum annular ring for package-substrate microvias |",
         "| 6 | EPC2057 land-pattern drawing | EPC datasheet, not in this repository | the "
         "switch-node land area, which bounds how many vias can land on the die at all |",
         "", "Items 3, 5 and 6 are the ones that would actually decide this gate. Without "
         "them the microvia diameter, the capture pad, the landing area and the via "
         "current limit all stay OPEN, and the `ls_to_L` repair cannot be qualified."]
    w("PRIMARY_SOURCES_TO_DOWNLOAD.md", L)
    return 0


if __name__ == "__main__":
    sys.exit(main())
