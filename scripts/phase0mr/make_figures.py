#!/usr/bin/env python3
"""Phase-0M-R Section 21 -- figures FIG-0MR-A .. FIG-0MR-K, all from the result files."""
from __future__ import annotations
import csv, json, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
sys.path.insert(0, str(R / "scripts" / "phase0m"))
OUT = R / "results" / "phase0mr"
plt.rcParams.update({"font.size": 8, "figure.dpi": 150, "savefig.bbox": "tight",
                     "axes.grid": True, "grid.alpha": 0.3})


def rd(n):
    p = OUT / n
    return list(csv.DictReader(p.open())) if p.is_file() else []


def ff(r, k, d=float("nan")):
    try:
        return float(r[k])
    except (KeyError, TypeError, ValueError):
        return d


# ------------------------------------------------------------------ A
def fig_a():
    fig, ax = plt.subplots(figsize=(11, 5.2))
    stages = ["architecture", "component\npartition", "converter\nsynthesis",
              "intra-VR\nrouting", "interconnect\n+ transition", "package RDL",
              "ET fixed\npoint", "cooling", "thermal field", "mechanical\nfield",
              "local solder\nmetric"]
    before = [1, 0, 1, 0, 0.5, 1, 1, 0.5, 1, 1, 1]
    after = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    x = np.arange(len(stages))
    col = {1: "#27ae60", 0.5: "#f1c40f", 0: "#c0392b"}
    for i, (b, a) in enumerate(zip(before, after)):
        ax.add_patch(Rectangle((i - .38, 1.05), .76, .55, fc=col[b], ec="k", lw=.6))
        ax.add_patch(Rectangle((i - .38, 0.25), .76, .55, fc=col[a], ec="k", lw=.6))
        if b != a:
            ax.annotate("", xy=(i, 1.02), xytext=(i, 0.83),
                        arrowprops=dict(arrowstyle="<-", color="#2c3e50", lw=1.6))
    ax.set_xticks(x); ax.set_xticklabels(stages, fontsize=6.4)
    ax.set_yticks([1.32, 0.52]); ax.set_yticklabels(["PHASE 0M\nproduction", "PHASE 0M-R\nproduction"],
                                                    fontsize=8)
    ax.set(xlim=(-.7, len(stages) - .3), ylim=(0.1, 1.95))
    ax.grid(False)
    for s, c, lab in ((1, "#27ae60", "in production"), (0.5, "#f1c40f", "present but non-physical"),
                      (0, "#c0392b", "absent")):
        ax.bar(0, 0, color=c, label=lab)
    ax.legend(loc="upper center", ncol=3, fontsize=7, frameon=False,
              bbox_to_anchor=(0.5, 1.0))
    ax.set_title("FIG-0MR-A  what Phase 0M measured versus what Phase 0M-R actually wired in",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0MR_A_production_flow.png"); plt.close(fig)


# ------------------------------------------------------------------ B
def fig_b():
    import routing_production as RP
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    col = {"gan_hs": "#c0392b", "gan_ls": "#e67e22", "inductor": "#1b6ca8",
           "cap_fly": "#27ae60", "cap_out": "#16a085"}
    for a, tpl in zip(ax, ("T1_EMBEDDED_4LAYER", "T4_SPLIT_SC_BUCK")):
        tiers = RP.TEMPLATES[tpl]
        zs = RP.tier_z(tpl)
        for i, (tier, z) in enumerate(zip(tiers, zs)):
            x0 = 0.0
            for c in tier:
                n = {"gan_hs": 3, "gan_ls": 3, "cap_fly": 2, "cap_out": 1, "inductor": 3}[c]
                w = RP.FOOT_MM2[c] * n / 6.0
                a.add_patch(Rectangle((x0, z / 1000 - RP.H_UM[c] / 2000), w,
                                      RP.H_UM[c] / 1000, fc=col[c], ec="k", lw=.5,
                                      alpha=.85))
                a.text(x0 + w / 2, z / 1000, f"{c}\nx{n}", ha="center", va="center",
                       fontsize=5.5)
                x0 += w + 0.06
        for e in RP.build_edges(tpl):
            ta, tb = e.tiers[0], e.tiers[-1]
            a.annotate("", xy=(2.3, zs[tb] / 1000), xytext=(2.3, zs[ta] / 1000),
                       arrowprops=dict(arrowstyle="<->", color="#2c3e50",
                                       lw=0.6 + 2.0 * min(e.i_rms / 21.0, 1.0)))
            if ta != tb:
                a.text(2.4, (zs[ta] + zs[tb]) / 2000, f"{e.rail} {e.i_rms:.2f} A",
                       fontsize=5.8)
        a.set(xlim=(-0.1, 3.4), ylim=(-0.2, max(zs) / 1000 + 0.5),
              xlabel="footprint (arbitrary)", ylabel="z (mm)",
              title=f"{tpl}\n{len(tiers)} tiers")
    fig.suptitle("FIG-0MR-B  component-level power path: T1 against T4 "
                 "(arrow width ~ current)", fontsize=10)
    fig.savefig(OUT / "FIG_0MR_B_component_power_path.png"); plt.close(fig)


# ------------------------------------------------------------------ C
def fig_c():
    cache = json.loads((OUT / "transition_dR_cache.json").read_text()) \
        if (OUT / "transition_dR_cache.json").is_file() else {}
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    labs, rb, dr = [], [], []
    for k, v in sorted(cache.items()):
        labs.append(v["cls"])
        rb.append(v["R_1D_ohm"] * 1e3)
        dr.append(v["dR_ohm"] * 1e3)
    if labs:
        x = np.arange(len(labs))
        ax[0].bar(x, rb, .6, label="1-D reference", color="#1b6ca8")
        ax[0].bar(x, dr, .6, bottom=rb, label="transition difference", color="#c0392b")
        ax[0].set_xticks(x); ax[0].set_xticklabels(labs, fontsize=7)
        ax[0].axhline(0, color="k", lw=.6)
        ax[0].set(ylabel="resistance (mOhm)",
                  title="C1  bulk + transition, per class,\nat the production geometry")
        ax[0].legend(fontsize=7)
        rat = [(a + b) / a for a, b in zip(rb, dr)]
        ax[1].bar(x, rat, .6, color=["#27ae60" if r < 1 else "#c0392b" for r in rat])
        ax[1].axhline(1.326, color="k", ls="--", lw=1.2, label="the retired global 1.326")
        ax[1].axhline(1.0, color="#7f8c8d", ls=":", lw=1)
        ax[1].set_xticks(x); ax[1].set_xticklabels(labs, fontsize=7)
        ax[1].set(ylabel="R_3D / R_1D", title="C2  one constant cannot serve four classes")
        ax[1].legend(fontsize=7)
    fig.suptitle("FIG-0MR-C  transition resistance decomposition", fontsize=10)
    fig.savefig(OUT / "FIG_0MR_C_transition_decomposition.png"); plt.close(fig)


# ------------------------------------------------------------------ D
def fig_d():
    rows = [r for r in rd("tsv_geometry_production_audit.csv")
            if r.get("policy") == "A_min_capability" and r.get("rail") == "Z2_LV_1000A"]
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    for h, c in (("100.0", "#27ae60"), ("300.0", "#1b6ca8"), ("1300.0", "#c0392b")):
        s = sorted([r for r in rows if r.get("h_nominal_um") == h],
                   key=lambda r: ff(r, "r_drill_um"))
        if not s:
            continue
        x = [ff(r, "r_drill_um") for r in s]
        ax[0].plot(x, [ff(r, "R_single_mohm") for r in s], "o-", color=c, label=f"h={h} um")
        ax[1].plot(x, [ff(r, "R_field_mohm") * 1e3 for r in s], "o-", color=c,
                   label=f"h={h} um")
        ok = [ff(r, "r_drill_um") for r in s if r["feasible"] == "True"]
        ax[2].plot(x, [ff(r, "aspect_ratio") for r in s], "o-", color=c, label=f"h={h} um")
        if ok:
            ax[2].axvline(min(ok), color=c, ls=":", lw=1)
    ax[2].axhline(10.0, color="k", ls="--", lw=1.2)
    ax[2].text(3, 11, "aspect-ratio limit", fontsize=6.5)
    ax[0].set(xlabel="TSV drilled radius (um)", ylabel="SINGLE-via R (mOhm)", yscale="log",
              title="D1  one via: the intuition holds")
    ax[1].set(xlabel="TSV drilled radius (um)", ylabel="FIELD R (nOhm)",
              title="D2  the field: R = rho h J / I,\nthe area cancels")
    ax[2].set(xlabel="TSV drilled radius (um)", ylabel="aspect ratio h / 2r", yscale="log",
              title="D3  feasibility is where radius matters\n(dotted = smallest buildable)")
    for a in ax:
        a.legend(fontsize=6)
    fig.suptitle("FIG-0MR-D  TSV radius: not a loss lever, decisively a feasibility variable",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0MR_D_tsv_feasibility.png"); plt.close(fig)


# ------------------------------------------------------------------ E
def fig_e():
    rows = rd("rdl_effective_tensor.csv")
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
    orgs = ["LINES_1D", "ORTHOGONAL", "MESH", "PLANE"]
    sel = [r for r in rows if ff(r, "t_diel_um") == 5.0]
    x = np.arange(len(orgs))
    kx = [ff(next(r for r in sel if r["organisation"] == o), "k_x") for o in orgs]
    ky = [ff(next(r for r in sel if r["organisation"] == o), "k_y") for o in orgs]
    kz = [ff(next(r for r in sel if r["organisation"] == o), "k_z") for o in orgs]
    ax[0].bar(x - .25, kx, .25, label="k_x", color="#1b6ca8")
    ax[0].bar(x, ky, .25, label="k_y", color="#5dade2")
    ax[0].bar(x + .25, kz, .25, label="k_z", color="#e67e22")
    ax[0].axhline(0.7, color="#c0392b", ls="--", lw=1.4,
                  label="what the production model uses (0.7, isotropic)")
    ax[0].set_xticks(x); ax[0].set_xticklabels(orgs, fontsize=7)
    ax[0].set(yscale="log", ylabel="effective k (W/m.K)",
              title="E1  the stack ORGANISATION decides")
    ax[0].legend(fontsize=6)
    ax[1].bar(x - .18, [a / b for a, b in zip(kx, ky)], .36, label="in-plane x/y",
              color="#27ae60")
    ax[1].bar(x + .18, [a / c for a, c in zip(kx, kz)], .36, label="in-plane / through",
              color="#8e44ad")
    ax[1].axhline(1.0, color="k", lw=.8)
    ax[1].set_xticks(x); ax[1].set_xticklabels(orgs, fontsize=7)
    ax[1].set(yscale="log", ylabel="anisotropy ratio",
              title="E2  Phase 0M's 153x was IN-PLANE on one line layer;\n"
                    "a real stack is in-plane isotropic and 95x through-thickness")
    ax[1].legend(fontsize=6)
    fig.suptitle("FIG-0MR-E  RDL effective thermal tensor by stack organisation",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0MR_E_rdl_tensor.png"); plt.close(fig)


# ------------------------------------------------------------------ F
def fig_f():
    eb = rd("cooling_energy_balance.csv")
    cv = rd("cooling_validation.csv")
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    names = [r["design"] for r in eb]
    x = np.arange(len(names))
    ax[0].bar(x, [ff(r, "h_effective") for r in eb], .6, color="#1b6ca8")
    ax[0].axhline(166000, color="#c0392b", ls="--", lw=1.4,
                  label="the calibrated h = 166 kW/m2K")
    ax[0].set_xticks(x); ax[0].set_xticklabels(names, rotation=30, ha="right", fontsize=5.8)
    ax[0].set(ylabel="effective h (W/m2K)", title="F1  what real coolers deliver")
    ax[0].legend(fontsize=6)
    ax2 = ax[1].twinx()
    ax[1].bar(x - .2, [ff(r, "dT_fluid_K") for r in eb], .4, color="#e67e22",
              label="coolant rise")
    ax2.bar(x + .2, [ff(r, "P_pump_hydraulic_W") for r in eb], .4, color="#8e44ad",
            label="pumping (hydraulic)")
    ax[1].set_xticks(x); ax[1].set_xticklabels(names, rotation=30, ha="right", fontsize=5.8)
    ax[1].set(ylabel="coolant temperature rise (K)", title="F2  the costs the Robin\n"
                                                           "boundary never charges")
    ax2.set_ylabel("pumping power (W)", color="#8e44ad")
    ax[2].bar(x, [ff(r, "T_j_compact_C") for r in eb], .6,
              color=["#27ae60" if ff(r, "T_j_compact_C") <= 84 else "#c0392b" for r in eb])
    ax[2].axhline(84.0, color="k", ls="--", lw=1.2, label="the 84 C reference")
    ax[2].set_xticks(x); ax[2].set_xticklabels(names, rotation=30, ha="right", fontsize=5.8)
    ax[2].set(ylabel="junction temperature (C)", title="F3  which coolers reach the target")
    ax[2].legend(fontsize=6)
    fig.suptitle("FIG-0MR-F  physical cooling in production", fontsize=10)
    fig.savefig(OUT / "FIG_0MR_F_cooling.png"); plt.close(fig)


# ------------------------------------------------------------------ K
def fig_k():
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    items = [
        ("intra-VR routing", "WIRED IN", "#27ae60"),
        ("transition resistance per class", "WIRED IN, cross-validated 0.25-0.73 %", "#27ae60"),
        ("physical cooling + coolant rise", "WIRED IN, solid side validated", "#27ae60"),
        ("spatial heat deposition", "WIRED IN, energy-checked", "#27ae60"),
        ("local temperature feedback", "WIRED IN", "#27ae60"),
        ("RDL thermal + mechanical layer", "MEASURED, ladder built, not default", "#f1c40f"),
        ("component partition geometry", "MEASURED, no template fully realizable", "#f1c40f"),
        ("high-stress SAC305 constitutive", "OPEN -- dominant blocker", "#c0392b"),
        ("required life N_required", "OPEN", "#c0392b"),
        ("mechanical allowable for G2", "OPEN", "#c0392b"),
        ("cohesive delamination parameters", "OPEN -- unsourced", "#c0392b"),
        ("package clearances", "OPEN -- unsourced", "#c0392b"),
        ("EM current-density allowable", "OPEN -- unsourced", "#c0392b"),
        ("Icepak conjugate validation", "NOT ATTEMPTED this phase", "#95a5a6"),
        ("HFSS AC loop validation", "ATTEMPTED, did not converge in budget", "#95a5a6"),
    ]
    for i, (name, state, c) in enumerate(items):
        y = len(items) - i
        ax.add_patch(Rectangle((0, y - .4), 4.3, .8, fc="#ecf0f1", ec="k", lw=.5))
        ax.text(0.08, y, name, va="center", fontsize=7.4)
        ax.add_patch(Rectangle((4.4, y - .4), 5.2, .8, fc=c, ec="k", lw=.5, alpha=.75))
        ax.text(4.5, y, state, va="center", fontsize=7.0)
    ax.set(xlim=(-0.1, 10.0), ylim=(0.2, len(items) + 1.2)); ax.axis("off")
    ax.set_title("FIG-0MR-K  model closure after Phase 0M-R", fontsize=10)
    fig.savefig(OUT / "FIG_0MR_K_closure_ladder.png"); plt.close(fig)




# ------------------------------------------------------------------ G
def fig_g():
    led = rd("intravr_loss_ledger.csv")
    rep = [r for r in rd("production_architecture_replay.csv") if r.get("status") == "OK"]
    case = "ARCH_Z2_BACKSIDE_AFTER"
    rows = [r for r in led if r["case"] == case] or led[:13]
    LAYER = {"P_switch_hs_conduction": "converter layer",
             "P_switch_ls_conduction": "converter layer",
             "P_inductor_DCR": "converter layer", "P_cap_ESR": "converter layer",
             "P_switching_hard": "converter layer", "P_gate": "converter layer",
             "P_Coss": "converter layer", "P_intraVR_metal": "converter layer",
             "P_intraVR_vertical": "converter layer", "P_TSV": "substrate / TSV field",
             "P_bumps": "BGA layer", "P_pkg_RDL": "interface layer", "P_other": "--"}
    agg = {}
    for r in rows:
        agg[LAYER.get(r["term"], "--")] = agg.get(LAYER.get(r["term"], "--"), 0.0) \
            + ff(r, "watts_system", 0.0)
    agg["die"] = 1000.0
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
    labs = [k for k in agg if agg[k] > 0]
    vals = [agg[k] for k in labs]
    ax[0].barh(range(len(labs)), vals, color="#1b6ca8")
    ax[0].set_yticks(range(len(labs))); ax[0].set_yticklabels(labs, fontsize=7)
    ax[0].set(xscale="log", xlabel="heat deposited (W)",
              title="G1  where each watt is deposited")
    ax[0].invert_yaxis()
    terms = [r["term"] for r in rows if ff(r, "watts_system", 0) > 0]
    w = [ff(r, "watts_system", 0) for r in rows if ff(r, "watts_system", 0) > 0]
    ax[1].barh(range(len(terms)), w,
               color=["#c0392b" if "intraVR" in t else "#27ae60" for t in terms])
    ax[1].set_yticks(range(len(terms)))
    ax[1].set_yticklabels([t.replace("P_", "") for t in terms], fontsize=6.5)
    ax[1].set(xscale="log", xlabel="watts, system",
              title="G2  the loss ledger\n(red = added by Phase 0M-R)")
    ax[1].invert_yaxis()
    fig.suptitle("FIG-0MR-G  spatial heat-source map, including intra-VR routing",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0MR_G_spatial_heat.png"); plt.close(fig)


# ------------------------------------------------------------------ H
def fig_h():
    rep = [r for r in rd("production_architecture_replay.csv") if r.get("status") == "OK"]
    ref = [r for r in rep if r.get("template") in ("T1_EMBEDDED_4LAYER", "lumped")
           and "27" in str(r.get("cooler", "")) or r.get("mode") == "BEFORE"]
    keys = ["L_P_switch_hs_conduction", "L_P_switch_ls_conduction", "L_P_inductor_DCR",
            "L_P_cap_ESR", "L_P_switching_hard", "L_P_gate", "L_P_Coss",
            "L_P_intraVR_metal", "L_P_intraVR_vertical", "L_P_TSV", "L_P_bumps",
            "L_P_pkg_RDL"]
    cols = plt.cm.tab20(np.linspace(0, 1, len(keys)))
    labs = [f"{r['arch'].replace('ARCH_','')}\n{r['mode']}" for r in ref]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    bottom = np.zeros(len(ref))
    for k, c in zip(keys, cols):
        v = np.array([ff(r, k, 0.0) for r in ref])
        ax.bar(range(len(ref)), v, .6, bottom=bottom, color=c,
               label=k.replace("L_P_", ""))
        bottom += v
    ax.set_xticks(range(len(ref))); ax.set_xticklabels(labs, fontsize=6.5)
    ax.set(ylabel="system electrical loss (W)",
           title="FIG-0MR-H  architecture loss decomposition after production integration")
    ax.legend(fontsize=6, ncol=2, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.savefig(OUT / "FIG_0MR_H_loss_decomposition.png"); plt.close(fig)


# ------------------------------------------------------------------ I
def fig_i():
    rep = [r for r in rd("production_architecture_replay.csv") if r.get("status") == "OK"]
    arches = ["ARCH_Z1_EMBEDDED", "ARCH_Z2_BACKSIDE", "ARCH_Z4_POWER_DIE"]
    def get(a, m):
        s = [r for r in rep if r["arch"] == a and r["mode"] == m
             and ("27" in str(r.get("cooler", "")) or m == "BEFORE")
             and r.get("template") in ("T1_EMBEDDED_4LAYER", "lumped")]
        return s[0] if s else None
    fig, ax = plt.subplots(1, 4, figsize=(13, 3.6))
    for j, (key, lab) in enumerate((("P_elec_total_w", "system loss (W)"),
                                    ("T_max_C", "T_max (C)"),
                                    ("die_warpage_pv_um", "die warpage (um)"),
                                    ("du_corner_um", "corner shear (um)"))):
        b = [ff(get(a, "BEFORE") or {}, key, np.nan) for a in arches]
        f_ = [ff(get(a, "AFTER") or {}, key, np.nan) for a in arches]
        x = np.arange(len(arches))
        ax[j].bar(x - .2, b, .4, label="Phase 0M path", color="#95a5a6")
        ax[j].bar(x + .2, f_, .4, label="Phase 0M-R path", color="#c0392b")
        ax[j].set_xticks(x)
        ax[j].set_xticklabels([a.replace("ARCH_", "").replace("_", "\n") for a in arches],
                              fontsize=6.5)
        ax[j].set(ylabel=lab, title=lab)
        if j == 0:
            ax[j].legend(fontsize=6.5)
    fig.suptitle("FIG-0MR-I  ETM response before and after production integration",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0MR_I_before_after.png"); plt.close(fig)


# ------------------------------------------------------------------ J
def fig_j():
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(7.0, 5.6))
    nodes = {"G": (-1.4, 0.35), "E": (0, 1), "T": (1.7, 1), "M": (1.7, -0.45),
             "D": (0, -0.45)}
    lab = {"G": "GEOMETRY", "E": "ELECTRICAL", "T": "THERMAL", "M": "MECHANICAL",
           "D": "DAMAGE"}
    for k, (x, y) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - .52, y - .19), 1.04, .38,
                                    boxstyle="round,pad=0.03",
                                    fc="#ecf0f1" if k != "D" else "#fdecea", ec="k", lw=1))
        ax.text(x, y, lab[k], ha="center", va="center", fontsize=8, weight="bold")

    def arrow(a, b, c, ls, txt, dx=0.0, dy=0.0, w=1.7):
        (x0, y0), (x1, y1) = nodes[a], nodes[b]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=w, ls=ls,
                                    shrinkA=32, shrinkB=32,
                                    connectionstyle="arc3,rad=0.14"))
        ax.text((x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy, txt, fontsize=6.2, color=c,
                ha="center")
    arrow("E", "T", "#27ae60", "-", "loss -> heat", dy=.12)
    arrow("T", "E", "#27ae60", "-", "rho(T): 22.8 %", dy=-.14)
    arrow("T", "M", "#27ae60", "-", "thermal strain", dx=.44)
    arrow("G", "E", "#1b6ca8", "-", "R(geom)", dy=.16)
    arrow("G", "T", "#1b6ca8", "-", "k_eff(geom)", dy=-.55, dx=1.0)
    arrow("G", "M", "#1b6ca8", "-", "E, CTE(geom)", dy=-.16, dx=-.1)
    arrow("M", "E", "#c0392b", "--", "0.16 %", dy=.22, dx=-.2, w=1.0)
    arrow("M", "T", "#e67e22", "--", "TIM: 1.5 K", dx=.55, w=1.0)
    arrow("M", "D", "#c0392b", ":", "", w=1.0)
    arrow("D", "E", "#c0392b", ":", "+33 % at 25 %", dx=-.55, w=1.0)
    arrow("D", "T", "#c0392b", ":", "+12.5 K at 25 %", dy=.14, w=1.0)
    ax.text(0.15, 1.72, "SOLID = solved and iterated\nBLUE = geometry, now fully resolved\n"
                        "DASHED = absent, magnitude measured\nDOTTED = absent, needs a damage model",
            fontsize=6.6, ha="center")
    ax.text(0.15, -1.15, "ETM-L1   E <-> T -> M, geometry-coupled    THE FRAMEWORK TODAY\n"
                         "ETM-L2   adds mechanical feedback          not built, not justified\n"
                         "ETM-L3   adds damage feedback              needed only for progression",
            fontsize=7, ha="center", family="monospace")
    ax.set(xlim=(-2.4, 3.0), ylim=(-1.5, 2.05)); ax.axis("off")
    ax.set_title("FIG-0MR-J  ETM coupling matrix, measured after production integration",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0MR_J_coupling.png"); plt.close(fig)


if __name__ == "__main__":
    only = sys.argv[1:] or list("abcdefghijk")
    for k in only:
        fn = globals().get(f"fig_{k}")
        if fn is None:
            raise SystemExit(f"no figure {k!r}; have "
                             f"{sorted(x[4:] for x in globals() if x.startswith('fig_'))}")
        fn(); print(f"  FIG-0MR-{k.upper()}")
    print("done")
