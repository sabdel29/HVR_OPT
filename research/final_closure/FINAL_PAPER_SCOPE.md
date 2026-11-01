# Final paper scope — the active architecture

This file states what the TCPMT paper compares, may claim and must not claim for the
**current** architecture. The scope frozen before the final physical lineage, whose Z2 was
the BGA-fed construction, is archived unchanged (with its history) at
`archive/FINAL_PAPER_SCOPE_PRE_DIRECT_FEED.md`. Every rule below that also appears there is
restated, not re-decided; the dated amendments at the end are the ones that hold now.

## What the paper compares

Two physically instantiated distributed vertical power-delivery architectures for a 1 kW,
1 V load supplied from 48 V through 49 hybrid (3:1 switched-capacitor + two-phase buck)
regulator cells:

- **Z1 — embedded (`Z1_EMBEDDED`).** The regulator cells are embedded in the package
  between the substrate and the die. 48 V enters through the BGA field and the package
  48 V RDL and crosses the substrate (its TSV field) before conversion; 1 V travels a short
  vertical path to the die.
- **Z2 — direct-fed backside (`Z2_DIRECT_FEED`).** The regulator cells sit on the land side
  inside the PCB opening and clear its sidewall by the specified 1 mm. 48 V enters the
  backside regulator **directly**, through a dedicated external feed in the opening whose
  loop resistance `R_Z2_direct_feed_loop` is a requirement, not a part. No 48 V current
  flows in the Z2 BGA field or in a package 48 V RDL. Only 1 V (supply and return) crosses
  into the substrate: through the explicit VR-to-substrate attach (Cu pillar + solder cap
  + underfill, a CLOSE_ANALOG geometry) and then the TSV field to the die.
- **Control — `Z2_BGA_FED_CONTROL`.** The same backside regulator fed through the BGA field
  and the package RDL. It exists only for `CONTROLLED_BGA_FED_Z1_VS_Z2_EXPERIMENT` and the
  appendix comparison. It is never the primary Z2 and never enters a headline ordering.

The frozen architecture record is `Z2_DIRECT_FEED_ARCHITECTURE.md`
(`z2_direct_feed_architecture.json`).

## Loss boundaries

"Loss" is never written without its boundary.

- **Package-internal loss** (`P_loss_package_internal_w`): every conductor inside the
  package boundary. For Z1 it starts at the BGA pads on the PCB, where the board 48 V node
  common to both architectures meets the package. For Z2 it starts at the backside
  regulator's 48 V input terminals; the external direct-feed loop is outside it.
- **Platform-inclusive loss** (`P_loss_platform_inclusive_*`): the package-internal loss
  plus, for Z2, the feed-loop dissipation at a **named** loop resistance (0, 1 mOhm, R*).
  Because no source gives that resistance, no platform-inclusive winner is claimed; the
  result is the crossover R*: Z2 is lower platform-inclusive only while its feed loop
  stays below R*.
- A generic claim that one architecture "has lower loss" is forbidden; each loss sentence
  names its boundary.

## The paper MAY claim

1. A physically instantiated Z1/Z2 comparison under declared geometry assumptions.
2. An electrical package-internal loss comparison in which every conductor has exactly one
   owner, and the platform-inclusive comparison as a requirement on the external feed
   ("for Z2 to keep its electrical advantage, `R_Z2_direct_feed_loop` < R*").
3. An electrothermal temperature comparison from a converged E–T fixed point.
4. A package-deformation comparison (die and package warpage, joint displacement driver).
5. A local, fatigue-relevant solder *response* at the critical joint, ranked only where
   the gap exceeds twice its quantified uncertainty.
6. Model-specific accuracy against a matched reference solver, stage by stage.
7. Model-specific speedups against the matched reference, on the same problem and the
   same hardware.
8. Which class-B inputs preserve and which reverse each ordering. Reversals are a central
   result, not a caveat; no universal winner is claimed.
9. Physical realisability of each architecture under the declared geometry.

## The paper MUST NOT claim

- manufacturing qualification of either architecture or of the attach;
- a universal BGA, pad, TSV, RDL or attach safe current or current density, or an
  electromigration-safe current;
- an absolute solder fatigue life or number of cycles to failure;
- a value of the external feed-loop resistance, or that any connector meets or misses
  R* (a connector datasheet gives a contact resistance, never the loop resistance);
- any dimension or performance number taken from the ARM construction precedent, which is
  an architectural precedent only;
- a 48 V BGA field, a package 48 V RDL term or a lateral package 48 V path in the primary Z2;
- superiority over a commercial tool, except where a matched benchmark was run;
- a single "framework accuracy" figure;
- that the 48 V input current waveform is known — it is not derivable from the converter
  model, and every HV-side result is conditioned on a named scenario.

