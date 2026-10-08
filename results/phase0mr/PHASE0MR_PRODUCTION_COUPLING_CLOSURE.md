# PHASE 0M-R --- PRODUCTION-COUPLING CLOSURE

**Verdict: C --- PRODUCTION COUPLING PRESERVES THE ARCHITECTURE ORDERING; ABSOLUTE RESPONSES
CHANGE MATERIALLY.**

Stated immediately, because it qualifies the verdict: **two of the four orderings do change.**
Peak temperature reorders for a real physical reason. Corner-joint shear reorders only
between Z1 and Z4, and only because of a heat-deposition substitution forced by a gap in the
global mesh --- that one is not physics and must not be read as such. What survives is the
ordering the project's scientific claim actually rests on: **Z2 better than Z1 on solder
fatigue, before and after, on every metric.**

---

## What Phase 0M-R actually did

Phase 0M found five first-order models that existed as validated SCREENING tools and did not
drive anything. Phase 0M-R wired them into the production path and re-ran a frozen comparison
matrix through it.

| model | Phase 0M | Phase 0M-R |
|---|---|---|
| intra-VR routing | measured, absent from the total | **in the total, template-aware** |
| transition resistance | one global constant, 1.326 | **per class, solved exactly, cross-validated** |
| physical cooling | measured, not in the loop | **in the loop, with a streamwise coolant rise** |
| spatial heat deposition | one lumped load | **per layer, energy-checked** |
| local temperature feedback | package maximum | **the converter's own layer temperature** |
| RDL thermal and mechanical | measured on unit cells | ladder built and measured; **not yet the default** |
| component partition | area check only | **six independent feasibility questions** |

## The measured effect

| architecture | system loss | peak temperature | die warpage | corner-joint shear |
|---|---|---|---|---|
| Z1_EMBEDDED | 125.10 -> **141.78** W (+13.3 %) | 84.87 -> **123.53** C (+38.7 K) | 20.04 -> **25.37** um (+26.6 %) | 2.7447 -> **4.2803** um (+55.9 %) |
| Z2_BACKSIDE | 126.19 -> **143.61** W (+13.8 %) | 83.31 -> **130.31** C (+47.0 K) | 17.24 -> **22.62** um (+31.2 %) | 2.0754 -> **3.4101** um (+64.3 %) |
| Z4_POWER_DIE | 123.64 -> **134.74** W (+9.0 %) | 83.30 -> **96.32** C (+13.0 K) | 30.14 -> **35.95** um (+19.3 %) | 2.9744 -> **3.6681** um (+23.3 %) |

**The absolute responses change by up to +13 % in loss, +47 K in temperature, +31 % in
warpage and +56 % in the reliability driver.** None of that was visible through the Phase-0M
production path.

## Ordering

| metric | before | after | changed? |
|---|---|---|---|
| system electrical loss | Z4_POWER_DIE < Z1_EMBEDDED < Z2_BACKSIDE | Z4_POWER_DIE < Z1_EMBEDDED < Z2_BACKSIDE | **no** |
| peak temperature | Z4_POWER_DIE < Z2_BACKSIDE < Z1_EMBEDDED | Z4_POWER_DIE < Z1_EMBEDDED < Z2_BACKSIDE | **YES** |
| die warpage | Z2_BACKSIDE < Z1_EMBEDDED < Z4_POWER_DIE | Z2_BACKSIDE < Z1_EMBEDDED < Z4_POWER_DIE | **no** |
| corner-joint shear | Z2_BACKSIDE < Z1_EMBEDDED < Z4_POWER_DIE | Z2_BACKSIDE < Z4_POWER_DIE < Z1_EMBEDDED | **YES** |

Two orderings change and two do not, and **the two changes have different causes.** One is a
physical result. The other is an artifact of a modelling substitution and must not be read as
physics. Telling them apart needed the converter depth below the cooled face:

| architecture | converter layer | depth below the cooled face | real layer? |
|---|---|---|---|
| Z1_EMBEDDED | `tile_band` | 0.973 mm | yes |
| Z2_BACKSIDE | `conv` | **1.273 mm** | yes |
| Z4_POWER_DIE | `interface` | 0.355 mm | **NO --- substituted** |

**The temperature reordering (Z1 and Z2 swap) is REAL.** Z2 puts its converter on the
backside, 1.273 mm below the cooled face against Z1's 0.973 mm. Against the retired
calibrated Robin boundary --- a near-isothermal sink at h = 166 000 W/m2K over the whole top
face --- that extra 0.3 mm was almost free, and Z2 came out 1.56 K COOLER than Z1. Against a
physical cooler with finite h and a streamwise caloric rise it costs **6.78 K at the peak**,
and Z2 becomes the hottest of the three. The signature confirms the mechanism: the gap is
6.78 K at the PEAK but only 1.44 K in the mean, which is what a depth penalty looks like and
is not what a uniform offset would look like.

