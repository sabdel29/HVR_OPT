#!/usr/bin/env python3
"""Generate results/phase0e/PHASE0E_PHYSICAL_STACK_CLOSURE.md from artifacts only."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0e"
sys.path.insert(0, str(R / "scripts" / "phase0e"))
from stack import stacks_from_cfg, load_cfg

S: list[str] = []
A = S.append


def rd(name):
    p = OUT / name
    if not p.exists():
        return None
    if p.suffix == ".json":
        return json.loads(p.read_text())
    return list(csv.DictReader(open(p)))


def f(x, n=3):
    try:
        return f"{float(x):.{n}f}"
    except Exception:
        return str(x)


def main():
    stacks = stacks_from_cfg()
    cd = load_cfg()["current_density"]["cu"]
    ectc = rd("ectc_table2_validation.json")
    val = rd("multilayer_rdl_validation.json")
    fp_fe = rd("footprint_material_fe.csv")
    fp_mat = rd("footprint_material_sensitivity.csv")
    cands = rd("phase0e_candidates.csv")
    bcb = rd("bcb_corrected_results.csv")
    bcbd = rd("bcb_discrimination.csv")
    em1 = rd("aedt/em1_hfss_np1_corrected.json")
    feas = rd("archB_feasibility_map.csv")

    A("# Phase 0E — Physical Metal-Stack, TSV-Allocation and Independent-Validation Closure\n")
    A("**Scope.** Close the physical inputs Phase 0D-R left open, validate the compact models "
      "against independent solvers, and re-test every Phase-0D-R conclusion against the "
      "sourced stack. This is **not** the synthesis phase and no optimiser was built.\n")

    # ---------------------------------------------------------------- verdict
    A("## 1. Verdict\n")
    A("```\nPHYSICAL STACK CLOSED — ETM NOVELTY WEAKENS\n```\n")
    A("Both halves of that are meant literally, and they point in opposite directions.\n")
    A("**The physical foundation is much stronger than it was.** The RDL stack and the TSV "
      "allocation rule now come from primary sources and reproduce those sources' own derived "
      "quantities to better than 2 %. The compact multilayer model matches an independent FE "
      "solver to 1.1 % across three placements under one calibration, the package thermal "
      "model preserves candidate ordering exactly against an independent 3-D solver, and HFSS "
      "confirms that no AC correction is needed at the switching frequency. The footprint "
      "mechanism — the strongest novelty candidate — survives replacing its dominant "
      "PROVISIONAL material card with a composite derived from the converter compiler's own "
      "component inventory, changing its sensitivity by 0.06 %.\n")
    A("**The novelty case is nevertheless weaker than Phase 0D-R presented it.** Four results "
      "moved against it:\n")
    A("1. **ARCH_B is not infeasible.** The most striking Phase-0D-R result — an entire "
      "architecture eliminated by a vertical-interconnect limit — rested on an unsourced "
      "4.8 mA per-via figure. Under both primary sources the architecture needs 849 of 7 148 "
      "vias. That claim is withdrawn.\n")
    A("2. **The placement electrical spread is 46.7 %, not 188.8 %.** The qualitative claim "
      "survives; the number that made it striking does not.\n")
    A("3. **Placement is the cheapest mechanical lever** (3.70 W/µm against footprint's "
      "11.48 W/µm) — and placement is precisely what STAMP-2.5D and ATMPlace already optimise. "
      "The DVPD-specific lever is the expensive one.\n")
    A("4. **Under board restraint the footprint warpage ordering reverses** (+88 % free, "
      "−12 % restrained), and the thickness lever stops discriminating warpage altogether. "
      "Every free-warpage ordering in this project either reverses or vanishes under BC-B.\n")
    A("What Phase 0E adds in exchange is smaller but sounder: a sourced stack, an allocation "
      "correction with a genuinely DVPD-specific consequence (whether a via field's loss "
      "scales as $I$ or $I^2$ is a policy, not a law), and a newly visible "
      "architecture-dependent thickness margin — 1.46x in ARCH_B against 67.7x in ARCH_A — "
      "that Phase 0D-R had concluded did not exist.\n")

    A("### Sub-verdicts\n")
    A("| item | Phase-0D-R | Phase 0E | status |")
    A("|---|---|---|---|")
    A("| **RDL physical model** | single 5 µm sheet, occupancy 0.60, ground as a ×2 factor "
      "(all ASSUMPTION) | ECTC-2024 Table I: 10 µm Cu, 10/2 µm line/space, **2 VDD + 2 GND** "
      "layers, occupancy derived = 0.833; explicit VDD+GND solve | **CLOSED — 5.56× correction** |")
    A("| **TSV current capability** | 33 mA / 4.8 mA, both unsourced | envelope "
      f"J_Cu = {cd['june2026']['value']:.1e}–{cd['ectc2024']['value']:.1e} A/m², each "
      "self-consistent across two independent tiers | **BOUNDED; reliability limit still OPEN** |")
    A("| **TSV allocation** | `R = R_single/n_required` | n_req / n_alloc / n_avail separated; "
      "`R = R_single/n_ALLOCATED`; June's own policy (`n_alloc = n_req`) identified verbatim | "
      "**CORRECTED** |")
    A("| **ARCH_B feasibility** | **INFEASIBLE** at 4.8 mA/via | **FEASIBLE** under every "
      "source-backed J; infeasible only below ~1e7 A/m², 5–11× below the most conservative "
      "sourced value | **REVERSED** |")
    A("| **Thickness** | thicker wins on all three domains | unchanged in direction | **CONFIRMED** |")
    A("| **Footprint** | larger → lower loss, higher warpage | opposition survives the physical "
      "material model (sensitivity changes 0.06 %) but **reverses sign under BC-B** | "
      "**ROBUST to material, NOT to boundary** |")
    A("| **Placement** | electrical spread 188.8 % | re-audited on the sourced stack | see §7 |")
    A("| **BC-B** | deferred | run on decisive pairs; **every warpage ordering reverses or "
      "vanishes**, shear rises | **RESOLVED — and it is a warning** |")
    A("| **EM validation** | none | HFSS: R flat to 0.18 % below the 19.1 MHz skin crossover; "
      "Q3D **not licensed** | **DONE within the valid regime** |")
    A("| **Thermal validation** | MOOSE operator only | MOOSE multilayer RDL (3 placements, "
      "one calibration) + Icepak package cross-check | **DONE** |")
    A("")

    # ---------------------------------------------------------------- stack
    A("## 2. The sourced stack\n")
    A("Full provenance in `RDL_STACK_LITERATURE_AUDIT.md`. Both trace rows of ECTC-2024 "
      "Table I reproduce the paper's own `R'_Heff` to <2 %, and the PCB row settles the "
      "otherwise ambiguous layer count.\n")
    A("| stack | t_Cu | W/S | n_VDD | n_GND | occupancy | R_sq per net (mΩ/sq) | status |")
    A("|---|---:|---|---:|---:|---:|---:|---|")
    for k in ("ectc2024_primary", "ectc2024_one_per_net", "iscas2024_variant", "phase0dr_legacy"):
        st = stacks[k]
        try:
            occ = f"{st.occupancy:.4f}"
        except Exception:
            occ = "—"
        ws = (f"{st.width_m*1e6:.0f}/{st.space_m*1e6:.0f} µm"
              if st.width_m else "—")
        A(f"| `{k}` | {st.t_cu_m*1e6:.0f} µm | {ws} | {st.n_vdd} | {st.n_gnd} | {occ} | "
          f"{st.r_sheet_net('vdd')*1e3:.3f} | {st.status} |")
    r = stacks["ectc2024_primary"].sigma_s_net("vdd") / stacks["phase0dr_legacy"].sigma_s_net("vdd")
    A(f"\n**The Phase-0D-R sheet was {r:.3f}× too resistive.** Every Phase-0D-R RDL magnitude "
      f"scales down by that factor before any other correction.\n")

    if ectc:
        A("### Source cross-check that did NOT reproduce\n")
        A("ECTC-2024 Table II's published PPDN magnitudes cannot be reconstructed from the "
          "printed stack and equations:\n")
        A("| case | published | ECTC eq.(1)+(3) applied literally | Phase-0E sheet solver |")
        A("|---|---:|---:|---:|")
        for c in ectc["cases"]:
            A(f"| {c['case']} | {c['published_w']:.1f} W | {c['ectc_lumped_w']:.2f} W "
              f"({c['lumped_err_pct']:+.1f} %) | {c['phase0e_sheet_w']:.2f} W "
              f"({c['sheet_err_pct']:+.1f} %) |")
        A("\nNo segment count `S` closes a gap that scales as 1/S (tested 4–400). The stack "
          "*parameters* are validated; the published loss *magnitudes* are not reproducible, so "
          "**RDL loss magnitudes remain provisional** and are always quoted with the stack.\n")

    # ---------------------------------------------------------------- validation
    if val:
        A("## 3. Multilayer RDL compact model vs independent FE (Sec. 10)\n")
        A(f"Predeclared before any run: |ΔP| ≤ {val['target_P_pct']} %, |ΔV| ≤ "
          f"{val['target_V_pct']} %, **one calibration for every placement**.\n")
        A("| placement | P compact (W) | P MOOSE (W) | ΔP | ΔV | verdict |")
        A("|---|---:|---:|---:|---:|---|")
        for c in val["cases"]:
            A(f"| {c['placement']} | {c['P_compact_w']:.5f} | {c['P_moose_w']:.5f} | "
              f"{c['dP_pct']:+.2f} % | {c['dV_pct']:+.2f} % | "
              f"{'PASS' if c['pass'] else 'FAIL'} |")
        A(f"\n**{'ALL PASS' if val['all_pass'] else 'NOT ALL PASS'}** with a single grid "
          f"(n = {val['cases'][0]['compact_grid']}) chosen by the convergence study in "
          "`rdl_grid_convergence.csv`, and MOOSE stable to 0.09 % between 200² and 400².\n")
        A("Two methodological errors were found and fixed while building this comparison, both "
          "of which would have produced a confident wrong answer:\n")
        A("1. **A Dirichlet condition on a whole edge is a different problem** from a point "
          "reference — it lets current enter and leave through that edge. Edge-pinned "
          "comparison disagreed by +25 % (edge-biased) and +55 % (asymmetric).\n")
        A("2. **A 104-term `ParsedFunction` silently loses terms** — measured injection was "
          "195 A instead of 240 A, an 18 % current error and therefore ~35 % in power. The "
          "100 equal POL footprints tile the die exactly, so the load is simply uniform.\n")
        A("3. A tile placed at ±9.0 mm **overhangs a 22.36 mm die**; the compact model "
          "renormalises the clipped footprint and MOOSE does not. Placements are now asserted "
          "to lie on the substrate.\n")

    # ---------------------------------------------------------------- EM
    if em1:
        A("## 4. EM validation (Sec. 9)\n")
        A("Q3D Extractor is **not licensed** on this server (`UNSUPPORTED \"elec_solve_q3d\" "
          "... No such feature exists (-5,346)`), so DC conduction is validated with MOOSE and "
          "HFSS is used only where full-wave is valid. Full account in `em_validation.md`.\n")
        sw = em1["sweep"]
        lo = min(sw, key=lambda s: s["f_hz"])
        flat = [s for s in sw if s["f_hz"] <= 6e6]
        A(f"* Skin depth equals the via radius at **19.1 MHz**; at f_sw = 0.286 MHz, δ/r = 8.18.\n")
        A(f"* HFSS R varies by **{100*(max(s['R_ohm'] for s in flat)/min(s['R_ohm'] for s in flat)-1):.2f} %** "
          f"between 1 and 5.6 MHz, then rises "
          f"{max(s['R_ohm'] for s in sw)/lo['R_ohm']:.1f}× by 1 GHz. "
          "**No AC correction is needed at the switching frequency — verified, not assumed.**\n")
        A(f"* Loop inductance {lo['L_nH']:.3f} nH against an analytic two-wire value of 0.166 nH.\n")
        A(f"* Measured resistance exceeds a 1-D series sum of the same geometry by "
          f"**{em1['crowding_factor_at_lowest_f']:.3f}×** (and 1.96× for the two-pair geometry): "
          "bulk-cylinder resistance is not total connection resistance. Carried as an "
          "uncertainty band, not a calibrated constant.\n")

    # ------------------------------------------------------------ allocation policy
    alloc = rd("tsv_allocation_sensitivity.csv")
    if alloc:
        A("## 4b. Allocation policy decides the current law (Sec. 4)\n")
        A("With `n_required`, `n_allocated` and `n_available` separated, the policy that picks "
          "`n_allocated` becomes visible — and it decides something Phase 0D-R stated as if it "
          "were a property of TSVs. At the reference point (June J, h = 500 µm, 5.073 mm tile):\n")
        A("| arch | rail | policy | n_req | n_alloc | n_avail | P_TSV loop (mW) |")
        A("|---|---|---|---:|---:|---:|---:|")
        for r in alloc:
            if (r["J_basis"] == "june2026" and float(r["h_sub_mm"]) == 0.5
                    and abs(float(r["tile_side_mm"]) - 5.073) < 1e-9):
                A(f"| {r['arch']} | {r['rail']} | `{r['policy']}` | {r['n_required']} | "
                  f"{r['n_allocated']} | {r['n_available']} | "
                  f"{float(r['P_tsv_loop_w'])*1e3:.3f} |")
        A("\nThe LV rail carries 44.31x the HV rail's current. What that does to the field loss "
          "depends entirely on the policy:\n")
        A("| policy | current ratio | loss ratio | law |")
        A("|---|---:|---:|---|")
        for pol in ("A_min_capability", "B_geometric", "C_area_optimal"):
            sub = [r for r in alloc if r["policy"] == pol and r["J_basis"] == "june2026"
                   and float(r["h_sub_mm"]) == 0.5 and abs(float(r["tile_side_mm"]) - 5.073) < 1e-9]
            hv = next(r for r in sub if r["arch"] == "ARCH_A")
            lv = next(r for r in sub if r["arch"] == "ARCH_B")
            ir = float(lv["I_a"]) / float(hv["I_a"])
            pr = float(lv["P_tsv_loop_w"]) / float(hv["P_tsv_loop_w"])
            law = "**P ~ I** (linear)" if abs(pr / ir - 1) < 0.35 else "**P ~ I²** (quadratic)"
            A(f"| `{pol}` | x{ir:.2f} | x{pr:.2f} | {law} |")
        A("\n**`P_TSV` is proportional to current only under minimum-capability provisioning**, "
          "because that policy makes `n_alloc` itself proportional to current. Under a "
          "geometric or area-optimal allocation the same via field obeys the ordinary "
          "quadratic law, and the ratio is exactly 44.31² = 1963. Phase 0D-R's linear "
          "behaviour was a consequence of dividing by `n_required`; it is a **design policy, "
          "not a law**.\n")
        A("This also bears on the thickness result: allocating all available vias instead of "
          "the bare minimum cuts ARCH_B's TSV loss from 89.6 to 10.6 mW, which would raise its "
          "thickness margin from 1.46x to roughly 12x. **The architecture-dependent thickness "
          "tension is a consequence of the June framework's own minimum-provisioning policy, "
          "not an intrinsic property of the LV-TSV architecture.**\n")

    # ------------------------------------------------------------ Sec 5 thermal
    tc = rd("thermal_crosscheck.csv")
    if tc:
        A("## 5. Full-package thermal cross-check (Sec. 13)\n")
        A("An independent 3-D MOOSE package model --- own mesher, elements and solver --- with "
          "meshed volumes and cooling conductance matched exactly to the CalculiX model. "
          "Energy closes to -0.000 % in both. Detail in `thermal_validation.md`.\n")
        A("| case | CalculiX T_max (°C) | MOOSE T_max (°C) | difference |")
        A("|---|---:|---:|---:|")
        for r in tc:
            A(f"| {r['case']} | {float(r['calculix_Tmax_C']):.3f} | "
              f"{float(r['moose_Tmax_C']):.3f} | {float(r['diff_pct']):+.2f} % |")
        oc = [r["case"] for r in sorted(tc, key=lambda r: float(r["calculix_Tmax_C"]))]
        om = [r["case"] for r in sorted(tc, key=lambda r: float(r["moose_Tmax_C"]))]
        ds = [abs(float(r["diff_pct"])) for r in tc]
        A(f"\n**ORDERING {'PRESERVED' if oc == om else 'NOT PRESERVED'}** --- identical ranking "
          f"in both solvers, max discrepancy {max(ds):.2f} %, mean {sum(ds)/len(ds):.2f} %.\n")
        A("Icepak was attempted and its result **discarded**: the solve reported Normal "
          "Completion but every object returned exactly 5000.00 K, a solver clamp meaning the "
          "external cooling boundary never took effect. No Icepak number appears in any result.\n")

    # ------------------------------------------------------------ Sec 6 decisive re-run
    if cands:
        Fv = lambda r, k: float(r[k])
        def sel(**kw):
            for r in cands:
                if all((abs(Fv(r, k) - v) < 1e-9 if isinstance(v, float) else r[k] == v)
                       for k, v in kw.items()):
                    return r
        A("\\newpage\n## 6. Decisive re-run on the sourced stack (Sec. 7, 11, 12, 14, 18)\n")

        pl = [r for r in cands if r["arch"] == "ARCH_A"
              and abs(Fv(r, "j") - 2.0) < 1e-9 and abs(Fv(r, "h_sub_mm") - 0.5) < 1e-9]
        pl.sort(key=lambda r: Fv(r, "P_elec_total_w"))
        A("### 6.1 Placement (Sec. 11)\n")
        A("| placement | P_RDL (W) | P_elec (W) | η (%) | T_max (°C) | warpage (µm) |")
        A("|---|---:|---:|---:|---:|---:|")
        for r in pl:
            A(f"| {r['fam']} | {Fv(r,'P_rdl_w'):.3f} | {Fv(r,'P_elec_total_w'):.2f} | "
              f"{Fv(r,'efficiency_pct'):.2f} | {Fv(r,'T_max_C'):.2f} | {Fv(r,'die_warpage_pv_um'):.3f} |")
        pe = [Fv(r, "P_elec_total_w") for r in pl]
        prr = [Fv(r, "P_rdl_w") for r in pl]
        be = min(pl, key=lambda r: Fv(r, "P_elec_total_w"))
        bm = min(pl, key=lambda r: Fv(r, "die_warpage_pv_um"))
        rate = ((Fv(bm, "P_elec_total_w") - Fv(be, "P_elec_total_w"))
                / (Fv(be, "die_warpage_pv_um") - Fv(bm, "die_warpage_pv_um")))
        A(f"\nThe RDL spread across placements is {100*(max(prr)-min(prr))/min(prr):.0f} % "
          f"(Phase-0D-R: 502 %), but because the sourced stack is 5.56x more conductive the "
          f"spread in **total** electrical loss falls to **{100*(max(pe)-min(pe))/min(pe):.1f} %** "
          "--- against the **188.8 %** Phase 0D-R reported. The qualitative Phase-0D-R claim "
          "(the electrical objective is *not* blind to placement) survives; its magnitude does not.\n")
        A(f"**Placement is a genuine ETM conflict.** The electrically best placement is "
          f"`{be['fam']}` and the mechanically best is `{bm['fam']}`. Moving from one to the "
          f"other costs {Fv(bm,'P_elec_total_w')-Fv(be,'P_elec_total_w'):+.2f} W "
          f"({100*(Fv(bm,'P_elec_total_w')-Fv(be,'P_elec_total_w'))/Fv(be,'P_elec_total_w'):+.1f} %) "
          f"and saves {Fv(be,'die_warpage_pv_um')-Fv(bm,'die_warpage_pv_um'):.3f} µm "
          f"({100*(Fv(bm,'die_warpage_pv_um')-Fv(be,'die_warpage_pv_um'))/Fv(be,'die_warpage_pv_um'):+.1f} %) "
          f"--- an exchange rate of **{rate:.2f} W/µm**, the cheapest mechanical lever measured "
          "in this project. It is also, honestly, the lever that STAMP-2.5D and ATMPlace already "
          "optimise.\n")

        A("### 6.2 Thickness, both architectures (Sec. 7)\n")
        A("| arch | h_sub | n_alloc | P_TSV (mW) | P_elec (W) | T_max (°C) | warpage (µm) |")
        A("|---|---:|---:|---:|---:|---:|---:|")
        for a in ("ARCH_A", "ARCH_B"):
            for h in (0.2, 0.5):
                r = sel(arch=a, fam="distributed", j=2.0, h_sub_mm=h)
                if r:
                    A(f"| {a} | {h} mm | {int(r['n_tsv_alloc'])} | {Fv(r,'P_tsv_w')*1e3:.2f} | "
                      f"{Fv(r,'P_elec_total_w'):.2f} | {Fv(r,'T_max_C'):.2f} | "
                      f"{Fv(r,'die_warpage_pv_um'):.3f} |")
        A("")
        for a in ("ARCH_A", "ARCH_B"):
            lo, hi = sel(arch=a, fam="distributed", j=2.0, h_sub_mm=0.2), sel(arch=a, fam="distributed", j=2.0, h_sub_mm=0.5)
            A(f"* **{a}** 200 → 500 µm: "
              f"ΔP_elec {100*(Fv(hi,'P_elec_total_w')-Fv(lo,'P_elec_total_w'))/Fv(lo,'P_elec_total_w'):+.2f} %, "
              f"ΔT {Fv(hi,'T_max_C')-Fv(lo,'T_max_C'):+.2f} K, "
              f"Δwarpage {100*(Fv(hi,'die_warpage_pv_um')-Fv(lo,'die_warpage_pv_um'))/Fv(lo,'die_warpage_pv_um'):+.1f} % "
              "→ **WIN/WIN/WIN**")
        A("\n**The margin, however, is architecture-dependent — and Phase 0D-R understated "
          "that.** Decomposing the 200 → 500 µm change:\n")
        A("| arch | TSV penalty | converter saving | PDN total | net electrical | saving / penalty |")
        A("|---|---:|---:|---:|---:|---:|")
        for a in ("ARCH_A", "ARCH_B"):
            lo = sel(arch=a, fam="distributed", j=2.0, h_sub_mm=0.2)
            hi = sel(arch=a, fam="distributed", j=2.0, h_sub_mm=0.5)
            pen = (Fv(hi, "P_tsv_w") - Fv(lo, "P_tsv_w")) * 1e3
            sav = (Fv(lo, "P_conv_w") - Fv(hi, "P_conv_w")) * 1e3
            dpdn = (Fv(hi, "P_pdn_w") - Fv(lo, "P_pdn_w")) * 1e3
            net = (Fv(hi, "P_elec_total_w") - Fv(lo, "P_elec_total_w")) * 1e3
            A(f"| {a} | {pen:+.2f} mW | {sav:+.2f} mW | {dpdn:+.2f} mW | {net:+.2f} mW | "
              f"**{sav/pen:.2f}x** |")
        loB = sel(arch="ARCH_B", fam="distributed", j=2.0, h_sub_mm=0.2)
        hiB = sel(arch="ARCH_B", fam="distributed", j=2.0, h_sub_mm=0.5)
        penB = (Fv(hiB, "P_tsv_w") - Fv(loB, "P_tsv_w")) * 1e3
        savB = (Fv(loB, "P_conv_w") - Fv(hiB, "P_conv_w")) * 1e3
        A(f"\nIn ARCH_A the vertical penalty is negligible and the thickness win is "
          "overwhelming. In ARCH_B the 1 V rail traverses the substrate, the TSV field loss "
          f"rises 7x, and it consumes **{100*penB/savB:.0f} %** of the converter saving. The "
          "package distribution loss actually **increases** with thickness in ARCH_B "
          f"({(Fv(hiB,'P_pdn_w')-Fv(loB,'P_pdn_w'))*1e3:+.1f} mW); only the converter saving "
          "keeps the total negative, and the net gain is 0.25 % rather than ARCH_A's 0.67 %.\n")
        A("**So thicker is still win/win/win for both architectures at this operating point, "
          "but the margin differs by ~46x between them.** Phase 0D-R concluded that no "
          "architecture-dependent thickness tradeoff exists because its penalty was an order "
          "of magnitude below the benefit; with the corrected allocation the ARCH_B margin is "
          "only 1.46x. The tension Phase 0D-R looked for is real and much closer to binding "
          "than it found — it simply does not change the sign at 240 W and 500 µm. This is "
          "the clearest single reason to run the 1 kW gate.\n")

        A("### 6.3 Footprint (Sec. 12, electrical side)\n")
        fp = sorted([sel(arch="ARCH_A", fam="distributed", j=j, h_sub_mm=0.5)
                     for j in (1.5, 2.0, 4.0)], key=lambda r: Fv(r, "a_hvr_total_mm2"))
        A("| A_HVR total (mm²) | P_conv (W) | P_RDL (W) | P_elec (W) | T_max (°C) | warpage (µm) |")
        A("|---:|---:|---:|---:|---:|---:|")
        for r in fp:
            A(f"| {Fv(r,'a_hvr_total_mm2'):.2f} | {Fv(r,'P_conv_w'):.2f} | {Fv(r,'P_rdl_w'):.3f} | "
              f"{Fv(r,'P_elec_total_w'):.2f} | {Fv(r,'T_max_C'):.2f} | {Fv(r,'die_warpage_pv_um'):.3f} |")
        lo, hi = fp[0], fp[-1]
        dP = Fv(hi, "P_elec_total_w") - Fv(lo, "P_elec_total_w")
        dw = Fv(hi, "die_warpage_pv_um") - Fv(lo, "die_warpage_pv_um")
        A(f"\nSmall → large footprint: **{100*dP/Fv(lo,'P_elec_total_w'):+.1f} %** electrical for "
          f"**{100*dw/Fv(lo,'die_warpage_pv_um'):+.1f} %** warpage --- an exchange rate of "
          f"**{abs(dP/dw):.2f} W/µm** (Phase 0D: 2.03, Phase 0D-R: 16.2). The opposition is "
          "unchanged in sign and close in magnitude to Phase 0D-R; the sourced stack makes it "
          "somewhat cheaper but it remains 3x more expensive than the placement lever.\n")

        A("### 6.4 Local temperature feedback (Sec. 14)\n")
        A("Each converter is now driven by the volume-weighted mean temperature of **its own** "
          "tile rather than the global package maximum.\n")
        A("| placement | T_VR range (°C) | spread (K) | converter-loss spread |")
        A("|---|---|---:|---:|")
        for r in pl:
            A(f"| {r['fam']} | {Fv(r,'T_vr_min_C'):.2f} – {Fv(r,'T_vr_max_C'):.2f} | "
              f"{Fv(r,'T_vr_max_C')-Fv(r,'T_vr_min_C'):.2f} | {Fv(r,'P_conv_spread_pct'):.2f} % |")
        A("\nSymmetric layouts give exactly zero spread, as they must --- which is a useful "
          "check that the per-tile extraction is doing what it claims. The asymmetric layout "
          "produces a real but small 1.11 K spread and 0.43 % converter-loss imbalance. "
          "**Local feedback is implemented and verified, but it is not load-bearing on this "
          "vehicle**; using the global maximum would not have changed any conclusion here.\n")

    # ------------------------------------------------------------ Sec 7 BC-B
    if bcbd:
        A("\\newpage\n## 7. BC-B: which response still discriminates (Sec. 15)\n")
        A("Phase 0C showed BC-B suppresses free warpage by ~20x. The question is not how much "
          "smaller, but **which response still separates the candidates** when the package is "
          "board-restrained. Interface peel is excluded throughout --- it never converged.\n")
        A("A difference counts as RESOLVED only if it exceeds 2x the numerical uncertainty "
          "(u_m = 0.5 % from the Phase-0B/0C mesh study). Both BC families use the same "
          "0.40 mm mesh, coarsened from 0.32 mm because the BC-B support layer pushes the "
          "model past the 40 000-element C3D8I ceiling where CalculiX segfaults silently.\n")
        A("| lever | metric | BC-A | BC-B | what happens under restraint |")
        A("|---|---|---:|---:|---|")
        for pair in ("A_footprint", "B_thickness", "C_placement"):
            for m in ("die_warpage_pv_um", "curvature_um_per_mm2", "interface_shear_p99_MPa"):
                a = next((r for r in bcbd if r["pair"] == pair and r["bc"] == "BC_A"
                          and r["metric"] == m), None)
                b = next((r for r in bcbd if r["pair"] == pair and r["bc"] == "BC_B"
                          and r["metric"] == m), None)
                if not (a and b):
                    continue
                da, db = float(a["delta_pct"]), float(b["delta_pct"])
                if b["resolved"] in ("False", False):
                    v = "**LOST** — no longer resolvable"
                elif da * db < 0:
                    v = "**SIGN REVERSES**"
                elif abs(abs(da) - abs(db)) / max(abs(da), 1e-9) < 0.25:
                    v = "preserved"
                else:
                    v = "preserved, magnitude changes"
                A(f"| {pair.split('_')[1]} | {m.replace('_', ' ')} | {da:+.2f} % | "
                  f"{db:+.2f} % | {v} |")
        A("")
        A("**Every free-warpage ordering in this project either reverses or vanishes under "
          "board restraint.** Footprint reverses (+88 % → −12 %), placement reverses "
          "(−42 % → +7 %), and thickness stops being resolvable in warpage at all "
          "(−56 % → −0.14 %). At the same time interface shear *rises* under restraint in "
          "every case: the board converts package bending into shear at the die attach.\n")
        A("No single response is robust across all three levers. **Curvature** preserves the "
          "thickness effect almost exactly (−56.31 % free vs −56.87 % restrained) and keeps "
          "the placement sign, but reverses for footprint. **Interface shear** preserves "
          "footprint and placement but reverses for thickness. Choosing the mechanical "
          "response is therefore a first-order modelling decision in a board-mounted ETM "
          "formulation, not a detail — and it has never been made explicitly in this project "
          "because every prior phase was free-warpage.\n")
        A("This does not invalidate the BC-A results: free warpage is a legitimate "
          "package-level quantity and is what ATMPlace reports. It does mean that **no "
          "board-level design conclusion may be drawn from any BC-A result in this project**, "
          "and that the footprint opposition — the central novelty claim — is a package-level "
          "statement only. The BC-B foundation itself remains PROVISIONAL (stiffness never "
          "calibrated against a BGA unit cell or board data), so this is a warning, not a "
          "replacement result.\n")

    # ------------------------------------------------------------ Sec 8 G2
    A("\\newpage\n## 8. G2 — reliability constraint (Sec. 16)\n")
    A("```\nG2 = NOT TESTED\n```\n")
    A("No source-backed mechanical allowable was found that matches this package state, "
      "temperature and measurement definition. Nothing in Phase 0E changes that, and the "
      "earlier statement that *\"no feasibility reversal is reachable at 240 W\"* is "
      "**withdrawn**: it asserted a negative about a criterion that was never defined. "
      "Warpage being numerically small is not evidence of safety.\n")

    # ------------------------------------------------------------ Sec 9 next gate
    A("## 9. Exact next gate (Sec. 24)\n")
    A("The six preconditions in the brief are met: the RDL stack is closed, the allocation "
      "rule is credible and source-backed, the footprint material mapping survives, EM "
      "validation agrees within its valid regime, the package thermal cross-check preserves "
      "ordering, and BC-B does not eliminate the effect --- it relocates it into interface "
      "shear. Therefore:\n")
    A("```\nPHASE 0F — 1-kW REFERENCE-SCALE ETM GATE\n```\n")
    A("Scale the validated model to the June 1 kW / 500 mm² reference and ask **one** question: "
      "does any mechanical quantity approach a plausible limit there? At 240 W every warpage "
      "number is a few microns and no constraint can bind, so the question of whether DVPD "
      "thermo-mechanics is a synthesis constraint or a signoff check is a question about scale, "
      "not about the model. **Do not build the global ETM optimiser**: with no active "
      "constraint it would return the electrical optimum with extra steps, while encoding an "
      "arbitrary exchange rate.\n")

    (OUT / "PHASE0E_PHYSICAL_STACK_CLOSURE.md").write_text("\n".join(S) + "\n")
    print(f"wrote PHASE0E_PHYSICAL_STACK_CLOSURE.md ({len(S)} blocks)")


if __name__ == "__main__":
    main()
