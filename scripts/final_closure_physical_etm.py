"""FINAL CLOSURE --- the physical electrothermal fixed point, mechanics, and joint search.

Runs the PHYSICAL Z1/Z2 packages (the Phase-0N builders) through:

  ledger(T)  -> tier-aware heat map -> conjugate thermal FE -> T  (repeat to a fixed point)
  -> thermoelastic FE once on the converged field -> warpage, all-site joint drivers

Three corrections to the historical production path are made here, each because the
historical form was wrong for the physical packages:

1. THE BOTTOM HEAT FLOW WAS NEVER COMPUTED. production_et.solve_thermal set
   q_bot = Q_total - q_top and then reported energy_residual = q_top + q_bot - Q_total,
   which is zero by construction -- every historical "energy residual" was a tautology.
   Here q_bot is integrated from the board-bottom film faces of the SOLVED field, so the
   residual can actually fail.
2. THE FE SUBSTRATE NOW HOLDS THE ELECTRICAL TSV FIELD. The substrate carried a
   19.6 % Cu fraction smeared over all 900 mm^2. The adopted field is 1444 vias of
   30 um per cell, i.e. 18.2 % inside the 49 tiles and plain silicon elsewhere.
3. THE RDL TIER TENSOR IS THE TIER'S OWN. A four-metal-layer, 40 um stack tensor was
   applied to single 10 um tiers. It is replaced by the laminate of one 10 um tier
   (validated separately against an explicit RVE).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts/phase0i",
           "scripts/phase0g", "scripts/phase0b", "scripts/phase0e", "scripts/phase0dr",
           "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

import final_closure_ledger as FL                                   # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hvr_scratch import path as scratch                             # noqa: E402

OUT = R / "research" / "final_closure"
WD = Path(os.environ["FC_WORKDIR"]) if "FC_WORKDIR" in os.environ else scratch("fc_etm")
ET_TOL_K = 0.25            # declared before any physical result was read
#: mechanical mesh convergence, DECLARED before the h = 0.8 mm runs were read:
#: relative change of T_max, die warpage and critical-joint du between h_xy 1.1 and 0.8
MESH_TOL_REL = 0.02
MESH_LEVELS_MM = (1.1, 0.8)
#: The h_xy 1.1 -> 0.8 pair is NOT a refinement for Z2: lowering h_xy re-grades the grid,
#: Z2 keeps 38 lines per axis and its largest interior element GROWS from 1.12 to 1.72 mm,
#: and neither level refines z. It is kept only as a re-meshing sensitivity. Convergence
#: is judged on the NESTED study, declared before its results were read, with the same
#: 2 % tolerance on the same observables: every base (h_xy = 1.1) interval split in two
#: in-plane, r = (2, 1), and every layer's elements split in two through the thickness,
#: r = (1, 2). Every base node survives in both, so each is a strict refinement.
#: PRODUCTION MESH. The unrefined grid puts three elements across a 2.37 mm converter
#: tile, and the nested in-plane refinement raised the converged peak temperature by more
#: than the declared 2 % (mesh_convergence.json). Production therefore uses the h_xy = 1.1
#: grid with every in-plane interval split in two (r21); ITS convergence is judged against
#: r31 in-plane and against the measured through-thickness sensitivity (r11 -> r12).
PRODUCTION_H_XY = 1.1
PRODUCTION_REFINE = (2, 1)
#: refined meshes exceed the SPOOLES ceiling, so their structural solves use ITERATIVE
#: CHOLESKY, verified against SPOOLES on the base mesh (solver_check/)
PRODUCTION_SOLVER = "ITERATIVE CHOLESKY"
INPLANE_SEQUENCE = ((1, 1), (2, 1), (3, 1))
THROUGH_THICKNESS = ((1, 1), (1, 2))
ET_TOL_P_REL = 1e-3
ET_MAX_ITER = 8
THREADS = int(os.environ.get("FC_THREADS", "12"))
COOLER = "TOP_SI_MICROCHANNEL_27"
#: Class-B sensitivity hooks, set only by final_closure_sensitivity.py. On the production
#: path BUILD_HOOKS is empty and EXTRA_FILM is None, so nothing below changes.
#:   BUILD_HOOKS  callables (mesh, stack, tiles) -> dict, applied after the TSV/RDL
#:                material assignment and before the material cards are built
#:   EXTRA_FILM   callable (mesh, tiles, Q_W) -> {"elems", "h_W_m2K", "T_C", "label"}: one
#:                more convective face set (bottom faces, F1), whose heat flow is
#:                COMPUTED from the solved field and enters the heat balance
BUILD_HOOKS: list = []
EXTRA_FILM = None

# --- material corrections -------------------------------------------------
TSV_N_PER_CELL = 1444      # the adopted 'A_same_field' fabric (tsv_fields)
TSV_D_MM = 0.030


def tsv_tile_fraction(tile_side_mm):
    return TSV_N_PER_CELL * math.pi * (TSV_D_MM / 2) ** 2 / tile_side_mm ** 2


def tsv_material(stack, f):
    si, cu = stack["materials"]["silicon"], stack["materials"]["copper"]
    v = lambda d, k: d[k]["value"] if isinstance(d[k], dict) else d[k]
    E_si = si["isotropic_check"]["E"]; nu_si = si["isotropic_check"]["nu"]
    a_si, k_si = v(si, "cte"), v(si, "k")
    E_cu, nu_cu, a_cu, k_cu = v(cu, "E"), v(cu, "nu"), v(cu, "cte"), v(cu, "k")
    E = f * E_cu + (1 - f) * E_si
    kz = f * k_cu + (1 - f) * k_si
    kxy = k_si * (k_cu + k_si + f * (k_cu - k_si)) / (k_cu + k_si - f * (k_cu - k_si))
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E, "status": "DERIVED"},
            "nu": {"value": f * nu_cu + (1 - f) * nu_si, "status": "DERIVED"},
            "cte": {"value": (f * E_cu * a_cu + (1 - f) * E_si * a_si) / E,
                    "status": "DERIVED"},
            "k": {"value": kxy, "status": "DERIVED"},
            "k_ortho": {"value": [kxy, kxy, kz], "status": "DERIVED"},
            "cu_area_fraction": f}


#: one 10 um RDL tier = a Cu sublayer (t_Cu, in-layer occupancy) on dielectric
RDL_TIER = {"t_tier_um": 10.0, "t_cu_um": 5.0, "occupancy": 0.30,
            "k_cu": 400.0, "k_d": 0.35, "E_cu": 117e3, "E_d": 20e3,
            "a_cu": 17.0e-6, "a_d": 30.0e-6, "nu": 0.30}


def rdl_tier_laminate(p=RDL_TIER):
    """The production tensor of one 10 um RDL tier.

    VALIDATION CHANGED IT. The first version used the Voigt in-plane value
    occ*k_Cu (60.3 W/mK) and the series through-thickness value (0.698 W/mK). An
    explicit RVE of the DECLARED tier (square Cu grid, 30 % occupancy, 5 um Cu on
    5 um dielectric) solved in AEDT 2026 R1 Mechanical gave k_x = 34.28 and
    k_z = 0.620 W/mK: Voigt overstates in-plane conduction by 76 % for a grid
    (cross-lines do not conduct along x), and the series form overstates k_z by
    12.5 % because it ignores the constriction of heat onto the grid lines. The
    production tensor therefore ADOPTS the RVE values, read from
    research/final_closure/reference_rve.json rather than retyped; the grid
    laminate is kept as the analytic check (-3.7 % in-plane). Stiffness and CTE
    use the same grid laminate form; they were not RVE-validated (B-class).
    """
    import json as _json
    phi = p["t_cu_um"] / p["t_tier_um"]
    o = p["occupancy"]
    wp = 1.0 - math.sqrt(1.0 - o)
    ser = lambda a_, b_: 1.0 / (wp / a_ + (1 - wp) / b_)
    k_sub_x = wp * p["k_cu"] + (1 - wp) * ser(p["k_cu"], p["k_d"])
    kx = phi * k_sub_x + (1 - phi) * p["k_d"]
    k_sub_z = o * p["k_cu"] + (1 - o) * p["k_d"]
    kz = 1.0 / (phi / k_sub_z + (1 - phi) / p["k_d"])
    src = "grid laminate (analytic)"
    f = R / "research" / "final_closure" / "reference_rve.json"
    if f.exists():
        rv = _json.loads(f.read_text())
        if rv.get("rdl_tier_kx", {}).get("reference_value") and \
                rv.get("rdl_tier_kz", {}).get("reference_value"):
            kx = float(rv["rdl_tier_kx"]["reference_value"])
            kz = float(rv["rdl_tier_kz"]["reference_value"])
            src = "explicit RVE, AEDT 2026 R1 Mechanical (reference_rve.json)"
    E_sub = wp * p["E_cu"] + (1 - wp) * ser(p["E_cu"], p["E_d"])
    E = phi * E_sub + (1 - phi) * p["E_d"]
    st_cu = wp * p["E_cu"]
    a = (phi * (st_cu * p["a_cu"] + (1 - wp) * p["E_d"] * p["a_d"])
         + (1 - phi) * p["E_d"] * p["a_d"]) / (phi * (st_cu + (1 - wp) * p["E_d"])
                                               + (1 - phi) * p["E_d"])
    return {"status": "DERIVED", "elastic_type": "iso",
            "E": {"value": E, "status": "DERIVED"},
            "nu": {"value": p["nu"], "status": "ASSUMPTION"},
            "cte": {"value": a, "status": "DERIVED"},
            "k": {"value": kz, "status": "DERIVED"},
            "k_ortho": {"value": [kx, kx, kz], "status": "DERIVED"},
            "provenance": src}


class _NestedRefinement:
    """Split every in-plane interval of the base graded grid into rxy equal parts and
    every layer's through-thickness elements into rz parts, while the mesh is built.
    Every base node survives, so the result is strictly nested in the base mesh."""

    def __init__(self, rxy=1, rz=1):
        self.rxy, self.rz = int(rxy), int(rz)

    def __enter__(self):
        import etm.mesh as M
        self.M, self.g0, self.L0 = M, M._grid_1d_graded, M.Layer
        rxy, rz, g0, L0 = self.rxy, self.rz, self.g0, self.L0

        def grid(*a, **k):
            xs = g0(*a, **k)
            if rxy == 1:
                return xs
            t = np.linspace(0.0, 1.0, rxy + 1)[1:-1]
            ins = (xs[:-1, None] + np.outer(np.diff(xs), t)).ravel()
            return np.unique(np.round(np.concatenate([xs, ins]), 9))

        def layer(name, z0, z1, nz, *rest, **kw):
            return L0(name, z0, z1, nz * rz, *rest, **kw)

        M._grid_1d_graded = grid
        if rz != 1:
            M.Layer = layer
        return self

    def __exit__(self, *exc):
        self.M._grid_1d_graded, self.M.Layer = self.g0, self.L0
        return False


def refine_tag(refine):
    return "" if tuple(refine) == (1, 1) else f"_r{refine[0]}{refine[1]}"


def case_path(arch, scen, h_xy=None, refine=None):
    """The ETM case file; the production mesh unless a level is named explicitly."""
    h_xy = PRODUCTION_H_XY if h_xy is None else h_xy
    refine = PRODUCTION_REFINE if refine is None else refine
    return OUT / f"etm_{arch}_{scen}_h{h_xy}{refine_tag(refine)}.json"


def production_label():
    r = tuple(PRODUCTION_REFINE)
    base = f"graded h_xy = {PRODUCTION_H_XY} mm grid"
    if r == (1, 1):
        return base
    return (base + (f", every in-plane interval split in {r[0]}" if r[0] > 1 else "")
            + (f", every layer split in {r[1]} through the thickness" if r[1] > 1 else ""))


def build(arch, h_xy=1.1, refine=(1, 1)):
    import physical_package as PP
    import production_et as PE
    with _NestedRefinement(*refine):
        if arch == "Z1":
            m, mats, st, tiles = PP.build_physical_z1(h_xy=h_xy)
        else:
            cfg = PP.load_physical_package_config(
                R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
            m, mats, st, tiles = PP.build_physical_package(cfg, h_xy=h_xy)
    st = copy.deepcopy(st)
    side = tiles[0].ax
    f = tsv_tile_fraction(side)
    st["materials"]["tsv_tile"] = tsv_material(st, f)
    st["materials"]["rdl_tier"] = rdl_tier_laminate()
    cen = m.elem_centroids()
    mat = list(m.elem_material)
    n_in = n_out = 0
    for e in np.concatenate([m.elem_set(layer="sub_lower"),
                             m.elem_set(layer="tile_band")]):
        x, y = cen[e - 1][:2]
        inside = any(abs(x - t.cx) <= t.ax / 2 + 1e-9 and abs(y - t.cy) <= t.ay / 2 + 1e-9
                     for t in tiles)
        mat[e - 1] = "tsv_tile" if inside else "silicon"
        n_in += inside
        n_out += not inside
    m.elem_material = np.array(mat, dtype=object) if isinstance(
        m.elem_material, np.ndarray) else mat
    info = {"tsv_tile_cu_fraction": f, "sub_lower_in_tiles": n_in,
            "sub_lower_outside_tiles": n_out}
    for hook in BUILD_HOOKS:
        info.update(hook(m, st, tiles) or {})
    mats = PE.build_materials(st)
    return m, mats, st, tiles, info


def layer_mean_T(m, Tn, layers):
    import production_et as PE
    ids = np.concatenate([PE._layer_elems(m, L) for L in layers])
    nodes = np.unique(m.elems[ids - 1].ravel())
    return float(np.nanmean(Tn[nodes - 1]))


#: which deposits are confined to the 49 cell footprints. The physical converter
#: tiers contain OUT-OF-CELL encapsulant as well as the devices; depositing a tier's
#: loss over every element of the layer put GaN device loss into the underfill out
#: to the package corners, where it has almost no path to the cold plate, and
#: produced a 362 C hot spot at (15, 15) mm in an element carrying no device at all.
IN_TILE_KEYS = ("hs", "ls", "caps", "ind", "rdl", "lv", "tsv", "pads")


def deposits_from_ledger(arch, L):
    """(layers tuple, in_tiles) -> W."""
    lay = FL.LAYERS[arch]
    tile_layers = set()
    for k in IN_TILE_KEYS:
        v = lay[k]
        tile_layers.update(v if isinstance(v, list) else [v])
    dep = {((lay["die"],), False): FL.P_LOAD_W}
    for r in L["rows"]:
        if r["P_w"] <= 0:
            continue
        layers = tuple(r["deposit_layer"].split(","))
        key = (layers, all(x in tile_layers for x in layers))
        dep[key] = dep.get(key, 0.0) + r["P_w"]
    return dep


def _region_elems(m, layers, in_tiles, tiles):
    import production_et as PE
    ids = np.concatenate([PE._layer_elems(m, x) for x in layers])
    if not in_tiles:
        return ids
    cen = m.elem_centroids()[ids - 1]
    keep = np.zeros(len(ids), bool)
    for t in tiles:
        keep |= ((np.abs(cen[:, 0] - t.cx) <= t.ax / 2 + 1e-9)
                 & (np.abs(cen[:, 1] - t.cy) <= t.ay / 2 + 1e-9))
    return ids[keep]


def write_thermal(m, mats, st, deposits, h_face, t_face, path, tiles):
    import production_et as PE
    ccxio = PE.ccxio
    tb = st["thermal_bc"]
    h_bot, t_amb = tb["h_bottom"]["value"], tb["ambient_bottom"]["value"]
    L = ccxio._nodes_block(m) + ccxio._elements_blocks(m, "C3D8")
    L += ccxio._fmt_set("NALL", np.arange(1, m.n_nodes + 1), "NSET")
    for mat in sorted(set(m.elem_material)):
        L += [f"*MATERIAL, NAME={mat.upper()}"] + mats[mat].ccx_conductivity()
        L += [f"*SOLID SECTION, ELSET=E_{mat.upper()}, MATERIAL={mat.upper()}"]
    V = m.elem_volumes()
    dflux, deposited, k = [], 0.0, 0
    for (layers, in_tiles), w in deposits.items():
        ids = _region_elems(m, layers, in_tiles, tiles)
        vol = V[ids - 1].sum()
        if vol <= 0:
            raise PE.EnergyError(f"{layers} has no meshed volume for {w} W")
        k += 1
        L += ccxio._fmt_set(f"E_SRC_{k}", ids)
        dflux.append(f"E_SRC_{k},BF,{w / vol:.9g}")
        deposited += (w / vol) * vol
    top, bot = ccxio.top_film_faces(m), ccxio.bottom_film_faces(m)
    L += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL,{float(t_face.mean()):.6f}"]
    L += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "*DFLUX"] + dflux + ["*FILM"]
    for e, h_i, t_i in zip(top, h_face, t_face):
        L.append(f"{int(e)},F2,{t_i:.6f},{h_i * PE.W_M2K_TO_W_MM2K:.9g}")
    for e in bot:
        L.append(f"{int(e)},F1,{t_amb},{h_bot * PE.W_M2K_TO_W_MM2K:.9g}")
    extra = EXTRA_FILM(m, tiles, sum(deposits.values())) if EXTRA_FILM else None
    if extra is not None:
        if set(map(int, extra["elems"])) & set(map(int, bot)):
            raise ValueError("extra film faces overlap the board-bottom film")
        for e in extra["elems"]:
            L.append(f"{int(e)},F1,{extra['T_C']:.6f},"
                     f"{extra['h_W_m2K'] * PE.W_M2K_TO_W_MM2K:.9g}")
    L += ["*NODE FILE", "NT", "*END STEP"]
    path.write_text("\n".join(L) + "\n")
    return {"top": top, "bot": bot, "deposited_w": deposited,
            "h_bot": h_bot, "t_amb": t_amb, "extra": extra}


def solve_thermal(m, mats, st, deposits, wd, tiles, max_fluid_iter=8, tol_k=0.02):
    import production_et as PE
    from cooling_production import CANDIDATES
    ccxio = PE.ccxio
    wd.mkdir(parents=True, exist_ok=True)
    cooler = CANDIDATES[COOLER]
    Q = sum(deposits.values())
    top = ccxio.top_film_faces(m)
    cen = np.array([m.elem_centroids()[int(e) - 1] for e in top])
    areas = np.array([ccxio.face_area(m, e) for e in top])
    h_face = np.full(len(top), cooler.h_uniform(Q))
    m_dot = cooler.m_dot_g_s * 1e-3 * (2.0 if cooler.two_sided else 1.0)
    order = np.argsort(cen[:, 0])
    frac = np.zeros(len(top))
    frac[order] = (np.cumsum(areas[order]) - 0.5 * areas[order]) / areas.sum()
    t_face = cooler.t_in_c + frac * Q / (m_dot * PE.CP_F)
    hist, t0 = [], time.time()
    for it in range(max_fluid_iter):
        ti = wd / f"th_{it}.inp"
        info = write_thermal(m, mats, st, deposits, h_face, t_face, ti, tiles)
        ccxio.run_ccx(ti, threads=THREADS)
        frd = wd / f"th_{it}.frd"
        if not frd.is_file():
            raise RuntimeError(f"CalculiX produced no result for {ti}")
        Tn = ccxio.read_frd(frd)["NDTEMP"]
        Tnode = Tn[1:m.n_nodes + 1, 0]
        ts = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][4:], 0])) for e in top])
        q_face = h_face * PE.W_M2K_TO_W_MM2K * areas * (ts - t_face)
        q_up = np.zeros_like(q_face)
        q_up[order] = np.cumsum(q_face[order]) - 0.5 * q_face[order]
        t_new = cooler.t_in_c + q_up / (m_dot * PE.CP_F)
        dmax = float(np.max(np.abs(t_new - t_face)))
        hist.append({"iter": it, "max_dT_fluid_K": dmax, "T_max_C": float(np.nanmax(Tnode))})
        t_face = 0.5 * t_face + 0.5 * t_new
        if dmax < tol_k:
            break
    # the bottom heat flow, COMPUTED from the solved field
    bot = info["bot"]
    tb = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][:4], 0])) for e in bot])
    ab = np.array([ccxio.face_area(m, e) for e in bot])
    q_bot = float(np.sum(info["h_bot"] * PE.W_M2K_TO_W_MM2K * ab * (tb - info["t_amb"])))
    q_top = float(q_face.sum())
    out = {"T_node": Tnode, "T_max_C": float(np.nanmax(Tnode)),
           "T_mean_C": float(np.nanmean(Tnode)), "q_top_W": q_top, "q_bot_W": q_bot,
           "Q_deposited_W": info["deposited_w"], "Q_ledger_W": Q,
           "deposit_residual_rel": (info["deposited_w"] - Q) / Q,
           "energy_residual_rel": (q_top + q_bot - Q) / Q,
           "fluid_iters": len(hist), "fluid_hist": hist,
           "wall_s": time.time() - t0, "n_elems": m.n_elems, "n_nodes": m.n_nodes}
    ex = info.get("extra")
    if ex is not None:                    # sensitivity only: the extra film's heat flow,
        tx = np.array([float(np.nanmean(Tn[m.elems[int(e) - 1][:4], 0]))   # computed too
                       for e in ex["elems"]])
        ax = np.array([ccxio.face_area(m, e) for e in ex["elems"]])
        q_x = float(np.sum(ex["h_W_m2K"] * PE.W_M2K_TO_W_MM2K * ax * (tx - ex["T_C"])))
        out.update({"q_extra_W": q_x, "extra_film": {k: v for k, v in ex.items()
                                                     if k != "elems"},
                    "extra_film_faces": int(len(ex["elems"])),
                    "energy_residual_rel": (q_top + q_bot + q_x - Q) / Q})
    return out


def run_et(arch, scen, h_xy=1.1, refine=(1, 1)):
    t0 = time.time()
    m, mats, st, tiles, minfo = build(arch, h_xy, refine)
    lay = FL.LAYERS[arch]
    conv_layers = [lay["hs"], lay["ls"], lay["caps"], lay["ind"]] + lay["rdl"]
    temps = {"conv": 85.0, "bga": 60.0, "sub": 85.0, "interface": 85.0}
    hist, th, L = [], None, None
    wd = WD / f"{arch}_{scen}_h{h_xy}{refine_tag(refine)}"
    for it in range(ET_MAX_ITER):
        L = FL.self_consistent(arch, scen, temps)
        dep = deposits_from_ledger(arch, L)
        th = solve_thermal(m, mats, st, dep, wd / f"et{it}", tiles)
        Tn = th["T_node"]
        new = {"conv": layer_mean_T(m, Tn, conv_layers),
               "bga": layer_mean_T(m, Tn, [lay["bga"]]),
               "sub": layer_mean_T(m, Tn, [lay["tsv"]]),
               "interface": layer_mean_T(m, Tn, [lay["pads"]])}
        d_t = max(abs(new[k] - temps[k]) for k in temps)
        d_p = (abs(L["P_loss_w"] - hist[-1]["P_loss_w"]) / L["P_loss_w"]) if hist else 1.0
        hist.append({"iter": it, "P_loss_w": L["P_loss_w"], "T_max_C": th["T_max_C"],
                     "T_die_mean_C": layer_mean_T(m, Tn, [lay["die"]]),
                     **{f"T_{k}_C": v for k, v in new.items()},
                     "max_dT_K": d_t, "dP_rel": d_p,
                     "energy_residual_rel": th["energy_residual_rel"],
                     "wall_s": th["wall_s"]})
        temps = new
        print(f"  {arch} {scen} it{it}: Ploss={L['P_loss_w']:.3f} W Tmax={th['T_max_C']:.2f} "
              f"dT={d_t:.3f} K residual={th['energy_residual_rel']:+.2e}", flush=True)
        if d_t < ET_TOL_K and d_p < ET_TOL_P_REL:
            break
    t_et = time.time() - t0
    return m, mats, st, tiles, minfo, L, th, hist, t_et, wd


def joint_search(m, U, Tn, arch, tiles):
    """In-plane relative displacement across the BGA layer at EVERY legal site."""
    from scipy.interpolate import LinearNDInterpolator
    import physical_coords as PCO
    import pkg_rdl_network as K
    zl = {L.name: (L.z0, L.z1) for L in m.layers}
    z0, z1 = zl["bga"]
    nb, nt = m.node_ids_at_z(z0), m.node_ids_at_z(z1)
    pb, pt = m.nodes[nb - 1][:, :2], m.nodes[nt - 1][:, :2]
    ub = LinearNDInterpolator(pb, U[nb, :2])
    ut = LinearNDInterpolator(pt, U[nt, :2])
    tb = LinearNDInterpolator(pb, Tn[nb - 1])
    sites = PCO.bga_lattice_sites(K.architecture_cutout_mm(arch))
    S = np.array(sites)
    dub, dut, tt = ub(S), ut(S), tb(S)
    du = np.hypot(dut[:, 0] - dub[:, 0], dut[:, 1] - dub[:, 1]) * 1000.0
    ok = np.isfinite(du)
    order = np.argsort(-np.where(ok, du, -1))
    ranked = [{"rank": i + 1, "x_mm": float(S[j, 0]), "y_mm": float(S[j, 1]),
               "du_um": float(du[j]), "T_C": float(tt[j])}
              for i, j in enumerate(order[:ok.sum()])]
    return {"n_sites": int(len(S)), "n_evaluated": int(ok.sum()), "ranked": ranked,
            "critical": ranked[0] if ranked else None}


def mechanics(m, mats, st, Tn, wd, arch, tiles, solver="", threads=None):
    import production_et as PE
    ccxio = PE.ccxio
    t0 = time.time()
    si = wd / "structural.inp"
    wd.mkdir(parents=True, exist_ok=True)
    ccxio.write_structural(m, mats, Tn, st, "BC_BOARD", si, solver=solver)
    ccxio.run_ccx(si, threads=threads or THREADS)
    sres = ccxio.read_frd(si.with_suffix(".frd"))
    sm = PE.metrics.structural_metrics(m, sres["DISP"], sres["STRESS"], st)
    js = joint_search(m, sres["DISP"], Tn, arch, tiles)
    return {"die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm.get("pkg_warpage_pv_um"),
            "joint_search": js, "wall_s": time.time() - t0,
            "structural_solver": solver or "SPOOLES",
            "structural_threads": threads or THREADS}


def _raise_stack_limit():
    """CalculiX segfaults (rc = -11) on the finer structural models under the default
    8 MB stack; solver subprocesses inherit this limit from the worker."""
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_STACK,
                           (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except (ValueError, OSError):
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    os.environ.setdefault("OMP_STACKSIZE", "512M")


def run_case(arch, scen, h_xy=1.1, do_mech=True, refine=(1, 1), solver="", threads=None):
    """solver = "NONE" runs the E-T fixed point only (thermal mesh-convergence levels)."""
    _raise_stack_limit()
    if solver == "NONE":
        do_mech = False
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = run_et(arch, scen, h_xy, refine)
    res = {"arch": arch, "scenario": scen, "h_xy_mm": h_xy, "refine": list(refine),
           "materials": minfo,
           "ledger_rows": L["rows"], "P_loss_w": L["P_loss_w"],
           "i_hv_avg_a": L["i_hv_avg_a"], "energy_ledger": L["energy"],
           "thermal": {k: v for k, v in th.items() if k not in ("T_node",)},
           "et_history": hist, "et_converged": (hist[-1]["max_dT_K"] < ET_TOL_K
                                                and hist[-1]["dP_rel"] < ET_TOL_P_REL),
           "et_wall_s": t_et, "threads": THREADS}
    # write THIS case now, and again after mechanics: a failure in another worker, or a
    # long structural solve, must not withhold the converged thermal state
    f = OUT / f"etm_{arch}_{scen}_h{h_xy}{refine_tag(refine)}.json"
    f.write_text(json.dumps(res, indent=1, default=float))
    if do_mech:
        try:
            res["mechanics"] = mechanics(m, mats, st, th["T_node"], wd, arch, tiles,
                                         solver, threads)
        except Exception as e:                    # recorded, never silently dropped
            res["mechanics_error"] = str(e)[-600:]
        f.write_text(json.dumps(res, indent=1, default=float))
    return {"arch": arch, "scenario": scen, "h_xy_mm": h_xy, "file": str(f),
            "mechanics_ok": "mechanics" in res}


def main():
    import multiprocessing as mp
    cases = [(a, s) for s in FL.SCENARIOS for a in ("Z1", "Z2")]
    if len(sys.argv) > 1:
        cases = []
        for c in sys.argv[1:]:                    # ARCH:SCEN[:H[:rXZ[:SOLVER:THREADS]]]
            a, sc, *h = c.split(":")
            args = [a, sc] + ([float(h[0])] if h else [])
            if len(h) > 1:
                args += [True, (int(h[1][1]), int(h[1][2]))]
            if len(h) > 3:
                args += [h[2], int(h[3])]
            cases.append(tuple(args))
    with mp.Pool(len(cases)) as p:
        out = p.starmap(run_case, cases)
    for r in out:
        print(f"{r['arch']} {r['scenario']} h={r['h_xy_mm']}: written {r['file']} "
              f"mechanics_ok={r['mechanics_ok']}")


if __name__ == "__main__":
    main()
