"""The feasibility stage (TCPMT review round 2): every declared limit, on every case and variant,
BEFORE any ranking.

A candidate that fails any limit is not ranked. Every case file of the study is evaluated --
the compared cases of each input state (tcpmt_cases: production = implemented decoupling,
references S0 and S1), the robustness variants (interface feedback, die hot spot, conductivity,
cooling-model form, decoupling, attach/board/TSV decisions), case A1 (rated flying capacitors)
and the regulator-count study.

LIMITS (declared, with sources; LIMITS below)
  GaN junction        T_J <= the device's own T_J maximum, per device tier (DEVICES: the EPC
                      datasheet of every part the converter synthesis can select; 150 C for all
                      of them): the tier's maximum inside the cells plus the device's R_thJC at
                      its own dissipation (P_tier / (N cells x devices per cell)); never the
                      whole-field maximum
  R_DS(on) fit        each device's junction bound <= the upper end of its own fit range
                      (DEVICES ron_fit_C: the coefficients are linear-equivalent fits of the
                      datasheet normalized R_DS(on) vs T_J curves over 25-125 C)
  MLCC                X7R/X7S/X7T class <= 125 C: flying-capacitor tier and the inductor tier
                      (it holds C_out), in the cells
  inductor            <= 125 C (inductor tier in the cells)
  build-up dielectric Tg ~ 150 C, every RDL tier element (converter and package RDL)
  encapsulant         Tg ~ 150 C, converter-tier elements outside the cells
  board laminate      Tg ~ 170 C (high-Tg FR-4 class), every board element
  processor die       T_die,max <= 105 C (NEW, declared): die_T_max_C of the case file when the
                      chain recorded it, else the die layer of the converged field
  solder law          the hottest joint of the all-site search <= 125 C (the calibrated range of
                      the SAC305 law; the critical joint is reported too); solidus 217 C
  BGA provisioning    (a) the PEAK PER-BALL CURRENT against the 1.5-A target (the engineering
                      rule) at the case's own waveform: the solved per-ball peak fraction of the
                      package network at the case's ball count x the case's 48-V RMS current
                      (the DC peak x k rule; Z1, Z2's BGA-ring feed) and, for Z1 in the
                      production state, the worst-ball RMS of the harmonic port model
                      (input_decoupling.json ball_currents_recommended, scaled to the case's
                      48-V current); the check takes the WORSE of the two and reports both;
                      Z3's 1-V balls at DC with equal sharing. BGA_POLICY decides how it enters
                      (review round 3; the authors decide): "hard" = a filter (fails the
                      candidate), "requirement" (default) = a stated requirement on the package,
                      reported but not a filter. Every record carries its verdict under BOTH
                      policies and the rankings are stored for both (apply_bga_policy applies
                      either to a stored feasibility.json without rerunning). (b) at least 25 %
                      of the package's own ball sites left for signal and auxiliary nets
                      (always a filter)
  static IR drop      per-rail MAXIMUM static drop of the 1-V path <= 30 mV (tcpmt_ir_drop)
  operating point     the E-T fixed point (and, for the interface feedback, the feedback
                      iteration) converged; a run-away has no operating point

SOURCES OF THE REGION TEMPERATURES, in order: the case's thermal.region_T_max_C (recorded by the
chain since review round 2) / die_T_max_C; the stored converged deck and field
(tcpmt_region_temps.deck_region_maxima, located by tcpmt_cases.converged_field); else the
whole-field peak as a BOUND -- a check that passes on the bound passes, one that fails only on
the bound is UNRESOLVED (the candidate is then not ranked either).

OMITTED CONVERTER LOSSES. The margins are re-checked with the high bundle of
research/tcpmt_revision/omitted_losses.json (dead time, core, AC winding, dielectric) plus its
electrothermal feedback, each region raised by its own dT/dP from the case's first two E-T
iterations (the slope the omitted-loss study used).

    python tcpmt_feasibility.py [--no-fields]   -> research/tcpmt_revision/feasibility.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

R = Path(__file__).resolve().parents[1]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0d", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))
import tcpmt_cases as TC                                            # noqa: E402

FC = TC.FC
SENS = TC.SENS
TR = TC.TR
OUT = TR / "feasibility.json"

LIMITS = {"gan_Tj_C": 150.0, "ron_fit_max_C": 125.0, "mlcc_C": 125.0, "inductor_C": 125.0,
          "buildup_Tg_C": 150.0, "encapsulant_Tg_C": 150.0, "board_Tg_C": 170.0,
          "die_C": 105.0, "solder_cal_C": 125.0, "solder_solidus_C": 217.0,
          "bga_A_per_ball": 1.5, "bga_power_site_fraction_max": 0.75,
          "ir_drop_mV_per_rail": 30.0}
#: REVIEW ROUND 3 -- how the 1.5-A per-ball target enters the stage (the authors decide later;
#: both are evaluated on every record, so post-processing applies either without reruns):
#:   hard          the per-ball check is a FILTER: a case above 1.5 A per ball is infeasible
#:   requirement   the per-ball check is a STATED REQUIREMENT on the package (the current each
#:                 ball must carry), reported beside the verdict, not a filter (DEFAULT)
BGA_POLICIES = {"hard": "the per-ball check is a filter: above 1.5 A per ball the candidate is "
                        "infeasible",
                "requirement": "the per-ball check is a stated requirement on the package (the "
                               "current each ball must carry), reported, not a filter"}
BGA_POLICY = os.environ.get("TCPMT_BGA_POLICY", "requirement")
if BGA_POLICY not in BGA_POLICIES:
    raise SystemExit(f"TCPMT_BGA_POLICY={BGA_POLICY!r}: not one of {sorted(BGA_POLICIES)}")
#: the checks the policy switches (everything else is always a filter)
BGA_POLICY_CHECKS = ("bga_current",)
LIMIT_SOURCES = {
    "gan_Tj_C": "per device: the T_J maximum of the part's EPC datasheet, Maximum Ratings "
                "(DEVICES[part]['Tj_max_C']; 150 C for every part of the table); this value "
                "applies only to a part without a record",
    "ron_fit_max_C": "per device: the upper end of the T_J range the part's R_DS(on)(T_J) "
                     "coefficient is fitted over (DEVICES[part]['ron_fit_C'], 25-125 C: "
                     "linear-equivalent fit of the datasheet normalized R_DS(on) vs T_J curve, "
                     "scripts/phase0d/electrical.py); this value applies only to a part without "
                     "a record",
    "mlcc_C": "X7R/X7S/X7T temperature class of the library parts",
    "inductor_C": "declared (125 C class of the interposer inductor)",
    "buildup_Tg_C": "ABF-class build-up film Tg (declared)",
    "encapsulant_Tg_C": "encapsulant / underfill Tg (declared)",
    "board_Tg_C": "high-Tg FR-4 class laminate (declared)",
    "die_C": "processor die junction limit (DECLARED, review round 2)",
    "solder_cal_C": "calibrated range of the SAC305 constitutive law",
    "solder_solidus_C": "SAC305 solidus",
    "bga_A_per_ball": "1.5-A per-ball engineering rule (the count closure's criterion)",
    "bga_power_site_fraction_max": "DECLARED: at least 25 % of the package's own ball sites "
                                   "left for signal and auxiliary nets",
    "ir_drop_mV_per_rail": "DECLARED: 30 mV per rail (3 % of the 1-V rail), maximum static "
                           "drop of the 1-V path"}
#: GaN DEVICE TABLE: every part the converter synthesis can select (every "hs" / "ls" of
#: research/tcpmt_revision/dse_phase2_summary.json -- runs.*.optimum, .M49, .per_count.*,
#: robustness_larger_placement_budgets.* -- and the parts of design_49_cell_full_set). Values
#: from the public EPC datasheets (epc-co.com, retrieved 2026-11-18); "source" names the copy in
#: ETM_project/scratch/epc_ds/ (outside the repository; the EPC2014C / EPC2057 copies in
#: review_work/dl_epc are byte-identical), its revision, and the tables / figure used.
#:   Tj_max_C          upper end of the operating T_J range (Maximum Ratings)
#:   R_jc_K_W          R_thJC junction-to-case, typ (Thermal Characteristics); the case is the
#:                     die back ("Case TOP" where stated; EPC2366, PQFN: the exposed die on top)
#:   R_jb_K_W          R_thJB junction-to-board, typ
#:   R_ja_K_W          R_thJA, typ: on 1 in2 of 2-oz Cu, single-layer FR4 (datasheet note) where
#:                     given, else on the JEDEC 51-2 board (R_ja_note); None: not given
#:   die_mm            die size (bare die); package body (EPC2366)
#:   V_DS_V, I_D_A     continuous ratings; I_D at the printed condition I_D_cond
#:   R_ds_on_max_mohm  R_DS(on) max at V_GS = 5 V, T_J = 25 C (test current in R_ds_on_cond)
#:   height_um         mounted height incl. terminal, nominal (Side View; the values of
#:                     Scalable_Integrated_VR/src/HVR_epc_device_data.json)
#:   ron_curve_C       T_J span of the datasheet curve "normalized R_DS(on) vs T_J"
#:   ron_fit_C         T_J range of the model's linear-equivalent R_DS(on)(T_J) coefficient
#:                     (scripts/phase0d/electrical.py: 25-125 C); its upper end is the device's
#:                     limit in the ron_fit check
#:   ron_norm_125C     normalized R_DS(on) at T_J = 125 C, READ FROM THE FIGURE (300-dpi render,
#:                     axes calibrated on the grid lines; the same reading gives 1.00 +/- 0.004
#:                     at 25 C): +/- 0.01; alpha_ron_per_K = (ron_norm_125C - 1) / 100 K
DEVICES = {
    "EPC2014C": {"Tj_max_C": 150.0, "R_jc_K_W": 3.6, "R_jb_K_W": 9.3, "die_mm": [1.7, 1.1],
                 "V_DS_V": 40.0, "I_D_A": 10.0, "I_D_cond": "T_A = 25 C, R_thJA = 43 C/W",
                 "R_ja_K_W": 80.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                 "R_ds_on_max_mohm": 16.0, "R_ds_on_cond": "V_GS = 5 V, I_D = 10 A",
                 "package": "bare passivated die, solder bumps (outline: solder bars)",
                 "height_um": 685.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                 "ron_norm_125C": 1.60, "alpha_ron_per_K": 6.0e-3,
                 "source": "epc_ds/EPC2014C/EPC2014C.pdf, rev. May 22, 2021: Maximum Ratings, "
                           "Thermal and Static Characteristics (p. 1); Fig. 8 (p. 3)"},
    "EPC2057": {"Tj_max_C": 150.0, "R_jc_K_W": 2.3, "R_jb_K_W": 7.0, "die_mm": [1.5, 1.2],
                "V_DS_V": 50.0, "I_D_A": 9.6, "I_D_cond": "T_A = 25 C",
                "R_ja_K_W": 72.5, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (note 2); "
                                               "JEDEC 51-2 PCB 82, EPC90155 EVB 68.5",
                "R_ds_on_max_mohm": 8.5, "R_ds_on_cond": "V_GS = 5 V, I_D = 6 A",
                "package": "bare passivated die, solder bars",
                "height_um": 638.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.80, "alpha_ron_per_K": 8.0e-3,
                "source": "epc_ds/EPC2057/EPC2057.pdf, rev. April 8, 2025: Maximum Ratings, "
                          "Thermal and Static Characteristics (p. 1); Fig. 9 (p. 3)"},
    "EPC2055": {"Tj_max_C": 150.0, "R_jc_K_W": 1.0, "R_jb_K_W": 2.5, "die_mm": [2.5, 1.5],
                "V_DS_V": 40.0, "I_D_A": 29.0, "I_D_cond": "T_A = 25 C",
                "R_ja_K_W": 64.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                "R_ds_on_max_mohm": 4.2, "R_ds_on_cond": "V_GS = 5 V, I_D = 15 A",
                "package": "bare passivated die, solder bars (outline: solder bumps)",
                "height_um": 638.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.60, "alpha_ron_per_K": 6.0e-3,
                "source": "epc_ds/EPC2055/EPC2055.pdf, rev. June 20, 2025: Maximum Ratings, "
                          "Thermal and Static Characteristics (p. 1); Fig. 9 (p. 3)"},
    "EPC2090": {"Tj_max_C": 150.0, "R_jc_K_W": 1.07, "R_jb_K_W": 2.9, "die_mm": [2.3, 1.45],
                "V_DS_V": 100.0, "I_D_A": 46.0, "I_D_cond": "T_J <= 125 C",
                "R_ja_K_W": None, "R_ja_note": "not given",
                "R_ds_on_max_mohm": 5.2, "R_ds_on_cond": "V_GS = 5 V, I_D = 16 A",
                "package": "bare passivated die, Cu pillars (datasheet: for use inside a "
                           "package, not for PCB mounting); R_thJC to Case TOP, R_thJB to Case "
                           "BOTTOM",
                "height_um": 606.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.57, "alpha_ron_per_K": 5.7e-3,
                "source": "epc_ds/EPC2090/EPC2090.pdf, rev. December 19, 2024 (last page: July "
                          "2024): Maximum Ratings, Thermal and Static Characteristics (p. 1); "
                          "Fig. 9 (p. 3)"},
    "EPC2214": {"Tj_max_C": 150.0, "R_jc_K_W": 2.7, "R_jb_K_W": 7.5, "die_mm": [1.35, 1.35],
                "V_DS_V": 80.0, "I_D_A": 10.0, "I_D_cond": "T_A = 25 C",
                "R_ja_K_W": 81.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                "R_ds_on_max_mohm": 20.0, "R_ds_on_cond": "V_GS = 5 V, I_D = 6 A",
                "package": "bare passivated die, solder bumps (AEC-Q101)",
                "height_um": 805.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.65, "alpha_ron_per_K": 6.5e-3,
                "source": "epc_ds/EPC2214/EPC2214.pdf, rev. April 25, 2025: Maximum Ratings, "
                          "Thermal and Static Characteristics (p. 1); Fig. 9 (p. 3)"},
    "EPC2366": {"Tj_max_C": 150.0, "R_jc_K_W": 0.6, "R_jb_K_W": 1.8, "die_mm": [3.3, 2.6],
                "V_DS_V": 40.0, "I_D_A": 88.0, "I_D_cond": "T_J < 125 C",
                "R_ja_K_W": 54.0, "R_ja_note": "JEDEC 51-2 PCB (no 1-in2 value); EPC90167 EVB "
                                               "26",
                "R_ds_on_max_mohm": 1.0, "R_ds_on_cond": "V_GS = 5 V, I_D = 30 A",
                "package": "PQFN 3.3 x 2.6 mm (die_mm: the package body), exposed die 2.5 x "
                           "1.8 mm on top; R_thJC to Case TOP (the exposed die), R_thJB to Case "
                           "BOTTOM (terminals)",
                "height_um": 700.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.53, "alpha_ron_per_K": 5.3e-3,
                "source": "epc_ds/EPC2366/EPC2366.pdf, rev. June 12, 2026: Maximum Ratings, "
                          "Thermal Characteristics (p. 1), Static Characteristics (p. 2), "
                          "Package Outline (p. 9); Fig. 9 (p. 4)"},
    "EPC7003": {"Tj_max_C": 150.0, "R_jc_K_W": 2.8, "R_jb_K_W": 5.6, "die_mm": [1.7, 1.1],
                "V_DS_V": 100.0, "I_D_A": 10.0, "I_D_cond": "not stated",
                "R_ja_K_W": 130.0, "R_ja_note": "JEDEC 51-2 PCB (no 1-in2 value); EPC9006C EVB "
                                                "88",
                "R_ds_on_max_mohm": 30.0, "R_ds_on_cond": "V_GS = 5 V, I_D = 6 A",
                "package": "bare passivated die (rad hard), 95Pb/5Sn solder bars (text: solder "
                           "bumps); R_thJC to Case TOP, R_thJB to Case BOTTOM",
                "height_um": 782.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.77, "alpha_ron_per_K": 7.7e-3,
                "source": "epc_ds/EPC7003/EPC7003.pdf, PRELIMINARY (stamp on p. 1), rev. July "
                          "17, 2025: Maximum Ratings, Thermal and Static Characteristics "
                          "(p. 1); Fig. 9 (p. 3)"},
    "EPC2212": {"Tj_max_C": 150.0, "R_jc_K_W": 2.0, "R_jb_K_W": 4.0, "die_mm": [2.1, 1.6],
                "V_DS_V": 100.0, "I_D_A": 18.0, "I_D_cond": "T_A = 25 C",
                "R_ja_K_W": 69.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                "R_ds_on_max_mohm": 13.5, "R_ds_on_cond": "V_GS = 5 V, I_D = 11 A",
                "package": "bare passivated die, solder bars (AEC-Q101)",
                "height_um": 685.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.75, "alpha_ron_per_K": 7.5e-3,
                "source": "epc_ds/EPC2212/EPC2212.pdf, rev. April 4, 2026: Maximum Ratings, "
                          "Thermal and Static Characteristics (p. 1); Fig. 9 (p. 3)"},
    "EPC2035": {"Tj_max_C": 150.0, "R_jc_K_W": 6.5, "R_jb_K_W": 65.0, "die_mm": [0.9, 0.9],
                "V_DS_V": 60.0, "I_D_A": 1.7, "I_D_cond": "T_A = 25 C, R_thJA = 546 C/W "
                                                          "(as printed)",
                "R_ja_K_W": 100.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                "R_ds_on_max_mohm": 45.0, "R_ds_on_cond": "V_GS = 5 V, I_D = 1 A",
                "package": "bare passivated die, solder bumps",
                "height_um": 625.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.57, "alpha_ron_per_K": 5.7e-3,
                "source": "epc_ds/EPC2035/EPC2035.pdf, rev. April 22, 2021: Maximum Ratings, "
                          "Thermal (R_thJB 65 C/W as printed) and Static Characteristics "
                          "(p. 1); Fig. 8 (p. 3)"},
    "EPC2012C": {"Tj_max_C": 150.0, "R_jc_K_W": 4.2, "R_jb_K_W": 12.5, "die_mm": [1.7, 0.9],
                 "V_DS_V": 200.0, "I_D_A": 5.0, "I_D_cond": "T_A = 25 C, R_thJA = 26 C/W",
                 "R_ja_K_W": 85.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                 "R_ds_on_max_mohm": 100.0, "R_ds_on_cond": "V_GS = 5 V, I_D = 3 A",
                 "package": "bare passivated die, solder bars",
                 "height_um": 685.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                 "ron_norm_125C": 1.68, "alpha_ron_per_K": 6.8e-3,
                 "source": "epc_ds/EPC2012C/EPC2012C.pdf, rev. April 22, 2021: Maximum Ratings, "
                           "Thermal and Static Characteristics (p. 1); Fig. 8 (p. 3; axis "
                           "labelled from -25 C, curve drawn 0-150 C)"},
    "EPC7002": {"Tj_max_C": 150.0, "R_jc_K_W": 3.6, "R_jb_K_W": 9.3, "die_mm": [1.7, 1.1],
                "V_DS_V": 40.0, "I_D_A": 10.0, "I_D_cond": "not stated",
                "R_ja_K_W": 80.0, "R_ja_note": "1 in2 Cu, single-layer 2-oz FR4 (Note 1)",
                "R_ds_on_max_mohm": 14.5, "R_ds_on_cond": "V_GS = 5 V, I_D = 10 A",
                "package": "bare passivated die (rad hard), 95Pb/5Sn solder bars",
                "height_um": 782.0, "ron_curve_C": [0.0, 150.0], "ron_fit_C": [25.0, 125.0],
                "ron_norm_125C": 1.71, "alpha_ron_per_K": 7.1e-3,
                "source": "epc_ds/EPC7002/EPC7002.pdf, PRELIMINARY (stamp on p. 1), rev. July "
                          "17, 2025: Maximum Ratings, Thermal and Static Characteristics "
                          "(p. 1); Fig. 9 (p. 3)"},
}
#: the BGA field of each package outline (0.8-mm lattice): Z2 has the board opening
BGA_SITES = {"Z1": 1369, "Z3": 1369, "Z2": 528, "Z2BF": 528}
#: a temperature check within this of its limit is reported MARGINAL (the numerical uncertainty
#: of the compared peak temperatures is 1.9-3.2 K, uncertainty.json); the verdict is unchanged
MARGINAL_K = 2.0

LAYER_KEYS = ("hs", "ls", "caps", "ind")


# ------------------------------------------------------------------ the case list
def _variant_name(path):
    s = Path(path).stem
    return s.split("__", 1)[1] if "__" in s else None


def classify(path, case):
    """(role, state, tier) of a case file. Roles: compared (a cell of a tcpmt_cases table),
    variant (robustness / design variant), count (regulator-count study), superseded."""
    p = Path(path)
    for st in TC.STATES:
        for t in TC.TIERS:
            for a in TC.ARCHS:
                q = TC.case_path(st, t, a)
                if q is not None and q.resolve() == p.resolve():
                    return "compared", st, t
    if TC.is_superseded(p):
        return "superseded", _state(case), _tier(p, case)
    if "countopt" in p.parts:
        return "count", _state(case), "A"
    return "variant", _state(case), _tier(p, case)


def _state(case):
    inv = {v: k for k, v in TC.SCEN.items()}
    return inv.get(case.get("scenario"), case.get("scenario"))


def _tier(path, case):
    v = _variant_name(path) or ""
    if case.get("tier") in ("A", "B"):
        return case["tier"]
    if v.endswith("_A") or v.endswith("_A_fvmap") or "_A_" in v or v in ("z3_top_only",):
        return "A"
    if (v.endswith("_B") or "_B_" in v or v.endswith("_B_fvmap") or v in (
            "z1_bottom_plate_tim", "z2_cooled_tim", "z3_plate_tim")):
        return "B"
    if v == "z2_cooled" or (case.get("arch") == "Z3" and not v):
        return "I"            # interface-free bottom plate (a bound)
    return "A"


def all_case_files():
    out = []
    for f in sorted(FC.glob("etm_*_h1.1_r21.json")):
        out.append(f)
    out += sorted(SENS.glob("etm_*__*.json"))
    out += sorted((TR / "countopt").glob("etm_Z1_*_h1.1_r21.json"))
    return out


def runaway_records():
    """Interface-feedback runs without a converged case file (run-away): the last pass."""
    rv = TR / "review_variants"
    out = []
    for a in TC.ARCHS:
        for scen in sorted({p.name.split("_")[2] + "_" + p.name.split("_")[3]
                            for p in rv.glob(f"etm_{a}_HV_*__tim_warp_fb_*_it*.json")}):
            for t in ("A", "B"):
                if (SENS / f"etm_{a}_{scen}__tim_warp_fb_{t}.json").is_file():
                    continue
                its = sorted(rv.glob(f"etm_{a}_{scen}__tim_warp_fb_{t}_it*.json"),
                             key=lambda p: int(p.stem.rsplit("_it", 1)[1]))
                if its:
                    out.append(its[-1])
    return out


# ------------------------------------------------------------------ inputs per case
def design_of(case):
    """n_vr, devices per cell, parts of the converter the case was computed with."""
    d = case.get("design") or {}
    conv = next((r.get("converter") for r in case.get("ledger_rows") or []
                 if isinstance(r.get("converter"), dict)), None) or {}
    topo = d.get("topology") or {}
    if isinstance(topo, dict) and topo:
        n_, k_ = int(topo["N"]), int(topo["K"])
    elif conv.get("topology"):
        n_, k_ = int(conv["topology"][0]), int(conv["topology"][1])
    else:
        n_, k_ = 3, 3                          # the production N3K3K_A2 (legacy records)
    return {"n_vr": int(d.get("n_vr") or conv.get("n_vr") or 49),
            "hs_part": d.get("hs_part") or conv.get("hs") or "EPC2014C",
            "ls_part": d.get("ls_part") or conv.get("ls") or "EPC2057",
            "hs_per_cell": n_, "ls_per_cell": k_}


def _tier_power(case, key):
    term = {"hs": "P_conv_hs", "ls": "P_conv_ls"}[key]
    return sum(r["P_w"] for r in case["ledger_rows"] if r["term"] == term)


def region_temperatures(path, case, use_fields=True):
    """({region: max C}, source) -- recorded, deck, or the whole-field bound."""
    th = case.get("thermal") or {}
    rec = th.get("region_T_max_C") or case.get("region_T_max_C")
    if isinstance(rec, dict) and rec.get("hs_in_cells") is not None:
        return dict(rec), "case file (chain)"
    if use_fields:
        p = Path(path)
        if "production converged field" in str(case.get("thermal_from", "")):
            # a mechanics-only variant: its thermal state IS the production case's
            import final_closure_physical_etm as E
            p = E.case_path(case["arch"], case["scenario"])
            case = json.loads(p.read_text())
        f = TC.converged_field(p, case)
        if f and f.get("inp"):
            import tcpmt_region_temps as RT
            try:
                r = RT.deck_region_maxima(f["inp"], f["thermal"], case)
                return r, "converged deck" + ("" if p == Path(path) else f" of {p.name}")
            except Exception as e:                          # noqa: BLE001 -- recorded
                return {"error": str(e)[-300:]}, "deck failed"
    return {}, "bound (whole-field peak)"


def die_max(case, reg):
    for v in (case.get("die_T_max_C"), (case.get("thermal") or {}).get("die_T_max_C"),
              (case.get("z3_land") or {}).get("T_die_max_C")):
        if isinstance(v, (int, float)):
            return float(v), "die_T_max_C (case file)"
    if reg.get("die") is not None:
        return float(reg["die"]), "die layer of the converged field"
    return None, None


def joints(case):
    js = (case.get("mechanics") or {}).get("joint_search") or {}
    ranked = js.get("ranked") or []
    crit = js.get("critical") or {}
    return {"T_critical_C": crit.get("T_C"),
            "T_hottest_C": max((r["T_C"] for r in ranked), default=None),
            "du_um": crit.get("du_um")}


# ------------------------------------------------------------------ BGA provisioning
_NET = {}


def _network(path=None):
    p = Path(path) if path else FC / "package_network.json"
    if p not in _NET:
        _NET[p] = json.loads(p.read_text()) if p.is_file() else {}
    return _NET[p]


def _screen():
    if "screen" not in _NET:
        f = FC / "bga_count_screen.csv"
        _NET["screen"] = list(csv.DictReader(f.open())) if f.is_file() else []
    return _NET["screen"]


def peak_fraction(net_arch, n, network=None):
    """Largest per-ball current per ampere of the 48-V rail current at n balls per rail:
    the converged network when n is its matched count, else the exhaustive screen (level 1) of
    the production network (never for another design's network)."""
    pn = _network(network)
    if pn and pn.get("matched_count") == n:
        conv = pn.get("convergence") or {}
        v = [conv.get(f"{net_arch}_{r}", {}).get("final", {}).get("i_ball_max_a")
             for r in ("supply", "return")]
        if all(x is not None for x in v):
            lv = max((pn.get("meta") or {}).get("final_levels") or [0])
            return max(v), f"package network (level {lv})"
    if network is None or Path(network).resolve() == (FC / "package_network.json").resolve():
        for r in _screen():
            if r["arch"] == net_arch and int(r["n_per_rail"]) == int(n):
                return float(r["peak_fraction"]), "count screen (level 1)"
    return None, None


def scen_ratio(scen):
    """48-V RMS / average of a named scenario (the ledger's SCEN_RATIO; HV_SDEC: the
    implemented decoupling's k_eq)."""
    if scen == TC.SCEN["SDEC"]:
        d = json.loads((TR / "input_decoupling.json").read_text())
        return float(d["summary"]["recommended"]["k_eq"])
    import final_closure_ledger as FL
    return float(FL.SCEN_RATIO[scen])


def port_model_ball_rms(case, n):
    """(worst-ball RMS in A at the case's 48-V current, source) from the decoupling chain's
    port model (input_decoupling.json summary.ball_currents_recommended: DC + harmonics of every
    ball, the recommended clock plan + ring), when it describes this case: the production
    state (the implemented decoupling) on the same ball count. The port model's value is at
    the chain's S0 current (I_total_dc_A) and scales with the 48-V current."""
    if case.get("scenario") != TC.SCEN["SDEC"]:
        return None, "reference state: the scenario factor (closure rule) alone"
    f = TR / "input_decoupling.json"
    try:
        b = json.loads(f.read_text())["summary"]["ball_currents_recommended"]
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError):
        return None, "no port-model ball currents in input_decoupling.json"
    if int(b.get("n_per_rail") or -1) != int(n) or not b.get("I_total_dc_A"):
        return None, (f"the port model's ball currents are for {b.get('n_per_rail')} balls per "
                      f"rail, not {n}")
    i_avg = case.get("i_hv_avg_a") or ((1000.0 + case["P_loss_w"]) / 48.0
                                       if case.get("P_loss_w") else None)
    if i_avg is None:
        return None, "no 48-V current in the case"
    scale = float(i_avg) / float(b["I_total_dc_A"])
    return float(b["I_ball_rms_max_A"]) * scale, (
        f"port model worst-ball RMS {b['I_ball_rms_max_A']:.3f} A at {b['I_total_dc_A']:.2f} A, "
        f"x {scale:.4f} to the case's {float(i_avg):.2f} A")


