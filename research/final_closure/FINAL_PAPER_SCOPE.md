# Final paper scope — frozen before the manuscript is modified

This file fixes what the TCPMT paper will and will not claim **before** the final
physical lineage is run, so that the claims cannot drift toward whatever the numbers
turn out to favour.

## What the paper compares

Two physically instantiated distributed vertical power-delivery architectures for a
1 kW, 1 V load supplied from 48 V through 49 hybrid (3:1 switched-capacitor + two-phase
buck) regulator cells:

- **Z1 — embedded:** the regulator cells sit inside the package substrate; 48 V crosses
  the substrate and 1 V travels a short vertical path to the die.
- **Z2 — backside:** the regulator cells sit on the land side inside a 23.36 mm PCB
  cutout; 48 V reaches them laterally through the package RDL and 1 V crosses the
  substrate through a TSV field.

## The paper MAY claim

1. A physically instantiated Z1/Z2 comparison under declared geometry assumptions.
2. An electrical loss comparison in which every conductor has exactly one owner.
3. An electrothermal temperature comparison from a converged E–T fixed point.
4. A package-deformation comparison (die and package warpage, joint displacement driver).
5. A local, fatigue-relevant solder *response* comparison at the critical joint.
6. Model-specific accuracy against a matched reference solver, stage by stage.
7. Model-specific speedups against the matched reference, on the same problem and the
   same hardware.
8. Robustness of the architecture ordering over the declared sensitivities.
9. Physical realisability of each architecture under the declared geometry.

## The paper MUST NOT claim

- manufacturing qualification of either architecture;
- a universal BGA, pad, TSV or RDL safe current or current density;
- an absolute solder fatigue life or number of cycles to failure;
- superiority over a commercial tool, except where a matched benchmark was run;
- a single "framework accuracy" figure;
- that the 48 V input current waveform is known — it is not derivable from the
  converter model, and every HV-side result is conditioned on a named scenario.

## How open quantities are handled

| class | meaning | consequence for the paper |
|---|---|---|
| A — paper-critical | can move loss, heat, temperature, warpage, joint driver or ordering | closed before the final comparison |
| B — paper-sensitivity | no single value exists | carried over a declared range; ordering must be shown robust; wording conditional |
| C — qualification | an allowable, a rating, a lifetime | limits claims only; never blocks the comparison |

The classification of every OPEN gate is in `paper_gate_classification.csv`.

## The 48 V waveform

HV-S0, HV-S1 and HV-S2 are **named scenarios**, not a bracket, not lower/nominal/upper,
and not a confidence interval. From an average current alone no finite RMS upper bound
exists. The final comparison is run for every scenario that is physically solvable, and
the paper states for each whether the architecture ordering holds.

## BGA construction for the comparison

The main comparison uses a **matched** BGA count, legal in both architectures and
satisfying the declared electrical criterion for both at HV-S0, so that architecture and
count optimisation are not confounded. Architecture-specific counts, the non-monotonic
count dependence and the dependence on the unsourced 1.5 A/ball engineering criterion are
reported as a separate provisioning sensitivity. 1.5 A/ball is never treated as a
reliability allowable.

## Amendments after the scope was frozen

**2026-10-27 — production mesh and HV-S0 ordering rule.** The declared mesh check
(h_xy 1.1 against 0.8 mm, 2 % tolerance) turned out not to be a refinement: lowering
h_xy re-grades the grid, and for Z2 both levels had 38 lines per axis with a *larger*
largest element at 0.8 mm. It was replaced by a nested refinement (every interval split,
every coarse node kept) with the same 2 % tolerance on the same observables. On it the
base grid failed (peak temperature moved by more than 2 %), so the production lineage
moved to the in-plane-split grid and every final number was recomputed on it.

Because the base and the split grid gave **opposite** HV-S0 peak-temperature orderings,
one rule was added after that observation: an HV-S0 ordering is claimed only where the
Z1/Z2 gap exceeds twice the largest measured mesh change of that observable
(`ordering.json`). The rule can only withdraw a claim, never create one.

**2026-10-27 18:36 — handling an observable that fails at the production level (declared
before any r31 mechanical result existed).** If the in-plane change r21 -> r31 of an
observable exceeds the 2 % tolerance, that observable is not reported as converged. Its
discretisation uncertainty on the production grid is bounded by Richardson extrapolation
over the three nested levels r11, r21, r31 with the observed order and a safety factor of
1.25 (U = 1.25 |v_r21 - v_extrapolated| / |v_extrapolated|); if the observed order cannot be
formed (non-monotone sequence), the observable is unbounded and the paper is not ready.
A bounded observable is reported with U, and any Z1/Z2 ordering involving it is claimed only
where the gap exceeds 2U. This extends the rule above; it can only withdraw claims.

**2026-10-28 — the primary Z2 is direct-fed.** This amendment restates the architecture
frozen in `Z2_DIRECT_FEED_ARCHITECTURE.md` (commit 30d92b5) before any result of the
corrected lineage existed; none of its rules depends on a corrected-lineage number.

- The **Z2** described above ("48 V reaches them laterally through the package RDL") is
  superseded as the primary construction. The primary Z2 takes its 48 V directly into the
  backside regulator through a dedicated external connection in the PCB opening; only 1 V
  crosses the substrate, through an explicit VR-to-substrate attach; the converter clears
  the opening sidewall by the specified 1 mm. The BGA-fed Z2 survives only as the control
  of `CONTROLLED_BGA_FED_Z1_VS_Z2_EXPERIMENT` and is reported as such.
- The paper MAY claim the platform-inclusive crossover R* as a **requirement** on the
  external feed loop ("for Z2 to keep its electrical advantage, R_Z2_direct_feed_loop < R*").
- The paper MUST NOT claim a value of that loop resistance, that any connector meets or
  misses the requirement, or manufacturability of the attach; it MUST NOT use the ARM
  construction precedent for any dimension or performance number.
- Item 8 above ("robustness of the architecture ordering") is replaced by: **which class-B
  inputs preserve and which reverse each ordering**. Reversals are reported as a central
  result, not hidden as caveats; no universal winner is claimed.
- The cold-plate correlation is not recalibrated to the Icepak benchmark; the
  Icepak-equivalent coefficient is a class-B sensitivity.
