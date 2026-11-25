"""Si-IF backside VR study -- find catalog Murata MLCCs for the flying-capacitor library.

Prefix searches on Murata's public product-information API (the JSON behind SimSurfing),
through the read-only helpers of scripts/tcpmt_decap_parts.py (generic client, no personal
data). Lists the existing parts (size, rating, dielectric, thickness, status) for the
prefixes below and writes mlcc_search.json next to this script.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import tcpmt_decap_parts as PA  # noqa: E402  (helpers only; nothing is written by it)

# GRM <size><thk> <temp char> <rating> <cap code>: sizes 15=0402 18=0603 21=0805 31=1206
# 32=1210; R7=X7R C7=X7S D7=X7T C8=X6S Z7=X7R(thin); 1C=16V 1E=25V YA=35V 1H=50V 2A=100V
PREFIXES = [
    # 16 V
    "GRM21BC71C226", "GRM21BC81C226", "GRM31CR71C226", "GRM31CC81C476", "GRM32ER71C476",
    "GRM31CC71C226", "GRM188C81C106", "GRM188C71C475",
    # 25 V
    "GRM21BC71E106", "GRM21BC81E226", "GRM31CR71E106", "GRM31CC71E226", "GRM31CC81E226",
    "GRM32ER71E226", "GRM32EC81E476", "GRM188C81E106", "GRM188C71E225", "GRM155D71E105",
    "GRM31CZ71E226", "GRM21BZ71E106",
    # 35 V
    "GRM21BC7YA475", "GRM31CC7YA106", "GRM32EC7YA226", "GRM31CR7YA106", "GRM188R7YA105",
    # 50 V
    "GRM188D71H105", "GRM21BD71H225", "GRM21BC71H475", "GRM31CR71H475", "GRM31CC71H106",
    "GRM31CZ71H106", "GRM32ER71H106", "GRM32EC71H106", "GRM32ER71H226",
    # 100 V
    "GRM188D72A105", "GRM21BD72A225", "GRM21BC72A105", "GRM31CC72A475", "GRM32EC72A106",
    "GRM31CR72A225", "GRM32ER72A225", "GRM32ER72A475",
]


def prefix_search(pn):
    body = {"searchCondClass": 1, "partNum": pn, "page": 1, "pageSize": 100,
            "productCategoryId": "ceramicCapacitorSMD", "languageRegion": "en-us",
            "series": "", "sortKey": "", "valSearchCondList": [],
            "rangeValSearchCondList": [], "dateRangeSearchCondList": [],
            "advancedSearchCalculatedCondList": []}
    hits = PA._post("/products/search", body).get("productSearchResult") or []
    out = {}
    for h in hits:
        d = PA._flat(h)
        g = lambda k: (d.get(k) or [None])[0]  # noqa: E731
        out[g("partNum")] = {"capacitance": g("capacitance"), "rated_voltage": g("ratedVoltage"),
                             "dielectric": g("tempChara"), "size_inch": g("sizeCodeInInch"),
                             "LxW_mm": g("lengthxWidth"), "thickness": g("thickness"),
                             "thickness_max": g("thicknessMax"),
                             "operating_temp": g("operaTemp"), "status": g("productionStatus")}
    return out


def main():
    res = {}
    for p in PREFIXES:
        try:
            res[p] = prefix_search(p)
        except Exception as e:  # network or API error: record and continue
            res[p] = {"error": str(e)}
        n = len(res[p]) if "error" not in res[p] else -1
        print(f"{p:16s} {n:3d}", "; ".join(
            f"{k} {v['capacitance']} {v['rated_voltage']} {v['dielectric']} {v['thickness']} "
            f"[{v['status']}]" for k, v in list(res[p].items())[:6] if isinstance(v, dict)),
            flush=True)
        time.sleep(0.3)
    (HERE / "mlcc_search.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