def bga_check(arch, case, feed=None):
    """[(name, value, limit, ok, basis, extra)] of the BGA provisioning of one case. The
    per-ball check (bga_current) takes the WORSE of the DC peak x k rule and, where the port
    model describes the case, the worst-ball RMS (review round 3); both are in `extra`."""
    rows = {r["term"]: r for r in case.get("ledger_rows") or []}
    out = []
    lim = LIMITS["bga_A_per_ball"]
    if "P_BGA_supply" in rows:                       # BGA-fed 48 V (Z1, the Z2BF control)
        import re
        n = int(re.search(r"N=(\d+)", rows["P_BGA_supply"]["conductor"]).group(1))
        i_rms = float(rows["P_BGA_supply"]["I_a"])
        net = (case.get("design") or {}).get("package_network")
        frac, src = peak_fraction("Z2" if arch == "Z2BF" else "Z1", n,
                                  R / net if net else None)
        sites = BGA_SITES.get(arch, 1369)
        dc = None if frac is None else frac * i_rms
        rms, rsrc = port_model_ball_rms(case, n) if arch == "Z1" else (None, "no port model")
        val = max((x for x in (dc, rms) if x is not None), default=None)
        out.append(("bga_current", val, lim, None if val is None else val <= lim,
                    f"48-V balls: {n}/rail; worse of the DC peak x k rule (peak fraction "
                    f"{frac} ({src}) x I_rms {i_rms:.2f} A = "
                    + (f"{dc:.3f} A" if dc is not None else "n/a")
                    + ") and the worst-ball RMS (" + (f"{rms:.3f} A, " if rms is not None
                                                      else "") + rsrc + ")",
                    {"I_ball_closure_rule_A": dc, "I_ball_rms_max_A": rms,
                     "n_per_rail": n, "I_rms_48V_A": i_rms}))
        out.append(("bga_sites", 2 * n / sites, LIMITS["bga_power_site_fraction_max"],
                    2 * n / sites <= LIMITS["bga_power_site_fraction_max"],
                    f"{2 * n} of {sites} sites carry 48 V", {}))
    elif arch == "Z3":
        z = case.get("z3_design") or {}
        b = z.get("bga_1v") or {}
        if not b:                    # a sensitivity record: the count of Z3's own config
            import final_closure_ledger as FL
            sp = FL.z3_spec()["bga"]
            b = {"n_per_rail": sp["n_per_rail"], "sites_total": sp["sites_total"],
                 "I_per_ball_A_dc_equal_sharing": sp["criterion_current_a"] / sp["n_per_rail"]}
        if b:
            n, tot = int(b["n_per_rail"]), int(b["sites_total"])
            i_dc = float(b["I_per_ball_A_dc_equal_sharing"])
            out.append(("bga_current", i_dc, LIMITS["bga_A_per_ball"],
                        i_dc <= LIMITS["bga_A_per_ball"] * (1 + 1e-9),
                        f"1-V balls: {n}/rail at DC, equal sharing (the ledger's assumption)",
                        {"I_ball_dc_equal_sharing_A": i_dc, "n_per_rail": n}))
            out.append(("bga_sites", 2 * n / tot, LIMITS["bga_power_site_fraction_max"],
                        2 * n / tot <= LIMITS["bga_power_site_fraction_max"],
                        f"{2 * n} of {tot} sites carry 1 V; {tot - 2 * n} left for signals",
                        {}))
    elif arch == "Z2" and feed:
        # the package-internal boundary has no power ball; the BGA-RING FEED the platform
        # accounting uses carries the 48 V through the package's ring of balls
        n, frac, src = feed["n_per_rail"], feed.get("peak_fraction"), feed.get("source")
        ext = case.get("external_feed") or {}
        i_rms = ext.get("i_48_rms_a")
        if i_rms is None:
            i_avg = case.get("i_hv_avg_a") or ((1000.0 + case["P_loss_w"]) / 48.0
                                               if case.get("P_loss_w") else None)
            if i_avg is not None:
                i_rms = float(i_avg) * scen_ratio(case.get("scenario"))
        val = None if (frac is None or i_rms is None) else frac * i_rms
        out.append(("bga_current", val, LIMITS["bga_A_per_ball"],
                    None if val is None else val <= LIMITS["bga_A_per_ball"],
                    f"BGA-ring feed: {n}/rail, peak fraction {frac} ({src}) x I_rms {i_rms} "
                    "(DC peak x k rule; no port model of the ring feed)",
                    {"I_ball_closure_rule_A": val, "I_ball_rms_max_A": None,
                     "n_per_rail": n}))
        out.append(("bga_sites", 2 * n / BGA_SITES["Z2"], LIMITS["bga_power_site_fraction_max"],
                    2 * n / BGA_SITES["Z2"] <= LIMITS["bga_power_site_fraction_max"],
                    f"{2 * n} of {BGA_SITES['Z2']} sites carry the 48-V feed", {}))
    return out


