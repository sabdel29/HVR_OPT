#!/usr/bin/env python3
"""PHASE 0N-R TASKS B/C/D -- Z2_CUTOUT geometry, BGA capacity and lateral alignment.

Land-side distributed VR cells with a PCB through-cutout. Construction precedent:
ARM US20260059645A1 and Intel US20250233088A1 (patents -- industry precedent, NOT
demonstrated hardware); bottom-side package VR is peer-reviewed in Xu et al.,
IEEE TCPMT 2019, 10.1109/TCPMT.2019.2903285.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b", "phase0d"):
    sys.path.insert(0, str(R / "scripts" / d))
import production_et as PE                                              # noqa: E402
import board as BRD                                                     # noqa: E402
import zarch as ZA                                                      # noqa: E402

OUT = R / "research" / "phase0nr"
OUT.mkdir(parents=True, exist_ok=True)

# --- selected-device geometry (configs/phase0nr/device_geometry.yaml) ---------------
HS, LS, L_IND, MLCC, RDL = 685.0, 638.0, 500.0, 100.0, 10.0
J_DESIGN = 1.0e8          # A/m^2, the framework's design-side provisioning density
I_BALL_CONSERVATIVE = 1.5  # A/ball, an engineering electromigration-style bound

m, mats, st, tiles = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
g = st["geometry"]
Lx = g["power_substrate"]["size_x"]["value"]
Ly = g["power_substrate"]["size_y"]["value"]
side = tiles[0].ax
x0, x1 = min(t.x0 for t in tiles), max(t.x1 for t in tiles)
y0, y1 = min(t.y0 for t in tiles), max(t.y1 for t in tiles)
BGA_H, BGA_D, BGA_P = (BRD.BALL_H_MM * 1e3, BRD.BALL_D_MM * 1e3, BRD.BALL_P_MM * 1e3)
PCB = BRD.BOARD_CASES["fr4_1p6mm"]["t_mm"] * 1e3

# --- TASK B: the Z2 cell stack, inverted so the inductor stays nearest the POL ------
# Z1 puts the inductor in the TOP power layer "near the POLs" (Krishnakumar 2026).
# Z2 hangs below the substrate, so keeping the inductor nearest the die INVERTS the
# tier order: the high-side device ends up deepest into the cutout.
STACK = [("land-side attach RDL", RDL, "1 V collection + 48 V distribution plane"),
         ("inductor + output cap", L_IND, "nearest the substrate, so nearest the POL"),
         ("interlayer RDL", RDL, ""),
         ("LS GaN EPC2057", LS, "518 +-25 die + 120 +-12 bump"),
         ("interlayer RDL", RDL, ""),
         ("flying capacitors", MLCC, "BOUNDED 0/100/250 um, OPEN"),
         ("interlayer RDL", RDL, ""),
         ("HS GaN EPC2014C", HS, "deepest into the cutout; 685 nom / 815 max")]
serial = sum(t for _n, t, _c in STACK)
four_tier = HS + MLCC + LS + L_IND + 3 * RDL

print("=" * 78)
print("TASK B -- Z2 CELL STACK (all 11 components per cell, nothing offloaded)")
print("=" * 78)
z = 0.0
for n, t, c in STACK:
    print(f"  {n:24} {t:7.0f} um   z {z:7.0f} -> {z+t:7.0f}   {c}")
    z += t
print(f"  {'SERIAL TOTAL':24} {serial:7.0f} um")
print(f"  four-tier component stack (no land-side RDL)  {four_tier:.0f} um")
print(f"  the OLD Z2 model used CONV_CELL_MM = 1226 um, which EXCLUDES the {HS:.0f} um HS")
print(f"  understatement of the frozen Z2 converter height: {1921-1226:.0f} um")

print()
print("=" * 78)
print("TASK C -- HEIGHT CLOSURE WITH A PCB THROUGH-CUTOUT")
print("=" * 78)
avail = BGA_H + PCB
print(f"  sourced BGA ball height                  {BGA_H:8.0f} um  (SOURCE_BACKED)")
print(f"  assumed PCB thickness                    {PCB:8.0f} um  (ASSUMPTION)")
print(f"  substrate underside -> PCB backside      {avail:8.0f} um  = cutout depth available")
for tag, h in (("four-tier stack", four_tier), ("with land-side RDL", serial)):
    print(f"  {tag:24} {h:8.0f} um -> protrudes {h-avail:+.0f} um past the PCB backside")
print(f"  WITHOUT a cutout the gap is only the ball height: shortfall "
      f"{serial-BGA_H:.0f} um")

# --- TASK C: cutout size and BGA capacity -------------------------------------------
print()
print("=" * 78)
print("TASK C -- CUTOUT FOOTPRINT AND REMAINING BGA CAPACITY")
print("=" * 78)
print(f"  {len(tiles)} cells of {side:.4f} mm side; grid bbox "
      f"{x1-x0:.3f} x {y1-y0:.3f} mm")
nx = int(Lx // (BGA_P * 1e-3)) if False else int(Lx / (BGA_P / 1e3))
nx = ny = int(Lx / (BGA_P / 1e3))
rows = []
for clr_mm in (0.0, 0.5, 1.0):
    cx, cy = (x1 - x0) + 2 * clr_mm, (y1 - y0) + 2 * clr_mm
    kept = sum(1 for i in range(nx) for j in range(ny)
               if not (-cx / 2 <= -Lx / 2 + (i + .5) * BGA_P / 1e3 <= cx / 2
                       and -cy / 2 <= -Ly / 2 + (j + .5) * BGA_P / 1e3 <= cy / 2))
    rows.append((clr_mm, cx, cy, kept))
    print(f"  sidewall clearance {clr_mm:.1f} mm -> cutout {cx:.2f} x {cy:.2f} mm, "
          f"{kept} of {nx*ny} BGA sites remain")

I_IN = 1000.0 / ZA.rail_currents()["I_in_a"] and ZA.rail_currents()["I_in_a"]
a_ball = math.pi * (BGA_D * 1e-6) ** 2 / 4.0
i_ball_j = J_DESIGN * a_ball
print()
print(f"  48 V system input current               {I_IN:8.2f} A   (zarch.rail_currents)")
print(f"  ball cross-section                      {a_ball*1e6:8.4f} mm^2")
print(f"  per-ball at J_design = 1e8 A/m^2        {i_ball_j:8.2f} A")
need_j = math.ceil(I_IN / i_ball_j)
need_c = math.ceil(I_IN / I_BALL_CONSERVATIVE)
print(f"  balls needed for 48 V  (J_design)       {need_j:8d}   + same for return")
print(f"  balls needed for 48 V  ({I_BALL_CONSERVATIVE} A/ball)      {need_c:8d}   + same for return")
print(f"  worst case (conservative, both rails)   {2*need_c:8d} of "
      f"{rows[-1][3]} remaining sites = {100*2*need_c/rows[-1][3]:.1f} %")
print("  NOTE the 1 V output does NOT use the BGA: it rises through the substrate TSVs.")

# --- TASK D: lateral alignment between cell outputs and die POL regions -------------
print()
print("=" * 78)
print("TASK D -- LATERAL ALIGNMENT, CELL OUTPUT vs DIE POL REGION")
print("=" * 78)
Dx = g["functional_die"]["size_x"]["value"]
n = int(round(math.sqrt(len(tiles))))
offs = []
for t in tiles:
    # the die region this cell serves, on an n x n equal partition of the die
    i = min(n - 1, max(0, int((t.cx + Dx / 2) / (Dx / n))))
    j = min(n - 1, max(0, int((t.cy + Dx / 2) / (Dx / n))))
    px = -Dx / 2 + (i + .5) * Dx / n
    py = -Dx / 2 + (j + .5) * Dx / n
    offs.append(math.hypot(t.cx - px, t.cy - py))
print(f"  die {Dx} mm over a {n}x{n} POL partition -> region pitch {Dx/n:.3f} mm")
cpitch = (max(t.cx for t in tiles) - min(t.cx for t in tiles)) / (n - 1)
print(f"  cell-CENTRE pitch {cpitch:.3f} mm (the {x1-x0:.3f} mm bbox adds half a cell each end)")
print(f"  cell-centre to POL-region-centre offset: mean {sum(offs)/len(offs):.3f} mm, "
      f"max {max(offs):.3f} mm")
print(f"  -> residual LOW-VOLTAGE lateral run is at most {max(offs)*1e3:.0f} um, "
      f"against a {serial:.0f} um vertical stack")

json.dump({"stack": [{"layer": n_, "t_um": t_, "note": c_} for n_, t_, c_ in STACK],
           "serial_um": serial, "four_tier_um": four_tier,
           "bga_h_um": BGA_H, "pcb_um": PCB, "cutout_depth_um": avail,
           "protrusion_um": serial - avail,
           "cell_side_mm": side, "n_cells": len(tiles),
           "grid_bbox_mm": [x1 - x0, y1 - y0],
           "cutout_options": [{"clearance_mm": c, "cutout_mm": [cx, cy], "bga_sites": k}
                              for c, cx, cy, k in rows],
           "bga_sites_full": nx * ny, "i_in_a": I_IN,
           "balls_needed_jdesign": need_j, "balls_needed_conservative": need_c,
           "lateral_offset_max_mm": max(offs),
           "lateral_offset_mean_mm": sum(offs) / len(offs)},
          (OUT / "z2_cutout_geometry.json").open("w"), indent=1)
print(f"\nwrote {OUT/'z2_cutout_geometry.json'}")
