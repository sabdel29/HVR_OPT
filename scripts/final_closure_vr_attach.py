"""VR-to-substrate attach density: the B1 input geom.vr_attach_density.

The direct-fed Z2 hands its 1 V output to the package substrate through an array of Cu-pillar
+ solder-cap bumps embedded in underfill, one VDD/GND checkerboard over each regulator cell.
The production array is the Au et al. ECTC 2016 construction (CLOSE_ANALOG). Its density is a
geometry choice with no single defensible value, so it is bracketed by two PUBLISHED
constructions, never by an invented "half density":

  dense   15 um pillars at 30 um pitch   Au et al., ECTC 2016, 10.1109/ECTC.2016.127
  sparse  30 um bumps at 80 um pitch     Na et al., Electronics 12(1):144, 10.3390/electronics12010144
          (30 um diameter + 50 um space)

Both endpoints keep the PRODUCTION material system and heights (Cu 14 um + solder cap 16 um,
underfill between), so geometry is not confounded with material; the all-solder attach is the
separate material bound (mat.vr_attach_material). Between the endpoints the ENGINEERING
sweep holds the dense pillar diameter and opens the pitch: it locates a crossover and is not a
manufacturing geometry.

For every case this file builds the REAL finite lattice in every cell (not A_cell / p^2):

  lattice   bump centres on a square grid of pitch p, centred on the cell; a site is legal if
            its bump lies inside the cell footprint with an edge clearance of at least half
            the bump-to-bump space, (p - d) / 2 -- the margin at which the same array would
            tile a neighbouring cell. VDD/GND alternate in a checkerboard (i + j even: VDD).
  electric  per bump the Cu and solder segments in SERIES, R = (rho_Cu h_Cu + rho_s h_cap)/A,
            plus the constriction of the uniform output-plane current into each bump on the
            regulator side and out of it on the substrate side (2-D finite-volume unit cell,
            checked against the annulus solution); rails in parallel. Equal sharing between
            the bumps is assessed by the current-redistribution length of the output plane
            over its distributed bump sink, against the cell size.
  thermal   through thickness: each column Cu + solder in SERIES, columns in PARALLEL with the
            underfill, k_z = f k_col + (1 - f) k_uf; in plane: each z-slice a Maxwell-Garnett
            array of its own inclusion, slices in parallel (the Phase 0M-R form). f is the
            REAL lattice metal fraction. Both are checked against an explicit AEDT RVE
            (scripts/reference_tools/aedt_attach_rve.py).
  mechanic  two BOUNDS, no "best" modulus: A underfill-dominated (the production convention,
            density-independent by construction); B column-stiffened Voigt with the real f.

No current density is turned into a reliability criterion: the per-bump current density is an
OUTPUT, and the electromigration literature cited for it is CONTEXT_ONLY.
"""
from __future__ import annotations

import csv
import json
import os
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts", "scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts/phase0e",
           "scripts/phase0dr", "scripts/phase0i", "scripts/phase0g", "scripts/phase0b"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
D = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"   # campaign hook
OUT_JSON = D / "vr_attach_density_study.json"
OUT_CSV = D / "vr_attach_density_study.csv"
RVE = D / "reference_attach_rve.json"

#: the cell footprint the attach covers (sqrt of the 5.61 mm^2 regulator cell, as the mesh)
CELL_SIDE_UM = math.sqrt(5.61) * 1e3
#: production heights (30 um framework allowance): Au et al. print the cap height as "16mm"
#: in the publisher's own abstract (IEEE Xplore metadata, arnumber 7545539), an evident unit
#: error for 16 um at 15 um diameter / 30 um pitch; the full text is closed and was not
#: retrievable here, so the pillar height is the allowance minus the cap (30 - 16 = 14 um).
H_CU_UM, H_CAP_UM = 14.0, 16.0
#: the regulator output plane that feeds the bumps (final_closure_ledger.vout_plane_r2)
PLANE_T_UM, PLANE_OCC = 10.0, 0.80

_AU = {"source": "Au et al., ECTC 2016", "doi": "10.1109/ECTC.2016.127",
       "class": "CLOSE_ANALOG",
       "evidence": "abstract: '30um pitch micro Cu pillar bump (15um diameter)'; cap height "
                   "printed '16mm' (unit error, read as 16 um)"}
_NA = {"source": "Na et al., Electronics 12(1):144 (2023; online 28 Dec 2022)",
       "doi": "10.3390/electronics12010144", "class": "CLOSE_ANALOG",
       "evidence": "abstract: 'bumps with a diameter of 30 um, a height of 40 um, and a space "
                   "of 50 um' (a pure-Sn cap on a Cu post/Ni barrier); pitch = 30 + 50 = 80 um"}

