# PHASE 0M PARTS 17-19 --- Z5 RE-AUDIT FROM FIRST PRINCIPLES

Phase 0I reported ~768 W of RDL loss for `ARCH_Z5_2P5D_LATERAL` and read it as pricing 2.5D.
Phase 0I-R narrowed that to the tested LOW-VOLTAGE lateral topology. Phase 0M neither
preserves nor withdraws the number: it traces the code path, states the implied equivalent
loop resistance, checks every parameter against interposer rather than PCB geometry, and
evaluates a FAMILY of lateral architectures.

## 1. The code path, traced end to end

| step | value |
|---|---|
| rail voltage | 1.0 V (the LV rail crosses the interposer laterally) |
| lateral current | 1000.0 A |
| source position | x = -14.364 mm, 3.184 mm clear of the die edge |
| destination | 100 POL cells on a 22.36 mm die |
| solve span | 42.940 mm |
| RDL thickness | 10.0 um |
| line / space | 10.0 / 2.0 um --> occupancy 0.8333 |
| layer count | 2 VDD + 2 GND |
| rho at 85 C | 2.1343e-08 Ohm.m |
| sheet R per net | VDD 1.2806, GND 1.2806 mOhm/sq |
| **loop sheet R** | **2.5611 mOhm per square** |
| **P = I^2 R** | **768.072 W** (VDD 384.036 + GND 384.036) |

## 2. The implied equivalent loop resistance

```
R_eq = P / I^2 = 768.072 / 1000^2 = 0.76807 mOhm
IR drop = 0.7681 V on a 1 V rail
```

Against the stack's own 2.5611 mOhm per loop square, that is
**0.2999 loop squares**. For a source line 3.18 mm
clear of a 22.36 mm-wide die, a 1-D estimate gives
0.142 squares before any spreading inside the die,
so 0.30 squares is geometrically consistent. **The number is what the geometry gives.**

| variation | P (W) | R_eq (mOhm) | loop squares |
|---|---|---|---|
| `ectc2024_primary` | 768.072 | 0.76807 | 0.2999 |
| `ectc2024_one_per_net` | 1536.145 | 1.53614 | 0.2999 |
| `iscas2024_variant` | 2560.241 | 2.56024 | 0.2999 |
| `ectc2024_primary_gap0.5` | 680.014 | 0.68001 | 0.2655 |
| `ectc2024_primary_gap1` | 710.275 | 0.71027 | 0.2773 |
| `ectc2024_primary_gap2` | 768.072 | 0.76807 | 0.2999 |
| `ectc2024_primary_gap4` | 876.777 | 0.87678 | 0.3423 |
| `ectc2024_primary_grid121` | 767.239 | 0.76724 | 0.2996 |
| `ectc2024_primary_grid161` | 768.072 | 0.76807 | 0.2999 |
| `ectc2024_primary_grid201` | 768.381 | 0.76838 | 0.3000 |

Grid-converged: 121 -> 201 moves the answer by 0.15 %. The loop-square count is invariant
across stacks, as it must be --- it is pure geometry --- and varies 0.27 to 0.34 with the gap.

## 3. Part 18 --- did Z5 inherit PCB routing assumptions? NO, AND THE REVERSE

| path | t_Cu | W / S | layers per net | occupancy | **loop R per square** |
|---|---|---|---|---|---|
| PCB | 152.0 um | 32 / 32 um | 1 | 0.500 | **0.5616 mOhm/sq** |
| RDL | 10.0 um | 10 / 2 um | 2 | 0.833 | **2.5611 mOhm/sq** |

The suspicion in the brief was that a PCB parameter had leaked into the interposer path. The
opposite is the case: **the PCB row is 4.56x MORE conductive per square than the RDL row**,
because 152 um of copper at 50 % occupancy beats 2 x 10 um at 83 %. Had Z5 inherited PCB
routing it would have reported ~169 W, not 768 W. **No defect is logged. The Z5 number is
computed on interposer geometry and it survives.**

The brief's expectation that "a shorter route with more/larger parallel RDL planes should be
recomputed from geometry" is tested and the answer is that the interposer RDL is THINNER than
the board, not thicker. Thin-film redistribution buys density and loses cross-section.

## 4. Part 19 --- the Z5 FAMILY, not one point

Both conversion stages are charged at their real modelled cost from the same upstream loss
model the rest of the project uses. Stage 1 converts 48 V to the lateral rail beside the die;
stage 2 converts the lateral rail to 1 V at the load.

