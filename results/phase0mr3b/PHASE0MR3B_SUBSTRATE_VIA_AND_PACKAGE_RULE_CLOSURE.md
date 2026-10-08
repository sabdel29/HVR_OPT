# PHASE 0M-R3B --- SUBSTRATE-VIA TECHNOLOGY, PACKAGE-RULE AND PROCESS-MARGIN CLOSURE

**Verdict: D --- THE PHYSICAL `ls_to_L` TOPOLOGY, EVALUATED AGAINST SOURCED SUBSTRATE-VIA RULES, MAKES THE FROZEN Z1/Z2 PAIR NOT_REALIZABLE UNDER THE CURRENT COMPONENT TOPOLOGY.**

Both architectures share one converter cell, so the finding applies to both equally. The deciding mechanical ordering is untouched -- and is not the question this gate asked.

---

## 1. The span was the artifact

`ls_to_L` was recorded at 673 um. That is a tier MID-PLANE to tier MID-PLANE distance: it runs from the centre of the low-side GaN die to the centre of the inductor, through 303 um of die body and 250 um of inductor body. The build-up a via chain actually crosses is **120 um** -- RDL 10 + flying-capacitor layer 100 + RDL 10. The overstatement is **5.61x**, and it is systematic: `hs_to_ls` is overstated 65.5x (DEFECT #62).

This does NOT change the via count -- `n_required` has no length in it -- so the Phase-0M-R3A arithmetic stands. It changes the resistance, and it changes what technology question is being asked.

## 2. The technology is ordinary; the design point is not

A 120 um stack through three build-up layers is embedded-component packaging, for which primary literature exists. Two sources were obtained in full text:

* **Ostmann et al. 2008** (Fraunhofer IZM / AT&S / IMEC-CMST), chip embedding: contacts to embedded dies are laser-drilled, metallised microvias; minimum **150 um I/O pad pitch in production**, 100 um at prototype level, and *"for pitches smaller than 100 um ... vialess interconnection methods"* are indicated instead. Minimum 10 um plated Cu in the via; die placement +/-10 um at 3 sigma.
* **Cauwe et al., CEAS Space Journal 15:101-112 (2023)**, HDI qualification: the qualified multi-level configuration is **two stacked microvias plus one staggered**, and *"Stacking three levels of microvias is considered a reliability risk."*

The Phase-0M-R3 design point is r = 20 um at **70 um pitch**, in a **three-layer** gap. It is finer than any sourced pitch for this class and needs one more stacked level than the sourced qualified configuration.

## 3. The landing area was also wrong

`edge_loss()` computes the vias available over 1.80 mm2, the gan_ls footprint. But the chain has to get through the flying-capacitor layer, and in that layer the 5.61 mm2 cell already holds two 2.00 mm2 embedded MLCCs. The free area is **1.61 mm2**, and that is the binding number (DEFECT #63).

At the corrected landing area the Phase-0M-R3 design point gives routing ratio **1.0427 > 1** and is **infeasible on its own terms**, before any sourcing question is asked.

## 4. The full sweep

| pitch | stacking | d | n_req | n_avail | ratio | feasible |
|---|---|---|---|---|---|---|
| 70 um | fully stacked | 40 um | 171 | 164 | 1.043 | no |
| 70 um | semi stacked | 40 um | 171 | 82 | 2.085 | no |
| 100 um | fully stacked | 40 um | 171 | 80 | 2.138 | no |
| 100 um | fully stacked | 70 um | 55 | 80 | 0.688 | **yes** |
| 100 um | semi stacked | 40 um | 171 | 40 | 4.275 | no |
| 100 um | semi stacked | 70 um | 55 | 40 | 1.375 | no |
| 150 um | fully stacked | 40 um | 171 | 35 | 4.886 | no |
| 150 um | fully stacked | 120 um | 19 | 35 | 0.543 | **yes** |
| 150 um | semi stacked | 40 um | 171 | 17 | 10.059 | no |
| 150 um | semi stacked | 120 um | 19 | 17 | 1.118 | no |

**0 configurations satisfy both sourced bounds.** Every feasible option requires three fully stacked microvia levels, which is the configuration the HDI qualification identifies as a reliability risk.

The nearest miss is instructive: at 150 um pitch, 120 um diameter, semi-stacked, the field needs 1.71 mm2 against 1.61 mm2 available -- short by **6 %**. That is a repartitioning target, not a via-technology problem.

## 5. The vertical path is 16 % more resistive than the series model

A 3-D DC solve of one physical column -- microvia, land, microvia, land, microvia -- returns **1.163x** the analytical series resistance for a 120 um via and **1.160x** for a 70 um one, converged to 0.13 % and 0.34 % on the two finest meshes. A plain copper bar control returns `rho L / A` to -0.000 %. The penalty is land spreading and is insensitive to diameter.

## 6. Clearances and TSV margin

One of the three clearances moves to SOURCE_BOUNDED: an embedded die takes a 15-20 um dielectric cap (Ostmann 2008), which lies inside the existing [10, 25, 50] um bound, so no corner moves. **Two remain OPEN.** And they are no longer the binding constraint -- the interconnect fails first.

No TSV manufacturing tolerance could be sourced. 32 um can absorb **3.23 %** symmetric tolerance before AR = 10 is violated, 34 um 6.25 %, 36 um 9.09 %, and 30 um none at all. 32 um is **PARAMETRICALLY MARGINED, NOT process-qualified**.

## 7. No ETM solve was rerun, and why

The span correction removes **1.110 W** of intra-VR vertical loss, which is 0.80 % of the electronics total and above the 0.5 % rerun threshold. It was still not rerun, for a reason that is not about size:

* The correction is **exactly common mode**. Z1 and Z2 share one converter cell, one partition template and one set of currents, so the same 1.110 W leaves both.
* Section 9 requires the corrected configuration to be **frozen first**. There is no corrected configuration to freeze: no via geometry satisfies both sourced bounds, and selecting one of the unsourced options would be inventing the process technology this gate exists to source.

So **D_driver = 1.1943** is carried as the Phase-0M-R3 configuration's ordering and is explicitly NOT re-asserted for a corrected one. The physical spans are available in production behind `PHASE0MR3B_PHYSICAL_SPANS=1`, default off, so every prior result is bit-identical until a phase deliberately turns it on.

| | Z1 | Z2 |
|---|---|---|
| T_max | 118.68 C | **126.91 C** |
| local fatigue-relevant inelastic response | 4.6401 um | **3.8851 um** |

## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** technology and package rules closed, PROVEN_REALIZABLE | not available: five via parameters and two clearances are OPEN, and no configuration satisfies both sourced bounds |
| **B** technology closed, clearances still block | the technology is NOT closed, and the clearances are no longer what blocks first |
| **C** technology remains unsourced, pair stays CONDITIONAL | true as far as it goes, and too weak: the design point is not merely unsourced, it is infeasible at the corrected landing area on its own arithmetic |
| **E** via-chain model changes electrical results materially, ordering survives | the 0.80 % loss change is real and the ordering does survive, but this is the smaller finding and would bury the realizability result |
| **F** the deciding ordering changes | it does not; the correction is common mode |

## Optimizer

**FORBIDDEN**, unchanged. `architecture templates realizable` is DOWNGRADED from PARTIAL back to NO.
