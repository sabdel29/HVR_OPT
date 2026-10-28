# Package 48 V RDL: cross-check against Omelet (`pkgintc`)

**In one line.** Omelet's `pkgintc` is a **multiconductor, per-unit-length RLGC, signal-integrity**
extractor for package-interconnect *cross-sections* at 10 MHz – 50 GHz. HVR_OPT's package RDL
model is a **DC, plan-view, current-sharing** model of one 48 V copper sheet fed by BGA balls and
drained by converter pads. They solve different physics. No Omelet code or numerical value is
used in HVR_OPT. Four of its *ideas* (geometry hash, cache key, pre-registration, "the reference
validates, it never calibrates") were adopted, plus its reference-mesh check, and section 10 says
where each one now lives.

**What was read.** A local, read-only copy of `mgharib5/Omelet-pkgintc`, branch
`pkg-interconnect-physics`, commit `94adc70cd7582c5016b96f39f8a6980568b38d09` (read from `.git/`),
at `~/claude_scratch/omelet_ref/repo`. Files were read only. Nothing in that tree was executed
or imported. Every Omelet citation below is `file:line` at that commit. HVR_OPT citations are
to the current working tree.

---

## 1. What Omelet is

* Upstream Omelet is a gem5/Garnet network simulator for 2.5D/3D chiplet systems
  (`README.md:5`). The branch adds `pkgintc`, a "physics-derived package-interconnect" model
  (`docs/pkgintc/README.md:1-5`).
* **Representation:** a 2-D *cross-section*, taken perpendicular to the routing direction
  (`pkgintc/xsec/geometry2d.py:1-12`). It yields per-unit-length R′, L′, C′ and G′
  (`docs/pkgintc/01_architecture.md:70`), which are chained into S-parameters
  (`01_architecture.md:69`). The Q2D reference "solves the SAME problem … a 2-D cross-section,
  per-unit-length R, L, G, C" (`tools/pkgintc/hfss_q2d_reference.py:4-5`) and exports full
  per-metre matrices (`tools/pkgintc/q2d_multilayer.py:4-6, 89-96`).
* **Frequency band:** `F_MIN_HZ, F_MAX_HZ = 1e7, 5e10` (`tools/pkgintc/case_uniform_rdl.py:25`)
  and "frequency 10 MHz – 50 GHz, 201 log points" (`docs/pkgintc/03_hfss_validation_plan.md:104`).
  The Q2D references adapt at 50 GHz (`q2d_multilayer.py:24`, `hfss_q2d_reference.py:40`).
* **Return path:** an infinite PEC ground plane at y = 0, imposed exactly by images
  (`geometry2d.py:98-106`, `pkgintc/xsec/capacitance.py:10`, `pkgintc/xsec/impedance.py:7-14`).
  The Q2D references make that plane PEC so they match (`q2d_multilayer.py:50-54`,
  `hfss_q2d_reference.py:137-144`).
* **Acceptance metrics:** |S| in dB, phase, delay, attenuation and Z0
  (`03_hfss_validation_plan.md:30-38`). These are signal-integrity quantities.
* **No power-delivery content.** A search of `docs/`, `pkgintc/` and `tools/` for
  `power delivery|PDN|IR drop|current sharing|voltage regulator|48 V` returns nothing.
  "HFSS power closure" (`docs/pkgintc/22_hfss_power_closure.md:1-6`) is the port-power
  balance of an S-parameter solve at 20 GHz, not supply current.

## 2. What does HVR's RDL model solve?

It solves the steady **DC** potential of **one copper layer seen in plan view**: the package
48 V RDL sheet. The sheet sits at z = 0, on top of the BGA (z = −300…0 µm) and on the land side
of the substrate (z = 0…300 µm), as recorded in `research/final_closure/architecture_geometry.json`:

    −∇·(σ_s ∇V) + g_a V [balls] = −(I/49)/A_pad [pads],   ∂V/∂n = 0 on the 30 × 30 mm edge

* σ_s = 1/R_sq is a homogenised sheet conductance (5 µm Cu at 30 % occupancy).
* The 54 BGA balls per rail (0.4 mm discs) couple the sheet to the rail (V = 0) through an
  areal conductance g_a = 1/(ρ_c + R_ball·πr²).
* The 49 converter VIN pads (0.2 mm squares) each draw I/49.
* Z1 has no PCB opening. Z2's 23.36 mm opening leaves no ball inside it.
* The observables are R_eff = P/I² and the largest pad-average drop, at I = 1 A, using
  linearity.
* The formulation and the geometry are one function,
  `scripts/reference_tools/moose_pkg_rdl_reference.py`: docstring lines 1-21 and `problem()` at
  :72. The production refined-FV solver (`production()`, :85) and MOOSE heat_transfer-opt
  (`moose()`, :148, with `Reaction` :176 and `BodyForce` :182) both solve it.
* The return rail is the same model, applied to the return balls and pads. It is a separate
  solve.

The exact geometry, with its SHA-256, is in `research/final_closure/rdl_geometry_{Z1,Z2}.json`.
The figures are `presentation/prelim_hvr/figs/rdl_model_explained_{Z1,Z2}.svg` and
`rdl_reference_annotated_{Z1,Z2}.png`. **Orientation:** DC, current sharing, package power.

## 3. What does Omelet's RDL model solve?

Its "organic RDL" benchmarks are **signal lines**:

* Cu traces 6 µm wide on a 12 µm pitch, in polyimide, over a continuous Cu ground plane,
  2 mm long (`03_hfss_validation_plan.md:93-106`).
* The extractor requires "every net to be a single straight path on one metal layer (the
  uniform-MTL case)" (`geometry2d.py:197-205`).
