"""TCPMT revision -- capacitor datasheet data for the input decoupling and the flying caps.

Every number used for a real part comes from the manufacturer's own characteristic data,
fetched from Murata's public product-information API (the JSON behind the SimSurfing charts
on pim.murata.com; generic client, no personal data) and cached, extracted, in
research/tcpmt_revision/capacitor_datasheet_data.json so the analysis reruns offline:

  spec      size, thickness (nominal and max), rated voltage, dielectric class,
            operating-temperature range, production status
  dc_bias   capacitance vs DC bias (25 C, the chart's own AC level)
  c_temp    capacitance vs temperature at 0 V and at the working bias, when Murata has it
  esr / z   R(f) and |Z|(f) at the working DC bias (25 C)

Silicon capacitors come from the same API's catalogue (spec only: Murata publishes no
DC-bias curve for them; their capacitance is voltage-stable by construction, a vendor claim
recorded as such).

    python tcpmt_decap_parts.py --fetch      refresh the cache from the API
    python tcpmt_decap_parts.py              print the summary table from the cache
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision"
CACHE = OUT / "capacitor_datasheet_data.json"
API = "https://pimapi.murata.com/public/api/pim/v1"
HDR = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
       "Origin": "https://pim.murata.com", "Referer": "https://pim.murata.com/"}
PRODUCT_URL = "https://www.murata.com/en-us/products/productdetail?partno={pn}%23"

#: role -> (working DC bias V, candidate parts). Input decoupling sees 48 V; the flying
#: capacitors hold 32 V (C1) and 16 V (C2) (manuscript Fig. 2, fig_converter.py).
CANDIDATES = {
    "input_48V": (48.0, [
        "GRM155R62A104KE14#",      # 0402 0.1 uF 100 V X5R  (85 C: reference only)
        "GRM155R72A472KA01#",      # 0402 4.7 nF 100 V X7R  (largest 0402 100 V >= 125 C)
        "GRM188R72A104KA35#",      # 0603 0.1 uF 100 V X7R
        "GRM188D72A105KE01#",      # 0603 1 uF 100 V X7T
        "GRM21BR72A474KA73#",      # 0805 0.47 uF 100 V X7R
        "GRM21BC72A105KE01#",      # 0805 1 uF 100 V X7S
        "GRM21BD72A225KE01#",      # 0805 2.2 uF 100 V X7T
        "GRM31CR72A105KA01#",      # 1206 1 uF 100 V X7R
        "GRM31CC72A475KE11#",      # 1206 4.7 uF 100 V X7S
        "GRM32EC72A106KE05#",      # 1210 10 uF 100 V X7S (2.5 mm: too tall, reference)
    ]),
    "flying_C1_32V": (32.0, [
        "GRM155R71H104KE14#",      # 0402 0.1 uF 50 V X7R
        "GRM155C71H104JE19#",      # 0402 0.1 uF 50 V X7S
        "GRM155D71H224KE01#",      # 0402 0.22 uF 50 V X7T
        "GCM188R71H224KA64#",      # 0603 0.22 uF 50 V X7R
        "GRM188D71H105KE01#",      # 0603 1 uF 50 V X7T
        "GRM21BD71H225KE01#",      # 0805 2.2 uF 50 V X7T
        "GRM21BC71H475KE11#",      # 0805 4.7 uF 50 V X7S
        "GRM188D72A105KE01#",      # 0603 1 uF 100 V X7T (100 V option for C1)
    ]),
    "flying_C2_16V": (16.0, [
        "GRM155D71E224KE01#",      # 0402 0.22 uF 25 V X7T
        "GRM155D71E105KE11#",      # 0402 1 uF 25 V X7T
        "GRM188R7YA474KE05#",      # 0603 0.47 uF 35 V X7R
        "GRM188C71E225KE11#",      # 0603 2.2 uF 25 V X7S
        "GRM21BC7YA475KE11#",      # 0805 4.7 uF 35 V X7S
        "GRM21BC71E106KE01#",      # 0805 10 uF 25 V X7S (the synthesis' 10 uF/25 V class)
        "GRM188D71H105KE01#",      # 0603 1 uF 50 V X7T (50 V option for C2)
    ]),
}
#: the synthesis' own selection (HVR_FULL_OPT_EPC_V2 capacitor library)
SYNTHESIS_PART = "GCM21BR71E106KA73"
TEMPS_C = (85.0, 105.0, 125.0)


# ------------------------------------------------------------------ API
def _post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=HDR,
                                 method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def _search(pn, cat="ceramicCapacitorSMD", exact=True, page=1, size=100):
    body = {"searchCondClass": 3 if exact else 2, "partNum": pn, "page": page,
            "pageSize": size, "productCategoryId": cat, "languageRegion": "en-us",
            "series": "", "sortKey": "", "valSearchCondList": [],
            "rangeValSearchCondList": [], "dateRangeSearchCondList": [],
            "advancedSearchCalculatedCondList": []}
    return _post("/products/search", body).get("productSearchResult") or []


def _flat(p):
    return {it["id"]: [v["displayName"] or v["value"] for v in it["valueList"]
                       if (v["displayName"] or v["value"])] for it in p["itemInfoList"]}


def _chara(pn, ctype, **par):
    par.setdefault("supply_status", "B")
    req = {"ReqType": "Characteristics", "languageRegion": "en-us",
           "ReqChara": [{"partnumber": pn, "chara_type": ctype, "parameter": par,
                         "WorkInfo": {"color": "#EA002A", "line_dash": ""}}]}
    r = _post("/characteristics/characteristics", req)
    cd = (r.get("JsonCharaData") or [{}])[0].get("charadata") or [{}]
    s = cd[0]
    if "data" not in s:
        return None, s.get("error", "no data")
    return s, ""


def _curve(s, cols=(0, 1)):
    return [[float(p[c][0]) for c in cols] for p in s["data"]]


#: the charts give capacitance in the unit of 'y_subunit_plot' (u, n or p farad)
_TO_UF = {"u": 1.0, "n": 1e-3, "p": 1e-6, "m": 1e3, "": 1e6}


def _cap_scale(s):
    sub = str(s.get("y_subunit_plot", "u") or "")
    if sub not in _TO_UF:
        raise ValueError(f"unknown capacitance unit {sub!r}")
    return _TO_UF[sub]


def fetch_part(pn, bias):
    rec = {"part": pn.rstrip("#"), "url": PRODUCT_URL.format(pn=pn.rstrip("#")),
           "data_source": f"{API}/characteristics/characteristics (Murata SimSurfing data)",
           "working_bias_V": bias}
    hits = _search(pn)
    if not hits:
        rec["error"] = "not found"
        return rec
    d = _flat(hits[0])
    g = lambda k: (d.get(k) or [None])[0]
    rec["spec"] = {"capacitance": g("capacitance"), "rated_voltage": g("ratedVoltage"),
                   "dielectric": g("tempChara"), "size_inch": g("sizeCodeInInch"),
                   "LxW_mm": g("lengthxWidth"), "thickness": g("thickness"),
                   "thickness_max": g("thicknessMax"), "operating_temp": g("operaTemp"),
                   "status": g("productionStatus")}
    for ac in (1.0, 0.5):                         # the chart's own AC level
        s, err = _chara(pn, "c_dcbias_capchange_cap", ac=ac)
        if s:
            k = _cap_scale(s)
            rec["dc_bias"] = {"ac_Vrms": ac, "T_C": float(s.get("tc", 25)),
                              "unit_in_chart": s.get("y_subunit_plot"),
                              "V_change_pct_C_uF": [[float(p[0][0]), float(p[1][0]),
                                                     float(p[2][0]) * k] for p in s["data"]]}
            break
    rec["c_temp"] = {}
    for dc in sorted({0.0, bias}):
        for ac in (1.0, 0.5):
            s, err = _chara(pn, "c_temp_capchange_cap", ac=ac, dc=dc)
            if s:
                rec["c_temp"][f"{dc:g}V"] = {"ac_Vrms": ac,
                                             "T_C_change_pct": _curve(s, (0, 1))}
                break
    rec["dc_bias_hot"] = {}
    for t in TEMPS_C:
        for ac in (1.0, 0.5):
            s, err = _chara(pn, "c_dcbias_capchange_cap", ac=ac, tc=t)
            if s:
                k = _cap_scale(s)
                rec["dc_bias_hot"][f"{t:g}C"] = [[float(p[0][0]), float(p[2][0]) * k]
                                                 for p in s["data"]]
                break
    for ctype in ("r", "z"):
        for dc in (bias, 0.0):
            s, err = _chara(pn, ctype, dc=dc, tc=25)
            if s:
                rec[ctype] = {"dc_V": dc, "T_C": 25.0, "f_MHz_ohm": _curve(s, (0, 1))}
                break
    if "dc_bias" in rec:                          # unit sanity: C(0 V) ~ nominal
        ratio = rec["dc_bias"]["V_change_pct_C_uF"][0][2] / c_nominal_uf(rec)
        rec["check_C0_over_nominal"] = ratio
        if not 0.7 < ratio < 1.4:
            raise RuntimeError(f"{pn}: C(0 V)/nominal = {ratio:.3g} -- unit error?")
    return rec


def fetch_silicon():
    out = []
    for page in range(1, 6):
        res = _search("935", cat="siliconCapacitor", exact=False, page=page)
        for p in res:
            d = _flat(p)
            g = lambda k: (d.get(k) or [None])[0]
            out.append({"part": g("partNum"), "series": g("series"),
                        "capacitance": g("capacitanceLabel"),
                        "rated_voltage": g("withstandingVoltage"), "LxW_mm": g("lengthxWidth"),
                        "thickness": g("thickness"), "operating_temp": g("operaTemp"),
                        "status": g("productionStatus"), "features": g("productFeatures")})
        if len(res) < 100:
            break
    return out


def fetch_all():
    data = {"source": "Murata public PIM API (pim.murata.com), fetched by "
                      "scripts/tcpmt_decap_parts.py --fetch",
            "parts": {}, "silicon_catalogue": fetch_silicon()}
    for role, (bias, pns) in CANDIDATES.items():
        for pn in pns:
            key = pn.rstrip("#")
            if key in data["parts"]:
                rec = data["parts"][key]
                rec["roles"].append(role)
                for ctype in ("r", "z"):             # the second role's own bias
                    s, err = _chara(pn, ctype, dc=bias, tc=25)
                    if s:
                        rec.setdefault(f"{ctype}_by_bias", {})[f"{bias:g}V"] = \
                            _curve(s, (0, 1))
                continue
            print("fetching", pn, role, flush=True)
            rec = fetch_part(pn, bias)
            rec["roles"] = [role]
            data["parts"][key] = rec
    hits = _search(SYNTHESIS_PART + "#") or _search(SYNTHESIS_PART, exact=False)
    data["synthesis_part"] = {"part": SYNTHESIS_PART, "found_in_murata_catalogue": bool(hits),
                              "note": "the HVR_FULL_OPT_EPC_V2 library entry"}
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=0))
    fetch_temp_rise()                             # the recommended ring part's self-heating
    compact()
    return load()


def fetch_temp_rise(pn="GRM31CC72A475KE11#"):
    """Murata's self-heating curves (temperature rise vs ripple current at 100 kHz, 500 kHz,
    1 MHz) for one part, merged into the cache."""
    req = {"ReqType": "Characteristics", "languageRegion": "en-us",
           "ReqChara": [{"partnumber": pn, "chara_type": "temp_rise",
                         "parameter": {"supply_status": "B"},
                         "WorkInfo": {"color": "#EA002A", "line_dash": ""}}]}
    r = _post("/characteristics/characteristics", req)
    curves = {}
    for s in (r.get("JsonCharaData") or [{}])[0].get("charadata") or []:
        if "data" in s:
            curves[s.get("caption2", "")] = _curve(s, (0, 1))
    data = json.loads(CACHE.read_text())
    data["parts"][pn.rstrip("#")]["temp_rise_A_rms_K"] = curves
    CACHE.write_text(json.dumps(data, separators=(",", ":")))
    _LOADED.clear()
    return curves


def self_heating_K(rec, i_rms_a, freq="1MHz"):
    d = np.array(rec["temp_rise_A_rms_K"][freq])
    return float(np.interp(i_rms_a, d[:, 0], d[:, 1], left=d[0, 1] * (i_rms_a / d[0, 0]) ** 2))


def compact(sig=5):
    """Round every float in the cache to `sig` significant digits and shorten the silicon
    feature text (the cache is data for reruns, not a datasheet mirror)."""
    def rnd(x):
        if isinstance(x, float):
            return float(f"{x:.{sig}g}")
        if isinstance(x, list):
            return [rnd(v) for v in x]
        if isinstance(x, dict):
            return {k: rnd(v) for k, v in x.items()}
        return x
    data = json.loads(CACHE.read_text())
    for s in data.get("silicon_catalogue", []):
        f = s.get("features") or ""
        s["features"] = " ".join(f.split())[:160]
    CACHE.write_text(json.dumps(rnd(data), separators=(",", ":")))
    _LOADED.clear()


# ------------------------------------------------------------------ evaluation helpers
_LOADED = {}


def load():
    if "d" not in _LOADED:
        _LOADED["d"] = json.loads(CACHE.read_text())
    return _LOADED["d"]


def _num(s, unit_scale=None):
    import re
    m = re.search(r"([0-9.]+)", str(s).replace(",", ""))
    return float(m.group(1)) if m else float("nan")


def dims_mm(rec):
    """(L, W, T_nom, T_max) in mm."""
    sp = rec["spec"]
    L, W = (float(x) for x in sp["LxW_mm"].replace("mm", "").split("×"))
    return L, W, _num(sp["thickness"]), _num(sp["thickness_max"])


def rated_v(rec):
    return _num(rec["spec"]["rated_voltage"])


def t_max_c(rec):
    return _num(str(rec["spec"]["operating_temp"]).split("～")[-1])


def c_nominal_uf(rec):
    s = rec["spec"]["capacitance"]
    v = _num(s)
    return v * 1e-3 if "nF" in s else v * 1e-6 if "pF" in s else v


def c_at_bias(rec, v):
    """Capacitance (uF) at DC bias v, 25 C, from the manufacturer's curve (never beyond the
    curve's last point, which is the rated voltage)."""
    d = np.array(rec["dc_bias"]["V_change_pct_C_uF"])
    if v > d[-1, 0] + 1e-9:
        raise ValueError(f"{rec['part']}: {v} V is beyond its rated curve ({d[-1, 0]} V)")
    return float(np.interp(v, d[:, 0], d[:, 2]))


