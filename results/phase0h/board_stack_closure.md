# Phase 0H Sec. 11 — Board stack: what could be sourced, and what stays an envelope

## 1. The question

Phase 0G closed the **sign** question: all five explicit board cases preserve the free-package
thickness direction, so no board in the calibrated envelope reverses the mechanical preference.
What stayed open is **magnitude**: the mounted warpage range of 9.7–29.2 µm rests on an
assumed laminate and is an engineering envelope, not a prediction of any real assembly.

Phase 0H asks whether the reference system's actual board can be reconstructed.

## 2. What the reference system specifies

June-2026 Table III gives the vertical-interconnect technology parameters, and they were
already used to build the explicit BGA model in Phase 0G:

| parameter | value | used for |
|---|---|---|
| BGA diameter `d_c` | 400 µm | ball geometry |
| BGA height `h_c` | 300 µm | standoff |
| BGA pitch `p_c` | 800 µm | area fraction `π(0.4)²/4/(0.8)² = 0.19635` |
| BGA area `A_c` | 125,663 µm² | cross-check (consistent) |
| BGA resistance `R_c` | 0.3 mΩ | electrical |
| BGA material | solder, resistivity 130 nΩ·m | material identity |
| # VICs (48 V→1 V) | 132 BGAs, 85 mm² | array extent |

**These are the only board-interface numbers the reference system publishes**, and they
describe the *interconnect*, not the *board*.

On the board itself, June-2026 is deliberately non-committal. Table III labels the platform
row: *"PCB, wafer, panel or any other system integration platform"*. The framework is written
to be platform-agnostic.

## 3. What could not be sourced

| quantity needed for a predictive board model | status |
|---|---|
| PCB thickness | **NOT SPECIFIED** by the reference system |
| layer count | **NOT SPECIFIED** |
| copper plane fractions per layer | **NOT SPECIFIED** |
| laminate modulus (E_x, E_y, E_z) | **NOT SPECIFIED** |
| orthotropic elastic constants | **NOT SPECIFIED** |
| CTE_x / CTE_y / CTE_z | **NOT SPECIFIED** |
| solder-mask contribution | **NOT SPECIFIED** |
| BGA map beyond count and pitch | partially — 132 balls, 85 mm², pitch 800 µm |
| ball alloy | "solder", with resistivity only — no mechanical properties |

Nothing here is a retrieval failure that a better search would fix. The reference framework is
platform-agnostic **by design**, so a board specification does not exist to be found.

## 4. Decision: the envelope is retained, and it is retained honestly

The Phase-0G board envelope stays as the model:

| case | t (mm) | E (MPa) | ν | CTE (ppm/K) |
|---|---|---|---|---|
| compliant | 0.80 | 12,000 | 0.20 | 18 |
| fr4_1p6mm | 1.60 | 20,000 | 0.20 | 18 |
| fr4_2p4mm | 2.40 | 20,000 | 0.20 | 18 |
| fr4_3p2mm | 3.20 | 20,000 | 0.20 | 18 |
| stiff_metal_backed | 2.00 | 70,000 | 0.30 | 12 |

with the BGA layer built from the **sourced** June-2026 geometry (0.4 mm balls, 0.8 mm pitch,
area fraction 0.19635) and `E_solder = 20 GPa` from the STAMP-2.5D material table.

Two properties of this envelope are what make the Phase-0G conclusion safe despite the missing
data, and both were demonstrated rather than assumed:

1. **The sign is invariant across it.** `S_h < 0` for every case, from the most compliant to
   metal-backed — a 6× span in flexural rigidity.
2. **The model is continuous with its own limits.** A vanishing board returns the free package
   to +18.1 % (the residual being the BGA layer's own contribution), and a stiff CTE-matched
   board flattens it to 2.67 µm. It responds correctly to both stiffness and CTE.

## 5. What may and may not be said

**May be said:** the mechanical thickness and footprint *directions* for a mounted assembly,
because they are invariant across the whole envelope.

**May NOT be said:** any absolute mounted warpage as a prediction. The values 9.7–29.2 µm (and
up to 38.7 µm with a 175 °C stress-free reference) are what *this envelope* produces. A real
board with copper planes, a stiffener, an orthotropic laminate and a genuine ball map would
give different magnitudes, and the direction of that difference is not known.

**Also may not be said:** that the envelope is conservative. It is not known to be. It brackets
plausible boards; it does not bound the worst case.

## 6. What would close it

A board specification for the target system: stack-up with layer count and copper fractions,
laminate supplier data (orthotropic E and CTE), solder-mask, stiffener or lid if present, and
the ball map. This is product data, not literature — it cannot be sourced from a paper, and the
reference framework does not carry it because it is written to span PCB, wafer and panel
platforms.
