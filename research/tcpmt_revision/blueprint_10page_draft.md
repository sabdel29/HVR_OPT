# Blueprint for the 10-page TCPMT paper (draft for author approval)

Scope: a full restructure of the 23-page manuscript (`manuscript_v2/`) into **10 pages in total** in IEEE two-column TCPMT format, counting references and biographies. This blueprint merges six reviewer reports (structure, electrical, thermal/mechanical, results, hostile reviewer, state of the art). The lead editor checked every number quoted here against `macros_front.tex`, `macros_methods.tex`, `macros_results.tex`, `results_macros.tex`, the compiled PDF, supplement Table S2, the optimizer and routing code (`HVR_FULL_OPT_EPC_V2.py`, `paper_routing.py`) and the full text of Choi et al. [21]. Numbers marked **[verify]** were derived by the editor and are not yet a macro. Items marked **[run Rn]** depend on a run in §9.2. Verdicts of the five robustness variants now being rerun (board_h1, board_h0_h1grid, board_t2p4, f2_void, f1_sidewall_filled) are marked **[update]**.

---

## 0. The paper in one sentence, and how the reviewer disagreements were resolved

**Thesis the reader must leave with.** Where a near-point-of-load regulator is integrated in a 2.5-D/3-D package decides three things at once: its routing loss, the path its heat takes and the strain in the joints that carry it. ETM-DVPD is a coupled electrothermal–mechanical simulator. It synthesizes the regulator for a system target and carries it to the critical solder joint on one geometry, under a given thermal solution. It returns design decisions that no single-domain tool returns, some of which run against intuition.

| # | Disagreement | Decision | Why |
|---|---|---|---|
| 1 | Organize by data flow (structure) or by question (results curator) | Methods follow the data flow of Fig. 1. Results are titled by finding. Each result subsection opens with what a single-domain analysis would conclude and closes with the design rule. | The author's first priority is the simulator, so the methods read as a pipeline. The findings carry the "why it matters". |
| 2 | Count story: the author wants "conversion vs routing balance"; the electrical and hostile reviewers say the data do not support it | Show conversion and routing as separate curves (Fig. 3a) and say plainly what sets the optimum for this target. Tell the routing-vs-conversion trade at two scales: count (Fig. 3a) and integration (Fig. 3b), where it decides the outcome. Fix the screen's routing model before writing (Decision D2, run R2). | Verified in Table S2: conversion alone is lowest at M = 36 (97.25 W), and routing falls only from 12.0 W (M = 16) to 4.2 W (M = 56). The screen's routing model (`paper_routing.py`) applies √(f_sw/1 MHz) to the DC load current and puts the full 1 kA through the BGA in every integration. Printed as an equation, a reviewer would reject both. |
| 3 | Inductor: the author decided to keep the 250-nH, 1.6-mΩ, 1-mm² part; the reviewers rate it critical | Keep it as the baseline, labelled a design target with its basis in Table II. Add the inductor-technology run R3 so the conclusions are shown not to depend on it (Decision D1). | This respects the author's decision while defusing the most likely cause of rejection (§9.3, risk K1). |
| 4 | Omitted converter losses: add them to the baseline (hostile) or keep them as a bound (electrical) | Keep them as a bound for this submission. Z2 under cooling A is shown as conditional wherever it is ranked (Decision D3). | Putting them in the baseline means rerunning every production case. The headline verdicts do not rest on Z2-A. |
| 5 | Primary loss metric | Platform-inclusive loss: from the common 48-V node, including the 48-V feed and pumping. The package-internal loss is what the thermal model receives. | This answers the fairness concern (Z1 is counted from its BGA pads, Z2/Z3 from the converter terminals) and fixes one ranking metric. |
| 6 | 23 % coupling penalty as a headline (structure) or not novel (SOTA) | Report it in Sec. VI on the same basis as [21]: +29 % over the uncoupled ledger here, +15.8 % in [21]. Leave it out of the abstract. | [21] already shows electrothermal coupling. The novelty is what coupling does to the design decision. |
| 7 | Verification as a figure (current Fig. 7), a table, or supplement only | One compact main-text table (Table III: check, reference, max error). The "establishes / does not establish" matrix and the runtime chart move to the supplement. | Verification is a main credibility claim, so its evidence must sit in the 10 pages. A 3-column table is the densest form. |
| 8 | Fig. 10: redraw as a "results by level of physics" figure (structure) or drop (curator) | Move it to the supplement. Table V (verdict ladder plus conditions) carries the "which physics changes which ranking" argument. The new Fig. 5 shows the joint inversion. | A table states each level, verdict and deciding number in about 0.28 page. A bar chart repeats Table IV. |
| 9 | Mechanical numerics: rerun (thermal, hostile) or caveat | Rerun if time allows (R7). Otherwise one sentence in Sec. V. | The warpage-based statements under cooling A survive the 13 % solver term and the 37 % through-thickness term (Z1 17.5 µm against 58.1 and 46.9 µm). Only Z3/Z1 warpage under B is withdrawn. |
| 10 | Joint ranking depends on the board | State the condition with the claim. Run the all-site joint search on the 90-mm board with its own electrothermal field (R4) to turn the condition into a result. | The flattest-die/worst-joint finding is a headline, and a cold-rim 3× board reverses it under cooling A. |
| 11 | References: 40 (structure, SOTA) or fewer | 36 core references plus at most 4 optional. | References cost about 0.029 page each (measured on the current PDF: 62 references take 1.83 pages). |
| 12 | Biographies: budget 0.3–0.4 page, or assume none | Budget 0.30 page. Confirm with the current TCPMT template: Choi et al., TCPMT 16(7), July 2026, prints none. | If they are not printed, the 0.30 page becomes reserve. |
| 13 | Contributions: qualitative or with numbers (an open item in the work log) | Qualitative. Numbers go in the abstract and conclusion. | Avoids repeating numbers. The SOTA and structure reviewers agree. |
| 14 | Code/data DOI (hostile) | Keep the author decision: data available from the corresponding author on request. | Author decision of 2026-11-24. |
| 15 | Five-tier Z1 under cooling B beats four-tier Z2 in loss (results curator) | Include it as the co-design result in VII-E (Decision D6). | It is the clearest proof that the integration bounds the converter. It is verified in macros: Z1 five-tier B 113.9 W and feasible, against Z2 four-tier B 118.1 W. |

---

## 1. Title, abstract and contributions

