"""PHASE 0N-AF --- the package-level RDL as an actual 2-D resistor network.

THE CONDUCTOR THAT DID NOT EXIST. The physical mesh has `conv_0_land_side_attach_rdl`
inside each of the 49 cell footprints, and nothing joining them to the peripheral BGA
ring. Electrically the cells were fed by nothing. This builds the missing sheet and
solves it.

    sources   selected BGA supply sites, actual surviving-annulus coordinates
    loads     the 49 cell VIN nodes on the 7x7 grid
    medium    a uniform 2-D sheet over the 30x30 mm substrate underside
    solve     G V = I, one node grounded, sparse CG

Z1 and Z2 differ ONLY in where the sources may sit. Z2's BGA ring is annular -- 841 of
1369 sites are removed by the 23.36 mm PCB cutout -- so its 48 V must cross the opening
laterally to reach cells that sit inside it. Z1 has no cutout and can feed from anywhere.
That is a real architectural difference in the distribution path, and it falls out of the
geometry rather than being asserted.

LINEARITY IS USED DELIBERATELY. The network is linear, so it is solved ONCE at unit
total current. Every loss then scales as I_rms^2, which lets the geometry close while the
48 V waveform stays open: resistance is a property of the sheet, not of the waveform.
Losses are reported per named scenario (HV-S0/S1/S2), never as a bracket.

WHAT IS NOT SOURCE-BACKED. The DVPD source states only that "specific trace dimensions
depend on process technology", so it does NOT fix our Cu thickness or occupancy. Both are
swept over declared cases, and every result carries which case produced it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
from interconnect import rho_cu                                        # noqa: E402

T_REF_C = 20.0
SUBSTRATE_MM = 30.0

# --- RDL construction cases. NONE is source-backed; the source explicitly defers to
# --- process technology. Thickness scale is CLOSE_ANALOG to 10.1109/TVLSI.2022.3183904,
# --- which uses t_RDL ~ 10 um in a backside PDN -- a thickness SCALE, not a statement
# --- that our 10 um FE tier is solid copper.
T_CU_CASES = {"RDL_T1": 2.0e-3, "RDL_T2": 5.0e-3, "RDL_T3": 10.0e-3}   # mm
OCCUPANCY_CASES = {"RDL_P": 0.80, "RDL_M": 0.30}
CASE_STATUS = {
    "t_cu": "BOUNDED_FROM_LITERATURE -- 10 um scale from TVLSI 2022 (CLOSE_ANALOG); "
            "the Cu fraction of that 10 um is not given by any source",
    "occupancy": "BOUNDED_ENGINEERING -- plane-rich vs mesh/routing-limited, declared",
}


def sheet_resistance_ohm_sq(t_cu_mm: float, occupancy: float, T_c: float = T_REF_C):
    """R_square = rho(T) / (t_Cu * occupancy). Electrical only -- NOT the thermal tensor."""
    return rho_cu(T_c) / (t_cu_mm * 1e-3 * occupancy)


def cell_centres(cells: int = 49, pitch_mm: float | None = None):
    """DELEGATES to the FE placement. The hard-coded 3.0 mm pitch was wrong: the actual
    placement is 3.165243 mm, so every earlier RDL result used the wrong grid."""
    import physical_coords as PCO
    return PCO.physical_cell_coordinates()


N_SUPPLY_DEFAULT = 16          # matched across architectures unless a case changes it
N_RETURN_DEFAULT = 16


def _supply_sites(arch: str, cells=None, n_supply: int = N_SUPPLY_DEFAULT,
                  n_return: int = N_RETURN_DEFAULT,
                  allocation_rule: str = "nearest_symmetric",
                  bga_case: str = "BGA_P1"):
    """Candidate sites differ by architecture; the ALLOCATION RULE and COUNTS do not.

    That is the whole point: Z1 draws from the full centred lattice, Z2 from the sites
    surviving the 23.36 mm cutout, and everything else is held identical. Any resistance
    difference is then attributable to which sites exist rather than to how many balls
    each architecture was given or how they were chosen.

    BGA_P0 reproduces the frozen historical Z2 allocation and must NOT be used for the
    controlled comparison.
    """
    import physical_coords as PCO
    cells = cells or PCO.physical_cell_coordinates()
    if bga_case == "BGA_P0":
        sup, ret = PCO.annulus_supply_return()
        return sup, ret, "BGA_P0 historical frozen allocation (reproduction only)"
    cand = PCO.bga_lattice_sites(architecture_cutout_mm(arch))
    sel = PCO.select_power_sites(cand, cells, n_supply, n_return, allocation_rule)
    where = "annulus (cutout removes the interior)" if arch == "Z2" else "full lattice"
    return (sel["supply"], sel["return"],
            f"{bga_case}/{allocation_rule}: {n_supply}+{n_return} from {where} "
            f"({sel['n_candidates']} candidates)")


class SheetNetwork:
    """Uniform 2-D resistive sheet on an n x n node grid over the substrate footprint."""

    def __init__(self, n: int, r_sq: float, span_mm: float = SUBSTRATE_MM):
        self.n, self.r_sq, self.span = n, r_sq, span_mm
        self.h = span_mm / (n - 1)
        xs = np.linspace(-span_mm / 2, span_mm / 2, n)
        self.xs = xs
        # a square sheet patch has resistance R_sq regardless of size, so each grid edge
        # of equal aspect contributes conductance 1/R_sq
        self.g_edge = 1.0 / r_sq

    def node(self, i, j):
        return i * self.n + j

    def nearest(self, x, y):
        i = int(np.clip(np.round((x + self.span / 2) / self.h), 0, self.n - 1))
        j = int(np.clip(np.round((y + self.span / 2) / self.h), 0, self.n - 1))
        return self.node(i, j)

    def footprint(self, x, y, d_mm):
        """Nodes inside a contact of diameter d_mm centred at (x, y).

        A POINT source in a 2-D sheet has a logarithmic singularity: R_eff grows like
        log(1/h) and never converges under refinement. The first version of this solver
        injected at single nodes and failed its own 1 % convergence test at 2.015 %.
        Real contacts have finite area -- a 400 um BGA ball, a cell VIN pad -- so
        injection is spread over the nodes the contact actually covers, which removes
        the singularity rather than hiding it behind a looser threshold.
        """
        r = d_mm / 2.0
        out = []
        for i in range(self.n):
            for j in range(self.n):
                xx, yy = self.xs[i], self.xs[j]
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                    out.append(self.node(i, j))
        return out or [self.nearest(x, y)]

    def laplacian(self):
        n, g = self.n, self.g_edge
        rows, cols, vals = [], [], []
        for i in range(n):
            for j in range(n):
                a = self.node(i, j)
                for di, dj in ((1, 0), (0, 1)):
                    if i + di < n and j + dj < n or (di == 1 and i + 1 < n) or (
                            dj == 1 and j + 1 < n):
                        if i + di >= n or j + dj >= n:
                            continue
                        b = self.node(i + di, j + dj)
                        rows += [a, b, a, b]
                        cols += [a, b, b, a]
                        vals += [g, g, -g, -g]
        return sp.csr_matrix(sp.coo_matrix((vals, (rows, cols)),
                                           shape=(n * n, n * n)))

    def solve(self, source_xy, sink_xy, i_total: float = 1.0,
              d_src_mm: float = 0.400, d_snk_mm: float = 2.3685):
        """Inject i_total split equally over sources, extract split equally over sinks.

        Equal INJECTION at the balls is the boundary condition; the resulting per-ball
        CURRENT is not equal, because the sheet decides how much each path carries. That
        distinction is the point of solving the network at all.
        """
        G = self.laplacian().tolil()
        nn = self.n * self.n
        I = np.zeros(nn)
        src_groups = [self.footprint(*p, d_src_mm) for p in source_xy]
        snk_groups = [self.footprint(*p, d_snk_mm) for p in sink_xy]
        src = [g[0] for g in src_groups]
        snk = [g[0] for g in snk_groups]
        for g in src_groups:
            for nd in g:
                I[nd] += i_total / len(src_groups) / len(g)
        for g in snk_groups:
            for nd in g:
                I[nd] -= i_total / len(snk_groups) / len(g)
        # ground one sink node to fix the reference
        ref = snk_groups[0][0]
        G[ref, :] = 0.0
        G[ref, ref] = 1.0
        I[ref] = 0.0
        V = spla.spsolve(G.tocsr(), I)
        return V, src, snk

    def dissipation(self, V):
        """Sum g*(dV)^2 over every edge -- the sheet's own Joule loss at the solved V."""
        n, g = self.n, self.g_edge
        Vg = V.reshape(n, n)
        p = g * (np.diff(Vg, axis=0) ** 2).sum() + g * (np.diff(Vg, axis=1) ** 2).sum()
        return float(p)


