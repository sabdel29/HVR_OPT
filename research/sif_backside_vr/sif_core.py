"""Si-IF backside VR study -- engine overlay (catalog parts, one tier, core loss).

Side study (not part of the TCPMT paper): off-the-shelf power components mounted side by side on
the wafer backside of a silicon interconnect fabric, power to the top through through-wafer vias.

The synthesis engine Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py is imported READ-ONLY;
nothing in it is changed. Its rules are selected by the environment before the import:
corrected capacitor rule (derating 0.8, 10 % effective-capacitance ripple at 105 C, ESR(f)),
switch stress rule (derating 0.9), corrected C_OSS, datasheet R_G, body footprints, packing
on, one tier (HVR_MAX_TIERS=1). Everything study-specific is passed through the engine's
existing objects and functions:

  * libraries     catalog inductors and Murata MLCCs as subclasses of the engine's Inductor and
                  Capacitor (extra fields: body x/y, rated currents, core-loss model, price);
                  the MLCC vendor tables are added to the engine's vendor dictionary at run time
  * topologies    the engine's family (N >= 2, 2 <= K <= N, K_A = ceil(K/2)) plus the plain buck
                  N = 1, K = 1, B = [1], D = V_out/V_in, which the generator does not emit; the
                  engine's loss expressions reduce exactly to the buck there (conduction
                  I^2 [D R_HS + (1 - D) R_LS + R_L], overlap at V_in, C_OSS E_HS(V_in) +
                  Q_LS(V_in) V_in - E_LS(V_in), no flying capacitor)
  * selection     the engine's decomposition (_optimize_mixed): for an inductor, capacitor and
                  f_sw the loss is A(hs) + B(ls) + C; this module adds the inductor core loss to
                  C and keeps every gate of the engine (current ripple < 0.5 I, output ripple
                  < 0.25 V with 50 uF, inductor f_max, flying-capacitor ripple and ESR(f),
                  device voltage and current screens, I_sat >= max(B) I / N)
  * extra gates   catalog ratings (switchable): inductor peak current I_dc + dI_L/2 <= I_sat and
                  inductor RMS current <= I_rms
  * placement     all parts of a cell (N HS, K LS, K inductors, N - 1 flying capacitors, plus
                  optional driver/decoupling overhead) in ONE tier of the square cell of side
                  sqrt(I_cell / J), every part grown by the keep-out (half to the cell edge), by the
                  engine's own placement test (_multiset_fits: exact for one part type and for up
                  to three parts, guillotine-exact up to six, MaxRects beyond); where that finds no
                  placement, further MaxRects orderings (engine's _maxrects) are tried -- every
                  accepted placement is constructive, so a feasible verdict is always real
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from dataclasses import dataclass, field, replace
from typing import Optional

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
ENGINE_DIR = os.path.join(REPO, "Scalable_Integrated_VR", "src")
EPC_CSV = os.path.join(REPO, "Scalable_Integrated_VR", "EPC-Product-Table.csv")

# engine rules for this study: the engine's defaults except one tier and the keep-out (the
# keep-out is passed explicitly to every placement call below; the variable only documents it)
ENGINE_ENV = {
    "HVR_CAP_RULE": "stress", "HVR_CAP_DERATING": "0.8", "HVR_CAP_RIPPLE": "1",
    "HVR_CAP_RIPPLE_MAX": "0.10", "HVR_CAP_T_DESIGN": "105", "HVR_CAP_ESR_F": "1",
    "HVR_SW_RULE": "stress", "HVR_SW_DERATING": "0.9", "HVR_COSS_RULE": "corrected",
    "HVR_PACK_RULE": "on", "HVR_PACK_KEEPOUT_UM": "100", "HVR_RG_RULE": "datasheet",
    "HVR_FOOTPRINT_RULE": "body", "HVR_TIER_RULE": "mixed", "HVR_MAX_TIERS": "1",
}
for _k, _v in ENGINE_ENV.items():
    os.environ[_k] = _v
os.environ.pop("HVR_CAP_MAX_HEIGHT_UM", None)
sys.dont_write_bytecode = True                      # never write .pyc into the engine directory
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)
import HVR_FULL_OPT_EPC_V2 as H                     # noqa: E402

V_GS = 5.0
V_TH, V_PL, R_DRV = 1.0, 1.6, 0.7                   # engine constants (compute_total_loss)
C_OUT_F = 50e-6                                     # engine constant (output-ripple gate)
RIPPLE_FACTOR = 0.5                                 # |dI_out| < 0.5 I_cell (DSE driver value)
V_RIPPLE_FRAC = 0.25                                # dV_out < 0.25 V_out (DSE driver value)


# ============================================================ library classes
@dataclass
class CatalogInductor(H.Inductor):
    """Engine Inductor + catalog fields. part_dims_mm() reads pkg_x_mm / pkg_y_mm."""
    pkg_x_mm: float = float("nan")
    pkg_y_mm: float = float("nan")
    i_rms_a: float = float("nan")
    vendor: str = ""
    series: str = ""
    part_number: str = ""
    core_model: dict = field(default_factory=dict)
    price_usd: float = float("nan")
    dcr_typ_mohm: float = float("nan")


@dataclass
class CatalogCapacitor(H.Capacitor):
    pkg_x_mm: float = float("nan")
    pkg_y_mm: float = float("nan")
    price_usd: float = float("nan")
    dielectric: str = ""
    size_inch: str = ""


@dataclass
class SimplePart:
    """Overhead part (gate driver, bootstrap or input capacitor) for the placement test."""
    name: str
    pkg_x_mm: float
    pkg_y_mm: float
    height_um: float = 1000.0
    price_usd: float = float("nan")
    footprint_mm2: float = float("nan")


# ============================================================ core loss
def _igse_ki(k, alpha, beta):
    th = np.linspace(0.0, 2.0 * np.pi, 20001)
    integ = np.trapezoid(np.abs(np.cos(th)) ** alpha, th)
    return k / ((2.0 * np.pi) ** (alpha - 1.0) * integ * 2.0 ** (beta - alpha))


def duty_factor(D, alpha):
    """iGSE factor of a two-slope (PWM) flux waveform relative to the symmetric (D = 0.5) one:
    [D^(1-a) + (1-D)^(1-a)] / [2 * 0.5^(1-a)]."""
    D = min(max(D, 1e-4), 1 - 1e-4)
    return (D ** (1 - alpha) + (1 - D) ** (1 - alpha)) / (2.0 * 0.5 ** (1 - alpha))


def core_loss_w(ind, dI_pp, f, D):
    """Core loss (W) of one inductor carrying a triangular ripple dI_pp (A, peak to peak) at f
    (Hz) with duty D. Models (ind.core_model["type"]):
      "igse"     material Steinmetz (k [W/m^3, f in Hz, B in T], alpha, beta) through the iGSE,
                 with dB_pp = B_ref * dI_pp / I_ref (linear core below saturation: B_ref at I_ref,
                 e.g. the saturation flux at I_sat) and core volume V_core (m^3)
      "kfactor"  vendor form (Eaton/Coiltronics): B_pp[G] = K * L[uH] * dI_pp, P[W] = a f^x B_pp^y
                 (f in the unit given), measured with symmetric square-wave drive -> duty factor
      "partfit"  P[W] = c f^alpha dI_pp^beta (fit to vendor loss data, symmetric drive) -> duty
      "none"     0
    """
    m = getattr(ind, "core_model", None) or {}
    t = m.get("type", "none")
    dI = np.abs(np.asarray(dI_pp, dtype=float))
    f = np.asarray(f, dtype=float)
    if t == "none":
        return np.zeros(np.broadcast(dI, f).shape)
    if t == "igse":
        a, b = m["alpha"], m["beta"]
        ki = m.get("_ki")
        if ki is None:
            ki = m["_ki"] = _igse_ki(m["k"], a, b)
        dB = m["B_ref_T"] * dI / m["I_ref_A"]
        Dc = min(max(D, 1e-4), 1 - 1e-4)
        return m["V_core_m3"] * ki * dB ** b * f ** a * (Dc ** (1 - a) + (1 - Dc) ** (1 - a))
    if t == "kfactor":
        fs = f * m.get("f_scale", 1.0)              # e.g. 1e-3 for kHz
        Bpp = m["K"] * (ind.l_nh * 1e-3) * dI
        return m["a"] * fs ** m["x"] * Bpp ** m["y"] * duty_factor(D, m["x"])
    if t == "partfit":
        fs = f * m.get("f_scale", 1.0)
        return m["c"] * fs ** m["alpha"] * dI ** m["beta"] * duty_factor(D, m["alpha"])
    if t == "kfactor_table":
        return _kfactor_table(ind, m, dI, f, D)
    if t == "steinmetz_rows":
        return _steinmetz_rows(m, dI, f, D)
    raise ValueError(f"unknown core model {t!r}")


def _cos_integral(alpha):
    """int_0^2pi |cos t|^alpha dt = 2 sqrt(pi) Gamma((alpha+1)/2) / Gamma(alpha/2 + 1)."""
    return 2.0 * math.sqrt(math.pi) * math.exp(math.lgamma((alpha + 1) / 2.0)
                                               - math.lgamma(alpha / 2.0 + 1.0))


def igse_ratio(D, alpha, beta):
    """Loss of a two-slope (PWM) flux waveform of duty D over the sinusoidal Steinmetz loss at
    the same peak-to-peak flux (iGSE, Venkatachalam et al. 2002):
    (k_i / k) 2^beta [D^(1-alpha) + (1-D)^(1-alpha)],
    k_i / k = 1 / ((2 pi)^(alpha-1) int|cos|^alpha 2^(beta-alpha))."""
    D = min(max(float(D), 1e-4), 1 - 1e-4)
    alpha = np.asarray(alpha, dtype=float)
    beta = np.asarray(beta, dtype=float)
    ci = np.vectorize(_cos_integral)(alpha)
    ki_k = 1.0 / ((2.0 * np.pi) ** (alpha - 1.0) * ci * 2.0 ** (beta - alpha))
    return ki_k * 2.0 ** beta * (D ** (1.0 - alpha) + (1.0 - D) ** (1.0 - alpha))


def _kfactor_table(ind, m, dI, f, D):
    """Vendor K-factor chart: B_pp[G] = K L[nH] dI 1e-3; P = a(f) B^b(f) per chart frequency,
    ln P interpolated linearly in ln f; below the lowest chart frequency the energy per cycle is
    held (P ~ f); above the highest the last segment's slope continues. Sinusoidal chart ->
    PWM by the iGSE with the local exponents."""
    dI, f = np.broadcast_arrays(np.asarray(dI, dtype=float), np.asarray(f, dtype=float))
    tab = np.array(m["table"], dtype=float)
    fc, a, b = tab[:, 0], tab[:, 1], tab[:, 2]
    lfc = np.log(fc)
    B = np.maximum(m["K_G_per_nH_A"] * ind.l_nh * 1e-3 * dI, 1e-30)
    lB = np.log(B)
    lf = np.log(f)
    i = np.clip(np.searchsorted(lfc, lf) - 1, 0, len(fc) - 2)
    lP1 = np.log(a[i]) + b[i] * lB
    lP2 = np.log(a[i + 1]) + b[i + 1] * lB
    t = (lf - lfc[i]) / (lfc[i + 1] - lfc[i])
    seg_alpha = (lP2 - lP1) / (lfc[i + 1] - lfc[i])
    lP = lP1 + t * (lP2 - lP1)
    beta = b[i] + np.clip(t, 0.0, 1.0) * (b[i + 1] - b[i])
    alpha = seg_alpha.copy()
    lo = lf < lfc[0]
    if lo.any():
        lP0 = np.log(a[0]) + b[0] * lB
        lP = np.where(lo, lP0 + (lf - lfc[0]), lP)
        alpha = np.where(lo, 1.0, alpha)
        beta = np.where(lo, b[0], beta)
    alpha = np.clip(alpha, 1.0, 3.0)
    P = np.exp(lP) * igse_ratio(D, alpha, beta)
    return np.where(dI > 0, P, 0.0)


def _steinmetz_rows(m, dI, f, D):
    """Material Steinmetz rows [f_lo, f_hi, k (kW/m^3), alpha, beta] with peak flux
    B_pk = B_ref dI / (2 I_ref) and core volume V_core; sinusoidal -> PWM by the iGSE."""
    dI, f = np.broadcast_arrays(np.asarray(dI, dtype=float), np.asarray(f, dtype=float))
    rows = np.array(m["rows"], dtype=float)
    j = np.clip(np.searchsorted(rows[:, 0], f, side="right") - 1, 0, len(rows) - 1)
    k, al, be = rows[j, 2], rows[j, 3], rows[j, 4]
    B_pk = m["B_ref_T"] * dI / m["I_ref_A"] / 2.0
    P = 1e3 * k * f ** al * np.maximum(B_pk, 0.0) ** be * m["V_core_m3"]
    return P * igse_ratio(D, al, be)


# ============================================================ libraries
def device_prices():
    """Commercial unit prices of the EPC parts: the product table's price column (it matches
    Digi-Key's largest tape-and-reel break, prices_raw.json epc_check), completed by the largest
    break from prices_raw.json for commercial parts the table lacks."""
    import pandas as pd
    raw = pd.read_csv(EPC_CSV, dtype=str, encoding="utf-8-sig")
    raw.columns = raw.columns.str.strip()
    pcol = [c for c in raw.columns if c.lower().startswith("price")][0]
    price, src = {}, {}
    for _, r in raw.iterrows():
        try:
            v = float(str(r[pcol]).replace(",", ""))
        except (TypeError, ValueError):
            continue
        if math.isfinite(v) and v > 0:
            price[str(r["PartNumber"]).strip()] = v
            src[str(r["PartNumber"]).strip()] = "EPC product table"
    pr = os.path.join(HERE, "prices_raw.json")
    if os.path.isfile(pr):
        for e in json.load(open(pr)).get("epc_missing", []):
            if e.get("price") and not e["part"].startswith("EPC7") and e["part"] not in price:
                price[e["part"]] = float(e["price"])
                src[e["part"]] = f"Digi-Key largest break ({e.get('qty')} pcs)"
    return price, src


def load_devices(commercial_only=True):
    """EPC catalog table through the engine loader. commercial_only: drop the rad-hard EPC Space
    parts (EPC7xxx, sold in units of 1-10 at $170-310) and parts without a commercial price."""
    df = H.load_epc_devices(EPC_CSV, V_gs_op=V_GS)
    price, _src = device_prices()
    if commercial_only:
        keep = [(not p.startswith("EPC7")) and (p in price) for p in df["PartNumber"]]
        dropped = sorted(df["PartNumber"][[not k for k in keep]])
        df = df[keep].reset_index(drop=True)
        DEVICE_FILTER_NOTE["dropped"] = dropped
    return df, price


DEVICE_FILTER_NOTE: dict = {}


def inject_mlcc_vendor_data(path=os.path.join(HERE, "mlcc_vendor_data.json")):
    """Add the catalog MLCC vendor tables to the engine's vendor dictionary (run time only;
    the engine's own entries are kept where a part is in both)."""
    H._vendor("__load__")                           # make the engine load its own table first
    data = json.load(open(path))["parts"]
    for pn, rec in data.items():
        H._VENDOR.setdefault(pn, rec)
    return data


