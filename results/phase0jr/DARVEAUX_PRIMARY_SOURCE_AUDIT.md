# Phase 0J-R Sec. 14/15/16 — Darveaux, from the primary source

## Files

`Darveaux_2000_Simulation_Methodology.pdf` was supplied and read in full.
**`Darveaux_2002_Crack_Growth_Fatigue.pdf` was NOT supplied**, nor the optional 1997 paper.
Darveaux 2000 is the paper that re-derives the constants after the plastic-work bug, so the
branch is assessable; the absence of the 2002 companion is recorded rather than papered over.

## Exactly what the method requires — extracted, not paraphrased from secondary sources

| item | value from the primary |
|---|---|
| crack initiation | `N_0 = K1 · ΔW_ave^K2` (Eq. 13) |
| crack growth | `da/dN = K3 · ΔW_ave^K4` (Eq. 14) |
| total life | `N_f = N_0 + a / (da/dN)` |
| **ΔW_ave definition** | `Σ(ΔW·V)/ΣV` over the **interface elements** |
| **averaging-layer thickness** | **first three element layers, each 0.0005 in = 12.7 µm**; the Figure 9 correlation uses the **first two layers**, total 0.001 in |
| element arrangement | slice or quarter-symmetry; both reported separately |
| constitutive models | **Anand**, and a separate "Darveaux" model; ANSYS 5.2 and 5.6 |
| final crack length | joint interface diameter; the worked example uses 0.016 in with shape factor 2.6 |
| **alloys** | **62Sn36Pb2Ag and 60Sn40Pb — eutectic SnPb only** |
| test matrix | 4 assemblies, 2 alloys, 8 thermal-cycle conditions, all ceramic chip carriers / CBGA |

### Table 6 — recovered in full

Fourteen rows of `K1`–`K4` indexed by model configuration, simulation method, constitutive
model, ANSYS version, temperature-change command, time-step scheme **and averaging-layer
thickness**. Representative rows (QTR, NL FEA, Anand, 5.6, BF, fine):

| layer thickness (10⁻³ in) | K1 (cycles/psi^K2) | K2 | K3 (10⁻⁷ in/cycle/psi^K4) | K4 |
|---|---|---|---|---|
| 0.5 | 71 000 | −1.62 | 2.76 | 1.05 |
| 1.0 | 56 300 | −1.62 | 3.34 | 1.04 |
| 1.5 | 48 300 | −1.64 | 3.80 | 1.04 |

The constants move by **47 % in K1 across a 3× change in averaging thickness alone**, with the
model, mesh, solver and alloy all held fixed.

## Sec. 16 — the alloy question, answered from the source

**Every Darveaux constant in this paper is for eutectic SnPb.** There is no SAC composition
anywhere in the test matrix. The constants therefore **cannot** produce an absolute SAC305
lifetime, and none is attempted. This confirms, from the primary, what Phase 0J inferred from a
secondary description.

## Sec. 15 — was targeted refinement justified?

**Yes, and it was performed — for Syed, not for Darveaux.** The graded mesh built for Syed's
25 µm layers has **12.5 µm elements**, which is essentially Darveaux's 12.7 µm requirement, so
the extraction geometry is now reproducible. What remains incompatible is everything else:

| requirement | ours | compatible? |
|---|---|---|
| layer thickness 12.7 µm | **12.5 µm** | **yes, now** |
| 2–3 layers at the interface | **2 per face** | **yes** |
| constitutive model Anand | Norton **overstress** viscoplastic | **no** |
| alloy | SAC305 | **no — constants are SnPb** |
| package | CBGA on ceramic chip carrier | BGA on FR-4 | partial |

So the mesh blocker Phase 0J reported (*"37.5 µm, 3× too coarse"*) is **removed**, and the
remaining blockers are alloy and constitutive model — which no amount of meshing fixes.

## What the source says about transferring methodology — in its own words

> *"the error in field use extrapolations could be up to 7X"* — if constants derived with one
> modelling methodology are applied to another.

> *"Since the slopes are consistent (K4 = 1.04 to 1.05), relative fatigue life predictions
> should be somewhat independent of the averaging scheme chosen."*

The second sentence is the one that matters most for this project, and it comes from the
primary rather than from a review: **relative predictions are robust to the averaging scheme;
absolute ones are not.** That is independent corroboration, from a different author and a
different alloy, of the central Phase-0J-R conclusion.

## Verdict

**INADMISSIBLE for SAC305 absolute life** — criterion 1 fails outright and no re-meshing can
change it.
**Retained as methodological evidence** for two specific claims: that averaging thickness
materially changes a fitted constant (47 % in K1 over 3×), and that relative life is far more
transferable than absolute life.