def z2_ring_feed():
    """The Z2 BGA-ring feed of the platform accounting (tcpmt_platform feed design)."""
    p = TR / "platform_inclusive.json"
    d = json.loads(p.read_text()) if p.is_file() else {}
    fd = (d.get("feed_design") or {}).get("Z2_bga_ring")
    if fd:
        return {"n_per_rail": fd["n_per_rail"], "peak_fraction": fd.get("peak_fraction"),
                "source": fd.get("peak_fraction_source")}
    pn = _network()
    n = pn.get("matched_count")
    if not n:
        return None
    frac, src = peak_fraction("Z2", n)
    return {"n_per_rail": n, "peak_fraction": frac, "source": src}


# ------------------------------------------------------------------ the checks of one case
def evaluate(path, case, use_fields=True, feed=None):
    arch = case["arch"]
    role, state, tier = classify(path, case)
    des = design_of(case)
    th = case.get("thermal") or {}
    t_max = th.get("T_max_C")
    reg, src = region_temperatures(path, case, use_fields)
    bound = src.startswith("bound") or "error" in reg
    checks = {}

    def put(name, value, limit, basis, on_bound=False):
        if value is None:
            checks[name] = {"value": None, "limit": limit, "ok": None, "basis": basis}
            return
        ok = value <= limit
        if on_bound and not ok:
            ok = None                          # fails only on the bound: unresolved
        checks[name] = {"value": float(value), "limit": limit, "ok": ok, "basis": basis,
                        "margin": float(limit - value), "on_bound": bool(on_bound),
                        # within the numerical uncertainty of a peak temperature: the verdict
                        # stands, but it is stated as marginal
                        "marginal": abs(limit - value) <= MARGINAL_K}

    def region(key):
        v = reg.get(key)
        if v is None:                  # not resolved from the field: the whole-field bound
            return t_max, True
        return v, False

    # operating point
    conv = case.get("et_converged")
    if "converged" in case and case.get("variant", {}).get("name", "").startswith("tim_warp"):
        conv = bool(case.get("converged"))
    if case.get("_runaway"):
        conv = False
    checks["operating_point"] = {"value": None, "limit": None, "ok": bool(conv),
                                 "basis": "E-T fixed point" + (" + interface feedback"
                                                               if "tim_warp" in str(path) else "")}
    # junction per device tier, against the device's own T_J maximum (DEVICES)
    tj, tj_bound, fit_hi = {}, False, {}
    for key, part_key, per_key in (("hs", "hs_part", "hs_per_cell"),
                                   ("ls", "ls_part", "ls_per_cell")):
        part = des[part_key]
        dev = DEVICES.get(part)
        t_in, b = region(f"{key}_in_cells")
        tj_bound = tj_bound or b
        p_tier = _tier_power(case, key)
        p_dev = p_tier / (des["n_vr"] * des[per_key])
        tj_max = (dev or {}).get("Tj_max_C", LIMITS["gan_Tj_C"])
        if dev is None or t_in is None:
            tj[key] = None
            put(f"gan_Tj_{key}", None, tj_max, f"no datasheet record for {part}")
            continue
        tj[key] = t_in + p_dev * dev["R_jc_K_W"]
        fit_hi[key] = (part, (dev.get("ron_fit_C") or [None, LIMITS["ron_fit_max_C"]])[1])
        put(f"gan_Tj_{key}", tj[key], tj_max,
            f"{part}: {'bound' if b else 'tier max in cells'} {t_in:.2f} C + {p_dev:.3f} W x "
            f"{dev['R_jc_K_W']} K/W", on_bound=b)
    h_last = (case.get("et_history") or [{}])[-1]
    t_eval = max((h_last.get(f"T_{k}_C") or -1e9) for k in ("hs", "ls"))
    # each device's junction bound against the upper end of ITS OWN R_DS(on)(T_J) fit range
    # (DEVICES ron_fit_C); the binding device (smallest margin) gives the value and the limit
    k_fit = min(fit_hi, key=lambda k: fit_hi[k][1] - tj[k], default=None)
    per = ", ".join(f"{k} {p} {tj[k]:.2f} vs {hi:g} C" for k, (p, hi) in fit_hi.items())
    put("ron_fit", None if k_fit is None else tj[k_fit],
        LIMITS["ron_fit_max_C"] if k_fit is None else fit_hi[k_fit][1],
        f"junction bound of each device against the upper end of its own R_DS(on) fit range "
        f"(DEVICES ron_fit_C): {per or 'no junction'}; binding: {k_fit} (the ledger evaluates "
        f"R_DS(on) at the tier in-cell means, here up to {t_eval:.1f} C)", on_bound=tj_bound)
    t_cap, b1 = region("caps_in_cells")
    t_ind, b2 = region("ind_in_cells")
    put("mlcc", None if t_cap is None else max(t_cap, t_ind or -1e9), LIMITS["mlcc_C"],
        "flying-capacitor tier and the inductor/C_out tier, in the cells", on_bound=b1 or b2)
    put("inductor", t_ind, LIMITS["inductor_C"], "inductor tier, in the cells", on_bound=b2)
    v, b = region("rdl_all")
    put("buildup", v, LIMITS["buildup_Tg_C"], "every RDL tier element", on_bound=b)
    v, b = region("encapsulant")
    put("encapsulant", v, LIMITS["encapsulant_Tg_C"], "converter tiers outside the cells",
        on_bound=b)
    v, b = region("board")
    put("board", v, LIMITS["board_Tg_C"], "every board element", on_bound=b)
    dmax, dsrc = die_max(case, reg)
    if dmax is None and t_max is not None:
        put("die", t_max, LIMITS["die_C"], "bound (whole-field peak)", on_bound=True)
    else:
        put("die", dmax, LIMITS["die_C"], dsrc or "n/a")
    jt = joints(case)
    put("solder_law", jt["T_hottest_C"], LIMITS["solder_cal_C"],
        f"hottest joint of the all-site search (critical joint {jt['T_critical_C']})")
    put("solder_solidus", jt["T_hottest_C"], LIMITS["solder_solidus_C"], "hottest joint")
    for name, val, lim, ok, basis, extra in bga_check(arch, case,
                                                      feed if arch == "Z2" else None):
        checks[name] = {"value": val, "limit": lim, "ok": ok, "basis": basis, **extra}
        if name in BGA_POLICY_CHECKS:
            checks[name]["policy_switched"] = True
    try:
        import tcpmt_ir_drop as IR
        d = IR.static_drop(case, n_vr=des["n_vr"])
        checks["ir_drop"] = {"value": d["max_mV"], "limit": LIMITS["ir_drop_mV_per_rail"],
                             "ok": d["max_mV"] <= LIMITS["ir_drop_mV_per_rail"],
                             "basis": f"per-rail maximum (VDD {d['VDD_mV']:.2f}, GND "
                                      f"{d['GND_mV']:.2f} mV)",
                             "VDD_mV": d["VDD_mV"], "GND_mV": d["GND_mV"],
                             "loop_mV": d["loop_mV"], "terms": d["terms"],
                             "mean_loss_over_I_mV": d["mean_loss_over_I_mV"]}
    except Exception as e:                                   # noqa: BLE001 -- recorded
        checks["ir_drop"] = {"value": None, "limit": LIMITS["ir_drop_mV_per_rail"], "ok": None,
                             "basis": f"not evaluated: {str(e)[-200:]}"}
    by_policy = {p: verdict_under(checks, p) for p in BGA_POLICIES}
    verdict, fails, open_ = (by_policy[BGA_POLICY]["verdict"], by_policy[BGA_POLICY]["fails"],
                             by_policy[BGA_POLICY]["unresolved"])
    return {"case": Path(path).name, "path": TC.rel(path), "arch": arch,
            "scenario": case.get("scenario"), "state": state, "tier": tier, "role": role,
            "variant": _variant_name(path), "P_loss_w": case.get("P_loss_w"), "T_max_C": t_max,
            "design": des, "regions": reg, "region_source": src, "die_T_max_C": dmax,
            "junction_C": tj, "joints": jt, "checks": checks, "fails": fails,
            "unresolved": open_, "verdict": verdict, "bga_policy": BGA_POLICY,
            "by_bga_policy": by_policy, "bga_requirement": bga_requirement(arch, checks)}


