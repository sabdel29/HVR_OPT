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


def _supply_sites(arch: str, cells=None):
    """Supply/return sites, from the REAL centred 0.8 mm BGA lattice in both cases.

    The previous Z1 placement was synthesised by adding (+0.4, +0.4) mm to selected cell
    centres. Those are not lattice positions at all -- is_on_bga_lattice() rejects them
    -- so the Z1 arm of the comparison was built on fabricated coordinates. Both
    architectures now draw from physical_coords, under ONE allocation rule, so that
    placement and cutout effects are not confounded.
    """
    import physical_coords as PCO
    cells = cells or PCO.physical_cell_coordinates()
    ann_sup, ann_ret = PCO.annulus_supply_return()
    n_pairs = len(ann_sup) // 2
    if arch == "Z2":
        return ann_sup, ann_ret, "surviving annulus (cutout removes the interior)"
    legal = PCO.bga_lattice_sites()                      # Z1 has no cutout
    sup, ret = PCO.select_sites(legal, cells, n_pairs)
    return sup, ret, "full centred 0.8 mm lattice, nearest-to-load symmetric pairs"


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
               T_c: float = T_REF_C) -> dict:
    r_sq = sheet_resistance_ohm_sq(t_cu_mm, occupancy, T_c)
    net = SheetNetwork(n_grid, r_sq)
    cells = cell_centres()
    sup, ret, placement = _supply_sites(arch, cells)
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
            "source_placement": placement}


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
