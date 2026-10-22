# Architecture claim matrix

Phase 0N. One row per architecture-level claim currently made or implied.
`confidence`: **HIGH** = reproduced from artifacts and robust to the corrections tested;
**CONDITIONAL** = reproduced but dependent on an unsourced choice; **UNSUPPORTED** = the
evidence does not carry it.

| # | claim | current manuscript wording | evidence | confidence | action | final allowed wording |
|---|---|---|---|---|---|---|
| 1 | Z1 embeds the converter in the substrate | "the converter cells are built into the $1.30$\,mm substrate" (Fig. 2 caption, §II) | Mesh: 1226 µm `tile_band` inside a 1300 µm substrate, converter in 30.5 % of the area | **CONDITIONAL** | **REWORD** | "the low-side devices, flying capacitors and inductors — 1226 µm of the 1921 µm component stack — are embedded in the 1.30 mm substrate" |
| 2 | The converter stack is 1921 µm | Table I row "Converter stack height 1921 µm", adjacent to "Substrate thickness 1.30 mm" | 1921 = 685+100+606+500+3×10, the four-tier **template**; only 1226 µm is embedded | **UNSUPPORTED as placed** — the adjacency implies 1921 µm fits in 1300 µm | **REWORD + FOOTNOTE** | "Converter component stack 1921 µm (of which 1226 µm is embedded; the 685 µm high-side device is flip-chipped below the substrate and is not represented in the thermomechanical geometry)" |
| 3 | The high-side device is below z = 0 | not stated in the manuscript | `zarch.embedded_cell_um()` docstring cites June-2026 Sec. II; **no geometry exists** below z = 0 except BGA and board | **UNSUPPORTED as modelled** | **DISCLOSE** | "the high-side device is placed outside the modelled domain; its loss is deposited in the embedded band" |
| 4 | Z2 mounts cells on the substrate underside | "the cells are mounted on the substrate underside" (§II) | Mesh: a **full-area** 1226 µm `hvr_effective` slab, 1103.40 mm³ vs Z1's 337.02 mm³ | **UNSUPPORTED** — the model is not laterally distributed | **REWORD + CORRECT** | "the backside converter is represented as a continuous layer of converter medium below the substrate; its lateral subdivision into cells is not resolved" |
| 5 | The comparison isolates placement | "the identical field carries the 1 V output rail"; architecture framed as placement | Converter volume differs by **3.27×** between the two | **UNSUPPORTED** | **DISCLOSE** | "the two architectures differ in converter placement **and** in the modelled lateral extent of the converter medium" |
| 6 | Z2 runs +8.14 K hotter | Table, abstract, §V | Reproduced exactly; but a silicon backside fill gives **−2.77 K** | **UNSUPPORTED** — the sign is not robust | **WITHDRAW the ordering claim** | "the temperature ordering depends on the backside fill and is not established" |
| 7 | Z2 carries 16.3 % less Δu_c | abstract, §V | Reproduced exactly; spans **3.59 %–65.56 %** across defensible fills | **CONDITIONAL** | **QUALIFY** | "16.3 % for the frozen backside treatment; the magnitude is conditional on an unsourced fill and spans 3.6–65.6 % over the tested bracket" |
| 8 | Δu_c ordering Z2 < Z1 | abstract, §V | D_u > 1 in **all three** fills (1.0373, 1.1947, 2.9035) | **HIGH** | **KEEP, state as direction only** | "the displacement driver is lower for the backside architecture in every backside treatment tested" |
| 9 | Z2 carries 18.4 % less Δε_in; D_ε = 1.2260 | abstract, §V | Local submodel **not rerun** for the variants; driven by Δu_c and T_joint, both of which move | **CONDITIONAL** | **QUALIFY** | "conditional on the frozen backside treatment and on the constitutive extrapolation already disclosed" |
| 10 | Worst via AR 5.05 → 0.833 by permutation | §IV | `routing_feasibility.csv`; unaffected by the backside fill (a routing-domain result) | **HIGH** | **KEEP** | unchanged |
| 11 | The package is geometrically realizable | "geometrically realizable partition" (abstract) | Only **vertical-interconnect** realizability is shown; stack and assembly realizability are not | **UNSUPPORTED as scoped** | **NARROW** | "a geometrically realizable **vertical interconnect**"; keep component-stack and board-assembly realizability explicitly NOT ESTABLISHED |
| 12 | Topology is a 3:1 SC + 3-phase buck | Table I (pre-correction) | **WRONG.** The component count is blind to switching phases. The ripple equation decomposes exactly as K_A driven + (K−K_A) freewheeling, so there are **two** phases and K=3 is the branch count | **WITHDRAWN** | **CORRECTED** | "3:1 SC + two-phase buck with K=3 parallel inductor branches, K_A=2 in phase A" |
| 12b | 6.803 A is the per-phase current | §IV | It is the **branch** current I_cell·B_i/N; equal to I/K only because K=N=3 here | **WITHDRAWN** | **CORRECTED** | "per-inductor branch current" |
| 13 | The three phases are interleaved | **not claimed** | No phase-shift construct exists; `coupling_k = 0.0` | n/a | **GUARD** | never write "interleaved" |
| 14 | Devices are EPC2014C / EPC2057 | Table I | Electrical model uses them; **stack heights use EPC2212 / EPC2090** | **UNSUPPORTED as a single set** | **DISCLOSE** | state both pairs and which quantity each governs |
| 15 | DVPD converts close to the load | abstract, §I | Correct but incomplete: omits lumped VPD, so the discriminator is invisible | **CONDITIONAL** | **EXPAND** | add the LPD → lumped VPD → DVPD taxonomy with the residual lateral low-voltage path as the discriminator |
| 16 | Substrate is a package substrate | "package substrate" throughout | Modelled as **silicon** with TSVs, 30 × 30 mm (ASSUMPTION) | **CONDITIONAL** | **DISCLOSE** | "a silicon power substrate" — do not imply an organic FC-BGA core |

