"""Si-IF backside VR study -- vendor data for the catalog flying-capacitor library.

For every catalog Murata MLCC below, fetch from Murata's public product-information API (the
data behind SimSurfing; read-only helpers of scripts/tcpmt_decap_parts.py, generic client, no
personal data) what the synthesis engine's corrected capacitor rule needs:
  spec       size, thickness (nominal, max), rating, dielectric, temperature range, status
  dc_bias    C(V) at 25 C (the chart's own AC level)                 -> c_v_25c
  c_temp     C(T) at DC biases on a grid up to 0.8 V_rated              -> temp_factor
  r          ESR(f) at 25 C at a few DC biases                          -> esr_f
and write mlcc_vendor_data.json (same table format as Scalable_Integrated_VR/src/
HVR_capacitor_vendor_data.json, which the overlay injects at run time; nothing in the engine
directory is written). Where Murata has no C-temperature chart at a bias, the nearest bias
with a chart is used; with none at all, the EIA class limit at the design temperature is used
(X7R -15 %, X7S/X6S -22 %, X7T -33 %) and the record says so.

    python mlcc_fetch.py           fetch (about 10 min, 0.3 s between requests)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import tcpmt_decap_parts as PA  # noqa: E402  (helpers only)

OUT = HERE / "mlcc_vendor_data.json"
RAW = HERE / "mlcc_vendor_raw.json"
FETCHED = time.strftime("%Y-%m-%d")

PARTS = [
    # 16 V
    "GRM188C71C475KE21", "GRM188C81C106MA73", "GRM21BC81C226ME44", "GRM31CC71C226ME11",
    # 25 V
    "GRM155D71E105KE11", "GRM188C71E225KE11", "GRM188C81E106ME01", "GRM21BC71E106KE01",
    "GRM21BZ71E106KE15", "GRM21BC81E226ME44", "GRM31CR71E106KA12", "GRM31CC71E226ME15",
    "GRM31CC81E226KE11", "GRM32ER71E226KE15",
    # 35 V
    "GRM21BC7YA475KE11",
    # 50 V
    "GRM188D71H105KE01", "GRM21BD71H225KE01", "GRM21BC71H475KE11", "GRM31CR71H475KA12",
    # 100 V
    "GRM188D72A105KE01", "GRM21BC72A105KE01", "GRM21BD72A225KE01", "GRM31CC72A475KE11",
    "GRM32EC72A106KE05",
]
T_GRID_C = tuple(float(t) for t in range(-55, 126, 5))
CLASS_LIMIT_AT_DESIGN = {"X7R": 0.85, "X7S": 0.78, "X6S": 0.78, "X7T": 0.67, "X5R": 0.85}


def _sleep():
    time.sleep(0.3)


def _num(s):
    import re
    m = re.search(r"[-+]?\d*\.?\d+", str(s).replace(",", ""))
    return float(m.group()) if m else None


def spec(pn):
    hits = PA._search(pn + "#")
    if not hits:
        return None
    d = PA._flat(hits[0])
    g = lambda k: (d.get(k) or [None])[0]  # noqa: E731
    return {"capacitance": g("capacitance"), "rated_voltage": g("ratedVoltage"),
            "dielectric": g("tempChara"), "size_inch": g("sizeCodeInInch"),
            "LxW_mm": g("lengthxWidth"), "thickness": g("thickness"),
            "thickness_max": g("thicknessMax"), "operating_temp": g("operaTemp"),
            "status": g("productionStatus")}


def dc_bias(pn):
    for par in ({"ac": 1.0}, {"ac": 0.5}, {}):
        s, err = PA._chara(pn + "#", "c_dcbias_capchange_cap", **par)
        _sleep()
        if s:
            k = PA._cap_scale(s)
            return {"ac_Vrms": float(s.get("ac", 1)), "T_C": float(s.get("tc", 25)),
                    "V_C_uF": [[float(p[0][0]), float(p[2][0]) * k] for p in s["data"]]}
    return {"error": err}


def c_temp(pn, dc):
    s, err = PA._chara(pn + "#", "c_temp_capchange_cap", dc=dc)
    _sleep()
    if not s:
        return {"error": err}
    k = PA._cap_scale(s)
    return {"ac_Vrms": float(s.get("ac", 0.1)), "dc_V": float(s.get("dc", dc)),
            "T_C_uF": [[float(p[0][0]), float(p[2][0]) * k] for p in s["data"]]}


def esr(pn, dc):
    s, err = PA._chara(pn + "#", "r", dc=dc, tc=25)
    _sleep()
    if not s:
        return {"error": err}
    return {"dc_V": float(dc), "f_MHz_ohm": PA._curve(s, (0, 1))}


def bias_grid(vr, step_frac, top=0.8):
    step = max(1.0, round(vr * step_frac))
    g = list(np.arange(0.0, top * vr + 1e-9, step))
    return [float(x) for x in g]


def fetch():
    raw = {"source": ("Murata public PIM API (pimapi.murata.com/public/api/pim/v1), the data "
                      "behind SimSurfing"), "fetched": FETCHED, "parts": {}}
    for pn in PARTS:
        print("fetching", pn, flush=True)
        sp = spec(pn)
        _sleep()
        rec = {"part": pn, "url": PA.PRODUCT_URL.format(pn=pn), "spec": sp}
        if sp is None:
            rec["error"] = "not found"
            raw["parts"][pn] = rec
            continue
        vr = _num(sp["rated_voltage"])
        rec["dc_bias"] = dc_bias(pn)
        rec["c_temp"] = {f"{dc:g}V": c_temp(pn, dc) for dc in bias_grid(vr, 0.08)}
        rec["r"] = {f"{dc:g}V": esr(pn, dc) for dc in sorted({0.0, round(0.25 * vr),
                                                              round(0.5 * vr),
                                                              round(0.8 * vr)})}
        raw["parts"][pn] = rec
    RAW.write_text(json.dumps(raw, separators=(",", ":"), ensure_ascii=False))
    return raw


def build(raw):
    out = {"source": raw["source"], "fetched": raw["fetched"],
           "note": ("c_v_25c: C(V) at 25 C (uF); temp_factor: [V_bias, [[T_C, C(V,T)/C(V,25 C)]]] "
                    "from the C-temperature charts at bias (nearest charted bias; EIA class "
                    "limit at 105 C where Murata has no chart); esr_f: [V_bias, [[f_Hz, R_ohm]]] "
                    "at 25 C, 10 kHz-300 MHz. Same format as HVR_capacitor_vendor_data.json."),
           "parts": {}}
    for pn, rec in raw["parts"].items():
        sp = rec.get("spec")
        if not sp or "V_C_uF" not in rec.get("dc_bias", {}):
            print("skip (no spec or DC-bias chart):", pn)
            continue
        L, W = (float(x) for x in sp["LxW_mm"].replace("mm", "").split("×"))
        tf, basis = [], "c_temp charts at bias"
        for key, c in sorted(rec["c_temp"].items(), key=lambda kv: float(kv[0][:-1])):
            if "T_C_uF" not in c:
                continue
            d = np.array(c["T_C_uF"])
            c25 = float(np.interp(25.0, d[:, 0], d[:, 1]))
            tf.append([float(key[:-1]),
                       [[t, round(float(np.interp(t, d[:, 0], d[:, 1])) / c25, 5)]
                        for t in T_GRID_C if d[0, 0] - 1e-9 <= t <= d[-1, 0] + 1e-9]])
        if not tf:
            lim = CLASS_LIMIT_AT_DESIGN.get(sp["dielectric"], 0.67)
            tf = [[0.0, [[-55.0, lim], [25.0, 1.0], [85.0, lim], [105.0, lim], [125.0, lim]]]]
            basis = f"EIA class limit ({sp['dielectric']}: x{lim} at 85-125 C), no Murata chart"
        er = []
        for key, r in sorted(rec["r"].items(), key=lambda kv: float(kv[0][:-1])):
            if "f_MHz_ohm" not in r:
                continue
            d = np.array(r["f_MHz_ohm"])
            keep = (d[:, 0] >= 0.01) & (d[:, 0] <= 300.0)
            er.append([float(key[:-1]),
                       [[float(f"{f * 1e6:.5g}"), float(f"{x:.5g}")] for f, x in d[keep]]])
        tmax = _num(str(sp["operating_temp"]).split("～")[-1])
        out["parts"][pn] = {
            "url": rec["url"], "rated_voltage_V": _num(sp["rated_voltage"]),
            "capacitance": sp["capacitance"], "dielectric": sp["dielectric"],
            "size_inch": sp["size_inch"], "L_mm": L, "W_mm": W,
            "thickness": sp["thickness"], "max_height_um": _num(sp["thickness_max"]) * 1e3,
            "t_rated_c": tmax, "status": sp["status"],
            "tolerance": 0.10 if pn[13] == "K" else 0.20,
            "c_v_25c": [[v, c] for v, c in rec["dc_bias"]["V_C_uF"]],
            "temp_factor": tf, "temp_factor_basis": basis, "esr_f": er,
        }
    OUT.write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    print("wrote", OUT, len(out["parts"]), "parts")
    return out


if __name__ == "__main__":
    raw = json.loads(RAW.read_text()) if ("--build" in sys.argv and RAW.exists()) else fetch()
    build(raw)