def build_capacitor_library(path=os.path.join(HERE, "mlcc_vendor_data.json"), prices=None):
    data = inject_mlcc_vendor_data(path)
    prices = prices or {}
    lib = []
    for pn, rec in data.items():
        c0 = float(np.interp(0.0, *zip(*rec["c_v_25c"])))
        nominal = _nominal_uf(rec.get("capacitance"), c0)
        esr_nom = H.cap_esr_mohm(type("C", (), {"vendor_part": pn, "esr_mohm": 5.0})(),
                                 1e6, 0.0)
        name = f"Murata-{pn}-{_fmt_uf(nominal)}-{int(rec['rated_voltage_V'])}V"
        lib.append(CatalogCapacitor(
            name=name, technology="MLCC", c_uf=nominal, esr_mohm=esr_nom, esl_ph=0.0,
            v_max=float(rec["rated_voltage_V"]), footprint_mm2=round(rec["L_mm"] * rec["W_mm"], 6),
            source=f"Murata {pn} ({rec['size_inch']}, {rec['dielectric']}); {rec['url']}",
            vendor_part=pn, height_um=float(rec["max_height_um"]),
            pkg_x_mm=float(rec["L_mm"]), pkg_y_mm=float(rec["W_mm"]),
            price_usd=float(prices.get(pn, float("nan"))), dielectric=rec["dielectric"],
            size_inch=rec["size_inch"]))
    return lib


