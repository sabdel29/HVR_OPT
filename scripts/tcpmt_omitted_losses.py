#!/usr/bin/env python3
"""TCPMT revision: the converter loss terms the EPEPS model omits, quantified per case and per
regulator count, and whether any architecture ranking or the regulator-count optimum moves.

Omitted terms (Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py compute_total_loss has none of
them): GaN dead-time (third-quadrant) conduction, inductor core loss, inductor AC winding
resistance, flying-capacitor dielectric loss.

Topology facts used (thesis Fig. hvr-arch / manuscript_v2 Fig. 2, cross-checked against the
model's own conduction terms, which this reading reproduces exactly):
  * four states per period, A (0..DT), OFF, B (T/2..T/2+DT), OFF;
  * every inductor branch has one low-side (LS) device; its switch node sits at V_in/N while
    its own phase conducts and is grounded otherwise, so the per-branch ripple is the buck
    ripple (V_in/N - V_out) D / (f L) -- not the model's summed output ripple;
  * each LS device has exactly TWO dead-time intervals per period: before its high-side (HS)
    turns on (it carries the branch valley current for the full dead time) and after the HS
    turns off (branch peak current, after the switch node has commutated, t_c = Q_node/I_pk);
  * the extra currents some LS devices carry (the LS of L2 carries I_L2 + I_L3 in phase A, the
    LS of L1 carries I_L1 + I_L2 in phase B) flow while those devices are ON, so they add no
    dead-time term;
  * HS devices never reverse-conduct (branch currents stay positive, checked per design);
  * each flying capacitor carries +I_b for D T and -I_b for D T half a period later (odd
    harmonics only); the model's 2(1-1/N) R_C term is exactly that waveform's RMS on R_C.

Outputs research/tcpmt_revision/omitted_losses.json. Inputs: the case JSONs of the final
lineage, case D of the regulator-count DSE, the digitized manufacturer curves
(research/tcpmt_revision/omitted_losses_inputs.json, scripts/tcpmt_omitted_losses_digitize.py)
and, when present, the private finer-grid DSE reruns under $HVR_SCRATCH/dse_grid
(scripts/tcpmt_omitted_losses_fsw_grid.py).

    python -I scripts/tcpmt_omitted_losses_digitize.py     # manufacturer curves -> inputs JSON
    python scripts/tcpmt_omitted_losses_fsw_grid.py        # private engine, 50/99/197/785 points
    python scripts/tcpmt_omitted_losses.py                 # this analysis -> omitted_losses.json
"""
from __future__ import annotations

import csv
import functools
import itertools
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("ETM_RESULTS_ROOT") or REPO / "research")      # campaign hook
TR = RES / "tcpmt_revision"
INP = TR / "omitted_losses_inputs.json"
OUT = TR / "omitted_losses.json"
FC = RES / "final_closure"
DSE_DATA = TR / "dse_j35" / "data"
#: TCPMT round 3: the regulator-count screen under the corrected capacitor rule (rated parts,
#: full library) -- the case-D screen of the paper (case_D_etm35.csv is the legacy-capacitor
#: rerun) -- and the enumeration it was selected from (every architecture, 50-point f_sw grid)
CASE_D = DSE_DATA / "case_D_etm35_caprule_full.csv"
ALL_ARCH = DSE_DATA / "all_architectures_etm35_caprule_full.csv"
#: the phase-2 sweeps of the extended count list (16..120) under the production converter rules
#: at each tier limit (t4 = the production rule, at most 4 tiers), and their summary
P2_SUMMARY = TR / "dse_phase2_summary.json"
P2_RUNS = ("etm35_p2_t4", "etm35_p2_t5", "etm35_p2_tinf")
P2_PRODUCTION = "etm35_p2_t4"
SCR = Path(os.environ.get("HVR_SCRATCH", "/home/beams0/SABDELZAHER/ETM_project/scratch_omitloss"))
GRID = SCR / "dse_grid" / "data"
#: the DSE routing score needs paper_routing.py (outside the repository, as sweep_etm.py): its
#: location is recorded by the campaign's engine snapshot (scripts/campaign/build_dse_engine.py)
DSE_ENGINE = Path(os.environ.get("HVR_DSE_ENGINE") or SCR / "dse_engine")
PAPER_ROUTING_DIR = Path("/home/beams0/SABDELZAHER/Salma_Thesis/analysis/"
                         "system_partitioning_comparison/scripts")

sys.path.insert(0, str(REPO / "Scalable_Integrated_VR" / "src"))
sys.path.insert(0, str(REPO / "scripts" / "phase0nw"))   # design_record (round 3)

V_IN, V_OUT, P_LOAD, I_SYS = 48.0, 1.0, 1000.0, 1000.0
ALPHA_CU = 3.93e-3                       # 1/K, scripts/phase0d/electrical.py
RHO_CU_20 = 1.72e-8                      # Ohm m, reference of the FEM AC-resistance curve
MU0 = 4e-7 * math.pi

# ---------------------------------------------------------------------------------- cases
#: review round 2: the compared cases come from tcpmt_cases -- the PRODUCTION state (implemented
#: input decoupling) by default, TCPMT_OMIT_STATE=S0 for the reference -- with Z3 on its COUPLED
#: land side; the superseded uncoupled Z3 cases (z3_top_only, z3_plate_tim, the interface-free
#: second plate) are no longer evaluated. A case not run yet is left out.
def _registry_cases():
    sys.path.insert(0, str(REPO / "scripts"))
    import tcpmt_cases as TC
    st = os.environ.get("TCPMT_OMIT_STATE", TC.PRODUCTION_STATE)
    label = {"A": "cooling A (top plate)", "B": "cooling B (top + bottom plate)"}
    out = {}
    for t in TC.TIERS:
        for a in TC.ARCHS:
            pth = TC.case_path(st, t, a)
            if pth is not None:
                out[f"{t}_{a}"] = (f"{label[t]}, {TC.STATE_LABEL[st]}", a,
                                   pth.relative_to(FC).as_posix())
    return out


CASES = _registry_cases()
#: (better, worse) under one cooling configuration: every pair of integrations of a cooling,
#: oriented by the package loss of the cases in force (round 2 fixed them to its own ranking);
#: the headline pair of a cooling is its best against its runner-up. Set by ranked_pairs().
PAIRS: list = []
HEADLINE: list = []


def ranked_pairs(cases):
    """(pairs, headline) from the compared cases' own package losses."""
    pairs, head = [], []
    for t in ("A", "B"):
        ks = sorted((k for k in cases if k.split("_")[0] == t),
                    key=lambda k: cases[k]["P_package_w"])
        pairs += [(a, b) for i, a in enumerate(ks) for b in ks[i + 1:]]
        if len(ks) >= 2:
            head.append((ks[0], ks[1]))
    return pairs, head

# ------------------------------------------------------------------------------ inputs
DIG = json.loads(INP.read_text())


def _lib():
    import HVR_FULL_OPT_EPC_V2 as V2
    ind = {i.name: i for i in V2.INDUCTOR_LIBRARY}
    cap = {c.name: c for c in V2.CAPACITOR_LIBRARY}
    # round 3: the corrected rule's library carries the rated parts the design record selects
    for fn in ("_rated_capacitors", "default_capacitor_library"):
        if hasattr(V2, fn):
            for c in getattr(V2, fn)():
                cap.setdefault(c.name, c)
    return V2, ind, cap


V2, IND, CAP = _lib()
#: voltage derating of the corrected rules (the authors' decision: capacitors 0.8, switches 0.9)
CAP_DERATING = float(getattr(V2, "CAP_V_DERATING", 0.8))
SW_DERATING = float(getattr(V2, "SW_V_DERATING", 0.9))
IND_NAME = "Shared_Core_UIC_250_nH"
L_IND = IND[IND_NAME].l_nh * 1e-9
RDC25 = IND[IND_NAME].r_dcr_mohm * 1e-3
ISAT = IND[IND_NAME].i_sat_a
V_ENV = IND[IND_NAME].footprint_mm2 * 1e-6 * IND[IND_NAME].height_um * 1e-6     # m3
BSAT_TYM5, MUR_TYM5 = 1.25, 15.0          # source of the library inductor, Table II


def q_oss_nC(dev: str, v: float) -> float:
    """Output charge at V_DS = v: digitized curves where the datasheet plots them, otherwise
    the product-table value scaled as sqrt(v / V_test), V_test = VDSmax/2 (EPC convention)."""
    dev = DIGITIZED_STAND_IN.get(dev, dev)            # round 3: declared stand-in curves
    if dev == "EPC2014C":
        d = DIG["EPC2014C_coss"]
        return float(np.interp(v, [0] + d["V_DS_V"], [0] + d["Q_OSS_nC"]))
    if dev in ("EPC2057", "EPC2090"):
        d = DIG[f"{dev}_qoss"]
        vv = [0.0] + [x for x, q in zip(d["V_DS_V"], d["Q_OSS_nC"]) if q is not None]
        qq = [0.0] + [q for q in d["Q_OSS_nC"] if q is not None]
        return float(np.interp(v, vv, qq))
    table = {"EPC2212": (18.0, 50.0), "EPC2214": (8.0, 40.0)}
    q, vt = table[dev] if dev in table else _product_qoss(dev)
    return q * math.sqrt(v / vt)


_QOSS_CACHE = {}


def _product_qoss(dev: str):
    """(Q_OSS nC, its test V_DS) of any library part: the product-table value at the datasheet
    test voltage (HVR_epc_device_data.json; None -> V_DS,max/2, the EPC convention) -- the
    synthesis engine's own Q_OSS rule (round 3), for parts without digitized curves."""
    if not _QOSS_CACHE:
        df = V2.load_epc_devices(str(REPO / "Scalable_Integrated_VR" / "EPC-Product-Table.csv"), 5.0)
        dd = json.loads((REPO / "Scalable_Integrated_VR" / "src" /
                         "HVR_epc_device_data.json").read_text())["parts"]
        for _, r in df.iterrows():
            vt = (dd.get(r["PartNumber"]) or {}).get("QOSS_V_test_V") or float(r["VDSmax"]) / 2.0
            _QOSS_CACHE[r["PartNumber"]] = (float(r["QOSS_nC"]), float(vt))
    return _QOSS_CACHE[dev]


# ----------------------------------------------------------------------- dead time (GaN)
VSD_SHIFT = {  # figure-to-table offset at low current: datasheet table V_SD(0.5 A, 25 C)
    "EPC2057": DIG["EPC2057_reverse"]["V_SD_25C_V"][0] - 1.4,
    "EPC2090": DIG["EPC2090_reverse"]["V_SD_25C_V"][0] - 1.5,
}


#: TCPMT round 3: a device without digitized curves takes the digitized device of the same
#: role and family as a DECLARED STAND-IN (the decided low side EPC2055 and the M = 25
#: neighbour's EPC2366: the EPC2057 curves; recorded in the output)
DIGITIZED_STAND_IN = {"EPC2055": "EPC2057", "EPC2366": "EPC2057"}


