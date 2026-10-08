#!/usr/bin/env python3
"""Phase-0M Part 45 -- splice Phase 0M into the chronological full technical report."""
from __future__ import annotations
import csv, math, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
REP = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
M = R / "results" / "phase0m"
G = str(M)
rows = lambda n: list(csv.DictReader(open(M / n))) if (M / n).is_file() else []
F = lambda r, k: float(r[k])


def fm(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def place(s, name, frag, before):
    pat = re.compile(rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n",
                     re.S)
    if pat.search(s):
        print(f"  ok  {name}: refreshed")
        return pat.sub(lambda _: frag, s, count=1)
    assert before in s, f"anchor missing for {name}"
    print(f"  ok  {name}: inserted")
    return s.replace(before, frag + before, 1)


def sub(s, old, new, what):
    if new in s and old not in s:
        print(f"  ok  {what} (already applied)")
        return s
    assert s.count(old) == 1, f"anchor problem for {what}: count={s.count(old)}"
    print(f"  ok  {what}")
    return s.replace(old, new, 1)


def narrative() -> str:
    me = rows("me_energy_reconstruction.csv")
    prov = rows("specimen_count_provenance.csv")
    crowd = [r for r in rows("current_crowding_transition_sweep.csv") if r["status"] == "OK"]
    route = [r for r in rows("intra_vr_routing_model.csv") if r.get("level") == "R1"]
    part = rows("component_partition_templates.csv")
    z5d = rows("z5_path_decomposition.csv")
    z5f = rows("z5_architecture_comparison.csv")
    eff = rows("effective_layer_properties.csv")
    cool = rows("cooling_architecture_sensitivity.csv")
    cetm = rows("cooling_etm_sensitivity.csv")
    poly = rows("polymer_modulus_screen.csv")
    pre = rows("assembly_prestress_test.csv")
    fb = rows("etm_feedback_magnitudes.csv")
    mat = rows("PHYSICS_PRIORITY_MATRIX.csv")
    sens = rows("design_space_sensitivity.csv")

    ks = [F(r, "K_crowd") for r in crowd]
    ps = [F(r, "p_system_w") for r in route]
    m1z1 = next((r for r in me if r["model"] == "M1" and r["arch"] == "Z1"), {})
    m1z2 = next((r for r in me if r["model"] == "M1" and r["arch"] == "Z2"), {})
    polyw = max((r for r in poly if r["case"] != "baseline"),
                key=lambda r: abs(F(r, "ratio_shift_pct")), default={})
    prat = next((r for r in pre if r["arch"] == "RATIO"), {})
    sw = max((r for r in sens if r["case"] != "baseline"),
             key=lambda r: abs(F(r, "ratio_shift_pct")), default={})
    cw = max(cetm, key=lambda r: abs(F(r, "warpage_vs_uniform_pct"))) if cetm else {}
    tsv_ref = next((r for r in eff if r["layer"] == "TSV_array"
                    and "p=60" in r["geometry"]), {})
    rdl = [r for r in eff if r["layer"] == "RDL_dielectric"]
    p1 = [r["physics"] for r in mat if r["priority"] == "P1"]

    L = ["<!-- BEGIN GENERATED: phase0m_narrative -->", "", r"\newpage", "",
         "# Phase 0M --- Geometry-Resolved Power Delivery, Component-Level Architecture, "
         "Cooling and ETM-Coupling Audit (current authoritative)", ""]
    A = L.append
    A("**Verdict: G --- MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER; OPTIMIZATION "
      "STILL PREMATURE.** Phase 0M is an audit and model-generalization gate. It did not "
      "build the optimizer, did not run an architecture DOE, and did not implement physics "
      "merely because it exists.")
    A("")
    A("## Residual Phase-0L-R closure")
    A("")
    A("DEFECT #46 is eliminated at the root rather than patched. CalculiX `ME` --- the "
      "mechanical strain, total minus thermal --- is now requested in the deck, the "
      "inelastic strain is reconstructed as `eps_in = ME - C^-1(T):S`, and the temperature "
      "itself is recovered from the same output block through `tr(E - ME) = 3 alpha "
      "(T - T_zero)`. No separately parsed temperature block appears anywhere in the energy "
      "path, so the class of error cannot recur.")
    A("")
    A("| model | arch | W production | W solver-coherent | ratio | isochoric residual, ME | "
      "isochoric residual, Python |")
    A("|---|---|---|---|---|---|---|")
    for r in me:
        A(f"| {r['model']} | {r['arch']} | {fm(r['W_production_MJ_per_m3'], 5)} | "
          f"{fm(r['W_me_self_MJ_per_m3'], 5)} | {fm(r['me_over_production'], 4)} | "
          f"{float(r['isochoric_residual_ME']):.2e} | "
          f"{float(r['isochoric_residual_python']):.2e} |")
    A("")
    A(f"The Phase-0L-R fix was correct and its residual is now bounded: the two routes agree "
      f"to 0.79 to 1.56 %. On the assumption-free test --- inelastic flow must be isochoric "
      f"--- the ME route is **16 to 20 times cleaner**. Recomputed Z1/Z2 inelastic energy: "
      f"{fm(m1z1.get('W_me_self_MJ_per_m3'), 5)} against "
      f"{fm(m1z2.get('W_me_self_MJ_per_m3'), 5)} MJ/m3, ratio "
      f"**{fm(float(m1z1['W_me_self_MJ_per_m3'])/float(m1z2['W_me_self_MJ_per_m3']), 4) if m1z1 and m1z2 else '--'}**.")
    A("")
    A("One authoritative specimen-count provenance table now exists, because four counts were "
      "live and had been quoted against each other:")
    A("")
    A("| phase | n / cell | packages | status | model | D |")
    A("|---|---|---|---|---|---|")
    for r in prov:
        A(f"| {r['phase']} | **{r['n_per_cell']}** | **{r['packages']}** | {r['status']} | "
          f"`{r['model']}` | {fm(r['D'], 4)} |")
    A("")
    A("The theorem-like wording *any monotone solder law MUST rank Z1 worse* is withdrawn "
      "from both reports, the status file and the two generators that produce them. The "
      "licensed statement is that the global package supplies a constitutive-law-independent "
      "deformation driver favoring Z2, and every presently testable constitutive/life-law "
      "combination preserves that ordering.")
    A("")
    A("## The TSV radius law")
    A("")
    A("The hypothesis under test was *increasing TSV radius decreases ohmic loss but "
      "decreases density*. It is true for one via. For a FIELD it depends entirely on the "
      "allocation policy, and under the policy the reference framework actually uses it is "
      "false in a strong sense:")
    A("")
    A("$$R_{field} = \\frac{\\rho h}{A_c}\\cdot\\frac{J_{max} A_c}{I} "
      "= \\frac{\\rho h J_{max}}{I}$$")
    A("")
    A("The conductor cross-section cancels **identically** --- not merely the radius, so the "
      "result is independent of via shape and of the liner too. Three corollaries follow: the "
      "IR drop `rho h J_max` does not depend on the current; the loss `I rho h J_max` is "
      "LINEAR in current, not quadratic; and the copper fraction `I / (J_max A_field)` "
      "contains neither the radius nor the height, so the effective conductivity, modulus and "
      "CTE do not move with radius either. **Derating harder --- a lower `J_max` --- lowers "
      "the loss.** Measured over r = 2.5 to 50 um the field resistance moves 0.07 % under "
      "minimum-capability allocation and 314 % under fixed-count allocation.")
    A("")
    A(f"![FIG-0M-A]({G}/FIG_0M_A_tsv_allocation.png)")
    A("")
    A("*FIG-0M-A. Single via against via field. The first panel shows the intuition holding "
      "for one via; the second shows it cancelling for a minimum-provisioned field.*")
    A("")
    A(f"![FIG-0M-B]({G}/FIG_0M_B_tsv_coupling.png)")
    A("")
    A("*FIG-0M-B. One TSV variable seen in four domains at once.*")
    A("")
    A("## Current crowding is a function, not a constant")
    A("")
    A(f"No DC conduction solver was installed, so one was built and verified: exact on a "
      f"uniform bar at every mesh, and within 0.9 % of the analytic spreading resistance "
      f"`rho/(4a)` on a contact resolved by six cells per radius. Across "
      f"{len(crowd)} converged transition geometries **`K_crowd` spans {min(ks):.3f} to "
      f"{max(ks):.3f}**, a factor of {max(ks)/min(ks):.2f}, against the single constant 1.326 "
      f"the framework applies to BGA, C4, TSV and microbump alike. The excess resistance `dR` "
      f"is length-independent to five decimal places while `K_crowd` is not, so `dR` is the "
      f"transferable quantity and `K_crowd` is an artifact of how much bulk conductor is "
      f"attached to the transition.")
    A("")
    A(f"![FIG-0M-C]({G}/FIG_0M_C_crowding_map.png)")
    A("")
    A("*FIG-0M-C. Current density through a TSV, its landing pad and the RDL trace.*")
    A("")
    A("## Intra-converter routing did not exist")
    A("")
    A(f"Of the three routing levels, the framework had two. Intra-converter metallization --- "
      f"the metal between the input pads, the switches, the flying capacitors, the inductors "
      f"and the output pads --- was absent entirely. It is worth **{min(ps):.2f} to "
      f"{max(ps):.2f} W** system-wide, {100*min(ps)/1000:.2f} to {100*max(ps)/1000:.2f} % of "
      f"the load, against a converter loss of 125.26 W. There is no double counting: the "
      f"upstream loss model contains every device and passive parasitic and no metallization "
      f"at all.")
    A("")
    A("It does not change the architecture ranking, because the converter cell is the same "
      "compiled design in Z1, Z2 and Z4 and the term is common-mode. What it does expose is a "
      "feasibility failure the framework could not see: **the VR output plane needs 8.6 times "
      "the available tile width** to stay inside the sourced copper current-density envelope "
      "at the reference 10 um single-layer RDL.")
    A("")
    A(f"![FIG-0M-D]({G}/FIG_0M_D_routing_graph.png)")
    A("")
    A("*FIG-0M-D. The intra-VR component-terminal graph and the three routing levels.*")
    A("")
    A("## Component partitioning was already assumed, and never checked")
    A("")
    A("`_compute_area` in the upstream converter sizing returns `max()` over the four "
      "component classes, not `sum()`. Four-layer vertical stacking is therefore already "
      "assumed --- by the area model and by nothing else. The electrical, thermal and "
      "mechanical models all place the VR as a single lumped block, and nothing verifies that "
      "the four layers exist in a given architecture.")
    A("")
    A("| template | levels | stack height | array footprint | fits the 500 mm2 die shadow |")
    A("|---|---|---|---|---|")
    for r in part:
        A(f"| `{r['template']}` | {r['n_levels']} | {fm(r['stack_height_um'], 0)} um | "
          f"{fm(r['area_all_cells_mm2'], 1)} mm2 | **{r['fits_die_shadow']}** "
          f"({fm(r['die_shadow_utilisation'], 2)}) |")
    A("")
    A("**A single-level VR misses the die shadow by 1.76x**, so vertical partitioning is a "
      "precondition rather than an optimization. Z2 and Z4 as three-level stacks are 8 % over "
      "and need a fourth level. `T4_SPLIT_SC_BUCK`, which splits by voltage domain, is the "
      "only two-level template that fits.")
    A("")
    A(f"![FIG-0M-E]({G}/FIG_0M_E_partition_templates.png)")
    A("")
    A("*FIG-0M-E. Component-partition templates against height and die-shadow area.*")
    A("")
    A("## Z5 re-audited: the number survives, the class conclusion does not")
    A("")
    A(f"Traced from rail voltage to `P = I^2 R`: **{fm(z5d[0]['P_loop_w'], 3)} W**, equivalent "
      f"loop resistance **{fm(z5d[0]['R_eq_mohm'], 5)} mOhm**, "
      f"{fm(z5d[0]['loop_squares'], 4)} loop squares on a "
      f"{fm(z5d[0]['sheet_R_loop_mohm_sq'], 4)} mOhm/sq stack, IR drop "
      f"{fm(z5d[0]['IR_drop_v'], 4)} V on a 1 V rail. Grid-converged to 0.15 %.")
    A("")
    A("It did not inherit PCB routing assumptions, and the check runs the other way: the PCB "
      "row of the same source table is **4.56 times more conductive per square** than the RDL "
      "row, because 152 um of copper at 50 % occupancy beats two 10 um layers at 83 %. Had Z5 "
      "used PCB geometry it would have reported about 169 W. No defect is logged.")
    A("")
    A("The CLASS conclusion does move. Feeding the same 1 V rail from four die edges cuts the "
      "lateral loss 4.5x; a 12 V lateral rail cuts it 144x. What is eliminated is the "
      "one-sided low-voltage lateral topology, not 2.5D. No lateral variant beats the "
      "vertical architectures, and at 48 V the family degenerates into vertical delivery "
      "under another name.")
    A("")
    A(f"![FIG-0M-F]({G}/FIG_0M_F_z5_decomposition.png)")
    A("")
    A("*FIG-0M-F. Z5: PCB against RDL per square, loss against gap, and the voltage family.*")
    A("")
    A("## Thermal homogenization, decided by explicit geometry")
    A("")
    A("Three candidate models disagreed by up to 80 % on the same TSV array, so the question "
      "was settled by finite volumes on explicit unit cells with a predeclared 10 % / 25 % "
      "acceptance band. The rule of mixtures is essentially exact along the vias; "
      "Maxwell-Garnett is conditional across them; and the pre-existing framework's "
      "transverse model is rejected at four of the five geometries and conditional at the fifth --- never accepted --- 19 to 74 % low, because it puts the liner in series with "
      "the copper when heat can flow around the via.")
    A("")
    A(f"The RDL is the most anisotropic layer in the package --- "
      f"**{fm(rdl[0]['anisotropy_kz_over_kxy'], 0) if rdl else '--'}x to "
      f"{fm(max(F(r, 'anisotropy_kz_over_kxy') for r in rdl), 0) if rdl else '--'}x** between "
      f"along-line and across-line conduction --- and the framework gives it one isotropic "
      f"value. A caveat the audit states itself: these cells are single-direction line layers; "
      f"a meshed plane is far less anisotropic.")
    A("")
    A(f"![FIG-0M-G]({G}/FIG_0M_G_k_tensors.png)")
    A("")
    A("*FIG-0M-G. Anisotropic effective conductivity, and which homogenization survives.*")
    A("")
    A("## Cooling: the largest single gap")
    A("")
    A("The Robin coefficient `h_top = 166 000 W/m2K` was inverse-calibrated to reach 84 C. "
      "Derived instead from channel geometry and flow with source-backed correlations, three "
      "things appear that the calibrated boundary hides.")
    A("")
    A("At the source's stated 1.6 g/s the coolant temperature rise for 1125 W of heat is "
      "**168 K**, which single-phase water cannot do; 26.9 g/s is needed for a 10 K rise. No "
      "laminar architecture reaches 166 kW/m2K --- the best gets 0.70x, and the calibrated "
      "value needs 50 g/s in the transitional regime, **74 W of pumping power, 7.4 % of the "
      "load**, and 1.46 MPa of pressure drop, none of which is charged anywhere. And because "
      "the sink is a single temperature, the boundary cannot produce a streamwise gradient.")
    A("")
    A(f"Imposing the real coolant rise on the same global model, changing nothing else, moves "
      f"the die warpage by up to **{fm(abs(F(cw, 'warpage_vs_uniform_pct')), 2) if cw else '--'} %** "
      f"and `T_max` by **{fm(abs(F(cw, 'Tmax_vs_uniform_K')), 1) if cw else '--'} K**. Cooling "
      f"mass flow is therefore a MECHANICAL design variable, and the uniform boundary sets "
      f"its effect to zero by construction.")
    A("")
    A(f"![FIG-0M-H]({G}/FIG_0M_H_cooling.png)")
    A("")
    A("*FIG-0M-H. What physical cooler stands behind one calibrated coefficient.*")
    A("")
    A("## Missing mechanics, measured where it could be")
    A("")
    A(f"Ten of twelve mechanisms are not modelled. Six are P1: {', '.join(p1)}. Two were "
      f"measured rather than classified by assertion.")
    A("")
    A(f"**Polymer stiffness.** Halving the organic board's modulus moves the Z1 corner shear "
      f"by about 12 % and the Z1/Z2 driver ratio by "
      f"{fm(polyw.get('ratio_shift_pct'), 2)} %, against a relative-life envelope that itself "
      f"spans 2.5 %. Underfill and TIM modulus move the ratio by less than 0.05 %. It is P1 "
      f"rather than P0 because the effect is common-mode: the ordering is untouched at every "
      f"modulus tried. What is not settled is the TIME dependence, and no DMA data for the "
      f"specific laminate exists here, so a Prony series cannot be fitted.")
    A("")
    if prat:
        A(f"**Assembly prestress.** With a reflow cool-down from 217 C prepended, the "
          f"stabilised-cycle Z1/Z2 strain ratio moves from "
          f"{fm(prat['d_peeq_per_cycle'], 4)} to {fm(prat['inelastic_work_MJ_per_m3'], 4)}, "
          f"a shift of {fm(prat['dpeeq_shift_pct'], 2)} %.")
        A("")
    A("**Rate-independent plasticity is not needed** and adding it to a unified viscoplastic "
      "law would double-count, because Anand and Norton both represent the total inelastic "
      "strain. **Moisture is out of scope**, declared rather than omitted: the publication "
      "claim is dry steady operating ETM. **Cohesive zones are not added**, because their "
      "traction-separation laws and fracture energies are not sourced and inventing them "
      "would put a fabricated parameter at the centre of a failure prediction.")
    A("")
    A("## The coupling matrix, with the size of every absent arrow")
    A("")
    A("| arrow | size | against | verdict |")
    A("|---|---|---|---|")
    A("| M to E, elastic geometry | 0.16 % on R | 22.8 % from rho(T), already modelled | "
      "**negligible, 137x smaller** |")
    A("| M to T, TIM bond line | 1.5 K at a 4 % change | 51 K junction rise | second order, "
      "2.9 % |")
    A("| M to E, contact pressure | zero | -- | not applicable; every interface is "
      "metallurgical |")
    A("| DAMAGE to E, cracked area | +33 % R at 25 % lost | 22.8 % | **material, once damage "
      "exists** |")
    A("| DAMAGE to T, delamination | +12.5 K at 25 % | 51 K | **material, once damage "
      "exists** |")
    A("| EM voiding to E | **OPEN** | -- | the current-density limit itself is unsourced |")
    A("")
    A("The framework is at **ETM-L1**, `E <-> T -> M`. That is sufficient for architecture "
      "ranking, because the absent arrows are 0.7 % and 2.9 % of terms already present and "
      "are common-mode across architectures. **ETM-L3** would be required to predict failure "
      "progression, and nothing in this project currently claims to.")
    A("")
    A(f"![FIG-0M-I]({G}/FIG_0M_I_coupling_matrix.png)")
    A("")
    A("*FIG-0M-I. Every coupling arrow, present and absent, with its measured magnitude.*")
    A("")
    A(f"![FIG-0M-J]({G}/FIG_0M_J_priority_ladder.png)")
    A("")
    A("*FIG-0M-J. The physics-priority ladder.*")
    A("")
    A("## Does any new dimension change the ranking?")
    A("")
    if sens:
        A("| TSV geometry | copper fraction | du Z1 | du Z2 | Z1/Z2 | ratio shift | "
          "die warpage Z1 |")
        A("|---|---|---|---|---|---|---|")
        for r in sens:
            A(f"| `{r['case']}` | {fm(r['f_cu'], 4)} | {fm(r['du_Z1_um'], 4)} | "
              f"{fm(r['du_Z2_um'], 4)} | {fm(r['du_ratio'], 4)} | "
              f"{fm(r['ratio_shift_pct'], 2)} % | **{fm(r['warp_Z1_shift_pct'], 2)} %** |")
        A("")
        A(f"The largest shift any interconnect-geometry change produces in the Z1/Z2 driver "
          f"ratio is **{fm(sw.get('ratio_shift_pct'), 2)} %** (`{sw.get('case')}`) --- "
          f"comparable to the whole width of the relative-life envelope, so not negligible, "
          f"but the ratio never approaches unity and the ORDER never changes. "
          f"**Interconnect geometry does not change the architecture ranking.**")
        A("")
        A(f"The ABSOLUTE mechanical response is a different matter. The same changes move the "
          f"die warpage by **{fm(min(float(r['warp_Z1_shift_pct']) for r in sens), 1)} % to "
          f"+{fm(max(float(r['warp_Z1_shift_pct']) for r in sens), 1)} %**, because the TSV "
          f"field's copper fraction sets the effective CTE and stiffness of the entire "
          f"through-substrate layer. That was invisible while the field was a frozen "
          f"homogenized block. The control case `d_x2_p_x2`, which doubles the diameter and "
          f"the pitch together and therefore holds the copper fraction constant, reproduces "
          f"the baseline to the last digit --- confirming that the mechanical model responds "
          f"to the copper FRACTION and not to the via.")
        A("")
    A("## Verdict and what follows")
    A("")
    A("Of the seven candidate verdicts, **G** is the only one the evidence supports as "
      "dominant. **A** fails because the model is not closed: the electromigration limit is "
      "open, no first-stage converter compiles below 48 V, meshed-plane RDL anisotropy is "
      "unvalidated and no cohesive parameters exist. **B** and **C** fail on measurement --- "
      "both change feasibility, neither changes order. **D** fails because the 768 W survives "
      "on interposer geometry and Phase 0I-R had already narrowed the class claim. **F** is "
      "contradicted by four separate results. **E** is TRUE and is the largest single "
      "instance of G rather than an alternative to it.")
    A("")
    A("The optimizer remains **FORBIDDEN**. Of its six preconditions, none is fully met after "
      "Phase 0M and two moved from NO to PARTIAL.")
    A("")
    A("<!-- END GENERATED: phase0m_narrative -->")
    return "\n".join(L) + "\n"


def main() -> int:
    s = REP.read_text()
    s = sub(s, "# Phase 0L-R --- Constitutive Robustness, Report Propagation and "
               "Auditor-Dossier Closure (current authoritative)",
            "# Phase 0L-R --- Constitutive Robustness, Report Propagation and "
            "Auditor-Dossier Closure (extended by Phase 0M)",
            "demote Phase 0L-R")
    s = place(s, "phase0m_narrative", narrative(),
              "\n<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    # re-splice EVERY generated current-facing block. The Phase-0M Part-0-A edit changed the
    # gate count inside `exec_summary`, which is GENERATED -- editing the report copy alone
    # left the report and its generator disagreeing (Sixteen against Seventeen), and the
    # build's own verbatim check caught it. The generator is the source; the report copy is
    # replaced from it, never edited.
    cfp = R / "results" / "phase0h" / "generated_current_facing.md"
    gen = cfp.read_text()
    for name in ("exec_summary", "governing_equations", "validation_status",
                 "publication_claims"):
        pat = rf"<!-- BEGIN GENERATED: {name} -->\n.*?<!-- END GENERATED: {name} -->\n"
        src = re.search(pat, gen, re.S)
        assert src, f"generator has no block {name}"
        assert re.search(pat, s, re.S), f"report has no block {name}"
        s = re.sub(pat, lambda _m, _t=src.group(0): _t, s, count=1, flags=re.S)
    print("  ok  4 generated current-facing blocks: re-spliced from the generator")

    # refresh the YAML-generated status block too: it is produced from the same file, so a
    # Phase-0M edit to the YAML must reach it. Phase 0H learned this the hard way.
    gsp = R / "results" / "phase0g" / "generated_status_sections.md"
    gs = gsp.read_text()
    start = s.index("<!-- GENERATED FROM results/CURRENT_SCIENTIFIC_STATUS.yaml")
    m = re.search(r"\n+\\newpage\n+# References", s[start:])
    assert m, "generated status block boundary not found"
    s = s[:start] + gs.rstrip("\n") + s[start + m.start():]
    print("  ok  generated status block: refreshed")
    REP.write_text(s)
    print(f"\nreport now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
