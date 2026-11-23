"""Finding 6 -- board size, mounting, clamping preload and board-bottom cooling.

The production board is a coupon of the package's own size (+-15 mm): the corner ball sits
0.6 mm from a free edge, Z2's BGA ring rests on a 3.32-mm board frame, nothing clamps the
assembly, and the board underside carries h = 10 W/m2K against the authors' own 60-520 W/m2K
estimate of a full server board. This driver runs, per architecture, ONE electrothermal fixed
point on a board LARGER than the package (configs/tcpmt_mech: board.extent_factor; mesh option
of etm.mesh.build) and then several thermoelastic solves on that same converged field:

  free           3-2-1 on the board underside (the production restraint)
  screws         u_z = 0 on node patches at the four board corners, in-plane free
  screws_pinned  the same patches fixed in x, y, z (a rigid chassis at 25 C)
  edge           u_z = 0 along the board-underside perimeter (simply supported)
  clamp_screws   cold-plate clamp: uniform pressure on the TIM top (force from config),
                 reacted at the screws, with the thermal load
  clamp_only     the same clamp at the stress-free temperature (no thermal load)
  clamp_backplate  the clamp reacted by a backplate under the package footprint, with heat

and compares them with the production coupon case of the same mesh level (cost: elements,
wall time; effect: T_max, die warpage, critical du and site, interconnect drivers). Results go
to research/tcpmt_revision/board_study/ only; no production file is touched.

    FC_THREADS=2 python tcpmt_mech_board.py run ARCH [--factor 3] [--hbot 10] [--refine 11]
    python tcpmt_mech_board.py local ARCH [--factor 3]   the clamp in the local response
    python tcpmt_mech_board.py summarize      -> research/tcpmt_revision/board_study.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_mech_laws as LAW                                       # noqa: E402

OUTD = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "board_study"   # campaign hook
SUMMARY = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "board_study.json"
SCEN = "HV_S0"


def bcfg():
    return LAW.cfg()["board"]


def tag(arch, factor, hbot, refine):
    r = "" if tuple(refine) == (1, 1) else f"_r{refine[0]}{refine[1]}"
    return f"{arch}_x{factor:g}_hb{hbot:g}{r}"


def clamp_lines(m, force_n):
    """*DLOAD on the TIM top faces: a uniform pressure carrying force_n over the die."""
    import production_et as PE
    top = PE.ccxio.top_film_faces(m)
    area = sum(PE.ccxio.face_area(m, e) for e in top)
    p = force_n / area
    return ["*DLOAD"] + [f"{int(e)},P2,{p:.9g}" for e in top], p, area


def mech_case(E, m, mats, st, Tn, wd, arch, tiles, name, bc, params=None, loads=None,
              thermal=True, solver="SPOOLES", threads=2):
    E.STRUCT_BC, E.STRUCT_PARAMS = bc, params
    E.STRUCT_LOADS = (lambda _m: loads) if loads else None
    t_ref = st["structural_bc"]["t_ref"]["value"]
    T = Tn if thermal else np.full_like(np.asarray(Tn, float), t_ref)
    t0 = time.time()
    try:
        me = E.mechanics(m, mats, st, T, wd / name, arch, tiles, solver, threads)
    except Exception as e:                        # recorded, never silent
        me = {"error": str(e)[-600:]}
    finally:
        E.STRUCT_BC, E.STRUCT_PARAMS, E.STRUCT_LOADS = "BC_BOARD", None, None
    me["wall_total_s"] = time.time() - t0
    return me


def summary_of(me):
    if "error" in me:
        return {"error": me["error"]}
    c = me["joint_search"]["critical"]
    ic = {k: {"gamma_max": v.get("gamma_max"), "critical_xy_mm": [v["critical"]["x_mm"],
                                                                  v["critical"]["y_mm"]]}
          for k, v in (me.get("interconnects") or {}).items() if "critical" in v}
    bga_c = (me.get("interconnects") or {}).get("bga", {}).get("critical", {})
    return {"die_warpage_pv_um": me["die_warpage_pv_um"],
            "pkg_warpage_pv_um": me.get("pkg_warpage_pv_um"),
            "du_c_um": c["du_um"], "T_joint_C": c["T_C"], "site_mm": [c["x_mm"], c["y_mm"]],
            "du_z_um": bga_c.get("du_z_um"), "interconnects": ic,
            "wall_s": me.get("wall_s")}


def run(arch, factor, hbot, refine):
    import final_closure_physical_etm as E
    from hvr_scratch import path as scratch
    os.environ["HVR_BOARD_EXTENT_FACTOR"] = f"{factor:g}"
    os.environ["HVR_BOARD_FAR_H_MM"] = f"{float(bcfg()['far_field_h_max_mm']):g}"
    t = tag(arch, factor, hbot, refine)
    E.WD = scratch("mech_board", t)
    if abs(hbot - 10.0) > 1e-9:
        def hook(m, st, tiles, h=hbot):
            st["thermal_bc"]["h_bottom"]["value"] = float(h)
            return {"h_bottom_W_m2K": float(h)}
        E.BUILD_HOOKS.append(hook)
    E._raise_stack_limit()
    h = E.PRODUCTION_H_XY
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = E.run_et(arch, SCEN, h, refine)
    res = {"arch": arch, "scenario": SCEN, "board_extent_factor": factor,
           "board_side_mm": factor * 30.0, "h_bottom_W_m2K": hbot, "refine": list(refine),
           "n_elems": m.n_elems, "n_nodes": m.n_nodes, "materials": minfo,
           "P_loss_w": L["P_loss_w"], "thermal": {k: v for k, v in th.items()
                                                  if k != "T_node"},
           "et_history": hist, "et_wall_s": t_et, "et_converged": (
               hist[-1]["max_dT_K"] < E.ET_TOL_K and hist[-1]["dP_rel"] < E.ET_TOL_P_REL),
           "mechanics": {}}
    OUTD.mkdir(parents=True, exist_ok=True)
    f = OUTD / f"{t}.json"
    f.write_text(json.dumps(res, indent=1, default=float))
    Tn = th["T_node"]
    mt = bcfg()["mounting"]
    zb = next(Lr for Lr in m.layers if Lr.name == "board").z0     # board underside plane
    scr = {"inset_mm": float(mt["screw_inset_mm"]), "patch_mm": float(mt["screw_patch_mm"]),
           "z_mm": zb}
    force = float(LAW._val(bcfg()["clamp"]["force_N"]))
    lines, p, area = clamp_lines(m, force)
    res["clamp"] = {"force_N": force, "pressure_MPa": p, "area_mm2": area}
    plan = [("free", "BC_BOARD", None, None, True),
            ("screws", "BC_BOARD_SCREWS", scr, None, True),
            ("screws_pinned", "BC_BOARD_SCREWS_PINNED", scr, None, True),
            ("edge", "BC_BOARD_EDGE", {"z_mm": zb}, None, True),
            ("clamp_screws", "BC_BOARD_SCREWS", scr, lines, True),
            ("clamp_only", "BC_BOARD_SCREWS", scr, lines, False),
            ("clamp_backplate", "BC_BACKPLATE", {"footprint_half_mm": 15.0}, lines, True)]
    if "--only" in sys.argv:
        keep = sys.argv[sys.argv.index("--only") + 1].split(",")
        plan = [x for x in plan if x[0] in keep]
    for name, bc, prm, ld, thermal in plan:
        me = mech_case(E, m, mats, st, Tn, wd, arch, tiles, name, bc, prm, ld, thermal)
        res["mechanics"][name] = me
        f.write_text(json.dumps(res, indent=1, default=float))
        s = summary_of(me)
        print(f"{t} {name}: {json.dumps({k: s.get(k) for k in ('die_warpage_pv_um', 'du_c_um', 'site_mm', 'wall_s', 'error')}, default=float)}",
              flush=True)
    return f


def local(arch, factor, hbot=10.0, refine=(1, 1)):
    """The clamp in the local response: the critical joint of the screw-mounted larger board
    cycled between the clamp-only state (cold) and clamp + heat (hot), against the same
    mounting without clamp (cold = stress-free). In a linear global model the clamp leaves
    the cyclic kinematics unchanged; what it adds is a mean load that the creep law sees."""
    import tcpmt_mech_kinematics as KIN
    import tcpmt_mech_submodel as SUB
    r = json.loads((OUTD / f"{tag(arch, factor, hbot, refine)}.json").read_text())
    me = r["mechanics"]
    c = me["screws"]["joint_search"]["critical"]

    def at(case):
        cand = KIN.expand_sites(me[case]["interconnects"]["bga"]["candidates"])
        return next(k for k in cand if abs(k["x_mm"] - c["x_mm"]) < 1e-6
                    and abs(k["y_mm"] - c["y_mm"]) < 1e-6)
    t = f"{arch}_x{factor:g}"
    tasks = [dict(study="board_local", tag=f"{t}_screws_thermal", kin=at("screws"),
                  meta={"arch": arch, "case": "screws (no clamp)"}),
             dict(study="board_local", tag=f"{t}_screws_clamp", kin=at("clamp_screws"),
                  kin_cold=at("clamp_only"), meta={"arch": arch, "case": "clamp, screws"})]
    recs = SUB.run_tasks(tasks)
    out = {t_["tag"]: {"d_eps": (recs.get(t_["tag"]) or {}).get("d_peeq_per_cycle"),
                       "site_mm": [c["x_mm"], c["y_mm"]], "case": t_["meta"]["case"]}
           for t_ in tasks}
    a, b = (out[f"{t}_screws_thermal"]["d_eps"], out[f"{t}_screws_clamp"]["d_eps"])
    out["clamp_effect_rel"] = (b / a - 1) if (a and b) else None
    f = OUTD / f"{tag(arch, factor, hbot, refine)}_local.json"
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


# ------------------------------------------------------------------ the compared state
#: TCPMT round 3 (campaign): the board, mounting and clamp effects on the COMPARED cases of a
#: state (the production state SDEC by default), mechanics only on each case's own converged
#: field (production mesh); results go to board_study/<STATE>_<TIER>_<ARCH>.json
STATE_PLAN_COUPON = ("free", "screws", "screws_pinned", "edge", "clamp_screws", "clamp_only",
                     "clamp_backplate")
STATE_PLAN_LARGE = ("free_ring_hot", "free_ring_cold", "screws_ring_hot",
                    "clamp_screws_ring_hot")


def _state_task(t):
    """One structural solve of the state plan (a pool worker: its own STRUCT_* settings)."""
    import final_closure_physical_etm as E
    name, bc, prm, loads, thermal, mesh_key = t
    m, mats, st, tiles, Tn, wd, arch = _STATE_CTX[mesh_key]
    me = mech_case(E, m, mats, st, Tn, wd, arch, tiles, name, bc, prm, loads, thermal,
                   solver=E.PRODUCTION_SOLVER, threads=int(os.environ.get("FC_THREADS", "2")))
    return name, me


_STATE_CTX = {}


def map_field_to_large(m_small, T_small, m_big, lx, ly, t_ref, ring="hot"):
    """Nodal temperatures on the larger-board mesh from the coupon's converged field: the
    package grid is kept exactly (etm.mesh: same coordinates), so every coupon node maps; a
    board-ring node takes the coupon's board-edge temperature at the same height (ring='hot':
    the adiabatic-edge field extended -- a board fin of this conductance and film decays over
    about 0.1 m, so the ring stays near it) or the stress-free temperature (ring='cold', the
    other bound: a ring that does not heat restrains the most)."""
    import numpy as np
    key = lambda p: (round(float(p[0]), 6), round(float(p[1]), 6), round(float(p[2]), 6))  # noqa
    idx = {key(p): i for i, p in enumerate(m_small.nodes)}
    T = np.empty(m_big.n_nodes)
    n_ring = 0
    for i, p in enumerate(m_big.nodes):
        j = idx.get(key(p))
        if j is not None:
            T[i] = T_small[j]
            continue
        n_ring += 1
        if ring == "cold":
            T[i] = t_ref
            continue
        q = (min(max(p[0], -lx / 2), lx / 2), min(max(p[1], -ly / 2), ly / 2), p[2])
        j = idx.get(key(q))
        if j is None:
            raise RuntimeError(f"board-ring node {tuple(p)} has no coupon edge node at "
                               f"{q} (the package grid was not kept)")
        T[i] = T_small[j]
    return T, n_ring


def state_run(arch, tier, state="SDEC", factor=None, only=None):
    """Board size, mounting and clamp on one compared case, mechanics only on its converged
    field (production mesh, production solver):
      coupon   free (the production restraint: must reproduce the case), screws, pinned
               screws, simply supported edge, the clamp reacted at the screws with and
               without heat, and reacted by a backplate under the package;
      larger   a board `factor` x the package side (configs/tcpmt_mech board) with its ring at
               the coupon's board-edge temperature (hot) or at the stress-free temperature
               (cold), free, on screws, and with the clamp at the screws."""
    import multiprocessing as mp
    import numpy as np
    import final_closure_physical_etm as E
    import final_closure_sensitivity as S
    import production_et as PE
    import tcpmt_mech_production as MP
    from hvr_scratch import path as scratch
    factor = float(factor or max(bcfg()["extent_factor_options"]))
    S.set_state(state)
    base, frd, base_name = S.thermal_base(arch, tier)
    E._raise_stack_limit()
    m, mats, st, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    Tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    if abs(float(np.nanmax(Tn)) - base["thermal"]["T_max_C"]) > 1e-6:
        raise RuntimeError(f"{frd} is not the converged field of {base_name}")
    t_ref = st["structural_bc"]["t_ref"]["value"]
    lx = st["geometry"]["power_substrate"]["size_x"]["value"]
    ly = st["geometry"]["power_substrate"]["size_y"]["value"]
    tg = f"{state}_{tier}_{arch}"
    wd = scratch("mech_board", tg)
    # the larger board: the same builder with the board ring, the coupon field mapped onto it
    os.environ["HVR_BOARD_EXTENT_FACTOR"] = f"{factor:g}"
    os.environ["HVR_BOARD_FAR_H_MM"] = f"{float(bcfg()['far_field_h_max_mm']):g}"
    try:
        mb, matsb, stb, tilesb, _ib = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    finally:
        os.environ.pop("HVR_BOARD_EXTENT_FACTOR", None)
        os.environ.pop("HVR_BOARD_FAR_H_MM", None)
    T_hot, n_ring = map_field_to_large(m, Tn, mb, lx, ly, t_ref, "hot")
    T_cold, _ = map_field_to_large(m, Tn, mb, lx, ly, t_ref, "cold")
    _STATE_CTX.update({"coupon": (m, mats, st, tiles, Tn, wd, arch),
                       "large_hot": (mb, matsb, stb, tilesb, T_hot, wd, arch),
                       "large_cold": (mb, matsb, stb, tilesb, T_cold, wd, arch)})
    mt = bcfg()["mounting"]
    plan = []
    for mesh_key, mm in (("coupon", m), ("large_hot", mb)):
        zb = next(Lr for Lr in mm.layers if Lr.name == "board").z0
        scr = {"inset_mm": float(mt["screw_inset_mm"]), "patch_mm": float(mt["screw_patch_mm"]),
               "z_mm": zb}
        force = float(LAW._val(bcfg()["clamp"]["force_N"]))
        lines, pr, area = clamp_lines(mm, force)
        if mesh_key == "coupon":
            clamp = {"force_N": force, "pressure_MPa": pr, "area_mm2": area}
            plan += [("free", "BC_BOARD", None, None, True, "coupon"),
                     ("screws", "BC_BOARD_SCREWS", scr, None, True, "coupon"),
                     ("screws_pinned", "BC_BOARD_SCREWS_PINNED", scr, None, True, "coupon"),
                     ("edge", "BC_BOARD_EDGE", {"z_mm": zb}, None, True, "coupon"),
                     ("clamp_screws", "BC_BOARD_SCREWS", scr, lines, True, "coupon"),
                     ("clamp_only", "BC_BOARD_SCREWS", scr, lines, False, "coupon"),
                     ("clamp_backplate", "BC_BACKPLATE", {"footprint_half_mm": lx / 2, "z_mm": zb},
                      lines, True, "coupon")]
        else:
            plan += [("free_ring_hot", "BC_BOARD", None, None, True, "large_hot"),
                     ("free_ring_cold", "BC_BOARD", None, None, True, "large_cold"),
                     ("screws_ring_hot", "BC_BOARD_SCREWS", scr, None, True, "large_hot"),
                     ("clamp_screws_ring_hot", "BC_BOARD_SCREWS", scr, lines, True,
                      "large_hot")]
    if only:
        plan = [x for x in plan if x[0] in only]
    res = {"arch": arch, "tier": tier, "state": state, "case": base_name,
           "case_file": MP.rel(S.OUT / base_name) if (S.OUT / base_name).is_file() else base_name,
           "thermal_frd": str(frd),
           "inputs_sha1": MP.inputs_sha1([S.OUT / base_name, frd]),
           "board_extent_factor": factor, "board_side_mm": factor * lx,
           "n_elems": {"coupon": m.n_elems, "large": mb.n_elems},
           "n_ring_nodes": n_ring, "clamp": clamp, "materials": minfo,
           "case_mechanics": {"die_warpage_pv_um": base["mechanics"]["die_warpage_pv_um"],
                              "du_c_um": base["mechanics"]["joint_search"]["critical"]["du_um"],
                              "site_mm": [base["mechanics"]["joint_search"]["critical"]["x_mm"],
                                          base["mechanics"]["joint_search"]["critical"]["y_mm"]],
                              "T_joint_C": base["mechanics"]["joint_search"]["critical"]["T_C"]},
           "ring_rule": map_field_to_large.__doc__.split("\n\n")[0].strip(),
           "mechanics": {}}
    OUTD.mkdir(parents=True, exist_ok=True)
    f = OUTD / f"{tg}.json"
    n = max(1, min(len(plan), int(os.environ.get("FC_POOL_MAX", "1"))))
    with mp.get_context("fork").Pool(n, maxtasksperchild=1) as pool:
        for name, me in pool.imap_unordered(_state_task, plan):
            res["mechanics"][name] = me
            f.write_text(json.dumps(res, indent=1, default=float))
            sm = summary_of(me)
            print(f"{tg} {name}: " + json.dumps({k: sm.get(k) for k in (
                "die_warpage_pv_um", "du_c_um", "site_mm", "wall_s", "error")}, default=float),
                flush=True)
    res["all_solves_ok"] = bool(res["mechanics"]) and all(
        "error" not in me for me in res["mechanics"].values())
    fr = res["mechanics"].get("free") or {}
    if "die_warpage_pv_um" in fr:
        cm = res["case_mechanics"]
        res["free_reproduces_case"] = {
            "warp_rel": fr["die_warpage_pv_um"] / cm["die_warpage_pv_um"] - 1,
            "du_rel": fr["joint_search"]["critical"]["du_um"] / cm["du_c_um"] - 1}
    f.write_text(json.dumps(res, indent=1, default=float))
    return f


def state_et(arch, tier, state="SDEC", factor=None, refine=(1, 1)):
    """Where the larger board's ring really sits between the two bounds of state_run: ONE
    electrothermal fixed point of the compared case (its state's ledger hooks and its cooling
    base, as tcpmt_review_variants runs it) on the board `factor` x the package side, on the
    coarse rung, then free / screws / clamp mechanics on that field; compared with the case's
    own coupon rung (sensitivity/ladder/<case>_r11.json). The Z3 board-plane deposit keeps its
    FV map over the package footprint (the ring takes none of it) and its ledger temperature is
    the whole board's mean, as in the coupon."""
    import final_closure_physical_etm as E
    import tcpmt_cases as TC
    import tcpmt_review_variants as RV
    import tcpmt_uncertainty as TU
    import tcpmt_mech_production as MP
    from hvr_scratch import path as scratch
    factor = float(factor or max(bcfg()["extent_factor_options"]))
    scen = TC.SCEN[state]
    RV.set_scenario(scen)
    RV.apply_tier(arch, tier)
    RV._long_ccx()
    os.environ["HVR_BOARD_EXTENT_FACTOR"] = f"{factor:g}"
    os.environ["HVR_BOARD_FAR_H_MM"] = f"{float(bcfg()['far_field_h_max_mm']):g}"
    rt = f"r{refine[0]}{refine[1]}"
    tg = f"{state}_{tier}_{arch}_x{factor:g}_{rt}"
    E.WD = scratch("mech_board_et", tg)
    E._raise_stack_limit()
    m, mats, st, tiles, minfo, L, th, hist, t_et, wd = E.run_et(arch, scen, E.PRODUCTION_H_XY,
                                                                refine)
    cp = TC.case_path(state, tier, arch)
    coupon_f = TU.ladder_files(cp)[rt] if rt != "r21" else cp
    res = {"arch": arch, "tier": tier, "state": state, "board_extent_factor": factor,
           "board_side_mm": factor * st["geometry"]["power_substrate"]["size_x"]["value"],
           "refine": list(refine), "n_elems": m.n_elems, "materials": minfo,
           "P_loss_w": L["P_loss_w"], "thermal": {k: v for k, v in th.items() if k != "T_node"},
           "et_history": hist, "et_wall_s": t_et,
           "et_converged": (hist[-1]["max_dT_K"] < E.ET_TOL_K
                            and hist[-1]["dP_rel"] < E.ET_TOL_P_REL),
           "coupon_case": MP.rel(coupon_f) if Path(coupon_f).is_file() else None,
           "inputs_sha1": MP.inputs_sha1([coupon_f]), "mechanics": {}}
    OUTD.mkdir(parents=True, exist_ok=True)
    f = OUTD / f"{tg}.json"
    f.write_text(json.dumps(res, indent=1, default=float))
    mt = bcfg()["mounting"]
    zb = next(Lr for Lr in m.layers if Lr.name == "board").z0
    scr = {"inset_mm": float(mt["screw_inset_mm"]), "patch_mm": float(mt["screw_patch_mm"]),
           "z_mm": zb}
    lines, _p, _a = clamp_lines(m, float(LAW._val(bcfg()["clamp"]["force_N"])))
    for name, bc, prm, ld in (("free", "BC_BOARD", None, None),
                              ("screws", "BC_BOARD_SCREWS", scr, None),
                              ("clamp_screws", "BC_BOARD_SCREWS", scr, lines)):
        # the production structural solver: SPOOLES fails on the Z2 larger board (the
        # merged branch's Z2_x3_hb10 lost every solve the same way)
        me = mech_case(E, m, mats, st, th["T_node"], wd, arch, tiles, name, bc, prm, ld, True,
                       solver=E.PRODUCTION_SOLVER,
                       threads=int(os.environ.get("FC_THREADS", "2")))
        res["mechanics"][name] = me
        f.write_text(json.dumps(res, indent=1, default=float))
        sm = summary_of(me)
        print(f"{tg} {name}: " + json.dumps({k: sm.get(k) for k in (
            "die_warpage_pv_um", "du_c_um", "site_mm", "wall_s", "error")}, default=float),
            flush=True)
    res["all_solves_ok"] = bool(res["mechanics"]) and all(
        "error" not in me for me in res["mechanics"].values())
    f.write_text(json.dumps(res, indent=1, default=float))
    os.environ.pop("HVR_BOARD_EXTENT_FACTOR", None)
    os.environ.pop("HVR_BOARD_FAR_H_MM", None)
    return f


