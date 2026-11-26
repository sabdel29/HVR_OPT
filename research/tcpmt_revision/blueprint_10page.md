# Blueprint for the 10-page TCPMT paper (final, after two audits)

Scope: a full restructure of the 23-page manuscript (`manuscript_v2/`) into **10 pages in total** in IEEE two-column TCPMT format, counting references and biographies. This version revises `blueprint_10page_draft.md` (left unchanged) using Audit 1 (content and claims) and Audit 2 (page calibration). Where an audit and the draft disagreed, the audit's verified finding wins unless it contradicts an explicit author decision; those cases are open decisions (§9.1).

Numbers are from `macros_front.tex`, `macros_methods.tex`, `macros_results.tex`, `results_macros.tex` and supplement Table S2, rechecked for this version. Marks:
- **[Rn]**: the number or claim depends on run Rn (§9.2).
- **[update]**: depends on the five robustness variants now being rerun (board_h1, board_h0_h1grid, board_t2p4, f2_void, f1_sidewall_filled).
- **[verify]**: derived by the editor, not yet a macro.

If decisions D1–D3 trigger a rerun of the production chain, every number in §4 changes and must be regenerated before writing (risk K2).

---

## 0. Thesis, and what changed after the audits

**Thesis the reader must leave with.**
- Where a near-point-of-load regulator is integrated in a 2.5-D/3-D package decides three things at once: its routing loss, the path its heat takes and the strain in the joints that carry it.
- ETM-DVPD synthesizes the regulator for a system target and carries it, on one geometry and under a given thermal solution, to the critical solder joint, then filters out what cannot be built or operated.
- For a 1-kW processor, each added level of physics changes which integration wins. The paper shows this progression on page 2 (Table I) and explains it in Secs. V–VI.

**What changed from the draft, and why.**

| # | Audit finding | Resolution in this blueprint |
|---|---|---|
| 1 | Inductor: one sentence of R3 cannot answer ½LI² = 66 µJ in 0.5 mm³. All headline numbers rest on this part, which is selected at all 18 feasible counts. | D1 reopened (§9.1). R3 now has two variants and runs first. Its result is shown as a curve in Fig. 3(a) and as rows in Table IV. If the verdicts hold, re-base on the physically consistent design. Table II states the inductor's basis and its L/DCR gap to [39]. |
| 2 | "91.1 % vs 90.9 % [38]" is not a validation. The model omits about 25 W nominal (21 W of it dead time) and overstates C_oss (13.2 vs 7.4 W). | New run R16: the loss model on [38]'s own parts and operating point, against its measurement. R6 (circuit check at the design point) stays. Dead time and core loss go into the model if any full rerun happens (D3). Otherwise state that the nominal estimate keeps M* = 36 by 3.7 W. |
| 3 | The count is not sharp. M = 35 trails by 2.3 W on the fine grid; the upper omitted-loss estimate moves M* to 50; only square neighbours were carried through the chain; the square-grid restriction is never stated. | V-A presents the count as a jagged landscape with a near-optimal set. It states the square-grid rule and that the chain confirms M* only against the buildable neighbours 25 and 49. R21 (rectangular grids) is optional within D2(a). |
| 4 | Two routing models: the sweep books 5.2 W at M = 36, the coupled Z1 ledger 11.9 W. | D2(a) recommended: score the sweep with the framework's own ledger, per integration. P_route(M) is printed as Eq. (3). |
| 5 | Converter-tier cards are unverified. Halving the GaN-tier conductivity adds 11.5 K, which equals the 11.4-K binding margin. Temperature-independent k makes this worse. | R13 moved to P1 (Stage A) and extended to k(T) of Si and Cu. Table III lists the cards as "bounded" until R13 returns. |
| 6 | The 30-mm coupon equals the substrate size, so Z2's board is a 3.3-mm frame around a 23.36-mm opening. | D5: adopt the 90-mm board, with its own electrothermal field, for the mechanics if R4 confirms the joint ordering. Board size, opening and mounting go into Table II. |
| 7 | About 86 % of the 48-V loss is AC (1 − 1/k_rms²). Harmonics reach about 16 f_sw, where δ_Cu ≈ 18 µm. A fundamental-only skin-depth sentence will not pass, and this term decides the single-sided Z2/Z1 verdict. | New run R17: harmonic-weighted R_ac/R_dc per conductor class. III-C states the factor, not a skin depth at f_sw. |
| 8 | The 2-A ball rule comes from one source and is applied at up to 113 °C; at 1.5 A nothing is feasible. | IV-A states the current-density basis (about 1.6 × 10³ A/cm² over the ball section **[verify at the pad opening]**) and that no thermal derating is applied. VI-D keeps the 1.5-A condition. |
| 9 | Fairness: Z2/Z3 reuse Z1's decoupling, substrate and board copper; nothing is optimized per integration. | II-A says the shared design record isolates the integration. VI-D adds per-integration co-design under Z2's 3.46-mm depth (R10, redefined) and the copper Z3 would need (R20). |
| 10 | Claims not supported: the heading "Conversion Meets Routing at 36 Cells"; "every stage is verified"; the joint inversion in the abstract before R4/R1; "requirements no single domain reveals"; the bonding flatness result; "infeasible" for validity limits; platform loss as the primary metric; "Pareto pair". | Each is fixed: V-A is retitled; the wording becomes "each solver stage is verified" plus a list of what is bounded; the abstract's joint clause is conditional; the "no single domain" grouping is dropped; bonding goes to limitations unless R15 (D6); ratings and validity limits are reported separately; the primary metric is package-internal loss with U95 and the platform is expressed as R* (D4); "Pareto" is used only with R10. |
| 11 | Needed in the paper but planned for the supplement: k, E, CTE and Tg; board, opening and mounting; h_eff and TIM; library composition and the inductor basis. | All are rows of Table II. |
| 12 | Redundancy: Table V's deciding-number column; the answer per cooling stated four times; Fig. 5 duplicating Table IV; nine "single-domain" openers; report-style counts. | Table V merged into Table I without that column. The answer is stated once with numbers (VI-A) and once without (VII). Fig. 5(b) becomes panel (g) of Fig. 4 and Fig. 5(a) is dropped. One lead paragraph opens Sec. VI. Cut from the paper: 124/4/5/20 verdict counts, "23,211 of 40,555 pairs", the 788-kHz grid, the seven-tier result, signal-site counts, the neighbours' joint percentages. |
| 13 | Front-load the ladder; show what the optimizer buys; Fig. 1 overloaded; too many symbols; the abstract needs numbers; R9 and R11 to P1. | Table I (ladder × prior art) is cited in Sec. I. Fig. 3(a) gets the fixed-topology curve (R18), and the prior-art design is optionally carried through the chain (R19, D8). Fig. 1 loses its badges, stop criteria and inset. Names in text, labels in floats; β_D, K_A and **B** leave the text. The abstract carries −10.6 W, −32 K, 46 vs 30 mV and 2.0–3.6×. R9 runs in Stage A, R11 in Stage B. |
| 14 | Page budget: real reserve of only 0.1–0.3 page; floats under-sized by about 0.3 page; words per page too generous; float crowding in Secs. III and VII. | Calibrated budget (§7): floats cut from a realistic 3.2 to 2.50 pages by merging, the text set at 5,200 words, a 0.51-page reserve with biographies, and a cut order. Floats are distributed so no section carries more float than text. |
| 15 | References: Avula et al., TCPMT 2022, belongs in the core list. | Added (a new bib entry; read the full text first). |

Unchanged draft decisions that survived both audits:
- methods follow the data flow of Fig. 1, and results are titled by finding;
- verification is a compact main-text table;
- references are kept to about 38;
- contributions are qualitative;
- data are available on request (author decision of 2026-11-24);
- the +29 % coupling penalty is reported on the same basis as [21] and kept out of the abstract.

---

## 1. Title, abstract, contributions and naming

### 1.1 Title (D10)
- **Recommended:** *From System Target to Solder Joint: Coupled Electrothermal–Mechanical Design of 2.5-D/3-D Package-Integrated Power Delivery* (15 words). It states the scope, the physics, that the framework designs (not only simulates) and the system class, in the author's own terms. It also carries forward "From Device to Solder Joint".
- **Alternative:** *ETM-DVPD: A Coupled Electrothermal–Mechanical Simulator for Near-Point-of-Load Power Delivery in High-Performance Computing* (15 words). It puts the tool's name in the title.
- Index terms: 2.5-D/3-D integration, distributed vertical power delivery, electrothermal–mechanical co-design, hybrid switched-capacitor converter, integrated voltage regulator, near-point-of-load regulation, solder joint reliability, thermal management.

### 1.2 Abstract (≤ 200 words; numbers update with any rerun)
> Kilowatt AI and data-center processors draw a kiloampere below 1 V, pulling voltage regulators into 2.5-D/3-D packages, near the point of load. The integration sets routing loss, heat path and joint strain together, yet existing tools fix the converter or solve one physics. We present ETM-DVPD, a coupled electrothermal–mechanical framework that carries a regulator from a system target to the critical solder joint on one package geometry. Its electrical solver sweeps the regulator count and, at each count, synthesizes a hybrid switched-capacitor topology with its GaN devices, passives and switching frequency from a part library, minimizing conversion plus routing loss. Its package solvers check buildability, iterate loss and temperature to a fixed point under a given thermal solution, solve the mounted package thermoelastically at every interconnect site and locate the critical joint with a viscoplastic submodel. For a 1-kW, 48-to-1-V processor it selects 36 cells. Under single-sided cooling the embedded and package-backside regulators tie electrically, and only the embedded one survives a non-conforming plate interface. Double-sided cooling makes the package-backside regulator best by 10.6 W and 32 K. The board-backside regulator drops 46 mV against a 30-mV limit, and the flattest package strains its joints 2.0–3.6 times more.

- The last clause holds only if R4 and the five reruns keep the joint ordering **[R4] [update]**. Otherwise it becomes: "… and neither warpage nor the largest joint displacement locates the critical joint."
- The abstract carries only findings that the full flow produces. The three coupled ones come first: the thermal solution flips the integration, the interface feedback removes a candidate, and the joints do not follow the warpage. The 1-V drop is an electrical finding that the flow catches, and it is not described as coupled.

