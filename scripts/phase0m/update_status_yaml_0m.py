#!/usr/bin/env python3
"""Phase-0M -- update the single source of truth.

Staged transaction: every edit is validated before anything is written.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
Y = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
OUT = R / "results" / "phase0m"


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def num(rows, key, fn=min, cast=float):
    v = [cast(r[key]) for r in rows if r.get(key) not in (None, "", "nan")]
    return fn(v) if v else float("nan")


crowd = [r for r in rd("current_crowding_transition_sweep.csv") if r["status"] == "OK"]
route = [r for r in rd("intra_vr_routing_model.csv") if r.get("level") == "R1"]
part = rd("component_partition_templates.csv")
z5d = rd("z5_path_decomposition.csv")
me = rd("me_energy_reconstruction.csv")
poly = rd("polymer_modulus_screen.csv")
pre = rd("assembly_prestress_test.csv")
sens = rd("design_space_sensitivity.csv")
cetm = rd("cooling_etm_sensitivity.csv")

k_lo, k_hi = num(crowd, "K_crowd", min), num(crowd, "K_crowd", max)
p_lo, p_hi = num(route, "p_system_w", min), num(route, "p_system_w", max)
m1z1 = next((r for r in me if r["model"] == "M1" and r["arch"] == "Z1"), {})
m1z2 = next((r for r in me if r["model"] == "M1" and r["arch"] == "Z2"), {})
polyw = max((r for r in poly if r["case"] != "baseline"),
            key=lambda r: abs(float(r["ratio_shift_pct"])), default={})
prat = next((r for r in pre if r["arch"] == "RATIO"), {})
sw = max((r for r in sens if r["case"] != "baseline"),
         key=lambda r: abs(float(r["ratio_shift_pct"])), default={}) if sens else {}
cw = max(cetm, key=lambda r: abs(float(r["warpage_vs_uniform_pct"]))) if cetm else {}

DEFECTS = f"""
  - id: 47
    title: "PER-VIA CURRENT LIMIT WAS A PRIMITIVE IN AMPERES, AND IT IS THE ONLY THING THAT
            SETS FIELD RESISTANCE"
    detail: "configs/phase0dr/power_path_graphs.yaml carries i_max_a per tier -- BGA 0.5 A,
             C4 0.2 A, TSV 0.033 A, microbump 0.02 A -- as a primitive number. Phase 0M Part 3
             derives that under the allocation policy the framework actually uses,
             R_field = rho h J_max / I with the conductor cross-section cancelling identically,
             so J_max is the ONLY parameter that sets the field resistance and it was entered
             rather than derived."
    detected_by: "Phase 0M Part 1 parameter classification"
    impact: "The via-field resistance, IR drop and Joule loss of every architecture depend on a
             primitive. The geometry the framework carefully models cancels out."
    fix: "i_max_a is replaced by J_max * A_conductor, with J_max a PROCESS limit swept over the
          sourced 1e8 to 4e8 A/m2 envelope and A_conductor DERIVED from r and the liner."
    status: CONFIRMED, MODEL REPLACED IN scripts/phase0m/interconnect.py

  - id: 48
    title: "ONE GLOBAL CURRENT-CROWDING CONSTANT APPLIED TO FOUR DIFFERENT INTERCONNECT CLASSES"
    detail: "scripts/phase0e/architecture0e.py sets CROWDING_DEFAULT = 1.326, measured in HFSS on
             ONE P/G TSV loop, and multiplies the single-conductor resistance of BGA, C4, TSV and
             microbump by it alike."
    detected_by: "Phase 0M Parts 7 and 8"
    impact: "K_crowd measured over {len(crowd)} converged transition geometries spans
             {k_lo:.3f} to {k_hi:.3f}, a factor of {k_hi/k_lo:.2f}. A generous landing pad gives
             K < 1; a narrow trace entry gives K > 1.4. The excess resistance dR is
             length-INDEPENDENT while K_crowd is not, so K_crowd is not even the right form."
    fix: "A 3-D DC conduction solver derives K_crowd per geometry
          (results/phase0m/current_crowding_transition_sweep.csv). dR, not K_crowd, is the
          transferable quantity."
    status: CONFIRMED, FUNCTION AVAILABLE, NOT YET WIRED INTO THE PRODUCTION PATH

  - id: 49
    title: "THE TSV LINER IS ABSENT FROM THE CONDUCTOR AREA"
    detail: "ppdn.tier_area_m2() uses the full drilled diameter as conductor. A real TSV has a
             dielectric liner between the copper and the silicon."
    detected_by: "Phase 0M Part 2"
    impact: "The conducting area is overstated by [r/(r-t_ox)]^2 = 7.0 % at r = 15 um,
             t_ox = 0.5 um. R_field is UNAFFECTED under minimum-capability allocation because
             the cross-section cancels, but the per-via current, the copper fraction and every
             derived thermal and mechanical effective property are wrong -- and Part 21 shows
             the liner fraction t_ox/r is what makes a fine-pitch field thermally worse in
             plane at equal copper."
    fix: "TSVGeometry carries t_liner and uses r_cu = r - t_liner for all conducting areas."
    status: CONFIRMED, MODEL REPLACED

  - id: 50
    title: "THE CONVERTER AREA MODEL SILENTLY ASSUMES FOUR-LAYER VERTICAL STACKING, AND SAYS
            THE OPPOSITE"
    detail: "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py::_compute_area returns
             max(N*fp_hs, K*fp_ls, K*fp_ind, (N-1)*fp_cap). Its docstring says 'Total estimated
             component footprint' and the file header claims the function was 'fixed: area = SUM
             of all component footprints (not max)'. It is a max. The sibling implementation in
             HVR_FULL_OPT_sizing.py is honest about it: 'Vertical stacking model: total footprint
             is the max across layers'."
    detected_by: "Phase 0M Part 14"
    impact: "The reported 5.61 mm2 per VR cell is a PER-LAYER footprint. The summed component
             footprint of the compiled 1-kW cell is {float(part[0]['summed_component_area_mm2']):.2f} mm2,
             {float(part[0]['summed_component_area_mm2'])/5.61:.2f}x larger. Component-level z
             partitioning is therefore ALREADY assumed -- by the area model and by nothing else.
             Nothing checks that the four layers exist in a given architecture, and a
             single-level VR misses the 500 mm2 die shadow by 1.76x."
    fix: "configs/phase0m/component_partition_templates.yaml makes the partition explicit and
          checks each template for height, per-level area, array footprint against the die
          shadow, voltage-domain mixing and level crossings."
    status: CONFIRMED, DOCUMENTED, UPSTREAM NOT EDITED (separate repository)

  - id: 51
    title: "INTRA-CONVERTER ROUTING IS ABSENT FROM EVERY LOSS TERM"
    detail: "The framework models VR-to-package and package-to-POL routing. It models no metal
             between the converter's own components. The upstream loss model contains
             R_DS(on), the inductor DCR, the capacitor ESR and the switching losses, and no
             metallization at all."
    detected_by: "Phase 0M Part 10"
    impact: "{p_lo:.2f} to {p_hi:.2f} W system-wide, {100*p_lo/1000:.2f} to {100*p_hi/1000:.2f} %
             of the load, against a converter loss of 125.26 W. Common-mode across Z1, Z2 and Z4,
             so it does not reorder them, but it is not small. It also exposes a feasibility
             failure the framework could not see: the VR output plane needs 8.6x the available
             tile width to stay inside the sourced copper current-density envelope."
    fix: "scripts/phase0m/routing.py models it at R0/R1/R2 fidelity."
    status: CONFIRMED, MODEL BUILT, NOT YET WIRED INTO THE PRODUCTION LOSS TOTAL

  - id: 52
    title: "THE CALIBRATED COOLING BOUNDARY IS INCONSISTENT WITH THE SOURCE'S OWN FLOW RATE
            BY A FACTOR OF 16.8"
    detail: "h_top = 166 000 W/m2K was inverse-calibrated to reach 84 C. Derived from geometry
             and flow, no laminar microchannel architecture reaches it: the best laminar case
             gets 0.70x and reaching the calibrated value needs 50 g/s in the transitional
             regime, 74 W of pumping and 1.46 MPa. Separately, at the source's stated 1.6 g/s
             the coolant temperature rise for 1125 W of heat is 168 K, which single-phase water
             cannot do; 26.9 g/s is needed for a 10 K rise."
    detected_by: "Phase 0M Parts 23-25"
    impact: "The Robin boundary absorbs a caloric resistance that DOMINATES the thermal path at
             low flow and presents it as a surface property. It charges no pumping power --
             7.4 % of the load at the calibrated operating point. And because its sink is a
             single temperature it cannot produce a streamwise gradient: imposing the real
             coolant rise moves the die warpage by up to {abs(float(cw.get('warpage_vs_uniform_pct', 0))):.2f} %
             and T_max by {abs(float(cw.get('Tmax_vs_uniform_K', 0))):.1f} K."
    fix: "scripts/phase0m/cooling.py derives h from channel geometry and flow with source-backed
          correlations and charges the pressure drop and pumping power."
    status: CONFIRMED, MODEL BUILT, NOT YET ADOPTED BY THE ETM LOOP
