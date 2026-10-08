#!/usr/bin/env python3
"""Phase-0M -- the top-level gate document, assembled from every result file."""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def f(x, d=4):
    try:
        return f"{float(x):.{d}f}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def g(x, d=4):
    try:
        return f"{float(x):.{d}g}"
    except (TypeError, ValueError):
        return str(x) if x not in (None, "") else "--"


def main() -> int:
    me = rd("me_energy_reconstruction.csv")
    prov = rd("specimen_count_provenance.csv")
    tsv = rd("tsv_geometry_sensitivity.csv")
    crowd = [r for r in rd("current_crowding_transition_sweep.csv") if r["status"] == "OK"]
    route = [r for r in rd("intra_vr_routing_model.csv") if r.get("level") == "R1"]
    part = rd("component_partition_templates.csv")
    z5 = rd("z5_architecture_comparison.csv")
    z5d = rd("z5_path_decomposition.csv")
    eff = rd("effective_layer_properties.csv")
    cool = rd("cooling_architecture_sensitivity.csv")
    cetm = rd("cooling_etm_sensitivity.csv")
    poly = rd("polymer_modulus_screen.csv")
    pre = rd("assembly_prestress_test.csv")
    fb = rd("etm_feedback_magnitudes.csv")
    mat = rd("PHYSICS_PRIORITY_MATRIX.csv")
    sens = rd("design_space_sensitivity.csv")

    ks = [float(r["K_crowd"]) for r in crowd]
    ps = [float(r["p_system_w"]) for r in route]
    m1z1 = next((r for r in me if r["model"] == "M1" and r["arch"] == "Z1"), None)
    m1z2 = next((r for r in me if r["model"] == "M1" and r["arch"] == "Z2"), None)
    polyw = max((r for r in poly if r["case"] != "baseline"),
                key=lambda r: abs(float(r["ratio_shift_pct"])), default=None)
    prat = next((r for r in pre if r["arch"] == "RATIO"), None)
    sw = max((r for r in sens if r["case"] != "baseline"),
             key=lambda r: abs(float(r["ratio_shift_pct"])), default=None) if sens else None
    cw = max(cetm, key=lambda r: abs(float(r["warpage_vs_uniform_pct"]))) if cetm else None
    p0 = [r for r in mat if r["priority"] == "P0"]
    p1 = [r for r in mat if r["priority"] == "P1"]

    md = f"""# PHASE 0M --- GEOMETRY-RESOLVED POWER DELIVERY, COMPONENT-LEVEL ARCHITECTURE, COOLING AND ETM-COUPLING AUDIT

**Verdict: G --- MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER; OPTIMIZATION STILL PREMATURE.**

Phase 0M is an audit and model-generalization gate. It did not build the optimizer, did not
run an architecture DOE, and did not implement physics merely because it exists.

---

## 0. Residual Phase-0L-R closure

### 0-A/B  Stale current-facing language

`method` in the executive summary claimed "Eleven sequential falsification gates (0B-0I plus
the 0D-R and 0I-R audit gates)". There have been sixteen. Corrected. The `next_gate` block
still named Phase 0L as next; replaced.

### 0-C  Anand wording

Replaced everywhere with the precise statement: **two constitutive families can currently be
PARAMETERIZED in the relevant regime, and only one can presently be INTEGRATED through the
production package solve.** The historical report previously said both at once --- section 116
had it right and the gate quote in the Phase-0L-R chapter had "parameterised AND integrated"
for two families, which contradicted the integrability ceiling three paragraphs above it.

### 0-D  Specimen-count provenance

One authoritative table, `SPECIMEN_COUNT_PROVENANCE.md`:

| phase | n/cell | packages | status | model | D |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['phase']} | **{r['n_per_cell']}** | **{r['packages']}** | {r['status']} | `{r['model']}` | {f(r['D'], 4)} |" for r in prov)}

### 0-E  Theorem-like wording

"any monotone solder law MUST rank Z1 worse" is withdrawn from both reports, the status YAML
and the two generators that produce them. The licensed wording is: *the global package
supplies a constitutive-law-independent deformation driver favoring Z2, and every presently
testable constitutive/life-law combination preserves that ordering.*

### 0-F  DEFECT #46 eliminated at the root

CalculiX `ME` (mechanical strain = total minus thermal) is now requested in the deck and the
inelastic strain is reconstructed as `eps_in = ME - C^-1(T):S`, with the temperature itself
recovered from the SAME output block via `tr(E - ME) = 3 alpha (T - T_zero)`. **No separately
parsed temperature block is used anywhere in the energy path**, so the class of error cannot
recur.

| model | arch | W production | W solver-coherent | ratio | isochoric residual, ME | isochoric residual, Python |
|---|---|---|---|---|---|---|
{chr(10).join(f"| {r['model']} | {r['arch']} | {f(r['W_production_MJ_per_m3'], 5)} | {f(r['W_me_self_MJ_per_m3'], 5)} | {f(r['me_over_production'], 4)} | {g(r['isochoric_residual_ME'], 3)} | {g(r['isochoric_residual_python'], 3)} |" for r in me)}

The DEFECT-#46-fixed production route agrees with the solver-coherent route to
**0.79 to 1.56 %**, so the Phase-0L-R fix was correct and its residual is now bounded. The
assumption-free check --- inelastic flow must be isochoric --- is **16 to 20 times cleaner**
on the ME route.

Decision-relevant Z1/Z2 energy, recomputed: Z1 {f(m1z1['W_me_self_MJ_per_m3'], 5) if m1z1 else '--'},
Z2 {f(m1z2['W_me_self_MJ_per_m3'], 5) if m1z2 else '--'} MJ/m3, ratio
**{f(float(m1z1['W_me_self_MJ_per_m3'])/float(m1z2['W_me_self_MJ_per_m3']), 4) if m1z1 and m1z2 else '--'}**.

---

## 1-4. Interconnect geometry: nothing derivable stays primitive

Every TSV, C4, bump, microbump, pad and RDL parameter is classified MATERIAL / PROCESS /
DESIGN / DERIVED, and `classify()` raises on anything unclassified
(`INTERCONNECT_PARAMETER_CLASSIFICATION.md`, `configs/phase0m/interconnect_design_space.yaml`).

Three primitives are removed and logged as defects: **#47** the per-via current in amperes,
**#48** the single global crowding multiplier 1.326, **#49** the missing TSV liner.

### The TSV radius law --- the publication-relevant result

The user hypothesis was *"increasing TSV radius decreases ohmic loss but decreases density"*.
True for one via. For a FIELD it depends entirely on the allocation policy:

| policy | R_field | measured spread, r = 2.5 to 50 um |
|---|---|---|
{chr(10).join(f"| `{p}` | {d} | {s} |" for p, d, s in (("A_min_capability", "`rho h J_max / I` --- **the conductor cross-section cancels identically**", "**0.07 %**"), ("B_fixed_count", "`~ 1/r^2`", "314 %"), ("C/D fixed pitch, additive spacing", "`(2 + s_min/r)^2`, decreasing and saturating", "4.9 %"), ("C/D fixed pitch, proportional keep-out", "`4 (1+k_KOZ)^2` --- **cancels again**", "--"), ("E_fixed_cu_fraction", "`rho h / (phi A_field)` --- **cancels identically**", "0.02 %")))}

Under minimum-capability provisioning the radius is **not an electrical, thermal or
mechanical lever at all**: `phi_Cu = I / (J_max A_field)` contains neither the radius nor the
height, so `k_eff`, `E_eff` and `CTE_eff` do not move either. Three further corollaries:
`IR_drop = rho h J_max` is independent of the CURRENT; `P = I rho h J_max` is LINEAR in
current, not quadratic; and **derating harder --- a LOWER `J_max` --- lowers the loss**.

What the radius does change is FEASIBILITY: `I (2 + s_min/r)^2 / (J_max pi A_f f) <= 1` is
monotone decreasing in `r`, and the aspect ratio `h/2r` improves.

---

## 5. The pre-existing TSV electrothermal framework: FOUND

`/home/beams0/MGHARIB/Model/TSVs_Framework_MultiGND_new_3_HSPICE.py`, sha256 `eaf21b1f...`,
wrapped rather than reimplemented (`TSV_FRAMEWORK_INTERFACE.md`). Its DC resistance matches
this project's independent model exactly and its skin-effect solution reproduces the
Phase-0E note (`delta/r = 4.41` at 1 MHz) to three figures. Its HFSS validation record shows
0.42 % mean relative error on insertion loss over 786 samples.

Its transverse thermal model is **rejected** by the Part-21 RVEs (19 to 74 % low). Its
`k_z`, its RLGC layer and its loop inductance are used. The trained ML surrogate is
deliberately NOT used: it was fitted on GHz signal-integrity data and has no established
validity for a DC power via field.

---

## 6-8. Current crowding: a derived function, not a constant

No DC conduction solver was installed (Elmer, GetDP, Palace all absent; Palace's
electrostatic mode is a permittivity solver and is not one in any case). A conservative
finite-volume solver was built and verified: **exact** on a uniform bar at every mesh,
and converging to `rho/(4a)` within **0.9 %** on a circular contact resolved by 6 cells per
radius.

**`K_crowd` spans {f(min(ks), 3)} to {f(max(ks), 3)} over {len(crowd)} converged geometries**
--- a factor of {f(max(ks)/min(ks), 2)} --- against the single constant 1.326 applied to BGA,
C4, TSV and microbump alike. More usefully: the EXCESS resistance `dR` is length-independent
to five decimal places while `K_crowd` is not, so **`dR` is the transferable quantity**.

---

## 9-13. Routing: one of three levels was missing entirely

| level | status before Phase 0M |
|---|---|
| LEVEL 1 intra-converter | **ABSENT** |
| LEVEL 2 VR to package | present |
| LEVEL 3 package to POL | present |

Level 1 adds **{f(min(ps), 2)} to {f(max(ps), 2)} W** system-wide
({f(100*min(ps)/1000, 2)} to {f(100*max(ps)/1000, 2)} % of the load) depending on the RDL
stack and via policy, against a converter loss of 125.3 W. No double counting: the upstream
loss model contains every device and passive parasitic and no metallization.

The binding constraint is not resistance but current density: **the VR output plane needs
8.6x the available tile width** to stay inside the sourced copper envelope at the reference
10 um single-layer RDL.

---

## 14-16. Component partition: already assumed, never checked

`HVR_FULL_OPT_EPC_V2::_compute_area` returns `max()` over the four component classes, not
`sum()`. Four-layer vertical stacking is therefore **already assumed by the converter area
model and by nothing else**; the summed component footprint is
{f(part[0]['summed_component_area_mm2'], 2)} mm2 against the 5.61 mm2 the model reports,
{f(float(part[0]['summed_component_area_mm2'])/5.61, 2)}x.

| template | levels | height | array footprint | fits the 500 mm2 die shadow |
|---|---|---|---|---|
{chr(10).join(f"| `{r['template']}` | {r['n_levels']} | {f(r['stack_height_um'], 0)} um | {f(r['area_all_cells_mm2'], 1)} mm2 | **{r['fits_die_shadow']}** ({f(r['die_shadow_utilisation'], 2)}) |" for r in part)}

**A single-level VR misses by 1.76x. Vertical partitioning is a precondition, not an
optimization.** Z2 and Z4 as three-level stacks are 8 % over. `T4_SPLIT_SC_BUCK` --- split by
voltage domain --- is the only two-level template that fits.

---

## 17-19. Z5: the number survives, the class conclusion does not

**`P = {f(z5d[0]['P_loop_w'], 3)} W`, `R_eq = {f(z5d[0]['R_eq_mohm'], 5)} mOhm`,
{f(z5d[0]['loop_squares'], 4)} loop squares, IR drop {f(z5d[0]['IR_drop_v'], 4)} V on a 1 V
rail.** Grid-converged to 0.15 %.

**It did NOT inherit PCB routing --- the reverse.** The PCB row is **4.56x MORE conductive per
square** than the RDL row (0.5616 against 2.5611 mOhm/sq loop), because 152 um of copper at
50 % occupancy beats 2 x 10 um at 83 %. Had Z5 inherited PCB geometry it would have reported
about 169 W. **No defect logged.**

But the CLASS conclusion moves: feeding the same 1 V rail from four die edges cuts the
lateral loss **4.5x**, and a 12 V lateral rail cuts it **144x**. No lateral variant beats the
vertical architectures, and at 48 V the family degenerates into vertical delivery by another
name.

---

## 20-22. Thermal homogenization: one model accepted, one rejected

| quantity | closed form | verdict against the RVE |
|---|---|---|
| `k_z`, all layers | Voigt / rule of mixtures | **ACCEPTED**, better than 1 % |
| `k_xy`, bump layers | Maxwell-Garnett | **ACCEPTED**, better than 0.5 % |
| `k_xy`, TSV arrays | Maxwell-Garnett | **CONDITIONAL**, 11 to 39 % high |
| `k_xy`, TSV arrays | the pre-existing framework | **REJECTED** at four of five geometries, CONDITIONAL at the fifth, never ACCEPTED; 19 to 74 % low |

The RDL is **153x to 276x anisotropic** and is currently given one isotropic conductivity.
At fixed copper fraction, a smaller via is thermally worse in plane, because the liner
fraction scales as `t_ox/r`.

The local reliability region is NOT homogenized; global/local submodelling is retained.

---

## 23-26. Cooling: the largest single gap

* At the source's stated 1.6 g/s the coolant temperature rise is **168 K**. The flow needed
  for 10 K is 26.9 g/s, **16.8x** the stated value.
* **No laminar architecture reaches h = 166 000 W/m2K.** Reaching it needs 50 g/s in the
  transitional regime, **74 W of pumping --- 7.4 % of the load --- and 1.46 MPa**. The
  framework charges neither.
* The caloric resistance `1/(2 m_dot c_p)` DOMINATES the path at low flow and a single Robin
  coefficient absorbs it into `h`, making it look like a surface property.
* A real coolant temperature rise moves the die warpage by up to
  **{f(cw['warpage_vs_uniform_pct'], 2) if cw else '--'} %** and `T_max` by
  **{f(cw['Tmax_vs_uniform_K'], 1) if cw else '--'} K**; the uniform boundary sets both to zero.

---

## 27-33. Missing mechanics

{len([r for r in mat if r['status'] == 'NOT MODELLED'])} of {len(mat)} mechanisms are NOT MODELLED.
P0: {', '.join(r['physics'] for r in p0) or 'none'}. P1: {', '.join(r['physics'] for r in p1)}.

Measured here, not asserted:

* **Board stiffness is first order on the driver.** Halving the board modulus moves the Z1
  corner shear by about 12 % and the Z1/Z2 ratio by
  {f(polyw['ratio_shift_pct'], 2) if polyw else '--'} %, against a relative-life envelope that
  spans 2.5 %. Underfill and TIM modulus move the ratio by less than 0.05 %.
* **Assembly prestress** {"moves the Z1/Z2 strain ratio by " + f(prat['dpeeq_shift_pct'], 2) + " %." if prat else "was tested; see MISSING_MECHANICS_PHYSICS_AUDIT.md."}
* **Rate-independent plasticity is not needed** and adding it to a unified law would
  double-count.
* **Moisture is out of scope**, declared, not omitted.
* **Cohesive zones are not added** because their material parameters are not sourced.

---

## 34-37. ETM coupling

**Current level: ETM-L1** (`E <-> T -> M`). Every absent arrow has a number:

| arrow | size | against | verdict |
|---|---|---|---|
| M -> E, elastic geometry | 0.16 % on R | 22.8 % from `rho(T)`, already modelled | **NEGLIGIBLE, 137x smaller** |
| M -> T, TIM bond line | 1.5 K at 4 % | 51 K junction rise | second order, 2.9 % |
| M -> E, contact pressure | zero | -- | not applicable, all interfaces bonded |
| DAMAGE -> E, cracked area | +33 % R at 25 % | 22.8 % | **material, once damage exists** |
| DAMAGE -> T, delamination | +12.5 K at 25 % | 51 K | **material, once damage exists** |
| EM voiding -> E | **OPEN** | -- | the EM limit itself is unsourced |

**Retain one-way mechanics.** ETM-L1 is sufficient for ranking; ETM-L3 is required for
failure progression and for nothing else this project currently claims.

---

## 39. Focused sensitivities --- does any new dimension change the RANKING?

{("| TSV geometry case | f_Cu | du Z1 | du Z2 | Z1/Z2 ratio | ratio shift | die warpage Z1 | T_max shift |" + chr(10) + "|---|---|---|---|---|---|---|---|" + chr(10) + chr(10).join(f"| `{r['case']}` | {f(r['f_cu'], 4)} | {f(r['du_Z1_um'], 4)} | {f(r['du_Z2_um'], 4)} | {f(r['du_ratio'], 4)} | {f(r['ratio_shift_pct'], 2)} % | **{f(r['warp_Z1_shift_pct'], 2)} %** | {f(r['Tmax_Z1_shift_K'], 2)} K |" for r in sens)) if sens else "TSV-to-mechanics sensitivity not available."}

{("**The ranking does not change; the absolute mechanical response does, strongly.** The largest ratio shift from any interconnect-geometry change is **" + f(sw['ratio_shift_pct'], 2) + " %**, nowhere near the 32 % gap between the architectures. But the same changes move the die warpage by **" + f(min(float(r['warp_Z1_shift_pct']) for r in sens), 1) + " % to +" + f(max(float(r['warp_Z1_shift_pct']) for r in sens), 1) + " %**, because the TSV field's copper fraction sets the effective CTE and stiffness of the whole through-substrate layer. That was invisible while the field was a frozen homogenized block, and it is why `d_x2_p_x2` --- which doubles the diameter and the pitch together, holding the copper fraction constant --- reproduces the baseline to the last digit. **The mechanical model responds to the copper fraction, not to the via.**") if sw and sens else ""}

---

## 46. VERDICT

**G --- MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER; OPTIMIZATION STILL PREMATURE.**

Rejected, with reasons:

* **A** (model closed, new variables proven) --- REJECTED. The variables are promoted and
  several new levers are proven, but the model is not closed: the electromigration limit is
  OPEN, no first-stage converter compiles below 48 V, the meshed-plane RDL anisotropy is
  unvalidated, and no cohesive parameters exist.
* **B** (interconnect geometry changes ranking) --- REJECTED on measurement. Under the
  allocation policy the framework actually uses, TSV geometry changes nothing electrically,
  thermally or mechanically, and the measured effect on the Z1/Z2 driver ratio is far below
  the architecture gap.
* **C** (partitioning changes ranking) --- REJECTED as stated, but it changes FEASIBILITY:
  three of eight templates do not fit the die shadow and a single-level VR misses by 1.76x.
* **D** (Z5 conclusion changes) --- REJECTED as stated. The 768 W survives on interposer
  geometry. What changes is the CLASS framing, which Phase 0I-R had already narrowed.
* **E** (cooling is a first-order ETM variable) --- **TRUE, and the largest single instance
  of G.** Not chosen as the dominant verdict only because it is one of several.
* **F** (compact models adequate, new variables second order) --- REJECTED. Contradicted by
  the cooling result, the RDL anisotropy, the absent intra-VR routing and the 2.4x crowding
  spread.

The first-order gaps, in order of size: the cooling boundary is not tied to any hardware and
hides 7.4 % of the load in uncharged pumping power; intra-VR routing is absent and worth up
to 3.9 % of the load; the RDL is modelled as isotropic when it is 153x anisotropic; the
pre-existing transverse TSV homogenization is 19 to 74 % wrong; current crowding is one
constant where the measured spread is 2.4x; and board viscoelasticity moves the reliability
driver ratio by about 3 %.

## 47. Optimizer gate

**FORBIDDEN, unchanged.** Phase 0M defines eventual optimizer variables and does not build
the optimizer. Of the six conditions:

| condition | status after Phase 0M |
|---|---|
| dominant geometry-dependent interconnect models closed | **NO** --- EM limit OPEN, crowding now a function but uncalibrated against measurement |
| routing scope physically correct | **PARTIAL** --- Level 1 now exists, at R1/R2 fidelity |
| architecture templates realizable | **PARTIAL** --- 5 of 8 fit; T1 fits but is not demonstrated |
| cooling boundary tied to physical hardware | **NO** --- derived here, not yet adopted by the ETM loop |
| dominant mechanical physics closed | **NO** --- 10 of 12 mechanisms unmodelled; 6 are P1 |
| `N_required` exists | **NO** |
"""
    (OUT / "PHASE0M_PHYSICAL_ARCHITECTURE_GATE.md").write_text(md)
    print(f"wrote {OUT/'PHASE0M_PHYSICAL_ARCHITECTURE_GATE.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