| lateral V | die edges fed | P_lateral | P_stage1 | P_stage2 | **P_total** | eta | status |
|---|---|---|---|---|---|---|---|
| 1.0 | 1 | 768.072 | 125.26 | 0 | **893.34** | 52.82 % | COMPLETE |
| 1.0 | 2 | 278.212 | 125.26 | 0 | **403.48** | 71.25 % | COMPLETE |
| 1.0 | 4 | 171.793 | 125.26 | 0 | **297.06** | 77.10 % | COMPLETE |
| 3.3 | 1 | 70.530 | -- | 270.17 | **340.70** | 74.59 % | LOWER BOUND -- a stage could not be compiled |
| 3.3 | 2 | 25.547 | -- | 270.17 | **295.72** | 77.18 % | LOWER BOUND -- a stage could not be compiled |
| 3.3 | 4 | 15.775 | -- | 270.17 | **285.95** | 77.76 % | LOWER BOUND -- a stage could not be compiled |
| 5.0 | 1 | 30.723 | -- | 210.43 | **241.15** | 80.57 % | LOWER BOUND -- a stage could not be compiled |
| 5.0 | 2 | 11.128 | -- | 210.43 | **221.56** | 81.86 % | LOWER BOUND -- a stage could not be compiled |
| 5.0 | 4 | 6.872 | -- | 210.43 | **217.30** | 82.15 % | LOWER BOUND -- a stage could not be compiled |
| 12.0 | 1 | 5.334 | -- | 149.69 | **155.02** | 86.58 % | LOWER BOUND -- a stage could not be compiled |
| 12.0 | 2 | 1.932 | -- | 149.69 | **151.62** | 86.83 % | LOWER BOUND -- a stage could not be compiled |
| 12.0 | 4 | 1.193 | -- | 149.69 | **150.88** | 86.89 % | LOWER BOUND -- a stage could not be compiled |
| 24.0 | 1 | 1.333 | -- | 129.87 | **131.21** | 88.40 % | LOWER BOUND -- a stage could not be compiled |
| 24.0 | 2 | 0.483 | -- | 129.87 | **130.36** | 88.47 % | LOWER BOUND -- a stage could not be compiled |
| 24.0 | 4 | 0.298 | -- | 129.87 | **130.17** | 88.48 % | LOWER BOUND -- a stage could not be compiled |
| 48.0 | 1 | 0.333 | 0 | 125.26 | **125.60** | 88.84 % | COMPLETE |
| 48.0 | 2 | 0.121 | 0 | 125.26 | **125.39** | 88.86 % | COMPLETE |
| 48.0 | 4 | 0.075 | 0 | 125.26 | **125.34** | 88.86 % | COMPLETE |

Rows marked LOWER BOUND are ones where the upstream optimizer could not compile a first
stage at that output voltage. **Those stages are not worth zero watts and are not counted as
zero**: the CSV carries two explicitly-labelled sensitivities,
`P_total_stage1_at_97pct_w` and `..._99pct_w`, for a switched-capacitor first stage at 97 %
and 99 % efficiency. Those are ASSUMPTIONS, clearly marked, not results.

### Distribution alone

Feeding the die from more than one edge was solved directly on the same resistive sheet, not
scaled. An earlier version of this analysis scaled the clustered loss as `I^2 R / nc^1.5` on
the argument that the lateral path shortens as `1/sqrt(nc)`; that is wrong twice for a
monolithic die --- a converter cannot sit inside the die, and the source-to-die gap is set by
the VR footprint and does not shrink.

| die edges fed | R_eq (mOhm) | loop squares | P at 1 V, 1000 A |
|---|---|---|---|
| 1 | 0.76807 | -- | 768.07 W |
| 2 | 0.27821 | -- | 278.21 W |
| 4 | 0.17179 | -- | 171.79 W |

## 5. Verdict

* **The ~768 W result SURVIVES** for the topology Phase 0I actually tested: a 1 V rail fed
  laterally from ONE side of the die across a 2-layer, 10 um ECTC-2024 RDL. Equivalent loop
  resistance **0.76807 mOhm**, 0.2999 loop squares, IR drop
  0.768 V on a 1 V rail. Grid-converged, geometry-consistent, and not
  inherited from a PCB.
* **2.5D as a CLASS is NOT eliminated.** Feeding the same 1 V rail from four die edges cuts
  the lateral loss 4.5x. Raising the lateral rail to 12 V cuts it 144x. The penalty is a
  property of the low-voltage one-sided topology, not of lateral delivery.
* **But no lateral variant beats the vertical architectures.** The best complete row is
  48 V lateral with four-edge feeding at 125.34 W, against
  126.09 W for Z1 --- and at 48 V "lateral distribution" means the input rail is routed
  laterally and the whole converter sits at the load, which is vertical delivery by another
  name. The family degenerates into the vertical architectures exactly where it becomes
  competitive.
