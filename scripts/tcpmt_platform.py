"""Platform-inclusive loss: package-internal loss + a physical 48-V feed + cooling overhead
(TCPMT review MC16).

Feeds (loop resistance from the common board 48-V node to the converter input terminals,
including the distribution to the 49 cells):
  Z1   inside the package-internal boundary (package 48-V network solved in the ledger)
  Z2   (i)  BGA-fed: 48 V through the BGA ring and a substrate 48-V RDL, SOLVED by the
            production voltage-fed network (research/final_closure/etm_Z2BF_HV_S0_h1.1_r21.json)
       (ii) direct flex bridge across the board-opening clearance onto a distribution plane
            pair under the converter (declared geometry below; an estimate)
  Z3   the board's own 48-V plane pair under the package, reached through the board
       (declared geometry below; an estimate)
Sheet estimates: a plane fed along one edge and drawn uniformly over a square of side L
has R = R_s / 3 per conductor (supply and return in series); R_s = rho(T)/t.
Cooling overhead: shaft pumping power of every plate (cooling A: one plate, B: two), at the
middle of the declared pump-efficiency band, with the band reported.

    python tcpmt_platform.py   -> research/tcpmt_revision/platform_inclusive.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FC = R / "research" / "final_closure"
SENS = FC / "sensitivity"
TR = R / "research" / "tcpmt_revision"
OUT = TR / "platform_inclusive.json"
RHO_CU_20, ALPHA_CU = 1.72e-8, 3.93e-3
T_FEED_C = 60.0                 # declared copper temperature of the feed conductors
V_IN, P_LOAD = 48.0, 1000.0
K_SCEN = {"S0": 1.0, "S1": 4.0}


def rho(t_c):
    return RHO_CU_20 * (1 + ALPHA_CU * (t_c - 20.0))


def sheet_square(t_cu_m, t_c=T_FEED_C):
    """Edge-fed square plane, uniform sink: R = R_s/3 per conductor."""
    return rho(t_c) / t_cu_m / 3.0


def feeds():
    z2bf = json.loads((FC / "etm_Z2BF_HV_S0_h1.1_r21.json").read_text())
    hv = {r["term"]: r for r in z2bf["ledger_rows"]}
    r_bf = sum(hv[k]["R_ohm"] for k in ("P_pkg_RDL_HV_supply", "P_BGA_supply",
                                        "P_pkg_RDL_HV_return", "P_BGA_return"))
    # (ii) flex bridge: two 70-um copper conductors, 20 mm wide, 15 mm long, plus a
    # 70-um distribution plane pair under the 21.36-mm cell grid
    t, w, l = 70e-6, 20e-3, 15e-3
    r_flex = 2 * rho(T_FEED_C) * l / (w * t) + 2 * sheet_square(t)
    # Z3: the board's 48-V plane pair (two 70-um planes) under the package; the vias to the
    # converter pads (25 per cell) are negligible against the planes
    r_z3 = 2 * sheet_square(t)
    return {"Z2_bga_fed": {"R_ohm": r_bf, "kind": "solved (voltage-fed package network)",
                           "P_coupled_A_W": z2bf["P_loss_w"],
                           "geometry": "BGA ring + substrate 48-V RDL (production network)"},
            "Z2_flex": {"R_ohm": r_flex, "kind": "estimate",
                        "geometry": "2 x 70 um Cu, 20 mm x 15 mm bridge + 70-um plane pair "
                                    f"under the cell grid, copper at {T_FEED_C:.0f} C"},
            "Z3_board_planes": {"R_ohm": r_z3, "kind": "estimate",
                                "geometry": f"70-um 48-V plane pair under the package, copper at "
                                            f"{T_FEED_C:.0f} C"}}


def solve_feed(p_int, r, k):
    """Eq. (1): P = P_int + (k I)^2 R, 48 V I = P_load + P, by fixed point."""
    i = (P_LOAD + p_int) / V_IN
    for _ in range(100):
        p = p_int + (k * i) ** 2 * r
        i_new = (P_LOAD + p) / V_IN
        if abs(i_new - i) < 1e-12:
            break
        i = i_new
    return p - p_int, i


def main():
    cool = json.loads((TR / "cooling_spec.json").read_text())
    hy = cool["plate"]["hydraulics"]
    pump = {"0.75": hy["P_shaft_eta_0.75_W"], "0.55": hy["P_shaft_eta_0.55_W"],
            "0.35": hy["P_shaft_eta_0.35_W"], "hyd": hy["P_hydraulic_W"]}
    F = feeds()
    cases = {"A": {"Z1": FC / "etm_Z1_HV_S0_h1.1_r21.json",
                   "Z2": FC / "etm_Z2_HV_S0_h1.1_r21.json",
                   "Z3": SENS / "etm_Z3_HV_S0__z3_top_only.json"},
             "B": {"Z1": SENS / "etm_Z1_HV_S0__z1_bottom_plate_tim.json",
                   "Z2": SENS / "etm_Z2_HV_S0__z2_cooled_tim.json",
                   "Z3": SENS / "etm_Z3_HV_S0__z3_plate_tim.json"}}
    # Z3 with the coupled land-side term, when the study exists (agent z3land)
    z3l = TR / "z3_land_coupled.json"
    z3_source = "lower bound (land side not in the ledger)"
    if z3l.is_file():
        d = json.loads(z3l.read_text())
        pick = d.get("recommended_case_files") or {}
        for t in ("A", "B"):
            if pick.get(t) and (SENS / pick[t]).is_file():
                cases[t]["Z3"] = SENS / pick[t]
                z3_source = d.get("recommended_label", "coupled land side")
    feed_of = {"Z1": None, "Z2": "Z2_bga_fed", "Z3": "Z3_board_planes"}
    out = {"feeds": F, "pump_shaft_W_per_plate": pump, "z3_source": z3_source, "tiers": {},
           "macros": {}}
    for t, row in cases.items():
        n = 1 if t == "A" else 2
        out["tiers"][t] = {}
        for a, f in row.items():
            c = json.loads(Path(f).read_text())
            p_int = c["P_loss_w"]
            r = F[feed_of[a]]["R_ohm"] if feed_of[a] else 0.0
            pf, i = solve_feed(p_int, r, K_SCEN["S0"])
            pf1, _ = solve_feed(p_int, r, K_SCEN["S1"])
            rec = {"case": Path(f).name, "P_int_W": p_int, "feed": feed_of[a],
                   "R_feed_mohm": 1e3 * r, "P_feed_W": pf, "P_feed_S1_W": pf1,
                   "I_in_A": i, "plates": n,
                   "P_pump_shaft_W": n * pump["0.55"],
                   "P_pump_band_W": [n * pump["0.75"], n * pump["0.35"]],
                   "P_pump_hydraulic_W": n * pump["hyd"]}
            rec["P_platform_W"] = p_int + pf + rec["P_pump_shaft_W"]
            rec["P_platform_no_pump_W"] = p_int + pf
            out["tiers"][t][a] = rec
    m = out["macros"]
    m["FeedRbgaZtwo"] = f"{1e3 * F['Z2_bga_fed']['R_ohm']:.2f}"
    m["FeedRflexZtwo"] = f"{1e3 * F['Z2_flex']['R_ohm']:.2f}"
    m["FeedRZthree"] = f"{1e3 * F['Z3_board_planes']['R_ohm']:.2f}"
    m["FeedPbgaZtwo"] = f"{out['tiers']['A']['Z2']['P_feed_W']:.2f}"
    m["FeedPbgaZtwoSone"] = f"{out['tiers']['A']['Z2']['P_feed_S1_W']:.1f}"
    m["FeedPZthree"] = f"{out['tiers']['B']['Z3']['P_feed_W']:.2f}"
    m["FeedPZthreeSone"] = f"{out['tiers']['B']['Z3']['P_feed_S1_W']:.1f}"
    for t in ("A", "B"):
        for a, tag in (("Z1", "Zone"), ("Z2", "Ztwo"), ("Z3", "Zthree")):
            rec = out["tiers"][t][a]
            m[f"Plat{t}{tag}"] = f"{rec['P_platform_W']:.1f}"
            m[f"PlatNoPump{t}{tag}"] = f"{rec['P_platform_no_pump_W']:.1f}"
    m["PumpShaftPlate"] = f"{pump['0.55']:.0f}"
    OUT.write_text(json.dumps(out, indent=1, default=float))
    for t, row in out["tiers"].items():
        for a, rec in row.items():
            print(t, a, f"P_int={rec['P_int_W']:.1f} feed={rec['R_feed_mohm']:.2f} mOhm "
                        f"P_feed={rec['P_feed_W']:.2f} (S1 {rec['P_feed_S1_W']:.1f}) "
                        f"pump={rec['P_pump_shaft_W']:.0f} platform={rec['P_platform_W']:.1f}")
    return out


if __name__ == "__main__":
    main()