def _nominal_uf(s, fallback):
    if not s:
        return fallback
    s = str(s).replace("μ", "u").replace("µ", "u").replace(",", "")
    import re
    m = re.match(r"\s*([\d.]+)\s*([upn]?)F", s)
    if not m:
        return fallback
    v = float(m.group(1))
    return v * {"u": 1.0, "n": 1e-3, "p": 1e-6, "": 1e6}[m.group(2)]


def _fmt_uf(c):
    return f"{c:g}uF"


def build_inductor_library(path=os.path.join(HERE, "inductor_library.json"), dcr="max",
                           isat="vendor"):
    """Catalog inductors from the curated library JSON (see build_inductor_library.py).
    dcr: "max" (25 C maximum) or "typ"; isat: "vendor" (the vendor's primary rating: 30 % drop
    for composites, 20 % for ferrites) or "20" (20 % drop for every part)."""
    d = json.load(open(path))
    lib = []
    for p in d["parts"]:
        r = p["DCR_max_mohm"] if (dcr == "max" and p.get("DCR_max_mohm")) else p["DCR_typ_mohm"]
        if r is None:
            r = p["DCR_max_mohm"]
        if isat == "20" and p.get("Isat20_A"):
            p = dict(p, Isat_A=p["Isat20_A"])
        x, y, h = p["length_mm"], p["width_mm"], p["height_mm"]
        lib.append(CatalogInductor(
            name=f"{p['vendor']}-{p['part_number']}", category="catalog_smd",
            l_nh=float(p["L_nH"]), r_dcr_mohm=float(r), i_sat_a=float(p["Isat_A"]),
            q_factor=float("nan"), footprint_mm2=round(x * y, 6), height_um=1e3 * h,
            f_max_mhz=float(p.get("f_max_MHz") or 3.0), coupling_k=0.0,
            core_loss_k=float("nan"), core_loss_alpha=float("nan"),
            source=p.get("datasheet_url", ""), pkg_x_mm=float(x), pkg_y_mm=float(y),
            i_rms_a=float(p["Irms_A"]) if p.get("Irms_A") else float("nan"),
            vendor=p["vendor"], series=p["series"], part_number=p["part_number"],
            core_model=dict(p["core_model"]), price_usd=float(p.get("price_usd") or float("nan")),
            dcr_typ_mohm=float(p.get("DCR_typ_mohm") or float("nan"))))
    return lib


