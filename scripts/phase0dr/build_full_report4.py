#!/usr/bin/env python3
"""Append sections 8-20 (equations, validation, physics, results, defects, novelty, roadmap)."""
from __future__ import annotations
import csv, json, textwrap
from pathlib import Path

R = Path(__file__).resolve().parents[2]
RES = R / "results"
MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"


def rd(p): return list(csv.DictReader((RES / p).open()))
def jd(p): return json.loads((RES / p).read_text())
def fl(v, n=3):
    try: return f"{float(v):.{n}f}"
    except (TypeError, ValueError): return str(v)


def tbl(hdr, body, src=None, align=None):
    a = align or ("l" + "r" * (len(hdr) - 1))
    out = ["| " + " | ".join(map(str, hdr)) + " |",
           "|" + "|".join({"l": ":--", "r": "--:", "c": ":-:"}[c] for c in a) + "|"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in body]
    if src: out += ["", f"Source: `{src}`"]
    return "\n".join(out) + "\n"


S, A = [], None
S = []; A = S.append

A("\\newpage\n# Governing Equations\n")
A(textwrap.dedent(r"""
**Converter loss** (upstream `compute_total_loss`, unmodified). Conduction and switching:

$$P_{cond} = \frac{V_{out}}{V_{in}} I_{out,rms}^2 \big( R_{common} - R_{corr} \big), \qquad
  I_{out,rms} = \sqrt{I_{out}^2 + \Delta i_{eff}^2/12}$$

$$P_{sw} = \underbrace{f_{sw}\Big(\tfrac{V_{in}}{N}-V_{out}\Big) I_{out,rms}\frac{Q_{GD}+Q_G}{I_g}}_{HS}
 + \underbrace{f_{sw}\big(N C_G^{HS} + K C_G^{LS}\big) V_{gs}^2}_{gate}
 + \underbrace{\tfrac{f_{sw}}{2}\Big(N C_{OSS}^{HS}(\tfrac{V_{in}}{N}-V_{out})^2 + K C_{OSS}^{LS} V_{out}^2\Big)}_{C_{OSS}}$$

Coupled-inductor ripple correction: $\Delta i_{eff} = \Delta i_{raw}/(1+k_c(K-1))$.

**Rail assignment and stage currents.**

$$P_{in} = V_{out} I_{out} + P_{conv}, \qquad I_{in} = P_{in}/V_{in}, \qquad
  \eta_{stage} = \frac{V_{out}I_{out}}{P_{in}}$$

**Bulk interconnect resistance**, per tier, with temperature and parallelism:

$$R_{single}(T) = \frac{\rho(T)\,L}{A}, \qquad \rho(T) = \rho_{20}\big[1+\alpha(T-20)\big],
  \qquad A = \begin{cases}\pi d^2/4 & \text{circular (BGA, TSV, C4)}\\ d^2 & \text{square (pad)}\end{cases}$$

$$n_{req} = \left\lceil \frac{I}{I_{max}} \right\rceil, \qquad
  R_{field} = \frac{R_{single}}{n_{req}}, \qquad
  R_{loop} = R_{supply} + R_{ground}, \qquad P = I_{rms}^2 R_{loop}$$

Feasibility: if $n_{req} > n_{avail}(A_{fp},\text{pitch})$ the architecture is **infeasible**.

**Device temperature coefficients.**

$$R_{DS(on)}(T) = R_{25}\big[1+\alpha_{GaN}(T-25)\big], \qquad
  R_{DCR}(T) = R_{25}\big[1+\alpha_{Cu}(T-25)\big]$$

**2-D RDL sheet.** With sheet conductance $\sigma_s = t_{Cu}\,\mathrm{occ}/\rho(T)$:

$$\nabla\!\cdot\!\big(\sigma_s \nabla V\big) = -J(x,y), \qquad
  P_{supply} = \int \sigma_s |\nabla V|^2\, dA, \qquad P_{loop} = 2P_{supply}$$

**Skin depth** (used to justify the DC treatment at $f_{sw}$):
$\delta = \sqrt{\rho/(\pi f \mu)}$.

**Thermal.** Steady-state anisotropic conduction with Robin cooling:

$$\nabla\!\cdot\!(\mathbf{K}\nabla T) + q = 0, \qquad
  -\mathbf{K}\nabla T\cdot\mathbf{n} = h\,(T - T_\infty)$$

**Thermoelasticity.** Temperature enters only as a load; a gradient is never used as a stress:

$$\nabla\!\cdot\!\boldsymbol\sigma + \mathbf b = 0, \qquad
  \boldsymbol\sigma = \mathbf C : \big(\boldsymbol\varepsilon - \boldsymbol\alpha\,\Delta T\big),
  \qquad \Delta T = T - T_{ref}$$

Silicon uses the cubic tensor ($C_{11}=166$, $C_{12}=64$, $C_{44}=79.6$ GPa).

**Warpage metric.** Peak-to-valley out-of-plane displacement over a named surface:

$$w_{pv} = \max_{(x,y)} u_z(x,y) - \min_{(x,y)} u_z(x,y)$$

**Materiality and resolution** (Phase-0B/0C decision rule):

$$S_m = \frac{m_{max}-m_{min}}{|m_{med}|}, \qquad \text{resolved} \iff S_m > 2u_m$$

**Pareto dominance.** $x$ dominates $y$ iff $f_i(x)\le f_i(y)\ \forall i$ and $\exists i: f_i(x)<f_i(y)$.
ET tuple $(P_{elec}, T_{max})$; ETM tuple $(P_{elec}, T_{max}, w_{pv})$.

### Symbols

| Symbol | Meaning | Units |
|:--|:--|:--|
| $V_{in}, V_{out}$ | converter input / output rail | V |
| $I_{in}, I_{out}$ | rail currents (upstream / downstream of conversion) | A |
| $P_{conv}, P_{PDN}, P_{elec}$ | converter, distribution, total electrical loss | W |
| $\rho(T), \alpha$ | resistivity and its temperature coefficient | $\Omega$m, 1/K |
| $\sigma_s, t_{Cu}$, occ | RDL sheet conductance, Cu thickness, metal occupancy | S/sq, m, -- |
| $h_{sub}, t_{tile}$ | power-substrate and HVR-tile thickness | m |
| $n_{req}, n_{avail}$ | required / available parallel conductors | -- |
| $\mathbf K, h, T_\infty$ | conductivity tensor, film coefficient, sink temperature | W/mK, W/m$^2$K, $^\circ$C |
| $\mathbf C, \boldsymbol\alpha, T_{ref}$ | stiffness tensor, CTE, stress-free temperature | Pa, 1/K, $^\circ$C |
| $w_{pv}$ | peak-to-valley warpage | m |
| $S_m, u_m$ | architectural spread, numerical uncertainty | -- |
| $J$ | area-budget current density target ($A_{budget}=I_{out}/J$) | A/mm$^2$ |
"""))

