"""Supplementary material: every parameter, mesh, boundary, solver setting, runtime and
variant behind the paper, generated from the objects the solvers use (TCPMT review MC15).

Writes manuscript_v2/supplement/supp_tables.tex, which the supplement's main file includes:
the section headings (in the order of the paper), every table as a captioned longtable and the
notes beneath it. LaTeX numbers the tables S1, S2, ... in reading order and every cross-reference
goes through a label, so adding or removing a table renumbers consistently. Tables whose inputs
are missing are emitted as a marked placeholder, so the supplement always compiles.

Inputs are read, never written. Internal identifiers (run, layer, card and case keys) are mapped
to readable labels here; an identifier without a mapping is printed as it is.

TCPMT round 3: the regulator count, converter, parts and mixed tiers come from the design record
(configs/design_points.yaml, HVR_DESIGN), the compared cases from tcpmt_cases (production state
SDEC, Z3 always the coupled land-side case), every result from the root in force
($ETM_RESULTS_ROOT for a campaign); nothing falls back on the frozen research/ tree.

    python tcpmt_supplement.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
sys.path.insert(0, str(R / "scripts" / "phase0nw"))
import design_record as DR                                          # noqa: E402
import tcpmt_cases as TC                                            # noqa: E402

FC = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
DSE_DATA = TR / "dse_j35" / "data"
#: generated supplement files (this script's output, tcpmt_capacitor_evidence's table) go under
#: $ETM_RESULTS_ROOT for a campaign (hook); hand-written inputs stay in the frozen tree
SUPP = Path(os.environ.get("ETM_RESULTS_ROOT") or R) / "manuscript_v2" / "supplement"
SUPP_SRC = R / "manuscript_v2" / "supplement"
OUT = SUPP / "supp_tables.tex"
ARCHS = ("Z1", "Z2", "Z3")
NAMES = {"Z1": "embedded", "Z2": "package-backside", "Z3": "board-backside"}
STATE_TEXT = {"SDEC": "implemented decoupling", "S0": "ideal input smoothing",
              "S1": "no decoupling", "S2": "square pulse at the overall ratio"}


def J(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else None


_REC: dict = {}


def case_record(case_file):
    """The record of a case named in a result file (a bare name, a checkout-relative or an
    absolute path), looked up BY NAME in the root in force (final_closure, its sensitivity/ and
    ladder/ folders) -- never in the frozen tree; None when the root does not hold it."""
    if not case_file:
        return None
    nm = Path(str(case_file)).name
    if nm not in _REC:
        _REC[nm] = next((J(d / nm) for d in (FC, FC / "sensitivity", FC / "sensitivity" / "ladder")
                         if (d / nm).is_file()), None)
    return _REC[nm]


# ---------------------------------------------------------------- the design in force
CLASS_NOUN = {"gan_hs": ("HS GaN", "HS GaN"), "gan_ls": ("LS GaN", "LS GaN"),
              "inductor": ("inductor", "inductors"), "cap_fly": ("flying capacitor",
                                                                 "flying capacitors")}


def tier_contents(parts):
    """'2 HS GaN, 2 flying capacitors' from a tier's {class: n} (design record)."""
    out = []
    for c in DR.CLASSES:
        n = int((parts or {}).get(c) or 0)
        if n:
            out.append(f"{n} {CLASS_NOUN[c][n != 1]}")
    return ", ".join(out)


def tier_by_index(i):
    """The design record's tier i (1 = the converter's input end), or None."""
    t = DR.tiers()
    return t[i - 1] if 1 <= i <= len(t) and t[i - 1]["name"].startswith(f"tier{i}_") else None


def design_sentence(key=None, lib=None):
    """'M = 36 (6 x 6 cells), N3K3K_A2, EPC2014C / EPC2055, 805 kHz, flying capacitor ...'."""
    d = DR.get(key)
    N, K, KA = DR.topology(key)
    g = DR.grid_n(key)
    cap = passive_label(d["capacitor"], lib if lib is not None else passive_library(), maker=True)
    return (rf"$M = {DR.n_vr(key)}$ ({g}$\times${g} cells), N{N}K{K} ($K_A = {KA}$), "
            rf"{tex(d['hs_part'])} / {tex(d['ls_part'])}, {float(d['f_sw_hz']) / 1e3:.0f}~kHz, "
            rf"flying capacitor {cap}, {len(DR.tiers(key))} mixed tiers")


def thin_design():
    """(key, capacitor height um) of the thin-capacitor sensitivity design of the record: the
    sensitivity entry whose flying-capacitor height is below the production one; else None."""
    h0 = float(DR.get().get("cap_height_um") or 0.0)
    for k in DR.keys():
        e = DR.get(k)
        h = e.get("cap_height_um")
        if e.get("role") == "sensitivity" and h is not None and float(h) < h0:
            return k, float(h)
    return None


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
     lambda m: f"N{m.group(1)}K{m.group(2)} ($K_A = {m.group(3)}$)"),
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


_SUPERSEDED_NAMES = {Path(k).name for k in TC.SUPERSEDED}


def z3_dag(arch, case_file, rec=None):
    """Marks a Z3 result WITHOUT the coupled land-side redistribution. Decided by the case
    record (tcpmt_cases.is_coupled_z3: the production-state Z3 cases carry it although their
    file name does not say z3_land); a record the root does not hold is marked only when its
    name is one of the superseded uncoupled cases."""
    if arch != "Z3":
        return ""
    rec = rec if rec is not None else case_record(case_file)
    if rec is not None:
        return "" if TC.is_coupled_z3(rec) else r"$^\dagger$"
    return r"$^\dagger$" if Path(str(case_file or "")).name in _SUPERSEDED_NAMES else ""


# ---------------------------------------------------------------- S-I prior work
def prior_section():
    L = section("Comparison with Prior Work",
                r"Table~\ref{tab:supp-prior} details the capability comparison of the paper's "
                r"introduction. Every entry for another work rests on a passage of the cited "
                r"source; where neither source describes a capability, the entry states so.")
    if not (SUPP_SRC / "tab_prior_detailed.tex").is_file():
        return L + placeholder("prior work", "tab_prior_detailed.tex")
    return L + [r"\input{tab_prior_detailed}", ""]


# ---------------------------------------------------------------- S-II converter screen
@lru_cache(maxsize=1)
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
            re.sub(r"-[\d.]+[un]?F-(?:BV)?[\d.]+V?\d*$", "", name).split("-", 1)[-1]
        pre = name.split("-")[0] + " " if maker and "-" in name else ""
        return f"{tex(pre + part)} ({p.c_uf:g}~\\textmu F, {p.v_max:.0f}~V)"
    return prose(name.replace("_", " "))


def screen_run():
    """The screen run the design record's entry was picked from: its 'screen.source' names
    dse_phase2_summary.json runs.<run>.per_count.<M> (TCPMT round 3: etm35_p2_t4, the
    production converter rules -- corrected capacitor rule, mixed tiers, at most 4 tiers)."""
    src = str((DR.get().get("screen") or {}).get("source") or "")
    m = re.search(r"runs\.([A-Za-z0-9_]+)\.per_count", src)
    return m.group(1) if m else None


def p2_runs():
    """runs{} of the phase-2 screen summary in the root in force ({} when absent)."""
    return (J(TR / "dse_phase2_summary.json") or {}).get("runs") or {}


def max_tiers(tag):
    """Tier limit of a screen run: its phase-2 summary entry, else its tag (_t4 -> 4,
    _tinf -> None); 'unknown' when neither says."""
    run = p2_runs().get(tag) or {}
    if "max_tiers" in run:
        return run["max_tiers"]
    m = re.search(r"_t(\d+|inf)$", tag or "")
    return (None if m.group(1) == "inf" else int(m.group(1))) if m else "unknown"


def dse_rows(tag):
    """{M: row} of the case-D screen CSV of a run in the root in force; None when absent."""
    f = DSE_DATA / f"case_D_{tag}.csv"
    if not f.is_file():
        return None
    return {int(float(r["M"])): r for r in csv.DictReader(f.open())}


def dse_feasible(r):
    return r is not None and str(r.get("feasible")) in ("True", "true", "1")


def dse_passive(r, key):
    """The selected passive of a screen row ('capacitor' / 'inductor'; the private reruns of
    round 2 wrote 'cap' / 'ind')."""
    return r.get(key) or r.get({"capacitor": "cap", "inductor": "ind"}[key])


def tier_rule(n):
    return ("no tier limit" if n is None else "tier limit unknown" if n == "unknown"
            else f"at most {n} converter tiers")