"""

BLOCKS = f"""
# ============================================================================================
# PHASE 0M -- GEOMETRY-RESOLVED POWER DELIVERY, COMPONENT-LEVEL ARCHITECTURE, COOLING AND
# ETM-COUPLING AUDIT. Added 2026-09-16.
# ============================================================================================

interconnect_geometry:
  status: "PROMOTED TO DESIGN VARIABLES -- classification enforced in code"
  classification: "results/phase0m/INTERCONNECT_PARAMETER_CLASSIFICATION.md;
                   configs/phase0m/interconnect_design_space.yaml"
  tsv_radius_law: >-
    Under the minimum-capability allocation the reference framework actually uses,
    R_field = rho h J_max / I and the conductor cross-section cancels IDENTICALLY -- not
    merely the radius. IR drop = rho h J_max is independent of current; P = I rho h J_max is
    LINEAR in current; and phi_Cu = I / (J_max A_field) contains neither the radius nor the
    height, so the effective conductivity, modulus and CTE do not move with radius either.
    Measured spread over r = 2.5 to 50 um: 0.07 % (policy A), 0.02 % (fixed copper fraction),
    4.9 % (fixed pitch with additive spacing), 314 % (fixed count).
  radius_is_a_lever_for: "feasibility and aspect ratio, not loss"
  sensitivity_if_J_depends_on_r: >-
    the cancellation is exact only for J_max independent of r. If J_max = J0 (r0/r)^a then
    R_field ~ r^-a. No primary source giving a could be retrieved; a = 0 is carried and the
    sensitivity is stated, not assumed away.
  current_crowding: >-
    K_crowd = {k_lo:.3f} to {k_hi:.3f} over {len(crowd)} converged geometries, against the single
    global constant 1.326 in production. The EXCESS resistance dR is length-independent to five
    decimals while K_crowd is not, so dR is the transferable quantity.
  pre_existing_tsv_framework: >-
    FOUND at /home/beams0/MGHARIB/Model/TSVs_Framework_MultiGND_new_3_HSPICE.py (sha256
    eaf21b1f...). DC resistance and skin solution agree with this project's independent model.
    Its TRANSVERSE thermal model is REJECTED by the Phase-0M RVEs (19 to 74 % low). Its trained
    ML surrogate is deliberately NOT used: fitted on GHz signal-integrity data, no established
    validity for a DC power via field.