# ============================================================ topologies
def arch_buck(V_in, V_out):
    return H.VRArchitecture(N=1, K=1, K_A=1, B_array=[1], D=V_out / V_in, component_count=3)


def architectures(V_in, V_out, n_max, d_max=0.5):
    """Plain buck + the engine's family with N <= n_max and D = N V_out / V_in <= d_max."""
    fam = H.generate_architectures(1, 1, 1, 1, 4 * n_max - 1, V_out, V_in)
    fam = [a for a in fam if a.N <= n_max and a.D <= d_max + 1e-12]
    return [arch_buck(V_in, V_out)] + sorted(fam, key=lambda a: (a.N, a.K))


# ============================================================ placement (one tier)
_FIT_CACHE: dict = {}
N_EXTRA_ORDERS = 16


def cell_classes(arch, hs, ls, ind, cap, ko_mm, extra=()):
    """((a, b), count) per distinct body (grown by the keep-out), identical bodies merged."""
    cls = {}
    for n, part in ((arch.N, hs), (arch.K, ls), (arch.K, ind), (arch.N - 1, cap)) + tuple(extra):
        if n <= 0 or part is None:
            continue
        x, y = H.part_dims_mm(part)
        d = (round(max(x, y) + ko_mm, 9), round(min(x, y) + ko_mm, 9))
        cls[d] = cls.get(d, 0) + n
    return tuple(sorted(cls.items()))


def fits_one_tier(cd, side):
    """Do all parts cd = ((a, b), count) place in one side x side tier?"""
    side = round(side, 9)
    key = (cd, side)
    if key in _FIT_CACHE:
        return _FIT_CACHE[key]
    eps = H._PACK_EPS
    items = [(a, b, i) for i, ((a, b), c) in enumerate(cd) for _ in range(c)]
    if (sum(a * b for a, b, _ in items) > side * side + eps
            or any(a > side + eps for a, b, _ in items)):
        _FIT_CACHE[key] = False
        return False
    res = bool(H._multiset_fits(cd, side))
    if not res and len(cd) > 1 and len(items) >= 5:
        rng = random.Random(len(items) * 1000003 + int(side * 1e6))
        it = list(items)
        for _ in range(N_EXTRA_ORDERS):
            rng.shuffle(it)
            if H._maxrects(it, side) is not None:
                res = True
                break
    _FIT_CACHE[key] = res
    return res


def placement(cd, side):
    """Coordinates of a one-tier placement (for the report), or None."""
    side = round(side, 9)
    tagged = [((a, b), c, i) for i, ((a, b), c) in enumerate(cd)]
    pl = H.tier_placement(tagged, side) if len(cd) > 0 else []
    if pl is not None:
        return pl
    items = [(a, b, i) for i, ((a, b), c) in enumerate(cd) for _ in range(c)]
    rng = random.Random(len(items) * 1000003 + int(side * 1e6))
    for _ in range(N_EXTRA_ORDERS):
        rng.shuffle(items)
        p = H._maxrects(items, side)
        if p is not None:
            return p
    return None


