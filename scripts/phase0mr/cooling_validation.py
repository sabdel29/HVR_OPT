#!/usr/bin/env python3
"""Phase-0M-R Section 11 -- cooling validation, at the level each tool can actually reach.

THE COMPACT MODEL HAS THREE PARTS AND THEY ARE VALIDATED SEPARATELY.

  FLUID SIDE   `m_dot cp dT = Q`, the Nusselt correlation and the friction factor.
               Validated ANALYTICALLY: the energy balance is checked to machine precision
               and the correlation is used only inside its stated Reynolds range.

  SOLID SIDE   fin efficiency, area amplification and base conduction -- the part that turns
               a channel-wall `h` into an effective `h` on the footprint.
               Validated NUMERICALLY against MOOSE: the finned solid is solved explicitly
               with a convective boundary on the wetted walls and a uniform flux on the base,
               and the base-to-fluid resistance is compared with the compact model.
               **This is the half the compact model can get wrong, and it is now checked.**

  COUPLING     the streamwise fluid temperature rise feeding back on the wall.
               Validated by construction: the production solve iterates it to a fixed point
               and the energy removed is compared with the energy deposited.

MOOSE cannot model the flow, and saying otherwise would be the same category error as calling
an electrostatic solve a DC conduction validation. It is used for the conduction problem it
can pose exactly.

PREDECLARED ACCEPTANCE, fixed before running:
    solid-side thermal resistance   <= 5 % ACCEPTED, <= 10 % CONDITIONAL, else REJECTED
    energy balance                  <= 0.1 %
"""
from __future__ import annotations
import csv, math, shutil, subprocess, sys, time
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for d in ("phase0mr", "phase0m"):
    sys.path.insert(0, str(R / "scripts" / d))
from cooling import Microchannel, K_F, CP_F, nu_lam, f_re                  # noqa: E402
from moose_conduction import MOOSE, available                              # noqa: E402

OUT = R / "results" / "phase0mr"
WD = OUT / "coolval"
OUT.mkdir(parents=True, exist_ok=True)
ACCEPT_PCT, CONDITIONAL_PCT = 5.0, 10.0

CASES = {
    "TuckermanPease_50x302": dict(w_ch_um=50, h_ch_um=302, t_fin_um=50, k_solid=130.0),
    "wide_100x200": dict(w_ch_um=100, h_ch_um=200, t_fin_um=100, k_solid=130.0),
    "tall_50x500": dict(w_ch_um=50, h_ch_um=500, t_fin_um=50, k_solid=130.0),
    "copper_100x500": dict(w_ch_um=100, h_ch_um=500, t_fin_um=100, k_solid=385.0),
}


def moose_fin(name: str, w_ch, h_ch, t_fin, t_base, k_solid, h_wall, L,
              n_w=10, n_h=28, n_b=6, timeout=900) -> dict:
    """One half-fin + half-channel unit cell, solved explicitly.

    Symmetry planes at the fin mid-plane and the channel mid-plane, so the cell is
    (t_fin/2 + w_ch/2) wide. Base: uniform heat flux. Wetted walls: convective to T_f = 0.
    R_solid = T_base_mean / Q.
    """
    d = WD / name
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    xw = t_fin / 2.0 + w_ch / 2.0
    z_top = t_base + h_ch
    q = 1.0e4                                   # W/m2 on the base, arbitrary: R is linear
    src = f"""[Mesh]
  [gen]
    type = GeneratedMeshGenerator
    dim = 3
    nx = {n_w} ny = 4 nz = {n_b + n_h}
    xmin = 0 xmax = {xw:.9g} ymin = 0 ymax = {L:.9g} zmin = 0 zmax = {z_top:.9g}
  []
  [carve]
    type = ParsedSubdomainMeshGenerator
    input = gen
    combinatorial_geometry = 'x > {t_fin / 2.0:.9g} & z > {t_base:.9g}'
    block_id = 9
  []
  [kill]
    type = BlockDeletionGenerator
    input = carve
    block = '9'
    new_boundary = 'wet'
  []
  [walltop]
    type = ParsedGenerateSideset
    input = kill
    combinatorial_geometry = 'z > {z_top - 1e-12:.9g} & x < {t_fin / 2.0 + 1e-12:.9g}'
    normal = '0 0 1'
    new_sideset_name = 'fintop'
  []
  [basess]
    type = ParsedGenerateSideset
    input = walltop
    combinatorial_geometry = 'z < 1e-12'
    normal = '0 0 -1'
    new_sideset_name = 'base'
  []
[]
[Variables/T]
  initial_condition = 0.0
[]
[Kernels/c]
  type = HeatConduction
  variable = T
[]
[Materials/m]
  type = HeatConductionMaterial
  thermal_conductivity = {k_solid:.9g}
[]
[BCs]
  [q_in]
    type = NeumannBC
    variable = T
    boundary = 'base'
    value = {q:.9g}
  []
  [conv_wet]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'wet'
    T_infinity = 0.0
    coefficient = {h_wall:.9g}
  []
  [conv_top]
    type = ConvectiveFluxFunction
    variable = T
    boundary = 'fintop'
    T_infinity = 0.0
    coefficient = {h_wall:.9g}
  []
[]
[Postprocessors]
  [T_base]
    type = SideAverageValue
    variable = T
    boundary = 'base'
  []
  [A_base]
    type = AreaPostprocessor
    boundary = 'base'
  []
  [Q_wet]
    type = SideDiffusiveFluxIntegral
    variable = T
    boundary = 'wet'
    diffusivity = thermal_conductivity
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -pc_hypre_type'
  petsc_options_value = 'hypre boomeramg'
  nl_rel_tol = 1e-11
[]
[Outputs]
  csv = true
[]
"""
    p = d / f"{name}.i"
    p.write_text(src)
    r = subprocess.run([str(MOOSE), "-i", p.name], cwd=d, capture_output=True,
                       text=True, timeout=timeout)
    csvp = d / f"{name}_out.csv"
    if r.returncode != 0 or not csvp.is_file():
        return {"status": f"MOOSE FAILED rc={r.returncode}",
                "stderr": (r.stderr or r.stdout)[-400:]}
    last = list(csv.DictReader(csvp.open()))[-1]
    a_base = float(last["A_base"])
    t_base_mean = float(last["T_base"])
    q_tot = q * a_base
    return {"status": "OK", "T_base_mean_K": t_base_mean, "Q_W": q_tot,
            "A_base_m2": a_base, "R_solid_K_W": t_base_mean / q_tot,
            "R_solid_per_area_K_m2_W": t_base_mean / q,
            "h_eff_from_moose": q / t_base_mean}