## How open quantities are handled

| class | meaning | consequence for the paper |
|---|---|---|
| A — paper-critical | can move loss, heat, temperature, warpage, joint driver or ordering | closed before the final comparison |
| B — paper-sensitivity | no single value exists | carried over a declared range; which orderings it preserves or reverses is reported; wording conditional |
| C — qualification | an allowable, a rating, a lifetime | limits claims only; never blocks the comparison |

The classification of every OPEN gate is in `paper_gate_classification.csv`; the class-B
runs are in `classB_resolution.json`.

## The 48 V waveform

HV-S0, HV-S1 and HV-S2 are **named scenarios**, not a bracket, not lower/nominal/upper,
and not a confidence interval. From an average current alone no finite RMS upper bound
exists. The final comparison is run for every scenario that is physically solvable, and
the paper states for each whether the architecture ordering holds. An operating point at
which a joint reaches the solder's melting point ranks nothing.

## BGA construction for the comparison

Z1 uses a **matched** 48 V BGA count, legal and satisfying the declared electrical
criterion at HV-S0. The Z2 BGA field is mechanical and carries no 48 V current. The
dependence on the unsourced 1.5 A/ball engineering criterion is reported as a
provisioning sensitivity; 1.5 A/ball is never treated as a reliability allowable.

## Amendments that hold

**2026-10-27 — production mesh and HV-S0 ordering rule.** The declared mesh check (h_xy
1.1 against 0.8 mm) was not a refinement; it was replaced by a nested refinement (every
interval split, every coarse node kept) with the same 2 % tolerance on the same
observables. The base grid failed it, so the production lineage is the in-plane-split
grid. An HV-S0 ordering is claimed only where the Z1/Z2 gap exceeds twice the largest
measured mesh change of that observable (`ordering.json`); the rule can only withdraw a
claim.

**2026-10-27 18:36 — an observable that fails at the production level.** If the in-plane
change r21 -> r31 exceeds 2 %, the observable is not reported as converged; its
uncertainty is bounded by Richardson extrapolation over r11, r21, r31 with the observed
order and a safety factor of 1.25. A non-monotone sequence leaves it unbounded and the
paper not ready. Orderings involving a bounded observable are claimed only beyond 2U.

**2026-10-28 — the primary Z2 is direct-fed** (`Z2_DIRECT_FEED_ARCHITECTURE.md`, declared
before any result of the corrected lineage). The cold-plate correlation is not
recalibrated to the Icepak benchmark; the Icepak-equivalent coefficient is a class-B
sensitivity.

**2026-11-01 — loss boundaries.** The single "loss" ordering is split into the
package-internal ordering and the platform-inclusive one, which is conditional on the
feed-loop resistance and names no single winner (`ordering.json`). The readiness rule
fails while a generic loss ordering, or a stored platform-inclusive winner, exists.

**2026-11-01 — attach density (`geom.vr_attach_density`, B1).** Declared while the
attach-density runs were in progress, before any of their converged results was read.

- The attach density is taken at two published constructions, one dense and one sparse,
  with the production material system (Cu pillar + solder cap, 14 + 16 µm, underfill) held constant:
  15 µm at 30 µm pitch (Au et al., ECTC 2016, CLOSE_ANALOG; its "16mm" cap height is a
  unit error, read as 16 µm) and 30 µm at 80 µm pitch (Na et al., Electronics 2023,
  CLOSE_ANALOG). Pitches between them are an ENGINEERING_SENSITIVITY used only to locate a
  crossover, never a manufacturing geometry.
- Each case is the real finite lattice of the cell: legal sites with the stated edge
  clearance, VDD/GND counts by the stated checkerboard rule, metal area and area fraction
  from those sites. No count is hard-coded.
- Per-bump current and average current density are outputs only. Electromigration
  sources are CONTEXT_ONLY; no electromigration-safe current is claimed.
- Each bump is the Cu column and the solder cap in series plus the two-sided constriction;
  equal sharing is not assumed silently — the spreading length is compared with the cell,
  and the equal-sharing block model is reported as the upper bound it is.
- The thermal card (series column, parallel underfill; Maxwell-Garnett in plane) is checked
  against an explicit unit-cell FEM in both directions for both endpoints. The mechanical
  card is BOUNDED (underfill-dominated A, column-stiffened B); no structural
  homogenisation claim is made.
- The gate stays unresolved until its evidence exists; an ordering the attach density can
  move is reported as such, with the crossover requirement if one exists. The local solder
  response remains unranked unless its gap exceeds 2U.