**The corner-shear reordering (Z1 and Z4 swap) is CONDITIONAL and is not evidence about Z4.**
`zglobal.stack_for` gives the Z4 power-die architecture no converter layer at all --- the
Phase-0I global model never represented that die geometrically --- so its heat is deposited
in the `interface` layer, only 0.355 mm below the cooled face. That is far closer to the
cooler than any real Z4 power die would sit. Z4 consequently heats by 13 K where Z1 heats by
39 K, its thermal strain is correspondingly understated, and it overtakes Z1. **Recorded as
conditional, and the first item on the next-work list.**

### The finding that neither ordering shows on its own

**Z2 becomes the hottest architecture and remains the best on the reliability driver.** It
runs 6.78 K above Z1 at the peak and still carries 20 % less corner-joint shear. Peak
temperature and the fatigue driver do not track each other here, because the driver is set by
CTE mismatch across a thin substrate rather than by absolute temperature. Any screening study
that ranked these architectures on T_max alone would have ordered them wrongly for the metric
that actually decides the design.

## Independent validation

| what | against | result |
|---|---|---|
| transition resistance, 5 geometries | **MOOSE**, independent mesher/formulation/solver | **0.25 to 0.73 %, 5/5 ACCEPTED** |
| uniform bar | analytic | exact at every mesh, both codes |
| spreading resistance | analytic `rho/(4a)` | +0.9 % at 6 cells per contact radius |
| cooling solid side | **MOOSE**, explicit fins | 3.78 % at the production geometry; **2/4 ACCEPTED**, one REJECTED at 10.11 % |
| cooling fluid side | analytic energy balance | exact |
| loss decomposition | the upstream aggregate | machine precision, or the ledger refuses to total |
| spatial heat | the electrical total | within 1e-6 relative, guarded |

The first cross-solver run **failed**, at 12.1 % and 18.7 % on the narrow-trace cases. The
cause was MOOSE's centroid-based subdomain assignment staircasing the trace, and the
disagreement changed sign in the direction the staircase predicted each time. Mesh alignment
is now part of the case definition and every run reports its discretised block volumes.

## Answers to the questions the replay had to settle

**Q1. How much does wiring intra-VR routing into production change P_elec?**
3.650 + 1.893 W on Z1 and
3.666 + 1.901 W on Z2 at the reference
stack --- about 5 W system-wide, 0.5 % of the load. Across every stack and via policy
examined the term spans 4.55 to 43.84 W.

**Q2. Is it still common mode once partitioning is architecture-specific?**
**No, and the Phase-0M claim is narrowed.** It varies **7.5 %** across templates. A template
that splits by voltage domain puts the 16 V intermediate rail across the tier boundary
instead of the 1 V rail and its vertical loss collapses by three orders of magnitude.

**Q3. How much does replacing K_crowd with geometry-specific dR move each architecture?**
It REDUCES the interconnect loss. On Z2 the TSV term falls from
1.6640 to 1.0019 W and the bump
term from 0.1671 to 0.0171 W,
because `dR` at the nominal geometry is NEGATIVE where the retired constant added 32.6 %.

**Q4. Does physical cooling change architecture ordering?**
**Yes --- it reorders peak temperature, and for a real reason.** A calibrated Robin boundary
at h = 166 000 W/m2K is nearly isothermal over the whole top face, so how DEEP a converter
sits below that face barely registers. A physical cooler has finite h and a streamwise
caloric rise, and depth starts to cost. Z2's backside converter sits 1.273 mm down against
Z1's 0.973 mm, and Z2 goes from 1.56 K cooler than Z1 to 6.78 K hotter. The absolute effect
is larger still: +47 K on Z2.

Cooling hardware is also a first-order design variable in its own right, not a boundary
condition to be chosen for convenience:

| cooler | total flow | Z2 peak temperature | Z2 corner shear |
|---|---|---|---|
| TOP_SI_MICROCHANNEL_27 | 27 g/s | 130.31 C | 3.4101 um |
| TOP_SI_MICROCHANNEL_50 | 50 g/s | 114.89 C | 2.8842 um |
| TWO_SIDED_SI_14 | 27 g/s (13.5 per side) | 136.53 C | 3.6258 um |

Two results worth stating. Buying flow works: 27 to 50 g/s is worth
15.4 K and 15.4 % of the driver, at 74 W of pumping.
And **two-sided cooling at EQUAL TOTAL FLOW is worse, not better** --- +6.2 K --- because
the second side faces the board rather than the die, so diverting half the heat into a
thermally remote path costs more than the extra area returns.

**Q5. What pumping power?**
115553 W/m2K at 27 g/s costs 14.7 W hydraulic; reaching the old
calibrated 166 000 W/m2K needs 50 g/s, **74 W --- 7.4 % of the load ---** and 1.46 MPa.

**Q6. Does streamwise coolant warming change the Z1/Z2 mechanical driver ratio?**
The ratio moves from 1.3225 to
1.2552 --- a shift of
-5.1 %. Z2 stays ahead.

