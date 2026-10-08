# COMPARISON WITH PRIOR DVPD AND PACKAGE CO-DESIGN FRAMEWORKS

Only works whose **full text was read** are scored. Capability is not inferred from a title
or an abstract. Works that could not be obtained in full text from this host are listed at
the end and are not scored.

Legend: **✓** modelled explicitly · **△** partial, assumed or reported as future work ·
**—** not included.

## Works read in full

| key | work | what it is |
|---|---|---|
| **[A]** | Krishnakumar *et al.*, *A Comprehensive Design Framework for Vertical Power Delivery in HPC*, arXiv:2606.28837, Jun. 2026 | the baseline DVPD framework: converter synthesis, interconnect allocation, floorplanning and thermal feasibility in one flow |
| **[B]** | Krishnakumar *et al.*, *Vertical Power Delivery for HPC Systems with Buck-Derived Regulators*, ECTC 2024 | buck-derived VPD; lateral routing loss; effective vertical-routing models over C4 bumps, TSVs and µ-bumps |
| **[C]** | Krishnakumar *et al.*, *Design Considerations for DC-DC Voltage Regulators in DVPD Systems*, ISCAS 2024 | converter design considerations for DVPD; RDL and PCB trace geometry; an Icepak thermal profile for one architecture |
| **[D]** | Wang *et al.*, *Electrothermal Co-optimization of 2.5D Power Distribution Network with TTSV Cooling*, Sci. Rep. 15, 2025 | metaheuristic electrothermal co-optimization of a 2.5-D PDN with thermal TSVs and a manufacturing-cost objective |
| **[E]** | Krishnakumar & Partin-Vaisband, *Vertical Power Delivery for Emerging Packaging and Integration Platforms --- Power Conversion and Distribution*, arXiv:2309.10141, Sep. 2023 | the architecture study that defines the vertical-integration family used here: devices on the interposer periphery, devices embedded beneath the die, and multi-stage variants, at 1 kW and high current density |
| **[F]** | Krishnakumar & Partin-Vaisband, *Dynamic Power Management Methodology for DVPD in HPC Systems*, arXiv:2605.24874, May 2026 | load-aware regulator activation; segment-resolved conduction loss including the path inside the cell; ripple and regulation constraints |
| **[G]** | this work | |

## Capability matrix

Generated from the manuscript table by `scripts/phase0mr3c/sync_prior_comparison.py`. Do not edit by hand.

Legend: **✓** modelled explicitly · **△** partial, assumed or reported as future work · **—** not included.

| capability | [A] | [B] | [C] | [E] | [F] | [D] | [G] |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Converter synthesis from a device library | ✓ | ✓ | ✓ | △ | — | — | ✓ |
| Multi-stage hybrid regulator topology | ✓ | ✓ | ✓ | ✓ | △ | — | ✓ |
| Switching, gate and C_oss loss terms | ✓ | △ | △ | △ | ✓ | — | ✓ |
| Rail-aware per-segment current assignment | △ | △ | △ | △ | △ | — | ✓ |
| Geometry-derived through-substrate via model | ✓ | ✓ | △ | △ | — | ✓ | ✓ |
| Geometry-derived RDL plane model | ✓ | ✓ | ✓ | △ | ✓ | ✓ | ✓ |
| Bump and transition resistance | △ | ✓ | — | ✓ | — | △ | ✓ |
| Intra-converter routing inside the cell | — | — | — | — | ✓ | — | ✓ |
| Temperature-dependent rho and R_on | ✓ | — | — | — | — | ✓ | ✓ |
| Component heights in the stack budget | △ | — | — | △ | — | — | ✓ |
| Component partition across tiers | △ | — | — | ✓ | — | — | ✓ |
| Electrical–thermal fixed point | ✓ | — | △ | — | — | ✓ | ✓ |
| Anisotropic / homogenised thermal model | △ | — | — | — | — | ✓ | ✓ |
| Physical cooling boundary with a stated domain | ✓ | — | △ | — | — | ✓ | ✓ |
| Pump power separated from electronics scope | △ | — | — | — | — | — | ✓ |
| Global thermoelastic package model | — | — | — | — | — | — | ✓ |
| Explicit assembly state, free against mounted | — | — | — | — | — | — | ✓ |
| Local solder inelastic-response model | — | — | — | — | — | — | ✓ |
| Mechanical-to-electrical feedback quantified | — | — | — | — | — | — | ✓ |
| Vertical-interconnect realizability check | — | — | — | △ | — | △ | ✓ |
| Manufacturability separated from feasibility | — | — | — | — | — | △ | ✓ |
| Independent cross-solver validation reported | △ | — | △ | — | — | ✓ | ✓ |
| Computational cost reported | — | — | — | — | — | △ | ✓ |
| Load-dependent operating point | — | — | — | — | ✓ | — | — |
| Regulator activation and power management | — | — | — | — | ✓ | — | — |
| Output ripple and regulation constraint | △ | △ | △ | △ | ✓ | — | △ |
| Manufacturing-cost objective | — | — | — | — | — | ✓ | — |

