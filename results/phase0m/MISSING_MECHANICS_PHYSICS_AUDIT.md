# PHASE 0M PARTS 27-33 --- MISSING-MECHANICS PHYSICS AUDIT

## What each term means, for a reader who is not a mechanician

**RATE-INDEPENDENT PLASTICITY.** Permanent deformation set by how hard you push, not how
long. Push past the yield stress and the metal takes a permanent set immediately; hold the
load and nothing more happens.

**CREEP / VISCOPLASTICITY.** Time- and temperature-dependent irreversible deformation. Hold
a solder joint at 85 C under load and it keeps deforming. This is what the project models.

**VISCOELASTICITY.** Time-dependent deformation that can RECOVER. A polymer loaded and then
unloaded springs back slowly rather than instantly. It is not damage and it is not
plasticity; it changes how much load a stiff member passes to a soft one, and how that
changes with dwell time.

**ASSEMBLY PRESTRESS / RESIDUAL STRESS.** Stress already present before the product is ever
switched on, left over from reflow, cure, cool-down and board attach. The joint does not
start at zero.

**DAMAGE.** Progressive degradation of stiffness or strength: the material gets weaker as it
is cycled, before anything visibly breaks.

**COHESIVE DELAMINATION.** Two bonded surfaces separating, governed by a traction-separation
law and a fracture energy rather than by a stress limit.

**CONTACT.** An interface that can open, close, slide, or conduct differently depending on
how hard it is pressed together.

**MOISTURE.** Water diffusing into polymers, swelling them, softening them, and degrading
adhesion; at reflow it can flash to steam and blow an interface apart.

## The physics matrix

| | mechanism | status | priority | effect size |
|---|---|---|---|---|
| A | rate-independent solder plasticity | **PARTIALLY MODELLED** | **P2** | NOT SEPARATELY IDENTIFIABLE. In a unified viscoplastic law there is no distinct rate-independent part -- Anand and Norton both represent the TOTAL inelastic strain. Adding a separate rate-independent term on top would double-count. |
| B | solder creep / unified viscoplasticity | **CURRENTLY MODELLED** | **P0** | dominant: 100 % of the modelled inelastic strain |
| C | organic-substrate and board viscoelasticity | **NOT MODELLED** | **P1** | MEASURED IN THIS PHASE -- see polymer_modulus_screen.csv |
| D | underfill / mold viscoelasticity | **NOT MODELLED** | **P1** | MEASURED IN THIS PHASE for the modulus; the time dependence is not |
| E | assembly / cure / reflow prestress | **NOT MODELLED** | **P1** | MEASURED IN THIS PHASE -- see assembly_prestress_test.csv |
| F | residual stress from process history | **NOT MODELLED** | **P1** | NOT ESTIMATED -- no process data exists in this repository |
| G | moisture diffusion and hygroscopic swelling | **NOT MODELLED** | **P3** | OUT OF SCOPE at the declared mission |
| H | moisture-dependent modulus and adhesion | **NOT MODELLED** | **P3** | OUT OF SCOPE at the declared mission |
| I | contact / sliding | **NOT MODELLED** | **P3** | ZERO for the intact package -- see etm_feedback_magnitudes.csv |
| J | interface delamination / cohesive zone | **NOT MODELLED** | **P1** | 25 % of the die delaminated is worth 12.5 K of junction rise (etm_feedback_magnitudes.csv) -- large, but only once damage exists |
| K | solder crack initiation and propagation | **NOT MODELLED** | **P2** | the correlation ranks architectures without a crack; a crack is needed only to predict crack PATH, area, or an electrical open |
| L | TSV / RDL cracking or plasticity | **NOT MODELLED** | **P1** | NOT ESTIMATED. Phase 0M gives the RDL layer an anisotropic property tensor for the first time, which is a prerequisite. |

Ten of twelve mechanisms are NOT MODELLED. That is not a scandal --- most of them should not
be modelled yet --- but it must be stated plainly and it is, in both reports.

## Part 30 measured --- does polymer stiffness matter?

The organic board, the underfill and the TIM are linear elastic with one modulus each. If
their stiffness is wrong or time-dependent, the displacement TRANSFERRED to the solder joint
is wrong, and that displacement is the single input the whole reliability chain reads.

| case | du Z1 | du Z2 | Z1/Z2 ratio | du Z1 shift | ratio shift |
|---|---|---|---|---|---|
| `baseline` | 2.7486 um | 2.0796 um | 1.3217 | 0.00 % | 0.00 % |
| `board_fr4_E_x0.5` | 2.4210 um | 1.8919 um | 1.2796 | -11.92 % | -3.18 % |
| `board_fr4_E_x0.7` | 2.5808 um | 1.9802 um | 1.3033 | -6.10 % | -1.39 % |
| `board_fr4_E_x1.3` | 2.8727 um | 2.1577 um | 1.3314 | 4.52 % | 0.73 % |
| `underfill_homog_E_x0.5` | 2.7504 um | 2.0805 um | 1.3220 | 0.07 % | 0.02 % |
| `underfill_homog_E_x0.7` | 2.7495 um | 2.0801 um | 1.3218 | 0.03 % | 0.01 % |
| `underfill_homog_E_x1.3` | 2.7478 um | 2.0791 um | 1.3216 | -0.03 % | -0.00 % |
| `tim_E_x0.5` | 2.7494 um | 2.0803 um | 1.3216 | 0.03 % | -0.00 % |
| `tim_E_x0.7` | 2.7491 um | 2.0800 um | 1.3217 | 0.02 % | -0.00 % |
| `tim_E_x1.3` | 2.7482 um | 2.0792 um | 1.3218 | -0.01 % | 0.01 % |
| `all_polymers_E_x0.5` | 2.4241 um | 1.8937 um | 1.2801 | -11.80 % | -3.15 % |

