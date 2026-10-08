"""Phase-0F: the 1-kW reference-scale evaluator.

Everything here is built on the Phase-0E validated pieces -- the sourced ECTC-2024 RDL stack,
the separated n_req / n_alloc / n_avail allocation, the rail-aware power-path graphs -- and
adds three things Phase 0E did not have:

  * a GEOMETRY GATE (scripts/phase0f/geometry.py): no impossible converter/substrate pair is
    ever meshed;
  * the 1-kW load, its own converter design and its own cooling calibration;
  * per-VR LOCAL temperature in the ET fixed point, at 49 regulators rather than 4.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0b", "phase0d", "phase0dr", "phase0e", "phase0f"):
    sys.path.insert(0, str(R / "scripts" / p))

from etm.config import build_materials, load_doe, load_stack
from etm.mesh import build
from etm.placement import Tile, generate
from etm import ccxio, metrics
from electrical import compile_hvr
from architecture0e import evaluate as elec_eval, CROWDING_DEFAULT
from stack import stacks_from_cfg
from geometry import cell_stack, check as geom_check, fitting_inductors

OUT = R / "results" / "phase0f"
P0B = R / "results" / "phase0b"

# ---- 1 kW reference point (see PHASE0F_1KW_ETM_GATE.md Sec. 3) -------------------------
P_LOAD_W = 1000.0
V_POL = 1.0
I_TOTAL_A = 1000.0
DIE_MM = 22.36
M_VR = 49
J_TARGET = 3.5
BOUND = "nominal"
H_XY = 0.60
THREADS = 16
ELEM_CEILING = 40000

PLACE = {"uniform": "uniform", "compact": "compact", "asymmetric": "asymmetric"}


def design_1kw(m_vr: int = M_VR, j: float = J_TARGET, h_sub_mm: float = 1.5,
               bound: str = BOUND):
    """Compile a converter that PHYSICALLY FITS the substrate, or return None."""
    fit, budget = fitting_inductors(h_sub_mm, bound)
    if not fit:
        return None, None, f"no inductor fits h_sub={h_sub_mm*1e3:.0f} um (budget {budget:.0f} um)"
    d = compile_hvr(P_LOAD_W / V_POL / m_vr, j, inductor_library=fit)
    if d is None:
        return None, None, f"no converter from the {len(fit)} fitting inductors"
    g = geom_check(d, h_sub_mm, bound)
    if not g.feasible:
        return None, g, g.reason
    return d, g, "realizable"


def tiles_for(fam, side, stack, doe, n_vr):
    """Phase-0F families for large M; the Phase-0B families are hard-wired to n_vr = 4."""
    from placement0f import build as build0f
    g, rules = stack["geometry"], doe["placement_rules"]
    die = g["functional_die"]["size_x"]["value"]
    tiles, meta = build0f(fam, n_vr, side, die, rules["edge_keepout_mm"]["value"],
                          rules["min_gap_mm"]["value"])
    return [(t.cx, t.cy) for t in tiles]


def placement_meta(fam, side, stack, doe, n_vr):
    from placement0f import build as build0f
    g, rules = stack["geometry"], doe["placement_rules"]
    _, meta = build0f(fam, n_vr, side, g["functional_die"]["size_x"]["value"],
                      rules["edge_keepout_mm"]["value"], rules["min_gap_mm"]["value"])
    return meta


def _stack_with_tile(stack, t_tile_mm, h_bottom=None):
    """Deep copy so the loaded stack is never mutated.

    `h_bottom` overrides the substrate-underside film. June-2026 cools with
    substrate-embedded micro-channels "positioned adjacent to the GaN switch layer", i.e.
    from INSIDE the substrate, whereas every earlier phase cooled the TIM top surface. The
    two put the through-thickness thermal gradient in OPPOSITE directions, and warpage is
    driven by that gradient, so both are carried.
    """
    st = json.loads(json.dumps(stack))
    st["geometry"]["hvr_tile"]["thickness"]["value"] = t_tile_mm
    if h_bottom is not None:
        st["thermal_bc"]["h_bottom"]["value"] = h_bottom
        st["thermal_bc"]["h_bottom"]["status"] = "DERIVED_PHASE0F"
    return st


def tile_temperatures(m, T, n_tiles):
    """Volume-weighted mean temperature of each tile's own elements (Sec. 12)."""
    out = []
    for k in range(n_tiles):
        sel = np.where(m.elem_tile == k)[0]
        if sel.size == 0:
            out.append(float(np.max(T))); continue
        conn = m.elems[sel] - 1
        xyz = m.nodes[conn]
        vol = ((xyz[:, :, 0].max(1) - xyz[:, :, 0].min(1))
               * (xyz[:, :, 1].max(1) - xyz[:, :, 1].min(1))
               * (xyz[:, :, 2].max(1) - xyz[:, :, 2].min(1)))
        out.append(float((T[conn].mean(axis=1) * vol).sum() / vol.sum()))
    return out


