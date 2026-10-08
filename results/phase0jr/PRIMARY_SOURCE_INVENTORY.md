# Phase 0J-R Sec. 0 — Primary source inventory

Six PDFs were supplied in `results/Papers/` and **all six were read in full before any search
was attempted**. Two expected files were **not supplied**: `Darveaux_2002_Crack_Growth_Fatigue.pdf`
and the optional `Darveaux_1997_Solder_Joint_Fatigue_Life.pdf`. Darveaux 2000 is present and is
the paper that actually re-derives the constants, so the branch is still assessable; this is
recorded rather than worked around.

No long passages are quoted. Short verbatim fragments are used only where the exact wording is
the evidence, and each is attributed to a page.

---

## 1. Syed 2004 — IEEE ECTC original

| field | value |
|---|---|
| title | Accumulated Creep Strain and Energy Density Based Thermal Fatigue Life Prediction Models for SnAgCu Solder Joints |
| author / venue | A. Syed, Amkor Technology · Proc. 54th ECTC 2004, pp. 737–746 |
| DOI | 10.1109/ECTC.2004.1319419 |
| **alloy** | **SnAgCu balls: 4.0Ag0.5Cu or 3.9Ag0.5Cu** (i.e. SAC405 / SAC395) on SnAgCu paste — **not SAC305** |
| package / joint | BGA and CSP, 8×8 to 27×27 mm, 4 ball pitches, 4 ball diameters; SMD pads, electrolytic NiAu on package, OSP board; board-level **BGA solder ball** |
| failure definition | in-situ resistance > **300 Ω**, confirmed by 10 further events within 10 % of the time of first failure; **MEAN life** (not characteristic) |
| temperature profiles | **TC1** −40/+125 °C, 15 min ramps **and 15 min dwells**, 1 cycle/h · **TC2** −55/+125 °C, 12 min ramps, **3 min dwells**, 2 cycles/h · **TC3** 0/+100 °C, 10 min ramps, **5 min dwells**, 2 cycles/h. Profiles measured on the boards, not chamber setpoints. |
| constitutive models | (i) **Wiese double power law** (two mechanisms, Table 1 Eq. 1); (ii) **Schubert hyperbolic sine** (Table 1 Eq. 2) |
| FE code | ANSYS, 3-D global/local with substructuring; implicit creep `TBOPT=11` (double power law) and `TBOPT=8` (sinh) |
| **averaging** | **volume-averaged over a 25 µm thick solder layer**, at **both package and board side**, **two elements across each layer**; the appended deck adds: *"Life prediction model parameters are only valid for this thickness"* |
| damage metrics | `NL,CREQ` accumulated **creep** strain; `SEND,CREEP` **creep** strain energy density — creep only, not plastic+creep |
| life equations | Eq. 6 `N_f=(C'·ε_acc)^−1` · Eq. 7 `N_f=(W'·w_acc)^−1` · Eq. 8/9 partitioned two-mechanism forms |
| **coefficients (ORIGINAL)** | power law: `C'=0.0358`, `W'=0.0012`, partitioned `C_I=0.013`, `C_II=0.036`; sinh: `0.0405`, `0.0014` |
| dataset | **12 calibration points** (Tables 2a/2b), mean life **275–10 027 cycles**; plus a 4-configuration independent validation package (Table 3) |
| reported error | "within 25 % in most cases"; partitioned fit R² = 0.9997 |
| domain | accelerated thermal **and power** cycling; explicitly **not** fast bend or vibration fatigue |

## 2. Syed 2004 — author-corrected version

Same paper with a per-page correction notice and an appended 24-page ECTC presentation deck.
**Constants are different and supersede the original.** Full comparison in
`SYED_2004_VERSION_AUDIT.md`. Corrected: `C'=0.0468`, `W'=0.0015`, partitioned `C_I=0.106`,
`C_II=0.045`; sinh `0.0513`, `0.0019`. Root cause, from the deck: the original constants were
regressed on **first-cycle** values through a post-processing error, and SnAgCu stabilises only
after the 2nd cycle with a **20–30 % reduction** after the first.

The deck also contributes two facts the paper body does not:
* the 25 µm layers are taken at **both** faces with **two elements each**, and the constants are
  declared valid **only** for that extraction;
* a direct check of time-independent plasticity in Syed's own model: creep strain 0.4641 %
  vs 0.4629 %, **plastic contribution 0.125 %** of strain and 0.225 % of energy, concluding
  *"No need to model time independent plasticity for Thermal Cycle simulations"*.

## 3. Schubert 2003

