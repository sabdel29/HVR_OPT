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
            c = json.loads(f.read_text())
            h = c["et_history"][-1]
            x["T_regions"] = {k[2:-2]: v for k, v in h.items()
                              if k.startswith("T_") and k.endswith("_C")}
            x["q_split"] = (c.get("thermal_boundary") or {}).get("q_split_W")
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
            f"TlsRise{k}": (fx(x["T_regions"]["ls"] - 25.0, 0)
                            if (x.get("T_regions") or {}).get("ls") is not None else NA),
            f"Ths{k}": fx((x.get("T_regions") or {}).get("hs"), 1),
            f"Tind{k}": fx((x.get("T_regions") or {}).get("ind"), 1),
            f"Qplate{k}": fx((x.get("q_split") or {}).get("converter_plate"), 0),
            f"Qtop{k}": fx((x.get("q_split") or {}).get("top"), 0),
            f"QdieDown{k}": (fx((x["q_split"]["converter_plate"] - x["P_loss_w"]), 0)
                             if (x.get("q_split") or {}).get("converter_plate") else NA),
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
                    mac[f"DeltaPrtAbs{k}"] = fx(abs(p1 - pb), 1)
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
            dc = gb.get("conv", 0) - g1.get("conv", 0)
            dr = (zb["P_loss_w"] - gb.get("conv", 0)) - (z1["P_loss_w"] - g1.get("conv", 0))
            mac[f"dPconv{k}"], mac[f"dPconvAbs{k}"] = fx(dc, 2), fx(abs(dc), 1)
            mac[f"dProute{k}"], mac[f"dProuteAbs{k}"] = fx(dr, 2), fx(abs(dr), 2)
            t1, tb = (z1.get("T_regions") or {}), (zb.get("T_regions") or {})
            if "ls" in t1 and "ls" in tb:
                mac[f"dTls{k}"] = fx(tb["ls"] - t1["ls"], 1)
                mac[f"dTlsAbs{k}"] = fx(abs(tb["ls"] - t1["ls"]), 0)
            mac[f"dTmax{k}"] = fx(zb["T_max_C"] - z1["T_max_C"], 1)
            mac[f"dTmaxAbs{k}"] = fx(abs(zb["T_max_C"] - z1["T_max_C"]), 0)
            mac[f"dTjoint{k}"] = fx(zb["T_joint_C"] - z1["T_joint_C"], 1)
            mac[f"dTjointAbs{k}"] = fx(abs(zb["T_joint_C"] - z1["T_joint_C"]), 0)
    for a in ARCHS:
        if (a, "HV_S0") in S and (a, "HV_S1") in S:
            mac[f"RiseSone{ATAG[a]}"] = fx(S[(a, "HV_S1")]["P_loss_w"]
                                           - S[(a, "HV_S0")]["P_loss_w"], 1)
    for b in ("Z2", "Z3"):
        k = f"{ATAG[b]}Szero"
        if f"dPconv{k}" in mac and f"dProute{k}" in mac:
            dr = float(mac[f"dProute{k}"])
            if dr != 0:                     # |conversion change| per watt of routing change
                mac[f"ConvToRoute{ATAG[b]}"] = fx(abs(float(mac[f"dPconv{k}"]) / dr), 1)
    sens = sorted((D / "sensitivity").glob("etm_*__*.json")) if (D / "sensitivity").exists() else []
    mac["NvariantRuns"] = str(sum(1 for f in sens
                                  if (json.loads(f.read_text()).get("mechanics") or {})
                                  .get("joint_search")))
    # ratios of the mechanical drivers against the embedded reference
    for b in ("Z2", "Z3"):
        if ("Z1", "HV_S0") in S and (b, "HV_S0") in S:
            z1, zb = S[("Z1", "HV_S0")], S[(b, "HV_S0")]
            mac[f"WarpRatio{ATAG[b]}"] = fx(zb["die_warpage_pv_um"] / z1["die_warpage_pv_um"], 2)
            mac[f"WarpFold{ATAG[b]}"] = fx(z1["die_warpage_pv_um"] / zb["die_warpage_pv_um"], 1)
            mac[f"DuRatio{ATAG[b]}"] = fx(zb["du_c_um"] / z1["du_c_um"], 2)
    mac.update(landside_macros())
    mac.update(sensitivity_macros(S))
    T = tier_cases(S)
    mac.update(tier_macros(T))
    mac.update(isothermal_macros())
    lt = R / "research" / "tcpmt_revision" / "layer_temperatures.json"
    if lt.exists():                 # board / substrate means per cooling tier (mechanism)
        for a, tiers in json.loads(lt.read_text())["cases"].items():
            for t, v in tiers.items():
                mac[f"Tboard{t}{ATAG[a]}"] = fx(v["board"], 0)
                mac[f"TboardBot{t}{ATAG[a]}"] = fx(v["board_bottom"], 0)
                mac[f"Tsub{t}{ATAG[a]}"] = fx(v["substrate"], 0)
                mac["CteBoard"], mac["CteSi"] = fx(1e6 * v["cte_board"], 1), fx(1e6 * v["cte_silicon"], 1)
    # Z3 is outside the Z1/Z2 mesh ladder: its own r21 -> r31 change, per observable
    f21, f31 = D / "etm_Z3_HV_S0_h1.1_r21.json", D / "etm_Z3_HV_S0_h1.1_r31.json"
    if f21.exists() and f31.exists():
        def q(c):
            m = c.get("mechanics") or {}
            cr = (m.get("joint_search") or {}).get("critical") or {}
            return {"Ploss": c["P_loss_w"], "Tmax": c["thermal"]["T_max_C"],
                    "Warp": m.get("die_warpage_pv_um"), "Du": cr.get("du_um")}
        a, b = q(json.loads(f21.read_text())), q(json.loads(f31.read_text()))
        for k in a:
            if a[k] and b[k]:
                mac[f"MeshZthree{k}"] = fx(100 * abs(b[k] - a[k]) / abs(b[k]), 1)
    tf = R / "research" / "tcpmt_revision" / "tier_feed_crossover.json"
    if tf.exists():
        for t, row in json.loads(tf.read_text()).get("tiers", {}).items():
            for b, v in row.items():
                r = v.get("R_star_mohm")
                mac[f"RstarTier{t}{ATAG[b]}"] = (NA if r is None else "none" if r == 0
                                                  else fx(r, 1))
    mac.update(feed_macros())
    mac.update(verification_macros(S))
    mac.update(network_macros())
    try:                                    # the S1 feed requirement against Z1's own loop
        mac["RstarOverLoopZtwo"] = fx(float(mac["RstarZtwoSone"]) / float(mac["RloopZone"]), 1)
    except (KeyError, ValueError):
        pass
    mac.update(accuracy_macros())
    import tcpmt_review_macros as RVM       # second review round: new artifacts
    for k, v in RVM.macros().items():
        if k in mac and mac[k] != v:
            print(f"  WARNING review macro {k} overrides {mac[k]} -> {v}")
        mac[k] = v
    lines = ["% GENERATED by scripts/tcpmt_manuscript_macros.py -- do not edit",
             f"% source: {D}"]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    OUT_MAC.write_text("\n".join(lines) + "\n")
    OUT_TAB.write_text(compare_table(S, mac))
    print(f"wrote {OUT_MAC} ({len(mac)} macros) and {OUT_TAB}")