def verdict_under(checks, policy):
    """{verdict, fails, unresolved} of a record's checks under a BGA policy: under 'hard'
    every check filters; under 'requirement' the BGA_POLICY_CHECKS are reported only."""
    if policy not in BGA_POLICIES:
        raise ValueError(f"BGA policy {policy!r}: not one of {sorted(BGA_POLICIES)}")

    def filters(name):
        return policy == "hard" or name not in BGA_POLICY_CHECKS
    fails = sorted(k for k, c in checks.items() if c["ok"] is False and filters(k))
    open_ = sorted(k for k, c in checks.items() if c["ok"] is None and filters(k))
    return {"verdict": "infeasible" if fails else ("unresolved" if open_ else "feasible"),
            "fails": fails, "unresolved": open_}


def bga_requirement(arch, checks):
    """The per-ball current the case asks of its BGA, stated as a requirement (the
    'requirement' policy's reading of bga_current), with both currents where they exist."""
    c = checks.get("bga_current")
    if not c or c.get("value") is None:
        return None
    return {"I_ball_A": c["value"], "target_A": c["limit"], "meets_target": c["ok"],
            "I_ball_closure_rule_A": c.get("I_ball_closure_rule_A"),
            "I_ball_rms_max_A": c.get("I_ball_rms_max_A"),
            "statement": (f"{arch}: each power ball must carry {c['value']:.2f} A "
                          + ("(within" if c["ok"] else "(above")
                          + f" the {c['limit']:g}-A target)")}


