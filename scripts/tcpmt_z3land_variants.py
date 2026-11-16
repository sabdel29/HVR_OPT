"""Z3 1 V spreading in the COUPLED electrothermal solution (TCPMT revision).

The Z3 ledger records P_sub_land_1V_spreading and P_PCB_plane_1V_spreading as zero
NOT_MODELLED rows, so its 1 V loss is a lower bound. These class-B variants put both
spreading conductors into the coupled ledger of the production E-T fixed point (production
mesh, S0) and rerun it with mechanics, under cooling B (z3_plate_tim) or A (z3_top_only):

  land side   P = 2 kappa I_rail^2 R_s(T_land),   R_s = rho_Cu(T_land) / (t_Cu occ)
              kappa = P_one_rail / (I^2 R_s) of the committed 2-D FV sheet at its solved
              point (tcpmt_z3land_fv.land_shape), I_rail = the 1 V rail RMS current the
              ledger's 1 V BGA rows use (49 x cell output RMS), occ = 0.80, t_Cu swept;
              T_land = node mean of the WHOLE substrate land-side layer (sub_lower),
              where the heat is deposited: uniformly over all of it, not over the cells
  board planes P = (kappa_VDD + kappa_GND) I_rail^2 R_s,b(T_board), the same FV approach on
              the board's 1 V planes (tcpmt_z3land_fv), DECLARED 2 x 35 um Cu per rail at
              80 % occupancy; T_board = node mean of the whole board, where it is deposited

Both follow the framework's rule that a conductor's resistance is evaluated over the region
its loss is deposited in (final_closure_physical_etm.temperature_regions, DEFECT #68). Each
rail's static spread dV = kappa_V I_dc R_s is recorded with the case (I_dc = P_load / V_out).

The *_fvmap variants are a DEPOSIT-DISTRIBUTION sensitivity of the uniform deposit: the same
runs with both spreading losses deposited along their FV loss maps (FVMAP_BINS power-density
bins over the same layers) instead of uniformly; the ledger, its temperatures and the totals
are unchanged.

Nothing in final_closure_* is edited: the variants register themselves in
final_closure_sensitivity.VARIANTS from this module and patch the ledger, the temperature
regions, the deposit map and the CalculiX timeout inside their own apply(), in their own
process, exactly as the existing hooks do.

    python tcpmt_z3land_variants.py run VARIANT      E-T + mechanics (S.run_full via S._task)
    python tcpmt_z3land_variants.py remech VARIANT [HOURS]   mechanics only, converged field
    python tcpmt_z3land_variants.py check VARIANT    patches on the mesh, no solve
    python tcpmt_z3land_variants.py augment VARIANT  rewrite the case's z3_land block
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_sensitivity as S                               # noqa: E402
import final_closure_physical_etm as E                              # noqa: E402
import final_closure_ledger as FL                                   # noqa: E402
import tcpmt_z3land_fv as FV                                        # noqa: E402

LAND_TERM, PLANE_TERM = "P_sub_land_1V_spreading", "P_PCB_plane_1V_spreading"
#: E-T temperature keys added for Z3: the whole land-side layer and the whole board
LAND_KEY, BOARD_KEY = "land", "board"
LAND_OCC = FV.LAND_OCC
I_DC_A = FL.P_LOAD_W / FL.V_OUT
#: structural solves on the loaded host can pass the 2 h CalculiX default
CCX_TIMEOUT_S = 8 * 3600

#: name -> (land-side t_Cu um, cooling tier, board planes in the coupled ledger)
RUNS = {
    "z3_land_t10_B": (10.0, "B", True),
    "z3_land_t20_B": (20.0, "B", True),
    "z3_land_t40_B": (40.0, "B", True),
    "z3_land_t40_A": (40.0, "A", True),
    "z3_land_t40_B_noplane": (40.0, "B", False),
    "z3_land_t100_B": (100.0, "B", True),
    "z3_land_t10_B_fvmap": (10.0, "B", True),
    "z3_land_t40_B_fvmap": (40.0, "B", True),
}
#: deposit-distribution sensitivity: the two spreading losses deposited along their FV loss
#: maps (fv_bins) instead of uniformly over the whole layer; everything else as the base run
FVMAP = {"z3_land_t10_B_fvmap", "z3_land_t40_B_fvmap"}
FVMAP_BINS = 32
COOLING = {"A": S.v_z3_top_only, "B": S.v_z3_plate_tim}
COOLING_NAME = {"A": "z3_top_only", "B": "z3_plate_tim"}

#: the configuration this process runs (configure()), and the last evaluation of each row
STATE: dict = {"t_um": None, "plane": True, "fvmap": False, "last": {}}
DEPOSIT_RECORD: dict = {}
#: FV-map deposit bins on the built mesh: problem -> [(element ids, fraction of the loss)]
MESH_BINS: dict = {}


def board_shape():
    return json.loads(FV.OUT.read_text())["board_planes"]


def rho_cu(t_c):
    from interconnect import rho_cu as _rho
    return _rho(t_c)


def land_rs(t_c, t_um):
    return rho_cu(t_c) / (t_um * 1e-6 * LAND_OCC)


def board_rs(t_c):
    return rho_cu(t_c) / (FV.BOARD_T_PER_RAIL_UM * 1e-6 * FV.BOARD_OCC)


def land_eval(i_rms, t_c, t_um):
    k = FV.land_shape()
    r_s = land_rs(t_c, t_um)
    return {"T_C": float(t_c), "t_um": float(t_um), "I_rms_A": float(i_rms),
            "R_s_mohm_sq": r_s * 1e3, "kappa_one_rail": k["kappa_one_rail"],
            "P_w": 2.0 * k["kappa_one_rail"] * i_rms ** 2 * r_s,
            "R_eff_ohm": 2.0 * k["kappa_one_rail"] * r_s,
            "dV_static_one_rail_mV": k["kappa_V_one_rail"] * I_DC_A * r_s * 1e3}


def board_eval(i_rms, t_c):
    b = board_shape()
    r_s = board_rs(t_c)
    return {"T_C": float(t_c), "I_rms_A": float(i_rms), "R_s_mohm_sq": r_s * 1e3,
            "kappa_two_rails": b["kappa_two_rails"],
            "P_w": b["kappa_two_rails"] * i_rms ** 2 * r_s,
            "R_eff_ohm": b["kappa_two_rails"] * r_s,
            "dV_static_VDD_mV": b["kappa_V_VDD"] * I_DC_A * r_s * 1e3,
            "dV_static_GND_mV": b["kappa_V_GND"] * I_DC_A * r_s * 1e3}


# ------------------------------------------------------------------ patches
def configure(t_um, plane=True, fvmap=False):
    """Select the land-side copper and whether the board planes are carried; the ledger
    patch reads this at call time, so one process can re-evaluate several runs."""
    STATE.update(t_um=float(t_um), plane=bool(plane), fvmap=bool(fvmap), last={})


def patch_ledger():
    """Replace the two NOT_MODELLED rows of final_closure_ledger.z3_rows by their modelled
    values; every other Z3 row is produced by the original z3_rows unchanged."""
    if getattr(FL.z3_rows, "_z3land", False):
        return
    orig = FL.z3_rows
    k_land = FV.land_shape()
    b = board_shape()
    land_in = json.loads(FV.OUT.read_text())["land_side"]["loss_fraction_in_footprints"]

    def z3_rows(add, lay, temps, t_sub, t_bga, i_cell_rms):
        def add2(term, conductor, rail, value, R_ohm, I_a, current_type, model, layer,
                 evidence, maturity, note=""):
            if term == LAND_TERM and STATE["t_um"] is not None:
                t_c = float(temps.get(LAND_KEY, t_sub))
                ev = land_eval(I_a, t_c, STATE["t_um"])
                STATE["last"]["land"] = ev
                return add(
                    term, "package land-side 1 V redistribution: BGA balls -> TSV fields, both "
                    "rails (t_Cu %g um, %.0f %% occupancy)" % (STATE["t_um"], 100 * LAND_OCC),
                    rail, ev["P_w"], ev["R_eff_ohm"], I_a, current_type,
                    "2 kappa I^2 R_s(T), R_s = rho_Cu(T) / (t_Cu occ); kappa = %.6f per rail "
                    "from the 2-D FV sheet at its solved point (%s)"
                    % (k_land["kappa_one_rail"], k_land["source"]),
                    lay["tsv"], "FV_SHEET_GEOMETRY_DESIGN_CHOICE", "BOUNDED",
                    "t_Cu = %g um is a swept DESIGN_CHOICE; R_s = %.4f mOhm/sq at T_land = %.2f C "
                    "(whole land-side layer); per-rail static spread %.1f mV at %.0f A DC; equal "
                    "ball sharing (the BGA rows' assumption); deposited uniformly over the whole "
                    "30 mm land side (the FV puts %.1f %% of it inside the cell footprints, "
                    "30.6 %% of the area)"
                    % (STATE["t_um"], ev["R_s_mohm_sq"], t_c, ev["dV_static_one_rail_mV"],
                       I_DC_A, 100 * land_in))
            if term == PLANE_TERM and STATE["t_um"] is not None and STATE["plane"]:
                t_c = float(temps.get(BOARD_KEY, temps.get("pcb_via", t_bga)))
                ev = board_eval(I_a, t_c)
                STATE["last"]["board"] = ev
                al = b["allocation"]
                return add(
                    term, "PCB 1 V copper planes: via fields -> BGA balls, both rails (%d x %g um "
                    "Cu per rail, %.0f %% occupancy)" % (al["planes_per_rail"], al["t_plane_um"],
                                                         100 * al["occupancy"]),
                    rail, ev["P_w"], ev["R_eff_ohm"], I_a, current_type,
                    "(kappa_VDD + kappa_GND) I^2 R_s(T), R_s = rho_Cu(T) / (t_Cu,rail occ); "
                    "kappa = %.6f (two rails) from the 2-D FV sheet with the via-in-pad field "
                    "as disk sources (tcpmt_z3land_fv)" % b["kappa_two_rails"],
                    lay["pcb_via"], "FV_SHEET_DECLARED_ALLOCATION", "BOUNDED",
                    "DECLARED allocation %s; R_s = %.4f mOhm/sq at T_board = %.2f C (whole "
                    "board); static spread VDD %.1f / GND %.1f mV at %.0f A DC; equal ball "
                    "sharing; deposited uniformly over the whole board"
                    % (al["basis"], ev["R_s_mohm_sq"], t_c, ev["dV_static_VDD_mV"],
                       ev["dV_static_GND_mV"], I_DC_A))
            return add(term, conductor, rail, value, R_ohm, I_a, current_type, model, layer,
                       evidence, maturity, note)
        return orig(add2, lay, temps, t_sub, t_bga, i_cell_rms)
    z3_rows._z3land = True
    FL.z3_rows = z3_rows


def patch_regions():
    """Two more E-T temperature regions for Z3: the whole land-side layer and the whole
    board (not confined to the cells), where the two spreading losses are deposited."""
    if getattr(E.temperature_regions, "_z3land", False):
        return
    orig_r, orig_h = E.temperature_regions, E.temps_from_history

    def temperature_regions(arch):
        reg = orig_r(arch)
        if arch == "Z3":
            lay = FL.LAYERS[arch]
            reg[LAND_KEY] = ([lay["tsv"]], False)
            reg[BOARD_KEY] = ([lay["pcb_via"]], False)
        return reg

    def temps_from_history(h):
        t = orig_h(h)
        for k in (LAND_KEY, BOARD_KEY):
            if f"T_{k}_C" in h:
                t[k] = h[f"T_{k}_C"]
        return t
    temperature_regions._z3land = temps_from_history._z3land = True
    E.temperature_regions, E.temps_from_history = temperature_regions, temps_from_history


def patch_deposits():
    """deposits_from_ledger confines every sub_lower and board row to the cell footprints
    (IN_TILE_KEYS 'tsv', 'pcb_via'): right for the TSV and via fields, wrong for the two
    spreading planes, which span the whole 30 mm substrate and board. Their watts are moved
    to the not-confined key of the same layer; the total is unchanged."""
    if getattr(E.deposits_from_ledger, "_z3land", False):
        return
    orig = E.deposits_from_ledger

    def deposits_from_ledger(arch, L):
        dep = orig(arch, L)
        if arch != "Z3":
            return dep
        lay = FL.LAYERS[arch]
        moved = {LAND_TERM: lay["tsv"], PLANE_TERM: lay["pcb_via"]}
        for term, layer in moved.items():
            p = sum(r["P_w"] for r in L["rows"] if r["term"] == term and r["P_w"] > 0)
            if p <= 0:
                continue
            k_in, k_all = ((layer,), True), ((layer,), False)
            rest = sum(r["P_w"] for r in L["rows"] if r["P_w"] > 0
                       and tuple(r["deposit_layer"].split(",")) == (layer,)
                       and r["term"] not in moved)
            if abs(dep[k_in] - p - rest) > 1e-9 * max(1.0, dep[k_in]):
                raise RuntimeError(f"{k_in} holds {dep[k_in]} W, not {rest} + {p} W")
            if rest > 0:
                dep[k_in] = rest
            else:
                del dep[k_in]
            if STATE.get("fvmap"):                # sensitivity: along the FV loss map
                prob = "land" if term == LAND_TERM else "board"
                for k, (_ids, frac) in enumerate(MESH_BINS[prob]):
                    key = ((layer,), ("fvmap", prob, k))
                    dep[key] = dep.get(key, 0.0) + p * frac
                continue
            dep[k_all] = dep.get(k_all, 0.0) + p
        tot = FL.P_LOAD_W + sum(r["P_w"] for r in L["rows"] if r["P_w"] > 0)
        if abs(sum(dep.values()) - tot) > 1e-9 * tot:
            raise RuntimeError(f"deposits {sum(dep.values())} W != load + ledger {tot} W")
        return dep
    deposits_from_ledger._z3land = True
    E.deposits_from_ledger = deposits_from_ledger


def patch_write_thermal():
    """Record what each thermal input deck actually receives: per deposit region the
    element count, volume and watts (the inspection behind the deposit residual)."""
    if getattr(E.write_thermal, "_z3land", False):
        return
    orig = E.write_thermal

    def write_thermal(m, mats, st, deposits, h_face, t_face, path, tiles, arch=None):
        info = orig(m, mats, st, deposits, h_face, t_face, path, tiles, arch=arch)
        V = m.elem_volumes()
        regs = []
        for k, ((layers, in_tiles), w) in enumerate(deposits.items(), start=1):
            ids = E._region_elems(m, layers, in_tiles, tiles)
            cen = m.elem_centroids()[ids - 1]
            regs.append({"set": f"E_SRC_{k}", "layers": list(layers),
                         "in_tiles": (bool(in_tiles) if not isinstance(in_tiles, tuple)
                                      else list(in_tiles)),
                         "W": float(w), "n_elems": int(len(ids)),
                         "volume_mm3": float(V[ids - 1].sum()),
                         "xy_extent_mm": [float(cen[:, 0].min()), float(cen[:, 0].max()),
                                          float(cen[:, 1].min()), float(cen[:, 1].max())]})
        DEPOSIT_RECORD.clear()
        DEPOSIT_RECORD.update({"inp": str(path), "regions": regs,
                               "sum_deposits_W": float(sum(deposits.values())),
                               "deposited_W": float(info["deposited_w"])})
        return info
    write_thermal._z3land = True
    E.write_thermal = write_thermal


def patch_ccx_timeout(seconds=CCX_TIMEOUT_S):
    import production_et as PE
    if getattr(PE.ccxio.run_ccx, "_z3land", False):
        return
    orig = PE.ccxio.run_ccx

    def run_ccx(job, threads=None, timeout=7200):
        return orig(job, threads, max(int(timeout), int(seconds)))
    run_ccx._z3land = True
    PE.ccxio.run_ccx = run_ccx


def patch_all():
    patch_ledger()
    patch_regions()
    patch_deposits()
    patch_write_thermal()
    patch_ccx_timeout()


# ------------------------------------------------------------------ FV-map deposit
def fv_loss_map(problem):
    """Two-rail FV loss map on the committed 0.1 mm grid, normalised to 1 (VDD + GND)."""
    n, xc = FV.grid(FV.GRID_MM)
    tot = np.zeros((n, n))
    for rail in ("VDD", "GND"):
        q = (FV.land_sources(n, xc, rail) if problem == "land"
             else FV.board_sources(n, xc, rail)[0])
        tot += FV.solve(q)[2]
    return xc, tot / tot.sum()


def fv_bins(m, layer, problem, k_bins=FVMAP_BINS):
    """Each element of `layer` takes the FV loss of the grid cells whose centres lie in its
    x-y rectangle, shared over the layer's z-stack by thickness; elements are grouped into
    k_bins logarithmic power-density bins, each deposited at its own mean density. Returns
    [(element ids, fraction of the loss)], the fractions summing to 1."""
    import production_et as PE
    xc, frac = fv_loss_map(problem)
    cs = np.zeros((len(xc) + 1, len(xc) + 1))
    cs[1:, 1:] = frac.cumsum(0).cumsum(1)
    ids = PE._layer_elems(m, layer)
    p = m.nodes[m.elems[ids - 1] - 1]
    lo, hi = p.min(axis=1), p.max(axis=1)
    i0, i1 = (np.searchsorted(xc, lo[:, 0] - 1e-9), np.searchsorted(xc, hi[:, 0] - 1e-9))
    j0, j1 = (np.searchsorted(xc, lo[:, 1] - 1e-9), np.searchsorted(xc, hi[:, 1] - 1e-9))
    s_xy = cs[i1, j1] - cs[i0, j1] - cs[i1, j0] + cs[i0, j0]
    L = m.layer(layer)
    s = s_xy * (hi[:, 2] - lo[:, 2]) / (L.z1 - L.z0)
    if abs(s.sum() - 1.0) > 1e-9:
        raise RuntimeError(f"FV map on {layer} sums to {s.sum()}, not 1")
    s = np.maximum(s, 0.0)                        # summed-area round-off
    s = s / s.sum()
    vol = m.elem_volumes()[ids - 1]
    d = s / vol
    # log bins over four decades below the peak density; everything under them (slivers
    # holding no grid-cell centre, the far field) shares the lowest bin
    lg = np.log(np.maximum(d, d.max() * 1e-4))
    b = np.clip(((lg - lg.min()) / max(lg.max() - lg.min(), 1e-12) * k_bins).astype(int),
                0, k_bins - 1)
    return [(ids[b == k], float(s[b == k].sum())) for k in range(k_bins) if (b == k).any()]


def patch_fvmap():
    """E.build also bins the Z3 land-side and board layers along their FV loss maps, and
    E._region_elems resolves the ('fvmap', problem, k) deposit keys to those bins."""
    if getattr(E.build, "_z3land", False):
        return
    orig_build, orig_reg = E.build, E._region_elems

    def build(arch, h_xy=1.1, refine=(1, 1)):
        out = orig_build(arch, h_xy, refine)
        if arch == "Z3":
            lay = FL.LAYERS[arch]
            MESH_BINS.update({"land": fv_bins(out[0], lay["tsv"], "land"),
                              "board": fv_bins(out[0], lay["pcb_via"], "board")})
        return out

    def _region_elems(m, layers, in_tiles, tiles):
        if isinstance(in_tiles, tuple) and in_tiles and in_tiles[0] == "fvmap":
            return MESH_BINS[in_tiles[1]][in_tiles[2]][0]
        return orig_reg(m, layers, in_tiles, tiles)
    build._z3land = _region_elems._z3land = True
    E.build, E._region_elems = build, _region_elems


def apply(t_um, tier, plane=True, fvmap=False):
    COOLING[tier]()
    configure(t_um, plane, fvmap)
    patch_all()
    if fvmap:
        patch_fvmap()


def what(t_um, tier, plane, fvmap=False):
    s = ("Z3 with the land-side 1 V redistribution in the coupled ledger (t_Cu = %g um, 80 %% "
         "occupancy, FV shape factor), deposited over the whole substrate land side"
         % t_um)
    if plane:
        s += ("; and the board 1 V plane spreading (2 x 35 um Cu per rail, 80 %, FV shape "
              "factor), deposited over the whole board")
    else:
        s += "; board 1 V plane spreading left NOT_MODELLED (control)"
    s += f"; cooling {tier} ({COOLING_NAME[tier]})"
    if fvmap:
        s += ("; DEPOSIT SENSITIVITY: both spreading losses follow their FV loss maps (%d "
              "power-density bins) instead of a uniform deposit" % FVMAP_BINS)
    return s


for _name, (_t, _tier, _plane) in RUNS.items():
    _fv = _name in FVMAP
    S.VARIANTS[_name] = dict(
        kind="full", archs=("Z3",),
        apply=(lambda t=_t, tier=_tier, plane=_plane, fv=_fv: apply(t, tier, plane, fv)),
        gates=[], nature=(f"ENGINEERING_SENSITIVITY (Z3 1 V spreading, cooling {_tier})"
                          + (", deposit-distribution sensitivity" if _fv else "")),
        what=what(_t, _tier, _plane, _fv))


# ------------------------------------------------------------------ case records
def scratch_dir(variant):
    from hvr_scratch import path as scratch
    return scratch("fc_sens", variant) / (f"Z3_{S.SCEN}_h{E.PRODUCTION_H_XY}"
                                          f"{E.refine_tag(E.PRODUCTION_REFINE)}")


def last_thermal_frd(variant):
    wd = scratch_dir(variant)
    last_it = sorted(wd.glob("et*"), key=lambda p: int(p.name[2:]))[-1]
    frd = sorted(last_it.glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))[-1]
    return frd


def z3_land_block(variant, case):
    """What the coupled case carries beyond S.run_full's record: the configuration, the
    shape factors, the two rows' evaluation (temperature, sheet resistance, static spread)
    and the deposit inspection of the final thermal deck."""
    t_um, tier, plane = RUNS[variant]
    rows = {r["term"]: r for r in case["ledger_rows"]}
    h = case["et_history"]
    t_eval = E.temps_from_history(h[-2] if len(h) > 1 else h[-1])
    i_rms = rows[LAND_TERM]["I_a"]
    land = land_eval(i_rms, t_eval.get(LAND_KEY), t_um)
    if abs(land["P_w"] - rows[LAND_TERM]["P_w"]) > 1e-9 * land["P_w"]:
        raise RuntimeError(f"{variant}: land-side row {rows[LAND_TERM]['P_w']} W is not "
                           f"reproduced at the recorded temperature ({land['P_w']} W)")
    blk = {"variant": variant, "t_land_um": t_um, "cooling_tier": tier,
           "cooling_hook": COOLING_NAME[tier], "board_planes_in_ledger": plane,
           "land_occupancy": LAND_OCC, "I_rail_rms_A": i_rms, "I_rail_dc_A": I_DC_A,
           "shape_factors": {"land": {k: v for k, v in FV.land_shape().items()},
                             "board": {k: board_shape()[k] for k in
                                       ("kappa_two_rails", "kappa_V_VDD", "kappa_V_GND",
                                        "allocation")}},
           "rho_cu_model": "interconnect.rho_cu (1.70e-8 Ohm m at 20 C, alpha 3.93e-3/K), as "
                           "every Cu row of the ledger",
           "T_ledger_eval_C": t_eval, "T_converged_C": E.temps_from_history(h[-1]),
           "land": land}
    if plane:
        b = board_eval(i_rms, t_eval.get(BOARD_KEY))
        if abs(b["P_w"] - rows[PLANE_TERM]["P_w"]) > 1e-9 * b["P_w"]:
            raise RuntimeError(f"{variant}: board-plane row is not reproduced")
        blk["board"] = b
    else:
        blk["board_bound_uncoupled"] = board_eval(
            i_rms, E.temps_from_history(h[-1]).get(BOARD_KEY))
    blk["deposit"] = "fv_map" if variant in FVMAP else "uniform"
    if variant in FVMAP and MESH_BINS:
        blk["fvmap_bins"] = {k: {"n_bins": len(v), "n_elems": int(sum(len(i) for i, _ in v)),
                                 "fractions": [f for _, f in v]} for k, v in MESH_BINS.items()}
    if DEPOSIT_RECORD:
        blk["deposit_inspection"] = dict(DEPOSIT_RECORD)
    return blk


def augment(variant, task=None):
    if STATE["t_um"] is None:                     # standalone: the ledger/region patches only
        configure(RUNS[variant][0], RUNS[variant][2], variant in FVMAP)
        patch_all()
    f = S.case_file("Z3", variant)
    c = json.loads(f.read_text())
    c["z3_land"] = z3_land_block(variant, c)
    if task is not None:
        c["z3_land"]["task"] = task
    f.write_text(json.dumps(c, indent=1, default=float))
    return c


def run(variant):
    patch_ccx_timeout()
    task = S._task(("Z3", variant))
    print(task, flush=True)
    if "error" in task:
        return task
    augment(variant, task)
    return task


def remech(variant, hours=12.0):
    """Mechanics only, on the variant's converged thermal field (asserted equal to the case
    file's T_max), with a longer CalculiX timeout -- final_closure_remech for a variant."""
    import production_et as PE
    t_um, tier, plane = RUNS[variant]
    apply(t_um, tier, plane, variant in FVMAP)
    patch_ccx_timeout(int(hours * 3600))
    E._raise_stack_limit()
    f = S.case_file("Z3", variant)
    res = json.loads(f.read_text())
    m, mats, st, tiles, _ = E.build("Z3", E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    frd = last_thermal_frd(variant)
    tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(tn)) - res["thermal"]["T_max_C"]) > 1e-6:
        raise RuntimeError(f"{frd} is not the converged field of {f.name}")
    t0 = time.time()
    res["mechanics"] = E.mechanics(m, mats, st, tn, scratch_dir(variant), "Z3", tiles,
                                   E.PRODUCTION_SOLVER, 1)
    res["mechanics"]["note"] = (f"structural step run separately on the converged field "
                                f"({frd.name}), CalculiX timeout {hours:g} h")
    res.pop("mechanics_error", None)
    f.write_text(json.dumps(res, indent=1, default=float))
    print("re-mech", variant, res["mechanics"]["die_warpage_pv_um"],
          res["mechanics"]["joint_search"]["critical"], f"{time.time() - t0:.0f} s", flush=True)


