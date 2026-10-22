#!/usr/bin/env python3
"""PHASE 0N-S Task 9 -- the residual 1 V lateral RDL loss in Z2.

The cell grid and the die POL partition are nearly co-pitched, so the low-voltage
path is almost vertical. "Almost" is not a number; this quantifies it and compares
it with the other interconnect terms in the frozen ledger.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
for d in ("phase0mr", "phase0m", "phase0i", "phase0h", "phase0g", "phase0f",
          "phase0e", "phase0dr", "phase0b", "phase0d"):
    sys.path.insert(0, str(R / "scripts" / d))
import production_et as PE                                              # noqa: E402
from interconnect import rho_cu                                         # noqa: E402

OUT = R / "research" / "phase0ns"
OUT.mkdir(parents=True, exist_ok=True)

T_RDL_UM = 10.0            # sourced interlayer RDL copper thickness (ECTC-2024)
T_PKG_C = 95.0             # package RDL temperature, frozen replay operating point
I_CELL = 20.408163265306122

m, mats, st, tiles = PE.build_global("ARCH_Z2_BACKSIDE", 0.30)
Dx = st["geometry"]["functional_die"]["size_x"]["value"]
n = int(round(math.sqrt(len(tiles))))
side = tiles[0].ax

rho = rho_cu(T_PKG_C)                       # ohm*m at the package temperature
r_sheet = rho / (T_RDL_UM * 1e-6)           # ohm per square

offs = []
for t in tiles:
    i = min(n - 1, max(0, int((t.cx + Dx / 2) / (Dx / n))))
    j = min(n - 1, max(0, int((t.cy + Dx / 2) / (Dx / n))))
    px = -Dx / 2 + (i + .5) * Dx / n
    py = -Dx / 2 + (j + .5) * Dx / n
    offs.append(math.hypot(t.cx - px, t.cy - py))

# Each cell's output spreads over its own footprint width, so the lateral run is
# modelled as a sheet of length = offset and width = cell side. The return path
# doubles it, exactly as the framework's R_loop = 2 R_field convention does.
def loss(offset_mm, loop=True):
    r = r_sheet * (offset_mm / side)        # squares = L/W
    r *= 2.0 if loop else 1.0
    return r, I_CELL ** 2 * r

r_max, p_max = loss(max(offs))
r_mean, p_mean = loss(sum(offs) / len(offs))
p_sys_mean = p_mean * len(tiles)
p_sys_max = p_max * len(tiles)

print(f"rho_cu({T_PKG_C:.0f} C) = {rho:.3e} ohm.m   sheet R = {r_sheet*1e3:.4f} mohm/sq "
      f"at {T_RDL_UM:.0f} um Cu")
print(f"cell side {side:.4f} mm, {len(tiles)} cells, {I_CELL:.3f} A per cell\n")
print(f"{'case':10}{'offset um':>11}{'squares':>10}{'R loop uohm':>14}"
      f"{'P/cell mW':>12}{'P system W':>12}")
for tag, o in (("mean", sum(offs)/len(offs)), ("max", max(offs))):
    r, p = loss(o)
    print(f"{tag:10}{o*1e3:11.1f}{o/side:10.4f}{r*1e6:14.2f}{p*1e3:12.2f}"
          f"{p*len(tiles):12.4f}")

led = {}
import csv
for row in csv.DictReader((R / "results/phase0mr3c/final_loss_ledger.csv").open()):
    if row["case"] == "Z2" and row["scope"] == "ELECTRONICS":
        led[row["term"]] = float(row["watts"])
print("\n*** NOT AN ADDITIONAL LOSS TERM ***")
print("  The framework ALREADY solves lateral spreading: P_pkg_RDL comes from")
print("  rdl_network_solve on the ectc2024_primary stack -- 2 VDD + 2 GND layers of")
print("  10 um Cu, as a 2-D network over the real source/POL grid. The strip estimate")
print("  above is 1-D, single-layer and confined to the cell width, so it is an UPPER")
print("  BOUND on a degenerate implementation, not a term to add.")
print("\ncomparison with the frozen Z2 interconnect terms (system W):")
for k in ("P_TSV", "P_bumps", "P_pkg_RDL", "P_intraVR_metal"):
    print(f"   {k:18} {led[k]:9.4f}")
print(f"   {'lateral 1 V RDL':18} {p_sys_mean:9.4f}   (mean offset)")
print(f"   {'lateral 1 V RDL':18} {p_sys_max:9.4f}   (max offset, upper bound)")
print(f"\n   AUTHORITATIVE lateral term  P_pkg_RDL = {led['P_pkg_RDL']:.4f} W")
print(f"     = {100*led['P_pkg_RDL']/led['P_TSV']:.0f} % of P_TSV ({led['P_TSV']:.4f} W)")
print(f"     = {100*led['P_pkg_RDL']/1000:.3f} % of the 1 kW load")
print(f"   single-layer strip upper bound {p_sys_mean:.3f} W (mean offset), "
      f"{p_sys_max:.3f} W (max)")
print("\n   FINDING: lateral spreading is of the SAME ORDER as the TSV term the")
print("   architecture comparison turns on. 'Almost vertical' understates it.")

json.dump({"rho_ohm_m": rho, "r_sheet_ohm_sq": r_sheet, "t_rdl_um": T_RDL_UM,
           "t_pkg_c": T_PKG_C, "cell_side_mm": side, "n_cells": len(tiles),
           "i_cell_a": I_CELL,
           "offset_mean_mm": sum(offs)/len(offs), "offset_max_mm": max(offs),
           "r_loop_mean_ohm": r_mean, "r_loop_max_ohm": r_max,
           "p_cell_mean_w": p_mean, "p_cell_max_w": p_max,
           "p_system_mean_w": p_sys_mean, "p_system_max_w": p_sys_max,
           "frozen_z2_terms_w": led},
          (OUT / "lateral_rdl_loss.json").open("w"), indent=1)
print(f"\nwrote {OUT/'lateral_rdl_loss.json'}")