* It solves 2-D electrostatics by BEM for C′ (`capacitance.py:1-25`), the magneto-quasi-static
  filament problem for R′(f) and L′(f) (`impedance.py:1-40`), and transmission-line theory on
  top of those for S(f).
* `case_uniform_rdl.py:2-7, 28-35` reports these cross-sections and their closed-form
  parallel-plate limits: C, L, Z0, delay, and skin depth at 1 and 50 GHz
  (`case_uniform_rdl.py:51-66`).

**Orientation:** multiconductor, RLGC, signal integrity.

## 4. What mathematical assumptions are shared?

* **Linear, passive, reciprocal 2-D elliptic problems.** Both operators are Laplacian-type.
  Both are solved at unit excitation and scaled by superposition. HVR solves once at 1 A, and
  losses scale as I². Omelet uses unit potentials to obtain each matrix column
  (`capacitance.py:20-23`).
* **Quasi-static fields.** HVR is the zero-frequency limit. Omelet is quasi-TEM
  (`01_architecture.md:213-231`).
* **Frozen material constants and no fitted coefficients.** HVR: one `problem()` feeds both
  solvers. Omelet: R2, `01_architecture.md:20-24`.
* **Discretisation kept apart from physics.** Omelet: R1, `01_architecture.md:13-18`. HVR: the
  reference's m1/m2/m3 mesh sequence, `moose_pkg_rdl_reference.py:242`.

## 5. What assumptions differ?

| | HVR package RDL | Omelet `pkgintc` |
|---|---|---|
| Solver plane | plan view (x-y) of one sheet | transverse cross-section of a uniform line (`geometry2d.py:3-11`) |
| Frequency | f = 0 (DC) | 10 MHz – 50 GHz. The MTL layer refuses f ≤ 0: "MTL ports are undefined at DC" (`pkgintc/mtl/line.py:231-232`). Log grids need f > 0 (`pkgintc/num/discretisation.py:33-34`) |
| Unknown | scalar V; in-plane current J = −σ_s∇V spreads in 2-D | conductor charges (BEM) and filament currents, giving R′, L′, G′, C′ and then S(f) |
| Translation invariance | none; point-like sources and sinks | assumed along the line (uniform MTL) |
| Return path | explicit return balls and pads, solved as their own rail with finite resistance | infinite PEC plane by images (`geometry2d.py:98-106`) |
| Excitation | 54 balls with areal contact conductance g_a; 49 pads with prescribed current | ports with reference impedances (`pkgintc/geom/assembly.py:436-444`) |
| Balls, vias, contacts | BGA balls and pad terminals are the core of the model | the cross-section extractor refuses any net with vias (`geometry2d.py:173-177, 214-218`); the composer refuses vias and bumps (`pkgintc/network/__init__.py:1-7`). Via kinds are `rdl_via, ubump, cucu, hybrid_bond, tsv`, with no BGA ball (`pkgintc/geom/conductors.py:109`). No contact-resistance model exists: a search for `bga|ball|contact resist|rho_c` in `pkgintc/` returns nothing |
| Conductor | homogenised sheet (t_Cu × occupancy) | explicit rectangles and circles, panel- and filament-meshed |
| Dielectric | irrelevant at DC | central (ε_r, tan δ, stratified BEM) |
| Boundary | insulated sheet edge (Neumann) | open space over a PEC plane |
| Outputs and gates | R_eff, pad drops, ball split; relative error against a converged reference | RLGC(f), S(f), Z0, delay; dB and phase gates (`03_hfss_validation_plan.md:30-38`) |

## 6. Can any geometry abstraction be reused?