**Q7. Does anisotropic RDL homogenization change T_max or warpage materially?**
Yes: -1.9 K to +4.7 K on T_max and -4.4 % to +2.9 % on warpage, depending on the rung.

**Q8. Does adding the RDL to the mechanical mesh change Z1/Z2 ordering?**
**No.** The ratio moves 1.3217 -> 1.3222 ->
1.3202, at most 0.11 %.

**Q9. Does TSV radius ever matter through feasibility?**
**Decisively.** At 300 um only r >= 15 um is buildable at a 10:1 aspect limit --- and 15 um
is the reference radius, so the source geometry sits ON the limit. At 1300 um no radius in
the swept range works.

**Q10. Does T4's intermediate rail improve interconnect loss?**
Yes, in the vertical term: it collapses from 0.06535 to
0.00017 W per cell, because 1.44 A crosses the boundary instead of 20.4 A.
It does not help the total, because the lateral term grows to compensate, and T4 fails the
area bound by 2 %.

**Q11. Does Z5 remain poor?**
Yes as a one-sided low-voltage lateral feed, and no as a class. Four-edge feeding cuts the
lateral loss 4.5x and a 12 V lateral rail cuts it 144x, but no lateral variant beats the
vertical architectures, and at 48 V the family degenerates into vertical delivery.

**Q12. Which missing term is largest?**
In **watts**, intra-VR routing (about 5 W, up to 39 W at a thin stack). In **kelvin**, the
cooling boundary (+47 K). In **warpage** and in the **local driver**, the cooling boundary again,
through temperature. In **feasibility**, the package clearances --- three unsourced numbers
that prevent any partition template from being called buildable.

**Q13. Did any ranking change?**
**Yes, two of four, for two different reasons.** The electrical and warpage orderings did
not. Peak temperature reordered because Z2's backside converter is 0.3 mm deeper below the
cooled face than Z1's and a physical cooler charges for that depth --- a REAL result.
Corner-joint shear reordered only between Z1 and Z4, entirely because Z4's heat is deposited
in a substituted layer 0.355 mm below the cooler --- CONDITIONAL, and not evidence about Z4.
**Z2 remains best on the reliability driver in both, which is the ordering the project's
claim rests on.** The most useful thing the replay found is that the two do not track: Z2
becomes the HOTTEST architecture while remaining the BEST on fatigue.

**Q14. Which Phase-0M statements must be narrowed or withdrawn?**
Four, all narrowed rather than withdrawn:

* *"intra-VR routing is common-mode across architectures"* --- true only at fixed component
  topology; **7.5 % template-dependent**;
* *"the RDL is 153x to 276x anisotropic"* --- that is IN-PLANE for a single-direction line
  layer. **Every realistic stack organisation is in-plane isotropic**; the real anisotropy is
  through-thickness, 57x to 270x, and in the opposite sense;
* *"dR is the excess resistance"* --- it is a **difference against a stated 1-D reference**
  with different terminal conditions, and it can legitimately be negative;
* *"TSV radius is not a lever"* --- not a FIELD-LOSS lever under one allocation policy;
  decisively a **feasibility** variable.

## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** physical production path closed, replay authorised | rejected. The replay ran and is sound, but "closed" is not earned: six blocking items remain OPEN, no partition template is fully realizable, and the RDL is not yet the default mechanical or thermal representation |
| **B** production coupling CHANGES architecture ordering | rejected as the dominant statement. Two of four orderings change and both trace to one modelling substitution for Z4, not to physics. The ordering the scientific claim rests on is preserved |
| **D** the cooling model dominates architecture uncertainty | **largely TRUE and the single biggest contributor** --- it supplies most of the 47 K and, through temperature, most of the warpage and driver change. Not chosen as dominant because the verdict has to describe what the replay concluded about ORDERING, which is C's subject |
| **E** RDL / routing physics dominate | rejected. Routing is about 0.5 % of the load and the RDL moves the ratio by 0.11 %. Cooling is an order of magnitude larger |
| **F** independent validation failed | rejected. 5 of 5 transition cells ACCEPTED at 0.25 to 0.73 %; the one REJECTED cooling case is outside the production regime and is reported as such |
| **G** multiple first-order couplings remain open, framework not closed | rejected as the dominant statement, though several DO remain open. It was Phase 0M's verdict and this phase closed five of the models it named; repeating it would understate what changed |

## Optimizer gate

**FORBIDDEN, unchanged.** Two preconditions moved from NO to PARTIAL and one from NO to YES.
Four remain NO, and any one of them is sufficient:

| precondition | status |
|---|---|
| interconnect geometry and crowding validated | **PARTIAL** --- cross-validated to 0.75 %, but the EM allowable is OPEN |
| routing scope physically correct | **PARTIAL** --- all three levels exist, at analytic/sheet fidelity |
| cooling boundary tied to physical hardware | **YES** |
| architecture templates realizable | **NO** |
| dominant mechanical physics closed | **NO** |
| an admissible mechanical criterion exists | **NO** |
| a required life exists | **NO** |