def state_local(state="SDEC"):
    """The clamp in the local response of each compared case (v2 model, production law at its
    converged window): the critical joint of the screw-mounted coupon cycled between the
    clamp-only state (cold) and clamp + heat (hot), against the same mounting without clamp."""
    import tcpmt_mech_kinematics as KIN
    import tcpmt_mech_submodel as SUB
    tasks, meta = [], {}
    for f in sorted(OUTD.glob(f"{state}_*_*.json")):
        r = json.loads(f.read_text())
        me = r.get("mechanics") or {}
        if not all(k in me and "joint_search" in me[k] for k in ("screws", "clamp_screws",
                                                                  "clamp_only")):
            continue
        c = me["screws"]["joint_search"]["critical"]

        def at(case, c=c, me=me):
            cand = KIN.expand_sites(me[case]["interconnects"]["bga"]["candidates"])
            return min(cand, key=lambda k: (k["x_mm"] - c["x_mm"]) ** 2
                       + (k["y_mm"] - c["y_mm"]) ** 2)
        t = f.stem
        tasks += [dict(study="board_local", tag=f"{t}_screws_thermal", kin=at("screws"),
                       meta={"case": t, "what": "screws, no clamp"}),
                  dict(study="board_local", tag=f"{t}_screws_clamp", kin=at("clamp_screws"),
                       kin_cold=at("clamp_only"), meta={"case": t, "what": "clamp at the "
                                                                          "screws"})]
        meta[t] = [c["x_mm"], c["y_mm"]]
    recs = SUB.run_tasks(tasks) if tasks else {}
    out = {}
    for t, site in meta.items():
        a = (recs.get(f"{t}_screws_thermal") or {}).get("d_peeq_per_cycle")
        b = (recs.get(f"{t}_screws_clamp") or {}).get("d_peeq_per_cycle")
        out[t] = {"site_mm": site, "d_eps_screws": a, "d_eps_clamp": b,
                  "clamp_effect_rel": (b / a - 1) if (a and b) else None,
                  "card_sha": (recs.get(f"{t}_screws_clamp") or {}).get("card_sha")}
    return out