**No code.** Omelet's `Assembly` (stackup, routed nets, `Path`, `ViaTransition`, `Plane`,
`Port`, with unit-carrying quantities; `assembly.py`, `conductors.py:96-110`) is built for
signal nets over ground planes. It has no current-injecting ball with an areal conductance, no
sheet conductance with occupancy, and no sink with prescribed current. HVR's geometry is fully
given by `problem()` → `{balls, pads, sigma_s, g_a}` plus the sheet outline and the cutout.

What was reused is the **identity idea only**: canonical JSON followed by SHA-256
(`assembly.py:451-457`). It was re-implemented in `scripts/visualize_rdl_geometry.py`
(`canonical()`, `sha256()`, `build_payload()`, `rail_payload()`) with two
deliberate differences:

* Coordinates are rounded to 1e-6 mm before hashing, so float noise cannot change the identity.
* List order is kept, because `ball{i}` and `pad{i}` are the MOOSE block names.

Omelet notes that its round conductors are *inscribed* polygons (`geometry2d.py:34-43`). The HVR
analogue was observed independently, not borrowed: gmsh's ball discs are 0.04 % short of πr²
(`ball_block_area_rel_deficit_max` in `tool_evidence/pkg_rdl_moose_{Z1,Z2}/06_annotated_render.json`).

## 7. Can any Q2D/PyAEDT setup code be reused?

**No.** `q2d_multilayer.py` and `hfss_q2d_reference.py` do the following:

* build Q2D `XYSection` designs (`q2d_multilayer.py:38-40`, `hfss_q2d_reference.py:95-97`);
* assign `SignalLine` and `ReferenceGround` conductors over a PEC plane
  (`q2d_multilayer.py:71-77`, `hfss_q2d_reference.py:202-213`);
* adapt at 50 GHz and export distributed per-metre RLGC (`q2d_multilayer.py:79-96`,
  `hfss_q2d_reference.py:215-229, 280-286`).

A cross-section solver cannot represent a plan-view sheet fed through balls. Q2D was not tried
on this host. HVR's licence record lists Q3D Extractor and Maxwell DC conduction as unlicensed
(`presentation/prelim_hvr/tool_evidence/README.md`).

Three *practices* in that code are worth knowing. They are not adopted here:

* Q2D silently ignores HFSS-style adaptive keys, so the script reads back what was applied
  (`hfss_q2d_reference.py:231-255`).
* It deletes stale project files before a rebuild (`hfss_q2d_reference.py:84-93`).
* It sets and records solver defaults that change the physics, such as the causal-dielectric
  conversion (`hfss_q2d_reference.py:101-115`).

## 8. Can any visualization code be reused?

**No. There is none.** No `.py` file in the Omelet tree matches
`matplotlib|pyplot|import vtk|pyvista|.svg` (0 files). The HVR figures are new code in
`scripts/visualize_rdl_geometry.py`, built on `scripts/figstyle.py` and VTK 9.6.2.

## 9. Which pieces MUST NOT be reused (Omelet is high-frequency SI; HVR is DC power delivery)?

1. **The PEC image ground and `ReferenceGround`.** They impose a zero-resistance, infinitely
   wide return. HVR's return is 54 discrete balls feeding a finite sheet, solved as its own rail,
   and its resistance is of the same order as the supply rail's
   (`research/final_closure/package_network.json`, `loop.*.r_return_ohm` against
   `r_supply_ohm`). An image plane would delete that loss and the return topology.
2. **Per-unit-length RLGC, MTL chain matrices and S-parameters.** They assume translation
   invariance along a line. Current in the sheet spreads in 2-D between point-like balls and pads.
3. **The filament skin and proximity impedance, external inductance from the vacuum capacitance
   (`01_architecture.md:213-231`), dielectric loss G′, and causal permittivity.** These are
   frequency-domain physics with no DC role. At f = 0 they reduce to R′ = 1/(σA) of a uniform
   line, which is not the sharing problem.
4. **Q2D and HFSS setups:** `XYSection`, wave ports, adaptive ΔS, frequency sweeps.
5. **dB, phase and Z0 gates and eligibility floors** (`03_hfss_validation_plan.md:30-49`). HVR's
   gates are relative errors of R_eff and pad drop against a converged reference.
6. **Every Omelet material constant and dimension:** σ_Cu = 5.8e7 S/m, ε_r, tan δ, trace widths
   and pitches, dielectric heights (`03_hfss_validation_plan.md:99-103`,
   `hfss_q2d_reference.py:31-39`, `q2d_multilayer.py:16-23`). HVR uses its own ρ_Cu(T)
   (`scripts/phase0m/interconnect.py` `rho_cu`), the 5 µm / 30 % sheet, and the ball and contact
   model of `problem()`.

