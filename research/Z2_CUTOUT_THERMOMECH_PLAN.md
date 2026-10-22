# Z2-CUTOUT — thermal and mechanical plan

Phase 0N-R Task E. **A plan, not results.** No ETM run is permitted until the Task G
closure gate is met (`research/Z2_CUTOUT_GEOMETRY.md` §4 and
`research/Z2_CUTOUT_BGA_POWER_RETURN.md` §3 are both still open).

## 1. Why the cutout is not merely a clearance fix

Removing a 23.4 mm square from the board changes two things the frozen model
treats as fixed:

- **Stiffness.** The frozen mesh has a continuous 1.6 mm FR-4 slab under the whole package.
  A frame with a 23.4 mm hole has far less bending stiffness under the die centre, and
  the package is then supported only at its periphery.
- **Cooling.** The frozen model's bottom boundary is a uniform film on a continuous board.
  With a through-cutout the VR cells face **ambient through the hole**, which ARM's FIG. 3
  exploits deliberately with a heat sink on the inductor.

Both act directly on the quantities under audit: warpage, Δu_c, and the critical joint.

## 2. What must be meshed

| element | treatment |
|---|---|
| PCB | **annular frame**, not a full-area slab — no elements inside the cutout |
| BGA | ball field **only** in the board regions surrounding the cutout |
| VR cells | 49 discrete footprints at 2.3685 mm side, **not** a full-area layer |
| land side outside the cells | explicitly defined medium (air / underfill / mold) — currently **undefined**, and Phase 0N showed this choice moves Δu_c by a factor of 18 |
| cell bottom face | thermal boundary, §3 |
| cutout sidewall | lateral clearance, unsourced, bounded 0.5–1.0 mm |

## 3. Backside thermal boundary — a bounded study, not result fishing

No source selects a package thermal solution for this construction, so the boundary is
carried as a **bounded uncertainty** with three defensible corners, reported together:

| # | boundary | rationale |
|---:|---|---|
| 1 | **weak natural convection** on the exposed cell bottoms | the pessimistic corner: cutout open, no dedicated cooling |
| 2 | **conduction to the board frame** around the cutout plus weak convection | the cells are attached to the substrate, which is attached to the frame |
| 3 | **explicit backside TIM + heat sink** dissipating through the cutout | ARM US20260059645A1 FIG. 3 and claims 16/19 — **patent precedent, not demonstrated** |

These bracket the answer; **none is adopted as "the" boundary**, and the spread is to be
reported as the uncertainty it is. Corner 3 additionally consumes vertical space that
§4 of the geometry document has already shown is not available at nominal heights.

## 4. The critical joint must be recomputed

The local solder submodel currently takes the **corner BGA joint of a full-area ball
field**. After the cutout that location may no longer carry a ball, and the stress
distribution certainly changes: the outermost surviving ball ring sits at the cutout edge,
where the frame is stiffest and the package is least supported inboard of it.

**The critical joint must be re-identified from the post-cutout ball field**, not inherited.
Reusing the old corner would be exactly the kind of silent carry-over this audit exists to
catch. Until that is done, no Δu_c or Δε_in from a cutout geometry is meaningful.

## 5. Expected direction, stated as a hypothesis only

A frame is more compliant under the die than a slab, so Z2-CUTOUT would plausibly warp
**more** than the frozen full-slab Z2, not less. The frozen Z2's low Δu_c may therefore owe
something to a board the real construction does not have. **This is a hypothesis to test,
not a finding**, and it is recorded here so the test is not quietly skipped if the number
comes out favourably.