def state_summarize(state="SDEC", with_local=False):
    """The compared state's board, mounting and clamp effects -> board_study_<state>.json:
    per case, every solve against the case (the production coupon, free) and the change of
    die warpage and critical du, with the uncertainty of the compared outputs for scale."""
    import tcpmt_mech_production as MP
    U = {}
    uf = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / \
        "uncertainty.json"
    if uf.exists():
        uu = json.loads(uf.read_text()).get("U") or {}
        U = {k: v for k, v in uu.items()}
    out = {"what": "board size, mounting and clamp on the compared cases, mechanics only on "
                   "their converged fields (finding 6)", "state": state, "config": bcfg(),
           "cases": {}, "inputs_sha1": {}}
    for f in sorted(OUTD.glob(f"{state}_?_Z?.json")):
        r = json.loads(f.read_text())
        out["inputs_sha1"].update(r.get("inputs_sha1") or {})
        out["inputs_sha1"][str(f.resolve())] = MP.sha1(f)
        cm = r["case_mechanics"]
        rows = {}
        for k, me in (r.get("mechanics") or {}).items():
            sm = summary_of(me)
            if "du_c_um" in sm:
                sm["warp_rel_vs_case"] = sm["die_warpage_pv_um"] / cm["die_warpage_pv_um"] - 1
                sm["du_rel_vs_case"] = sm["du_c_um"] / cm["du_c_um"] - 1
                sm["site_moved"] = (sorted(abs(v) for v in sm["site_mm"])
                                    != sorted(abs(v) for v in cm["site_mm"]))
            rows[k] = sm
        ukey = f"{r['tier']}.{r['arch']}"
        out["cases"][f.stem] = {"arch": r["arch"], "tier": r["tier"], "case": r["case"],
                                "board_side_mm": r["board_side_mm"], "n_elems": r["n_elems"],
                                "clamp": r.get("clamp"), "case_mechanics": cm,
                                "free_reproduces_case": r.get("free_reproduces_case"),
                                "U_case": {"warp": U.get(f"{ukey}.warp"),
                                           "du": U.get(f"{ukey}.du")},
                                "mechanics": rows}
    # the larger board's own field (state_et, coarse rung) against the coupon rung: where the
    # ring sits between the hot-ring and cold-ring bounds of the production-mesh solves
    for f in sorted(OUTD.glob(f"{state}_?_Z?_x*_r*.json")):
        r = json.loads(f.read_text())
        key = f"{state}_{r['tier']}_{r['arch']}"
        c = out["cases"].get(key)
        cf = r.get("coupon_case")
        cp = json.loads((R / cf).read_text()) if cf and (R / cf).is_file() else None
        fr = summary_of((r.get("mechanics") or {}).get("free") or {"error": "missing"})
        if c is None or not cp or "du_c_um" not in fr:
            continue
        out["inputs_sha1"][str(f.resolve())] = MP.sha1(f)
        cm = cp["mechanics"]
        et = {"file": f.name, "refine": r["refine"], "et_converged": r.get("et_converged"),
              "T_max_K": r["thermal"]["T_max_C"] - cp["thermal"]["T_max_C"],
              "P_loss_rel": r["P_loss_w"] / cp["P_loss_w"] - 1,
              "warp_rel": fr["die_warpage_pv_um"] / cm["die_warpage_pv_um"] - 1,
              "du_rel": fr["du_c_um"] / cm["joint_search"]["critical"]["du_um"] - 1}
        for k in ("screws", "clamp_screws"):
            sk = summary_of((r.get("mechanics") or {}).get(k) or {"error": "missing"})
            if "du_c_um" in sk:
                et[f"{k}_warp_rel_vs_free"] = sk["die_warpage_pv_um"] / fr["die_warpage_pv_um"] - 1
                et[f"{k}_du_rel_vs_free"] = sk["du_c_um"] / fr["du_c_um"] - 1
        hot = (c["mechanics"].get("free_ring_hot") or {})
        cold = (c["mechanics"].get("free_ring_cold") or {})
        for y in ("warp", "du"):
            h, cl = hot.get(f"{y}_rel_vs_case"), cold.get(f"{y}_rel_vs_case")
            if h is not None and cl is not None and abs(h - cl) > 1e-12:
                et[f"{y}_position_in_bracket"] = (et[f"{y}_rel"] - cl) / (h - cl)
        c["larger_board_own_field"] = et
    if with_local:
        loc = state_local(state)
        for t, v in loc.items():
            if t in out["cases"]:
                out["cases"][t]["clamp_local"] = v
        out["local_note"] = ("v2 local model, production law at its converged window; cold "
                             "half-cycle at the clamp-only state")
    f = OUTD.parent / f"board_study_{state}.json"
    f.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def baseline(arch, refine):
    import final_closure_physical_etm as E
    f = E.case_path(arch, SCEN, E.PRODUCTION_H_XY, refine)
    return json.loads(f.read_text()) if f.exists() else None, f