#: round 3: the extended count sweep selects parts without digitized REVERSE curves; their
#: third-quadrant drop takes a digitized part of the same voltage class (declared stand-in,
#: used only by the omitted-term bound of the screen; Q_OSS uses each part's own product data)
VSD_STAND_IN = {"EPC2214": "EPC2090", "EPC2212": "EPC2090", "EPC7003": "EPC2090",
                "EPC7002": "EPC2090", "EPC2012C": "EPC2090", "EPC2035": "EPC2057"}


def _dig(dev: str) -> str:
    if f"{dev}_reverse" in DIG:
        return dev
    return DIGITIZED_STAND_IN.get(dev) or VSD_STAND_IN.get(dev, dev)


def v_sd(dev: str, i_a: float, t_j: float, variant: str = "figure") -> float:
    """Third-quadrant drop at V_GS = 0 (EPC recommends 0 V off): datasheet reverse
    characteristic, linear in T between the 25 and 125 C curves (extrapolated beyond)."""
    dev = _dig(dev)
    d = DIG[f"{dev}_reverse"]
    I = np.array(d["I_A"], float)
    v25 = float(np.interp(i_a, I, d["V_SD_25C_V"]))
    v125 = float(np.interp(i_a, I, d["V_SD_125C_V"]))
    v = v25 + (v125 - v25) * (t_j - 25.0) / 100.0
    if variant == "table":
        v -= VSD_SHIFT[dev]
    return v


def dead_time_cell_w(br, f, t_dt, t_ls, ls_dev, hs_dev, variant="figure", commutation=True):
    """Dead-time loss of one cell [W]: two events per LS device per period."""
    e = 0.0
    for b in br:
        i_v, i_p = b["I_valley"], b["I_peak"]
        if i_v <= 0:
            raise ValueError("negative valley current: HS reverse conduction not modelled")
        q = (q_oss_nC(hs_dev, b["V_sw"]) + q_oss_nC(ls_dev, b["V_sw"])) * 1e-9
        t_c = q / i_p if commutation else 0.0
        e += v_sd(ls_dev, i_v, t_ls, variant) * i_v * t_dt
        e += v_sd(ls_dev, i_p, t_ls, variant) * i_p * max(0.0, t_dt - t_c)
    return e * f


# ---------------------------------------------------------------------------- core loss
K10 = DIG["TYM5_loss_10MHz"]["P_at_1mT_W_m3"]     # W/m3 at B_pk = 1 mT, 10 MHz
BETA = DIG["TYM5_loss_10MHz"]["beta"]


def tri_factor(D, alpha, beta):
    """iGSE: loss of a triangular flux (rise fraction D) / sinusoid of the same peak flux."""
    from scipy.special import gamma
    integ = 2.0 * math.sqrt(math.pi) * gamma((alpha + 1) / 2) / gamma(alpha / 2 + 1)
    return (2 ** alpha * (D ** (1 - alpha) + (1 - D) ** (1 - alpha))
            / ((2 * math.pi) ** (alpha - 1) * integ))


FERRITE = DIG["ferrite_3F4_temperature"]["500kHz_50mT"]


def k_temp_core(t_c, mode):
    if mode == "metal_composite":
        return 1.0
    if mode == "ferrite_like":    # 3F4, 500 kHz / 50 mT, normalized at 25 C; quadratic beyond 120 C
        T, P = np.array(FERRITE["T_C"], float), np.array(FERRITE["Pv_kW_m3"], float)
        p25 = float(np.interp(25.0, T, P))
        if t_c <= T[-1]:
            return float(np.interp(t_c, T, P)) / p25
        c = np.polyfit(T[-4:], P[-4:], 2)
        return float(np.polyval(c, t_c)) / p25
    raise KeyError(mode)


CORE_CASES = {
    # B per ampere, core volume, frequency exponent
    "low": dict(b_per_a=0.6 * BSAT_TYM5 / ISAT, vol=V_ENV, alpha=1.5,
                why="soft saturation: 10 % L drop reached at 0.6 B_sat; alpha 1.5"),
    "nominal": dict(b_per_a=BSAT_TYM5 / ISAT, vol=V_ENV, alpha=1.25,
                    why="B reaches B_sat = 1.25 T at the library I_sat = 23 A; core fills the "
                        "1 mm2 x 500 um envelope; alpha 1.25 (metal composite)"),
    "high": dict(b_per_a=math.sqrt(L_IND * MU0 * MUR_TYM5 / V_ENV), vol=V_ENV, alpha=1.0,
                 why="all magnetic energy in a closed mu_r = 15 core confined to the envelope "
                     "(contradicts I_sat = 23 A, so a bound); alpha = 1 (energy per cycle "
                     "cannot rise as f falls below the 10 MHz data)"),
}


def core_cell_w(br, f, D, t_ind, case, tmode="metal_composite"):
    c = CORE_CASES[case]
    p = 0.0
    for b in br:
        bpk = c["b_per_a"] * b["dI"] / 2.0                      # T
        pv_sine = K10 * (f / 10e6) ** c["alpha"] * (bpk * 1e3) ** BETA
        p += pv_sine * tri_factor(D, c["alpha"], BETA) * c["vol"]
    return p * k_temp_core(t_ind, tmode)


def core_saturation(br, case):
    """Peak flux (DC + ripple) of the busiest branch under a flux model, vs B_sat."""
    c = CORE_CASES[case]
    b_max = max(c["b_per_a"] * b["I_peak"] for b in br)
    return {"B_peak_T": b_max, "saturated": bool(b_max > BSAT_TYM5)}


# ----------------------------------------------------------------------- AC winding loss
RAC = DIG["segment_Rac"]
_F = np.array(RAC["f_MHz"], float)
_R = np.array([r for r in RAC["R_ac_mOhm"]], float)
_RDC_SEG = RAC["R_dc_mOhm"]


def _fit_rac():
    from scipy.optimize import least_squares
    pU = least_squares(lambda p: np.log(_RDC_SEG + p[0] * _F ** p[1]) - np.log(_R), [20, 0.6]).x

    def dowell(fm, t, m):
        dl = np.sqrt(RHO_CU_20 / (np.pi * fm * 1e6 * MU0))
        x = t / dl
        z1 = (np.sinh(2 * x) + np.sin(2 * x)) / (np.cosh(2 * x) - np.cos(2 * x))
        z2 = (np.sinh(x) - np.sin(x)) / (np.cosh(x) + np.cos(x))
        return x * (z1 + (2.0 / 3.0) * (m * m - 1) * z2)
    pL = least_squares(lambda p: np.log(dowell(_F, p[0] * 1e-6, p[1])) - np.log(_R / _RDC_SEG),
                       [100, 1.5], bounds=([5, 1], [1000, 20])).x
    return pU, pL, dowell


RAC_U, RAC_D, _DOWELL = _fit_rac()


def f_ratio(fm, model):
    """R_ac/R_dc of the source segment at fm (MHz), 20 C copper."""
    if model == "nominal":          # R_dc + a f^b through the FEM points (3-98 MHz)
        return (_RDC_SEG + RAC_U[0] * fm ** RAC_U[1]) / _RDC_SEG
    if model == "high":             # Dowell fit through the same points
        return float(_DOWELL(fm, RAC_D[0] * 1e-6, RAC_D[1]))
    if model == "low":              # FEM above 3 MHz, quadratic eddy regime below it
        f0 = _F[0]
        if fm >= f0:
            return float(np.interp(fm, _F, _R)) / _RDC_SEG
        return 1.0 + (_R[0] / _RDC_SEG - 1.0) * (fm / f0) ** 2
    raise KeyError(model)


def rho_ratio(t_c):
    return (1.0 + ALPHA_CU * (t_c - 20.0))


def tri_harmonics(dI, D, n_max=400):
    n = np.arange(1, n_max + 1)
    amp = dI * np.abs(np.sin(n * np.pi * D)) / (np.pi ** 2 * n ** 2 * D * (1 - D))
    return n, amp ** 2 / 2.0                              # RMS^2 of each harmonic


def ac_winding_cell_w(br, f, D, t_ind, model, arch, dI_out):
    """Winding loss the model misses: sum_n I_n^2 R_dc(T) F(n f, T) over the per-branch ripple
    spectrum minus the ripple share the model books (I_out_rms with the summed ripple)."""
    rdc = RDC25 * (1.0 + ALPHA_CU * (t_ind - 25.0))
    # skin/proximity scale with delta ~ sqrt(rho/f): F(f, T) = F_20C(f * rho20/rhoT)
    fscale = 1.0 / rho_ratio(t_ind)
    p_ex, p_dc_true = 0.0, 0.0
    for b in br:
        n, i2 = tri_harmonics(b["dI"], D)
        F = np.array([f_ratio(k * f / 1e6 * fscale, model) for k in n])
        p_ex += float(np.sum(i2 * (F - 1.0))) * rdc
        p_dc_true += float(np.sum(i2)) * rdc
    sum_b2 = sum(x * x for x in arch["B"])
    p_dc_model = dI_out ** 2 / 12.0 * rdc * sum_b2 / arch["N"] ** 2
    return p_ex, p_dc_true - p_dc_model


# ------------------------------------------------------------------- dielectric (MLCC)
DIEL_CASES = {"low": dict(df=0.01, c_frac=1.0), "nominal": dict(df=0.025, c_frac=0.5),
              "high": dict(df=0.10, c_frac=0.3)}
DF_TC = -0.004       # 1/K, X7R dissipation factor falls with temperature (assumption, floor 0.3)


def c_eff_positions(cap, N, t_c):
    """[C_eff (F)] of the N - 1 flying capacitors at their own DC bias (position j holds
    (N - j) V_in / N) and t_c, from the part's vendor DC-bias and temperature data less its
    tolerance (HVR_FULL_OPT_EPC_V2.cap_c_eff_uf: the rated Murata parts); None without vendor
    data."""
    c = CAP[cap]
    if not hasattr(V2, "cap_c_eff_uf"):
        return None
    out = []
    for j in range(1, N):
        ce = V2.cap_c_eff_uf(c, (N - j) * V_IN / N, t_c)
        if ce is None or ce <= 0:
            return None
        out.append(ce * 1e-6)
    return out


def _esr_table(cap, v):
    """(log10 f, ESR in Ohm) of the part's vendor ESR(f) at the bias nearest v -- the table
    HVR_FULL_OPT_EPC_V2.cap_esr_mohm interpolates; None for a part without one."""
    c = CAP[cap]
    d = (V2._vendor(c.vendor_part) if getattr(c, "vendor_part", None)
         and hasattr(V2, "_vendor") else None)
    if not d or not d.get("esr_f"):
        return None
    b = min((x for x, _ in d["esr_f"]), key=lambda x: abs(x - v))
    tab = dict(d["esr_f"])[b]
    return (np.log10([fq for fq, _ in tab]), np.array([r for _, r in tab], float))