# ------------------------------------------------------------------ omitted-loss margins
OMIT_KEY = {("A", "Z1"): "A_Z1", ("A", "Z2"): "A_Z2", ("A", "Z3"): "A_Z3_toponly",
            ("B", "Z1"): "B_Z1", ("B", "Z2"): "B_Z2", ("B", "Z3"): "B_Z3",
            ("I", "Z3"): "A_Z3_secondplate", ("I", "Z2"): "B_Z2"}


def slopes(case):
    """dT/dP (K/W) of the recorded regions from the case's first two E-T iterations."""
    h = case.get("et_history") or []
    if len(h) < 2 or abs(h[1]["P_loss_w"] - h[0]["P_loss_w"]) < 1e-6:
        return None
    dp = h[1]["P_loss_w"] - h[0]["P_loss_w"]
    out = {}
    for k in ("hs", "ls", "caps", "ind", "bga", "interface", "sub"):
        a, b = h[0].get(f"T_{k}_C"), h[1].get(f"T_{k}_C")
        if a is not None and b is not None:
            out[k] = (b - a) / dp
    out["die"] = (h[1]["T_die_mean_C"] - h[0]["T_die_mean_C"]) / dp
    out["T_max"] = (h[1]["T_max_C"] - h[0]["T_max_C"]) / dp
    return out