#: sensitivity runs the prose quotes, by a letters-only macro tag
SENS_TAG = {"z1_tier_reference": "TierRef", "z2_cooled": "ZtwoCooled", "z3_top_only": "ZthreeTop",
            "board_hbot100": "HbotLo", "board_hbot500": "HbotHi", "tsv_min": "TsvMin",
            "tsv_mid": "TsvMid", "attach_sparse": "AttSparse", "f2_void": "Void",
            "icepak_equivalent": "Icepak", "gan_k_half": "GanHalf", "board_h1": "BoardHone"}


def sensitivity_macros(S):
    """\\Sens<Variant><Arch><Obs>: the value of a quoted sensitivity run, and \\SensD...: its
    change against the production case of the same architecture (absolute units)."""
    out = {}
    sd = D / "sensitivity"
    for v, tag in SENS_TAG.items():
        for a in ARCHS:
            f = sd / f"etm_{a}_HV_S0__{v}.json"
            if not f.exists():
                continue
            c = json.loads(f.read_text())
            m = c.get("mechanics") or {}
            h = c["et_history"][-1]
            crit = (m.get("joint_search") or {}).get("critical") or {}
            vals = {"Ploss": c["P_loss_w"], "Tmax": c["thermal"]["T_max_C"],
                    "Tls": h.get("T_ls_C"), "Warp": m.get("die_warpage_pv_um"),
                    "Du": crit.get("du_um"), "Tjoint": crit.get("T_C")}
            base = S.get((a, "HV_S0")) or {}
            bvals = {"Ploss": base.get("P_loss_w"), "Tmax": base.get("T_max_C"),
                     "Tls": (base.get("T_regions") or {}).get("ls"),
                     "Warp": base.get("die_warpage_pv_um"), "Du": base.get("du_c_um"),
                     "Tjoint": base.get("T_joint_C")}
            nd = {"Ploss": 1, "Tmax": 1, "Tls": 1, "Warp": 1, "Du": 2, "Tjoint": 1}
            for k, val in vals.items():
                if val is None:
                    continue
                out[f"Sens{tag}{ATAG[a]}{k}"] = fx(val, nd[k])
                if bvals.get(k) is not None:
                    out[f"SensD{tag}{ATAG[a]}{k}"] = fx(val - bvals[k], nd[k])
                    out[f"SensDAbs{tag}{ATAG[a]}{k}"] = fx(abs(val - bvals[k]), nd[k])
    return out


