#!/usr/bin/env python3
"""TCPMT revision -- complete-package thermal cross-check of the production model.

A reviewer asked for at least one COMPLETE-PACKAGE check of the production thermal model
against an independent solver; until now only unit cells were checked (reference_thermal_
column_moose_*.json). This script solves one verification problem, identical in both codes:

  geometry, mesh, materials  the production package of the architecture, built by
        final_closure_physical_etm.build at the production mesh (h_xy = 1.1 mm, refine (2, 1));
  heat  the converged HV-S0 deposits, deposits_from_ledger(arch, case ledger_rows), on the
        same elements, as uniform body sources;
  top   a UNIFORM film: the production coefficient CANDIDATES[COOLER].h_uniform(Q) at the
        dissipated power Q, against the coolant INLET temperature (the production deck has
        the same h but warms the sink along the flow);
  bottom the production natural-convection film (h_bottom at ambient_bottom) on the board
        underside; Z3 also keeps its production converter-underside cold plate
        (z3_converter_cold_plate: the top plate's h at the inlet temperature).

CalculiX solves it through the production functions (write_thermal -> ccxio.run_ccx), the
streamwise top film replaced by the uniform one; one output request (*NODE PRINT, NT) is
appended so the nodal temperatures carry 7 significant digits (the .frd carries 6). MOOSE
(heat_transfer-opt) solves the SAME deck, exported block-for-block (tcpmt_fullpkg_moose),
on the identical mesh and on a uniformly refined copy (every hex split 2 x 2 x 2); --ladder
adds a third nested level (n x n x n) and the observed-order Richardson estimate. An input
audit recomputes every conductivity, source density and film face from the model objects
with independent code and compares them with the deck.

Usage:  tcpmt_fullpkg_verify.py ARCH [ARCH ...] [--repeats N] [--no-refined]
        tcpmt_fullpkg_verify.py ARCH --ladder 3   (after the run above: the 3x3x3 level)
        tcpmt_fullpkg_verify.py --side           (two production-model observations)
        tcpmt_fullpkg_verify.py --summarize      (rebuild the summary block only)
Writes research/tcpmt_revision/fullpkg_verification.json (merged per architecture), and the
MOOSE inputs and log tails under research/tcpmt_revision/fullpkg_verification/<ARCH>/.
Environment: HVR_SCRATCH for the solver work directories; nice -n 10 on the shared host.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402
import production_et as PE                                          # noqa: E402
from cooling_production import CANDIDATES                           # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402
import tcpmt_fullpkg_moose as MX                                    # noqa: E402

OUT = R / "research" / "tcpmt_revision" / "fullpkg_verification.json"
EVID = R / "research" / "tcpmt_revision" / "fullpkg_verification"
CORES = 8                     # the host is shared: at most 8 cores for either solver
SCEN = "HV_S0"


def case_file(arch):
    return E.case_path(arch, SCEN)          # the production mesh (h1.1, r21)


# ---------------------------------------------------------------------------
# the verification problem
# ---------------------------------------------------------------------------

def define(arch):
    # the verification problem has UNIFORM sinks at the inlet temperature everywhere (top
    # film and, for Z3, the converter plate): the uniform-sink coefficient (with R_cal) is the
    # consistent one there, so the Z3 plate is written in that form (TCPMT revision: the
    # production plates resolve their sink along the flow instead)
    E.BOTTOM_PLATE_RULE = "fixed_flow_legacy"
    case = json.loads(case_file(arch).read_text())
    if not (E.current_lineage(case) and case.get("et_converged")):
        raise RuntimeError(f"{case_file(arch).name} is not a converged current-lineage case")
    t0 = time.time()
    m, mats, st, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    t_build = time.time() - t0
    if m.n_elems != case["thermal"]["n_elems"] or m.n_nodes != case["thermal"]["n_nodes"]:
        raise RuntimeError("the rebuilt mesh is not the production case's mesh")
    dep = E.deposits_from_ledger(arch, {"rows": case["ledger_rows"]})
    Q = float(sum(dep.values()))
    if abs(Q - case["thermal"]["Q_ledger_W"]) > 1e-9 * Q:
        raise RuntimeError("deposits do not reproduce the case's ledger total")
    cooler = CANDIDATES[E.COOLER]
    tb = st["thermal_bc"]
    return {"arch": arch, "case": case, "m": m, "mats": mats, "st": st, "tiles": tiles,
            "minfo": minfo, "dep": dep, "Q": Q, "h_u": float(cooler.h_uniform(Q)),
            "t_in": float(cooler.t_in_c), "h_bot": float(tb["h_bottom"]["value"]),
            "t_amb": float(tb["ambient_bottom"]["value"]), "t_build_s": t_build}


def film_namer(D):
    hb = D["h_bot"] * PE.W_M2K_TO_W_MM2K

    def name(face, t, h):
        if face == "F2":
            return "top"
        return "bottom" if abs(h - hb) <= 1e-12 * hb else "plate"
    return name


# ---------------------------------------------------------------------------
# CalculiX through the production functions
# ---------------------------------------------------------------------------

def read_dat_temperatures(path, n):
    """The last 'temperatures for set NALL' block of a CalculiX .dat file."""
    T, blk = None, None
    for line in path.read_text().splitlines():
        if "temperatures for set" in line:
            blk = np.full(n, np.nan)
            T = blk
            continue
        if blk is not None:
            s = line.split()
            if len(s) == 2:
                try:
                    blk[int(s[0]) - 1] = float(s[1])
                except ValueError:
                    blk = None
            elif s:
                blk = None
    if T is None or np.isnan(T).any():
        raise RuntimeError(f"incomplete nodal temperatures in {path}")
    return T


def run_calculix(D, wd, repeats):
    m = D["m"]
    wd.mkdir(parents=True, exist_ok=True)
    top = PE.ccxio.top_film_faces(m)
    deck = wd / "fullpkg_ccx.inp"
    t0 = time.time()
    info = E.write_thermal(m, D["mats"], D["st"], D["dep"], np.full(len(top), D["h_u"]),
                           np.full(len(top), D["t_in"]), deck, D["tiles"], arch=D["arch"])
    t_write = time.time() - t0
    txt, tail = deck.read_text(), "*NODE FILE\nNT\n*END STEP\n"
    if not txt.endswith(tail):
        raise RuntimeError("unexpected end of the production deck")
    deck.write_text(txt[:-len(tail)] + "*NODE FILE\nNT\n*NODE PRINT, NSET=NALL\nNT\n"
                    "*END STEP\n")
    walls, reported, log = [], [], ""
    for rep in range(repeats + 1):              # rep 0 = warm-up, untimed (unless alone)
        for ext in (".frd", ".dat"):
            deck.with_suffix(ext).unlink(missing_ok=True)
        t0 = time.time()
        log = PE.ccxio.run_ccx(deck, threads=CORES)
        dt = time.time() - t0
        if rep or repeats == 0:
            walls.append(dt)
            t_rep = re.findall(r"Total CalculiX Time:\s*([0-9.]+)", log)
            reported.append(float(t_rep[-1]) if t_rep else None)
    T_frd = PE.ccxio.read_frd(deck.with_suffix(".frd"))["NDTEMP"][1:m.n_nodes + 1, 0]
    T_dat = read_dat_temperatures(deck.with_suffix(".dat"), m.n_nodes)
    solver = [ln.strip() for ln in log.splitlines()
              if "solver" in ln.lower() or "cpu" in ln.lower()][:6]
    np.savez(wd / "ccx_T.npz", T_dat=T_dat, T_frd=T_frd)
    return {"T": T_dat, "T_frd": T_frd, "deck": deck, "deposited_W": info["deposited_w"],
            "t_write_deck_s": t_write, "walls_s": walls, "ccx_reported_s": reported,
            "newton_iterations": len(re.findall(r"^ iteration \d+", log, flags=re.M)),
            "threads": CORES,
            "log_solver_lines": solver,
            "frd_vs_dat_max_abs_K": float(np.max(np.abs(T_frd - T_dat)))}


# ---------------------------------------------------------------------------
# independent input audit (model objects vs the deck CalculiX solved)
# ---------------------------------------------------------------------------

def _rel(a, b):
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))


def audit(D, deck, P):
    m, mats, tiles = D["m"], D["mats"], D["tiles"]
    out = {"node_coord_max_abs_mm": float(np.max(np.abs(deck["xyz"] - m.nodes))),
           "connectivity_identical": bool(np.array_equal(deck["hexes"], m.elems)),
           "material_labels_identical": bool(all(
               a.upper() == b for a, b in zip(m.elem_material, deck["material"])))}
    k_model = np.array([(mats[x].k_ortho or [mats[x].k] * 3) for x in m.elem_material],
                       float) * 1e-3                                  # W/mK -> W/(mm K)
    k_deck = np.array([deck["conductivity"][x] for x in deck["material"]], float)
    out["conductivity_max_rel"] = _rel(k_deck, k_model)
    # heat: region = layer LABEL (not the z-range test production uses) and, for in-cell
    # deposits, element centroid inside a cell footprint; density = W / region volume
    V = m.elem_volumes()
    cen = m.elem_centroids()
    in_cell = np.zeros(m.n_elems, bool)
    for t in tiles:
        in_cell |= ((np.abs(cen[:, 0] - t.cx) <= t.ax / 2 + 1e-9)
                    & (np.abs(cen[:, 1] - t.cy) <= t.ay / 2 + 1e-9))
    lay = np.asarray(m.elem_layer, dtype=object)
    q_model = np.zeros(m.n_elems)
    regions = []
    for (layers, it), w in D["dep"].items():
        sel = np.isin(lay, list(layers)) & (in_cell if it else True)
        q_model[sel] += w / V[sel].sum()        # '+=': an overlap would show as a mismatch
        regions.append({"layers": list(layers), "in_cells": bool(it), "W": float(w),
                        "n_elems": int(sel.sum()), "volume_mm3": float(V[sel].sum()),
                        "q_W_mm3": float(w / V[sel].sum())})
    q_deck = np.zeros(m.n_elems)
    for name, q in deck["dflux"]:
        q_deck[deck["elsets"][name] - 1] = q
    nz = q_model > 0
    out.update({"source_support_identical": bool(np.array_equal(nz, q_deck > 0)),
                "source_density_max_rel": _rel(q_deck[nz], q_model[nz]),
                "deposited_W_on_deck_mesh": float(np.sum(
                    q_deck * MX.elem_volumes(deck["xyz"], deck["hexes"]))),
                "deposited_W_model": float(np.sum(q_model * V)), "Q_ledger_W": D["Q"],
                "regions": regions})
    # films: faces found geometrically, coefficients from the model
    z = m.nodes[:, 2]
    ztop_e, zbot_e = z[m.elems[:, 4:] - 1], z[m.elems[:, :4] - 1]
    zmax, zmin = z.max(), z.min()
    exp = {"top": (np.flatnonzero(np.all(np.abs(ztop_e - zmax) < 1e-9, 1)) + 1,
                   D["h_u"], D["t_in"])}
    if D["arch"] == "Z3":
        board = np.flatnonzero(lay == "board")
        zb0 = zbot_e[board].min()
        on = board[np.all(np.abs(zbot_e[board] - zb0) < 1e-9, 1)]
        covered = {tuple(sorted(r)) for r in m.elems[:, 4:]}
        exp["bottom"] = (np.array([e + 1 for e in on
                                   if tuple(sorted(m.elems[e, :4])) not in covered]),
                         D["h_bot"], D["t_amb"])
        exp["plate"] = (np.flatnonzero(np.all(np.abs(zbot_e - zmin) < 1e-9, 1)) + 1,
                        D["h_u"], D["t_in"])
    else:
        exp["bottom"] = (np.flatnonzero(np.all(np.abs(zbot_e - zmin) < 1e-9, 1)) + 1,
                         D["h_bot"], D["t_amb"])
    films = {}
    for s in P["sidesets"]:
        e_exp, h_exp, t_exp = exp[s["name"]]
        films[s["name"]] = {
            "face": s["face"], "n_faces": int(len(s["elems"])),
            "faces_identical": bool(np.array_equal(np.sort(e_exp), s["elems"])),
            "h_W_m2K": s["h_W_mm2K"] / PE.W_M2K_TO_W_MM2K, "T_inf_C": s["T_inf_C"],
            "h_rel_err": abs(s["h_W_mm2K"] / (h_exp * PE.W_M2K_TO_W_MM2K) - 1),
            "T_abs_err_K": abs(s["T_inf_C"] - t_exp),
            "area_mm2": float(MX.face_areas(P["xyz"], P["hexes"], s["elems"]).sum())}
    out["films"] = films
    out["films_complete"] = sorted(films) == sorted(exp)
    out["passed"] = bool(
        out["connectivity_identical"] and out["material_labels_identical"]
        and out["node_coord_max_abs_mm"] <= 5.0001e-7 and out["conductivity_max_rel"] < 1e-5
        and out["source_support_identical"] and out["source_density_max_rel"] < 1e-8
        and out["films_complete"]
        and all(f["faces_identical"] and f["h_rel_err"] < 1e-8 and f["T_abs_err_K"] < 1e-6
                for f in films.values()))
    return out


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def film_heat(P, T):
    q = {}
    for s in P["sidesets"]:
        c = list(MX.FACE_NODES[s["face"]])
        tf = T[P["hexes"][s["elems"] - 1][:, c] - 1].mean(axis=1)
        a = MX.face_areas(P["xyz"], P["hexes"], s["elems"])
        q[s["name"]] = float(np.sum(s["h_W_mm2K"] * a * (tf - s["T_inf_C"])))
    return q


def layer_groups(m, arch):
    names = [L.name for L in m.layers]
    conv = [n for n in names if n.startswith(("z1conv_", "z3conv_", "conv_"))]
    g = {n: [n] for n in names}
    g["converter_all_tiers"] = conv
    g["substrate"] = [n for n in ("sub_lower", "tile_band") if n in names]
    return g


def metrics(P, T, elem_layer, groups, regions_elems=None, t_ref=25.0):
    """T_max, volume-averaged layer/group/region temperatures (exact for trilinear bricks:
    the mean over a brick of a trilinear field is the mean of its corner values)."""
    V = MX.elem_volumes(P["xyz"], P["hexes"])
    Te = T[P["hexes"] - 1].mean(axis=1)
    i = int(np.argmax(T))
    out = {"T_max_C": float(T[i]), "T_max_rise_K": float(T[i] - t_ref),
           "T_max_xyz_mm": [float(v) for v in P["xyz"][i]],
           "T_min_C": float(T.min()),
           "T_volume_mean_C": float(np.sum(V * Te) / np.sum(V)),
           "layer_volume_mean_C": {}, "region_volume_mean_C": {}}
    for g, layers in groups.items():
        sel = np.isin(elem_layer, layers)
        out["layer_volume_mean_C"][g] = float(np.sum(V[sel] * Te[sel]) / np.sum(V[sel]))
    for k, ids in (regions_elems or {}).items():
        out["region_volume_mean_C"][k] = float(np.sum(V[ids - 1] * Te[ids - 1])
                                               / np.sum(V[ids - 1]))
    return out


def nodal_means(D, T, groups):
    """The production conventions on the production mesh: layer_mean_T-style node means of
    the layer's element nodes, and the ledger temperature regions (region_nodes)."""
    m, lay = D["m"], np.asarray(D["m"].elem_layer, dtype=object)
    out = {"layer_node_mean_C": {}, "ledger_region_node_mean_C": {}}
    for g, layers in groups.items():
        nodes = np.unique(m.elems[np.isin(lay, layers)].ravel())
        out["layer_node_mean_C"][g] = float(T[nodes - 1].mean())
    for k, (layers, it) in E.temperature_regions(D["arch"]).items():
        nodes = E.region_nodes(m, D["tiles"], layers, it)
        out["ledger_region_node_mean_C"][k] = float(T[nodes - 1].mean())
    return out


