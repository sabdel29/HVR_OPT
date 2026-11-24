"""Flying-capacitor evidence matrix (TCPMT revision, Option A).

Requirement per cell, from the design record in force (configs/design_points.yaml, HVR_DESIGN):
C_i holds (N - i) V_in / N; rated voltage x 0.8 must cover the stress; the effective capacitance
at bias, at the synthesis rule's temperature (105 C) and less tolerance must hold the switching
ripple (I_out / N) D / f_sw below 10 % of V_Ci (the synthesis engine's own rule and models); both
capacitors within the cell; heights judged against the 100-um tier of the thin-capacitor
sensitivity and against 150 um.

Every entry rests on manufacturer data already in the repository (Murata public characteristic
data: research/tcpmt_revision/capacitor_datasheet_data.json, flying_cap_vendor_data.json;
the decap survey: flying_caps.json) or on the manufacturer pages cited. Effective capacitance
is "not published" where no vendor curve was obtained. Manufacturers not covered are listed.

    python tcpmt_capacitor_evidence.py   -> research/tcpmt_revision/capacitor_evidence.json
                                            manuscript_v2/supplement/tab_capacitor_evidence.tex
"""
from __future__ import annotations

import json
import os
import math
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
import sys as _sys                                                     # noqa: E402
for _p in ("scripts", "scripts/phase0nw", "Scalable_Integrated_VR/src"):
    if str(R / _p) not in _sys.path:
        _sys.path.insert(0, str(R / _p))
import design_record as DR                                             # noqa: E402
import HVR_FULL_OPT_EPC_V2 as H                                        # noqa: E402
TR = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
OUT = TR / "capacitor_evidence.json"
TAB = Path(os.environ.get("ETM_RESULTS_ROOT") or R) / "manuscript_v2" / "supplement" / "tab_capacitor_evidence.tex"


def _requirement():
    """C_1 and C_2 of the production design: voltage and the effective capacitance that holds
    the engine's ripple rule, (I_out / N) D / f_sw / C <= CAP_RIPPLE_MAX * V_Ci."""
    n, _k, _ka = DR.topology()
    f = float(DR.get()["f_sw_hz"])
    q = (DR.P_LOAD_W / DR.V_OUT / DR.n_vr() / n) * DR.buck_duty() / f
    req = {}
    for i in (1, 2):
        v = (n - i) * DR.V_IN / n
        req[f"C{i}"] = {"V": v, "C_uF": round(1e6 * q / (H.CAP_RIPPLE_MAX * v), 3)}
    return req


REQ = _requirement()
AREA, DERATE = round(DR.cell_area_mm2(), 2), H.CAP_V_DERATING
T_RULE = H.CAP_T_DESIGN_C
MURATA = "https://www.murata.com/en-us/products/productdetail?partno="


def eff(part, v):
    """Effective capacitance at bias v, at the rule's temperature, less tolerance (vendor data)."""
    cap = H.Capacitor(part, "MLCC", c_uf=1.0, esr_mohm=0, esl_ph=0, v_max=100,
                      footprint_mm2=1.28, source="", vendor_part=part)
    return H.cap_c_eff_uf(cap, v, T_RULE)