def dse_selection_table():
    """The converter selected at every count of the screen the design record was picked from
    (the production converter rules), the design's own count marked."""
    tag = next((t for t in (screen_run(), "etm35_caprule_full")
                if t and (DSE_DATA / f"case_D_{t}.csv").is_file()), None)
    if tag is None:
        return placeholder("per-count selection", f"case_D_{screen_run() or 'etm35_p2_t4'}.csv")
    rows = dse_rows(tag)
    meta = J(DSE_DATA / f"meta_{tag}.json") or {}
    lib = passive_library()
    m0 = DR.n_vr()
    # the same screen on the nested 16x finer f_sw grid (scripts/tcpmt_dse_fsw_grid.py)
    fine = J(TR / "dse_fsw_fine.json") or {}
    fc = {int(k): v.get("fine") for k, v in (fine.get("counts") or {}).items()}
    nf = 2 if fc else 0
    body = []
    for m, r in sorted(rows.items()):
        mk = r"$^\ast$" if m == m0 else ""
        if not dse_feasible(r):
            why = prose((r.get("reason") or "no feasible member").replace("architecture", "member"))
            body.append(rf"{m}{mk} & \multicolumn{{{8 + nf}}}{{l}}{{{why}}} \\")
            continue
        top = f"N{int(float(r['N']))}K{int(float(r['K']))}, $K_A = {int(float(r['K_A']))}$"
        f = fc.get(m) or {}
        same = (f.get("topology") == r.get("arch") and f.get("hs") == r.get("hs")
                and f.get("ls") == r.get("ls"))
        ftxt = (f" & {f['f_sw_kHz']:.1f} & {f['total_loss_W']:.2f}" + ("" if same else
                                                                     r"$^\dagger$")
                if f else (" & -- & --" if nf else ""))
        body.append(f"{m}{mk} & {top} & {tex(r['hs'])} / {tex(r['ls'])} & "
                    f"{passive_label(dse_passive(r, 'inductor'), lib)} & "
                    f"{passive_label(dse_passive(r, 'capacitor'), lib)} & "
                    f"{float(r['f_sw_Hz']) / 1e3:.1f} & {float(r['conv_loss_total_W']):.2f} & "
                    f"{float(r['routing_loss_W']):.2f} & {float(r['total_loss_W']):.2f}"
                    + ftxt + r" \\")
    head = [r"$M$ & Topology & HS / LS device & Inductor & Flying capacitor & "
            r"$f_{\mathrm{sw}}$ & \multicolumn{3}{c}{Loss (W)}"
            + (r" & \multicolumn{2}{c}{" + f"{fine.get('n_grid_points')}" + r"-point grid}"
               if nf else "") + r" \\",
            r"\cmidrule(l){7-9}" + (r"\cmidrule(l){10-11}" if nf else ""),
            r" & & & & & (kHz) & Conversion & Routing & Total"
            + (r" & $f_{\mathrm{sw}}$ (kHz) & Total (W)" if nf else "") + r" \\"]
    spec = r"@{}rllllrrrr" + ("rr" if nf else "") + "@{}"
    feas = [(float(r["total_loss_W"]), m) for m, r in rows.items() if dse_feasible(r)]
    best = min(feas)[1] if feas else None
    note = (f"Specification: {meta.get('P_load', 1000) / 1e3:g}~kW at {meta.get('V_out', 1):g}~V "
            f"from {meta.get('V_in', 48):g}~V on a {meta.get('die_area_mm2', 500):g}-mm$^2$ die, "
            f"$J_{{\\mathrm{{t}}}} = {meta.get('J_target', 3.5):g}$~A\\,mm$^{{-2}}$; topology "
            r"re-synthesized at every count with the discrete device library (case~D) under the "
            r"converter rules of the paper (Section~III): each flying capacitor rated with 0.8 "
            r"derating for the voltage it holds, with its effective capacitance and its ESR at "
            r"$f_{\mathrm{sw}}$; every switch at 0.9 of its rating; $C_{\mathrm{oss}}$ charged "
            r"at each node swing; datasheet gate resistance; body footprints placed with a "
            r"50-\textmu m keep-out in tiers that may mix part classes, "
            + tier_rule(max_tiers(tag)) + ". "
            + ((rf"{fine['n_grid_points']}-point grid: the same screen with the "
                rf"{fine['n_grid_points_screen']}-point $f_{{\mathrm{{sw}}}}$ grid of the "
                r"synthesis split 16 times (every original point kept); "
                + (r"no count changes its topology or parts" if not
                   fine.get("n_counts_selection_changed") else
                   r"$^\dagger$: another topology or part") + ". ") if nf else "")
            + (rf"Least total loss at $M = {best}$. " if best is not None else "")
            + rf"$^\ast$: the production design ({design_sentence(lib=lib)}). "
            r"HS/LS: high- and low-side GaN devices; inductor: inductance and DC resistance. "
            r"Losses are for the package of $M$ regulators: conversion from the synthesis loss "
            r"model, routing from the model of~\cite{Krishnakumar2026DVPD} (electrical only).")
    return ltab(spec, 9 + nf, head, body,
                r"Converter selected at each regulator count (production converter rules)",
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


def mat_label(n, short=False):
    """Readable name of a material card; the derived card of a mixed converter tier
    (conv_tier<i>) by the record tier it homogenizes."""
    if n in MAT_LABEL:
        return MAT_LABEL[n]
    m = re.match(r"^conv_tier(\d+)$", n)
    if m:
        t = tier_by_index(int(m.group(1)))
        if short or t is None:
            return f"Converter tier {m.group(1)} card"
        return f"Converter tier {m.group(1)} ({tier_contents(t['parts'])})"
    return tex(n)


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
#: the RDL layers of a converter stack (design_record.converter_tiers)
LAYER_PART = {"bottom_substrate_rdl": "Converter landing RDL (on the substrate)",
              "interlayer_rdl": "Interlayer RDL", "output_rdl": "Converter output RDL",
              "land_side_attach_rdl": "Land-side attach RDL"}


def layer_label(n):
    """Readable name of a mesh layer; a converter layer (<z>conv_<i>_<name>) is an RDL of the
    stack or a tier of the design record, numbered from the converter's input end."""
    if n in LAYER_LABEL:
        return LAYER_LABEL[n]
    m = re.match(r"^(?:z\d)?conv_(\d+)_(.+)$", n)
    if not m:
        return tex(n)
    part = m.group(2)
    if part in LAYER_PART:
        return LAYER_PART[part]
    tp = DR.tier_parts()
    t = re.match(r"^tier(\d+)_", part)
    if t and part in tp:
        i = int(t.group(1))
        end = " (input end)" if i == 1 else " (output end)" if i == len(tp) else ""
        return f"Converter tier {i}{end}: {tier_contents(tp[part])}"
    return "Converter layer " + tex(part.replace("_", " "))


def stack_tables(B):
    import numpy as np
    body = []
    tops = {}
    for a, (m, st, tiles, info) in B.items():
        lay = np.array(m.elem_layer, dtype=object)
        mat = np.array(m.elem_material, dtype=object)
        if body:
            body.append(r"\midrule")
        body.append(rf"\multicolumn{{4}}{{@{{}}l}}{{\emph{{{a} ({NAMES[a]})}}}} \\")
        for ly in m.layers:
            if ly.name == "board":
                tops[a] = round(float(ly.z1), 4)
            mats_ = sorted(set(mat[lay == ly.name]))
            labs = [mat_label(x, short=True) for x in mats_]
            labs = labs[:1] + [lb[0].lower() + lb[1:] if lb[1:2].islower() else lb
                               for lb in labs[1:]]
            body.append(f"{layer_label(ly.name)} & {tm(ly.z0, '.4f')} & {1e3 * (ly.z1 - ly.z0):.0f} & "
                        f"{', '.join(labs)} \\\\")
    head = [r"Layer & $z_0$ (mm) & $t$ (\textmu m) & Materials present \\"]
    if tops and len(set(tops.values())) == 1:
        board = (rf"the board top is at $z={next(iter(tops.values())):g}$~mm in every "
                 r"integration")
    else:
        board = "the board top is at " + ", ".join(rf"$z={z:g}$~mm in {a}"
                                                    for a, z in tops.items())
    note = (r"Every layer of the production mesh, in the order of the mesh ($z_0$: bottom face; "
            + board + "). Converter tiers: the mixed tiers of the design record ("
            + design_sentence() + "), numbered from the converter's input (48-V) end and "
            r"named by the parts they hold; tiers and interlayer RDLs together "
            + f"{DR.converter_stack_um():.0f}" + r"~\textmu m. Z1 stacks them upward from the "
            r"substrate; Z2 and Z3 hang them below the substrate and the board, the output end "
            r"against the attach. Materials: the cards of Table~\ref{tab:supp-materials} "
            r"assigned to elements of the layer.")
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
            ("Flow distribution", f.get("flow_distribution",
                                        "uniform over the channels (ideal plenum)")),
            *([("Construction", f"{p['construction']['n_zones']}-zone manifold, alternating "
                                f"inlet/outlet headers; pass {p['construction']['pass_length_mm']:.2f} mm, "
                                f"{p['construction']['m_dot_per_pass_g_s']:.2f} g/s per zone")]
              if (p.get("construction") or {}).get("n_zones", 1) > 1 else []),
            ("Velocity, $Re$, $Pr$", f"{rg['velocity_m_s']:.2f} m/s, {rg['Re']:.0f} (laminar), {f['Pr']:.2f}"),
            ("Entrance lengths $L_h$ / $L_{th}$", f"{rg['L_hydrodynamic_entrance_mm']:.1f} / {rg['L_thermal_entrance_mm']:.1f} mm"),
            ("$Nu$ (Shah--London, 3 walls, fully developed)", f"{ht['Nu_fully_developed_3walls']:.2f}"),
            ("$h_{\\mathrm{ch}}$, $\\eta_{\\mathrm{f}}$, $\\Lambda$", f"{ht['h_channel_W_m2K']:.0f} W\\,m$^{{-2}}$K$^{{-1}}$, {ht['fin_efficiency']:.3f}, {ht['area_amplification_Lambda']:.2f}"),
            ("$R_{\\mathrm{conv}}$, $R_{\\mathrm{cal}}$, $R_{\\mathrm{base}}$", f"{ht['R_conv_K_W'] * 1e3:.2f}, {ht['R_caloric_K_W'] * 1e3:.2f}, {ht['R_base_K_W'] * 1e3:.2f} mK/W"),
            ("$h_{\\mathrm{eff}}$ uniform sink / streamwise sink", f"{ht['h_eff_uniform_sink_W_m2K']:.0f} / {ht['h_eff_streamwise_sink_W_m2K']:.0f} W\\,m$^{{-2}}$K$^{{-1}}$"),
            ("$\\Delta p$ fully developed / with entrance and plenum", f"{hy['dp_fully_developed_kPa']:.0f} / {hy['dp_with_entrance_and_plenum_kPa']:.0f} kPa")
            if "dp_header_kPa" not in hy else
            ("$\\Delta p$ fully developed + entrance / plenum / turns + headers (est.) / total",
             f"{hy['dp_fd_plus_entrance_kPa']:.1f} / {hy['dp_plenum_kPa']:.1f} / "
             f"{hy['dp_turns_kPa'] + hy['dp_header_kPa']:.1f} / {hy['dp_total_kPa']:.1f} kPa"),
            *([("Single pass (variant)", f"$\\Delta p$ {p['single_pass']['dp_total_kPa']:.0f} kPa, "
                                         f"{p['single_pass']['P_hydraulic_W']:.1f} W hydraulic per plate")]
              if p.get("single_pass") and (p.get("construction") or {}).get("n_zones", 1) > 1
              else []),
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
    land = []
    for v in c["tiers"].values():
        z3 = v["cases"].get("Z3") or {}
        t = ((case_record(z3.get("file")) or {}).get("z3_land") or {}).get("t_land_um")
        land.append(t if t is not None else grab(r"z3_land_t(\d+)", z3.get("file"), float))
    states = {case_state({"file": x.get("file")}) for v in c["tiers"].values()
              for x in v["cases"].values() if x.get("file")}
    note = (r"Total: dissipated heat, the die's 1000~W plus the package loss. Cooling~A: top "
            r"plate; cooling~B: top plate and a bottom plate under the cell grid.")
    if states == {TC.PRODUCTION_STATE}:
        note += (rf" Every case in the production state ({STATE_TEXT[TC.PRODUCTION_STATE]}).")
    if land and all(x is not None for x in land) and len(set(land)) == 1:
        note += (rf" Z3: land-side ({land[0]:g}~\textmu m) and board-plane redistribution in "
                 r"the coupled solution.")
    L += ltab(r"@{}llrrrr@{}", 6, head, body, "Heat balance per cooling and integration (W)",
              "tab:supp-heat", note)
    return L


# ---------------------------------------------------------------- S-IV flying capacitors
CAP_TEMPS_C = (25.0, 105.0, 125.0)


def flying_cap_rows():
    """The flying capacitors at the operating point of the design in force, evaluated with the
    synthesis engine's own models (HVR_FULL_OPT_EPC_V2: vendor DC-bias and temperature data
    less tolerance, vendor ESR(f), the ripple of the worst position): the design's part, the
    other rated parts of the corrected rule, the part the legacy (published) capacitor rule
    selects at the design's count (case_D_etm35.csv of the root in force) and the thin silicon
    candidates. No campaign job writes the round-2 cap49_comparison.json, so the table is
    computed here. (rows, context) or (None, None) when the engine is unavailable."""
    try:
        sys.path.insert(0, str(R / "Scalable_Integrated_VR" / "src"))
        import HVR_FULL_OPT_EPC_V2 as H
        d = DR.get()
        N, K, KA = DR.topology()
        arch = H.VRArchitecture(N=N, K=K, K_A=KA, B_array=list(d.get("B_array") or [1] * N),
                                D=DR.buck_duty(), component_count=sum(DR.part_counts().values()))
        lib = {c.name: c for c in list(H.default_capacitor_library("stress"))}
        rated = list(getattr(H, "RATED_CAPACITORS", []))
        thin = list(getattr(H, "research_capacitor_library", lambda: [])())
        lib.update({c.name: c for c in thin})
    except Exception:                                               # noqa: BLE001
        return None, None
    f = float(d["f_sw_hz"])
    i_out = DR.P_LOAD_W / DR.V_OUT / DR.n_vr()
    v_c1 = (N - 1) * DR.V_IN / N
    order = [(d["capacitor"], "production")]
    order += [(c.name, "rated") for c in rated if c.name != d["capacitor"]]
    order += [(c.name, "thin") for c in thin if c.name not in {n for n, _ in order}]
    rows = []
    for name, role in order:
        c = lib.get(name)
        if c is None:
            continue
        rows.append({"name": name, "role": role, "v_max": float(c.v_max),
                     "rating_ok": float(c.v_max) * H.CAP_V_DERATING >= v_c1,
                     "esr_mohm": float(H.cap_esr_mohm(c, f, v_c1)),
                     "height_um": getattr(c, "height_um", None),
                     "ripple": [H.flying_cap_ripple(arch, c, i_out, DR.V_IN, DR.V_OUT, f, t)
                                for t in CAP_TEMPS_C]})
    return rows, {"v_c1": v_c1, "derating": H.CAP_V_DERATING}


def capacitor_tables():
    lib = passive_library()
    d = DR.get()
    thin = thin_design()
    L = section("Flying-Capacitor Technology",
                r"Table~\ref{tab:supp-capev} is the evidence behind the flying capacitor of the "
                r"production design, the rated part "
                + passive_label(d["capacitor"], lib, maker=True)
                + (rf" in a {float(d['cap_height_um']):.0f}-\textmu m tier"
                   if d.get("cap_height_um") else "")
                + (rf", and behind the thin-capacitor technology of the sensitivity design "
                   rf"(a {thin[1]:.0f}-\textmu m capacitor tier)" if thin else "")
                + r"; Table~\ref{tab:supp-cap49} gives the flying capacitors at the operating "
                  r"point of the production design.")
    if (SUPP / "tab_capacitor_evidence.tex").is_file():
        L += [r"\input{tab_capacitor_evidence}", ""]
    else:
        L += placeholder("flying-capacitor evidence matrix", "tab_capacitor_evidence.tex")
    rows, ctx = flying_cap_rows()
    if not rows:
        return L + placeholder("flying capacitors of the production design",
                               "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py")
    role = {"production": "production", "rated": "rated", "thin": "thin"}

    def rip(x):
        if x is None or not math.isfinite(x):
            return "--"
        return r"$>$100\,\%" if x > 1.0 else f"{100 * x:.1f}\\,\\%"
    body = []
    for r in rows:
        h = r["height_um"]
        body.append(f"{passive_label(r['name'], lib, maker=True)} & {role[r['role']]} & "
                    f"{r['v_max']:.0f} & {'pass' if r['rating_ok'] else 'fail'} & "
                    f"{r['esr_mohm']:.2f} & {'--' if h is None else f'{float(h):.0f}'} & "
                    + " & ".join(rip(x) for x in r["ripple"]) + r" \\")
    head = [r"Part & Role & Rated & $C_1$ & ESR at $f_{\mathrm{sw}}$ & Height & "
            r"\multicolumn{3}{c}{Worst ripple $\Delta V_{C_i,\mathrm{pp}}/V_{C_i}$} \\",
            r"\cmidrule(l){7-9}",
            r" & & V & rating & (m$\Omega$) & (\textmu m) & 25\,$^\circ$C & 105\,$^\circ$C & "
            r"125\,$^\circ$C \\"]
    note = (f"Design: {design_sentence(lib=lib)}. Role: production, the part of the design "
            r"record; rated, another part rated for the voltage it holds; thin, the "
            r"silicon-capacitor candidate of the thin-tier technology. Ripple at the worst "
            r"capacitor position, limit 10\,\%, with the effective capacitance at bias and "
            r"temperature from vendor data less 10\,\% tolerance; --: no vendor bias data, so "
            r"the effective capacitance is unknown. $C_1$ rating: rated voltage times "
            + f"{ctx['derating']:g} against the {ctx['v_c1']:g}" + r"~V that $C_1$ holds. "
            r"Height: the part's maximum mounted height.")
    return L + ltab(r"@{}llrlrrrrr@{}", 9, head, body,
                    "Flying capacitors at the operating point of the production design",
                    "tab:supp-cap49", note)


# ---------------------------------------------------------------- S-V local solder model
JOINT_CASE = {"A_Z1": "Z1, A", "A_Z2": "Z2, A", "A_Z3": "Z3, A", "B_Z1": "Z1, B",
              "B_Z2": "Z2, B", "B_Z3": "Z3, B"}


#: the solder laws of the v2 local model (configs/tcpmt_mech/mechanics_revision.yaml)
LAW_LABEL = {"schubert2003": ("Schubert et al.", r"\cite{Schubert2003ECTC}"),
             "xiao_armstrong2005": ("Xiao and Armstrong",
                                    r"\cite{Xiao2005SAC}, constants as tabulated "
                                    r"in~\cite[Table~6]{Yuan2023SAC305}"),
             "xa_measured_norton": ("measured Norton fits",
                                    r"per-temperature Norton fits of the measured points "
                                    r"of~\cite{Xiao2005SAC} (\cite[Table~5]{Yuan2023SAC305})")}
LAW_FORM = {"garofalo": "Garofalo (hyperbolic sine)", "measured_norton": "Norton, per temperature",
            "norton": "Norton"}


def _law(k):
    return LAW_LABEL.get(k, (tex(k), ""))


def _win_txt(w):
    out = [f"{x[0]:.3g}--{x[1]:.3g}~MPa {h}" for h in ("hot", "cold")
           for x in [(w or {}).get(h)] if x]
    return ", ".join(out) or "--"


def _cal_txt(cal):
    cal = cal or {}
    T, s = cal.get("T_C"), cal.get("stress_MPa")
    out = ([rng(f"{T[0]:g}", f"{T[1]:g}", r"\,$^\circ$C")] if T else []) + \
          ([f"{s[0]:g}--{s[1]:g}~MPa"] if s else [])
    return ", ".join(out) or "not stated"


def _extrap_txt(cal, win):
    """What the visited stress window and the cycle's temperatures extrapolate beyond a law's
    calibration window."""
    cal = cal or {}
    T, s = cal.get("T_C"), cal.get("stress_MPa")
    if not T and not s:
        return "unknown (no calibration window)"
    out = []
    ws = [x for x in (win or {}).values() if x]
    if s and ws:
        lo, hi = min(x[0] for x in ws), max(x[1] for x in ws)
        if lo < s[0] or hi > s[1]:
            out.append(f"stress {lo:g}--{hi:g}~MPa visited against {s[0]:g}--{s[1]:g}~MPa")
    if T and T[0] > 25.0:
        out.append(rf"the 25-$^\circ$C cold dwell (rows below {T[0]:g}\,$^\circ$C)")
    return "; ".join(out) or "none"


def _e_law(expr):
    """(E0, slope, T0, floor) in MPa of the v2 record's 'E0 + (slope)(T - T0), floor Ef';
    None if unparsed."""
    m = re.match(r"\s*([-\d.eE+]+)\s*\+\s*\(([-\d.eE+]+)\)\s*\(T\s*-\s*([-\d.eE+]+)\)"
                 r"(?:,\s*floor\s*([-\d.eE+]+))?", str(expr or ""))
    if not m:
        return None
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)),
            float(m.group(4)) if m.group(4) else 0.0)