| field | value |
|---|---|
| title / venue | Fatigue Life Models for SnAgCu and SnPb Solder Joints Evaluated by Experiments and Simulation · Proc. 53rd ECTC 2003, pp. 603–610 |
| DOI | 10.1109/ECTC.2003.1216343 |
| **alloy** | **Sn95.5Ag3.8Cu0.7 (SAC387)** vs Sn59Pb40Ag1 — **not SAC305** |
| packages | flip-chip on board (with/without underfill), **PBGA 256 / 272 / 313 / 316**, 1.27 mm pitch, on 1.0–1.57 mm FR-4 |
| cycles | −55/+125 °C and −55/+150 °C, **30 min total, 10 min dwells, 5 min ramps**; literature data at −40/+125 °C, 60 min |
| constitutive | creep law with **primary + secondary** parts (Tables 1–3), 108 creep data points |
| metrics | Eq. 5 accumulated **creep** strain; Eq. 6 viscoplastic **energy density** — both defined as *"the actual minimum (or average) over the path of local maximum"*, i.e. a **band of local maxima**, not a fixed-thickness layer |
| life equations | `N_f = θ1 (ε_acc^cr)^−θ2` and `N_f = θ3 (ΔW_cr)^−θ4` |
| **coefficients** | **slopes only, in the text: −1.3 (strain) and −1.0 (energy) for SnAgCu** (SnPb: −1.80 and −1.20). **Prefactors θ1, θ3 are NOT printed** — they exist only as fitted lines in Figures 7 and 8, whose data are not in the text layer. |
| dataset | best-fit through **14 experiments** |
| reported error | not quantified; a SnAgCu/SnPb crossover at 600–800 cycles (strain) and 6000–8000 (energy) |

## 4. Darveaux 2000

| field | value |
|---|---|
| title / venue | Effect of Simulation Methodology on Solder Joint Crack Growth Correlation · Proc. 50th ECTC 2000, pp. 1048–1058 |
| DOI | 10.1109/ECTC.2000.853299 |
| **alloy** | **62Sn36Pb2Ag and 60Sn40Pb — EUTECTIC SnPb ONLY. No SAC of any composition.** |
| packages | ceramic chip carriers / CBGA, 4 assemblies, 8 thermal-cycle conditions |
| constitutive | Anand, and a separate "Darveaux" model; ANSYS 5.2 and 5.6 |
| **averaging** | `ΔW_ave = Σ(ΔW·V)/ΣV` over interface elements; **first three element layers each 0.0005 in (12.7 µm)**; Figure 9 correlation uses the **first two layers**, total 0.001 in |
| life equations | `N_0 = K1·ΔW_ave^K2` (initiation), `da/dN = K3·ΔW_ave^K4` (growth), `N_f = N_0 + a/(da/dN)` |
| **coefficients** | **Table 6 recovered in full** — 14 rows, K1–K4 as a function of model config (slice / quarter), simulation method (NL FEA, L+NL), constitutive model, ANSYS version, temperature command, time-step scheme and layer thickness. Example, QTR / NL FEA / Anand / 5.6 / BF / fine: 1.0e-3 in → K1 = 56 300, K2 = −1.62, K3 = 3.34, K4 = 1.04. Units: K1 cycles/psi^K2, K3 10⁻⁷ in/cycle/psi^K4. |
| **reported error** | **"the error in field use extrapolations could be up to 7X"** if constants from one methodology are used with another; and **"Since the slopes are consistent (K4 = 1.04 to 1.05), relative fatigue life predictions should be somewhat independent of the averaging scheme chosen."** |

## 5. Syed 2001

| field | value |
|---|---|
| title / venue | Predicting Solder Joint Reliability for Thermal, Power, & Bend Cycle within 25 % Accuracy · Proc. 51st ECTC 2001 |
| alloy | **eutectic Sn/Pb** |
| scope | thermal cycle, **power cycle**, bend cycle |
| **power-cycle method** | *"The only difference is that while in temperature cycle case a uniform temperature change is assumed for the whole model, the temperature distribution for power cycle needs to be determined by first performing a transient heat transfer analysis... The temperature distribution is then used in stress analysis to determine the mean life as described above."* **No acceleration factor and no dwell equivalence are used.** |
| power-cycle validation | 27 mm 256-lead PBGA, Peltier top-heating, **260 s cycle**, 16 assemblies; measured mean life **5550**, predicted **6750** → **+20 %** |
| stabilisation | *"At least 3 power cycles were simulated to get the stable cyclic results."* |
| boundary of validity | bend cycling at 1 cycle/s is **excluded** — creep plays no role and time-independent plasticity governs |

## 6. Vasudevan & Fan 2008

| field | value |
|---|---|
| title / venue | An Acceleration Model for Lead-Free (SAC) Solder Joint Reliability · Proc. 58th ECTC 2008, pp. 139–145 |
| alloys | **SAC105, SAC305, SAC405** |
| model type | **3-parameter modified Norris–Landzberg ACCELERATION FACTOR** — not an FEA damage model |
| equation | `AF = N1/N2 = (f1/f2)^−m · (ΔT1/ΔT2)^−n · exp[(Ea/k)(1/T_max,1 − 1/T_max,2)]` |
| **coefficients** | **m = 0.33, n = 1.9, Ea/k = 1414 K** |
| dataset | **17 pairs** of thermal-cycle tests, Intel and published sources, multiple packages (FCBGA, socket, die-side capacitor) |
| reported error | **average deviation < 6 %** |
| dwell handling | cyclic **frequency** is the time variable, not dwell time explicitly; an extended-cycle-time study (up to 480 min) is reported separately |
| use | test-to-test and test-to-field **life scaling**; it cannot convert an FEA metric into a life |