def entries():
    fc = json.loads((TR / "flying_caps.json").read_text())
    rows = []
    for part, vr in (("GRM188D72A105KE01", 100.0), ("GRM188D71H105KE01", 50.0)):
        c1, c2 = eff(part, 32.0), eff(part, 16.0)
        rows.append(dict(
            maker="Murata", part=part, status="production", kind="MLCC 0603 X7T",
            C_nom_uF=1.0, V_rated=vr, BV=None, C_eff_uF={"32V": c1, "16V": c2},
            derating="at the rule temperature (105 C), -10 % tolerance (vendor DC-bias and C-T "
                     "at bias)",
            esr_mohm_805kHz=7.8, size_mm=[1.6, 0.8], h_max_um=1000.0,
            n_C1=math.ceil(REQ["C1"]["C_uF"] / c1), n_C2=math.ceil(REQ["C2"]["C_uF"] / c2),
            url=MURATA + part, source="Murata public characteristic data (repository cache)"))
    rows.append(dict(
        maker="Murata", part="GCM21BR71E106KA73", status="published library part; not in the "
        "current Murata catalog", kind="MLCC 0805 X7R", C_nom_uF=10.0, V_rated=25.0, BV=None,
        C_eff_uF={"32V": None, "16V": 2.29}, derating="16-V value: decap survey (same-class "
        "equivalent)", esr_mohm_805kHz=3.25, size_mm=[2.0, 1.25], h_max_um=1250.0,
        n_C1=None, n_C2=1, url="https://www.murata.com", source="flying_caps.json"))
    rows.append(dict(
        maker="Murata", part="GRM31CR71H226KE08", status="published library entry; not found in "
        "the Murata catalog (largest 1206 50-V X7R: 4.7 uF)", kind="MLCC 1206 X7R",
        C_nom_uF=22.0, V_rated=50.0, BV=None, C_eff_uF={"32V": None, "16V": None},
        derating="not published", esr_mohm_805kHz=None, size_mm=[3.2, 1.6], h_max_um=None,
        n_C1=None, n_C2=None, url="https://www.murata.com", source="flying_cap_vendor_data.json"))
    for part, bv, vr in (("935146050510", 100.0, 32.0), ("935146831510", 30.0, 16.0)):
        n1 = math.ceil(REQ["C1"]["C_uF"] / 0.009) if vr * DERATE >= 32 else None
        rows.append(dict(
            maker="Murata", part=part, status="production (WLSC silicon)", kind="silicon, 100 um",
            C_nom_uF=0.010, V_rated=vr, BV=bv, C_eff_uF={"32V": 0.009 if vr >= 32 else None,
                                                        "16V": 0.009},
            derating="no DC-bias dependence; -10 % tolerance", esr_mohm_805kHz=None,
            size_mm=[0.8, 0.8], h_max_um=100.0, n_C1=n1,
            n_C2=math.ceil(REQ["C2"]["C_uF"] / 0.009),
            url="https://www.murata.com/en-us/products/capacitor/siliconcapacitors/overview/"
                "lineup/wlsc",
            source="Murata WLSC line-up; rated voltage per Murata FAQ "
                   "(https://www.murata.com/support/faqs/capacitor/siliconcapacitors/qlty/0001)"))
    rows.append(dict(
        maker="TDK", part="CGB series (low profile)", status="production", kind="MLCC, 0.22 mm max",
        C_nom_uF=1.0, V_rated=6.3, BV=None, C_eff_uF={"32V": None, "16V": None},
        derating="not applicable (rating)", esr_mohm_805kHz=None, size_mm=None, h_max_um=220.0,
        n_C1=None, n_C2=None,
        url="https://product.tdk.com/en/catalog/datasheets/mlcc_commercial_lowprofile_en.pdf",
        source="TDK low-profile MLCC catalogue (4-6.3 V for the 0.22-mm variants)"))
    rows.append(dict(
        maker="ELSPES", part="deep-trench silicon capacitors", status="research / early product",
        kind="silicon, ~70 um", C_nom_uF=None, V_rated=None, BV=5.0,
        C_eff_uF={"32V": None, "16V": None}, derating="not applicable (breakdown 4-5 V)",
        esr_mohm_805kHz=None, size_mm=None, h_max_um=70.0, n_C1=None, n_C2=None,
        url="https://elspes.com/products/decoupling", source="ELSPES product page"))
    rows.append(dict(
        maker="Murata", part="custom 3-D silicon capacitor / IPD", status="custom (research "
        "candidate)", kind="silicon, configurable thickness", C_nom_uF=None, V_rated=None, BV=None,
        C_eff_uF={"32V": None, "16V": None}, derating="catalogue maxima of capacitance, voltage "
        "and thickness are stated independently; not shown to be achievable together",
        esr_mohm_805kHz=None, size_mm=None, h_max_um=None, n_C1=None, n_C2=None,
        url="https://www.murata.com/-/media/webrenewal/products/capacitor/siliconcapacitors/pdf/"
            "silicon-capacitors-catalog-rev16.ashx", source="Murata silicon capacitor catalogue"))
    for c in fc.get("candidates", {}).values() if isinstance(fc.get("candidates"), dict) else []:
        pass
    for r in rows:
        r.update(verdict(r))
    return rows