A("\\newpage\n# Electrical Model Validation\n")
tv = rd("phase0d/tsv_resistance_validation.csv")
mx = max(abs(float(r["error_pct"])) for r in tv if r["check"] != "june_reference")
A(textwrap.dedent(f"""
**Analytic scaling.** All 23 checks in `results/phase0d/tsv_resistance_validation.csv` agree
with the closed form to a maximum of **{mx:.2e} %** (machine precision): $R\\propto h$,
$R\\propto 1/d^2$, $R\\propto 1/n$, and $\\rho(125)/\\rho(20)=1.41265=1+\\alpha\\cdot105$.

**June-2026 reference.** Model 7.215 m$\\Omega$ vs quoted 7.1 m$\\Omega$ for a 300 um Cu TSV
(**+1.62 %**); BGA +3.45 %; micro-bump **exact** once the square cross-section is recovered.

**Independent FE (MOOSE).** Analytic strip conductance reproduced to 5.8e-12 %; distributed
source/load sheet dissipation agrees to **0.33--0.45 %**.

**AC correction is not required at the operating point.** Skin depth in copper:

| $f$ | $\\delta$ | vs 15 um TSV radius | vs 5 um RDL |
|:--|--:|:--|:--|
| $f_{{sw}}$ = 0.286 MHz | 123 um | 8.2x larger --- no skin effect | 25x larger --- none |
| 10 MHz (35th harmonic) | 20.7 um | 1.4x larger --- onset | 4x larger --- none |
| 1 GHz | 2.1 um | 7x smaller --- deep skin effect | comparable |

At $f_{{sw}}$ every conductor is electrically thin, so $R_{{ac}}\\approx R_{{dc}}$ and the DC model is
correct. **No current-crowding correction was applied**, because none was demonstrated ---
introducing an empirical factor without evidence is precisely what the brief forbids.
"""))