---

## Thesis-contribution status (Phase 0N-R, Section 17)

### A — proven and physically robust now

| claim | why it survives |
|---|---|
| **VPD vs DVPD distinction**: the discriminator is the spatial distribution of conversion and the residual low-voltage lateral path, not proximity | Quoted verbatim from two sources held in full (`10.1109/TCPMT.2026.3724907`, `10.1109/ECTC51529.2024.00364`). Independent of our geometry. |
| **Rail-aware vertical-interconnect loss**: the same vertical structure dissipates ≈0 W or 0.991 W depending only on which rail crosses it | A statement about rail assignment and current, derived in the electrical domain; unaffected by the backside fill or device heights. |
| **Conductor-plane topology, not material-layer count, governs via realizability** | Routing-domain result from `routing_feasibility.csv`. |
| **A pure tier permutation removes the deep crossing: worst via AR 5.05 → 0.833** | Routing-domain result, independent of substrate thickness and of the backside fill. **But it is NOT independent of device height** — re-checked during this phase: the baseline's worst net (`hs_to_cf`) crosses the low-side tier, so with the corrected EPC2057 height it becomes **5.32**, and the improvement factor **6.06× → 6.38×**. The repartitioned 0.833 is unchanged (it crosses the 100 µm capacitor tier). The mechanism and the conclusion are robust; **the baseline number must be restated as 5.32** when the corrected device geometry is adopted. |
| **The global→local mechanical methodology** | Keeping warpage, driver (Δu_c), response (Δε_in), damage, life and failure as six distinct quantities is a methodological contribution independent of the numbers. |
| **Two-phase HVR semantics** (Phase 0N-R): K is the branch count, K_A the phase-A branch count, branch current `I_cell·B_i/N` | Derived from the implementation and verified to machine precision against the ripple equation. |

### B — numerically demonstrated but geometry-conditional

| quantity | frozen value | why conditional |
|---|---|---|
| T_max, Z1/Z2 | 118.32 / 126.46 °C | sign of ΔT reverses with the backside fill |
| die warpage | 41.616 / 38.916 µm | same |
| Δu_c | 4.6252 / 3.8714 µm (16.3 %) | magnitude spans 3.6–65.6 % over surrogates |
| Δε_in | 1.4072 / 1.1478 ×10⁻² (18.43 %) | inherits the above **and** was not rerun for the surrogates |
| converter loss split | 137.292 / 139.659 W | depends on the thermal field, hence on the same geometry |

### C — invalidated or withdrawn

| withdrawn claim | replaced by |
|---|---|
| "Z2 runs +8.14 K hotter" as an architecture result | the sign is not established |
| "16.3 % lower driver" as an architecture result | conditional magnitude; direction holds only across the surrogates tested |
| "18.43 % lower response" as an architecture result | doubly conditional |
| "same converter, only placement differs" | false in the frozen mesh: 337.02 vs 1103.40 mm³ |
| "the package is geometrically realizable" | only the **vertical interconnect** is |
| "3:1 SC + 3-phase buck" | 3:1 SC + **two-phase** buck, K = 3 branches |
| "per-phase current = I_cell/K = 6.803 A" | **branch** current `I_cell·B_i/N` |
| "temperature and mechanical rankings are opposite for these architectures" | peak temperature is not *in general* sufficient; the surrogates include divergent cases |
| Z1's 1.30 mm substrate closes | 8 µm short with the corrected EPC2057 height |
| "worst via AR 5.05" for the baseline tier order | **5.32** with the corrected low-side height; the 0.833 repartitioned value and the conclusion stand |

### D — open

- A physically closed Z1 implementation (bottom substrate or stacked power layers hosting the high-side device; h_sub ≥ 1.308 mm).
- A physically closed Z2 implementation (backside construction and board interface; no literature-supported cross-section was reachable).
- Lateral resolution of the 49 cells in Z2.
- Explicit supply/return geometry in both.
- The local solder response after corrected geometry.
- Absolute life — not attempted, and not attemptable without solder data at the operating stress.
