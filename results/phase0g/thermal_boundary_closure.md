# Phase 0G Sec. 8/9/10 — Thermal-boundary closure and the robustness of the mechanical
# ordering to it

## 1. The open model-form question

Every phase of this project has cooled the package through an **equivalent Robin boundary on
the TIM top surface**. June-2026 does not: it places micro-channels **inside the substrate,
adjacent to the GaN switch layer** (Sec. IV-D). Phase 0F calibrated the top boundary to match
the reference junction temperature (`h_top = 166,000 W/m²K` → `T_max = 84.07 °C`, converged)
and recorded the mismatch as a caveat, but did not test what the mismatch does to any
conclusion.

Phase 0F also established the second half of the problem: the substrate-side topology
**saturates**. Driven to the ceiling `h = 398,672 W/m²K` it reaches only **90.96 °C**,
6.96 K above the reference junction temperature, and does not converge. Substrate-side
cooling alone cannot reproduce the reference thermal state at 1 kW.

The two topologies therefore bracket a genuine model-form uncertainty rather than a parameter
uncertainty, and the mechanical ordering — the only ordering still standing after Sec. 6/7 —
had to be tested across it.

## 2. Stated model-form limit of the test

The substrate-side film is applied to the substrate **underside**, which is an external face
only when no board is attached. With an explicit BGA + PCB the same surface is internal and
CalculiX cannot carry a film there. The substrate topology is therefore run on `BC_A`/`BC_B`
only. For the mounted assembly the thermal boundary is instead perturbed over a **4× band**
in `h_top` (×0.5, ×1, ×2), which moves both the temperature level and the through-thickness
gradient — the two channels by which a thermal boundary can reach the mechanics at all.

A second consequence is recorded rather than hidden: under **bottom** cooling, `BC_B`'s
0.3 mm compliant support layer sits between the substrate and the coolant and insulates it.
`BC_A` reaches 81.30 °C at `h = 0.80 mm` where `BC_B` reaches 95.63 °C. Under substrate-side
cooling the two restraints are **not thermally comparable**, and only their internal
thickness trends may be compared, not their absolute values.

## 3. Results

| thermal boundary | restraint | T_max 0.80 / 2.00 mm (°C) | W(0.80) µm | W(2.00) µm | S_h |
|---|---|---|---|---|---|
| top, calibrated | BC_A | 84.65 / 84.16 | 11.1708 | 1.2719 | **−0.8861** |
| top, calibrated | BC_B | 84.35 / 84.15 | 0.3722 | 0.8887 | **+1.3875** |
| top, calibrated | BOARD FR-4 1.6 | 84.31 / 84.15 | 25.1482 | 14.0309 | **−0.4421** |
| top, calibrated | BOARD compliant | 84.32 / 84.15 | 29.2334 | 9.8448 | **−0.6632** |
| substrate, saturated | BC_A | 81.30 / 98.09 | 16.2087 | 9.2238 | **−0.4309** |
| substrate, saturated | BC_B | 95.63 / 110.39 | 0.4828 | 0.9099 | **+0.8845** |
| top × 0.5 | BOARD FR-4 1.6 | 98.72 / 98.53 | 31.2170 | 17.4231 | **−0.4419** |
| top × 0.5 | BOARD compliant | 98.73 / 98.53 | 36.2124 | 12.1790 | **−0.6637** |
| top × 2 | BOARD FR-4 1.6 | 77.18 / 77.03 | 22.1457 | 12.3525 | **−0.4422** |
| top × 2 | BOARD compliant | 77.19 / 77.03 | 25.7804 | 8.6900 | **−0.6629** |

## 4. Findings

**(a) No thermal boundary flips any sign.** `BC_A` and every explicit board stay negative;
`BC_B` stays positive. The Sec. 7 conclusion — that the reversal belongs to BC-B and not to
board mounting — is **not an artifact of the cooling model**.

**(b) The mounted normalized response is essentially thermal-boundary-invariant.** Across a
4× range in `h_top` and a 21.5 K span in operating temperature:

| board | S_h at ×0.5 | S_h at ×1 | S_h at ×2 | spread |
|---|---|---|---|---|
| FR-4 1.6 mm | −0.4419 | −0.4421 | −0.4422 | **0.07 %** |
| compliant | −0.6637 | −0.6632 | −0.6629 | **0.12 %** |

The normalized thickness response is a **structural property of the assembly** — set by its
stiffness and CTE architecture — not a thermal one. The thermal boundary moves magnitudes
substantially (22.1 → 36.2 µm at `h = 0.80 mm`, a 64 % range) while leaving `S_h` unchanged
to three decimal places.

**(c) Substrate-side cooling changes magnitudes strongly and compresses the trend.** For
`BC_A`, warpage at `h = 0.80 mm` rises from 11.17 µm to 16.21 µm (+45 %) and `S_h` weakens
from −0.886 to −0.431, because a thicker substrate now sits between the heat and the coolant
and the temperature *rises* with thickness (81.30 → 98.09 °C) instead of falling. The trend
survives; it is halved.

**(d) The substrate-side topology cannot meet the reference thermal target.** At 110.39 °C
for `BC_B` at `h = 2.00 mm` the design is far outside the reference operating point. This is
a **thermal feasibility problem** for substrate-side-only cooling at the 1 kW reference, and
is recorded as such — it is not a mechanical finding.

## 5. Sec. 9 — independent thermal validation

Phase 0F validated the decisive thickness pair against an independent MOOSE
`heat_transfer-opt` solve of the same problem (`thermal_moose_1kw.csv`):

| case | CalculiX T_max (°C) | MOOSE T_max (°C) | Q_out (W) | energy residual |
|---|---|---|---|---|
| h = 0.80 mm | 84.65 | 87.44 | 1124.70 | −2.7 × 10⁻⁸ % |
| h = 1.50 mm | 84.21 | 86.43 | 1124.70 | −2.7 × 10⁻⁸ % |

The two codes agree to **2.2–2.8 K on T_max (2.6–3.3 %)** and both close their energy balance
to 3 × 10⁻⁸ %. Critically, **both give the same thickness trend** — the thinner substrate
runs hotter by 1.01 K (MOOSE) against 0.44 K (CalculiX) — so the thermal input to the
mechanical ordering is independently corroborated in sign.

The residual 2–3 K offset is a known consequence of the two codes clipping the overhanging
tile differently at the die edge, diagnosed in Phase 0F. It is not resolved here and does not
affect the ordering.

**The Icepak route remains unusable.** The Phase-0E Icepak solve returned exactly 5000 K on
every object — a solver clamp caused by applying an external boundary condition to an
internal solid/air interface. That result was discarded, has never been used, and is not used
here.

## 6. Verdict on the thermal boundary

1. The **top-surface calibrated boundary is retained** as the authoritative thermal model. It
   is the only one that reaches the reference junction temperature, and it is corroborated by
   an independent code to 2.2–2.8 K.
2. The **model-form mismatch with June's embedded channels is now bounded, not merely
   flagged**: it changes warpage magnitudes by up to 45 % and weakens `S_h` by roughly half,
   but flips no sign and changes no ordering.
3. **The mechanical conclusions of Sec. 6/7 survive thermal-boundary uncertainty**, which is
   one of the two conditions set for recommending the ETM optimizer. The other condition —
   an admissible mechanical criterion — is **not** met (Sec. 12).
4. Substrate-side-only cooling is recorded as **thermally infeasible at the 1 kW reference**
   under this model, an independent finding that does not bear on the mechanical verdict.