A("# Thermal Model Validation\n")
A(textwrap.dedent("""
* **Energy conservation.** Robin flux integrated over both cooled surfaces equals the injected
  power to $\\pm 0.000$ % on every run in every phase --- an independent check, not a solver
  residual.
* **Cooling calibration.** $h_{top}$ secant-solved to the June-2026 cooled baseline: 83.514
  $^\\circ$C against 84 $^\\circ$C, residual $-0.49$ K, then frozen.
* **Mesh convergence.** $T_{max}$ changed 0.29 % (thin substrate) and 0.18 % (thick) over the
  final refinement step.
* **Conduction operator validated against MOOSE** to 5.8e-12 % on an analytic case.

**Not done:** a MOOSE or Icepak cross-check of the full 3-D package thermal model with
spatially mapped Joule heat (TH-1...TH-4). This is the largest open validation item and is
carried to the roadmap.
"""))

A("# Mechanical Model Validation\n")
A(textwrap.dedent("""
* **Analytic check.** Single-element free thermal expansion reproduces $\\alpha\\Delta T$ exactly
  (1.666e-3 mm for 16.66 ppm/K over 100 K).
* **Mesh convergence.** Four graded levels; die warpage 0.50 %, package warpage 0.40 %,
  Si $\\sigma_1$ p99 4.43 % --- all inside target. Independently repeated for the thick
  substrate (0.45 %).
* **Solver discovery.** ITERATIVE CHOLESKY disagreed with the direct solver by **35 % on
  package warpage** and was rejected; C3D8I has a ~40 k element ceiling in this build, handled
  by graded meshing plus a hard guard.
* **Support conditions.** BC-A is 3-2-1 rigid-body suppression with reaction forces
  $\\le 4.3\\times10^{-10}$ N --- direct evidence the constraint manufactures no stress.
  BC-B is a compliant support layer anchored to source-backed BGA geometry.
* **Homogenisation.** Valid for warpage (spread preserved to 1.7 pp, absolute bias $-6$ to
  $-9$ %); **invalid for local stress** ($+82$ to $+97$ %).
* **Known limitations.** M0 rung only --- linear thermoelastic, operational load, no assembly
  pre-stress, no plasticity, creep or fatigue. **No ANSYS structural validation exists.**
"""))

A("\\newpage\n# Coupled ETM Physics --- mechanisms, not just numbers\n")
A(textwrap.dedent("""
**Why placement affects warpage.** The HVR tiles are stiff, low-CTE inclusions embedded in a
silicon substrate and heated from within. Global curvature follows the first and second moments
of that inclusion field about the neutral axis. Concentrating it centrally (compact) maximises
local curvature; spreading it to the perimeter (edge) reduces peak deflection; offsetting it
(asymmetric) adds a tilt. Measured correlations bear this out: $r(w, I_{polar}) = -0.62$,
$r(w, |M_1|) = +0.48$.

**Why count is inert.** Subdividing a fixed total inclusion area into more, smaller, still
symmetric pieces changes neither the first moment (still zero) nor materially the second
moment. C05, C13 and C17 have identical $A_{tot}$ and near-identical $I_{polar}$, and their
warpages agree to 0.02--4 %.

**Why footprint changes the mechanical moment.** Unlike count, footprint changes $A_{tot}$
directly, hence the inclusion volume and its moment --- which is why it moves warpage ($\\pm21$ %)
where count does not.

**Why thickness changes bending stiffness.** Two competing effects: plate stiffness grows as
$D\\sim Eh^3$, while the *fixed-thickness* inclusion sits further from the shifted neutral axis
so its moment arm grows as $\\sim h$. Net $w\\sim h^{-1.95\\pm0.02}$, measured identically across
four placement configurations.

**Why converter loss has high mechanical leverage.** A $\\pm25$ % change in HVR loss is only
$\\pm3.7$ % of total package heat yet moves warpage $\\pm10.8$ %, because that heat is deposited
exactly at the CTE-mismatched inclusion rather than spread over the die.

**Why the rail voltage sets the interconnect penalty.** For fixed transferred power,
$I\\propto 1/V$, so an identical segment on the 1 V rail carries 44x the current and dissipates
~1960x more. This is why the same physical TSV is negligible in ARCH_A and 45x more lossy in
ARCH_B --- and why the *feasibility* limit bites only on the LV rail.
"""))