def _e_of_t(expr):
    """E(T) in MPa from the v2 record's elastic law; None if unparsed."""
    e = _e_law(expr)
    return (lambda T: max(e[3], e[0] + e[1] * (T - e[2]))) if e else None


def _e_txt(expr):
    """The elastic law as typeset text, in GPa."""
    e = _e_law(expr)
    if not e:
        return prose(expr or "--") + "~MPa"
    return (rf"$E(T) = {e[0] / 1e3:g} {'-' if e[1] < 0 else '+'} {abs(e[1]) / 1e3:g}\,"
            rf"(T-{e[2]:g})$~GPa" + (f" (floor {e[3] / 1e3:g}~GPa)" if e[3] else ""))


def solder_tables_v2(p):
    """The v2 local model (TCPMT round 3, tcpmt_solder_parameters.v2_parameters): zero-yield
    creep laws of a law band, each carried as a temperature-dependent Norton surrogate fitted
    over the stress window the joints visit, and the global-kinematics boundary conditions."""
    L = section("Local Solder-Joint Model",
                r"Tables~\ref{tab:supp-card}--\ref{tab:supp-localsetup} list every parameter of "
                r"the local solder-joint model behind the local responses, with its source, "
                r"calibration window and what is extrapolated, and the limitations of the laws.")
    s = p.get("solder") or {}
    el, cr, ex = s.get("elastic") or {}, s.get("creep") or {}, s.get("expansion") or {}
    prod = cr.get("production_law")
    name, cite = _law(prod)
    eot = _e_of_t(el.get("E_MPa"))
    nu = el.get("nu")
    body = [f"{tm(float(r['T_C']), '.0f')} & "
            f"{num(eot(float(r['T_C'])) / 1e3) if eot else '--'} & {num(nu)} & "
            f"{sci(r.get('A'), 3)} & {num(r.get('n'), 4)} \\\\" for r in cr.get("rows") or []]
    err = cr.get("surrogate_max_rate_err_rel") or {}
    yz = grab(r"flat at ([0-9.eE+-]+) MPa", s.get("yield_and_hardening"), float)
    alpha = ex.get("alpha_per_K")
    head = [r"$T$ & $E$ & $\nu$ & $A$ & $n$ \\",
            r"($^\circ$C) & (GPa) & & (s$^{-1}$MPa$^{-n}$) & \\"]
    note = (rf"Production law: {name} ({LAW_FORM.get(cr.get('form'), tex(cr.get('form') or '--'))}"
            + (f"~{cite}" if cite else "") + f"), for {prose(cr.get('alloy_of_the_law') or '--')}; "
            f"the joint is {prose(s.get('alloy_of_the_joint') or '--')}. "
            r"The solver integrates $\dot\varepsilon_{\mathrm{in}} = A(T)\,(\sigma_{\mathrm{vm}}-"
            r"\sigma_y)^{n(T)}$ with a zero yield surface"
            + (f" ($\\sigma_y = {p10(yz)[1:-1] if p10(yz).startswith('$') else p10(yz)}$~MPa)"
               if yz else "")
            + r", i.e., the applied von~Mises stress the laws were fitted in, with no "
            r"rate-independent hardening; the law enters as a temperature-dependent Norton "
            r"surrogate fitted at every 2.5-$^\circ$C row of the card (listed at 25-$^\circ$C "
            r"steps) over the stress window the joints visit"
            + (f", {_win_txt(cr.get('visited_window_MPa'))}" if cr.get("visited_window_MPa")
               else "")
            + (f" ({prose(cr['window_status'])})" if cr.get("window_status") else "")
            + (rf"; surrogate rate error at most {100 * err['hot']:.0f}\,\% (hot dwell) and "
               rf"{100 * err['cold']:.0f}\,\% (cold dwell)" if err.get("hot") is not None
               and err.get("cold") is not None else "")
            + ". Elasticity: " + _e_txt(el.get("E_MPa")) + r", $\nu$ = " + num(nu)
            + " (" + prose(re.sub(r"^ASSUMPTION", "assumption",
                                  str(el.get("kind") or "assumption"))) + ")"
            + (rf"; thermal expansion {alpha * 1e6:.3g}~ppm/K, stress-free at "
               rf"{float(ex.get('T_ref_C', 25)):.0f}\,$^\circ$C" if alpha else "") + ".")
    L += ltab(r"@{}rrrrr@{}", 5, head, body, "Solder card as passed to the solver (production "
              "law)", "tab:supp-card", note)

    # -- ingredients: every law of the band, with its calibration and what is extrapolated
    cu = p.get("copper_pads") or {}
    rows = [("Elasticity", r"Linear in $T$ (Table~\ref{tab:supp-card})",
             r"Room-temperature $E$: midpoint of the 40--50-GPa band of~\cite{Paska2024SAC305}; "
             r"slope and $\nu$ assumed",
             "Room temperature only; no temperature dependence in the source"),
            ("Yield and hardening", "None (zero yield)",
             r"The zero-yield laws carry no rate-independent hardening; no hardening card "
             r"is used", "--")]
    laws = [(prod, {"form": cr.get("form"), "alloy": cr.get("alloy_of_the_law"),
                    "calibration_window": cr.get("calibration_window"),
                    "visited_window_MPa": cr.get("visited_window_MPa"),
                    "window_status": cr.get("window_status")}, True)]
    laws += [(k, v, False) for k, v in (s.get("band_laws") or {}).items()]
    for k, v, is_prod in laws:
        nm, ct = _law(k)
        cal = v.get("calibration_window") or {}
        rows.append((f"Creep: {nm}" + (" (production)" if is_prod else " (band)"),
                     LAW_FORM.get(v.get("form"), tex(v.get("form") or "--"))
                     if v.get("form") else "--",
                     (ct + "; " if ct else "") + prose(v.get("alloy") or "--"),
                     "Calibrated: " + _cal_txt(cal) + "; visited: "
                     + _win_txt(v.get("visited_window_MPa")) + "; extrapolated: "
                     + _extrap_txt(cal, v.get("visited_window_MPa"))))
    rows.append(("Thermal expansion", "Constant",
                 (rf"{alpha * 1e6:.3g}~ppm/K, assumed (21--24~ppm/K commonly quoted)"
                  if alpha else "--"), "No temperature dependence"))
    rows.append(("Copper pads", "Linear elastic",
                 rf"$E = {float(cu.get('E_MPa', 0)) / 1e3:.0f}$~GPa, $\nu = {num(cu.get('nu'))}$, "
                 rf"{float(cu.get('cte_per_K', 0)) * 1e6:.3g}~ppm/K; handbook-type constants",
                 "No temperature dependence"))
    L += ltab(r"@{}L{2.4cm}L{2.4cm}L{6.4cm}L{5.8cm}@{}", 4,
              [r"Ingredient & Model form & Source & Calibration window and extrapolation \\"],
              [" & ".join(r) + r" \\" for r in rows],
              "Sources and calibration windows of the solder laws", "tab:supp-cardsrc",
              r"Visited: the stress window of the last cycle over the joints (5--95\,\% "
              r"quantiles, strain-weighted) on which each law's surrogate is fitted; "
              r"extrapolated: what that window and the cycle's temperatures leave outside the "
              r"law's calibration.")

    # -- geometry, boundary conditions, loading and integration
    g, bc, lc = p.get("geometry") or {}, p.get("boundary_conditions") or {}, \
        p.get("loading_cycle") or {}
    ti, rsp, me = p.get("time_integration") or {}, p.get("response") or {}, p.get("mesh") or {}
    rs, ds = ti.get("ramp_step") or {}, ti.get("dwell_step") or {}
    src = r"~\cite[Table~III]{Krishnakumar2026DVPD}" if "Krishnakumar" in str(g.get("source")) \
        else ""
    unc = J(TR / "uncertainty.json") or {}
    prow = [
        ("Ball, as homogenized globally",
         rf"diameter {float(g.get('ball_diameter_um', 0)):.0f}~\textmu m, stand-off "
         rf"{float(g.get('standoff_um', 0)):.0f}~\textmu m" + src),
        ("Solder volume", prose(g.get("solder_shape") or "--") +
         r" (the convention of the global ball-array homogenization)"),
        ("Copper pads", rf"{float(g.get('pad_um', 0)):.0f}~\textmu m square, "
         rf"{float(g.get('pad_thickness_um', 0)):.0f}~\textmu m thick"),
        ("Averaging core", r"solder less a fixed-width band"
         + (f" ({float(g['averaging_band_frac']):.3f} of the side)"
            if g.get("averaging_band_frac") is not None else "")
         + " at the pads and the free surface"),
        ("Elements", f"{tex(me.get('element', '--'))}, level {tex(me.get('level', '--'))}: "
         f"{me.get('n_elements', '--')} elements, {me.get('n_core_elements', '--')} in the "
         "averaging core"),
        ("Pad faces", prose(bc.get("pad_faces") or "--")),
        ("Global-to-local transfer", prose(bc.get("transfer_from_global") or "--")),
        ("Temperature", prose(bc.get("temperature") or "--")
         + (rf"; stress-free at {float(bc['stress_free_temperature_C']):.0f}\,$^\circ$C"
            if bc.get("stress_free_temperature_C") is not None else "")),
        ("Cycle",
         rf"{lc.get('n_cycles', '--')} cycles of {float(lc.get('period_s', 0)):g}~s: "
         rf"{float(lc.get('dwell_hot_s', 0)):g}~s hot dwell at $T_{{\mathrm{{j}}}}$ with $\du$ and "
         rf"{float(lc.get('dwell_cold_s', 0)):g}~s cold dwell at "
         rf"{float(lc.get('T_cold_C', 25)):g}\,$^\circ$C, " + prose(lc.get("ramp") or "")
         + ("; sensitivity: dwell " + "/".join(f"{float(x):g}" for x in
                                               lc.get("dwell_sensitivity_s") or []) + "~s, ramp "
            + "/".join(f"{float(x):g}" for x in lc.get("ramp_sensitivity_s") or []) + "~s"
            if lc.get("dwell_sensitivity_s") else "")),
        ("Time integration",
         rf"implicit viscoplastic update ({tex(ti.get('procedure', '--'))}); creep tolerance "
         rf"{ti.get('CETOL', '--')} on the change of inelastic strain rate per increment"),
        ("Increments, ramp step",
         rf"initial {float(rs.get('dt0_s', 0)):g}~s, minimum {p10(rs.get('dt_min_s'))}~s, "
         rf"maximum {float(rs.get('dt_max_s', 0)):g}~s"),
        ("Increments, dwell step",
         rf"initial {float(ds.get('dt0_s', 0)):g}~s, minimum {p10(ds.get('dt_min_s'))}~s, "
         rf"maximum {float(ds.get('dt_max_s', 0)):g}~s"),
        ("Response $\\deps$", prose(rsp.get("definition") or "--")),
    ]
    if unc.get("eps_basis"):
        prow.append(("Compared responses", prose(unc["eps_basis"])
                     + r" (Table~\ref{tab:supp-unc})"))
    L += ltab(r"@{}L{3.6cm}L{13.2cm}@{}", 2, [r"Item & Setting \\"],
              [f"{a} & {b} \\\\" for a, b in prow],
              "Local model geometry, boundary conditions, loading and integration",
              "tab:supp-localsetup")

    # -- limitations of the laws, in prose
    items = [rf"The production law ({name}) was fitted to "
             rf"{prose(cr.get('alloy_of_the_law') or 'another alloy')}, not to the joint's "
             rf"{prose(s.get('alloy_of_the_joint') or 'SAC305')}."]
    rvm = cr.get("rate_vs_measured_Sn3.9Ag0.6Cu") or {}
    if _cal_txt(cr.get("calibration_window")) == "not stated":
        items.append(r"Its constants are reprinted without their data window, so its "
                     r"calibration window is not stated"
                     + (rf"; inside the measured window of the band laws its creep rate is "
                        rf"{rvm['ratio_min']:.0f}--{rvm['ratio_max']:.0f} times the measured "
                        rf"Sn3.9Ag0.6Cu rates (geometric mean {rvm['ratio_geomean']:.0f})"
                        if rvm.get("ratio_min") is not None else "") + ".")
    for k, v in (s.get("band_laws") or {}).items():
        cal = v.get("calibration_window") or {}
        items.append(rf"The band law {_law(k)[0]} ({prose(v.get('alloy') or '--')}) is "
                     rf"calibrated on {_cal_txt(cal)}; the joints visit "
                     rf"{_win_txt(v.get('visited_window_MPa'))}, which extrapolates "
                     + _extrap_txt(cal, v.get("visited_window_MPa")) + ".")
    if err.get("hot") is not None and err.get("cold") is not None:
        items.append(rf"The Norton surrogate reproduces the production law within "
                     rf"{100 * err['hot']:.0f}\,\% (hot dwell) and {100 * err['cold']:.0f}\,\% "
                     r"(cold dwell) in rate over the visited window; the error travels with "
                     r"the card.")
    if str(cr.get("window_status") or "").startswith("initial"):
        items.append(r"The visited window is the configured initial one: the iteration of the "
                     r"window to self-consistency has not been run.")
    band = p.get("law_band") or {}
    if band:
        hold = band.get("rankings_hold_across_laws")
        items.append(r"Every compared local response is recomputed under each law of the band"
                     + ("" if hold is None else
                        "; the rankings " + ("hold" if hold is True else "do not all hold")
                        + " across the laws") + ".")
    L += [r"\noindent\emph{Limitations of the solder laws.}", r"\begin{itemize}"]
    L += [rf"\item {x}" for x in items] + [r"\end{itemize}", ""]
    # S12-S15: the production-state responses, the critical-joint check, the local-model
    # checks and the interconnect layers (the block keeps its seven tables, S9-S15)
    L += joint_band_table() + critical_v2_table() + local_checks_table() + \
        interconnect_table()
    return L