routing_scope:
  level_1_intra_converter: "ABSENT before Phase 0M. Now modelled at R0/R1/R2 fidelity."
  level_2_vr_to_package: "PRESENT (zpower.evaluate_z vertical tiers)"
  level_3_package_to_pol: "PRESENT (stack.rdl_network_solve)"
  intra_vr_loss_w: "{p_lo:.2f} to {p_hi:.2f} system-wide, {100*p_lo/1000:.2f} to {100*p_hi/1000:.2f} % of the load"
  double_counting: "NONE. The upstream converter model contains every device and passive
                    parasitic and no metallization."
  changes_ranking: false
  changes_ranking_reason: >-
    the converter cell is identical across Z1, Z2 and Z4, so intra-VR metallization is a
    common additive term.
  binding_constraint: >-
    current density, not resistance: the VR output plane needs 8.6x the available tile width
    at the reference 10 um single-layer RDL to stay inside the sourced copper envelope.
  fidelity: "R1 is conservative by about 37 % against R2 on the output net; R3 is needed only
             for transitions."

component_partition:
  previously_modelled: >-
    IMPLICITLY, in the converter AREA model alone -- _compute_area returns max() over the four
    component classes, which is a four-layer vertical stacking assumption. See defect 50. The
    electrical, thermal and mechanical models all place the VR as one lumped block.
  summed_component_footprint_mm2: {float(part[0]['summed_component_area_mm2']):.2f}
  reported_tile_area_mm2: 5.61
  single_level_verdict: "INFEASIBLE by 1.76x against the 500 mm2 die shadow. Vertical
                         partitioning is a precondition, not an optimization."
  templates_fitting: "{sum(1 for r in part if r['fits_die_shadow'] == 'True')} of {len(part)}"
  credible: "T1_EMBEDDED_4LAYER (fits, no mixed-voltage level, but the source calls it an open
             challenge) and T4_SPLIT_SC_BUCK (the only two-level template that fits)"
  z2_z4_finding: "as three-level stacks both are 8 % OVER the die shadow and need a fourth level"
  changes_rail_assignment: "only T4_SPLIT_SC_BUCK, which puts an intermediate 16 V rail across a
                            tier boundary -- a rail the power-path graph cannot represent"
  changes_electrical_ranking: false