_MINSIDE_CACHE: dict = {}


def min_side(cd, tol=2e-3):
    """Smallest square side (mm) in which cd places in one tier (bisection on the placement
    test; the test is constructive, so the result is an upper bound on the true minimum).
    Cached: the geometry does not depend on the cell current."""
    if cd in _MINSIDE_CACHE:
        return _MINSIDE_CACHE[cd]
    area = sum(a * b * c for (a, b), c in cd)
    lo = max(math.sqrt(area), max(a for (a, b), c in cd))
    if fits_one_tier(cd, lo):
        _MINSIDE_CACHE[cd] = lo
        return lo
    hi, cap = 1.25 * lo, sum(a * c for (a, b), c in cd) + 1.0
    while not fits_one_tier(cd, hi):
        lo, hi = hi, hi * 1.25
        if hi > cap:
            _MINSIDE_CACHE[cd] = float("inf")
            return float("inf")
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if fits_one_tier(cd, mid):
            hi = mid
        else:
            lo = mid
    _MINSIDE_CACHE[cd] = hi
    return hi


# ------------------------------------------------------------ rectangular cells (sensitivity)
# The engine's cell is a square of side sqrt(I / J). Rectangular cells tile the backside as well;
# with a few large parts the square leaves a strip unused. The rectangular variant accepts any
# W x H = I / J with 1 <= W / H <= ASPECT_MAX (both orientations) and uses the same placement
# primitives: the engine's guillotine frontier (exact for guillotine layouts) up to six parts,
# a MaxRects placement in the rectangle (the engine's algorithm, written for W x H) beyond.
ASPECTS = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
ASPECT_MAX = 3.0
_RECT_CACHE: dict = {}
_MINRECT_CACHE: dict = {}


def _maxrects_wh(items, W, H_):
    """The engine's MaxRects (best short-side fit, rotation allowed) in a W x H rectangle."""
    eps = H._PACK_EPS
    free, out = [(0.0, 0.0, W, H_)], []
    for a, b, tag in items:
        best = None
        for fx, fy, fw, fh in free:
            for w, h in ((a, b), (b, a)):
                if w <= fw + eps and h <= fh + eps:
                    k = (min(fw - w, fh - h), max(fw - w, fh - h), fy, fx)
                    if best is None or k < best[0]:
                        best = (k, fx, fy, w, h)
        if best is None:
            return None
        _, x, y, w, h = best
        r = (x, y, w, h)
        out.append((x, y, w, h, tag))
        nf = []
        for f in free:
            if not H._overlap(f, r):
                nf.append(f)
                continue
            fx, fy, fw, fh = f
            if x > fx + eps:
                nf.append((fx, fy, x - fx, fh))
            if x + w < fx + fw - eps:
                nf.append((x + w, fy, fx + fw - x - w, fh))
            if y > fy + eps:
                nf.append((fx, fy, fw, y - fy))
            if y + h < fy + fh - eps:
                nf.append((fx, y + h, fw, fy + fh - y - h))
        free = [f for i, f in enumerate(nf)
                if not any(j != i and H._contains(g, f) and (g != f or j < i)
                           for j, g in enumerate(nf))]
    return out


def fits_rect(cd, W, H_):
    """Do all parts cd place in one W x H tier (W >= H)?"""
    W, H_ = round(max(W, H_), 9), round(min(W, H_), 9)
    key = (cd, W, H_)
    if key in _RECT_CACHE:
        return _RECT_CACHE[key]
    eps = H._PACK_EPS
    items = [(a, b, i) for i, ((a, b), c) in enumerate(cd) for _ in range(c)]
    res = False
    if (sum(a * b for a, b, _ in items) <= W * H_ + eps
            and all(a <= W + eps and b <= H_ + eps for a, b, _ in items)):
        if len(items) <= H.FRONTIER_MAX_ITEMS:
            fr = H._frontier(tuple(d for d, _ in cd), tuple(c for _, c in cd), W)
            res = any((w <= W + eps and h <= H_ + eps) or (h <= W + eps and w <= H_ + eps)
                      for w, h, _ in fr)
        if not res:
            orders = [lambda t: -t[0] * t[1], lambda t: -t[0], lambda t: -t[1],
                      lambda t: -(t[0] + t[1])]
            for k in orders:
                if _maxrects_wh(sorted(items, key=k), W, H_) is not None:
                    res = True
                    break
            if not res and len(items) >= 5:
                rng = random.Random(len(items) * 1000003 + int(W * 1e6) + int(H_ * 7e5))
                it = list(items)
                for _ in range(N_EXTRA_ORDERS):
                    rng.shuffle(it)
                    if _maxrects_wh(it, W, H_) is not None:
                        res = True
                        break
    _RECT_CACHE[key] = res
    return res


def fits_area(cd, area_mm2, aspects=ASPECTS):
    """Is there a cell W x H = area with W / H in aspects in which cd places? Aspect 1 uses the
    square test (fits_one_tier), so a rectangular verdict is never worse than the square one."""
    if fits_one_tier(cd, math.sqrt(area_mm2)):
        return True
    return any(fits_rect(cd, math.sqrt(area_mm2 * r), math.sqrt(area_mm2 / r))
               for r in aspects if r > 1.0)