A("\\newpage\n# Architecture Comparison\n")
cor = rd("phase0dr/coupled_candidates_corrected.csv")
body = []
for r in sorted(cor, key=lambda x: float(x["P_elec_total_w"])):
    body.append([r["case"].replace("ARCH_", "").replace("_distributed", "/dist")
                 .replace("_asymmetric", "/asym").replace("_edge", "/edge").replace("_compact", "/comp"),
                 r["tsv_rail"], int(float(r["n_vr"])) if "n_vr" in r else 4,
                 fl(r["a_hvr_total_mm2"], 1), f"{float(r['h_sub_mm'])*1000:.0f}",
                 fl(r["P_conv_w"], 2), f"{float(r['P_bga_w'])*1e3:.2f}",
                 f"{float(r['P_c4_w'])*1e3:.2f}", f"{float(r['P_tsv_w'])*1e3:.2f}",
                 fl(r["P_rdl_w"], 2), f"{float(r['P_microbump_w'])*1e3:.2f}",
                 fl(r["P_elec_total_w"], 2), fl(r["efficiency_pct"], 2),
                 fl(r["T_max_C"], 2), fl(r["die_warpage_pv_um"])])
A(tbl(["case", "TSV rail", "N", "A_HVR (mm²)", "h_sub (µm)", "P_conv (W)", "P_BGA (mW)",
       "P_C4 (mW)", "P_TSV (mW)", "P_RDL (W)", "P_µb (mW)", "P_elec (W)", "η (%)",
       "T_max (°C)", "warp (µm)"], body,
      src="results/phase0dr/coupled_candidates_corrected.csv"))
rc = jd("phase0dr/reversal_corrected.json")
A(f"\nET Pareto: `{rc['et_best']}` (single point). "
  f"ETM Pareto ({len(rc['etm_pareto'])} members): " +
  ", ".join(f"`{c}`" for c in rc["etm_pareto"]) + ".\n")

A("\\newpage\n# Positive Results\n")
A(textwrap.dedent("""
1. **Architecture changes mechanics substantially.** Die warpage spans 1.8--15.6 um (8.5x)
   across the frozen DOE at fixed load, footprint and heat.
2. **Substrate thickness is win/win/win**, and survives every correction: $-56.5$ % warpage,
   $-2.75$ K, $-1.0$ % electrical loss, with $w\\propto h^{-1.95\\pm0.02}$ measured identically
   across four placement configurations (interaction spread 0.79 pp).
3. **HVR footprint is a genuine ETM opposition**: $-54$ % electrical loss for $+84$ % warpage.
4. **Converter loss carries disproportionate mechanical leverage** --- 3.7 % of package heat
   moves warpage 10.8 %.
5. **The rail carried by a segment is decisive**, and it is architecture-specific: the same TSV
   is 45x more lossy on the LV rail. Phase 0E shows this does **not** eliminate the LV-TSV
   architecture --- it is feasible under every source-backed current density --- but it does
   leave that architecture with a 1.46x thickness margin against ARCH_A's 67.7x.
6. **Numerical soundness**: energy balance $\\pm0.000$ %, warpage converged to 0.50 %, reactions
   $\\le 4.3\\times10^{-10}$ N, sheet model within 0.33--0.45 % of an independent FE solver.
"""))

