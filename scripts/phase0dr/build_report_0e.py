#!/usr/bin/env python3
"""Append the Phase-0E chapter. Runs after build_full_report3.py, before 4."""
from __future__ import annotations
import csv, json, re, sys, textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "results"
P0E = RES / "phase0e"
MD = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
sys.path.insert(0, str(REPO / "scripts" / "phase0e"))
from stack import stacks_from_cfg, load_cfg

S = []
A = S.append


def figure(path, caption, w="92%"):
    """Continue the document's figure numbering by counting what is already in the file."""
    n = len(re.findall(r"!\[\*\*Figure ", MD.read_text())) + sum(
        1 for x in S if x.startswith("\n![**Figure")) + 1
    return (f"\n![**Figure {n}.** {caption} *(Phase 0E; data: `results/phase0e/`)*]"
            f"({P0E / path}){{width={w}}}\n")


def rd(n):
    p = P0E / n
    if not p.exists():
        return None
    return json.loads(p.read_text()) if p.suffix == ".json" else list(csv.DictReader(open(p)))


stacks = stacks_from_cfg()
cd = load_cfg()["current_density"]["cu"]
val = rd("multilayer_rdl_validation.json")
ectc = rd("ectc_table2_validation.json")
em1 = rd("aedt/em1_hfss_np1_corrected.json")
fp_fe = rd("footprint_material_fe.csv")
fp_mat = rd("footprint_material_sensitivity.csv")
cands = rd("phase0e_candidates.csv")
bcbd = rd("bcb_discrimination.csv")
bcb = rd("bcb_corrected_results.csv")
ice = rd("aedt/icepak_TH1.json")

A("\\newpage\n# Phase 0E --- Physical Stack Closure and Independent Validation (authoritative)\n")
A(textwrap.dedent("""
Phase 0D-R corrected the *current paths*. It left the *physical stack* unsourced, and since
its own dominant term was the RDL, the dominant term rested on four assumptions. Phase 0E
closes them from primary sources, separates three quantities that had been conflated in the
TSV model, and revalidates against independent solvers. **The ANSYS licence was restored on
2026-09-06**, so HFSS and Icepak are used here; Q3D Extractor is not licensed.
"""))

A("## The four assumptions that set the dominant term\n")
A("| parameter | Phase 0D-R | Phase 0E | source |")
A("|---|---|---|---|")
A("| RDL Cu thickness | 5 µm (ASSUMPTION) | **10 µm** | ECTC-2024 Table I; independently confirmed by ISCAS-2024 |")
A("| metal occupancy | 0.60 (ASSUMPTION) | **0.833, derived** from the 10/2 µm line/space rule | ECTC-2024 Table I |")
A("| layer count | 1 (ASSUMPTION) | **2 VDD + 2 GND** | ECTC-2024 \"P/G layers\" column, settled by the PCB row |")
A("| ground return | \"×2 on the answer\" | explicit second network, solved | — |")
r = stacks["ectc2024_primary"].sigma_s_net("vdd") / stacks["phase0dr_legacy"].sigma_s_net("vdd")
A(figure("FIG_0E_A_metal_stack.png",
         "The sourced multilayer power stack replaces the assumed single sheet. Occupancy is "
         "derived from the line/space design rule, not chosen."))
A(f"\nSheet conductance rises by **{r:.3f}×**, so every Phase-0D-R RDL magnitude falls by that "
  "factor. The stack is not merely quoted: both trace rows of the source table reproduce the "
  "paper's own derived `R'_Heff` to better than 2 %, which is why it is treated as closed.\n")

A("## What the sources would not confirm\n")
A(textwrap.dedent("""
The June-2026 framework contains **no metal stack at all** --- its PPDN is a lumped
`rho_mohm_per_mm = 0.5` distance model with no thickness, layer count or occupancy. And
ECTC-2024's *published loss magnitudes* (Table II) cannot be reconstructed from its own
printed stack and equations: applying them literally gives 0.22-0.35 W against a published
39.5-76 W, and no segment count closes a gap that scales as 1/S. The stack **parameters** are
validated; the **magnitudes** are not. RDL losses are therefore always quoted with the stack
that produced them.
"""))

