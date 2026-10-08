#!/usr/bin/env python3
"""Phase-0M-R Section 14 -- controlled architecture replay through the PRODUCTION path.

Not an optimizer and not a DOE. A frozen comparison matrix, run twice: once through the
Phase-0M production path (BEFORE) and once through the Phase-0M-R path (AFTER), changing
only which models are wired in. Everything else -- load, footprint, materials, mission,
failure-law treatment -- is held fixed.

BEFORE: global K_crowd = 1.326; no intra-VR routing; calibrated Robin h with one sink
        temperature; lumped VR.
AFTER:  per-class R_bulk + dR_transition from the validated solver; template-aware intra-VR
        routing in the total; physical cooling with a streamwise coolant rise; spatial heat
        deposition; converter re-evaluated at its own layer temperature.
"""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b", "phase0d"):
    sys.path.insert(0, str(R / "scripts" / d))
import ppdn as PP                                                          # noqa: E402
import zarch as ZA                                                         # noqa: E402
import zglobal as ZG                                                       # noqa: E402
import kw1                                                                 # noqa: E402
from stack import stacks_from_cfg, rdl_network_solve                       # noqa: E402
from architecture0e import pol_grid, CROWDING_DEFAULT                      # noqa: E402
from interconnect import rho_cu                                            # noqa: E402
from ledger import LossLedger, converter_decomposition, LedgerError        # noqa: E402
import interconnect_production as IP                                       # noqa: E402
import routing_production as RP                                            # noqa: E402
import production_et as PE                                                 # noqa: E402
from cooling_production import CoolingDesign, CANDIDATES                   # noqa: E402

OUT = R / "results" / "phase0mr"
WD = OUT / "replay"
OUT.mkdir(parents=True, exist_ok=True)
WD.mkdir(parents=True, exist_ok=True)

DIE_MM, N_VR, LOAD_W = 22.36, 49, 1000.0
H_SUB = {"ARCH_Z1_EMBEDDED": 1.30, "ARCH_Z2_BACKSIDE": 0.30, "ARCH_Z4_POWER_DIE": 0.30}
# production transition geometry per interconnect class: (r_via, r_pad, w_trace, t_rdl, l)
TRANSITION_GEOM = {
    "tsv": (15e-6, 18e-6, 10e-6, 10e-6, 100e-6),
    "microbump": (5e-6, 6e-6, 5e-6, 5e-6, 40e-6),
    "bga": (200e-6, 240e-6, 200e-6, 40e-6, 800e-6),
    "c4": (50e-6, 60e-6, 50e-6, 15e-6, 300e-6),
}
_DESIGN_CACHE: dict = {}


def compiled_design():
    if "d" not in _DESIGN_CACHE:
        d, g, why = kw1.design_1kw()
        if d is None:
            raise RuntimeError(f"no compiled converter: {why}")
        _DESIGN_CACHE["d"] = d
    return _DESIGN_CACHE["d"]


def converter_terms(t_c: float) -> dict:
    """Converter loss decomposed per component, at the LOCAL layer temperature."""
    from HVR_FULL_OPT_EPC_V2 import LossModelInputs, compute_total_loss
    from electrical import rdson_at, dcr_at, ALPHA_GAN_RDSON
    from dataclasses import replace as dc_replace
    d = compiled_design()
    hs = dc_replace(d.hs, R_DS_ON=rdson_at(d.hs.R_DS_ON, t_c, ALPHA_GAN_RDSON))
    ls = dc_replace(d.ls, R_DS_ON=rdson_at(d.ls.R_DS_ON, t_c, ALPHA_GAN_RDSON))
    ind = dc_replace(d.inductor, r_dcr_mohm=dcr_at(d.inductor.r_dcr_mohm, t_c))
    lr = compute_total_loss(d.arch, LossModelInputs(
        hs_device=hs, ls_device=ls, inductor=ind, capacitor=d.capacitor,
        I_out=d.i_out_a, V_out=d.v_out, V_in=d.v_in, f_sw=d.f_sw_hz))
    dec = converter_decomposition(d.arch, hs, ls, ind, d.capacitor, d.i_out_a,
                                  d.v_out, d.v_in, d.f_sw_hz, lr)
    dec["p_conv_total_w"] = lr.total_loss * N_VR
    return dec