### 1.1 Title
- **Recommended:** *From System Target to Solder Joint: A Coupled Electrothermal–Mechanical Framework for 2.5-D/3-D Package-Integrated Power Delivery* (16 words)
  - It states the scope (end to end), the physics (coupled ETM), what the paper delivers (a framework) and the class of system (2.5-D/3-D package-integrated power delivery, the author's own words).
  - It carries forward the current "From Device to Solder Joint".
- **Alternative:** *ETM-DVPD: Coupled Electrothermal–Mechanical Simulation and Design of Near-Point-of-Load Power Delivery for High-Performance Computing* (15 words)
  - It puts the tool's name in the title, which helps citation, and states the HPC context.
- In either case, the abstract and Sec. II name the framework ETM-DVPD.
- Index terms: 2.5-D/3-D integration, distributed vertical power delivery, electrothermal–mechanical co-design, hybrid switched-capacitor converter, integrated voltage regulator, near-point-of-load regulation, solder joint reliability, thermal management.

### 1.2 Abstract (200 words, draft)
> Kilowatt AI and data-center processors draw a kiloampere below 1 V, pushing voltage regulators into 2.5-D/3-D packages, near the point of load. The integration decides routing loss, heat path and joint strain together, yet existing tools either fix the converter or solve one physics. We present ETM-DVPD, a coupled electrothermal–mechanical framework that carries a regulator from a system target to the solder joint on one package geometry. Its electrical solver sweeps the regulator count and, at each count, synthesizes the hybrid switched-capacitor topology, GaN devices, passives and switching frequency from a part library to minimize conversion plus routing loss. Its package solvers check realizability, iterate loss and temperature to a fixed point under a given thermal solution, solve the mounted package thermoelastically at every interconnect site, locate the critical joint with a viscoplastic submodel and reject designs that break a part or package limit. Every stage is verified against a numerical reference. For a 1-kW, 48-to-1-V processor, the framework selects 36 cells at 805 kHz and compares embedded, package-backside and board-backside integration. The preferred integration changes with the thermal solution, the board-backside regulator fails its 1-V drop limit under either cooling, and the flattest package has the most strained joints.

Outline: problem (1 sentence) · gap (1) · framework (1) · electrical solver (1) · package solvers (1) · trust (1) · demonstration (1) · three findings (1).
- Only the three most robust findings appear:
  - the preferred integration flips with the thermal solution;
  - Z3 fails its 1-V path under both coolings;
  - the joint inversion, which holds under all three solder laws.
- If R4 or the pending variants make the joint inversion conditional, replace the last clause with "and neither warpage nor the largest joint displacement locates the critical joint".

### 1.3 Contributions (qualitative; four)
1. **A coupled simulator for near-POL power delivery in 2.5-D/3-D packages.**
   - It is steady state and carries one design record from discrete parts to the critical solder joint of the mounted package, on one geometry.
   - Its parts: a rail-aware loss ledger inside a tier-resolved electrothermal fixed point, under any thermal solution expressed as a boundary; a thermoelastic solution evaluated at every interconnect site; a viscoplastic search for the critical joint; and realizability and feasibility filters.
   - Every coupling is classified and every stage is verified (Secs. II, IV, V).
2. **Synthesis driven by the system target.**
   - A count sweep re-synthesizes the hybrid switched-capacitor regulator at every count by exhaustive search over GaN devices, inductors, capacitors and switching frequencies under part-level rules, trading conversion against routing loss.
   - The selected count is then confirmed through the coupled chain (Secs. III, VI).
3. **Comparison through the full flow.**
   - Embedded, package-backside and board-backside integrations of one design record are compared under identical thermal solutions and one platform-inclusive loss boundary.
   - Infeasible designs are filtered out, and every compared difference is resolved against its own numerical uncertainty (Sec. VII).
4. **Outcomes that only the coupled solution returns.**
   - The preferred integration changes with the thermal solution and the loss boundary.
   - Neither warpage nor the largest joint displacement locates the critical joint.
   - The package imposes requirements on decoupling, interconnect, converter height and bonding flatness that no single domain reveals (Sec. VII).

Wording rules for "first": "to our knowledge" once, in contribution 1. Never write "global optimum", "closed loop" or "validated" (say "verified").

---

## 2. Section and subsection outline (9 sections, 21 subsections, 4,800 words of text)

**Terms fixed once (Sec. I or II) and used everywhere:**
- *topology* = (N,K) member;
- *design* = count + topology + parts + f_sw + tier stack;
- *integration* = Z1 embedded, Z2 package-backside, Z3 board-backside (always name and label together);
- *thermal solution* = cooling A (one top cold plate) or B (top and bottom plates);
- *routing loss* = I²R loss in every conductor between the 48-V node and the die pads, including intra-cell connections.

**Banned:** "production state", "reference" (meaning a case), "mode(s)", "screen" (say "sweep"), "escalated", "pending", "campaign", "ladder rung" (say "mesh level").

### I. Introduction — 620 words (+ Table I)
**Purpose:** pose the need for a coupled simulator, show what prior art cannot do, and state the contributions.
**Key message:** at a kiloampere, choosing the integration couples three physics, and the cell count couples the converter to the package. No existing tool carries a synthesized regulator to the joint.

| ¶ | Content | Words |
|---|---|---|
| 1 | Problem: 1–2-kW AI/HPC packages at < 1 V draw ~1 kA; 1 mΩ costs 1 kW; regulation moves into or under the package (near-POL, 2.5-D/3-D); DVPD; integration options Z1 [1], Z2 [8], Z3 [10] (Fig. 1) | 120 |
| 2 | Why coupling is needed. The integration fixes which rail crosses each interconnect (routing), where the converter's heat flows (temperature → loss), and which CTE mismatch loads which joint. The count fixes cell area → admissible parts → tier heights → via depth. An electrically optimal design can break a via rule, the ball current, the cooling, a part rating, the joints or assembly flatness. Close with the requirement: one model chain on one geometry, from system target to solder joint. | 140 |
| 3 | Prior art in three families, each ending with what it lacks: (i) DVPD design frameworks [1] and self-consistent ET [21], [24] (fixed design, lumped T_max, no board, no mechanics); (ii) sign-off tools [12], [14] (given layout); (iii) power-module synthesis and ETM co-simulation [16], [19], [20] (fixed circuit, stand-alone module); plus placement/thermal comparisons [26] and the warpage/reliability review [Kim 2023]. Cite Table I. | 190 |
| 4 | Gap and what is adopted (one sentence each). Adopted from [1]: specification, embedded-stack technology, BGA and TSV rules. From [35], [36]: the hybrid family and loss model. Name what prior art does better (droop and floorplan in [1]; conjugate CFD in [21]; life models in [12], [14]); this concession raises credibility. | 70 |
| 5 | Four contributions (§1.3) and a one-line roadmap | 100 |

- **Move to supplement:** the regulator-demonstration list ([29]–[34]); the paragraph "Relative to its closest predecessors…"; the detailed Table S1.

### II. The ETM-DVPD Framework — 420 words (+ Fig. 1)
**Key message:** a design record is carried from stage to stage on one geometry. Couplings are declared, and the count and integration are outputs of the flow.

**A. Inputs, Outputs and the Design Record (140)**
- *Inputs:*
  - system target: P_load, V_out, V_in, die footprint and power map, J_t, ripple limits;
  - part library: GaN devices, inductors, capacitors with ratings, outlines and loss data;
  - candidate integrations;
  - thermal solution as a boundary map h(x,y), T_f(x,y) on each cooled face, or a coolant model that computes them;
  - part and package limits.
- *Outputs:* ranked feasible designs with loss by conductor and component, temperature, warpage, Δu at every interconnect site, Δε_in at the critical joint, verdicts, and the numerical U95 of each.
- *Design record:* count and grid, topology, parts, f_sw, tier plan and order, decoupling plan. Every stage reads the converter only from this record.

**B. One Geometry and Four Couplings (160)**
- One stack description feeds the ledger and both FE meshes.
- Each ledger term maps to an element set; the deposited heat equals the ledger total.
- The coupling classes:
  - E↔T: two-way, fixed point;
  - T→M: one-way;
  - M→joint: one-way;
  - M→T: optional, through the cold-plate interface gap;
  - M→E: neglected, because α_Cu ΔT is more than 100× smaller than the resistivity TCR (one sentence).
- *Scope stated once here:* steady state; no transient droop; no life prediction.

**C. Designing and Comparing Through the Full Flow (120)**
The end-to-end procedure, in order:
1. The electrical sweep proposes M* and its design record.
2. Each (integration, thermal solution) pair is built, checked for realizability, solved and filtered.
3. Feasible designs are ranked by platform-inclusive loss, with peak temperature and joint response reported beside it. A difference counts only if it is resolved.
4. Neighbouring counts and alternative converters (five tiers) pass through the same chain.
5. Inputs without a defensible single value are varied through the whole chain.

The designer closes the outer loop; say this in one clause.

- **Equations:** none.
- **Move to supplement:** the algorithm box (current Fig. 2) as pseudo-code, and the long "one geometry" paragraph.

### III. Electrical Solver: Synthesizing the Regulator and Its Count — 780 words (+ Fig. 2a, Table II, Fig. 3a)
**Key message:** at every count the regulator is re-synthesized from parts under part-level rules. Its conversion loss and its routing loss are computed on the package geometry, and their sum picks the count.

**A. A Hybrid Family Searched Over a Part Library (160)**
- The (N,K) hybrid SC–buck family: N SC branches, K inductor branches, 2 ≤ K ≤ N, 2N + 2K − 1 parts. D = N·V_out/V_in. K_A = ⌈K/2⌉ and a balanced **B** are fixed by rule, a deliberate reduction of the search space.
- The search space as numbers:
  - up to 42 members, from a part budget of 15 rising to 30 as the cell area allows;
  - 90 GaN transistors from one vendor, 11 inductors, 10 capacitors;
  - 50 log-spaced f_sw values from 43 kHz to 200 MHz, capped at each inductor's rated frequency;
  - ≤ 4.5 × 10⁷ combinations per member, enumerated exhaustively **[verify against `HVR_FULL_OPT_EPC_V2.py`]**.
- Claim this search space, not a "huge library".

**B. Conversion Loss Under Part-Level Rules (230)**
- **Eq. (1), new:** per-cell loss.
  - P_cell = Σ I²_rms R_on(T), including ripple
  - \+ Σ I²_L,rms DCR(T)
  - \+ Σ I²_C,rms ESR(f_sw, V_bias)
  - \+ f_sw · Σ_hard transitions [E_oss(V_node) + E_overlap(R_g)]
  - \+ f_sw · Σ Q_g V_drv,
  - with E_oss = Q_oss V/3 and Q_oss ∝ √V.
- The rules are stated as Table II rows, not prose:
  - voltage stress with derating (S₁ blocks V_in/N, stacked switches max(N−1,2)·V_in/N, C_i holds (N−i)·V_in/N; 0.9 for switches, 0.8 for capacitors);
  - current ratings and I_sat **[state whether I_sat is checked against peak or average current; the code checks average]**;
  - C_eff at bias, 105 °C and minus tolerance, keeping ripple ≤ 10 %;
  - ESR at f_sw;
  - C_oss charged at the actual node swings;
  - 2-D packing in the square cell of side (I_cell/J_t)^½ with a 50-µm keep-out, at most four tiers;
  - ripple limits, with the 50-µF output capacitance assumed and not placed (state it).
- *Validation:* circuit simulation of four other members, worst-case error 7.1 %, rather than "94.4 % accuracy". Add the design-point circuit check (R6). Comparison: the cell efficiency at 25 °C, 91.1 % (27.8 W out, 2.70 W lost), against 90.9 % for the measured hybrid of [38].
- *Omitted terms,* named once: core loss, AC winding loss, dead time, dielectric loss. They are bounded in VII-F.
- *Selection temperature:* 25 °C. R9 tests this, or VI-C states that the coupled chain confirms the count.

**C. Routing Loss on the Package Geometry (230)**
- Every conductor carries its rail and the RMS current of that rail.
- **Eq. (2)** (current Eq. 2): via-field provisioning and resistance, with ρ(T) at the converged temperature.
- Lateral runs are sheets. Z3's land-side and board-plane redistribution is P = κR_s(T)I², stated inline; the shape factors go to the supplement.
- k_rms is defined once:
  - a single cell's input pulse gives 3.8 (1/√D = 4 for an ideal rectangle);
  - with interleaving and the ring it is 2.64;
  - state the ball count at which it was computed (R5).
- **Eq. (3)** (current Eq. 1 with pumping added): P_plat = P_int + (k_rms I)² R_feed + P_pump, where V_in I = P_load + P_int + (k_rms I)² R_feed. Define both boundaries and say which one ranks (P_plat). R* is the feed resistance at which a backside integration loses its lead.
- One sentence each:
  - contact and intermetallic resistance are bounded by the all-solder attach;
  - AC resistance: at 805 kHz the skin depth is 73 µm, thicker than every RDL and plane;
  - droop is outside the scope.

**D. The Count Sweep (160)**
- **Eq. (4):** M* = argmin over M of [ M · min over (member, parts, f_sw) in F(M) of P_cell(I_cell, A_cell) + P_route(M) ], with I_cell = P_load/(V_out·M) and A_cell = I_cell/J_t.
- The physics of each term:
  - per-cell current falls as 1/M;
  - the shrinking cell excludes large parts and branches;
  - switching and gate loss grow with M·f_sw;
  - packing fails from M = 60;
  - routing falls with M.
- P_route must be printed as an equation, according to Decision D2:
  - (a) the ledger of Eq. (2) on the Z1 stack at 25 °C, or
  - (b) the vertical chain and lateral network of [1] without the √f factor.
- 27 counts from 16 to 120. One sentence: the neighbouring counts are carried through the coupled chain in VI-C.

- **Move to supplement:**
  - the node analysis of stacked-switch stress and the C_oss swing derivation;
  - the median-R_g rule; the placement algorithm and the 0.48-mm² budget rule;
  - ESR-at-bias procedure; the fine f_sw grid (788 kHz, −0.46 W: one clause in VI-A);
  - Table S2; the full passive library (new table); J_t sensitivity (R12);
  - the thin-capacitor technology evidence.

### IV. Package Solvers: Realizability, Heat, Deformation and Joints — 900 words (+ Fig. 1a–c, Fig. 2b)
**Key message:** the same cells are placed in three integrations, checked for buildability, solved to an electrothermal fixed point under the thermal solution, solved thermoelastically at every site, and filtered against every limit.

**A. Three Integrations of One Design Record (120)**
- Common to all three: Si substrate 300 µm with 30/60-µm TSVs; BGA 0.8 mm SAC305 with 1,369 sites; board 3.2 mm IT-968G.
- Z1: converter between substrate and die; 48 V crosses BGA and TSVs.
- Z2: converter in a board opening, joined by a 30-µm-pitch Cu-pillar attach; 48 V through a 528-site ball ring.
- Z3: converter on the board underside; 1 V crosses plated through-holes, the full BGA and the TSVs, then spreads laterally.
- Only the placement differs; layer stacks go to the supplement.

**B. Physical Realizability (150)**
- Tier packing and the tier-order rule: via rule first, then routing loss, then heat path.
- Via rule: 120-µm laser microvias at aspect ratio ≤ 1, with capture pads [46], [47].
- Copper posts.
- Assumption stated: die terminals on both faces, with the single-face sensitivity in one clause.
- Ball provisioning: ≤ 2 A per power ball at the implemented waveform, ≤ 75 % of the sites carrying power [44]. Define the checked current (R5).
- Converter height against the depth the integration provides.
- Assembly checks: JEDEC reflow coplanarity at 245 °C [62]; thermocompression-bond gap allowance at 250 °C [45].

**C. Electrothermal Fixed Point and the Cooling Interface (270)**
- Steady conduction on the explicit stack with orthotropic homogenized cards: TSV, attach, RDL, ball, board-via and converter tiers with posts.
- The converter-tier cards are *bounded, not verified*: the post bounds move the peak ≤ 2.7 K; halving the GaN-tier conductivity adds 11.5 K.
- **Eq. (5):** ∇·(k∇T) + q‴(x;T) = 0 in the domain, with −k∇T·n = h(x)[T − T_f(x)] on cooled faces, and R_j(T) = R_j,25[1 + α_j(T̄_j − 25 °C)].
- The thermal solution is the framework's interface. The demonstrated plate gets one sentence:
  - Si microchannels with a fin-efficiency model; Nu = 6.32 for three-wall H1 heating;
  - coolant warming along the flow, iterated with the solid;
  - 4-zone manifold, 27 g/s, 65 kPa; within 0.3 % of conjugate CFD.
- Assumptions stated:
  - TIM 50 µm, 3 W/m·K, about 33 K of the rise **[verify]**;
  - uniform 1-kW die (power map in VII-E);
  - 30-mm coupon board with 10 W/m²K beneath;
  - material cards independent of temperature.
- Fixed point:
  - each ledger term is evaluated at the mean temperature of the element set that receives its heat;
  - R_on coefficient 6.0 × 10⁻³ K⁻¹, fitted over 25–125 °C, which is why 125 °C is a limit; Cu and DCR 3.93 × 10⁻³ K⁻¹;
  - C_oss, Q_g and ESR held at 25 °C (state it);
  - stop at 0.25 K and 0.1 %, reached in 4–6 solves;
  - contraction factor 0.03–0.22, so there is no runaway; energy residual 10⁻⁷.
- One sentence on prior art: [21] updates the loss from the single maximum temperature.

**D. Thermomechanics and the Critical Solder Joint (280)**
- *Global model:*
  - linear thermoelastic on the same mesh; T_ref = 25 °C, so the solution is the power-off → operating excursion;
  - rigid-body restraint only; board and BGA meshed;
  - Δu = ‖u_t − u_b‖_xy at every site of every interconnect layer (inline).
- *Local joint:*
  - driven by the fitted displacement of both pad faces at T_sj (translation, stretch, shear, rotation);
  - 3-s ramps, 300-s dwells, last of four cycles;
  - **Eq. (6)** (current Eq. 6): Δε_in averaged over the core.
- *Three-law band, with the reason:*
  - no calibrated law exists for these joints;
  - the production law creeps 13–73× faster than the measured data;
  - all laws are extrapolated in stress.
  - Every ranking is judged under all three.
- *No life law,* in one sentence: any life relation monotone in Δε_in keeps the ranking.
- *Critical-joint search,* in three sentences:
  - a dominance bound with a 10–11 % margin;
  - it closed in every case, solving 1,051 of 6,532 sites under the production law;
  - it is needed because in 23,211 of 40,555 site pairs ordered by (Δu, T_sj) the dominated site responds more.
- *Interface feedback,* inline: h_loc = (h_eff⁻¹ + g/k_TIM)⁻¹, bounded by a conforming TIM and a rigid plate.
- *Assembly:* isothermal, unconstrained, stress-free at 25 °C; reported as a requirement.

**E. Feasibility Before Ranking (80)**
- The limits are listed once, as the row labels of Table IV's feasibility block:
  - GaN T_jn ≤ 150 °C; R_on fit ≤ 125 °C; capacitor and inductor tiers ≤ 125 °C;
  - dielectric and encapsulant ≤ 150 °C; board ≤ 170 °C; die ≤ 105 °C;
  - hottest joint ≤ 125 °C (solder-law range);
  - static 1-V drop ≤ 30 mV per rail (**define "per rail"**: footnote b of the current Table V implies the supply path and the return path of the 1-V rail, each at 1 kA; confirm with the authors);
  - ball rule; converged operating point.
- A design that fails is reported but not ranked.

- **Move to supplement:**
  - the tier-order algorithm and current Fig. 6 (except the design-point half, which becomes Fig. 2b);
  - card construction; the h_eff equation and hydraulics (current Eq. 4, manifold, entry length, caloric resistance);
  - the Z3 sheet shape factors (current Eq. 3);
  - solder card, surrogate refits and stress windows; the search seeding and margin rule;
  - the local-model setup tables; the interconnect-layer drivers.

### V. Verification and Numerical Uncertainty — 330 words (+ Table III)
**Key message:** each stage agrees with a matched numerical reference. Each compared difference is judged against its own discretization uncertainty, and 19 of 20 are resolved. The framework is verified, not validated against a measured package.

- Table III gives the matched references.
- Production-mesh error, measured from above with MOOSE on refined meshes up to 3.0 M elements: 2.1 K, inside bias + U95 (2.3 K).
- Resolution rule, inline: |D + β_D| > U95(D), with a GCI on D's own mesh levels. 19 of 20 differences are resolved; the only unresolved one is Z3 vs Z1 loss under B. Why per-difference matters: U95(D) = 0.33 W against 1.4 W for the sum of the two cases' own U95.
- Mechanical numerics, one sentence: after R7, the mesh and solver; otherwise the solver and through-thickness terms, which withdraw only Z3/Z1 warpage under B.
- U95 is numerical. Model-form uncertainty is handled by running alternatives through the chain (VII-F).
- Cost:
  - 0.4–0.6 h per coupled evaluation on a two-socket workstation;
  - 18-min count sweep;
  - local joint solves run in parallel;
  - solver versions (CalculiX 2.23, MOOSE).
- **Move to supplement:** the "establishes/does not establish" matrix (current Table III), the verification chart (current Fig. 7), GCI safety-factor rules and the bias formula, per-case U95 (S18), the differences table (current Table IV), runtime and memory (S16).

### VI. End-to-End Design of a 1-kW, 48-to-1-V Package — 480 words (+ Fig. 3a, Table II)
**Key message:** the framework turns the system target into a buildable design. Temperature, not the electrical sweep, sets the count's margin.

**A. Conversion Meets Routing at 36 Cells (200)**
- *Opens with:* what an electrical-only sweep sees.
- Body:
  - 27 counts; 18 admit a four-tier member; nine different members are selected; none fits four tiers from 60 cells;
  - optimum M = 36, N3K3, EPC2014C/EPC2055, 805 kHz, 2.99 mm; 102.4 W = 97.2 conversion + 5.2 routing (update these after R2);
  - which term sets the optimum (§4.1);
  - five tiers: N4K4, −10.9 W, 3.73 mm;
  - the same inductor and capacitor are chosen at every count, so credit the topology, switches and f_sw;
  - the inductor-technology result (R3).
- *Closes with:* the count is a synthesis output, not an input.

**B. Copper Posts and Interleaved Clocks Make It Buildable (140)**
- No tier order meets the via rule (worst aspect ratio 8.3 against 1; best of 548 regroupings 5.7), so copper posts are required.
- The part-to-tier assignment changes intra-cell routing from 5.35 to 13.2 W.
- Decoupling:
  - capacitance inside the stack resonates and raises k_rms (3.8 → 5.2, and 13 at the worst inductance);
  - 12 interleaved phases set k_rms (2.71 alone, 2.64 with the ring);
  - k_rms sets the ball count (170 per rail at 1.98 A; bare pulses would need 2.6 A per ball even at 220).
- *Rule:* decouple by interleaving, not inside the stack.

**C. Temperature Reprices the Design (140)**
- The coupled embedded design loses 29 % more than its 25 °C ledger (137.0 vs 106.1 W), on the same basis as [21]'s +15.8 %.
- One sentence reconciling with [21]'s 231 W: a fixed 64-cell DSCH design at 3.6 MHz and 2 A/mm², against the synthesized one here.
- The neighbours, 8.1 and 17.6 W behind in the sweep, fall 24.3 and 35.3 W behind once coupled. Both fail under cooling A, and their joints respond 15–22 % more.
- Model and material validity bind before device ratings: margins 11.4 K (R_on fit), 12.2 K (capacitor), 12.1 K (solder range), 17.3 K (die), against 36.4 K to the GaN rating.
- *Rule:* the count's margin is thermal.

- **Move to supplement:** the decoupling detail (85-pH loop, 29–650-pH band, 12 µF per cell, 16 × 0402 per cell), the microbump driver, neighbour warpage, and the per-tier temperatures.

### VII. Three Integrations Through the Full Flow — 1,000 words (+ Fig. 3b, Fig. 4, Fig. 5, Table IV, Table V)
**Key message:** every added physics or boundary reorders or removes candidates, and no single domain or cooling returns the answer.

- **A. Routing Versus Conversion Across Integrations (140):**
  - the common-temperature view (routing only);
  - the coupled waterfall (Fig. 3b): moving the converter out of the package removes the 48-V network but adds kiloampere 1-V conductors, and the hotter converter returns part of the saving as conversion loss.
  - *Rule:* rank on the converged state.
- **B. The Thermal Solution Picks the Integration (230):**
  - Cooling A:
    - Z3 fails its ratings;
    - Z1 and Z2 tie at the platform within the feed range;
    - Z2's 2.2-W package lead depends on the decoupling;
    - a rigid plate on the warped die removes Z2.
  - Cooling B:
    - the bottom plate is an electrical decision for Z2 and a mechanical one for Z1;
    - Z2 leads in platform loss, peak temperature and joint strain.
  - One clause on R11 if run (the cooling each integration needs).
  - *Rule:* choose the thermal solution with the integration.
- **C. Board-Backside Regulation Fails on Its 1-V Path (110):**
  - Z3-B passes every rating but drops 46.2 mV, of which 25.0 mV is lateral redistribution;
  - its 1-V balls take 73 % of the sites;
  - no cooling fixes it.
  - *Rule:* size the 1-V lateral path before the cooling.
- **D. The Flattest Die Has the Most Strained Joints (220, Fig. 5):**
  - Z1's joints run hot and carry the membrane mismatch between board and silicon;
  - in the backside integrations, much of Δu is rigid rotation;
  - in Z2-A, the largest-Δu joint is not critical.
  - State the board condition with the claim (R4).
  - *Rule:* judge joints by their own response, from an all-site search.
- **E. Requirements No Single Domain Reveals (150):**
  - the shallowest integration bounds converter height (five-tier co-design, a Pareto pair);
  - bonding flatness of the fine-pitch attaches;
  - the die power map;
  - the signal-site budget (Z2 196 sites left, Z3 369).
- **F. Which Physics and Which Conditions Change the Verdict (150, Table V):**
  - read the ladder;
  - name the conditions that reverse a verdict;
  - give the verdict counts **[update]**;
  - end with the answer for each thermal solution.

- **Move to supplement:**
  - current Fig. 9(a) (rail currents), Fig. 10 and Fig. 11;
  - low-CTE and cure-referenced assembly cases; interconnect-layer local responses;
  - thin-capacitor and caloric variants; VIII-H screening mechanics;
  - mounting and clamp subcounts; card-bound detail; ball-rating detail; omitted-loss detail (Table S23).

### VIII. Limitations — 160 words
All in one paragraph, without repeating numbers already given:
- verified, not validated against a measured system;
- the loss model is validated on sibling members, and the omitted terms (6.5–55 W) are bounded;
- the inductor is a design target, not a fabricated part;
- the solder laws are uncalibrated, so Δε_in is comparative and no life is predicted;
- the 2-A ball rule is an assumption (at 1.5 A nothing is feasible);
- the board is a coupon, and the joint ranking depends on the board's rim;
- steady state only, with no droop and no transients;
- assembly is isothermal from a stress-free 25 °C;
- one specification: the mechanisms and rules generalize, the numbers do not.

### IX. Conclusion — 110 words
- The answer for each thermal solution (§4.4).
- Three rules:
  1. rank feasible designs on the converged state at the platform boundary under one thermal solution;
  2. choose the cooling together with the integration;
  3. find the critical joint by its own response.
- One line of outlook: transient/droop, a calibrated life law, measured validation.
- No new numbers.

---

## 3. Figure and table plan (5 figures and 5 tables, down from 11 and 5)

| New | Content | Source | Size (page) | Message |
|---|---|---|---|---|
| **Fig. 1** | (a)–(c) half-sections of Z1–Z3 to scale, in the style of current Fig. 5: rails colored, the rail current written per layer, cold plates/TIM/board film drawn as boundary conditions, the critical joint ringed, and an inset of the joint submodel with its drive. (d) The flow: target + library → [count sweep × HVR optimizer] → design record → [stack builder + realizability] → [ledger ⇄ thermal fixed point] → [thermoelastic, all sites] → [critical-joint search] → [feasibility] → ranked designs. Outer loops over integrations, thermal solutions and robustness variants. Data written on every arrow: q‴(x); T → R(T); T(x) → thermal strain; u at the cut boundary + T_sj → joint; g(x,y) → TIM. Stop criteria in small type. Badges on the blocks prior art lacks (matching Table I rows). | Redraw: merges current Figs. 1, 2 and 5 | double, 0.42 | What the simulator is and how it couples |
| **Fig. 2** | (a) The (N,K) family and the selected N3K3 cell, with blocking voltages and branch currents. (b) The four tiers of the design record to scale, with copper posts and the worst via aspect ratio per net class (8.3 against 1). | Merge current Fig. 3(a) with the design-point half of Fig. 6; drop the timing trace | single, 0.18 (0.14 without b) | The synthesized converter and why posts are needed |
| **Fig. 3** | (a) Count sweep: conversion, routing and total against M (four-tier rule), with the selected member printed at each count, crosses where no four-tier member exists, the five-tier total faint, and M = 36 starred. Stacked conduction/switching/routing bars are an option. (b) Waterfall of package-internal loss, Z2−Z1 and Z3−Z1, under cooling A: routing removed or added, conversion change caused by temperature, net. | Redraw current Fig. 4(a) with the losses split; current Fig. 9(b,c) | single, 0.32 | Conversion against routing at both scales (count and integration) |
| **Fig. 4** | Under cooling A: (a)–(c) temperature sections; (d)–(f) die warpage; (g)–(i) Δu over the ball field, with the largest-Δu joint and the critical joint marked and Δε_in printed. | Keep current Fig. 8, about 25 % shorter | double, 0.32 | It is a real 3-D coupled solution; the joints do not follow the warpage |
| **Fig. 5** | (a) Δε_in at the critical joint against die warpage, with Δu_c as marker size, for the six cases plus the two neighbouring counts (and five-tier Z1-B if R10 is run); three-law band as error bars. (b) Z2-A: Δε_in of every solved site against Δu, with the largest-Δu and critical joints marked. | New, from `solder_critical_v2.json` and `solder_law_band.json` | single, 0.22 | The flattest die has the most strained joints, and the largest-Δu joint can be the wrong one |
| **Table I** | Capability comparison: 12 rows in groups Design / Physics / Feasibility & credibility; columns [1], [21], [16]/[19]/[20], [12]/[14], this work; ≤ 3 footnotes. Concede droop, floorplan, conjugate CFD and life. Drop the "technology-neutral cooling" and "runtime" rows. | Trim current Table I using the SOTA report §4. **Verify the PowerSynth/[20] cells against full texts.** | single, 0.20 | What prior art cannot do |
| **Table II** | Specification → search space and rules → synthesized design record (parts with rating against stress; inductor labelled "design target, basis [39]") → package and cooling (5 rows) | Trim current Table II, adding the search-space and rule rows | single, 0.28 | Reproducible inputs and the synthesized design |
| **Table III** | Check · reference · max error, about 11 rows: cards 1.3 % (RDL series rule replaced, 12.5 %); networks 0.13 %; thermal unit cells 0.1 % of rise; full Z1 package on the identical mesh 5 × 10⁻⁵ K; refined to 3.0 M elements 2.1 K; thermoelastic 0.43 % (closed form), 0.01 % (FE); iterative vs direct solver 2 % in Δu_c, 13 % in warpage (or the R7 result); cold plate vs CFD 0.3 % ΔT, 0.7 % Δp; local L0–L3 2.9 %; loss model 7.1 % worst; fixed point 0.25 K/0.1 %, energy 10⁻⁷ | Merge current Table III and Fig. 7 | single, 0.17 | Every stage is verified |
| **Table IV** | Z1–Z3 under A and B, about 16 rows. *Performance:* platform-inclusive loss (primary) and efficiency; package-internal loss ± U95 (* = unresolved); conversion/routing; peak T ± U95; GaN T_jn; die max; heat to bottom plate. *Mechanics:* warpage ± U95; Δu_c ± U95; T_sj; Δε_in [band]. *Interconnect:* 1-V drop per rail; power balls per rail and % of sites. *Feasibility:* limits failed (or the binding margin); ranked. Feed R and pumping go in a footnote. | Trim current Table V; absorb current Table IV as ± and * | double, 0.34 | The comparison, with every number in one place |
| **Table V** | **Verdict ladder.** Rows add one level of physics or boundary and name the prior art at that depth; columns give verdict A, verdict B and the deciding number (§4.3). Then a conditions block (decoupling state, nominal omitted losses, 1.5-A balls, 3× board with cold rim, "no ranking change" list) and the verdict counts **[update]**. | New: replaces current VII-F, IX-A, the narrative of Fig. 10 and Fig. 11 | single, 0.28 | No single domain gives the answer, and how robust each verdict is |

**Totals:** figures 1.46 pages; tables 1.27 pages; 10 floats = 2.73 pages.

**Cut order if over budget:**
1. Fig. 2(b) (−0.04);
2. Fig. 5 becomes Δε_in annotations in Fig. 4(g)–(i) plus one sentence (−0.22);
3. the package block of Table II moves into the text (−0.05).

---

## 4. Results plan

### 4.1 Results kept, with the numbers to quote (all verified unless marked)

**VI-A Count sweep**
- 27 counts (16–120); 18 admit a four-tier member; 9 different members.
- Routing falls from 12.0 W (M = 16) to 4.2 W (M = 56). Conversion is lowest at M = 36 (97.25 W).
- Optimum 102.4 W = 97.2 + 5.2 W: N3K3 (K_A = 2, **B** = [1,1,1]), D = 0.0625, 805 kHz (788 kHz on a 16× finer grid, −0.46 W), EPC2014C/EPC2055, four tiers, 2.99 mm.
- Square grids: 16 → 141.4 W; 25 → 110.6 W; 49 → 120.0 W; 64 and 81 infeasible.
- Five tiers: N4K4 at 957 kHz, 91.5 W (−10.9 W), 3.73 mm. With no tier limit: 49 cells, 83.4 W, seven tiers, 5.54 mm.
- **What to say honestly:**
  - for this target, the conversion term places the optimum;
  - routing adds a slope that penalizes small counts (+6.8 W at M = 16 relative to M = 36);
  - packing ends the feasible range at M = 56.
  - Update with R2; if D2-a is chosen, the routing slope may grow.

**VI-B Buildable stack**
- 24 tier orders; worst aspect ratio 8.3 against 1; best of 548 regroupings 5.7; thin capacitor ≥ 5.7.
- Intra-cell routing 5.35 W for the chosen order, 13.2 W with the worst assignment.
- k_rms:
  - single-cell pulse 3.79 (1/√D = 4.0);
  - in-stack capacitors 5.2 (13 at the worst inductance);
  - ring alone 3.91;
  - interleaving alone 2.71;
  - interleaving + ring 2.64 (2.62–2.66).
- Balls: Z1 170 per rail at 1.98 A; Z2 166 at 1.94 A; Z3 500 at 2.0 A. Bare pulses would need 2.6 A per ball even at 220 per rail.
- **[R5]** k_rms at 170 balls is 2.42, and the harmonic worst ball is 2.2 A RMS. Reconcile before quoting.

**VI-C Coupled embedded design**
- 137.0 W (88.0 % package-internal), against 106.1 W at 25 °C: +29 % (understated by 23 %). [21] reports +15.8 %.
- Low-side devices take 74.3 W of the 125.1 W conversion loss (59 %).
- Peak 113.0 °C, in the input-end tier.
- Margins: R_on fit 11.4 K; capacitor 12.2 K; solder range 12.1 K; die 17.3 K; GaN rating 36.4 K.
- Neighbours:
  - sweep: 8.1 W (M = 25, N4K2) and 17.6 W (M = 49, N3K2) behind;
  - coupled under A: 24.3 and 35.3 W behind (161.3 and 172.3 W; peaks 130.2 and 127.0 °C);
  - under B: 23.7 and 34.5 W behind;
  - both infeasible under A;
  - Δε_in 8.30 and 8.05 against 6.81 × 10⁻³ (+22 % and +18 %), resolved under all laws.

**VII-A Routing vs conversion**
- At a common temperature (25/100 °C), conversion is identical. Z2 is 2.8/3.9 W below Z1; Z3 is 20.6/44.4 W above.
- Coupled under A:
  - Z2−Z1 = −4.86 W (48-V package path) + 0.52 (TSVs) + 0.22 (attach) + 0.07 (intra-cell) + 1.85 (conversion, +4.4 K) = −2.21 W;
  - Z3−Z1 = +43.1 W, of which 11.5 W is board vias and 1-V BGA, 8.27 W lateral spreading, and 24.3 W conversion (+66.6 K).

**VII-B Thermal solution**
- **Cooling A:**
  - Z3: 180.1 W, T_jn 180.8 °C, fails ratings (and 55.0 mV).
  - Package-internal: Z2 134.8 against Z1 137.0 W (D = −2.30/U95 0.33).
  - Platform: Z1 140.2 against Z2 145.4 W with the ball-ring feed (1.89 mΩ). R* = 0.6 mΩ, below every evaluated feed (0.62–1.89 mΩ), so Z1 is lower by 0.3–5.2 W **[verify 0.3 W at 0.62 mΩ]**.
  - Z2 runs 5.5 K hotter.
  - Ideal decoupling flips the package ranking (Z1 lower by 2.3 W).
  - Rigid plate:
    - Z1 gap 12 µm → 141.1 W, 123.7 °C, margin 0.5 K;
    - Z2 gap 37 µm → 152.3 W, 178.7 °C, die 143.2 °C → infeasible.
- **Cooling B:**
  - Z2: −16.6 W and −41 K relative to its cooling-A case, with 139 W leaving through the bottom plate.
  - Z1: −0.9 W (9 W through the bottom plate). Warpage 17.5 → 5.2 µm and Δu_c 1.94 → 0.77 µm, yet Δε_in only 6.81 → 5.60.
  - Z2 vs Z1:
    - package-internal −17.9 W (−18.16/0.33);
    - platform 128.6 against 139.3 W (−10.6 W; R* = 4.6 mΩ);
    - peak −32 K (77.0 against 109.3 °C);
    - Δε_in 1.55 against 5.60 (3.6× lower).
  - The rigid plate under B: +0.9 W (Z1), +1.7 W (Z2); both stay feasible.

**VII-C Z3**
- Under B: 136.9 W, 78.0 °C, every rating met.
- 1-V drop 46.2 mV = 16.1 (land side) + 8.9 (board planes) + 21.2 (vertical), against 30 mV.
- Lateral loss 4.8 + 2.8 = 7.6 W. Without it the drop would pass and the loss would fall to about 129 W, below Z1-B's 136.1 W. This is a decomposition, so say "about".
- 500 balls per rail (73 % of 1,369 sites), leaving 369.
- Z3 against Z1 loss under B is the one unresolved difference (+0.58/0.62).

**VII-D Joints**
- Δε_in (×10⁻³), production law:

  | | Z1 | Z2 | Z3 |
  |---|---|---|---|
  | Cooling A | 6.81 | 3.35 | 3.11 |
  | Cooling B | 5.60 | 1.55 | 2.13 |

  - Lowest law: A 5.97/2.55/2.34; B 4.77/0.81/1.36.
  - Z1 is 2.0–3.6× the others; the ordering holds under all three laws; every difference is resolved.
- T_sj: Z1 112.9 (A) and 105.0 (B) °C, against ≤ 96.2 °C elsewhere.
- Deforming Δu at the critical joint: Z1 1.97 and 1.61 µm, against ≤ 1.36 µm elsewhere.
- Rigid rotation: Z2-A 1.50 µm, Z3-A 2.40 µm.
- Z3-A has the largest Δu (3.74 µm) and the smallest Δε_in.
- Z2-A's critical joint is an inner ring site, 79.7 % above the largest-Δu joint. Z2-B's is the mirror corner (1.068×).
- 23,211 of 40,555 site pairs reverse (up to about 7×).
- Condition: a 3× board with a 25 °C rim reverses Z1/Z2 under A; B holds **[R4]**.

**VII-E Requirements**
- Five-tier converter:
  - −22.2 W in Z1 (A 114.8 W; B 113.9 W, feasible, 108.9 °C);
  - protrudes 273 µm below Z2's 3.2-mm board (the four-tier stack clears it by 469 µm); in Z2 it would save 17.7 W under B;
  - under B, five-tier Z1 (113.9 W) loses less than four-tier Z2 (118.1 W), but Z2 runs 32 K cooler with 3.6× lower joint strain at four tiers. A Pareto pair **[R10 for five-tier Δε_in]**.
- Bonding gaps: 147.6 µm (Z1) and 61.5 µm (Z2) against an 8-µm allowance; Z3 12.0 against 50 µm.
- Reflow coplanarity: 80/127/81 µm against 80 µm.
- Core-heavy die map: Z1 108.6 (A) and 108.1 (B) °C; Z2-A 107.1 °C plus converter failures. Only Z2-B meets every limit (die 97.4 °C). Z3-B keeps its die at 96.8 °C but still fails the 1-V drop.

**VII-F Conditions**
- Decoupling state: flips the A package ranking.
- Nominal omitted losses (25 W, 21 W of it dead time):
  - Z2-A exceeds the R_on fit and the capacitor class (127.5 and 126.9 °C);
  - gaps shift by ≤ 0.9 W (A, toward Z1) and ≤ 3.9 W (B, toward Z2);
  - Z1 needs 174 balls per rail.
- Upper omitted losses: Z1 also fails; the sweep prefers M = 50 by 2.5 W.
- C_oss law: 13.2 W against 7.4 W from datasheet curves (conservative).
- 1.5-A ball rule: no integration is feasible (Z1 1.73 A at 220 balls; Z2 needs 77 % of sites; Z3 needs 667 balls).
- 0.1× passive-tier conductivity: removes Z1 (219 °C).
- No ranking change from: feed model, board films, mounting and clamp (Δε_in −48 to +190 %, ordering kept on the coupon), the solder-law band, post bounds, caloric resistance (+0.9–3.0 W), thin capacitor (≤ 1.4 W).
- Counts: 153 verdicts over 51 decisions = 124 preserved / 4 withdrawn / 5 reversed / 20 pending. Joint column: 38 preserved, 5 pending. **[update after the five reruns]**

### 4.2 The "unexpected findings" narrative (the spine of Secs. VI–VII)
Read as a progression in which each added physics overturns the previous answer:
1. **Electrical intuition says move the regulator out of the package.** At a common temperature the package-backside regulator wins by routing alone, and the board-backside regulator (today's practice) loses but looks feasible.
2. **Temperature reprices the design.** Coupling adds 29 % to the loss, triples the count's margin and removes both neighbours. Under a top plate, Z2's converter runs hotter and gives back part of its routing saving, and Z3 cooks at 181 °C.
3. **The boundary flips the ranking.** Z2's 48-V feed carries the cells' residual pulse, so at the platform the embedded regulator matches or beats it.
4. **The thermal solution picks the integration.** A bottom plate cuts Z2's loss by 16.6 W and its peak by 41 K, while for Z1 it mainly flattens the die. The same plate is an electrical decision for one integration and a mechanical one for the other.
5. **Today's board-backside layout fails on its 1-V path, not on cooling.** Lateral redistribution in the land side and board planes takes 25 mV of the 46-mV drop.
6. **The flattest die has the most strained joints.** Z1's hot, membrane-loaded corner joints respond 2.0–3.6× more than the backside integrations, whose larger displacement is partly rigid rotation. Inside one package, the joint that moves most is not the one that strains most.
7. **The domains feed back into each other.**
   - Warpage opens the cold-plate interface and removes Z2 under a rigid plate.
   - The board's thickness rules out a converter 22 W better.
   - The integrations flattest in operation are the hardest to bond.
   - A realistic die map leaves only the dual-cooled package-backside design within limits.

### 4.3 Table V (verdict ladder), proposed rows
| Level added (prior art at this depth) | Cooling A | Cooling B | Deciding number |
|---|---|---|---|
| Electrical, common temperature ([1]) | Z2 < Z1 ≪ Z3 | same | Z2 −2.8…−3.9 W; Z3 +20.6…+44.4 W |
| + E–T fixed point, declared cooling ([21]) | Z3 infeasible; Z2 < Z1 (package) | Z2 < Z1 | T_jn 180.8 °C; −2.2 / −17.9 W |
| + Platform boundary (feed, pumping) | Z1 ≤ Z2 | Z2 < Z1 | R* 0.6 / 4.6 mΩ vs feeds 0.62–1.89 mΩ |
| + Lateral 1-V redistribution, static drop | Z3 out | Z3 out | 46.2 mV vs 30 mV |
| + Thermomechanics of a given layout ([12], [14]) | Z1 flattest | Z1 flattest (vs Z3 unresolved) | 17.5 vs 58.1/46.9 µm |
| + All-site joint response (this work) | Z1 most strained | Z1 most strained | 6.81 vs 3.35/3.11 (×10⁻³) |
| + Interface feedback (rigid plate) | Z2 infeasible | both feasible | 178.7 °C |
| + Realizability and assembly | posts; bonding gaps Z1, Z2 | same | AR 8.3; 147.6/61.5 vs 8 µm |
| + Core-heavy die map | Z1, Z2 exceed die limit | only Z2 feasible | 108.6/107.1 vs 97.4 °C |
| **Verdict** | **Z1 (margins 11–17 K)** | **Z2 (robust)** | |
| Condition: ideal decoupling | package ranking → Z1 | — | 2.3 W |
| Condition: nominal omitted losses | Z2 infeasible | ranking kept | 127 °C; ≤ 3.9 W |
| Condition: 1.5 A per ball | none feasible | none feasible | 1.73 A at 220 balls |
| Condition: 3× board, 25 °C rim | joint ranking reverses | kept | [R4] |
| Counts | 124/4/5/20 of 153 [update] | | |

### 4.4 The answer the conclusion states
- **Top plate only:** the embedded regulator is the only integration feasible across interfaces and the nominal omitted losses. Its electrical lead at the platform depends on the feed, and a core-heavy die map consumes its 11–17-K margins.
- **Top and bottom plates:** the package-backside regulator leads in platform loss (−10.6 W), peak temperature (−32 K) and joint strain (3.6× lower). It is the only design that meets every limit under the core-heavy die map.
- **Board-backside:** infeasible under both until its 1-V lateral path is redesigned.

---

## 5. Reviewer-concern coverage

| # | Anticipated concern | Where the paper answers it | Needs |
|---|---|---|---|
| 1 | The inductor (250 nH, 1.6 mΩ, I_sat 23 A in 1 mm² × 0.5 mm) is implausible, and it is chosen at every count | Table II row ("design target", basis [39]); III-B; VI-A sentence with the R3 result; VIII | R3; Decision D1 |
| 2 | Routing model, and whether "conversion vs routing" is real | III-C/D with Eqs. (2) and (4) printed; Fig. 3(a) shows the split; VI-A says what sets M*; Fig. 3(b) shows the integration-level trade | R2; Decision D2 |
| 3 | Loss model not validated at the design point; C_oss and R_g rules unvalidated | III-B (worst 7.1 %; design-point circuit check; comparison with [38]); VII-F (C_oss conservative) | R6 |
| 4 | Omitted losses (dead time 21 W) exceed several gaps | VII-F and Table V row; Z2-A marked conditional; VIII | Decision D3 |
| 5 | Synthesis scored at 25 °C | III-B statement; VI-C coupled confirmation of the neighbours | R9 (optional) |
| 6 | Novelty against [1], [21] (shared authors) and commercial ETM sign-off | I ¶3–4; Table I with concessions; contributions; VI-C reconciles 231 W vs 137 W | — |
| 7 | Verified, not validated; converter-tier cards unverified | V (Table III); IV-C card bounds (≤ 2.7 K; GaN-tier k/2 → +11.5 K); VIII | R13 (optional) |
| 8 | Mechanical numerics (13 % solver term, 37 % through-thickness term) | V, one sentence; Table III row | R7 |
| 9 | Coupon board; joint ranking depends on the board rim | IV-C assumptions; VII-D states the condition; Table V row | R4 |
| 10 | Assembly: temperature-independent encapsulant, stress-free reference | VII-E reports the gap as a requirement with its range (cure-referenced reflow 35/55/35 µm); VIII | R15 (optional) |
| 11 | Fairness: shared converter, different boundaries, Z3 under A | II-C and VII: platform-inclusive primary; VII-E five-tier co-design; one sentence that Z3 needs a bottom plate, which is why B exists | — |
| 12 | Generality: one target, one package | VIII; II-C (inputs are general); optional cooling-requirement thresholds or J_t sensitivity | R11, R12 (optional) |
| 13 | Solder model: uncalibrated; core average excludes the interface band; microbumps unranked | IV-D (three-law band, why; no life); VIII; one sentence on why the BGA is the ranked layer | R14 (optional) |
| 14 | Electrical fidelity: AC resistance, droop, C_out | III-C (skin depth vs conductor thickness); II-B scope; III-B (C_out assumed) | — |
| 15 | Ball rule from one paper, applied at 113 °C; electromigration; signal path | IV-B/E; VII-F (1.5 A → none feasible); one sentence on current densities (~2 × 10³ A/cm² in balls **[verify]**, TSVs similar); VII-E site budget; Z1 signal path through the inter-cell gaps (0.89 mm) as an assumption | R5 |
| 16 | U95 is numerical only; the 2.2-W gap; R_on fit used as a limit; uniform die | V; VII-B (the 2.2-W lead is conditional); IV-C (why 125 °C); VII-E (die map) | — |
| 17 | k_rms bookkeeping (4.0 / 3.79 / 3.78; 2.64 at 220 vs 2.42 at 170; harmonic 2.2 A) | III-C defines k_rms once; VI-B quotes one consistent set | R5; Decision D9 |
| 18 | Verdicts still pending | VII-F counts; nothing pending at submission | five reruns |
| 19 | Reproducibility | V (solver versions, runtimes); Table II (all inputs); Data Availability (on request, author decision) | — |
| 20 | Neglected couplings (M→E; temperature dependence of switching loss) | II-B; IV-C | — |
| 21 | Die terminals on both faces, but the EPC parts are single-sided | IV-B, with the single-face sensitivity (same order, AR 8.3) | — |
| 22 | "30 mV per rail" undefined | IV-E definition | — |

---

## 6. Reference plan and biographies

**Count:** 36 core references (≈ 1.05 pages at 0.029 page each). Up to 4 optional references cost about +0.03 page each.

**Core 36,** with current numbers:
- Motivation and integrations:
  - [1] Krishnakumar TCPMT 2026; [2] Ye TCPMT 2026; [3] Swaminathan TCPMT 2026;
  - [8] Arm cut-out VR patent (Z2); [10] LEGO-PoL (vertical modules, Z3).
- Tools and frameworks:
  - [12] RedHawk-SC ET; [14] Sherlock;
  - [16] PowerSynth; [19] PowerSynth reliability; [20] ETM co-simulation of SiC modules;
  - [21] Choi TCPMT 2026; [24] Choi TCPMT 2025; [26] Xu TCPMT 2019 (VR top/bottom placement).
- **New:** Kim et al., TCPMT 13(10), 2023, review of 2.5-D warpage and interconnect reliability (already in `refs.bib` as `Kim2023Review25D`).
- Converter and parts:
  - [35] ECTC 2025; [36] EPEPS 2026 (doi 10.1109/EPEPS70015.2026.11792885);
  - [37] DSCH; [38] DPMIH (also the measured 90.9 % hybrid);
  - [39] Rasheedi TCPMT 2026; [40] GRM188; [41] EPC2014C; [42] EPC2055.
- Package rules: [44] ball I_max; [45] 30-µm TCB; [46] chip embedding; [47] IPC-2226A; [62] JEDEC JEP95.
- Thermal: [49] Shah & London; [50] Qu & Mudawar.
- Solder: [54] Schubert; [55] Xiao; [56] Yuan.
- Solvers and uncertainty: [57] MOOSE; [59] CalculiX; [60] Roache; [61] Celik.

**Optional, in this order:**
1. Avula et al., TCPMT 12(1):131–146, 2022, "Multiphysics challenges and opportunities for IVRs". Read it before citing; it is the most direct TCPMT motivation for a coupled simulator.
2. [58] Timoshenko, only if Table III names the closed form.
3. [30] MSC-PoL (regulator demonstration).
4. [9] Vicor (industrial anchor for Z3).

**Supplement only:** [9], [13], [15], [17], [18], [22], [23], [25], [27], [28], [43], [48], [51], [52], [53], [58].
**Drop:** [4], [5], [6], [7], [11], [29], [31], [32], [33], [34].

**Biographies:**
- Three biographies of about 70–90 words each (degree, position, research interests, membership), with photos if the template asks for them; about 0.30 page in all.
- Choi et al., TCPMT, July 2026, prints none. Check the current TCPMT author instructions; if biographies are not printed, the 0.30 page becomes reserve.

---

## 7. Page-budget arithmetic (IEEE two-column, ~1,000 words per full text page)

| Item | Basis | Pages |
|---|---|---|
| Front matter: title, byline, 200-word abstract, index terms, first-page footnotes (equal contribution, funding, affiliations) | | 0.45 |
| Text | 4,800 words (I 620, II 420, III 780, IV 900, V 330, VI 480, VII 1,000, VIII 160, IX 110) | 4.80 |
| Display equations | 6 (P_cell, via field, platform loss, count objective, thermal/E–T, Δε_in) | 0.20 |
| Headings and float spacing | 9 sections, 21 subsections | 0.25 |
| Figures | 0.42 + 0.18 + 0.32 + 0.32 + 0.22 | 1.46 |
| Tables | 0.20 + 0.28 + 0.17 + 0.34 + 0.28 | 1.27 |
| Data availability | 2 lines | 0.02 |
| References | 36 × 0.029 | 1.05 |
| Biographies | 3 × ~80 words | 0.30 |
| **Total** | | **9.80** |
| **Reserve** | | **0.20** |

**Calibration on the current paper.** The same per-item rates applied to the current paper (~14,700 words of prose, 11 figures ≈ 4.3 pages, 5 tables ≈ 1.5, 62 references ≈ 1.83, front ≈ 0.6) predict 23.5 pages against the actual 23. The rates are slightly conservative: current text pages hold about 1,050–1,150 words.

**Word discipline:**
- Each number is stated once: in a table, or in the one sentence that interprets it.
- Use at most one number per sentence when possible.
- Rules become the closing sentence of their finding (IX-A of the current paper is deleted).
- The conclusion repeats no numbers.

---

## 8. Supplement structure (grows from 21 pages; holds derivations, algorithms and secondary results only)

- **S-I Prior work.** Detailed capability table (current Table S1), with a PowerSynth/[20] column and a passage cited for every cell.
- **S-II Converter synthesis.**
  - Member enumeration and part budget; the full loss equations; the stacked-switch stress and C_oss node-swing derivations; the gate-resistance rule.
  - Placement and tier-packing algorithm.
  - **New:** full part library, with the 11 inductors (L, DCR, I_sat, area, height, f_max, source, measured or target) and the 10 capacitors (bias data).
  - Selection at every count (Table S2) with the fine f_sw grid; J_t sensitivity (R12); the count-sweep routing model and its equations; circuit-simulation validation, including the N3K3 check (R6); thin-capacitor technology evidence (current S7).
- **S-III Package construction and realizability.** Layer stacks; material cards; tier-order search and regrouping (current Fig. 6 and its text); copper-post sizing; via rules; single-face terminal sensitivity; ball provisioning procedure.
- **S-IV Electrical ledger.** Input states and the decoupling port model (in-stack capacitors, ring, interleaving, loop-inductance band); feed crossover R*; Z3 lateral redistribution (sheet equations, shape factors, grid check); rail currents per class (current Fig. 9(a)).
- **S-V Thermal model and cooling.** Tier cards and bounds; the cold-plate model (current Eq. 4), manifold hydraulics, entry length; CFD check; heat balance (current S8); caloric-resistance variant; TIM-gap feedback iterations.
- **S-VI Mechanics and the solder joint.**
  - Thermoelastic setup; interconnect-layer drivers (current S15).
  - Local model geometry, boundary conditions and cycle (S11); solder cards and law band, with sources, windows and surrogate refits (S9–S10).
  - Critical-joint search algorithm, margin rule and closure statistics (S13); local checks for mesh, cycles, dwell, ramp and averaging band (S12, S14).
- **S-VII Verification and uncertainty.** Verification matrix (current Table III); verification chart with runtimes (current Fig. 7); mesh levels, GCI safety factors, bias formula; per-case U95 (S18); table of compared differences (current Table IV); solver-term and through-thickness checks (or the R7 results); meshes, runtimes, memory (S16).
- **S-VIII Results detail.** Feasibility of every limit in every case (S19); fields under cooling B; neighbouring-count fields and joints; five-tier and thin-capacitor cases; current Fig. 10 (full comparison chart); waterfall under cooling B.
- **S-IX Robustness and conditions.**
  - Variant list (S22) and robustness map (current Fig. 11), updated after the five reruns.
  - Board, mounting, clamp and encapsulant variants (S26); omitted losses (S23); die power map; ball rating at 1.5 A; assembly warpage at reflow and bonding, with the low-CTE and cure-referenced cases (S25).

Rule: no main-text claim may rest only on the supplement. Each main claim keeps its decisive number in Tables II–V or Figs. 3–5.

---

## 9. Open decisions, pre-writing runs and risks

### 9.1 Open decisions for the authors (real choices only)

**D1. Inductor.**
- (a) Keep the design-target part with no sensitivity. This was the prior decision; reviewer risk is high.
- (b) **Recommended:** keep it as the baseline and run R3. Report in one sentence of VI-A what the library alone yields and whether the integration rankings survive.
- (c) Rebuild the baseline on a library-only design. This is a full rerun.
- What a reviewer will compute: ½LI_sat² = 66 µJ in 0.5 mm³. Even the 11.6-A operating peak needs about 0.4 mm³ of metal-composite core (taking µr ≈ 15 and B_sat ≈ 1.25 T). The cited array [39] gives 50 nH, 8.2 mΩ and 2 A per 0.2-mm² segment (figures from the internal audit of 2026-11-18; **[verify against [39]]**). Five segments therefore cannot give 250 nH and 1.6 mΩ at once.

**D2. Routing model of the count sweep.**
- (a) Score the sweep with the framework's own ledger, per integration. This makes the count an integration-aware output and "one geometry" true for the count. It costs about a day of coding and could move M*.
- (b) **Minimum:** keep the model of [1], removing the √(f_sw) factor on the DC current and the integration-blind 1-kA BGA term, then rerun the 18-min sweep. The editor estimates that M* stays at 36 with a margin of about 5.5 W **[verify with R2]**.
- In either case, print P_route(M) as an equation.

**D3. Omitted converter losses.**
- (a) Add dead time and core loss to the baseline model and rerun every production case.
- (b) **Recommended for this submission:** keep them as a bound. Table V row; Z2-A marked conditional; the abstract and conclusion do not rest on Z2-A.

**D4. Primary loss metric.** Platform-inclusive (**recommended**) or package-internal.

**D5. Title.** Recommended or alternative (§1.1).

**D6. Five-tier co-design result** (VII-E). Include it (**recommended**; R10 adds the joint response) or move it to the supplement.

**D7. Showing design for a given thermal solution.**
- Run R11 and quote the minimum cooling each integration needs to stay feasible (one sentence in VII-B, figure in the supplement), or skip it.
- Recommended if time allows: it answers "generality" and makes "given a thermal solution" concrete.

**D8. Mechanical numerics.** Run R7 and drop the caveat (**recommended**), or keep the one-sentence caveat.

**D9. Ball-current definition.**
- Check the DC peak × k_rms (now 1.98 A), or the harmonic RMS per ball (2.2 A at 220 balls).
- Recommended: recompute both at the adopted counts (R5) and adopt the larger as the checked current. Z2's ring stays within 75 % up to 198 balls per rail.

**D10. Contributions.** Qualitative (**recommended**) or with numbers.

### 9.2 Runs before writing (pinback, ≥ 40 cores)

| Priority | Run | Purpose | Cost |
|---|---|---|---|
| P1 | R1 Five pending variant mesh ladders (already running) | Final verdict counts; confirms the joint ranking | running |
| P1 | R2 Count sweep with the corrected routing model (D2) | Defensible P_route(M); confirms M* | 18 min (b) / ~1 day (a) |
| P1 | R3 Inductor technology: sweep without the design-target part, then the coupled Z1/Z2 comparison under A and B with that design (or with a physically consistent variant of [39]) | Shows whether the conclusions depend on the inductor | 18 min + ~0.5–1 day |
| P1 | R4 All-site Δε_in on the 90-mm board with its own electrothermal field, Z1 and Z2, A and B | Turns the board condition on the headline joint finding into a result | hours |
| P1 | R5 k_rms and harmonic per-ball RMS at 170 (Z1) and 166 (Z2) balls | One consistent ball current and count | < 1 h |
| P1 | R6 Circuit simulation of the N3K3 cell at 805 kHz, 27.8 A, with EPC models | Validation at the design point | hours |
| P2 | R7 Direct solver (or tightened iterative tolerance) + through-thickness mesh level on the six cases | Removes the mechanical-numerics caveat | hours |
| P2 | R8 Critical joints driven from the three in-plane mesh levels (54 local solves) | Complete U95 of Δε_in | < 1 h |
| P2 | R9 Sweep scored at operating temperature | Selection is not an artifact of 25 °C | 18 min |
| P2 | R10 Δε_in of five-tier Z1 under B | Completes the Pareto statement | < 1 h |
| P2 | R11 Cooling-requirement sweep (top-plate h_eff or TIM resistance), Z1–Z3, A and B, electrothermal only | Design for a given thermal solution; generality | ~3 h |
| P2 | R12 Count sweep at J_t = 2.5 and 5 A/mm² | Sensitivity of M* to J_t (supplement + one sentence) | 40 min |
| P3 | R13 Explicit-part converter cell against its homogenized card | Fidelity of the tier cards (peak, T_jn) | hours |
| P3 | R14 Interface-band average of Δε_in at the critical joints | Ordering under Darveaux-style averaging | < 1 h |
| P3 | R15 Bonding gap with a 150-°C cure reference | Range for the bonding requirement | < 1 h |

**Order:** R2 and R3 first. If either moves the design point, every downstream result must be regenerated, so no writing starts before they return. R1, R4 and R5 can run in parallel.

### 9.3 Risks

- **K1, the inductor (critical).** A power-electronics reviewer can reject the paper on ½LI². Mitigation: D1(b) with R3. If the rankings survive, say so in one sentence; if they do not, the paper's comparative claims must be re-scoped.
- **K2, the design point moves.** If R2 (option a) or R3 changes M* or the design, every production case, mesh ladder, joint search and robustness variant must be rerun: about 1–2 days of compute plus regeneration of macros and figures (with the etm Python 3.12 interpreter only).
- **K3, page overrun.** Float heights are estimates; the reserve is 0.2 page (0.5 if biographies are not printed). Cut order: Fig. 2(b); then Fig. 5 folded into Fig. 4; then the Table II package block; then references down to 33.
- **K4, the pending variants.** If any of them reverses the Z1/Z2 joint ranking, the joint inversion becomes conditional, and the abstract's last clause switches to the critical-joint statement (§1.2).
- **K5, novelty overlap with the senior author's own [1] and [21].** Mitigation: Table I with concessions, an explicit "adopted from" sentence, and contributions written as capabilities absent from [1], [21] and the commercial tools.
- **K6, Z2 under cooling A.** It is conditional on decoupling, the interface and the omitted losses. Never headline it; the cooling-B and Z3 verdicts carry the abstract.
- **K7, supplement dependence.** Check before submission that every claim in the abstract, the contributions and the conclusion has its evidence in the 10 pages.
- **K8, honesty of the count narrative.** If R2 confirms that the conversion term places M*, the text must say so. The "balance" is shown in Fig. 3(a), and at the integration level in Fig. 3(b). Overclaiming here is easy to catch from Table S2.
- **K9, schedule.** P1 runs take about one day if the design point holds. The rewrite (one writer per section group, then an editorial pass for redundancy and process language) follows author approval of this blueprint.