#: the three-tier comparison (TCPMT revision). Common temperature: no coupling. A: the same
#: top cold plate for every integration. B: the same top plate plus the same bottom plate
#: (top-plate coefficient, inlet temperature, 50-um TIM) under the cell-grid footprint.
#: I: interface-free bottom plates, reported as bounds. ("prod", None) = production case.
TIERS = {"A": {"Z1": ("prod", None), "Z2": ("prod", None), "Z3": ("sens", "z3_top_only")},
         "B": {"Z1": ("sens", "z1_bottom_plate_tim"), "Z2": ("sens", "z2_cooled_tim"),
               "Z3": ("sens", "z3_plate_tim")},
         "I": {"Z2": ("sens", "z2_cooled"), "Z3": ("prod", None)}}


def case_record(kind, arch, variant):
    """One integration under one cooling configuration, read from its case file."""
    f = (D / f"etm_{arch}_HV_S0_h1.1_r21.json" if kind == "prod"
         else D / "sensitivity" / f"etm_{arch}_HV_S0__{variant}.json")
    if not f.exists():
        return None
    c = json.loads(f.read_text())
    m = c.get("mechanics") or {}
    crit = (m.get("joint_search") or {}).get("critical") or {}
    h = c["et_history"][-1]
    g = ledger_groups(c["ledger_rows"])
    th = c["thermal"]
    q_bottom = th.get("q_bottom_plate_W", th.get("q_extra_W"))
    loc = (c.get("local") or {}).get("d_peeq_per_cycle")
    return {"P": c["P_loss_w"], "conv": g.get("conv", 0.0),
            "route": c["P_loss_w"] - g.get("conv", 0.0), "Tmax": th["T_max_C"],
            "Tdie": h.get("T_die_mean_C"), "Tls": h.get("T_ls_C"),
            "warp": m.get("die_warpage_pv_um"), "du": crit.get("du_um"),
            "Tj": crit.get("T_C"), "qb": q_bottom, "eps": loc,
            "Tjhot": max((x["T_C"] for x in (m.get("joint_search") or {}).get("ranked", [])),
                         default=None),
            "converged": c.get("et_converged"), "file": f.name}