def omitted_margins(rec, case, omit):
    """The high bundle (+ its feedback) applied to the checked temperatures."""
    if not omit:
        return None
    key = f"{rec['tier']}_{rec['arch']}"           # the registry keys of the regenerated study
    if key not in omit["cases"]:
        key = OMIT_KEY.get((rec["tier"], rec["arch"]))  # the committed (earlier) study's keys
    if key not in omit["cases"]:
        return None
    hi = omit["cases"][key]["omitted"]["high"]["total_w"]
    nom = omit["cases"][key]["omitted"]["nominal"]["total_w"]
    fb = ((omit.get("electrothermal_feedback_estimate") or {}).get("per_case") or {}).get(key, {})
    s = slopes(case)
    if s is None:
        return None
    src = omit["cases"][key].get("file", "")
    out = {"omitted_case": key, "omitted_case_file": src,
           # the bundle was evaluated on another (superseded) case of the same integration
           "approximate": bool(src) and TC.is_superseded(R / src),
           "bundles": {}}
    for name, p_om, f in (("nominal", nom, fb.get("feedback_nominal_w", 0.0)),
                          ("high", hi, fb.get("feedback_high_w", 0.0))):
        dp = p_om + f
        c = rec["checks"]
        shifted = {}
        for chk, reg in (("gan_Tj_hs", "hs"), ("gan_Tj_ls", "ls"), ("ron_fit", "ls"),
                         ("mlcc", "caps"), ("inductor", "ind"), ("die", "die"),
                         ("solder_law", "bga"), ("encapsulant", "T_max"),
                         ("buildup", "T_max")):
            if chk not in c or c[chk]["value"] is None:
                continue
            sl = s.get(reg, s["T_max"])
            if chk == "ron_fit":
                sl = max(s.get("hs", 0.0), s.get("ls", 0.0))
            v = c[chk]["value"] + sl * dp
            shifted[chk] = {"value": v, "limit": c[chk]["limit"], "dT_K": sl * dp,
                            "ok": v <= c[chk]["limit"]}
        out["bundles"][name] = {"dP_w": dp, "P_omitted_w": p_om, "feedback_w": f,
                                "checks": shifted,
                                "fails": sorted(k for k, v in shifted.items() if not v["ok"])}
    return out