**The board dominates and the underfill and TIM do not.** Halving the board modulus moves
the Z1 corner shear by about 12 % and the Z1/Z2 ratio by about 3 %; halving the underfill
modulus moves the ratio by less than 0.05 %. The TIM is nearly irrelevant because it is
already two orders of magnitude softer than everything around it.

Three percent on the ratio is not negligible against a relative-life envelope of 1.19 to
1.22, which itself spans 2.5 %. So **board stiffness is a first-order input to the driver**,
and a linear-elastic laminate at one temperature is an approximation the framework has never
tested. It is classified **P1** rather than P0 for one reason: the effect is common-mode ---
both architectures move the same way and the ORDERING is untouched at every modulus tried.

What is NOT settled is the TIME dependence. Modulus scaling is a proxy for it and a
conservative one; a real Prony series would also change the DWELL response, which is where
the creep strain accumulates. No DMA data for the specific laminate is available in this
repository, so a Prony series cannot be fitted here.

## Part 31 measured --- does assembly prestress change the stabilised cycle?

The operational model is stress-free at the cycle minimum. The real joint is stress-free near
reflow, about 217 C, and arrives at room temperature already loaded. Tested by prepending a
reflow cool-down and comparing the STABILISED cycle, which is the only thing the life law
reads.

| architecture | reference state | d(PEEQ)/cycle | inelastic work | stabilisation | shift |
|---|---|---|---|---|---|
| Z1 | cycle minimum | 0.011694 | 1.19157 | 0.039 % | -- % |
| Z1 | reflow 217 C | 0.011734 | 1.19375 | 0.194 % | 0.34 % |
| Z2 | cycle minimum | 0.009745 | 0.90762 | 0.030 % | -- % |
| Z2 | reflow 217 C | 0.009789 | 0.90983 | 0.224 % | 0.45 % |

**The Z1/Z2 ratio moves from 1.2000 to 1.1987, a shift of -0.11 %.**

## Part 29 --- is rate-independent plasticity needed?

**No, and adding it would double-count.** The selected model M1 is a pure overstress
viscoplastic law with the yield surface removed; Anand and Norton both represent the TOTAL
inelastic strain, with no separate rate-independent branch to add. A unified law that already
reproduces the measured creep data cannot also be given an independent plastic strain without
counting the same deformation twice.

Classification: **LOW PRIORITY FOR CURRENT RANKING.** It becomes relevant only if a life law
is adopted whose calibration separates the two branches, in which case the model form must
match the law's, not the other way round.

## Part 32 --- moisture

**OUT OF SCOPE, stated explicitly.** The publication claim is DRY STEADY OPERATING ETM. No
humidity, storage or MSL requirement exists in any supplied source or in this repository.
Moisture becomes **P1 the moment such a requirement appears**, and the branch is named here
so that it is a decision rather than an omission.

## Part 33 --- damage, crack growth and delamination

Fatigue-life CORRELATION and explicit DAMAGE SIMULATION are different things and the project
does the first. The correlation ranks architectures without propagating a crack. Explicit
damage becomes necessary only if the framework must predict a crack path, a delamination
area, a stiffness knockdown, an electrical open or a thermal-contact degradation. The
first-order sizes are in `etm_feedback_magnitudes.csv`:

| mechanism | at | effect |
|---|---|---|
| crack reduces conducting cross-section | dR/R at 5 % joint area lost | 0.05263 (MATERIAL ONLY WITH DAMAGE) |
| crack reduces conducting cross-section | dR/R at 25 % joint area lost | 0.3333 (MATERIAL ONLY WITH DAMAGE) |
| crack reduces conducting cross-section | dR/R at 50 % joint area lost | 1 (MATERIAL ONLY WITH DAMAGE) |
| delamination removes interface thermal conductance | local dT_j at 5 % of the die area delaminated | 1.974 (MATERIAL ONLY WITH DAMAGE) |
| delamination removes interface thermal conductance | local dT_j at 25 % of the die area delaminated | 12.5 (MATERIAL ONLY WITH DAMAGE) |

25 % of a joint's area lost is worth a 33 % resistance rise --- 1.5x the whole
resistivity-versus-temperature effect. 25 % of the die delaminated is worth 12.5 K. Both are
large. Neither exists before damage does.

**Cohesive zones are NOT added**, because the brief's own rule bites: the traction-separation
laws and interface fracture energies for these interfaces are not sourced, and inventing them
would put a fabricated parameter at the centre of a failure prediction.