def temp_factor(rec, v, t_c):
    """C(T)/C(25 C) at bias v: the hot DC-bias curve if Murata has one at t_c, else the
    C-temperature curve at the working bias, else at 0 V (conservative for X7R/X7S: the
    bias flattens the temperature dependence), else None."""
    hot = rec.get("dc_bias_hot", {})
    if hot:
        ts = sorted(float(k[:-1]) for k in hot)
        t_use = min(ts, key=lambda t: abs(t - t_c))
        if abs(t_use - t_c) <= 10.0:
            d = np.array(hot[f"{t_use:g}C"])
            return float(np.interp(v, d[:, 0], d[:, 1]) / c_at_bias(rec, v)), \
                f"DC-bias curve at {t_use:g} C"
    ct = rec.get("c_temp", {})
    for key in (f"{v:g}V", "0V"):
        if key in ct:
            d = np.array(ct[key]["T_C_change_pct"])
            f = (1 + np.interp(t_c, d[:, 0], d[:, 1]) / 100.0) / \
                (1 + np.interp(25.0, d[:, 0], d[:, 1]) / 100.0)
            return float(f), f"C-temperature curve at {key}"
    return None, "no temperature data"


def _fcurve(rec, ctype, bias=None):
    if bias is not None and f"{bias:g}V" in rec.get(f"{ctype}_by_bias", {}):
        return np.array(rec[f"{ctype}_by_bias"][f"{bias:g}V"])
    if bias is not None and abs(rec[ctype]["dc_V"] - bias) > 1e-9:
        raise KeyError(f"{rec['part']}: no {ctype}(f) at {bias} V")
    return np.array(rec[ctype]["f_MHz_ohm"])


