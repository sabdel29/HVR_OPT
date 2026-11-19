"""Platform-inclusive loss: package-internal loss + a physical 48-V feed + cooling overhead
(TCPMT review MC16; review round 2: production state, documented feeds).

Feeds (loop resistance from the common board 48-V node to the converter input terminals,
including the distribution to the cells):
  Z1   inside the package-internal boundary (package 48-V network solved in the ledger)
  Z2   THE FEED OF TABLE V: the BGA-RING feed -- 48 V through n balls per rail of the ring of
       ball sites that survives around the 2.4-mm board opening (528 of the 1369 lattice
       sites), and a substrate 48-V RDL sheet to the cells' input pads, SOLVED by the production
       voltage-fed network (package_network.json; the BGA-fed control Z2BF). Those 2n balls DO
       carry power: they are outside the package-internal boundary of Z2 but they are BGA power
       sites of the platform (Table V counts them).
       ALTERNATIVE (declared estimate, not in Table V): a flex bridge across the board-opening
       clearance onto a distribution plane pair under the converter, 0 balls (feed_design).
  Z3   the board's own 48-V plane pair under the package, reached through the board (declared
       geometry; an estimate, not in the Z3 design record)
Sheet estimates: a plane fed along one edge and drawn uniformly over a square of side L has
R = R_s / 3 per conductor (supply and return in series); R_s = rho(T)/t.
Feed current: the production state (implemented decoupling) carries k_eq x the average current
in the feed, on the declared assumption that each backside integration interleaves its cells
and places the same ring of input capacitors at its feed; S0 (k = 1) and S1 (k = 4) are the
references. Cooling overhead: shaft pumping power of every plate (cooling A: one plate, B: two),
at the middle of the declared pump-efficiency band, with the band reported; each plate at its
own flow (cooling B's bottom plate sized to the top plate's coolant rise) when the case file or
the cooling specification records it, else every plate at the full flow (pump_basis).

    python tcpmt_platform.py   -> research/tcpmt_revision/platform_inclusive.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import tcpmt_cases as TC                                            # noqa: E402

FC = R / "research" / "final_closure"
SENS = FC / "sensitivity"
TR = R / "research" / "tcpmt_revision"
OUT = TR / "platform_inclusive.json"
RHO_CU_20, ALPHA_CU = 1.72e-8, 3.93e-3
T_FEED_C = 60.0                 # declared copper temperature of the feed conductors
V_IN, P_LOAD = 48.0, 1000.0
I_BALL_RULE_A = 1.5
GRID_SIDE_MM = 21.36            # the cell grid's bounding box (the region a plane pair feeds)
FLEX = {"t_um": 70.0, "w_mm": 20.0, "l_mm": 15.0}
PLANE_T_UM = 70.0


def k_scen():
    d = json.loads((TR / "input_decoupling.json").read_text())
    return {"SDEC": float(d["summary"]["recommended"]["k_eq"]), "S0": 1.0, "S1": 4.0}


def rho(t_c):
    return RHO_CU_20 * (1 + ALPHA_CU * (t_c - 20.0))


def sheet_square(t_cu_m, t_c=T_FEED_C):
    """Edge-fed square plane, uniform sink: R = R_s/3 per conductor."""
    return rho(t_c) / t_cu_m / 3.0


def ring_feed():
    """The Z2 BGA-ring feed at the count of the package network in force, and the count the
    production waveform needs (bga_count_production.json, when the re-closure has run)."""
    pn = json.loads((FC / "package_network.json").read_text())
    n = int(pn["matched_count"])
    conv = pn["convergence"]
    frac = max(conv["Z2_supply"]["final"]["i_ball_max_a"],
               conv["Z2_return"]["final"]["i_ball_max_a"])
    drop = max(conv["Z2_supply"]["final"]["max_cell_drop_v"],
               conv["Z2_return"]["final"]["max_cell_drop_v"])
    lp = pn["loop"]["Z2"]
    out = {"n_per_rail": n, "sites": 2 * n, "lattice_sites": 528,
           "ball": "0.4-mm SAC305 at 0.8-mm pitch, 300 um (Krishnakumar 2026 Table III)",
           "placement": "nearest-symmetric selection on the ring of sites around the 23.36-mm "
                        "board opening (pkg_rdl_network, cutout 23.36 mm)",
           "sheet": "substrate 48-V RDL (production voltage-fed FV network, traced 0.2-mm VIN "
                    "pads)",
           "R_supply_20C_ohm": lp["r_supply_ohm"], "R_return_20C_ohm": lp["r_return_ohm"],
           "R_loop_20C_ohm": lp["r_loop_ohm"], "peak_fraction": frac,
           "peak_fraction_source": "package_network.json (converged)",
           "max_cell_drop_V_per_A": drop, "match_scenario": pn["meta"].get("match_scenario",
                                                                          "HV_S0")}
    prod = TR.parent / "final_closure" / "bga_count_production.json"
    if prod.is_file():
        pc = json.loads(prod.read_text())
        cl = pc["closure"].get("Z2__HV_SDEC") or {}
        out["production_requirement"] = {
            "n_min_per_rail": cl.get("n_min"), "status": cl.get("status"),
            "matched_count": pc.get("matched_count"),
            "peak_at_n_min_A": cl.get("peak_at_n_min_A")}
    return out


def feeds():
    z2bf = json.loads((FC / "etm_Z2BF_HV_S0_h1.1_r21.json").read_text())
    hv = {r["term"]: r for r in z2bf["ledger_rows"]}
    r_bf = sum(hv[k]["R_ohm"] for k in ("P_pkg_RDL_HV_supply", "P_BGA_supply",
                                        "P_pkg_RDL_HV_return", "P_BGA_return"))
    t, w, l = FLEX["t_um"] * 1e-6, FLEX["w_mm"] * 1e-3, FLEX["l_mm"] * 1e-3
    r_flex = 2 * rho(T_FEED_C) * l / (w * t) + 2 * sheet_square(t)
    r_z3 = 2 * sheet_square(PLANE_T_UM * 1e-6)
    return {"Z2_bga_fed": {"R_ohm": r_bf, "kind": "solved (voltage-fed package network)",
                           "P_coupled_A_W": z2bf["P_loss_w"],
                           "geometry": "BGA ring + substrate 48-V RDL (production network)"},
            "Z2_flex": {"R_ohm": r_flex, "kind": "estimate (declared geometry; not in Table V)",
                        "geometry": f"2 x {FLEX['t_um']:.0f} um Cu, {FLEX['w_mm']:.0f} mm x "
                                    f"{FLEX['l_mm']:.0f} mm bridge + {PLANE_T_UM:.0f}-um plane pair "
                                    f"under the cell grid, copper at {T_FEED_C:.0f} C"},
            "Z3_board_planes": {"R_ohm": r_z3, "kind": "estimate (declared geometry)",
                                "geometry": f"{PLANE_T_UM:.0f}-um 48-V plane pair under the "
                                            f"package, copper at {T_FEED_C:.0f} C"}}


def feed_design(F, i_avg):
    """Geometry and current capacity of every feed, at S0, the production state and S1."""
    ks = k_scen()
    rf = ring_feed()
    cur = {s: k * i_avg for s, k in ks.items()}
    ring = dict(rf)
    ring.update({"R_loop_feed_ohm": F["Z2_bga_fed"]["R_ohm"],
                 "I_rms_A": cur,
                 "I_ball_peak_A": {s: rf["peak_fraction"] * i for s, i in cur.items()},
                 "rule_A": I_BALL_RULE_A,
                 "passes_rule": {s: rf["peak_fraction"] * i <= I_BALL_RULE_A
                                 for s, i in cur.items()},
                 "max_sheet_drop_mV": {s: 1e3 * rf["max_cell_drop_V_per_A"] * i
                                       for s, i in cur.items()},
                 "in_table_V": True,
                 "boundary": "outside the package-internal boundary of Z2; 2n BGA power sites "
                             "of the platform"})
    t_m = PLANE_T_UM * 1e-6
    w_m = GRID_SIDE_MM * 1e-3
    plane = {"conductors": "two Cu planes (48 V and its return), one per conductor",
             "t_um": PLANE_T_UM, "occupancy": 1.0, "region": f"{GRID_SIDE_MM} mm square under "
             "the cell grid, fed along one edge, drawn uniformly (R = R_s/3 per conductor)",
             "status": "DECLARED (not in the Z3 design record)",
             "R_loop_ohm": F["Z3_board_planes"]["R_ohm"], "I_rms_A": cur,
             "edge_current_density_A_mm2": {s: i / (w_m * t_m) * 1e-6 for s, i in cur.items()},
             "edge_current_per_width_A_mm": {s: i / GRID_SIDE_MM for s, i in cur.items()},
             "static_drop_mV": 1e3 * i_avg * F["Z3_board_planes"]["R_ohm"],
             "sites": 0, "in_table_V": True}
    tf, wf = FLEX["t_um"] * 1e-6, FLEX["w_mm"] * 1e-3
    flex = {"geometry": F["Z2_flex"]["geometry"], "R_loop_ohm": F["Z2_flex"]["R_ohm"],
            "status": "DECLARED ESTIMATE: no connector, bend or attach resistance; not a design "
                      "record and not used in Table V (Table V uses the BGA ring)",
            "I_rms_A": cur,
            "bridge_current_density_A_mm2": {s: i / (wf * tf) * 1e-6 for s, i in cur.items()},
            "sites": 0, "in_table_V": False,
            "recommendation": "describe it with this geometry and status where the text quotes "
                              "0.6 mOhm, or drop the quote (the Table V feed is the BGA ring)"}
    return {"Z2_bga_ring": ring, "Z3_plane_pair": plane, "Z2_flex_alternative": flex}


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
    ks = k_scen()
    feed_of = {"Z1": None, "Z2": "Z2_bga_fed", "Z3": "Z3_board_planes"}
    out = {"feeds": F, "pump_shaft_W_per_plate": pump, "k_feed": ks,
           "production_state": TC.PRODUCTION_STATE, "states": {}, "macros": {}}
    i_ref = None
    for st in ("SDEC", "S0"):
        tiers = {}
        for t in TC.TIERS:
            n = 1 if t == "A" else 2
            tiers[t] = {}
            for a in TC.ARCHS:
                p, c = TC.load(st, t, a)
                if c is None:
                    tiers[t][a] = {"case": TC.expected_path(st, t, a).name, "missing": True}
                    continue
                p_int = c["P_loss_w"]
                r = F[feed_of[a]]["R_ohm"] if feed_of[a] else 0.0
                pf, i = solve_feed(p_int, r, ks[st])
                pf1, _ = solve_feed(p_int, r, ks["S1"])
                if a == "Z2" and st == TC.PRODUCTION_STATE and t == "A":
                    i_ref = i
                rec = {"case": p.name, "P_int_W": p_int, "feed": feed_of[a],
                       "R_feed_mohm": 1e3 * r, "k_feed": ks[st], "P_feed_W": pf,
                       "P_feed_S1_W": pf1, "I_in_A": i, "plates": n,
                       "P_pump_shaft_W": n * pump["0.55"],
                       "P_pump_band_W": [n * pump["0.75"], n * pump["0.35"]],
                       "P_pump_hydraulic_W": n * pump["hyd"],
                       "pump_basis": f"{n} full plate(s)"}
                # TCPMT revision: every plate at its OWN flow (cooling B's bottom plate sized to
                # the top plate's coolant rise), from the case's own plate record, else from the
                # cooling specification's record of the same case file
                cool_case = (((cool.get("tiers") or {}).get(t) or {}).get("cases") or {}).get(a)
                cool_rec = (c.get("thermal") or {}).get("cooling")
                if cool_rec:
                    sh = cool_rec["P_pump_shaft_total_W"]
                    rec.update({"P_pump_shaft_W": sh["0.55"],
                                "P_pump_band_W": [sh["0.75"], sh["0.35"]],
                                "P_pump_hydraulic_W": cool_rec["P_pump_hydraulic_total_W"],
                                "pump_basis": "each plate at its own flow (case record)"})
                elif (cool_case and cool_case.get("case_records_plates")
                      and cool_case.get("file") == p.name):
                    sh = cool_case["P_shaft_W"]
                    rec.update({"P_pump_shaft_W": sh["0.55"],
                                "P_pump_band_W": [sh["0.75"], sh["0.35"]],
                                "P_pump_hydraulic_W": cool_case["P_pump_hydraulic_W"],
                                "pump_basis": "each plate at its own flow (cooling_spec)"})
                rec["P_platform_W"] = p_int + pf + rec["P_pump_shaft_W"]
                rec["P_platform_no_pump_W"] = p_int + pf
                tiers[t][a] = rec
        out["states"][st] = tiers
    out["tiers"] = out["states"][TC.PRODUCTION_STATE]       # the production table
    if i_ref is None:
        z = json.loads((FC / "etm_Z2_HV_S0_h1.1_r21.json").read_text())
        i_ref = (P_LOAD + z["P_loss_w"]) / V_IN
    out["feed_design"] = feed_design(F, i_ref)
    m = out["macros"]
    m["FeedRbgaZtwo"] = f"{1e3 * F['Z2_bga_fed']['R_ohm']:.2f}"
    m["FeedRflexZtwo"] = f"{1e3 * F['Z2_flex']['R_ohm']:.2f}"
    m["FeedRZthree"] = f"{1e3 * F['Z3_board_planes']['R_ohm']:.2f}"
    fd = out["feed_design"]
    ring, plane, flex = fd["Z2_bga_ring"], fd["Z3_plane_pair"], fd["Z2_flex_alternative"]
    m["FeedRingN"] = str(ring["n_per_rail"])
    m["FeedRingSites"] = str(ring["sites"])
    m["FeedRingPeak"] = f"{ring['I_ball_peak_A']['SDEC']:.2f}"
    m["FeedRingPeakSzero"] = f"{ring['I_ball_peak_A']['S0']:.2f}"
    m["FeedRingPeakSone"] = f"{ring['I_ball_peak_A']['S1']:.1f}"
    m["FeedRingPasses"] = "yes" if ring["passes_rule"]["SDEC"] else "no"
    req = ring.get("production_requirement") or {}
    if req.get("n_min_per_rail"):
        m["FeedRingNprod"] = str(req["n_min_per_rail"])
    m["FeedPlaneJ"] = f"{plane['edge_current_density_A_mm2']['SDEC']:.0f}"
    m["FeedPlaneAmm"] = f"{plane['edge_current_per_width_A_mm']['SDEC']:.1f}"
    m["FeedPlaneDrop"] = f"{plane['static_drop_mV']:.1f}"
    m["FeedFlexJ"] = f"{flex['bridge_current_density_A_mm2']['SDEC']:.0f}"
    pr = out["tiers"]
    for st, tag in ((TC.PRODUCTION_STATE, ""), ("S0", "Szero")):
        T = out["states"][st]
        for t in ("A", "B"):
            for a, at in (("Z1", "Zone"), ("Z2", "Ztwo"), ("Z3", "Zthree")):
                rec = T[t][a]
                if rec.get("missing"):
                    continue
                m[f"Plat{t}{at}{tag}"] = f"{rec['P_platform_W']:.1f}"
                m[f"PlatNoPump{t}{at}{tag}"] = f"{rec['P_platform_no_pump_W']:.1f}"
                if a != "Z1":
                    m[f"PlatFeed{t}{at}{tag}"] = f"{rec['P_feed_W']:.2f}"
                if a == "Z2" and t == "A":
                    m[f"FeedPbgaZtwo{tag}"] = f"{rec['P_feed_W']:.2f}"
                    m[f"FeedPbgaZtwoSone{tag}"] = f"{rec['P_feed_S1_W']:.1f}"
                if a == "Z3" and t == "B":
                    m[f"FeedPZthree{tag}"] = f"{rec['P_feed_W']:.2f}"
                    m[f"FeedPZthreeSone{tag}"] = f"{rec['P_feed_S1_W']:.1f}"
    m["PumpShaftPlate"] = f"{pump['0.55']:.0f}"
    OUT.write_text(json.dumps(out, indent=1, default=float))
    for st, T in out["states"].items():
        for t, row in T.items():
            for a, rec in row.items():
                if rec.get("missing"):
                    print(st, t, a, "missing:", rec["case"])
                    continue
                print(st, t, a, f"P_int={rec['P_int_W']:.1f} feed={rec['R_feed_mohm']:.2f} mOhm "
                                f"k={rec['k_feed']:.2f} P_feed={rec['P_feed_W']:.2f} "
                                f"(S1 {rec['P_feed_S1_W']:.1f}) pump={rec['P_pump_shaft_W']:.0f} "
                                f"platform={rec['P_platform_W']:.1f}")
    print(json.dumps({k: v for k, v in m.items() if k.startswith("Feed")}, indent=1))
    return out


if __name__ == "__main__":
    main()