## Reproduction and testing of published assumptions

Each entry states what the prior work establishes, how the same quantity is represented
here, and what is obtained. The purpose is to identify the conditions under which a prior
conclusion holds, not to contest it.

| # | Prior position | Representation in this framework | Outcome | Interpretation |
|---|---|---|---|---|
| 1 | Vertical interconnect is short and its loss is small relative to lateral routing [A],[B],[C] | every vertical segment carries the rail actually assigned to it, and its loss is evaluated from via geometry and the segment current | **REPRODUCED, AND FOUND RAIL-DEPENDENT.** For the embedded architecture the through-substrate field carries 48 V and dissipates ≈0 W; for the backside architecture the identical field carries 1 V and dissipates 0.991 W | the conclusion holds for a high-voltage vertical path and does not transfer to a low-voltage one. Vertical loss is a property of the rail assignment, not of the interconnect |
| 2 | Lateral delivery of a 1 V rail across the package is prohibitively lossy, motivating near-POL conversion [A],[B],[C] | the same lateral sheet model with geometry-derived conductor width and temperature-dependent resistivity | **REPRODUCED** | retained as motivation. The framework does not conclude that lateral or 2.5-D delivery is infeasible in general; only the evaluated 1 V stack is assessed |
| 3 | A larger converter footprint is electrically and thermally favourable [A],[C] | the same footprint variation, evaluated first for a free package and then for five explicit board constructions | **REVERSED BY ASSEMBLY STATE.** Die warpage increases by 20.3 % with footprint for the free package and decreases by 16.6–29.0 % on every explicit board | the electrical and thermal preference is unchanged; the mechanical consequence changes sign with the assembly state, so a free-package mechanical screen can invert the conclusion |
| 4 | Substrate thickness is selected on electrical and thermal grounds [A],[B] | the same thickness variation carried through the thermoelastic model under the explicit assembly | **TRENDS DO NOT OPPOSE.** Under the mounted assembly the mechanical trend does not contradict the electrical–thermal preference in the evaluated range | no conflict is found, so thickness remains an electrical–thermal decision in this range |
| 5 | Converter components may be assigned to tiers on electrical grounds, since the assignment does not change component count, area or stack height [A] | the tier assignment is propagated into the conductor-plane topology of the package and each vertical net is checked for aspect ratio and landing area | **INVALIDATED BY PHYSICAL REALIZABILITY FOR ONE ORDERING.** Two orderings that are electrically and thermally indistinguishable differ by a factor of six in worst via aspect ratio, 5.05 against 0.833 | tier assignment is not a free electrical choice. It is constrained by the package conductor-plane structure, and the constraint is invisible to an electrical model |
| 6 | Peak temperature is used to rank architectures for reliability [A],[C],[D] | peak temperature and the local corner-joint response are evaluated on the same converged field for the same pair | **NOT EQUIVALENT.** The backside architecture is 8.14 K hotter and carries 16.3 % lower local response | peak temperature is not sufficient to rank local mechanical response. This is not a claim that temperature is unimportant: temperature-dependent constitutive behaviour is inside the response model |

## Not obtained in full text, therefore not scored

| work | reason |
|---|---|
| Khorasani *et al.*, ECTC 2024, 1 kW IVR in CCM–DCM boundary mode | full text not reachable from this host |
| Kong *et al.*, *A Vertical Power Delivery Architecture for HPC*, IEEE TPEL 2025 | full text not reachable from this host |
| Ahmed *et al.*, LEGO-PoL and Mini-LEGO CPU voltage regulators, IEEE TPEL 2021/2023 | full text not reachable from this host |
| MDPI reviews on chiplet thermal management and multi-field reliability | publisher blocks full-text retrieval from this host |

These are cited where they motivate the problem, and they are not entered in the capability
matrix.
