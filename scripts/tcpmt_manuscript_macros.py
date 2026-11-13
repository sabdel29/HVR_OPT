"""Generate manuscript_v2/results_macros.tex and the comparison table FROM the artifacts.

Every result number in the TCPMT manuscript (manuscript_v2) is a macro defined here, read
from research/final_closure/ (or $TCPMT_RESULTS_DIR, used to test against an older
lineage). A rerun changes the paper by regenerating this file, never by editing prose.

Architectures: Z1 (embedded), Z2 (package backside, board opening), Z3 (board backside);
any architecture without a production result is printed as "--". Scenario suffixes: none
for HV-S0 (headline), Sone, Stwo.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = Path(os.environ.get("TCPMT_RESULTS_DIR", R / "research" / "final_closure"))
MS = R / "manuscript_v2"
OUT_MAC = MS / "results_macros.tex"
OUT_TAB = MS / "tab_compare.tex"
sys.path.insert(0, str(R / "scripts"))

ARCHS = ("Z1", "Z2", "Z3")
ATAG = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
SCENS = ("HV_S0", "HV_S1", "HV_S2")
STAG = {"HV_S0": "", "HV_S1": "Sone", "HV_S2": "Stwo"}
STAG_X = {"HV_S0": "Szero", "HV_S1": "Sone", "HV_S2": "Stwo"}
P_LOAD_W = 1000.0
NORTON_T_MAX_C = 125.0
SAC305_SOLIDUS_C = 217.0
NA = "--"

#: ledger term -> reporting group (prefix match, first hit wins)
GROUPS = (("conv", ("P_conv_",)),
          ("intra", ("P_intraVR",)),
          ("hv", ("P_pkg_RDL_HV", "P_BGA_supply", "P_BGA_return")),
          ("tsv", ("P_TSV",)),
          ("attach", ("P_VR_attach", "P_VR_PCB_attach", "P_board_attach")),
          ("board", ("P_board", "P_PCB", "P_pcb", "P_BGA_LV", "P_BGA_1V", "P_BGA_VDD",
                     "P_BGA_GND", "P_bga_lv", "P_sub_land")),
          ("pads", ("P_pad",)),
          ("lv", ("P_pkg_RDL_LV",)))


def J(name):
    f = D / name
    return json.loads(f.read_text()) if f.exists() else None


def fx(v, n=1):
    return f"{v:.{n}f}" if isinstance(v, (int, float)) else NA


def group_of(term):
    for g, pre in GROUPS:
        if any(term.startswith(p) for p in pre):
            return g
    return "other"


def ledger_groups(rows):
    out = {}
    for r in rows:
        g = group_of(r["term"])
        out[g] = out.get(g, 0.0) + (r["P_w"] or 0.0)
    return out


def load_cases():
    """(arch, scen) -> merged record: final_results row + ledger groups + raw case extras."""
    fin = J("final_results.json") or []
    S = {(x["arch"], x["scenario"]): dict(x) for x in fin}
    led = (J("electrical_ledger.json") or {}).get("rows") or []
    for (a, s), x in S.items():
        x["groups"] = ledger_groups([r for r in led if r["arch"] == a and r["scenario"] == s])
    # an architecture the results aggregator does not know yet (Z3 before its merge) is read
    # straight from its case file, so the table never silently drops it
    for a in ARCHS:
        for s in SCENS:
            if (a, s) in S:
                continue
            f = D / f"etm_{a}_{s}_h1.1_r21.json"
            if not f.exists():
                continue
            r = json.loads(f.read_text())
            if "mechanics" not in r or not (r["mechanics"] or {}).get("joint_search"):
                continue
            th, mm, h = r["thermal"], r["mechanics"], r["et_history"][-1]
            crit = mm["joint_search"]["critical"]
            S[(a, s)] = {"arch": a, "scenario": s, "P_loss_w": r["P_loss_w"],
                         "P_loss_package_internal_w": r["P_loss_w"],
                         "T_max_C": th["T_max_C"], "T_die_mean_C": h["T_die_mean_C"],
                         "T_conv_mean_C": h["T_conv_C"],
                         "die_warpage_pv_um": mm["die_warpage_pv_um"],
                         "pkg_warpage_pv_um": mm.get("pkg_warpage_pv_um"),
                         "critical_joint_xy_mm": [crit["x_mm"], crit["y_mm"]],
                         "du_c_um": crit["du_um"], "T_joint_C": crit["T_C"],
                         "d_eps_in_per_cycle": None, "local_mesh_U_rel": None,
                         "et_iterations": len(r["et_history"]),
                         "et_wall_s": r["et_wall_s"], "mech_wall_s": mm["wall_s"],
                         "n_joint_sites": mm["joint_search"]["n_sites"],
                         "groups": ledger_groups(r["ledger_rows"]),
                         "_from_case_file": True}
    for (a, s), x in S.items():
        f = D / f"etm_{a}_{s}_h1.1_r21.json"
        if f.exists():
            h = json.loads(f.read_text())["et_history"][-1]
            x["T_regions"] = {k[2:-2]: v for k, v in h.items()
                              if k.startswith("T_") and k.endswith("_C")}
    return S


def room_temperature_loss(arch, scen):
    """The loss a decoupled electrical analysis would report: every region at 25 C."""
    try:
        import final_closure_ledger as FL
        keys = ("conv", "hs", "ls", "ind", "caps", "bga", "sub", "interface", "attach")
        return FL.self_consistent(arch, scen, {k: 25.0 for k in keys})["P_loss_w"]
    except Exception as e:                                   # noqa: BLE001 - report, continue
        print(f"  room-temperature ledger unavailable for {arch} {scen}: {e}")
        return None


def main():
    S = load_cases()
    mac = {}
    have = sorted({a for a, _ in S})
    print("architectures with production results:", have)
    for (a, s), x in sorted(S.items()):
        t = ATAG.get(a)
        if t is None:
            continue
        k = t + STAG[s]
        g = x.get("groups") or {}
        p = x["P_loss_w"]
        mac.update({
            f"Ploss{k}": fx(p, 1), f"Eff{k}": fx(100 * P_LOAD_W / (P_LOAD_W + p), 1),
            f"Pconv{k}": fx(g.get("conv"), 1),
            f"Proute{k}": fx(p - g.get("conv", 0.0), 2),
            # a group absent from the ledger is structurally absent in that architecture
            f"Phv{k}": fx(g.get("hv"), 2), f"Ptsv{k}": fx(g.get("tsv"), 2),
            f"Patt{k}": fx(g.get("attach"), 2), f"Pintra{k}": fx(g.get("intra"), 2),
            f"Pboard{k}": fx(g.get("board"), 2), f"Ppads{k}": fx(g.get("pads"), 3),
            f"Tmax{k}": fx(x["T_max_C"], 1), f"Tdie{k}": fx(x["T_die_mean_C"], 1),
            f"Tconv{k}": fx(x["T_conv_mean_C"], 1), f"Tjoint{k}": fx(x["T_joint_C"], 1),
            f"Warp{k}": fx(x["die_warpage_pv_um"], 1),
            f"PkgWarp{k}": fx(x.get("pkg_warpage_pv_um"), 1),
            f"Du{k}": fx(x["du_c_um"], 2),
            f"Eps{k}": fx(1e3 * x["d_eps_in_per_cycle"], 2) if x.get("d_eps_in_per_cycle")
            else NA,
            f"EpsU{k}": fx(100 * x["local_mesh_U_rel"], 1)
            if x.get("local_mesh_U_rel") is not None else NA,
            f"EtIters{k}": str(x.get("et_iterations", NA)),
            f"TjointHot{k}": fx(x.get("T_joint_hottest_C"), 1),
            f"Tls{k}": fx((x.get("T_regions") or {}).get("ls"), 1),
            f"Ths{k}": fx((x.get("T_regions") or {}).get("hs"), 1),
            f"Njoint{k}": str(x.get("n_joint_sites", NA)),
        })
        other = g.get("other")
        if other:
            print(f"  WARNING {a} {s}: {other:.3f} W in ledger terms with no reporting group")
        p25 = room_temperature_loss(a, s)
        if p25 is not None:
            mac[f"Prt{k}"] = fx(p25, 1)
            mac[f"Under{k}"] = fx(100 * (p - p25) / p, 0)
            mac[f"Rise{k}"] = fx(p - p25, 1)
    # architecture differences that the prose quotes (decoupled vs coupled)
    for s in SCENS:
        for b in ("Z2", "Z3"):
            if ("Z1", s) in S and (b, s) in S:
                k = f"{ATAG[b]}{STAG_X[s]}"
                d = S[("Z1", s)]["P_loss_w"] - S[(b, s)]["P_loss_w"]
                mac[f"DeltaP{k}"] = fx(d, 2)
                p1, pb = room_temperature_loss("Z1", s), room_temperature_loss(b, s)
                if p1 is not None and pb is not None:
                    mac[f"DeltaPrt{k}"] = fx(p1 - pb, 2)
    for s in SCENS:
        for b in ("Z2", "Z3"):
            if ("Z1", s) not in S or (b, s) not in S:
                continue
            z1, zb = S[("Z1", s)], S[(b, s)]
            k = f"{ATAG[b]}{STAG_X[s]}"
            d = zb["P_loss_w"] - z1["P_loss_w"]
            mac[f"LossGap{k}"] = fx(abs(d), 1)
            mac[f"LossLead{k}"] = "Z1" if d > 0 else b
            g1, gb = z1.get("groups") or {}, zb.get("groups") or {}
            mac[f"dPconv{k}"] = fx(gb.get("conv", 0) - g1.get("conv", 0), 2)
            mac[f"dProute{k}"] = fx((zb["P_loss_w"] - gb.get("conv", 0))
                                    - (z1["P_loss_w"] - g1.get("conv", 0)), 2)
            t1, tb = (z1.get("T_regions") or {}), (zb.get("T_regions") or {})
            if "ls" in t1 and "ls" in tb:
                mac[f"dTls{k}"] = fx(tb["ls"] - t1["ls"], 1)
            mac[f"dTmax{k}"] = fx(zb["T_max_C"] - z1["T_max_C"], 1)
    # ratios of the mechanical drivers against the embedded reference
    for b in ("Z2", "Z3"):
        if ("Z1", "HV_S0") in S and (b, "HV_S0") in S:
            z1, zb = S[("Z1", "HV_S0")], S[(b, "HV_S0")]
            mac[f"WarpRatio{ATAG[b]}"] = fx(zb["die_warpage_pv_um"] / z1["die_warpage_pv_um"], 2)
            mac[f"DuRatio{ATAG[b]}"] = fx(zb["du_c_um"] / z1["du_c_um"], 2)
    mac.update(landside_macros())
    mac.update(feed_macros())
    mac.update(verification_macros(S))
    mac.update(network_macros())
    lines = ["% GENERATED by scripts/tcpmt_manuscript_macros.py -- do not edit",
             f"% source: {D}"]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    OUT_MAC.write_text("\n".join(lines) + "\n")
    OUT_TAB.write_text(compare_table(S, mac))
    print(f"wrote {OUT_MAC} ({len(mac)} macros) and {OUT_TAB}")


def landside_macros():
    """Z3 land-side 1 V redistribution (NOT_MODELLED in the coupled ledger): the 2-D sheet
    bound of scripts/tcpmt_z3_landside_estimate.py, and the BGA pitch at which the 1 V balls
    would fit under the cell grid instead."""
    f = R / "research" / "tcpmt_revision" / "z3_landside_spreading.json"
    if not f.exists():
        return {}
    j = json.loads(f.read_text())
    cs = sorted(j["cases"], key=lambda c: c["t_cu_um"])
    n_need = 2 * 667                                   # 1.5 A per ball, both rails
    bbox = 21.36                                       # cell-grid bounding box (mm)
    return {"LandPmax": fx(cs[0]["P_two_rails_w"], 0), "LandTmin": fx(cs[0]["t_cu_um"], 0),
            "LandPmin": fx(cs[-1]["P_two_rails_w"], 0), "LandTmax": fx(cs[-1]["t_cu_um"], 0),
            "LandDVmax": fx(cs[0]["dV_one_rail_mV"], 0),
            "LandDVmin": fx(cs[-1]["dV_one_rail_mV"], 0),
            "LandBallsInside": str(j["balls_inside_footprints"]),
            "LandBallsRail": str(j["balls_per_rail"]),
            "PitchMaxZthree": fx(bbox / n_need ** 0.5, 2)}


def feed_macros():
    """Direct-feed crossover R* per backside architecture and scenario."""
    cx = J("direct_feed_crossover.json") or {}
    out = {}
    per_arch = cx.get("architectures") or {"Z2": cx}       # older files: Z2 only
    for b, c in per_arch.items():
        if b not in ATAG:
            continue
        for s, v in (c.get("scenarios") or {}).items():
            k = f"{ATAG[b]}{STAG_X[s]}"
            ok = v.get("R_star_mohm") is not None and not v.get("Z1_operating_point_inadmissible")
            out[f"Rstar{k}"] = fx(v["R_star_mohm"], 2) if ok else NA
            out[f"Adv{k}"] = fx(v.get("advantage_at_zero_feed_w"), 2)
            out[f"Irms{STAG_X[s]}"] = fx(v.get("I_48_rms_a"), 1)
            out[f"PfeedPerMohm{STAG_X[s]}"] = fx(v.get("P_feed_per_mohm_w"), 2)
    return out


def verification_macros(S):
    mc = J("mesh_convergence.json") or {"cases": {}}
    lm = J("local_mesh_study.json") or {}
    au = J("energy_audit.json") or {}
    out = {}
    worst = [c.get("worst") for c in mc.get("cases", {}).values()]
    out["MeshWorstProd"] = (fx(100 * max(worst), 1) if worst and None not in worst else NA)
    us = [c.get("U") for c in (lm.get("cases") or {}).values() if c.get("U") is not None]
    out["LocalUrange"] = (f"{100 * min(us):.1f}--{100 * max(us):.1f}\\,\\%" if us else NA)
    walls = [(x.get("et_wall_s") or 0) + (x.get("mech_wall_s") or 0)
             for (a, s), x in S.items() if s == "HV_S0" and a in ATAG]
    if walls:
        lo, hi = min(walls) / 3600, max(walls) / 3600
        out["EvalHours"] = (f"{lo:.1f}--{hi:.1f}~h" if hi - lo >= 0.1 else f"{hi:.1f}~h")
    else:
        out["EvalHours"] = NA
    out["EnergyTol"] = "%.0e" % au["tolerance_rel"] if au.get("tolerance_rel") else NA
    out["EtItersMax"] = str(max((x.get("et_iterations") or 0) for x in S.values())) if S else NA
    return out


def network_macros():
    pn = J("package_network.json") or {}
    if not pn:
        return {}
    out = {"NballMatched": str(pn.get("matched_count", NA))}
    for a in ("Z1", "Z2"):
        lp = (pn.get("loop") or {}).get(a) or {}
        if lp.get("r_loop_ohm"):
            out[f"Rloop{ATAG[a]}"] = fx(1e3 * lp["r_loop_ohm"], 2)
    return out


def compare_table(S, mac):
    cols = [a for a in ARCHS]

    def cell(a, key, s="HV_S0"):
        return mac.get(f"{key}{ATAG[a]}{STAG[s]}", NA)

    def both(a, key):
        """S0 value with the S1 value in parentheses."""
        v0, v1 = cell(a, key), cell(a, key, "HV_S1")
        return v0 if v1 == NA else f"{v0} ({v1})"

    def row(label, f):
        return f"{label} & " + " & ".join(f(a) for a in cols) + r" \\"

    def loc(a):
        x = S.get((a, "HV_S0"))
        if not x:
            return NA
        cx, cy = x["critical_joint_xy_mm"]
        return f"({cx:.1f}, {cy:.1f})"

    def rstar(a, s):
        if a == "Z1":
            return "n/a"
        return mac.get(f"Rstar{ATAG[a]}{STAG_X[s]}", NA)

    def calib(a):
        flags = []
        for s in ("HV_S0", "HV_S1"):
            x = S.get((a, s))
            if not x:
                flags.append(NA)
            else:
                flags.append("yes" if x["T_joint_C"] <= NORTON_T_MAX_C else "no")
        return "/".join(flags)

    L = [r"% GENERATED by scripts/tcpmt_manuscript_macros.py -- do not edit",
         r"\begin{table}[!t]",
         r"\caption{The three integrations evaluated by the framework on one regulator and "
         r"one cooling solution. Smoothed input (S0); pulsed input (S1) in parentheses where "
         r"it changes the result. Loss inside the package-internal boundary.}",
         r"\label{tab:compare}", r"\centering", r"\footnotesize",
         r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabular}{@{}lrrr@{}}", r"\toprule",
         r" & Z1 embedded & Z2 pkg.\ backside & Z3 board backside \\", r"\midrule",
         r"\multicolumn{4}{@{}l}{\emph{Electrical (W)}}\\",
         row("Conversion", lambda a: cell(a, "Pconv")),
         row("Intra-cell routing", lambda a: cell(a, "Pintra")),
         row("48-V package path", lambda a: both(a, "Phv")),
         row("TSV field", lambda a: cell(a, "Ptsv")),
         row("VR attach", lambda a: cell(a, "Patt")),
         row("Board vias, 1-V BGA", lambda a: cell(a, "Pboard")),
         row("Package-internal total", lambda a: both(a, "Ploss")),
         row("Feed limit $R^*$ (m$\\Omega$)",
             lambda a: rstar(a, "HV_S0") if rstar(a, "HV_S1") in (NA, "n/a")
             else f"{rstar(a, 'HV_S0')} ({rstar(a, 'HV_S1')})"),
         r"\midrule", r"\multicolumn{4}{@{}l}{\emph{Thermal ($^\circ$C)}}\\",
         row("Peak", lambda a: both(a, "Tmax")),
         row("Die, mean", lambda a: cell(a, "Tdie")),
         row("Converter, mean", lambda a: cell(a, "Tconv")),
         row("Critical joint", lambda a: both(a, "Tjoint")),
         r"\midrule", r"\multicolumn{4}{@{}l}{\emph{Mechanical}}\\",
         row("Die warpage (\\textmu m)", lambda a: cell(a, "Warp")),
         row("Joint sites searched", lambda a: cell(a, "Njoint")),
         row("Critical joint $(x, y)$ (mm)", loc),
         row("$\\du$ (\\textmu m)", lambda a: both(a, "Du")),
         row("$\\deps$ ($10^{-3}$/cycle)", lambda a: cell(a, "Eps")),
         row("\\quad uncertainty $U$ (\\%)", lambda a: cell(a, "EpsU")),
         r"\midrule", r"\multicolumn{4}{@{}l}{\emph{Rules and cost}}\\",
         row("Joint $\\le 125\\,^\\circ$C, S0/S1", calib),
         row("E--T iterations", lambda a: cell(a, "EtIters")),
         r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
