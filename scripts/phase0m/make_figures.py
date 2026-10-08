#!/usr/bin/env python3
"""Phase-0M Part 43 -- figures FIG-0M-A .. FIG-0M-J, all generated from the result files."""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow, FancyBboxPatch

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0m"))
OUT = R / "results" / "phase0m"
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
    rows = [r for r in rd("tsv_geometry_sensitivity.csv")
            if r["rail"] == "Z2_LV_1000A" and r["j_max"] == "100000000.0"]
    fig, ax = plt.subplots(2, 2, figsize=(9, 6.4))
    pols = ["A_min_capability", "B_fixed_count", "C_fixed_pitch", "E_fixed_cu_fraction"]
    cols = dict(zip(pols, ["#1b6ca8", "#c0392b", "#27ae60", "#8e44ad"]))
    for p in pols:
        s = sorted([r for r in rows if r["policy"] == p and r["feasible"] == "True"],
                   key=lambda r: ff(r, "r_um"))
        if not s:
            continue
        x = [ff(r, "r_um") for r in s]
        ax[0, 0].plot(x, [ff(r, "R_single_mohm") for r in s], "o-", color=cols[p], label=p)
        ax[0, 1].plot(x, [ff(r, "R_field_mohm") * 1e3 for r in s], "o-", color=cols[p], label=p)
        ax[1, 0].plot(x, [ff(r, "n_allocated") for r in s], "o-", color=cols[p], label=p)
        ax[1, 1].plot(x, [ff(r, "phi_cu") for r in s], "o-", color=cols[p], label=p)
    allr = sorted({ff(r, "r_um") for r in rows})
    a0 = sorted([r for r in rows if r["policy"] == "A_min_capability"],
                key=lambda r: ff(r, "r_um"))
    ax[0, 0].plot([ff(r, "r_um") for r in a0],
                  [ff(r, "I_max_per_via_mA") for r in a0], "k--", lw=1,
                  label="I_max per via (mA)")
    ax[0, 0].set(xlabel="TSV radius (um)", ylabel="single-via R (mOhm) / I_max (mA)",
                 yscale="log", title="A1  single via: R falls, capacity rises")
    ax[0, 1].set(xlabel="TSV radius (um)", ylabel="FIELD R (nOhm)", yscale="log",
                 title="A2  the FIELD: radius cancels under A and E")
    ax[1, 0].set(xlabel="TSV radius (um)", ylabel="vias allocated", yscale="log",
                 title="A3  allocated count")
    ax[1, 1].set(xlabel="TSV radius (um)", ylabel="copper area fraction",
                 title="A4  copper fraction -> k_eff, CTE_eff")
    for a in ax.ravel():
        a.legend(fontsize=6)
    fig.suptitle("FIG-0M-A  TSV radius, pitch and allocation: the field is not the via",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_A_tsv_allocation.png")
    plt.close(fig)


# ------------------------------------------------------------------ B
def fig_b():
    rows = [r for r in rd("tsv_geometry_sensitivity.csv")
            if r["rail"] == "Z2_LV_1000A" and r["j_max"] == "100000000.0"
            and r["policy"] == "C_fixed_pitch" and r["feasible"] == "True"]
    rows = sorted(rows, key=lambda r: ff(r, "r_um"))
    x = [ff(r, "r_um") for r in rows]
    fig, ax = plt.subplots(1, 4, figsize=(12, 3.0))
    ax[0].plot(x, [ff(r, "P_joule_W") for r in rows], "o-", color="#c0392b")
    ax[0].set(xlabel="r (um)", ylabel="field Joule loss (W)", title="ELECTRICAL")
    ax[1].plot(x, [ff(r, "k_z") for r in rows], "o-", label="k_z", color="#1b6ca8")
    ax[1].plot(x, [ff(r, "k_xy") for r in rows], "s--", label="k_xy", color="#5dade2")
    ax[1].set(xlabel="r (um)", ylabel="effective k (W/m.K)", title="THERMAL")
    ax[1].legend(fontsize=6)
    ax2 = ax[2].twinx()
    ax[2].plot(x, [ff(r, "E_xy_MPa") / 1e3 for r in rows], "o-", color="#27ae60")
    ax2.plot(x, [ff(r, "CTE_eff") * 1e6 for r in rows], "s--", color="#e67e22")
    ax[2].set(xlabel="r (um)", ylabel="E_xy (GPa)", title="MECHANICAL")
    ax2.set_ylabel("CTE_eff (ppm/K)", color="#e67e22")
    ax[3].plot(x, [ff(r, "aspect_ratio") for r in rows], "o-", color="#8e44ad",
               label="aspect ratio h/2r")
    ax[3].plot(x, [ff(r, "n_required") / max(ff(r, "n_available"), 1) for r in rows],
               "s--", color="#34495e", label="n_req / n_avail")
    ax[3].axhline(10.0, color="#8e44ad", ls=":", lw=1)
    ax[3].axhline(1.0, color="#34495e", ls=":", lw=1)
    ax[3].set(xlabel="r (um)", ylabel="ratio", yscale="log", title="FEASIBILITY")
    ax[3].legend(fontsize=6)
    fig.suptitle("FIG-0M-B  one TSV variable, four domains (fixed-pitch allocation, 1000 A)",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_B_tsv_coupling.png")
    plt.close(fig)


# ------------------------------------------------------------------ C
def fig_c():
    import crowding as CR
    from conduction3d import FVConduction
    c = CR.build("TSV_pad_RDL")
    xn, yn, zn = c.mesh(refine=1.3)
    m = FVConduction(xn, yn, zn)
    m.assign(c.sigma_fn())
    X, Y, Z = np.meshgrid(m.xc, m.yc, m.zc, indexing="ij")
    inj = (X ** 2 + Y ** 2 <= c.r_via ** 2) & (Z <= m.zc[0] + 1e-18)
    edge = ((X >= m.xc[-1] - 1e-18) | (X <= m.xc[0] + 1e-18)
            | (Y >= m.yc[-1] - 1e-18) | (Y <= m.yc[0] + 1e-18))
    gnd = edge & (m.sigma > c.sigma_metal * 0.5)
    m.solve(inj, 1.0, gnd, axis_in=2, axis_gnd=0)
    J = m.j_field()
    metal = m.sigma > c.sigma_metal * 0.5
    Jm = np.where(metal, J, np.nan)
    kz = int(np.argmin(np.abs(m.zc - (c.z_rdl0 + c.t_rdl / 2))))
    jy = int(np.argmin(np.abs(m.yc)))
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    jav = np.nanmean(Jm)
    p0 = ax[0].pcolormesh(m.xc * 1e6, m.yc * 1e6, (Jm[:, :, kz] / jav).T,
                          cmap="inferno", shading="auto")
    ax[0].set(xlabel="x (um)", ylabel="y (um)", xlim=(-40, 60),
              title=f"in the RDL layer, z = {m.zc[kz]*1e6:.1f} um")
    fig.colorbar(p0, ax=ax[0], label="|J| / J_avg")
    p1 = ax[1].pcolormesh(m.xc * 1e6, m.zc * 1e6, (Jm[:, jy, :] / jav).T,
                          cmap="inferno", shading="auto")
    ax[1].set(xlabel="x (um)", ylabel="z (um)", xlim=(-40, 60),
              title="cross-section through the via axis")
    fig.colorbar(p1, ax=ax[1], label="|J| / J_avg")
    fig.suptitle("FIG-0M-C  TSV -> landing pad -> RDL: current crowding at the constriction",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_C_crowding_map.png")
    plt.close(fig)


# ------------------------------------------------------------------ D
def fig_d():
    import routing as RT
    comps = RT.tile_layout(RT.DESIGN["tile_side_mm"])
    byname = {c.name: c for c in comps}
    nets = RT.nets()
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    zc = {c.layer: c.z_um for c in comps}
    lay_order = sorted(set(zc.values()))
    col = {"gan_hs": "#c0392b", "gan_ls": "#e67e22", "inductor": "#1b6ca8",
           "cap_fly": "#27ae60", "cap_out": "#16a085", "pad_in": "#7f8c8d",
           "pad_out": "#2c3e50"}
    for c in comps:
        ax[0].add_patch(Rectangle((c.x_mm - c.w_mm / 2, c.z_um / 1000 - 0.06),
                                  c.w_mm, 0.12, fc=col.get(c.kind, "#bdc3c7"),
                                  ec="k", lw=.4, alpha=.85))
        ax[0].text(c.x_mm, c.z_um / 1000 + 0.10, c.name, ha="center", fontsize=5.5)
    for n in nets:
        a, b = byname[n.src], byname[n.dst]
        ls = "-" if n.geom == "vertical" else "--"
        ax[0].plot([a.x_mm, b.x_mm], [a.z_um / 1000, b.z_um / 1000], ls,
                   color="k", lw=0.6 + 1.6 * min(n.i_rms_a / 21.0, 1.0), alpha=.6)
    ax[0].set(xlabel="x within the VR tile (mm)", ylabel="z (mm)",
              title="LEVEL 1  intra-VR component-terminal graph\n"
                    "(line width ~ current; solid = vertical via stack)")
    lv = ["board", "BGA", "VR cell", "TSV field", "microbump", "RDL / POL", "die"]
    y = np.arange(len(lv))[::-1]
    p = {"LEVEL 2": (1, 4), "LEVEL 3": (5, 5)}
    for i, name in enumerate(lv):
        ax[1].add_patch(FancyBboxPatch((0.1, y[i] - 0.28), 1.6, 0.56,
                                       boxstyle="round,pad=0.02",
                                       fc="#ecf0f1", ec="k", lw=.6))
        ax[1].text(0.9, y[i], name, ha="center", va="center", fontsize=8)
    ax[1].annotate("", xy=(1.95, y[2]), xytext=(1.95, y[4]),
                   arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=2))
    ax[1].text(2.05, (y[2] + y[4]) / 2, "LEVEL 2\nVR -> package\nMODELLED",
               fontsize=7, color="#c0392b", va="center")
    ax[1].annotate("", xy=(-0.25, y[5]), xytext=(-0.25, y[6]),
                   arrowprops=dict(arrowstyle="<->", color="#27ae60", lw=2))
    ax[1].text(-0.35, (y[5] + y[6]) / 2, "LEVEL 3\npackage -> POL\nMODELLED",
               fontsize=7, color="#27ae60", va="center", ha="right")
    ax[1].annotate("", xy=(1.95, y[2] + 0.3), xytext=(1.95, y[2] - 0.3),
                   arrowprops=dict(arrowstyle="<->", color="#2980b9", lw=2))
    ax[1].text(2.05, y[2] + 0.45, "LEVEL 1  intra-VR\nABSENT BEFORE PHASE 0M",
               fontsize=7, color="#2980b9", va="center")
    ax[1].set(xlim=(-1.6, 4.2), ylim=(-0.8, len(lv) - 0.2), title="the three routing levels")
    ax[1].axis("off")
    fig.suptitle("FIG-0M-D  intra-VR and package routing", fontsize=10)
    fig.savefig(OUT / "FIG_0M_D_routing_graph.png")
    plt.close(fig)


# ------------------------------------------------------------------ E
def fig_e():
    rows = rd("component_partition_templates.csv")
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
    names = [r["template"] for r in rows]
    util = [ff(r, "die_shadow_utilisation") for r in rows]
    hgt = [ff(r, "stack_height_um") for r in rows]
    cols = ["#27ae60" if u <= 1 else "#c0392b" for u in util]
    ax[0].barh(range(len(rows)), util, color=cols)
    ax[0].axvline(1.0, color="k", ls="--", lw=1)
    ax[0].set_yticks(range(len(rows)))
    ax[0].set_yticklabels([n.replace("_", " ") for n in names], fontsize=6.5)
    ax[0].set(xlabel="VR-array footprint / 500 mm2 die shadow",
              title="does the whole VR array fit under the die?")
    ax[0].invert_yaxis()
    ax[1].scatter(hgt, util, c=cols, s=70, zorder=3)
    for i, n in enumerate(names):
        ax[1].annotate(n.split("_")[0], (hgt[i], util[i]), fontsize=6.5,
                       xytext=(4, 4), textcoords="offset points")
    ax[1].axhline(1.0, color="k", ls="--", lw=1)
    ax[1].set(xlabel="stack height (um)", ylabel="die-shadow utilisation",
              title="height against area: the two binding constraints")
    fig.suptitle("FIG-0M-E  component-partition templates "
                 "(green = fits the die shadow, red = does not)", fontsize=10)
    fig.savefig(OUT / "FIG_0M_E_partition_templates.png")
    plt.close(fig)


# ------------------------------------------------------------------ F
def fig_f():
    dec = rd("z5_path_decomposition.csv")
    cmp_ = rd("z5_pcb_vs_rdl.csv")
    fam = rd("z5_architecture_comparison.csv")
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    lab = [r["path"] for r in cmp_]
    loop = [ff(r, "loop_R_mohm_per_sq") for r in cmp_]
    ax[0].bar(lab, loop, color=["#7f8c8d", "#c0392b"])
    for i, v in enumerate(loop):
        ax[0].text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=7)
    ax[0].set(ylabel="loop R per square (mOhm)",
              title="F1  the interposer RDL is 4.6x WORSE\nper square than the PCB row")
    gaps = [r for r in dec if r["stack"].startswith("ectc2024_primary_gap")]
    gv = [float(r["stack"].split("gap")[1]) for r in gaps]
    ax[1].plot(gv, [ff(r, "P_loop_w") for r in gaps], "o-", color="#c0392b")
    ax[1].set(xlabel="VR-to-die gap (mm)", ylabel="Z5-LV lateral loss (W)",
              title="F2  loss versus the lateral gap")
    for nc, c in (("1", "#c0392b"), ("2", "#e67e22"), ("4", "#27ae60")):
        s = sorted([r for r in fam if r["n_die_edges_fed"] == nc],
                   key=lambda r: ff(r, "v_lateral"))
        if s:
            ax[2].plot([ff(r, "v_lateral") for r in s],
                       [ff(r, "P_lateral_w") for r in s], "o-", color=c,
                       label=f"{nc} die edge(s) fed")
    ax[2].axhline(126.09, color="k", ls="--", lw=1, label="Z1 total, 126.1 W")
    ax[2].set(xlabel="lateral rail voltage (V)", ylabel="lateral loss (W)",
              xscale="log", yscale="log", title="F3  the Z5 family")
    ax[2].legend(fontsize=6)
    fig.suptitle("FIG-0M-F  Z5 lateral path: PCB versus RDL, and the voltage family",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_F_z5_decomposition.png")
    plt.close(fig)


# ------------------------------------------------------------------ G
def fig_g():
    rows = rd("effective_layer_properties.csv")
    sel = [r for r in rows if r["layer"] in
           ("TSV_array", "microbump_underfill", "C4_underfill", "BGA_mold",
            "RDL_dielectric")]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
    labs, kz, kxy = [], [], []
    for r in sel:
        labs.append(f"{r['layer'].replace('_',' ')}\n{r['geometry']}")
        kz.append(ff(r, "RVE_kz"))
        kxy.append(ff(r, "RVE_kxy"))
    x = np.arange(len(labs))
    ax[0].bar(x - .2, kz, .4, label="k_z (through)", color="#1b6ca8")
    ax[0].bar(x + .2, kxy, .4, label="k_xy (in plane)", color="#e67e22")
    ax[0].set_xticks(x); ax[0].set_xticklabels(labs, fontsize=5.0, rotation=30, ha="right")
    ax[0].set(yscale="log", ylabel="effective k (W/m.K)",
              title="G1  every heterogeneous layer is anisotropic")
    ax[0].legend(fontsize=6)
    tsv = [r for r in rows if r["layer"] == "TSV_array"]
    x2 = np.arange(len(tsv))
    for key, lab, c in (("RVE_kxy", "explicit-geometry RVE", "#2c3e50"),
                        ("maxwell_kxy", "Maxwell-Garnett", "#e67e22"),
                        ("framework_kxy", "pre-existing framework", "#c0392b"),
                        ("reuss_kxy", "Reuss (series)", "#95a5a6")):
        ax[1].plot(x2, [ff(r, key) for r in tsv], "o-", label=lab, color=c)
    ax[1].set_xticks(x2)
    ax[1].set_xticklabels([r["geometry"].replace("r_cu=", "r=").replace(" t_ox=0.5", "")
                           for r in tsv], fontsize=5.5, rotation=20, ha="right")
    ax[1].set(ylabel="in-plane k (W/m.K)", yscale="log",
              title="G2  which homogenization is right for k_xy?")
    ax[1].legend(fontsize=6)
    fig.suptitle("FIG-0M-G  anisotropic effective thermal properties, validated on RVEs",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_G_k_tensors.png")
    plt.close(fig)


# ------------------------------------------------------------------ H
def fig_h():
    rows = rd("cooling_architecture_sensitivity.csv")
    arcs = sorted({r["architecture"] for r in rows})
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    cols = dict(zip(arcs, ["#1b6ca8", "#c0392b", "#27ae60", "#8e44ad", "#e67e22"]))
    for a in arcs:
        s = sorted([r for r in rows if r["architecture"] == a],
                   key=lambda r: ff(r, "m_dot_g_s"))
        md = [ff(r, "m_dot_g_s") for r in s]
        ax[0].plot(md, [ff(r, "h_effective_W_m2K") for r in s], "o-", color=cols[a], label=a)
        ax[1].plot(md, [ff(r, "T_j_C") for r in s], "o-", color=cols[a], label=a)
        ax[2].plot([ff(r, "pump_W") for r in s], [ff(r, "T_j_C") for r in s], "o-",
                   color=cols[a], label=a)
    ax[0].axhline(166000, color="k", ls="--", lw=1.2)
    ax[0].text(2, 1.8e5, "the calibrated h_top = 166 kW/m2K", fontsize=6.5)
    ax[0].set(xlabel="coolant mass flow (g/s)", ylabel="effective h on the footprint (W/m2K)",
              xscale="log", yscale="log", title="H1  what cooler gives 166 kW/m2K?")
    ax[1].axhline(84.0, color="k", ls="--", lw=1.2)
    ax[1].text(2, 88, "the 84 C reference target", fontsize=6.5)
    ax[1].axvline(1.6, color="#7f8c8d", ls=":", lw=1.2)
    ax[1].text(1.7, 150, "the source's stated 1.6 g/s", fontsize=6.5, rotation=90)
    ax[1].set(xlabel="coolant mass flow (g/s)", ylabel="junction temperature (C)",
              xscale="log", title="H2  junction temperature")
    ax[2].axhline(84.0, color="k", ls="--", lw=1.2)
    ax[2].set(xlabel="pumping power (W)", ylabel="junction temperature (C)", xscale="log",
              title="H3  the cost the Robin boundary never charges")
    ax[0].legend(fontsize=5.5)
    fig.suptitle("FIG-0M-H  physical cooling architectures behind one calibrated coefficient",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_H_cooling.png")
    plt.close(fig)


# ------------------------------------------------------------------ I
def fig_i():
    fig, ax = plt.subplots(figsize=(6.6, 5.4))
    nodes = {"E": (0, 1), "T": (1.6, 1), "M": (1.6, -0.4), "D": (0, -0.4)}
    lab = {"E": "ELECTRICAL", "T": "THERMAL", "M": "MECHANICAL", "D": "DAMAGE"}
    for k, (x, y) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - .48, y - .2), .96, .4,
                                    boxstyle="round,pad=0.03",
                                    fc="#ecf0f1" if k != "D" else "#fdecea",
                                    ec="k", lw=1))
        ax.text(x, y, lab[k], ha="center", va="center", fontsize=8.5, weight="bold")
    def arrow(a, b, c, ls, txt, dx=0.0, dy=0.0, w=1.6):
        (x0, y0), (x1, y1) = nodes[a], nodes[b]
        ax.annotate("", xy=(x1 - .5 * np.sign(x1 - x0) if abs(x1 - x0) > .1 else x1,
                            y1 - .22 * np.sign(y1 - y0) if abs(y1 - y0) > .1 else y1),
                    xytext=(x0 + .5 * np.sign(x1 - x0) if abs(x1 - x0) > .1 else x0,
                            y0 + .22 * np.sign(y1 - y0) if abs(y1 - y0) > .1 else y0),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=w, ls=ls))
        ax.text((x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy, txt, fontsize=6.4, color=c,
                ha="center")
    arrow("E", "T", "#27ae60", "-", "loss -> heat", dy=.10)
    arrow("T", "E", "#27ae60", "-", "rho(T), Rds(T)", dy=-.10)
    arrow("T", "M", "#27ae60", "-", "thermal strain", dx=.42)
    arrow("M", "E", "#c0392b", "--", "geometry -> R\ndR/R = 0.16 %\n(0.7 % of rho(T))",
          dy=.30, dx=-.15, w=1.1)
    arrow("M", "T", "#e67e22", "--", "TIM bond line\n1.5 K at 4 %", dx=.60, w=1.1)
    arrow("M", "D", "#c0392b", ":", "damage accrues", dy=-.10, w=1.1)
    arrow("D", "E", "#c0392b", ":", "cracked area\n+33 % R at 25 %", dx=-.62, w=1.1)
    arrow("D", "T", "#c0392b", ":", "delamination\n+12.5 K at 25 %", dy=.10, w=1.1)
    ax.text(0.8, 1.62, "SOLID = built and iterated to a fixed point\n"
                       "DASHED = absent, magnitude measured in Phase 0M\n"
                       "DOTTED = absent, requires a damage model",
            fontsize=6.6, ha="center")
    ax.text(0.8, -1.05, "ETM-L1  E <-> T -> M      THE CURRENT FRAMEWORK\n"
                        "ETM-L2  E <-> T <-> M     not built; not needed before damage\n"
                        "ETM-L3  E <-> T <-> M <-> DAMAGE   needed for failure progression",
            fontsize=7, ha="center", family="monospace")
    ax.set(xlim=(-1.3, 2.9), ylim=(-1.35, 1.9))
    ax.axis("off")
    ax.set_title("FIG-0M-I  ETM coupling matrix, with the size of every absent arrow",
                 fontsize=10)
    fig.savefig(OUT / "FIG_0M_I_coupling_matrix.png")
    plt.close(fig)


# ------------------------------------------------------------------ J
def fig_j():
    rows = rd("PHYSICS_PRIORITY_MATRIX.csv")
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    rows = sorted(rows, key=lambda r: (order[r["priority"]], r["id"]))
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    cols = {"P0": "#c0392b", "P1": "#e67e22", "P2": "#f1c40f", "P3": "#95a5a6"}
    sty = {"CURRENTLY MODELLED": "#27ae60", "PARTIALLY MODELLED": "#f39c12",
           "NOT MODELLED": "#ecf0f1"}
    for i, r in enumerate(rows):
        y = len(rows) - i
        ax.add_patch(Rectangle((0, y - .4), 3.6, .8, fc=sty[r["status"]], ec="k", lw=.5))
        ax.text(0.08, y, f"{r['id']}  {r['physics']}", va="center", fontsize=7.2)
        ax.add_patch(Rectangle((3.7, y - .4), .5, .8, fc=cols[r["priority"]], ec="k", lw=.5))
        ax.text(3.95, y, r["priority"], va="center", ha="center", fontsize=7.5,
                color="w", weight="bold")
        ax.text(4.35, y, r["status"], va="center", fontsize=6.3)
    ax.set(xlim=(-0.1, 7.6), ylim=(0.2, len(rows) + 1.4))
    ax.axis("off")
    ax.text(0.0, len(rows) + 1.0,
            "P0 before architecture conclusions   P1 before absolute reliability   "
            "P2 refinement   P3 out of scope", fontsize=7)
    ax.set_title("FIG-0M-J  physics-priority ladder", fontsize=10)
    fig.savefig(OUT / "FIG_0M_J_priority_ladder.png")
    plt.close(fig)


if __name__ == "__main__":
    only = sys.argv[1:] or list("abcdefghij")
    for k in only:
        fn = globals().get(f"fig_{k}")
        if fn:
            fn(); print(f"  FIG-0M-{k.upper()}")
    print("figures done")