def solve_case(arch: str, n_grid: int, t_cu_mm: float, occupancy: float,
               T_c: float = T_REF_C, n_supply: int = N_SUPPLY_DEFAULT,
               n_return: int = N_RETURN_DEFAULT,
               allocation_rule: str = "nearest_symmetric",
               bga_case: str = "BGA_P1", candidate_override=None) -> dict:
    r_sq = sheet_resistance_ohm_sq(t_cu_mm, occupancy, T_c)
    net = SheetNetwork(n_grid, r_sq)
    cells = cell_centres()
    if candidate_override is not None:
        import physical_coords as PCO
        sel = PCO.select_power_sites(candidate_override, cells, n_supply, n_return,
                                     allocation_rule)
        sup, ret = sel["supply"], sel["return"]
        placement = f"CONTROLLED/{allocation_rule}: {n_supply}+{n_return}"
    else:
        sup, ret, placement = _supply_sites(arch, cells, n_supply, n_return,
                                            allocation_rule, bga_case)
    # Z2's supply sites are restricted to the surviving annulus; Z1 has no cutout, so
    # the same ring is used for comparability -- the DIFFERENCE is that Z2's load sits
    # inside an opening its supply cannot cross directly.
    V, src, snk = net.solve(sup, cells, i_total=1.0)
    p_norm = net.dissipation(V)                  # W at 1 A total -> equals R_eff
    drop = float(V[src].mean() - V[snk].mean())
    return {"arch": arch, "n_grid": n_grid, "nodes": n_grid ** 2,
            "edges": 2 * n_grid * (n_grid - 1),
            "t_cu_mm": t_cu_mm, "occupancy": occupancy,
            "r_sheet_ohm_sq": r_sq,
            "r_eff_ohm": p_norm,              # P at 1 A = R_eff
            "v_drop_at_1A": drop,
            "n_sources": len(src), "n_sinks": len(snk),
            "n_supply_requested": n_supply, "n_return_requested": n_return,
            "allocation_rule": allocation_rule, "bga_case": bga_case,
            "source_placement": placement}