@functools.lru_cache(maxsize=4096)
def _esr_residual_cell_w(cap, N, f, D, I_b):
    """Flying-capacitor loss of one cell the production rules MISBOOK for a part with a vendor
    ESR(f) (the rated parts): the rules book every flying capacitor at the vendor ESR at f_sw
    and the C_1 bias (CAP_ESR_F; that ESR contains the dielectric loss at f_sw), whereas each
    harmonic n f_sw of the +/-I_b pulse current sees ESR(n f_sw) at the capacitor's own bias
    (position j holds (N - j) V_in / N). Residual = true - booked (vendor 25-C data); negative
    when the harmonics see a lower ESR than the fundamental."""
    n = np.arange(1, 4001, 2)
    i2 = (4.0 * I_b * np.abs(np.sin(n * np.pi * D)) / (n * np.pi)) ** 2 / 2.0
    lf = np.log10(n * f)
    t1 = _esr_table(cap, (N - 1) * V_IN / N)
    booked = (N - 1) * float(np.sum(i2)) * float(np.interp(math.log10(f), *t1))
    true = 0.0
    for j in range(1, N):
        t = _esr_table(cap, (N - j) * V_IN / N)
        true += float(np.sum(i2 * np.interp(lf, *t)))
    return true - booked


def dielectric_cell_w(arch, I_b, f, D, cap, t_caps, case, df_tc=DF_TC):
    """Dielectric loss of one cell's flying capacitors that the converter model omits.
    A part with a vendor ESR(f) (the rated flying capacitor): the production rules already book
    its ESR at f_sw, dielectric loss included, so only the residual over the harmonics and the
    capacitor biases is omitted (_esr_residual_cell_w; measured data: one value for every
    bundle). Otherwise the library ESR is a ~10-MHz value with a negligible dielectric share and
    the whole term DF / (2 pi f C_eff) is omitted; C_eff is the part's vendor DC-bias capacitance
    at each position (if known) or the bundle's fraction of its nominal C."""
    if _esr_table(cap, V_IN / arch["N"]) is not None:
        return _esr_residual_cell_w(cap, int(arch["N"]), float(f), float(D), float(I_b))
    c = DIEL_CASES[case]
    df = c["df"] * max(0.3, 1.0 + df_tc * (t_caps - 25.0))
    n = np.arange(1, 4001, 2)
    amp = 4.0 * I_b * np.abs(np.sin(n * np.pi * D)) / (n * np.pi)
    s = float(np.sum(amp ** 2 / 2.0 * df / (2 * np.pi * n * f)))     # x 1/C per capacitor
    cv = c_eff_positions(cap, arch["N"], t_caps)
    if cv is None:
        return (arch["N"] - 1) * s / (CAP[cap].c_uf * 1e-6 * c["c_frac"])
    return s * sum(1.0 / x for x in cv)


# -------------------------------------------------------------------------- the design
def design(N, K, K_A, f, I_vr, hs, ls, cap, L=L_IND):
    """B_i > 1 (shared inductors) only enters the re-selection check: inductor i carries
    I B_i / N, the flying capacitors carry the branch current I / N."""
    B = V2.generate_B_array(N, K, K_A)
    D = N * V_OUT / V_IN
    v_sw = V_IN / N
    dI = (v_sw - V_OUT) * D / (f * L)
    dI_out = (D / (f * L)) * (V_IN / N * K_A - V_OUT * K)
    br = []
    for b in B:
        Ib = I_vr * b / N
        br.append({"I_avg": Ib, "dI": dI, "I_valley": Ib - dI / 2, "I_peak": Ib + dI / 2,
                   "V_sw": v_sw})
    # switch stress (the authors' rule, HVR_FULL_OPT_EPC_V2.switch_stresses): S1 blocks V_in/N,
    # the stacked S2..SN max(N - 1, 2) V_in/N, the low side V_in/N; their node swing 2 V_in/N
    v_stack = (V2.switch_stresses(N, V_IN)[1] if hasattr(V2, "switch_stresses")
               else max(N - 1, 2) * V_IN / N)
    return {"N": N, "K": K, "K_A": K_A, "B": B, "D": D, "f": f, "I_vr": I_vr, "hs": hs, "ls": ls,
            "cap": cap, "branches": br, "dI_branch": dI, "dI_out_model": dI_out,
            "I_b": I_vr / N, "V_C_max": V_IN * (N - 1) / N, "V_HS_stack_max": v_stack,
            "V_HS_stack_swing": 2 * V_IN / N}


BUNDLES = {
    "low": dict(t_dt=2e-9, vsd="table", commutation=True, core="low", ac="low", diel="low"),
    "nominal": dict(t_dt=5e-9, vsd="figure", commutation=True, core="nominal", ac="nominal",
                    diel="nominal"),
    "high": dict(t_dt=10e-9, vsd="figure", commutation=True, core="high", ac="high",
                 diel="high"),
}
# over-bound of the dead-time term: the switch node is assumed to commutate in zero time
HIGH_TC0 = dict(BUNDLES["high"], commutation=False)


def omitted_terms(des, M, t_ls, t_ind, t_caps, bundle, core_tmode="metal_composite"):
    bz = BUNDLES[bundle] if isinstance(bundle, str) else bundle
    br, f, D = des["branches"], des["f"], des["D"]
    dt = M * dead_time_cell_w(br, f, bz["t_dt"], t_ls, des["ls"], des["hs"], bz["vsd"],
                              bz["commutation"])
    core = M * core_cell_w(br, f, D, t_ind, bz["core"], core_tmode)
    ac_ex, ac_dc = ac_winding_cell_w(br, f, D, t_ind, bz["ac"], des, des["dI_out_model"])
    diel = M * dielectric_cell_w(des, des["I_b"], f, D, des["cap"], t_caps, bz["diel"])
    out = {"dead_time_w": dt, "core_w": core, "ac_winding_w": M * (ac_ex + ac_dc),
           "ac_winding_skin_proximity_w": M * ac_ex, "ac_winding_ripple_bookkeeping_w": M * ac_dc,
           "dielectric_w": diel}
    out["total_w"] = dt + core + out["ac_winding_w"] + diel
    return out


# ------------------------------------------------------------------------- case data
def load_cases():
    res = {}
    for key, (cool, arch, fn) in CASES.items():
        d = json.loads((FC / fn).read_text())
        e = d["et_history"][-1]
        conv = sum(r["P_w"] for r in d["ledger_rows"] if r["term"].startswith("P_conv_"))
        fp = FC / fn                      # campaign hook: the file actually read, not research/
        try:
            frel = fp.relative_to(REPO).as_posix()
        except ValueError:
            frel = fp.as_posix()
        res[key] = {"cooling": cool, "arch": arch, "file": frel,
                    "P_package_w": float(e["P_loss_w"]), "P_converter_model_w": conv,
                    "T_hs_C": e["T_hs_C"], "T_ls_C": e["T_ls_C"], "T_ind_C": e["T_ind_C"],
                    "T_caps_C": e["T_caps_C"], "converged": bool(d.get("et_converged"))}
    return res


def read_csv(p):
    with open(p) as fh:
        return list(csv.DictReader(fh))


def dse_rows(path):
    """Feasible rows of a screen CSV. The sweep records the selected passives as 'capacitor' /
    'inductor' (the private reruns of round 2 as 'cap' / 'ind')."""
    out = []
    for r in read_csv(path):
        if r.get("feasible") not in ("True", "true", True):
            continue
        out.append({"M": int(float(r["M"])), "N": int(float(r["N"])), "K": int(float(r["K"])),
                    "K_A": int(float(r["K_A"])),
                    "f_sw_Hz": float(r["f_sw_Hz"]), "hs": r["hs"], "ls": r["ls"],
                    "cap": r.get("capacitor") or r.get("cap") or None,
                    "ind": r.get("inductor") or r.get("ind") or None,
                    "conv_loss_total_W": float(r["conv_loss_total_W"]),
                    "routing_loss_W": float(r["routing_loss_W"]),
                    "total_loss_W": float(r["total_loss_W"])})
    return out


def _record():
    import design_record as DR
    return DR.get()


def cap_of(r, capmap):
    """The flying capacitor of a screen row: the sweep's own selection; else the private
    rerun's; else the design record's part as a declared stand-in (round 3: never the legacy
    25-V part)."""
    return r["cap"] or (capmap.get(r["M"], (None,))[0]) or _record()["capacitor"]


def caps_from_rerun():
    p = GRID / "case_D_n50_all.csv"
    if not p.exists():
        return {}
    return {int(r["M"]): (r["cap"], r["ind"]) for r in read_csv(p) if r.get("feasible") == "True"}


# --------------------------------------------------------------------------- analysis
def n_cells() -> int:
    """The regulator count of the design in force (THE design record; 36 in production)."""
    import design_record as DR
    return DR.n_vr()


def screen_row(rows, des):
    """The screen's row at the design's count, and whether it IS the design (topology, parts,
    capacitor and f_sw); None when the count is not a feasible screen point."""
    r = next((x for x in rows if x["M"] == des["M"]), None)
    if r is None:
        return None, False
    same = ((r["N"], r["K"], r["K_A"]) == (des["N"], des["K"], des["K_A"])
            and (r["hs"], r["ls"]) == (des["hs"], des["ls"])
            and (r["cap"] in (None, des["cap"]))
            and abs(r["f_sw_Hz"] - des["f"]) <= 1e-6 * des["f"])
    return r, same


def production_design(rows=()):
    """The production converter of the design record (TCPMT round 3: no longer the DSE row at
    M = 49): topology, parts, f_sw and the capacitor, checked against the record's 25-C
    conversion loss with the compiled design (design_record.compiled) and against the case-D
    screen's row at the design's count (`rows`)."""
    import design_record as DR
    e = DR.get()
    M = int(e["n_vr"])
    t = e["topology"]
    des = design(int(t["N"]), int(t["K"]), int(t["K_A"]), float(e["f_sw_hz"]), I_SYS / M,
                 e["hs_part"], e["ls_part"], e["capacitor"])
    comp = DR.compiled()
    des["model_loss_25C_per_vr_w"] = float(comp.loss_25c_w)
    des["record_loss_per_vr_w"] = float(e["conversion_25C_W"]) / M
    des["M"] = M
    des["design"] = DR.name()
    des["digitized_stand_in"] = {d: DIGITIZED_STAND_IN[d] for d in (e["hs_part"], e["ls_part"])
                                 if d in DIGITIZED_STAND_IN}
    r, same = screen_row(list(rows), des)
    des["case_D_file"] = CASE_D.name
    des["case_D_row_is_design"] = bool(same)
    des["case_D_loss_per_vr_w"] = (r["conv_loss_total_W"] / M) if r is not None else None
    des["case_D_total_loss_w"] = r["total_loss_W"] if r is not None else None
    des["record_screen"] = e.get("screen")
    return des


_DEVS = None


def _dev(name):
    global _DEVS
    if _DEVS is None:
        df = V2.load_epc_devices(str(REPO / "Scalable_Integrated_VR" / "EPC-Product-Table.csv"), 5.0)
        _DEVS = {row["PartNumber"]: V2.row_to_device(row) for _, row in df.iterrows()}
    return _DEVS[name]