def thermal_structural(tiles, st, h_sub, h_top, p_die_extra, wd, bc="BC_A", h_xy=H_XY):
    wd.mkdir(parents=True, exist_ok=True)
    mats = build_materials(st)
    m = build(tiles, st, h_sub, h_xy=h_xy, z_scale=1.4, support_layer=(bc == "BC_B"))
    if len(m.elems) > ELEM_CEILING:
        raise RuntimeError(f"{len(m.elems)} C3D8I elements exceeds the {ELEM_CEILING} ceiling "
                           "where CalculiX segfaults silently")
    ti = wd / "th.inp"
    films = ccxio.write_thermal(m, mats, tiles, st, p_die_extra, h_top, ti)
    ccxio.run_ccx(ti, threads=THREADS)
    Tn = ccxio.read_frd(wd / "th.frd")["NDTEMP"]
    tm = metrics.thermal_metrics(m, Tn, films, st,
                                 p_die_extra + sum(t.power_w for t in tiles), h_top)
    Tnode = Tn[1:m.n_nodes + 1, 0]
    t_tiles = tile_temperatures(m, Tnode, len(tiles))
    si = wd / "st.inp"
    ccxio.write_structural(m, mats, Tnode, st, bc, si, solver="")
    ccxio.run_ccx(si, threads=THREADS)
    s = ccxio.read_frd(wd / "st.frd")
    sm = metrics.structural_metrics(m, s["DISP"], s["STRESS"], st)
    kap = curvature(m, s["DISP"])
    for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
        for f in wd.glob(pat):
            f.unlink(missing_ok=True)
    return tm, sm, t_tiles, kap, len(m.elems)


def curvature(m, U):
    ids = m.node_ids_at_z(m.layer("die").z1)
    xyz = m.nodes[ids - 1]
    uz = U[ids, 2] * 1000.0
    A = np.column_stack([xyz[:, 0] ** 2 + xyz[:, 1] ** 2, xyz[:, 0], xyz[:, 1],
                         np.ones_like(xyz[:, 0])])
    c, *_ = np.linalg.lstsq(A, uz, rcond=None)
    return float(c[0])