## 10. Ideas adopted (no code, no values) and where they now live in HVR_OPT

| Idea | Omelet source | Where it lives in HVR_OPT | Status |
|---|---|---|---|
| Geometry hash | `pkgintc/geom/assembly.py:451-457` | `scripts/visualize_rdl_geometry.py` (`build_payload`, `rail_payload`, and the permanent negative tests in `hash_negative_tests`); `research/final_closure/rdl_geometry_{Z1,Z2}.json` (`geometry_hash`, `rail_hashes`, `hash_method`); `data-geometry-hash` on `rdl_model_explained_*.svg`; `06_annotated_render.json`; PNG text chunk | adopted in this work |
| Solver cache key | `assembly.py:459-488` ("This -- not `geometry_hash` -- is what a cached solver result may be keyed on") | `render_key` in `tool_evidence/pkg_rdl_moose_{Z1,Z2}/06_annotated_render.json`: SHA-256 over the geometry hash, Exodus SHA-256, VTK and rsvg versions, colormap, viewports, arrow parameters and the script's own SHA-256 (`render_key()`). HVR_OPT does not cache solver results for this stage, so **no solver cache key was introduced** | adopted for the figure only |
| Pre-registration | `03_hfss_validation_plan.md:17-26` | Already HVR_OPT practice: tolerances declared before results were read (`scripts/final_closure_physical_etm.py:48-56`), and `research/final_closure/local_mesh_policy.json` (`declared_at`, `declared_before_any_result_of_levels`, `amendments`). **The MOOSE RDL reference was not pre-registered with a hash before it ran**, because the run predates this hash. Its identity is checked afterwards: `verify_against_solve()` in `scripts/visualize_rdl_geometry.py` shows that the Exodus blocks are `problem()`'s balls and pads (centroids within float32 precision), that the `rdl.i` constants equal `problem()`, that the Exodus mesh is the m3 mesh, and that the CSV reproduces the reference JSON exactly | partial |
| "The reference validates, it never calibrates" | `03_hfss_validation_plan.md:3`: "**Rule that governs everything here:** HFSS validates, it never calibrates." Also `01_architecture.md:20-24` and `hfss_q2d_reference.py:17` ("Nothing in pkgintc is tuned to this reference.") | Both solvers take the same `problem()` (`moose_pkg_rdl_reference.py:7-15`). The MOOSE result is read only by reporting code: `scripts/final_closure_accuracy_matrix.py:100`, `scripts/final_closure_evidence.py:163`, `scripts/prelim_deck_main.py:157`, `scripts/prelim_deck_final_sections.py:206`, and `scripts/visualize_rdl_geometry.py`. No production parameter is derived from it | holds by construction for this stage |
| Reference-mesh check at 2× density | `03_hfss_validation_plan.md:126-129`: "A model–reference difference smaller than the reference's mesh sensitivity is reported as such, not as a pass." | `moose_pkg_rdl_reference.py:242` runs m1/m2/m3 (h_fine 0.04 / 0.02 / 0.01 mm), with an Aitken extrapolation at :254. `mesh_sensitivity()` in `scripts/visualize_rdl_geometry.py` now writes the reference's own m2→m3 change next to the model error, in `reference_mesh_sensitivity` of `tool_evidence/pkg_rdl_moose_{Z1,Z2}/07_slide_numbers.json` | adopted in this work |

**What the 2× check says.** For both architectures and both observables, the production–MOOSE
difference *exceeds* the reference's own m2→m3 change, so it is resolved. It exceeds it only by
1.25–1.53×, which is the same order as the reference's own mesh uncertainty. The comparison
against the extrapolated reference (`rel_err_R_eff_vs_extrapolated` in
`reference_pkg_rdl_moose_{Z1,Z2}.json`) is therefore the better-conditioned statement of
agreement. The authoritative values are the generated `reference_mesh_sensitivity` blocks; the
ratio range here is quoted from them. Regenerate them; do not edit them.

## 11. No Omelet numerical parameter was copied

**No Omelet number, constant, material value, dimension, tolerance, gate, frequency, mesh or
solver setting, and no Omelet code, was copied into HVR_OPT.** The Omelet tree was read and was
never executed or imported. The hash recipe was re-implemented from the idea, using HVR's own
rounding (1e-6 mm), canonicalisation and order rules. Every physical input in the figures and
in the geometry files comes from HVR's own `problem()`, `architecture_geometry.json`,
`package_stack.yaml` and the MOOSE output files. The only thing shared is the name of the
standard algorithm, SHA-256.