def esr_at(rec, f_hz, bias=None):
    """R(f) (Ohm) at the given DC bias (default: the record's working bias), log-log
    interpolation of the manufacturer's curve; f may be an array."""
    d = _fcurve(rec, "r", bias)
    return np.exp(np.interp(np.log(np.asarray(f_hz) / 1e6), np.log(d[:, 0]),
                            np.log(d[:, 1])))


def z_at(rec, f_hz, bias=None):
    d = _fcurve(rec, "z", bias)
    return np.exp(np.interp(np.log(np.asarray(f_hz) / 1e6), np.log(d[:, 0]),
                            np.log(d[:, 1])))


def srf_esl(rec, v=None):
    """Self-resonant frequency (|Z| minimum) and the ESL it implies with the capacitance at
    the curve's bias, plus the ESL read from the inductive branch at 3x SRF (a check)."""
    d = np.array(rec["z"]["f_MHz_ohm"])
    i = int(np.argmin(d[:, 1]))
    f0 = d[i, 0] * 1e6
    c = c_at_bias(rec, rec["z"]["dc_V"]) * 1e-6
    esl_srf = 1.0 / ((2 * np.pi * f0) ** 2 * c)
    f3 = 3 * f0
    if f3 / 1e6 < d[-1, 0]:
        z3, r3 = z_at(rec, f3), esr_at(rec, f3)
        x3 = np.sqrt(max(z3 ** 2 - r3 ** 2, 0.0))
        esl_hf = (x3 + 1.0 / (2 * np.pi * f3 * c)) / (2 * np.pi * f3)
    else:
        esl_hf = float("nan")
    return f0, esl_srf, esl_hf


