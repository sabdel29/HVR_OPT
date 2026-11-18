"""Supplementary material: every parameter, mesh, boundary, solver setting, runtime and
variant behind the paper, generated from the objects the solvers use (TCPMT review MC15).

Writes manuscript_v2/supplement/supp_tables.tex (included by the supplement's main file).
Sections that depend on artifacts not yet present are emitted as a marked placeholder, so the
supplement always compiles.

    python tcpmt_supplement.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
FC = R / "research" / "final_closure"
TR = R / "research" / "tcpmt_revision"
OUT = R / "manuscript_v2" / "supplement" / "supp_tables.tex"
ARCHS = ("Z1", "Z2", "Z3")
NAMES = {"Z1": "embedded", "Z2": "package-backside", "Z3": "board-backside"}


def J(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else None


def tex(s):
    out = []
    for ch in str(s):
        out.append({"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&",
                    "#": r"\#", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}",
                    "<": r"\textless{}", ">": r"\textgreater{}", "$": r"\$", "{": r"\{",
                    "}": r"\}"}.get(ch, ch))
    return "".join(out)


def num(x, d=3):
    if x is None:
        return "--"
    if isinstance(x, (list, tuple)):
        return "/".join(num(v, d) for v in x)
    try:
        v = float(x)
    except (TypeError, ValueError):
        return tex(x)
    if v == 0:
        return "0"
    a = abs(v)
    if a >= 1e4 or a < 1e-3:
        m, e = f"{v:.{max(d - 1, 1)}e}".split("e")
        return f"${m}\\times10^{{{int(e)}}}$"
    return f"{v:.{d}g}"


def placeholder(title, what):
    return [f"\\subsection*{{{title}}}", f"\\emph{{Pending: {tex(what)}.}}", ""]


# ------------------------------------------------------------------ materials and stacks
def build_all():
    import final_closure_physical_etm as E
    out = {}
    for a in ARCHS:
        m, mats, st, tiles, info = E.build(a, E.PRODUCTION_H_XY, E.PRODUCTION_REFINE)
        out[a] = (m, st, tiles, info)
    return out


def card_value(c, key):
    v = c.get(key)
    if isinstance(v, dict):
        return v.get("value"), v.get("status"), v.get("note") or v.get("source")
    return v, None, None


def materials_table(B):
    used = {}
    for a, (m, st, tiles, info) in B.items():
        for name in sorted(set(m.elem_material)):
            used.setdefault(name, {"archs": [], "card": st["materials"][name]})
            used[name]["archs"].append(a)
    L = [r"\subsection*{S1. Material cards}",
         r"Values exactly as passed to the solvers (conductivity in W\,m$^{-1}$K$^{-1}$, "
         r"modulus in GPa, CTE in ppm/K). $k$: isotropic or (in-plane/through-thickness); "
         r"status: SOURCE\_BACKED (datasheet or handbook), DERIVED (homogenized from "
         r"constituents by a verified rule), PROVISIONAL or ASSUMPTION (declared, varied in the "
         r"sensitivity study). Properties are temperature-independent except where noted.",
         r"\begin{longtable}{@{}p{2.6cm}p{2.1cm}rrrp{1.6cm}p{1.0cm}@{}}", r"\toprule",
         r"Card & $k$ & $E$ & $\nu$ & CTE & Status & Used in \\", r"\midrule", r"\endhead"]
    for name, d in sorted(used.items()):
        c = d["card"]
        ko, _, _ = card_value(c, "k_ortho")
        k, ks, _ = card_value(c, "k")
        kk = (f"{ko[0]:.3g}/{ko[2]:.3g}" if isinstance(ko, (list, tuple)) else num(k))
        E_, _, _ = card_value(c, "E")
        nu, _, _ = card_value(c, "nu")
        cte, _, _ = card_value(c, "cte")
        if c.get("elastic_type") == "ortho" and E_ is None:
            E_s, nu_s = "cubic", "cubic"
        else:
            E_s = num(E_ / 1e3 if isinstance(E_, (int, float)) else E_)
            nu_s = num(nu)
        cte_s = num(cte * 1e6 if isinstance(cte, (int, float)) else cte)
        L.append(f"{tex(name)} & {kk} & {E_s} & {nu_s} & {cte_s} & "
                 f"{tex(c.get('status', ks or ''))} & {', '.join(d['archs'])} \\\\")
    L += [r"\bottomrule", r"\end{longtable}", ""]
    return L


def stack_tables(B):
    L = [r"\subsection*{S2. Layer stacks as meshed}",
         r"Every layer of the production mesh, bottom to top ($z$ in mm; the board top is "
         r"$z=-0.3$ for Z1/Z2). Materials per layer are the element materials present.", ""]
    for a, (m, st, tiles, info) in B.items():
        import numpy as np
        lay = np.array(m.elem_layer, dtype=object)
        mat = np.array(m.elem_material, dtype=object)
        L += [f"\\paragraph*{{{a} ({NAMES[a]})}}",
              r"\begin{tabular}{@{}lrrl@{}}", r"\toprule",
              r"Layer & $z_0$ & $t$ (\textmu m) & Materials \\", r"\midrule"]
        for ly in m.layers:
            mats_ = sorted(set(mat[lay == ly.name]))
            L.append(f"{tex(ly.name)} & {ly.z0:.4f} & {1e3 * (ly.z1 - ly.z0):.0f} & "
                     f"{tex(', '.join(mats_))} \\\\")
        L += [r"\bottomrule", r"\end{tabular}", ""]
    return L


# ------------------------------------------------------------------ mesh, solvers, runtimes
def mesh_runtime_table():
    import final_closure_physical_etm as E
    L = [r"\subsection*{S3. Meshes, solvers and runtimes}",
         r"Production mesh: graded $h_{xy}=1.1$~mm grid with every in-plane interval split in "
         r"two (r21); 8-node hexahedra (thermal C3D8, structural C3D8I incompatible modes); "
         r"CalculiX~2.23. Thermal: steady conduction, direct solver; E--T stop: every coupled "
         r"region temperature changes $<0.25$~K and the loss $<0.1$\,\%; coolant energy balance "
         r"iterated to 0.02~K. Structural: linear thermoelastic, $T_{\mathrm{ref}}=25\,^\circ$C, "
         r"rigid-body motion restrained only, ITERATIVE CHOLESKY (verified against the direct "
         r"SPOOLES solver to $10^{-4}$ on the base mesh). Machine: two-socket Intel Xeon Gold "
         r"6342 (2.8~GHz, 48 cores), shared; thermal solves on 2 threads, structural on 1.",
         r"\begin{tabular}{@{}lrrrrrrr@{}}", r"\toprule",
         r" & Nodes & Elements & Struct.\ DOF & E--T iter. & E--T (s) & Struct.\ (s) & "
         r"Total (h) \\", r"\midrule"]
    for a in ARCHS:
        c = J(FC / f"etm_{a}_HV_S0_h1.1_r21.json")
        th, me = c["thermal"], c.get("mechanics", {})
        tot = (c["et_wall_s"] + me.get("wall_s", 0)) / 3600
        L.append(f"{a} & {th['n_nodes']:,} & {th['n_elems']:,} & {3 * th['n_nodes']:,} & "
                 f"{len(c['et_history'])} & {c['et_wall_s']:.0f} & {me.get('wall_s', 0):.0f} & "
                 f"{tot:.1f} \\\\".replace(",", "{,}"))
    L += [r"\bottomrule", r"\end{tabular}", "",
          r"Times exclude geometry construction and meshing (under 2~min per architecture), "
          r"the local solder submodel (reported in S6) and postprocessing; they include every "
          r"E--T iteration (each a thermal solve with its coolant balance) and the structural "
          r"solve with the all-site joint search. Sensitivity runs repeat the same chain.", ""]
    return L


def cooling_table():
    c = J(TR / "cooling_spec.json")
    if not c:
        return placeholder("S4. Cold plate", "cooling_spec.json")
    p = c["plate"]
    g, f, rg, ht, hy, ti = (p["geometry"], p["fluid"], p["regime"], p["heat_transfer"],
                            p["hydraulics"], p["tim"])
    rows = [("Channels, width $\\times$ depth, fin", f"{g['channels']}, {g['w_ch_um']:.0f}$\\times${g['h_ch_um']:.0f}~\\textmu m, {g['t_fin_um']:.0f}~\\textmu m"),
            ("Channel length / plate width", f"{g['length_mm']:.2f} / {g['width_mm']:.2f} mm"),
            ("Base, solid", f"{g['t_base_um']:.0f}~\\textmu m Si, $k$ = {g['k_solid_W_mK']:.0f}"),
            ("Hydraulic diameter, aspect ratio", f"{g['D_h_um']:.1f}~\\textmu m, {g['aspect_ratio']:.3f}"),
            ("Coolant, inlet", f"water, {f['T_inlet_C']:.0f}\\,$^\\circ$C, {f['m_dot_g_s']:.0f}~g/s ({f['V_dot_ml_min']:.0f} ml/min) per plate"),
            ("Flow distribution", "uniform over the channels (ideal plenum)"),
            ("Velocity, $Re$, $Pr$", f"{rg['velocity_m_s']:.2f} m/s, {rg['Re']:.0f} (laminar), {f['Pr']:.2f}"),
            ("Entrance lengths $L_h$ / $L_{th}$", f"{rg['L_hydrodynamic_entrance_mm']:.1f} / {rg['L_thermal_entrance_mm']:.1f} mm"),
            ("$Nu$ (Shah--London, 3 walls, fully developed)", f"{ht['Nu_fully_developed_3walls']:.2f}"),
            ("$h_{\\mathrm{ch}}$, $\\eta_{\\mathrm{f}}$, $\\Lambda$", f"{ht['h_channel_W_m2K']:.0f} W/m$^2$K, {ht['fin_efficiency']:.3f}, {ht['area_amplification_Lambda']:.2f}"),
            ("$R_{\\mathrm{conv}}$, $R_{\\mathrm{cal}}$, $R_{\\mathrm{base}}$", f"{ht['R_conv_K_W'] * 1e3:.2f}, {ht['R_caloric_K_W'] * 1e3:.2f}, {ht['R_base_K_W'] * 1e3:.2f} mK/W"),
            ("$h_{\\mathrm{eff}}$ uniform sink / streamwise sink", f"{ht['h_eff_uniform_sink_W_m2K']:.0f} / {ht['h_eff_streamwise_sink_W_m2K']:.0f} W/m$^2$K"),
            ("$\\Delta p$ fully developed / with entrance and plenum", f"{hy['dp_fully_developed_kPa']:.0f} / {hy['dp_with_entrance_and_plenum_kPa']:.0f} kPa"),
            ("Pumping power, hydraulic", f"{hy['P_hydraulic_W']:.1f} W per plate"),
            ("Pumping power, shaft ($\\eta$ = 0.75/0.55/0.35)", f"{hy['P_shaft_eta_0.75_W']:.1f} / {hy['P_shaft_eta_0.55_W']:.1f} / {hy['P_shaft_eta_0.35_W']:.1f} W per plate"),
            ("TIM", f"{ti['thickness_um']:.0f}~\\textmu m, $k$ = {ti['k_W_mK']:.0f}, $h$ = {ti['h_W_m2K']:.0f} W/m$^2$K"),
            ("Coolant rise", f"{p['dT_fluid_K_per_kW']:.2f} K per kW")]
    L = [r"\subsection*{S4. Cold plate and cooling tiers}",
         r"\begin{tabular}{@{}p{4.2cm}p{4.2cm}@{}}", r"\toprule"]
    L += [f"{a} & {b} \\\\" for a, b in rows]
    L += [r"\bottomrule", r"\end{tabular}", "",
          r"Heat balance per case (W): total dissipated (die 1000~W plus package loss), to the "
          r"top plate, to the bottom plate (cooling~B), and to natural convection.",
          r"\begin{tabular}{@{}llrrrr@{}}", r"\toprule",
          r"Tier & Arch & Total & Top & Bottom & Natural \\", r"\midrule"]
    for t, v in c["tiers"].items():
        for a, x in v["cases"].items():
            L.append(f"{t} & {a} & {x['Q_total_W']:.1f} & {x['q_top_plate_W']:.1f} & "
                     f"{x['q_bottom_plate_W']:.1f} & "
                     f"{x['q_board_natural_W'] + x['q_converter_underside_natural_W']:.2f} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", ""]
    return L


def feasibility_table():
    f = J(TR / "feasibility.json")
    if not f:
        return placeholder("S5. Temperature feasibility", "feasibility.json")
    lim = f["limits"]
    L = [r"\subsection*{S5. Component and material temperature feasibility}",
         r"Maximum temperatures from the converged fields ($^\circ$C); GaN junction bounded "
         r"from the tier maximum by $R_{\theta\mathrm{JC}}$ at the device's own dissipation. "
         f"Limits: GaN $T_J\\le{lim['gan_Tj_C']:.0f}$; $R_{{DS(on)}}$ fit $\\le{lim['ron_fit_max_C']:.0f}$; "
         f"X7R/X7S capacitors $\\le{lim['mlcc_C']:.0f}$; inductor $\\le{lim['inductor_C']:.0f}$; "
         f"build-up dielectric and encapsulant $T_g\\approx{lim['buildup_Tg_C']:.0f}$; board "
         f"$T_g\\approx{lim['board_Tg_C']:.0f}$; solder law $\\le{lim['solder_cal_C']:.0f}$.",
         r"\begin{tabular}{@{}lrrrrrrrl@{}}", r"\toprule",
         r"Case & $T_J$ HS & $T_J$ LS & Caps & Ind. & RDL & Encap. & Joint & Fails \\",
         r"\midrule"]
    for lab, c in f["cases"].items():
        rg = c["regions"]
        fails = [k for k, v in c["checks"].items() if isinstance(v, dict) and not v["ok"]]
        L.append(f"{tex(lab)} & {rg['hs']['device']['Tj_bound_C']:.1f} & "
                 f"{rg['ls']['device']['Tj_bound_C']:.1f} & {rg['caps']['in_cells']['max_C']:.1f} & "
                 f"{rg['ind']['in_cells']['max_C']:.1f} & {rg['rdl']['all']['max_C']:.1f} & "
                 f"{rg['encapsulant']['all']['max_C']:.1f} & {c['joints']['T_critical_C']:.1f} & "
                 f"{tex(', '.join(fails) or 'none')} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", ""]
    return L


def solder_table():
    p = J(TR / "solder_parameters.json")
    if not p:
        return placeholder("S6. Local solder model", "solder_parameters.json (solder study)")
    L = [r"\subsection*{S6. Local solder model}", r"\begin{tabular}{@{}p{3.4cm}p{5.0cm}@{}}",
         r"\toprule", r"Quantity & Value (source) \\", r"\midrule"]

    def walk(d, pre=""):
        for k, v in d.items():
            if isinstance(v, dict) and not ({"value"} & set(v)):
                yield from walk(v, pre + k + ".")
            else:
                yield pre + k, v
    for k, v in walk(p):
        if isinstance(v, dict):
            val = v.get("value")
            src = v.get("source", "")
            s = f"{num(val) if not isinstance(val, str) else tex(val)} ({tex(src)})" if src else (
                num(val) if not isinstance(val, str) else tex(val))
        else:
            s = num(v) if not isinstance(v, str) else tex(v)
        L.append(f"{tex(k)} & {s} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", ""]
    return L


def variants_table():
    import final_closure_sensitivity as S
    L = [r"\subsection*{S7. Package decisions varied (robustness study)}",
         r"Each run changes one declared input on the production mesh and reruns the whole "
         r"chain (full) or the mechanics on the converged field (mech).",
         r"\begin{longtable}{@{}p{2.8cm}p{0.7cm}p{1.1cm}p{3.6cm}@{}}", r"\toprule",
         r"Variant & Kind & Archs & What changes \\", r"\midrule", r"\endhead"]
    for name, v in S.VARIANTS.items():
        L.append(f"{tex(name)} & {v['kind']} & {'/'.join(v['archs'])} & {tex(v['what'])} \\\\")
    L += [r"\bottomrule", r"\end{longtable}", ""]
    return L


def scenario_table():
    L = [r"\subsection*{S8. The selected regulator under the three input scenarios}",
         r"Package-internal loss, peak and low-side tier temperature, critical joint, "
         r"die warpage and local response (L3) per scenario, production cooling.",
         r"\begin{tabular}{@{}llrrrrrr@{}}", r"\toprule",
         r"Arch & Scen. & $P$ (W) & $T_{\max}$ & $T_{\mathrm{LS}}$ & $\du$ (\textmu m) at $T_{\mathrm{j}}$ & "
         r"Warp (\textmu m) & $k$ \\", r"\midrule"]
    import math
    kmap = {"S0": "1", "S1": "4", "S2": f"{math.sqrt(48):.2f}"}
    for a in ARCHS:
        for s in ("S0", "S1", "S2"):
            c = J(FC / f"etm_{a}_HV_{s}_h1.1_r21.json")
            if not c:
                continue
            me = c.get("mechanics") or {}
            cr = (me.get("joint_search") or {}).get("critical") or {}
            h = c["et_history"][-1]
            du = f"{cr['du_um']:.2f} at {cr['T_C']:.0f}" if cr else "--"
            warp = f"{me['die_warpage_pv_um']:.1f}" if me else "--"
            L.append(f"{a} & {s} & {c['P_loss_w']:.1f} & {c['thermal']['T_max_C']:.1f} & "
                     f"{h.get('T_ls_C', float('nan')):.1f} & {du} & {warp} & {kmap[s]} \\\\")
    L += [r"\bottomrule", r"\end{tabular}", ""]
    return L


def verification_table():
    acc = J(FC / "accuracy_speed_matrix.json")
    if not acc:
        return placeholder("S9. Verification", "accuracy_speed_matrix.json")
    L = [r"\subsection*{S9. Verification matrix}",
         r"\begin{longtable}{@{}p{2.6cm}p{2.9cm}rp{1.6cm}@{}}", r"\toprule",
         r"Stage & Reference & Error & Evidence \\", r"\midrule", r"\endhead"]
    for r in acc.get("rows", []):
        e = r.get("error")
        es = (f"{100 * e:+.3g}\\,\\%" if isinstance(e, (int, float)) else tex(e or "--"))
        L.append(f"{tex(r['stage'])} & {tex(r.get('reference_tool') or '--')} & {es} & "
                 f"{tex(r.get('evidence_class') or '')} \\\\")
    L += [r"\bottomrule", r"\end{longtable}", ""]
    return L


def uncertainty_table():
    u = J(TR / "uncertainty.json")
    if not u:
        return placeholder("S10. Uncertainty per output", "uncertainty.json")
    L = [r"\subsection*{S10. Uncertainty per output and architecture}"]
    L += u.get("latex_supplement", [])
    return L


def prior_table():
    f = R / "manuscript_v2" / "supplement" / "tab_prior_detailed.tex"
    if not f.is_file():
        return placeholder("S0. Prior work", "tab_prior_detailed.tex")
    return [r"\subsection*{S0. Capabilities of the closest prior work, with sources}",
            r"Every cell for the other works is supported by a quoted passage "
            r"(review\_work/novelty/notes.txt).", r"\def\PriorTableCompact{0}",
            r"\input{tab_prior_detailed}", ""]


def z3land_table():
    d = J(TR / "z3_land_coupled.json")
    if not d:
        return placeholder("S11. Z3 redistribution", "z3_land_coupled.json")
    L = [r"\subsection*{S11. Z3 with the land-side and board-plane redistribution coupled}",
         r"Land-side copper $t$, board planes $2\times35$~\textmu m per rail at 80\,\% "
         r"occupancy, equal ball sharing; S0. FV-map: the redistribution heat deposited along its "
         r"finite-volume loss map instead of uniformly.",
         r"\begin{tabular}{@{}lrrrrrrrr@{}}", r"\toprule",
         r"Run & $P$ (W) & Land (W) & Planes (W) & $\Delta V$ land (mV) & $T_{\max}$ & Warp & "
         r"$\du$ & $R^*$ \\", r"\midrule"]
    for r in d["table"]:
        L.append(f"{tex(r['run'])} & {num(r['P_loss_w'], 4)} & {num(r.get('P_land_w'), 3)} & "
                 f"{num(r.get('P_board_plane_w'), 3)} & {num(r.get('dV_land_static_one_rail_mV'), 3)} & "
                 f"{num(r.get('T_max_C'), 4)} & {num(r.get('die_warpage_pv_um'), 3)} & "
                 f"{num(r.get('du_c_um'), 3)} & {num(r.get('R_star_mohm'), 3)} \\\\")
    dv = d["derived"]
    L += [r"\bottomrule", r"\end{tabular}", "",
          f"Tie with Z1 under cooling~B: {dv['tie_with_board_planes']['t_um']:.0f}~\\textmu m "
          f"(land side alone: {dv['tie_land_only']['t_um']:.0f}~\\textmu m). Land-side drop "
          f"$\\le30$~mV per rail: $t \\ge {dv['drop_30mV_one_rail']['t_um']:.0f}$~\\textmu m.", ""]
    return L


def review_variants_table():
    import json as _j
    SENS = FC / "sensitivity"
    rows = []
    for f in sorted(SENS.glob("etm_*__*.json")):
        name = f.stem.split("__")[1]
        if not any(k in name for k in ("tim_warp_fb", "die_hotspot", "plate_local_h", "sdec",
                                       "z1_rated", "z1_input_decoupling", "z3_land")):
            continue
        c = J(f)
        me = c.get("mechanics") or {}
        cr = (me.get("joint_search") or {}).get("critical") or {}
        rows.append((f.stem.split("_")[1], name, c.get("P_loss_w"), c["thermal"]["T_max_C"],
                     me.get("die_warpage_pv_um"), cr.get("du_um"), cr.get("T_C")))
    L = [r"\subsection*{S12. Review-round variants}",
         r"Interface feedback (tim\_warp\_fb), die power map (die\_hotspot), caloric correction "
         r"(plate\_local\_h), implemented decoupling (sdec, z1\_input\_decoupling), rated flying "
         r"capacitors (z1\_rated\_cf: 830~\textmu m, cfmax: 1030~\textmu m), coupled Z3 "
         r"redistribution (z3\_land). Production mesh; A/B: cooling tier.",
         r"\begin{longtable}{@{}llrrrrr@{}}", r"\toprule",
         r"Arch & Variant & $P$ (W) & $T_{\max}$ & Warp (\textmu m) & $\du$ (\textmu m) & "
         r"$T_{\mathrm{j}}$ \\", r"\midrule", r"\endhead"]
    for a, n, p, t, w, du, tj in rows:
        L.append(f"{a} & {tex(n)} & {num(p, 4)} & {num(t, 4)} & {num(w, 3)} & {num(du, 3)} & "
                 f"{num(tj, 4)} \\\\")
    L += [r"\bottomrule", r"\end{longtable}", ""]
    return L


def capacitor_tables():
    L = []
    f = R / "manuscript_v2" / "supplement" / "tab_capacitor_evidence.tex"
    if f.is_file():
        L += [r"\subsection*{S13. Flying-capacitor evidence matrix}", r"\input{tab_capacitor_evidence}", ""]
    else:
        L += placeholder("S13. Flying-capacitor evidence matrix", "tab_capacitor_evidence.tex")
    d = J(TR / "cap49_comparison.json")
    if d:
        L += [r"\subsection*{S14. Flying capacitors of the 49-cell design}",
              r"Worst position ripple $\Delta V_{C_i,pp}/V_{C_i}$ (limit 10\,\%) with $-10$\,\% "
              r"tolerance; effective capacitance at bias and temperature from vendor data.",
              r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule",
              r"Part & Rated V & $C_1$ rating & ESR (m$\Omega$) & \multicolumn{3}{c}{Ripple at "
              r"25 / 105 / 125\,$^\circ$C} \\", r"\midrule"]
        for name, c in d["parts"].items():
            rp = [c["by_temperature"][k]["ripple_worst"] for k in ("25C", "105C", "125C")]
            rs = " & ".join("--" if (x is None or x == float("inf") or x > 9) else
                            f"{100 * x:.1f}\\,\\%" for x in rp)
            L.append(f"{tex(name)} & {c['v_max']:.0f} & {'pass' if c['rating_ok_C1'] else 'fail'} "
                     f"& {c['esr_mohm_at_fsw']:.2f} & {rs} \\\\")
        L += [r"\bottomrule", r"\end{tabular}", ""]
    else:
        L += placeholder("S14. Flying capacitors of the 49-cell design", "cap49_comparison.json")
    d = J(TR / "dse_caprule.json")
    if d:
        L += [r"\subsection*{S15. Regulator-count screen before and after the capacitor-rule "
              r"correction}",
              f"Legacy configuration reproduces the published screen: "
              f"{'yes' if d['legacy_reproduces_published'] else 'no'}. Total loss (W) and member "
              r"$N/K$ per count; --: infeasible.",
              r"\begin{tabular}{@{}rllll@{}}", r"\toprule",
              r"$M$ & Published & + voltage rule & + effective $C$ & + ESR($f$) \\", r"\midrule"]
        for r in d["per_count"]:
            def c(t):
                x = r.get(t)
                if not x:
                    return "--"
                nk = x["arch"].replace("N=", "").replace(",K=", "/").split(",")[0]
                return f"{x['P_total_W']:.1f} ({nk})"
            L.append(f"{r['M']} & {c('etm35')} & {c('etm35_caprule')} & {c('etm35_caprule_ripple')} "
                     f"& {c('etm35_caprule_full')} \\\\")
        L += [r"\bottomrule", r"\end{tabular}", "", tex(d["conclusion"]) + ".", ""]
    else:
        L += placeholder("S15. Regulator-count screen, corrected rule", "dse_caprule.json")
    return L


def json_lines(d, limit=80):
    import json as _j
    out = []
    for line in _j.dumps(d, indent=1, default=str).splitlines()[:limit]:
        out.append(line[:110])
    return out


def main():
    B = build_all()
    L = ["% GENERATED by scripts/tcpmt_supplement.py -- do not edit"]
    L += prior_table()
    L += materials_table(B)
    L += stack_tables(B)
    L += mesh_runtime_table()
    L += cooling_table()
    L += feasibility_table()
    L += solder_table()
    L += variants_table()
    L += scenario_table()
    L += verification_table()
    L += uncertainty_table()
    L += z3land_table()
    L += review_variants_table()
    L += capacitor_tables()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