if val:
    A("## The compact multilayer model is validated against an independent solver\n")
    A(f"Predeclared before any run: $|\\Delta P| \\le {val['target_P_pct']}$ %, "
      f"$|\\Delta V| \\le {val['target_V_pct']}$ %, "
      "**one calibration for all placements** --- no per-case fitting.\n")
    A("| placement | compact (W) | MOOSE FE (W) | ΔP | ΔV | |")
    A("|---|---:|---:|---:|---:|---|")
    for c in val["cases"]:
        A(f"| {c['placement']} | {c['P_compact_w']:.5f} | {c['P_moose_w']:.5f} | "
          f"{c['dP_pct']:+.2f} % | {c['dV_pct']:+.2f} % | {'PASS' if c['pass'] else 'FAIL'} |")
    A(figure("FIG_0E_D_rdl_validation.png",
             "Multilayer RDL compact model against an independent FE solver, with the grid "
             "convergence that fixes the working resolution."))
    A("\nGetting this right required fixing three defects in the *comparison*, each of which "
      "would have produced a confident wrong answer: a whole-edge Dirichlet reference (a "
      "different boundary-value problem, +25 % / +55 % error), a 104-term `ParsedFunction` that "
      "silently lost terms (18 % of the injected current), and a tile placed 0.27 mm off the "
      "die edge where the two codes treat clipping differently.\n")

if em1:
    sw = em1["sweep"]
    flat = [s for s in sw if s["f_hz"] <= 6e6]
    fl = 100 * (max(s["R_ohm"] for s in flat) / min(s["R_ohm"] for s in flat) - 1)
    A("## EM validation --- and a solver used only where it is valid\n")
    A(textwrap.dedent(f"""
    Q3D Extractor is **not licensed** on this server (`UNSUPPORTED "elec_solve_q3d" ... No such
    feature exists (-5,346)`), so DC conduction is validated with MOOSE and HFSS is confined to
    its valid regime. A two-port series extraction at 286 kHz was tried first and **rejected**:
    HFSS returned `Z11 = Z12 = -4.2e7` ohm and the series impedance is their difference --- eleven
    digits of cancellation. With the far end shorted instead, a one-port gives the loop
    impedance directly.

    Skin depth equals the via radius at **19.1 MHz**; at f_sw = 0.286 MHz, δ/r = 8.18. HFSS
    shows R varying by **{fl:.2f} %** between 1 and 5.6 MHz and then rising
    {max(s['R_ohm'] for s in sw)/min(s['R_ohm'] for s in sw):.1f}× by 1 GHz. **No AC correction is
    needed at the switching frequency --- verified rather than assumed.** Measured resistance
    exceeds a 1-D series sum of the same geometry by {em1['crowding_factor_at_lowest_f']:.2f}×
    (1.96× for a second geometry), so bulk-cylinder resistance is not total connection
    resistance; that band is carried as an uncertainty, not a calibration.
    """))

A("## TSV allocation --- three quantities that were one\n")
A(textwrap.dedent("""
Phase 0D-R computed `R_field = R_single / n_required`. That silently makes the via field's
loss proportional to current --- but only because `n_required` is itself proportional to
current. Phase 0E separates `n_required` (capability), `n_allocated` (actually assigned, and
what resistance must use) and `n_available` (geometry), and enforces
`n_req <= n_alloc <= n_avail`. Under a geometric allocation policy the same field gives
`P ~ I^2`, so the apparent linearity is a **design policy, not a law**.

The policy itself is source-backed. June-2026 states it verbatim: *"the number of parallel
VICs per connection is sized based on the connection current and per-via current limit, with
current assumed to be uniformly distributed across the allocated VICs."*

Measured across the same via field, with the LV rail carrying 44.31x the HV rail's current:
"""))
A("| policy | current ratio | TSV field-loss ratio | law |")
A("|---|---:|---:|---|")
A("| `A_min_capability` (June's own) | x44.31 | x46.26 | **P ~ I** (linear) |")
A("| `B_geometric` | x44.31 | x1963.65 | **P ~ I²** (quadratic) |")
A("| `C_area_optimal` | x44.31 | x1963.65 | **P ~ I²** (quadratic) |")
A(textwrap.dedent("""

The quadratic ratio is exactly 44.31² = 1963. The linear behaviour Phase 0D-R reported as if
it were a property of through-silicon vias is a consequence of provisioning the count at the
bare current-capability minimum. It also means the architecture-dependent thickness margin
below is a consequence of that provisioning policy rather than of the LV-TSV architecture
itself: allocating all available vias instead of the minimum cuts ARCH_B's TSV loss from
89.6 mW to 10.6 mW and would raise its thickness margin from 1.46x to roughly 12x.
"""))