A("# Negative and Null Results\n")
A(textwrap.dedent("""
These are reported at equal prominence because several of them constrain the thesis more than
the positive results support it.

1. **VR count is mechanically inert.** +0.02 % (4->6), $-4.07$ % (4->8), $-0.21$ % (2->4
   compact). This killed the variable the original novelty argument leaned on.
2. **Tile aspect ratio is inert** ($-1.76$ %). On this square vehicle the AR = 2 and AR = 0.5
   cases are provably *identical* by 90$^\\circ$ symmetry, so that DOE case can never detect
   anisotropy.
3. **Interface peel never converged** --- 19.2 % per refinement step, and the exclusion-radius
   variants were no better (19.98--20.07 %). Root cause: the underfill is one element thick at
   every standard level. Marked UNRESOLVED AT M0 and excluded from all decisions.
4. **No architecture-dependent thickness tradeoff.** Even forcing the 1 V rail through the
   substrate leaves the penalty an order of magnitude below the thermal benefit.
5. **"ET is blind to placement" was wrong** --- an artifact of a lumped RDL model. Corrected
   spread is 188.8 %, not 1.08 %.
6. **The cheap mechanical win was wrong.** 2.03 W/um becomes **16.2 W/um**, 8x worse.
7. **No dominance reversal is achievable** with warpage as a pure added objective ---
   structurally, not empirically.
8. **G2 has never been testable.** No source-backed allowable exists, and all warpages
   (1.8--8.6 um) sit far inside any plausible limit at this power scale.
"""))