z5_reaudit:
  survives: true
  p_lateral_w: {float(z5d[0]['P_loop_w']):.3f}
  r_eq_mohm: {float(z5d[0]['R_eq_mohm']):.5f}
  loop_squares: {float(z5d[0]['loop_squares']):.4f}
  ir_drop_v: {float(z5d[0]['IR_drop_v']):.4f}
  grid_converged_pct: 0.15
  pcb_inheritance: >-
    NO, AND THE REVERSE. The PCB row is 4.56x MORE conductive per square than the RDL row
    (0.5616 against 2.5611 mOhm/sq loop) because 152 um of copper at 50 % occupancy beats
    2 x 10 um at 83 %. Had Z5 inherited PCB geometry it would have reported about 169 W.
    No defect logged.
  class_conclusion: >-
    2.5D as a CLASS is NOT eliminated. Four-edge feeding cuts the lateral loss 4.5x; a 12 V
    lateral rail cuts it 144x. What is eliminated is the one-sided low-voltage lateral topology.
    No lateral variant beats the vertical architectures, and at 48 V the family degenerates into
    vertical delivery by another name.

thermal_homogenization:
  method: "explicit-geometry finite-volume RVEs; predeclared acceptance 10 % / 25 %"
  periodicity_verified: "1x1 versus 2x2 cell identical to 0.000 %"
  voigt_kz: "ACCEPTED, better than 1 % on every layer"
  maxwell_kxy_bumps: "ACCEPTED, better than 0.5 %"
  maxwell_kxy_tsv: "CONDITIONAL, 11 to 39 % high"
  framework_kxy_tsv: "REJECTED at four of five geometries, CONDITIONAL at the fifth, never
                      ACCEPTED; 19 to 74 % low -- it puts the liner in series with the copper"
  rdl_anisotropy: "153x to 276x between along-line and across-line conduction, currently
                   modelled as one isotropic k. Caveat: these cells are single-direction line
                   layers; a meshed plane is far less anisotropic."
  liner_finding: "at fixed copper fraction a smaller via is thermally worse in plane, because
                  the liner fraction scales as t_ox/r"
  local_region: "NOT homogenized -- global/local submodelling retained"

cooling_boundary:
  status_before: "h_top = 166 000 W/m2K, INVERSE-CALIBRATED; h_bottom = 10 W/m2K; one uniform
                  sink temperature"
  derivation_status: "DERIVED IN PHASE 0M from channel geometry and flow with source-backed
                      correlations; NOT YET ADOPTED by the ETM loop"
  architectures_tested: "top microchannel in silicon, top cold plate in copper,
                         substrate-embedded, two-sided, and the Tuckerman-Pease reference point"
  key_findings: >-
    (1) at the source's stated 1.6 g/s the coolant temperature rise for 1125 W is 168 K, and
    26.9 g/s is needed for 10 K; (2) no laminar architecture reaches 166 kW/m2K -- the best gets
    0.70x and the calibrated value needs 50 g/s, 74 W of pumping (7.4 % of the load) and
    1.46 MPa; (3) the caloric resistance dominates the path at low flow and the Robin boundary
    presents it as a surface property; (4) two-sided cooling is the largest single lever.
  is_first_order_etm_variable: true
  etm_effect: "an imposed coolant temperature rise moves die warpage by up to
               {abs(float(cw.get('warpage_vs_uniform_pct', 0))):.2f} % and T_max by
               {abs(float(cw.get('Tmax_vs_uniform_K', 0))):.1f} K; the uniform boundary sets both to zero"
  icepak: "NOT REVISITED. No Icepak validation is claimed or may be claimed until the earlier
           5000 K clamp is understood and repaired."

