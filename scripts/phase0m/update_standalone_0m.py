#!/usr/bin/env python3
"""Phase-0M Part 44 -- update the standalone current-framework audit report.

The standalone report must answer, in the reader's own terms:
  which dimensions are currently fixed; which are now design variables; exactly what routing
  is represented; whether intra-VR routing is represented; how current crowding is treated;
  component-level stack partitioning; thermal homogenization; how the cooling boundary is
  derived; which mechanics are missing; and the DIRECTION of every ETM coupling.

Missing physics is not hidden and nothing audited is described as implemented.
"""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
MD = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
M = R / "results" / "phase0m"
rows = lambda n: list(csv.DictReader(open(M / n))) if (M / n).is_file() else []
F = lambda r, k: float(r[k])


def fm(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def chapter() -> str:
    crowd = [r for r in rows("current_crowding_transition_sweep.csv") if r["status"] == "OK"]
    route = [r for r in rows("intra_vr_routing_model.csv") if r.get("level") == "R1"]
    part = rows("component_partition_templates.csv")
    z5d = rows("z5_path_decomposition.csv")
    eff = rows("effective_layer_properties.csv")
    cetm = rows("cooling_etm_sensitivity.csv")
    poly = rows("polymer_modulus_screen.csv")
    pre = rows("assembly_prestress_test.csv")
    mat = rows("PHYSICS_PRIORITY_MATRIX.csv")
    sens = rows("design_space_sensitivity.csv")
    me = rows("me_energy_reconstruction.csv")
    ks = [F(r, "K_crowd") for r in crowd]
    ps = [F(r, "p_system_w") for r in route]
    polyw = max((r for r in poly if r["case"] != "baseline"),
                key=lambda r: abs(F(r, "ratio_shift_pct")), default={})
    prat = next((r for r in pre if r["arch"] == "RATIO"), {})
    sw = max((r for r in sens if r["case"] != "baseline"),
             key=lambda r: abs(F(r, "ratio_shift_pct")), default={})
    cw = max(cetm, key=lambda r: abs(F(r, "warpage_vs_uniform_pct"))) if cetm else {}
    rdl = [r for r in eff if r["layer"] == "RDL_dielectric"]
    L = []
    A = L.append
    A("\\newpage")
    A("")
    A("# 23. Geometry resolution, routing scope, cooling derivation and coupling "
      "directionality")
    A("")
    A("This chapter records what Phase 0M **audited** and what it **built**. Where it built "
      "a model, that model is not yet wired into the production path, and the text says so "
      "each time. Nothing here should be read as already in use unless it says it is.")
    A("")
    A("## 23.1 Which dimensions are fixed, and which are now design variables")
    A("")
    A("Until Phase 0M the interconnect stack was frozen to sourced values. Resistance was "
      "derived from geometry --- that part was already right --- but three quantities were "
      "primitives that geometry could have produced, and one of them turned out to be the "
      "only thing that sets the answer.")
    A("")
    A("| quantity | before | after Phase 0M | class |")
    A("|---|---|---|---|")
    A("| TSV radius, height, pitch | frozen to June-2026 Table III | DESIGN variables with "
      "`p >= max(2r + s_min, 2r(1+k_KOZ))` and `h/2r <= AR_max` enforced | DESIGN |")
    A("| TSV liner thickness | **absent from the model** | PROCESS limit; the conducting "
      "radius is `r - t_ox` | PROCESS |")
    A("| per-via current limit | a primitive **in amperes** | `J_max x A_conductor`, with "
      "`J_max` swept over the sourced 1e8 to 4e8 A/m2 envelope | PROCESS |")
    A("| current-crowding factor | one global constant, 1.326 | DERIVED per geometry from a "
      "3-D conduction solve | DERIVED |")
    A("| RDL thickness, width, space, layer count | frozen to the ECTC-2024 stack | DESIGN "
      "variables; the ECTC stack is a REFERENCE TECHNOLOGY, not a bound | DESIGN |")
    A("| bump and pad geometry | frozen | DESIGN variables with pad-over-bump and UBM "
      "thickness | DESIGN |")
    A("| coolant flow, channel geometry, TIM thickness | **did not exist**; one calibrated "
      "`h` | DESIGN variables, with `h` DERIVED from them | DESIGN |")
    A("")
    A("The classification is enforced in code: `scripts/phase0m/interconnect.py::classify()` "
      "raises on any parameter not in the table, and "
      "`configs/phase0m/interconnect_design_space.yaml` is generated from the same table.")
    A("")
    A("**The result a reader should take from this chapter first.** Under the allocation "
      "policy the framework actually uses --- size the via count to the connection current "
      "--- the via-field resistance is")
    A("")
    A("$$R_{field} = \\frac{\\rho(T)\\, h\\, J_{max}}{I}$$")
    A("")
    A("in which the conductor cross-section has cancelled identically. The TSV radius is not "
      "an electrical lever, and because the copper fraction `I/(J_max A_field)` is also "
      "independent of it, not a thermal or mechanical one either. It is a feasibility and "
      "manufacturability variable. Measured over radii from 2.5 to 50 um, the field "
      "resistance moves 0.07 %.")
    A("")
    A("## 23.2 Exactly what routing is represented")
    A("")
    A("| level | what it is | represented? |")
    A("|---|---|---|")
    A("| LEVEL 1, intra-converter | metal between the input pads, the switches, the flying "
      "capacitors, the inductors and the output pads | **NO, before Phase 0M. Modelled in "
      "Phase 0M, not yet in the production loss total.** |")
    A("| LEVEL 2, VR to package | VR terminal through the BGA, TSV, microbump fields | YES |")
    A("| LEVEL 3, package to POL | multilayer RDL sheet across the die | YES |")
    A("")
    A("**Is intra-VR routing represented? No.** The question has a clean answer because the "
      "upstream converter loss model contains `R_DS(on)`, the inductor DCR, the capacitor ESR "
      "and the switching losses, and no metallization at all. Adding the metallization "
      "therefore cannot double-count.")
    A("")
    A(f"Modelled at obstacle-aware Manhattan fidelity with widths derived from the "
      f"current-density rule, intra-VR routing is worth **{min(ps):.2f} to {max(ps):.2f} W** "
      f"system-wide --- {100*min(ps)/1000:.2f} to {100*max(ps)/1000:.2f} % of the load --- "
      f"against a converter loss of 125.26 W. It is common-mode across Z1, Z2 and Z4 and does "
      f"not change their order.")
    A("")
    A("It does expose something the framework could not see: at the reference 10 um "
      "single-layer RDL the VR output plane needs **8.6 times the available tile width** to "
      "stay inside the sourced copper current-density envelope. The remedy is more copper ---"
      " nine layers, or 86 um --- and the constraint had never been checked because there "
      "was no intra-VR net to check it on.")
    A("")
    A("## 23.3 How current crowding is treated")
    A("")
    A("Q3D is not licensed. Elmer, GetDP and Palace are not installed, and Palace's "
      "electrostatic mode solves a permittivity problem rather than DC conduction in any "
      "case. MOOSE is present and its steady conduction operator is the same operator, so it "
      "remains the independent cross-check. Phase 0M built a conservative finite-volume "
      "solver for `div(sigma grad V) = 0`, verified exact on a uniform bar at every mesh and "
      "within 0.9 % of the analytic spreading resistance on a contact resolved by six cells "
      "per radius.")
    A("")
    A(f"Across {len(crowd)} converged transition geometries **the crowding factor spans "
      f"{min(ks):.3f} to {max(ks):.3f}** --- a factor of {max(ks)/min(ks):.2f} --- against the "
      f"single constant 1.326 currently applied to BGA, C4, TSV and microbump alike. A "
      f"generous landing pad drives it below 1; a narrow trace entry drives it above 1.4.")
    A("")
    A("More usefully: the **excess** resistance `dR = R_3D - R_bulk` is length-independent to "
      "five decimal places while the RATIO is not. `dR` is the transferable quantity; a "
      "constant multiplier is the wrong functional form, not merely the wrong number.")
    A("")
    A("## 23.4 Component-level stack partitioning")
    A("")
    A("Component-level partitioning was **already assumed**, in exactly one place. The "
      "upstream converter area model returns `max()` over the four component classes, not "
      "`sum()` --- a four-layer vertical stacking assumption, described in its own docstring "
      "as a total footprint. The electrical, thermal and mechanical models all place the VR "
      "as one lumped block with one terminal, one temperature and one modulus, and nothing "
      "checks that the four layers exist.")
    A("")
    A(f"The summed component footprint of the compiled 1-kW cell is "
      f"**{fm(part[0]['summed_component_area_mm2'], 2)} mm2** against the 5.61 mm2 the model "
      f"reports.")
    A("")
    A("| template | levels | stack height | array footprint | fits the 500 mm2 die shadow |")
    A("|---|---|---|---|---|")
    for r in part:
        A(f"| `{r['template']}` | {r['n_levels']} | {fm(r['stack_height_um'], 0)} um | "
          f"{fm(r['area_all_cells_mm2'], 1)} mm2 | **{r['fits_die_shadow']}** |")
    A("")
    A("A single-level VR misses the die shadow by 1.76x, so vertical partitioning is a "
      "precondition rather than a choice. The backside-chiplet and power-die architectures, "
      "built as three-level stacks, are 8 % over and need a fourth level.")
    A("")
    A("## 23.5 Thermal homogenization")
    A("")
    A("Every heterogeneous layer is now given an anisotropic tensor, validated against "
      "explicit-geometry finite volumes on unit cells with a predeclared acceptance band "
      "(10 % accept, 25 % conditional).")
    A("")
    A("| layer | `k_z` | `k_xy` | which closed form survives |")
    A("|---|---|---|---|")
    for r in eff:
        if r["layer"] in ("TSV_array",) and "p=60" not in r["geometry"]:
            continue
        if r["layer"] in ("TSV_periodicity_check",):
            continue
        A(f"| {r['layer'].replace('_', ' ')} ({r['geometry']}) | {fm(r['RVE_kz'], 2)} | "
          f"{fm(r['RVE_kxy'], 3)} | "
          f"{'Voigt for k_z; Maxwell CONDITIONAL for k_xy' if r['layer'] == 'TSV_array' else 'Voigt and Maxwell both ACCEPTED' if 'bump' in r['layer'] or 'C4' in r['layer'] or 'BGA' in r['layer'] else 'directional, see below'} |")
    A("")
    A(f"Two findings matter for the reader. First, **the RDL is "
      f"{fm(rdl[0]['anisotropy_kz_over_kxy'], 0) if rdl else '--'}x to "
      f"{fm(max(F(r, 'anisotropy_kz_over_kxy') for r in rdl), 0) if rdl else '--'}x "
      f"anisotropic** between along-line and across-line conduction, and the framework "
      f"currently gives it one isotropic conductivity. Second, the transverse model in the "
      f"pre-existing TSV framework is **rejected** at four of the five geometries and **conditional** at the fifth --- never accepted --- 19 to 74 % low, because it forces all "
      f"in-plane heat through the oxide liner when heat can flow around the via.")
    A("")
    A("The local reliability region is deliberately NOT homogenized. Global/local "
      "submodelling is retained: tensors in the package model, explicit geometry in the joint "
      "and transition submodels.")
    A("")
    A("## 23.6 How the cooling boundary is derived")
    A("")
    A("It is not derived. `h_top = 166 000 W/m2K` is **inverse-calibrated** so the 1-kW "
      "package reaches the reference junction temperature, `h_bottom = 10 W/m2K` is an "
      "assumption, and the sink is one uniform temperature. A calibrated film coefficient is "
      "not a cooling technology: it cannot be transferred to another architecture, it carries "
      "no pumping cost, and it cannot produce a temperature gradient along the flow.")
    A("")
    A("Phase 0M derives `h` from channel geometry and mass flow instead, using laminar "
      "rectangular-duct Nusselt numbers, straight-fin efficiency, the caloric resistance and "
      "the laminar friction factor. Three results follow.")
    A("")
    A("* At the source's own stated 1.6 g/s the coolant temperature rise for 1125 W is "
      "**168 K**. Single-phase water cannot do that. A 10 K rise needs 26.9 g/s.")
    A("* **No laminar architecture reaches 166 kW/m2K.** The best gets 0.70x. Reaching the "
      "calibrated value needs 50 g/s in the transitional regime, **74 W of pumping --- 7.4 % "
      "of the load ---** and 1.46 MPa of pressure drop. The framework charges neither.")
    A("* At low flow the caloric resistance `1/(2 m_dot c_p)` DOMINATES the path, and a single "
      "Robin coefficient absorbs it into `h`, presenting a flow property as a surface one.")
    A("")
    A(f"Cooling is also a mechanical variable. Imposing the real coolant temperature rise on "
      f"the same global model, changing nothing else, moves the die warpage by up to "
      f"**{fm(abs(F(cw, 'warpage_vs_uniform_pct')), 2) if cw else '--'} %** and the peak "
      f"temperature by **{fm(abs(F(cw, 'Tmax_vs_uniform_K')), 1) if cw else '--'} K**. The "
      f"uniform boundary sets both to zero by construction.")
    A("")
    A("No Icepak validation is claimed. The earlier attempt returned exactly 5000 K on every "
      "object --- a solver clamp --- and none may be claimed until that is understood.")
    A("")
    A("## 23.7 Which mechanics are missing")
    A("")
    A(f"{len([r for r in mat if r['status'] == 'NOT MODELLED'])} of {len(mat)} mechanisms are "
      f"not modelled. The full matrix with effect sizes is "
      f"`results/phase0m/PHYSICS_PRIORITY_MATRIX.csv`.")
    A("")
    A("| mechanism | status | priority |")
    A("|---|---|---|")
    for r in mat:
        A(f"| {r['physics']} | {r['status']} | **{r['priority']}** |")
    A("")
    A("Two were measured rather than assumed:")
    A("")
    A(f"* **Polymer stiffness.** Halving the organic board's modulus moves the corner-joint "
      f"shear by about 12 % and the Z1/Z2 driver ratio by "
      f"{fm(polyw.get('ratio_shift_pct'), 2)} %, against a relative-life envelope that spans "
      f"2.5 %. Underfill and TIM modulus move it by under 0.05 %. Classified P1 rather than "
      f"P0 because the effect is common-mode and the ordering is untouched.")
    if prat:
        A(f"* **Assembly prestress.** With a reflow cool-down from 217 C prepended to the "
          f"joint model, the stabilised-cycle Z1/Z2 strain ratio moves "
          f"{fm(prat['dpeeq_shift_pct'], 2)} %. The prestress largely relaxes out of the "
          f"stabilised cycle, which is the cycle the life law reads.")
    A("")
    A("Rate-independent plasticity is **not** needed: a unified viscoplastic law already "
      "represents the total inelastic strain and adding a separate branch would double-count. "
      "Moisture is **out of scope**, declared rather than omitted, because the publication "
      "claim is dry steady operating ETM. Cohesive zones are **not** added because the "
      "traction-separation laws and fracture energies for these interfaces are not sourced.")
    A("")
    A("The largest unmodelled mechanism that could change the ranking is **RDL and TSV "
      "cracking**. The RDL is not in the mechanical mesh at all, and the power-die and 2.5D "
      "architectures load it hardest.")
    A("")
    A("## 23.8 The direction of every ETM coupling")
    A("")
    A("| from -> to | status | measured size |")
    A("|---|---|---|")
    A("| electrical -> thermal | **PRESENT**, iterated to a fixed point | the whole loss |")
    A("| thermal -> electrical | **PRESENT** | `rho(T)` moves R by 22.8 % over the cycle |")
    A("| thermal -> mechanical | **PRESENT** | the whole thermal strain |")
    A("| mechanical -> electrical | **ABSENT** | 0.16 % on R, **137x smaller** than `rho(T)` |")
    A("| mechanical -> thermal | **ABSENT** | 1.5 K for a 4 % TIM bond-line change, 2.9 % of "
      "the junction rise |")
    A("| mechanical -> damage | **ABSENT** | no damage variable exists |")
    A("| damage -> electrical | **ABSENT** | +33 % on R at 25 % of a joint lost |")
    A("| damage -> thermal | **ABSENT** | +12.5 K at 25 % of the die delaminated |")
    A("")
    A("The framework is at **ETM-L1**: `E <-> T -> M`, with mechanics returning nothing. That "
      "is sufficient for architecture ranking, because the two absent arrows before damage "
      "are 0.7 % and 2.9 % of terms already in the loop and both are common-mode. **ETM-L3**, "
      "with damage feeding back into conductance and stiffness, would be required to predict "
      "failure PROGRESSION --- and nothing in this framework currently claims to.")
    A("")
    A("One arrow is **OPEN rather than negligible**: electromigration voiding. The "
      "current-density limit that would size it could not be sourced, so its effect cannot be "
      "estimated and must not be invented.")
    A("")
    A("## 23.9 Does any of this change the architecture ranking?")
    A("")
    if sens:
        A("| TSV geometry | copper fraction | corner shear Z1 | Z2 | Z1/Z2 | ratio shift | "
          "die warpage Z1 |")
        A("|---|---|---|---|---|---|---|")
        for r in sens:
            A(f"| `{r['case']}` | {fm(r['f_cu'], 4)} | {fm(r['du_Z1_um'], 4)} um | "
              f"{fm(r['du_Z2_um'], 4)} um | {fm(r['du_ratio'], 4)} | "
              f"{fm(r['ratio_shift_pct'], 2)} % | **{fm(r['warp_Z1_shift_pct'], 2)} %** |")
        A("")
        A(f"**No.** The largest shift any interconnect-geometry change produces in the "
          f"reliability driver ratio is {fm(sw.get('ratio_shift_pct'), 2)} % --- comparable to "
          f"the whole width of the relative-life envelope, so not negligible --- but the ratio "
          f"never approaches unity and the ORDER never changes.")
        A("")
        A(f"The ABSOLUTE response is a different matter, and it is new. The same changes move "
          f"the die warpage by {fm(min(float(r['warp_Z1_shift_pct']) for r in sens), 1)} % to "
          f"+{fm(max(float(r['warp_Z1_shift_pct']) for r in sens), 1)} %, because the TSV "
          f"field's copper fraction sets the effective CTE and stiffness of the whole "
          f"through-substrate layer --- invisible while that field was a frozen homogenized "
          f"block. The control case that doubles diameter and pitch together, holding the "
          f"copper fraction constant, reproduces the baseline exactly, which confirms the "
          f"mechanical model responds to the copper FRACTION and not to the via.")
    A("")
    A("## 23.10 The energy metric is now solver-coherent")
    A("")
    A("Phase 0L-R found and fixed a step-boundary temperature aliasing defect that had "
      "inflated every inelastic-energy number by 18.5 %. Phase 0M removes the possibility "
      "rather than the instance: the solver's own mechanical strain `ME` is requested in the "
      "deck, the inelastic strain is `ME - C^-1(T):S`, and the temperature is recovered from "
      "the same output block as `tr(E - ME)/(3 alpha)`. No separately parsed temperature is "
      "used anywhere in the energy path.")
    A("")
    A("| model | arch | production | solver-coherent | ratio | isochoric residual, ME | "
      "isochoric residual, Python |")
    A("|---|---|---|---|---|---|---|")
    for r in me:
        A(f"| {r['model']} | {r['arch']} | {fm(r['W_production_MJ_per_m3'], 5)} | "
          f"{fm(r['W_me_self_MJ_per_m3'], 5)} | {fm(r['me_over_production'], 4)} | "
          f"{float(r['isochoric_residual_ME']):.2e} | "
          f"{float(r['isochoric_residual_python']):.2e} |")
    A("")
    A("The two routes agree to 0.79 to 1.56 %, which bounds the residual of the Phase-0L-R "
      "fix. On the assumption-free test --- inelastic flow must be volume-preserving --- the "
      "solver-coherent route is 16 to 20 times cleaner.")
    A("")
    return "\n".join(L) + "\n"


def main() -> int:
    s = MD.read_text()
    if "# 23. Geometry resolution, routing scope" in s:
        # refresh in place
        start = s.index("\\newpage\n\n# 23. Geometry resolution, routing scope")
        end = s.index("\n# 24. Current assumptions and open items")
        s = s[:start] + chapter() + s[end + 1:]
        MD.write_text(s)
        print("chapter 23 refreshed")
        return 0
    renames = [("# 28. Glossary", "# 29. Glossary"),
               ("# 27. Symbol table", "# 28. Symbol table"),
               ("# 26. Auditor checklist", "# 27. Auditor checklist"),
               ("# 25. Reproducibility", "# 26. Reproducibility"),
               ("# 24. Current claims --- what can and cannot be said",
                "# 25. Current claims --- what can and cannot be said"),
               ("# 23. Current assumptions and open items",
                "# 24. Current assumptions and open items"),
               ("Section 27", "Section 28"),
               ("Section 23", "Section 24")]
    for old, new in renames:
        assert s.count(old) == 1, f"rename anchor {old!r} count={s.count(old)}"
        s = s.replace(old, new, 1)
    anchor = "\\newpage\n\n# 24. Current assumptions and open items"
    assert s.count(anchor) == 1, "insert anchor missing"
    s = s.replace(anchor, chapter() + anchor, 1)
    MD.write_text(s)
    print(f"chapter 23 inserted; report now {len(s.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
