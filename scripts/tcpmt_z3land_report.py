"""Z3 with its 1 V spreading in the coupled ledger: the numbers (TCPMT revision).

Reads the coupled cases of tcpmt_z3land_variants (research/final_closure/sensitivity/
etm_Z3_HV_S0__z3_land_*.json) and the three-tier reference cases, and writes
research/tcpmt_revision/z3_land_coupled.json:

  per run     total loss, conversion / routing, land-side and board-plane rows, per-rail
              static spread, T_max, die warpage, critical joint (du, T), R* against Z1 of
              the same cooling tier, the within-tier ranking, and the deposit check
  derived     the land-side copper at which coupled Z3-B ties Z1-B, and the copper that
              keeps the land-side static spread within 30 mV (3 % of 1 V)
  deposit     the *_fvmap runs against their uniform-deposit twins (T_max, warpage, joint)
  sharing     the equal-ball-sharing assumption against a free (Kirchhoff) division of the
              board-plane + BGA + land-side network (tcpmt_z3land_fv.network_check), context

R* is computed exactly as scripts/tcpmt_tier_feed.py does (final_closure_direct_feed.
platform_point / crossover on the case's converged temperatures, Z1 of the same tier as the
reference), with the variant's ledger patch active so the re-solved Z3 ledger carries the
same spreading rows as the coupled case.

The deposit check is independent of the solver path: each run's final thermal deck (.inp) is
parsed -- nodes, elements, the E_SRC sets and their *DFLUX body fluxes -- and sum(BF x V) is
compared with the load plus the ledger total of the case.

    python tcpmt_z3land_report.py   -> research/tcpmt_revision/z3_land_coupled.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_z3land_variants as V                                   # noqa: E402
import tcpmt_z3land_fv as FV                                        # noqa: E402
import final_closure_sensitivity as S                               # noqa: E402
import final_closure_physical_etm as E                              # noqa: E402
import final_closure_ledger as FL                                   # noqa: E402

OUT = R / "research" / "tcpmt_revision" / "z3_land_coupled.json"
D = R / "research" / "final_closure"
#: the three-tier reference cases (tcpmt_manuscript_macros.TIERS, S0)
REF = {"A": {"Z1": D / "etm_Z1_HV_S0_h1.1_r21.json", "Z2": D / "etm_Z2_HV_S0_h1.1_r21.json",
             "Z3": S.OUT / "etm_Z3_HV_S0__z3_top_only.json"},
       "B": {"Z1": S.OUT / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
             "Z2": S.OUT / "etm_Z2_HV_S0__z2_cooled_tim.json",
             "Z3": S.OUT / "etm_Z3_HV_S0__z3_plate_tim.json"}}
DROP_LIMIT_MV = 30.0


def conv_of(rows):
    return sum(r["P_w"] for r in rows if r["term"].startswith("P_conv_"))


def summary(c):
    m = c.get("mechanics") or {}
    js = m.get("joint_search") or {}
    crit = js.get("critical") or {}
    h = c["et_history"][-1]
    conv = conv_of(c["ledger_rows"])
    return {"P_loss_w": c["P_loss_w"], "P_conversion_w": conv,
            "P_routing_w": c["P_loss_w"] - conv, "T_max_C": c["thermal"]["T_max_C"],
            "T_die_mean_C": h.get("T_die_mean_C"), "T_sub_C": h.get("T_sub_C"),
            "T_ls_C": h.get("T_ls_C"), "T_conv_C": h.get("T_conv_C"),
            "die_warpage_pv_um": m.get("die_warpage_pv_um"),
            "critical_joint": ({"du_um": crit.get("du_um"), "T_C": crit.get("T_C"),
                                "x_mm": crit.get("x_mm"), "y_mm": crit.get("y_mm")}
                               if crit else None),
            "T_joint_hottest_C": max((x["T_C"] for x in js.get("ranked", [])), default=None),
            "et_converged": c.get("et_converged"), "et_iterations": len(c["et_history"]),
            "mechanics_error": c.get("mechanics_error")}


def r_star(case, p_z1, t_um=None, plane=True):
    """tcpmt_tier_feed.py's R*, with the variant's ledger rows active (t_um None = the
    reference ledger, both spreading rows NOT_MODELLED)."""
    import final_closure_direct_feed as DF
    V.configure(t_um if t_um is not None else 1.0, plane)
    V.STATE["t_um"] = t_um
    temps = DF.converged_temps(case)
    base = DF.platform_point("HV_S0", temps, 0.0, arch="Z3")
    r = DF.crossover("HV_S0", temps, p_z1, arch="Z3")
    return {"P_Z1_w": p_z1, "P_internal_w": case["P_loss_w"],
            "P_internal_recomputed_w": base["P_total_w"],
            "advantage_at_zero_feed_w": p_z1 - case["P_loss_w"],
            "R_star_mohm": None if r is None else r * 1e3,
            "meaning": "0 = Z3 behind Z1 even with a lossless 48 V feed"}


# ------------------------------------------------------------------ deposit check
def parse_deck(inp):
    """sum over *DFLUX body-flux sets of BF x element volume, from the deck alone."""
    nodes, elems, sets, flux = {}, {}, {}, {}
    mode, cur = None, None
    with open(inp) as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            if s.startswith("*"):
                u = s.upper()
                mode, cur = None, None
                if u.startswith("*NODE FILE") or u.startswith("*NODE PRINT"):
                    mode = None
                elif u.startswith("*NODE") and "NSET" not in u.split(",")[0]:
                    mode = "node"
                elif u.startswith("*ELEMENT"):
                    mode = "elem"
                elif u.startswith("*ELSET") and "ELSET=E_SRC_" in u.replace(" ", ""):
                    cur = u.replace(" ", "").split("ELSET=")[1]
                    sets[cur] = []
                    mode = "set"
                elif u.startswith("*DFLUX"):
                    mode = "dflux"
                continue
            if mode == "node":
                p = s.split(",")
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
            elif mode == "elem":
                p = [int(x) for x in s.split(",") if x]
                elems[p[0]] = p[1:]
            elif mode == "set":
                sets[cur] += [int(x) for x in s.split(",") if x]
            elif mode == "dflux":
                p = s.split(",")
                flux[p[0].strip().upper()] = (p[1].strip().upper(), float(p[2]))
    xyz = np.zeros((max(nodes) + 1, 3))
    for k, v in nodes.items():
        xyz[k] = v
    out, tot = [], 0.0
    for name, ids in sets.items():
        kind, bf = flux[name]
        if kind != "BF":
            raise RuntimeError(f"{inp}: {name} carries {kind}, not a body flux")
        conn = np.array([elems[e] for e in ids])
        p = xyz[conn]
        vol = np.abs((p[:, 1, 0] - p[:, 0, 0]) * (p[:, 3, 1] - p[:, 0, 1])
                     * (p[:, 4, 2] - p[:, 0, 2]))
        w = bf * float(vol.sum())
        tot += w
        out.append({"set": name, "n_elems": len(ids), "BF_W_mm3": bf,
                    "volume_mm3": float(vol.sum()), "W": w})
    return {"deck": str(inp), "sets": out, "sum_BF_x_V_W": tot}


def deposit_check(variant, case):
    th = case["thermal"]
    total = FL.P_LOAD_W + case["P_loss_w"]
    rows = {r["term"]: r["P_w"] for r in case["ledger_rows"]}
    chk = {"deposit_residual_rel_reported": th["deposit_residual_rel"],
           "Q_ledger_W_reported": th["Q_ledger_W"], "Q_deposited_W_reported": th["Q_deposited_W"],
           "load_plus_P_loss_W": total,
           "Q_ledger_minus_load_plus_P_loss_W": th["Q_ledger_W"] - total}
    ins = (case.get("z3_land") or {}).get("deposit_inspection")
    if ins:
        regs = ins["regions"]

        def spread(layer):
            """the not-tile-confined region(s) of a layer: one uniform set, or the FV-map bins"""
            sel = [r for r in regs if r["layers"] == [layer] and r["in_tiles"] is not True]
            if not sel:
                return None
            return {"sets": [r["set"] for r in sel], "W": sum(r["W"] for r in sel),
                    "n_elems": sum(r["n_elems"] for r in sel),
                    "volume_mm3": sum(r["volume_mm3"] for r in sel),
                    "xy_extent_mm": [min(r["xy_extent_mm"][0] for r in sel),
                                     max(r["xy_extent_mm"][1] for r in sel),
                                     min(r["xy_extent_mm"][2] for r in sel),
                                     max(r["xy_extent_mm"][3] for r in sel)]}
        land, plane = spread(FL.LAYERS["Z3"]["tsv"]), spread(FL.LAYERS["Z3"]["pcb_via"])
        chk["regions"] = regs
        chk["land_region"] = land
        chk["land_region_W_minus_row_W"] = (land["W"] - rows[V.LAND_TERM]) if land else None
        chk["plane_region"] = plane
        chk["plane_region_W_minus_row_W"] = ((plane["W"] - rows[V.PLANE_TERM])
                                             if plane else None)
        chk["sum_regions_W"] = sum(r["W"] for r in regs)
    try:
        frd = V.last_thermal_frd(variant)
        deck = parse_deck(frd.with_suffix(".inp"))
        chk["deck"] = deck
        chk["deck_sum_minus_load_plus_P_loss_rel"] = (deck["sum_BF_x_V_W"] - total) / total
    except (IndexError, FileNotFoundError) as e:
        chk["deck"] = f"not available: {e}"
    return chk


def tmax_location(variant, m):
    """Where the converged field peaks: node coordinates and the layer that holds them, and
    the peak of the die alone (from the run's final thermal result)."""
    import production_et as PE
    try:
        frd = V.last_thermal_frd(variant)
    except (IndexError, FileNotFoundError):
        return None
    tn = PE.ccxio.read_frd(frd)["NDTEMP"][1:m.n_nodes + 1, 0]
    k = int(np.nanargmax(tn))
    x, y, z = (float(v) for v in m.nodes[k])
    lay = [L.name for L in m.layers if L.z0 - 1e-9 <= z <= L.z1 + 1e-9]
    die = np.unique(m.elems[m.elem_set(layer="die") - 1].ravel()) - 1
    sub = np.unique(m.elems[m.elem_set(layer="sub_lower") - 1].ravel()) - 1
    return {"T_C": float(tn[k]), "x_mm": x, "y_mm": y, "z_mm": z, "layers": lay,
            "T_die_max_C": float(np.nanmax(tn[die])),
            "T_sub_lower_max_C": float(np.nanmax(tn[sub])),
            "T_sub_lower_min_C": float(np.nanmin(tn[sub])), "frd": frd.name}


# ------------------------------------------------------------------ derived thicknesses
def root_in_inverse_t(ts, ps, target):
    """t at which P(t) = target, P interpolated in u = 1/t by the quadratic through the
    three points nearest the crossing (the spreading loss is linear in u, the thermal
    feedback adds a weak curvature); also the linear-in-u value of the bracketing pair."""
    u = 1.0 / np.asarray(ts, float)
    p = np.asarray(ps, float)
    o = np.argsort(u)
    u, p = u[o], p[o]
    f = p - target
    br = [i for i in range(len(u) - 1) if f[i] * f[i + 1] <= 0]
    if not br:
        # outside the sampled range: linear in u through the two nearest points
        i = 0 if abs(f[0]) < abs(f[-1]) else len(u) - 2
        uu = u[i] + (target - p[i]) * (u[i + 1] - u[i]) / (p[i + 1] - p[i])
        return {"t_um": 1.0 / uu if uu > 0 else None, "bracketed": False,
                "method": "linear in 1/t, extrapolated"}
    i = br[0]
    u_lin = u[i] - f[i] * (u[i + 1] - u[i]) / (f[i + 1] - f[i])
    idx = sorted(range(len(u)), key=lambda k: abs(u[k] - u_lin))[:3]
    c = np.polyfit(u[idx], p[idx], 2) if len(idx) == 3 else np.polyfit(u[idx], p[idx], 1)
    rts = np.roots(np.polysub(c, [target]))
    rts = [float(r.real) for r in rts if abs(r.imag) < 1e-12 and u[i] - 1e-12 <= r.real <= u[i + 1] + 1e-12]
    u_q = rts[0] if rts else u_lin
    return {"t_um": 1.0 / u_q, "t_um_linear_in_inverse_t": 1.0 / u_lin, "bracketed": True,
            "bracket_t_um": [1.0 / u[i + 1], 1.0 / u[i]],
            "method": "quadratic in 1/t through the three nearest runs"}


def drop_thickness(t_land_of_t, limit_mv=DROP_LIMIT_MV, n_rails=1):
    """t_Cu with n_rails x kappa_V I_dc rho(T_land(t)) / (t occ) = limit (fixed point)."""
    k = FV.land_shape()["kappa_V_one_rail"]
    t = 50.0
    for _ in range(50):
        r_s_t = V.rho_cu(t_land_of_t(t)) / V.LAND_OCC            # Ohm m (R_s x t)
        t_new = n_rails * k * V.I_DC_A * r_s_t / (limit_mv * 1e-3) * 1e6
        if abs(t_new - t) < 1e-9:
            break
        t = t_new
    return {"t_um": t, "T_land_C": t_land_of_t(t), "n_rails": n_rails}


def main():
    V.patch_ledger()                      # the spreading rows (switched by V.STATE per run)
    V.patch_regions()                     # converged temperatures carry T_land / T_board
    refs = {t: {a: json.loads(f.read_text()) for a, f in row.items()} for t, row in REF.items()}
    out = {"model": __doc__.split("\n\n")[1].strip(),
           "shape_factors": json.loads(FV.OUT.read_text())["used_in_coupled_ledger"],
           "land_fv_source": FV.land_shape()["source"],
           "board_plane_fv_source": FV.OUT.relative_to(R).as_posix(),
           "board_allocation": json.loads(FV.OUT.read_text())["board_planes"]["allocation"],
           "references": {t: {a: {"file": REF[t][a].name, **summary(c)}
                              for a, c in row.items()} for t, row in refs.items()},
           "runs": {}}
    for t in ("A", "B"):                  # the reference Z3 (spreading NOT_MODELLED) R*
        out["references"][t]["Z3"]["R_star"] = r_star(refs[t]["Z3"], refs[t]["Z1"]["P_loss_w"])
    mesh = E.build("Z3", E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)[0]
    for name, (t_um, tier, plane) in V.RUNS.items():
        f = S.case_file("Z3", name)
        if not f.exists():
            continue
        c = json.loads(f.read_text())
        rows = {r["term"]: r for r in c["ledger_rows"]}
        z = c.get("z3_land") or {}
        rec = {"file": f.relative_to(R).as_posix(), "t_land_um": t_um, "cooling_tier": tier,
               "board_planes_in_ledger": plane, **summary(c),
               "P_land_w": rows[V.LAND_TERM]["P_w"],
               "P_board_plane_w": rows[V.PLANE_TERM]["P_w"],
               "land": z.get("land"), "board": z.get("board"),
               "board_bound_uncoupled": z.get("board_bound_uncoupled"),
               "T_land_C": c["et_history"][-1].get(f"T_{V.LAND_KEY}_C"),
               "T_board_C": c["et_history"][-1].get(f"T_{V.BOARD_KEY}_C")}
        if z.get("land"):
            rec["dV_land_static_one_rail_mV"] = z["land"]["dV_static_one_rail_mV"]
        if z.get("board"):
            rec["dV_board_static_VDD_mV"] = z["board"]["dV_static_VDD_mV"]
            rec["dV_board_static_GND_mV"] = z["board"]["dV_static_GND_mV"]
        ref = refs[tier]
        rec["R_star"] = r_star(c, ref["Z1"]["P_loss_w"], t_um, plane)
        rank = sorted([("Z1", ref["Z1"]["P_loss_w"]), ("Z2", ref["Z2"]["P_loss_w"]),
                       ("Z3", c["P_loss_w"])], key=lambda x: x[1])
        rec["ranking_in_tier"] = [{"arch": a, "P_loss_w": p} for a, p in rank]
        rec["vs_Z1_same_tier_w"] = c["P_loss_w"] - ref["Z1"]["P_loss_w"]
        rec["vs_Z2_same_tier_w"] = c["P_loss_w"] - ref["Z2"]["P_loss_w"]
        rec["vs_Z1B_w"] = c["P_loss_w"] - refs["B"]["Z1"]["P_loss_w"]
        rec["vs_Z2B_w"] = c["P_loss_w"] - refs["B"]["Z2"]["P_loss_w"]
        rec["delta_vs_reference_Z3_w"] = c["P_loss_w"] - ref["Z3"]["P_loss_w"]
        rec["deposit_check"] = deposit_check(name, c)
        rec["deposit"] = (c.get("z3_land") or {}).get("deposit", "uniform")
        rec["T_max_location"] = tmax_location(name, mesh)
        rec["task"] = z.get("task")
        out["runs"][name] = rec
    out["derived"] = derived(out, refs)
    out["table"] = compact_table(out)
    out["equal_sharing_context"] = sharing_context(refs)
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    table(out)
    print("wrote", OUT)


def derived(out, refs):
    runs = out["runs"]
    p_z1b = refs["B"]["Z1"]["P_loss_w"]
    d = {"P_Z1B_w": p_z1b, "P_Z2B_w": refs["B"]["Z2"]["P_loss_w"]}
    both = {r["t_land_um"]: r for k, r in runs.items()
            if r["cooling_tier"] == "B" and r["board_planes_in_ledger"] and k not in V.FVMAP}
    ctrl = runs.get("z3_land_t40_B_noplane")
    if len(both) >= 2:
        ts = sorted(both)
        d["tie_with_board_planes"] = {
            **root_in_inverse_t(ts, [both[t]["P_loss_w"] for t in ts], p_z1b),
            "runs_t_um": ts, "P_loss_w": [both[t]["P_loss_w"] for t in ts],
            "board_allocation": "2 x 35 um Cu per rail, 80 %"}
    if ctrl and 40.0 in both:
        # the coupled effect of the board planes, measured at t = 40 um (both - control),
        # scaled to each run by its own plane row
        dp40 = both[40.0]["P_loss_w"] - ctrl["P_loss_w"]
        row40 = both[40.0]["P_board_plane_w"]
        d["board_plane_coupled_increment_t40_w"] = dp40
        d["board_plane_row_t40_w"] = row40
        d["board_plane_feedback_t40_w"] = dp40 - row40
        ts = sorted(both)
        lo = [both[t]["P_loss_w"] - dp40 * both[t]["P_board_plane_w"] / row40 for t in ts]
        half = [both[t]["P_loss_w"] - 0.5 * dp40 * both[t]["P_board_plane_w"] / row40 for t in ts]
        d["land_only_P_loss_w_estimated"] = dict(zip(map(str, ts), lo))
        d["land_only_P_loss_w_t40_coupled"] = ctrl["P_loss_w"]
        d["tie_land_only"] = {**root_in_inverse_t(ts, lo, p_z1b),
                              "basis": "coupled runs minus the board planes' coupled increment "
                                       "(measured at t = 40 um by the no-plane control, scaled "
                                       "by each run's plane row)"}
        d["tie_with_2oz_central_planes"] = {
            **root_in_inverse_t(ts, half, p_z1b),
            "basis": "board planes on the four 2-oz central layers (2 x 69.6 um per rail): "
                     "half the 2 x 35 um plane term, same scaling"}
    # land-side static spread <= 30 mV, at the land temperature of the cooling-B runs
    tb = sorted((r["t_land_um"], r["T_land_C"]) for k, r in runs.items()
                if r["cooling_tier"] == "B" and r["board_planes_in_ledger"] and r["T_land_C"]
                and k not in V.FVMAP)
    if tb:
        tt, TT = zip(*tb)

        def t_land_of_t(t):
            return float(np.interp(1.0 / t, 1.0 / np.asarray(tt)[::-1], np.asarray(TT)[::-1]))
        d["drop_30mV_one_rail"] = drop_thickness(t_land_of_t, n_rails=1)
        d["drop_30mV_VDD_plus_GND"] = drop_thickness(t_land_of_t, n_rails=2)
        d["drop_rule"] = ("land-side static spread (max - min of the rail plane potential, FV) "
                          "at the DC rail current 1000 A, rho_Cu at the coupled land-side "
                          "temperature of the cooling-B runs (interpolated in 1/t)")
    # deposit distribution: the FV-map deposit against the uniform one, same run otherwise
    for name in sorted(V.FVMAP):
        base = name.replace("_fvmap", "")
        if name in runs and base in runs:
            a, b = runs[base], runs[name]
            ca, cb = a["critical_joint"] or {}, b["critical_joint"] or {}
            d.setdefault("deposit_sensitivity", {})[name] = {
                "against": base,
                "dP_loss_w": b["P_loss_w"] - a["P_loss_w"],
                "dT_max_K": b["T_max_C"] - a["T_max_C"],
                "dT_land_K": (b["T_land_C"] or 0) - (a["T_land_C"] or 0),
                "dT_board_K": (b["T_board_C"] or 0) - (a["T_board_C"] or 0),
                "d_die_warpage_um": ((b["die_warpage_pv_um"] or 0) - (a["die_warpage_pv_um"] or 0)
                                     if a["die_warpage_pv_um"] and b["die_warpage_pv_um"]
                                     else None),
                "d_du_c_um": (cb.get("du_um") - ca.get("du_um")
                              if cb.get("du_um") and ca.get("du_um") else None),
                "dT_joint_K": (cb.get("T_C") - ca.get("T_C")
                               if cb.get("T_C") and ca.get("T_C") else None),
                "uniform": {k: a[k] for k in ("P_loss_w", "T_max_C", "die_warpage_pv_um",
                                              "critical_joint", "T_land_C", "T_board_C")},
                "fv_map": {k: b[k] for k in ("P_loss_w", "T_max_C", "die_warpage_pv_um",
                                             "critical_joint", "T_land_C", "T_board_C")}}
    return d


def sharing_context(refs):
    """The coupled rows assume EQUAL ball sharing, as the ledger's BGA rows do. The free
    (Kirchhoff) division of the same board-plane + BGA + land-side network dissipates less
    (Thomson's principle) but loads the balls unevenly (tcpmt_z3land_fv.network_check, at
    the reference Z3-B temperatures). Uncoupled estimate of Z3-B under the free division:
    reference Z3-B + (free board + BGA + land) - (equal BGA, already in the reference)."""
    h = refs["B"]["Z3"]["et_history"][-1]
    t_c = {"t_land_c": h["T_sub_C"], "t_board_c": h["T_pcb_via_C"], "t_bga_c": h["T_bga_C"]}
    nc = FV.network_check(**t_c)
    g = FV.network_check(t_land_um=(40.0,), h_mm=FV.GRID_CHECK_MM, **t_c)["cases"][0]
    p_ref, p_z1 = refs["B"]["Z3"]["P_loss_w"], refs["B"]["Z1"]["P_loss_w"]
    est = {}
    for c in nc["cases"]:
        tr = c["two_rails"]
        p = p_ref + tr["free_network"]["sum_w"] - tr["equal_sharing"]["bga_w"]
        est[str(c["t_land_um"])] = {"P_Z3B_free_sharing_est_w": p, "ahead_of_Z1B_w": p_z1 - p}
    return {"network_check": nc,
            "grid_check_t40_0p05mm": {"free_over_equal": g["two_rails"]["free_over_equal"],
                                      "two_rails": g["two_rails"]},
            "temperatures_from": REF["B"]["Z3"].name,
            "Z3B_free_sharing_estimate": est,
            "note": "free sharing puts ~365 of ~685 balls per rail above the 1.5 A criterion "
                    "that set the 667-ball count (max ~3.3-3.4 A); equal sharing is what that "
                    "criterion presumes"}


def compact_table(out):
    """One row per primary run (uniform deposit), with its FV-map deposit counterpart where
    it exists: the numbers a results table needs."""
    rows = []
    for name, r in out["runs"].items():
        if name in V.FVMAP:
            continue
        cj = r["critical_joint"] or {}
        loc = r.get("T_max_location") or {}
        row = {"run": name, "file": r["file"], "cooling_tier": r["cooling_tier"],
               "t_land_um": r["t_land_um"], "board_planes_in_ledger": r["board_planes_in_ledger"],
               "P_loss_w": r["P_loss_w"], "P_conversion_w": r["P_conversion_w"],
               "P_routing_w": r["P_routing_w"], "P_land_w": r["P_land_w"],
               "P_board_plane_w": r["P_board_plane_w"],
               "P_board_plane_bound_uncoupled_w": (r.get("board_bound_uncoupled") or {}).get("P_w"),
               "dV_land_static_one_rail_mV": r.get("dV_land_static_one_rail_mV"),
               "dV_board_static_VDD_mV": r.get("dV_board_static_VDD_mV"),
               "T_land_C": r["T_land_C"], "T_board_C": r["T_board_C"],
               "T_max_C": r["T_max_C"], "T_max_at": loc.get("layers"),
               "T_max_xyz_mm": [loc.get("x_mm"), loc.get("y_mm"), loc.get("z_mm")],
               "T_die_max_C": loc.get("T_die_max_C"),
               "die_warpage_pv_um": r["die_warpage_pv_um"], "du_c_um": cj.get("du_um"),
               "T_joint_C": cj.get("T_C"), "joint_xy_mm": [cj.get("x_mm"), cj.get("y_mm")],
               "R_star_mohm": r["R_star"]["R_star_mohm"],
               "ranking_in_tier": " < ".join(x["arch"] for x in r["ranking_in_tier"]),
               "vs_Z1_same_tier_w": r["vs_Z1_same_tier_w"],
               "vs_Z2_same_tier_w": r["vs_Z2_same_tier_w"]}
        fv = out["runs"].get(name + "_fvmap")
        if fv:
            cf = fv["critical_joint"] or {}
            lf = fv.get("T_max_location") or {}
            row["fv_map_deposit"] = {"P_loss_w": fv["P_loss_w"], "T_max_C": fv["T_max_C"],
                                     "T_max_at": lf.get("layers"),
                                     "T_max_xyz_mm": [lf.get("x_mm"), lf.get("y_mm"),
                                                      lf.get("z_mm")],
                                     "T_die_max_C": lf.get("T_die_max_C"),
                                     "die_warpage_pv_um": fv["die_warpage_pv_um"],
                                     "du_c_um": cf.get("du_um"), "T_joint_C": cf.get("T_C"),
                                     "joint_xy_mm": [cf.get("x_mm"), cf.get("y_mm")],
                                     "R_star_mohm": fv["R_star"]["R_star_mohm"],
                                     "file": fv["file"]}
        rows.append(row)
    return rows


def table(out):
    hdr = ("run", "P", "conv", "route", "land", "plane", "dVland", "Tmax", "warp", "du_c",
           "Tj", "R*", "rank")
    print(" ".join(f"{h:>8s}" for h in hdr))
    for n, r in out["runs"].items():
        cj = r["critical_joint"] or {}
        rs = r["R_star"]["R_star_mohm"]
        print(" ".join([f"{n[8:]:>8s}"] + [f"{x:8.2f}" if isinstance(x, (int, float)) else
                                           f"{str(x):>8s}" for x in (
            r["P_loss_w"], r["P_conversion_w"], r["P_routing_w"], r["P_land_w"],
            r["P_board_plane_w"], r.get("dV_land_static_one_rail_mV"), r["T_max_C"],
            r["die_warpage_pv_um"], cj.get("du_um"), cj.get("T_C"), rs)]
            + [" < ".join(x["arch"] for x in r["ranking_in_tier"])]))
    print(json.dumps(out["derived"], indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