def term_tc(des, M, t_ls, t_ind, t_caps, bundle="nominal", dT=1.0):
    a = omitted_terms(des, M, t_ls, t_ind, t_caps, bundle)
    b = omitted_terms(des, M, t_ls + dT, t_ind + dT, t_caps + dT, bundle)
    return {k: (b[k] - a[k]) / dT for k in a}


ALPHA_HS, ALPHA_LS = 6.0e-3, 8.0e-3     # 1/K, the published class values (legacy rules)


def _alpha(part, role):
    """The device's own R_DS(on) coefficient (electrical.alpha_ron, TCPMT round 3)."""
    import design_record as DR
    DR._paths()                         # scripts/phase0d (electrical) on the path
    import electrical as EL
    return EL.alpha_ron(part, role)


def modeled_conv_dPdT(des, t):
    """d(modeled converter loss)/dT per tier [W/K] for the system of the design in force, from the model's
    own conduction decomposition (scripts/phase0mr/ledger.py converter_decomposition) and
    the TCs the ledger uses; switching and ESR terms carry no temperature dependence."""
    N, B = des["N"], des["B"]
    hs, ls = _dev(des["hs"]), _dev(des["ls"])
    i_rms2 = des["I_vr"] ** 2 + des["dI_out_model"] ** 2 / 12.0
    k = (V_OUT / V_IN) * i_rms2
    sb2 = sum(b * b for b in B)
    corr_coef = (4 * B[-1] - 1) / N if B[-1] > 1 else 3.0 / N
    c_ls = k * ((V_IN / (N ** 2 * V_OUT)) * sb2 + 2 * sb2 / N - corr_coef)
    c_ind = k * (V_IN / (N ** 2 * V_OUT)) * sb2
    M = n_cells()
    return {"hs": M * k * hs.R_DS_ON * _alpha(des["hs"], "hs"),
            "ls": M * c_ls * ls.R_DS_ON * _alpha(des["ls"], "ls"),
            "ind": M * c_ind * RDC25 * ALPHA_CU, "caps": 0.0}


def et_feedback(des, cases, arch_out, bundles=("low", "nominal", "high")):
    """Second-order effect: the omitted heat raises each tier by (dT/dP) x P_omit, which raises
    the MODELED (temperature-dependent) converter loss. dT/dP per tier from the first two
    iterations of each case's own E-T fixed point."""
    res = {}
    for key, c in cases.items():
        d = json.loads((REPO / c["file"]).read_text())["et_history"]
        dp = d[1]["P_loss_w"] - d[0]["P_loss_w"]
        slope = {t: (d[1][f"T_{t}_C"] - d[0][f"T_{t}_C"]) / dp for t in ("hs", "ls", "ind", "caps")}
        g = modeled_conv_dPdT(des, None)
        loop = sum(g[t] * slope[t] for t in g)              # W of modeled loss per W deposited
        rec = {"dT_dP_K_per_W": slope, "dPconv_dT_W_per_K": g, "loop_gain": loop}
        for bn in bundles:
            p_om = arch_out[key]["omitted"][bn]["total_w"]
            rec[f"feedback_{bn}_w"] = loop * p_om / (1.0 - loop)
        res[key] = rec
    pairs = []
    for a, b in PAIRS:
        pairs.append({"better": a, "worse": b,
                      **{f"delta_feedback_{bn}_w": res[b][f"feedback_{bn}_w"] - res[a][f"feedback_{bn}_w"]
                         for bn in bundles}})
    return {"per_case": res, "pairs": pairs}


def architecture_analysis(des, cases):
    out = {}
    for key, c in cases.items():
        rec = {}
        M = n_cells()
        for bn in BUNDLES:
            rec[bn] = omitted_terms(des, M, c["T_ls_C"], c["T_ind_C"], c["T_caps_C"], bn)
        rec["high_tc0"] = omitted_terms(des, M, c["T_ls_C"], c["T_ind_C"], c["T_caps_C"], HIGH_TC0)
        rec["nominal_core_ferrite_like"] = omitted_terms(des, M, c["T_ls_C"], c["T_ind_C"],
                                                         c["T_caps_C"], "nominal", "ferrite_like")
        rec["high_core_ferrite_like"] = omitted_terms(des, M, c["T_ls_C"], c["T_ind_C"],
                                                      c["T_caps_C"], "high", "ferrite_like")
        rec["dP_dT_nominal_w_per_K"] = term_tc(des, M, c["T_ls_C"], c["T_ind_C"], c["T_caps_C"])
        rec["notes"] = []
        ls_curves = _dig(des["ls"])
        if ls_curves != des["ls"]:
            rec["notes"].append(f"V_SD and Q_OSS of the low side {des['ls']}: the {ls_curves} "
                                f"datasheet curves (declared stand-in)")
        if c["T_ls_C"] > 125:
            rec["notes"].append(f"T_ls above the 125 C datasheet curve: V_SD extrapolated "
                                f"linearly in T; also above the 150 C {des['ls']} rating" if
                                c["T_ls_C"] > 150 else "T_ls above 125 C: V_SD extrapolated")
        out[key] = {**c, "omitted": rec}
    # pairwise
    pairs = []
    for a, b in PAIRS:
        gap = cases[b]["P_package_w"] - cases[a]["P_package_w"]
        rec = {"better": a, "worse": b, "gap_paper_w": gap, "delta_omitted_w": {}, "flip": {},
               "dT_tiers_K": {t: cases[b][f"T_{t}_C"] - cases[a][f"T_{t}_C"]
                              for t in ("hs", "ls", "ind", "caps")}}
        for bn in list(BUNDLES) + ["high_tc0", "nominal_core_ferrite_like", "high_core_ferrite_like"]:
            oa, ob = out[a]["omitted"][bn], out[b]["omitted"][bn]
            d = {k: ob[k] - oa[k] for k in oa}
            rec["delta_omitted_w"][bn] = d
            rec["flip"][bn] = bool(gap + d["total_w"] < 0)
        dn = rec["delta_omitted_w"]["nominal"]["total_w"]
        rec["new_gap_nominal_w"] = gap + dn
        rec["scale_to_flip_nominal"] = (gap / -dn) if dn < 0 else None
        rec["scale_to_flip_note"] = ("omitted terms narrow the gap; they would have to be this "
                                     "many times their nominal temperature-induced difference"
                                     if dn < 0 else
                                     "omitted terms widen the gap: no positive scaling flips it")
        # generic requirement: one omitted term of TC 1 %/K (sign adverse) in the tier with
        # the largest temperature difference
        dts = rec["dT_tiers_K"]
        tier = max(dts, key=lambda t: abs(dts[t]))
        rec["generic_requirement"] = {
            "tier": tier, "dT_K": dts[tier],
            "P_required_at_1pct_per_K_w": abs(gap) / (0.01 * abs(dts[tier])) if dts[tier] else None,
            "required_TC_sign": ("negative (term must fall with temperature)" if dts[tier] > 0
                                 else "positive (term must rise with temperature)"),
        }
        pairs.append(rec)
    return out, pairs


def dse_analysis(rows, capmap, temps=(25.0, 100.0)):
    res = {}
    for T in temps:
        per = []
        for r in rows:
            cap = cap_of(r, capmap)
            des = design(r["N"], r["K"], r["K_A"], r["f_sw_Hz"], I_SYS / r["M"], r["hs"], r["ls"],
                         cap)
            hs_rating = float(_dev(r["hs"]).VDSmax)
            rec = {"M": r["M"], "arch": f"N{r['N']}K{r['K']}K_A{r['K_A']}", "f_sw_Hz": r["f_sw_Hz"],
                   "hs": r["hs"], "ls": r["ls"], "cap": cap, "paper_total_w": r["total_loss_W"],
                   "dI_branch_A": des["dI_branch"], "I_branch_A": des["I_b"],
                   "I_valley_A": des["branches"][0]["I_valley"],
                   "flying_cap_max_V": des["V_C_max"], "cap_rating_V": CAP[cap].v_max,
                   "cap_within_derating": bool(CAP[cap].v_max * CAP_DERATING >= des["V_C_max"]),
                   "hs_stack_max_V": des["V_HS_stack_max"],
                   "hs_rating_V": hs_rating,
                   "hs_within_derating": bool(hs_rating * SW_DERATING >= des["V_HS_stack_max"]),
                   "core_saturation": {c: core_saturation(des["branches"], c) for c in CORE_CASES}}
            for bn in BUNDLES:
                o = omitted_terms(des, r["M"], T, T, T, bn)
                rec[bn] = o
                rec[f"total_with_{bn}_w"] = r["total_loss_W"] + o["total_w"]
            rec["dead_time_high_tc0_w"] = omitted_terms(des, r["M"], T, T, T, HIGH_TC0)["dead_time_w"]
            per.append(rec)
        summ = {}
        base_order = [p["M"] for p in sorted(per, key=lambda p: p["paper_total_w"])]
        for bn in BUNDLES:
            order = [p["M"] for p in sorted(per, key=lambda p: p[f"total_with_{bn}_w"])]
            best = order[0]
            second = order[1]
            tot = {p["M"]: p[f"total_with_{bn}_w"] for p in per}
            swaps = [(a, b) for i, a in enumerate(base_order) for b in base_order[i + 1:]
                     if order.index(a) > order.index(b)]
            summ[bn] = {"optimum_M": best, "runner_up_M": second,
                        "margin_w": tot[second] - tot[best], "order": order,
                        "swapped_pairs_vs_paper": swaps,
                        "kendall_tau": _kendall(base_order, order)}
        # 81 combinations of the four terms' low/nominal/high (+27 with the zero-commutation
        # dead-time over-bound): does the optimum ever move?
        def dtv(p, k):
            return p["dead_time_high_tc0_w"] if k == "high_tc0" else p[k]["dead_time_w"]
        combos, combos_tc0 = [], []
        for cmb in itertools.product(("low", "nominal", "high", "high_tc0"), ("low", "nominal", "high"),
                                     ("low", "nominal", "high"), ("low", "nominal", "high")):
            tot = {}
            for p in per:
                o = (dtv(p, cmb[0]) + p[cmb[1]]["core_w"] + p[cmb[2]]["ac_winding_w"]
                     + p[cmb[3]]["dielectric_w"])
                tot[p["M"]] = p["paper_total_w"] + o
            order = sorted(tot, key=tot.get)
            rec_c = {"dead_time": cmb[0], "core": cmb[1], "ac": cmb[2], "diel": cmb[3],
                     "optimum_M": order[0], "runner_up_M": order[1],
                     "margin_w": tot[order[1]] - tot[order[0]]}
            (combos_tc0 if cmb[0] == "high_tc0" else combos).append(rec_c)
        m0 = base_order[0]                 # the screen's own optimum (76 before round 3)
        moved = [c for c in combos if c["optimum_M"] != m0]
        moved_tc0 = [c for c in combos_tc0 if c["optimum_M"] != m0]
        res[f"T_{T:g}C"] = {"per_count": per, "paper_order": base_order, "summary": summ,
                            "combinations_81": {"n_optimum_moves": len(moved),
                                                "n_moves_with_core_high": sum(
                                                    c["core"] == "high" for c in moved),
                                                "n_moves_with_core_low_or_nominal": sum(
                                                    c["core"] != "high" for c in moved),
                                                "cases_optimum_moves": moved,
                                                "min_margin_w": min(c["margin_w"] for c in combos
                                                                    if c["optimum_M"] == m0)
                                                if any(c["optimum_M"] == m0 for c in combos)
                                                else None,
                                                "screen_optimum_M": m0},
                            "combinations_27_dead_time_tc0": {
                                "n_optimum_moves": len(moved_tc0),
                                "cases_optimum_moves": moved_tc0,
                                "screen_optimum_M": m0}}
    return res


