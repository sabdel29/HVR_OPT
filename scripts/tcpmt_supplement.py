"""Supplementary material: every parameter, mesh, boundary, solver setting, runtime and
variant behind the paper, generated from the objects the solvers use (TCPMT review MC15).

Writes manuscript_v2/supplement/supp_tables.tex, which the supplement's main file includes:
the section headings (in the order of the paper), every table as a captioned longtable and the
notes beneath it. LaTeX numbers the tables S1, S2, ... in reading order and every cross-reference
goes through a label, so adding or removing a table renumbers consistently. Tables whose inputs
are missing are emitted as a marked placeholder, so the supplement always compiles.

Inputs are read, never written. Internal identifiers (run, layer, card and case keys) are mapped
to readable labels here; an identifier without a mapping is printed as it is.

    python tcpmt_supplement.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
FC = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
#: generated supplement files (this script's output, tcpmt_capacitor_evidence's table) go under
#: $ETM_RESULTS_ROOT for a campaign (hook); hand-written inputs stay in the frozen tree
SUPP = Path(os.environ.get("ETM_RESULTS_ROOT") or R) / "manuscript_v2" / "supplement"
SUPP_SRC = R / "manuscript_v2" / "supplement"
OUT = SUPP / "supp_tables.tex"
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
    if not math.isfinite(v):
        return "--"
    a = abs(v)
    if a >= 1e4 or a < 1e-3:
        m, e = f"{v:.{max(d - 1, 1)}e}".split("e")
        return f"${m}\\times10^{{{int(e)}}}$"
    return f"{v:.{d}g}"


def sci(x, d=2):
    """Always in scientific notation (creep coefficients)."""
    if x is None:
        return "--"
    m, e = f"{float(x):.{d}e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


def p10(x):
    """A power of ten as $10^{n}$, anything else through num()."""
    if x and x > 0 and abs(math.log10(x) - round(math.log10(x))) < 1e-12:
        return f"$10^{{{int(round(math.log10(x)))}}}$"
    return num(x)


def fx(x, d=1):
    return "--" if x is None else f"{float(x):.{d}f}"


# ---------------------------------------------------------------- prose from data strings
# Plain-text tokens of the data files rendered as typeset prose; everything else is escaped.
_SPELL = (("homogenisation", "homogenization"), ("homogenised", "homogenized"),
          ("discretisation", "discretization"), ("stabilisation", "stabilization"),
          ("modelling", "modeling"), ("segfaults", "fails"))
def _sci_tex(m):
    mant, sign, exp = m.group(1), m.group(2), m.group(3)
    e = ("-" if sign == "-" else "") + exp
    return f"$10^{{{e}}}$" if float(mant) == 1 else f"${mant}\\times10^{{{e}}}$"


_RULES = [(re.compile(p), r) for p, r in (
    (r"(?<![\w.])(\d+(?:\.\d+)?)e([+-]?)0*(\d+)(?![\w.])", _sci_tex),
    (r"HV-S(\d)", lambda m: f"S{m.group(1)}"),
    (r"(?<![A-Za-z])M=(\d+)", lambda m: f"$M = {m.group(1)}$"),
    (r"(?<![A-Za-z])N=(\d+)", lambda m: f"$N = {m.group(1)}$"),
    (r"(?<![A-Za-z])N(\d)K(\d)K_A(\d)(?![A-Za-z0-9])",
     lambda m: f"$N{m.group(1)}K{m.group(2)}K_A{m.group(3)}$"),
    (r"(?<![A-Za-z])rho L / A(?![A-Za-z])", r"$\rho L/A$"),
    (r"R\*", r"$R^*$"),
    (r"(?<![A-Za-z])E = (?=\d)", r"$E$ = "),
    (r"dT_compact/dT_CFD", r"$\Delta T_{\mathrm{compact}}/\Delta T_{\mathrm{CFD}}$"),
    (r"(?<![A-Za-z_])T_max(?![A-Za-z_])", r"$T_{\max}$"),
    (r"(?<![A-Za-z_])R_eff(?![A-Za-z_])", r"$R_{\mathrm{eff}}$"),
    (r"(?<![A-Za-z_])du_c(?![A-Za-z_])", r"$\du$"),
    (r"critical-joint du(?![A-Za-z_])", r"critical-joint $\du$"),
    (r"(?<![A-Za-z_])k_xy(?![A-Za-z_])", r"$k_{xy}$"),
    (r"(?<![A-Za-z_])k_x(?![A-Za-z_])", r"$k_x$"),
    (r"(?<![A-Za-z_])k_z(?![A-Za-z_])", r"$k_z$"),
    (r"(?<![A-Za-z_])h_xy(?![A-Za-z_])", r"$h_{xy}$"),
    (r"(?<![A-Za-z_])P_loss(?![A-Za-z_])", r"$P$"),
    (r"(?<![A-Za-z])dT(?![A-Za-z_])", r"$\Delta T$"),
    (r"(?<![A-Za-z])eta(?![A-Za-z])", r"$\eta$"),
    (r"(?<![A-Za-z])rho_c(?![A-Za-z])", r"$\rho_{\mathrm{c}}$"),
    (r"(?<![A-Za-z])rho(?![A-Za-z_])", r"$\rho$"),
    (r"(?<=\d)\s?um(?![A-Za-z])", r"~\textmu m"),
    (r"(?<=\d)\s?uF(?![A-Za-z])", r"~\textmu F"),
    (r"(?<=\d)\s?mOhm(?![A-Za-z])", r"~m$\Omega$"),
    (r"(?<=\d)\s?Ohm(?![A-Za-z])", r"~$\Omega$"),
    (r"\(Ohm\)", r"($\Omega$)"),
    (r"W/m2K", r"W\,m$^{-2}$K$^{-1}$"),
    (r"W/mK", r"W\,m$^{-1}$K$^{-1}$"),
    (r"(?<=\d)\s?mm2(?![A-Za-z0-9])", r"~mm$^2$"),
    (r"(?<=[\d\s])x(?=\s?\d)", r"$\times$"),
    (r"(?<=\d) C(?![A-Za-z0-9])", r"\,$^\circ$C"),
    (r"<=", r"$\le$"), (r">=", r"$\ge$"), (r"->", r"$\to$"),
    (r"~(?=\d)", r"$\approx$"),
    (r"(?<=\d) ?%", r"\,\%"),
    (r"(?<=\d)-(?=\d)", r"--"),
    (r"(?<![\w.)])-(?=\d)", r"$-$"),
)]


def prose(s):
    s = str(s)
    for a, b in _SPELL:
        s = s.replace(a, b)
    out, i = [], 0
    while i < len(s):
        best = None
        for rx, rep in _RULES:
            m = rx.search(s, i)
            if m and m.end() > m.start() and (best is None or m.start() < best[0].start()):
                best = (m, rep)
        if best is None:
            out.append(tex(s[i:]))
            break
        m, rep = best
        out.append(tex(s[i:m.start()]))
        out.append(rep if isinstance(rep, str) else rep(m))
        i = m.end()
    return "".join(out)


def grab(pattern, text, cast=str, default=None):
    """A value that the data files carry only inside a description string."""
    m = re.search(pattern, str(text or ""))
    if not m:
        return default
    try:
        return cast(m.group(1))
    except (TypeError, ValueError):
        return default


def tm(v, spec="g"):
    """A number as text, in math mode when negative (a minus sign, not a hyphen)."""
    s = format(v, spec)
    return f"${s}$" if s.startswith("-") else s


def rng(a, b, unit=""):
    return f"{tm(float(a)) if str(a).startswith('-') else a}--{b}{unit}"


# ---------------------------------------------------------------- layout helpers
def section(title, lead=None):
    L = [rf"\section{{{title}}}"]
    if lead:
        L += [lead]
    return L + [""]


def ltab(spec, n, head, rows, caption, label, note=None, size=r"\footnotesize", sep="3pt"):
    """A captioned longtable: caption and label on the first head, the column head repeated on
    continuation pages, and the note set directly beneath the table."""
    lines = len(rows) + len(head) + 6 + (len(note) // 160 if note else 0)
    L = [rf"\needspace{{{min(lines, 40) * 0.8:.1f}\baselineskip}}",
         r"\begingroup" + size + rf"\setlength{{\tabcolsep}}{{{sep}}}",
         rf"\begin{{longtable}}{{{spec}}}",
         rf"\caption{{{caption}}}\label{{{label}}}\\",
         r"\toprule", *head, r"\midrule", r"\endfirsthead",
         rf"\multicolumn{{{n}}}{{@{{}}l}}{{\emph{{Table~\ref{{{label}}} (continued)}}}}\\",
         r"\toprule", *head, r"\midrule", r"\endhead",
         r"\midrule", rf"\multicolumn{{{n}}}{{r@{{}}}}{{\emph{{continued on next page}}}}\\",
         r"\endfoot", r"\bottomrule", r"\endlastfoot", *rows, r"\end{longtable}"]
    if note:
        L += [r"\nopagebreak\noindent " + note + r"\par"]
    L += [r"\endgroup", r"\medskip", ""]
    return L


def placeholder(title, what):
    return [rf"\noindent\emph{{Pending ({tex(title)}): input {tex(what)} not found.}}", ""]


DAGGER_NOTE = (r" $^\dagger$Z3 without the land-side and board-plane redistribution in the "
               r"coupled solution (the coupled cases are in Table~\ref{tab:supp-z3land}).")


def z3_dag(arch, case_file):
    """Marks a Z3 result that predates the coupled land-side redistribution (by its file)."""
    return r"$^\dagger$" if arch == "Z3" and "z3_land" not in str(case_file or "") else ""


# ---------------------------------------------------------------- S-I prior work
def prior_section():
    L = section("Comparison with Prior Work",
                r"Table~\ref{tab:supp-prior} details the capability comparison of the paper's "
                r"introduction. Every entry for another work rests on a passage of the cited "
                r"source; an entry that the accessible sources do not settle is marked ``?''.")
    if not (SUPP_SRC / "tab_prior_detailed.tex").is_file():
        return L + placeholder("prior work", "tab_prior_detailed.tex")
    return L + [r"\input{tab_prior_detailed}", ""]


# ---------------------------------------------------------------- S-II converter screen
def passive_library():
    """Library entries of the synthesis engine by name (inductors, capacitors); {} if absent."""
    try:
        sys.path.insert(0, str(R / "Scalable_Integrated_VR" / "src"))
        import HVR_FULL_OPT_EPC_V2 as H
        lib = {i.name: ("L", i) for i in H.INDUCTOR_LIBRARY}
        caps = list(H.default_capacitor_library("stress"))
        caps += list(getattr(H, "research_capacitor_library", lambda: [])())
        lib.update({c.name: ("C", c) for c in caps})
        return lib
    except Exception:                                               # noqa: BLE001
        return {}


def passive_label(name, lib, maker=False):
    """Inductor: inductance and DC resistance; capacitor: part number, capacitance, rating."""
    if not name:
        return "--"
    k, p = lib.get(name, (None, None))
    if k == "L":
        return f"{p.l_nh:.0f}~nH, {p.r_dcr_mohm:.1f}~m$\\Omega$"
    if k == "C":
        part = getattr(p, "vendor_part", None) or \
            re.sub(r"-[\d.]+u?F-[\d.]+V$", "", name).split("-", 1)[-1]
        pre = name.split("-")[0] + " " if maker and "-" in name else ""
        return f"{tex(pre + part)} ({p.c_uf:g}~\\textmu F, {p.v_max:.0f}~V)"
    return prose(name.replace("_", " "))


def dse_selection_table():
    d = TR / "dse_j35" / "data"
    f = d / "case_D_etm35_caprule_full.csv"
    if not f.is_file():
        return placeholder("per-count selection", "case_D_etm35_caprule_full.csv")
    rows = list(csv.DictReader(f.open()))
    meta = J(d / "meta_etm35_caprule_full.json") or {}
    lib = passive_library()
    body = []
    for r in rows:
        m = int(float(r["M"]))
        if r.get("feasible") != "True":
            why = prose((r.get("reason") or "no feasible member").replace("architecture", "member"))
            body.append(rf"{m} & \multicolumn{{8}}{{l}}{{{why}}} \\")
            continue
        top = f"$N{int(float(r['N']))}K{int(float(r['K']))}K_A{int(float(r['K_A']))}$"
        body.append(f"{m} & {top} & {tex(r['hs'])} / {tex(r['ls'])} & "
                    f"{passive_label(r.get('inductor'), lib)} & "
                    f"{passive_label(r.get('capacitor'), lib)} & "
                    f"{float(r['f_sw_Hz']) / 1e3:.1f} & {float(r['conv_loss_total_W']):.2f} & "
                    f"{float(r['routing_loss_W']):.2f} & {float(r['total_loss_W']):.2f} \\\\")
    head = [r"$M$ & Topology & HS / LS device & Inductor & Flying capacitor & "
            r"$f_{\mathrm{sw}}$ & \multicolumn{3}{c}{Loss (W)} \\",
            r"\cmidrule(l){7-9}",
            r" & & & & & (kHz) & Conversion & Routing & Total \\"]
    spec = r"@{}rllllrrrr@{}"
    note = (f"Specification: {meta.get('P_load', 1000) / 1e3:g}~kW at {meta.get('V_out', 1):g}~V "
            f"from {meta.get('V_in', 48):g}~V on a {meta.get('die_area_mm2', 500):g}-mm$^2$ die, "
            f"$J_{{\\mathrm{{t}}}} = {meta.get('J_target', 3.5):g}$~A\\,mm$^{{-2}}$; topology "
            r"re-synthesized at every count with the discrete device library (case~D) under the "
            r"corrected capacitor rule (Table~\ref{tab:supp-caprule}). HS/LS: high- and low-side "
            r"GaN devices; inductor: inductance and DC resistance. Losses are for the package of "
            r"$M$ regulators: conversion from the synthesis loss model, routing from the model "
            r"of~\cite{Krishnakumar2026DVPD} (electrical only).")
    return ltab(spec, 9, head, body,
                r"Converter selected at each regulator count (corrected capacitor rule)",
                "tab:supp-dse", note)


# ---------------------------------------------------------------- S-III package model
MAT_LABEL = {"bga_homog": "BGA layer (homogenized)", "board_fr4": "Board (homogenized)",
             "hvr_effective": "Converter tier (effective medium)",
             "microbump": "Microbump layer (homogenized)",
             "pcb_via_field": "Board via field (homogenized)", "rdl_tier": "RDL tier (laminate)",
             "silicon": "Silicon", "tim": "TIM", "tsv_tile": "TSV tile (homogenized)",
             "underfill_homog": "Underfill and encapsulant",
             "vr_attach": "VR attach to the substrate", "vr_attach_pcb": "VR attach to the board",
             "copper": "Copper", "tsv_homog": "TSV field (homogenized)"}
STATUS = {"SOURCE_BACKED": "source", "DERIVED": "derived", "PROVISIONAL": "provisional",
          "ASSUMPTION": "assumption"}


def mat_label(n):
    return MAT_LABEL.get(n, tex(n))


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
    body = []
    for name, d in sorted(used.items(), key=lambda kv: mat_label(kv[0])):
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
        st_ = c.get("status", ks or "")
        body.append(f"{mat_label(name)} & {kk} & {E_s} & {nu_s} & {cte_s} & "
                    f"{STATUS.get(st_, tex(st_.lower()))} & {', '.join(d['archs'])} \\\\")
    head = [r"Material card & $k$ & $E$ (GPa) & $\nu$ & CTE (ppm/K) & Basis & Used in \\"]
    note = (r"Values exactly as passed to the solvers, temperature-independent. $k$ in "
            r"W\,m$^{-1}$K$^{-1}$, isotropic or in-plane/through-thickness; silicon elastic "
            r"constants cubic. Basis: source, datasheet or handbook value; derived, homogenized "
            r"from the constituents by a rule verified in Table~\ref{tab:supp-verif}; provisional, "
            r"declared value varied in the robustness study (Table~\ref{tab:supp-variants}).")
    return ltab(r"@{}lrrrrll@{}", 7, head, body, "Material cards", "tab:supp-materials", note)


LAYER_LABEL = {"board": "Board", "bga": "BGA", "sub_lower": "Si substrate (TSV field)",
               "tile_band": "Si substrate, top band", "interface": "Microbump interface",
               "die": "Die", "tim": "TIM", "z2_top_rdl": "Top RDL",
               "conv_attach_vr_substrate": "VR attach to the substrate",
               "z3_attach_vr_pcb": "VR attach to the board"}
LAYER_PART = {"bottom_substrate_rdl": "RDL to the substrate", "interlayer_rdl": "interlayer RDL",
              "output_rdl": "output RDL", "land_side_attach_rdl": "land-side attach RDL",
              "flying_caps": "flying capacitors",
              "inductor_plus_cout": "inductors and output capacitors"}


def layer_label(n):
    if n in LAYER_LABEL:
        return LAYER_LABEL[n]
    m = re.match(r"^(?:z\d)?conv_(\d+)_(.+)$", n)
    if not m:
        return tex(n)
    i, part = m.groups()
    g = re.match(r"^gan_(hs|ls)_(.+)$", part)
    if g:
        lab = f"GaN {'high' if g.group(1) == 'hs' else 'low'} side ({tex(g.group(2))})"
    else:
        lab = LAYER_PART.get(part, tex(part.replace("_", " ")))
    return f"Converter tier {i}: {lab}"


def stack_tables(B):
    import numpy as np
    body = []
    for a, (m, st, tiles, info) in B.items():
        lay = np.array(m.elem_layer, dtype=object)
        mat = np.array(m.elem_material, dtype=object)
        if body:
            body.append(r"\midrule")
        body.append(rf"\multicolumn{{4}}{{@{{}}l}}{{\emph{{{a} ({NAMES[a]})}}}} \\")
        for ly in m.layers:
            mats_ = sorted(set(mat[lay == ly.name]))
            labs = [mat_label(x) for x in mats_]
            labs = labs[:1] + [lb[0].lower() + lb[1:] if lb[1:2].islower() else lb
                               for lb in labs[1:]]
            body.append(f"{layer_label(ly.name)} & {tm(ly.z0, '.4f')} & {1e3 * (ly.z1 - ly.z0):.0f} & "
                        f"{', '.join(labs)} \\\\")
    head = [r"Layer & $z_0$ (mm) & $t$ (\textmu m) & Materials present \\"]
    note = (r"Every layer of the production mesh, in the order of the mesh ($z_0$: bottom face; "
            r"the board top is at $z=-0.3$~mm in Z1 and Z2). Materials: the cards of "
            r"Table~\ref{tab:supp-materials} assigned to elements of the layer.")
    return ltab(r"@{}L{6.4cm}rrL{6.6cm}@{}", 4, head, body, "Layer stacks as meshed",
                "tab:supp-stacks", note)


def cooling_tables():
    c = J(TR / "cooling_spec.json")
    if not c:
        return placeholder("cold plate", "cooling_spec.json")
    p = c["plate"]
    g, f, rg, ht, hy, ti = (p["geometry"], p["fluid"], p["regime"], p["heat_transfer"],
                            p["hydraulics"], p["tim"])
    rows = [("Channels, width $\\times$ depth, fin", f"{g['channels']}, {g['w_ch_um']:.0f}$\\times${g['h_ch_um']:.0f}~\\textmu m, {g['t_fin_um']:.0f}~\\textmu m"),
            ("Channel length / plate width", f"{g['length_mm']:.2f} / {g['width_mm']:.2f} mm"),
            ("Base, solid", f"{g['t_base_um']:.0f}~\\textmu m Si, $k$ = {g['k_solid_W_mK']:.0f}~W\\,m$^{{-1}}$K$^{{-1}}$"),
            ("Hydraulic diameter, aspect ratio", f"{g['D_h_um']:.1f}~\\textmu m, {g['aspect_ratio']:.3f}"),
            ("Coolant, inlet", f"water, {f['T_inlet_C']:.0f}\\,$^\\circ$C, {f['m_dot_g_s']:.0f}~g/s ({f['V_dot_ml_min']:.0f} ml/min) per plate"),
            ("Flow distribution", "uniform over the channels (ideal plenum)"),
            ("Velocity, $Re$, $Pr$", f"{rg['velocity_m_s']:.2f} m/s, {rg['Re']:.0f} (laminar), {f['Pr']:.2f}"),
            ("Entrance lengths $L_h$ / $L_{th}$", f"{rg['L_hydrodynamic_entrance_mm']:.1f} / {rg['L_thermal_entrance_mm']:.1f} mm"),
            ("$Nu$ (Shah--London, 3 walls, fully developed)", f"{ht['Nu_fully_developed_3walls']:.2f}"),
            ("$h_{\\mathrm{ch}}$, $\\eta_{\\mathrm{f}}$, $\\Lambda$", f"{ht['h_channel_W_m2K']:.0f} W\\,m$^{{-2}}$K$^{{-1}}$, {ht['fin_efficiency']:.3f}, {ht['area_amplification_Lambda']:.2f}"),
            ("$R_{\\mathrm{conv}}$, $R_{\\mathrm{cal}}$, $R_{\\mathrm{base}}$", f"{ht['R_conv_K_W'] * 1e3:.2f}, {ht['R_caloric_K_W'] * 1e3:.2f}, {ht['R_base_K_W'] * 1e3:.2f} mK/W"),
            ("$h_{\\mathrm{eff}}$ uniform sink / streamwise sink", f"{ht['h_eff_uniform_sink_W_m2K']:.0f} / {ht['h_eff_streamwise_sink_W_m2K']:.0f} W\\,m$^{{-2}}$K$^{{-1}}$"),
            ("$\\Delta p$ fully developed / with entrance and plenum", f"{hy['dp_fully_developed_kPa']:.0f} / {hy['dp_with_entrance_and_plenum_kPa']:.0f} kPa"),
            ("Pumping power, hydraulic", f"{hy['P_hydraulic_W']:.1f} W per plate"),
            ("Pumping power, shaft ($\\eta$ = 0.75/0.55/0.35)", f"{hy['P_shaft_eta_0.75_W']:.1f} / {hy['P_shaft_eta_0.55_W']:.1f} / {hy['P_shaft_eta_0.35_W']:.1f} W per plate"),
            ("TIM", f"{ti['thickness_um']:.0f}~\\textmu m, $k$ = {ti['k_W_mK']:.0f}~W\\,m$^{{-1}}$K$^{{-1}}$, $h$ = {ti['h_W_m2K']:.0f} W\\,m$^{{-2}}$K$^{{-1}}$"),
            ("Coolant rise", f"{p['dT_fluid_K_per_kW']:.2f} K per kW")]
    L = ltab(r"@{}L{6.2cm}L{7.6cm}@{}", 2, [r"Quantity & Value \\"],
             [f"{a} & {b} \\\\" for a, b in rows], "Microchannel cold plate",
             "tab:supp-plate",
             r"One plate design for every cooled face: the top plate of coolings~A and~B and the "
             r"bottom plate of cooling~B, each behind the TIM listed.")
    body = []
    for t, v in c["tiers"].items():
        for a, x in v["cases"].items():
            if x.get("missing"):                # a compared case not run yet (tcpmt_cases)
                body.append(f"{t} & {a} & -- & -- & -- & -- \\\\")
                continue
            body.append(f"{t} & {a} & {x['Q_total_W']:.1f} & {x['q_top_plate_W']:.1f} & "
                        f"{x['q_bottom_plate_W']:.1f} & "
                        f"{x['q_board_natural_W'] + x['q_converter_underside_natural_W']:.2f} \\\\")
    head = [r"Cooling & Integration & Total & Top plate & Bottom plate & Natural convection \\"]
    land = [grab(r"z3_land_t(\d+)", v["cases"].get("Z3", {}).get("file"))
            for v in c["tiers"].values()]
    note = (r"Total: dissipated heat, the die's 1000~W plus the package loss. Cooling~A: top "
            r"plate; cooling~B: top plate and a bottom plate under the cell grid.")
    if land and all(land) and len(set(land)) == 1:
        note += (rf" Z3: land-side ({land[0]}~\textmu m) and board-plane redistribution in the "
                 r"coupled solution.")
    L += ltab(r"@{}llrrrr@{}", 6, head, body, "Heat balance per cooling and integration (W)",
              "tab:supp-heat", note)
    return L


# ---------------------------------------------------------------- S-IV flying capacitors
def capacitor_tables():
    L = section("Flying-Capacitor Technology",
                r"Table~\ref{tab:supp-capev} is the evidence behind the technology condition of "
                r"capacitor case~A0 and Table~\ref{tab:supp-cap49} compares the published "
                r"flying capacitor of the 49-cell design with the rated parts of case~A1.")
    if (SUPP / "tab_capacitor_evidence.tex").is_file():
        L += [r"\input{tab_capacitor_evidence}", ""]
    else:
        L += placeholder("flying-capacitor evidence matrix", "tab_capacitor_evidence.tex")
    d = J(TR / "cap49_comparison.json")
    if not d:
        return L + placeholder("49-cell flying capacitors", "cap49_comparison.json")
    body = []
    lib = passive_library()
    for name, c in d["parts"].items():
        rp = [c["by_temperature"][k]["ripple_worst"] for k in ("25C", "105C", "125C")]
        rs = " & ".join("--" if (x is None or x == float("inf") or x > 9) else
                        f"{100 * x:.1f}\\,\\%" for x in rp)
        body.append(f"{passive_label(name, lib, maker=True)} & {c['v_max']:.0f} & "
                    f"{'pass' if c['rating_ok_C1'] else 'fail'} & {c['esr_mohm_at_fsw']:.2f} & "
                    f"{rs} \\\\")
    head = [r"Part & Rated & $C_1$ & ESR at $f_{\mathrm{sw}}$ & \multicolumn{3}{c}{Worst "
            r"ripple $\Delta V_{C_i,\mathrm{pp}}/V_{C_i}$} \\", r"\cmidrule(l){5-7}",
            r" & V & rating & (m$\Omega$) & 25\,$^\circ$C & 105\,$^\circ$C & 125\,$^\circ$C \\"]
    dz = str(d.get("design", "")).split()
    if len(dz) > 1 and dz[-1] in ("kHz", "MHz"):
        dz = dz[:-2] + [dz[-2] + " " + dz[-1]]
    note = (f"Design: {prose(', '.join(dz))}. Ripple at the worst capacitor position, "
            r"limit 10\,\%, with the effective capacitance at bias and temperature from vendor "
            r"data less 10\,\% tolerance; --: no vendor bias data, so the effective capacitance "
            r"is unknown. $C_1$ rating: rated voltage times 0.8 against the 32~V that $C_1$ "
            r"holds.")
    return L + ltab(r"@{}lrlrrrr@{}", 7, head, body,
                    "Flying capacitors of the 49-cell design", "tab:supp-cap49", note)


# ---------------------------------------------------------------- S-V local solder model
JOINT_CASE = {"A_Z1": "Z1, A", "A_Z2": "Z2, A", "A_Z3": "Z3, A", "B_Z1": "Z1, B",
              "B_Z2": "Z2, B", "B_Z3": "Z3, B"}


def solder_tables():
    p = J(TR / "solder_parameters.json")
    L = section("Local Solder-Joint Model",
                r"Tables~\ref{tab:supp-card}--\ref{tab:supp-stress} list every parameter of the "
                r"local solder-joint model behind the published local responses, with its source "
                r"and calibrated range, and the limitations of the creep card.")
    if not p:
        return L + placeholder("local solder model", "solder_parameters.json")
    s = p["solder_SAC305"]
    el, yh, cr, ex = s["elastic"], s["yield_and_hardening"], s["creep"], s["expansion"]
    # -- card rows
    by_t = {}
    for r in el["rows"]:
        by_t.setdefault(r["T_C"], {}).update(E=r["E_MPa"] / 1e3, nu=r["nu"])
    for r in yh["rows"]:
        by_t.setdefault(r["T_C"], {}).update(sy=r["sigma_y0_MPa"], ss=r["sigma_sat_MPa"],
                                             es=r.get("eps_p_at_saturation"))
    for r in cr["rows"]:
        by_t.setdefault(r["T_C"], {}).update(A=r["A"], n=r["n"], m=r.get("m"))
    body = [f"{tm(t, '.0f')} & {num(v.get('E'))} & {num(v.get('nu'))} & {num(v.get('sy'), 4)} & "
            f"{num(v.get('ss'), 4)} & {sci(v.get('A'), 3)} & {num(v.get('n'), 4)} \\\\"
            for t, v in sorted(by_t.items())]
    t_rows = sorted(by_t)
    floor = grab(r"floor\s+([\d.]+)\s*MPa", el.get("law"), float)
    e_ref = by_t.get(25.0, {}).get("E")
    slope = ((by_t[t_rows[-1]]["E"] - by_t[t_rows[0]]["E"]) / (t_rows[-1] - t_rows[0])
             if len(t_rows) > 1 else None)
    es = next((v["es"] for v in by_t.values() if v.get("es") is not None), None)
    m_exp = next((v["m"] for v in by_t.values() if v.get("m") is not None), 0.0)
    head = [r"$T$ & $E$ & $\nu$ & $\sigma_{y0}$ & $\sigma_{\mathrm{sat}}$ & $A$ & $n$ \\",
            r"($^\circ$C) & (GPa) & & (MPa) & (MPa) & (s$^{-1}$MPa$^{-n}$) & \\"]
    note = (rf"Elasticity: $E(T) = {num(e_ref)} {'-' if slope < 0 else '+'} "
            rf"{abs(slope):.3g}\,(T-25)$~GPa"
            + (f" (floor {floor / 1e3:g}~GPa)" if floor else "") +
            r", constant $\nu$. Yield and hardening: $\sigma_y$ rises linearly from "
            r"$\sigma_{y0}$ at zero inelastic strain to $\sigma_{\mathrm{sat}}$ at an accumulated "
            rf"equivalent inelastic strain of {num(es)}, constant beyond; isotropic hardening. "
            r"Creep (Norton law of the overstress): $\dot\varepsilon_{\mathrm{in}} = A(T)\,"
            r"\langle\sigma_{\mathrm{vm}}-\sigma_y\rangle^{n(T)}\,t^{m}$ with "
            rf"$m={num(m_exp)}$, so no creep occurs below $\sigma_y$; $A$ for stress in MPa. "
            rf"Thermal expansion {ex['alpha_per_K'] * 1e6:.3g}~ppm/K, temperature-independent, "
            rf"stress-free at {ex['T_ref_C']:.0f}\,$^\circ$C. The solver interpolates every "
            r"column linearly between rows and holds the end rows outside them.")
    L += ltab(r"@{}rrrrrrr@{}", 7, head, body, "Solder (SAC305) card as passed to the solver",
              "tab:supp-card", note)

    # -- ingredients, sources, calibrated ranges
    band = grab(r"(\d+-\d+) GPa", el.get("source"))
    rp02 = grab(r"Rp0\.2 = ([\d.]+-[\d.]+) MPa", yh.get("cross_check"))
    s25 = by_t.get(25.0, {}).get("sy")
    ytab = grab(r"Table (\d+) Chaboche", yh.get("source"))
    clamp_hi = grab(r"clamped above ([\d.]+) C", yh.get("source"), float)
    alloy = grab(r"bulk (Sn[0-9.A-Za-z]+) ", cr.get("data"))
    npts = grab(r"(\d+) steady-state points", cr.get("data"), int)
    tmeas = grab(r"points at ([\d/]+) C", cr.get("data"))
    ctab = grab(r"Yuan 2023 Table (\d+)", cr.get("data"))
    sref = grab(r"sigma_ref = ([\d.]+) MPa", cr.get("card_row_rule"))
    qact = grab(r"Q = ([\d.]+) kJ/mol", cr.get("card_row_rule"))
    cte_rng = grab(r"(\d+-\d+) ppm/K", ex.get("source"))
    calr = cr.get("calibrated_range", {})
    cu = p.get("copper_pads", {})
    ycal = yh.get("calibrated_range_C") or []
    rows = [
        (r"Elasticity",
         r"Linear in $T$ (Table~\ref{tab:supp-card})",
         (rf"Room-temperature $E$: midpoint of the {prose(band)}-GPa band "
          r"of~\cite{Paska2024SAC305}" if band else r"\cite{Paska2024SAC305}") +
         r"; slope and $\nu$ assumed and varied in the sensitivity study",
         r"Room temperature only; no temperature dependence in the source"),
        (r"Yield and hardening",
         r"Bilinear, isotropic",
         rf"Chaboche fit of~\cite[Table~{ytab or '10'}]{{Yuan2023SAC305}} to stress--strain "
         r"curves of an Anand model fitted to SAC305 data~\cite{Motalab2012Anand}; rows "
         r"interpolated linearly in $T$" +
         (rf", held above {clamp_hi:g}\,$^\circ$C" if clamp_hi else "") +
         rf"; saturation strain {num(es)} a modeling choice. Check: measured $R_{{p0.2}}$ = "
         rf"{prose(rp02 or '--')}~MPa at room temperature~\cite{{Paska2024SAC305}} against "
         rf"$\sigma_{{y0}}(25\,^\circ\mathrm{{C}}) = {num(s25, 4)}$~MPa",
         (rng(f"{ycal[0]:g}", f"{ycal[1]:g}", r"\,$^\circ$C") if len(ycal) == 2 else "--") +
         r". In the viscoplastic steps $\sigma_y$ acts only as the creep threshold (no "
         r"rate-independent flow), as verified in the solver source and by probes"),
        (r"Creep",
         r"Norton law of the overstress",
         (rf"Steady-state tensile creep of bulk {tex(alloy)}~\cite{{Xiao2005SAC}}"
          if alloy else r"Tensile creep data of~\cite{Xiao2005SAC}") +
         (rf", as tabulated in~\cite[Table~{ctab}]{{Yuan2023SAC305}}" if ctab else "") +
         (rf"; {npts} points at {prose(tmeas)}\,$^\circ$C" if npts and tmeas else "") +
         r" (Table~\ref{tab:supp-creepfit}). Card rows: $n$ linear in $T$ between the measured "
         r"temperatures, constant below the lowest; $A$ from an Arrhenius fit of the rate" +
         (rf" at {sref}~MPa" if sref else "") + (rf" (apparent $Q = {qact}$~kJ/mol)" if qact
                                                   else ""),
         (rng(f"{calr['T_C'][0]:g}", f"{calr['T_C'][1]:g}", r"\,$^\circ$C") + ", " +
          rng(f"{calr['stress_MPa'][0]:g}", f"{calr['stress_MPa'][1]:g}", "~MPa")
          if calr.get("T_C") and calr.get("stress_MPa") else "--") +
         r" of applied (von~Mises) stress, not of the overstress the solver integrates; rows at "
         + ", ".join(tm(t) for t in calr.get("extrapolated_rows_C", [])) +
         r"\,$^\circ$C extrapolated"),
        (r"Thermal expansion",
         r"Constant",
         rf"{ex['alpha_per_K'] * 1e6:.3g}~ppm/K, assumed"
         + (rf", within the commonly quoted {prose(cte_rng)}~ppm/K" if cte_rng else ""),
         r"No temperature dependence"),
        (r"Copper pads",
         r"Linear elastic",
         rf"$E = {cu.get('E_MPa', 0) / 1e3:.0f}$~GPa, $\nu = {num(cu.get('nu'))}$, "
         rf"{cu.get('alpha_per_K', 0) * 1e6:.3g}~ppm/K; handbook-type constants, the package "
         r"model uses the same $E$",
         r"No temperature dependence"),
    ]
    st_ = yh.get("source_table") or {}
    srcfit = ""
    if st_.get("T_C") and st_.get("sigma_0_MPa") and st_.get("C_MPa") and st_.get("gamma"):
        srcfit = (rf" Yield and hardening, source fit~\cite[Table~{ytab or '10'}]{{Yuan2023SAC305}} "
                  r"at $T$ = " + "/".join(tm(t) for t in st_["T_C"]) + r"\,$^\circ$C: "
                  r"$\sigma_0$ = " + "/".join(f"{v:g}" for v in st_["sigma_0_MPa"]) +
                  r"~MPa, $C$ = " + "/".join(f"{v:g}" for v in st_["C_MPa"]) +
                  r"~MPa, $\gamma$ = " + "/".join(f"{v:g}" for v in st_["gamma"]) +
                  r"; the card takes $\sigma_{y0}=\sigma_0$ and $\sigma_{\mathrm{sat}} = "
                  r"\sigma_0 + C/\gamma$.")
    L += ltab(r"@{}L{2.0cm}L{2.3cm}L{7.6cm}L{5.1cm}@{}", 4,
              [r"Ingredient & Model form & Source & Calibrated range \\"],
              [" & ".join(r) + r" \\" for r in rows],
              "Sources and calibrated ranges of the solder card", "tab:supp-cardsrc",
              r"The alloy, the fitted variable and the extrapolated rows are limitations of the "
              r"creep card; Table~\ref{tab:supp-stress} gives the stresses at which the joints "
              r"actually creep." + srcfit)

    # -- creep fits at the measured temperatures
    fits = cr.get("data_fits_at_measured_T", [])
    body = []
    for x in fits:
        w = x["stress_window_MPa"]
        body.append(f"{x['T_C']:.0f} & {x['n_points']} & {w[0]:g}--{w[1]:g} & "
                    f"{sci(x['A'], 3)} & {x['n']:.3f} & {x['max_rel_rate_error_pct']:.1f} & "
                    f"{x['rms_rel_rate_error_pct']:.1f} \\\\")
    L += ltab(r"@{}rrrrrrr@{}", 7,
              [r"$T$ & Points & Stress & $A$ & $n$ & \multicolumn{2}{c}{Rate error (\%)} \\",
               r"\cmidrule(l){6-7}",
               r"($^\circ$C) & & (MPa) & (s$^{-1}$MPa$^{-n}$) & & max & RMS \\"],
              body, "Creep fits at the measured temperatures", "tab:supp-creepfit",
              (rf"Norton fits of the steady-state rates of~\cite{{Xiao2005SAC}} at each test "
               r"temperature, in the applied stress; the card rows of Table~\ref{tab:supp-card} "
               r"follow from these fits by the row rule of Table~\ref{tab:supp-cardsrc}."))

    # -- card versus intended law at the critical joints
    tj = cr.get("solver_vs_intended_at_tier_joints", {})
    fl = feas_labels()
    marked = False
    body = []
    for k, x in tj.items():
        lab, mk = joint_label(k, x["T_joint_C"], fl)
        marked |= mk
        body.append(f"{lab} & {x['T_joint_C']:.1f} & {sci(x['A_card'])} & "
                    f"{x['n_card']:.2f} & {sci(x['A_intended'])} & {x['n_intended']:.2f} & "
                    f"{x['rate_ratio_card_over_intended_at_30MPa']:.2f} & "
                    f"{100 * x['d_eps_card_grid_sensitivity_rel']:.2f} \\\\")
    rr = [x["rate_ratio_card_over_intended_at_30MPa"] for x in tj.values()]
    gs = [x["d_eps_card_grid_sensitivity_rel"] for x in tj.values()]
    fine = grab(r"on ([\d.]+) C rows", " ".join(cr.get("caveats", [])), float)
    gaps = [round(b - a, 6) for a, b in zip(t_rows, t_rows[1:])]
    dT = max(set(gaps), key=gaps.count) if gaps else None
    L += ltab(r"@{}lrrrrrrr@{}", 8,
              [r"Case & $T_{\mathrm{j}}$ & \multicolumn{2}{c}{Card, as interpolated} & "
               r"\multicolumn{2}{c}{Intended (Arrhenius)} & Rate ratio & $\deps$ change \\",
               r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}",
               r" & ($^\circ$C) & $A$ & $n$ & $A$ & $n$ & at 30~MPa & (\%) \\"],
              body, "Creep law of the card against the intended law at the critical joints",
              "tab:supp-cardgrid",
              (rf"Between rows {dT:g}\,$^\circ$C apart the solver interpolates $A$ linearly "
               r"instead of following the Arrhenius form from which the rows were built; at the "
               rf"critical joints its creep rate is {min(rr):.1f}--{max(rr):.1f} times the "
               r"intended one. $\deps$ change: effect of rebuilding the card on rows "
               rf"{fine:g}\,$^\circ$C apart ({100 * min(gs):.2f}--{100 * max(gs):.1f}\,\%), "
               r"contained in the uncertainty of the local response. Cases as in "
               r"Table~\ref{tab:supp-feas}." if rr and fine and dT else
               r"Cases as in Table~\ref{tab:supp-feas}.") + (DAGGER_NOTE if marked else ""))

    # -- geometry, boundary conditions, loading and integration
    g, bc, lc, ti, rsp = (p.get("geometry", {}), p.get("boundary_conditions", {}),
                          p.get("loading_cycle", {}), p.get("time_integration", {}),
                          p.get("response", {}))
    ab = g.get("averaging_band", {})
    ls, hs = ti.get("load_step", {}), ti.get("hold_step", {})
    ex_case = lc.get("example_case", {})
    halve = grab(r"< ([\d.]+) %", ti.get("dt0_source"))
    floor_rel = grab(r"below ([0-9.eE+-]+) x step period", ti.get("solver_floor"), float)
    unc = J(TR / "uncertainty.json") or {}
    eps_basis = unc.get("eps_basis")
    prow = [
        ("Ball, as homogenized globally",
         rf"diameter {g.get('ball_diameter_um', 0):.0f}~\textmu m, stand-off "
         rf"{g.get('standoff_height_um', 0):.0f}~\textmu m, pitch {g.get('pitch_um', 0):.0f}~\textmu m"
         r"~\cite[Table~III]{Krishnakumar2026DVPD}"),
        ("Solder volume",
         rf"equal-area square prism, side {g.get('solder_side_um', 0):.1f}~\textmu m (the "
         r"convention of the global ball-array homogenization)"),
        ("Copper pads", rf"{g.get('pad_side_um', 0):.0f}~\textmu m square, "
         rf"{g.get('pad_thickness_um', 0):.0f}~\textmu m thick, overhang "
         rf"{g.get('pad_overhang_um', 0):.1f}~\textmu m"),
        ("Averaging core",
         rf"solder less a band of {ab.get('band_um', 0):.1f}~\textmu m "
         rf"({ab.get('band_frac_of_side', 0):.3f} of the side, one L0 element) at the pads and "
         r"the free surface; core " + r"$\times$".join(f"{v:.0f}" for v in ab.get("core_um", []))
         + r"~\textmu m"),
        ("Elements", prose(p.get("mesh", {}).get("element", "--")) +
         r"; levels L0--L3 in Table~\ref{tab:supp-localmesh}"),
        ("Lower pad face", r"fixed, $u_x=u_y=u_z=0$"),
        ("Upper pad face", r"$u_y=u_z=0$; $u_x=\du$ in the hot half-cycle, 0 in the cold one"),
        ("Temperature", rf"uniform, prescribed per step; initial and stress-free "
         rf"{bc.get('initial_temperature_C', 25):.0f}\,$^\circ$C"),
        ("Global-to-local transfer",
         r"$\du=|u_{\mathrm{top}}-u_{\mathrm{bottom}}|_{xy}$ across the ball layer and "
         r"$T_{\mathrm{j}}$ at the critical site, from the package thermoelastic solution on the "
         r"converged electrothermal field"),
        ("Cycle",
         rf"{lc.get('n_cycles', '--')} cycles of {lc.get('period_s', 0):.0f}~s: "
         rf"{lc.get('dwell_hot_s', 0):.0f}~s at $T_{{\mathrm{{j}}}}$ with $\du$, then "
         rf"{lc.get('dwell_cold_s', 0):.0f}~s at {lc.get('T_cold_C', 25):.0f}\,$^\circ$C with "
         rf"$u_x = {lc.get('du_cold_um', 0):g}$; e.g., Z1 under cooling~A: "
         rf"$\du = {ex_case.get('du_um', 0):.2f}$~\textmu m at {ex_case.get('T_joint_C', 0):.1f}"
         r"\,$^\circ$C"),
        ("Load application",
         r"temperature and displacement change as steps at the start of each half-cycle, "
         rf"applied in a {lc.get('load_step_s', 0):g}-s step and held for "
         rf"{lc.get('hold_step_s', 0):g}~s at the same loads (a numerical device only)"),
        ("Time integration",
         rf"implicit (backward-Euler) viscoplastic update; creep tolerance {ti.get('CETOL', '--')} on the change "
         r"of inelastic strain rate per increment"),
        ("Increments, load step",
         rf"initial {ls.get('dt0_s', 0):g}~s, minimum {p10(ls.get('dt_min_s', 0))}~s, maximum "
         rf"{ls.get('dt_max_s', 0):g}~s, at most {ls.get('inc_max', 0):.0f}"),
        ("Increments, hold step",
         rf"initial {hs.get('dt0_s', 0):g}~s, minimum {p10(hs.get('dt_min_s', 0))}~s, maximum "
         rf"{hs.get('dt_max_s', 0):g}~s, at most {hs.get('inc_max', 0):.0f}"),
        ("Increment checks",
         (rf"halving the initial increment changes $\deps$ by less than {halve}\,\%"
          if halve else "--") +
         (rf"; the solver does not cut below {p10(floor_rel)} of the step period" +
          (rf" ({floor_rel * lc['load_step_s'] * 1e6:g}~\textmu s in the "
           rf"{lc['load_step_s']:g}-s load step)" if lc.get("load_step_s") else "")
          if floor_rel else "")),
        ("Response $\\deps$",
         r"increment over the last cycle of the volume-averaged accumulated equivalent "
         r"inelastic strain, $\varepsilon_{\mathrm{eq}}=\sum\sqrt{2/3}\,|\mathrm{d}"
         r"\varepsilon_{\mathrm{in}}|$, of the solder core; element value the mean of its "
         r"integration points, volume-weighted"),
        ("Uncertainty of $\\deps$",
         r"$U=U_{\mathrm{mesh}}+U_{\mathrm{time}}+U_{\mathrm{cyc}}$"),
    ]
    if eps_basis:
        ncyc = grab(r"(\d+) cycles", eps_basis)
        prow.append(("Compared responses",
                     (rf"stabilized L0 responses after {ncyc} cycles" if ncyc else
                      prose(eps_basis)) +
                     (r"; their $U$ adds the card-grid term" if "card grid" in eps_basis else "") +
                     r" (Table~\ref{tab:supp-unc})"))
    L += ltab(r"@{}L{3.6cm}L{13.2cm}@{}", 2, [r"Item & Setting \\"],
              [f"{a} & {b} \\\\" for a, b in prow],
              "Local model geometry, boundary conditions, loading and integration",
              "tab:supp-localsetup")

    # -- mesh family
    lev = p.get("mesh", {}).get("levels", {})
    body = [f"{k} & {v['n_xy_solder']}$\\times${v['n_xy_solder']}$\\times${v['n_z_solder']} & "
            f"{v['n_z_pad']} & {v['n_elements']} & {v['n_solder_elements']} & "
            f"{v['n_core_elements']} & {v['n_nodes']} & "
            f"{num(v['largest_inplane_solder_element_over_band'])} \\\\" for k, v in lev.items()]
    plr = p.get("mesh", {}).get("production_level_reported", "")
    note = (r"Nested hexahedral meshes; last column: largest in-plane solder element over the "
            r"averaging band. The comparison table of the paper reports L0 responses"
            + (r"; L3 is the production level declared by the mesh study." if "L3" in plr
               else "."))
    L += ltab(r"@{}lrrrrrrr@{}", 8,
              [r"Level & Solder & Pad & Elements & Solder & Core & Nodes & Element/ \\",
               r" & elements & layers & & elements & elements & & band \\"],
              body, "Local mesh family", "tab:supp-localmesh", note)

    # -- stress experienced under the production card
    se = p.get("stress_experienced_by_production_card", {})
    qs = ("q05", "q25", "q50", "q75", "q95")
    body = []
    for wkey, wlab in (("per_joint_strain_weighted", "strain-weighted"),
                       ("per_joint_time_weighted", "time-weighted")):
        blk = se.get(wkey, {})
        if not blk:
            continue
        if body:
            body.append(r"\midrule")
        body.append(rf"\multicolumn{{12}}{{@{{}}l}}{{\emph{{{wlab.capitalize()}}}}} \\")
        for k, x in blk.items():
            cells = [num(x["hot"][q]) for q in qs] + [num(x["cold"][q]) for q in qs]
            pk = num(se.get("peak_vm_MPa", {}).get(k)) if wkey.startswith("per_joint_strain") \
                else ""
            tjk = tj.get(k, {}).get("T_joint_C")
            lab = (joint_label(k, tjk, fl)[0] if tjk is not None
                   else JOINT_CASE.get(k, tex(k)))
            body.append(f"{lab} & " + " & ".join(cells) + f" & {pk} \\\\")
    win = [v for key in ("window_MPa_5_95pct_union_strain_weighted",
                         "window_MPa_5_95pct_union_time_weighted")
           for half in ("hot", "cold") for v in se.get(key, {}).get(half, [])]
    note = (r"Von~Mises stress of the element-mean stress over the last cycle in the solder "
            r"core, quantiles over the core weighted by the inelastic-strain increment times "
            r"volume (where the strain is deposited) or by time times volume (where the cycle is "
            r"spent); peak: largest value. Cases as in Table~\ref{tab:supp-feas}.")
    wtxt = []
    for key, lab in (("window_MPa_5_95pct_union_strain_weighted", "strain-weighted"),
                     ("window_MPa_5_95pct_union_time_weighted", "time-weighted")):
        w = se.get(key, {})
        if w.get("hot") and w.get("cold"):
            wtxt.append(f"{lab} {w['hot'][0]:.3g}--{w['hot'][1]:.3g}~MPa hot and "
                        f"{w['cold'][0]:.3g}--{w['cold'][1]:.3g}~MPa cold")
    if wtxt:
        note += r" 5--95\,\% windows over all joints: " + "; ".join(wtxt) + "."
    if win and calr.get("stress_MPa"):
        note += (rf" The joints creep at {min(win):.3g}--{max(win):.3g}~MPa (5--95\,\% windows), "
                 rf"against the {calr['stress_MPa'][0]:g}--{calr['stress_MPa'][1]:g}~MPa on which "
                 r"the creep card was calibrated.")
    if marked:
        note += DAGGER_NOTE
    L += ltab(r"@{}lrrrrrrrrrrr@{}", 12,
              [r"Case & \multicolumn{5}{c}{Hot half-cycle, quantile (MPa)} & "
               r"\multicolumn{5}{c}{Cold half-cycle, quantile (MPa)} & Peak \\",
               r"\cmidrule(lr){2-6}\cmidrule(lr){7-11}",
               r" & 5\,\% & 25\,\% & 50\,\% & 75\,\% & 95\,\% & 5\,\% & 25\,\% & 50\,\% & "
               r"75\,\% & 95\,\% & (MPa) \\"],
              body, "Stress at which the solder core creeps under the production card",
              "tab:supp-stress", note)

    # -- limitations of the creep card, in prose
    rows_A = {r["T_C"]: r["A"] for r in cr["rows"]}
    clamp = re.search(r"joint at ([\d.]+) C, (Z\d) HV-S(\d)", " ".join(cr.get("caveats", [])))
    afloor = grab(r"replaces any A t\^m < ([0-9.eE+-]+)", " ".join(cr.get("caveats", [])), float)
    items = []
    if alloy:
        items.append(rf"The creep data are for bulk {tex(alloy)}~\cite{{Xiao2005SAC}}, not for "
                     r"SAC305.")
    items.append(r"The card was fitted to the applied (von~Mises) stress, whereas the solver "
                 r"integrates the overstress $\sigma_{\mathrm{vm}}-\sigma_y$; the card therefore "
                 r"does not reproduce its own calibration data, and the joints creep far above "
                 r"the calibrated stresses (Table~\ref{tab:supp-stress}).")
    if rr:
        items.append(rf"Linear interpolation of $A$ between rows makes the creep rate at the "
                     rf"critical joints {min(rr):.1f}--{max(rr):.1f} times the intended one "
                     r"(Table~\ref{tab:supp-cardgrid}).")
    if clamp and t_rows:
        items.append(rf"Outside {tm(t_rows[0])} to {t_rows[-1]:g}\,$^\circ$C the solver holds the "
                     rf"end rows: a joint at {float(clamp.group(1)):g}\,$^\circ$C ("
                     rf"{clamp.group(2)}, S{clamp.group(3)}) uses the {t_rows[-1]:g}-$^\circ$C row.")
    if afloor and t_rows:
        items.append(rf"The solver replaces any $A\,t^m$ below {p10(afloor)} by {p10(afloor)}, so "
                     rf"the {tm(t_rows[0])}-$^\circ$C row ($A = {sci(rows_A[t_rows[0]], 1)[1:-1]}$) "
                     r"is never used.")
    L += [r"\noindent\emph{Limitations of the creep card.}", r"\begin{itemize}"]
    L += [rf"\item {x}" for x in items] + [r"\end{itemize}", ""]
    return L


# ---------------------------------------------------------------- S-VI verification
def mesh_runtime_table():
    body = []
    for a in ARCHS:
        c = J(FC / f"etm_{a}_HV_S0_h1.1_r21.json")
        if not c:
            continue
        th, me = c["thermal"], c.get("mechanics", {})
        tot = (c["et_wall_s"] + me.get("wall_s", 0)) / 3600
        body.append(f"{a} & {th['n_nodes']:,} & {th['n_elems']:,} & {3 * th['n_nodes']:,} & "
                    f"{len(c['et_history'])} & {c['et_wall_s']:.0f} & {me.get('wall_s', 0):.0f} & "
                    f"{tot:.1f} \\\\".replace(",", "{,}"))
    head = [r"Integration & Nodes & Elements & Structural & E--T & E--T & Structural & Total \\",
            r" & & & DOF & iterations & (s) & (s) & (h) \\"]
    note = (r"Production mesh: graded $h_{xy}=1.1$~mm grid with every in-plane interval split in "
            r"two (r21); 8-node hexahedra (thermal C3D8, structural C3D8I incompatible modes); "
            r"CalculiX~2.23. Thermal: steady conduction, direct solver; E--T stop: every coupled "
            r"region temperature changes by less than 0.25~K and the loss by less than 0.1\,\%; "
            r"coolant energy balance iterated to 0.02~K. Structural: linear thermoelastic, "
            r"$T_{\mathrm{ref}}=25\,^\circ$C, rigid-body motion restrained only, iterative "
            r"Cholesky solver (verified against the direct SPOOLES solver, "
            r"Table~\ref{tab:supp-verif}). Machine: two-socket Intel Xeon Gold 6342 (2.8~GHz, "
            r"48 cores), shared; thermal solves on 2 threads, structural on 1. Times include every "
            r"E--T iteration (each a thermal solve with its coolant balance) and the structural "
            r"solve with the all-site joint search; they exclude geometry construction and meshing "
            r"(under 2~min per integration), the local solder model and postprocessing. "
            r"Sensitivity runs repeat the same chain.")
    return ltab(r"@{}lrrrrrrr@{}", 8, head, body, "Meshes, solvers and runtimes (S0)",
                "tab:supp-mesh", note)


VERIF_LABEL = {
    "tsv_bulk": "TSV resistance", "tsv_tile_kz": "TSV tile, $k_z$",
    "tsv_tile_kx": "TSV tile, $k_{xy}$", "rdl_tier_kx": "RDL tier, $k_x$",
    "rdl_tier_kz": "RDL tier, $k_z$", "vr_attach_dense_kz": "Attach, dense, $k_z$",
    "vr_attach_dense_kxy": "Attach, dense, $k_{xy}$",
    "vr_attach_sparse_kz": "Attach, sparse, $k_z$",
    "vr_attach_sparse_kxy": "Attach, sparse, $k_{xy}$",
    "vr_attach_dense_electrical": "Attach, dense, bump resistance",
    "vr_attach_sparse_electrical": "Attach, sparse, bump resistance",
    "vr_attach_mechanical": "Attach, mechanical card", "pkg_rdl_Z1": "Package 48-V network, Z1",
    "pkg_rdl_Z2": "Package 1-V network, Z2", "thermal_column_aedt_Z1": "Thermal unit cell, Z1",
    "thermal_column_moose_Z1": "Thermal unit cell, Z1", "thermal_column_aedt_Z2":
    "Thermal unit cell, Z2", "thermal_column_moose_Z2": "Thermal unit cell, Z2",
    "mech_bilayer_closed_form": "Bilayer warpage", "mech_bilayer_aedt": "Bilayer warpage",
    "structural_solver_iterative_vs_direct": "Structural solver",
    "mesh_convergence_Z1": "Package mesh, Z1", "mesh_convergence_Z2": "Package mesh, Z2",
    "tsv_transition": "TSV end spreading", "rdl_plane_historical": "RDL sheet",
    "cooling_compact": "Cold-plate correlation", "homogenised_k_historical":
    "Homogenized conductivities", "cooling_icepak": "Cold-plate correlation",
    "converter_waveform": "Converter loss model", "pkg_rdl_convergence": "Package networks, mesh"}
REF_KIND = {"INDEPENDENT COMMERCIAL FEM": "independent commercial FEM",
            "INDEPENDENT OPEN-SOURCE FEM": "independent open-source FEM",
            "CLOSED FORM": "a closed form", "CLOSED FORM (model-form check)": "closed forms",
            "DIRECT SOLVER": "the direct solver"}


def verif_clean(s):
    s = str(s or "")
    for a, b in (("(equal_sharing_assessment)", ""), (" (Q3D and Maxwell are not licensed)", ""),
                 ("no circuit simulator installed and no switch-state schedule exists",
                  "no circuit-level simulation of the selected design exists"),
                 ("the physical lineage", "the final package geometry"),
                 ("physical ETM", "production package model"),
                 ("of the physical package", "of the package"),
                 ("the card is compared at the same f", "compared at the same metal fraction"),
                 ("MG is a dilute-limit form", "Maxwell-Garnett is a dilute-limit form"),
                 ("DECLARED", "declared"), ("ADOPTS", "adopts"), ("pass = True", "passed"),
                 ("named HV scenarios", "named input scenarios"), ("surf ", "surface "),
                 ("MOOSE heat_transfer-opt", "MOOSE"), ("graded FV sheet", "graded finite-volume sheet"),
                 ("aligned FV sheet", "aligned finite-volume sheet")):
        s = s.replace(a, b)
    return prose(re.sub(r"\s+;", ";", s).strip())


def verif_establishes(r):
    ev = r.get("evidence_class") or ""
    obs = verif_clean(r.get("observable") or "")
    ref = REF_KIND.get(r.get("reference_type") or "", "an independent solution")
    if r.get("status") == "HISTORICAL_REFERENCE_NOT_RERUN":
        return r"Agreement with the reference on an earlier package geometry"
    if ev == "UNVALIDATED":
        return (r"Bounds only: the response is carried for two cards, without a reference "
                r"solution" if r.get("status") == "BOUNDED" else
                r"No check: no reference solution is available")
    if ev == "MESH_CONVERGENCE":
        return f"Discretization change of {obs[0].lower() + obs[1:] if obs else 'the outputs'}"
    if ev == "SOLVER_VERIFICATION":
        return f"Agreement with {ref}: {obs}"
    if ev == "CLOSED_FORM_VERIFICATION":
        return f"Agreement with {ref}: {obs}"
    return f"Agreement with {ref}: {obs}" if obs else f"Agreement with {ref}"


def verification_table():
    acc = J(FC / "accuracy_speed_matrix.json")
    if not acc:
        return placeholder("verification matrix", "accuracy_speed_matrix.json")
    body = []
    for r in acc.get("rows", []):
        e = r.get("error")
        es = (f"${100 * e:+.3g}$\\,\\%" if isinstance(e, (int, float)) else
              verif_clean(e) if e else "--")
        refn = r.get("reference_tool")
        refs = "--" if refn in (None, "none", "none available") else verif_clean(
            refn.replace("Ansys Electronics Desktop 2026 R1", "AEDT").replace(
                "Ansys Icepak 2026 R1", "Icepak"))
        model = verif_clean(r.get("production_model") or "")
        lab = VERIF_LABEL.get(r["stage"], tex(r["stage"].replace("_", " ")))
        body.append(f"{lab}; {model} & {refs} & {es} & {verif_establishes(r)} & "
                    f"{verif_clean(r.get('limitations') or '--')} \\\\")
    note = (r"Check: the quantity and the production model it tests. Error: production against "
            r"reference, relative (thermal unit cells: of the reference temperature rise). AEDT: "
            r"Ansys Electronics Desktop 2026~R1; Icepak: Ansys Icepak 2026~R1; MOOSE: heat-transfer "
            r"module of the open-source MOOSE framework. " + prose(acc.get("note", ""))[:1].upper() +
            prose(acc.get("note", ""))[1:] + ".")
    return ltab(r"@{}L{3.3cm}L{2.7cm}L{1.55cm}L{3.9cm}L{5.2cm}@{}", 5,
                [r"Check; production model & Reference & Error & What it establishes & What it "
                 r"does not establish \\"],
                body, "Verification matrix", "tab:supp-verif", note)


UNC_NAME = {"P": "Loss (W)", "T": "Peak temp.\\ (K)", "warp": "Die warpage (\\textmu m)",
            "du": "$\\du$ (\\textmu m)", "eps": "$\\deps$ ($10^{-3}$/cycle)"}


def uncertainty_table():
    u = J(TR / "uncertainty.json")
    if not u:
        return placeholder("uncertainty", "uncertainty.json")
    U, rel = u.get("U", {}), u.get("relative", {})
    # the input state of the compared cases (tcpmt_uncertainty: the production state writes
    # uncertainty.json); a file without the field predates it -- S0 when it holds local responses
    st = u.get("state") or ("S0" if any(k.endswith(".eps") for k in U) else "SDEC")
    st_lab = {"SDEC": "implemented decoupling", "S0": "S0"}.get(st, st)
    body = []
    for y in ("P", "T", "warp", "du", "eps"):
        if body:
            body.append(r"\midrule")
        for a in ARCHS:
            c = rel.get(a, {}).get(y)
            comp = (" & ".join(f"{100 * c[k]:.2f}" for k in ("mesh", "tt", "et", "ref", "total"))
                    if c else r"\multicolumn{5}{c}{mesh, time, cycle and card grid}")
            ua = [U.get(f"{t}.{a}.{y}") for t in ("A", "B")]
            us = " & ".join("--" if x is None else (f"{x:.2f}" if x < 10 else f"{x:.1f}")
                            for x in ua)
            body.append(f"{UNC_NAME[y] if a == 'Z1' else ''} & {a} & {comp} & {us} \\\\")
    code = {"resolved": "R", "resolved with correlation credit": "Rc", "not resolved": "--"}
    seen = {}
    for r in u.get("comparisons", []):
        seen.setdefault((r["tier"], r["a"], r["b"]), []).append(r)
    comps = [rf"cooling~{t}, {a}/{b}: " +
             "; ".join(f"{UNC_NAME[r['output']].split(' (')[0]} {r['lower']} "
                       f"{code[r['verdict']]}" for r in rows)
             for (t, a, b), rows in seen.items()]
    head = [r"Output & Int. & \multicolumn{5}{c}{Relative components (\%)} & "
            r"\multicolumn{2}{c}{$\pm U$} \\",
            r"\cmidrule(lr){3-7}\cmidrule(l){8-9}",
            r" & & mesh & through-thickness & E--T stop & reference & total & cooling A & "
            r"cooling B \\"]
    note = (r"$U = U_{\mathrm{mesh}} + U_{\mathrm{tt}} + U_{\mathrm{ET}} + U_{\mathrm{ref}}$ "
            r"(linear sum, no credit for independence): extrapolation of the production ladder "
            r"r21$\to$r31 at the lowest order observed in the independent full-package ladders "
            r"(0.6), the through-thickness split, the E--T stop and the matched-reference "
            r"agreement of the solver; relative to the value (temperatures: to the rise above the "
            r"inlet); $\deps$: stabilized L0 response" +
            ("" if st == "S0" else r" (solved on the S0 cases; not compared in this state)") +
            r". Model-form uncertainty is not part of $U$: "
            r"it is covered by rerunning both integrations under each declared alternative "
            r"(Table~\ref{tab:supp-variants}). Comparisons, lower integration first (R: gap "
            r"$>2(U_a+U_b)$; Rc: resolved only with the paired discretization errors of one mesh "
            r"family; --: not resolved): " + ". ".join(c[:1].upper() + c[1:] for c in comps)
            + ".")
    return ltab(r"@{}llrrrrrrr@{}", 9, head, body,
                f"Numerical uncertainty of each compared output ({st_lab}, production mesh)",
                "tab:supp-unc", note)


# ---------------------------------------------------------------- S-VII feasibility, scenarios
CHECK_LABEL = {"gan_Tj": r"GaN $T_J$", "gan_Tj_hs": r"GaN $T_J$ (HS)",
               "gan_Tj_ls": r"GaN $T_J$ (LS)", "ron_fit": r"$R_{DS(on)}$ fit range",
               "mlcc": "capacitors", "inductor": "inductor", "solder_cal": "solder calibration",
               "solder_law": "solder law", "solder_solidus": "solder solidus",
               "buildup": r"build-up $T_g$", "encapsulant": r"encapsulant $T_g$",
               "board": r"board $T_g$", "die": "processor die", "bga_current": "ball current",
               "bga_sites": "ball sites", "ir_drop": "static drop",
               "operating_point": "operating point"}
VARIANT_SHORT = {"z3_top_only": "top plate only", "z1_bottom_plate_tim": "plate under board",
                 "z2_cooled_tim": "backside plate", "z3_plate_tim": "converter plate"}


def case_state(c):
    """Input state of a case record ('SDEC', 'S0', ...): its own field, else its file name."""
    st = c.get("state")
    if st:
        return st[3:] if str(st).startswith("HV_") else st
    m = re.search(r"HV_(SDEC|S\d)", c.get("case") or c.get("file") or "")
    return m.group(1) if m else None


def case_label(c):
    """Readable label of a compared case from its feasibility record: integration, cooling and
    the input state when it is not S0 (SDEC: the implemented decoupling, the production state)."""
    case_file = c.get("case") or ""
    t = {"A": "A", "B": "B", "I": "I"}.get(c.get("tier"), "A")
    s = f"{c.get('arch', '?')}, {t}"
    st = case_state(c)
    if st and st != "S0":
        s += ", " + tex(st)
    var = re.search(r"__(\w+)\.json$", case_file)
    if var and var.group(1) in VARIANT_SHORT and t == "A":
        s += f" ({VARIANT_SHORT[var.group(1)]})"
    return s


def feas_labels(f=None):
    """key -> (label, critical-joint temperature, marked) of the feasibility cases."""
    f = f or J(TR / "feasibility.json") or {"cases": {}}
    out = {}
    for key, c in f["cases"].items():
        d = z3_dag(c.get("arch"), c.get("case"))
        out[key] = (case_label(c) + d, (c.get("joints") or {}).get("T_critical_C"), bool(d))
    return out


def joint_label(key, t_joint, fl):
    """Label of a solder-study joint (key tier_arch): the feasibility case of that cooling and
    integration, in any input state, whose critical joint it is."""
    for k, (lab, tc, mark) in fl.items():
        if (k == key or k.endswith("_" + key)) and tc is not None and abs(tc - t_joint) < 1e-6:
            return lab, mark
    return JOINT_CASE.get(key, tex(key)), False


def record_label(r):
    """Readable label of any case or variant of the feasibility stage."""
    st = case_state(r)
    var = r.get("variant") or ("production case" if "__" not in (r.get("case") or "") else
                               (r.get("case") or "").split("__", 1)[1].rsplit(".", 1)[0])
    tag = r", superseded (uncoupled Z3)" if r.get("role") == "superseded" else ""
    return f"{tex(r.get('arch', '?'))}, {tex(st or '--')}: {tex(var)}{tag}"


def feasibility_table():
    """The feasibility stage (tcpmt_feasibility): every declared limit on every compared case
    of every input state (tcpmt_cases), and the verdict of every case and variant."""
    f = J(TR / "feasibility.json")
    if not f or "records" not in f:
        return placeholder("feasibility stage", "feasibility.json")
    lim = f["limits"]
    labels = feas_labels(f)

    def v(x, d=1):
        return "--" if x is None else f"{x:.{d}f}"
    order = {"SDEC": 0, "S0": 1, "S1": 2}
    keys = sorted(f["cases"], key=lambda k: (order.get(case_state(f["cases"][k]), 9),
                                             f["cases"][k].get("tier") or "",
                                             f["cases"][k].get("arch") or ""))
    body = []
    for key in keys:
        c = f["cases"][key]
        rg, ch, tj = c.get("regions") or {}, c.get("checks") or {}, c.get("junction_C") or {}
        fails = [CHECK_LABEL.get(k, tex(k)) for k in c.get("fails") or []]
        fails += [CHECK_LABEL.get(k, tex(k)) + " (unresolved)" for k in c.get("unresolved") or []]
        body.append(f"{labels[key][0]} & {v(tj.get('hs'))} & {v(tj.get('ls'))} & "
                    f"{v(rg.get('caps_in_cells'))} & {v(rg.get('ind_in_cells'))} & "
                    f"{v(rg.get('rdl_all'))} & {v(rg.get('encapsulant'))} & "
                    f"{v(c.get('die_T_max_C'))} & {v((c.get('joints') or {}).get('T_hottest_C'))} & "
                    f"{v((ch.get('ir_drop') or {}).get('value'))} & "
                    f"{', '.join(fails) or 'none'} \\\\")
    recs = f.get("records") or []
    if recs:
        body += [r"\midrule",
                 r"\multicolumn{11}{@{}l}{\emph{Every case and variant of the study (a candidate "
                 r"that fails any limit is not ranked)}} \\"]
        for r in recs:
            fl = ([CHECK_LABEL.get(k, tex(k)) for k in r.get("fails") or []]
                  + [CHECK_LABEL.get(k, tex(k)) + " (unresolved)"
                     for k in r.get("unresolved") or []])
            body.append(rf"\multicolumn{{6}}{{@{{}}L{{7.0cm}}}}{{{record_label(r)}}} & "
                        rf"\multicolumn{{2}}{{l}}{{{tex(r.get('verdict', '--'))}}} & "
                        rf"\multicolumn{{3}}{{L{{4.8cm}}}}{{{', '.join(fl) or '--'}}} \\")
    head = [r"Case & \multicolumn{2}{c}{GaN $T_J$} & Capacitors & Inductor & RDL & "
            r"Encapsulant & Die & Joint & Drop & Limits exceeded \\", r"\cmidrule(lr){2-3}",
            r" & HS & LS & & & & & & & (mV) & \\"]
    note = (r"Maximum temperatures ($^\circ$C) of the converged fields; GaN junction per device "
            r"tier: the tier maximum in the cells plus $R_{\theta\mathrm{JC}}$ at the device's own "
            r"dissipation; joint: the hottest joint of the all-site search; drop: per-rail maximum "
            r"static drop of the 1-V path. Limits: GaN $T_J\le" + f"{lim['gan_Tj_C']:.0f}" +
            r"$; $R_{DS(on)}$ temperature fit $\le" + f"{lim['ron_fit_max_C']:.0f}" +
            r"$; X7R/X7S capacitors $\le" + f"{lim['mlcc_C']:.0f}" + r"$; inductor $\le" +
            f"{lim['inductor_C']:.0f}" + r"$; build-up dielectric and encapsulant $T_g\approx" +
            f"{lim['buildup_Tg_C']:.0f}" + r"$; board $T_g\approx" + f"{lim['board_Tg_C']:.0f}" +
            r"$; processor die $\le" + f"{lim['die_C']:.0f}" +
            r"$; solder law calibrated $\le" + f"{lim['solder_cal_C']:.0f}" +
            r"$, solidus " + f"{lim.get('solder_solidus_C', 217):.0f}" +
            r"; every power ball $\le" + f"{lim['bga_A_per_ball']:.1f}" + r"$~A at the case's "
            r"waveform, with at least " + f"{100 * (1 - lim['bga_power_site_fraction_max']):.0f}" +
            r"\,\% of the ball sites left for signals; static drop $\le" +
            f"{lim['ir_drop_mV_per_rail']:.0f}" + r"$~mV per rail. Cases: integration, cooling "
            r"(A: top plate; B: top plate and bottom plate, the bottom one behind a 50-\textmu m "
            r"TIM) and input state when not S0 (SDEC: the implemented decoupling, the production "
            r"state; S1: no decoupling). A check that fails only on the whole-field bound is "
            r"unresolved; such a candidate is not ranked either." +
            (DAGGER_NOTE if any(v_[2] for v_ in labels.values()) else ""))
    return ltab(r"@{}L{3.0cm}rrrrrrrrrL{3.4cm}@{}", 11, head, body,
                "Feasibility stage: every limit on every case", "tab:supp-feas", note)


def scenario_table():
    """The selected regulator under every input state, cooling A: the production state
    (implemented decoupling) and the S0/S1 references from tcpmt_cases (Z3 on its coupled land
    side), S2 for the Z1/Z2 production-boundary cases; a case not run yet is a row of dashes."""
    import tcpmt_cases as TC
    dec = J(TR / "input_decoupling.json") or {}
    k_eq = ((dec.get("summary") or {}).get("recommended") or {}).get("k_eq")
    kmap = {"SDEC": "--" if k_eq is None else f"{k_eq:.2f}", "S0": "1", "S1": "4",
            "S2": f"{math.sqrt(48):.2f}"}
    body, marked = [], False
    for a in ARCHS:
        for s in ("SDEC", "S0", "S1", "S2"):
            if s == "S2":
                pth = FC / f"etm_{a}_HV_S2_h1.1_r21.json"
                pth = None if (a == "Z3" or not pth.is_file()) else pth
            else:
                pth = TC.case_path(s, "A", a)
            c = J(pth) if pth else None
            if not c:
                body.append(f"{a} & {s} & -- & -- & -- & -- & -- & {kmap[s]} \\\\")
                continue
            me = c.get("mechanics") or {}
            cr = (me.get("joint_search") or {}).get("critical") or {}
            h = c["et_history"][-1]
            du = f"{cr['du_um']:.2f} at {cr['T_C']:.0f}" if cr else "--"
            warp = f"{me['die_warpage_pv_um']:.1f}" if me else "--"
            marked |= bool(z3_dag(a, pth.name))
            body.append(f"{a}{z3_dag(a, pth.name)} & {s} & "
                        f"{c['P_loss_w']:.1f} & {c['thermal']['T_max_C']:.1f} & "
                        f"{h.get('T_ls_C', float('nan')):.1f} & {du} & {warp} & {kmap[s]} \\\\")
    head = [r"Integration & State & $P$ (W) & $T_{\max}$ & $T_{\mathrm{LS}}$ & "
            r"$\du$ (\textmu m) & Warpage & $k$ \\",
            r" & & & ($^\circ$C) & ($^\circ$C) & at $T_{\mathrm{j}}$ ($^\circ$C) & (\textmu m) & \\"]
    note = (r"Package-internal loss, peak and low-side tier temperature, critical joint and die "
            r"warpage under cooling~A (Z3: the coupled land-side case) per input state: SDEC, the "
            r"implemented decoupling (the production state); S0, ideal input smoothing; S1, no "
            r"decoupling; S2, the BGA/direct-fed scenario of the production-boundary cases. "
            r"$k$: RMS-to-average ratio of the current the 48-V feed carries; --: not run yet."
            + (DAGGER_NOTE if marked else ""))
    return ltab(r"@{}llrrrrrr@{}", 8, head, body,
                "The selected regulator under the input states", "tab:supp-scen", note)


# ---------------------------------------------------------------- S-VIII comparison
def z3_run_label(run):
    m = re.match(r"z3_land_t(\d+)_([AB])(.*)$", run)
    if not m:
        return tex(run)
    t, tier, rest = m.groups()
    s = f"{t}~\\textmu m, {tier}"
    if "noplane" in rest:
        s += ", no board planes"
    if "fvmap" in rest:
        s += ", FV map"
    return s


def z3land_table():
    d = J(TR / "z3_land_coupled.json")
    if not d:
        return placeholder("Z3 redistribution", "z3_land_coupled.json")
    body = []
    for r in d["table"]:
        body.append(f"{z3_run_label(r['run'])} & {num(r['P_loss_w'], 4)} & "
                    f"{num(r.get('P_land_w'), 3)} & {num(r.get('P_board_plane_w'), 3)} & "
                    f"{num(r.get('dV_land_static_one_rail_mV'), 3)} & {num(r.get('T_max_C'), 4)} & "
                    f"{num(r.get('die_warpage_pv_um'), 3)} & {num(r.get('du_c_um'), 3)} & "
                    f"{num(r.get('R_star_mohm'), 3)} \\\\")
    dv = d["derived"]
    head = [r"Land side, cooling & $P$ & Land & Planes & $\Delta V_{\mathrm{land}}$ & "
            r"$T_{\max}$ & Warpage & $\du$ & $R^*$ \\",
            r" & (W) & (W) & (W) & (mV) & ($^\circ$C) & (\textmu m) & (\textmu m) & (m$\Omega$) \\"]
    note = (r"Land-side copper thickness $t$ and cooling; board planes $2\times35$~\textmu m per "
            r"rail at 80\,\% occupancy, equal ball sharing, S0. $\Delta V_{\mathrm{land}}$: static "
            r"land-side drop of one rail; $R^*$: feed limit. Tie with Z1 under cooling~B at "
            f"$t = {dv['tie_with_board_planes']['t_um']:.0f}$~\\textmu m (land side alone: "
            f"{dv['tie_land_only']['t_um']:.0f}~\\textmu m); a land-side drop of at most 30~mV "
            f"per rail needs $t \\ge {dv['drop_30mV_one_rail']['t_um']:.0f}$~\\textmu m.")
    return ltab(r"@{}lrrrrrrrr@{}", 9, head, body,
                "Board-backside integration with the land-side and board-plane redistribution "
                "coupled", "tab:supp-z3land", note)


# ---------------------------------------------------------------- S-IX exploration
def caprule_screen_table():
    d = J(TR / "dse_caprule.json")
    if not d:
        return placeholder("capacitor-rule screen", "dse_caprule.json")
    body = []
    for r in d["per_count"]:
        def c(t):
            x = r.get(t)
            if not x:
                return "--"
            nk = x["arch"].replace("N=", "").replace(",K=", "/").split(",")[0]
            return f"{x['P_total_W']:.1f} ({nk})"
        body.append(f"{r['M']} & {c('etm35')} & {c('etm35_caprule')} & "
                    f"{c('etm35_caprule_ripple')} & {c('etm35_caprule_full')} \\\\")
    concl = prose(d["conclusion"])
    concl = concl[0].upper() + concl[1:]
    note = (r"Total loss (W) and the selected member $N/K$ at each count $M$; --: no feasible "
            r"member. Steps: the published rule; with the voltage rule (every flying capacitor "
            r"rated with 0.8 derating for the $(N-1)V_{\mathrm{in}}/N$ that $C_1$ holds, rated "
            r"parts admitted); with the effective-capacitance ripple check (parts without vendor "
            r"bias data excluded); with the ESR at the switching frequency. The legacy "
            r"configuration of the corrected engine reproduces the published screen: "
            + ("yes" if d.get("legacy_reproduces_published") else "no") + ". " +
            re.sub(r"M = (\d+)", r"$M = \1$", concl) + ".")
    return ltab(r"@{}rllll@{}", 5,
                [r"$M$ & Published & + voltage rule & + effective $C$ & + ESR($f$) \\"],
                body, "Regulator-count screen before and after the capacitor-rule correction",
                "tab:supp-caprule", note)


VARIANT_LABEL = {
    "board_t3p2": "PCB 3.2 mm thick", "board_eta025": "PCB copper coverage 25\\,\\%",
    "board_eta075": "PCB copper coverage 75\\,\\%", "board_h1": "PCB as five-block laminate",
    "board_h0_h1grid": "PCB single block, five-block grid",
    "tsv_min": "TSV field minimal", "tsv_mid": "TSV field half density",
    "f2_void": "Out-of-cell volume void", "f1_sidewall_filled": "Opening filled to the sidewall",
    "attach_h20": "Attach 20~\\textmu m tall", "attach_h40": "Attach 40~\\textmu m tall",
    "attach_sn": "Attach all-solder", "attach_dense": "Attach dense, real lattice",
    "attach_sparse": "Attach sparse", "attach_sparse_stiff": "Attach sparse, column-stiffened",
    "attach_eng_p34": "Attach at 34-\\textmu m pitch",
    "attach_eng_p37": "Attach at 37-\\textmu m pitch",
    "attach_eng_p41": "Attach at 41-\\textmu m pitch",
    "attach_stiff": "Attach card column-stiffened", "attach_uf_soft": "Attach underfill soft",
    "attach_uf_stiff": "Attach underfill stiff",
    "feed_heat_at_crossover": "Feed loss in the package",
    "icepak_equivalent": "Cold-plate $h$ from CFD", "z2_cooled_tim": "Z2 bottom plate via TIM",
    "bga_depop": "BGA depopulated", "z1_bottom_plate_tim": "Z1 bottom plate via TIM",
    "z3_plate_tim": "Z3 bottom plate via TIM", "z3_top_only": "Z3 top plate only",
    "z1_tier_reference": "Z1 reference tier order",
    "board_hbot100": "Board-bottom film 100", "board_hbot500": "Board-bottom film 500",
    "z2_cooled": "Z2 bottom plate, no TIM", "pad_drop": "1-V pads at the drop floor",
    "gan_k_half": "GaN-tier $k\\times0.5$", "conv_k_tenth": "Converter-tier $k\\times0.1$"}


def variant_label(name):
    if name in VARIANT_LABEL:
        return VARIANT_LABEL[name]
    m = re.match(r"conv_E(\d+)_a(\d+)$", name)
    if m:
        return f"Converter $E$ {m.group(1)}~GPa, CTE {m.group(2)}"
    return tex(name)


def variants_table():
    import final_closure_sensitivity as S
    body = []
    for name, v in S.VARIANTS.items():
        what = re.sub(r"\bmaterial dict\b", "material card", v["what"])
        what = what.replace("Z2-COOLED plate", "a bottom plate under the Z2 converter")
        body.append(f"{variant_label(name)} & {'mech.' if v['kind'] == 'mech' else 'full'} & "
                    f"{'/'.join(v['archs'])} & {prose(what)} \\\\")
    note = (r"Each run changes one declared input on the production mesh and reruns the whole "
            r"electrothermal--mechanical chain (full) or only the mechanics on the converged "
            r"field (mech.). The bottom-plate variants of Z1, Z2 and Z3 define cooling~B and the "
            r"top-plate-only variant of Z3 defines its cooling~A; the Z3 cases of the paper add the "
            r"coupled land-side and board-plane redistribution (Table~\ref{tab:supp-z3land}).")
    return ltab(r"@{}L{4.3cm}lL{1.0cm}L{10.7cm}@{}", 4,
                [r"Variant & Rerun & Int. & What changes \\"], body,
                "Package decisions varied in the robustness study", "tab:supp-variants", note)


OMIT_CASE = {"A_Z1": "Z1, A", "A_Z2": "Z2, A", "A_Z3_toponly": "Z3, A (top plate only)",
             "A_Z3_secondplate": "Z3, I", "B_Z1": "Z1, B", "B_Z2": "Z2, B", "B_Z3": "Z3, B"}


def omitted_losses_table():
    d = J(TR / "omitted_losses.json")
    if not d:
        return placeholder("omitted converter losses", "omitted_losses.json")

    def cell(o, k):
        lo, nom, hi = (o.get(b, {}).get(k) for b in ("low", "nominal", "high"))
        if nom is None:
            return "--"
        dd = 2 if max(abs(lo or 0), abs(nom), abs(hi or 0)) < 1 else 1
        return f"{nom:.{dd}f} ({lo:.{dd}f}--{hi:.{dd}f})"
    body = []
    for k, c in d.get("cases", {}).items():
        o = c.get("omitted", {})
        dg = z3_dag(c.get("arch"), c.get("file"))
        body.append(f"{OMIT_CASE.get(k, tex(k))}{dg} & {fx(c.get('T_ls_C'))} & "
                    f"{fx(c.get('P_package_w'))} & " +
                    " & ".join(cell(o, t) for t in ("dead_time_w", "core_w", "ac_winding_w",
                                                     "dielectric_w", "total_w")) + r" \\")
    b = d.get("assumptions", {}).get("bundles", {})
    tdt = [b.get(x, {}).get("t_dt") for x in ("low", "nominal", "high")]
    note = (r"Converter loss terms the synthesis loss model omits, in W for the package, at each "
            r"case's own tier temperatures: nominal (low--high bundle). Dead time: EPC2057 "
            r"reverse conduction from its datasheet over a dead time of "
            + (f"{tdt[1]:g}~ns ({tdt[0]:g}--{tdt[2]:g}~ns)" if all(tdt) else "2--10~ns") +
            r"; core: the loss line of the inductor's metal-composite material"
            r"~\cite{Rasheedi2026CoupledInductor}; AC winding: the winding's AC-resistance ratio "
            r"applied to its DC resistance; dielectric: an X7R dissipation factor over the "
            r"harmonics of the flying-capacitor current. $T_{\mathrm{LS}}$: low-side tier "
            r"temperature; $P$: package loss of the case. Cases as in Table~\ref{tab:supp-feas}."
            + (DAGGER_NOTE if any(z3_dag(c.get("arch"), c.get("file"))
                                  for c in d.get("cases", {}).values()) else ""))
    head = [r"Case & $T_{\mathrm{LS}}$ & $P$ & Dead time & Core & AC winding & Dielectric & "
            r"Total \\", r" & ($^\circ$C) & (W) & & & & & \\"]
    return ltab(r"@{}lrrrrrrr@{}", 8, head, body,
                "Omitted converter losses per integration and cooling", "tab:supp-omit", note)


REVIEW_KEYS = ("tim_warp_fb", "die_hotspot", "plate_local_h", "sdec", "z1_rated",
               "z1_input_decoupling", "z3_land")


def review_label(name):
    """Readable label and cooling tier of a review-round run from its name."""
    fv = name.endswith("_fvmap")
    if fv:
        name = name[:-len("_fvmap")]
    nop = name.endswith("_noplane")
    if nop:
        name = name[:-len("_noplane")]
    tier = ""
    m = re.match(r"(.*)_([AB])$", name)
    if m:
        name, tier = m.groups()
    lab = {"tim_warp_fb": "Interface warpage feedback", "die_hotspot": "Die hot-spot power map",
           "plate_local_h": "Local cold-plate coefficient",
           "sdec": "Implemented input decoupling",
           "z1_input_decoupling": "Implemented input decoupling, ring-capacitor ESR"}.get(name)
    if lab is None:
        r = re.match(r"z1_rated_(cfmax|cf)_(ref|rep)$", name)
        z = re.match(r"z3_land_t(\d+)$", name)
        if r:
            lab = (f"Rated $C_f$ ({'1030' if r.group(1) == 'cfmax' else '830'}~\\textmu m), "
                   f"{'reference' if r.group(2) == 'ref' else 'repartitioned'} order")
        elif z:
            lab = f"Land side {z.group(1)}~\\textmu m"
        else:
            lab = tex(name)
    if nop:
        lab += ", no board planes"
    if fv:
        lab += ", FV map"
    return lab, tier


def review_variants_table():
    import tcpmt_cases as TC
    SENS = FC / "sensitivity"
    body = []
    k_eq = k_op = None
    for f in sorted(SENS.glob("etm_*__*.json")):
        name = f.stem.split("__")[1]
        if not any(k in name for k in REVIEW_KEYS):
            continue
        c = J(f)
        me = c.get("mechanics") or {}
        cr = (me.get("joint_search") or {}).get("critical") or {}
        lab, tier = review_label(name)
        if TC.is_superseded(f):
            lab += " (superseded base)"
        arch = f.stem.split("_")[1]
        if not tier and arch in ("Z1", "Z2") and \
                str(c.get("production_case", "")).endswith("_h1.1_r21.json"):
            tier = "A"                       # on the production case: the production cooling
        kk = (c.get("variant") or {}).get("what", "")
        k_eq = k_eq or grab(r"k_eq = ([\d.]+)", kk)
        k_op = k_op or grab(r"k_open = ([\d.]+)", kk)
        body.append(f"{arch}{z3_dag(arch, f.name)} & {lab} & {tier or '--'} & "
                    f"{num(c.get('P_loss_w'), 4)} & {num(c['thermal']['T_max_C'], 4)} & "
                    f"{num(me.get('die_warpage_pv_um'), 3)} & {num(cr.get('du_um'), 3)} & "
                    f"{num(cr.get('T_C'), 4)} \\\\")
    head = [r"Int. & Variant & Cooling & $P$ (W) & $T_{\max}$ ($^\circ$C) & Warpage "
            r"(\textmu m) & $\du$ (\textmu m) & $T_{\mathrm{j}}$ ($^\circ$C) \\"]
    note = (r"Production mesh, S0 unless the input decoupling is implemented. Interface feedback: "
            r"TIM thickness following the die warpage; die hot-spot map: three quarters of the "
            r"die power in its central half; local cold-plate coefficient: caloric resistance "
            r"removed from the top-plate coefficient; rated $C_f$: rated MLCC flying capacitors "
            r"(capacitor tier 830 or 1030~\textmu m) in the reference or repartitioned tier order; "
            r"implemented input decoupling (scenario SDEC): the package 48-V network and the "
            r"cell-internal input runs carry the RMS-to-average current ratios of the implemented "
            r"decoupling" + (rf" ({k_eq} and {k_op}, respectively)" if k_eq and k_op else "") +
            r", for Z1 under cooling~A also with the ring capacitors' ESR loss in the ledger; "
            r"land side: Z3 with the land-side and board-plane redistribution coupled "
            r"(Table~\ref{tab:supp-z3land}); FV map: redistribution heat deposited along its "
            r"finite-volume loss map instead of uniformly." + DAGGER_NOTE)
    return ltab(r"@{}lL{6.2cm}lrrrrr@{}", 8, head, body, "Review-round variants",
                "tab:supp-review", note)


# ---------------------------------------------------------------- assembly
def main():
    B = build_all()
    L = ["% GENERATED by scripts/tcpmt_supplement.py -- do not edit"]
    L += prior_section()
    L += section("Converter Synthesis and Design-Space Exploration",
                 r"Table~\ref{tab:supp-dse} lists the converter that the synthesis selects at "
                 r"every regulator count of the screen.")
    L += dse_selection_table()
    L += section("Integration Architectures and Physical Models",
                 r"Tables~\ref{tab:supp-materials}--\ref{tab:supp-heat} give the material cards, "
                 r"the meshed layer stacks of the three integrations and the cooling.")
    L += materials_table(B) + stack_tables(B) + cooling_tables()
    L += capacitor_tables()
    L += solder_tables()
    L += section("Verification, Uncertainty and Cost",
                 r"Tables~\ref{tab:supp-mesh}--\ref{tab:supp-unc} give the production meshes, "
                 r"solver settings and runtimes, every verification check with what it does and "
                 r"does not establish, and the numerical uncertainty of each compared output.")
    L += mesh_runtime_table() + verification_table() + uncertainty_table()
    L += section("Evaluating a Design",
                 r"Table~\ref{tab:supp-feas} lists every limit, case and variant of the "
                 r"feasibility stage and Table~\ref{tab:supp-scen} the selected regulator under "
                 r"the input states.")
    L += feasibility_table() + scenario_table()
    L += section("Comparing Integrations",
                 r"Table~\ref{tab:supp-z3land} gives the board-backside integration with its "
                 r"1-V redistribution in the coupled solution.")
    L += z3land_table()
    L += section("Exploring the Design Space",
                 r"Table~\ref{tab:supp-caprule} gives the regulator-count screen before and "
                 r"after the capacitor-rule correction, Table~\ref{tab:supp-variants} the package "
                 r"decisions of the robustness study, Table~\ref{tab:supp-omit} the omitted "
                 r"converter losses and Table~\ref{tab:supp-review} the variants added in the "
                 r"review round.")
    L += caprule_screen_table() + variants_table() + omitted_losses_table()
    L += review_variants_table()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