### 1.3 Contributions (three, qualitative, ≤ 110 words; use as written)
1. ETM-DVPD, to our knowledge the first simulator that carries a synthesized near-point-of-load regulator from discrete parts to the critical solder joint of the mounted 2.5-D/3-D package, on one geometry, with classified couplings and stage-wise numerical verification (Secs. II–IV).
2. Target-driven synthesis: a count sweep that re-synthesizes the hybrid regulator from a part library at every count, under part-level rules, and scores conversion plus routing loss on the package geometry (Secs. III, V).
3. Comparison through the full flow: integrations of one design compared under identical thermal solutions, with infeasible designs filtered out, an all-site critical-joint search, and every difference judged against its own numerical uncertainty (Secs. IV, VI).

### 1.4 Naming and wording rules (for every writer)

**Names in the text, labels only in floats.**
- Integrations: *embedded* (Z1), *package-backside* (Z2), *board-backside* (Z3). The label appears once, in parentheses, in II-A.
- Thermal solutions: *single-sided cooling* (one top cold plate, A) and *double-sided cooling* (top and bottom plates, B).

**Symbols allowed in the text:** M, M*, f_sw, k_rms, P_cell, P_route, R*, Δu, Δε_in, T_sj, U95. Keep K_A, **B** and β_D in Table II and the supplement only. Name the optimizer once: "the hybrid-regulator (HVR) optimizer" in III-A, then "the synthesis".

**Fixed terms:**
- *design record* = count, grid, topology, parts, f_sw, tier plan and order, decoupling plan;
- *routing loss* = I²R in every conductor from the converter's 48-V terminals or BGA pads to the die pads, intra-cell conductors included;
- *package-internal loss* = the loss the thermal model receives;
- *platform condition* = the feed resistance R* at which a backside integration loses its lead.

**Banned:**
- "production state", "reference" (meaning a case), "mode(s)", "screen" (say "sweep"), "escalated", "pending", "campaign", "ladder rung" (say "mesh level");
- "every stage is verified" (say "each solver stage is verified against a matched numerical reference");
- "validated", except for the comparison with [38]'s measurement;
- "global optimum", "closed loop", "huge library";
- "no single domain reveals", except for the three coupled findings;
- "Pareto", unless R10 is done;
- "infeasible" for a design that only leaves a model-validity range (say "outside the validity range of the on-resistance fit / solder laws").

**Discipline:**
- Each number appears once in the body (in a float or in the one sentence that interprets it), plus at most once in the abstract.
- At most one number per sentence where possible.
- A design rule is the closing sentence of its finding.
- The conclusion repeats no numbers.
- No process narration: no macros, regeneration, campaigns, revision history, or how the data were gathered.

---

## 2. Outline: 7 sections, 16 subsections, 5,200 words of text

Word caps are hard (±10 %). Bullets list content to cover; they are not prose to transcribe. The editor trims to the cap.

### I. Introduction — 580 words (Fig. 1 and Table I first cited here)
**Purpose:** show why a coupled simulator is needed, what prior art cannot do and what the paper adds, and preview the answer on page 2.

| ¶ | Content | Words |
|---|---|---|
| 1 | Problem: 1–2-kW AI/HPC packages at < 1 V draw about 1 kA, so 1 mΩ costs 1 kW; regulation moves into or under the package (near-POL, 2.5-D/3-D; DVPD). The three integrations [1], [8], [10] (Fig. 1). | 110 |
| 2 | Why coupling: the integration fixes which rail crosses each interconnect (routing), where the converter's heat flows (temperature → loss) and which CTE mismatch loads which joint. The count fixes cell area → admissible parts → tier heights → via depth. So an electrically optimal design can break a via rule, the ball current, the cooling, a part rating or the joints. Requirement: one model chain on one geometry, from system target to solder joint. | 120 |
| 3 | Prior art in three families, each closed by what it lacks: (i) DVPD design frameworks [1] and self-consistent electrothermal models [21], [24] (fixed design or one topology, lumped T_max, no board, no mechanics); (ii) ETM sign-off tools [12], [14] (given layout); (iii) power-module synthesis and ETM co-simulation [16], [19], [20] (fixed circuit, stand-alone module). Add placement studies [26], the multiphysics IVR review [Avula 2022] and the warpage review [Kim 2023]. | 130 |
| 4 | Gap, adoptions and concessions, one sentence each. Adopted from [1]: specification, embedded stack, BGA/TSV technology; from [35], [36]: the hybrid family and loss model. Conceded: droop and floorplan in [1], conjugate CFD in [21], life models in [12], [14]. | 60 |
| 5 | Preview: "Table I lists, for the 1-kW processor studied here, what each depth of analysis concludes and which prior art reaches that depth; the answer changes at almost every level." | 50 |
| 6 | Three contributions (§1.3) and a one-line roadmap. | 110 |

- **Supplement:** the regulator-demonstration list ([29]–[34]), the paragraph "Relative to its closest predecessors…", and the detailed capability table (S1, with a passage cited for every cell).

### II. The ETM-DVPD Framework — 460 words (Fig. 1)
**Key message:** one design record is carried from stage to stage on one geometry. Couplings are declared, and the count and the integration are outputs of the flow.

**A. Three Integrations of One Regulator (130)** *(moved here from IV-A, per Audit 2)*
- All three share the cells and stack of the design record, a 300-µm Si substrate with 30/60-µm TSVs, a 0.8-mm SAC305 BGA (1,369 sites) and a 3.2-mm board. Only the placement differs.
- Embedded: converter between substrate and die; 48 V crosses the BGA and the TSVs.
- Package-backside: converter in a 23.36-mm board opening, joined by a 30-µm-pitch Cu-pillar attach; 48 V through a 528-site ball ring.
- Board-backside: converter on the board underside; 1 V crosses plated through-holes, the full BGA and the TSVs, then spreads laterally.
- Closing sentence: sharing one design record isolates the integration. Per-integration co-design is shown where it changes the answer (VI-D).

**B. One Geometry, Four Couplings (160)**
- One stack description feeds the ledger and both FE meshes. Each ledger term maps to an element set, and the deposited heat equals the ledger total.
- Coupling classes:
  - electrical ↔ thermal: two-way, fixed point;
  - thermal → mechanical: one-way;
  - mechanical → joint: one-way;
  - mechanical → thermal: optional, through the plate-interface gap;
  - mechanical → electrical: neglected, because α_Cu ΔT is more than 100× smaller than the resistivity TCR (one sentence).
- Scope, stated once: steady state; no transient droop; no life prediction.

**C. Designing and Comparing Through the Full Flow (170)**
- *Inputs:*
  - system target: P_load, V_out, V_in, die footprint and power map, J_t, ripple limits;
  - part library with ratings, outlines and loss data;
  - candidate integrations;
  - the thermal solution as boundary maps h(x,y), T_f(x,y) on each cooled face, or a coolant model that computes them;
  - part and package limits.
- *Outputs:* ranked feasible designs, with loss by conductor and component, temperatures, warpage, Δu at every interconnect site, Δε_in at the critical joint, verdicts, and the numerical U95 of each.
- *Procedure:*
  1. The sweep proposes M* and its design record.
  2. Each (integration, thermal solution) pair is built, checked, solved and filtered.
  3. Feasible designs are ranked by package-internal loss, with the platform condition, peak temperature and joint response beside it; a difference counts only if resolved.
  4. Neighbouring counts and alternative converters pass through the same chain.
  5. Inputs without a defensible single value are varied through the whole chain.
- One clause: the designer closes the outer loop.

- **Equations:** none.
- **Supplement:** the algorithm box (current Fig. 2) as pseudo-code; the long "one geometry" paragraph.

### III. Electrical Solver: Synthesizing the Regulator and Its Count — 920 words (Fig. 2, Table II)
**Key message:** at every count the regulator is re-synthesized from parts under part-level rules. Its conversion and routing losses are computed on the package geometry, and their sum picks the count.

**A. A Hybrid Family Searched Over a Part Library (200)** — cite Fig. 2 and Table II here.
- The (N,K) hybrid SC–buck family: N SC branches and K inductor branches, 2 ≤ K ≤ N, with 2N + 2K − 1 parts; D = N·V_out/V_in. The phase split and branch allocation are fixed by rule, a deliberate reduction of the search space (symbols in Table II only).
- The HVR optimizer enumerates every member within a part budget (15, rising to 30 as the cell area allows) and, for each, every combination of high-side device, low-side device, inductor, capacitor and f_sw that passes the rules. It returns the least-loss combination. State the number of combinations per member **[verify against `HVR_FULL_OPT_EPC_V2.py`]**.
- Library, stated honestly (one sentence each, details in Table II):
  - 90 GaN transistors (one vendor);
  - 10 capacitors with vendor bias data;
  - 11 package-integrated inductors from the literature, three of them design targets, including the selected one.
- f_sw: 50 log-spaced values from 43 kHz to 200 MHz, capped at each inductor's rated frequency.
- Claim the search space, not a "huge library".