A(figure("FIG_0E_BC_allocation_feasibility.png",
         "TSV allocation and the current-capability envelope. ARCH_B is feasible across the "
         "whole source-backed range; only the unsourced 4.8 mA candidate makes it infeasible."))
A("### The per-via limit, and the error it exposes\n")
A("| basis | J (A/m²) | I_max per 707 µm² via | agreement across independent tiers |")
A("|---|---:|---:|---|")
A(f"| June-2026 (conservative) | {cd['june2026']['value']:.1e} | 70.7 mA | pads 1.000e8 vs TSVs 9.366e7 → 6.8 % |")
A(f"| ECTC-2024 (aggressive) | {cd['ectc2024']['value']:.1e} | 282.8 mA | pad 4.000e8 vs TSV 4.027e8 → 0.7 % |")
A("| Phase-0D-R \"33 mA\" | — | 33 mA | **dropped the P&G factor of 2** |")
A("| Phase-0D-R \"4.8 mA\" | — | 4.8 mA | mixed one rail's current with another's allocation |")
A(textwrap.dedent("""

Separating the counts also changes a Phase-0D-R conclusion about thickness. Decomposing the
200 -> 500 um change at the reference point, the vertical penalty in ARCH_A is +2.09 mW
against a 141.21 mW converter saving (a 67.7x margin), but in ARCH_B it is +96.22 mW against
140.08 mW --- a margin of only **1.46x**, consuming 69 % of the benefit, and the package
distribution loss actually *rises* with thickness. Thicker still wins in both architectures,
but Phase 0D-R's conclusion that no architecture-dependent thickness tradeoff exists rested on
a penalty an order of magnitude smaller than the corrected one. The tension is real and close
to binding; it simply does not flip the sign at 240 W.

**ARCH_B is feasible under every source-backed current density.** At the reference point it
needs 849 of 7 148 available vias --- 11.9 % utilisation. It would become infeasible only
below about 1e7 A/m², which is 5-11× below the most conservative value either primary source
implies. The Phase-0D-R infeasibility verdict rested entirely on the one candidate with no
source, and is **withdrawn**.
"""))