#: the two literature endpoints (geometry only; production material and heights held)
CASES = {
    "dense": dict(d_um=15.0, pitch_um=30.0, h_cu_um=H_CU_UM, h_cap_um=H_CAP_UM,
                  role="production geometry", **_AU),
    "sparse": dict(d_um=30.0, pitch_um=80.0, h_cu_um=H_CU_UM, h_cap_um=H_CAP_UM,
                   role="lower-density published geometry, production material held", **_NA),
}
#: ENGINEERING_SENSITIVITY between the endpoints: the dense 15 um pillar at wider pitches
#: (the last point reproduces the sparse endpoint's metal fraction); NOT literature geometry
SWEEP_PITCH_UM = (34.0, 37.0, 41.0)
for _p in SWEEP_PITCH_UM:
    CASES[f"eng_p{_p:g}"] = dict(d_um=15.0, pitch_um=_p, h_cu_um=H_CU_UM, h_cap_um=H_CAP_UM,
                                 role="ENGINEERING_SENSITIVITY (not a published geometry)",
                                 source="engineering interpolation between the endpoints",
                                 doi=None, **{"class": "ENGINEERING_SENSITIVITY"},
                                 evidence="dense pillar diameter held, pitch opened")


# ------------------------------------------------------------------ lattice
def lattice(case: dict, side_um: float = CELL_SIDE_UM, cx_um: float = 0.0,
            cy_um: float = 0.0) -> dict:
    """The legal bump sites of ONE cell, centred on (cx, cy)."""
    d, p = float(case["d_um"]), float(case["pitch_um"])
    keep = (p - d) / 2.0
    n = int(math.floor((side_um - 2.0 * keep - d) / p + 1e-12)) + 1
    span = (n - 1) * p
    x = cx_um - span / 2.0 + p * np.arange(n)
    y = cy_um - span / 2.0 + p * np.arange(n)
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    vdd = (ii + jj) % 2 == 0
    edge = (side_um - span - d) / 2.0
    if edge + 1e-9 < keep:
        raise RuntimeError(f"lattice violates its own edge clearance: {edge} < {keep}")
    n_tot = n * n
    metal = n_tot * math.pi * d * d / 4.0
    return {"n_per_axis": n, "n_total": n_tot, "n_vdd": int(vdd.sum()),
            "n_gnd": int(n_tot - vdd.sum()), "edge_clearance_um": edge,
            "edge_rule_um": keep, "metal_area_um2": metal,
            "area_fraction": metal / side_um ** 2,
            "area_fraction_infinite_lattice": math.pi * d * d / (4.0 * p * p),
            "x_um": x, "y_um": y, "vdd_mask": vdd}


@lru_cache(maxsize=1)
def cell_centres_mm():
    """The 49 regulator-cell centres of the production Z2 mesh (and their side)."""
    import final_closure_physical_etm as E
    _m, _mats, _st, tiles, _info = E.build("Z2", 1.1, (1, 1))
    return tuple((float(t.cx), float(t.cy)) for t in tiles), float(tiles[0].ax)


def all_cells(case: dict) -> dict:
    """The lattice of EVERY cell from the mesh tiles; refuses a cell that differs."""
    centres, side_mm = cell_centres_mm()
    per = []
    for cx, cy in centres:
        L = lattice(case, side_mm * 1e3, cx * 1e3, cy * 1e3)
        per.append((L["n_total"], L["n_vdd"], L["n_gnd"]))
    if len(set(per)) != 1:
        raise RuntimeError(f"cells differ in their attach lattice: {sorted(set(per))}")
    return {"n_cells": len(per), "cell_side_mm": side_mm, "per_cell": per[0],
            "total_vdd": sum(p[1] for p in per), "total_gnd": sum(p[2] for p in per)}