V2_CASE = {"A_Z1": "Z1, A", "A_Z2": "Z2, A", "A_Z3": "Z3, A", "B_Z1": "Z1, B",
           "B_Z2": "Z2, B", "B_Z3": "Z3, B"}


def _lab(st_lab):
    """'SDEC_A_Z1' or 'A_Z1' -> 'Z1, A'."""
    k = "_".join(st_lab.split("_")[-2:])
    return V2_CASE.get(k, tex(st_lab))


def _sx(x, d=2):
    """x 1e3 at d decimals, or --"""
    return "--" if x is None else f"{1e3 * float(x):.{d}f}"


def _xy(x, y):
    """a site '(x, y)' in mm with typographic minus signs"""
    return f"({x:g}, {y:g})".replace("-", r"$-$")


def joint_band_table():
    b = J(TR / "solder_law_band.json")
    if not b or not b.get("band"):
        return placeholder("joint response under the law band", "solder_law_band.json")
    prod = b["production_law"]
    laws = [prod] + [k for k in b.get("band_laws") or [] if k != prod]
    # each joint's numerical U: the local checks' own (L0 -> L3, 4 -> 8 cycles), the values the
    # uncertainty record carries once it is rebuilt on this band
    jr = (J(TR / "solder_local_checks.json") or {}).get("joint_resolution") or {}
    urel = jr.get("U_rel") or {}
    body = []
    for lab in ("A_Z1", "A_Z2", "A_Z3", "B_Z1", "B_Z2", "B_Z3"):
        v, jt = b["band"].get(lab), (b.get("joints") or {}).get(lab)
        if not v or not jt:
            continue
        ur = urel.get(lab)
        body.append(f"{V2_CASE[lab]} & {_xy(jt['x_mm'], jt['y_mm'])} & {fx(jt['T_C'])} & "
                    f"{fx(jt['du_xy_um'], 2)} & {fx(jt['du_z_um'], 2)} & "
                    + " & ".join(_sx(v["values"].get(k)) for k in laws)
                    + f" & {_sx(v.get('min'))}--{_sx(v.get('max'))} & "
                    f"{'--' if ur is None else fx(100 * ur, 1)} \\\\")
    # the count neighbours (design subroots): their Z1 joints, each design's own law band
    nb_rows = 0
    for dk in ("m25", "m49"):
        nb = J(TR.parent / "designs" / dk / "tcpmt_revision" / "solder_law_band.json") or {}
        for lab in ("A_Z1", "B_Z1"):
            v, jt = (nb.get("band") or {}).get(lab), (nb.get("joints") or {}).get(lab)
            if not v or not jt or not v.get("complete"):
                continue
            nb_rows += 1
            mm = DR.get(dk)["n_vr"]
            body.append(f"{V2_CASE[lab]}, $M = {mm}$ & {_xy(jt['x_mm'], jt['y_mm'])} & "
                        f"{fx(jt['T_C'])} & {fx(jt['du_xy_um'], 2)} & {fx(jt['du_z_um'], 2)} & "
                        + " & ".join(_sx(v["values"].get(k)) for k in laws)
                        + f" & {_sx(v.get('min'))}--{_sx(v.get('max'))} & -- \\\\")
    cards = J(TR / "solder_law_cards.json") or {}
    cw = (cards.get("laws") or {}).get(prod) or {}
    rk = (b.get("rankings") or {})
    head = [r"Case & Site & $T_{\mathrm{sj}}$ & $|\Delta u_{xy}|$ & $\Delta u_z$ & "
            + " & ".join(_law(k)[0] for k in laws) + r" & Band & $U_{95}$ \\",
            r" & (mm) & ($^\circ$C) & (\textmu m) & (\textmu m) & "
            + " & ".join(r"\multicolumn{1}{c}{($10^{-3}$)}" for _ in laws)
            + r" & ($10^{-3}$) & (\%) \\"]
    st = {"SDEC": "the production state (implemented decoupling)",
          "S0": "the ideal-decoupling reference"}.get(b.get("state") or "S0", b.get("state"))
    cc = b.get("critical_check")
    note = (r"Joint response $\deps$ (per cycle) at each case's critical joint in " + st +
            r", local model driven by the full cut-boundary displacement of the global solution "
            r"(both pad faces: translation, in-plane stretch and rotation), linear 3-s ramps and "
            r"300-s dwells, 4 cycles, L0 mesh; one column per law of the solder-law band, the "
            r"production law first. Band: lowest--highest law, the reported uncertainty of the "
            r"joint response; $U_{95}$: numerical (own L0$\to$L3 and 4$\to$8-cycle changes, "
            r"Table~\ref{tab:supp-localchecks}). "
            + ((r"The production law's surrogate window is self-consistent at these joints "
                r"(the fitted window within 10\,\% of the one they visit, responses within "
                r"1\,\%)" if cw.get("converged") else
                r"The production law's surrogate window is \textbf{not converged}") + ": "
               + _win_txt(cw.get("window_MPa")) + ". " if cw else "")
            + (("Joints: under every law its own maximum-response site over the BGA lattice "
                r"(Table~\ref{tab:supp-critv2}); the site columns give the production law's" +
                ("" if b.get("same_site_all_laws") else
                 ", and " + "; ".join(
                     f"{V2_CASE[lab]}: " + ", ".join(
                         f"{_law(k)[0]} {_xy(*xy)}"
                         for k, xy in (v.get("sites_mm") or {}).items()
                         if k != prod and xy != (v.get("sites_mm") or {}).get(prod))
                     for lab, v in b["band"].items()
                     if not v.get("same_site_all_laws")) + " under the other laws")
                + ". ") if cc else r"Joints: the maximum-$|\Delta u_{xy}|$ sites. ")
            + "Ranking per law: " + "; ".join(
                f"{_law(k)[0]}: A {tex(rk.get(k, {}).get('A') or '--')}, B "
                f"{tex(rk.get(k, {}).get('B') or '--')}" for k in laws if rk.get(k)) + "."
            + (r" $M = 25$, $M = 49$: the Z1 joints of the count neighbours (their own "
               r"production cases), the same local model, law band and lattice search, each "
               r"law's window iterated on their own joints." if nb_rows else ""))
    return ltab(r"@{}lrrrr" + "r" * len(laws) + "rr@{}", 7 + len(laws), head, body,
                "Joint response of the compared cases under the solder-law band",
                "tab:supp-jointband", note, sep="2.5pt")


def critical_v2_table():
    c = J(TR / "solder_critical_v2.json")
    if not c or not c.get("cases"):
        return placeholder("critical-joint check", "solder_critical_v2.json")
    others = {law: J(TR / f"solder_critical_v2_{law}.json")
              for law in ("xiao_armstrong2005", "xa_measured_norton")}
    others = {k: v for k, v in others.items() if v and v.get("cases")}
    body, diffs = [], {}
    for lab, v in c["cases"].items():
        sc, mo = v.get("site_coverage") or {}, v.get("monotonicity") or {}
        mf, scr = v.get("monotonicity_screen") or {}, v.get("screen") or {}
        mr, md = v.get("max_response_site") or {}, v.get("max_du_site") or {}
        w = (mo.get("worst_violation") or {}).get("excess_rel")
        wf = scr.get("largest_reversal_rel")
        oth = []
        for law, cl in others.items():
            r = ((cl["cases"].get(lab) or {}).get("max_response_site") or {})
            if r and (abs(r["x_mm"] - mr.get("x_mm", 1e9)) > 1e-6
                      or abs(r["y_mm"] - mr.get("y_mm", 1e9)) > 1e-6):
                oth.append(f"{_law(law)[0]} {_xy(r['x_mm'], r['y_mm'])}")
        if oth:
            diffs[lab] = oth
        body.append(f"{_lab(lab)} & {sc.get('lattice_sites', '--')} & "
                    f"{scr.get('n_base', '--')}/{scr.get('n_lattice_front', '--')} & "
                    f"{v.get('n_solved', '--')} & "
                    f"{mo.get('n_violations', '--')}/{mo.get('n_ordered_pairs', '--')}"
                    + ("" if not w else rf" ({100 * w:.0f}\,\%)") + " & "
                    f"{mf.get('n_violations_over_1pct', '--')}/{mf.get('n_ordered_pairs', '--')}"
                    + ("" if wf is None else rf" ({100 * wf:.1f}\,\%)") + " & "
                    f"{fx(100 * scr['margin_rel'], 0) if scr.get('margin_rel') else '--'} & "
                    f"{_xy(md.get('x_mm', 0), md.get('y_mm', 0))} & "
                    f"{_xy(mr.get('x_mm', 0), mr.get('y_mm', 0))}"
                    + (r"$^\dagger$" if oth else "") + " & "
                    f"{fx(v.get('max_response_over_max_du'), 3)} \\\\")
    head = [r"Case & Lattice & Base/front & Solved & Viol. $(|\Delta u_{xy}|, T)$ & "
            r"Viol. screen & Margin & Max-$\Delta u$ site & Max-response site & Ratio \\",
            r" & & & & & & (\%) & (mm) & (mm) & \\"]
    dag = "; ".join(f"{_lab(lab)}: " + ", ".join(o) for lab, o in diffs.items())
    n_other = {law: sum(x.get("n_solved", 0) for x in cl["cases"].values())
               for law, cl in others.items()}
    note = (r"Critical joint under the full cut-boundary displacement: the maximum response "
            r"over the BGA lattice, production law at its converged window. Lattice: legal "
            r"sites of the 0.8-mm lattice (Z2: the ring around the board opening), every one "
            r"with its own kinematics from the case's converged fields. Base: the top 30 by "
            r"$|\Delta u_{xy}|$, by relative face tilt, by $|\varepsilon_z|$ and by the deforming "
            r"$\Delta u$, the strict Pareto front in ($|\Delta u_{xy}|$, $T$) and the corners; "
            r"front: the lattice's Pareto front in the screening features (deforming "
            r"$\Delta u$, $|\Delta u_z|$, $T$). The response is not monotone in "
            r"($|\Delta u_{xy}|$, $T$) (violations: reversed / all dominance pairs of the solved "
            r"sites, largest excess), but is in the screening features within the margin "
            r"(reversals beyond 1\,\% / pairs, largest): a site dominated in them by a solved "
            r"site $c$ responds at most (1 + margin)$\,\deps(c)$, margin = max(10\,\%, twice the "
            r"largest reversal). Every lattice site whose bound exceeded the maximum found was "
            r"solved, until none did"
            + (" (closed for every case)" if c.get("all_closed") else
               r" (\textbf{not closed})")
            + r": the maximum-response site bounds the whole lattice. Ratio: its response over "
            r"that at the maximum-$|\Delta u_{xy}|$ site. "
            + ("The other laws of the band are screened the same way at their own windows ("
               + ", ".join(f"{_law(k)[0]}: {n} sites solved" for k, n in n_other.items())
               + ")" + (rf"; $^\dagger$their maximum-response site differs: {dag}."
                        if dag else "; their maximum-response sites are the production law's.")
               if others else ""))
    return ltab(r"@{}lrrrrrrccr@{}", 10, head, body,
                "Critical joint over the BGA lattice with the full boundary transfer",
                "tab:supp-critv2", note, sep="2.2pt")


