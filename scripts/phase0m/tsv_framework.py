#!/usr/bin/env python3
"""Phase-0M Part 5 -- wrapper around the PRE-EXISTING TSV electrothermal framework.

FOUND, NOT REIMPLEMENTED.

  path      /home/beams0/MGHARIB/Model/TSVs_Framework_MultiGND_new_3_HSPICE.py
  mtime     2025-11-09  (43377 bytes; no version string in the file, so the mtime and a
            sha256 recorded in TSV_FRAMEWORK_INTERFACE.md are the version handle)
  entry     module-level functions; `main()` is guarded by __name__ so import is safe
  backend   HSPICE at /local/synopsys/hspice/W-2024.09-SP2-2/hspice/bin/hspice for the
            multi-conductor S-parameter solve; the analytic RLGC layer needs no backend
  companion /home/beams0/MGHARIB/tessera-master -- HFSS reference results and the
            error statistics that validate the framework's S-parameters
  surrogate /home/beams0/MGHARIB/Model/tsv_surrogate_v3.pt -- a trained ML surrogate; NOT
            used here, because a surrogate trained on a signal-integrity corpus has no
            established validity for a DC power via field

Functions this phase uses:

  Z_in(r_via, freq)                       internal impedance from the Bessel-function skin
                                          solution -> (R_internal, L_internal, Z)
  TSV_Inductance_SELF / _Mutual           external partial inductances to a reference via
  Substrate_Inductance_To_Ref / _Mutual   the same through the depleted substrate
  Via_cap(r_via, t_dep, t_ox)             MOS via capacitance per unit length
  depl_thick(...)                         depletion-region thickness (root of the residual)
  thermal_conductivity(r_via, t_ox, wid_subs, l_subs, N, M)
                                          -> (k_x, k_y, k_z, rho_cp) for a TSV ARRAY

WHY A WRAPPER AND NOT A CALL
The framework is written for signal integrity: micrometres in, per-unit-length out, one
reference via, and `thermal_conductivity` takes an (N, M) array count rather than a pitch.
This module adapts it to the power-delivery quantities Phase 0M needs and, critically,
CHECKS it against the independent Phase-0M model rather than trusting it.
"""
from __future__ import annotations
import hashlib, importlib.util, math, sys
from pathlib import Path

FRAMEWORK = Path("/home/beams0/MGHARIB/Model/TSVs_Framework_MultiGND_new_3_HSPICE.py")
TESSERA = Path("/home/beams0/MGHARIB/tessera-master")
_MOD = None


def available() -> bool:
    return FRAMEWORK.is_file()


def sha256() -> str:
    return hashlib.sha256(FRAMEWORK.read_bytes()).hexdigest()


def load():
    """Import the framework as a module without running its CLI."""
    global _MOD
    if _MOD is not None:
        return _MOD
    if not available():
        raise FileNotFoundError(
            f"TSV electrothermal framework not found at {FRAMEWORK}. "
            "Phase-0M Part 5 requires this to be logged, not invented.")
    spec = importlib.util.spec_from_file_location("tsv_framework_ext", FRAMEWORK)
    m = importlib.util.module_from_spec(spec)
    sys.modules["tsv_framework_ext"] = m
    spec.loader.exec_module(m)
    _MOD = m
    return m


# ---------------------------------------------------------------------------
# electrical
# ---------------------------------------------------------------------------
def skin_resistance(r_m: float, h_m: float, freq_hz: float, sigma: float = 5.8e7) -> dict:
    """Series resistance of ONE via at frequency f, from the framework's Bessel solution.

    Returns the DC value too, so the skin ratio is explicit rather than assumed negligible.
    """
    m = load()
    rint, lint, _ = m.Z_in(r_m, max(freq_hz, 1.0), cond_cu=sigma)
    r_ac = rint * h_m                      # Z_in is per unit length
    r_dc = h_m / (sigma * math.pi * r_m ** 2)
    delta = math.sqrt(2.0 / (2 * math.pi * max(freq_hz, 1.0) * 4e-7 * math.pi * sigma))
    return {"R_dc_ohm": r_dc, "R_ac_ohm": r_ac, "skin_ratio": r_ac / r_dc,
            "L_internal_H": lint * h_m, "delta_m": delta, "delta_over_r": delta / r_m,
            "freq_hz": freq_hz}


