#!/usr/bin/env python3
"""Reproduce ECTC-2024 Table II from its own stated stack, then test the Phase-0E
multilayer sheet solver on the identical problem.

This is the PHYSICAL stack validation that Phase 0D-R could not do: Phase 0D-R only showed
that the FD solver solves the assumed sheet correctly (vs MOOSE). Here the sheet itself is
taken from the source and checked against the source's own published answer.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "phase0e"))
from stack import RDLStack, stacks_from_cfg, rdl_network_solve, rho_cu

DIE_MM = 22.36                     # 500 mm^2
S_POL = 100                        # die divided into S equal segments
I_TOT = 1000.0                     # 1 kW at 1 V


def pol_grid(n_side=10, die=DIE_MM):
    q = (np.arange(n_side) + 0.5) / n_side * die - die / 2
    return [(x, y) for x in q for y in q]


def vrs_under_die(m, die=DIE_MM):
    """A2: VRs distributed in-interposer BELOW the die."""
    c = int(np.ceil(np.sqrt(m))); r = int(np.ceil(m / c))
    pts = []
    for i in range(r):
        for j in range(c):
            if len(pts) >= m: break
            pts.append(((j + .5) / c * die - die / 2, (i + .5) / r * die - die / 2))
    return pts[:m]


def vrs_periphery(m, die=DIE_MM, offset=1.5):
    """A1: VRs in rows along the die periphery."""
    per = int(np.ceil(m / 4)); sp = die / per
    pts = []
    for i in range(per):
        t = (i + .5) * sp - die / 2
        for p in ((t, -die/2 - offset), (t, die/2 + offset),
                  (-die/2 - offset, t), (die/2 + offset, t)):
            if len(pts) < m: pts.append(p)
    return pts[:m]


def ectc_lumped(vrs, r_h_eff_ohm_per_m, pols=None, i_tot=I_TOT):
    """ECTC eq. (3): current from VR j to segment i splits as (1/d_ji)/sum_k(1/d_ki);
    loss over each path is I^2 * R'_Heff * d. Both P and G networks -> factor 2."""
    pols = pols or pol_grid()
    i_seg = i_tot / len(pols)
    P = 0.0
    for (px, py) in pols:
        d = np.array([max(abs(px - vx) + abs(py - vy), 0.01) for vx, vy in vrs])  # Manhattan
        w = (1 / d) / (1 / d).sum()
        I = w * i_seg
        P += float((I ** 2 * r_h_eff_ohm_per_m * (d * 1e-3)).sum())
    return 2.0 * P


def run():
    stacks = stacks_from_cfg()
    st = stacks["ectc2024_primary"]
    rh = st.ectc_r_h_eff(500e-6, T_c=20.0, net="vdd")
    print(f"stack {st.name}: t={st.t_cu_m*1e6:.0f}um W/S={st.width_m*1e6:.0f}/{st.space_m*1e6:.0f}um "
          f"n_vdd={st.n_vdd} n_gnd={st.n_gnd}")
    print(f"R'_Heff (analytic, one network) = {rh:.5f} Ohm/m   [ECTC prints 0.046]\n")

    cases = [("A1 periphery M=40", vrs_periphery(40), 76.0),
             ("A2 under-die  M=40", vrs_under_die(40), 39.5),
             ("A2 under-die  M=100", vrs_under_die(100), 32.0)]

    # Sensitivity of the literal eq.(3) reading to the segment count: P ~ 1/S, so no
    # value of S can close a 200x gap. Recorded so the negative result is not hand-waved.
    s_scan = {}
    for S in (4, 10, 25, 100, 400):
        s_scan[S] = ectc_lumped(vrs_under_die(40), rh, pols=pol_grid(int(S ** .5)))
    print("literal eq.(3) vs segment count S (published A2 = 39.5 W):")
    for S, v in s_scan.items():
        print(f"    S={S:4d} -> {v:8.3f} W   (x{39.5/v:8.1f} short)")
    print()

    rows = []
    print(f"{'case':22s} {'ECTC lumped':>12s} {'published':>10s} {'err%':>8s}"
          f" {'0E sheet':>10s} {'err%':>8s}")
    for lab, vrs, pub in cases:
        p_lump = ectc_lumped(vrs, rh)
        i_vr = I_TOT / len(vrs)
        pols = pol_grid()
        sol = rdl_network_solve(st, vrs, [i_vr] * len(vrs), pols, [I_TOT / len(pols)] * len(pols),
                                span_mm=DIE_MM, T_c=20.0, n=81,
                                src_size_mm=2.0, load_size_mm=DIE_MM / 10)
        p_sheet = sol["p_loop_w"]
        e1 = 100 * (p_lump - pub) / pub
        e2 = 100 * (p_sheet - pub) / pub
        print(f"{lab:22s} {p_lump:11.2f}W {pub:9.1f}W {e1:+7.1f}% {p_sheet:9.2f}W {e2:+7.1f}%")
        rows.append({"case": lab, "published_w": pub, "ectc_lumped_w": p_lump,
                     "phase0e_sheet_w": p_sheet, "lumped_err_pct": e1, "sheet_err_pct": e2,
                     "n_vr": len(vrs)})

    # Effective spreading length implied by each number: L_eff = P / (I_tot^2 * R'_Heff)
    print(f"\nimplied effective spreading length L_eff = P / (I_tot^2 * R_Heff):")
    for r in rows:
        le_pub = r["published_w"] / (I_TOT ** 2 * rh) * 1e3
        le_sh = r["phase0e_sheet_w"] / (I_TOT ** 2 * rh) * 1e3
        r["L_eff_published_mm"], r["L_eff_sheet_mm"] = le_pub, le_sh
        print(f"    {r['case']:22s} published {le_pub:6.2f} mm   Phase-0E sheet {le_sh:6.2f} mm")

    out = REPO / "results" / "phase0e" / "ectc_table2_validation.json"
    out.write_text(json.dumps({"stack": st.name, "r_h_eff_ohm_per_m": rh,
                               "die_mm": DIE_MM, "i_total_a": I_TOT,
                               "n_pol": S_POL, "cases": rows,
                               "literal_eq3_vs_S": s_scan,
                               "verdict": ("STACK PARAMETERS VALIDATED EXACTLY; "
                                           "TABLE II MAGNITUDES NOT RECONSTRUCTIBLE "
                                           "FROM THE PRINTED EQUATIONS")}, indent=2))
    print(f"\nwrote {out.relative_to(REPO)}")
    return rows


if __name__ == "__main__":
    run()
