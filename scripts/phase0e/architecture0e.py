#!/usr/bin/env python3
"""Phase-0E architecture evaluation with the sourced stack and separated TSV counts.

WHAT IS DIFFERENT FROM PHASE 0D-R
  * RDL is the sourced ECTC-2024 stack (t=10 um, W/S=10/2, 2 VDD + 2 GND layers) solved as
    an explicit VDD + GND pair, not a single assumed sheet multiplied by two.
  * n_required, n_allocated and n_available are separate; R_field = R_single / n_ALLOCATED.
  * The per-via limit is J * A with J taken from a source-backed envelope, and feasibility
    is a MAP over J rather than one verdict.
  * The vertical tiers carry the HFSS-measured current-crowding factor.
"""
from __future__ import annotations
import json, math, sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "phase0e"))
sys.path.insert(0, str(REPO / "scripts" / "phase0dr"))
from stack import (RDLStack, stacks_from_cfg, load_cfg, rdl_network_solve,
                   allocate, i_max_per_via, n_required, n_available, Infeasible, rho_cu)
sys.path.insert(0, str(REPO / "scripts" / "phase0h"))
from scope import Q, Scope, ScopeError, total, watts_per_regulator, watts_system
import ppdn as ppdn0dr

DIE_MM = 22.36
NPOL = 10
GRID_N = 161                      # converged against MOOSE (see rdl_grid_convergence.csv)

# Measured in HFSS on the P/G TSV loop: R_loop is 1.326x the 1-D series estimate at
# 1 MHz, where delta/r = 4.4 and skin effect is negligible. The excess is geometric
# current crowding where the pad meets the via.
CROWDING_DEFAULT = 1.326


def pol_grid(n=NPOL, die=DIE_MM):
    q = (np.arange(n) + .5) / n * die - die / 2
    return [(float(x), float(y)) for x in q for y in q]


def j_envelope() -> dict:
    c = load_cfg()["current_density"]
    return {"cu": {k: v["value"] for k, v in c["cu"].items()},
            "solder": {k: v["value"] for k, v in c["solder"].items()}}


@dataclass
class TierResult:
    tier: str
    rail: str
    current_a: float
    n_req: int
    n_alloc: int
    n_avail: int
    i_per_via_a: float
    j_actual: float
    r_single_ohm: float
    r_field_ohm: float
    r_loop_ohm: float
    p_w: float
    feasible: bool
    # PHASE-0H Sec.2. p_w is ONE REGULATOR's via-field loss, because vertical_tier() is
    # called with the per-regulator current and the per-tile footprint. The field is stored
    # (not just documented) so it reaches every CSV and JSON this object is written into.
    scope: str = Scope.PER_REGULATOR.value

    @property
    def p(self) -> Q:
        """The tier loss as a scoped quantity. Use this, not p_w, in any summation."""
        return Q(self.p_w, "W", Scope(self.scope), tier=self.tier, rail=self.rail)

    def p_system(self, n_vr: int) -> Q:
        """This tier's loss for the WHOLE system: n_vr identical regulators."""
        return self.p.to_system(n_vr)


def vertical_tier_per_regulator(name: str, tier: dict, rail: str, I: float,
                  footprint_mm2: float,
                  T_c: float, h_m: float | None, j: float, policy: str,
                  crowding: float = CROWDING_DEFAULT, strict: bool = True) -> TierResult:
    area = ppdn0dr.tier_area_m2(tier)
    pitch = ppdn0dr._v(tier["pitch_m"])
    al = allocate(name, I, area, pitch, footprint_mm2 * 1e-6, j, policy=policy, strict=strict)
    rs = ppdn0dr.r_single(tier, T_c, h_m) * crowding
    r_field = rs / al.n_allocated
    r_loop = 2.0 * r_field                       # supply + identical return via field
    return TierResult(name, rail, I, al.n_required, al.n_allocated, al.n_available,
                      I / al.n_allocated, al.j_actual_a_per_m2, rs, r_field, r_loop,
                      I ** 2 * r_loop, al.feasible, Scope.PER_REGULATOR.value)


# The historical name. It is kept so Phases 0D-R/0E/0F scripts still import, but the
# explicit name above is what new code must call.
vertical_tier = vertical_tier_per_regulator