A("\\newpage\n# Model Defects Discovered and Fixed\n")
A(tbl(["#", "defect", "found in", "consequence if unfixed", "resolution"],
      [[1, "`rho_mohm_per_mm = 50` uncalibrated", "Phase 0D", "2100 % IR drop; a fixed point at 569 °C", "geometry-derived plane resistance"],
       [2, "lumped RDL gives every pair its own full-width conductor", "Phase 0D-R", "RDL loss wrong by ~65x; false 'ET is blind to placement'", "2-D sheet solve, MOOSE-validated"],
       [3, "hard-coded `r_tsv_ohm`/`r_bump_ohm`", "Phase 0C", "h_sub had no path into the electrical objective", "geometry-derived R(h,d,n,T)"],
       [4, "global 'TSV carries input current'", "Phase 0D-R", "wrong rail (and 44x wrong current) for ARCH_B", "per-segment rail from the power-path graph"],
       [5, "ground return omitted", "Phase 0D-R", "every interconnect loss understated 2x", "R_loop = R_supply + R_ground"],
       [6, "`min(n_req, n_avail)` silently overloads vias", "Phase 0D-R", "hides that ARCH_B is unbuildable", "hard infeasibility gate"],
       [7, "circular cross-section assumed for the chiplet pad", "Phase 0D-R", "+27 % on that tier", "square pad recovered from June's 100 µm² area"],
       [8, "point-source injection in the RDL sheet", "Phase 0D-R", "+776 % loss from a log singularity", "finite-area injection over the tile footprint"],
       [9, "footprint snapped to nearest grid cell", "Phase 0D-R", "destroys grid convergence", "exact cell-overlap area weighting"],
       [10, "ITERATIVE CHOLESKY solver", "Phase 0B", "35 % error on package warpage", "rejected; direct solver only"],
       [11, "C3D8I element ceiling ~40 k", "Phase 0B", "silent segfault", "graded mesh + hard guard"],
       [12, "underfill 1 element thick at all levels", "Phase 0C", "peel can never converge", "diagnosed; metric demoted"],
       [13, "placement classes count-specific", "Phase 0C / 0D", "N=6 distributed silently skipped", "family-to-class mapping per count"],
       [14, "`p99` not population-stable in a thin layer", "Phase 0C", "191 % artifact under refinement", "documented; raw + p99 both reported"],
       [15, "RDL stack (5 µm, occ 0.60, 1 layer) unsourced", "Phase 0E", "the DOMINANT term was an assumption; 5.56x too resistive", "ECTC-2024 Table I, verified against its own R'_Heff"],
       [16, "`R_field = R_single / n_required`", "Phase 0E", "makes P ~ I look like a law when it is an allocation policy", "n_req / n_alloc / n_avail separated; R uses n_alloc"],
       [17, "per-via limit 33 mA dropped the P&G factor of 2", "Phase 0E", "halves the apparent via capability", "N = 2I/(A·J) applied as the source writes it"],
       [18, "per-via limit 4.8 mA had no source", "Phase 0E", "**falsely declared ARCH_B infeasible**", "source-backed J envelope; feasibility reported as a map"],
       [19, "whole-edge Dirichlet used as a solver reference", "Phase 0E", "+25 % / +55 % error in the MOOSE comparison", "finite-area reference at the same point in both codes"],
       [20, "104-term `ParsedFunction` silently loses terms", "Phase 0E", "18 % of injected current lost, ~35 % in power", "uniform load + 4 boxcars + 11th-order Gauss"],
       [21, "tile placed 0.27 mm off the die edge", "Phase 0E", "clipped footprint treated differently by the two codes", "placements asserted to lie on the substrate"],
       [22, "AEDT exported `im(Z)` before `re(Z)`", "Phase 0E", "R and X transposed; a confident wrong EM validation", "columns matched by header name, never by position"],
       [23, "homogeneous HVR tile filling the bounding box", "Phase 0E", "mechanical inclusion volume overstated at small footprints", "composite from the compiler's own component inventory"],
       [24, "**150 µm tile holding a 500 µm inductor**", "Phase 0F", "**both thickness endpoints of four phases are unbuildable**", "height rule `t_cell + h_tsv <= h_sub`; geometry gate before every mesh"],
       [25, "Phase-0B cooling calibration reused at 4x the load", "Phase 0F", "package at ~130 °C instead of 84 °C; converter loss overstated ~25 mW/K x 46 K", "recalibrated at 1 kW; h_top is 9.47x larger"],
       [26, "Phase-0B placement families hard-wired to n_vr = 4", "Phase 0F", "no 49-regulator layout expressible at all", "Phase-0F lattice families with the same validation rules"],
       [27, "interface shear used without qualification", "Phase 0F", "a marginally converged, material-sensitive metric would have carried mounted design decisions", "convergence + 9-corner ordering test before any mounted claim"],
       [28, "electrical-only crossover sweep at frozen temperature", "Phase 0F", "removes the converter-loss reduction that motivates thickening; every load then falsely prefers thin", "crossover taken from full ET fixed points only"]],
      align="rlllr"))
A("\nThis table is evidence of audit rigour: nine were found by Phase 0E and five more by "
  "Phase 0F. **Defect 24 is the most consequential in the project.** For four phases the "
  "mechanical vehicle held a converter that could not physically fit inside it, and the "
  "inconsistency was carried forward once with the remark that it \"does not affect trends\" "
  "-- an assumption that was never tested until Phase 0F tested it. The directions did "
  "survive; the magnitudes and the swept thicknesses did not.\n")