def verdict(r):
    v1 = r["V_rated"] is not None and r["V_rated"] * DERATE >= REQ["C1"]["V"]
    v2 = r["V_rated"] is not None and r["V_rated"] * DERATE >= REQ["C2"]["V"]
    area = None
    if r.get("n_C1") and r.get("n_C2") and r.get("size_mm"):
        area = (r["n_C1"] + r["n_C2"]) * r["size_mm"][0] * r["size_mm"][1]
    fits = area is not None and area <= AREA
    h = r.get("h_max_um")
    return {"rating_C1_ok": v1, "rating_C2_ok": v2, "area_mm2_C1_C2": area, "area_ok": fits,
            "meets_100um": bool(v1 and fits and h is not None and h <= 100.0),
            "meets_150um": bool(v1 and fits and h is not None and h <= 150.0),
            "meets_without_height": bool(v1 and fits)}


def _t(s):
    """Plain catalogue text as LaTeX (units, ranges, special characters)."""
    s = str(s)
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")):
        s = s.replace(a, b)
    s = re.sub(r"(?<=\d)\s?uF\b", r"~\\textmu F", s)
    s = re.sub(r"(?<=\d)\s?um\b", r"~\\textmu m", s)
    return re.sub(r"(?<=\d)-(?=\d)", "--", s)