def min_rect(cd, aspects=ASPECTS, tol=2e-3):
    """Smallest cell area (mm^2) over the aspect ratios, and its (W, H)."""
    if cd in _MINRECT_CACHE:
        return _MINRECT_CACHE[cd]
    sq = min_side(cd)                                 # aspect 1: the square result
    best = (sq * sq, sq, sq) if np.isfinite(sq) else (float("inf"), None, None)
    aspects = tuple(r for r in aspects if r > 1.0)
    amin = sum(a * b * c for (a, b), c in cd)
    amax_dim = max(a for (a, b), c in cd)
    bmax_dim = max(b for (a, b), c in cd)
    for r in aspects:
        # scale s: W = s sqrt(r), H = s / sqrt(r); lower bound from area and part lengths
        lo = max(math.sqrt(amin), amax_dim / math.sqrt(r), bmax_dim * math.sqrt(r))
        if lo ** 2 >= best[0]:
            continue
        f = lambda s: fits_rect(cd, s * math.sqrt(r), s / math.sqrt(r))  # noqa: E731
        if f(lo):
            hi = lo
        else:
            hi = lo * 1.25
            while not f(hi):
                lo, hi = hi, hi * 1.25
                if hi > 1e3:
                    break
            if hi > 1e3:
                continue
            while hi - lo > tol and lo ** 2 < best[0]:
                mid = 0.5 * (lo + hi)
                if f(mid):
                    hi = mid
                else:
                    lo = mid
        if hi ** 2 < best[0]:
            best = (hi ** 2, hi * math.sqrt(r), hi / math.sqrt(r))
    _MINRECT_CACHE[cd] = best
    return best


# ============================================================ loss tables
@dataclass
class Opts:
    peak_isat: bool = True          # I_L,dc + dI_L/2 <= I_sat
    irms: bool = True               # I_L,rms <= I_rms rating
    core_loss: bool = True
    ton_min_ns: float = 0.0         # minimum high-side on-time D / f_sw (0: no limit)
    core_scale: float = 1.0         # multiplier on every core-loss model (sensitivity)


def _dev_arrays(devs, side, arch, V_in, V_out):
    N, K = arch.N, arch.K
    v1, v2 = V_in / N, H.stacked_swing(N, V_in)
    if side == "hs":
        R = np.array([d.R_DS_ON for d in devs])
        Qs = np.array([d.Q_GD + d.Q_G for d in devs])
        Ig = (V_GS - 0.5 * (V_TH + V_PL)) / (np.array([H.gate_resistance(d) for d in devs]) + R_DRV)
        CG = np.array([d.C_G for d in devs])
        E = np.array([N * H.e_oss_at(d, v1) + (N - 1) * (v2 * (H.q_oss_at(d, v2) - H.q_oss_at(d, v1))
                                                         - (H.e_oss_at(d, v2) - H.e_oss_at(d, v1)))
                      for d in devs])
        return R, Qs / Ig, CG, E
    R = np.array([d.R_DS_ON for d in devs])
    CG = np.array([d.C_G for d in devs])
    E = np.array([K * (H.q_oss_at(d, v1) * v1 - H.e_oss_at(d, v1)) for d in devs])
    return R, None, CG, E


def _groups(devs):
    g = {}
    for i, d in enumerate(devs):
        g.setdefault(tuple(sorted(H.part_dims_mm(d))), []).append(i)
    keys = list(g)
    return keys, [np.array(g[k]) for k in keys]


@dataclass
class Table:
    arch: object
    I: float
    V_in: float
    V_out: float
    hs: list
    ls: list
    inds: list
    caps: list
    fgrid: np.ndarray
    hkeys: list
    lkeys: list
    loss: np.ndarray                # (n_ind, n_cap, n_gh, n_gl), inf where no valid f
    fidx: np.ndarray                # best f index per entry
    ah: list                        # per ind: (nf, n_gh) best hs index (global) per f
    al: list                        # per ind: (nf, n_gl)
    n_valid_f: int = 0