def tier_resistance(tier_name: str, tier_cfg: dict, i_total: float, footprint_mm2: float,
                    t_c: float, h_m: float | None, j: float, mode: str) -> dict:
    """R_field for one tier. BEFORE: R_bulk * 1.326. AFTER: R_bulk + dR_transition."""
    a_c = PP.tier_area_m2(tier_cfg)
    pitch = PP._v(tier_cfg["pitch_m"])
    n_req = max(1, math.ceil(abs(i_total) / (j * a_c)))
    n_av = max(1, int(footprint_mm2 * 1e-6 * 0.5 / pitch ** 2))
    n = n_req
    r_bulk = PP.r_single(tier_cfg, t_c, h_m)
    if mode == "BEFORE":
        r_one = r_bulk * CROWDING_DEFAULT
        dr = r_bulk * (CROWDING_DEFAULT - 1.0)
        src = "global K_crowd = 1.326"
    else:
        g = TRANSITION_GEOM.get(tier_name)
        if g is None:
            r_one, dr, src = r_bulk, 0.0, "no transition geometry defined"
        else:
            d = IP.transition_dR(tier_name, *g, t_c=t_c)
            dr = d["dR_ohm"] * (h_m / (g[0] * 2) if False else 1.0)
            r_one = r_bulk + dr
            src = f"exact FV solve, cached ({d['key']})"
    r_field = r_one / n
    return {"tier": tier_name, "n_required": n_req, "n_available": n_av,
            "n_allocated": n, "R_bulk_one_ohm": r_bulk, "dR_one_ohm": dr,
            "R_one_ohm": r_one, "R_field_ohm": r_field, "R_loop_ohm": 2 * r_field,
            "P_w": i_total ** 2 * 2 * r_field, "feasible": n_req <= n_av,
            "transition_source": src}


