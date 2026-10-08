# Phase 0I-R Sec. 11/12/13 — Scope of the realizability and Z5 claims

## 1. What Phase 0I got right, and which must not be weakened

**DEFECT #33 stands in full.** The Phase-0H bound `h_sub,min` = 1.176–1.426 mm was **not
universal**. It is specific to architectures in which the converter components occupy the
substrate thickness. The corrected, retained claim:

| architecture | does converter component height constrain `h_sub`? |
|---|---|
| **Z1 embedded** | **YES** — the LS GaN, flying capacitor and inductor are inside the substrate power layers |
| Z2 backside | **NO** — the converter is below the substrate |
| Z4 separate power die | **NO** — the converter is above the substrate |
| Z5 lateral | **NO** — the converter is beside the die |

Nothing in this audit reduces that. It remains one of the most consequential structural
corrections in the project.

## 2. What Phase 0I over-claimed: two different things called "realizable"

Phase 0I's tables carry a `buildable: yes` column and the narrative says non-embedded
architectures "reach the source-demonstrated 0.300 mm". Both are true of **one** constraint
and were allowed to read as true of **all** constraints.

The 0.300 mm figure is derived from exactly one source fact: June-2026 Table III gives power-
layer TSVs of `d` = 30 µm at `h` = 300 µm, a demonstrated aspect ratio of 10:1. That
establishes that a **300 µm substrate carrying a TSV field** is a demonstrated technology
point. It establishes nothing else.

**It does not establish** that a complete Z2 or Z4 package at 0.300 mm satisfies:

| constraint | status in this project |
|---|---|
| backside clearance for a 1.23 mm converter chiplet under the substrate (Z2) | **NOT MODELLED** |
| power-die attach and its 1.23 mm stack between substrate and compute die (Z4) | **NOT MODELLED** |
| cooler / cold-plate clearance | **NOT MODELLED** |
| board clearance and standoff once the converter occupies the board side (Z2) | **NOT MODELLED** — Phase 0I noted the conflict with the BGA field but did not resolve it |
| bump-stack height budget | partially — BGA geometry is sourced, the rest is not |
| cavity, lid and stiffener rules | **NOT MODELLED** |
| package handling and warpage-at-reflow limits | **NOT MODELLED** (and Phase 0H showed the reflow allowables are inadmissible for the operational state anyway) |
| mechanical integrity of a 0.300 mm substrate carrying a 22.36 mm die | **NOT MODELLED** |
| the full manufacturing design-rule set | **NOT AVAILABLE** — no process design kit exists for this system |

## 3. The corrected wording

Everywhere the current-facing text asserted a thin-substrate bound, it now reads:

> **COMPONENT-HEIGHT-REALIZABLE UNDER THE CURRENT Z-ARCHITECTURE MODEL DOWN TO 0.300 mm.**

and the 0.300 mm figure is described as a **source-demonstrated substrate / TSV-layer
thickness**, never as a manufacturability guarantee.

What that phrasing preserves: the whole of DEFECT #33, because the correction was always
about *which components constrain the substrate*, not about whether every other packaging
rule is satisfied. What it removes: an implication Phase 0I never tested.

## 4. Sec. 13 — the Z5 claim was too broad

Phase 0I wrote *"Z5 is eliminated"* and read its ~768 W of RDL loss as pricing 2.5D as a
class. That over-reaches.

What the result actually proves: **the tested Z5 topology — in which a long lateral
interposer path carries the ~1 V / 1 kA rail — is electrically unattractive**, at 768.07 W of
modelled RDL loss and 52.8 % system efficiency.

What it does not prove: that 2.5D integration is infeasible. Untested alternatives that would
change the answer include higher-voltage lateral distribution, distributed conversion across
the interposer, shorter low-voltage runs, intermediate-voltage distribution with local
point-of-load conversion, and different plane geometries. **None of those were modelled**, and
Phase 0I-R does not model them either — it only corrects the claim.

Corrected wording:

> **The tested Z5 low-voltage-lateral topology is electrically eliminated by approximately
> 768 W of modelled RDL loss.**

Never: "2.5D is eliminated."

## 5. What remains genuinely open

* **Complete packaging realizability of the thinnest non-embedded stack.** This is now stated
  as an open item rather than implied closed.
* **MLCC height**, still OPEN, which is why the embedded bound is a 250 µm band and — as Sec.
  14 of the closure report shows — why the Z1-versus-Z4 electrical comparison inherits an open
  input.
* **2.5D variants other than the tested low-voltage-lateral topology.**
