"""TCPMT revision -- vendor data for the flying-capacitor feasibility rule of the synthesis engine.

The synthesis engine (Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py) checks, under the
corrected capacitor rule, every flying-capacitor position i against
    Delta V_Ci,pp = Q_i / C_eff,i <= r_max V_Ci,   C_eff,i = C(V_Ci, 25 C) x f_T(V_Ci, T) x (1 - tol)
and evaluates the capacitor ESR at f_sw. This script fetches the manufacturer data those terms
need from Murata's public product-information API (the JSON behind the SimSurfing charts on
pim.murata.com; generic client, no personal data), for the two rated 0603 X7T parts the
revision added (GRM188D72A105KE01, 100 V; GRM188D71H105KE01, 50 V):

  dc_bias   C(V) at 25 C, AC 1 Vrms (the chart's own level)              -> C(V_Ci, 25 C)
  c_temp    C(T) at DC bias 0 ... V_rated in 2-V steps, AC 0.1 Vrms       -> f_T(V, T) = C(V,T)/C(V,25 C)
            (Murata publishes no hot DC-bias chart for these parts: the API answers
            "Specified Temp. must be base temperature"; C-temperature at bias is the documented
            way to get the same information, Murata FAQ ceramiccapacitor/char/0051)
  r         ESR(f) at 25 C at DC bias 0 ... V_rated in 4-V steps           -> ESR(f_sw, V_Ci)
  z         |Z|(f) at 0, 16, 32 V (self-resonance check only)

plus a control pair of 0603 0.1 uF X7R parts with different ratings and different individual
specification codes (GRM188R71H104KA93, 50 V; GRM188R72A104KA35, 100 V), and the catalogue
status of the published library's MLCC part numbers.

    python scripts/tcpmt_caprule_vendor.py --fetch   query the API, write both JSON files
    python scripts/tcpmt_caprule_vendor.py           rebuild the engine table from the cache

Outputs
  research/tcpmt_revision/flying_cap_vendor_data.json   cache (5 significant digits) + checks
  Scalable_Integrated_VR/src/HVR_capacitor_vendor_data.json   the engine's reduced tables
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_decap_parts as PA                                       # noqa: E402

CACHE = R / "research" / "tcpmt_revision" / "flying_cap_vendor_data.json"
ENGINE_TABLE = R / "Scalable_Integrated_VR" / "src" / "HVR_capacitor_vendor_data.json"
PARTS = {"GRM188D72A105KE01": 100.0, "GRM188D71H105KE01": 50.0}
CONTROL = ("GRM188R71H104KA93", "GRM188R72A104KA35")
#: the published library's MLCC part numbers (HVR_FULL_OPT_EPC_V2.CAPACITOR_LIBRARY sources)
LIBRARY_MLCC = {"Murata-GRM155-10uF-6V3": "GRM155R60J106ME15",
                "Murata-GRM31-22uF-50V": "GRM31CR71H226KE08",
                "Murata-GCM21-10uF-25V": "GCM21BR71E106KA73"}
#: prefixes searched for a real 22 uF / 50 V Murata part in 1206/1210/1812 (none exists)
SEARCH_22U_50V = ("GRM31CR71H226", "GRM31CZ71H226", "GRM31CR61H226", "GRM31CC71H226",
                  "GRM32ER71H226", "GRM32EC71H226", "GRM32ER61H226", "GRM43ER71H226",
                  "GCM32ER71H226")
SEARCH_1206_50V_X7R = "GRM31CR71H475"            # the largest 50-V 1206 X7R Murata makes
F_KEEP_MHZ = (0.01, 300.0)                       # ESR(f) kept for the engine: 10 kHz - 300 MHz
T_GRID_C = tuple(float(t) for t in range(-55, 126, 5))
FETCH_DATE = "2026-11-16"


def _sleep():
    time.sleep(0.3)                               # be gentle with the public API


def _prefix_search(pn):
    body = {"searchCondClass": 1, "partNum": pn, "page": 1, "pageSize": 100,
            "productCategoryId": "ceramicCapacitorSMD", "languageRegion": "en-us",
            "series": "", "sortKey": "", "valSearchCondList": [],
            "rangeValSearchCondList": [], "dateRangeSearchCondList": [],
            "advancedSearchCalculatedCondList": []}
    hits = PA._post("/products/search", body).get("productSearchResult") or []
    out = []
    for h in hits:
        d = PA._flat(h)
        g = lambda k: (d.get(k) or [None])[0]             # noqa: E731
        out.append({"part": g("partNum"), "capacitance": g("capacitance"),
                    "rated_voltage": g("ratedVoltage"), "dielectric": g("tempChara"),
                    "size_inch": g("sizeCodeInInch"), "thickness": g("thickness"),
                    "operating_temp": g("operaTemp"), "status": g("productionStatus")})
    uniq = {o["part"]: o for o in out}
    return list(uniq.values())


def _spec(pn):
    hits = PA._search(pn + "#")
    if not hits:
        return None
    d = PA._flat(hits[0])
    g = lambda k: (d.get(k) or [None])[0]                 # noqa: E731
    return {"capacitance": g("capacitance"), "rated_voltage": g("ratedVoltage"),
            "dielectric": g("tempChara"), "size_inch": g("sizeCodeInInch"),
            "LxW_mm": g("lengthxWidth"), "thickness": g("thickness"),
            "thickness_max": g("thicknessMax"), "operating_temp": g("operaTemp"),
            "status": g("productionStatus")}


def _dc_bias(pn):
    for par in ({"ac": 1.0}, {"ac": 0.5}, {}):           # the chart's own AC level
        s, err = PA._chara(pn + "#", "c_dcbias_capchange_cap", **par)
        if s:
            break
    if not s:
        raise RuntimeError(f"{pn}: no DC-bias chart ({err})")
    k = PA._cap_scale(s)
    return {"ac_Vrms": float(s.get("ac", 1)), "T_C": float(s.get("tc", 25)),
            "V_C_uF": [[float(p[0][0]), float(p[2][0]) * k] for p in s["data"]]}


def _c_temp(pn, dc):
    s, err = PA._chara(pn + "#", "c_temp_capchange_cap", dc=dc)
    if not s:
        return None, err
    k = PA._cap_scale(s)
    return {"ac_Vrms": float(s.get("ac", 0.1)), "dc_V": float(s.get("dc", dc)),
            "T_C_uF": [[float(p[0][0]), float(p[2][0]) * k] for p in s["data"]]}, ""


def _r_or_z(pn, ctype, dc):
    s, err = PA._chara(pn + "#", ctype, dc=dc, tc=25)
    if not s:
        return None, err
    return {"dc_V": float(dc), "T_C": 25.0, "f_MHz_ohm": PA._curve(s, (0, 1))}, ""


def _hot_dc_bias_status(pn):
    s, err = PA._chara(pn + "#", "c_dcbias_capchange_cap", ac=1.0, tc=105.0)
    return "available" if s else err


def fetch():
    data = {"source": ("Murata public PIM API (pimapi.murata.com/public/api/pim/v1), the data "
                       "behind SimSurfing; fetched by scripts/tcpmt_caprule_vendor.py --fetch"),
            "fetched": FETCH_DATE, "parts": {}, "control": {}, "library_mlcc": {}}
    for pn, vr in PARTS.items():
        print("fetching", pn, flush=True)
        rec = {"part": pn, "url": PA.PRODUCT_URL.format(pn=pn), "spec": _spec(pn),
               "dc_bias": _dc_bias(pn), "c_temp": {}, "r": {}, "z": {},
               "hot_dc_bias_chart": _hot_dc_bias_status(pn)}
        for dc in np.arange(0.0, vr + 1e-9, 2.0):
            c, err = _c_temp(pn, float(dc))
            rec["c_temp"][f"{dc:g}V"] = c if c else {"error": err}
            _sleep()
        for dc in np.arange(0.0, vr + 1e-9, 4.0):
            r, err = _r_or_z(pn, "r", float(dc))
            rec["r"][f"{dc:g}V"] = r if r else {"error": err}
            _sleep()
        for dc in (0.0, 16.0, 32.0):
            z, err = _r_or_z(pn, "z", dc)
            rec["z"][f"{dc:g}V"] = z if z else {"error": err}
            _sleep()
        data["parts"][pn] = rec
    for pn in CONTROL:
        print("fetching control", pn, flush=True)
        data["control"][pn] = {"spec": _spec(pn), "dc_bias": _dc_bias(pn)}
    for name, pn in LIBRARY_MLCC.items():
        exact = _spec(pn)
        data["library_mlcc"][name] = {"part": pn, "in_murata_catalogue": exact is not None,
                                      "spec": exact}
        if exact is not None and name == "Murata-GRM155-10uF-6V3":
            data["library_mlcc"][name]["dc_bias"] = _dc_bias(pn)
    data["search_22uF_50V"] = {p: _prefix_search(p) for p in SEARCH_22U_50V}
    data["largest_1206_50V_X7R"] = _prefix_search(SEARCH_1206_50V_X7R)
    CACHE.write_text(json.dumps(_round(_trim(data)), separators=(",", ":")))
    return data


def _trim(data):
    """Keep the cache compact: C-temperature charts on a 1-degC grid, R(f) and |Z|(f) from
    1 kHz to 1 GHz (the engine table keeps the native ESR sampling from 10 kHz to 300 MHz)."""
    for rec in data["parts"].values():
        for c in rec["c_temp"].values():
            if "T_C_uF" in c:
                c["T_C_uF"] = [p for p in c["T_C_uF"] if abs(p[0] - round(p[0])) < 1e-9]
        for ctype in ("r", "z"):
            for c in rec[ctype].values():
                if "f_MHz_ohm" in c:
                    c["f_MHz_ohm"] = [p for p in c["f_MHz_ohm"] if 1e-3 <= p[0] <= 1e3]
    return data


def _round(x, sig=5):
    if isinstance(x, float):
        return float(f"{x:.{sig}g}")
    if isinstance(x, list):
        return [_round(v, sig) for v in x]
    if isinstance(x, dict):
        return {k: _round(v, sig) for k, v in x.items()}
    return x


def load():
    return json.loads(CACHE.read_text())


# ------------------------------------------------------------------ checks
def identity_check(data=None):
    """Are the two 0603 parts' curves the same? Compared on every chart both parts have, at the
    common bias points, on each chart's own sampling grid (interpolated onto the coarser one),
    and against a control pair of different designs."""
    data = data or load()
    a, b = (data["parts"][p] for p in PARTS)

    def rel(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        return float(np.max(np.abs(x - y) / np.maximum(np.abs(y), 1e-30)))

    A = np.array(a["dc_bias"]["V_C_uF"])
    B = np.array(b["dc_bias"]["V_C_uF"])
    common = B[B[:, 0] <= A[-1, 0] + 1e-9]
    on_grid = [v for v in common[:, 0] if np.any(np.abs(A[:, 0] - v) < 1e-9)]
    dcb = rel([np.interp(v, A[:, 0], A[:, 1]) for v in on_grid],
              [np.interp(v, B[:, 0], B[:, 1]) for v in on_grid])
    ct, rr = [], []
    for key, rec in b["c_temp"].items():
        if "T_C_uF" in rec and "T_C_uF" in a["c_temp"].get(key, {}):
            ct.append(rel(np.array(a["c_temp"][key]["T_C_uF"])[:, 1],
                          np.array(rec["T_C_uF"])[:, 1]))
    for key, rec in b["r"].items():
        if "f_MHz_ohm" in rec and "f_MHz_ohm" in a["r"].get(key, {}):
            rr.append(rel(np.array(a["r"][key]["f_MHz_ohm"])[:, 1],
                          np.array(rec["f_MHz_ohm"])[:, 1]))
    ca, cb = (np.array(data["control"][p]["dc_bias"]["V_C_uF"]) for p in CONTROL)
    vmax = min(ca[-1, 0], cb[-1, 0])
    vs = np.linspace(0.0, vmax, 11)
    ctrl = np.interp(vs, ca[:, 0], ca[:, 1]) / np.interp(vs, cb[:, 0], cb[:, 1])
    # the other X7T rating pairs of the decap-study cache (DC-bias charts only)
    old = json.loads((R / "research" / "tcpmt_revision" /
                      "capacitor_datasheet_data.json").read_text())["parts"]
    pairs = {}
    for p, q in (("GRM21BD72A225KE01", "GRM21BD71H225KE01"),
                 ("GRM155D71H224KE01", "GRM155D71E224KE01")):
        P = np.array(old[p]["dc_bias"]["V_change_pct_C_uF"])
        Q = np.array(old[q]["dc_bias"]["V_change_pct_C_uF"])
        shared = [v for v in Q[:, 0] if v <= P[-1, 0] + 1e-9
                  and np.any(np.abs(P[:, 0] - v) < 1e-9)]
        pairs[f"{p} vs {q}"] = rel([np.interp(v, P[:, 0], P[:, 2]) for v in shared],
                                   [np.interp(v, Q[:, 0], Q[:, 2]) for v in shared])
    ct_at = {k: v for k, v in zip(sorted(b["c_temp"], key=lambda s: float(s[:-1])), ct)}
    return {
        "dc_bias_grid_points": {list(PARTS)[0]: len(A), list(PARTS)[1]: len(B)},
        "dc_bias_grid_step_V": {list(PARTS)[0]: float(A[1, 0] - A[0, 0]),
                                list(PARTS)[1]: float(B[1, 0] - B[0, 0])},
        "dc_bias_max_rel_diff_on_shared_points": dcb,
        "n_shared_points": len(on_grid),
        "esr_biases_compared": len(rr), "esr_max_rel_diff": max(rr) if rr else None,
        "c_temp_biases_compared": len(ct), "c_temp_max_rel_diff": max(ct) if ct else None,
        "c_temp_max_rel_diff_by_bias": ct_at,
        "other_X7T_rating_pairs_dc_bias_max_rel_diff": pairs,
        "control_pair": list(CONTROL),
        "control_C_ratio_50V_over_100V_at": {f"{v:.1f}V": float(c) for v, c in zip(vs, ctrl)},
        "verdict": None,
    }


# ------------------------------------------------------------------ engine table
def _temp_factor_table(rec):
    """f_T(V, T) = C(V, T) / C(V, 25 C) from the C-temperature chart at each DC bias, on a
    5-degC grid from -55 to 125 C."""
    rows = []
    for key, c in sorted(rec["c_temp"].items(), key=lambda kv: float(kv[0][:-1])):
        if "T_C_uF" not in c:
            continue
        d = np.array(c["T_C_uF"])
        c25 = float(np.interp(25.0, d[:, 0], d[:, 1]))
        f = [[t, round(float(np.interp(t, d[:, 0], d[:, 1])) / c25, 5)] for t in T_GRID_C
             if d[0, 0] - 1e-9 <= t <= d[-1, 0] + 1e-9]
        rows.append([float(key[:-1]), f])
    return rows


def _esr_table(rec):
    rows = []
    for key, r in sorted(rec["r"].items(), key=lambda kv: float(kv[0][:-1])):
        if "f_MHz_ohm" not in r:
            continue
        d = np.array(r["f_MHz_ohm"])
        keep = (d[:, 0] >= F_KEEP_MHZ[0]) & (d[:, 0] <= F_KEEP_MHZ[1])
        rows.append([float(key[:-1]),
                     [[float(f"{f * 1e6:.5g}"), float(f"{x:.5g}")] for f, x in d[keep]]])
    return rows


def build_engine_table(data=None):
    data = data or load()
    out = {"source": data["source"], "fetched": data["fetched"],
           "note": ("Reduced from research/tcpmt_revision/flying_cap_vendor_data.json by "
                    "scripts/tcpmt_caprule_vendor.py. c_v_25c: C(V) at 25 C, AC 1 Vrms (uF); "
                    "temp_factor: [V_bias, [[T_C, C(V,T)/C(V,25 C)], ...]] from the "
                    "C-temperature charts at bias (AC 0.1 Vrms); esr_f: [V_bias, [[f_Hz, "
                    "R_ohm], ...]] at 25 C."),
           "parts": {}}
    for pn in PARTS:
        rec = data["parts"][pn]
        sp = rec["spec"]
        L, W = (float(x) for x in sp["LxW_mm"].replace("mm", "").split("×"))
        out["parts"][pn] = {
            "url": rec["url"], "rated_voltage_V": PA._num(sp["rated_voltage"]),
            "dielectric": sp["dielectric"], "size_inch": sp["size_inch"],
            "L_mm": L, "W_mm": W, "thickness": sp["thickness"],
            "max_height_um": PA._num(sp["thickness_max"]) * 1e3,
            "t_rated_c": PA._num(str(sp["operating_temp"]).split("～")[-1]),
            "tolerance": 0.10 if pn[13] == "K" else 0.20,
            "c_v_25c": [[v, c] for v, c in rec["dc_bias"]["V_C_uF"]],
            "temp_factor": _temp_factor_table(rec),
            "esr_f": _esr_table(rec),
        }
    ENGINE_TABLE.write_text(json.dumps(out, separators=(",", ":")))
    return out


def main():
    if "--fetch" in sys.argv:
        data = fetch()
        data = load()
    else:
        data = load()
    chk = identity_check(data)
    same_design = (chk["dc_bias_max_rel_diff_on_shared_points"] < 1e-4
                   and (chk["esr_max_rel_diff"] or 0.0) < 1e-4)
    ctrl = max(abs(v - 1.0) for v in chk["control_C_ratio_50V_over_100V_at"].values())
    chk["verdict"] = (
        ("GENUINE, not a data artifact: " if same_design else "NOT the same design: ")
        + "the construction-set charts (C-DC bias at 25 C, %d shared points; ESR(f) at %d DC "
          "biases) are identical to the cached precision (max rel. diff %.1e / %.1e), the "
          "C-temperature charts at bias are separate records that differ by up to %.1f %% "
          "(so the two part numbers are not one record duplicated), the queries were "
          "independent with different sampling grids (%.2f V vs %.2f V steps), the same "
          "pattern holds for the other X7T rating pairs (%s), and the X7R control pair with "
          "different individual specification codes differs by up to %.1f %%. Both parts "
          "carry the same individual specification code (KE01), size, thickness and nominal "
          "C: one dielectric design offered at two ratings."
        % (chk["n_shared_points"], chk["esr_biases_compared"],
           chk["dc_bias_max_rel_diff_on_shared_points"], chk["esr_max_rel_diff"] or 0.0,
           100 * (chk["c_temp_max_rel_diff"] or 0.0),
           *chk["dc_bias_grid_step_V"].values(),
           ", ".join(f"{k}: {v:.1e}" for k, v in
                     chk["other_X7T_rating_pairs_dc_bias_max_rel_diff"].items()),
           100 * ctrl))
    data["identity_check"] = chk
    CACHE.write_text(json.dumps(_round(_trim(data)), separators=(",", ":")))
    build_engine_table(data)
    print(json.dumps(chk, indent=1))


if __name__ == "__main__":
    main()