def coupled_1kw(arch, fam, h_sub_mm, h_top, stack, doe, wd, m_vr=M_VR, j=J_TARGET,
                bc="BC_A", tol=0.05, max_it=12, h_xy=H_XY, rdl=None, j_cu=None,
                h_bottom=None):
    """Full ET fixed point at 1 kW with per-VR local temperature."""
    des, g, why = design_1kw(m_vr, j, h_sub_mm)
    if des is None:
        return {"feasible": False, "reason": why, "arch": arch, "fam": fam,
                "h_sub_mm": h_sub_mm, "m_vr": m_vr, "j": j}
    rdl = rdl or stacks_from_cfg()["ectc2024_primary"]
    cs = cell_stack(des, BOUND)
    st = _stack_with_tile(stack, cs.t_cell_mm, h_bottom=h_bottom)
    side = math.sqrt(des.area_mm2)
    xy = tiles_for(fam, side, st, doe, m_vr)
    t_vr = [25.0] * len(xy)
    hist, prev = [], None
    for it in range(max_it):
        per_vr = [des.loss_at(t)["p_conv_w"] for t in t_vr]
        p_conv = float(sum(per_vr))
        e = elec_eval(arch, xy, side, h_sub_mm, I_TOTAL_A, p_conv, float(np.mean(t_vr)),
                      rdl, j_cu=j_cu, crowding=CROWDING_DEFAULT, strict=False,
                      t_tile_mm=cs.t_cell_mm)
        tiles = [Tile(cx, cy, side, side, per_vr[k]) for k, (cx, cy) in enumerate(xy)]
        tm, sm, t_tiles, kap, nel = thermal_structural(
            tiles, st, h_sub_mm, h_top, P_LOAD_W + e["P_pdn_w"], wd, bc=bc, h_xy=h_xy)
        Tn = tm["T_max_C"]
        hist.append({"it": it, "T_max_C": Tn, "P_conv_w": p_conv, "P_pdn_w": e["P_pdn_w"],
                     "T_vr_min": min(t_tiles), "T_vr_max": max(t_tiles)})
        if prev is not None and abs(Tn - prev) < tol:
            break
        prev, t_vr = Tn, t_tiles
    t = e["P_by_tier_w"]
    return {
        "feasible": True, "reason": why, "arch": arch, "fam": fam, "bc": bc,
        "h_sub_mm": h_sub_mm, "m_vr": m_vr, "j": j, "tile_side_mm": side,
        "t_tile_mm": cs.t_cell_mm, "inductor": des.inductor.name,
        "inductor_h_um": des.inductor.height_um, "h_tsv_um": g.h_tsv_um,
        "a_hvr_total_mm2": des.area_mm2 * m_vr, "f_sw_MHz": des.f_sw_hz / 1e6,
        "elec_feasible": e["feasible"], "elec_infeasible": "; ".join(e["infeasible"])[:160],
        "I_tsv_a": e["I_tsv_a"], "n_tsv_req": e["n_tsv_req"], "n_tsv_alloc": e["n_tsv_alloc"],
        "n_tsv_avail": e["n_tsv_avail"], "i_per_tsv_ma": e["i_per_tsv_ma"],
        "P_conv_w": e["P_conv_w"], "P_bga_w": t.get("bga", 0.0), "P_c4_w": t.get("c4", 0.0),
        "P_tsv_w": t.get("tsv", 0.0), "P_microbump_w": t.get("microbump", 0.0),
        "P_rdl_w": t.get("rdl", 0.0), "P_pdn_w": e["P_pdn_w"],
        "P_elec_total_w": e["P_elec_total_w"],
        "efficiency_pct": 100 * P_LOAD_W / (P_LOAD_W + e["P_elec_total_w"]),
        "T_max_C": tm["T_max_C"], "T_vr_min_C": min(hist[-1]["T_vr_min"], hist[-1]["T_vr_max"]),
        "T_vr_max_C": hist[-1]["T_vr_max"],
        "energy_residual_pct": tm["energy_residual_pct"],
        "die_warpage_pv_um": sm["die_warpage_pv_um"],
        "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"], "curvature_um_per_mm2": kap,
        "interface_shear_p99_MPa": sm.get("interface_shear_MPa", {}).get("p99", float("nan")),
        "si_principal_p99_MPa": sm.get("si_principal_MPa", {}).get("p99", float("nan")),
        "n_elem": nel, "et_iters": len(hist), "history": hist,
        "h_top_W_m2K": h_top, "h_bottom_W_m2K": (h_bottom if h_bottom is not None
                                                 else stack["thermal_bc"]["h_bottom"]["value"])}