def diff_dict(a, b):
    return {k: a[k] - b[k] for k in a if k in b}


def field_diff(Ta, Tb, rise):
    d = Ta - Tb
    i = int(np.argmax(np.abs(d)))
    return {"max_abs_K": float(np.abs(d[i])), "rms_K": float(np.sqrt(np.mean(d * d))),
            "mean_K": float(d.mean()), "max_abs_rel_to_rise": float(np.abs(d[i]) / rise),
            "rms_rel_to_rise": float(np.sqrt(np.mean(d * d)) / rise), "argmax_node": i + 1}


def timing(walls):
    return {"median_s": statistics.median(walls), "min_s": min(walls), "max_s": max(walls),
            "repeats": len(walls), "walls_s": walls}


def _load():
    return [round(x, 1) for x in os.getloadavg()]


# ---------------------------------------------------------------------------
# one architecture
# ---------------------------------------------------------------------------

def run_arch(arch, repeats, do_refined):
    wd = scratch("fullpkg", arch)
    load0 = _load()
    D = define(arch)
    m = D["m"]
    rise_ref = D["t_in"]
    print(f"[{arch}] mesh {m.n_elems} hex / {m.n_nodes} nodes, Q = {D['Q']:.4f} W, "
          f"h_u = {D['h_u']:.2f} W/m2K", flush=True)

    # --- CalculiX (production functions) -------------------------------------------
    cx = run_calculix(D, wd / "ccx", repeats)
    print(f"[{arch}] CalculiX T_max {cx['T'].max():.5f} C, walls {cx['walls_s']}", flush=True)

    # --- the deck as MOOSE sees it ---------------------------------------------------
    deck = MX.parse_deck(cx["deck"])
    P = MX.export_problem(deck, film_namer(D))
    aud = audit(D, deck, P)
    print(f"[{arch}] input audit passed = {aud['passed']}", flush=True)
    lay = np.asarray(m.elem_layer, dtype=object)
    groups = layer_groups(m, arch)
    reg_el = {k: E._region_elems(m, layers, it, D["tiles"])
              for k, (layers, it) in E.temperature_regions(arch).items()}

    # --- MOOSE on the identical mesh ---------------------------------------------------
    mw = wd / "moose_base"
    mw.mkdir(parents=True, exist_ok=True)
    gm = MX.write_gmsh(P, mw / "fullpkg.msh")
    sol = {}
    for solver in ("hypre", "mumps"):            # AMG (primary) and a direct-LU check
        stem = f"fullpkg_{solver}"
        (mw / f"{stem}.i").write_text(MX.moose_input(P, "fullpkg.msh", solver))
        runs = [MX.run_moose(mw, f"{stem}.i", CORES) for _ in range(repeats + 1)]
        mo = MX.read_moose(mw, stem)
        T, dmap = MX.map_to_nodes(P["xyz"], mo["xyz"], mo["T"])
        sol[solver] = {"T": T, "pp": mo["pp"], "runs": runs, "dmap": dmap}
        print(f"[{arch}] MOOSE base ({solver}) T_max {T.max():.6f} C, walls "
              f"{[round(r['wall_s'], 1) for r in runs]}", flush=True)
    T_mo, mo, dmap = sol["hypre"]["T"], sol["hypre"], sol["hypre"]["dmap"]

    T_cx = cx["T"]
    rise = float(T_cx.max() - rise_ref)
    met_cx = metrics(P, T_cx, lay, groups, reg_el, rise_ref)
    met_mo = metrics(P, T_mo, lay, groups, reg_el, rise_ref)
    nm_cx, nm_mo = nodal_means(D, T_cx, groups), nodal_means(D, T_mo, groups)
    q_cx, q_mo = film_heat(P, T_cx), film_heat(P, T_mo)
    q_dep = aud["deposited_W_on_deck_mesh"]
    pp = mo["pp"]
    q_mo_pp = {s["name"]: s["h_W_mm2K"] * (pp[f"intT_{s['name']}"]
                                          - s["T_inf_C"] * pp[f"area_{s['name']}"])
               for s in P["sidesets"]}
    base = {
        "T_max_C": {"calculix": met_cx["T_max_C"], "moose": met_mo["T_max_C"],
                    "moose_postprocessor": pp["Tmax"]},
        "T_max_err_K": met_cx["T_max_C"] - met_mo["T_max_C"],
        "T_max_err_rel_to_rise": (met_cx["T_max_C"] - met_mo["T_max_C"]) / rise,
        "field_ccx_minus_moose": field_diff(T_cx, T_mo, rise),
        "layer_volume_mean_err_K": diff_dict(met_cx["layer_volume_mean_C"],
                                             met_mo["layer_volume_mean_C"]),
        "layer_node_mean_err_K": diff_dict(nm_cx["layer_node_mean_C"],
                                           nm_mo["layer_node_mean_C"]),
        "ledger_region_node_mean_err_K": diff_dict(nm_cx["ledger_region_node_mean_C"],
                                                   nm_mo["ledger_region_node_mean_C"]),
        "energy": {"Q_ledger_W": D["Q"], "Q_deposited_on_deck_mesh_W": q_dep,
                   "note": "the deck prints node coordinates to 1e-6 mm, so the power "
                           "deposited on the solved mesh differs from the ledger total by "
                           f"{(q_dep - D['Q']) / D['Q']:+.2e} (relative); both codes solve "
                           "the deck",
                   "calculix": {"q_films_W": q_cx,
                                "residual_rel_to_ledger": (sum(q_cx.values()) - D["Q"]) / D["Q"],
                                "residual_rel_to_deposited":
                                    (sum(q_cx.values()) - q_dep) / q_dep},
                   "moose": {"q_films_W": q_mo, "q_films_from_side_integrals_W": q_mo_pp,
                             "residual_rel_to_ledger": (sum(q_mo.values()) - D["Q"]) / D["Q"],
                             "residual_rel_to_deposited":
                                 (sum(q_mo.values()) - q_dep) / q_dep}},
        "node_map_max_dist_mm": dmap,
        "calculix_output_resolution_K": float(10 ** (np.floor(np.log10(T_cx.max())) - 6)),
    }
    base["max_abs_layer_err_K"] = max(abs(v) for v in base["layer_volume_mean_err_K"].values())
    res = {
        "arch": arch, "scenario": SCEN, "variant": D["case"].get("architecture_variant"),
        "problem": {
            "case_file": str(case_file(arch).relative_to(R)),
            "production_T_max_C_streamwise_film": D["case"]["thermal"]["T_max_C"],
            "P_loss_W": D["case"]["P_loss_w"], "Q_dissipated_W": D["Q"],
            "deposits": aud.pop("regions"),
            "top_film": {"h_W_m2K": D["h_u"], "T_inf_C": D["t_in"],
                         "source": f"cooling_production.CANDIDATES['{E.COOLER}']"
                                   f".h_uniform(Q) at t_in_c"},
            "bottom_film": {"h_W_m2K": D["h_bot"], "T_inf_C": D["t_amb"],
                            "source": "stack thermal_bc h_bottom / ambient_bottom"},
            "mesh": {"h_xy_mm": E.PRODUCTION_H_XY, "refine": list(E.PRODUCTION_REFINE),
                     "label": E.production_label(), "n_elems": int(m.n_elems),
                     "n_nodes": int(m.n_nodes), "n_layers": len(m.layers),
                     "materials": sorted(set(map(str, m.elem_material)))},
        },
        "input_audit": aud,
        "moose_mesh": {"format": "Gmsh 2.2 ASCII", **gm,
                       "blocks": [{k: b[k] for k in ("name", "material", "n_elems")}
                                  | {"k_W_mmK": P["conductivity"][b["material"]],
                                     "q_W_mm3": (None if b["source"] is None else
                                                 P["sources"][b["source"]]["q_W_mm3"])}
                                  for b in P["blocks"]],
                       "sidesets": [{"name": s["name"], "face": s["face"],
                                     "n_faces": int(len(s["elems"])),
                                     "h_W_mm2K": s["h_W_mm2K"], "T_inf_C": s["T_inf_C"]}
                                    for s in P["sidesets"]]},
        "calculix": {**{k: cx[k] for k in ("deposited_W", "t_write_deck_s", "threads",
                                           "ccx_reported_s", "newton_iterations",
                                           "log_solver_lines", "frd_vs_dat_max_abs_K")},
                     "solver": "CalculiX 2.23 default (SPOOLES), *HEAT TRANSFER, STEADY STATE",
                     "timing": timing(cx["walls_s"]), "metrics": met_cx,
                     "production_conventions": nm_cx},
        "moose_base": {"metrics": met_mo, "production_conventions": nm_mo,
                       "ranks": CORES,
                       "solver": "NEWTON; GMRES(300) + hypre BoomerAMG, l_tol 1e-12 (primary)",
                       "solver_check_mumps": {
                           "solver": "NEWTON; PETSc LU (MUMPS)",
                           "max_abs_T_hypre_minus_mumps_K": float(np.max(np.abs(
                               sol["hypre"]["T"] - sol["mumps"]["T"])))},
                       "runs": {k: {"timing": timing([r["wall_s"] for r in v["runs"][1:]]
                                                     if repeats else
                                                     [v["runs"][0]["wall_s"]]),
                                    "moose_reported_s": [r["moose_reported_s"]
                                                         for r in v["runs"]],
                                    "solve_s": [r["solve_s"] for r in v["runs"]],
                                    "nonlinear_residuals": v["runs"][-1]["nonlinear_residuals"],
                                    "linear_its": v["runs"][-1]["linear_its_last"]}
                                for k, v in sol.items()}},
        "identical_mesh": base,
    }
    shutil.rmtree(EVID / arch, ignore_errors=True)
    (EVID / arch).mkdir(parents=True, exist_ok=True)
    for solver in sol:
        shutil.copy(mw / f"fullpkg_{solver}.i", EVID / arch / f"base_{solver}.i")
        (EVID / arch / f"base_{solver}_log_tail.txt").write_text(
            sol[solver]["runs"][-1]["log_tail"])

    # --- MOOSE on the uniformly refined copy ------------------------------------------
    if do_refined:
        F = MX.refine_uniform(P)
        fw = wd / "moose_refined"
        fw.mkdir(parents=True, exist_ok=True)
        gf = MX.write_gmsh(F, fw / "fullpkg.msh")
        (fw / "fullpkg_hypre.i").write_text(MX.moose_input(F, "fullpkg.msh", "hypre"))
        print(f"[{arch}] refined mesh {gf['n_hex']} hex / {gf['n_nodes']} nodes", flush=True)
        rf = MX.run_moose(fw, "fullpkg_hypre.i", CORES)
        mf = MX.read_moose(fw, "fullpkg_hypre")
        T_f, dmf = MX.map_to_nodes(F["xyz"], mf["xyz"], mf["T"])
        lay_f = lay[F["parent"] - 1]
        reg_f = {k: ((ids - 1)[:, None] * 8 + np.arange(8)[None, :]).ravel() + 1
                 for k, ids in reg_el.items()}
        met_f = metrics(F, T_f, lay_f, groups, reg_f, rise_ref)
        q_f = film_heat(F, T_f)
        qe = np.zeros(len(P["hexes"]))
        for name, qv in deck["dflux"]:
            qe[deck["elsets"][name] - 1] = qv
        q_dep_f = float(np.sum(qe[F["parent"] - 1] * MX.elem_volumes(F["xyz"], F["hexes"])))
        T_f_base = T_f[F["base_node_in_fine"] - 1]
        rise_f = met_f["T_max_C"] - rise_ref
        dT = met_mo["T_max_C"] - met_f["T_max_C"]
        res["moose_refined"] = {
            "mesh": {"format": "Gmsh 2.2 ASCII", **gf,
                     "construction": "every production hex split 2x2x2 at its edge midpoints "
                                     "(strictly nested; blocks, sources and films inherited)"},
            "metrics": met_f, "q_films_W": q_f,
            "energy_residual_rel_to_deposited": (sum(q_f.values()) - q_dep_f) / q_dep_f,
            "Q_deposited_W": q_dep_f,
            "timing": timing([rf["wall_s"]]), "moose_reported_s": rf["moose_reported_s"],
            "solve_s": rf["solve_s"], "nonlinear_residuals": rf["nonlinear_residuals"],
            "linear_its": rf["linear_its_last"], "ranks": CORES,
            "solver": "NEWTON; GMRES(300) + hypre BoomerAMG, l_tol 1e-12",
            "node_map_max_dist_mm": dmf}
        res["discretization_change"] = {
            "what": "MOOSE on the production mesh minus MOOSE on its uniform 2x2x2 refinement "
                    "(identical problem); the production CalculiX solve equals the former",
            "T_max_change_K": dT, "T_max_change_rel_to_rise": dT / rise_f,
            "T_max_production_mesh_minus_extrapolated_K_if_p2": dT * 4.0 / 3.0,
            "layer_volume_mean_change_K": diff_dict(met_mo["layer_volume_mean_C"],
                                                    met_f["layer_volume_mean_C"]),
            "region_volume_mean_change_K": diff_dict(met_mo["region_volume_mean_C"],
                                                     met_f["region_volume_mean_C"]),
            "field_at_production_nodes": field_diff(T_mo, T_f_base, rise_f),
            "calculix_vs_refined_moose": {
                "T_max_K": met_cx["T_max_C"] - met_f["T_max_C"],
                "field_at_production_nodes": field_diff(T_cx, T_f_base, rise_f)}}
        res["discretization_change"]["max_abs_layer_change_K"] = max(
            abs(v) for v in res["discretization_change"]["layer_volume_mean_change_K"].values())
        shutil.copy(fw / "fullpkg_hypre.i", EVID / arch / "refined_hypre.i")
        (EVID / arch / "refined_hypre_log_tail.txt").write_text(rf["log_tail"])
        print(f"[{arch}] MOOSE refined T_max {met_f['T_max_C']:.5f} C "
              f"(change {dT:+.4f} K), wall {rf['wall_s']:.1f} s", flush=True)
    res["load_average"] = {"before": load0, "after": _load()}
    return res


