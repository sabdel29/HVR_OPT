# Phase-0E — RDL / Interposer Power-Stack Literature Audit

## 1. What Phase 0D-R left open, and why it mattered

Phase 0D-R validated the **numerics** of a 2-D resistive sheet (FD vs MOOSE, 0.33-0.45 %).
It did not validate the **physical sheet**. Those were four unsourced choices:

| parameter | Phase-0D-R value | status then |
|---|---|---|
| Cu thickness | 5 µm | ASSUMPTION ("Phase-0A recorded 'UNSPECIFIED default'") |
| metal occupancy | 0.60 | ASSUMPTION |
| layer count | 1 | ASSUMPTION |
| ground return | "multiply supply loss by 2" | ASSUMPTION |

Because `P_RDL` turned out to be the dominant package-distribution term, these four numbers
set the magnitude of the dominant term. That is why closing them was the highest-priority
task of Phase 0E.

## 2. Search performed

| source | outcome |
|---|---|
| June-2026 framework paper (arXiv:2606.28837), full text retrieved | **no RDL trace dimensions**: "Although the specific trace dimensions depend on process technology..." Gives the vertical interconnect table and the VIC allocation. |
| June-2026 framework **source code** (`Scalable_Integrated_VR/src/`) | **no metal stack at all** — a lumped `rho_mohm_per_mm = 0.5` distance model (`DVPDRoutingModel.compute_ppdn_loss`, labelled "GLSVLSI'24 ROUTING LOSS MODEL"). No thickness, no layer count, no occupancy. |
| **ECTC-2024** "Vertical Power Delivery for HPC Systems with Buck-Derived Regulators" (PDF in workspace) | **CLOSES THE STACK** — Table I gives the RDL trace row explicitly. |
| **ISCAS-2024** "Design Considerations for DC-DC VRs in DVPD Systems" (PDF in workspace) | independent confirmation of RDL **thickness**. |
| Web search for process/foundry stacks | **UNAVAILABLE** — `WebSearch` is disabled by organisation policy in this environment. arXiv API and Semantic Scholar API were used instead (Sec. 6). |

Both ECTC-2024 and ISCAS-2024 were previously recorded as "full text not retrieved
(paywalled)". They are in fact present in the workspace as PDFs and were read in full for
Phase 0E. **That earlier statement is corrected.**

## 3. The sourced stack

ECTC-2024 Table I, "Traces" block, verbatim:

| Integration level | Type | Material | Thickness (µm) | Width (µm) | Space (µm) | P/G layers | R/l (Ω/m) | R'_Heff (Ω/m) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| RDL | Trace | Cu | **10** | **10** | **2** | **2** | 170 | 0.046 |
| PCB | Trace | Cu | 35 | 152 | 456 | 1 | 3.2 | 0.087 |

### 3.1 Self-consistency — the table reproduces itself to 4 significant figures