def evaluate(arch: str, tiles_xy, tile_side_mm: float, h_sub_mm: float, i_total_a: float,
             p_conv_total_w: float, T_c: float, stack: RDLStack, policy: str = "A_min_capability",
             j_cu: float | None = None, j_solder: float | None = None,
             v_in: float = 48.0, v_out: float = 1.0, t_tile_mm: float = 0.150,
             crowding: float = CROWDING_DEFAULT, strict: bool = False,
             lateral_route_mm: float | None = None, grid_n: int = GRID_N) -> dict:
    P = ppdn0dr.load_paths()
    A = P["architectures"][arch]
    tiers = P["tiers"]
    env = j_envelope()
    j_cu = j_cu if j_cu is not None else env["cu"]["june2026"]
    j_solder = j_solder if j_solder is not None else env["solder"]["ectc2024"]

    n_vr = len(tiles_xy)
    i_out = i_total_a / n_vr
    p_conv_vr = p_conv_total_w / n_vr
    rc = ppdn0dr.rail_currents(i_out, v_in, v_out, p_conv_vr)
    cur = {"HV": rc["I_in_a"], "LV": rc["I_out_a"]}

    tile_fp = tile_side_mm ** 2
    h_tsv_m = (h_sub_mm - t_tile_mm) * 1e-3
    if h_tsv_m <= 0:
        raise ValueError("h_sub must exceed tile thickness")

    rows, infeas = [], []
    for s in A["segments"]:
        tn = s["tier"]
        if tn in ("converter", "rdl"):
            continue
        I = cur[s["rail"]]
        h_m = h_tsv_m if tn == "tsv" else None
        fp = tile_fp if tn in ("tsv", "microbump") else (30.0 * 30.0) / n_vr
        jj = j_cu if tiers[tn]["material"] == "copper" else j_solder
        try:
            r = vertical_tier_per_regulator(tn, tiers[tn], s["rail"], I, fp,
                              T_c, h_m, jj, policy,
                              crowding, strict=strict)
            rows.append(r)
            if not r.feasible:
                infeas.append(f"{tn}: n_req {r.n_req} > n_avail {r.n_avail}")
        except Infeasible as e:
            infeas.append(str(e))

    pol = pol_grid()
    sol = rdl_network_solve(stack, list(tiles_xy), [i_out] * n_vr, pol,
                            [i_total_a / len(pol)] * len(pol), span_mm=DIE_MM, T_c=T_c,
                            n=grid_n, src_size_mm=tile_side_mm, load_size_mm=DIE_MM / NPOL,
                            ground_xy=pol[len(pol) // 2], ground_size_mm=DIE_MM / NPOL)
    p_rdl = sol["p_loop_w"]

    p_long = 0.0
    if lateral_route_mm:
        rs = stack.r_sheet_net("vdd", T_c)
        p_long = 2.0 * i_total_a ** 2 * rs * (lateral_route_mm / DIE_MM)
        p_rdl += p_long

    # DEFECT #30, fixed in Phase 0G and made structural in Phase 0H.
    # Each vertical tier is PER_REGULATOR; the RDL solve is SYSTEM. They are converted
    # explicitly and then summed through total(), which raises if any term is still
    # per-regulator. The guard is negative-tested in tests/phase0h/test_scope.py.
    q_tiers = [r.p_system(n_vr) for r in rows]
    q_rdl = watts_system(p_rdl, tier="rdl")
    q_pdn = total(q_tiers + [q_rdl], Scope.SYSTEM)
    by = {q.tier: q.value for q in q_tiers}
    by["rdl"] = q_rdl.value
    p_pdn = q_pdn.value
    tsv = next((r for r in rows if r.tier == "tsv"), None)
    return {
        "architecture": arch, "tsv_rail": A["tsv_rail"], "h_sub_mm": h_sub_mm,
        "n_vr": n_vr, "tile_side_mm": tile_side_mm, "A_hvr_mm2": tile_fp * n_vr,
        "policy": policy, "j_cu": j_cu, "j_solder": j_solder, "stack": stack.name,
        "I_out_per_vr_a": rc["I_out_a"], "I_in_per_vr_a": rc["I_in_a"],
        "I_tsv_a": cur[A["tsv_rail"]], "feasible": not infeas, "infeasible": infeas,
        "P_by_tier_w": by, "P_by_tier_per_vr_w": {r.tier: r.p_w for r in rows},
        "P_by_tier_scope": "SYSTEM", "P_by_tier_per_vr_scope": "PER_REGULATOR",
        "P_pdn_w": p_pdn, "P_conv_w": p_conv_total_w,
        "P_elec_total_w": p_pdn + p_conv_total_w, "p_rdl_long_w": p_long,
        "rdl": {k: sol[k] for k in ("p_loop_w", "p_vdd_w", "p_gnd_w",
                                    "r_sheet_vdd_ohm_sq", "symmetric_return_would_give_w")},
        "tiers": [r.__dict__ for r in rows],
        "n_tsv_req": tsv.n_req if tsv else None,
        "n_tsv_alloc": tsv.n_alloc if tsv else None,
        "n_tsv_avail": tsv.n_avail if tsv else None,
        "i_per_tsv_ma": tsv.i_per_via_a * 1e3 if tsv else None,
        "crowding": crowding,
    }