mechanics_physics:
  matrix: "results/phase0m/PHYSICS_PRIORITY_MATRIX.csv, 12 mechanisms"
  not_modelled: 10
  p0: "none -- creep/viscoplasticity, the only P0, is already modelled"
  p1: "organic-board viscoelasticity, underfill/mold viscoelasticity, assembly prestress,
       residual process stress, cohesive delamination, TSV/RDL cracking"
  rate_independent_plasticity: >-
    NOT NEEDED, and adding it to a unified viscoplastic law would double-count: Anand and
    Norton both represent the TOTAL inelastic strain and there is no separate branch to add.
  polymer_viscoelasticity: >-
    NEEDED (P1), and the board dominates. Halving the board modulus moves the Z1 corner shear
    about 12 % and the Z1/Z2 ratio {float(polyw.get('ratio_shift_pct', 0)):.2f} %, against a
    relative-life envelope spanning 2.5 %. Underfill and TIM modulus move the ratio by less
    than 0.05 %. Classified P1 not P0 because the effect is common-mode: the ORDERING is
    untouched at every modulus tried. The TIME dependence is NOT settled -- no DMA data for
    the specific laminate exists here, so a Prony series cannot be fitted.
  assembly_prestress: >-
    NEEDED FOR ABSOLUTE LIFE (P1). Measured on the stabilised cycle with a reflow cool-down
    from 217 C prepended: see results/phase0m/assembly_prestress_test.csv.
  moisture: "OUT OF SCOPE, declared. The publication claim is DRY STEADY OPERATING ETM.
             Becomes P1 the moment humidity, storage or MSL qualification enters the mission."
  crack_delamination_contact: >-
    NOT ADDED NOW. Contact does not apply -- every interface is metallurgical. Cohesive zones
    are not added because their traction-separation laws and fracture energies are not sourced.
    Crack propagation is not needed for RANKING and is needed only to predict crack path,
    delamination area, an electrical open or a thermal-contact degradation.
  largest_unmodelled_risk: "TSV/RDL cracking -- the RDL is not in the mechanical mesh at all,
                            and ARCH_Z4 and ARCH_Z5 load it hardest"

etm_coupling:
  current_level: "ETM-L1  (E <-> T -> M)"
  m_to_e: >-
    NOT MATERIAL before damage. Elastic geometry change gives dR/R = 0.16 % over the operating
    excursion, against 22.8 % from rho(T) which IS modelled -- 137x smaller, and far below the
    measured crowding spread. Contact-pressure feedback does not apply: every current-carrying
    interface is metallurgical. Electromigration voiding is OPEN, not negligible -- the limit
    itself is unsourced.
  m_to_t: >-
    SECOND ORDER BUT NOT ZERO. At the calibrated h the 50 um TIM contributes 0.0333 K/W against
    0.0121 K/W for convection, so the compliant layer DOMINATES the junction-to-coolant path
    and a 4 % bond-line change is worth 1.5 K, 2.9 % of the junction rise.
  damage_to_e_t: >-
    POTENTIALLY MATERIAL. 25 % of a joint's area lost is +33 % on R, 1.5x the whole rho(T)
    effect. 25 % of the die delaminated is +12.5 K.
  recommendation: "RETAIN ONE-WAY MECHANICS. ETM-L1 is sufficient for ranking; ETM-L3 is
                   required for failure progression and for nothing else this project claims."

phase0m_verdict:
  option_letter: "G"
  verdict: "MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER -- OPTIMIZATION STILL PREMATURE"
  largest_single_instance: "E -- cooling architecture is a first-order ETM design variable"
  rejected:
    - "A GEOMETRY-RESOLVED MODEL CLOSED -- rejected: the EM limit is OPEN, no first-stage
       converter compiles below 48 V, meshed-plane RDL anisotropy is unvalidated, and no
       cohesive parameters exist"
    - "B INTERCONNECT GEOMETRY CHANGES RANKING -- rejected on measurement: under the allocation
       policy in use, TSV geometry changes nothing electrically, thermally or mechanically"
    - "C PARTITIONING CHANGES RANKING -- rejected as stated; it changes FEASIBILITY, not order"
    - "D Z5 CONCLUSION CHANGES -- rejected as stated: the 768 W survives on interposer geometry.
       The CLASS framing changes, and Phase 0I-R had already narrowed it"
    - "F COMPACT MODELS ADEQUATE -- rejected: contradicted by cooling, RDL anisotropy, the
       absent intra-VR routing and the 2.4x crowding spread"
  first_order_gaps_in_order: >-
    the cooling boundary is not tied to any hardware and hides 7.4 % of the load in uncharged
    pumping power; intra-VR routing is absent and worth up to 3.9 % of the load; the RDL is
    modelled as isotropic when it is 153x anisotropic; the pre-existing transverse TSV
    homogenization is 19 to 74 % wrong; current crowding is one constant where the measured
    spread is 2.4x; and board viscoelasticity moves the reliability driver ratio by about 3 %.