def summary(data=None):
    data = data or load()
    rows = []
    for key, rec in data["parts"].items():
        if "spec" not in rec or "dc_bias" not in rec:
            rows.append({"part": key, "error": rec.get("error", "no dc-bias data")})
            continue
        v = rec["working_bias_V"]
        L, W, T, Tm = dims_mm(rec)
        row = {"part": key, "roles": rec["roles"], "C_nom_uF": c_nominal_uf(rec),
               "V_rated": rated_v(rec), "dielectric": rec["spec"]["dielectric"],
               "T_max_C": t_max_c(rec), "L_mm": L, "W_mm": W, "T_mm": T, "T_max_mm": Tm}
        for vb in sorted({16.0, 32.0, 48.0}):
            try:
                row[f"C_{vb:g}V_uF"] = c_at_bias(rec, vb)
            except ValueError:
                row[f"C_{vb:g}V_uF"] = None
        if "r" in rec:
            row["esr_bias_V"] = rec["r"]["dc_V"]
            for f in (805e3, 1.61e6, 5e6, 10e6):
                row[f"ESR_{f / 1e6:g}MHz_mohm"] = esr_at(rec, f) * 1e3
        if "z" in rec:
            f0, esl, esl_hf = srf_esl(rec)
            row.update({"SRF_MHz": f0 / 1e6, "ESL_pH_from_SRF": esl * 1e12,
                        "ESL_pH_from_3xSRF": esl_hf * 1e12})
        rows.append(row)
    return rows


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch_all()
    for r in summary():
        print(json.dumps(r, default=lambda x: round(x, 4) if isinstance(x, float) else x))