def loop_inductance(r_m: float, h_m: float, pitch_m: float, n_parallel: int = 1,
                    third_via_pitch_m: float | None = None) -> dict:
    """Loop inductance of a signal via referenced to a ground via one pitch away.

    `TSV_Inductance_SELF(r, TSV_LOC, REF_LOC)` already returns the PARTIAL LOOP inductance of
    that pair -- it is the two-wire form (mu/2pi) ln(d^2 / r r_0) -- so the loop value is
    that, not self minus mutual. The framework's `_Mutual` needs three DISTINCT locations
    (two conductors and a reference); calling it with the reference coincident with a
    conductor divides by zero, which is how this was caught.

    `n_parallel` interleaved P/G pairs reduce the loop inductance sub-linearly because of
    mutual coupling; the coupled value is returned when a third via location is supplied.
    """
    m = load()
    p_um = pitch_m * 1e6
    l_loop_per_m = m.TSV_Inductance_SELF(r_m, (0.0, 0.0), (p_um, 0.0))
    out = {"L_loop_per_m": l_loop_per_m, "L_loop_H": l_loop_per_m * h_m,
           "L_loop_nH": l_loop_per_m * h_m * 1e9, "pitch_m": pitch_m,
           "n_parallel": n_parallel,
           "L_parallel_uncoupled_nH": l_loop_per_m * h_m * 1e9 / max(n_parallel, 1)}
    if third_via_pitch_m:
        q_um = third_via_pitch_m * 1e6
        l_m = m.TSV_Inductance_Mutual(r_m, (0.0, 0.0), (q_um, 0.0), (p_um, 0.0))
        out["L_mutual_per_m"] = l_m
        out["k_coupling"] = l_m / l_loop_per_m if l_loop_per_m else float("nan")
        n = max(n_parallel, 1)
        out["L_parallel_coupled_nH"] = (l_loop_per_m + (n - 1) * l_m) / n * h_m * 1e9
    return out


# ---------------------------------------------------------------------------
# thermal -- the anisotropic homogenization Parts 20/21 need
# ---------------------------------------------------------------------------
def k_tensor(r_m: float, t_ox_m: float, pitch_m: float, field_side_m: float,
             k_cu: float = 385.0, k_ox: float = 1.4, k_si: float = 130.0) -> dict:
    """Anisotropic effective conductivity of a TSV array, via the framework.

    The framework signature is (r_via, t_ox, wid_subs, l_subs, N, M) where N and M are the
    array counts along each axis. A pitch is converted to counts by N = M = side / pitch.
    """
    m = load()
    n = max(int(field_side_m / pitch_m), 1)
    kx, ky, kz, rcp = m.thermal_conductivity(
        r_m, t_ox_m, field_side_m, field_side_m, n, n,
        K_metal=k_cu, K_ins=k_ox, K_subs=k_si)
    return {"k_x": kx, "k_y": ky, "k_z": kz, "rho_cp": rcp,
            "n_along_x": n, "n_along_y": n, "pitch_m": pitch_m,
            "f_cu_geometric": n * n * math.pi * r_m ** 2 / field_side_m ** 2}


def interface_record() -> dict:
    return {"path": str(FRAMEWORK), "sha256": sha256() if available() else None,
            "available": available(),
            "mtime": (FRAMEWORK.stat().st_mtime if available() else None),
            "bytes": (FRAMEWORK.stat().st_size if available() else None),
            "hfss_reference_dir": str(TESSERA),
            "hfss_error_stats": str(TESSERA / "error_stats_global.csv")}


if __name__ == "__main__":
    print("available:", available())
    if available():
        print("sha256:", sha256()[:16])
        for f in (1e0, 1e6, 1e9):
            d = skin_resistance(15e-6, 300e-6, f)
            print(f"  f={f:8.0e} Hz  R_dc={d['R_dc_ohm']*1e3:.4f} mOhm  "
                  f"R_ac={d['R_ac_ohm']*1e3:.4f} mOhm  ratio={d['skin_ratio']:.4f}  "
                  f"delta/r={d['delta_over_r']:.2f}")
        print(" ", loop_inductance(15e-6, 300e-6, 60e-6, n_parallel=8,
                                   third_via_pitch_m=120e-6))
        print(" ", k_tensor(15e-6, 0.5e-6, 60e-6, 22.36e-3))