phase0m_self_caught:
  note: >-
    Four faults in Phase-0M's OWN new code were caught before they reached a conclusion. They
    are recorded because the lesson generalises, not because they affected a result.
  items:
    - "a zero-width mesh cell from two interface planes an ULP apart produced a silently wrong
       K_crowd = 0.32 in a 92-point sweep; the only symptom was the current-balance residual.
       Fixed three ways and all three are negative-tested."
    - "fanned traces at +/-60 degrees with the ground on one face only were DEAD ENDS carrying
       no current, and returned K_crowd = 2.49. Traces are now axis-aligned and every lateral
       face is grounded."
    - "the first intra-VR routing layout was planar and returned 61 % of the load, because it
       forced a 6.8 A phase current down a lateral trace that does not exist in a vertically
       integrated VR."
    - "the clustered-Z5 loss was first SCALED as I^2 R / nc^1.5; that is wrong for a monolithic
       die and was replaced by a direct solve on the same resistive sheet."
"""


VERDICT_BLOCK = """  phase0m: "MULTIPLE MISSING PHYSICAL COUPLINGS ARE FIRST ORDER -- OPTIMIZATION STILL PREMATURE"
  phase0m_option_letter: "G"
  phase0m_dominant_blocker: >-
    The cooling boundary, which is inverse-calibrated rather than derived and hides 7.4 % of
    the load in uncharged pumping power. Stated in prose alongside the verdict; G is the
    single official verdict and E -- cooling as a first-order ETM design variable -- is its
    largest single instance rather than an alternative to it.
  rejected_verdicts_phase0m:
    "GEOMETRY-RESOLVED ARCHITECTURE MODEL CLOSED -- NEW ETM DESIGN VARIABLES PROVEN": >-
      rejected. The variables are promoted and several new levers are proven, but the model is
      not closed: the electromigration current-density limit is still OPEN, no first-stage
      converter compiles below 48 V, the meshed-plane RDL anisotropy is unvalidated, and no
      cohesive-zone parameters exist.
    "INTERCONNECT GEOMETRY MATERIALLY CHANGES ARCHITECTURE RANKING": >-
      rejected on measurement. Under the minimum-capability allocation the framework actually
      uses, the TSV cross-section cancels identically out of the field resistance AND out of
      the copper fraction, so radius changes nothing electrically, thermally or mechanically.
      Carried to the mechanical driver, the largest ratio shift from any interconnect-geometry
      change is 2.4 %, against a 32 % architecture gap. The ORDER never changes.
    "COMPONENT-LEVEL STACK PARTITIONING MATERIALLY CHANGES ARCHITECTURE RANKING": >-
      rejected as stated. Partitioning changes FEASIBILITY decisively -- a single-level VR
      misses the die shadow by 1.76x and three of eight templates do not fit -- but no
      partition reorders Z1, Z2 and Z4.
    "Z5 CONCLUSION CHANGES AFTER PHYSICAL ROUTING RE-AUDIT": >-
      rejected as stated. The ~768 W survives: it is computed on interposer RDL geometry, is
      grid-converged to 0.15 %, and did NOT inherit PCB routing -- the PCB row is 4.56x more
      conductive per square, so PCB inheritance would have given about 169 W. The CLASS framing
      does move, and Phase 0I-R had already narrowed it to the tested topology.
    "COOLING ARCHITECTURE IS A FIRST-ORDER ETM DESIGN VARIABLE": >-
      rejected AS THE DOMINANT VERDICT while being TRUE as a statement -- the distinction
      matters and is recorded rather than hidden. The cooling boundary is not tied to any
      hardware, no laminar cooler reaches the calibrated coefficient, reaching it costs 7.4 %
      of the load in uncharged pumping power, and a real coolant temperature rise moves die
      warpage by up to 8.2 %. It is the LARGEST SINGLE INSTANCE of G rather than a competing
      verdict, and exactly one verdict may be dominant.
    "CURRENT COMPACT MODELS REMAIN ADEQUATE -- NEW GEOMETRY VARIABLES ARE SECOND ORDER": >-
      rejected. Contradicted four separate ways: the cooling boundary cannot be realised by any
      laminar cooler and charges no pumping power; intra-VR routing is absent and worth up to
      3.9 % of the load; the RDL is modelled isotropic when it is 153x anisotropic; and the
      crowding constant spans 2.4x when measured.