def gap_shift_reconciliation(omit):
    """The three statements of the paper on how far the omitted terms move a gap, on one
    basis: the direct shift (the difference of the omitted terms between the two
    integrations at their own temperatures) and its electrothermal feedback, per bundle."""
    if not omit:
        return None
    pairs = (omit.get("summary") or {}).get("pairs") or {}
    rows = []
    for key, v in pairs.items():
        lo, nom, hi = v["delta_omitted_w_low_nom_high"]
        fnom, fhi = v["delta_feedback_w_nom_high"]
        tier = key.split("_")[0]
        rows.append({"pair": key, "tier": tier, "gap_w": v["gap_paper_w"],
                     "direct_w": {"low": lo, "nominal": nom, "high": hi},
                     "feedback_w": {"nominal": fnom, "high": fhi},
                     "total_w": {"nominal": nom + fnom, "high": hi + fhi},
                     "superseded_z3": "Z3" in key})
    out = {"rows": rows, "by_tier": {}, "by_tier_with_z3": {}}
    for t in ("A", "B"):
        # the I configuration ('secondplate') is not a cooling tier of the comparison
        tier_rows = [r for r in rows if r["tier"] == t and "secondplate" not in r["pair"]]
        for blk, rr in (("by_tier", [r for r in tier_rows if not r["superseded_z3"]]),
                        ("by_tier_with_z3", tier_rows)):
            if not rr:
                continue
            out[blk][t] = {
                "direct_max_w": {b: max(abs(r["direct_w"][b]) for r in rr)
                                 for b in ("nominal", "high")},
                "feedback_max_w": {b: max(abs(r["feedback_w"][b]) for r in rr)
                                   for b in ("nominal", "high")},
                "total_max_w": {b: max(abs(r["total_w"][b]) for r in rr)
                                for b in ("nominal", "high")},
                "smallest_gap_w": min(r["gap_w"] for r in rr),
                "pairs": [r["pair"] for r in rr]}
    out["statement"] = (
        "the 'at most 0.2 W' of the text is the DIRECT shift of the cooling-A Z1-Z2 gap (0.10 W "
        "nominal, 0.17 W high); the '+0.8 W' is the ELECTROTHERMAL FEEDBACK of the nominal "
        "bundle on that gap; '1.0-1.15 W' is the DIRECT shift of the cooling-B gaps against Z1 "
        "with the high bundle (Z2-Z1 1.0 W; Z3-Z1 1.15 W on the superseded uncoupled Z3). One "
        "statement covers all three, per tier: direct shift <= direct_max, with its feedback <= "
        "total_max (by_tier: the ranked Z1-Z2 pairs; by_tier_with_z3 adds the Z3 pairs, whose "
        "omitted-loss inputs are the superseded uncoupled Z3 cases until omitted_losses.json is "
        "regenerated on the coupled cases)")
    return out


