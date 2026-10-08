"""End-to-end Phase-0B M0 case: geometry -> thermal -> structural -> metrics."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import numpy as np

from . import ccxio, metrics
from .config import build_materials, open_decisions
from .mesh import build
from .placement import case_tiles

SPOOLES_C3D8I_MAX = 40000


def run_case(case_id: str, stack: dict, doe: dict, workdir: Path, *,
             h_top: float, h_xy: float = 0.55, z_scale: float = 1.0,
             bc: str = "BC_A", overrides: dict | None = None,
             solver: str = "ITERATIVE CHOLESKY",
             tsv_enabled: bool | None = None, threads: int | None = None,
             h_max_factor: float = 3.0, tsv_discrete_pitch: float | None = None,
             interface_nz: int | None = None,
             keep_files: bool = False) -> dict:
    t0 = time.time()
    case = dict(doe["cases"][case_id])
    dflt = doe["defaults"]
    p_die = case.get("p_die_w", dflt["p_die_w"])
    p_hvr = case.get("p_hvr_total_w", dflt["p_hvr_total_w"])

    stack = json.loads(json.dumps(stack))          # deep copy; never mutate the caller's dict
    if tsv_enabled is not None:
        stack["geometry"]["tsv_field"]["enabled"]["value"] = bool(tsv_enabled)

    workdir.mkdir(parents=True, exist_ok=True)
    tiles = case_tiles(case, stack, doe)
    m = build(tiles, stack, case["h_sub"], h_xy=h_xy, z_scale=z_scale,
              h_max_factor=h_max_factor, support_layer=(bc == "BC_B"),
              tsv_discrete_pitch=tsv_discrete_pitch, interface_nz=interface_nz)
    mats = build_materials(stack, overrides)

    # Measured limit of this CalculiX build: C3D8I + SPOOLES solves at 37.5k elements
    # and segfaults at 48k and 63k. C3D8 (no incompatible modes) survives but shear-locks
    # in bending, and the ITERATIVE CHOLESKY solver was measured to disagree with the
    # direct solver by 35% on package warpage. So the element budget is a hard gate,
    # never a silent fallback.
    if not solver and m.n_elems > SPOOLES_C3D8I_MAX:
        raise RuntimeError(
            f"{case_id}: {m.n_elems} elements exceeds the measured C3D8I/SPOOLES ceiling "
            f"({SPOOLES_C3D8I_MAX}). Coarsen h_xy / raise h_max_factor, or move to a build "
            f"with a direct solver that handles this size. Refusing to run.")

    # ---- thermal -----------------------------------------------------------
    tinp = workdir / "thermal.inp"
    films = ccxio.write_thermal(m, mats, tiles, stack, p_die, h_top, tinp)
    ccxio.run_ccx(tinp, threads=threads)
    tres = ccxio.read_frd(workdir / "thermal.frd")
    if "NDTEMP" not in tres:
        raise RuntimeError(f"no NDTEMP block in thermal.frd; blocks={sorted(tres)}")
    T = tres["NDTEMP"]
    tm = metrics.thermal_metrics(m, T, films, stack, p_die + p_hvr, h_top)

    # ---- structural --------------------------------------------------------
    temps = T[1:m.n_nodes + 1, 0]
    sinp = workdir / "structural.inp"
    binfo = ccxio.write_structural(m, mats, temps, stack, bc, sinp, solver=solver)
    ccxio.run_ccx(sinp, threads=threads)
    sres = ccxio.read_frd(workdir / "structural.frd")
    for blk in ("DISP", "STRESS"):
        if blk not in sres:
            raise RuntimeError(f"no {blk} block in structural.frd; blocks={sorted(sres)}")
    sm = metrics.structural_metrics(m, sres["DISP"], sres["STRESS"], stack)

    out = {
        "case": case_id, "spec": case,
        "mesh": {"h_xy_mm": h_xy, "z_scale": z_scale, "h_max_factor": h_max_factor,
                 "graded": True, "element_type": "C3D8I",
                 "tsv_discrete_pitch": tsv_discrete_pitch,
                 "n_nodes": m.n_nodes, "n_elems": m.n_elems,
                 "n_z_planes": int(len(m.zs)),
                 "elems_through_substrate": int(m.layers[0].nz + m.layers[1].nz),
                 "elems_through_die": int(m.layers[3].nz)},
        "loads": {"p_die_W": p_die, "p_hvr_total_W": p_hvr,
                  "p_per_tile_W": p_hvr / case["n_vr"],
                  "q_die_W_per_mm3": films["q_die_w_per_mm3"]},
        "cooling": {"h_top_W_m2K": h_top, "h_bot_W_m2K": films["h_bot_W_m2K"],
                    "a_top_mm2": films["a_top_mm2"], "a_bot_mm2": films["a_bot_mm2"]},
        "bc": binfo,
        "tiles": [{"cx": t.cx, "cy": t.cy, "ax": t.ax, "ay": t.ay, "P_W": t.power_w}
                  for t in tiles],
        "thermal": tm, "structural": sm,
        "overrides": overrides or {},
        "tsv_enabled": stack["geometry"]["tsv_field"]["enabled"]["value"],
        "runtime_s": round(time.time() - t0, 1),
    }
    (workdir / "metrics.json").write_text(json.dumps(out, indent=2))
    np.save(workdir / "nodes.npy", m.nodes)
    np.save(workdir / "temps.npy", temps)
    np.save(workdir / "disp.npy", sres["DISP"][1:m.n_nodes + 1])
    if not keep_files:
        for pat in ("*.frd", "*.inp", "*.dat", "*.sta", "*.cvg", "*.12d"):
            for f in workdir.glob(pat):
                f.unlink(missing_ok=True)
    return out


def calibrate_h_top(stack: dict, doe: dict, workdir: Path, *, ref_case: str = "C05",
                    target_tmax: float = 84.0, h_xy: float = 0.9, z_scale: float = 0.6,
                    tol: float = 0.5, max_iter: int = 8, threads: int | None = None) -> dict:
    """1-D/secant calibration of the cold-plate coefficient.

    The spec forbids picking h because it "looks reasonable". h_top is instead solved
    so that the REFERENCE architecture reaches a defensible junction temperature, then
    FROZEN for the entire DOE. Target defaults to the June-2026 cooled baseline (84 C).

    Note the Phase-0B load (282 W over 500 mm^2) is ~4.3x below June's 1 kW case, so
    this calibrates the *operating temperature*, not June's cooling hardware. Using
    June's own h would leave the vehicle near 39 C and would test mechanics at an
    unrepresentatively small dT.
    """
    case = dict(doe["cases"][ref_case])
    dflt = doe["defaults"]
    p_die = case.get("p_die_w", dflt["p_die_w"])
    p_hvr = case.get("p_hvr_total_w", dflt["p_hvr_total_w"])
    q = p_die + p_hvr

    g = stack["geometry"]
    a_top_m2 = (g["functional_die"]["size_x"]["value"] *
                g["functional_die"]["size_y"]["value"]) * 1e-6
    t_cool = stack["thermal_bc"]["coolant_temp"]["value"]

    # 1-D seed: assume ~2/3 of the rise is across the film
    dt_film = (target_tmax - t_cool) * (2.0 / 3.0)
    h = q / (a_top_m2 * dt_film)

    tiles = case_tiles(case, stack, doe)
    m = build(tiles, stack, case["h_sub"], h_xy=h_xy, z_scale=z_scale,
              h_max_factor=h_max_factor, support_layer=(bc == "BC_B"),
              tsv_discrete_pitch=tsv_discrete_pitch, interface_nz=interface_nz)
    mats = build_materials(stack)
    wd = workdir / "calibration"
    wd.mkdir(parents=True, exist_ok=True)

    hist = []
    prev = None
    for it in range(max_iter):
        tinp = wd / "cal.inp"
        films = ccxio.write_thermal(m, mats, tiles, stack, p_die, h, tinp)
        ccxio.run_ccx(tinp, threads=threads)
        T = ccxio.read_frd(wd / "cal.frd")["NDTEMP"]
        tmax = float(np.nanmax(T[1:m.n_nodes + 1, 0]))
        res = tmax - target_tmax
        hist.append({"iter": it, "h_top_W_m2K": h, "T_max_C": tmax, "residual_K": res})
        if abs(res) <= tol:
            break
        if prev is None:
            # film-resistance update: dT_film scales as 1/h
            dt_cond = tmax - t_cool - q / (a_top_m2 * h)
            h_new = q / (a_top_m2 * max(target_tmax - t_cool - dt_cond, 1.0))
        else:
            (h0, r0) = prev
            h_new = h - res * (h - h0) / (res - r0) if abs(res - r0) > 1e-12 else h * 1.1
        prev = (h, res)
        h = float(np.clip(h_new, 1e2, 1e7))

    return {"h_top_W_m2K": h, "target_T_max_C": target_tmax,
            "achieved_T_max_C": hist[-1]["T_max_C"],
            "residual_K": hist[-1]["residual_K"],
            "converged": abs(hist[-1]["residual_K"]) <= tol,
            "reference_case": ref_case, "iterations": hist,
            "calibration_mesh": {"h_xy_mm": h_xy, "z_scale": z_scale,
                                 "n_nodes": m.n_nodes, "n_elems": m.n_elems},
            "rationale": ("Solved so the reference architecture reaches the June-2026 cooled "
                          "baseline junction temperature; frozen for the whole DOE."),
            "status": "DERIVED"}