"""


def main() -> int:
    s = Y.read_text()
    edits = []
    # 1. meta
    edits.append(('  current_phase: "0L-R"\n  phase_name: "High-stress constitutive robustness, '
                  'report propagation and auditor-dossier closure"',
                  '  current_phase: "0M"\n  phase_name: "Geometry-resolved power delivery, '
                  'component-level architecture, cooling and ETM-coupling audit"\n'
                  '  extends_verdict_of_0m: "0L-R"'))
    # 2. next_gate id
    edits.append(('  id: "0L -- MISSION INPUT AND BOARD-LEVEL CALIBRATION IN PARALLEL, '
                  'then RDL / delamination"',
                  '  id: "POST-0M -- (1) MATERIAL CHARACTERISATION of SAC305 above 16 MPa, with '
                  'primary-paper acquisition in parallel; (2) ADOPT the Phase-0M physical '
                  'cooling model into the ETM loop; (3) PUT THE RDL IN THE MECHANICAL MESH, '
                  'which is the largest unmodelled mechanism that could change ranking."\n'
                  '  supersedes_0l_framing: >-\n'
                  '    The next_gate block named Phase 0L as next long after Phases 0L, 0L-R and\n'
                  '    0M had run. Repaired in Phase 0M Part 0-B.'))
    # 3. gate count in current_facing
    edits.append(('    method: "Eleven sequential falsification gates (0B-0I plus the 0D-R and '
                  '0I-R audit\n             gates), each designed so that a negative result',
                  '    method: "Seventeen sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, '
                  '0F, 0G, 0H,\n             0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M), each '
                  'designed so that a negative result'))
    staged = s
    for old, new in edits:
        if staged.count(old) == 1:
            staged = staged.replace(old, new)
        elif staged.count(new) >= 1:
            print(f"  already applied: {old[:60]!r}")
        else:
            print(f"ABORT: pattern count {staged.count(old)} for {old[:70]!r}")
            return 1
    # 3b. the Phase-0M verdict, inserted before the Phase-0L-R blocker entry
    if "  phase0m_option_letter:" not in staged:
        a = "  phase0lr_dominant_blocker: >-"
        if staged.count(a) != 1:
            print("ABORT: verdict anchor missing")
            return 1
        staged = staged.replace(a, VERDICT_BLOCK + a, 1)

    # 4. defects after #46, before the CURRENT-FACING banner
    if "  - id: 47" not in staged:
        key = "# CURRENT-FACING CONTENT (Phase-0H DEFECT #32)"
        if staged.count(key) != 1:
            print("ABORT: cannot locate the current-facing banner")
            return 1
        i = staged.index(key)
        # walk back over the banner rule line that precedes the title
        j = staged.rfind("\n#", 0, i - 1)
        if j < 0:
            print("ABORT: banner rule line not found")
            return 1
        staged = staged[:j] + "\n" + DEFECTS.rstrip("\n") + staged[j:]
    # 5. append the Phase-0M blocks
    if "phase0m_verdict:" not in staged:
        staged = staged.rstrip("\n") + "\n" + BLOCKS
    Y.write_text(staged)
    import yaml
    d = yaml.safe_load(Y.read_text())
    assert d["meta"]["current_phase"] == "0M"
    assert d["phase0m_verdict"]["option_letter"] == "G"
    assert d["routing_scope"]["changes_ranking"] is False
    assert "0L --" not in d["next_gate"]["id"]
    assert "Eleven sequential" not in Y.read_text()
    print(f"YAML updated and re-parsed: {len(Y.read_text().splitlines())} lines, "
          f"{len(d)} top-level keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