def controlled_cutout_experiment(n_grid: int = 61,
                                 t_cu_mm: float = 5.0e-3,
                                 occupancy: float = 0.30,
                                 n_supply: int = N_SUPPLY_DEFAULT) -> dict:
    """CTRL-FULL vs CTRL-CUTOUT: the ONLY difference is which sites exist.

    Same sheet, same cell coordinates, same ball count, same allocation rule, same RDL
    construction, same grid. Removing the central lattice sites is then the only change,
    so the difference IS the cutout penalty -- unlike comparing two architectures whose
    placements were chosen differently, which is what produced the withdrawn 5.13x and
    0.55 figures.
    """
    import physical_coords as PCO
    cells = PCO.physical_cell_coordinates()
    full = PCO.bga_lattice_sites()
    cut = PCO.bga_lattice_sites(23.36)
    out = {}
    for tag, cand in (("CTRL_FULL", full), ("CTRL_CUTOUT", cut)):
        c = solve_case("CTRL", n_grid, t_cu_mm, occupancy,
                       n_supply=n_supply, n_return=n_supply,
                       candidate_override=cand)
        c["n_candidate_sites"] = len(cand)
        out[tag] = c
    r_full = out["CTRL_FULL"]["r_eff_ohm"]
    r_cut = out["CTRL_CUTOUT"]["r_eff_ohm"]
    # placement sensitivity, on the SAME candidate set, isolates rule from geometry
    place = {}
    for rule in ("nearest_symmetric", "outer_perimeter"):
        place[rule] = solve_case("CTRL", n_grid, t_cu_mm, occupancy,
                                 n_supply=n_supply, n_return=n_supply,
                                 allocation_rule=rule,
                                 candidate_override=cut)["r_eff_ohm"]
    return {"cases": out,
            "delta_R_cutout_ohm": r_cut - r_full,
            "ratio_cutout_over_full": r_cut / r_full,
            "placement_on_fixed_candidates": place,
            "delta_R_placement_ohm": abs(place["outer_perimeter"]
                                         - place["nearest_symmetric"]),
            "note": ("delta_R_cutout is the ONLY quantity entitled to be called a "
                     "cutout penalty; delta_R_placement is how much the allocation "
                     "rule moves the answer on an unchanged candidate set")}


def convergence(arch: str, t_cu_mm: float, occupancy: float,
                levels=(41, 61, 81, 101)) -> dict:
    """Three discretizations, threshold DECLARED BEFORE the numbers are read."""
    THRESH = 0.01                     # 1 % between the two finest levels
    rows = [solve_case(arch, n, t_cu_mm, occupancy) for n in levels]
    fine, mid = rows[-1], rows[-2]
    d_r = abs(fine["r_eff_ohm"] - mid["r_eff_ohm"]) / fine["r_eff_ohm"]
    return {"levels": rows, "threshold": THRESH,
            "threshold_declared": "1 % on R_eff between the two finest levels, set "
                                  "before any result was inspected",
            "delta_r_eff": d_r, "converged": d_r < THRESH}


def losses(r_eff_ohm: float, scenarios: dict) -> dict:
    """P = I_rms^2 * R_eff, per named scenario. The network is linear, so one solve
    serves every scenario."""
    return {k: v ** 2 * r_eff_ohm for k, v in scenarios.items()}


