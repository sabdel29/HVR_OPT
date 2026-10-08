# PHASE 0M-R3C --- COMPONENT REPARTITIONING, PHYSICAL REALIZABILITY AND PAPER FREEZE

**Verdict: B --- A PROCESS-CONDITIONAL REPARTITION EXISTS, AND THE FINAL Z1/Z2 RESPONSE ORDERING SURVIVES.**

D_driver_final = **1.1947** against the historical 1.1943: **+0.04 %**. The entire interconnect correction -- a re-derived conductor-plane topology, a repartitioned stack, corrected physical spans and a source-bounded via geometry -- moves the deciding ratio by four hundredths of a percent.

---

## 1. The three-level via count was wrong --- DEFECT #64

Phase 0M-R3B counted three MATERIAL layers across the 120 um gap and concluded three stacked microvia levels, then measured that against a sourced stacking limit and reported zero feasible configurations. `RDL_UM = 10 um` is an interlayer REDISTRIBUTION layer -- patterned copper, which is precisely what a microvia lands on. Counting conductor planes instead of material layers:

| # | z | structure | via? |
|---|---|---|---|
| 0 | 1301 um | gan_ls terminal face | no |
| 1 | 1301-1311 | interlayer RDL --- CONDUCTOR PLANE, a capture land | no |
| 2 | 1311-1411 | flying-capacitor power layer, no conductor plane inside | **yes, one level** |
| 3 | 1411-1421 | interlayer RDL --- CONDUCTOR PLANE | no |
| 4 | 1421 um | inductor terminal face | no |

**One via level, not three.** The stacking-limit objection dissolves, and the Phase-0M-R3B conclusion that no configuration satisfies both sourced bounds is **withdrawn**: the baseline already passes at a sourced pitch (0.543 at 150 um for ls_to_L).

## 2. What the baseline's real problem was

Not `ls_to_L`. Re-counted properly, the binding net is **`hs_to_cf`**, which in the Phase-0M-R3 tier order crosses the entire 606 um low-side GaN tier in one via level:

| net | baseline depth | baseline AR | repartitioned depth | repartitioned AR |
|---|---|---|---|---|
| `ls_to_L` | 100 um | 0.83 | 10 um | **0.08** |
| `hs_to_ls` | 10 um | 0.08 | 100 um | **0.83** |
| `hs_to_cf` | 606 um | 5.05 | 10 um | **0.08** |

Worst aspect ratio falls from **5.05** to **0.83**.

## 3. The repartition

`T1C_REORDERED`: **gan_hs / cap_fly / gan_ls / inductor+cap_out**

the flying capacitors move from tier 2 to tier 1 and the low-side GaN switches from tier 1 to tier 2; nothing else changes. it puts the low-side switch adjacent to the inductor, so the 20.408 A switch node crosses only the interlayer RDL instead of a 100 um component tier, and it removes the 606 um hs_to_cf crossing entirely.

It is a PERMUTATION: same five component classes, same counts, same per-tier areas (max 5.61 mm2), same 1921 um stack height, same tier count. It is a permutation, so every Phase-0M-R3 area and height result carries. keeps both ends the June-2026 source fixes: high-side GaN flip-chipped at the bottom substrate, inductors in the top layer near the POLs.

144 of the enumerated partitions satisfy the per-tier area budget and 8 keep both sourced stack ends; this is the best of those 8 on the brief's hierarchy.

## 4. Framework provisioning is not a process qualification

Both statuses are carried separately everywhere, as they must be:

| net | n_req (framework, J_design) | n_avail | ratio | AR | process |
|---|---|---|---|---|---|
| `ls_to_L` | 19 | 30 | 0.633 | 0.083 | **OPEN** |
| `hs_to_ls` | 2 | 35 | 0.057 | 0.833 | **OPEN** |
| `hs_to_cf` | 1 | 31 | 0.032 | 0.083 | **OPEN** |

`n_required` is a CONSERVATIVE DESIGN-SIDE ALLOCATION at J_design = 1e8 A/m2. No sourced current allowable exists for this microvia technology, so it is never a statement about what manufacturing requires.

Two facts from primary sources obtained this phase sharpen the picture:

* the **EPC2057 datasheet** shows the part is a bare die with FOUR solder bars (pad 1 gate, pads 2 and 4 source, pad 3 drain) on 1500 x 1200 um, so the switch-node landing area is at most a quarter of the die, not its whole footprint;
* the `ls_to_L` edge is an **aggregate over K = 3 phases**. Per device the switch node carries 6.803 A, inside the EPC2057's 9.6 A continuous rating, and there are three such dies each with their own drain bar.

## 5. The one final ETM replay

Both configurations were frozen in `configs/phase0mr3c/frozen_pair_*.yaml` before solving. One solve each, identical settings, no sweep.

| | Z1 | Z2 |
|---|---|---|
| P_electronics | 137.292 W | 139.659 W |
| T_max | 118.32 C | **126.46 C** |
| T_mean | 93.41 C | 95.41 C |
| die warpage P-V | 41.616 um | 38.916 um |
| local fatigue-relevant inelastic response | 4.6252 um | **3.8714 um** |
| energy residual | 0.000 % | 0.000 % |

**D_driver_final = 1.1947.** Z2 carries 16.3 % less response while running +8.14 K hotter. The ordering survives, and the temperature/response decoupling survives with it.

## 6. What is still not earned

Neither architecture is PROVEN_REALIZABLE. Geometry closes; the microvia current allowable, the capture-pad diameter, a vendor design rule and two package clearances remain OPEN. The licensed verdict is **GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL**.

## Verdicts considered and rejected

| candidate | why rejected |
|---|---|
| **A** source-compatible repartition, ordering survives | 'source-compatible' would claim the process rules are closed. Four are OPEN |
| **C** repartition found, ordering CHANGES | it does not: +0.04 % |
| **D** no realizable repartition exists | contradicted. 144 partitions meet the area budget, 8 keep the sourced stack ends, and the best has worst AR 0.83 |
| **E** geometry closes but process data insufficient | true, and it omits the result the gate was opened to get: the replay ran and the ordering held. B states both |

## Framework status

**DEVELOPMENT STOPS HERE.** No fundamental contradiction was found. G2 remains NOT TESTED, the optimizer remains FORBIDDEN, and the next action is manuscript freeze.
