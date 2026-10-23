#!/usr/bin/env python3
"""PHASE 0N-V -- orthotropic board model for the IT-968G 18-layer 2.4 mm server PCB.

Replaces the unexplained isotropic E = 22 GPa / CTE = 16 ppm/K used by the historical
fr4_2p4mm case. Every quantity is classified SOURCE_BACKED / DERIVED / BOUNDED / OPEN.

Laminate  ITEQ IT-968G official datasheet W-CTE-1002-55B REV, fetched 2026-10-23.
Board     UGPCB 18-layer server PCB product page: 2.4 mm +-10 %, 18 layers,
          1/1/1/1/1/1/1/2/2/2/2/1/1/1/1/1/1/1 oz, laminate ITEQ IT968G.
Copper    the framework's own SOURCE_BACKED copper (configs/phase0b/package_stack.yaml).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
OUT = R / "research" / "phase0nv"
OUT.mkdir(parents=True, exist_ok=True)

# ---- SOURCE_BACKED: IT-968G datasheet -----------------------------------------------
E_WARP, E_FILL = 15.0e3, 14.0e3        # MPa, ASTM D3039
CTE_XY_A = (12.0, 14.0)                # ppm/K, IPC 2.4.41        <- primary
CTE_XY_B = (11.0, 12.0)                # ppm/K, IPC 2.4.24.5      <- method sensitivity
CTE_Z_A1, CTE_Z_A2 = 45.0, 260.0       # ppm/K pre-/post-Tg, IPC 2.4.24
TG, TD, MOT = 175.0, 400.0, 130.0      # degC

# ---- SOURCE_BACKED: board construction (UGPCB) ---------------------------------------
T_PCB_UM = 2400.0
N_1OZ, N_2OZ = 14, 4                   # from 1/1/1/1/1/1/1/2/2/2/2/1/1/1/1/1/1/1
OZ_UM = 34.8                           # standard finished-foil conversion, BOUNDED

# ---- SOURCE_BACKED in-framework copper ----------------------------------------------
E_CU, NU_CU, CTE_CU, K_CU = 110.0e3, 0.34, 16.66, 400.0
# cross-check from the brief's C11000 figures (copper.org unreachable: CDA site in
# maintenance, HTTP 403 / maintenance page on 2026-10-23):
CU_XCHECK = {"E_GPa": 117.0, "cte_ppm": 16.9, "k_W_mK": 391.0}

# ---- BOUNDED: laminate thermal conductivity (NOT in the IT-968G datasheet) -----------
# literature evidence that FR4 is thermally orthotropic (Jrnl Mat Res Tech 2026,
# 10.1016/j.jmrt.2026.01.011): k_xy ~ 3.4-4.5, k_z ~ 0.35-0.38 W/mK for ITS laminate.
# Isola 370HR datasheet gives a single k = 0.4 W/mK. Neither is IT-968G.
K_LAM_XY_BOUND = (0.4, 4.5)
K_LAM_Z_BOUND = (0.35, 0.40)
E_LAM_Z_BOUND = (E_WARP * 0.25, E_WARP * 0.6)   # OPEN; bracketed, see audit

t_cu_full = N_1OZ * OZ_UM + N_2OZ * 2 * OZ_UM
f_cu_full = t_cu_full / T_PCB_UM


def homogenize(eta):
    """eta = areal Cu coverage, applied uniformly to all 18 layers."""
    fv = f_cu_full * eta                      # Cu volume fraction
    fl = 1.0 - fv
    Ex = fv * E_CU + fl * E_WARP              # Voigt in-plane
    Ey = fv * E_CU + fl * E_FILL
    # Reuss over the OPEN E_lam_z bracket. A STIFFER laminate gives a STIFFER stack, so
    # the lower bound must be built from E_LAM_Z_BOUND[0]. Naming these the other way
    # round is what stored the composite bracket as [upper, lower].
    Ez_lo = 1.0 / (fv / E_CU + fl / E_LAM_Z_BOUND[0])
    Ez_hi = 1.0 / (fv / E_CU + fl / E_LAM_Z_BOUND[1])
    ax = (fv * E_CU * CTE_CU + fl * E_WARP * CTE_XY_A[0]) / Ex   # modulus-weighted
    ay = (fv * E_CU * CTE_CU + fl * E_FILL * CTE_XY_A[1]) / Ey
    az = fv * CTE_CU + fl * CTE_Z_A1                              # series, pre-Tg
    kxy = [fv * K_CU + fl * k for k in K_LAM_XY_BOUND]            # Voigt
    kz = [1.0 / (fv / K_CU + fl / k) for k in K_LAM_Z_BOUND]      # Reuss
    return dict(eta=eta, f_cu_vol=fv, Ex_MPa=Ex, Ey_MPa=Ey,
                Ez_MPa_bounds=[Ez_lo, Ez_hi], cte_x=ax, cte_y=ay, cte_z=az,
                k_xy_bounds=kxy, k_z_bounds=kz)


print(f"IT-968G  E_warp {E_WARP/1e3:.0f} / E_fill {E_FILL/1e3:.0f} GPa   "
      f"CTE_xy {CTE_XY_A[0]}/{CTE_XY_A[1]} ppm/K (IPC 2.4.41)   "
      f"CTE_z {CTE_Z_A1}/{CTE_Z_A2} pre/post-Tg")
print(f"         Tg {TG:.0f} C   Td {TD:.0f} C   MOT {MOT:.0f} C")
print(f"NOT in the datasheet: Poisson, thermal conductivity, E_z, shear moduli, density\n")
print(f"Copper: {N_1OZ} x 1 oz + {N_2OZ} x 2 oz at {OZ_UM} um/oz = {t_cu_full:.1f} um")
print(f"  full-coverage upper bound t_Cu/t_PCB = {100*f_cu_full:.2f} %  "
      f"(NOT the actual copper volume -- signal layers are patterned)\n")
hdr = f"{'eta':>5}{'f_Cu':>8}{'Ex GPa':>9}{'Ey GPa':>9}{'a_x':>7}{'a_y':>7}{'a_z':>7}{'k_xy W/mK':>22}"
print(hdr); print("-" * len(hdr))
rows = []
for eta in (0.0, 0.25, 0.50, 0.75, 1.0):
    r = homogenize(eta); rows.append(r)
    print(f"{eta:>5.2f}{r['f_cu_vol']:>8.3f}{r['Ex_MPa']/1e3:>9.1f}{r['Ey_MPa']/1e3:>9.1f}"
          f"{r['cte_x']:>7.2f}{r['cte_y']:>7.2f}{r['cte_z']:>7.2f}"
          f"{r['k_xy_bounds'][0]:>10.2f} - {r['k_xy_bounds'][1]:<9.2f}")
print(f"\nhistorical arbitrary fr4_2p4mm: E = 22.0 GPa (isotropic), CTE = 16.0 ppm/K, "
      f"k = 0.30\n  -> E is OUTSIDE the eta sweep until eta ~ "
      f"{next(r['eta'] for r in rows if r['Ex_MPa']/1e3 > 22.0):.2f}, and the CTE is "
      f"above every derived alpha_x.")

# ---------------------------------------------------------------------------------------
# THE ONE REDUCTION. Every consumer -- board.py, the two research documents, the guards --
# reads this block. Nothing downstream re-picks a value out of the sweep, because a second
# pick is a second source and the two drift apart silently (that is how the audit text came
# to say k_xy = 67.58 while board.py said 65.86).
#
# RULE: nominal eta, and the ARITHMETIC MIDPOINT of each bounded bracket, applied uniformly.
# The bracket itself is carried alongside so no consumer has to pretend the value is exact.
ETA_NOM = 0.50
_n = next(r for r in rows if abs(r["eta"] - ETA_NOM) < 1e-12)


def _mid(b):
    lo, hi = b
    if lo > hi:
        raise ValueError(f"bracket {b} is stored [upper, lower]; store [lower, upper]")
    return 0.5 * (lo + hi)


NOMINAL = {
    "eta": ETA_NOM,
    "rule": "nominal eta; arithmetic midpoint of each bounded bracket",
    "E_MPa": _n["Ex_MPa"],                 # in-plane, warp; see HOMOGENIZATION.md Sec.5
    "Ey_MPa": _n["Ey_MPa"],
    "Ez_MPa": _mid(_n["Ez_MPa_bounds"]), "Ez_MPa_bracket": _n["Ez_MPa_bounds"],
    "nu": 0.20,                            # ASSUMPTION, not an IT-968G property
    "cte": _n["cte_x"],
    "cte_y": _n["cte_y"], "cte_z": _n["cte_z"],
    "k_xy": _mid(_n["k_xy_bounds"]), "k_xy_bracket": _n["k_xy_bounds"],
    "k_z": _mid(_n["k_z_bounds"]), "k_z_bracket": _n["k_z_bounds"],
}
print(f"\nNOMINAL (eta={ETA_NOM}): E={NOMINAL['E_MPa']:.1f} MPa  cte={NOMINAL['cte']:.3f} ppm/K  "
      f"k_xy={NOMINAL['k_xy']:.3f}  k_z={NOMINAL['k_z']:.4f} W/mK")
print(f"  k_xy/k_z = {NOMINAL['k_xy']/NOMINAL['k_z']:.0f}x anisotropy")

json.dump({"laminate": {"name": "ITEQ IT-968G", "doc": "W-CTE-1002-55B",
                        "E_warp_MPa": E_WARP, "E_fill_MPa": E_FILL,
                        "cte_xy_primary_ppm": CTE_XY_A, "cte_xy_alt_ppm": CTE_XY_B,
                        "cte_z_pre_tg_ppm": CTE_Z_A1, "cte_z_post_tg_ppm": CTE_Z_A2,
                        "Tg_C": TG, "Td_C": TD, "MOT_C": MOT,
                        "absent": ["poisson", "thermal_conductivity", "E_z",
                                   "shear_moduli", "density"]},
           "board": {"t_um": T_PCB_UM, "tol_pct": 10.0, "layers": 18,
                     "n_1oz": N_1OZ, "n_2oz": N_2OZ, "oz_um": OZ_UM,
                     "t_cu_full_um": t_cu_full, "f_cu_full": f_cu_full,
                     "source": "UGPCB 18-layer server PCB"},
           "copper": {"E_MPa": E_CU, "nu": NU_CU, "cte_ppm": CTE_CU, "k_W_mK": K_CU,
                      "source": "framework package_stack.yaml (SOURCE_BACKED)",
                      "c11000_crosscheck": CU_XCHECK,
                      "crosscheck_note": "copper.org unreachable 2026-10-23 (CDA site "
                                         "maintenance); values agree within 6 %"},
           "bounds": {"k_lam_xy": K_LAM_XY_BOUND, "k_lam_z": K_LAM_Z_BOUND,
                      "E_lam_z": E_LAM_Z_BOUND},
           "nominal_tensor": NOMINAL,
           "sweep": rows},
          (OUT / "pcb_homogenization.json").open("w"), indent=1)
print(f"\nwrote {OUT/'pcb_homogenization.json'}")


# ---------------------------------------------------------------------------------------
# The YAML config is a THIRD consumer of the same reduction. It is regenerated here rather
# than hand-maintained, so it cannot drift away from the JSON and board.py.
_CFG = R / "configs" / "phase0nv" / "pcb_it968g_18layer.yaml"
if _CFG.exists():
    import yaml
    cfg = yaml.safe_load(_CFG.read_text())
    cfg["nominal"] = dict(NOMINAL, status="DERIVED",
                          note=("GENERATED by scripts/phase0nv_pcb_homogenization.py -- do "
                                "not hand-edit. eta = 0.50 is the MIDDLE OF THE BOUNDING "
                                "SWEEP, not a measurement; every mechanical result must "
                                "carry its eta sensitivity."))
    _CFG.write_text(yaml.safe_dump(cfg, sort_keys=False, width=88))
    print(f"regenerated {_CFG.relative_to(R)} nominal block")
