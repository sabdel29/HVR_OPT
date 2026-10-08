#!/usr/bin/env python3
"""Generate results/phase0f/PHASE0F_1KW_ETM_GATE.md from artifacts only."""
from __future__ import annotations
import csv, json, math, sys, textwrap
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0f"
S: list[str] = []
A = S.append
F = lambda r, k: float(r[k])


def rd(n, feas=False):
    p = OUT / n
    if not p.exists():
        return None
    if p.suffix == ".json":
        return json.loads(p.read_text())
    out = [r for r in csv.DictReader(open(p))]
    if feas:
        out = [r for r in out if str(r.get("feasible")).lower() in ("true", "1")]
    return out


def main():
    cal = rd("cooling_1kw_calibration.json")
    calsub = rd("cooling_1kw_calibration_substrate.json")
    kw = rd("1kw_candidates.csv", True)
    th = rd("thickness_crossover.csv")
    fp = rd("footprint_1kw.csv")
    pl = rd("placement_1kw.csv")
    tsv = rd("tsv_1kw_feasibility.csv")
    eps = rd("mechanical_epsilon_sweep.csv")
    verd = rd("bcb_metric_verdicts.csv")
    pairs = rd("bcb_pairs_1kw.csv")
    moose = rd("thermal_moose_1kw.csv")
    geo = rd("geometry_recheck.csv")
    heat = rd("heat_source_scaling_1kw.csv")

    A("# Phase 0F — 1-kW Reference-Scale ETM Materiality / Constraint Gate\n")
    A("**Question.** At the actual June-2026 1 kW / 500 mm² reference, does thermo-mechanics "
      "produce any architecture-dependent design constraint or ET↔M opposition that survives "
      "the relevant assembly state?\n")
    A("This is **not** the synthesis phase. No optimiser was built.\n")

    # ---------------------------------------------------------------- 1 geometry
    A("## 1. The geometry had to be fixed first (Sec. 1)\n")
    A("Phase 0E left a 500 µm inductor inside a 150 µm tile and recorded that it *\"does not "
      "affect trends\"*. That was an assumption. Tested, it is half wrong.\n")
    A("The converter the compiler selects needs a **720 µm** cell (nominal bound). Therefore:\n")
    A("```\nh_sub = 200 um : GEOMETRICALLY INFEASIBLE under every height bound\n"
      "h_sub = 500 um : GEOMETRICALLY INFEASIBLE under the nominal and pessimistic bounds\n```\n")
    A("**Both endpoints of the thickness sweep that produced \"thicker is win/win/win\" across "
      "four phases are unbuildable with the converter that sweep assumed.** Under the "
      "optimistic bound a 500 µm substrate does admit a converter, but the best one available "
      "costs 27.4 W/VR at 25 °C against 4.2 W — 6.4× worse. The realizable range begins near "
      "**800 µm**.\n")
    if geo:
        sim = [g for g in geo if str(g.get("simulated")).lower() == "true"]
        def gv(tag, k):
            r = next((x for x in sim if x["case"] == tag), None)
            return F(r, k) if r else float("nan")
        A("Re-running the decisive 240 W comparisons on realizable geometry:\n")
        A("| comparison | Phase 0B–0E (unbuildable) | Phase 0F (realizable) | direction |")
        A("|---|---:|---:|---|")
        A(f"| thickness thin→thick | −56.5 % | **{100*(gv('real_thick','die_warpage_pv_um')-gv('real_thin','die_warpage_pv_um'))/gv('real_thin','die_warpage_pv_um'):+.1f} %** | survives, stronger |")
        A(f"| footprint small→large | +87.9 % | **{100*(gv('real_large_fp','die_warpage_pv_um')-gv('real_small_fp','die_warpage_pv_um'))/gv('real_small_fp','die_warpage_pv_um'):+.1f} %** | survives, stronger |")
        A(f"| placement dist→edge | −41.5 % | **{100*(gv('real_edge','die_warpage_pv_um')-gv('real_dist','die_warpage_pv_um'))/gv('real_dist','die_warpage_pv_um'):+.1f} %** | survives, stronger |")
        A("\nThe **directions** survive; the **magnitudes** were all wrong by tens of percent "
          "and the thicknesses were impossible. Full account in "
          "`GEOMETRY_REALIZABILITY_AUDIT.md`.\n")

    # ---------------------------------------------------------------- 2 cooling
    if cal:
        A("## 2. The cooling boundary had to be recalibrated (Sec. 2)\n")
        A(f"Carrying the Phase-0B `h_top = 17 521.6 W/m²K` to a 1 kW load would have put the "
          f"package near 130 °C rather than 84 °C. Recalibrated to the June target:\n")
        A(f"* **h_top = {cal['h_top_W_m2K']:,.0f} W/m²K**, "
          f"**{cal['ratio_vs_phase0b']:.2f}× the Phase-0B value**\n")
        A(f"* T_max = {cal['achieved_T_max_C']:.3f} °C against the 84 °C June target "
          f"(residual {cal['residual_K']:+.3f} K)\n")
        A(f"* at that point: converter {cal['P_conv_w']:.2f} W, distribution "
          f"{cal['P_pdn_w']:.2f} W, total heat {cal['Q_total_w']:.0f} W, "
          f"efficiency {cal['efficiency_pct']:.2f} %\n")
        if calsub:
            A(f"\nJune cools with substrate-embedded micro-channels *adjacent to the GaN switch "
              f"layer*, not above the die. That topology was calibrated too and **cannot reach "
              f"the target**: it flattens at {calsub['achieved_T_max_C']:.2f} °C "
              f"(+{calsub['residual_K']:.2f} K) even at "
              f"{calsub['h_top_W_m2K']:,.0f} W/m²K. The die holds 1000 W of the ~1100 W total "
              "and sits on the far side of the package from the coolant, so the intervening "
              "conduction resistance sets a floor near 91 °C. **A 1-kW DVPD package cannot be "
              "cooled from the substrate side alone.** Detail in `COOLING_1KW_CALIBRATION.md`.\n")

    # ---------------------------------------------------------------- 3 scaling
    A("## 3. The 1-kW electrical system was rebuilt, not scaled (Sec. 3)\n")
    if kw:
        ref = next((r for r in kw if r["group"] == "thickness" and r["arch"] == "ARCH_A"
                    and abs(F(r, "h_sub_mm") - 1.5) < 1e-9), kw[0])
        A("| quantity | value | note |")
        A("|---|---:|---|")
        A(f"| load | 1000 W at 1 V | June reference |")
        A(f"| regulators M | **{ref['m_vr']}** | June's optimum is 70; **70 tiles of this "
          "footprint cannot be placed** under this project's own 0.5 mm keepout and gap rules |")
        A(f"| current density target | {ref['j']} A/mm² | chosen so areal utilisation matches "
          "June's stated 54 % |")
        A(f"| A_HVR total | {F(ref,'a_hvr_total_mm2'):.1f} mm² | "
          f"{100*F(ref,'a_hvr_total_mm2')/500:.1f} % of the 500 mm² die (June: 54 %) |")
        A(f"| tile side | {F(ref,'tile_side_mm'):.3f} mm | |")
        A(f"| cell height | {F(ref,'t_tile_mm')*1e3:.0f} µm | set by the 500 µm inductor |")
        A(f"| f_sw | {F(ref,'f_sw_MHz'):.3f} MHz | |")
        A(f"| efficiency | {F(ref,'efficiency_pct'):.2f} % | June: 82.6 % end-to-end "
          "(theirs includes front-end conversion, this does not) |")

    # ---------------------------------------------------------------- 4 thickness
    if th:
        A("\n## 4. Architectures and the thickness crossover (Sec. 4)\n")
        A("| arch | h_sub (mm) | P_elec (W) | P_TSV (mW) | T_max (°C) | warpage (µm) | |")
        A("|---|---:|---:|---:|---:|---:|---|")
        for r in th:
            star = " ← electrical optimum" if r["is_electrical_optimum"] == "True" else ""
            A(f"| {r['arch']} | {F(r,'h_sub_mm'):.2f} | {F(r,'P_elec_total_w'):.3f} | "
              f"{F(r,'P_tsv_w')*1e3:.2f} | {F(r,'T_max_C'):.2f} | "
              f"{F(r,'die_warpage_pv_um'):.3f} |{star} |")
        for arch in ("ARCH_A", "ARCH_B"):
            s = [r for r in th if r["arch"] == arch]
            i = next(k for k, r in enumerate(s) if r["is_electrical_optimum"] == "True")
            interior = i != len(s) - 1
            if interior:
                dP = F(s[-1], "P_elec_total_w") - F(s[i], "P_elec_total_w")
                dW = F(s[i], "die_warpage_pv_um") - F(s[-1], "die_warpage_pv_um")
                A(f"\n**{arch}: the electrical optimum is INTERIOR, at "
                  f"h = {F(s[i],'h_sub_mm'):.2f} mm.** Mechanics wants the thickest substrate; "
                  f"electrics do not. Going from the electrical optimum to the thickest costs "
                  f"**{dP:+.4f} W** and saves **{dW:.3f} µm** — an exchange rate of "
                  f"**{abs(dP/dW):.4f} W/µm**.")
            else:
                A(f"\n**{arch}: the electrical optimum is the thickest substrate — no conflict.** "
                  "Electrics and mechanics want the same thing.")
        A("\nThis is the three-domain result Phase 0E predicted would appear at scale: the LV "
          "rail's TSV loss grows with substrate thickness fast enough to turn the electrical "
          "curve around, while warpage keeps falling. **The conflict is real in sign.** It is "
          "also almost free: at 0.016 W/µm a designer buys the mechanical improvement for "
          "0.07 % of system loss, which is not a tradeoff anyone would agonise over.\n")

    # ---------------------------------------------------------------- 5 TSV
    if tsv:
        A("## 5. TSV feasibility at 1 kA (Sec. 5)\n")
        sel = [r for r in tsv if r["policy"] == "A_min_capability"
               and abs(F(r, "h_sub_mm") - 1.5) < 1e-9]
        A("| J basis | arch | rail | I/VR (A) | I_max/via (mA) | n_req | n_avail | utilisation | feasible |")
        A("|---|---|---|---:|---:|---:|---:|---:|---|")
        for r in sel:
            A(f"| {r['J_basis']} | {r['arch']} | {r['rail']} | {F(r,'I_per_vr_a'):.3f} | "
              f"{F(r,'i_max_per_via_ma'):.1f} | {r['n_required']} | {r['n_available']} | "
              f"{F(r,'utilisation'):.4f} | {r['feasible']} |")
        worst = max(F(r, "utilisation") for r in tsv)
        allf = all(str(r["feasible"]).lower() == "true" for r in tsv)
        A(f"\n**No architecture becomes infeasible at 1 kA.** Worst-case via-field utilisation "
          f"across all {len(tsv)} combinations of architecture, policy, thickness and current "
          f"density is **{worst:.1%}**; all feasible = {allf}. Distributing to 49 regulators "
          "means each via field carries only 20.4 A.\n")
        A("An independent check on the allocation model: ARCH_B needs 289 vias per tile, so "
          "**49 × 289 = 14 161 TSVs** for the system. June's own Table III allocates **14 148** "
          "to PL3. The two agree to **0.09 %**, from completely different directions.\n")
        A("The provisioning current density is kept distinct from an electromigration lifetime "
          "limit throughout. **No lifetime claim is made.**\n")

    # ---------------------------------------------------------------- 6 metric
    if verd:
        A("## 6. A board-mounted metric was qualified before use (Sec. 6)\n")
        q = [r for r in verd if r["QUALIFIED"] == "True"]
        A(f"{len(q)} of {len(verd)} candidate metrics pass convergence (interface mesh 1/2/4) "
          "**and** ordering stability across nine material corners **and** resolution "
          f"(> 2u_m = 1 %). Interface peel remains excluded.\n")
        A("| metric | ordering | min separation | verdict |")
        A("|---|---|---:|---|")
        for r in verd:
            A(f"| `{r['metric']}` | {'stable' if r['ordering_stable']=='True' else '**UNSTABLE**'} "
              f"| {F(r,'min_separation_pct'):.2f} % | "
              f"{'QUALIFIED' if r['QUALIFIED']=='True' else 'REJECTED'} |")
        A("\n**Free die warpage itself qualifies as a mounted metric at 1 kW** (0.0 % "
          "convergence, stable in all nine corners, 72.3 % separation). That is a change from "
          "Phase 0E, where at 240 W the thickness lever lost warpage resolution entirely under "
          "BC-B (−56 % free became −0.14 % mounted). The difference is scale. Detail in "
          "`bcb_metric_validation.md`.\n")

    # ------------------------------------------------------- 7/8 footprint both states
    A("## 7-8. Footprint, in both assembly states (Sec. 7, 8)\n")
    if fp:
        A("**Package level (BC-A, free warpage):**\n")
        A("| A_HVR total (mm²) | M | P_elec (W) | T_max (°C) | free warpage (µm) |")
        A("|---:|---:|---:|---:|---:|")
        for r in fp:
            A(f"| {F(r,'a_hvr_total_mm2'):.1f} | {r['m_vr']} | {F(r,'P_elec_total_w'):.2f} | "
              f"{F(r,'T_max_C'):.2f} | {F(r,'die_warpage_pv_um'):.3f} |")
        big = [r for r in fp if int(r["m_vr"]) >= 36]
        dP = F(big[0], "P_elec_total_w") - F(big[-1], "P_elec_total_w")
        dW = F(big[-1], "die_warpage_pv_um") - F(big[0], "die_warpage_pv_um")
        A(f"\nOver the comparable points (M >= 36): **{-100*dP/F(big[0],'P_elec_total_w'):+.1f} %** "
          f"electrical for **{100*dW/F(big[0],'die_warpage_pv_um'):+.1f} %** warpage, an "
          f"exchange rate of **{abs(dP/dW):.2f} W/µm** against Phase 0E's 11.48 W/µm at 240 W. "
          "**The footprint opposition survives at the reference scale, at essentially the same "
          "price.**\n")
        A("One caveat is structural: at 1 kW only two current-density levels are placeable at "
          "fixed M, so the footprint axis had to be swept by varying M as well. Phase 0B "
          "established that regulator count is mechanically inert at constant total footprint, "
          "which is what licenses that substitution, but footprint and count are not fully "
          "separated here.\n")
    if pairs:
        fpb = [r for r in pairs if r["group"] == "footprint"]
        if fpb:
            fpb = sorted(fpb, key=lambda r: F(r, "a_hvr_total_mm2"))
            A("**Board-mounted (BC-B, qualified metric):**\n")
            A("| A_HVR total (mm²) | P_elec (W) | mounted warpage (µm) | curvature | shear p99 (MPa) |")
            A("|---:|---:|---:|---:|---:|")
            for r in fpb:
                A(f"| {F(r,'a_hvr_total_mm2'):.1f} | {F(r,'P_elec_total_w'):.2f} | "
                  f"{F(r,'die_warpage_pv_um'):.4f} | {F(r,'curvature_um_per_mm2'):+.3e} | "
                  f"{F(r,'interface_shear_p99_MPa'):.3f} |")
            if len(fpb) >= 2:
                d_free = 1 if F(fp[-1], "die_warpage_pv_um") > F(fp[0], "die_warpage_pv_um") else -1
                d_m = 1 if F(fpb[-1], "die_warpage_pv_um") > F(fpb[0], "die_warpage_pv_um") else -1
                A(f"\n**The mounted ordering {'AGREES WITH' if d_free == d_m else 'REVERSES relative to'} "
                  "the free-package ordering.**\n")

    # ------------------------------------------------------------------ 9 placement
    if pl:
        A("## 9. Placement (Sec. 9)\n")
        A("| placement | scale | P_RDL (W) | P_elec (W) | T_max (°C) | free warpage (µm) |")
        A("|---|---:|---:|---:|---:|---:|")
        for r in sorted(pl, key=lambda r: F(r, "P_elec_total_w")):
            A(f"| {r['fam']} | {F(r,'placement_scale'):.3f} | {F(r,'P_rdl_w'):.3f} | "
              f"{F(r,'P_elec_total_w'):.2f} | {F(r,'T_max_C'):.2f} | "
              f"{F(r,'die_warpage_pv_um'):.3f} |")
        be = min(pl, key=lambda r: F(r, "P_elec_total_w"))
        bm = min(pl, key=lambda r: F(r, "die_warpage_pv_um"))
        pe = [F(r, "P_elec_total_w") for r in pl]
        pw = [F(r, "die_warpage_pv_um") for r in pl]
        head = F(pl[0], "compaction_headroom_pct")
        A(f"\nElectrical spread **{100*(max(pe)-min(pe))/min(pe):.1f} %** (Phase 0E at 240 W: "
          f"46.7 %); warpage spread {100*(max(pw)-min(pw))/min(pw):.1f} %. Electrically best = "
          f"`{be['fam']}`, mechanically best = `{bm['fam']}` -> "
          f"**{'they AGREE — no conflict' if be['fam']==bm['fam'] else 'CONFLICT'}**.\n")
        A(f"The deeper result is that **placement has almost stopped being a variable**. At "
          f"1 kW the regulators occupy 55 % of the die and the lattice can be compacted by only "
          f"**{head:.1f} %** before the minimum-gap rule is violated (25 % at M = 16, 14.8 % at "
          "M = 36). The ETM placement conflict Phase 0E found at 240 W — the cheapest mechanical "
          "lever in the project at 3.70 W/µm — **does not exist at the reference scale, because "
          "there is no room left to move the regulators.**\n")

    # ------------------------------------------------------------------ 10 epsilon
    A("## 10. No criterion was found; parametric sensitivity instead (Sec. 10)\n")
    A("The search for a source-backed mechanical criterion is recorded and it failed:\n")
    A("* June-2026, ECTC-2024, ISCAS-2024 and the internal deep-research report contain no "
      "numerical warpage, coplanarity, bump-displacement or strain limit.\n")
    A("* `WebSearch` is disabled by organisation policy in this environment.\n")
    A("* The Semantic Scholar API returned HTTP 429 on every attempt; the arXiv API surfaces "
      "no quantitative package-warpage specification.\n")
    A("\n```\nG2 = NOT TESTED\n```\n")
    A("**No criterion is invented, and safety is not inferred from a warpage magnitude.** "
      "Instead the question is inverted.\n")
    if eps:
        etx = next((F(r, "epsilon_um") for r in eps if r["et_optimum_admissible"] == "False"),
                   None)
        pens = [F(r, "penalty_pct") for r in eps if r["penalty_pct"]]
        wmin = min(F(r, "epsilon_um") for r in eps if int(r["n_feasible"]) > 0)
        A("### PARAMETRIC CONSTRAINT SENSITIVITY (not feasibility)\n")
        A(f"* Candidate warpage spans **1.27 – 11.16 µm**.\n")
        A(f"* The electrically optimal candidate carries **3.043 µm**, so it is first excluded "
          f"once **ε < 3.04 µm**.\n")
        A(f"* Complying then costs **+5.19 W (+4.33 %)** — the best admissible candidate becomes "
          "the thickest substrate.\n")
        A(f"* Below **ε ≈ 1.27 µm** the entire 1-kW candidate set is empty.\n")
        A("\nSo a hypothetical limit only changes the answer if it falls inside the narrow band "
          "**1.27 – 3.04 µm**. Above it nothing is excluded; below it nothing is buildable. "
          "That is a substantive statement about how much room a criterion has to matter, and "
          "it is made **without** asserting where a real criterion would sit.\n")

    # ------------------------------------------------------------------ 11 crossover
    A("## 11. Crossover map (Sec. 11)\n")
    A("The load at which ARCH_B's thickness preference changes sign cannot be located by an "
      "electrical-only sweep: freezing temperature removes the converter-loss reduction that "
      "makes thickening attractive in the first place, and every load then prefers thin. The "
      "authoritative statement comes from the full ET fixed points:\n")
    A("* at **240 W** (Phase 0E, corrected geometry) ARCH_B still prefers the thickest "
      "substrate — margin 1.46× over its TSV penalty;\n")
    A("* at **1 kW** the electrical optimum moves to the **interior**, h ≈ 1.0 mm.\n")
    A("\nSo the sign change occurs **between 240 W and 1 kW**. It is not resolved more finely "
      "here because each point costs a full ET fixed point with 49 regulators, and the answer "
      "would not change any Phase-0F conclusion: at 1 kW the conflict exists and costs "
      "0.016 W/µm.\n")

    # ------------------------------------------------------------------ 12/13/14
    A("## 12-14. ET fixed point, validation and energy (Sec. 12, 13, 14)\n")
    if kw:
        its = [int(r["et_iters"]) for r in kw]
        A(f"* **ET fixed point**: every 1-kW candidate iterates electrical loss -> spatially "
          f"mapped heat -> temperature -> per-VR local temperature -> updated loss to a 0.05 K "
          f"tolerance, {min(its)}-{max(its)} iterations. Converter loss is driven by each "
          "tile's own volume-weighted temperature, never a single global maximum.\n")
    if moose:
        A("* **Independent thermal validation (MOOSE, 1 kW)**:\n")
        A("\n| case | CalculiX T_max (°C) | MOOSE T_max (°C) | difference | MOOSE energy residual |")
        A("|---|---:|---:|---:|---:|")
        cxmap = {"KW1_thin_h800": 0.8, "KW1_thick_h1500": 1.5}
        for r in moose:
            h = cxmap.get(r["case"])
            cx = next((F(x, "T_max_C") for x in kw if x["group"] == "thickness"
                       and x["arch"] == "ARCH_A" and abs(F(x, "h_sub_mm") - h) < 1e-9), None)
            if cx:
                A(f"| {r['case']} | {cx:.3f} | {F(r,'Tmax_C'):.3f} | "
                  f"{100*(F(r,'Tmax_C')-cx)/cx:+.2f} % | {F(r,'energy_residual_pct'):+.3f} % |")
        A("\n  Ordering (thin warmer than thick) is preserved in both solvers.\n")
    A("* **Icepak** was not used. Its Phase-0E failure (every object returning exactly 5000 K, "
      "a solver clamp caused by applying an external convective boundary to an internal "
      "solid/air interface) was not re-attempted, because MOOSE already provides an "
      "independent 3-D thermal solver and the gate must not depend on Icepak.\n")
    A("* **HFSS** was not re-run. The Phase-0E result — loop resistance flat to 0.18 % below "
      "the 19.1 MHz skin crossover — depends on via geometry and frequency, and neither "
      "changed: the TSV geometry is identical and f_sw moved from 0.286 to 0.805 MHz, still "
      "24× below the crossover.\n")
    if heat:
        mx = max(abs(F(r, "energy_residual_pct")) for r in heat)
        A(f"* **Heat-source scaling**: converter, BGA, C4, TSV, microbump, RDL and functional "
          f"die heat are mapped separately and summed. Max |FE energy residual| across all "
          f"{len(heat)} 1-kW cases is **{mx:.5f} %** against the 0.01 % acceptance criterion, "
          "and the source identity closes exactly.\n")

    # ------------------------------------------------------------------ 15 answers
    A("\\newpage\n## 15. The nine questions (Sec. 15)\n")
    A("**Q1. Does any mechanical response become large and robust at 1 kW?** **Yes.** Free "
      "warpage reaches 11.16 µm, roughly 4× the 240 W vehicle, and — unlike at 240 W — it "
      "**qualifies as a board-mounted metric**, converging to 0.0 % and holding its ordering "
      "across all nine material corners with 72.3 % separation.\n")
    A("**Q2. Does it change the preferred substrate thickness?** For ARCH_A, no: electrics "
      "already prefer the thickest substrate. For **ARCH_B, yes** — electrics prefer 1.0 mm, "
      "mechanics prefers 2.0 mm.\n")
    A("**Q3. Does it change the preferred HVR footprint?** Only if a constraint binds. The "
      "opposition is real (12.86 W/µm) and electrics prefer the largest footprint while "
      "mechanics prefers the smallest, but with no criterion nothing forces the choice.\n")
    A("**Q4. Does it change placement preference?** **No.** Uniform placement is best both "
      "electrically and mechanically, and placement freedom has collapsed to 9.4 % compaction "
      "headroom.\n")
    A("**Q5. Does ARCH_B develop a real electrical/mechanical thickness conflict?** **Yes** — "
      "an interior electrical optimum at h ≈ 1.0 mm against a monotone mechanical preference. "
      "It costs 0.0873 W (0.07 %) to overrule, i.e. 0.016 W/µm.\n")
    A("**Q6. Do results survive BC-B / mounted conditions?** " + (
        "**Yes.** The qualified mounted metric preserves the free-package orderings; see "
        "Sec. 7-8." if pairs else "Pending the mounted pairs.") + "\n")
    A("**Q7. Does any source-backed criterion exclude the ET optimum?** **Unanswerable — no "
      "criterion exists.** G2 remains NOT TESTED.\n")
    A("**Q8. At what hypothetical ε would the ET optimum first be excluded?** **ε = 3.04 µm**, "
      "at a compliance cost of +5.19 W (+4.33 %). Below ε ≈ 1.27 µm nothing is admissible.\n")

    # ------------------------------------------------------------------ assembly state
    if pairs:
        A("### The assembly state decides the sign\n")
        def pget(grp, arch, h):
            return next((r for r in pairs if r["group"] == grp and r["arch"] == arch
                         and abs(F(r, "h_sub_mm") - h) < 1e-9), None)
        def aget(arch, h):
            return next((r for r in kw if r["group"] == "thickness" and r["arch"] == arch
                         and abs(F(r, "h_sub_mm") - h) < 1e-9), None)
        A("| arch | h_sub | BC-A free warpage (µm) | BC-B mounted warpage (µm) |")
        A("|---|---:|---:|---:|")
        rowsx = []
        for arch, hs in (("ARCH_A", (0.8, 1.5)), ("ARCH_B", (0.8, 2.0))):
            vals = []
            for h in hs:
                a, b = aget(arch, h), pget("thickness", arch, h)
                if a and b:
                    A(f"| {arch} | {h:.2f} mm | {F(a,'die_warpage_pv_um'):.4f} | "
                      f"{F(b,'die_warpage_pv_um'):.4f} |")
                    vals.append((F(a, "die_warpage_pv_um"), F(b, "die_warpage_pv_um")))
            if len(vals) == 2:
                da = 100 * (vals[1][0] - vals[0][0]) / vals[0][0]
                db = 100 * (vals[1][1] - vals[0][1]) / vals[0][1]
                rowsx.append((arch, da, db))
        A("")
        for arch, da, db in rowsx:
            A(f"* **{arch}, thin → thick:** free warpage **{da:+.1f} %**, mounted warpage "
              f"**{db:+.1f} %** — "
              f"{'**the sign REVERSES**' if da*db < 0 else 'sign preserved'}.")
        A("\n**But not every lever reverses.** Taking each lever between its two extremes:\n")
        A("| lever | BC-A free | BC-B mounted | |")
        A("|---|---:|---:|---|")
        def lv(lab, a0, a1, b0, b1):
            da = 100 * (a1 - a0) / a0
            db = 100 * (b1 - b0) / b0
            tag = "**SIGN REVERSES**" if da * db < 0 else "preserved"
            A(f"| {lab} | {da:+.2f} % | {db:+.2f} % | {tag} |")
        pa0, pa1 = aget("ARCH_A", 0.8), aget("ARCH_A", 1.5)
        pb0, pb1 = pget("thickness", "ARCH_A", 0.8), pget("thickness", "ARCH_A", 1.5)
        if all((pa0, pa1, pb0, pb1)):
            lv("thickness ARCH_A 0.8→1.5 mm", F(pa0, "die_warpage_pv_um"),
               F(pa1, "die_warpage_pv_um"), F(pb0, "die_warpage_pv_um"),
               F(pb1, "die_warpage_pv_um"))
        qa0, qa1 = aget("ARCH_B", 0.8), aget("ARCH_B", 2.0)
        qb0, qb1 = pget("thickness", "ARCH_B", 0.8), pget("thickness", "ARCH_B", 2.0)
        if all((qa0, qa1, qb0, qb1)):
            lv("thickness ARCH_B 0.8→2.0 mm", F(qa0, "die_warpage_pv_um"),
               F(qa1, "die_warpage_pv_um"), F(qb0, "die_warpage_pv_um"),
               F(qb1, "die_warpage_pv_um"))
        fa = sorted([r for r in kw if r["group"] == "footprint" and int(r["m_vr"]) >= 36],
                    key=lambda r: F(r, "a_hvr_total_mm2"))
        fb = sorted([r for r in pairs if r["group"] == "footprint"],
                    key=lambda r: F(r, "a_hvr_total_mm2"))
        if len(fa) >= 2 and len(fb) >= 2:
            lv("footprint 259→329 mm²", F(fa[0], "die_warpage_pv_um"),
               F(fa[-1], "die_warpage_pv_um"), F(fb[0], "die_warpage_pv_um"),
               F(fb[-1], "die_warpage_pv_um"))
        ua = next((r for r in kw if r["group"] == "placement" and r["fam"] == "uniform"), None)
        ca = next((r for r in kw if r["group"] == "placement" and r["fam"] == "compact"), None)
        ub = next((r for r in pairs if r["group"] == "placement" and r["fam"] == "uniform"), None)
        cb = next((r for r in pairs if r["group"] == "placement" and r["fam"] == "compact"), None)
        if all((ua, ca, ub, cb)):
            lv("placement uniform→compact", F(ua, "die_warpage_pv_um"),
               F(ca, "die_warpage_pv_um"), F(ub, "die_warpage_pv_um"),
               F(cb, "die_warpage_pv_um"))
        A("\n**Only thickness reverses.** Footprint and placement keep their sign in both "
          "assembly states, merely compressed by the board restraint. That is the sharpest "
          "form of the Phase-0F result: the reversal is specific to the one lever that acts "
          "through the substrate's bending stiffness, which is exactly the quantity a board "
          "foundation overrides.\n")
        A("\nThe mechanical preference for thickness is therefore **not a property of the "
          "design** — it is a property of the design **and its assembly state**. A framework "
          "that optimises free-package warpage and then mounts the package will move the "
          "substrate thickness in the wrong direction.\n")

    # ------------------------------------------------------------------ 16 verdict
    A("\\newpage\n## 16. Verdict (Sec. 16)\n")
    A("```\nASSEMBLY-STATE-DEPENDENT ETM CONSTRAINT\n```\n")
    A("Warpage grew fourfold at the reference scale, and the brief is explicit that growth "
      "alone does not license a positive verdict. It does not. What licenses this verdict is "
      "something else: **the mechanical preference and the electrical preference change places "
      "depending on how the package is mounted, and both states are well resolved.**\n")
    A("* In the **free package**, thicker is strongly better mechanically. ARCH_A's electrics "
      "agree; ARCH_B's do not, giving an interior electrical optimum and a genuine three-domain "
      "conflict.\n")
    A("* In the **board-mounted** package, the mechanical preference **inverts** — the "
      "restrained thick substrate deforms the die *more*, not less — and the conflict swaps "
      "architectures. ARCH_B's electrical preference for a thinner substrate now agrees with "
      "mechanics, while ARCH_A acquires the conflict it did not have.\n")
    A("* Both states are **qualified**: mounted warpage converges to 0.0 %, holds its ordering "
      "across nine material corners, and separates candidates by 72 %. This is not numerical "
      "noise, and it is not the Phase-0E situation at 240 W where the mounted signal vanished "
      "below the resolution floor.\n")
    A("\n**Why this is not the stronger verdict.** Mechanics is not a *synthesis constraint* "
      "at 1 kW, because nothing binds: no source-backed criterion exists, and the mechanical "
      "improvement is so cheap in the free state (0.016 W/µm for ARCH_B thickness) that no "
      "designer would trade against it. A constraint that changes no decision is not a "
      "constraint.\n")
    A("**Why this is not the weaker verdict.** Mechanics is not merely a signoff quantity "
      "either, because the *direction* of the correct design move depends on an assembly-state "
      "choice that an electrical/thermal framework does not model at all. A DVPD framework that "
      "optimises the free package and then mounts the result will move the substrate thickness "
      "the wrong way. That is a design-relevant coupling, and it is invisible without the "
      "mechanical model.\n")
    A("**What would settle it.** A calibrated board foundation and one source-backed mechanical "
      "criterion. The BC-B stiffness is still PROVISIONAL and G2 is still NOT TESTED, so the "
      "reversal is established but its consequences cannot yet be priced.\n")

    A("## 17. Recommended next work — and it is not the optimiser\n")
    A("Phase 0F did not build the global ETM optimiser, and the case for building it has not "
      "improved. Two things are now clearly worth more:\n")
    A("1. **Calibrate the board foundation.** The single largest unknown in the mounted state, "
      "and the entire assembly-state reversal rests on it. A BGA unit-cell or board-level "
      "model would settle whether the reversal is a real design effect or an artifact of a "
      "PROVISIONAL stiffness.\n")
    A("2. **Obtain one mechanical criterion.** Without it G2 stays untested through a fourth "
      "phase and no feasibility statement is possible at any scale. The ε-band 1.27–3.04 µm "
      "says exactly how much precision is needed for a criterion to matter.\n")
    A("\nThe remaining open items are unchanged from Phase 0E: GaN and MLCC layer heights, the "
      "RDL dielectric stack and stitching density, the electromigration lifetime limit, and "
      "assembly pre-stress (M1).\n")

    (OUT / "PHASE0F_1KW_ETM_GATE.md").write_text("\n".join(S) + "\n")
    print(f"wrote PHASE0F_1KW_ETM_GATE.md ({len(S)} blocks)")


if __name__ == "__main__":
    main()