def summarize():
    import final_closure_physical_etm as E
    out = {"what": "board size / mounting / clamp / board-bottom cooling (finding 6)",
           "config": bcfg(), "cases": {}}
    U = {}
    uf = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "uncertainty.json"
    if uf.exists():
        rel = json.loads(uf.read_text())["relative"]
        U = {a: {y: rel[a][y]["total"] for y in ("T", "warp", "du")} for a in rel}
    for f in sorted(OUTD.glob("*.json")):
        r = json.loads(f.read_text())
        a, refine = r["arch"], tuple(r["refine"])
        b, bf = baseline(a, refine)
        row = {"file": f.relative_to(R).as_posix(), "board_side_mm": r["board_side_mm"],
               "h_bottom_W_m2K": r["h_bottom_W_m2K"], "n_elems": r["n_elems"],
               "et_wall_s": r["et_wall_s"], "P_loss_w": r["P_loss_w"],
               "T_max_C": r["thermal"]["T_max_C"],
               "q_bot_W": r["thermal"].get("q_bot_W"),
               "mechanics": {k: summary_of(v) for k, v in r["mechanics"].items()},
               "clamp": r.get("clamp")}
        if b:
            bm = b["mechanics"]
            bc = bm["joint_search"]["critical"]
            row["coupon"] = {"file": bf.relative_to(R).as_posix(),
                             "n_elems": b["thermal"]["n_elems"], "et_wall_s": b["et_wall_s"],
                             "mech_wall_s": bm.get("wall_s"), "P_loss_w": b["P_loss_w"],
                             "T_max_C": b["thermal"]["T_max_C"],
                             "die_warpage_pv_um": bm["die_warpage_pv_um"],
                             "du_c_um": bc["du_um"], "site_mm": [bc["x_mm"], bc["y_mm"]],
                             "T_joint_C": bc["T_C"]}
            fr = row["mechanics"].get("free") or {}
            if "du_c_um" in fr:
                d = {"T_max_K": row["T_max_C"] - row["coupon"]["T_max_C"],
                     "P_loss_rel": row["P_loss_w"] / row["coupon"]["P_loss_w"] - 1,
                     "warp_rel": fr["die_warpage_pv_um"] / row["coupon"]["die_warpage_pv_um"] - 1,
                     "du_rel": fr["du_c_um"] / row["coupon"]["du_c_um"] - 1,
                     # a mirror-image twin (+-x, +-y swapped) is the same site
                     "site_moved": sorted(abs(v) for v in fr["site_mm"])
                     != sorted(abs(v) for v in row["coupon"]["site_mm"])}
                u = U.get(a, {})
                d["exceeds_2U"] = {
                    "T": abs(d["T_max_K"]) > 2 * u.get("T", 0) * (row["coupon"]["T_max_C"] - 25),
                    "warp": abs(d["warp_rel"]) > 2 * u.get("warp", 0),
                    "du": abs(d["du_rel"]) > 2 * u.get("du", 0)} if u else None
                d["cost_elements_x"] = row["n_elems"] / row["coupon"]["n_elems"]
                d["cost_et_wall_x"] = row["et_wall_s"] / max(row["coupon"]["et_wall_s"], 1)
                row["larger_board_vs_coupon"] = d
            for k in ("screws", "screws_pinned", "edge", "clamp_screws", "clamp_backplate"):
                mk = row["mechanics"].get(k) or {}
                if "du_c_um" in mk and "du_c_um" in fr:
                    mk["du_rel_vs_free"] = mk["du_c_um"] / fr["du_c_um"] - 1
                    mk["warp_rel_vs_free"] = mk["die_warpage_pv_um"] / fr["die_warpage_pv_um"] - 1
        out["cases"][f.stem] = row
    out["recommendation"] = recommend(out["cases"])
    SUMMARY.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return out