# ------------------------------------------------------------------ electrical
@lru_cache(maxsize=64)
def constriction_fv(p_um: float, d_um: float, n: int = 480) -> float:
    """Dimensionless constriction R / R_sheet of a uniform areal current over a p x p
    periodic cell drawn into a central disk of diameter d (quarter cell, symmetry edges,
    finite volume). Current injected over the disk area enters the bump directly."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    h = (p_um / 2.0) / n
    xc = (np.arange(n) + 0.5) * h
    X, Y = np.meshgrid(xc, xc, indexing="ij")
    sink = (X ** 2 + Y ** 2) <= (d_um / 2.0) ** 2       # Dirichlet cells (phi = 0)
    free = ~sink
    idx = -np.ones((n, n), dtype=int)
    idx[free] = np.arange(int(free.sum()))
    m = int(free.sum())
    diag = np.zeros(m)
    rows, cols = [], []
    # unit sheet resistance: conductance 1 across every interior face; the four quarter-cell
    # edges are symmetry lines (no flux), so faces leaving the domain do not exist
    for axis in (0, 1):
        a = np.s_[:-1, :] if axis == 0 else np.s_[:, :-1]
        b = np.s_[1:, :] if axis == 0 else np.s_[:, 1:]
        fa, fb = free[a], free[b]
        ia, ib = idx[a], idx[b]
        both = fa & fb
        rows += [ia[both], ib[both]]
        cols += [ib[both], ia[both]]
        np.add.at(diag, ia[fa], 1.0)                    # face to a free or a sink cell
        np.add.at(diag, ib[fb], 1.0)
    rows = np.concatenate(rows)
    cols = np.concatenate(cols)
    A = sp.csr_matrix((np.concatenate([diag, -np.ones(rows.size)]),
                       (np.concatenate([np.arange(m), rows]),
                        np.concatenate([np.arange(m), cols]))), shape=(m, m))
    q = np.full(m, 1.0 / (n * n))       # 1 A spread uniformly over the quarter cell's area
    phi = spl.spsolve(A.tocsc(), q)
    p_quarter = float(np.dot(q, phi))   # dissipation for 1 A into the quarter
    # the full cell carries 1 A: 1/4 A per quarter, dissipation (1/4)^2 p_quarter each
    return 4.0 * p_quarter / 16.0


def constriction_annulus(p_um: float, d_um: float) -> float:
    """The same quantity for the equal-area circular cell (closed form), as a check."""
    a, b = d_um / 2.0, p_um / math.sqrt(math.pi)
    br = b ** 4 * math.log(b / a) - b * b * (b * b - a * a) + (b ** 4 - a ** 4) / 4.0
    return br / (2.0 * math.pi * b ** 4)


def sheet_resistance(t_c: float = 20.0) -> float:
    from interconnect import rho_cu
    return rho_cu(t_c) / (PLANE_T_UM * 1e-6 * PLANE_OCC)


def bump_resistance(case: dict, t_c: float) -> dict:
    """Series vertical column plus the two constrictions, one bump, at temperature t_c."""
    from interconnect import rho_cu, rho_solder
    a = math.pi * (float(case["d_um"]) * 1e-6 / 2.0) ** 2
    r_v = (rho_cu(t_c) * case["h_cu_um"] * 1e-6 + rho_solder(t_c) * case["h_cap_um"] * 1e-6) / a
    c_fv = constriction_fv(case["pitch_um"], case["d_um"])
    r_c = 2.0 * c_fv * sheet_resistance(t_c)
    return {"R_vertical_ohm": r_v, "R_constriction_two_sides_ohm": r_c,
            "R_bump_ohm": r_v + r_c, "constriction_fraction": r_c / (r_v + r_c),
            "constriction_dimensionless_fv": c_fv,
            "constriction_dimensionless_annulus": constriction_annulus(case["pitch_um"],
                                                                       case["d_um"])}


def redistribution_length_mm(case: dict, r_bump_ohm: float, t_c: float = 20.0) -> float:
    """Length over which the output plane redistributes current into its distributed bump
    sink: lambda = sqrt(R_bump p^2 / R_sheet) for one rail (bumps of that rail sit at
    sqrt(2) p). Equal sharing is a fair model when lambda >= the cell size."""
    area_per_rail_bump = 2.0 * (case["pitch_um"] * 1e-6) ** 2
    return math.sqrt(r_bump_ohm * area_per_rail_bump / sheet_resistance(t_c)) * 1e3


def electrical(case: dict, t_c: float, i_cell_a: float, n_vr: int = 49) -> dict:
    L = lattice(case)
    rb = bump_resistance(case, t_c)
    out = {"T_attach_C": t_c, "I_cell_rms_A": i_cell_a, **rb}
    p_tot = 0.0
    for rail, n in (("VDD", L["n_vdd"]), ("GND", L["n_gnd"])):
        r_rail = rb["R_bump_ohm"] / n
        p = n_vr * i_cell_a ** 2 * r_rail
        a = math.pi * (float(case["d_um"]) * 1e-6 / 2.0) ** 2
        out[rail] = {"n_per_cell": n, "R_rail_per_cell_ohm": r_rail,
                     "I_per_bump_A": i_cell_a / n,
                     "J_avg_per_bump_A_m2": i_cell_a / n / a, "P_w": p}
        p_tot += p
    out["P_attach_total_w"] = p_tot
    out["redistribution_length_mm"] = redistribution_length_mm(case, rb["R_bump_ohm"])
    out["cell_side_mm"] = CELL_SIDE_UM / 1e3
    out["equal_sharing"] = ("fair: the output plane redistributes over a length >= the cell"
                            if out["redistribution_length_mm"] >= out["cell_side_mm"] else
                            "QUESTIONABLE: the redistribution length is below the cell size")
    return out


def two_sheet_network(case: dict, occ_top: float = PLANE_OCC, level: int = 2,
                      t_c: float = 20.0) -> dict:
    """Is equal bump sharing safe? One rail of one cell as a coupled network: the regulator
    output plane (inductor footprints inject I/3 each, as vout_plane_r2) and the substrate's
    top 1 V RDL (the die draws uniformly from it) joined by the distributed vertical stack
    attach + TSV field in series. The block model the ledger uses (output plane to a uniform
    sink, then uniform vertical currents, no lateral flow above) is ONE admissible current
    pattern of this network, so by Thomson's principle its loss bounds the network's from
    above. Returns both losses for 1 A at t_c, and the vertical-current non-uniformity."""
    import routing as RT
    import pkg_rdl_refined as RF
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    import tsv_fields as TF
    import physical_package as PP
    from interconnect import rho_cu
    s = RT.DESIGN["tile_side_mm"]
    comps = {c.name: c for c in RT.tile_layout(s)}
    legs = [comps[f"L{k}"] for k in range(3)]
    h_fine, h_coarse = RF.LEVELS[level]
    tx = sorted({round(c.x_mm + k * c.w_mm / 2, 9) for c in legs for k in (-1, 1)})
    ty = sorted({round(c.y_mm + k * c.h_mm / 2, 9) for c in legs for k in (-1, 1)})
    fx = RF.axis_faces(-s / 2, s / 2, tx, [], h_fine / 4, h_coarse / 4)
    fy = RF.axis_faces(-s / 2, s / 2, ty, [], h_fine / 4, h_coarse / 4)
    shA = RF.RefinedSheet(fx, fy, rho_cu(t_c) / (PLANE_T_UM * 1e-6 * PLANE_OCC))
    shB = RF.RefinedSheet(fx, fy, rho_cu(t_c) / (PLANE_T_UM * 1e-6 * occ_top))
    area = np.outer(shA.dx, shA.dy).ravel() * 1e-6               # m^2 per control volume
    a_cell = area.sum()
    L = lattice(case)
    rb = bump_resistance(case, t_c)["R_bump_ohm"]
    cfg = PP.load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    pc = TF.system_report(cfg.cells, cfg.cell_side_mm, 0.300, 1.0 * cfg.cells, T_C=t_c)["per_cell"]
    r_tsv = pc["r_vdd_ohm"] + pc["r_spread_vdd_ohm"]
    r_att = rb / L["n_vdd"]
    r_v = (r_att + r_tsv) * a_cell                                  # Ohm m^2, in series
    g = area / r_v
    qa = np.zeros(shA.n)
    for c in legs:
        ar = np.zeros(shA.n)
        for i in range(shA.nx):
            ox = min(shA.fx[i + 1], c.x_mm + c.w_mm / 2) - max(shA.fx[i], c.x_mm - c.w_mm / 2)
            if ox <= 0:
                continue
            for j in range(shA.ny):
                oy = (min(shA.fy[j + 1], c.y_mm + c.h_mm / 2)
                      - max(shA.fy[j], c.y_mm - c.h_mm / 2))
                if oy > 0:
                    ar[shA.node(i, j)] = ox * oy
        qa += ar / ar.sum() / 3.0
    qb = area / a_cell                                              # uniform draw, 1 A
    LA, LB, Gc = shA.laplacian(), shB.laplacian(), sp.diags(g)
    M = sp.bmat([[LA + Gc, -Gc], [-Gc, LB + Gc]]).tolil()
    rhs = np.concatenate([qa, -qb])
    ref = shA.n + shB.n - 1
    M[ref, :] = 0.0
    M[ref, ref] = 1.0
    rhs[ref] = 0.0
    V = spl.spsolve(M.tocsr(), rhs)
    va, vb = V[:shA.n], V[shA.n:]

    def p_sheet(Lx, v):
        Lc = Lx.tocoo()
        up = Lc.row < Lc.col
        return float(np.sum(-Lc.data[up] * (v[Lc.row[up]] - v[Lc.col[up]]) ** 2))
    i_v = g * (va - vb)
    p_net = {"plane": p_sheet(LA, va), "vertical": float(np.sum(g * (va - vb) ** 2)),
             "top_rdl": p_sheet(LB, vb)}
    # block model: output plane to a uniform sink + uniform vertical current
    import final_closure_ledger as FL
    r2, _ = FL.vout_plane_r2()
    p_blk = {"plane": r2 * rho_cu(t_c) / rho_cu(20.0), "vertical": r_v / a_cell, "top_rdl": 0.0}
    jv = i_v / area
    return {"occ_top": occ_top, "T_C": t_c, "r_attach_rail_cell_ohm": r_att,
            "r_tsv_rail_cell_ohm": r_tsv, "network_R_ohm": p_net,
            "network_total_ohm": sum(p_net.values()), "block_R_ohm": p_blk,
            "block_total_ohm": sum(p_blk.values()),
            "vertical_current_peak_over_mean": float(jv.max() / (1.0 / a_cell)),
            "n_cv": int(shA.n)}


# ------------------------------------------------------------------ thermal / mechanics
def k_column(case: dict) -> float:
    """Through-thickness conductivity of one column: Cu and solder in series."""
    import z2_converter as Z2C
    h_cu, h_cap = case["h_cu_um"], case["h_cap_um"]
    return (h_cu + h_cap) / (h_cu / Z2C.K_COPPER + h_cap / Z2C.K_SOLDER)


def card(case: dict, column_stiffened: bool = False) -> dict:
    """The homogenised attach card (z2_converter.vr_attach_material) at the REAL f."""
    import z2_converter as Z2C
    L = lattice(case)
    att = {"cu_height_um": case["h_cu_um"], "cap_height_um": case["h_cap_um"],
           "diameter_um": case["d_um"], "pitch_um": case["pitch_um"],
           "area_fraction": L["area_fraction"]}
    return Z2C.vr_attach_material(att, column_stiffened=column_stiffened)


def mesh_attach(case: dict) -> dict:
    """The cfg.attach entries a variant installs (final_closure_sensitivity)."""
    L = lattice(case)
    return {"cu_height_um": case["h_cu_um"], "cap_height_um": case["h_cap_um"],
            "diameter_um": case["d_um"], "pitch_um": case["pitch_um"],
            "area_fraction": L["area_fraction"]}


def ledger_spec(case: dict) -> dict:
    """The final_closure_ledger attach spec a variant installs: real-lattice rail counts and
    the constriction (in Cu, so it scales with the Cu resistivity)."""
    from interconnect import rho_cu
    L = lattice(case)
    c_fv = constriction_fv(case["pitch_um"], case["d_um"])
    return {"h_cu_um": case["h_cu_um"], "h_cap_um": case["h_cap_um"], "d_um": case["d_um"],
            "pitch_um": case["pitch_um"], "cell_side_mm": CELL_SIDE_UM / 1e3,
            "n_vdd": L["n_vdd"], "n_gnd": L["n_gnd"],
            "r_constriction_20c_ohm": 2.0 * c_fv * sheet_resistance(20.0),
            "model": "real lattice + series column + two-sided constriction"}


def _production_reference():
    """Production attach temperature, cell current and Z2 internal loss at HV-S0."""
    import final_closure_physical_etm as E
    import rms_currents as RMS
    r = json.loads(E.case_path("Z2", "HV_S0").read_text())
    t_att = r["et_history"][-1].get("T_attach_C", r["et_history"][-1]["T_sub_C"])
    return {"T_attach_C": t_att, "I_cell_rms_A": RMS.cell_currents()["i_cell_out_rms_a"],
            "P_Z2_internal_w": r["P_loss_w"],
            "P_attach_production_w": sum(x["P_w"] for x in r["ledger_rows"]
                                         if x["term"].startswith("P_VR_attach"))}


def production_card() -> dict:
    """The production homogenised card: the frozen spec at its infinite-lattice f."""
    import z2_converter as Z2C
    import final_closure_ledger as FL
    sp = FL.attach_spec()
    c = Z2C.vr_attach_material({"cu_height_um": sp["h_cu_um"], "cap_height_um": sp["h_cap_um"],
                                "diameter_um": sp["d_um"], "pitch_um": sp["pitch_um"]})
    kxy, _, kz = c["k_ortho"]["value"]
    return {"k_z_W_mK": kz, "k_xy_W_mK": kxy, "f": c["geometry"]["f"]}


def sharing(t_c: float, i_cell_a: float, n_vr: int = 49) -> dict:
    """Equal sharing, checked rather than assumed. The redistribution length of the output
    plane over its bump sink is far below the cell, so the bumps do NOT share equally; the
    coupled two-sheet network (two_sheet_network) gives the real pattern. The ledger's block
    model is an admissible current pattern of that network, hence (Thomson) an upper bound on
    its loss in both architectures' 1 V collection; what the density question needs is the
    PENALTY (sparse - dense), which the network may raise. Both rails, all cells (the GND
    network mirrors the VDD one to within one bump)."""
    k = 2.0 * n_vr * i_cell_a ** 2
    per = {}
    for name in CASES:
        net = two_sheet_network(CASES[name], t_c=t_c)
        per[name] = {"network_w": k * net["network_total_ohm"],
                     "block_w": k * net["block_total_ohm"],
                     "network_terms_ohm": net["network_R_ohm"],
                     "block_terms_ohm": net["block_R_ohm"],
                     "vertical_current_peak_over_mean": net["vertical_current_peak_over_mean"],
                     "n_cv": net["n_cv"]}
    pen = {name: {"block_w": per[name]["block_w"] - per["dense"]["block_w"],
                  "network_w": per[name]["network_w"] - per["dense"]["network_w"]}
           for name in CASES if name != "dense"}
    for v in pen.values():
        v["network_over_block"] = v["network_w"] / v["block_w"] if v["block_w"] else None
    return {"T_C": t_c, "I_cell_rms_A": i_cell_a,
            "verdict": ("equal sharing is NOT justified (redistribution length << cell); the "
                        "ledger's equal-sharing block model is an upper bound on the coupled "
                        "network's loss, and the density penalty is reported from both"),
            "per_case": per, "density_penalty_vs_dense": pen}


def etm_result(name: str) -> dict | None:
    """The S0 ETM of the variant attach_<name> (final_closure_sensitivity), if it ran."""
    f = D / "sensitivity" / f"etm_Z2_HV_S0__attach_{name}.json"
    if not f.exists():
        return None
    r = json.loads(f.read_text())
    att = {x["term"]: x["P_w"] for x in r["ledger_rows"] if x["term"].startswith("P_VR_attach")}
    crit = ((r.get("mechanics") or {}).get("joint_search") or {}).get("critical") or {}
    p_att = sum(att.values())
    return {"file": f.relative_to(R).as_posix(), "et_converged": r.get("et_converged"),
            "P_Z2_internal_w": r["P_loss_w"], "P_attach_VDD_w": att.get("P_VR_attach_VDD"),
            "P_attach_GND_w": att.get("P_VR_attach_GND"), "P_attach_total_w": p_att,
            "attach_fraction_of_Z2_internal": p_att / r["P_loss_w"],
            "T_max_C": r["thermal"]["T_max_C"],
            # the converter devices sit in the attach's heat path: their loss and temperature
            "P_conv_w": sum(x["P_w"] for x in r["ledger_rows"] if x["term"].startswith("P_conv")),
            "T_conv_C": r["et_history"][-1].get("T_conv_C"),
            "die_warpage_pv_um": (r.get("mechanics") or {}).get("die_warpage_pv_um"),
            "du_c_um": crit.get("du_um"), "T_joint_C": crit.get("T_C"),
            "critical_joint_xy_mm": ([crit["x_mm"], crit["y_mm"]] if crit else None),
            "d_eps_in_L0": (r.get("local") or {}).get("d_peeq_per_cycle")}


#: Part 10's materiality test for re-running the L3 local submodel, declared before any
#: density result was read
LOCAL_L3_RULE = ("re-run L3 if the critical joint moves to another site, if the joint driver "
                 "changes by more than 2U (its global uncertainty), or if the L0 local response "
                 "changes by more than the production local uncertainty U of Z2")


def local_level_decision(rows: dict) -> dict:
    """Brief Part 10: the local L3 submodel is re-run for a density case only if it changes
    materially what the local study saw. Declared before any density result was read: (a)
    the critical joint moves to another site, (b) the joint driver changes by more than twice
    its global uncertainty (the ordering rule's 2U), or (c) the L0 local response -- solved at
    the same level and settings as every class-B variant -- changes by more than the
    production local uncertainty U of Z2, the bound inside which the local verdict is formed.
    Otherwise the class-B L0 comparison stands."""
    import final_closure_physical_etm as E
    base = json.loads(E.case_path("Z2", "HV_S0").read_text())
    crit = base["mechanics"]["joint_search"]["critical"]
    od = (json.loads((D / "ordering.json").read_text()).get("orderings") or {}
          if (D / "ordering.json").exists() else {})
    u_du = ((od.get("du_c_um") or {}).get("uncertainty_rel") or {}).get("HV_S0")
    lm = (json.loads((D / "local_mesh_study.json").read_text()).get("cases") or {}
          if (D / "local_mesh_study.json").exists() else {}).get("Z2_HV_S0") or {}
    l0 = ((lm.get("levels") or {}).get("L0") or {}).get("d_peeq_per_cycle")
    out = {"rule": LOCAL_L3_RULE, "production": {"critical_joint_xy_mm": [crit["x_mm"], crit["y_mm"]],
                          "du_c_um": crit["du_um"], "T_joint_C": crit["T_C"],
                          "d_eps_in_L0": l0, "U_local_Z2": lm.get("U"), "U_du": u_du},
           "cases": {}}
    for name in ("dense", "sparse"):
        et = (rows.get(name) or {}).get("etm_S0") or {}
        if not et.get("du_c_um"):
            out["cases"][name] = {"decision": "PENDING -- no ETM mechanics"}
            continue
        moved = any(abs(a_ - b_) > 1e-9 for a_, b_ in zip(et["critical_joint_xy_mm"],
                                                         [crit["x_mm"], crit["y_mm"]]))
        d_du = (et["du_c_um"] - crit["du_um"]) / crit["du_um"]
        d_l0 = ((et["d_eps_in_L0"] - l0) / l0) if (et.get("d_eps_in_L0") and l0) else None
        why = ([f"critical joint moved to {et['critical_joint_xy_mm']}"] if moved else []) + (
            [f"joint driver changed {100 * d_du:+.2f} % > 2U"] if u_du and abs(d_du) > 2 * u_du
            else []) + ([f"L0 local response changed {100 * d_l0:+.1f} % > U"]
                        if d_l0 is not None and lm.get("U") and abs(d_l0) > lm["U"] else [])
        out["cases"][name] = {
            "critical_joint_moved": moved, "du_change_rel": d_du,
            "T_joint_change_K": et["T_joint_C"] - crit["T_C"], "L0_change_rel": d_l0,
            "decision": (("RUN L3: " + "; ".join(why)) if why else
                         "L3 not required: the class-B L0 comparison stands")
            if d_l0 is not None or why else "PENDING -- no L0 local response"}
    return out


def study() -> dict:
    ref = _production_reference()
    rve = json.loads(RVE.read_text()) if RVE.exists() else {}
    rows = {}
    for name, c in CASES.items():
        L = lattice(c)
        cells = all_cells(c)
        el = electrical(c, ref["T_attach_C"], ref["I_cell_rms_A"])
        el["attach_fraction_of_production_Z2_internal"] = (el["P_attach_total_w"]
                                                           / ref["P_Z2_internal_w"])
        cA, cB = card(c), card(c, column_stiffened=True)
        kxy, _, kz = cA["k_ortho"]["value"]
        row = {"case": name, "role": c["role"], "source": c["source"], "doi": c["doi"],
               "source_class": c["class"], "evidence": c["evidence"],
               "d_um": c["d_um"], "pitch_um": c["pitch_um"], "h_cu_um": c["h_cu_um"],
               "h_cap_um": c["h_cap_um"], "h_total_um": c["h_cu_um"] + c["h_cap_um"],
               "cell_side_um": CELL_SIDE_UM,
               **{k: L[k] for k in ("n_per_axis", "n_total", "n_vdd", "n_gnd",
                                    "edge_clearance_um", "edge_rule_um", "metal_area_um2",
                                    "area_fraction", "area_fraction_infinite_lattice")},
               "all_cells": cells, "electrical": el,
               "k_z_W_mK": kz, "k_xy_W_mK": kxy,
               "k_column_W_mK": k_column(c),
               "mech_bound_A": {"E_MPa": cA["E"]["value"], "cte": cA["cte"]["value"],
                                "basis": "underfill-dominated (production convention)"},
               "mech_bound_B": {"E_MPa": cB["E"]["value"], "cte": cB["cte"]["value"],
                                "basis": "column-stiffened Voigt at the real f"},
               "mechanical_status": "BOUNDED (no structural homogenisation reference run)"}
        for k in ("kz", "kxy"):
            # the RVE is the INFINITE periodic cell, so its error is against the card at the
            # same infinite-lattice f (reference_attach_rve.json), not at the real-lattice f
            rv = rve.get(f"vr_attach_{name}_{k}") or {}
            if rv.get("reference_value"):
                row[f"rve_{k}_W_mK"] = rv["reference_value"]
                row[f"rve_{k}_error"] = rv["rel_error"]
                row[f"rve_{k}_mesh_change"] = rv.get("mesh_change_rel")
        row["etm_S0"] = etm_result(name)
        rows[name] = row
    dense = rows["dense"]
    prod = {"P_attach_w": ref["P_attach_production_w"],
            "model": "legacy: n = floor(L/p)^2 // 2 per rail, series column, no constriction, "
                     "infinite-lattice f"}
    pc = production_card()
    out = {"gate": "geom.vr_attach_density", "subtype": "B1",
           "statement": ("The attach density is taken at two published constructions, one dense "
                         "and one sparse; the geometry-only comparison holds the production "
                         "Cu-pillar + solder-cap material and the 30 um height. The engineering "
                         "sweep between them is not a manufacturing geometry."),
           "allocation_rule": "checkerboard: site (i, j) is VDD if i + j is even, else GND",
           "edge_rule": "bump inside the cell with clearance >= (p - d) / 2 to the cell edge",
           "production_reference": ref, "production_attach_vs_refined_dense": {
               **prod, "refined_dense_P_attach_w": dense["electrical"]["P_attach_total_w"],
               "difference_w": dense["electrical"]["P_attach_total_w"] - prod["P_attach_w"],
               "kz_production_W_mK": pc["k_z_W_mK"], "f_production": pc["f"],
               "kz_refined_dense_W_mK": dense["k_z_W_mK"]},
           "equal_sharing_assessment": sharing(ref["T_attach_C"], ref["I_cell_rms_A"]),
           "current_density_note": ("an OUTPUT only; no electromigration-safe current density "
                                    "is claimed (EPTC 2015 10.1109/EPTC.2015.7412351 and "
                                    "Materials 2023 10.3390/ma16031134 are CONTEXT_ONLY)"),
           "mechanical_note": ("BOUNDED: A underfill-dominated, B column-stiffened Voigt at the "
                               "real f; Lee 2017 (10.3390/ma10101220) is CONTEXT_ONLY"),
           "local_level_decision": local_level_decision(rows),
           "cases": rows}
    return out


def _jsonable(o):
    if isinstance(o, np.ndarray):
        return None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    raise TypeError(type(o))


def write(res: dict) -> None:
    OUT_JSON.write_text(json.dumps(res, indent=1, default=_jsonable))
    cols = ["case", "role", "source_class", "doi", "d_um", "pitch_um", "h_total_um",
            "n_per_axis", "n_vdd", "n_gnd", "n_total", "edge_clearance_um", "area_fraction",
            "R_bump_mohm", "constriction_fraction", "R_rail_VDD_uohm", "R_rail_GND_uohm",
            "I_per_VDD_bump_mA", "J_avg_VDD_A_cm2", "P_VDD_w", "P_GND_w", "P_attach_w",
            "redistribution_length_mm", "k_z_W_mK", "k_xy_W_mK", "E_bound_A_MPa",
            "E_bound_B_MPa", "rve_kz_error", "rve_kxy_error", "etm_P_Z2_internal_w",
            "etm_P_attach_w", "etm_attach_fraction_of_Z2", "etm_T_max_C", "etm_du_c_um",
            "network_penalty_vs_dense_w", "block_penalty_vs_dense_w"]
    pen = res["equal_sharing_assessment"]["density_penalty_vs_dense"]
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in res["cases"].values():
            e = r["electrical"]
            w.writerow([r["case"], r["role"], r["source_class"], r["doi"], r["d_um"],
                        r["pitch_um"], r["h_total_um"], r["n_per_axis"], r["n_vdd"],
                        r["n_gnd"], r["n_total"], f"{r['edge_clearance_um']:.3f}",
                        f"{r['area_fraction']:.5f}", f"{1e3 * e['R_bump_ohm']:.4f}",
                        f"{e['constriction_fraction']:.4f}",
                        f"{1e6 * e['VDD']['R_rail_per_cell_ohm']:.4f}",
                        f"{1e6 * e['GND']['R_rail_per_cell_ohm']:.4f}",
                        f"{1e3 * e['VDD']['I_per_bump_A']:.3f}",
                        f"{e['VDD']['J_avg_per_bump_A_m2'] / 1e4:.1f}",
                        f"{e['VDD']['P_w']:.4f}", f"{e['GND']['P_w']:.4f}",
                        f"{e['P_attach_total_w']:.4f}", f"{e['redistribution_length_mm']:.2f}",
                        f"{r['k_z_W_mK']:.3f}", f"{r['k_xy_W_mK']:.4f}",
                        f"{r['mech_bound_A']['E_MPa']:.0f}", f"{r['mech_bound_B']['E_MPa']:.0f}",
                        r.get("rve_kz_error", ""), r.get("rve_kxy_error", ""),
                        *([f"{x[k]:.4f}" if x.get(k) is not None else "" for k in
                           ("P_Z2_internal_w", "P_attach_total_w",
                            "attach_fraction_of_Z2_internal", "T_max_C", "du_c_um")]
                          if (x := r.get("etm_S0")) else [""] * 5),
                        *([f"{pen[r['case']]['network_w']:.4f}",
                           f"{pen[r['case']]['block_w']:.4f}"] if r["case"] in pen
                          else ["0", "0"])])


if __name__ == "__main__":
    res = study()
    write(res)
    for n, r in res["cases"].items():
        e = r["electrical"]
        print(f"{n:9s} d{r['d_um']:g}/p{r['pitch_um']:g}: {r['n_vdd']}+{r['n_gnd']} bumps/cell, "
              f"f={r['area_fraction']:.4f}, R_bump={1e3 * e['R_bump_ohm']:.3f} mOhm "
              f"(constriction {100 * e['constriction_fraction']:.1f} %), P_attach="
              f"{e['P_attach_total_w']:.4f} W, kz={r['k_z_W_mK']:.2f}, kxy={r['k_xy_W_mK']:.3f}, "
              f"lambda={e['redistribution_length_mm']:.2f} mm")
    print("wrote", OUT_JSON.relative_to(R))