# ---------------------------------------------------------------------------
# a third level: MOOSE on the n x n x n refinement, and the three-level estimate
# ---------------------------------------------------------------------------

def richardson3(f1, f2, f3, r2, r3):
    """Generalized Richardson from levels h, h/r2, h/r3 (r3 > r2 > 1): the observed order p
    solves (f1 - f2)/(f2 - f3) = (1 - r2^-p)/(r2^-p - r3^-p); None if not monotone."""
    d12, d23 = f1 - f2, f2 - f3
    out = {"levels": [f1, f2, f3], "ratios": [1.0, r2, r3]}
    if d12 == 0.0 or d23 == 0.0 or (d12 > 0) != (d23 > 0):
        return {**out, "asymptotic": False, "reason": "non-monotone change"}
    g = lambda p: (1 - r2 ** -p) / (r2 ** -p - r3 ** -p)
    lo, hi, R = 0.05, 12.0, d12 / d23
    if not g(lo) < R < g(hi):
        return {**out, "asymptotic": False, "reason": f"ratio {R:.4g} outside the p range"}
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if g(mid) < R else (lo, mid)
    p = 0.5 * (lo + hi)
    ch = d12 / (1 - r2 ** -p)                  # C h^p on the production mesh
    f = f1 - ch
    return {**out, "asymptotic": True, "observed_order": p, "extrapolated": f,
            "production_mesh_error": f1 - f, "error_by_level": [f1 - f, f2 - f, f3 - f]}


