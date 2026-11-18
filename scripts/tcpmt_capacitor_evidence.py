"""Flying-capacitor evidence matrix (TCPMT revision, Option A).

Requirement per cell (N3K3K_A2, 48 V, 805 kHz): C1 at 32 V and C2 at 16 V; rated voltage x 0.8
must cover the stress; effective capacitance at bias, temperature and tolerance >= 0.19 uF (C1)
and >= 0.38 uF (C2) for 10 % ripple; both capacitors within the 5.61-mm2 cell; heights judged
against 100 um (reference tier, case A0) and 150 um.

Every entry rests on manufacturer data already in the repository (Murata public characteristic
data: research/tcpmt_revision/capacitor_datasheet_data.json, flying_cap_vendor_data.json;
the decap survey: flying_caps.json) or on the manufacturer pages cited. Effective capacitance
is "not published" where no vendor curve was obtained. Manufacturers not covered are listed.

    python tcpmt_capacitor_evidence.py   -> research/tcpmt_revision/capacitor_evidence.json
                                            manuscript_v2/supplement/tab_capacitor_evidence.tex
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
TR = R / "research" / "tcpmt_revision"
OUT = TR / "capacitor_evidence.json"
TAB = R / "manuscript_v2" / "supplement" / "tab_capacitor_evidence.tex"
REQ = {"C1": {"V": 32.0, "C_uF": 0.19}, "C2": {"V": 16.0, "C_uF": 0.38}}
AREA, DERATE = 5.61, 0.8
MURATA = "https://www.murata.com/en-us/products/productdetail?partno="


def eff(part, v):
    import sys
    sys.path.insert(0, str(R / "Scalable_Integrated_VR" / "src"))
    import HVR_FULL_OPT_EPC_V2 as H
    cap = H.Capacitor(part, "MLCC", c_uf=1.0, esr_mohm=0, esl_ph=0, v_max=100,
                      footprint_mm2=1.28, source="", vendor_part=part)
    return min(H.cap_c_eff_uf(cap, v, t) for t in (25.0, 105.0, 125.0))


def entries():
    fc = json.loads((TR / "flying_caps.json").read_text())
    rows = []
    for part, vr in (("GRM188D72A105KE01", 100.0), ("GRM188D71H105KE01", 50.0)):
        c1, c2 = eff(part, 32.0), eff(part, 16.0)
        rows.append(dict(
            maker="Murata", part=part, status="production", kind="MLCC 0603 X7T",
            C_nom_uF=1.0, V_rated=vr, BV=None, C_eff_uF={"32V": c1, "16V": c2},
            derating="worst of 25/105/125 C, -10 % tolerance (vendor DC-bias and C-T at bias)",
            esr_mohm_805kHz=7.8, size_mm=[1.6, 0.8], h_max_um=1000.0,
            n_C1=math.ceil(REQ["C1"]["C_uF"] / c1), n_C2=math.ceil(REQ["C2"]["C_uF"] / c2),
            url=MURATA + part, source="Murata public characteristic data (repository cache)"))
    rows.append(dict(
        maker="Murata", part="GCM21BR71E106KA73", status="published library part; not in the "
        "current Murata catalogue", kind="MLCC 0805 X7R", C_nom_uF=10.0, V_rated=25.0, BV=None,
        C_eff_uF={"32V": None, "16V": 2.29}, derating="16-V value: decap survey (same-class "
        "equivalent)", esr_mohm_805kHz=3.25, size_mm=[2.0, 1.25], h_max_um=1250.0,
        n_C1=None, n_C2=1, url="https://www.murata.com", source="flying_caps.json"))
    rows.append(dict(
        maker="Murata", part="GRM31CR71H226KE08", status="published library entry; not found in "
        "the Murata catalogue (largest 1206 50-V X7R: 4.7 uF)", kind="MLCC 1206 X7R",
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
    head = [r"Part & Status & Rated V (BV) & $C_{\mathrm{eff}}$ at 32/16~V (\textmu F) & "
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
           f"capacitance at bias, temperature and tolerance of at least {REQ['C1']['C_uF']:g}~"
           f"\\textmu F ($C_1$) and {REQ['C2']['C_uF']:g}~\\textmu F ($C_2$) for 10\\,\\% "
           f"ripple; both capacitors within the {AREA:g}-mm$^2$ cell; height judged against "
           r"100~\textmu m (the reference tier, case~A0) and 150~\textmu m. Parts, area: parts "
           r"needed for $C_1$ and $C_2$ and their footprint. ")
    if not any(r["meets_100um"] or r["meets_150um"] for r in rows):
        req += (r"No part meets the 100-\textmu m or the 150-\textmu m height together with the "
                r"voltage, capacitance and area requirements. ")
    req += ("The search covered the parts of " + ", ".join(makers[:-1]) +
            (" and " if len(makers) > 1 else "") + makers[-1] + " listed above")
    if not_covered:
        nc = list(not_covered)
        req += ("; the catalogues of " + ", ".join(nc[:-1]) + (" and " if len(nc) > 1 else "") +
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