def _kendall(a, b):
    n, s = len(a), 0
    for i in range(n):
        for j in range(i + 1, n):
            s += 1 if (b.index(a[i]) < b.index(a[j])) else -1
    return s / (n * (n - 1) / 2)


def flip_requirement_dse(per, bundle="nominal"):
    """Per competitor count: factor by which the nominal omitted-term DIFFERENCE vs the screen
    optimum would have to be scaled to close the paper's gap (None if the omitted terms favour
    the optimum)."""
    p0 = min(per, key=lambda p: p["paper_total_w"])      # the screen optimum (76 before round 3)
    out = []
    for p in per:
        if p["M"] == p0["M"]:
            continue
        gap = p["paper_total_w"] - p0["paper_total_w"]
        d = p[bundle]["total_w"] - p0[bundle]["total_w"]
        terms = {k: p[bundle][k] - p0[bundle][k] for k in
                 ("dead_time_w", "core_w", "ac_winding_w", "dielectric_w")}
        dc = terms["core_w"]
        out.append({"M": p["M"], "vs_M": p0["M"], "gap_paper_w": gap, "delta_omitted_nominal_w": d,
                    "delta_by_term_w": terms,
                    "scale_to_tie": (gap / -d) if d < 0 else None,
                    # factor on the core-loss difference alone (others nominal) that closes the gap
                    "core_scale_to_tie": (gap + d - dc) / -dc if dc < 0 else None})
    return out