def build_table(arch, I, V_in, V_out, df, ind_lib, cap_lib, fgrid, opts: Opts):
    """Minimum loss over f for every (inductor, capacitor, HS body group, LS body group)."""
    N, K, K_A, B, D = arch.N, arch.K, arch.K_A, arch.B_array, arch.D
    hs, ls = H.filter_candidate_devices(df, arch, V_in, V_out, V_GS, I, max(B))
    inds = H.filter_candidate_inductors(ind_lib, arch, I)
    if N > 1:
        caps = H.filter_candidate_capacitors(cap_lib, arch, V_in)
    else:
        caps = cap_lib[:1]                          # no flying capacitor: one placeholder
    if not hs or not ls or not inds or not caps:
        return None
    hkeys, hidx = _groups(hs)
    lkeys, lidx = _groups(ls)
    Rh, QIh, CGh, Eh = _dev_arrays(hs, "hs", arch, V_in, V_out)
    Rl, _, CGl, El = _dev_arrays(ls, "ls", arch, V_in, V_out)
    B_k, B_sum = B[-1], sum(b ** 2 for b in B)
    c_k = (4 * B_k - 1) if B_k > 1 else 3
    alpha = (V_in / (N ** 2 * V_out)) * B_sum + (2 * B_sum - c_k) / N
    IL_dc = max(B) * I / N
    v_c1 = (N - 1) * V_in / N
    # flying-capacitor ripple scales as 1/f: worst ratio at 1 Hz, and ESR(f) at the C_1 bias
    cap_r1 = np.array([H.flying_cap_ripple(arch, c, I, V_in, V_out, 1.0) if N > 1 else 0.0
                       for c in caps])
    nf = len(fgrid)
    cap_esr = np.zeros((len(caps), nf))
    for j, c in enumerate(caps):
        if N > 1 and H.CAP_ESR_F and getattr(c, "vendor_part", None):
            cap_esr[j] = [H.cap_esr_mohm(c, f, v_c1) * 1e-3 for f in fgrid]
        else:
            cap_esr[j] = c.esr_mohm * 1e-3
    ngh, ngl = len(hkeys), len(lkeys)
    loss = np.full((len(inds), len(caps), ngh, ngl), np.inf)
    fidx = np.zeros((len(inds), len(caps), ngh, ngl), dtype=np.int16)
    ah_all, al_all = [], []
    i_lim, v_lim = RIPPLE_FACTOR * I, V_RIPPLE_FRAC * V_out
    for ii, ind in enumerate(inds):
        L, R_L = ind.l_nh * 1e-9, ind.r_dcr_mohm * 1e-3
        boost = 1.0 + ind.coupling_k * max(K - 1, 0)
        fv = fgrid <= ind.f_max_mhz * 1e6 * (1 + 1e-12)
        f = fgrid
        d_raw = (D / (f * L)) * (V_in / N * K_A - V_out * K)
        d_eff = d_raw / boost
        ok = fv & (np.abs(d_eff) < i_lim) & (np.abs(d_eff) / (8.0 * f * C_OUT_F) < v_lim)
        if opts.ton_min_ns > 0:
            ok &= D / f >= opts.ton_min_ns * 1e-9 * (1 - 1e-12)
        dIL = (V_in / N - V_out) * D / (f * L)      # ripple of one inductor
        if opts.peak_isat:
            ok &= IL_dc + 0.5 * dIL <= ind.i_sat_a
        if opts.irms and np.isfinite(ind.i_rms_a):
            ok &= np.sqrt(IL_dc ** 2 + dIL ** 2 / 12.0) <= ind.i_rms_a
        ah_all.append(None)
        al_all.append(None)
        if not ok.any():
            continue
        I_rms = np.sqrt(I ** 2 + d_eff ** 2 / 12.0)
        kc = (V_out / V_in) * I_rms ** 2
        A = (kc[:, None] * Rh[None, :] + (f * (V_in / N - V_out) * I_rms)[:, None] * QIh[None, :]
             + f[:, None] * (N * CGh * V_GS ** 2 + Eh)[None, :])
        Bv = kc[:, None] * alpha * Rl[None, :] + f[:, None] * (K * CGl * V_GS ** 2 + El)[None, :]
        Amin = np.empty((nf, ngh))
        ah = np.empty((nf, ngh), dtype=np.int32)
        for g, ix in enumerate(hidx):
            sub = A[:, ix]
            k = np.argmin(sub, axis=1)
            ah[:, g] = ix[k]
            Amin[:, g] = sub[np.arange(nf), k]
        Bmin = np.empty((nf, ngl))
        al = np.empty((nf, ngl), dtype=np.int32)
        for g, ix in enumerate(lidx):
            sub = Bv[:, ix]
            k = np.argmin(sub, axis=1)
            al[:, g] = ix[k]
            Bmin[:, g] = sub[np.arange(nf), k]
        ah_all[-1], al_all[-1] = ah, al
        P_dcr = kc * (V_in / (N ** 2 * V_out)) * B_sum * R_L
        P_core = (opts.core_scale * K * core_loss_w(ind, dIL, f, D) if opts.core_loss
                  else 0.0 * f)
        base = Amin[:, :, None] + Bmin[:, None, :]          # (nf, ngh, ngl)
        for jj in range(len(caps)):
            okc = ok & (cap_r1[jj] / f <= H.CAP_RIPPLE_MAX)
            if not okc.any():
                continue
            C = P_dcr + kc * 2.0 * (1.0 - 1.0 / N) * cap_esr[jj] + P_core
            tot = base + C[:, None, None]
            tot[~okc] = np.inf
            k = np.argmin(tot, axis=0)
            loss[ii, jj] = np.take_along_axis(tot, k[None], axis=0)[0]
            fidx[ii, jj] = k
    return Table(arch, I, V_in, V_out, hs, ls, inds, caps, fgrid, hkeys, lkeys, loss, fidx,
                 ah_all, al_all, int(np.isfinite(loss).sum()))