With ρ_Cu = 17 nΩ·m (the paper's own value) and A_L = 500 mm²:

```
R/l      = rho/(W t)                     RDL: 170.00 Ohm/m   (printed 170)
                                         PCB:   3.195 Ohm/m  (printed 3.2)
N_Hmax   = sqrt(A_L)/(W+S)               RDL: 1863 traces ; PCB: 36.8 traces
R'_Heff  = (R/l) / (n * N_Hmax)          RDL: 0.0456 Ohm/m  (printed 0.046)
                                         PCB: 0.0869 Ohm/m  (printed 0.087)
```

Both rows match. The stack is therefore not merely quoted, it is **verified against the
source's own derived quantity**.

### 3.2 Resolving the layer-count ambiguity

"P/G layers = 2" could mean 2 layers total (1 VDD + 1 GND) or 2 layers per network. The
**PCB row decides it**: it carries "P/G layers = 1", and a PCB power distribution cannot have
zero return path — so the column counts layers **per network**. The formula then uses `n` =
the column value for one network, and reproduces both printed `R'_Heff` values.

**Adopted: the RDL carries 2 VDD layers and 2 GND layers.**

### 3.3 Occupancy is derived, not assumed

Occupancy follows from the line/space design rule and is no longer a free parameter:

    occ = W/(W+S) = 10/12 = 0.8333

## 4. Candidate stacks carried as an envelope

| stack | t_Cu | W/S | n_VDD | n_GND | occupancy | R_sq per net | status |
|---|---:|---|---:|---:|---:|---:|---|
| **ectc2024_primary** | 10 µm | 10/2 µm | 2 | 2 | 0.8333 | **1.020 mΩ/sq** | SOURCE_BACKED |
| ectc2024_one_per_net | 10 µm | 10/2 µm | 1 | 1 | 0.8333 | 2.040 mΩ/sq | rejected by the PCB-row check; kept as a bound |
| iscas2024_variant | 10 µm | 2/2 µm | 1 | 1 | 0.5000 | 3.400 mΩ/sq | SOURCE_BACKED (pessimistic width reading) |
| phase0dr_legacy | 5 µm | — | 1 | 0 | 0.60 | 5.667 mΩ/sq | ASSUMPTION (superseded) |

ISCAS-2024 states "trace width (32 µm on PCB and 2 µm for RDL), and thickness (152 µm on PCB
and 10 µm for RDL)". ECTC-2024 lists W = 10, S = 2 for the same group's RDL, so the ISCAS
sentence appears to transpose width and space. **Both readings agree that t_Cu = 10 µm, so
the thickness is doubly sourced**; the width reading is carried as the pessimistic bound.

## 5. Consequence

    sigma_s(Phase-0E) / sigma_s(Phase-0D-R) = (2 x 10 um x 0.8333) / (1 x 5 um x 0.60) = 5.556

The Phase-0D-R RDL sheet was **5.56x too resistive**. Every Phase-0D-R RDL loss magnitude
scales down by that factor before any other correction. The ground return is now an explicit
second network rather than a factor of two; for a symmetric P/G stack the factor happens to
come out at 2, but it is now *derived* and an asymmetric stack would give something else.

## 6. What is still NOT closed

* **The dielectric stack** (thickness, material, via transitions between RDL layers) is not
  given by any retrieved source. It does not enter a DC resistance calculation, but it would
  enter inductance, and it enters the mechanical model.
* **Inter-layer stitching-via density.** The solver supports finite stitching conductance;
  with none stated, ideal stitching is used, which is the optimistic bound. The multilayer
  solver reduces exactly to a single sheet of summed conductance in that limit (unit-tested).
* **Whether the RDL of the June architecture is the ECTC-2024 stack at all.** These are two
  papers by the same group with *different* TSV technologies (ECTC: d = 5 µm, h = 50 µm,
  p = 10 µm; June: d = 30 µm, h = 300 µm, p = 60 µm), so the RDL may differ too. The ECTC
  stack is the only sourced RDL from this group and is adopted as primary, with the envelope
  above bounding the alternative readings.
* **ECTC Table II's absolute PPDN magnitudes are not reconstructible** from the printed stack
  and equations — see `ectc_table2_validation.json`. Applying eq. (1)+(3) literally gives
  0.22-0.35 W against published 39.5-76 W, and no segment count `S` closes a gap that scales
  as 1/S. The Phase-0E sheet solver gives 104 W for the periphery case (published 76 W, +37 %)
  and much less for the dense under-die cases. **The stack parameters are validated; the
  published loss magnitudes are not reproducible, so RDL loss magnitudes remain provisional.**

## 7. Claim language this permits

Allowed: *"under the ECTC-2024 sourced RDL stack (10 µm Cu, 10/2 µm line/space, 2 VDD +
2 GND layers), RDL loss is X W"*.
Not allowed: *"the RDL loss is X W"* without the stack qualifier, and no absolute efficiency
claim, because the loss magnitudes could not be cross-validated against the source's own
published totals.