def recommend(cases):
    """Production if the larger board moves a compared output beyond twice its numerical
    uncertainty in any architecture at an affordable cost; otherwise a sensitivity."""
    rows = [c for c in cases.values() if c.get("larger_board_vs_coupon")]
    if not rows:
        return {"verdict": None, "basis": "no larger-board case summarized"}
    exceed = [k for k, c in cases.items() if c.get("larger_board_vs_coupon")
              and any((c["larger_board_vs_coupon"].get("exceeds_2U") or {}).values())]
    cost = max(c["larger_board_vs_coupon"]["cost_elements_x"] for c in rows)
    ranks = {}
    for k, c in cases.items():
        d = c.get("larger_board_vs_coupon")
        if d:
            ranks[k] = {"du_rel": d["du_rel"], "warp_rel": d["warp_rel"], "T_max_K": d["T_max_K"]}
    verdict = "production" if exceed and cost <= 2.0 else "sensitivity"
    return {"verdict": verdict, "cases_exceeding_2U": exceed, "max_element_cost_x": cost,
            "effects": ranks,
            "rule": "production when the larger board moves T_max, die warpage or the "
                    "critical du by more than twice the production numerical uncertainty "
                    "(uncertainty.json) in any architecture and costs at most 2x the "
                    "elements; otherwise kept as a declared sensitivity"}


