#!/usr/bin/env python3
"""PHASE 0N-S Tasks 1/2 -- PCB thickness sweep for the Z2 land-side cutout.

Closure is evaluated on the FULL interface stack, never on nominal board thickness
alone. Every allowance is named and classified.
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "research" / "phase0ns"
OUT.mkdir(parents=True, exist_ok=True)

# --- the land-side HVR stack (research/Z2_CUTOUT_GEOMETRY.md) -----------------------
HS_NOM, HS_MAX = 685.0, 815.0          # EPC2014C datasheet Side View
LS, L_IND, MLCC, RDL = 638.0, 500.0, 100.0, 10.0
FOUR_TIER_NOM = HS_NOM + LS + L_IND + MLCC + 3 * RDL      # 1953
FOUR_TIER_MAX = HS_MAX + LS + L_IND + MLCC + 3 * RDL      # 2083
LANDSIDE_RDL = 10.0
BGA = 300.0                            # SOURCE_BACKED, Krishnakumar 2026 Table III

# --- additive allowances. Each is named, classified and NOT sourced unless stated ---
ALLOW = [
    ("land-side attach RDL", LANDSIDE_RDL, "SOURCE_BACKED", "ECTC-2024 10 um interlayer RDL"),
    ("cell-to-substrate attach solder + underfill", 30.0, "BOUNDED",
     "same order as the 10 um microbump + underfill the package already uses; no source"),
    ("bottom keep-out below the deepest device", 50.0, "BOUNDED",
     "anchored on H_TSV_MIN_UM = 50 um, the only keep-out length the framework names"),
    ("assembly / placement tolerance", 50.0, "BOUNDED",
     "engineering allowance; no source"),
]
TIM_HS = 500.0   # TIM + spreader if backside cooling is used (ARM FIG. 3). BOUNDED.

BOARDS = [
    ("1.6 mm", 1600.0, 0.10, "historical framework ASSUMPTION (board.py FR-4 envelope)"),
    ("2.0 mm", 2000.0, 0.10, "PCBWay rigid-board thickness list"),
    ("2.4 mm", 2400.0, 0.10, "18-layer server/HPC board offered at 2.4 mm +-10 % (ugpcb); "
                             "PCBWay; within Schweizer 0.6-3.2 mm standard multilayer"),
    ("3.2 mm", 3200.0, 0.10, "Schweizer standard multilayer upper bound; PCBWay; JLCPCB; "
                             "Isola 370HR/IS410 laminate to 3.2 mm; Wurth DEVICE.embedding "
                             "max final PCB thickness 3.2 mm"),
    ("4.2 mm", 4200.0, 0.10, "Schweizer HIGHER-STANDARD capability only -- reported, "
                             "NOT a baseline design"),
]

alw = sum(a for _n, a, _c, _s in ALLOW)
rows = []
print(f"HVR four-tier stack   nominal {FOUR_TIER_NOM:.0f} um   EPC2014C-max {FOUR_TIER_MAX:.0f} um")
print(f"additive allowances   {alw:.0f} um  ({', '.join(n for n,_a,_c,_s in ALLOW)})")
print(f"required depth        nominal {FOUR_TIER_NOM+alw:.0f} um   max-device {FOUR_TIER_MAX+alw:.0f} um")
print(f"backside TIM+spreader {TIM_HS:.0f} um additional if case B cooling is used\n")
hdr = (f"{'board':8}{'nom':>7}{'-10%':>8}{'avail':>8}{'margin nom':>12}"
       f"{'margin max':>12}{'+TIM max':>11}  verdict")
print(hdr); print("-" * len(hdr))
for name, t, tol, src in BOARDS:
    tmin = t * (1 - tol)
    avail = tmin + BGA                      # worst-case board, nominal ball
    m_nom = avail - (FOUR_TIER_NOM + alw)
    m_max = avail - (FOUR_TIER_MAX + alw)
    m_tim = avail - (FOUR_TIER_MAX + alw + TIM_HS)
    if m_max >= 0:
        v = "CLOSES at max device"
    elif m_nom >= 0:
        v = "closes nominal only"
    else:
        v = "FAILS"
    if m_tim >= 0:
        v += "; TIM fits inside"
    print(f"{name:8}{t:7.0f}{tmin:8.0f}{avail:8.0f}{m_nom:12.0f}{m_max:12.0f}{m_tim:11.0f}  {v}")
    rows.append({"board": name, "t_nom_um": t, "t_min_um": tmin, "available_um": avail,
                 "margin_nominal_um": m_nom, "margin_maxdevice_um": m_max,
                 "margin_maxdevice_plus_tim_um": m_tim, "verdict": v, "source": src})

json.dump({"four_tier_nom_um": FOUR_TIER_NOM, "four_tier_max_um": FOUR_TIER_MAX,
           "allowances": [{"item": n, "um": a, "class": c, "basis": s}
                          for n, a, c, s in ALLOW],
           "allowance_total_um": alw, "bga_um": BGA, "tim_spreader_um": TIM_HS,
           "boards": rows},
          (OUT / "pcb_thickness_audit.json").open("w"), indent=1)
print(f"\nwrote {OUT/'pcb_thickness_audit.json'}")