def tier_cases(S):
    out = {}
    for t, row in TIERS.items():
        for a, (kind, v) in row.items():
            r = case_record(kind, a, v)
            if r is None:
                continue
            if kind == "prod":
                # every tier entry at the base local level L0 with the production settings --
                # the level every variant's local response is solved at -- so the column is
                # comparable; the declared production level (L3) is reported in Section V
                lm = ((J("local_mesh_study.json") or {}).get("cases") or {}).get(f"{a}_HV_S0") or {}
                r["eps"] = ((lm.get("levels") or {}).get("L0") or {}).get("d_peeq_per_cycle")
            out[(t, a)] = r
    return out


def tier_macros(T):
    """\\<Obs><Tier><Arch>, e.g. \\PlossAZthree, \\WarpBZone, \\QbotBZtwo."""
    nd = {"Ploss": ("P", 1), "Pconv": ("conv", 1), "Proute": ("route", 1),
          "Tmax": ("Tmax", 1), "Tdie": ("Tdie", 1), "Tls": ("Tls", 1), "Warp": ("warp", 1),
          "Du": ("du", 2), "Tjoint": ("Tj", 1), "TjointHot": ("Tjhot", 1), "Qbot": ("qb", 0)}
    out = {}
    for (t, a), r in T.items():
        for name, (key, n) in nd.items():
            if r.get(key) is not None:
                out[f"{name}{t}{ATAG[a]}"] = fx(r[key], n)
        if r.get("eps"):
            out[f"Eps{t}{ATAG[a]}"] = fx(1e3 * r["eps"], 2)
    # differences against Z1 within a tier, and the gain of each integration from A to B
    for t in ("A", "B"):
        for b in ("Z2", "Z3"):
            if (t, "Z1") in T and (t, b) in T:
                d = T[(t, b)]["P"] - T[(t, "Z1")]["P"]
                out[f"Gap{t}{ATAG[b]}"] = fx(abs(d), 1)
                out[f"Lead{t}{ATAG[b]}"] = "Z1" if d > 0 else b
                out[f"dTmaxTier{t}{ATAG[b]}"] = fx(abs(T[(t, b)]["Tmax"]
                                                       - T[(t, "Z1")]["Tmax"]), 0)
    for a in ARCHS:
        if ("A", a) in T and ("B", a) in T:
            out[f"GainB{ATAG[a]}"] = fx(T[("A", a)]["P"] - T[("B", a)]["P"], 1)
            out[f"CoolB{ATAG[a]}"] = fx(T[("A", a)]["Tmax"] - T[("B", a)]["Tmax"], 0)
    return out


