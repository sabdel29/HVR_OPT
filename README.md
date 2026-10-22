# HVR_OPT — Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery

A framework that evaluates how a kilowatt-class power-delivery architecture behaves **on the
physical package** — electrically, thermally, mechanically, and in terms of whether it can
actually be routed — rather than evaluating those domains one after another on a geometry the
electrical design has already fixed.

> **Status:** paper-frozen at Phase 0M-R3C. Manuscript ready for coauthor review.
> Full current state: [`CURRENT_STATUS.md`](CURRENT_STATUS.md).

---

## The problem

Deliver **1 kW at 1 V** to a 22.36 × 22.36 mm compute die.

That is **~1000 A**. At that current the delivery network, not the converter, limits
achievable efficiency: I²R loss in a 1 V rail crossing even a few millimetres of package
metal becomes comparable with the load itself. So the rail must be converted close to the
load — and then **where** conversion happens, and **which rail crosses which piece of package
interconnect**, start to matter enormously.

## The converter

Synthesised from a 90-device library rather than assumed:

| | |
|---|---|
| topology | hybrid 3:1 switched-capacitor + **two-phase** buck, $K=3$ parallel inductor branches ($K_A=2$ driven in phase A) |
| conversion | 48 V → 16 V intermediate → 1 V |
| cells | M = 49, each 20.408 A into 5.61 mm² |
| duty cycle | 0.0625 |
| switching frequency | 805.17 kHz |

## The two architectures

Both use the *same* converter. They differ in where it sits, and that changes which rail the
vertical interconnect carries:

| | **Z1 embedded** | **Z2 backside** |
|---|---|---|
| converter cells | inside the 1.30 mm package substrate | on the underside of a 0.30 mm substrate |
| through-substrate field carries | the **48 V input** rail, low current | the **1 V output** rail, full cell current |
| that field dissipates | ≈ 0 W | 0.991 W |

The same nominal via field, same geometry — three orders of magnitude apart in loss. This is
why "TSV resistance" alone is not a meaningful architecture metric: what matters is
**geometry × assigned rail × current × allocation**.

## What is coupled

    converter synthesis
        → explicit physical stack (component tiers, heights, per-tier area)
        → rail-aware power delivery network (RDL, vias, bumps, intra-cell routing)
        → anisotropic package thermal transport  ⟷  electrical  (fixed point, 3 iterations)
        → thermoelastic deformation of the package                (one-way, after convergence)
        → corner-joint displacement driver Δu_c
        → local viscoplastic solder submodel → inelastic response Δε_in

Everything is evaluated on **one** physical stack.

## Headline results

**Physical realizability is an active architecture constraint.** Two component tier orderings
with identical component set, count, per-tier area and total stack height differ by a factor
of six in worst build-up via aspect ratio:

    reference ordering      worst via AR = 5.05
    repartitioned ordering  worst via AR = 0.833

Only the tier *locations* were permuted; the electrical topology is untouched. A physically
problematic architecture becomes geometrically realizable for free.
Status: **geometrically realizable / process-conditional** — *not* manufacturing-qualified.

**Peak temperature does not uniquely rank local mechanical response.** On the frozen pair:

| | Z1 embedded | Z2 backside | |
|---|---:|---:|---|
| T_max | 118.32 °C | 126.46 °C | Z2 **+8.14 K hotter** |
| Δu_c displacement driver | 4.6252 µm | 3.8714 µm | Z2 **16.3 % lower** |
| Δε_in inelastic response | 1.4072×10⁻² | 1.1478×10⁻² | Z2 **18.43 % lower** |

Z2 is the hotter architecture **and** the one with the lower local inelastic response. The
mechanism is measured, not asserted: the displacement reduction alone would give 19.39 %, and
Z2's hotter joint gives 0.75 % of it back.

**Δε_in is a response — not damage, not life, not failure.** No damage law, life relation or
allowable is established here, and none is applied. The ordering is robust; the *magnitude*
is conditional on a solder model used far outside its fitted stress window.

## Manuscript

> Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery:
> Architecture-Dependent Inelastic Response and Physical Realizability

`manuscript/ETM_DVPD_JOURNAL_MANUSCRIPT.pdf` — 15 pages, builds clean, 25 references.

New to this? Read **[`manuscript/HANDOVER_README.md`](manuscript/HANDOVER_README.md)** —
written for someone picking the paper up cold.

## Where things live

| path | what |
|---|---|
| `manuscript/` | the paper, its figures, and every supporting audit |
| `results/phase0mr3c/` | **the frozen final state** — all authoritative numbers |
| `results/PAPER_FREEZE_DECISION.md` | what was frozen, and why development stopped |
| `results/PAPER_CLAIM_MATRIX.csv` | permitted and forbidden wording per claim |
| `results/ETM_DVPD_FULL_TECHNICAL_REPORT.md` | the long-form technical record |
| `configs/phase0mr3c/frozen_pair_*.yaml` | the two frozen architectures |
| `scripts/` | every analysis, audit and figure generator |
| `tests/` | the regression and semantic-guard suite |
| `Scalable_Integrated_VR/` | submodule — the converter loss model this framework imports |

Which directories are authoritative and which are historical:
[`SNAPSHOT_MANIFEST.md`](SNAPSHOT_MANIFEST.md).

## Reproducing

See [`REPRODUCE.md`](REPRODUCE.md). The short version:

    export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH   # project python + CalculiX
    python scripts/phase0mr3c/audit_manuscript.py          # → MANUSCRIPT AUDIT PASSED

That single command re-checks 82 numerical values in the manuscript against the frozen data
files. If the science is intact, it passes.

## A note on scope

This framework is an **evaluator**, not an optimizer. It does not search for an optimum and
does not claim one. Its contribution is showing which questions must be asked of the physical
package *during* architecture selection rather than after it — and being explicit about which
of its own answers are robust and which are conditional.