# ============================================================ design evaluation
def evaluate(arch, hs, ls, ind, cap, I, V_in, V_out, f, opts: Opts = Opts()):
    """Full loss breakdown of one cell (W) by the engine's expressions + core loss."""
    N, K, K_A, B, D = arch.N, arch.K, arch.K_A, arch.B_array, arch.D
    cap_f = cap
    if N > 1 and H.CAP_ESR_F and getattr(cap, "vendor_part", None):
        cap_f = replace(cap, esr_mohm=H.cap_esr_mohm(cap, f, (N - 1) * V_in / N))
    lr = H.compute_total_loss(arch, H.LossModelInputs(hs_device=hs, ls_device=ls, inductor=ind,
                                                      capacitor=cap_f, I_out=I, V_out=V_out,
                                                      V_in=V_in, f_sw=f))
    boost = 1.0 + ind.coupling_k * max(K - 1, 0)
    d_raw = (D / (f * ind.l_nh * 1e-9)) * (V_in / N * K_A - V_out * K)
    I_rms = math.sqrt(I ** 2 + (d_raw / boost) ** 2 / 12.0)
    kc = (V_out / V_in) * I_rms ** 2
    B_k, B_sum = B[-1], sum(b ** 2 for b in B)
    c_k = (4 * B_k - 1) if B_k > 1 else 3
    alpha = (V_in / (N ** 2 * V_out)) * B_sum + (2 * B_sum - c_k) / N
    dIL = (V_in / N - V_out) * D / (f * ind.l_nh * 1e-9)
    p_core = (float(opts.core_scale * K * core_loss_w(ind, dIL, f, D)) if opts.core_loss
              else 0.0)
    br = {
        "cond_hs_W": kc * hs.R_DS_ON,
        "cond_ls_W": kc * alpha * ls.R_DS_ON,
        "cond_ind_dcr_W": kc * (V_in / (N ** 2 * V_out)) * B_sum * ind.r_dcr_mohm * 1e-3,
        "cond_cap_esr_W": kc * 2.0 * (1.0 - 1.0 / N) * cap_f.esr_mohm * 1e-3,
        "sw_overlap_W": lr.p_sw_hs,
        "gate_W": lr.p_sw_gd,
        "coss_W": lr.p_sw_coss,
        "ind_core_W": p_core,
    }
    cond = br["cond_hs_W"] + br["cond_ls_W"] + br["cond_ind_dcr_W"] + br["cond_cap_esr_W"]
    assert abs(cond - lr.p_cond) <= 1e-9 * max(1.0, abs(lr.p_cond)), (cond, lr.p_cond)
    IL_dc = max(B) * I / N
    return {
        "loss_cell_W": lr.total_loss + p_core, "engine_loss_cell_W": lr.total_loss,
        "breakdown_cell_W": br, "dI_out_pp_A": lr.delta_i_out, "dV_out_pp_V": lr.delta_v_out,
        "dI_L_pp_A": dIL, "I_L_dc_max_A": IL_dc, "I_L_pk_A": IL_dc + 0.5 * dIL,
        "I_L_rms_A": math.sqrt(IL_dc ** 2 + dIL ** 2 / 12.0),
        "t_on_ns": 1e9 * D / f, "cap_esr_mohm_at_fsw": cap_f.esr_mohm if N > 1 else 0.0,
        "flying_cap_ripple_frac": (H.flying_cap_ripple(arch, cap, I, V_in, V_out, f)
                                   if N > 1 else 0.0),
    }


# ============================================================ placement verification
def place_rect(cd, W, H_):
    """Coordinates of a placement of cd in W x H: [(x, y, w, h, class)] or None. Replays the
    tests that accept a design (guillotine frontier up to six parts, the engine's MaxRects under
    its four orderings, then the seeded extra orderings of fits_one_tier / fits_rect)."""
    W, H_ = round(max(W, H_), 9), round(min(W, H_), 9)      # as in the placement tests
    items = [(a, b, i) for i, ((a, b), c) in enumerate(cd) for _ in range(c)]
    types, counts = tuple(d for d, _ in cd), tuple(c for _, c in cd)
    if len(items) <= H.FRONTIER_MAX_ITEMS:
        for w, h, _ in H._frontier(types, counts, round(W, 9)):
            if w <= W + 1e-9 and h <= H_ + 1e-9:
                return H._frontier_place(types, counts, round(W, 9), w, h,
                                         tags=list(range(len(cd))))
            if h <= W + 1e-9 and w <= H_ + 1e-9:
                pl = H._frontier_place(types, counts, round(W, 9), w, h,
                                       tags=list(range(len(cd))))
                return [(y, x, hh, ww, t) for x, y, ww, hh, t in pl]
    if len(cd) == 1 and abs(W - H_) < 1e-9:
        pl = H.tier_placement([(cd[0][0], cd[0][1], 0)], round(W, 9))
        if pl is not None:
            return pl
    for k in (lambda t: -t[0] * t[1], lambda t: -t[0], lambda t: -t[1], lambda t: -(t[0] + t[1])):
        pl = _maxrects_wh(sorted(items, key=k), W, H_)
        if pl is not None:
            return pl
    seeds = [len(items) * 1000003 + int(W * 1e6) + int(H_ * 7e5)]
    if abs(W - H_) < 1e-9:
        seeds.append(len(items) * 1000003 + int(round(W, 9) * 1e6))
    for sd in seeds:
        rng = random.Random(sd)
        it = list(items)
        for _ in range(N_EXTRA_ORDERS):
            rng.shuffle(it)
            pl = _maxrects_wh(it, W, H_)
            if pl is not None:
                return pl
    return None


def verify_placement(pl, cd, W, H_, tol=1e-7):
    """Every part inside W x H, no two overlapping, and the multiset of bodies equal to cd."""
    if pl is None:
        return False
    W, H_ = max(W, H_), min(W, H_)
    got = {}
    for x, y, w, h, t in pl:
        if x < -tol or y < -tol or x + w > W + tol or y + h > H_ + tol:
            return False
        got[(round(max(w, h), 6), round(min(w, h), 6))] = got.get(
            (round(max(w, h), 6), round(min(w, h), 6)), 0) + 1
    want = {}
    for (a, b), c in cd:
        want[(round(a, 6), round(b, 6))] = want.get((round(a, 6), round(b, 6)), 0) + c
    if got != want:
        return False
    for i in range(len(pl)):
        for j in range(i + 1, len(pl)):
            a, b = pl[i], pl[j]
            if (a[0] < b[0] + b[2] - tol and b[0] < a[0] + a[2] - tol
                    and a[1] < b[1] + b[3] - tol and b[1] < a[1] + a[3] - tol):
                return False
    return True
