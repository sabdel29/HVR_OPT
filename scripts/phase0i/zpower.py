#!/usr/bin/env python3
"""Phase-0I Sec.4 -- rail-aware electrical evaluation for each Z-architecture.

Everything is SYSTEM scope through the Phase-0H guard, so a per-regulator term cannot be
summed into a system total (DEFECT #30).

Two things differ per architecture and both matter:
  * WHICH RAIL crosses the substrate. Z2 puts 1000 A on the TSV field; Z1, Z4 and Z5 put
    23.4 A on it. At fixed geometry that is a factor of 1822 in I^2.
  * WHERE the 1 V rail has to travel laterally. Z4 hands it straight up through 10 um pads;
    Z1 spreads it under the die; Z5 carries it across the interposer from beside the die.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
for p in ("phase0i", "phase0h", "phase0f", "phase0e", "phase0dr"):
    sys.path.insert(0, str(REPO / "scripts" / p))

import ppdn as ppdn0dr                                                       # noqa: E402
from architecture0e import CROWDING_DEFAULT, j_envelope, pol_grid            # noqa: E402
from scope import Q, Scope, total, watts_per_regulator, watts_system         # noqa: E402
from stack import allocate, rdl_network_solve, stacks_from_cfg               # noqa: E402
from zarch import path_for, rail_currents, realizable                        # noqa: E402

DIE_MM = 22.36
NPOL = 10
GRID_N = 161
_DOE: list = []
_MSTACK: list = []


def _tier_loss_system(tier_name: str, tier_cfg: dict, I_total: float, area_mm2: float,
                      T_c: float, h_m: float | None, j: float, policy: str,
                      crowding: float = CROWDING_DEFAULT) -> tuple[Q, dict]:
    """Loss of ONE tier for the WHOLE system, built system-wide from the start.

    Phase-0E's vertical_tier_per_regulator() works per regulator because the embedded cell is
    per regulator. Here the field spans the package, so it is natural and safer to evaluate it
    system-wide directly -- no scope conversion is involved and none can be forgotten.
    """
    area_m2 = area_mm2 * 1e-6
    pitch = ppdn0dr._v(tier_cfg["pitch_m"])
    al = allocate(tier_name, I_total, ppdn0dr.tier_area_m2(tier_cfg), pitch, area_m2, j,
                  policy=policy, strict=False)
    rs = ppdn0dr.r_single(tier_cfg, T_c, h_m) * crowding
    r_field = rs / al.n_allocated
    r_loop = 2.0 * r_field                       # supply + identical return field
    p = I_total ** 2 * r_loop
    info = {"n_required": al.n_required, "n_allocated": al.n_allocated,
            "n_available": al.n_available, "i_per_via_a": I_total / al.n_allocated,
            "r_single_ohm": rs, "r_field_ohm": r_field, "r_loop_ohm": r_loop,
            "feasible": al.feasible}
    return watts_system(p, tier=tier_name), info


def evaluate_z(arch: str, h_sub_mm: float, p_conv_total_w: float, T_c: float = 85.0,
               load_w: float = 1000.0, policy: str = "A_min_capability",
               lateral_gap_mm: float = 2.0, stack=None,
               hvr_area_mm2: float = 274.89) -> dict:
    """Full rail-aware electrical evaluation of one Z-architecture at one thickness."""
    P = ppdn0dr.load_paths()
    tiers = P["tiers"]
    env = j_envelope()
    j_cu, j_solder = env["cu"]["june2026"], env["solder"]["ectc2024"]
    stack = stack or stacks_from_cfg()["ectc2024_primary"]
    rc = rail_currents(load_w)
    segs = path_for(arch, load_w)

    rz = realizable(arch, h_sub_mm)
    # TSV length: the embedded cell sits ON TOP of the via field, so only the remainder is
    # via. In every other architecture the field spans the whole substrate.
    if arch == "ARCH_Z1_EMBEDDED":
        h_tsv_m = max(h_sub_mm * 1e3 - (rz.t_cell_um or 0.0), 0.0) * 1e-6
    else:
        h_tsv_m = h_sub_mm * 1e-3

    rows, qs = [], []
    for s in segs:
        if s.tier in ("converter", "rdl"):
            continue
        tc = tiers[s.tier]
        jj = j_cu if tc["material"] == "copper" else j_solder
        hm = h_tsv_m if s.tier == "tsv" else None
        # field footprint: the BGA field spans the package, the TSV/microbump fields span
        # the die shadow they have to feed
        fp = (30.0 * 30.0) if s.tier == "bga" else DIE_MM ** 2
        q, info = _tier_loss_system(s.tier, tc, s.i_a, fp, T_c, hm, jj, policy)
        rows.append({"segment": s.seg, "tier": s.tier, "rail": s.rail, "v_volt": s.v_volt,
                     "i_a": s.i_a, "i_rms_a": s.i_rms_a, "location": s.location,
                     "scope": "SYSTEM", "p_w": q.value, **info})
        qs.append(q)

    # ---- the lateral RDL run, which is where the architectures differ most -------------
    # Source placement must match the validated Phase-0F lattice, not an idealised grid: a
    # perfect 7x7 covering interleaves with the load grid and returns ~0 lateral loss, which
    # is an artifact of the idealisation rather than a property of the architecture.
    import kw1
    from etm.config import load_doe, load_stack
    doe = _DOE[0] if _DOE else load_doe()
    if not _DOE:
        _DOE.append(doe)
    mstack = _MSTACK[0] if _MSTACK else load_stack()
    if not _MSTACK:
        _MSTACK.append(mstack)
    n_src = 49
    tile_side = math.sqrt(hvr_area_mm2 / n_src) if hvr_area_mm2 else DIE_MM / 7
    if arch == "ARCH_Z5_2P5D_LATERAL":
        # the VR field sits BESIDE the die, so every source is off to one side and the 1 V
        # rail must cross the gap before it can spread.
        span = DIE_MM + 2 * (lateral_gap_mm + tile_side * 3.5)
        xs = -(DIE_MM / 2 + lateral_gap_mm + tile_side / 2)
        src = [(xs, (k + .5) / n_src * DIE_MM - DIE_MM / 2) for k in range(n_src)]
    else:
        span = DIE_MM
        src = kw1.tiles_for("uniform", tile_side, mstack, doe, n_src)
    pol = pol_grid()
    sol = rdl_network_solve(stack, src, [rc["I_out_a"] / len(src)] * len(src), pol,
                            [rc["I_out_a"] / len(pol)] * len(pol), span_mm=span, T_c=T_c,
                            n=GRID_N, src_size_mm=tile_side,
                            load_size_mm=DIE_MM / NPOL,
                            ground_xy=pol[len(pol) // 2], ground_size_mm=DIE_MM / NPOL)
    q_rdl = watts_system(sol["p_loop_w"], tier="rdl")
    qs.append(q_rdl)
    rows.append({"segment": "lateral 1 V distribution", "tier": "rdl", "rail": "LV",
                 "v_volt": 1.0, "i_a": rc["I_out_a"], "i_rms_a": rc["I_out_a"],
                 "location": ("across the interposer from beside the die"
                              if arch == "ARCH_Z5_2P5D_LATERAL" else "under the die"),
                 "scope": "SYSTEM", "p_w": q_rdl.value})

    q_pdn = total(qs, Scope.SYSTEM)
    q_conv = watts_system(p_conv_total_w, tier="converter")
    q_tot = total([q_pdn, q_conv], Scope.SYSTEM)
    by = {r["tier"]: r["p_w"] for r in rows}
    tsvrow = next((r for r in rows if r["tier"] == "tsv"), None)
    return {
        "arch": arch, "h_sub_mm": h_sub_mm, "realizable": rz.feasible,
        "h_sub_min_um": rz.h_sub_min_um, "realizability_rule": rz.rule,
        "tsv_rail": tsvrow["rail"] if tsvrow else None,
        "tsv_current_a": tsvrow["i_a"] if tsvrow else None,
        "n_tsv_req": tsvrow["n_required"] if tsvrow else None,
        "n_tsv_alloc": tsvrow["n_allocated"] if tsvrow else None,
        "n_tsv_avail": tsvrow["n_available"] if tsvrow else None,
        "tsv_feasible": tsvrow["feasible"] if tsvrow else None,
        "P_by_tier_w": by, "P_by_tier_scope": "SYSTEM",
        "P_pdn_w": q_pdn.value, "P_conv_w": p_conv_total_w,
        "P_elec_total_w": q_tot.value,
        "efficiency_pct": 100.0 * load_w / (load_w + q_tot.value),
        "segments": rows,
    }