def run_ladder(arch, n, doc):
    """MOOSE on the n x n x n refinement of the SAME deck (re-audited against the model
    objects first), and the three-level estimate from levels 1, 2 and n."""
    c = doc["cases"][arch]
    wd = scratch("fullpkg", arch)
    D = define(arch)
    m = D["m"]
    deck = MX.parse_deck(wd / "ccx" / "fullpkg_ccx.inp")
    P = MX.export_problem(deck, film_namer(D))
    aud = audit(D, deck, P)
    if not aud["passed"]:
        raise RuntimeError("the stored deck no longer matches the model objects")
    lay = np.asarray(m.elem_layer, dtype=object)
    groups = layer_groups(m, arch)
    reg_el = {k: E._region_elems(m, layers, it, D["tiles"])
              for k, (layers, it) in E.temperature_regions(arch).items()}
    mb = MX.read_moose(wd / "moose_base", "fullpkg_hypre")
    T_mo, _ = MX.map_to_nodes(P["xyz"], mb["xyz"], mb["T"])
    F = MX.refine_uniform(P, n)
    nc = n ** 3
    fw = wd / f"moose_refined_x{n}"
    fw.mkdir(parents=True, exist_ok=True)
    gf = MX.write_gmsh(F, fw / "fullpkg.msh")
    (fw / "fullpkg_hypre.i").write_text(MX.moose_input(F, "fullpkg.msh", "hypre"))
    print(f"[{arch}] x{n} mesh {gf['n_hex']} hex / {gf['n_nodes']} nodes", flush=True)
    rf = MX.run_moose(fw, "fullpkg_hypre.i", CORES)
    mf = MX.read_moose(fw, "fullpkg_hypre")
    T_f, dmf = MX.map_to_nodes(F["xyz"], mf["xyz"], mf["T"])
    reg_f = {k: ((ids - 1)[:, None] * nc + np.arange(nc)[None, :]).ravel() + 1
             for k, ids in reg_el.items()}
    met_f = metrics(F, T_f, lay[F["parent"] - 1], groups, reg_f, D["t_in"])
    q_f = film_heat(F, T_f)
    qe = np.zeros(len(P["hexes"]))
    for name, qv in deck["dflux"]:
        qe[deck["elsets"][name] - 1] = qv
    q_dep = float(np.sum(qe[F["parent"] - 1] * MX.elem_volumes(F["xyz"], F["hexes"])))
    c[f"moose_refined_x{n}"] = {
        "mesh": {"format": "Gmsh 2.2 ASCII", **gf,
                 "construction": f"every production hex split {n}x{n}x{n} (strictly nested)"},
        "metrics": met_f, "q_films_W": q_f, "Q_deposited_W": q_dep,
        "energy_residual_rel_to_deposited": (sum(q_f.values()) - q_dep) / q_dep,
        "field_at_production_nodes_vs_production_mesh":
            field_diff(T_mo, T_f[F["base_node_in_fine"] - 1], met_f["T_max_C"] - D["t_in"]),
        "timing": timing([rf["wall_s"]]), "moose_reported_s": rf["moose_reported_s"],
        "solve_s": rf["solve_s"], "nonlinear_residuals": rf["nonlinear_residuals"],
        "linear_its": rf["linear_its_last"], "ranks": CORES,
        "solver": "NEWTON; GMRES(300) + hypre BoomerAMG, l_tol 1e-12",
        "node_map_max_dist_mm": dmf}
    lv = [c["moose_base"]["metrics"], c["moose_refined"]["metrics"], met_f]
    lad = {"levels": ["production mesh (x1)", "x2", f"x{n}"],
           "n_elems": [c["problem"]["mesh"]["n_elems"], c["moose_refined"]["mesh"]["n_hex"],
                       gf["n_hex"]],
           "T_max_C": richardson3(*(x["T_max_C"] for x in lv), 2.0, float(n)),
           "layer_volume_mean_C": {g: richardson3(*(x["layer_volume_mean_C"][g] for x in lv),
                                                  2.0, float(n)) for g in groups},
           "region_volume_mean_C": {k: richardson3(*(x["region_volume_mean_C"][k]
                                                     for x in lv), 2.0, float(n))
                                    for k in reg_el}}
    lad["note"] = ("observed order and extrapolation from three strictly nested uniform "
                   "refinements of the production mesh (h, h/2, h/%d), identical problem" % n)
    c["refinement_ladder"] = lad
    shutil.copy(fw / "fullpkg_hypre.i", EVID / arch / f"refined_x{n}_hypre.i")
    (EVID / arch / f"refined_x{n}_hypre_log_tail.txt").write_text(rf["log_tail"])
    t = lad["T_max_C"]
    print(f"[{arch}] x{n} T_max {met_f['T_max_C']:.5f} C, wall {rf['wall_s']:.1f} s; "
          f"observed order {t.get('observed_order')}, extrapolated {t.get('extrapolated')}",
          flush=True)
    return doc