def local_checks_table():
    c = J(TR / "solder_local_checks.json")
    if not c or not c.get("groups"):
        return placeholder("local-model checks", "solder_local_checks.json")
    g = c["groups"]
    labs = [x for x in ("A_Z1", "A_Z2", "A_Z3", "B_Z1", "B_Z2", "B_Z3")
            if x in (c.get("v2_baseline") or {})]

    def cell(group, var, lab):
        r = ((g.get(group) or {}).get(lab) or {}).get(var) or {}
        x = r.get("rel_to_v2")
        return "--" if x is None else f"{100 * x:+.1f}".replace("-", r"$-$")
    rows = [("v2 response ($10^{-3}$)", None, None)]
    rows += [("Mesh L1", "mesh", "L1"), ("Mesh L2", "mesh", "L2"), ("Mesh L3", "mesh", "L3"),
             ("8 cycles", "cycles", "N8"), ("Dwell 60 s", "dwell", "dwell60"),
             ("Dwell 900 s", "dwell", "dwell900"), ("Ramp 30 s", "dwell", "ramp30"),
             ("C3D8I elements", "element", "C3D8I"), ("C3D8R elements", "element", "C3D8R"),
             ("Earlier model (E)", "chain", "R2"), ("E + ramps", "chain", "ramp"),
             ("+ zero-yield law", "chain", "law"), ("+ $u_z$ released", "chain", "uz"),
             ("v2 with STEP loads", "chain", "v2_step")]
    body = []
    for name, group, var in rows:
        if group is None:
            body.append(f"{name} & " + " & ".join(_sx(c['v2_baseline'].get(l)) for l in labs)
                        + r" \\")
            continue
        body.append(f"{name} & " + " & ".join(cell(group, var, l) for l in labs) + r" \\")
    # the averaging band (tcpmt_mech_band_study): each band against the production band at the
    # same mesh level
    bs = J(TR / "solder_band_study_v2.json") or {}
    band_txt = ""
    if bs.get("joints"):
        for lev in bs.get("levels") or ():
            for bnd, info in bs["bands"].items():
                if bnd == bs.get("production_band"):
                    continue
                cells = []
                for l in labs:
                    x = (((bs["joints"].get(l) or {}).get("levels") or {}).get(lev) or {}).get(
                        bnd, {}).get("change_vs_production_band")
                    cells.append("--" if x is None else
                                 f"{100 * x:+.1f}".replace("-", r"$-$"))
                body.append(f"Band {info['band_um']:.0f}~\\textmu m ({lev}) & "
                            + " & ".join(cells) + r" \\")
        pb = bs["bands"][bs["production_band"]]["band_um"]
        band_txt = (rf" Band: the corner band excluded from the averaging core, against the "
                    rf"production {pb:.0f}~\textmu m at the same mesh level (L0, L2); the "
                    r"orderings of each cooling "
                    + ("hold under every band and level." if bs.get("orderings_hold_everywhere")
                       else "change under some band or level."))
    fp = c.get("fine_pitch_joints") or {}
    fp_txt = []
    for key, v in fp.items():
        if not v.get("d_eps"):
            continue
        t, a = ("B", key[2:]) if key.startswith("B_") else ("A", key)
        fp_txt.append(rf"{a}, {t}: {prose(v.get('label') or v.get('layer'))} "
                      rf"$\gamma = {1e3 * (v.get('gamma') or 0):.1f}\times10^{{-3}}$, "
                      rf"$\deps = {1e3 * v['d_eps']:.2f}\times10^{{-3}}$"
                      + (rf" ({1e3 * v['d_eps_uz']:.2f} under the in-plane transfer with "
                         r"$u_z$ released)" if v.get("d_eps_uz") else ""))
    head = [r"Check & " + " & ".join(V2_CASE[l] for l in labs) + r" \\"]
    note = (r"Change of $\deps$ against the production local model (first row), in \%. Mesh: "
            r"the nested joint meshes L1--L3 against L0; 8 cycles against 4; dwell and ramp "
            r"against 300 and 3~s; element types against C3D8. Attribution chain: an earlier local "
            r"model (overstress card with hardening, in-plane $\Delta u$ only, STEP loading) and "
            r"each change toward the production model in turn." + band_txt + " "
            + ("Critical fine-pitch joints, own geometry: " + "; ".join(fp_txt) + "."
               if fp_txt else ""))
    return ltab(r"@{}l" + "r" * len(labs) + "@{}", 1 + len(labs), head, body,
                "Checks of the local model at the compared joints", "tab:supp-localchecks",
                note)


LAYER_LABEL = {"bga": "BGA", "interface": "Die microbumps",
               "conv_attach_vr_substrate": "Cu-pillar attach", "z3_attach_vr_pcb": "SAC attach"}


def interconnect_table():
    d = J(TR / "interconnect_drivers.json")
    if not d or not d.get("cases"):
        return placeholder("interconnect layers", "interconnect_drivers.json")
    lad = (J(TR / "interconnect_mesh_ladder.json") or {}).get("cases") or {}
    body = []
    for lab, c in d["cases"].items():
        first = True
        for name, r in (c.get("layers") or {}).items():
            cr = r["critical"]
            lr = ((lad.get(lab) or {}).get("layers") or {}).get(name) or {}
            body.append(f"{_lab(lab) if first else ''} & {LAYER_LABEL.get(name, tex(name))} & "
                        f"{fx(r.get('h_um'), 0)} & ({cr['x_mm']:.2f}, {cr['y_mm']:.2f}) & "
                        f"{fx(cr.get('T_C'))} & {fx(1e3 * r['gamma_max'], 2)} & "
                        f"{fx(1e3 * (r.get('gamma_def_max') or 0), 2)} & "
                        f"{fx(cr.get('du_z_um'), 3)} & {fx(lr.get('r31_over_r21'), 2)} \\\\")
            first = False
        sp = c.get("bga_split") or {}
        sh = sp.get("share_along_du") or {}
        if sh:
            sg = lambda x: tm(round(100 * (x or 0)), "g")             # noqa: E731
            body.append(rf" & \multicolumn{{8}}{{l}}{{\emph{{BGA driver: membrane "
                        rf"{sg(sh.get('membrane'))}\,\%, bending "
                        rf"{sg(sh.get('bending'))}\,\%, residual "
                        rf"{sg(sh.get('residual'))}\,\% of $\Delta u$; rigid "
                        rf"rotation {fx(sp.get('rigid_rotation_um'), 3)}~\textmu m}}}} \\")
    head = [r"Case & Layer & $h$ & Critical site & $T$ & $\gamma$ & $\gamma_{\mathrm{def}}$ & "
            r"$\Delta u_z$ & r31/r21 \\",
            r" & & (\textmu m) & (mm) & ($^\circ$C) & ($10^{-3}$) & ($10^{-3}$) & (\textmu m) & "
            r" \\"]
    note = (r"Every interconnect layer of each compared case, searched at every site (BGA: the "
            r"legal lattice; the thinner layers: every mesh node). $\gamma = |\Delta u_{xy}|/h$ at "
            r"the layer's critical site; $\gamma_{\mathrm{def}}$: the largest layer shear strain "
            r"$\partial u_x/\partial z + \partial u_z/\partial x$ (the joint's rigid rotation "
            r"removed); r31/r21: $\gamma$ on the fine rung over the production rung of the case's "
            r"own ladder (the die-edge corner over the microbumps is singular, so its driver does "
            r"not converge). Membrane / bending: the in-plane displacement of each plate at its "
            r"stiffness-weighted neutral plane and its rotation times the lever arm, along "
            r"$\Delta u$ at the BGA critical site.")
    return ltab(r"@{}llrcrrrrr@{}", 9, head, body,
                "Interconnect layers of the compared cases", "tab:supp-interconnect", note,
                sep="2.5pt")


def solder_tables():
    p = J(TR / "solder_parameters.json")
    if p and "solder_SAC305" not in p and "solder" in p:
        return solder_tables_v2(p)                  # the v2 harness (TCPMT round 3)
    if not p or "solder_SAC305" not in p:
        return section("Local Solder-Joint Model",
                       r"The parameters of the local solder-joint model behind the local "
                       r"responses, with their sources and calibration windows.") + \
            placeholder("local solder model", "solder_parameters.json")
    L = section("Local Solder-Joint Model",
                r"Tables~\ref{tab:supp-card}--\ref{tab:supp-stress} list every parameter of the "
                r"local solder-joint model behind the published local responses, with its source "
                r"and calibrated range, and the limitations of the creep card.")
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
#: the campaign's job records (peak resident memory per attempt), under the root in force
JOB_STATUS = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "_campaign" / "status"


def job_rss_mb(pattern):
    """Peak resident memory (MB) of the finished jobs whose status files match a glob pattern:
    the runner's RUSAGE_CHILDREN maximum, i.e. the largest process of each job."""
    out = []
    for f in sorted(JOB_STATUS.glob(pattern)) if JOB_STATUS.is_dir() else []:
        d = J(f) or {}
        if d.get("status") == "done" and d.get("maxrss_mb"):
            out.append(float(d["maxrss_mb"]))
    return out


def _gb(vals):
    """'a' or 'a--b' in GB, one decimal; None when no job matched."""
    if not vals:
        return None
    lo, hi = min(vals) / 1024, max(vals) / 1024
    return f"{hi:.1f}" if abs(hi - lo) < 0.05 else f"{lo:.1f}--{hi:.1f}"