if fp_fe and fp_mat:
    A("## The most important mechanical result: footprint survives\n")
    A(textwrap.dedent("""
    Every mechanical footprint result in this project assumed the HVR tile was a homogeneous
    block of `hvr_effective` filling the whole electrical bounding box. The compiler's own area
    rule is a **maximum** over component-layer areas, not a sum --- components are vertically
    stacked and every layer but the largest is only partly filled.
    """))
    A("| j (A/mm²) | A_HVR (mm²) | Σ component area (mm²) | areal fill | E_eff (GPa) | CTE_eff (ppm/K) |")
    A("|---:|---:|---:|---:|---:|---:|")
    for m in sorted(fp_mat, key=lambda r: -float(r["a_hvr_mm2"])):
        A(f"| {float(m['j_target']):.1f} | {float(m['a_hvr_mm2']):.2f} | "
          f"{float(m['component_area_mm2']):.2f} | {float(m['areal_fill']):.4f} | "
          f"{float(m['E_eff_mpa'])/1e3:.1f} | {float(m['cte_eff'])*1e6:.3f} |")
    A(textwrap.dedent("""

    The bounding box spans 2.288× while the actual CTE-mismatched material spans only 1.407×:
    between j = 2.0 and j = 4.0 the box shrinks 42 % and the component area shrinks 3 %. The
    parts do not get smaller, they pack more densely.

    A scaling argument on `E_eff · CTE_eff · A_HVR` predicts the footprint sensitivity weakening
    by 26 %. **The finite-element answer is that it does not weaken at all.**
    """))
    A("| variant | warpage over A = 60 → 137 mm² | span |")
    A("|---|---|---:|")
    for v in ("homogeneous", "composite"):
        s = sorted([r for r in fp_fe if r["variant"] == v],
                   key=lambda r: float(r["A_HVR_total_mm2"]))
        w = [float(r["die_warpage_pv_um"]) for r in s]
        A(f"| {v} | {w[0]:.3f} → {w[-1]:.3f} µm | **{max(w)/min(w):.4f}×** |")
    A(figure("FIG_0E_F_footprint_material.png",
             "Left: the CTE-mismatched material does not scale with the electrical bounding "
             "box. Right: the footprint opposition survives the physical material model."))
    A(textwrap.dedent("""

    The physical material distribution shifts warpage uniformly by about +6 % and changes the
    footprint **sensitivity by 0.06 %**. The reason is that the tile both drives bending through
    CTE mismatch and resists it as a local stiffener; softening it moves those two in opposite
    directions and they nearly cancel. What survives is that the footprint dependence is
    **geometric** --- it is set by how much package area is occupied by a dissimilar inclusion,
    not by that inclusion's moduli. That is what makes it robust to the largest material
    uncertainty in the model.

    **Verdict: FOOTPRINT ETM OPPOSITION ROBUST.**
    """))

if bcb:
    A("## Board restraint changes which response discriminates\n")
    A(textwrap.dedent("""
    Phase 0C showed that a compliant board support suppresses free warpage by roughly twenty
    times, and left the question there. Phase 0E runs the decisive pairs under both boundary
    families and asks the question that actually matters for a design framework: **when the
    package is restrained, which response still separates the candidates?** Interface peel is
    excluded throughout --- it never converged and remains demoted.
    """))
    A("| pair | member | BC-A warpage (µm) | BC-B warpage (µm) | BC-A shear p99 (MPa) | BC-B shear p99 (MPa) |")
    A("|---|---|---:|---:|---:|---:|")
    fv = lambda r, k: float(r[k])
    for pair in sorted({r["pair"] for r in bcb}):
        for mem in sorted({r["member"] for r in bcb if r["pair"] == pair}):
            g = {r["bc"]: r for r in bcb if r["pair"] == pair and r["member"] == mem}
            if len(g) == 2:
                A(f"| {pair} | {mem} | {fv(g['BC_A'],'die_warpage_pv_um'):.4f} | "
                  f"{fv(g['BC_B'],'die_warpage_pv_um'):.4f} | "
                  f"{fv(g['BC_A'],'interface_shear_p99_MPa'):.3f} | "
                  f"{fv(g['BC_B'],'interface_shear_p99_MPa'):.3f} |")
    A(figure("FIG_0E_G_bcb.png",
             "Under board restraint warpage collapses while interface shear grows. The "
             "discriminating response changes, and for footprint the warpage ordering reverses."))
    A(textwrap.dedent("""

    Two things happen at once. Warpage falls by roughly an order of magnitude, and interface
    shear **rises** --- the restraint converts bending into shear at the die attach. For the
    footprint pair the warpage ordering also **reverses**: the larger footprint is worse under
    free warpage and better under restraint. Any board-level design conclusion drawn from the
    BC-A results in this report would therefore be wrong in sign.

    This does not invalidate the free-warpage work, which is a legitimate package-level
    quantity and the one prior thermo-mechanical placement work also reports. It does mean the
    ETM formulation must eventually choose its response deliberately: **free warpage for a
    package-level objective, interface shear for a board-mounted one**, and they do not agree.
    """))

MD.write_text(MD.read_text() + "".join(x if x.endswith("\n") else x + "\n" for x in S))
print(f"appended Phase-0E chapter; now {len(MD.read_text().splitlines())} lines")