def latex(rows, not_covered=()):
    """The evidence matrix as a captioned longtable (label tab:supp-capev) with its note and
    sources, for the supplement."""
    def f(x, d=2):
        return "--" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))
    head = [rf"Part & Status & Rated V (BV) & $C_{{\mathrm{{eff}}}}$ at "
            rf"{REQ['C1']['V']:g}/{REQ['C2']['V']:g}~V, {T_RULE:g}\,$^\circ$C (\textmu F) & "
            r"Size, maximum height & Parts, area & Verdict \\"]
    L = [r"% GENERATED by scripts/tcpmt_capacitor_evidence.py -- do not edit",
         r"\begingroup\footnotesize\setlength{\tabcolsep}{3pt}",
         r"\begin{longtable}{@{}L{3.2cm}L{3.4cm}L{1.3cm}L{1.6cm}L{2.0cm}L{1.5cm}L{3.5cm}@{}}",
         r"\caption{Flying-capacitor evidence matrix}\label{tab:supp-capev}\\",
         r"\toprule", *head, r"\midrule", r"\endfirsthead",
         r"\multicolumn{7}{@{}l}{\emph{Table~\ref{tab:supp-capev} (continued)}}\\",
         r"\toprule", *head, r"\midrule", r"\endhead",
         r"\midrule", r"\multicolumn{7}{r@{}}{\emph{continued on next page}}\\", r"\endfoot",
         r"\bottomrule", r"\endlastfoot"]
    for r in rows:
        size = ("--" if not r.get("size_mm") else
                f"{r['size_mm'][0]}$\\times${r['size_mm'][1]}~mm") + \
            (f", {r['h_max_um']:.0f}~\\textmu m" if r.get("h_max_um") else "")
        parts = "--" if r.get("area_mm2_C1_C2") is None else \
            f"{r['n_C1']}+{r['n_C2']}, {r['area_mm2_C1_C2']:.1f}~mm$^2$"
        vr = ("--" if r["V_rated"] is None else f"{r['V_rated']:g}") + \
            (f" ({r['BV']:.0f})" if r.get("BV") else "")
        if r["meets_100um"]:
            ver = "meets all"
        elif r["meets_without_height"]:
            ver = "rating, capacitance and area met; fails the 100/150-\\textmu m height"
        elif r["V_rated"] is None and not r.get("BV"):
            ver = "no voltage rating published"
        elif not r["rating_C1_ok"]:
            ver = "fails the $C_1$ rating"
        elif r["C_eff_uF"].get("32V") is None:
            ver = "effective capacitance not published"
        else:
            ver = "fails capacitance or area"
        L.append(f"{_t(r['maker'])} {_t(r['part'])} & {_t(r['status'])} & {vr} & "
                 f"{f(r['C_eff_uF']['32V'], 3)}/{f(r['C_eff_uF']['16V'], 3)} & {size} & {parts} & "
                 f"{ver} \\\\")
    L += [r"\end{longtable}"]
    makers = list(dict.fromkeys(r["maker"] for r in rows))
    req = (f"Requirement per cell: $C_1$ at {REQ['C1']['V']:g}~V and $C_2$ at "
           f"{REQ['C2']['V']:g}~V, rated voltage times {DERATE:g} covering the stress; effective "
           f"capacitance at bias, {T_RULE:g}\\,$^\\circ$C and tolerance of at least "
           f"{REQ['C1']['C_uF']:g}~\\textmu F ($C_1$) and {REQ['C2']['C_uF']:g}~\\textmu F "
           f"($C_2$) for {100 * H.CAP_RIPPLE_MAX:g}\\,\\% ripple, the synthesis rule of the "
           f"design point ($M = {DR.n_vr()}$, {float(DR.get()['f_sw_hz']) / 1e3:.0f}~kHz); "
           f"both capacitors within the {AREA:g}-mm$^2$ cell; height judged against the "
           r"100-\textmu m tier of the thin-capacitor sensitivity and against 150~\textmu m. "
           r"Parts, area: parts needed for $C_1$ and $C_2$ and their footprint. ")
    if not any(r["meets_100um"] or r["meets_150um"] for r in rows):
        req += (r"No part meets the 100-\textmu m or the 150-\textmu m height together with the "
                r"voltage, capacitance and area requirements. ")
    req += ("The search covered the parts of " + ", ".join(makers[:-1]) +
            (" and " if len(makers) > 1 else "") + makers[-1] + " listed above")
    if not_covered:
        nc = list(not_covered)
        req += ("; the catalogs of " + ", ".join(nc[:-1]) + (" and " if len(nc) > 1 else "") +
                nc[-1] + " were not part of it")
    L += [r"\nopagebreak\noindent " + req + r".\par", r"\smallskip",
          r"\noindent Sources:", r"{\raggedright", r"\begin{itemize}"]
    L += [f"\\item {_t(r['maker'])} {_t(r['part'])}: \\url{{{r['url']}}}" for r in rows]
    L += [r"\end{itemize}\par}", r"\endgroup", r"\medskip"]
    return L


def main():
    rows = entries()
    out = {"requirement": REQ, "area_mm2": AREA, "derating": DERATE, "rows": rows,
           "any_meets_100um": any(r["meets_100um"] for r in rows),
           "any_meets_150um": any(r["meets_150um"] for r in rows),
           "best_real_fallback": "Murata GRM188D72A105KE01 (0603, 1 uF, 100 V, X7T)",
           "not_covered": ["Samsung Electro-Mechanics", "Taiyo Yuden", "Kyocera AVX", "Vishay"],
           "inaccessible": ["TDK product pages (automated)", "Mouser", "Digi-Key"]}
    OUT.write_text(json.dumps(out, indent=1, default=float))
    TAB.write_text("\n".join(latex(rows, out["not_covered"])) + "\n")
    for r in rows:
        print(r["part"], r["V_rated"], r["C_eff_uF"], r.get("area_mm2_C1_C2"), r["meets_150um"],
              r["meets_without_height"])


if __name__ == "__main__":
    main()
