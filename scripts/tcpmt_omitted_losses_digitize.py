#!/usr/bin/env python3
"""Digitize the manufacturer curves the omitted-loss estimate needs (TCPMT revision).

Every curve is read from the PDF itself: the page is rendered with poppler's pdftoppm at
600 dpi, the plot frame and the light-grey gridlines are detected automatically inside a
region of interest, the pixel->data map is a least-squares fit through the gridlines of
known value, and the curve pixels are selected by colour. Nothing is read by eye except
the Ferroxcube 3F4 temperature curve (black curve on black gridlines), whose points are
listed explicitly below with the pixel scale they were read on.

Curves digitized
  EPC2057  Fig. 8  reverse drain-source characteristic, V_GS = 0, 25 and 125 C  (low side)
  EPC2057  Fig. 6  Q_OSS(V_DS) and E_OSS(V_DS)
  EPC2090  Fig. 8  reverse drain-source characteristic, 25 and 125 C            (low side, M = 40, 42)
  EPC2090  Fig. 6  Q_OSS(V_DS), E_OSS(V_DS)
  EPC2014C Fig. 7  reverse drain-source characteristic (reference only: the high side
                   never conducts in the third quadrant in this topology)
  EPC2014C Fig. 5a C_OSS(V_DS), integrated to Q_OSS and E_OSS
  TY-M5    Fig. 6c of the source of the library inductor (specific loss at 10 MHz vs B)
  Fig. 9b  of the same source: winding AC resistance vs frequency of the 8.2 mOhm segment

Usage (python -I keeps the interpreter from importing anything from the download folders):
    python -I scripts/tcpmt_omitted_losses_digitize.py
Writes research/tcpmt_revision/omitted_losses_inputs.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "research" / "tcpmt_revision" / "omitted_losses_inputs.json"
SCR = Path(os.environ.get("HVR_SCRATCH", "/home/beams0/SABDELZAHER/ETM_project/scratch_omitloss"))

PDF = {
    "EPC2057": Path("/home/beams0/SABDELZAHER/ETM_project/review_work/dl_epc/EPC2057.pdf"),
    "EPC2014C": Path("/home/beams0/SABDELZAHER/ETM_project/review_work/dl_epc/EPC2014C.pdf"),
    "EPC2090": SCR / "dl_epc2090" / "EPC2090.pdf",
    "IND_SRC": Path("/home/beams0/SABDELZAHER/Salma_Thesis/HVR/"
                    "Inductor_Arrays__Rami__Salma__TCPMT_-2.pdf"),
}
URL = {
    "EPC2057": "https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2057_datasheet.pdf",
    "EPC2014C": "https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2014C_datasheet.pdf",
    "EPC2090": "https://epc-co.com/epc/Portals/0/epc/documents/datasheets/EPC2090_datasheet.pdf",
    "3F4": "https://www.ferroxcube.com/upload/media/product/file/MDS/3f4.pdf",
    "LMG1210": "https://www.ti.com/lit/ds/symlink/lmg1210.pdf",
}
DPI = 600

# colour classes (RGB) of the EPC curve families
BLUE = lambda R, G, B: (B > 150) & (R < 90) & (G > 60) & (G < 170)
RED = lambda R, G, B: (R > 180) & (G < 100) & (B < 100)
DARKRED = lambda R, G, B: (R > 110) & (R < 190) & (G < 70) & (B < 80)


def render(pdf: Path, page: int, tmp: Path) -> np.ndarray:
    stem = tmp / f"{pdf.stem}_p{page}"
    subprocess.run(["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page), "-png",
                    str(pdf), str(stem)], check=True)
    png = sorted(tmp.glob(f"{stem.name}*.png"))[-1]
    return np.asarray(Image.open(png).convert("RGB")).astype(int)


def _groups(idx):
    idx = np.asarray(idx)
    if idx.size == 0:
        return []
    return [float(g.mean()) for g in np.split(idx, np.flatnonzero(np.diff(idx) > 2) + 1)]


def frame_grid(im, roi, grey=(150, 240), dark_frac=0.5, grid_frac=0.3):
    """Frame lines (dark, spanning > dark_frac of the ROI) and light-grey gridlines."""
    x0, x1, y0, y1 = roi
    sub = im[y0:y1, x0:x1]
    dark = sub.sum(axis=2) < 150
    rows = _groups([y + y0 for y in range(sub.shape[0]) if dark[y].sum() > dark_frac * sub.shape[1]])
    cols = _groups([x + x0 for x in range(sub.shape[1]) if dark[:, x].sum() > dark_frac * sub.shape[0]])
    R, G, B = sub[:, :, 0], sub[:, :, 1], sub[:, :, 2]
    g = (np.abs(R - G) < 10) & (np.abs(G - B) < 10) & (R > grey[0]) & (R < grey[1])
    grows = _groups([y + y0 for y in range(sub.shape[0]) if g[y].sum() > grid_frac * sub.shape[1]])
    gcols = _groups([x + x0 for x in range(sub.shape[1]) if g[:, x].sum() > grid_frac * sub.shape[0]])
    return rows, cols, grows, gcols


def lsq_map(pix, val):
    """value = a * pixel + b, least squares; returns (a, b, max residual in value units)."""
    pix, val = np.asarray(pix, float), np.asarray(val, float)
    A = np.vstack([pix, np.ones_like(pix)]).T
    (a, b), *_ = np.linalg.lstsq(A, val, rcond=None)
    return float(a), float(b), float(np.max(np.abs(a * pix + b - val)))


def calibrate(im, roi, xvals, yvals, x_edges=None, y_edges=None):
    """Axis maps from frame + gridlines. xvals/yvals: values of the detected gridlines
    (low->high); x_edges/y_edges: values of the frame lines (left,right)/(top,bottom)."""
    rows, cols, grows, gcols = frame_grid(im, roi)
    # frame lines are the outermost dark lines; gridlines are strictly inside them
    cols_f = [cols[0], cols[-1]]
    rows_f = [rows[0], rows[-1]]
    gcols = [c for c in gcols if cols_f[0] + 8 < c < cols_f[1] - 8]
    grows = [r for r in grows if rows_f[0] + 8 < r < rows_f[1] - 8]
    xp, xv = list(gcols), list(xvals)
    if len(xp) != len(xv):
        raise RuntimeError(f"x gridlines found {len(xp)} != expected {len(xv)}: {xp}")
    if x_edges is not None:
        xp += cols_f
        xv += list(x_edges)
    yp, yv = list(grows), list(yvals)[::-1]          # rows grow downward
    if len(yp) != len(yv):
        raise RuntimeError(f"y gridlines found {len(yp)} != expected {len(yv)}: {yp}")
    if y_edges is not None:
        yp += rows_f
        yv += list(y_edges)
    ax, bx, ex = lsq_map(xp, xv)
    ay, by, ey = lsq_map(yp, yv)
    return {"ax": ax, "bx": bx, "ay": ay, "by": by, "res_x": ex, "res_y": ey,
            "frame_rows": rows_f, "frame_cols": cols_f}


def curve_rows(im, cal, mask_fn, levels, roi, exclude=()):
    """For a steep curve x(y): at each y level, the median x of the coloured pixels."""
    x0, x1, y0, y1 = roi
    R, G, B = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    m = mask_fn(R, G, B)
    keep = np.zeros_like(m)
    keep[y0:y1, x0:x1] = True
    for ex in exclude:
        keep[ex[2]:ex[3], ex[0]:ex[1]] = False
    m &= keep
    out = []
    for lev in levels:
        y = int(round((lev - cal["by"]) / cal["ay"]))
        xs = np.flatnonzero(m[y - 2:y + 3, :].any(axis=0))
        if xs.size == 0:
            out.append(None)
            continue
        out.append(cal["ax"] * float(np.median(xs)) + cal["bx"])
    return out


def curve_cols(im, cal, mask_fn, xs_val, roi, exclude=()):
    """For a curve y(x): at each x value, the mean y of the coloured pixels in that column."""
    x0, x1, y0, y1 = roi
    R, G, B = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    m = mask_fn(R, G, B)
    keep = np.zeros_like(m)
    keep[y0:y1, x0:x1] = True
    for ex in exclude:
        keep[ex[2]:ex[3], ex[0]:ex[1]] = False
    m &= keep
    out = []
    for xv in xs_val:
        x = int(round((xv - cal["bx"]) / cal["ax"]))
        ys = np.flatnonzero(m[:, x - 2:x + 3].any(axis=1))
        if ys.size == 0:
            out.append(None)
            continue
        # one curve per colour: take the largest contiguous cluster
        cl = np.split(ys, np.flatnonzero(np.diff(ys) > 3) + 1)
        c = max(cl, key=len)
        out.append(cal["ay"] * float(c.mean()) + cal["by"])
    return out


def scale_roi(roi, im):
    """ROIs are written for a 600-dpi letter page (5100 x 6601 px)."""
    h, w = im.shape[:2]
    sx, sy = w / 5100.0, h / 6601.0
    return (int(roi[0] * sx), int(roi[1] * sx), int(roi[2] * sy), int(roi[3] * sy))


I_LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 25, 30]


def epc_reverse(dev, im, roi, xg, yg, x_edges, exclude):
    roi = scale_roi(roi, im)
    cal = calibrate(im, roi, xg, yg, x_edges=x_edges, y_edges=None)
    inner = (int(cal["frame_cols"][0]) + 6, int(cal["frame_cols"][1]) - 6,
             int(cal["frame_rows"][0]) + 6, int(cal["frame_rows"][1]) - 6)
    ex = [scale_roi(e, im) for e in exclude]
    v25 = curve_rows(im, cal, BLUE, I_LEVELS, inner, ex)
    v125 = curve_rows(im, cal, RED, I_LEVELS, inner, ex)
    pts = [(i, a, b) for i, a, b in zip(I_LEVELS, v25, v125) if a is not None and b is not None]
    I = np.array([p[0] for p in pts]); a25 = np.array([p[1] for p in pts]); a125 = np.array([p[2] for p in pts])
    sel = (I >= 3) & (I <= 12)
    fit = lambda v: np.polyfit(I[sel], v[sel], 1)
    s25, c25 = fit(a25)
    s125, c125 = fit(a125)
    return {"I_A": I.tolist(), "V_SD_25C_V": np.round(a25, 4).tolist(),
            "V_SD_125C_V": np.round(a125, 4).tolist(),
            "linear_fit_3_12A": {"V0_25C_V": round(float(c25), 4), "R_25C_ohm": round(float(s25), 5),
                                 "V0_125C_V": round(float(c125), 4), "R_125C_ohm": round(float(s125), 5)},
            "calibration_residual": [cal["res_x"], cal["res_y"]]}


def epc_qoss(dev, im, roi, xg, yg, x_edges, y_edges, vgrid, exclude=()):
    roi = scale_roi(roi, im)
    cal = calibrate(im, roi, xg, yg, x_edges=x_edges, y_edges=y_edges)
    inner = (int(cal["frame_cols"][0]) + 6, int(cal["frame_cols"][1]) - 6,
             int(cal["frame_rows"][0]) + 6, int(cal["frame_rows"][1]) - 6)
    q = curve_cols(im, cal, BLUE, vgrid, inner, [scale_roi(e, im) for e in exclude])
    return {"V_DS_V": list(vgrid), "Q_OSS_nC": [None if v is None else round(v, 4) for v in q],
            "calibration_residual": [cal["res_x"], cal["res_y"]]}


def epc2014c_coss(im):
    roi = scale_roi((450, 2480, 540, 2060), im)
    cal = calibrate(im, roi, [5, 10, 15, 20, 25, 30, 35], [50, 100, 150, 200, 250],
                    x_edges=[0, 40], y_edges=[300, 0])
    inner = (int(cal["frame_cols"][0]) + 6, int(cal["frame_cols"][1]) - 6,
             int(cal["frame_rows"][0]) + 6, int(cal["frame_rows"][1]) - 6)
    vg = [0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 39.5]
    # legend box of Fig. 5a (C_OSS swatch) sits at ~(28-40 V, 40-90 pF): exclude it
    c = curve_cols(im, cal, DARKRED, vg, inner, [scale_roi((1700, 2340, 1560, 1875), im)])
    v = np.array([x for x, y in zip(vg, c) if y is not None])
    cc = np.array([y for y in c if y is not None])
    # integrate C(V) from 0: Q(V) = int C dV, E(V) = int V C dV (C at 0 V from extrapolation)
    vv = np.concatenate([[0.0], v]); cv = np.concatenate([[cc[0]], cc])
    q = np.concatenate([[0.0], np.cumsum(0.5 * (cv[1:] + cv[:-1]) * np.diff(vv))]) * 1e-3   # nC
    e = np.concatenate([[0.0], np.cumsum(0.5 * (cv[1:] * vv[1:] + cv[:-1] * vv[:-1])
                                          * np.diff(vv))]) * 1e-3                     # nJ
    return {"V_DS_V": v.tolist(), "C_OSS_pF": np.round(cc, 2).tolist(),
            "Q_OSS_nC": np.round(q[1:], 4).tolist(), "E_OSS_nJ": np.round(e[1:], 4).tolist(),
            "check": "datasheet Q_OSS = 4 nC typ at 20 V",
            "calibration_residual": [cal["res_x"], cal["res_y"]]}


def tym5_loss(im):
    """Fig. 6c (log-log): specific loss at 10 MHz vs flux density; straight-line fit."""
    roi = scale_roi((3380, 4490, 5060, 5700), im)
    rows, cols, _, _ = frame_grid(im, roi, dark_frac=0.6)
    yt, yb = rows[0], rows[-1]
    xl, xr = cols[0], cols[-1]
    gray = im.sum(axis=2) // 3
    xs, ys = [], []
    for x in range(int(xl) + 12, int(xr) - 12):
        d = np.flatnonzero(gray[int(yt) + 8:int(yb) - 8, x] < 80)
        if d.size:
            xs.append(x)
            ys.append(d.mean() + int(yt) + 8)
    xs, ys = np.array(xs, float), np.array(ys, float)
    logB = (xs - xl) / ((xr - xl) / 2.0)                 # decades above 1 mT (axis 1..100 mT)
    logP = 4.0 + (yb - ys) / ((yb - yt) / 5.0)           # axis 1e4..1e9 W/m3
    beta, c = np.polyfit(logB, logP, 1)
    return {"beta": round(float(beta), 4), "P_at_1mT_W_m3": round(float(10 ** c), 1),
            "fit_max_residual_decades": round(float(np.max(np.abs(logP - (beta * logB + c)))), 4),
            "n_pixels": int(xs.size), "B_definition": "peak (amplitude) flux density, mT",
            "frequency_Hz": 10e6}


def rac_curve(im):
    """Fig. 9b: AC resistance (mOhm) vs frequency (MHz) of the 8.2 mOhm two-turn segment."""
    roi = scale_roi((3620, 4680, 2040, 2660), im)
    rows, cols, _, _ = frame_grid(im, roi)
    yt, yb = rows[0], rows[-1]                            # 500 and 0 mOhm
    xl, xr = cols[0], cols[-1]                            # 0 and 100 MHz
    gray = im.sum(axis=2) // 3
    fq = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 98]
    out = []
    for f in fq:
        x = int(round(xl + f * (xr - xl) / 100.0))
        d = np.flatnonzero(gray[int(yt) + 4:int(yb) - 3, x] < 90) + int(yt) + 4
        if d.size == 0:
            out.append(None)
            continue
        c = np.split(d, np.flatnonzero(np.diff(d) > 3) + 1)[0]      # topmost = the curve
        out.append(round(float((yb - c.mean()) * 500.0 / (yb - yt)), 2))
    return {"f_MHz": fq, "R_ac_mOhm": out, "R_dc_mOhm": 8.2,
            "note": "points below 3 MHz are hidden by the 8.2 mOhm label arrow and not read"}


# Ferroxcube 3F4 Fig. 7 (black on black gridlines): read on a 400-dpi render, y scale
# 2.2225 px per kW/m3 (0 at pixel 970, 400 at pixel 81 of the crop). 500 kHz / 50 mT curve.
FERRITE_3F4_500k_50mT = {"T_C": [0, 20, 40, 60, 80, 100, 120],
                         "Pv_kW_m3": [275.8, 238.5, 203.8, 181.0, 166.5, 176.8, 207.4]}
FERRITE_3F4_1M_30mT = {"T_C": [0, 20, 40, 60, 70, 80, 100, 120],
                       "Pv_kW_m3": [161.0, 147.0, 134.0, 125.0, 123.5, 124.0, 134.0, 155.0]}


def main():
    missing = [k for k, p in PDF.items() if not p.exists()]
    if missing:
        sys.exit(f"missing source PDFs: {missing}")
    tmp = Path(tempfile.mkdtemp(prefix="omitloss_digitize_"))
    res = {"_provenance": {"method": __doc__.strip().splitlines()[0], "dpi": DPI,
                           "pdf": {k: str(v) for k, v in PDF.items()}, "url": URL}}
    im57 = render(PDF["EPC2057"], 3, tmp)
    res["EPC2057_reverse"] = epc_reverse(
        "EPC2057", im57, (450, 2480, 4300, 5850), [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5],
        [10, 20, 30, 40, 50, 60], [0.0, 5.0], exclude=[(700, 1300, 4500, 4950)])
    res["EPC2057_reverse"]["datasheet_table"] = "V_SD = 1.4 V typ at I_S = 0.5 A, V_GS = 0 (Rev. Apr 8 2025)"
    vq = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35, 40, 45]
    res["EPC2057_qoss"] = epc_qoss("EPC2057", im57, (450, 2480, 2400, 3950), [10, 20, 30, 40],
                                   [2.4, 4.8, 7.2, 9.6], [0, 50], [12.0, 0.0], vq,
                                   exclude=[(990, 1330, 3015, 3050)])
    im90 = render(PDF["EPC2090"], 3, tmp)
    res["EPC2090_reverse"] = epc_reverse(
        "EPC2090", im90, (450, 2480, 4300, 5850), [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5],
        [20, 40, 60, 80, 100, 120], [0.0, 5.0], exclude=[(800, 1200, 4600, 4980)])
    res["EPC2090_reverse"]["datasheet_table"] = "V_SD = 1.5 V typ at I_S = 0.5 A, V_GS = 0 (Rev. Dec 19 2024)"
    vq90 = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 35, 40, 50, 60]
    res["EPC2090_qoss"] = epc_qoss("EPC2090", im90, (450, 2480, 2450, 3990), [25, 50, 75],
                                   [12, 24, 36], [0, 100], None, vq90,
                                   exclude=[(1000, 1560, 3070, 3100)])
    res["EPC2090_qoss"]["note"] = ("left axis labelled 0/12/24/36/'40': gridlines are equally "
                                   "spaced at 12 nC, so the top is 48 nC; calibration uses the "
                                   "gridlines only (datasheet Q_OSS = 27 nC typ at 50 V)")
    im14 = render(PDF["EPC2014C"], 3, tmp)
    res["EPC2014C_reverse"] = epc_reverse(
        "EPC2014C", im14, (2800, 4800, 2560, 4020), [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5],
        [15, 30, 45], [0.5, 5.0], exclude=[(3200, 3700, 2700, 3150)])
    res["EPC2014C_reverse"]["datasheet_table"] = "V_SD = 1.8 V typ at I_S = 0.5 A, V_GS = 0 (Rev. May 22 2021)"
    res["EPC2014C_coss"] = epc2014c_coss(im14)
    imp5 = render(PDF["IND_SRC"], 5, tmp)
    res["TYM5_loss_10MHz"] = tym5_loss(imp5)
    imp6 = render(PDF["IND_SRC"], 6, tmp)
    res["segment_Rac"] = rac_curve(imp6)
    res["ferrite_3F4_temperature"] = {"500kHz_50mT": FERRITE_3F4_500k_50mT,
                                      "1MHz_30mT": FERRITE_3F4_1M_30mT,
                                      "source": URL["3F4"] + " Fig. 7 (2008 Sep 01)"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1))
    print("wrote", OUT)
    for k in ("EPC2057_reverse", "EPC2090_reverse", "EPC2014C_reverse"):
        print(k, res[k]["linear_fit_3_12A"])
    print("TY-M5", res["TYM5_loss_10MHz"])


if __name__ == "__main__":
    main()