def isothermal_macros():
    """The uncoupled comparison: every region of every integration at one temperature."""
    try:
        import final_closure_ledger as FL
    except Exception:                                         # noqa: BLE001
        return {}
    keys = ("conv", "hs", "ls", "ind", "caps", "bga", "sub", "interface", "attach", "pcb_via")
    out = {}
    for T, tag in ((25.0, "Iso"), (100.0, "IsoHot")):
        vals = {}
        for a in ARCHS:
            try:
                L = FL.self_consistent(a, "HV_S0", {k: T for k in keys})
            except Exception:                                 # noqa: BLE001
                continue
            conv = sum(r["P_w"] for r in L["rows"] if r["term"].startswith("P_conv"))
            vals[a] = L["P_loss_w"]
            out[f"P{tag}{ATAG[a]}"] = fx(L["P_loss_w"], 1)
            out[f"Proute{tag}{ATAG[a]}"] = fx(L["P_loss_w"] - conv, 1)
            out[f"Pconv{tag}"] = fx(conv, 1)
        for b in ("Z2", "Z3"):
            if "Z1" in vals and b in vals:
                out[f"Gap{tag}{ATAG[b]}"] = fx(abs(vals[b] - vals["Z1"]), 1)
    return out


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
    # the sheet loss scales as 1/t: the copper at which the Z3 lower-bound advantage is used up
    pt = sum(c["P_two_rails_w"] * c["t_cu_um"] for c in cs) / len(cs)
    tie = {}
    fin = {(x["arch"], x["scenario"]): x for x in (J("final_results.json") or [])}
    if ("Z1", "HV_S0") in fin and ("Z3", "HV_S0") in fin:
        adv = fin[("Z1", "HV_S0")]["P_loss_w"] - fin[("Z3", "HV_S0")]["P_loss_w"]
        if adv > 0:
            tie = {"LandTie": fx(pt / adv, 0), "LandPT": fx(pt, 0)}
    return {**tie, "LandPmax": fx(cs[0]["P_two_rails_w"], 0), "LandTmin": fx(cs[0]["t_cu_um"], 0),
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
            # R* = 0: behind even with a lossless feed -- no feed resistance is affordable
            out[f"Rstar{k}"] = (("none" if v["R_star_mohm"] == 0 else fx(v["R_star_mohm"], 2))
                                if ok else NA)
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


ACC = {"TsvBulk": "tsv_bulk", "TsvKz": "tsv_tile_kz", "TsvKx": "tsv_tile_kx",
       "RdlKx": "rdl_tier_kx", "RdlKz": "rdl_tier_kz", "PkgRdlZone": "pkg_rdl_Z1",
       "ThermAedtZone": "thermal_column_aedt_Z1", "ThermAedtZtwo": "thermal_column_aedt_Z2",
       "ThermMooseZone": "thermal_column_moose_Z1", "ThermMooseZtwo": "thermal_column_moose_Z2",
       "MechClosed": "mech_bilayer_closed_form", "MechAedt": "mech_bilayer_aedt",
       "CoolingIcepak": "cooling_icepak", "AttDenseKz": "vr_attach_dense_kz",
       "AttDenseKxy": "vr_attach_dense_kxy"}


def accuracy_macros():
    """|relative error| (%) of each matched benchmark (accuracy_speed_matrix.json) and the
    group maxima the verification prose quotes."""
    acc = J("accuracy_speed_matrix.json") or {}
    by = {r["stage"]: r for r in acc.get("rows", []) if r.get("status") == "EXECUTED"
          and isinstance(r.get("error"), (int, float))}
    out = {}
    for k, st in ACC.items():
        if st in by:
            e = 100 * abs(by[st]["error"])
            out[f"Err{k}"] = fx(e, 2 if e < 1 else 1)
    homog = [100 * abs(by[k]["error"]) for k in ("tsv_bulk", "tsv_tile_kz", "tsv_tile_kx",
                                                 "vr_attach_dense_kz", "vr_attach_dense_kxy",
                                                 "vr_attach_sparse_kz", "vr_attach_sparse_kxy")
             if k in by]
    therm = [100 * abs(by[k]["error"]) for k in ("thermal_column_aedt_Z1",
                                                 "thermal_column_aedt_Z2",
                                                 "thermal_column_moose_Z1",
                                                 "thermal_column_moose_Z2") if k in by]
    if homog:
        out["ErrHomogMax"] = fx(max(homog), 1)
    if therm:
        out["ErrThermMax"] = fx(max(therm), 1)
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
    """Table II: the three integrations under the three-tier comparison."""
    A = ("Z1", "Z2", "Z3")

    def m(key, a):
        return mac.get(f"{key}{ATAG[a]}", NA)

    def row(label, f):
        return f"{label} & " + " & ".join(f(a) for a in A) + r" \\"

    def du_at(t):
        def f(a):
            du, tj = m(f"Du{t}", a), m(f"Tjoint{t}", a)
            return NA if du == NA else f"{du} ({tj})"
        return f

    def rstar(t):
        def f(a):
            if a == "Z1":
                return "n/a"
            return mac.get(f"RstarTier{t}{ATAG[a]}", NA)
        return f

    def calib(a):
        out = []
        for t in ("A", "B"):
            tj = mac.get(f"TjointHot{t}{ATAG[a]}")
            out.append(NA if tj in (None, NA) else ("yes" if float(tj) <= NORTON_T_MAX_C
                                                    else "no"))
        return "/".join(out)

    L = [r"% GENERATED by scripts/tcpmt_manuscript_macros.py -- do not edit",
         r"\begin{table}[!t]",
         r"\caption{The three integrations compared at S0 three ways: at one common temperature "
         r"(no electrothermal coupling), with the same top cold plate (cooling~A), and with the "
         r"same top and bottom cold plates (cooling~B). Loss inside the package-internal "
         r"boundary.}",
         r"\label{tab:compare}", r"\centering", r"\footnotesize",
         r"\setlength{\tabcolsep}{3pt}",
         r"\begin{tabular}{@{}lrrr@{}}", r"\toprule",
         r" & Z1 & Z2 & Z3 \\",
         r" & {\scriptsize embedded} & {\scriptsize pkg.\ backside} & "
         r"{\scriptsize board backside} \\", r"\midrule",
         r"\multicolumn{4}{@{}l}{\emph{Common temperature (no coupling)}}\\",
         row("Loss at 25\\,$^\\circ$C (W)", lambda a: m("PIso", a)),
         row("Loss at 100\\,$^\\circ$C (W)", lambda a: m("PIsoHot", a)),
         row("\\quad of which routing", lambda a: m("ProuteIsoHot", a)),
         r"\midrule", r"\multicolumn{4}{@{}l}{\emph{Cooling A: top plate}}\\",
         row("Loss (W)", lambda a: m("PlossA", a)),
         row("\\quad conversion / routing",
             lambda a: NA if m("PconvA", a) == NA else f"{m('PconvA', a)} / {m('ProuteA', a)}"),
         row("Peak temperature ($^\\circ$C)", lambda a: m("TmaxA", a)),
         row("Low-side tier ($^\\circ$C)", lambda a: m("TlsA", a)),
         row("Board, mean ($^\\circ$C)", lambda a: m("TboardA", a)),
         row("Die warpage (\\textmu m)", lambda a: m("WarpA", a)),
         row("$\\du$ (\\textmu m) at $T_{\\mathrm{j}}$ ($^\\circ$C)", du_at("A")),
         row("$\\deps$ ($10^{-3}$/cycle), L0", lambda a: m("EpsA", a)),
         r"\midrule",
         r"\multicolumn{4}{@{}l}{\emph{Cooling B: top and bottom plates}}\\",
         row("Loss (W)", lambda a: m("PlossB", a)),
         row("\\quad conversion / routing",
             lambda a: NA if m("PconvB", a) == NA else f"{m('PconvB', a)} / {m('ProuteB', a)}"),
         row("Peak temperature ($^\\circ$C)", lambda a: m("TmaxB", a)),
         row("Heat to bottom plate (W)", lambda a: m("QbotB", a)),
         row("Board, mean ($^\\circ$C)", lambda a: m("TboardB", a)),
         row("Die warpage (\\textmu m)", lambda a: m("WarpB", a)),
         row("$\\du$ (\\textmu m) at $T_{\\mathrm{j}}$ ($^\\circ$C)", du_at("B")),
         row("$\\deps$ ($10^{-3}$/cycle), L0", lambda a: m("EpsB", a)),
         r"\midrule", r"\multicolumn{4}{@{}l}{\emph{Rules}}\\",
         row("BGA sites for power", lambda a: {"Z1": str(2 * int(mac.get("NballMatched", 0)))
                                               if mac.get("NballMatched") else NA,
                                               "Z2": "0", "Z3": "1334"}[a]),
         row("Worst via aspect ratio", lambda a: "0.83"),
         row("Feed limit $R^*$, A / B (m$\\Omega$)",
             lambda a: "n/a" if a == "Z1" else f"{rstar('A')(a)} / {rstar('B')(a)}"),
         row("Joints $\\le 125\\,^\\circ$C, A/B", calib),
         r"\bottomrule", r"\end{tabular}",
         r"\par\smallskip\raggedright\footnotesize Z3 routing is a lower bound: the land-side "
         r"and board-plane 1-V redistribution is not in the coupled solution; a sheet estimate "
         r"adds " + mac.get("LandPmin", NA) + "--" + mac.get("LandPmax", NA) + r"~W "
         r"(Section~\ref{sec:compare}). Feed limit with the Z3 lower-bound ledger.",
         r"\end{table}", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