def run_split(arch, triples, doc):
    """Where the discretization change comes from: MOOSE on anisotropic refinements of the
    same deck, e.g. (2, 2, 1) in-plane only and (1, 1, 2) through the thickness only, each
    compared with MOOSE on the production mesh."""
    c = doc["cases"][arch]
    wd = scratch("fullpkg", arch)
    D = define(arch)
    m = D["m"]
    deck = MX.parse_deck(wd / "ccx" / "fullpkg_ccx.inp")
    P = MX.export_problem(deck, film_namer(D))
    if not audit(D, deck, P)["passed"]:
        raise RuntimeError("the stored deck no longer matches the model objects")
    lay = np.asarray(m.elem_layer, dtype=object)
    groups = layer_groups(m, arch)
    reg_el = {k: E._region_elems(m, layers, it, D["tiles"])
              for k, (layers, it) in E.temperature_regions(arch).items()}
    b = c["moose_base"]["metrics"]
    out = c.setdefault("refinement_split", {
        "what": "MOOSE on anisotropic refinements of the production mesh (nx, ny, nz children "
                "per hex), identical problem; changes are refined minus production mesh",
        "levels": {}})
    for f in triples:
        tag = "r%d%d%d" % tuple(f)
        F = MX.refine_uniform(P, f)
        nc = int(np.prod(f))
        fw = wd / f"moose_split_{tag}"
        fw.mkdir(parents=True, exist_ok=True)
        gf = MX.write_gmsh(F, fw / "fullpkg.msh")
        (fw / "fullpkg_hypre.i").write_text(MX.moose_input(F, "fullpkg.msh", "hypre"))
        rf = MX.run_moose(fw, "fullpkg_hypre.i", CORES)
        mf = MX.read_moose(fw, "fullpkg_hypre")
        T, _ = MX.map_to_nodes(F["xyz"], mf["xyz"], mf["T"])
        reg_f = {k: ((ids - 1)[:, None] * nc + np.arange(nc)[None, :]).ravel() + 1
                 for k, ids in reg_el.items()}
        met = metrics(F, T, lay[F["parent"] - 1], groups, reg_f, D["t_in"])
        q = film_heat(F, T)
        out["levels"][tag] = {
            "factors": list(map(int, f)), "n_hex": gf["n_hex"], "n_nodes": gf["n_nodes"],
            "T_max_C": met["T_max_C"], "T_max_xyz_mm": met["T_max_xyz_mm"],
            "T_max_change_K": met["T_max_C"] - b["T_max_C"],
            "layer_volume_mean_change_K": diff_dict(met["layer_volume_mean_C"],
                                                    b["layer_volume_mean_C"]),
            "region_volume_mean_change_K": diff_dict(met["region_volume_mean_C"],
                                                     b["region_volume_mean_C"]),
            "q_films_W": q, "wall_s": rf["wall_s"], "solve_s": rf["solve_s"]}
        print(f"[{arch}] {tag}: {gf['n_hex']} hex, T_max {met['T_max_C']:.4f} C "
              f"(change {met['T_max_C'] - b['T_max_C']:+.4f} K)", flush=True)
    out["uniform_x2_T_max_change_K"] = c["moose_refined"]["metrics"]["T_max_C"] - b["T_max_C"]
    return doc