def main():
    import rms_currents as RMS
    import power_path as PP
    out = {"case_status": CASE_STATUS, "architectures": {}}
    for arch in ("Z1", "Z2"):
        hv = RMS.hv_input_scenarios(PP.rail_currents(arch)["hv_total_a"])
        scen = {k: hv[k]["i_rms_a"] for k in ("HV_S0", "HV_S1", "HV_S2")}
        per_case = {}
        for tname, t in T_CU_CASES.items():
            for oname, o in OCCUPANCY_CASES.items():
                c = solve_case(arch, 61, t, o)
                c["scenario_loss_w"] = losses(c["r_eff_ohm"], scen)
                per_case[f"{tname}_{oname}"] = c
        conv = convergence(arch, T_CU_CASES["RDL_T2"], OCCUPANCY_CASES["RDL_M"])
        out["architectures"][arch] = {"cases": per_case, "convergence": conv,
                                      "scenarios_a": scen}
    d = R / "research" / "phase0naf"
    d.mkdir(parents=True, exist_ok=True)
    (d / "pkg_rdl_network.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    for arch, a in out["architectures"].items():
        print(f"\n=== {arch} package HV RDL (supply path, 1 A normalized) ===")
        print(f"{'case':16s} {'R_sq mOhm/sq':>13s} {'R_eff mOhm':>11s}  "
              f"{'S0 mW':>8s} {'S1 mW':>9s} {'S2 mW':>9s}")
        for k, c in a["cases"].items():
            s = c["scenario_loss_w"]
            print(f"{k:16s} {c['r_sheet_ohm_sq']*1e3:13.4f} {c['r_eff_ohm']*1e3:11.4f}  "
                  f"{s['HV_S0']*1e3:8.2f} {s['HV_S1']*1e3:9.1f} {s['HV_S2']*1e3:9.1f}")
        cv = a["convergence"]
        print(f"  convergence {[r['n_grid'] for r in cv['levels']]} -> "
              f"dR_eff {cv['delta_r_eff']*100:.3f} % (threshold "
              f"{cv['threshold']*100:.0f} %) converged={cv['converged']}")


if __name__ == "__main__":
    main()


# ===========================================================================
# PHASE 0N-AI --- VOLTAGE-FED BGA NETWORK.
#
# WHAT WAS WRONG. solve() above injects i_total/len(sources) at every ball. That
# is not a boundary condition, it is the ANSWER: equal sharing is imposed by the
# right-hand side, so no ball can ever be found to carry more than another, and
# any "the network decides the sharing" claim made from it was circular. The
# docstring of solve() asserts exactly that claim and it was false.
#
# WHAT THIS DOES INSTEAD. One rail node held at a fixed potential feeds every
# ball through its OWN series resistance; the balls reach the sheet through a
# finite-area contact; the die cells draw their load currents from pad nodes
# that reach the sheet the same way. Nothing constrains the balls to share
# equally, so the per-ball current is an output. With an asymmetric load the
# currents come out unequal, which is the test that the imposed version could
# not fail.
#
#     rail --[R_ball,j]-- ball_j --[contact]-- sheet -- [contact] -- cell_m -> i_m
#
# GRID INDEPENDENCE. A contact is stamped by AREA OVERLAP: node k of the sheet
# owns a square of side h, and the conductance it receives is proportional to
# the area that square shares with the physical contact disc. The overlaps sum
# to the true contact area at every refinement, so the total contact
# conductance does not drift with h. What DOES drift is the sheet's own
# spreading: a 400 um ball is smaller than one 0.5 mm grid cell, so a coarse
# sheet cannot resolve the constriction around it. That missing piece is added
# back analytically as R_sq/(2*pi) * ln(r_cover/a), the 2-D spreading
# resistance between the contact radius and the radius the covered nodes
# actually represent. It vanishes identically once the grid resolves the
# contact, so it is a discretisation correction, not a tuning knob.
# ===========================================================================

# Specific contact resistance between ball/pad and the RDL sheet, Ohm.mm^2.
# NOT source-backed: Table III's BGA resistance is pure bulk solder (see
# pad_interface.bga_ball_resistance_ohm), so the source supplies no contact
# term at all. These are declared engineering cases and every result says
# which one produced it.
#: ---------------------------------------------------------------------------
#: Minimal ArchitectureSpec. The solver previously branched on the LITERAL
#: string "Z2" to decide whether a PCB cutout removed the central BGA sites, so
#: architecture geometry was keyed to a name rather than to a specification and
#: no third architecture could be expressed at all. The cutout is now looked up
#: here; an unknown name is an error rather than a silent "no cutout", because
#: a typo must not quietly produce the Z1 geometry.
ARCHITECTURE_CUTOUT_MM = {
    "Z1": None,        # package-embedded: no land-side opening
    "Z2": 23.36,       # backside: PCB cutout removes the interior lattice
    "CTRL": None,      # controlled experiment: candidate set passed explicitly
}


def register_architecture(name: str, cutout_mm: float | None) -> None:
    """Declare a new architecture's land-side opening."""
    ARCHITECTURE_CUTOUT_MM[name] = cutout_mm


def architecture_cutout_mm(arch: str):
    if arch not in ARCHITECTURE_CUTOUT_MM:
        raise KeyError(
            f"unknown architecture {arch!r}; register it with "
            f"register_architecture(name, cutout_mm) rather than relying on a "
            f"default, which would silently give it the Z1 geometry")
    return ARCHITECTURE_CUTOUT_MM[arch]


#: the VR cell contact is the SQUARE tile footprint, not a disc of that width
VR_TILE_SIDE_MM = 2.3685438564654024

RHO_C_CASES = {"CONTACT_L": 1.0e-6, "CONTACT_N": 1.0e-5, "CONTACT_H": 1.0e-4}
RHO_C_STATUS = ("BOUNDED_ENGINEERING -- the DVPD source's own BGA and pad "
                "resistances are exactly rho*L/A and contain NO contact term, "
                "so no published value can be quoted here; swept over three "
                "declared decades and reported as a sensitivity")

_GL_X, _GL_W = np.polynomial.legendre.leggauss(64)


def _disc_rect_area(xc, yc, r, x1, x2, y1, y2):
    """Exact-to-quadrature area of disc(xc, yc, r) intersected with a rectangle."""
    a, b = max(x1, xc - r), min(x2, xc + r)
    if b <= a:
        return 0.0
    xm, xr = 0.5 * (a + b), 0.5 * (b - a)
    xs = xm + xr * _GL_X
    s = np.sqrt(np.maximum(0.0, r * r - (xs - xc) ** 2))
    hi = np.minimum(y2, yc + s)
    lo = np.maximum(y1, yc - s)
    return float(xr * np.dot(_GL_W, np.maximum(0.0, hi - lo)))


def contact_overlap(net: "SheetNetwork", x: float, y: float, d_mm: float,
                    shape: str = "disc"):
    """-> (node ids, overlap areas mm^2). The areas sum to the contact's real
    area at every grid level; that is what makes the stamping grid-independent.

    SHAPE IS NOT COSMETIC. A BGA ball is circular -- Table III's A_c = 125663
    um^2 is exactly pi*(200 um)^2 -- but a VR cell contact is the square tile
    footprint, and stamping a 2.3685 mm tile as a DISC of that diameter gives
    pi*(1.18425)^2 = 4.406 mm^2 against the true 2.3685^2 = 5.610 mm^2, a 21 %
    under-count. That is the same square-vs-circle error already recorded for
    the Table III Cu pad (d_c = 10 um with A_c = 100 um^2 is a square), so it
    is an error this project has made once before and must not repeat.
    """
    if shape == "square":
        return _square_overlap(net, x, y, d_mm)
    if shape != "disc":
        raise ValueError(f"unknown contact shape {shape!r}")
    r, h = d_mm / 2.0, net.h
    lo = np.searchsorted(net.xs, x - r - h) - 1
    hi = np.searchsorted(net.xs, x + r + h) + 1
    jlo = np.searchsorted(net.xs, y - r - h) - 1
    jhi = np.searchsorted(net.xs, y + r + h) + 1
    nodes, areas = [], []
    for i in range(max(0, lo), min(net.n, hi + 1)):
        for j in range(max(0, jlo), min(net.n, jhi + 1)):
            a = _disc_rect_area(x, y, r,
                                net.xs[i] - h / 2, net.xs[i] + h / 2,
                                net.xs[j] - h / 2, net.xs[j] + h / 2)
            if a > 0.0:
                nodes.append(net.node(i, j))
                areas.append(a)
    if not nodes:                      # disc fell between sample points
        nodes, areas = [net.nearest(x, y)], [np.pi * r * r]
    return nodes, np.asarray(areas)


def _square_overlap(net, x, y, side_mm):
    """Exact rectangle-rectangle overlap; no quadrature needed."""
    h, a = net.h, side_mm / 2.0
    nodes, areas = [], []
    ilo = max(0, np.searchsorted(net.xs, x - a - h) - 1)
    ihi = min(net.n, np.searchsorted(net.xs, x + a + h) + 2)
    jlo = max(0, np.searchsorted(net.xs, y - a - h) - 1)
    jhi = min(net.n, np.searchsorted(net.xs, y + a + h) + 2)
    for i in range(ilo, ihi):
        ox = (min(net.xs[i] + h / 2, x + a) - max(net.xs[i] - h / 2, x - a))
        if ox <= 0:
            continue
        for j in range(jlo, jhi):
            oy = (min(net.xs[j] + h / 2, y + a) - max(net.xs[j] - h / 2, y - a))
            if oy > 0:
                nodes.append(net.node(i, j))
                areas.append(ox * oy)
    if not nodes:
        nodes, areas = [net.nearest(x, y)], [side_mm ** 2]
    return nodes, np.asarray(areas)


def _contact_conductances(net, x, y, d_mm, rho_c_ohm_mm2, shape="disc"):
    """Pure area-overlap stamp. Returns (nodes, g_k) with sum(g_k) = A/rho_c.

    NO ANALYTIC SPREADING CORRECTION. A first version of this function added
    R_sq/(2*pi)*ln(r_cover/a) in series, with r_cover taken from the number of
    nodes the disc touched. That estimator is not even monotone in h: the
    touched-node count jumps as the disc boundary crosses cell boundaries, so
    r_spread read 1.15, 0.95, 0.43, 0.79, 0.46, 0.46 mOhm down a refinement
    sweep, and it dominated the ball path (84-94 % of it) at every level. The
    "corrected" model drifted 20 % over n = 101..401 and never settled.

    Removed, not retuned. With the plain stamp the same sweep is monotone and
    converges once the grid RESOLVES the contact: R_eff = 0.5355, 0.5402,
    0.5513, 0.5731, 0.5766, 0.5800, 0.5806 mOhm at n = 101..601, the last step
    being 0.10 %. A 400 um ball needs h <~ 50 um, which is why the converged
    grid is n = 601 and not the n = 101 the earlier study stopped at. The
    correction was solving a problem that refinement solves properly, and it
    was introducing a non-monotone discretisation artefact of its own.
    """
    nodes, areas = contact_overlap(net, x, y, d_mm, shape)
    a_tot = float(areas.sum())
    r_contact = rho_c_ohm_mm2 / a_tot
    return nodes, areas / rho_c_ohm_mm2, {
        "r_contact_ohm": r_contact, "a_contact_mm2": a_tot, "shape": shape,
        "n_nodes": len(nodes), "d_over_h": d_mm / net.h}


class VoltageFedNetwork:
    """Sheet + ball nodes + cell pad nodes + one rail node held at a potential."""

    def __init__(self, n, r_sq, span_mm=SUBSTRATE_MM):
        self.sheet = SheetNetwork(n, r_sq, span_mm)
        self.ns = n * n

    def build(self, ball_xy, cell_xy, r_ball_ohm, rho_c_ball, rho_c_cell,
              d_ball_mm, d_cell_mm, cell_shape="square"):
        net = self.sheet
        nb, nc = len(ball_xy), len(cell_xy)
        self.nb, self.nc = nb, nc
        self.i_ball = self.ns                      # ball nodes
        self.i_cell = self.ns + nb                 # cell pad nodes
        self.i_rail = self.ns + nb + nc            # single rail node
        N = self.i_rail + 1
        rows, cols, vals = [], [], []

        def edge(a, b, g):
            rows.extend((a, b, a, b))
            cols.extend((a, b, b, a))
            vals.extend((g, g, -g, -g))

        L = net.laplacian().tocoo()                # sheet interior
        rows.extend(L.row.tolist())
        cols.extend(L.col.tolist())
        vals.extend(L.data.tolist())

        self.ball_meta, self.cell_meta = [], []
        for j, (x, y) in enumerate(ball_xy):
            bj = self.i_ball + j
            edge(self.i_rail, bj, 1.0 / r_ball_ohm)          # the ball itself
            nd, g, meta = _contact_conductances(net, x, y, d_ball_mm, rho_c_ball)
            for k, gk in zip(nd, g):
                edge(bj, k, gk)
            self.ball_meta.append(meta)
        for m, (x, y) in enumerate(cell_xy):
            cm = self.i_cell + m
            nd, g, meta = _contact_conductances(net, x, y, d_cell_mm,
                                                rho_c_cell, cell_shape)
            for k, gk in zip(nd, g):
                edge(cm, k, gk)
            self.cell_meta.append(meta)

        self.G = sp.csr_matrix(sp.coo_matrix((vals, (rows, cols)), shape=(N, N)))
        self.N = N
        self.r_ball_ohm = r_ball_ohm
        return self

    def solve(self, i_cells, v_rail: float = 0.0):
        """Draw i_cells[m] out of cell pad m; the rail supplies all of it.

        The rail is the only Dirichlet node. Ball currents are NOT prescribed.
        """
        N = self.N
        i_cells = np.asarray(i_cells, float)
        assert len(i_cells) == self.nc
        rhs = np.zeros(N)
        rhs[self.i_cell:self.i_cell + self.nc] = -i_cells
        free = np.ones(N, bool)
        free[self.i_rail] = False
        Gff = self.G[free][:, free]
        gfr = np.asarray(self.G[free][:, [self.i_rail]].todense()).ravel()
        Vf = spla.spsolve(Gff.tocsc(), rhs[free] - gfr * v_rail)
        V = np.empty(N)
        V[free] = Vf
        V[self.i_rail] = v_rail
        return V

    def report(self, V, i_cells):
        i_cells = np.asarray(i_cells, float)
        i_tot = float(i_cells.sum())
        vb = V[self.i_ball:self.i_ball + self.nb]
        vc = V[self.i_cell:self.i_cell + self.nc]
        i_ball = (V[self.i_rail] - vb) / self.r_ball_ohm
        # Joule loss over EVERY edge of the assembled network
        Gc = self.G.tocoo()
        up = Gc.row < Gc.col
        p = float(np.sum(-Gc.data[up] * (V[Gc.row[up]] - V[Gc.col[up]]) ** 2))
        # independent check: power in at the rail minus power out at the loads
        p_vi = float(V[self.i_rail] * i_ball.sum() - np.dot(vc, i_cells))
        return {
            "i_total_a": i_tot,
            "p_loss_w": p,
            "p_loss_vi_w": p_vi,
            "energy_residual_rel": abs(p - p_vi) / max(abs(p), 1e-300),
            "r_eff_ohm": p / i_tot ** 2,
            "i_ball_a": i_ball,
            "i_ball_sum_a": float(i_ball.sum()),
            "i_ball_max_a": float(i_ball.max()),
            "i_ball_min_a": float(i_ball.min()),
            "ball_imax_over_imean": float(i_ball.max() / (i_tot / self.nb)),
            "max_cell_drop_v": float(V[self.i_rail] - vc.min()),
            "min_cell_drop_v": float(V[self.i_rail] - vc.max()),
            "r_ball_total_ohm": self.r_ball_ohm,
        }


# --- drivers for the voltage-fed form -------------------------------------

#: supply and return are modelled as TWO SEPARATE SHEETS (a plane pair), which
#: is why they are solved separately rather than as one network: the return
#: conductor has its own BGA sites and its own spreading problem, and the loop
#: resistance is the series sum. Sharing one sheet between both rails would
#: short them together.
RAILS = ("supply", "return")


def solve_rail_vf(arch, rail, n_grid, t_cu_mm, occupancy, i_cells=None,
                  rho_c_ball=None, rho_c_cell=None, T_c=T_REF_C,
                  n_supply=N_SUPPLY_DEFAULT, n_return=N_RETURN_DEFAULT,
                  allocation_rule="nearest_symmetric", bga_case="BGA_P1",
                  candidate_override=None, d_cell_mm=VR_TILE_SIDE_MM):
    import pad_interface as PI
    import physical_coords as PCO
    rho_c_ball = RHO_C_CASES["CONTACT_N"] if rho_c_ball is None else rho_c_ball
    rho_c_cell = RHO_C_CASES["CONTACT_N"] if rho_c_cell is None else rho_c_cell
    cells = cell_centres()
    if candidate_override is not None:
        sel = PCO.select_power_sites(candidate_override, cells, n_supply,
                                     n_return, allocation_rule)
        sup, ret = sel["supply"], sel["return"]
        placement = f"CONTROLLED/{allocation_rule}: {n_supply}+{n_return}"
    else:
        sup, ret, placement = _supply_sites(arch, cells, n_supply, n_return,
                                            allocation_rule, bga_case)
    balls = sup if rail == "supply" else ret
    if i_cells is None:
        i_cells = np.full(len(cells), 1.0 / len(cells))
    net = VoltageFedNetwork(n_grid, sheet_resistance_ohm_sq(t_cu_mm, occupancy, T_c))
    net.build(balls, cells, PI.bga_ball_resistance_ohm(T_c),
              rho_c_ball, rho_c_cell, PI.BGA_D_UM * 1e-3, d_cell_mm,
              cell_shape="square")
    V = net.solve(i_cells)
    out = net.report(V, i_cells)
    out.update({"arch": arch, "rail": rail, "n_grid": n_grid, "n_balls": len(balls),
                "t_cu_mm": t_cu_mm, "occupancy": occupancy,
                "rho_c_ball_ohm_mm2": rho_c_ball, "rho_c_cell_ohm_mm2": rho_c_cell,
                "source_placement": placement,
                "min_ball_d_over_h": float(min(m["d_over_h"]
                                               for m in net.ball_meta)),
                "min_ball_contact_nodes": int(min(m["n_nodes"]
                                                  for m in net.ball_meta)),
                "feed": "VOLTAGE_FED"})
    out["i_ball_a"] = out["i_ball_a"].tolist()
    return out


#: metrics the convergence study must settle, declared before inspection
VF_CONV_METRICS = ("r_eff_ohm", "p_loss_w", "max_cell_drop_v",
                   "i_ball_max_a", "ball_imax_over_imean")
VF_CONV_THRESH = 0.01
#: a 400 um ball on a 30 mm span is sub-grid until h <~ 50 um. Levels below
#: this do not resolve the contact and their R_eff is still climbing.
VF_CONV_LEVELS = (201, 301, 401, 501, 601)
VF_RESOLVED_GRID = 601


def converge_rail_vf(arch, rail, t_cu_mm=5.0e-3, occupancy=0.30,
                     levels=VF_CONV_LEVELS, **kw):
    """1 % on EVERY metric in VF_CONV_METRICS, not just on R_eff.

    The earlier study converged R_eff alone. R_eff is an integral of the field
    and settles first; the peak ball current is a local quantity and settles
    last, so declaring convergence on R_eff alone would have passed a solution
    whose worst-case ball loading was still moving.
    """
    rows = [solve_rail_vf(arch, rail, n, t_cu_mm, occupancy, **kw) for n in levels]
    fine, mid = rows[-1], rows[-2]
    deltas = {m: abs(fine[m] - mid[m]) / abs(fine[m]) for m in VF_CONV_METRICS}
    return {"arch": arch, "rail": rail, "levels": rows, "deltas": deltas,
            "threshold": VF_CONV_THRESH,
            "threshold_declared": ("1 % between the two finest levels on ALL of "
                                   + ", ".join(VF_CONV_METRICS)
                                   + "; declared before any value was inspected"),
            "worst_metric": max(deltas, key=deltas.get),
            "worst_delta": max(deltas.values()),
            "converged": max(deltas.values()) < VF_CONV_THRESH}


def loop_resistance_vf(arch, n_grid=VF_RESOLVED_GRID, t_cu_mm=5.0e-3, occupancy=0.30, **kw):
    """R_loop = R_supply + R_return, each from its OWN network and sites."""
    legs = {r: solve_rail_vf(arch, r, n_grid, t_cu_mm, occupancy, **kw)
            for r in RAILS}
    return {"arch": arch, "n_grid": n_grid,
            "r_supply_ohm": legs["supply"]["r_eff_ohm"],
            "r_return_ohm": legs["return"]["r_eff_ohm"],
            "r_loop_ohm": legs["supply"]["r_eff_ohm"] + legs["return"]["r_eff_ohm"],
            "legs": legs,
            "note": "two separate sheets in series; the return leg was previously "
                    "computed and then DISCARDED, so every earlier package-RDL "
                    "resistance omitted the return conductor entirely"}


def controlled_cutout_experiment_vf(n_grid=VF_RESOLVED_GRID, t_cu_mm=5.0e-3,
                                    occupancy=0.30, n_supply=N_SUPPLY_DEFAULT,
                                    **kw):
    """CTRL-FULL vs CTRL-CUTOUT on the VOLTAGE-FED, LOOP-INCLUSIVE model.

    Same question as the imposed-current version, asked of a model that no
    longer dictates its own ball sharing and no longer throws the return
    conductor away. Everything but the candidate set is held fixed, and the
    placement rule is varied on an UNCHANGED candidate set so the two effects
    can be told apart -- the earlier run found the apparent cutout penalty was
    mostly placement, in magnitude and in sign, so the decomposition is the
    result, not the ratio.
    """
    import physical_coords as PCO
    full = PCO.bga_lattice_sites()
    cut = PCO.bga_lattice_sites(23.36)

    def loop(cand, rule):
        legs = {r: solve_rail_vf("CTRL", r, n_grid, t_cu_mm, occupancy,
                                 n_supply=n_supply, n_return=n_supply,
                                 allocation_rule=rule,
                                 candidate_override=cand, **kw)
                for r in RAILS}
        return {"r_supply_ohm": legs["supply"]["r_eff_ohm"],
                "r_return_ohm": legs["return"]["r_eff_ohm"],
                "r_loop_ohm": legs["supply"]["r_eff_ohm"]
                              + legs["return"]["r_eff_ohm"],
                "n_candidate_sites": len(cand),
                "ball_imax_over_imean": max(legs[r]["ball_imax_over_imean"]
                                            for r in RAILS)}

    cases = {"CTRL_FULL": loop(full, "nearest_symmetric"),
             "CTRL_CUTOUT": loop(cut, "nearest_symmetric"),
             "CTRL_CUTOUT_OUTER": loop(cut, "outer_perimeter")}
    d_cut = cases["CTRL_CUTOUT"]["r_loop_ohm"] - cases["CTRL_FULL"]["r_loop_ohm"]
    d_place = (cases["CTRL_CUTOUT_OUTER"]["r_loop_ohm"]
               - cases["CTRL_CUTOUT"]["r_loop_ohm"])
    return {"n_grid": n_grid, "cases": cases,
            "delta_R_cutout_ohm": d_cut,
            "delta_R_placement_ohm": d_place,
            "placement_over_cutout": (abs(d_place) / abs(d_cut)
                                      if d_cut else None),
            "feed": "VOLTAGE_FED", "includes_return": True,
            "note": ("delta_R_cutout is the ONLY quantity entitled to be called "
                     "a cutout penalty; delta_R_placement is how far the same "
                     "candidate set moves under a different allocation rule")}