def tie_analysis(rows, capmap, T):
    """Per competitor of the screen optimum (M = 76 before round 3; others nominal): the dead
    time at which it ties the optimum, and the uniform core-loss multiplier (vs nominal) that
    ties it at t_dt = 2 and 5 ns."""
    des = {}
    for r in rows:
        cap = cap_of(r, capmap)
        des[r["M"]] = (r, design(r["N"], r["K"], r["K_A"], r["f_sw_Hz"], I_SYS / r["M"], r["hs"],
                                 r["ls"], cap))

    def total(M, t_dt=5e-9, core_scale=1.0, vsd="figure"):
        r, d = des[M]
        bz = dict(BUNDLES["nominal"], t_dt=t_dt, vsd=vsd)
        o = omitted_terms(d, M, T, T, T, bz)
        return r["total_loss_W"] + o["total_w"] + (core_scale - 1.0) * o["core_w"]

    m0 = min(des, key=lambda M: des[M][0]["total_loss_W"])   # the screen optimum (was 76)
    out = []
    for M in sorted(des):
        if M == m0:
            continue
        g = lambda t: total(M, t) - total(m0, t)
        lo, hi = 0.0, 40e-9
        t_tie = None
        if g(lo) * g(hi) < 0:
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if g(lo) * g(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            t_tie = 0.5 * (lo + hi)
        rec = {"M": M, "t_dt_tie_ns": None if t_tie is None else t_tie * 1e9,
               "sign_below_tie": f"M={m0} better" if g(0.0) > 0 else "competitor better"}
        for tdt in (2e-9, 5e-9):
            a0 = total(m0, tdt)
            aM = total(M, tdt)
            c0 = omitted_terms(des[m0][1], m0, T, T, T, dict(BUNDLES["nominal"], t_dt=tdt))["core_w"]
            cM = omitted_terms(des[M][1], M, T, T, T, dict(BUNDLES["nominal"], t_dt=tdt))["core_w"]
            # aM + (s-1) cM = a0 + (s-1) c0  ->  s = 1 + (a0 - aM) / (cM - c0)
            s = 1.0 + (a0 - aM) / (cM - c0) if abs(cM - c0) > 1e-12 else None
            rec[f"core_scale_to_tie_at_{tdt*1e9:g}ns"] = s if (s is not None and s > 0) else None
        out.append(rec)
    return out


def e_oss_nJ(dev, v):
    """E_OSS(v) = int_0^v v' dQ_OSS from the digitized charge curves (EPC2014C from C_OSS);
    for the sqrt-scaled table devices Q = a sqrt(v) gives E = Q v / 3."""
    dev = DIGITIZED_STAND_IN.get(dev, dev)            # round 3: declared stand-in curves
    if dev == "EPC2014C":
        d = DIG["EPC2014C_coss"]
        return float(np.interp(v, [0] + d["V_DS_V"], [0] + d["E_OSS_nJ"]))
    if dev in ("EPC2057", "EPC2090"):
        d = DIG[f"{dev}_qoss"]
        vv = np.array([0.0] + [x for x, q in zip(d["V_DS_V"], d["Q_OSS_nC"]) if q is not None])
        qq = np.array([0.0] + [q for q in d["Q_OSS_nC"] if q is not None])
        vg = np.linspace(0, v, 400)
        qg = np.interp(vg, vv, qq)
        return float(np.sum(0.5 * (vg[1:] + vg[:-1]) * np.diff(qg)))
    return q_oss_nC(dev, v) * v / 3.0


#: the C_OSS term of the screen: the production rules count every hard-switched transition at
#: its node swing ("corrected", adopted in round 3); the published term is kept for reference
COSS_RULE_SCREEN = "corrected" if hasattr(V2, "coss_energy_per_period") else "legacy"


def qoss_basis(dev):
    """Where q_oss_nC / e_oss_nJ take a part's output charge from."""
    if dev in ("EPC2014C", "EPC2057", "EPC2090"):
        return "digitized datasheet curve"
    if dev in DIGITIZED_STAND_IN:
        return f"{DIGITIZED_STAND_IN[dev]} digitized curve (declared stand-in)"
    return "product-table Q_OSS, sqrt law (the model's own basis)"


def coss_check(rows, capmap):
    """OUTSIDE the four requested terms: the screen's C_OSS term against the datasheet curves.
    The production rule (COSS_RULE 'corrected', HVR_FULL_OPT_EPC_V2.coss_energy_per_period)
    counts N high-side turn-ons at V_in/N, K switch-node charges 0 -> V_in/N and N - 1
    stacked-switch charges V_in/N -> 2 V_in/N from the table Q_OSS (sqrt law); the datasheet
    estimate takes the same transitions with the digitized charge curves (declared stand-ins
    where a part has none). The published term (C = Q_OSS/V_DSmax, the LS at V_out) is kept as
    model_coss_legacy_w."""
    out = []
    for r in rows:
        d = design(r["N"], r["K"], r["K_A"], r["f_sw_Hz"], I_SYS / r["M"], r["hs"], r["ls"],
                   cap_of(r, capmap))
        hs, ls = _dev(r["hs"]), _dev(r["ls"])
        f, N, K = d["f"], d["N"], d["K"]
        v1, v2 = V_IN / N, d["V_HS_stack_swing"]
        legacy = r["M"] * (f / 2) * (N * hs.C_OSS * (V_IN / N - V_OUT) ** 2
                                     + K * ls.C_OSS * V_OUT ** 2)
        if COSS_RULE_SCREEN == "corrected":
            arch = V2.VRArchitecture(N=N, K=K, K_A=d["K_A"], B_array=d["B"], D=d["D"],
                                     component_count=0)
            model = r["M"] * f * V2.coss_energy_per_period(arch, hs, ls, V_IN)["total"]
        else:
            model = legacy
        e_hs = N * e_oss_nJ(r["hs"], v1)
        e_node = K * (q_oss_nC(r["ls"], v1) * v1 - e_oss_nJ(r["ls"], v1))
        e_stk = (N - 1) * (v2 * (q_oss_nC(r["hs"], v2) - q_oss_nC(r["hs"], v1))
                           - (e_oss_nJ(r["hs"], v2) - e_oss_nJ(r["hs"], v1)))
        est = r["M"] * f * (e_hs + e_node + e_stk) * 1e-9
        out.append({"M": r["M"], "hs": r["hs"], "ls": r["ls"], "model_rule": COSS_RULE_SCREEN,
                    "charge_basis": {"hs": qoss_basis(r["hs"]), "ls": qoss_basis(r["ls"])},
                    "model_coss_w": model, "model_coss_legacy_w": legacy,
                    "datasheet_hard_turn_on_w": est,
                    "datasheet_without_stacked_w": r["M"] * f * (e_hs + e_node) * 1e-9,
                    "underestimate_w": est - model})
    return out


_RT = {}


def _paper_routing_dirs():
    """Where paper_routing.py may be: a copy in an engine directory (the private round-2 engine,
    the campaign's), the external path the campaign's engine snapshot records, the sweep's."""
    out = [SCR / "engine", DSE_ENGINE]
    try:
        ext = json.loads((DSE_ENGINE / "ENGINE.json").read_text())["external_paper_routing"]
        out.append(Path(ext["path"]).parent)
    except (OSError, KeyError, ValueError):
        pass
    out.append(PAPER_ROUTING_DIR)
    return [p for p in out if (p / "paper_routing.py").is_file()]


def routing_w(m, f):
    """The DSE's routing score (sweep_etm.routing_loss): the repository's routing model with the
    sweep's paper_routing.py."""
    key = (m, round(f, 3))
    if key in _RT:
        return _RT[key]
    for d in _paper_routing_dirs()[:1]:
        if str(d) not in sys.path:
            sys.path.append(str(d))     # appended: the repository's engine modules stay first
    from Framework_w_HVR_OPT_sizing_v2 import DieConfig, DVPDRoutingModel
    import paper_routing as PR
    die = DieConfig(die_area_mm2=500.0, die_side_mm=math.sqrt(500.0), n_pol_segments=100,
                    rho_mohm_per_mm=50.0, i_out_total_a=I_SYS, v_out=V_OUT)
    rm = DVPDRoutingModel(die)
    pos = DVPDRoutingModel.place_vrs_A2(m, die.die_side_mm)
    r = PR.total_routing_w(pos, rm.pols, die.i_out_total_a, f, die.die_side_mm, die.n_pol_segments)
    _RT[key] = float(r["total_routing_w"])
    return _RT[key]


def reselection_check(rows, T=25.0, bundle="nominal", capmap=None):
    """Would an optimizer that SAW the omitted terms pick another member at any count?
    Every feasible architecture the 50-point sweep enumerated (the screen's own
    all_architectures file; round 2: the private rerun all_architectures_n50_all.csv) is
    re-scored with conversion + routing + omitted terms. Devices and capacitor of the
    non-selected members are not recorded by the sweep: the selected member's parts at the same
    count stand in for them (round 2: EPC2014C / EPC2057 and the 25-V capacitor)."""
    p = GRID / "all_architectures_n50_all.csv"
    if not p.exists():
        p = ALL_ARCH
    if not p.exists():
        return {"available": False, "why": f"no architecture enumeration ({ALL_ARCH.name})"}
    if not _paper_routing_dirs():
        return {"available": False, "why": "paper_routing.py (the DSE routing score) not found"}
    capmap = capmap or {}
    sel = {r["M"]: r for r in rows}
    cand = {}
    for r in read_csv(p):
        if r["switch_mode"] != "discrete" or r["ripple_ok"] != "True" or r["area_ok"] != "True":
            continue
        if not r["loss"]:
            continue
        M = int(float(r["M"]))
        if M not in sel:
            continue
        k = (int(r["N"]), int(r["K"]), int(r["K_A"]), round(float(r["f_sw"]), 3))
        # the same architecture at several component counts: the sweep keeps the best
        cand.setdefault(M, {})[k] = min(float(r["loss"]), cand.get(M, {}).get(k, math.inf))
    out, chk = [], {}
    for M, cs in sorted(cand.items()):
        s = sel[M]
        cap = cap_of(s, capmap)
        scored = []
        for (N, K, KA, f), loss in cs.items():
            is_sel = (N, K, KA) == (s["N"], s["K"], s["K_A"]) and abs(f - s["f_sw_Hz"]) < 1.0
            des = design(N, K, KA, f, I_SYS / M, s["hs"], s["ls"], cap)
            o = omitted_terms(des, M, T, T, T, bundle)
            base = loss * M + routing_w(M, f)
            scored.append({"arch": f"N{N}K{K}K_A{KA}", "f_sw_Hz": f, "selected_in_paper": is_sel,
                           "paper_total_w": base, "omitted_w": o["total_w"],
                           "total_w": base + o["total_w"]})
        scored.sort(key=lambda x: x["paper_total_w"])
        paper_pick = scored[0]
        new_pick = min(scored, key=lambda x: x["total_w"])
        chk[M] = abs(paper_pick["paper_total_w"] - s["total_loss_W"])
        out.append({"M": M, "paper_pick": paper_pick["arch"], "omitted_aware_pick": new_pick["arch"],
                    "changes": new_pick["arch"] != paper_pick["arch"] or
                    abs(new_pick["f_sw_Hz"] - paper_pick["f_sw_Hz"]) > 1.0,
                    "total_paper_pick_w": paper_pick["total_w"], "total_new_pick_w": new_pick["total_w"],
                    "n_candidates": len(scored),
                    "best_three_with_omitted": sorted(scored, key=lambda x: x["total_w"])[:3]})
    if not out:
        return {"available": False, "why": f"no feasible enumerated architecture in {p.name}"}
    order = sorted(out, key=lambda x: x["total_new_pick_w"])
    return {"available": True, "T_C": T, "bundle": bundle, "enumeration": p.name,
            "non_selected_parts": "the selected member's devices and capacitor at the same count",
            "per_count": out,
            "optimum_M": order[0]["M"], "order": [x["M"] for x in order],
            "max_abs_reproduction_error_w": max(chk.values()),
            "n_counts_pick_changes": sum(x["changes"] for x in out)}


def grid_section():
    files = {n: GRID / f"case_D_{n}.csv" for n in ("n50_all", "n99_sel", "n197_sel", "n197_all",
                                                   "n785_all")}
    have = {k: dse_rows(v) for k, v in files.items() if v.exists()}
    if not have:
        return {"available": False}
    sec = {"available": True, "engine_grid_definition": {
        "file": "Scalable_Integrated_VR/src/HVR_FULL_OPT_EPC_V2.py:1293 (run_hvr_optimization) "
                "and HVR_FULL_OPT_sizing.py:644",
        "code": "f_sw_values = np.logspace(np.log10(0.043e6), np.log10(200e6), 50)",
        "step": "log10 step 0.0748 (18.8 % per point); finer grids 99/197/785 points are nested "
                "(every original point retained)"},
        "private_engine": str(SCR / "engine"), "driver": str(SCR / "sweep_etm_private.py"),
        "runs": {}}
    for k, rows in have.items():
        sec["runs"][k] = [{"M": r["M"], "arch": f"N{r['N']}K{r['K']}K_A{r['K_A']}",
                           "f_sw_Hz": r["f_sw_Hz"], "hs": r["hs"], "ls": r["ls"],
                           "total_loss_W": r["total_loss_W"]} for r in rows]
    # ripple-gate boundary: the optimizer's frequency is the lowest feasible grid point
    ref = {r["M"]: r for r in have["n50_all"]}
    bnd = []
    for M, r in sorted(ref.items()):
        I = I_SYS / M
        D = r["N"] * V_OUT / V_IN
        fmin = D * (V_IN / r["N"] * r["K_A"] - V_OUT * r["K"]) / (L_IND * 0.5 * I)
        bnd.append({"M": M, "f_ripple_gate_Hz": fmin, "f_grid50_Hz": r["f_sw_Hz"],
                    "excess_pct": 100 * (r["f_sw_Hz"] / fmin - 1)})
    sec["ripple_gate_boundary"] = bnd
    for k, rows in have.items():
        order = [r["M"] for r in sorted(rows, key=lambda r: r["total_loss_W"])]
        sec.setdefault("optimum", {})[k] = {"optimum_M": order[0], "order": order}
    return sec


def dse_phase2(capmap):
    """The omitted terms on the phase-2 sweeps (extended count list, production converter
    rules) at each tier limit: does the screen optimum move? t4 (at most 4 tiers) is the
    production rule the design record's screen comes from (dse_phase2_summary.json)."""
    summ = json.loads(P2_SUMMARY.read_text()) if P2_SUMMARY.is_file() else {}
    out = {}
    for run in P2_RUNS:
        p = DSE_DATA / f"case_D_{run}.csv"
        rows = dse_rows(p) if p.is_file() else []
        if len(rows) < 2:
            continue
        s = (summ.get("runs") or {}).get(run) or {}
        a = dse_analysis(rows, capmap)
        m_csv = a["T_25C"]["paper_order"][0]
        m_sum = (s.get("optimum") or {}).get("M")
        out[run] = {"file": p.name, "what": s.get("what"), "max_tiers": s.get("max_tiers"),
                    "production_rule": run == P2_PRODUCTION, "screen_optimum_M": m_csv,
                    "summary_optimum_M": m_sum,
                    "consistent_with_summary": (m_sum is None) or int(m_sum) == m_csv,
                    "best_square_grid": s.get("best_square_grid"), "analysis": a}
    return out


def out_of_scope_flags(des, dse, coss, p2):
    """The checks outside the four terms, stated from the design and screens in force."""
    m, per = des["M"], dse["T_25C"]["per_count"]
    cs = next((x for x in coss if x["M"] == m), None)
    rows = list(per) + [x for r in p2.values() for x in r["analysis"]["T_25C"]["per_count"]]
    bad_cap = sorted({x["M"] for x in rows if not x["cap_within_derating"]})
    bad_hs = sorted({x["M"] for x in rows if not x["hs_within_derating"]})
    cap = CAP[des["cap"]]
    hs_v = float(_dev(des["hs"]).VDSmax)
    return {
        "coss_term": (
            f"the screen's C_OSS term ({COSS_RULE_SCREEN} rule) at the design point (M = {m}) is "
            f"{cs['model_coss_w']:.2f} W against {cs['datasheet_hard_turn_on_w']:.2f} W from the "
            f"datasheet charge curves for the same transitions (HS {cs['hs']}: "
            f"{cs['charge_basis']['hs']}; LS {cs['ls']}: {cs['charge_basis']['ls']}; published "
            f"term {cs['model_coss_legacy_w']:.2f} W); see out_of_scope_coss_check"
            if cs else "the design count is not a feasible screen point: see "
                       "out_of_scope_coss_check"),
        "flying_cap_rating": (
            f"C1 holds V_in(N-1)/N = {des['V_C_max']:.0f} V in the N={des['N']} cell; the "
            f"selected {des['cap']} is rated {cap.v_max:.0f} V "
            f"({100 * des['V_C_max'] / cap.v_max:.0f} % of its rating, limit "
            f"{100 * CAP_DERATING:.0f} %); screen counts outside the derating: "
            f"{bad_cap or 'none'}"),
        "stacked_hs_rating": (
            f"S2..SN block max(N-1, 2) V_in/N = {des['V_HS_stack_max']:.0f} V for N={des['N']} "
            f"(node swing {des['V_HS_stack_swing']:.0f} V); the {des['hs']} is rated "
            f"{hs_v:.0f} V ({100 * des['V_HS_stack_max'] / hs_v:.0f} % of its rating, limit "
            f"{100 * SW_DERATING:.0f} %); screen counts outside the derating: {bad_hs or 'none'}"),
    }


def main():
    global PAIRS, HEADLINE
    capmap = caps_from_rerun()
    rows = dse_rows(CASE_D)
    des = production_design(rows)
    cases = load_cases()
    PAIRS, HEADLINE = ranked_pairs(cases)
    arch, pairs = architecture_analysis(des, cases)
    fb = et_feedback(des, cases, arch)
    dse = dse_analysis(rows, capmap)
    p2 = dse_phase2(capmap)
    grid = grid_section()
    dse_grid = {}
    for k in ("n197_all", "n785_all"):
        p = GRID / f"case_D_{k}.csv"
        if p.exists():
            dse_grid[k] = dse_analysis(dse_rows(p), capmap)
    resel = {f"{bn}_{T:g}C": reselection_check(rows, T, bn, capmap)
             for bn in ("nominal", "high") for T in (25.0, 100.0)}
    ties = {}
    for k, path in (("n50", CASE_D), ("n197_all", GRID / "case_D_n197_all.csv"),
                    ("n785_all", GRID / "case_D_n785_all.csv")):
        if path.exists():
            for T in (25.0, 100.0):
                ties[f"{k}_{T:g}C"] = tie_analysis(dse_rows(path), capmap, T)
    coss = coss_check(rows, capmap)
    # what the production cell looks like electrically (for the record)
    br0 = des["branches"][0]
    prod = {
        "design": {k: des[k] for k in ("design", "M", "N", "K", "K_A", "B", "D", "f", "I_vr", "hs",
                                       "ls", "cap", "dI_branch", "dI_out_model", "I_b", "V_C_max",
                                       "V_HS_stack_max", "V_HS_stack_swing",
                                       "model_loss_25C_per_vr_w", "record_loss_per_vr_w",
                                       "case_D_loss_per_vr_w", "case_D_total_loss_w",
                                       "case_D_file", "case_D_row_is_design",
                                       "digitized_stand_in", "record_screen")},
        "flying_cap_C_eff_uF_at_25C": (
            [1e6 * c for c in c_eff_positions(des["cap"], des["N"], 25.0)]
            if c_eff_positions(des["cap"], des["N"], 25.0) else None),
        "inductor": {"name": IND_NAME, "L_nH": L_IND * 1e9, "R_dc_mOhm_25C": RDC25 * 1e3,
                     "I_sat_A": ISAT, "envelope_mm3": V_ENV * 1e9,
                     "source": IND[IND_NAME].source,
                     "material": "Taiyo Yuden TY-M5 metal composite (mu_r 15, B_sat 1.25 T), per "
                                 "the cited source (Rasheedi et al., inductor-array TCPMT "
                                 "manuscript, Table II, Fig. 6)",
                     "provenance_caveat": "the cited segment is 50 nH / 8.2 mOhm in 0.2 mm2; "
                                          "250 nH equals five segments in series while 1.6 mOhm "
                                          "equals five in parallel, so no flux density follows "
                                          "from the library entry itself -- the core loss is "
                                          "therefore bracketed by three flux models"},
        "per_branch": {"I_avg_A": br0["I_avg"], "dI_pp_A": br0["dI"], "I_valley_A": br0["I_valley"],
                       "I_peak_A": br0["I_peak"], "V_sw_V": br0["V_sw"]},
        "dead_time_events": {
            "per_LS_device_per_period": 2, "per_cell_per_period": 2 * des["K"],
            "currents": "valley (full t_dt, before HS turn-on) and peak (t_dt - t_c, after HS "
                        "turn-off); HS devices never reverse-conduct",
            "t_c_ns": [((q_oss_nC(des["hs"], br0["V_sw"]) + q_oss_nC(des["ls"], br0["V_sw"]))
                        / br0["I_peak"])],
            "V_SD_at_I_b_25C_V": v_sd(des["ls"], br0["I_avg"], 25.0),
            "V_SD_at_I_b_125C_V": v_sd(des["ls"], br0["I_avg"], 125.0),
            "V_SD_table_anchored_at_I_b_25C_V": v_sd(des["ls"], br0["I_avg"], 25.0, "table"),
        },
        "core": {"tri_factor_nominal": tri_factor(des["D"], 1.25, BETA),
                 "B_pk_mT": {k: 1e3 * v["b_per_a"] * br0["dI"] / 2 for k, v in CORE_CASES.items()},
                 "B_dc_mT": {k: 1e3 * v["b_per_a"] * br0["I_avg"] for k, v in CORE_CASES.items()},
                 "cases": {k: v["why"] for k, v in CORE_CASES.items()}},
        "ac_winding": {"F_at_fsw": {m: f_ratio(des["f"] / 1e6, m) for m in ("low", "nominal",
                                                                            "high")},
                       "R_ac_at_fsw_mOhm_25C": {m: RDC25 * 1e3 * f_ratio(des["f"] / 1e6, m)
                                                for m in ("low", "nominal", "high")},
                       "fit_nominal_a_b": list(map(float, RAC_U)),
                       "fit_high_dowell_t_um_m": list(map(float, RAC_D))},
    }
    t_c_ns = 1e9 * ((q_oss_nC(des["hs"], br0["V_sw"]) + q_oss_nC(des["ls"], br0["V_sw"]))
                    * 1e-9 / br0["I_peak"])
    ls_dig = _dig(des["ls"])
    ls_note = ("" if ls_dig == des["ls"] else
               f"; the low side {des['ls']} has no digitized curves: the {ls_dig} curves "
               f"stand in (declared)")
    cv = c_eff_positions(des["cap"], des["N"], 25.0)
    out = {
        "_what": "Omitted converter losses (dead time, core, AC winding, dielectric) for the "
                 "integration-study regulator (the design record's production converter, M = "
                 f"{des['M']}) at each case's own tier temperatures, and for every feasible count "
                 f"of the regulator-count screen (case D, {CASE_D.name}; the phase-2 sweeps at "
                 "each tier limit). Bundles: low / nominal / high (see 'assumptions').",
        "assumptions": {
            "bundles": {k: {kk: (vv * 1e9 if kk == "t_dt" else vv) for kk, vv in v.items()}
                        for k, v in BUNDLES.items()},
            "dead_time": {
                "range_ns": [2, 10], "nominal_ns": 5,
                "justification": "TI LMG1210 (GaN half-bridge driver, SNOSD12D): minimum dead time "
                                 "0.8 ns typ / 3.1 ns max, adjustable to 20 ns, HO/LO delay "
                                 "mismatch 1 ns typ / 3.4 ns max; at 2 ns the switch node of this "
                                 f"cell (t_c ~ {t_c_ns:.1f} ns at the peak current) just completes "
                                 "its transition, so < 2 ns is not realizable without "
                                 "shoot-through risk; 10 ns is half the driver's maximum setting "
                                 "and a conservative fixed dead time at sub-MHz switching",
                "V_SD": "datasheet reverse characteristic (V_GS = 0, 25/125 C) digitized; 'table' "
                        "variant shifts it to the tabulated V_SD(0.5 A) (EPC2057 1.4 V, EPC2090 "
                        "1.5 V; the EPC2057 figure reads ~2.4 V at 1 A -- the datasheet is "
                        "internally inconsistent)" + ls_note,
                "commutation": "t_c = (Q_OSS,HS + Q_OSS,LS)(V_in/N) / I_peak; high bundle sets t_c = 0"},
            "core": {"material": "TY-M5 (Taiyo Yuden metal composite) specific loss at 10 MHz "
                                 "digitized from the cited source: P_v = %.4g W/m3 x (B_pk/1 mT)^%.4f"
                                 % (K10, BETA),
                     "frequency_scaling": "P_v ~ f^alpha, alpha 1.0 (upper bound) to 1.5; iGSE "
                                          "triangular-flux factor at the buck duty",
                     "temperature": "metal composite: no temperature coefficient (nominal); "
                                    "'ferrite_like' sensitivity uses the Ferroxcube 3F4 "
                                    "500 kHz / 50 mT curve normalized at 25 C",
                     "cases": {k: v["why"] for k, v in CORE_CASES.items()}},
            "ac_winding": "R_ac/R_dc vs frequency of the cited segment (FEM, Fig. 9b, 3-98 MHz) "
                          "applied to the library DCR; below 3 MHz: nominal R_dc + a f^b fit, high "
                          "Dowell fit, low quadratic eddy regime; temperature via delta ~ "
                          "sqrt(rho/f); includes the ripple the model books with the summed "
                          "output ripple instead of the per-branch ripple",
            "dielectric": (
                f"the rated {des['cap']} has a vendor ESR(f) at each bias, and the production "
                "rules book every flying capacitor at its ESR at f_sw and the C_1 bias "
                "(HVR_FULL_OPT_EPC_V2.cap_esr_mohm, CAP_ESR_F; dielectric loss at f_sw "
                "included): the omitted term is the residual sum_n I_n^2 ESR(n f_sw, V_Cj) - "
                "booked over the odd harmonics of the +/-I_b pulse current and the capacitors' "
                "own biases (vendor 25-C data, log-f interpolation, clamped beyond the table; "
                "one value for every bundle); a part without ESR(f) data (published library, "
                "ESR at ~10 MHz) omits the whole ESR_diel = DF/(2 pi f C_eff), DF (class-II "
                "MLCC, 1/2.5/10 %) falling 0.4 %/K (floor 30 %), C_eff its vendor DC-bias "
                "capacitance if known, else 100 / 50 / 30 % of nominal"
                if _esr_table(des["cap"], V_IN / des["N"]) is not None else
                "ESR_diel = DF/(2 pi f C_eff) over the odd harmonics of the flying-cap "
                "current; the library ESR is specified at ~10 MHz "
                "(HVR_FULL_OPT_EPC_V2.Capacitor.esr_mohm), where the dielectric share "
                "is negligible, so the whole dielectric term is counted as omitted; DF "
                "(class-II MLCC, 1/2.5/10 %) falls 0.4 %/K (floor 30 %); C_eff: "
                + (f"{des['cap']}'s own DC-bias capacitance at each flying-capacitor "
                   "position (vendor data less tolerance, at the case temperature; "
                   + ", ".join(f"{1e6 * c:.3f}" for c in cv) + " uF at 25 C)"
                   if cv else "100 / 50 / 30 % of the nominal capacitance "
                              "(low / nominal / high)")),
            "dse_temperature": "the DSE scores components at 25 C; omitted terms evaluated at "
                               "25 C and at 100 C (a uniform operating temperature)",
            "pairs": "every pair of integrations under one cooling, oriented by the package loss "
                     "of the cases in force; headline = the best against the runner-up",
        },
        "production_cell": prod,
        "cases": arch,
        "pairs": pairs,
        "headline_pairs": [p for p in pairs if (p["better"], p["worse"]) in HEADLINE],
        "electrothermal_feedback_estimate": fb,
        "dse_case_D": dse,
        "dse_flip_requirement_nominal_25C": flip_requirement_dse(dse["T_25C"]["per_count"]),
        "dse_phase2": p2,
        "dse_refined_grid_with_omitted": dse_grid,
        "dse_omitted_aware_reselection": resel,
        "dse_tie_analysis": ties,
        "fsw_grid_sensitivity": grid,
        "sources": {
            "EPC2057": DIG["_provenance"]["url"]["EPC2057"],
            "EPC2014C": DIG["_provenance"]["url"]["EPC2014C"],
            "EPC2090": DIG["_provenance"]["url"]["EPC2090"],
            "LMG1210": DIG["_provenance"]["url"]["LMG1210"],
            "Ferroxcube_3F4": DIG["_provenance"]["url"]["3F4"],
            "inductor_source": "Rasheedi, Abdelzaher, ... (TCPMT manuscript, local PDF "
                               + DIG["_provenance"]["pdf"]["IND_SRC"] + "), Table II, Figs. 6c, 9b",
            "flying_capacitor": getattr(CAP[des["cap"]], "source", des["cap"]),
            "case_D_screen": CASE_D.relative_to(RES).as_posix(),
        },
        "out_of_scope_coss_check": {
            "model_rule": COSS_RULE_SCREEN,
            "per_count": coss,
            "order_with_nominal_omitted_plus_coss_25C": sorted(
                [x["M"] for x in coss],
                key=lambda M: next(p["total_with_nominal_w"] for p in dse["T_25C"]["per_count"]
                                   if p["M"] == M) + next(x["underestimate_w"] for x in coss
                                                          if x["M"] == M))},
        "out_of_scope_flags": out_of_scope_flags(des, dse, coss, p2),
    }
    out = {"summary": _summary(out), **out}
    OUT.write_text(json.dumps(_round(out), indent=1))
    print("wrote", OUT)
    _report(out)


def _round(x, sig=6):
    """Floats to `sig` significant digits (numpy scalars included) for a readable JSON."""
    if isinstance(x, dict):
        return {k: _round(v, sig) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, sig) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        return v if (v == 0 or not math.isfinite(v)) else float(f"{v:.{sig}g}")
    return x


def _dse_summary(sec_by_T):
    dse = {}
    for T, sec in sec_by_T.items():
        dse[T] = {bn: {"optimum_M": s["optimum_M"], "runner_up_M": s["runner_up_M"],
                       "margin_w": round(s["margin_w"], 2), "kendall_tau_vs_paper": round(s["kendall_tau"], 3),
                       "order": s["order"]} for bn, s in sec["summary"].items()}
        cb = sec["combinations_81"]
        dse[T]["screen_optimum_M"] = sec["paper_order"][0]
        dse[T]["combinations_81_optimum_moves"] = {
            "n": cb["n_optimum_moves"], "all_with_core_upper_bound": cb["n_moves_with_core_low_or_nominal"] == 0,
            "winners": sorted({c["optimum_M"] for c in cb["cases_optimum_moves"]}),
            "max_lead_w": round(max([c["margin_w"] for c in cb["cases_optimum_moves"]] or [0.0]), 2)}
    return dse


def _unchanged(secs):
    return all(s["optimum_M"] == sec[T]["paper_order"][0]
               for sec in secs for T in sec for s in sec[T]["summary"].values())


def _summary(o):
    def r_or_none(v, n):
        return None if v is None else round(v, n)
    hp = {f"{p['better']}_vs_{p['worse']}": {
        "gap_paper_w": round(p["gap_paper_w"], 3),
        "delta_omitted_w_low_nom_high": [round(p["delta_omitted_w"][b]["total_w"], 3)
                                         for b in ("low", "nominal", "high")],
        "delta_feedback_w_nom_high": [round(q[f"delta_feedback_{b}_w"], 3) for q in
                                      o["electrothermal_feedback_estimate"]["pairs"]
                                      if (q["better"], q["worse"]) == (p["better"], p["worse"])
                                      for b in ("nominal", "high")],
        "flips_any_bundle": any(p["flip"].values()),
        "scale_to_flip_nominal": p["scale_to_flip_nominal"],
        "generic_P_required_at_1pct_per_K_w": r_or_none(
            p["generic_requirement"]["P_required_at_1pct_per_K_w"], 1),
        "required_TC_sign": p["generic_requirement"]["required_TC_sign"],
        "headline": (p["better"], p["worse"]) in HEADLINE}
        for p in o["pairs"]}
    p2 = o.get("dse_phase2") or {}
    return {
        "architecture_rankings_flip": any(p["flip"][b] for p in o["pairs"] for b in p["flip"]),
        "pairs": hp,
        "headline_pairs": [f"{a}_vs_{b}" for a, b in HEADLINE],
        "omitted_total_w_production_A_Z1_low_nom_high": [
            round(o["cases"]["A_Z1"]["omitted"][b]["total_w"], 2) for b in ("low", "nominal", "high")]
        if "A_Z1" in o["cases"] else None,
        "design": o["production_cell"]["design"]["design"],
        "design_M": o["production_cell"]["design"]["M"],
        "dse": _dse_summary(o["dse_case_D"]),
        "dse_screen_file": CASE_D.name,
        "dse_phase2": {run: {"production_rule": r["production_rule"],
                             "max_tiers": r["max_tiers"],
                             "screen_optimum_M": r["screen_optimum_M"],
                             "consistent_with_summary": r["consistent_with_summary"],
                             **_dse_summary(r["analysis"])} for run, r in p2.items()},
        "dse_optimum_unchanged_all_bundles_grids_temperatures": _unchanged(
            [o["dse_case_D"]] + list(o["dse_refined_grid_with_omitted"].values())),
        "dse_phase2_optimum_unchanged_all_bundles_temperatures": {
            run: _unchanged([r["analysis"]]) for run, r in p2.items()},
        "fsw_grid_optimum": {k: v["optimum_M"] for k, v in o["fsw_grid_sensitivity"].get("optimum", {}).items()},
    }


def _report(o):
    pd = o["production_cell"]["design"]
    print("\nproduction (%s, M=%d): f=%.1f kHz dI_branch=%.3f A  model 25C %.4f W/VR (case D %s)" % (
        pd["design"], pd["M"], pd["f"] / 1e3, pd["dI_branch"], pd["model_loss_25C_per_vr_w"],
        "--" if pd["case_D_loss_per_vr_w"] is None else "%.4f" % pd["case_D_loss_per_vr_w"]))
    print("\n%-17s %7s %6s %6s %6s | %s" % ("case", "Ppkg", "Tls", "Tind", "Tcap",
                                           "omitted total low / nom / high  [DT core AC diel nominal]"))
    for k, c in o["cases"].items():
        om = c["omitted"]
        n = om["nominal"]
        print("%-17s %7.2f %6.1f %6.1f %6.1f | %6.2f %6.2f %6.2f  [%5.2f %5.2f %5.2f %5.2f]" % (
            k, c["P_package_w"], c["T_ls_C"], c["T_ind_C"], c["T_caps_C"], om["low"]["total_w"],
            n["total_w"], om["high"]["total_w"], n["dead_time_w"], n["core_w"], n["ac_winding_w"],
            n["dielectric_w"]))
    print("\npairs: gap, delta omitted (low/nom/high), flips")
    for p in o["pairs"]:
        d = p["delta_omitted_w"]
        print("  %-17s vs %-17s gap %6.2f  d %+6.3f %+6.3f %+6.3f  ferrite(nom/high) %+6.3f %+6.3f "
              "flip %s" % (p["better"], p["worse"], p["gap_paper_w"], d["low"]["total_w"],
                           d["nominal"]["total_w"], d["high"]["total_w"],
                           d["nominal_core_ferrite_like"]["total_w"],
                           d["high_core_ferrite_like"]["total_w"],
                           any(p["flip"].values())))
    fb = o["electrothermal_feedback_estimate"]
    print("\nE-T feedback of the omitted heat (modeled-loss rise), per case nominal/high:")
    for k, r in fb["per_case"].items():
        print("  %-17s loop %.4f  slope_ls %.3f K/W  +%.2f / +%.2f W" % (
            k, r["loop_gain"], r["dT_dP_K_per_W"]["ls"], r["feedback_nominal_w"], r["feedback_high_w"]))
    for p in fb["pairs"]:
        print("  %-17s vs %-17s  d_feedback nominal %+.3f high %+.3f" % (
            p["better"], p["worse"], p["delta_feedback_nominal_w"], p["delta_feedback_high_w"]))
    secs = [("case D", T, sec) for T, sec in o["dse_case_D"].items()]
    secs += [(run, T, sec) for run, r in (o.get("dse_phase2") or {}).items()
             for T, sec in r["analysis"].items()]
    for name, T, sec in secs:
        print("\nDSE", name, T, "paper order", sec["paper_order"])
        for p in sec["per_count"]:
            print("  M=%3d %-9s f=%6.1f kHz paper %6.2f | +omit low %6.2f nom %6.2f high %6.2f "
                  "[nom DT %5.2f core %5.2f AC %5.2f diel %5.2f]" % (
                      p["M"], p["arch"], p["f_sw_Hz"] / 1e3, p["paper_total_w"],
                      p["total_with_low_w"], p["total_with_nominal_w"], p["total_with_high_w"],
                      p["nominal"]["dead_time_w"], p["nominal"]["core_w"],
                      p["nominal"]["ac_winding_w"], p["nominal"]["dielectric_w"]))
        for bn, s in sec["summary"].items():
            print("  %-8s optimum M=%d (runner-up %d, margin %.2f W) tau=%.3f order %s" % (
                bn, s["optimum_M"], s["runner_up_M"], s["margin_w"], s["kendall_tau"], s["order"]))
        cb = sec["combinations_81"]
        m0 = cb["screen_optimum_M"]
        print("  81 combos: optimum moves from M=%d in %d (core high %d, core low/nominal %d); "
              "min margin when M=%d = %s" % (m0, cb["n_optimum_moves"], cb["n_moves_with_core_high"],
                                             cb["n_moves_with_core_low_or_nominal"], m0,
                                             cb["min_margin_w"]))
        for c in cb["cases_optimum_moves"]:
            print("     moves:", {k: (round(float(v), 3) if not isinstance(v, str) else v)
                                  for k, v in c.items()})
        c0 = sec["combinations_27_dead_time_tc0"]
        print("  27 combos with the t_c = 0 dead-time over-bound: optimum moves from M=%d in %d %s"
              % (m0, c0["n_optimum_moves"],
                 sorted({(c["optimum_M"]) for c in c0["cases_optimum_moves"]})))
    fr = o["dse_flip_requirement_nominal_25C"]
    print("\nflip requirement (nominal, 25 C) vs the screen optimum M=%s:"
          % (fr[0]["vs_M"] if fr else "--"))
    for r in o["dse_flip_requirement_nominal_25C"]:
        print("  count %3d gap %6.2f  d_omit %+6.2f  scale_to_tie %s  core_scale %s" % (
            r["M"], r["gap_paper_w"], r["delta_omitted_nominal_w"], r["scale_to_tie"],
            r["core_scale_to_tie"]))
    for k, lst in o["dse_tie_analysis"].items():
        print("tie", k, [(r["M"], None if r["t_dt_tie_ns"] is None else round(r["t_dt_tie_ns"], 1),
                          None if r["core_scale_to_tie_at_2ns"] is None
                          else round(r["core_scale_to_tie_at_2ns"], 1)) for r in lst])
    for k, sec in o["dse_refined_grid_with_omitted"].items():
        for T, s in sec.items():
            print("refined", k, T, {bn: (v["optimum_M"], round(v["margin_w"], 2)) for bn, v in
                                    s["summary"].items()},
                  "81-combo moves", s["combinations_81"]["n_optimum_moves"])
    for k, r in o["dse_omitted_aware_reselection"].items():
        if r.get("available"):
            print("reselection", k, "optimum", r["optimum_M"], "picks changed",
                  r["n_counts_pick_changes"], "repro err %.2e" % r["max_abs_reproduction_error_w"],
                  "order", r["order"])
        else:
            print("reselection", k, "not available:", r.get("why"))
    g = o["fsw_grid_sensitivity"]
    if g.get("available"):
        print("grid optimum:", {k: v["optimum_M"] for k, v in g["optimum"].items()})
    cc = o["out_of_scope_coss_check"]
    print("C_OSS check (outside scope, model rule %s): (M, model, datasheet curves, published)"
          % cc["model_rule"], [(x["M"], round(x["model_coss_w"], 2),
                                round(x["datasheet_hard_turn_on_w"], 2),
                                round(x["model_coss_legacy_w"], 2)) for x in cc["per_count"]])
    for k, v in o["out_of_scope_flags"].items():
        print("  flag", k + ":", v)
    print("  order with nominal omitted + C_OSS deficit:", cc["order_with_nominal_omitted_plus_coss_25C"])


if __name__ == "__main__":
    main()
