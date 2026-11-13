"""Direct-feed crossover (Z2_DIRECT_FEED_ARCHITECTURE.md section 5).

The primary Z2 takes its 48 V through a dedicated external connection whose loop resistance
R_Z2_direct_feed_loop is NOT sourced: ARM US20260059645A1 names connector types only. So no
value is assumed. The external loop is swept, and the crossover where the platform-inclusive
Z2 loss equals Z1's is solved exactly. That gives a design requirement instead of an
invented connector.

For each named scenario:
  P_Z2(R) = P_int,Z2(I) + (k I)^2 R,   I = (P_load + P_Z2(R)) / 48 V   (self-consistent)
where P_int,Z2(I) is the PACKAGE-INTERNAL Z2 ledger at the converged electrothermal state
(temperatures of the production case), k = HV RMS/avg of the scenario. The reference is Z1's
converged package-internal loss, whose boundary is the BGA pads on the PCB. Board-level
48 V distribution upstream of that common node is excluded from both architectures.

The feed loss deposits no heat in the package here; the heat-location question is the
class-B variant `feed_heat_at_crossover` (final_closure_sensitivity.py).

    python final_closure_direct_feed.py        -> research/final_closure/direct_feed_crossover.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_ledger as FL                                   # noqa: E402
import final_closure_physical_etm as E                              # noqa: E402
import final_closure_results as FR                                  # noqa: E402

OUT = R / "research" / "final_closure" / "direct_feed_crossover.json"
SPEC = json.loads((R / "research/final_closure/z2_direct_feed_architecture.json")
                  .read_text())["direct_feed"]


def converged_temps(case):
    return E.temps_from_history(case["et_history"][-1])


def platform_point(scen, temps, r_ohm, tol_w=1e-9, max_iter=200, arch="Z2"):
    """Self-consistent platform-inclusive Z2 state at one external loop resistance.

    Power balance at the platform: V I = P_load + P_int(I) + (k I)^2 R. For a given P_int
    this is a quadratic in I whose LOWER root is the physical operating point; the outer
    loop updates P_int(I). Above R_max = V^2 / (4 k^2 (P_load + P_int)) the discriminant is
    negative: the feed cannot deliver the load at any current, and the point is returned
    as infeasible instead of iterating to overflow."""
    k, v = FL.SCEN_RATIO[scen], FL.V_IN
    i = (FL.P_LOAD_W + 140.0) / v
    a = k * k * r_ohm
    for _ in range(max_iter):
        L = FL.ledger(arch, scen, temps, i)
        c = FL.P_LOAD_W + L["P_loss_w"]
        if a == 0.0:
            i_new = c / v
        else:
            disc = v * v - 4.0 * a * c
            if disc < 0.0:
                return {"R_mohm": r_ohm * 1e3, "feasible": False,
                        "R_max_mohm": v * v / (4.0 * a / r_ohm * c) * 1e3,
                        "I_48_avg_a": None, "I_48_rms_a": None, "P_internal_w": None,
                        "P_feed_w": None, "P_total_w": None, "efficiency": None,
                        "energy_residual_w": None}
            i_new = (v - math.sqrt(disc)) / (2.0 * a)
        if abs(i_new - i) * v < tol_w:
            i = i_new
            break
        i = i_new
    L = FL.ledger(arch, scen, temps, i)
    p_feed = (k * i) ** 2 * r_ohm
    p_tot = L["P_loss_w"] + p_feed
    return {"R_mohm": r_ohm * 1e3, "feasible": True, "I_48_avg_a": i, "I_48_rms_a": k * i,
            "P_internal_w": L["P_loss_w"], "P_feed_w": p_feed, "P_total_w": p_tot,
            "efficiency": FL.P_LOAD_W / (FL.P_LOAD_W + p_tot),
            "energy_residual_w": v * i - FL.P_LOAD_W - p_tot}


def crossover(scen, temps, p_ref, lo=1e-8, hi=1.0, arch="Z2"):
    """R* with P_Z2(R*) = P_ref, by bisection on log R (P_Z2 is monotone in R). An
    infeasible point (the feed cannot deliver the load) counts as Z2 behind."""
    def f(r):
        p = platform_point(scen, temps, r, arch=arch)
        return float("inf") if not p["feasible"] else p["P_total_w"] - p_ref
    if f(lo) >= 0:
        return 0.0          # Z2 is not ahead even with a lossless feed
    if f(hi) < 0:
        return None         # still ahead at 1 Ohm: no crossover in range
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi / lo < 1 + 1e-10:
            break
    return math.sqrt(lo * hi)


def attach_density_rstar(scen, p_z1):
    """R* under the published attach densities (geom.vr_attach_density): each variant's own
    converged temperatures and its real-lattice attach ledger (final_closure_vr_attach.
    ledger_spec). The attach is Z2-only, so the Z1 reference is the production one."""
    import final_closure_vr_attach as VA
    out, orig = {}, FL.attach_spec
    try:
        for name in ("dense", "sparse"):
            f = R / "research/final_closure/sensitivity" / f"etm_Z2_{scen}__attach_{name}.json"
            if not f.exists():
                continue
            c = json.loads(f.read_text())
            sp = dict(orig())
            sp.update(VA.ledger_spec(VA.CASES[name]))
            FL.attach_spec = lambda sp=sp: sp
            temps = converged_temps(c)
            base = platform_point(scen, temps, 0.0)
            r = crossover(scen, temps, p_z1)
            out[name] = {"source": f.relative_to(R).as_posix(),
                         "P_Z2_internal_w": c["P_loss_w"],
                         "P_Z2_internal_recomputed_w": base["P_total_w"],
                         "advantage_at_zero_feed_w": p_z1 - c["P_loss_w"],
                         "advantage_at_zero_feed_recomputed_w": p_z1 - base["P_total_w"],
                         "R_star_mohm": None if r is None else r * 1e3}
    finally:
        FL.attach_spec = orig
    return out


def main():
    rs = np.logspace(math.log10(SPEC["sweep_mohm"][0]), math.log10(SPEC["sweep_mohm"][1]),
                     SPEC["sweep_points"]) * 1e-3
    out = {"parameter": SPEC["parameter"], "definition": SPEC["definition"],
           "assumed_value": None, "sweep_mohm": SPEC["sweep_mohm"],
           "boundary": ("Z2 package-internal ledger from the HVR input terminals; Z1 from the "
                        "BGA pads on the PCB; board-level 48 V upstream of the common node "
                        "excluded from both"),
           "heat_location": "outside the package (see class-B feed_heat_at_crossover)",
           "scenarios": {}}
    for scen in FL.SCENARIOS:
        f1, f2 = (E.case_path(a, scen) for a in ("Z1", "Z2"))
        if not (f1.exists() and f2.exists()):
            continue
        c1, c2 = json.loads(f1.read_text()), json.loads(f2.read_text())
        if c2.get("architecture_variant") != "Z2_DIRECT_FEED":
            raise RuntimeError(f"{f2.name} is not the direct-fed Z2")
        for f, c in ((f1, c1), (f2, c2)):
            if not E.current_lineage(c):
                raise RuntimeError(f"{f.name} is not of the corrected lineage")
        temps = converged_temps(c2)
        p_z1 = c1["P_loss_w"]
        base = platform_point(scen, temps, 0.0)
        r_star = crossover(scen, temps, p_z1)
        if "mechanics" not in c1:
            raise RuntimeError(f"{f1.name} has no joint search: admissibility unknown")
        t_joint = FR.hottest_joint_C(c1["mechanics"])
        z1_inadmissible = t_joint >= FR.SAC305_SOLIDUS_C
        at_star = platform_point(scen, temps, r_star) if r_star else None
        out["scenarios"][scen] = {
            # package-internal losses (each architecture inside its own boundary)
            "P_Z1_w": p_z1, "P_Z1_internal_w": p_z1,
            "efficiency_Z1": FL.P_LOAD_W / (FL.P_LOAD_W + p_z1),
            "P_Z2_internal_w": c2["P_loss_w"],
            "P_Z2_internal_recomputed_w": base["P_total_w"],
            "efficiency_Z2_zero_feed": base["efficiency"],
            # the package-internal gap of the two converged cases (the numbers every table
            # shows); R* is solved on the self-consistent re-solve at zero feed, which
            # differs from the converged case by the E-T tolerance only
            "advantage_at_zero_feed_w": p_z1 - c2["P_loss_w"],
            "advantage_at_zero_feed_recomputed_w": p_z1 - base["P_total_w"],
            "R_star_mohm": None if r_star is None else r_star * 1e3,
            "P_feed_at_R_star_w": None if not at_star else at_star["P_feed_w"],
            "efficiency_Z2_at_R_star": None if not at_star else at_star["efficiency"],
            "I_48_rms_a": base["I_48_rms_a"], "scen_rms_ratio": FL.SCEN_RATIO[scen],
            # feed loss per milliohm of external loop at the zero-feed operating point
            "P_feed_per_mohm_w": base["I_48_rms_a"] ** 2 * 1e-3,
            "Z1_hottest_joint_C": t_joint,
            "Z1_operating_point_inadmissible": z1_inadmissible,
            "requirement": (None if r_star is None or z1_inadmissible else
                            f"none: in {scen.replace('_', '-')} Z2 is not ahead even with a "
                            "lossless feed, so every milliohm of feed only adds loss"
                            if r_star == 0.0 else
                            f"for Z2 to keep its electrical advantage in {scen.replace('_', '-')}, "
                            f"R_Z2_direct_feed_loop < {r_star * 1e3:.3g} mOhm"),
            "temps_C": temps,
            "attach_density_R_star": (attach_density_rstar(scen, p_z1)
                                      if not z1_inadmissible else {}),
            "sweep": [platform_point(scen, temps, r) for r in rs]}
        s = out["scenarios"][scen]
        print(f"{scen}: P_Z1 {p_z1:.3f} W, P_Z2(0) {base['P_total_w']:.3f} W, "
              f"R* = {s['R_star_mohm']} mOhm, inadmissible Z1: {z1_inadmissible}")
    # TCPMT revision: every directly fed backside integration against Z1, same definitions
    # (Z2 repeats the block above; Z3 when its production cases exist)
    out["architectures"] = {}
    for b in ("Z2", "Z3"):
        blk = {}
        for scen in FL.SCENARIOS:
            f1, fb = E.case_path("Z1", scen), E.case_path(b, scen)
            if not (f1.exists() and fb.exists()):
                continue
            c1, cb = json.loads(f1.read_text()), json.loads(fb.read_text())
            if "mechanics" not in c1:
                continue
            temps = converged_temps(cb)
            p_z1 = c1["P_loss_w"]
            base = platform_point(scen, temps, 0.0, arch=b)
            r_star = crossover(scen, temps, p_z1, arch=b)
            z1_inad = FR.hottest_joint_C(c1["mechanics"]) >= FR.SAC305_SOLIDUS_C
            at = platform_point(scen, temps, r_star, arch=b) if r_star else None
            blk[scen] = {"P_Z1_w": p_z1, f"P_{b}_internal_w": cb["P_loss_w"],
                         "P_internal_recomputed_w": base["P_total_w"],
                         "advantage_at_zero_feed_w": p_z1 - cb["P_loss_w"],
                         "R_star_mohm": None if r_star is None else r_star * 1e3,
                         "efficiency_at_R_star": None if not at else at["efficiency"],
                         "I_48_rms_a": base["I_48_rms_a"],
                         "P_feed_per_mohm_w": base["I_48_rms_a"] ** 2 * 1e-3,
                         "Z1_operating_point_inadmissible": z1_inad,
                         "sweep": [platform_point(scen, temps, r, arch=b) for r in rs]}
            print(f"{b} {scen}: P_Z1 {p_z1:.3f} W, P_{b}(0) {base['P_total_w']:.3f} W, "
                  f"R* = {blk[scen]['R_star_mohm']} mOhm")
        if blk:
            out["architectures"][b] = {"scenarios": blk}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
