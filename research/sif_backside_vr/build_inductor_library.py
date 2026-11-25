#!/usr/bin/env python3
"""Si-IF backside VR study -- curated catalog-inductor library with core-loss models.

Input : inductor_catalog_raw.json  (datasheet values and loss data collected from manufacturer
        documents on 2026-11-25; one record per part, one core-loss record per series)
Output: inductor_library.json      (the parts the sweep uses, each with a core-loss model that
        sif_core.core_loss_w evaluates) and inductor_sources.json (per-part datasheet and price
        sources, per-series core-loss method, calibration and assumptions)

Electrical values
  L nominal; DCR max at 25 C (derived nominal x (1 + tol) where the datasheet gives only a
  tolerance; consistent with the EPC table's max R_DS(on)); I_sat the vendor's primary rating for
  the core material (30 % drop for soft-saturating composite/metal parts, 20 % for ferrite) --
  the 20 %-drop value of every part (given, or 0.72 x the 30 % value for composites, the mean of
  the 10 % and 30 % values for Wurth ferrites) is kept as Isat20_A for the sensitivity run;
  I_rms the vendor's 40 C (40 K) rise rating; body L x W (x H) for placement.
  f_max: the vendor's stated limit, capped at 3 MHz (the study range) and, for parts whose loss
  data is a vendor chart, at the chart's top frequency.

Core loss (sinusoidal or symmetric loss data converted to the PWM waveform by the iGSE in
sif_core.core_loss_w)
  vendor   Eaton FP1308R3 / FP1007R6 / FP1107R1 / TL1011V2: the datasheet K-factor,
           B_pp[G] = K L[nH] dI_pp 1e-3, and the digitized loss-vs-B_pp curves, P[W] = a(f) B^b(f)
           per chart frequency, interpolated in log f ("kfactor_table")
  ferrite  no vendor data (Coilcraft SLC/SLR, Wurth WE-HCF/WE-HCM, TDK VLB, Bourns TLVR1005T):
           Ferroxcube 3F3 (below 1 MHz) / 3F4 (1-3 MHz row) Steinmetz coefficients
           ("steinmetz_rows", 100 C), flux swing dB_pp = B_sat,ref dI_pp / I_sat with
           B_sat,ref = 0.385 T -- the mean of K L I_sat over all 20 Eaton parts (0.31-0.39 T) --
           and core volume = k_v x body volume, k_v calibrated so that the proxy reproduces the
           Eaton charts of the same construction class (geometric mean over their frequencies
           and flux ranges): FP charts for slab/drum VRM ferrites, the TL1011V2 chart for the
           Bourns TLVR (the Eaton TLVR ferrite is a multi-MHz grade, ~10x lower loss)
  composite no vendor data (Coilcraft XEL/XGL, Wurth WE-MAPI/WE-XHMI, TDK CLT32/SPM5030VT):
           Micrometals mix -8 (carbonyl iron, mu 35) Steinmetz fits near 100 kHz and 1 MHz, peak
           flux; dB_pp = B_ref dI_pp / I_sat with B_ref the median over these parts of the
           energy estimate B(I_sat) = I_sat sqrt(mu0 mu_r L / V_core) (mu_r 25), core volume
           0.7 x body volume (the molded winding takes the rest)
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RAW = os.path.join(HERE, "inductor_catalog_raw.json")
OUT = os.path.join(HERE, "inductor_library.json")
SRC = os.path.join(HERE, "inductor_sources.json")

F_CAP_MHZ = 3.0
MU0 = 4e-7 * math.pi
MU_R_COMPOSITE = 25.0
KV_COMPOSITE = 0.7
B_SAT_FERRITE_T = None            # computed from the Eaton K-factors (mean K L I_sat)
COMPOSITE = ("XEL", "XGL", "WE-MAPI", "WE-XHMI", "CLT32", "SPM5030")
EATON_CHART = {"FP1308R3": "FP1308R", "FP1007R6": "FP1007R6", "FP1107R1": "FP1107R1",
               "TL1011V2": "TL1011V2"}


def series_key(s):
    return s.split(" ")[0]


def is_composite(series):
    return any(series.startswith(c) for c in COMPOSITE)


def chart_record(core, key):
    for r in core:
        s = r.get("series", "")
        if key == "FP1308R" and s.startswith("FP1308R"):
            return r
        if key == "FP1007R6" and s.startswith("FP1007R6"):
            return r
        if key == "FP1107R1" and s.startswith("FP1107R1"):
            return r
        if key == "TL1011V2" and s.startswith("TL1011V2"):
            return r
    raise KeyError(key)


def _f_hz(label):
    lab = label.lower().replace(" ", "")
    if lab.endswith("mhz"):
        return float(lab[:-3]) * 1e6
    if lab.endswith("khz"):
        return float(lab[:-3]) * 1e3
    raise ValueError(label)


def chart_table(rec):
    fits = rec["params"].get("fits_P_W_vs_Bpp_G") or rec["params"].get("fits_25C_P_W_vs_Bpp_G")
    rows = sorted([_f_hz(k), v["a"], v["b"], v.get("Bpp_range_G")] for k, v in fits.items())
    return float(rec["params"]["K_factor"]), rows


def ferroxcube_rows(core):
    rec = next(r for r in core if "Ferroxcube" in r.get("vendor", "") + r.get("series", ""))
    p = rec["params"]
    rows = [[r["f_kHz"][0] * 1e3, r["f_kHz"][1] * 1e3, r["Cm"], r["x"], r["y"]] for r in p["3F3"]]
    r4 = [r for r in p["3F4"] if r["f_kHz"][0] >= 1000][0]        # the 1-3 MHz row of 3F4
    rows.append([r4["f_kHz"][0] * 1e3, r4["f_kHz"][1] * 1e3, r4["Cm"], r4["x"], r4["y"]])
    return rows, rec["source"]


def micrometals_rows(core, mix="-8"):
    rec = next(r for r in core if "Micrometals" in r.get("vendor", "") + r.get("series", ""))
    p = rec["params"]
    lo, hi = p["fit_near_100kHz"][mix], p["fit_near_1MHz"][mix]
    fx = math.sqrt(1e5 * 1e6)                       # switch between the two fits at 316 kHz
    return ([[0.0, fx, lo["k"], lo["alpha"], lo["beta"]],
             [fx, 1e9, hi["k"], hi["alpha"], hi["beta"]]], rec["source"])


def p_steinmetz_rows(rows, f, B_pk, V_m3):
    """Sinusoidal loss (W) from piecewise Steinmetz rows [f_lo, f_hi, k, a, b] in kW/m^3."""
    for f_lo, f_hi, k, a, b in rows:
        if f_lo <= f < f_hi or (f >= f_hi and (f_lo, f_hi) == tuple(rows[-1][:2])):
            return 1e3 * k * f ** a * B_pk ** b * V_m3
    f_lo, f_hi, k, a, b = rows[0]
    return 1e3 * k * f ** a * B_pk ** b * V_m3


def main():
    raw = json.load(open(RAW))
    parts, core = raw["parts"], raw["core_loss"]
    frows, fsrc = ferroxcube_rows(core)
    mrows, msrc = micrometals_rows(core)

    # --- ferrite flux at I_sat from the Eaton K-factors -------------------------------------
    kli = []
    for p in parts:
        sk = series_key(p["series"])
        if sk in EATON_CHART:
            K, _ = chart_table(chart_record(core, EATON_CHART[sk]))
            kli.append(K * p["L_nH"] * 1e-3 * p["Isat_A"] * 1e-4)          # G -> T
    b_sat_fer = float(np.mean(kli))

    # --- calibration of the ferrite proxy on the Eaton FP charts (V = body volume) -----------
    ratios, by_chart = [], {}
    for sk, key in EATON_CHART.items():
        rec = chart_record(core, key)
        K, table = chart_table(rec)
        p0 = next(p for p in parts if series_key(p["series"]) == sk)
        vol = p0["length_mm"] * p0["width_mm"] * p0["height_mm"] * 1e-9
        rr = []
        for f, a, b, rng in table:
            if f > 3.0e6:
                continue
            lo, hi = (rng if rng else (300.0, 3000.0))
            for Bpp in np.geomspace(lo, hi, 5):
                P_chart = a * Bpp ** b
                P_mat = p_steinmetz_rows(frows, f, Bpp * 1e-4 / 2.0, vol)
                rr.append(P_chart / P_mat)
        by_chart[key] = {"geomean_ratio": float(np.exp(np.mean(np.log(rr)))),
                         "min": float(min(rr)), "max": float(max(rr)), "n": len(rr)}
        if key.startswith("FP"):
            ratios += rr
    kv_fer = float(np.exp(np.mean(np.log(ratios))))
    kv_tlvr = by_chart["TL1011V2"]["geomean_ratio"]

    # --- composite flux at I_sat: energy estimate, median over the composite parts ----------
    bref = []
    for p in parts:
        if is_composite(p["series"]):
            v = KV_COMPOSITE * p["length_mm"] * p["width_mm"] * p["height_mm"] * 1e-9
            bref.append(p["Isat_A"] * math.sqrt(MU0 * MU_R_COMPOSITE * p["L_nH"] * 1e-9 / v))
    b_ref_comp = float(np.median(bref))

    lib, src = [], []
    for p in parts:
        sk = series_key(p["series"])
        x, y, h = float(p["length_mm"]), float(p["width_mm"]), float(p["height_mm"])
        vol = x * y * h * 1e-9
        dcr_max = p.get("DCR_max_mohm") or (p["DCR_typ_mohm"] * 1.1)
        isat = float(p["Isat_A"])
        drops = p.get("Isat_by_drop_A") or {}
        if "20%" in drops:
            isat20, isat20_basis = float(drops["20%"]), "datasheet 20 % value"
        elif "10%" in drops and "30%" in drops and not is_composite(p["series"]):
            isat20 = 0.5 * (drops["10%"] + drops["30%"])
            isat20_basis = "mean of the 10 % and 30 % values"
        else:
            isat20, isat20_basis = 0.72 * isat, "0.72 x the 30 % value (XGL/SPM ratio)"
        fmax = F_CAP_MHZ
        txt = str(p.get("max_or_recommended_frequency") or "")
        if "up to 2 MHz" in txt:
            fmax = 2.0
        if sk in EATON_CHART:
            rec = chart_record(core, EATON_CHART[sk])
            K, table = chart_table(rec)
            fmax = min(fmax, max(r[0] for r in table) / 1e6)
            model = {"type": "kfactor_table", "K_G_per_nH_A": K,
                     "table": [[r[0], r[1], r[2]] for r in table], "waveform": "sinusoidal"}
            method = f"vendor K-factor chart ({rec['series'][:40]})"
            msrc_ = rec["source"]
        elif is_composite(p["series"]):
            model = {"type": "steinmetz_rows", "rows": mrows, "B_ref_T": b_ref_comp,
                     "I_ref_A": isat, "V_core_m3": KV_COMPOSITE * vol, "waveform": "sinusoidal"}
            method = "material proxy: Micrometals -8 carbonyl iron, flux from I_sat"
            msrc_ = msrc
        else:
            # calibrated on the Eaton charts of the same construction class: TLVR parts on the
            # TL1011V2 chart (multi-MHz ferrite), slab/drum VRM ferrites on the FP charts
            tlvr = "TLVR" in p["series"]
            kv = kv_tlvr if tlvr else kv_fer
            model = {"type": "steinmetz_rows", "rows": frows, "B_ref_T": b_sat_fer,
                     "I_ref_A": isat, "V_core_m3": kv * vol, "waveform": "sinusoidal"}
            method = ("material proxy: Ferroxcube 3F3/3F4, volume factor calibrated on the Eaton "
                      + ("TL1011V2 (TLVR) chart" if tlvr else "FP charts"))
            msrc_ = fsrc
        price = p.get("price_usd")
        price_note = p.get("price_note")
        if price is None:
            sib = [q for q in parts if q["series"] == p["series"] and q.get("price_usd")]
            if sib:
                near = min(sib, key=lambda q: abs(q["L_nH"] - p["L_nH"]))
                price = near["price_usd"]
                price_note = f"no listing; price of {near['part_number']} used"
        lib.append({"vendor": p["vendor"].split(" (")[0], "series": sk,
                    "part_number": p["part_number"], "L_nH": p["L_nH"],
                    "DCR_typ_mohm": p.get("DCR_typ_mohm"), "DCR_max_mohm": dcr_max,
                    "Isat_A": isat, "Isat_definition": p.get("Isat_definition"),
                    "Isat20_A": isat20, "Isat20_basis": isat20_basis,
                    "Irms_A": p["Irms_A"], "length_mm": x, "width_mm": y, "height_mm": h,
                    "core_material": p.get("core_material"), "f_max_MHz": fmax,
                    "core_model": model, "core_loss_method": method, "price_usd": price})
        src.append({"part": f"{p['vendor'].split(' (')[0]}-{p['part_number']}",
                    "datasheet_url": p.get("datasheet_url"),
                    "datasheet_revision": p.get("datasheet_revision"),
                    "price_usd": price, "price_qty": p.get("price_qty"),
                    "price_source_url": p.get("price_source_url"), "price_note": price_note,
                    "DCR_note": p.get("DCR_note"), "core_loss_method": method,
                    "core_loss_source": msrc_})
    meta = {"retrieved": raw.get("retrieved"), "n_parts": len(lib),
            "ferrite_B_sat_ref_T": b_sat_fer, "ferrite_B_sat_ref_spread_T": [min(kli), max(kli)],
            "ferrite_kv_calibration": kv_fer, "ferrite_kv_tlvr": kv_tlvr,
            "eaton_chart_vs_proxy": by_chart,
            "composite_B_ref_T": b_ref_comp, "composite_B_ref_spread_T": [min(bref), max(bref)],
            "composite_mu_r_assumed": MU_R_COMPOSITE, "composite_kv": KV_COMPOSITE,
            "notes": __doc__}
    json.dump({"meta": meta, "parts": lib}, open(OUT, "w"), indent=1)
    json.dump({"meta": {k: meta[k] for k in meta if k != "notes"}, "core_loss_records": core,
               "parts": src, "raw_notes": raw.get("notes")}, open(SRC, "w"), indent=1)
    print(f"{len(lib)} parts -> {OUT}")
    print(f"ferrite B_sat,ref = {b_sat_fer:.3f} T (spread {min(kli):.3f}-{max(kli):.3f})")
    print(f"ferrite proxy volume factor k_v = {kv_fer:.3f}; per chart:",
          json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in by_chart.items()}))
    print(f"composite B_ref = {b_ref_comp:.3f} T (spread {min(bref):.3f}-{max(bref):.3f})")


if __name__ == "__main__":
    main()