def main():
    if sys.argv[1:2] == ["run"]:
        arch = sys.argv[2]
        factor = float(sys.argv[sys.argv.index("--factor") + 1]) if "--factor" in sys.argv \
            else max(bcfg()["extent_factor_options"])
        hbot = float(sys.argv[sys.argv.index("--hbot") + 1]) if "--hbot" in sys.argv else 10.0
        r = sys.argv[sys.argv.index("--refine") + 1] if "--refine" in sys.argv else "11"
        print(run(arch, factor, hbot, (int(r[0]), int(r[1]))))
    elif sys.argv[1:2] == ["local"]:
        factor = float(sys.argv[sys.argv.index("--factor") + 1]) if "--factor" in sys.argv \
            else max(bcfg()["extent_factor_options"])
        print(json.dumps(local(sys.argv[2], factor), indent=1, default=float))
    elif sys.argv[1:2] == ["summarize"]:
        s = summarize()
        print(json.dumps(s["recommendation"], indent=1, default=float))
    elif sys.argv[1:2] == ["state"]:
        # python tcpmt_mech_board.py state ARCH TIER [--state SDEC] [--factor 3] [--only a,b]
        st = sys.argv[sys.argv.index("--state") + 1] if "--state" in sys.argv else "SDEC"
        fac = float(sys.argv[sys.argv.index("--factor") + 1]) if "--factor" in sys.argv \
            else None
        only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv \
            else None
        print(state_run(sys.argv[2], sys.argv[3], st, fac, only))
    elif sys.argv[1:2] == ["state-et"]:
        # python tcpmt_mech_board.py state-et ARCH TIER [--state SDEC] [--factor 3] [--refine 11]
        st = sys.argv[sys.argv.index("--state") + 1] if "--state" in sys.argv else "SDEC"
        fac = float(sys.argv[sys.argv.index("--factor") + 1]) if "--factor" in sys.argv \
            else None
        r = sys.argv[sys.argv.index("--refine") + 1] if "--refine" in sys.argv else "11"
        print(state_et(sys.argv[2], sys.argv[3], st, fac, (int(r[0]), int(r[1]))))
    elif sys.argv[1:2] == ["state-summarize"]:
        # python tcpmt_mech_board.py state-summarize [--state SDEC] [--local]
        st = sys.argv[sys.argv.index("--state") + 1] if "--state" in sys.argv else "SDEC"
        s = state_summarize(st, "--local" in sys.argv)
        for k, c in s["cases"].items():
            print(k, {n: (round(v.get("warp_rel_vs_case", float("nan")), 4),
                          round(v.get("du_rel_vs_case", float("nan")), 4))
                      for n, v in c["mechanics"].items()}, c.get("clamp_local"))


if __name__ == "__main__":
    main()