# ---------------------------------------------------------------------------
# two observations about the production model made while defining the problem
# ---------------------------------------------------------------------------

#: the converged Z2 production field collected by tcpmt_collect_variant_fields (outside git)
Z2_FIELD = Path("/home/beams0/SABDELZAHER/ETM_project/scratch/fields/etm_Z2_HV_S0_r21/"
                "thermal_converged.frd")


def side_observations():
    """(a) the streamwise film's sink temperature within one streamwise column of faces;
    (b) the z-range 'bga' temperature region on the Z2 geometry, where the converter shares
    the BGA's z range inside the PCB opening. Neither affects the verification problem."""
    out = {}
    D = define("Z1")
    m, ccxio = D["m"], PE.ccxio
    cooler = CANDIDATES[E.COOLER]
    top = ccxio.top_film_faces(m)
    cen = m.elem_centroids()[top - 1]
    areas = np.array([ccxio.face_area(m, e) for e in top])
    m_dot = cooler.m_dot_g_s * 1e-3 * (2.0 if cooler.two_sided else 1.0)
    order = np.argsort(cen[:, 0])                      # as solve_thermal orders the faces
    frac = np.zeros(len(top))
    frac[order] = (np.cumsum(areas[order]) - 0.5 * areas[order]) / areas.sum()
    t_face = cooler.t_in_c + frac * D["Q"] / (m_dot * PE.CP_F)
    xs = np.unique(np.round(cen[:, 0], 9))
    spread = np.array([np.ptp(t_face[np.abs(cen[:, 0] - x) < 1e-9]) for x in xs])
    out["streamwise_film_within_column_sink_spread"] = {
        "what": "solve_thermal assigns each top face the coolant temperature after the heat of "
                "every face before it in an argsort on centroid x; faces sharing one x (one "
                "streamwise column) therefore get different sink temperatures, spread over the "
                "column's share of the coolant rise, although a 1-D coolant model gives them one",
        "arch": "Z1", "faces": int(len(top)), "columns": int(len(xs)),
        "coolant_rise_K": float(D["Q"] / (m_dot * PE.CP_F)),
        "spread_K_median": float(np.median(spread)), "spread_K_max": float(spread.max()),
        "status": "observation only; not part of the verification problem (uniform film)"}
    m2, _, _, tiles2, _ = E.build("Z2", E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
    lay2 = np.asarray(m2.elem_layer, dtype=object)
    reg = E._region_elems(m2, ["bga"], False, tiles2)
    lab = np.flatnonzero(lay2 == "bga") + 1
    extra = sorted(set(map(str, lay2[np.setdiff1d(reg, lab) - 1])))
    ob = {"what": "temperature_regions('Z2')['bga'] selects by element-centroid z (production "
                  "_layer_elems), so inside the PCB opening it also takes the converter elements "
                  "that share the BGA's z range; the region feeds the ledger's BGA temperature, "
                  "used only by the BGA-fed terms (the Z2BF control on this geometry)",
          "region_elements_z_range": int(len(reg)), "bga_label_elements": int(len(lab)),
          "extra_layers_in_region": extra}
    if Z2_FIELD.exists():
        T = PE.ccxio.read_frd(Z2_FIELD)["NDTEMP"][1:m2.n_nodes + 1, 0]
        ob.update({"field": str(Z2_FIELD),
                   "T_region_node_mean_C": float(T[np.unique(m2.elems[reg - 1]) - 1].mean()),
                   "T_bga_label_node_mean_C": float(T[np.unique(m2.elems[lab - 1]) - 1].mean())})
    ob["status"] = "observation only; Z1 and Z3 stacks do not overlap in z (unaffected)"
    out["z2_bga_temperature_region"] = ob
    return out


def inplane_ladder(c):
    """The in-plane refinement ladder x1 (production), x2, x3, x4 = (n, n, 1) levels from
    run_split: observed order from the coarse triple (x1, x2, x3) and the fine triple
    (x2, x3, x4); the fine triple sets the extrapolation and the production-mesh error."""
    lv = c.get("refinement_split", {}).get("levels", {})
    if not all(k in lv for k in ("r221", "r331", "r441")):
        return None
    b = c["moose_base"]["metrics"]
    seq = [None, lv["r221"], lv["r331"], lv["r441"]]

    def ladder(f):
        coarse = richardson3(f[0], f[1], f[2], 2.0, 3.0)
        fine = richardson3(f[1], f[2], f[3], 1.5, 2.0)
        r = {"levels": f, "observed_order_x1x2x3": coarse.get("observed_order"),
             "observed_order_x2x3x4": fine.get("observed_order"),
             "asymptotic_fine": fine["asymptotic"]}
        if fine["asymptotic"]:
            r.update({"extrapolated": fine["extrapolated"],
                      "production_mesh_error": f[0] - fine["extrapolated"],
                      "x4_error": f[3] - fine["extrapolated"]})
        return r

    tm = ladder([b["T_max_C"]] + [s["T_max_C"] for s in seq[1:]])
    lay = {g: ladder([b["layer_volume_mean_C"][g]]
                     + [b["layer_volume_mean_C"][g] + s["layer_volume_mean_change_K"][g]
                        for s in seq[1:]]) for g in b["layer_volume_mean_C"]}
    reg = {k: ladder([b["region_volume_mean_C"][k]]
                     + [b["region_volume_mean_C"][k] + s["region_volume_mean_change_K"][k]
                        for s in seq[1:]]) for k in b["region_volume_mean_C"]}
    return {"what": "in-plane refinement only (every in-plane interval of the production mesh "
                    "split in n = 1, 2, 3, 4; through-thickness unchanged), identical problem; "
                    "extrapolation from the finest three levels (generalized Richardson)",
            "n_hex": [c["problem"]["mesh"]["n_elems"]] + [s["n_hex"] for s in seq[1:]],
            "T_max_C": tm, "layer_volume_mean_C": lay, "region_volume_mean_C": reg}


#: the layer means the reviewer response quotes
SUMMARY_GROUPS = ("die", "converter_all_tiers", "substrate", "bga", "board")


def summarize(doc):
    """The headline numbers of every case, read back from the case records."""
    out = {}
    for arch, c in doc.get("cases", {}).items():
        b, pm = c["identical_mesh"], c["problem"]["mesh"]
        mc = c["moose_base"]["runs"]
        s = {"mesh": f"{pm['n_elems']} hex / {pm['n_nodes']} nodes ({pm['label']})",
             "input_audit_passed": c["input_audit"]["passed"],
             "T_max_C": {"production_streamwise_film":
                         c["problem"]["production_T_max_C_streamwise_film"],
                         "calculix": b["T_max_C"]["calculix"],
                         "moose": b["T_max_C"]["moose"]},
             "identical_mesh": {
                 "T_max_err_K": b["T_max_err_K"],
                 "T_max_err_pct_of_rise": 100 * b["T_max_err_rel_to_rise"],
                 "field_max_abs_K": b["field_ccx_minus_moose"]["max_abs_K"],
                 "field_rms_K": b["field_ccx_minus_moose"]["rms_K"],
                 "max_abs_layer_mean_err_K": b["max_abs_layer_err_K"],
                 "calculix_print_resolution_K": b["calculix_output_resolution_K"],
                 "energy_residual_rel_to_deposited": {
                     k: b["energy"][k]["residual_rel_to_deposited"]
                     for k in ("calculix", "moose")}},
             "layer_volume_mean_C": {
                 g: {"calculix": c["calculix"]["metrics"]["layer_volume_mean_C"][g],
                     "moose": c["moose_base"]["metrics"]["layer_volume_mean_C"][g]}
                 for g in SUMMARY_GROUPS},
             "runtime_s_median": {
                 "calculix": c["calculix"]["timing"]["median_s"],
                 "moose_hypre": mc["hypre"]["timing"]["median_s"],
                 "moose_mumps": mc["mumps"]["timing"]["median_s"]},
             "cores": "8 CalculiX threads (SPOOLES factorization single-threaded); "
                      "8 MOOSE MPI ranks"}
        if "discretization_change" in c:
            d, f = c["discretization_change"], c["moose_refined"]
            s["T_max_C"]["moose_refined"] = f["metrics"]["T_max_C"]
            s["refinement"] = {
                "mesh": f"{f['mesh']['n_hex']} hex / {f['mesh']['n_nodes']} nodes",
                "sign": "production mesh minus uniform 2x2x2 refinement",
                "T_max_change_K": d["T_max_change_K"],
                "T_max_change_pct_of_rise": 100 * d["T_max_change_rel_to_rise"],
                "max_abs_layer_mean_change_K": d["max_abs_layer_change_K"],
                "field_change_max_abs_K": d["field_at_production_nodes"]["max_abs_K"],
                "field_change_rms_K": d["field_at_production_nodes"]["rms_K"],
                "T_max_production_minus_extrapolated_K_if_p2":
                    d["T_max_production_mesh_minus_extrapolated_K_if_p2"],
                "moose_refined_wall_s": f["timing"]["median_s"]}
            for g in SUMMARY_GROUPS:
                s["layer_volume_mean_C"][g]["moose_refined"] = \
                    f["metrics"]["layer_volume_mean_C"][g]
        if "refinement_ladder" in c:
            lad = c["refinement_ladder"]
            n3 = [k for k in c if k.startswith("moose_refined_x")][0]
            t = lad["T_max_C"]
            s["T_max_C"][n3] = c[n3]["metrics"]["T_max_C"]
            s["refinement_ladder"] = {
                "n_elems": lad["n_elems"],
                "T_max": {k: t.get(k) for k in ("asymptotic", "observed_order", "extrapolated",
                                                "production_mesh_error")},
                "layer_mean_production_mesh_error_K": {
                    g: lad["layer_volume_mean_C"][g].get("production_mesh_error")
                    for g in SUMMARY_GROUPS},
                "layer_mean_observed_order": {
                    g: lad["layer_volume_mean_C"][g].get("observed_order")
                    for g in SUMMARY_GROUPS},
                "moose_wall_s": c[n3]["timing"]["median_s"]}
        il = inplane_ladder(c)
        if il is not None:
            c["inplane_ladder"] = il
            sp = c["refinement_split"]["levels"]
            s["refinement_attribution_x2"] = {
                "sign": "refined minus production mesh",
                "uniform_2x2x2_T_max_change_K":
                    -c["discretization_change"]["T_max_change_K"]
                    if "discretization_change" in c else None,
                "in_plane_only_T_max_change_K": sp["r221"]["T_max_change_K"],
                "through_thickness_only_T_max_change_K": sp["r112"]["T_max_change_K"]
                if "r112" in sp else None}
            s["inplane_ladder"] = {
                "n_hex": il["n_hex"],
                "T_max_C": il["T_max_C"]["levels"],
                "T_max_observed_order": [il["T_max_C"]["observed_order_x1x2x3"],
                                         il["T_max_C"]["observed_order_x2x3x4"]],
                "T_max_extrapolated_C": il["T_max_C"].get("extrapolated"),
                "T_max_production_mesh_error_K": il["T_max_C"].get("production_mesh_error"),
                "T_max_production_mesh_error_pct_of_rise":
                    (100 * il["T_max_C"]["production_mesh_error"]
                     / (il["T_max_C"]["extrapolated"] - c["problem"]["top_film"]["T_inf_C"])
                     if il["T_max_C"].get("extrapolated") is not None else None),
                "layer_mean_production_mesh_error_K": {
                    g: il["layer_volume_mean_C"][g].get("production_mesh_error")
                    for g in SUMMARY_GROUPS},
                "ledger_region_production_mesh_error_K": {
                    k: v.get("production_mesh_error")
                    for k, v in il["region_volume_mean_C"].items()}}
        out[arch] = s
    doc["summary"] = out
    doc["caveats"] = [
        "The verification problem replaces the production streamwise top film (sink warming "
        "along the flow, 1-D coolant balance) by a uniform film at the inlet temperature with "
        "the same h; the streamwise coolant model itself is not cross-checked. It enters the deck "
        "through the same per-face *FILM lines verified here.",
        "On the identical mesh both codes use trilinear hexahedra with exact quadrature on "
        "axis-aligned bricks, so their discrete systems coincide: that comparison verifies the "
        "deck (materials, anisotropy, sources, films, units) and the CalculiX solve, not the "
        "discretization. The refined MOOSE meshes measure the discretization error.",
        "Both codes use the production homogenized material cards; the homogenizations are "
        "checked separately (unit-cell and RVE references), not here.",
        "CalculiX prints nodal temperatures to 7 significant digits (1e-4 K above 100 C, 1e-5 K "
        "below), which bounds the measurable identical-mesh agreement.",
        "The deck prints node coordinates to 1e-6 mm and conductivities to 6 significant digits; "
        "both codes solve the deck as printed (input audit).",
        "Runtimes are wall clock on a shared 96-core host (load average 60-80) with 8 cores per "
        "solver; CalculiX's default SPOOLES factorization is single-threaded and its Newton loop "
        "factors twice for this linear problem.",
        "Extrapolated mesh-converged values come from nested refinements with observed orders "
        "below 2 (the change is in-plane and sits in the converter stack and everything below "
        "it); they are estimates, not bounds."]
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arch", nargs="*")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--no-refined", action="store_true")
    ap.add_argument("--summarize", action="store_true",
                    help="only rebuild the summary block from the stored cases")
    ap.add_argument("--ladder", type=int, default=0,
                    help="add MOOSE on the NxNxN refinement to the stored cases of ARCH")
    ap.add_argument("--side", action="store_true",
                    help="record the two production-model observations (side_observations)")
    ap.add_argument("--split", nargs="+", default=[],
                    help="anisotropic refinements of ARCH, e.g. 2,2,1 1,1,2")
    a = ap.parse_args()
    doc = json.loads(OUT.read_text()) if OUT.exists() else {}
    if a.split:
        triples = [tuple(int(v) for v in s.split(",")) for s in a.split]
        for arch in a.arch:
            run_split(arch, triples, doc)
            OUT.write_text(json.dumps(summarize(doc), indent=1, default=float))
            print(f"wrote {OUT}", flush=True)
        return
    if a.side:
        doc["side_observations"] = side_observations()
        OUT.write_text(json.dumps(doc, indent=1, default=float))
        print(json.dumps(doc["side_observations"], indent=1, default=float))
        return
    if a.ladder:
        for arch in a.arch:
            run_ladder(arch, a.ladder, doc)
            OUT.write_text(json.dumps(summarize(doc), indent=1, default=float))
            print(f"wrote {OUT}", flush=True)
        return
    if a.summarize:
        OUT.write_text(json.dumps(summarize(doc), indent=1, default=float))
        print(json.dumps(doc["summary"], indent=1, default=float))
        return
    doc.update({
        "stage": "tcpmt_fullpkg_verification",
        "purpose": "complete-package cross-check of the production thermal model (CalculiX on "
                   "the explicit package mesh) against MOOSE on the identical problem, plus "
                   "MOOSE on a uniformly refined copy for the discretization change",
        "moose": {"executable": str(MX.MOOSE), "mpiexec": str(MX.MPIEXEC),
                  "filemesh_formats": MX.FILEMESH_FORMATS,
                  "objects": "AnisoHeatConduction, AnisoHeatConductionMaterial (diagonal "
                             "k_ortho), BodyForce, ConvectiveHeatFluxBC, NodalValueSampler"},
        "calculix": {"deck_writer": "final_closure_physical_etm.write_thermal",
                     "runner": "phase0b/etm/ccxio.run_ccx", "element": "C3D8"},
        "cores": {"calculix_threads": CORES, "moose_mpi_ranks": CORES,
                  "note": "CalculiX assembles on 8 threads but its default SPOOLES "
                          "factorization runs on one ('Using 1 cpu for spooles'), and its "
                          "Newton loop factors twice for this linear problem"},
        "timing_method": f"wall clock of the solver process; {a.repeats} timed repeats after "
                         "one untimed warm-up on the production mesh (median and range), one "
                         "run on the refined copy; shared host, so load averages are recorded",
    })
    doc.setdefault("cases", {})
    for arch in a.arch:
        doc["cases"][arch] = run_arch(arch, a.repeats, not a.no_refined)
        doc["generated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, indent=1, default=float))
        print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