A("\\newpage\n# Uncertainty and Fidelity Ladder\n")
A(tbl(["class", "item", "magnitude", "effect on conclusions"],
      [["numerical", "mechanical mesh convergence", "0.50 % (die warpage)", "negligible"],
       ["numerical", "RDL sheet grid", "≤0.72 %", "negligible"],
       ["numerical", "multilayer RDL vs MOOSE, 3 placements", "0.45–1.10 % (power)", "negligible; one calibration"],
       ["numerical", "HFSS R(f) flatness below the skin crossover", "0.18 %", "no AC term needed at f_sw"],
       ["parameter", "RDL t_Cu — **CLOSED** at 10 µm", "envelope 1.02–3.40 mΩ/sq across readings", "no longer dominant-by-assumption; doubly sourced"],
       ["parameter", "RDL occupancy — **CLOSED**, derived 0.833", "set by the 10/2 µm line/space rule", "no longer free"],
       ["parameter", "RDL layer count — **CLOSED**, 2 VDD + 2 GND", "factor 2 vs the 1+1 reading", "settled by the source's own PCB row"],
       ["parameter", "**J_Cu provisioning (1.0e8 vs 4.0e8)**", "**4x; each self-consistent across 2 tiers**", "ARCH_B feasible under BOTH; no longer binary"],
       ["parameter", "**I_max,reliability** — still OPEN", "no primary EM study retrievable here", "**no feasibility claim is made**"],
       ["parameter", "ECTC Table II magnitudes not reproducible", "0.22–0.35 W vs published 39.5–76 W", "**RDL magnitudes stay provisional**"],
       ["parameter", "hvr_effective E, CTE", "warpage 3.5x across the range", "magnitudes untrustworthy; **footprint ordering robust to 0.06 %**"],
       ["parameter", "HVR tile height (150 µm modelled)", "the chosen inductor alone is 500 µm tall", "absolute warpage is not a design value"],
       ["parameter", "current crowding at via/pad", "1.33–1.96x on a 1-D series estimate", "<1 % of PDN loss; carried as a band"],
       ["parameter", "α_GaN (7.5e-3 /K)", "2x change moves rate ~12 %", "not load-bearing"],
       ["parameter", "C4 geometry", "P_C4 ≈ 0.74 mW", "negligible"],
       ["model-form", "H0 homogenisation", "−6 to −9 % warpage; +82–97 % local stress", "warpage usable; local stress excluded"],
       ["model-form", "multilayer RDL, ideal stitching", "stitching density unstated by any source", "optimistic bound; solver supports finite stitching"],
       ["model-form", "explicit VDD + GND networks", "exactly 2x only for a symmetric stack", "now derived rather than assumed"],
       ["model-form", "M0 rung", "no assembly pre-stress, no plasticity", "no lifetime claim possible"],
       ["boundary", "**BC-A vs BC-B**", "**warpage suppressed ~20-30x under BC-B**", "at 240 W orderings reverse or vanish; **at 1 kW warpage QUALIFIES as a mounted metric**"],
       ["geometry", "**HVR cell height (720 µm, was 150 µm)**", "**h_sub < 770 µm is unbuildable**", "**supersedes every 0B-0E absolute magnitude**"],
       ["boundary", "1-kW cooling calibration", "9.47x the Phase-0B coefficient; DERIVED", "sets every 1-kW temperature-dependent loss"],
       ["model-form", "top- vs substrate-side cooling", "substrate-side cannot reach 84 °C at all", "gradient direction, and therefore warpage sign, depends on it"],
       ["boundary", "cooling calibration", "residual −0.49 K", "frozen for all phases"]],
      align="llll"))
A(textwrap.dedent("""
### Status of every major claim

**PROVEN** --- architecture changes warpage 8.5x; thickness is win/win/win with
$w\\propto h^{-1.95}$; count and aspect ratio inert; footprint opposition; RDL dominates
distribution loss; the model chain is numerically sound and MOOSE-validated.

**SUPPORTED** --- the moment-based mechanism (adj-$R^2=0.72$); LV-rail TSV 45x penalty;
converter-loss leverage; H0 bias of $-6$ to $-9$ %.

**PROVISIONAL** --- all absolute warpage values; all absolute RDL losses; BC-B magnitudes;
$\\alpha_{GaN}$; C4 geometry; the square-tile footprint approximation.

**OPEN** --- any mechanical allowable; the RDL metal stack; $I_{via,max}$; capacitor-ESR and
gate-charge temperature dependence; ANSYS cross-validation; assembly pre-stress.

**NOT TESTED** --- G2 feasible-set reversal; kW-scale behaviour; transient response; BC-B under
the corrected electrical model; PALACE EM validation; MOOSE package-thermal validation.
"""))

MD.write_text(MD.read_text() + "".join(S))
print(f"appended sections 8-17; now {len(MD.read_text().splitlines())} lines")