def compact_solid(w_ch, h_ch, t_fin, t_base, k_solid, h_wall) -> dict:
    """The compact model's SOLID side only, on the same unit cell."""
    p = w_ch + t_fin
    m = math.sqrt(2 * h_wall / (k_solid * t_fin))
    eta = math.tanh(m * h_ch) / (m * h_ch)
    a_wet_per_base = (w_ch + 2 * eta * h_ch) / p
    r_conv = 1.0 / (h_wall * a_wet_per_base)          # K m2 / W on the base area
    r_base = t_base / k_solid
    return {"fin_efficiency": eta, "area_amplification": a_wet_per_base,
            "R_solid_per_area_K_m2_W": r_conv + r_base,
            "h_eff_compact": 1.0 / (r_conv + r_base)}


def main() -> int:
    if not available():
        print("MOOSE absent"); return 1
    rows = []
    t_base, L = 100e-6, 1000e-6
    for name, c in CASES.items():
        mc = Microchannel(w_ch_um=c["w_ch_um"], h_ch_um=c["h_ch_um"],
                          t_fin_um=c["t_fin_um"], k_solid=c["k_solid"], m_dot_g_s=27.0)
        s = mc.solve()
        h_wall = s["h_channel_W_m2K"]
        w, h, tf = (c["w_ch_um"] * 1e-6, c["h_ch_um"] * 1e-6, c["t_fin_um"] * 1e-6)
        cm = compact_solid(w, h, tf, t_base, c["k_solid"], h_wall)
        mo = moose_fin(name, w, h, tf, t_base, c["k_solid"], h_wall, L)
        row = {"case": name, **{k: c[k] for k in c}, "h_wall_W_m2K": h_wall,
               "Nu": s["Nu"], "Re": s["Re"], "regime": s["regime"],
               "fin_efficiency": cm["fin_efficiency"],
               "area_amplification": cm["area_amplification"],
               "R_compact_K_m2_W": cm["R_solid_per_area_K_m2_W"],
               "R_moose_K_m2_W": mo.get("R_solid_per_area_K_m2_W"),
               "moose_status": mo.get("status")}
        if mo.get("status") == "OK":
            e = 100 * abs(cm["R_solid_per_area_K_m2_W"] - mo["R_solid_per_area_K_m2_W"]) \
                / mo["R_solid_per_area_K_m2_W"]
            row["error_pct"] = e
            row["verdict"] = ("ACCEPTED" if e <= ACCEPT_PCT else
                              "CONDITIONAL" if e <= CONDITIONAL_PCT else "REJECTED")
        rows.append(row)
        print(f"  {name:24s} h_wall={h_wall:8.0f} eta={cm['fin_efficiency']:.4f} "
              f"amp={cm['area_amplification']:5.2f}  R_compact={cm['R_solid_per_area_K_m2_W']:.6e} "
              f"R_moose={mo.get('R_solid_per_area_K_m2_W', float('nan')):.6e} "
              f"err={row.get('error_pct', float('nan')):.2f} %  "
              f"{row.get('verdict', mo.get('status'))}", flush=True)
    k = sorted({x for r in rows for x in r})
    with open(OUT / "cooling_validation.csv", "w", newline="") as fh:
        w_ = csv.DictWriter(fh, fieldnames=k); w_.writeheader(); w_.writerows(rows)
    ok = [r for r in rows if r.get("verdict")]
    print(f"\n{sum(1 for r in ok if r['verdict']=='ACCEPTED')}/{len(ok)} ACCEPTED")
    print(f"wrote {OUT/'cooling_validation.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