**B. Conversion Loss Under Part-Level Rules (320)**
- **Eq. (1):** P_cell = Σ I²_rms R_on(T) (ripple included) + Σ I²_L,rms DCR(T) + Σ I²_C,rms ESR(f_sw, V_bias) + f_sw Σ_hard [E_oss(V_node) + E_overlap(R_g)] + f_sw Σ Q_g V_drv, with E_oss = Q_oss V/3 and Q_oss ∝ √V. Add the dead-time and core-loss terms if D3(a) is chosen.
- The rules appear as Table II rows, not prose:
  - voltage stress with derating (0.9 switches, 0.8 capacitors), with each switch's and capacitor's stress;
  - current ratings and I_sat (state whether I_sat is checked against average or peak current; the code checks average);
  - C_eff at bias, 105 °C and minus tolerance, keeping capacitor ripple ≤ 10 %;
  - ESR at f_sw;
  - C_oss charged at the actual node swings;
  - 2-D packing in the square cell of side (I_cell/J_t)^½ with a 50-µm keep-out, in at most four tiers (or under the integration's height limit, R10);
  - ripple limits, with 50 µF of output capacitance per cell assumed and not placed.
- Validation, one sentence each:
  - circuit simulation of four other members, worst error 7.1 % (not "94.4 % accuracy");
  - the design-point circuit check **[R6]**;
  - the model on [38]'s own parts and operating point against its measured efficiency **[R16]** (replaces the "91.1 vs 90.9 %" comparison).
- Omitted terms named once: dead time, core loss, AC winding loss, dielectric loss. They add 6.5–55 W (nominal 25 W, of which 21 W is dead time), and the √V C_oss law books 13.2 W against 7.4 W from the datasheet curves (conservative). Under D3(b), add one sentence: the nominal estimate keeps M* = 36 by 3.7 W, and the upper one moves it to 50 by 2.5 W.
- Selection temperature: 25 °C. **[R9]** gives the count scored at the operating temperature (one clause).

**C. Routing Loss and the Count Objective (400)**
- Rail-aware ledger: every conductor carries its rail and that rail's RMS current. Lateral runs are sheets. The board-backside lateral redistribution is P = κR_s(T)I², stated inline, with the shape factors in the supplement.
- **Eq. (2):** via-field provisioning and resistance (current Eq. 2), with ρ(T) at the converged temperature.
- k_rms is the RMS-to-average ratio of the 48-V current, defined here once; its values appear only in V-A.
- AC resistance: a harmonic-weighted factor R_ac/R_dc for each conductor class (balls, planes, RDLs, TSVs), computed from the cell's input-current spectrum up to 16 f_sw **[R17]**. Do not write a skin-depth-at-f_sw sentence.
- Contact and intermetallic resistance are bounded by the all-solder attach (one clause). Droop is outside the scope.
- **Eq. (3):** P_route(M) = Σ over the conductors c of the integration at count M of I²_rms,c R_c(T₀), and M* = argmin over M of [M · min over F(M) of P_cell(I_cell, A_cell) + P_route(M)], with I_cell = P_load/(V_out M) and A_cell = I_cell/J_t. Under D2(a) the same ledger serves the sweep and the coupled chain, evaluated per integration at 25 °C with the implemented decoupling. Under D2(b) it is [1]'s chain without the √f factor.
- Physics of each term, one sentence:
  - per-cell current falls as 1/M;
  - the shrinking cell excludes large parts and branches;
  - switching and gate loss grow with M f_sw;
  - packing ends the feasible range;
  - routing falls with M.
- State that the package builder realizes square grids of square cells (or r × c grids if R21 is done).
- **Eq. (4):** P(R) = P_int + (k_rms I)² R with V_in I = P_load + P(R) (current Eq. 1). P_int is the package-internal loss. R* is the feed resistance at which a backside integration loses its lead, a specification for the feed. Pumping is added at the platform. One sentence on the two boundaries: Z1 is counted from its BGA pads, Z2 and Z3 from the converter terminals, which is why the platform condition is reported.

- **Supplement:**
  - the stacked-switch stress and C_oss node-swing derivations;
  - the median-R_g rule; the placement algorithm and the 0.48-mm² budget rule; the ESR-at-bias procedure;
  - Table S2 (selection at every count) and the fine f_sw grid;
  - the full part library with sources and measured/target flags (new table);
  - the R6/R16 validation detail; the AC-factor derivation (R17);
  - J_t sensitivity (R12); the thin-capacitor evidence.

### IV. Package Solvers: Buildability, Heat, Deformation and Joints — 1,120 words (Table III)
**Key message:** the same cells are placed in each integration, checked for buildability, solved to an electrothermal fixed point under the thermal solution and solved thermoelastically at every site. The critical joint is found by its own response. Every design is filtered against every limit, and each solver is verified against a matched reference.

**A. Physical Realizability (190)**
- Tier packing and the tier-order rule: via rule first, then routing loss, then heat path.
- Via rule: 120-µm laser microvias, aspect ratio ≤ 1, capture pads [46], [47]. Copper posts are sized to the land patterns at 100 A/mm².
- Assumption: die terminals on both faces; the single-face sensitivity keeps the same order and aspect ratio (one clause).
- Ball provisioning:
  - the smallest legal count with ≤ 2 A per power ball at the implemented waveform across the k_rms band, with ≤ 75 % of sites carrying power [44];
  - the checked current is defined once **[R5]**;
  - current-density basis and no thermal derating, one sentence (§0 row 8).
- Converter height against the depth the integration provides (package-backside: 3.46 mm, from the 3.2-mm board and balls less the attach).
- Not evaluated: placement within a tier, encapsulation, lamination warpage (one clause, repeated in VII).

**B. Electrothermal Fixed Point Under a Given Thermal Solution (330)**
- Steady conduction on the explicit stack, with orthotropic homogenized cards for TSVs, attaches, RDLs, balls, board vias and converter tiers with posts.
  - The converter-tier cards are bounded: the post bounds move the peak by 2.7–3.1 K, and halving the GaN-tier conductivity adds 11.5 K. They become "verified" only after **[R13]**, which also adds k(T) for Si and Cu.
- **Eq. (5):** ∇·(k∇T) + q‴(x;T) = 0, with −k∇T·n = h(x)[T − T_f(x)] on cooled faces, and R_j(T) = R_j,25[1 + α_j(T̄_j − 25 °C)].
- The thermal solution is the framework's interface. The demonstrated cold plate:
  - Si microchannels with a fin-efficiency model; Nu = 6.32 for three-wall H1 heating (a lower bound given the entry length);
  - coolant warming resolved along the flow and iterated with the solid;
  - four-zone manifold, 27 g/s, 65 kPa; within 0.3 % of conjugate CFD for the channel;
  - h_eff = 132 kW/m²K on the footprint, behind a 50-µm, 3-W/m·K TIM (60 kW/m²K) (values in Table II);
  - single-sided cooling = top plate; double-sided = an identical plate under the cell grid. A bottom plate alone is not an option (one clause).
- Assumptions, one line each: uniform 1-kW die (power map in VI-D); board size and 10-W/m²K natural convection beneath (Table II); manifold flow split taken as uniform, without CFD.
- Fixed point:
  - each ledger term is evaluated at the mean temperature of the element set that receives its heat;
  - R_on coefficient 6.0 × 10⁻³ K⁻¹, fitted over 25–125 °C, which is why 125 °C is a validity limit; Cu and DCR 3.93 × 10⁻³ K⁻¹;
  - C_oss, Q_g and ESR held at 25 °C;
  - stop at 0.25 K and 0.1 %, reached in 4–6 solves; contraction 0.03–0.22, so there is no runaway.
- One sentence on prior art: [21] updates the loss from the single maximum temperature.

**C. Thermomechanics and the Critical Solder Joint (320)**
- *Global model:*
  - linear thermoelastic on the same mesh; T_ref = 25 °C, so the solution is the power-off → operating excursion;
  - board and BGA meshed; rigid-body restraint only; board size and mounting in Table II (90-mm board if D5);
  - Δu = ‖u_t − u_b‖_xy at every site of every interconnect layer (inline).
- *Local joint:*
  - driven by the fitted displacement of both pad faces at T_sj (translation, stretch, shear, rotation; not Δu alone);
  - 3-s ramps, 300-s dwells, last of four cycles;
  - **Eq. (6):** Δε_in averaged over the core (the band excluded at the singular corners is a numerical device).
- *Three-law band:* no calibrated law exists for these joints; the production law creeps 13–73× faster than the measured data; all laws are extrapolated in stress. Every ranking is judged under all three.
- *No life law:* any life relation monotone in Δε_in keeps the ranking (one sentence).
- *Critical-joint search,* two sentences: a dominance bound with a 10–11 % margin over three screening features (deforming Δu, vertical displacement, T_sj); it closed in every case. Show why it is needed in Fig. 4(g), not with pair counts.
- *Interface feedback,* inline: h_loc = (h_eff⁻¹ + g/k_TIM)⁻¹ with g(x,y) from the solved warpage, bounded by a conforming TIM and a rigid plate.
- One clause: microbump and pillar layers are screened by their shear driver, not ranked, because the microbump driver peaks at a singular corner.

**D. Feasibility, Verification and Uncertainty (280)** *(V and IV-E merged here)*
- Limits, listed once, in two groups:
  - *ratings:* GaN T_jn ≤ 150 °C; capacitor and inductor tiers ≤ 125 °C; dielectric and encapsulant ≤ 150 °C; board ≤ 170 °C; die ≤ 105 °C; static 1-V drop ≤ 30 mV per rail (the larger of the supply-path and return-path drops at 1 kA); ball current and sites; a converged operating point;
  - *model validity:* R_on fit ≤ 125 °C; hottest joint within the solder laws' 125-°C range.
  - A design that fails a rating is not ranked. One that leaves a validity range is reported as outside the model, not as infeasible.
- Verification: Table III gives each check, its reference and the maximum error, and says what is bounded rather than verified. The production-mesh peak error, measured from above on meshes refined to 3.0 M elements, is 2.1 K, inside its bias plus U95 (2.3 K).
- Resolution rule, in words: a difference counts only if it exceeds its own bias-corrected 95 % numerical uncertainty, estimated on its own mesh levels (GCI). 19 of 20 compared differences are resolved. Why this matters: U95 of the single-sided package gap is 0.33 W, against 1.4 W for the two cases' own U95 summed.
- U95 is numerical. Model-form uncertainty is handled by carrying alternatives through the chain (VI-D).
- Cost: 0.4–0.6 h per coupled evaluation on a two-socket workstation; the 18-min sweep; local solves run in parallel; CalculiX 2.23 and MOOSE.

- **Supplement:**
  - the tier-order algorithm and current Fig. 6; card construction;
  - the h_eff equation and hydraulics; the Z3 sheet shape factors; the decoupling port model;
  - solder cards, surrogate refits and stress windows; search seeding, margin rule and closure statistics; local-model setup and checks;
  - the "establishes / does not establish" matrix (current Table III), the verification chart (current Fig. 7), GCI rules and the bias formula, per-case U95 (S18), the differences table (current Table IV), runtime and memory (S16).

### V. Synthesizing a Buildable Regulator for a 1-kW Processor — 700 words (Fig. 3(a); Table II)
**Key message:** the framework turns the target into a buildable design. The count is an output of the parts, buildability needs copper posts and interleaved clocks, and temperature, not the electrical sweep, sets the count's margin.

**A. A Jagged Count Landscape (420)** — the first citation of Fig. 3.
- 27 counts; 18 admit a four-tier member; nine different members are selected; none fits four tiers from 60 cells. Discrete parts make the landscape jagged: adjacent counts below 50 cells differ by up to 16 W when the member or switch pair changes. This is why the topology is re-synthesized at every count rather than sized continuously as in [1].
- Honest count statement (update with R2): the conversion term places the minimum at 36 cells (97.2 W); routing tilts the landscape against small counts (+6.8 W at 16 relative to 36); packing ends it at 56. Present a near-optimal set, not a sharp optimum: the non-square count 35 trails by 5.8 W, inside the model's error. Of the buildable square grids, 25 and 49 trail by 8.1 and 17.6 W and are carried through the chain in V-B. Under D2(a), add whether the count depends on the integration.
- What the optimizer buys:
  - the fixed-topology curve **[R18]**: "+X W at the selected count";
  - optionally, the fixed 64-cell DSCH of [1], [21] through the same chain **[R19]**: "Y W more / outside limits".
- Inductor dependence: the same inductor and capacitor are chosen at every count, so the topology, switches and f_sw carry the gains. The library-only or energy-consistent result **[R3]** goes on the Fig. 3(a) curve plus one sentence.
- The selected design record (N3K3, EPC2014C/EPC2055, 805 kHz, four tiers, 2.99 mm) is in Table II and is not repeated in prose.
- Buildable only with posts and interleaving (one paragraph):
  - no tier order meets the via rule (worst aspect ratio 8.3 against 1; the best of 548 regroupings is 5.7), so copper posts cross the 1-mm capacitor tier;
  - the part-to-tier assignment moves intra-cell routing from 5.35 to 13.2 W;
  - capacitance that fits in the stack resonates and raises k_rms (3.8 → 5.2); 12 interleaved phases with a ring outside the grid give 2.64, which sets 170 balls per rail at 1.98 A, while bare pulses would need 2.6 A per ball even at 220 **[R5]**;
  - closing rule: decouple an embedded regulator by interleaving, not inside the stack.

**B. Temperature Reprices the Design (280)**
- The coupled embedded design loses 29 % more than its 25-°C ledger (137.0 vs 106.1 W), on the same basis as [21]'s +15.8 %. One sentence reconciles with [21]'s 231 W: a fixed 64-cell DSCH at 3.6 MHz against a synthesized one.
- The buildable neighbours fall from 8.1 and 17.6 W behind in the sweep to 24.3 and 35.3 W behind once coupled.
  - Under single-sided cooling, 25 cells leave the validity ranges of the R_on fit and the solder laws, and 49 cells also exceed the capacitor class (a rating).
  - Under double-sided cooling, both pass but stay 23.7 and 34.5 W behind.
- Validity and capacitor limits bind before device ratings: margins 11.4 K (R_on fit), 12.1 K (solder range), 12.2 K (capacitor), 17.3 K (die), against 36.4 K to the GaN rating.
- Closing rule: the count is an electrical result, but its margin is thermal.

- **Supplement:** decoupling detail (85-pH loop, 29–650-pH band, 12 µF per cell, 16 × 0402 per cell); the neighbours' fields, warpage and joints; the per-tier temperatures; the five-tier, seven-tier and thin-capacitor sweeps.

### VI. Three Integrations Through the Full Flow — 1,060 words (Fig. 3(b), Fig. 4, Table IV)
**Lead paragraph (60):** the one place where the single-domain contrast is made, pointing to Table I. Every added physics or boundary reorders or removes a candidate, and no single domain or cooling returns the answer. Table IV holds every number of the six cases.

**A. The Thermal Solution Picks the Integration (380)**
- At a common temperature only routing differs: package-backside 2.8–3.9 W below embedded, board-backside 20.6–44.4 W above (25/100 °C).
- Single-sided cooling (Fig. 3(b)):
  - the package-backside converter removes 4.86 W of 48-V package path, but, cooled only through the attach and substrate, it runs 4.4 K hotter and returns 1.85 W, so its package lead is 2.2 W (resolved);
  - its feed makes the platform comparison a tie: R* = 0.6 mΩ lies below every physical feed evaluated (0.62–1.89 mΩ);
  - its package lead depends on the decoupling state;
  - the board-backside converter reaches 180.8 °C junctions and leaves the ranking.
- Interface feedback: a rigid plate on the warped die opens mean gaps of 12 µm (embedded) and 37 µm (package-backside). The embedded design stays within limits with a 0.5-K margin; the package-backside design reaches 178.7 °C. Only the embedded regulator survives every interface.
- Double-sided cooling:
  - the bottom plate takes 139 W from the package-backside converter (−16.6 W, −41 K): an electrical decision;
  - for the embedded design it takes only 9 W (−0.9 W) but flattens the die (17.5 → 5.2 µm): a mechanical decision;
  - the package-backside regulator leads at both boundaries (−17.9 W inside the package, −10.6 W at the platform, R* = 4.6 mΩ above the feeds) and by 32 K at the peak, with 3.6× lower joint strain.
- **[R11]**, one sentence: the minimum h_eff (or TIM resistance) each integration needs to stay within limits.
- Closing rule: choose the thermal solution with the integration.

**B. Board-Backside Regulation Fails on Its 1-V Path (140)**
- Under double-sided cooling it meets every rating (78.0 °C) but drops 46.2 mV against 30 mV: 16.1 mV in the land side, 8.9 mV in the board planes, 21.2 mV vertical. Lateral loss is 7.6 W, and its 1-V balls take 73 % of the sites.
- Passing would need **[R20]** X µm of land-side copper (or N board planes), so no cooling fixes it.
- Closing rule: size the 1-V lateral path before the cooling.
- Do not call this a coupled finding: it is the electrical check of the full flow, and [1] also computes IR drop.

**C. The Flattest Package Has the Most Strained Joints (280)** *(conditional title, §1.2; values in Table IV)*
- The embedded regulator has the flattest die and the smallest Δu, yet 2.0–3.6× the joint strain of the backside integrations, under both coolings and all three laws, every difference resolved.
- Mechanism:
  - its joints run hot (112.9 and 105.0 °C against ≤ 96.2 °C elsewhere);
  - they carry the membrane mismatch between the hot board (109 °C under the embedded design, against 83 °C under the package-backside one) and the silicon, while the stiff, nearly symmetric sandwich keeps the die flat;
  - in the backside integrations, membrane and bending terms cancel, and part of Δu is rigid rotation (1.50 and 2.40 µm);
  - the board-backside design has the largest Δu (3.74 µm) and the smallest strain under single-sided cooling.
- Inside the package-backside ring, the joint that moves most is not the critical one: an inner-ring site responds 80 % more (Fig. 4(g)).
- The board condition: the result on the 90-mm board **[R4, D5] [update]**.
- Closing rule: judge joints by their own response, from an all-site search.

**D. When the Answer Changes (200)**
- Co-design: the shallowest integration bounds the converter.
  - The five-tier converter saves 22.2 W in the embedded design but protrudes 273 µm below the package-backside board.
  - Synthesized under that 3.46-mm depth, the package-backside converter is **[R10]**.
  - Under double-sided cooling, the five-tier embedded design (113.9 W) loses less than the four-tier package-backside one (118.1 W). The package-backside one runs about 32 K cooler with **[R10]** lower joint strain, so the choice is a trade.
- Die power map: a core-heavy map pushes the embedded die to 108.6/108.1 °C under single/double-sided cooling, and the single-sided package-backside converter outside its validity ranges. Only the double-sided package-backside design meets every limit (die 97.4 °C).
- Conditions that reverse a verdict, one clause each:
  - the input-decoupling state (the single-sided package ranking);
  - the nominal omitted losses (the single-sided package-backside design leaves the R_on-fit and capacitor ranges) **[D3]**;
  - a 1.5-A ball rule (no integration is feasible);
  - a 3×-larger board with a 25-°C rim (the single-sided joint ranking) **[R4] [update]**.
- Unchanged by: the feed model, board films, mounting and clamp, the three-law band, post bounds, caloric resistance and the thin capacitor.

- **Supplement:**
  - current Fig. 9(a) (rail currents), Fig. 10 and Fig. 11, with the robustness map and verdict counts;
  - interconnect-layer local responses; mounting and clamp subcounts; card bounds; ball-rating detail; omitted losses (S23); die map;
  - the low-CTE and cure-referenced assembly cases;
  - the double-sided waterfall detail; the R11 map; the R20 copper curve.

### VII. Limitations and Conclusion — 360 words
**Limitations (160), one paragraph, no repeated numbers:**
- verified, not validated against a measured package; the converter model has one measured anchor **[R16]**;
- the omitted converter terms are bounded **[D3]**;
- the inductor is a design target **[D1]**;
- the solder laws are uncalibrated, so Δε_in is comparative and no life is predicted;
- the ball rule is an assumption;
- assembly warpage at reflow and bonding needs a cure reference and above-Tg cards (D6);
- steady state only, with no droop or transients;
- one specification: the mechanisms and rules generalize, the numbers do not.

**Conclusion (200), no numbers:**
- The answer for each thermal solution (§4.5).
- Three rules:
  1. filter by limits, then rank on the converged state under one thermal solution;
  2. choose the cooling together with the integration;
  3. find the critical joint by its own response.
- One line of outlook: transients and droop, a calibrated life law, measured validation.

---

## 3. Figures and tables (4 figures and 4 tables, down from 11 and 5)

| New | Content | Source | Size (page, incl. spacing) | First cited | Message |
|---|---|---|---|---|---|
| **Fig. 1** | (a)–(c) Schematic, not-to-scale half-sections of the three integrations: rails colored, rail current per layer, cold plates and TIM drawn as boundaries, package-internal boundary dashed, critical joint ringed, **copper posts drawn in the embedded section** (replaces Fig. 2(b)). (d) The flow: target + library → [count sweep × HVR optimizer] → design record → [stack builder + realizability] → [ledger ⇄ thermal fixed point] → [thermoelastic, all sites] → [critical-joint search] → [feasibility] → ranked designs, with outer loops over integrations, thermal solutions and alternatives. Short data labels on the arrows (q‴; T → R(T); T(x) → thermal strain; u + T_sj → joint; g(x,y) → TIM). **No badges, stop criteria or inset.** | Current Fig. 1 simplified; current Fig. 2 absorbed | double, 0.44 | I ¶1 | What the simulator is and how it couples |
| **Fig. 2** | The (N,K) family drawn at N = 3, K = 3, with the generic extension dashed; blocking voltages and branch currents of the selected cell. No timing trace. | Current Fig. 3(a), redrawn | single, 0.20 | III-A | The synthesized converter and its search space |
| **Fig. 3** | (a) Count sweep: conversion, routing and total against M, with the selected member at each count; square (buildable) grids filled, counts without a member crossed; the fixed-topology total **[R18]**, the library-only or energy-consistent total **[R3]** and, optionally, the prior-art design **[R19]**; M* starred. Under D2(a), routing per integration as thin lines. (b) Waterfalls of package-internal loss, package-backside − embedded and board-backside − embedded, under **both** coolings: routing removed, routing added, conversion change caused by temperature, net. | Current Fig. 4(a) redrawn with the losses split; current Fig. 9(b,c) extended to cooling B | single, 0.32 | V-A (a); VI-A (b) | Conversion against routing at both scales, count and integration |
| **Fig. 4** | Single-sided cooling: (a)–(c) temperature sections; (d)–(f) Δu over the ball field, with the largest-Δu and critical joints marked and Δε_in printed; (g) package-backside: Δε_in of every solved site against Δu, the largest-Δu and critical joints marked. **No warpage row** (warpage with ± U95 is in Table IV). | Current Fig. 8 minus a row, plus old Fig. 5(b) as (g), from `solder_critical_v2.json` | double, 0.35 | VI lead | A real coupled 3-D solution; the joints do not follow the displacement |
| **Table I** | **Depth-of-analysis ladder (front-loaded).** Rows add one level of physics or boundary. Columns: prior art reaching that depth; verdict under single-sided (A); verdict under double-sided (B). No deciding-number column. Three footnotes carry the concessions (droop and floorplan [1]; conjugate CFD [21]; life [14]). Rows in §4.3. | Merges the current Table I with the draft Table V | single, 0.22 | I ¶5 | What prior art can do, and what answer each depth returns |
| **Table II** | (1) Specification and search space; (2) synthesized design record, with rating against stress; inductor row "design target, basis [39]; L/DCR vs [39] stated"; (3) package, materials and cooling: substrate, BGA and the ball rule with its basis; board size, Z2 opening, mounting; k, E, CTE, Tg of Si, encapsulant, board, SAC305, Cu; h_eff, TIM; board film. **No Source column.** Rows in §4.6. | Current Table II trimmed, plus Table S3 and Table S5 essentials | single, 0.40 | III-A | Reproducible inputs and the synthesized design |
| **Table III** | Check · reference · max. error, 12 rows (§4.7), the last row listing what is bounded, not verified. | Current Table III + Fig. 7 merged | single, 0.17 | IV-D | Each solver stage is verified, and what is not is named |
| **Table IV** | The six cases (three integrations × two coolings), 13 rows (§4.4): package-internal loss ± U95; R*; peak ± U95; warpage ± U95; Δu ± U95; T_sj; Δε_in [band]; power balls per rail (% of sites); 1-V drop; ratings exceeded; validity exceeded; ranked; R3 block **[R3]**. Feed resistances and pumping in footnotes. | Current Table V trimmed; current Table IV absorbed as ± and * | double, 0.40 | VI lead | Every number of the comparison in one place |

**Totals:** figures 1.31 pages, tables 1.19 pages; 8 floats = **2.50 pages** (the draft's plan was a realistic 3.2).

**Float placement:**
- pages 1–2: Fig. 1, Table I (intro);
- Sec. III: Fig. 2, Table II (0.60 page against about 0.9 page of text);
- Sec. IV: Table III;
- Secs. V–VI: Fig. 3, Fig. 4, Table IV (1.07 pages against about 1.7 pages of text).
- Fig. 3 must not be cited before V-A. IEEE places no double-column float on page 1.

**Cut order if over budget:**
1. the Table IV R3 block moves into the text (−0.04);
2. Fig. 2 becomes the N3K3 cell only (−0.05);
3. Table I goes to 7 rows (merge the platform and 1-V rows into notes) (−0.04);
4. references go to 35 (−0.08);
5. Table III goes inline in IV-D (net −0.08).

---

## 4. Results plan

### 4.1 Numbers to quote, by subsection (current values; marks show what may change)

**V-A Count landscape** **[R2] [R3] [D3]**
- 27 counts (16–120); 18 admit a four-tier member; nine members; none from 60 cells.
- Conversion is lowest at 36 (97.25 W). Routing falls from 12.0 W (16) to 4.2 W (56); +6.8 W at 16 relative to 36.
- Total 102.4 W = 97.2 + 5.2 W at M* = 36. Runner-up 35 (non-square) at +5.8 W.
- Square grids: 16 → 141.4 W, 25 → 110.6 W, 49 → 120.0 W; 64 and 81 admit no member.
- Jaggedness: 28 → 108.4 W against 30 → 124.9 W (N5K5, EPC2057 pair).
- Design record (Table II): N3K3, D = 0.0625, 805 kHz, EPC2014C/EPC2055, four tiers, 2.99 mm.
- Same inductor (250 nH, 1.6 mΩ) and capacitor (GRM188, 1 µF) at every count.
- Posts: 24 orders; worst aspect ratio 8.3 against 1; best of 548 regroupings 5.7. Intra-cell routing 5.35 W (chosen) against 13.2 W (worst assignment).
- k_rms: single-cell pulse 3.79 (1/√D = 4.0); in-stack capacitors 5.2 (13 at the worst inductance); ring alone 3.91; interleaving alone 2.71; interleaving + ring 2.64 (2.62–2.66) **[R5]**.
- Balls: 170 per rail at 1.98 A (embedded); 166 at 1.94 A (package-backside ring); 500 at 2.0 A (board-backside, 73 % of sites). Bare pulses would need 2.6 A per ball at 220 per rail. **[R5]** must reconcile k_rms at 170 balls (2.42) and the harmonic worst ball (2.2 A RMS) before any ball number is quoted.
- Cut: the 788-kHz fine grid; the five- and seven-tier sweep optima (the five-tier design appears only in VI-D).

**V-B Temperature reprices** **[rerun if D1–D3]**
- 137.0 W coupled against 106.1 W at 25 °C (+29 %; [21]: +15.8 %).
- Neighbours (Z1):
  - sweep 8.1 (25, N4K2) and 17.6 W (49, N3K2) behind;
  - coupled, single-sided: 24.3 and 35.3 W behind (peaks 130.2 and 127.0 °C);
  - coupled, double-sided: 23.7 and 34.5 W behind.
- Single-sided status: 25 cells exceed the R_on-fit and solder-law ranges (validity); 49 cells also exceed the capacitor class (rating). Double-sided: both pass.
- Margins (embedded, single-sided): R_on fit 11.4 K, solder range 12.1 K, capacitor 12.2 K, die 17.3 K, inductor 18.4 K, GaN 36.4 K.
- Low-side devices take 74.3 of the 125.1 W of conversion (59 %); peak 113.0 °C, in the input-end tier (only if words allow).

**VI-A Thermal solution** **[R17] [D4] [R11]**
- Common temperature: package-backside −2.8 / −3.9 W, board-backside +20.6 / +44.4 W (25 / 100 °C).
- Single-sided waterfall: −4.86 (48-V package path) + 0.52 (TSVs) + 0.22 (attach) + 0.07 (intra-cell) + 1.85 (conversion, +4.4 K) = −2.2 W, resolved (U95 0.33 W).
- Board-backside − embedded: +43.1 W (11.5 W board vias and 1-V BGA, 8.27 W lateral, 24.3 W conversion at +66.6 K); junction 180.8 °C.
- Platform (single-sided): R* = 0.6 mΩ; feeds 0.62–1.89 mΩ, so embedded lower by 0.3–5.2 W **[verify 0.3 W at 0.62 mΩ]**. Electrically a tie.
- Ideal decoupling flips the package ranking (embedded lower by 2.3 W).
- Rigid plate:
  - embedded: gap 12 µm → 141.1 W, 123.7 °C, R_on margin 0.5 K;
  - package-backside: gap 37 µm → 152.3 W, 178.7 °C, die 143.2 °C → fails.
- Double-sided:
  - package-backside: −16.6 W and −41 K relative to single-sided, 139 W through the bottom plate;
  - embedded: −0.9 W (9 W through the bottom plate); warpage 17.5 → 5.2 µm; Δu 1.94 → 0.77 µm; Δε_in 6.81 → 5.60 (−18 %).
- Package-backside against embedded, double-sided: package −17.9 W (resolved); platform 128.6 against 139.3 W (−10.6 W; R* = 4.6 mΩ); peak 77.0 against 109.3 °C (−32 K); Δε_in 1.55 against 5.60 (3.6×).
- Rigid plate under double-sided cooling: +0.9 W (embedded), +1.7 W (package-backside); both feasible.

**VI-B Board-backside** **[R20]**
- Double-sided: 136.9 W, 78.0 °C, every rating met.
- 1-V drop 46.2 mV = 16.1 (land side) + 8.9 (board planes) + 21.2 (vertical), against 30 mV; loop 77.6 mV (footnote only).
- Lateral loss 4.8 + 2.8 = 7.6 W. Without it the drop would pass and the loss would fall to about 129 W, below the embedded 136.1 W; say "about" (it is a decomposition).
- 500 balls per rail (73 %). The loss against the embedded design is the one unresolved difference (+0.58 W against U95 0.62 W).
- Cut: the 369 remaining sites.

**VI-C Joints** **[R4] [update]**
- Δε_in (×10⁻³/cycle, production law; Table IV only):

  | | Embedded | Package-backside | Board-backside |
  |---|---|---|---|
  | Single-sided | 6.81 | 3.35 | 3.11 |
  | Double-sided | 5.60 | 1.55 | 2.13 |

  - Lowest law: 5.97/2.55/2.34 and 4.77/0.81/1.36. Ratio 2.0–3.6×, ordering kept under all three laws, all resolved.
- T_sj: 112.9 / 105.0 °C (embedded) against ≤ 96.2 °C.
- Deforming Δu at the critical joint: 1.97 / 1.61 µm against ≤ 1.36 µm.
- Rigid rotation: 1.50 µm (package-backside, single-sided), 2.40 µm (board-backside, single-sided).
- Board-backside, single-sided: largest Δu (3.74 µm), smallest Δε_in.
- Package-backside, single-sided: critical joint is an inner ring site, 79.7 % above the largest-Δu joint. Double-sided: the mirror corner (1.068×), because the streamwise coolant breaks the symmetry.
- Board means: 109 °C (embedded) against 83 °C (package-backside), single-sided.
- Condition: a 3× board with a 25-°C rim reverses embedded/package-backside under single-sided cooling; double-sided holds **[R4]**.
- Cut: "23,211 of 40,555 pairs".

**VI-D When the answer changes** **[R10] [D3]**
- Five-tier: −22.2 W in the embedded design (single-sided 114.8 W; double-sided 113.9 W, feasible, 108.9 °C). It protrudes 273 µm below the package-backside board, which the four-tier stack clears by 469 µm (depth 3.46 mm). In the package-backside design it would save 17.7 W (double-sided).
- **[R10]** the best package-backside converter under 3.46 mm, and five-tier Δε_in.
- Die map: embedded 108.6 (single-sided) and 108.1 °C (double-sided); package-backside single-sided 107.1 °C plus converter failures; package-backside double-sided 97.4 °C, all limits met; board-backside double-sided 96.8 °C but fails the drop.
- Nominal omitted losses (25 W, 21 W dead time): package-backside single-sided at 127.5 / 126.9 °C (R_on fit / capacitor); gaps shift ≤ 0.9 W (single-sided, toward embedded) and ≤ 3.9 W (double-sided, toward package-backside); the embedded design needs 174 balls per rail.
- 1.5-A rule: no integration feasible (embedded 1.73 A at 220 balls; package-backside needs 77 % of sites; board-backside 667 balls).
- 0.1× passive-tier conductivity removes the embedded design (219 °C): supplement only.
- Cut from the paper: verdict counts (153/124/4/5/20; joint 38/5); bonding gaps 147.6 / 61.5 / 12.0 µm against 8 / 50 µm and reflow 80 / 127 / 81 µm (D6).

### 4.2 The narrative spine (each step overturns the previous answer)
1. **Electrical intuition says move the regulator out of the package.** At a common temperature the package-backside regulator wins by routing alone, and the board-backside regulator (today's practice) loses but looks feasible.
2. **Temperature reprices the design.** Coupling adds 29 % to the loss and removes both buildable neighbours. Validity and capacitor limits bind long before the GaN rating.
3. **Under one plate, heat gives back what routing saved.** The package-backside converter, cooled only through its attach, returns part of its routing saving. Its feed makes the electrical comparison a tie, and a rigid plate on its warped die removes it. The board-backside converter cooks at 181 °C.
4. **The same bottom plate means different things.** It is an electrical decision for the package-backside regulator and a mechanical one for the embedded regulator, and it makes the package-backside regulator best in loss, temperature and joint strain.
5. **Today's board-backside layout fails on its 1-V path, not on cooling.** Lateral redistribution takes more than half of its 46-mV drop.
6. **The flattest die has the most strained joints.** Inside one package, the joint that moves most is not the one that strains most.
7. **The integration bounds the converter, and the die map bounds the cooling.** The better converter does not fit the package-backside depth. A realistic die map leaves only the double-sided package-backside design within every limit.

Unexpected for a packaging reader: 3, 4, 5, 6 and 7. They prove why the coupled flow matters, so the results lead with them.

### 4.3 Table I rows (ladder × prior art)

| Depth of analysis (each row adds to those above) | Prior art at this depth | Single-sided (A) | Double-sided (B) |
|---|---|---|---|
| Electrical, fixed converter, one temperature | [1]ᵃ, [26] | Z2 < Z1 ≪ Z3 | Z2 < Z1 ≪ Z3 |
| + Electrothermal fixed point under the cooling | [21]ᵇ, [12] | Z3 exceeds ratings; Z2 < Z1 in package | Z2 < Z1 |
| + Feed to the 48-V node (platform) | — | Z1 ≈ Z2: the feed decides | Z2 < Z1 |
| + Static 1-V drop with lateral redistribution | [1] | Z3 fails | Z3 fails |
| + Thermomechanics of the given layout | [12], [14]ᶜ, [20] | Z1 flattest | Z1 flattest |
| + All-site critical-joint search | this work | Z1 most strained **[R4]** | Z1 most strained |
| + Plate-interface feedback | this work | Z2 fails under a rigid plate | both pass |
| + Synthesis and realizability | this work ([1]: one topology, continuous sizing) | posts; Z2 depth bounds the converter | same |
| + Core-heavy die power map | this work | Z1, Z2 exceed limits | only Z2 passes |

- Footnotes:
  - ᵃ also droop and floorplan, not resolved here;
  - ᵇ conjugate CFD of one integration, loss updated from the maximum temperature;
  - ᶜ solder life; here comparative strain without a life law.
- One line: module tools [16], [19] synthesize layouts for a fixed circuit.
- **Verify** every prior-art cell against the full texts (Table S1 evidence).

### 4.4 Table IV rows
Columns: the six cases, A then B.
- *Performance:* package-internal loss ± U95 (* = unresolved); R* (mΩ); peak temperature ± U95.
- *Mechanics:* die warpage ± U95; Δu ± U95; T_sj; Δε_in [three-law band].
- *Interconnect:* power balls per rail (% of sites); static 1-V drop per rail.
- *Feasibility:* ratings exceeded; validity exceeded; ranked.
- *Converter alternative* **[R3]**: package-internal loss and verdict for Z1 and Z2 (Z3 "—").
- Footnotes: physical feed resistances and platform losses; pumping per plate; the decoupling state; the band definition.
- Removed (Audit 2): efficiency, GaN T_jn, die maximum, heat per plate, the conversion/routing split (Fig. 3(b) shows it).

### 4.5 The answer (conclusion, no numbers)
- **Single-sided cooling:** the embedded regulator is the only integration that stays within limits across plate interfaces. Electrically it ties with the package-backside regulator, the feed deciding. A core-heavy die map consumes its margins.
- **Double-sided cooling:** the package-backside regulator leads in loss, peak temperature and joint strain, and it is the only design that meets every limit under the core-heavy die map.
- **Board-backside:** fails under both until its 1-V lateral path is redesigned.

### 4.6 Table II rows (about 20)
- *Specification and search space:*
  - 1 kW at 1 V from 48 V; die 22.36 mm, uniform;
  - J_t = 3.5 A/mm²; ripple limits with 50 µF per cell assumed;
  - search space: members within 15–30 parts; 90 GaN, 10 capacitors, 11 integrated inductors (8 measured, 3 design targets **[verify]**); 50 f_sw, 43 kHz–200 MHz; M = 16–120;
  - derating 0.9 / 0.8; ≤ 4 tiers; 50-µm keep-out.
- *Design record:*
  - 36 cells (6 × 6), I_cell 27.8 A; N3K3 (phase split 2, balanced allocation), D = 0.0625, 805 kHz;
  - high-side and low-side devices with rating / stress and R_on;
  - inductor: 250 nH, 1.6 mΩ, I_sat 23 A / 11.6 A peak, 1 mm² × 0.5 mm, "design target; basis [39]" **[D1]**;
  - flying capacitors with C_eff at bias and 105 °C;
  - tier plan, 2.99 mm, posts;
  - 2.70 W per cell (2.00 conduction / 0.70 switching);
  - decoupling: 56 × 1206 ring, 12 phases.
- *Package, materials, cooling:*
  - Si 300 µm, 30 × 30 mm, TSVs 30/60 µm;
  - BGA 0.8 mm, 0.4-mm SAC305, 1,369 sites (ring 528), ≤ 2 A per power ball (basis);
  - board IT-968G, 3.2 mm, size **[D5]**, opening 23.36 mm, mounting free;
  - materials (k / E / CTE / Tg): Si 130 / cubic / 2.6 / –; encapsulant 0.7 / 8 / 30 / 150; board 65.9∥ 0.45⊥ / 30.2 / 14.7 / 170; SAC305 – / 45 − 0.12(T − 25) / 21.5 / –; Cu (from S3) **[verify the solder and Cu k values]**;
  - cold plate: h_eff 132 kW/m²K (`\CoolHeffUni`; **[verify its reference area]**), water 25 °C, 27 g/s, 65 kPa; TIM 50 µm, 3 W/m·K (60 kW/m²K); board film 10 W/m²K.

### 4.7 Table III rows
| # | Check | Reference | Max error |
|---|---|---|---|
| 1 | Cards (TSV, attach, RDL) | Explicit unit cells (AEDT) | 1.3 % (the RDL series rule was off by 12.5 % and is replaced) |
| 2 | Package networks | MOOSE | 0.13 % |
| 3 | Thermal unit cells | AEDT/MOOSE | 0.1 % of the rise |
| 4 | Full embedded package, identical mesh | MOOSE | 5 × 10⁻⁵ K |
| 5 | Production mesh vs 3.0 M elements | MOOSE | 2.1 K (inside 2.3 K) |
| 6 | Thermoelastic element | Closed form [58] and FE | 0.43 % and 0.01 % |
| 7 | Iterative vs direct solver | — | 2 % in Δu, 13 % in warpage **[R7]** |
| 8 | Cold plate | Conjugate CFD | 0.3 % ΔT, 0.7 % Δp |
| 9 | Local joint, L0–L3 | Nested meshes | 2.9 % |
| 10 | Loss model | Circuit simulation (four members) / N3K3 circuit **[R6]** / [38] measured **[R16]** | 7.1 % / [R6] / [R16] |
| 11 | Fixed point; energy | — | 0.25 K, 0.1 %; 10⁻⁷ |
| 12 | *Bounded, not verified:* converter-tier cards **[R13]**; board-backside via and attach cards; manifold flow split | — | — |

---

## 5. Reviewer-concern coverage

| # | Anticipated concern | Where the paper answers it | Needs |
|---|---|---|---|
| 1 | Inductor implausible (½LI²; L/DCR far beyond [39]); chosen at every count | Table II basis row; V-A sentence + Fig. 3(a) curve; Table IV R3 block; VII | D1, R3 |
| 2 | Routing model; is "conversion vs routing" real? | III-C Eqs. (2)–(3); Fig. 3(a) split; V-A honest statement; Fig. 3(b) integration scale | D2, R2 |
| 3 | Loss model not validated at the design point | III-B: worst 7.1 %; R6 circuit; R16 measured; C_oss conservative | R6, R16 |
| 4 | Omitted losses exceed several gaps | III-B bound and selection robustness; VI-D condition; VII | D3 |
| 5 | Count not sharp; square grids only | V-A near-optimal set; square-grid rule stated; neighbours through the chain | (R21) |
| 6 | Synthesis scored at 25 °C | III-B clause with the R9 result | R9 |
| 7 | Novelty against [1], [21] (shared authors) and commercial ETM tools | Table I with concessions; I ¶3–4; contributions; V-B 231 W reconciliation; optional prior-art design through the chain | R19 (D8) |
| 8 | Verified, not validated; converter cards unverified; k(T) ignored | IV-D wording + Table III bounded row; IV-B bounds; VII | R13 |
| 9 | Mechanical numerics (13 % solver term, 37 % through-thickness term) | Table III row 7; IV-D one clause | R7 |
| 10 | Coupon board equals the substrate; joint ranking depends on the rim | Table II board row; VI-C board result; VI-D condition | D5, R4 |
| 11 | AC resistance of the 48-V path (86 % AC; harmonics) | III-C harmonic factor | R17 |
| 12 | Ball rule from one source, at 113 °C; electromigration | IV-A basis sentence; VI-D 1.5-A condition | R5 |
| 13 | Fairness: shared decoupling, substrate and copper; different boundaries | II-A isolation sentence; R* platform condition (III-C, VI-A); VI-D height-constrained co-design; VI-B copper requirement | R10, R20 |
| 14 | Platform loss has no U95; feed is a free parameter | D4: package-internal loss with U95 primary; platform as R* | — |
| 15 | Assembly flatness from an isothermal, above-Tg, 25-°C-referenced model | Dropped to VII unless R15 | D6, R15 |
| 16 | "Infeasible" used for validity-limit failures | IV-D two groups; Table IV two rows | — |
| 17 | Solder model uncalibrated; core average excludes the interface band | IV-C band and reason; no life; VII | R14 (optional) |
| 18 | Steady state; no droop; C_out not placed | II-B scope; III-B C_out sentence; VII | — |
| 19 | Generality: one target, one package | VII; R11 design map; R12 J_t sensitivity (supplement + one clause) | R11, R12 |
| 20 | k_rms bookkeeping (4.0 / 3.79 / 3.78; 2.64 at 220 vs 2.42 at 170; harmonic 2.2 A) | k_rms defined once in III-C; one consistent set in V-A | R5 |
| 21 | Die terminals on both faces, but the parts are single-sided | IV-A assumption + sensitivity clause | — |
| 22 | "30 mV per rail" undefined | IV-D definition | — |
| 23 | Reproducibility | Table II (all inputs); IV-D solver versions and costs; data on request | — |

---

## 6. References and biographies

**Count:** 38 core references, 1.04 pages at 0.0274 page each (measured on the current PDF).

**Core, with current numbers:**
- *Motivation and integrations:* [1] Krishnakumar TCPMT 2026; [2] Ye TCPMT 2026; [3] Swaminathan TCPMT 2026; [8] Arm cut-out VR (package-backside); [10] LEGO-PoL (board-backside); Avula et al., TCPMT 12(1):131–146, 2022, doi 10.1109/TCPMT.2021.3124248 (**new bib entry; read the full text before citing**); Kim et al., TCPMT 2023 (`Kim2023Review25D`).
- *Tools and frameworks:* [12] RedHawk-SC ET; [14] Sherlock; [16] PowerSynth; [19] PowerSynth reliability; [20] SiC ETM co-simulation; [21] Choi TCPMT 2026; [24] Choi TCPMT 2025; [26] Xu TCPMT 2019.
- *Converter and parts:* [35] ECTC 2025; [36] EPEPS 2026; [37] DSCH; [38] DPMIH (the measured hardware of R16); [39] Rasheedi TCPMT 2026; [40] GRM188; [41] EPC2014C; [42] EPC2055; the source papers of any inductor named in Table II.
- *Package rules:* [44] Kuan (ball I_max); [45] 30-µm TCB; [46] chip embedding; [47] IPC-2226A; [62] JEDEC JEP95 (only if D6 keeps reflow).
- *Thermal:* [49] Shah & London; [50] Qu & Mudawar.
- *Solder:* [54] Schubert; [55] Xiao; [56] Yuan.
- *Solvers and uncertainty:* [57] MOOSE; [58] Timoshenko (named in Table III); [59] CalculiX; [60] Roache; [61] Celik.

**Optional, in this order:**
1. one solder electromigration source for the current-density basis (IV-A);
2. [30] MSC-PoL;
3. [9] Vicor.

**Supplement only:** [9], [13], [15], [17], [18], [22], [23], [25], [27], [28], [43], [48], [51], [52], [53].
**Drop:** [4], [5], [6], [7], [11], [29], [31], [32], [33], [34].

**Biographies (D9):**
- Three biographies of about 80 words each, with photos if the template asks: about 0.25 page.
- Choi et al. (TCPMT, July 2026, 9 pages) prints none, and the current manuscript has none. Confirm with the current TCPMT author instructions; if they are not printed, the 0.25 page becomes reserve.

---

## 7. Page budget (calibrated on the current PDF by Audit 2)

**Rates:**
- text pages hold 1,060–1,140 words with their headings, so 1,040 words per page including 23 headings and 6 display equations;
- floats as measured, including surrounding space (single-column h/1392 pt + 0.013 page; double-column h/696 pt + 0.027 page);
- references 0.0274 page each;
- front matter 0.48 page with a 200-word abstract.

| Item | Basis | Pages |
|---|---|---|
| Front matter | Title, byline, 200-word abstract, index terms, first-page footnotes | 0.48 |
| Text | 5,200 words: I 580, II 460, III 920, IV 1,120, V 700, VI 1,060, VII 360; 7 section and 16 subsection headings; 6 display equations | 5.00 |
| Figures | Fig. 1 0.44 + Fig. 2 0.20 + Fig. 3 0.32 + Fig. 4 0.35 | 1.31 |
| Tables | Table I 0.22 + II 0.40 + III 0.17 + IV 0.40 | 1.19 |
| Float placement | White space left by float placement (Audit 2: +0.1–0.3) | 0.20 |
| Data availability | 2 lines | 0.02 |
| References | 38 × 0.0274 | 1.04 |
| Biographies | 3 × ~80 words with photos | 0.25 |
| **Total** | | **9.49** |
| **Reserve** | 0.76 if biographies are not printed | **0.51** |

**Why this fits where the draft did not:**
- the merges below remove about 0.7 page of float relative to the draft's realistic 3.2 pages;
- the 1,000-words-per-page rate is replaced by the measured one;
- the reserve is real, not two cancelling errors.

**Merges, agreed before writing:**
- Table V into Table I;
- Fig. 5 into Fig. 4(g);
- Fig. 2(b) into Fig. 1;
- the Fig. 4 warpage row into Table IV;
- the Table V deciding-number column dropped;
- Table IV cut to 13 rows;
- the Table II Source column dropped;
- 21 → 16 subsections.

**Word allocation against the current text:**
- intro 1,014 → 580;
- framework 870 → 460;
- electrical 1,543 → 920;
- package solvers + verification 5,421 → 1,120;
- results (current VI–VIII, 4,829) → 1,760;
- discussion + conclusion 1,824 → 360.

Results get 34 % of the text, against 31 % in the draft.

**Control:**
- each writer receives the cap and the float list;
- the editor measures after the first full draft (compile, then count pages);
- if the total exceeds 9.75 pages, apply the cut order of §3 before trimming prose.

---

## 8. Supplement structure (grows from 21 pages; derivations, algorithms and secondary results only)

- **S-I Prior work.** Detailed capability table (current S1) with a passage cited for every cell, including PowerSynth and [20].
- **S-II Converter synthesis.**
  - Member enumeration and part budget; full loss equations; stacked-switch stress and C_oss node-swing derivations; gate-resistance rule; placement and tier packing.
  - **New:** full part library with sources and measured/target flags (11 inductors: L, DCR, I_sat, area, height, f_max; 10 capacitors with bias data).
  - Table S2 with the fine f_sw grid; the count-sweep routing model and its equations; R6 and R16 validation detail; J_t sensitivity (R12); fixed-topology sweeps (R18); the inductor alternatives (R3).
  - Five- and seven-tier sweeps; thin-capacitor evidence.
- **S-III Package construction and realizability.** Layer stacks; full material cards; tier-order search and regrouping (current Fig. 6); post sizing; via rules; single-face sensitivity; ball provisioning and the current-density basis.
- **S-IV Electrical ledger.**
  - Decoupling port model (in-stack capacitors, ring, interleaving, loop-inductance band) and the k_rms derivation (R5); the harmonic AC-resistance factors (R17).
  - Feed crossover R*; board-backside lateral redistribution (sheet equations, shape factors, grid check); the copper requirement (R20); rail currents (current Fig. 9(a)).
- **S-V Thermal model and cooling.** Tier cards and bounds, plus R13 with k(T); cold-plate model (current Eq. 4), manifold hydraulics and entry length; CFD check; heat balance; caloric-resistance variant; interface-gap feedback iterations; the cooling-requirement map (R11).
- **S-VI Mechanics and the solder joint.** Thermoelastic setup; interconnect-layer drivers; local model geometry and cycle; solder cards and law band, with sources, windows and refits; the critical-joint search (algorithm, margin, closure, pair statistics); local checks (mesh, cycles, dwell, ramp, band).
- **S-VII Verification and uncertainty.** Verification matrix (current Table III); verification chart with runtimes (current Fig. 7); mesh levels, GCI safety factors, bias formula; per-case U95; the differences table; solver and through-thickness terms (R7); meshes, runtimes, memory.
- **S-VIII Results detail.** Feasibility of every limit in every case; fields under double-sided cooling; neighbouring-count fields and joints; five-tier and thin-capacitor cases; the full comparison chart (current Fig. 10); the prior-art design record and results (R19).
- **S-IX Robustness and conditions.**
  - Variant list and robustness map (current Fig. 11) with the verdict counts, updated after the five reruns.
  - Board, mounting, clamp and encapsulant variants; omitted losses (S23); die power map; 1.5-A ball rule; assembly warpage at reflow and bonding (low-CTE and cure-referenced cases; R15 if run).

**Rule:** no claim in the abstract, the contributions or the conclusion may rest only on the supplement. Each keeps its decisive number in Tables I–IV or Figs. 3–4 (check K7 before submission).

---

## 9. Decisions, runs and risks

### 9.1 Open decisions for the first author

**D1. Inductor (gating; this reopens the author decision of 2026-11-18).**
- *What a reviewer will compute:*
  - ½LI_sat² = 66 µJ in 0.5 mm³. A metal-composite core (μr ≈ 15, B_sat ≈ 1.25 T) stores at most about 41 kJ/m³, so even the 11.6-A operating peak (17 µJ) needs about 0.4 mm³ of core.
  - The cited array [39] gives 50 nH, 8.2 mΩ and 2 A per 0.2-mm² segment **[verify against [39]]**. Any series-parallel combination keeps L/DCR ≈ 6 nH/mΩ, against 156 nH/mΩ for the target part, a 25× gap.
- *The library:* the 11 inductors are all package-integrated parts from the literature. Three are UIC entries whose values are design targets rather than the measurements of their sources, including the selected part **[verify against the source notes in `HVR_FULL_OPT_EPC_V2.py`]**. Of the measured ones, only two carry the 9.3-A branch current, and one of those (13 mm²) does not fit the 7.94-mm² cell. The remaining 6-nH part would force tens of MHz. **R3 may therefore find no viable library-only design at J_t = 3.5 A/mm²** (risk K10).
- *Options:*
  - (a) Keep the target part, state its basis and L/DCR gap in Table II, and show its dependence: the R3 curve in Fig. 3(a) and the R3 block in Table IV. Claims are scoped to a target inductor technology. This honours the prior decision, but reviewer risk stays high.
  - (b) **Recommended if R3 keeps the verdicts:** re-base the paper on the physically consistent design (R3b) and keep the target part as a technology sensitivity. This needs a full rerun (K2), best bundled with D2 and D3.
  - (c) Keep everything as is, with no R3 (the prior decision). The highest rejection risk.

**D2. Routing model of the count sweep (gating).**
- (a) **Recommended:** score the sweep with the framework's own ledger, per integration, at 25 °C with the implemented decoupling (about one day of coding). This makes "one geometry" true for the count and the conversion–routing balance real, and the count may become integration-dependent, a strong result. Non-square counts need R21 (r × c grids of square cells) or are left to the electrical sweep.
- (b) Minimum: [1]'s model without the √f_sw factor and with an integration-aware BGA term, rerun in 18 min. Two routing numbers then remain in print (5.2 vs 11.9 W), and a reviewer will ask why.

**D3. Omitted converter losses.**
- (a) **Recommended if any full rerun happens:** put dead time and core loss in the model, in both the sweep and the chain.
- (b) Otherwise keep them as a bound, mark the single-sided package-backside result conditional, and state the selection robustness (M* kept by 3.7 W nominal).

**D4. Primary ranking metric (reverses the draft's recommendation).** **Recommended:** package-internal loss with U95, the platform expressed as the feed limit R*. Platform loss has no U95, and its feed resistance is a free parameter; at 0.62 mΩ the single-sided gap is a few tenths of a watt.

**D5. Board for the mechanics.** **Recommended:** if R4 keeps the joint ordering on the 90-mm board with its own electrothermal field, make it the production board for all mechanical results. Otherwise keep the coupon and state the rim condition with the claim.

**D6. Assembly flatness.**
- (a) Run R15 (150-°C cure reference, above-Tg encapsulant cards) and report one sentence.
- (b) **Recommended:** drop the bonding and reflow results from the main text and state the need in VII; the numbers go to the supplement as illustrative.

**D7. Table I.** **Recommended:** merge the capability table with the verdict ladder and front-load it in Sec. I. Alternative: keep two tables (+0.15 page; the reserve allows it).

**D8. Prior-art design through the full chain (R19).** Carry the fixed 64-cell DSCH of [1], [21] (2 A/mm² over the 500-mm² die) through the same package and cooling. This is the most direct proof of what synthesis adds over [1] and [21]. **Recommended** if the design parameters of [1] are at hand (about 0.5–1 day).

**D9. Biographies:** confirm whether TCPMT prints them (budgeted at 0.25 page).

**D10. Title:** recommended or alternative (§1.1).

Settled in this blueprint (no answer needed):
- ratings and validity limits reported separately (no rerun; extending the R_on fit to 150 °C is an optional run);
- names in text, labels in floats;
- three qualitative contributions;
- data on request.

### 9.2 Runs (pinback, ≥ 40 cores; the califone queue for long ladders)

**Stage A — cheap checks that inform the decisions (hours; no model change; start now, in parallel with R1):**

| Run | Purpose | Cost |
|---|---|---|
| R3 Inductor alternatives: (a) measured-library-only sweep; (b) energy-consistent 1-mm² target derived from [39]; then coupled Z1/Z2 under A and B for the resulting design | Decides D1; Fig. 3(a) curve, Table IV block | 2 × 18 min + ~0.5 day |
| R5 k_rms and harmonic per-ball RMS at 170 / 166 balls; adopt one checked current | One consistent ball current and count | < 1 h |
| R6 Circuit simulation of the N3K3 cell at 805 kHz, 27.8 A, with EPC models | Design-point loss check | hours |
| R9 Sweep scored at the operating temperature | The selection is not an artifact of 25 °C | 18 min |
| R12 Sweep at J_t = 2.5 and 5 A/mm² | Sensitivity of M* (and of R3) to J_t | 40 min |
| R13 Explicit-part unit cells against each converter-tier card, plus k(T) of Si and Cu | Card fidelity; the 11-K margin | hours |
| R16 Loss model on [38]'s parts and operating point against its measured efficiency | One measured anchor for the converter model | hours |
| R17 Harmonic R_ac/R_dc for balls, planes, RDLs and TSVs from the input-current spectrum | Closes the AC-loss question on the term that decides the single-sided verdict | hours |
| R18 Fixed-topology sweeps (e.g., N3K3 and N2K2 held fixed) | What the topology search buys (Fig. 3(a)) | 2 × 18 min |
| R20 Board-backside copper needed for 30 mV (analytic, shape factors) | Turns the 1-V failure into a requirement | minutes |
| R1 Five pending variant mesh ladders (running) | Joint ordering under the board and encapsulant variants | running |

**Stage B — after the decisions: model freeze, then one full rerun (about 1–2 days on ≥ 40 cores):**

| Run | Purpose |
|---|---|
| R2 Ledger-scored count sweep per integration (D2a), with R21 if chosen | Defensible P_route(M); M* per integration |
| Production rerun if D1(b), D3(a), R17 or R13 changes the model: six cases, mesh ladders, joint searches, neighbours, R1 redone on the new design | Every number of Secs. V–VI and Table IV |
| R4 All-site Δε_in on the 90-mm board with its own electrothermal field, Z1/Z2 × A/B (all six cases if D5 adopts it) | Joint claim and production board |
| R7 Direct solver (or tighter tolerance) + a through-thickness mesh level on the six cases | Removes the mechanical-numerics caveat |
| R8 Critical joints driven from the three in-plane mesh levels | Complete U95 of Δε_in |
| R10 Height-constrained synthesis under Z2's 3.46-mm depth (and unconstrained for Z1), through the chain with joints | Fair co-design (VI-D); a "Pareto" claim only if it holds |
| R11 Cooling-requirement map (top-plate h_eff and TIM resistance), Z1–Z3, A and B, electrothermal | "Given a thermal solution" as a design map |
| R19 Prior-art DSCH design through the chain (D8) | Novelty over [1], [21] |

**Stage C — optional:** R14 (interface-band averaging of Δε_in); R15 (assembly with cure reference, only if D6(a)); R_on fit extended to 150 °C.

**Order and gating:**
- Stage A returns within about a day.
- D1–D3 are then decided together, and the model is frozen once, so the production chain is rerun at most once.
- Writing of Secs. I–IV can start at the model freeze, since they depend on the model choices, not on the results.
- Secs. V–VI and the abstract wait for Stage B.
- Macros and figures are regenerated with the etm Python 3.12 interpreter only.

### 9.3 Risks

- **K1, inductor (critical).** A power-electronics reviewer can reject the paper on ½LI² and L/DCR. Mitigation: D1 with R3. If the verdicts survive, re-base (D1b); if not, scope the claims and present the dependence as a finding (inductor technology sets feasibility at this current density).
- **K2, the design point moves.** D1(b), D2(a), D3(a), R17 or R13 can change M* or the design. Then every production case, ladder, joint search and variant reruns: about 1–2 days of compute plus regeneration. Mitigation: one model freeze, one rerun.
- **K3, page overrun.** The reserve is 0.51 page (0.76 without biographies), with a pre-agreed cut order (§3). Writers over their caps are the main threat; the editor enforces caps per subsection.
- **K4, the joint claim.** If R4 or a pending variant reverses the embedded/package-backside joint ordering under single-sided cooling, VI-C retitles to the critical-joint statement and the abstract's last clause switches (§1.2).
- **K5, overlap with the senior author's [1] and [21].** Mitigation: Table I with concessions, an explicit "adopted from" sentence, contributions written as capabilities absent from [1], [21] and the commercial tools, and R19 if possible.
- **K6, the single-sided package-backside result.** It is conditional on decoupling, interface and omitted losses. Never headline it; the double-sided and board-backside results and the interface feedback carry the abstract.
- **K7, supplement dependence.** Check before submission that every abstract, contribution and conclusion claim has its evidence in the 10 pages.
- **K8, honesty of the count narrative.** If R2 confirms that conversion places M*, say so. The conversion–routing balance is shown at both scales in Fig. 3, and the integration scale is where routing decides.
- **K9, schedule.** Stage A about 1 day; Stage B 1–2 days; then writing (one writer per section group), an editorial pass for redundancy and process language, a page check and a proofread.
- **K10, no viable library-only design.** If R3(a) finds none at 3.5 A/mm², report that as the result (it motivates the target technology) and rely on R3(b) and R12 for the dependence.
- **K11, the margin is consumed.** If R17 (AC loss), R13 (k(T)) or D3(a) uses up the embedded design's 11-K margin, single-sided cooling may admit no integration. That is still a strong, coupled result, but the single-sided answer in §4.5 and the abstract then changes.

### 9.4 Writing plan and editorial checks
1. One writer per section group: I–II; III; IV; V–VI; VII and the abstract last. Each receives this blueprint, the caps, the float list and the naming rules (§1.4).
2. The editor merges, removes every repeated number and process phrase, and checks that each results subsection closes with its rule.
3. Compile and measure. If the total exceeds 9.75 pages, apply the §3 cut order before trimming prose.
4. An independent proofread against the macros, then a K7 check (no main claim rests only on the supplement).