def check(variant):
    """The patches on the production mesh without a solve: ledger rows at the cooling-tier
    reference temperatures, the deposit map and its regions, the totals."""
    t_um, tier, plane = RUNS[variant]
    apply(t_um, tier, plane, variant in FVMAP)
    ref = json.loads((S.OUT / f"etm_Z3_{S.SCEN}__{COOLING_NAME[tier]}.json").read_text())
    temps = E.temps_from_history(ref["et_history"][-1])
    temps.setdefault(LAND_KEY, temps["sub"])
    temps.setdefault(BOARD_KEY, temps["pcb_via"])
    m, mats, st, tiles, _ = E.build("Z3", E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    L = FL.self_consistent("Z3", S.SCEN, temps)
    dep = E.deposits_from_ledger("Z3", L)
    V = m.elem_volumes()
    print(variant, "P_loss", round(L["P_loss_w"], 4), "(reference", round(ref["P_loss_w"], 4), ")")
    for r in L["rows"]:
        if r["term"] in (LAND_TERM, PLANE_TERM):
            print("  ", r["term"], round(r["P_w"], 4), r["maturity"], r["deposit_layer"])
    for (layers, in_tiles), w in dep.items():
        ids = E._region_elems(m, layers, in_tiles, tiles)
        print(f"   {','.join(layers)[:60]:60s} in_tiles={str(in_tiles):5s} {w:10.4f} W "
              f"{len(ids):6d} elems {V[ids - 1].sum():9.3f} mm3")
    print("  sum deposits", sum(dep.values()), "load + ledger", FL.P_LOAD_W + L["P_loss_w"])
    regions = E.temperature_regions("Z3")
    print("  regions", {k: v for k, v in regions.items() if k in (LAND_KEY, BOARD_KEY, "sub")})


def main():
    cmd, variant = sys.argv[1], sys.argv[2]
    if variant not in RUNS:
        raise SystemExit(f"unknown variant {variant}; known {sorted(RUNS)}")
    if cmd == "run":
        run(variant)
    elif cmd == "remech":
        remech(variant, float(sys.argv[3]) if len(sys.argv) > 3 else 12.0)
    elif cmd == "check":
        check(variant)
    elif cmd == "augment":
        augment(variant)
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