def electrical(arch: str, h_sub_mm: float, mode: str, t_conv_c: float, t_pkg_c: float,
               template: str = "T1_EMBEDDED_4LAYER") -> dict:
    d = compiled_design()
    dec = converter_terms(t_conv_c)
    led = LossLedger(n_vr=N_VR)
    for k in ("P_switch_hs_conduction", "P_switch_ls_conduction", "P_inductor_DCR",
              "P_cap_ESR", "P_switching_hard", "P_gate", "P_Coss"):
        led.add(k, dec[k], scope="PER_REGULATOR")
    # intra-VR metallisation
    if mode == "AFTER":
        rt = RP.template_loss(template, t_cu_m=10e-6, n_layers=9,
                              via_policy="D_area_optimal", t_c=t_conv_c)
        led.add("P_intraVR_metal", rt["P_intraVR_metal_system_w"])
        led.add("P_intraVR_vertical", rt["P_intraVR_vertical_system_w"])
        intra_infeas = rt["n_infeasible"]
    else:
        led.add("P_intraVR_metal", 0.0, note="ABSENT from the Phase-0M production path")
        led.add("P_intraVR_vertical", 0.0, note="ABSENT from the Phase-0M production path")
        intra_infeas = None
    # vertical tiers
    P = PP.load_paths()
    tiers = P["tiers"]
    segs = ZA.path_for(arch, LOAD_W)
    h_tsv = (max(h_sub_mm * 1e3 - 1226.0, 0.0) * 1e-6 if arch == "ARCH_Z1_EMBEDDED"
             else h_sub_mm * 1e-3)
    p_tsv, p_bump, rows = 0.0, 0.0, []
    for s in segs:
        if s.tier in ("converter", "rdl"):
            continue
        tc = tiers[s.tier]
        j = 1.0e8 if tc["material"] == "copper" else 3.97e7
        fp = (30.0 * 30.0) if s.tier == "bga" else DIE_MM ** 2
        hm = h_tsv if s.tier == "tsv" else None
        r = tier_resistance(s.tier, tc, s.i_a, fp, t_pkg_c, hm, j, mode)
        r.update(arch=arch, mode=mode, rail=s.rail, i_a=s.i_a)
        rows.append(r)
        if s.tier == "tsv":
            p_tsv += r["P_w"]
        else:
            p_bump += r["P_w"]
    led.add("P_TSV", p_tsv)
    led.add("P_bumps", p_bump)
    # package RDL
    stack = stacks_from_cfg()["ectc2024_primary"]
    from etm.config import load_doe, load_stack
    side = math.sqrt(274.89 / N_VR)
    src = kw1.tiles_for("uniform", side, load_stack(), load_doe(), N_VR)
    pol = pol_grid()
    sol = rdl_network_solve(stack, src, [LOAD_W / len(src)] * len(src), pol,
                            [LOAD_W / len(pol)] * len(pol), span_mm=DIE_MM, T_c=t_pkg_c,
                            n=121, src_size_mm=side, load_size_mm=DIE_MM / 10,
                            ground_xy=pol[len(pol) // 2], ground_size_mm=DIE_MM / 10)
    led.add("P_pkg_RDL", sol["p_loop_w"])
    led.add("P_other", 0.0, note="no unassigned residual")
    return {"ledger": led, "tiers": rows, "dec": dec,
            "P_elec_total_w": led.total(), "intra_infeasible": intra_infeas,
            "T_conv_C": t_conv_c, "T_pkg_C": t_pkg_c, "mode": mode,
            "template": template if mode == "AFTER" else "lumped"}


# ---------------------------------------------------------------------------
# the full production loop: electrical <-> thermal fixed point, then mechanics
# ---------------------------------------------------------------------------
LEGACY_H_TOP = 166000.0


def run_case(arch: str, mode: str, template: str = "T1_EMBEDDED_4LAYER",
             cooler_name: str = "TOP_SI_MICROCHANNEL_27", h_sub_mm: float | None = None,
             max_et_iter: int = 6, tol_k: float = 0.25, h_xy: float = 0.80) -> dict:
    """One architecture through the whole production path, BEFORE or AFTER."""
    h_sub = H_SUB[arch] if h_sub_mm is None else h_sub_mm
    cooler = CANDIDATES[cooler_name]
    t_conv = t_pkg = 85.0
    hist, el = [], None
    wd = WD / f"{arch}_{mode}_{template}_{cooler_name}"
    if wd.exists():
        import shutil as _sh
        _sh.rmtree(wd, ignore_errors=True)
    t0 = time.time()
    for it in range(max_et_iter):
        el = electrical(arch, h_sub, mode, t_conv, t_pkg, template)
        led = el["ledger"]
        hm = PE.HeatMap(die_w=LOAD_W,
                        converter_w=led.converter_total(),
                        intravr_w=led.terms["P_intraVR_metal"]
                                  + led.terms["P_intraVR_vertical"],
                        tsv_w=led.terms["P_TSV"], rdl_w=led.terms["P_pkg_RDL"],
                        bump_w=led.terms["P_bumps"])
        if mode == "BEFORE":
            # the incumbent boundary: one calibrated h, one uniform sink temperature
            legacy = CoolingDesign("LEGACY", 50, 300, 50, 1e9)   # flow so large dT_f -> 0
            th = _solve_legacy(arch, h_sub, hm, wd / f"it{it}", h_xy)
        else:
            th = PE.solve_thermal(arch, h_sub, hm, cooler, wd / f"it{it}", h_xy=h_xy)
        if th.get("status") != "OK":
            return {"arch": arch, "mode": mode, "status": th.get("status", "THERMAL FAIL")}
        m, Tn = th["mesh"], th["T_node"]
        conv_layer = th["conv_layer"]
        t_conv_new = PE.layer_mean_temperature(m, Tn, conv_layer)
        t_pkg_new = th["T_mean_C"]
        d_t = max(abs(t_conv_new - t_conv), abs(t_pkg_new - t_pkg))
        hist.append({"iter": it, "T_conv_C": t_conv_new, "T_pkg_C": t_pkg_new,
                     "T_max_C": th["T_max_C"], "P_elec_w": el["P_elec_total_w"],
                     "dT_K": d_t, "energy_residual_pct": th["energy_residual_pct"]})
        t_conv, t_pkg = t_conv_new, t_pkg_new
        if d_t < tol_k:
            break
    # ---- mechanics on the converged temperature field --------------------------------
    st = th["stack"]
    mats = th["materials"]
    si = wd / "structural.inp"
    ccxio_ = PE.ccxio
    ccxio_.write_structural(m, mats, Tn, st, "BC_BOARD", si, solver="")
    ccxio_.run_ccx(si, threads=8)
    sres = ccxio_.read_frd(si.with_suffix(".frd"))
    sm = PE.metrics.structural_metrics(m, sres["DISP"], sres["STRESS"], st)
    du = _corner_shear(m, sres["DISP"])
    return {"arch": arch, "mode": mode, "template": el["template"],
            "cooler": cooler_name if mode == "AFTER" else "calibrated Robin h=166000",
            "h_sub_mm": h_sub, "status": "OK",
            "P_elec_total_w": el["P_elec_total_w"],
            **{f"L_{k}": v for k, v in el["ledger"].terms.items()},
            "P_converter_w": el["ledger"].converter_total(),
            "P_interconnect_w": el["ledger"].interconnect_total(),
            "T_max_C": th["T_max_C"], "T_mean_C": th["T_mean_C"],
            "T_conv_C": t_conv, "T_pkg_C": t_pkg,
            "dT_fluid_span_K": th.get("dT_fluid_span_K", 0.0),
            "h_effective_W_m2K": th.get("h_effective_W_m2K", LEGACY_H_TOP),
            "fluid_iters": th.get("fluid_iters", 0),
            "energy_residual_pct": th["energy_residual_pct"],
            "die_warpage_pv_um": sm["die_warpage_pv_um"],
            "pkg_warpage_pv_um": sm["pkg_warpage_pv_um"],
            "du_corner_um": du, "et_iters": len(hist),
            "et_converged": hist[-1]["dT_K"] < tol_k,
            "intra_infeasible": el["intra_infeasible"],
            "wall_s": time.time() - t0, "hist": hist,
            "tiers": el["tiers"], "ledger_rows": el["ledger"].as_rows(f"{arch}_{mode}")}


def _solve_legacy(arch: str, h_sub_mm: float, hm, wd: Path, h_xy: float) -> dict:
    """The Phase-0M production boundary: one calibrated h, one uniform sink temperature,
    and the heat deposited exactly as before (die + converter only)."""
    import numpy as _np
    wd.mkdir(parents=True, exist_ok=True)
    doe = PE.load_doe()
    st, extra, _ = ZG.stack_for(arch, h_sub_mm)
    side = math.sqrt(274.89 / N_VR)
    xy = kw1.tiles_for("uniform", side, st, doe, N_VR)
    tiles = [PE.Tile(cx, cy, side, side, hm.converter_w / N_VR) for cx, cy in xy]
    m = PE.build(tiles, st, h_sub_mm, h_xy=h_xy, z_scale=1.4, support_layer=False,
                 extra_bottom_layers=extra)
    mats = PE.build_materials(st)
    ti = wd / "legacy_th.inp"
    films = PE.ccxio.write_thermal(m, mats, tiles, st, hm.die_w, LEGACY_H_TOP, ti)
    PE.ccxio.run_ccx(ti, threads=8)
    frd = wd / "legacy_th.frd"
    if not frd.is_file():
        return {"status": "CCX FAILED"}
    Tn = PE.ccxio.read_frd(frd)["NDTEMP"]
    Tnode = Tn[1:m.n_nodes + 1, 0]
    tm = PE.metrics.thermal_metrics(m, Tn, films, st, hm.die_w + hm.converter_w,
                                    LEGACY_H_TOP)
    return {"status": "OK", "mesh": m, "materials": mats, "stack": st, "tiles": tiles,
            "T_node": Tnode, "T_max_C": tm["T_max_C"], "T_mean_C": tm["T_mean_C"],
            "T_min_C": tm["T_min_C"], "energy_residual_pct": tm["energy_residual_pct"],
            "conv_layer": PE.converter_layer(arch, m),
            "dT_fluid_span_K": 0.0, "h_effective_W_m2K": LEGACY_H_TOP, "fluid_iters": 0,
            "deposited_w": hm.die_w + hm.converter_w}


def _corner_shear(m, U) -> float:
    zl = {L.name: (L.z0, L.z1) for L in m.layers}
    z0, z1 = zl["bga"]
    nb, nt = m.node_ids_at_z(z0), m.node_ids_at_z(z1)
    pb, pt = m.nodes[nb - 1], m.nodes[nt - 1]
    rb = np.hypot(pb[:, 0], pb[:, 1])
    sel = nb[rb > 0.92 * rb.max()]
    best = 0.0
    for idb in sel:
        p = m.nodes[idb - 1]
        j = int(np.argmin((pt[:, 0] - p[0]) ** 2 + (pt[:, 1] - p[1]) ** 2))
        idt = nt[j]
        best = max(best, math.hypot(U[idt, 0] - U[idb, 0], U[idt, 1] - U[idb, 1]))
    return best * 1000.0