def mesh_runtime_table():
    """Mesh, runtime and peak memory of the compared cases of the production state under
    cooling A (tcpmt_cases; Z3 the coupled land-side case); a case not run is a row of dashes.
    Peak memory: the campaign's job record of the case (status/*.json, maxrss); the note gives
    the other stages by job class."""
    st = TC.PRODUCTION_STATE
    body, threads = [], set()
    missing = False
    for a in ARCHS:
        pth = TC.case_path(st, "A", a)
        c = J(pth) if pth else None
        if not c:
            body.append(f"{a} & -- & -- & -- & -- & -- & -- & -- & -- \\\\")
            missing = True
            continue
        threads.add(c.get("threads"))
        th, me = c["thermal"], c.get("mechanics") or {}
        tot = (c["et_wall_s"] + me.get("wall_s", 0)) / 3600
        mem = _gb(job_rss_mb(f"prod.{a}.{st}.A.a*.json")) or "--"
        body.append(f"{a}{z3_dag(a, pth.name, c)} & {th['n_nodes']:,} & {th['n_elems']:,} & "
                    f"{3 * th['n_nodes']:,} & {len(c['et_history'])} & {c['et_wall_s']:.0f} & "
                    f"{me.get('wall_s', 0):.0f} & {tot:.1f} & {mem} \\\\".replace(",", "{,}"))
    n_thr = next(iter(threads)) if len(threads) == 1 and None not in threads else 2
    head = [r"Integration & Nodes & Elements & Structural & E--T & E--T & Structural & Total "
            r"& Peak \\",
            r" & & & DOF & iterations & (s) & (s) & (h) & memory (GB) \\"]
    stages = [("the coarsest mesh rung (r11)", "ladder.*.r11.a*.json"),
              ("the through-thickness rung (r12)", "ladder.*.r12.a*.json"),
              ("the finest rung (r31)", "ladder.*.r31.a*.json"),
              ("the complete-package MOOSE reference", "moose.fullpkg.a*.json"),
              ("the mechanics-only reruns on converged fields", "mech.board*.a*.json"),
              ("the reflow and bonding checks", "mech.reflow.*.a*.json"),
              ("a critical-joint search of the local model", "mech.critical*.a*.json"),
              ("the local-model checks with the finest joint mesh", "mech.local_checks.a*.json")]
    mem_txt = [f"{what} {_gb(job_rss_mb(pat))}~GB" for what, pat in stages if job_rss_mb(pat)]
    mem_note = ((r" Peak memory: the largest resident set of any process of the job, from the "
                 r"campaign's job records (thermal and structural solves of the case); "
                 r"other stages: " + "; ".join(mem_txt) + ".") if mem_txt else "")
    note = (rf"Cases: the production state ({STATE_TEXT[st]}) under cooling~A, Z3 with the "
            r"coupled land-side and board-plane redistribution" + ("; --: not run" if missing
                                                                    else "") + ". "
            r"Production mesh: graded $h_{xy}=1.1$~mm grid with every in-plane interval split in "
            r"two (r21); 8-node hexahedra (thermal C3D8, structural C3D8I incompatible modes); "
            r"CalculiX~2.23. Thermal: steady conduction, direct solver; E--T stop: every coupled "
            r"region temperature changes by less than 0.25~K and the loss by less than 0.1\,\%; "
            r"coolant energy balance iterated to 0.02~K. Structural: linear thermoelastic, "
            r"$T_{\mathrm{ref}}=25\,^\circ$C, rigid-body motion restrained only, iterative "
            r"Cholesky solver (verified against the direct SPOOLES solver, "
            r"Table~\ref{tab:supp-verif}). Machine: two-socket Intel Xeon Gold 6342 (2.8~GHz, "
            rf"48 cores), shared; thermal solves on {n_thr} threads, structural on 1. Times "
            r"include every "
            r"E--T iteration (each a thermal solve with its coolant balance) and the structural "
            r"solve with the all-site joint search; they exclude geometry construction and meshing "
            r"(under 2~min per integration), the local solder model and postprocessing. "
            r"Sensitivity runs repeat the same chain." + mem_note
            + (DAGGER_NOTE if any(r"$^\dagger$" in b for b in body) else ""))
    return ltab(r"@{}lrrrrrrrr@{}", 9, head, body,
                "Meshes, solvers, runtimes and memory (production state, cooling A)",
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


def _cooling_row(r):
    """The cold-plate row with the plate model in force (three-wall H1 Nusselt number) against
    the conjugate CFD solution (cooling_spec.json); the matrix row predates that model and is
    never printed with the superseded correlation's error."""
    cf = ((J(TR / "cooling_spec.json") or {}).get("plate") or {}).get("cfd_comparison") or {}
    if not isinstance(cf.get("dT_base_mean_rel_diff"), (int, float)):
        return None
    nu = cf.get("Nu")
    return dict(r, error=cf["dT_base_mean_rel_diff"],
                production_value=cf.get("dT_base_mean_correlation_K"),
                reference_value=cf.get("dT_base_mean_cfd_K"),
                production_model=("laminar microchannel correlation (three-wall H1 Nusselt "
                                  "number" + (f" {nu:.2f}" if nu else "") + ", fin efficiency, "
                                  "base resistance)"),
                limitations=("one channel half-pitch with symmetry walls at the single-pass "
                             "flow; constant water properties; the manifold flow split and "
                             "its header losses are not part of the check"))


def verification_table():
    acc = J(FC / "accuracy_speed_matrix.json")
    if not acc:
        return placeholder("verification matrix", "accuracy_speed_matrix.json")
    body = []
    for r in acc.get("rows", []):
        if r.get("stage") == "cooling_icepak":
            r = _cooling_row(r)
            if r is None:
                continue
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
    # the state of the laddered reference cases (tcpmt_uncertainty: the S0 cooling-A production
    # cases of the integrations that have one; Z3 has none in round 3)
    ref_st = sorted({case_state({"file": (v or {}).get("file")}) or "S0"
                     for v in (u.get("reference_cases") or {}).values()}) or ["S0"]
    ref_lab = "/".join(ref_st)
    body = []
    cases = u.get("cases") or {}
    for y in ("P", "T", "warp", "du", "eps"):
        if body:
            body.append(r"\midrule")
        for a in ARCHS:
            c = rel.get(a, {}).get(y)
            comp = (" & ".join(f"{100 * c[k]:.2f}" for k in ("mesh", "tt", "et", "ref", "total"))
                    + (f" & {100 * c['bias_rel']:+.2f}" if "bias_rel" in c else " & --")
                    if c else r"\multicolumn{6}{c}{local mesh and cycle count; law band in the "
                              r"resolution}" if y == "eps" else
                    rf"\multicolumn{{6}}{{c}}{{no {ref_lab} reference ladder}}")
            cells = []
            for t in ("A", "B"):
                x = U.get(f"{t}.{a}.{y}")
                o = ((cases.get(t) or {}).get(a) or {}).get("outputs", {}).get(y) or {}
                cells.append("--" if x is None else
                             (f"{x:.2f}" if x < 10 else f"{x:.1f}")
                             + (r"$^\dagger$" if o.get("provisional") else ""))
            body.append(f"{UNC_NAME[y] if a == 'Z1' else ''} & {a} & {comp} & "
                        f"{' & '.join(cells)} \\\\")
    code = {"resolved": "R", "not resolved": "--", "law-conditional": "L", "pending": "P",
            # a file of the superseded rule
            "resolved with correlation credit": "Rc"}
    seen = {}
    for r in u.get("comparisons", []):
        seen.setdefault((r["tier"], r["a"], r["b"]), []).append(r)
    comps = [rf"cooling~{t}, {a}/{b}: " +
             "; ".join(f"{UNC_NAME[r['output']].split(' (')[0]} {r.get('lower') or ''} "
                       f"{code.get(r['verdict'], r['verdict'])}"
                       + (r"$^\dagger$" if r.get("provisional") else "") for r in rows)
             for (t, a, b), rows in seen.items()]
    n_need = len(u.get("ladder_runs_needed") or [])
    head = [r"Output & Int. & \multicolumn{6}{c}{Relative to the value, " + ref_lab +
            r" reference ladder (\%)} & \multicolumn{2}{c}{$U_{95}$} \\",
            r"\cmidrule(lr){3-8}\cmidrule(l){9-10}",
            r" & & mesh & through-thickness & E--T stop & reference & total & bias $\beta$ & "
            r"cooling A & cooling B \\"]
    note = (r"One rule for every comparison: $D = y_b - y_a$ is resolved when "
            r"$|D+\beta_D| > U_{95}(D)$, with $\beta_D$ the signed production-mesh bias and "
            r"$U_{95}(D)$ the uncertainty of the difference at about 95\,\% coverage. "
            r"Discretization: a GCI-type estimate on the nested ladder r11/r21/r31 of $D$ itself "
            r"(the observed order with $F_s = 1.25$ where the ladder is asymptotic, "
            r"$|p - 2| \leq 0.2$; otherwise $F_s = 3$ with the order limited to [0.5, 2]), so "
            r"errors shared on one mesh family cancel only where they move together; the "
            r"through-thickness split r11$\to$r12 ($F_s = 3$), the E--T stop of each case and "
            r"the matched-reference agreement of the solver, in quadrature. Columns: the "
            r"components of each integration's " + ref_lab + r" reference ladder (cooling~A "
            r"production case), relative to the value "
            r"(temperatures: to the rise above the inlet); $U_{95}$ of each compared case; "
            r"$\dagger$: the case has no ladder of its own and carries its reference's estimate "
            rf"provisionally (identical mesh; {n_need} ladder rungs listed for the campaign). "
            r"$\deps$: own local numerical $U$ (L0$\to$L3, cycle count), resolved only when "
            r"resolved under every law of the solder-law band (L: production law only)" +
            ("" if st == "S0" else r" (solved on the S0 cases; not compared in this state)") +
            r". Model-form uncertainty is not part of $U$: "
            r"it is covered by rerunning both integrations under each declared alternative "
            r"(Table~\ref{tab:supp-variants}). Comparisons, lower integration first (R: "
            r"resolved; --: not resolved; P: pending): " +
            ". ".join(c[:1].upper() + c[1:] for c in comps) + ".")
    return ltab(r"@{}llrrrrrrrr@{}", 10, head, body,
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
    the input state when it is not the production state (SDEC, the implemented decoupling)."""
    case_file = c.get("case") or ""
    t = {"A": "A", "B": "B", "I": "I"}.get(c.get("tier"), "A")
    s = f"{c.get('arch', '?')}, {t}"
    st = case_state(c)
    if st and st != TC.PRODUCTION_STATE:
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


def variant_text(name):
    """Readable name of a case variant: a robustness variant, a cooling base, a further
    variant or a land-side run, with its cooling when the name carries one."""
    if name in VARIANT_LABEL or re.match(r"conv_E(\d+)_a(\d+)$", name):
        return variant_label(name)
    m = re.match(r"(.+?)_+([AB])$", name)       # a mapped variant run under cooling A or B
    if m and (m.group(1) in VARIANT_LABEL or re.match(r"conv_E(\d+)_a(\d+)$", m.group(1))):
        return variant_label(m.group(1)) + f", cooling~{m.group(2)}"
    it = re.search(r"_it(\d+)$", name)
    lab, tier = review_label(name[:it.start()] if it else name)
    if it:
        lab += f", iteration {it.group(1)}"
    return lab + (f", cooling~{tier}" if tier else "")


def record_label(r):
    """Readable label of any case or variant of the feasibility stage."""
    st = case_state(r)
    case = r.get("case") or ""
    var = r.get("variant") or (None if "__" not in case else
                               case.split("__", 1)[1].rsplit(".", 1)[0])
    txt = (f"base case, cooling~{r.get('tier') or 'A'}" if var is None else variant_text(var))
    tag = r", superseded (uncoupled Z3)" if r.get("role") == "superseded" else ""
    return f"{tex(r.get('arch', '?'))}, {tex(st or '--')}: {txt}{tag}"


def feasibility_table():
    """The feasibility stage (tcpmt_feasibility): every declared limit on every compared case
    of every input state (tcpmt_cases), and the verdict of every case and variant."""
    f = J(TR / "feasibility.json")
    if not f or "records" not in f:
        return placeholder("feasibility stage", "feasibility.json")
    lim = f["limits"]
    labels = feas_labels(f)
    # the per-ball current under the policy in force (tcpmt_feasibility: a filter, or a stated
    # requirement on the package that is reported, not filtered on)
    if (f.get("bga_policy") or {}).get("in_force") == "requirement":
        sens = lim.get("bga_A_per_ball_sensitivity")
        bga = (r"the current of every power ball at the case's waveform a stated requirement on "
               r"the package (target " + f"{lim['bga_A_per_ball']:.1f}" + "~A"
               + (f", {sens:.1f}~A as sensitivity" if sens is not None else "")
               + "), reported, not a filter")
    else:
        bga = (r"every power ball $\le" + f"{lim['bga_A_per_ball']:.1f}" + r"$~A at the case's "
               r"waveform")

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
            r"$; X7R/X7S/X7T capacitors $\le" + f"{lim['mlcc_C']:.0f}" + r"$; inductor $\le" +
            f"{lim['inductor_C']:.0f}" + r"$; build-up dielectric and encapsulant $T_g\approx" +
            f"{lim['buildup_Tg_C']:.0f}" + r"$; board $T_g\approx" + f"{lim['board_Tg_C']:.0f}" +
            r"$; processor die $\le" + f"{lim['die_C']:.0f}" +
            r"$; solder law calibrated $\le" + f"{lim['solder_cal_C']:.0f}" +
            r"$, solidus " + f"{lim.get('solder_solidus_C', 217):.0f}" + "; " + bga +
            r", with at least " + f"{100 * (1 - lim['bga_power_site_fraction_max']):.0f}" +
            r"\,\% of the ball sites left for signals; static drop $\le" +
            f"{lim['ir_drop_mV_per_rail']:.0f}" + r"$~mV per rail. Cases: integration, cooling "
            r"(A: top plate; B: top plate and bottom plate, the bottom one behind a 50-\textmu m "
            r"TIM) and input state when not the production state " + tex(TC.PRODUCTION_STATE) +
            " (" + STATE_TEXT[TC.PRODUCTION_STATE] + "): " +
            "; ".join(f"{s}, {STATE_TEXT[s]}" for s in TC.STATES if s != TC.PRODUCTION_STATE) +
            r"; Z3 always with the coupled land-side redistribution. A check that fails only on "
            r"the whole-field bound is unresolved; such a candidate is not ranked either." +
            (DAGGER_NOTE if any(v_[2] for v_ in labels.values()) else ""))
    return ltab(r"@{}L{3.0cm}rrrrrrrrrL{3.4cm}@{}", 11, head, body,
                "Feasibility stage: every limit on every case", "tab:supp-feas", note)


def scenario_table():
    """The selected regulator under every input state, cooling A: the production state
    (implemented decoupling) and the S0/S1 references from tcpmt_cases (Z3 on its coupled land
    side), S2 on the Z1/Z2 production-boundary cases and the Z3 land-side base; a case not run
    yet is a row of dashes."""
    try:                                        # the ledger's scenario ratios (design record)
        import final_closure_ledger as FL
        ratio = {k[3:]: float(v) for k, v in FL.SCEN_RATIO.items()}
    except Exception:                                               # noqa: BLE001
        ratio = {"S0": 1.0, "S1": 1.0 / math.sqrt(DR.buck_duty()),
                 "S2": math.sqrt(DR.V_IN / DR.V_OUT)}
    dec = J(TR / "input_decoupling.json") or {}
    k_dec = ((dec.get("summary") or {}).get("recommended") or {}).get("k_eq")
    if k_dec is None:
        k_dec = (DR.get().get("decoupling") or {}).get("k_eq")

    def kfmt(x):
        return "--" if x is None else (f"{x:.0f}" if abs(x - round(x)) < 1e-9 else f"{x:.2f}")

    def s2_path(a):
        """The S2 case of an integration under cooling A: the chain's production-boundary case
        (Z1, Z2) or the coupled land-side base (Z3), as the campaign writes them."""
        base = TC.COOLING_BASE[(a, "A")]
        p = (FC / f"etm_{a}_HV_S2_h1.1_r21.json" if base is None else
             FC / "sensitivity" / f"etm_{a}_HV_S2__{base}.json")
        return p if p.is_file() else None
    body, marked = [], False
    for a in ARCHS:
        for s in (*TC.STATES, "S2"):
            pth = s2_path(a) if s == "S2" else TC.case_path(s, "A", a)
            c = J(pth) if pth else None
            k = (grab(r"k_eq = ([\d.]+)", ((c or {}).get("variant") or {}).get("what"), float)
                 or k_dec) if s == TC.PRODUCTION_STATE else ratio.get(s)
            if not c:
                body.append(f"{a} & {s} & -- & -- & -- & -- & -- & {kfmt(k)} \\\\")
                continue
            me = c.get("mechanics") or {}
            cr = (me.get("joint_search") or {}).get("critical") or {}
            h = c["et_history"][-1]
            du = f"{cr['du_um']:.2f} at {cr['T_C']:.0f}" if cr else "--"
            warp = (f"{me['die_warpage_pv_um']:.1f}"
                    if me.get("die_warpage_pv_um") is not None else "--")
            dg = z3_dag(a, pth.name, c)
            marked |= bool(dg)
            body.append(f"{a}{dg} & {s} & "
                        f"{c['P_loss_w']:.1f} & {c['thermal']['T_max_C']:.1f} & "
                        f"{h.get('T_ls_C', float('nan')):.1f} & {du} & {warp} & {kfmt(k)} \\\\")
    head = [r"Integration & State & $P$ (W) & $T_{\max}$ & $T_{\mathrm{LS}}$ & "
            r"$\du$ (\textmu m) & Warpage & $k$ \\",
            r" & & & ($^\circ$C) & ($^\circ$C) & at $T_{\mathrm{j}}$ ($^\circ$C) & (\textmu m) & \\"]
    note = (r"Package-internal loss, peak and low-side tier temperature, critical joint and die "
            r"warpage under cooling~A (Z3: the coupled land-side case) per input state: SDEC, the "
            r"implemented decoupling (the production state); S0, ideal input smoothing; S1, no "
            r"decoupling (a square pulse at the buck duty $D = N V_{\mathrm{out}}/V_{\mathrm{in}}"
            + f" = 1/{1.0 / DR.buck_duty():.0f}$); S2, a square pulse at the overall conversion "
            r"ratio $V_{\mathrm{out}}/V_{\mathrm{in}}$. $k$: RMS-to-average ratio of the current "
            r"the 48-V feed carries (SDEC: the loss-equivalent $k_{\mathrm{eq}}$ the case was run "
            r"with)" + ("; --: not run" if any(" -- & -- " in b for b in body) else "") + "."
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
    dv = d.get("derived") or {}
    head = [r"Land side, cooling & $P$ & Land & Planes & $\Delta V_{\mathrm{land}}$ & "
            r"$T_{\max}$ & Warpage & $\du$ & $R^*$ \\",
            r" & (W) & (W) & (W) & (mV) & ($^\circ$C) & (\textmu m) & (\textmu m) & (m$\Omega$) \\"]
    states = {case_state({"file": r.get("file")}) for r in d["table"] if r.get("file")}

    def tie(key):
        """'at t = X um' of a tie with Z1 under cooling B; None when the record has none."""
        x = dv.get(key) or {}
        t = x.get("t_um")
        if t is None:
            return None
        return (f"$t = {t:.0f}$~\\textmu m" + ("" if x.get("bracketed", True) else
                                                " (extrapolated beyond the runs)"))
    tb, tl = tie("tie_with_board_planes"), tie("tie_land_only")
    drop = (dv.get("drop_30mV_one_rail") or {}).get("t_um")
    note = (r"Land-side copper thickness $t$ and cooling; board planes $2\times35$~\textmu m per "
            r"rail at 80\,\% occupancy, equal ball sharing"
            + (", " + "/".join(sorted(s for s in states if s)) if states - {None} else "")
            + r". $\Delta V_{\mathrm{land}}$: static land-side drop of one rail; $R^*$: feed "
            r"limit. "
            + (f"Tie with Z1 under cooling~B at {tb}" + (f" (land side alone: {tl})" if tl
                                                         else "") + "; "
               if tb else "No tie with Z1 under cooling~B within the runs; ")
            + (r"a land-side drop of at most 30~mV per rail needs "
               rf"$t \ge {drop:.0f}$~\textmu m." if drop is not None else
               r"the 30-mV land-side drop thickness is not available."))
    return ltab(r"@{}lrrrrrrrr@{}", 9, head, body,
                "Board-backside integration with the land-side and board-plane redistribution "
                "coupled", "tab:supp-z3land", note)


# ---------------------------------------------------------------- S-IX exploration
#: the screen runs of the campaign (scripts/campaign/build_manifest.py dse_sweeps), case D:
#: (tag, column head); the phase-2 runs carry the production converter rules at a tier limit
SCREEN_RUNS = (("etm35", "Legacy rule"), ("etm35_caprule_full", "Corrected rule"),
               ("etm35_p2_t4", r"$\le$4 tiers"), ("etm35_p2_t5", r"$\le$5 tiers"),
               ("etm35_p2_tinf", "No tier limit"))


def caprule_screen_table():
    """Total loss and selected member at every count under each screen run in the root in
    force: the legacy (published) capacitor rule rerun on the current engine, the corrected
    capacitor rule, and the phase-2 screens with the production converter rules at the tier
    limits (the round-2 dse_caprule.json is not regenerated; the CSVs are)."""
    runs = [(t, h, dse_rows(t)) for t, h in SCREEN_RUNS]
    runs = [(t, h, rows) for t, h, rows in runs if rows]
    if not runs:
        return placeholder("regulator-count screen", "case_D_etm35_p2_t4.csv")
    prod_tag = screen_run()
    m0 = DR.n_vr()
    best = {}
    for t, _h, rows in runs:
        f = [(float(r["total_loss_W"]), m) for m, r in rows.items() if dse_feasible(r)]
        best[t] = min(f) if f else None
    counts = sorted({m for _t, _h, rows in runs for m in rows})
    body = []
    for m in counts:
        cells = []
        for t, _h, rows in runs:
            r = rows.get(m)
            if r is None:
                cells.append("")                                    # count not screened
            elif not dse_feasible(r):
                cells.append("--")
            else:
                c = f"{float(r['total_loss_W']):.1f} ({int(float(r['N']))}/{int(float(r['K']))})"
                cells.append(rf"\textbf{{{c}}}" if best[t] and best[t][1] == m else c)
        body.append(f"{m}{r'$^\ast$' if m == m0 else ''} & " + " & ".join(cells) + r" \\")
    opt = "; ".join(
        f"{h.replace(chr(36), '').replace(r'\le', 'at most ')}: $M = {best[t][1]}$ "
        f"({best[t][0]:.1f}~W)" if best[t] else f"{h}: none" for t, h, _r in runs)
    note = (r"Total loss (W) and the selected member $N/K$ of case~D at each count $M$; --: no "
            r"feasible member; blank: count not screened by that run; bold: least loss of the "
            r"run. Legacy rule: the published flying-capacitor rule, rerun on the current "
            r"engine. Corrected rule: every flying capacitor rated with "
            r"0.8 derating for the $(N-1)V_{\mathrm{in}}/N$ that $C_1$ holds (rated parts "
            r"admitted), the effective-capacitance ripple check (parts without vendor bias data "
            r"excluded) and the ESR at the switching frequency. Tier columns: the production "
            r"converter rules (corrected capacitor rule, datasheet gate resistance, capacitor "
            r"body footprints, tiers that may mix part classes) at a limit on the converter "
            r"tiers"
            + (rf"; the production rule is the run of the design record's screen "
               rf"({tier_rule(max_tiers(prod_tag))})" if prod_tag else "")
            + rf". $^\ast$: the production design, $M = {m0}$. Least loss: {opt}.")
    return ltab(r"@{}r" + "l" * len(runs) + "@{}", 1 + len(runs),
                [r"$M$ & " + " & ".join(h for _t, h, _r in runs) + r" \\"],
                body, "Regulator-count screen before and after the capacitor-rule correction and "
                "under the tier limit", "tab:supp-caprule", note)


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
    "gan_k_half": "GaN-tier $k\\times0.5$", "conv_k_tenth": "Converter-tier $k\\times0.1$",
    # mechanics-only and cooling-model variants of the final campaign
    "encap_emc_lowcte": "Low-CTE mold compound",
    "encap_emc_lowcte_const": "Mold compound without $T_g$",
    "encap_uf_tg": "Underfill-class encapsulant",
    "bga_card_local": "BGA layer from the local solder card",
    "board_t2p4": "PCB 2.4 mm thick", "conv_posts_lower": "Copper posts, lower bound",
    "conv_posts_upper": "Copper posts, upper bound",
    "plate_caloric_legacy": "Cold-plate coefficient with the caloric resistance",
    # cooling-model and card forms run as alternatives
    "conv_k_legacy": "Converter tiers as one medium", "conv_gap_legacy": "Encapsulant cap, no posts",
    "nu_legacy_table": "Cold-plate Nu, three-wall table", "props_legacy_50C": "Coolant at 50~$^\\circ$C",
    "wall_viscosity": "Wall-viscosity correction", "plate_single_pass": "Single-pass cold plates",
    "board_hbot60": "Board-bottom film 60", "board_hbot520": "Board-bottom film 520"}
#: neutral descriptions of the alternative forms (the registry's text names their history)
VARIANT_WHAT = {
    "conv_k_legacy": "one effective medium (k 60 W\\,m$^{-1}$K$^{-1}$) on the inductor, output- and "
                     "flying-capacitor tiers, solid silicon on the GaN tiers",
    "nu_legacy_table": "cold-plate Nu from the three-wall table with a long wall adiabatic instead "
                       "of the short-wall-adiabatic H1 fit"}


def variant_label(name):
    if name in VARIANT_LABEL:
        return VARIANT_LABEL[name]
    m = re.match(r"conv_E(\d+)_a(\d+)$", name)
    if m:
        return f"Converter $E$ {m.group(1)}~GPa, CTE {m.group(2)}"
    return tex(name)


BOARD_LABEL = {"screws": "screws at the board corners", "screws_pinned": "pinned screws",
               "edge": "simply supported edge", "clamp_screws": "clamp at the screws",
               "clamp_backplate": "clamp on a backplate",
               "free_ring_hot": "3x board, ring at the edge temperature",
               "free_ring_cold": "3x board, ring at 25~$^\\circ$C",
               "screws_ring_hot": "3x board on screws",
               "clamp_screws_ring_hot": "3x board, clamp at the screws"}


def screen_label(key):
    """'SDEC_A_Z2__board_screws_pinned' -> 'pinned screws (Z2, implemented, A)'."""
    ref, name = key.split("__", 1)
    st, t, a = ref.split("_")
    lab = (BOARD_LABEL.get(name[6:], tex(name[6:])) if name.startswith("board_")
           else variant_label(name))
    return (f"{lab[:1].lower() + lab[1:] if not lab.startswith(('PCB', 'BGA', 'TSV', 'GaN')) else lab}"
            f" ({a}, {STATE_NAME.get(st, st)} decoupling, cooling~{t})")


def variants_table():
    import final_closure_sensitivity as S
    sc = J(TR / "robustness_joint.json") or {}
    g0 = (sc.get("groups") or {}).get("S0_A") or {}
    body = []
    for name, v in S.VARIANTS.items():
        what = re.sub(r"\bmaterial dict\b", "material card", v["what"])
        what = what.replace("Z2-COOLED plate", "a bottom plate under the Z2 converter")
        o = ((g0.get(name) or {}).get("orderings") or {}).get("eps:Z1/Z2")
        if name in VARIANT_WHAT:
            what = None
        jt = (f"{1e3 * o['variant'][0]:.2f} / {1e3 * o['variant'][1]:.2f}" if o else "--")
        body.append(f"{variant_label(name)} & {'mech.' if v['kind'] == 'mech' else 'full'} & "
                    f"{'/'.join(v['archs'])} & "
                    f"{VARIANT_WHAT[name] if what is None else prose(what)}"
                    + (f" & {jt}" if g0 else "") + r" \\")
    val = sc.get("validation") or {}
    note = (r"Each run changes one declared input on the production mesh and reruns the whole "
            r"electrothermal--mechanical chain (full) or only the mechanics on the converged "
            r"field (mech.). The bottom-plate variants of Z1, Z2 and Z3 define cooling~B and the "
            r"top-plate-only variant of Z3 defines its cooling~A; the Z3 cases of the paper add the "
            r"coupled land-side and board-plane redistribution (Table~\ref{tab:supp-z3land}).")
    if g0:
        b = next(iter(g0.values()))["orderings"]["eps:Z1/Z2"]["base"]
        note += (rf" Joint: $\deps$ of Z1 / Z2 ($10^{{-3}}$ per cycle, ideal decoupling, "
                 rf"cooling~A; reference {1e3 * b[0]:.2f} / {1e3 * b[1]:.2f}), the production "
                 rf"local model at the {sc['K']} worst sites of each reference case's "
                 r"critical-joint search, the variant's response being the largest of them; an "
                 r"integration a variant does not touch keeps the reference value. "
                 + (rf"A full critical-joint search on {len(val)} variants of different kinds "
                    rf"({'; '.join(screen_label(k) for k in sorted(val))}) "
                    + ("found the worst site inside those sites in every one."
                       if sc.get("validation_all_in_top_k") else
                       "found the worst site outside those sites in "
                       + str(sum(1 for x in val.values() if not x.get("max_in_top_k")))
                       + " of them.") if val else ""))
    return ltab(r"@{}L{4.0cm}lL{0.9cm}L{" + ("8.9" if g0 else "10.7") + "cm}"
                + ("r" if g0 else "") + "@{}", 4 + bool(g0),
                [r"Variant & Rerun & Int. & What changes" + (r" & Joint" if g0 else "")
                 + r" \\"], body,
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
    return ltab(r"@{}lL{6.2cm}lrrrrr@{}", 8, head, body, "Further variants of the compared cases",
                "tab:supp-review", note)


def assembly_mounting_table():
    """TCPMT round 3 (findings 5-8, 11a), after the review-round variants: reflow / bonding
    warpage against the coplanarity limits, board size / mounting / clamp and the encapsulant
    and BGA-card variants, mechanics only on the production fields under cooling A and B."""
    rf = J(TR / "reflow_warpage.json") or {}
    bd = J(TR / "board_study_SDEC.json") or {}
    vr = J(TR / "robustness_mech_SDEC.json") or {}
    if not (rf.get("cases") or bd.get("cases") or vr.get("variants")):
        return placeholder("assembly warpage, mounting and material variants",
                           "reflow_warpage.json / board_study_SDEC.json")
    L = []
    rows = []
    for key, c in sorted((rf.get("cases") or {}).items()):
        if "_r21" not in key:
            continue
        a, sfx = key.split("_r21")
        enc = {"": "production", "_encap_uf_tg": "underfill class (Tg 130)",
               "_encap_emc_lowcte": "low-CTE mold compound (Tg 165)"}.get(sfx, tex(sfx))
        ch = c.get("checks") or {}
        b, sol, tc = ch.get("bga@bga_reflow") or {}, ch.get("bga@bga_solidus") or {}, \
            ch.get("tcb") or {}
        w, ws, g = b.get("warpage") or {}, sol.get("warpage") or {}, \
            tc.get("gap_nonuniformity") or {}
        rows.append(f"{a} & {enc} & {fx(w.get('pv_plane_removed_um'), 0)} & "
                    f"{tm(round(w.get('bow_corner_minus_centre_um', 0)), 'g')} & "
                    f"{fx(ws.get('pv_plane_removed_um'), 0)} & "
                    f"{fx(b.get('pv_over_room_coplanarity'), 2)} & "
                    f"{fx(tc.get('T_C'), 0)} & {fx(g.get('pv_plane_removed_um'), 1)} & "
                    f"{fx(tc.get('limit_um'), 0)} \\\\")
    if rows:
        lim = rf.get("limits") or {}
        cv = (lim.get("bga_coplanarity_room_um") or {}).get("value")
        rl = (lim.get("bga_reflow_warpage_um") or {}).get("value") or [None, None]
        head = [r"Int. & Encapsulant & PV 245 & Bow 245 & PV 217 & PV/cop. & $T_{\mathrm{bond}}$ "
                r"& Gap & Limit \\",
                r" & & (\textmu m) & (\textmu m) & (\textmu m) & & ($^\circ$C) & (\textmu m) & "
                r"(\textmu m) \\"]
        note = (r"Isothermal warpage of the unmounted package (no board, BGA or TIM; Z3 without "
                r"its converter) at the SAC305 reflow peak (245\,$^\circ$C) and solidus "
                r"(217\,$^\circ$C) against a 25-$^\circ$C stress-free state, production mesh: "
                r"plane-removed peak-to-valley over the ball footprint and the signed bow (corners "
                r"minus centre, positive away from the board); PV/cop.: over the "
                + (f"{cv:g}" if cv else "80") + r"-\textmu m room-temperature coplanarity "
                r"(JEP95); the SPP-024A reflow window is "
                + (f"{rl[0]:g} to +{rl[1]:g}" if rl[0] is not None else "--")
                + r"~\textmu m. Gap: plane-removed non-uniformity of the fine-pitch joint's gap "
                r"at its bonding temperature (Z1: converter top under the flat die; Z2: substrate "
                r"underside against the converter top; Z3: board underside against the converter "
                r"top), against a declared limit (half the solder cap or bump stand-off).")
        L += ltab(r"@{}llrrrrrrr@{}", 9, head, rows, "Warpage at reflow and bonding",
                  "tab:supp-reflow", note, sep="2.5pt")
    rows = []
    var_lab = {"screws": "Screws at the board corners", "screws_pinned": "Screws, pinned",
               "edge": "Edge simply supported", "clamp_screws": "Clamp 200 N at the screws",
               "clamp_only": "Clamp only (25 C)", "clamp_backplate": "Clamp on a backplate",
               "free_ring_hot": "3x board, ring at the edge temperature",
               "free_ring_cold": "3x board, ring at 25 C",
               "screws_ring_hot": "3x board on screws",
               "clamp_screws_ring_hot": "3x board, clamp at the screws"}
    cases = bd.get("cases") or {}
    order = [f"SDEC_{t}_{a}" for t in ("A", "B") for a in ("Z1", "Z2", "Z3")]
    cols = [k for k in order if k in cases]
    # the joint response at the worst of the case's K worst sites (tcpmt_mech_joint_screen)
    sc = J(TR / "robustness_joint.json") or {}
    scv = sc.get("variants") or {}

    def eps_txt(key):
        v = scv.get(key) or {}
        x = v.get("change_rel")
        return "--" if x is None else f"{100 * x:+.0f}"

    for var, lab in var_lab.items():
        cells = []
        for k in cols:
            r = (cases[k].get("mechanics") or {}).get(var) or {}
            if "warp_rel_vs_case" in r:
                cells.append((f"{100 * r['warp_rel_vs_case']:+.0f} / "
                              f"{100 * r['du_rel_vs_case']:+.0f}"
                              + (f" / {eps_txt(f'{k}__board_{var}')}" if scv else ""))
                             .replace("-", r"$-$").replace(r"$-$$-$", "--"))
            else:
                cells.append("--")
        rows.append(prose(lab) + " & " + " & ".join(cells) + r" \\")
    for name, tag in (("encap_uf_tg", "Underfill-class encapsulant (Tg 130)"),
                      ("encap_emc_lowcte", "Low-CTE mold compound (Tg 165)"),
                      ("encap_emc_lowcte_const", "Mold compound without Tg"),
                      ("bga_card_local", "BGA layer from the local solder card")):
        per = (vr.get("variants") or {}).get(name) or {}
        cells = []
        for k in cols:
            _s, t, a = k.split("_")
            ch = ((per.get(t) or {}).get("change_rel") or {}).get(a) or {}
            cells.append("--" if ch.get("warp") is None else
                         (f"{100 * ch['warp']:+.0f} / {100 * ch['du']:+.0f}"
                          + (f" / {eps_txt(f'{k}__{name}')}" if scv else ""))
                         .replace("-", r"$-$").replace(r"$-$$-$", "--"))
        rows.append(f"{tag} & " + " & ".join(cells) + r" \\")
    if cols:
        head = [r"Variant & " + " & ".join(f"{k.split('_')[2]}, {k.split('_')[1]}" for k in cols)
                + r" \\"]
        note = (r"Change of die warpage / largest ball displacement $\du$"
                + (r" / joint response $\deps$" if scv else "")
                + r" (\%) against each compared case "
                r"(production state), mechanics only on the case's converged field, production "
                r"mesh"
                + ((rf"; $\deps$: the production local model at the {sc.get('K')} worst "
                    r"sites of the case's critical-joint search, the variant's response being "
                    r"the largest of them (a clamp is held through the cycle: its cold "
                    r"half-cycle is the clamp-only state at the same site)") if scv else "")
                + r". Mounting: $u_z = 0$ on 2-mm patches 3~mm inside the board corners (pinned: "
                r"also in plane), or along the underside perimeter; clamp: the cold-plate preload "
                r"as a uniform pressure on the TIM, reacted at the screws or by a backplate under "
                r"the package; 3x board: the board extended to three package sides with its ring "
                r"at the coupon's edge temperature or at 25\,$^\circ$C (bounds of the ring's "
                r"temperature); encapsulant classes with their glass transition on the "
                r"out-of-cell fill.")
        L += ltab(r"@{}L{5.0cm}" + "r" * len(cols) + "@{}", 1 + len(cols), head, rows,
                  "Board, mounting, clamp and material variants on the production fields",
                  "tab:supp-mounting", note, sep="2.5pt")
    return L


# ---------------------------------------------------------------- assembly
#: the input states by the names the paper uses (no internal state labels in the supplement)
STATE_NAME = {"SDEC": "implemented", "S0": "ideal", "S1": "bare", "S2": "ratio pulse"}
_STATE_PHRASES = (
    ("input state when not the production state SDEC (implemented decoupling): S0, ideal input "
     "smoothing; S1, no decoupling;",
     "input state when not the production state (implemented decoupling): ideal, ideal input "
     "smoothing; bare, no decoupling;"),
    ("per input state: SDEC, the implemented decoupling (the production state); S0, ideal input "
     "smoothing; S1, no decoupling",
     "per input state: implemented, the implemented decoupling (the production state); ideal, "
     "ideal input smoothing; bare, no decoupling"),
    ("; S2, a square pulse at the overall conversion", "; ratio pulse, a square pulse at the "
                                                       "overall conversion"),
    ("(SDEC: the loss-equivalent", "(implemented: the loss-equivalent"),
    ("Production mesh, S0 unless the input decoupling is implemented.",
     "Production mesh, ideal decoupling unless the input decoupling is implemented."),
    ("implemented input decoupling (scenario SDEC)", "implemented input decoupling"),
    ("equal ball sharing, S0.", "equal ball sharing, ideal decoupling."),
    ("S0 reference ladder", "ideal-decoupling reference ladder"),
    ("the S0 cases", "the ideal-decoupling cases"),
    ("converged S0 heat map", "converged ideal-decoupling heat map"),
    ("S0 heat map", "ideal-decoupling heat map"),
    ("Z1 S0 die warpage", "Z1 ideal-decoupling die warpage"),
    ("at the S0 current", "at the ideal-decoupling current"))


def state_names(txt):
    """Internal input-state labels (S0, S1, S2, SDEC) to the names of the paper, and the paper's
    temperature symbols: T_jn for a GaN junction, T_sj for a solder joint."""
    for a, b in _STATE_PHRASES:
        txt = txt.replace(a, b)
    txt = txt.replace("$T_J$", r"$T_{\mathrm{jn}}$").replace(r"$T_J\le", r"$T_{\mathrm{jn}}\le")
    txt = txt.replace(r"$T_{\mathrm{j}}$", r"$T_{\mathrm{sj}}$")
    txt = re.sub(r"\{(Z[123]), (SDEC|S0|S1|S2): ",
                 lambda m: "{" + m.group(1) + ", " + STATE_NAME[m.group(2)] + ": ", txt)
    txt = re.sub(r"^(Z[123], [AB]), (SDEC|S0|S1|S2) &",
                 lambda m: m.group(1) + ", " + STATE_NAME[m.group(2)] + " &", txt, flags=re.M)
    txt = re.sub(r"^(Z[123][^&\n]*) & (SDEC|S0|S1|S2) &",
                 lambda m: m.group(1) + " & " + STATE_NAME[m.group(2)] + " &", txt,
                 flags=re.M)
    return txt


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
                 r"Table~\ref{tab:supp-variants} gives the package decisions of the robustness "
                 r"study, Table~\ref{tab:supp-omit} the omitted converter losses and "
                 r"Table~\ref{tab:supp-review} further variants of the compared cases; the "
                 r"warpage at reflow and bonding and the board, mounting, clamp and material "
                 r"variants on the production fields follow them.")
    L += variants_table() + omitted_losses_table()
    L += review_variants_table()
    L += assembly_mounting_table()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    txt = "\n".join(L) + "\n"
    for a, b in ((r"(NOT SAC305; DEFECT \#41)", "(not SAC305)"),
                 ("(NOT SAC305; DEFECT #41)", "(not SAC305)"), ("(NOT SAC305)", "(not SAC305)"),
                 # one name for the die power map, as in the paper
                 ("Die hot-spot power map", "Core-heavy die power map"),
                 ("die hot-spot map", "core-heavy die map")):
        txt = txt.replace(a, b)
    txt = state_names(txt)
    OUT.write_text(txt)
    print(f"wrote {OUT} ({len(L)} lines)")


if __name__ == "__main__":
    main()