# ------------------------------------------------------------------ ranking
def rankings(records, policy=None):
    """Per input state and cooling: feasible candidates ranked by package-internal loss; the
    excluded ones with the limits they fail (or leave unresolved). `policy`: a BGA policy (the
    records' by_bga_policy verdicts); None = the policy each record was evaluated under."""
    out = {}
    if policy is not None:
        records = [dict(r, **r["by_bga_policy"][policy]) for r in records]
    by_case = {r["path"]: r for r in records}
    for st in TC.STATES:
        for t in TC.TIERS:
            cand, excl, missing = [], [], []
            for a in TC.ARCHS:
                p = TC.case_path(st, t, a)
                if p is None:
                    missing.append(a)
                    continue
                r = by_case.get(TC.rel(p))
                if r is None:
                    missing.append(a)
                elif r["verdict"] == "feasible":
                    cand.append((r["P_loss_w"], a))
                else:
                    excl.append({"arch": a, "verdict": r["verdict"], "fails": r["fails"],
                                 "unresolved": r["unresolved"]})
            cand.sort()
            out[f"{st}_{t}"] = {"ranked": [a for _p, a in cand],
                                "loss_w": {a: p for p, a in cand}, "excluded": excl,
                                "missing": missing,
                                "complete": not missing}
    return out


def summary_of(records, policy=None):
    """Case counts and the infeasible / unresolved lists (under `policy`, or the policy each
    record was evaluated under), with both policies' lists beside them."""
    def pick(r, p):
        return r["by_bga_policy"][p]["verdict"] if p else r["verdict"]
    out = {"n_cases": len(records),
           "infeasible": sorted(r["case"] for r in records if pick(r, policy) == "infeasible"),
           "unresolved": sorted(r["case"] for r in records if pick(r, policy) == "unresolved")}
    out["by_bga_policy"] = {p: {"infeasible": sorted(r["case"] for r in records
                                                      if pick(r, p) == "infeasible"),
                                "unresolved": sorted(r["case"] for r in records
                                                     if pick(r, p) == "unresolved")}
                            for p in BGA_POLICIES}
    return out


def apply_bga_policy(doc, policy):
    """A stored feasibility document under another BGA policy, without rerunning anything:
    each record's verdict / fails / unresolved from its by_bga_policy entry, the compared
    cells, the rankings and the summary. Returns a new document."""
    import copy
    if policy not in BGA_POLICIES:
        raise ValueError(f"BGA policy {policy!r}: not one of {sorted(BGA_POLICIES)}")
    d = copy.deepcopy(doc)
    for r in d["records"]:
        r.update(r["by_bga_policy"][policy])
        r["bga_policy"] = policy
    for key, r in d["cases"].items():
        r.update(r["by_bga_policy"][policy])
        r["bga_policy"] = policy
    d["rankings"] = d["rankings_by_bga_policy"][policy]
    d["summary"] = summary_of(d["records"])
    d["bga_policy"] = dict(d["bga_policy"], in_force=policy)
    return d


# ------------------------------------------------------------------ main
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    use_fields = "--no-fields" not in argv
    omit_p = TR / "omitted_losses.json"
    omit = json.loads(omit_p.read_text()) if omit_p.is_file() else None
    feed = z2_ring_feed()
    files = all_case_files()
    records = []
    for f in files:
        c = json.loads(f.read_text())
        if "ledger_rows" not in c or "thermal" not in c:
            continue
        r = evaluate(f, c, use_fields, feed)
        m = omitted_margins(r, c, omit) if r["role"] in ("compared",) else None
        if m:
            r["omitted_losses"] = m
        records.append(r)
        print(f"{r['verdict']:11s} {r['role']:10s} {r['state']!s:5s} {r['tier']} "
              f"{f.name:58s} fails={','.join(r['fails']) or '-'} "
              f"open={','.join(r['unresolved']) or '-'}", flush=True)
    for f in runaway_records():
        c = json.loads(f.read_text())
        c.setdefault("arch", f.name.split("_")[1])
        c.setdefault("scenario", "_".join(f.name.split("_")[2:4]))
        c["_runaway"] = True
        r = evaluate(f, c, use_fields, feed)
        r["role"], r["verdict"] = "variant", "infeasible"
        r["fails"] = sorted(set(r["fails"]) | {"operating_point"})
        for v in r["by_bga_policy"].values():
            v["verdict"], v["fails"] = "infeasible", sorted(set(v["fails"]) | {"operating_point"})
        records.append(r)
        print(f"{r['verdict']:11s} runaway    {f.name}", flush=True)
    rk = rankings(records)
    # the comparison tables of the paper: the compared cells, keyed <tier>_<arch> for the
    # production state (fig_tiers reads cases[<tier>_<arch>]["case"/"checks"])
    cases = {}
    for r in records:
        if r["role"] == "compared":
            key = (f"{r['tier']}_{r['arch']}" if r["state"] == TC.PRODUCTION_STATE
                   else f"{r['state']}_{r['tier']}_{r['arch']}")
            cases[key] = r
    out = {"rule": "a candidate that fails any limit is not ranked; a check that fails only on "
                   "the whole-field bound is unresolved and the candidate is not ranked either",
           "limits": LIMITS, "limit_sources": LIMIT_SOURCES, "devices": DEVICES,
           "bga_sites": BGA_SITES, "production_state": TC.PRODUCTION_STATE,
           "cases": cases, "rankings": rk, "records": records,
           "z2_ring_feed": feed,
           "omitted_gap_shift": gap_shift_reconciliation(omit),
           "bga_policy": {"in_force": BGA_POLICY, "policies": BGA_POLICIES,
                          "switched_checks": list(BGA_POLICY_CHECKS),
                          "how": "every record carries by_bga_policy (verdict, fails, "
                                 "unresolved under each policy) and bga_requirement; "
                                 "rankings_by_bga_policy holds both rankings; "
                                 "tcpmt_feasibility.apply_bga_policy(doc, policy) re-derives "
                                 "the verdicts, rankings and summary of a stored document "
                                 "(env TCPMT_BGA_POLICY selects the policy of a run)"},
           "rankings_by_bga_policy": {p: rankings(records, p) for p in BGA_POLICIES},
           "summary": summary_of(records)}
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(f"wrote {OUT}: {len(records)} cases, "
          f"{len(out['summary']['infeasible'])} infeasible, "
          f"{len(out['summary']['unresolved'])} unresolved")
    return out


if __name__ == "__main__":
    main()
