"""Fig. 10 (proposed): every production model against its matched reference.

Dot plot, one row per benchmark (grouped by stage), |relative error| on a log axis;
marker shape = kind of reference (never colour alone). Runtimes as text columns
(median of timed repeats, same machine). Data: accuracy_speed_matrix.json.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import style as S

S.setup()
M = {r["stage"]: r for r in S.J("accuracy_speed_matrix.json")["rows"]}

GROUPS = [
    ("Vertical interconnect", [("tsv_bulk", "Single-TSV resistance", "C"),
                               ("tsv_tile_kz", "TSV field $k_z$", "C"),
                               ("tsv_tile_kx", "TSV field $k_x$", "C")]),
    ("Redistribution tier", [("rdl_tier_kx", "RDL tier $k_x$", "C"),
                             ("rdl_tier_kz", "RDL tier $k_z$ (series rule)", "C")]),
    ("Regulator attach", [("vr_attach_dense_kz", "Attach $k_z$, 15/30 µm", "C"),
                          ("vr_attach_dense_kxy", "Attach $k_{xy}$, 15/30 µm", "C"),
                          ("vr_attach_sparse_kz", "Attach $k_z$, 30/80 µm", "C"),
                          ("vr_attach_sparse_kxy", "Attach $k_{xy}$, 30/80 µm", "C"),
                          ("vr_attach_dense_electrical", "Bump resistance, 15/30 µm", "F"),
                          ("vr_attach_sparse_electrical", "Bump resistance, 30/80 µm", "F")]),
    ("Package 48-V network", [("pkg_rdl_Z1", "Z1 network, $R_\\mathrm{eff}$", "O"),
                              ("pkg_rdl_Z2", "BGA-fed control network", "O")]),
    ("Package thermal", [("thermal_column_aedt_Z1", "Z1 unit cell vs AEDT", "C"),
                         ("thermal_column_moose_Z1", "Z1 unit cell vs MOOSE", "O"),
                         ("thermal_column_aedt_Z2", "Z2 unit cell vs AEDT", "C"),
                         ("thermal_column_moose_Z2", "Z2 unit cell vs MOOSE", "O")]),
    ("Thermoelastic", [("mech_bilayer_closed_form", "Bilayer vs closed form", "F"),
                       ("mech_bilayer_aedt", "Bilayer vs AEDT", "C"),
                       ("structural_solver_iterative_vs_direct", "Iterative vs direct solver", "S")]),
    ("Cooling boundary", [("cooling_icepak", "Cold-plate correlation vs CFD", "C")]),
    ("Discretisation", [("mesh_convergence_Z1", "Global mesh, Z1", "S"),
                        ("mesh_convergence_Z2", "Global mesh, Z2", "S")]),
]
MK = {"C": dict(marker="o", mfc=S.INK, mec=S.INK),          # commercial FEM / CFD
      "O": dict(marker="s", mfc="white", mec=S.INK),        # open-source FEM
      "F": dict(marker="D", mfc="white", mec=S.INK),        # closed form
      "S": dict(marker="x", mfc=S.INK, mec=S.INK)}          # self-consistency check
NOTE = {"rdl_tier_kz": "reference adopted", "cooling_icepak": "conservative; run as a sensitivity"}


def fmt_t(t):
    if t is None:
        return "–"
    if t < 1e-3:
        return f"{t * 1e6:.1f} µs"
    if t < 1:
        return f"{t * 1e3:.0f} ms"
    return f"{t:.0f} s" if t < 1e3 else f"{t / 60:.0f} min"


n = sum(len(g[1]) for g in GROUPS) + len(GROUPS)
fig = plt.figure(figsize=(S.COL_W, 0.128 * n + 0.75))
ax = fig.add_axes([0.42, 0.085, 0.36, 0.86])
ax.set_xscale("log")
ax.set_xlim(5e-3, 40)
ax.set_ylim(n - 0.3, -0.7)
ax.grid(axis="x", which="major", color=S.GRID, lw=0.5)
ax.grid(axis="y", visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_yticks([])
ax.axvline(1.0, color=S.MUTED, lw=0.6, ls=(0, (2, 2)), zorder=1)
ax.text(1.0, -0.65, "1 %", ha="center", va="bottom", fontsize=6, color=S.INK2)
ax.set_xlabel("|relative error| vs reference (%)", labelpad=1.5)
y = 0
xr_text = 1.03          # axes fraction for runtime columns
ax.text(xr_text + 0.02, -0.65, "model", transform=ax.get_yaxis_transform(), ha="left",
        va="bottom", fontsize=6, color=S.INK2)
ax.text(xr_text + 0.40, -0.65, "reference", transform=ax.get_yaxis_transform(), ha="left",
        va="bottom", fontsize=6, color=S.INK2)
for gname, items in GROUPS:
    ax.text(-1.15, y + 0.15, gname, transform=ax.get_yaxis_transform(), ha="left",
            va="center", fontsize=6.6, color=S.INK, fontstyle="italic")
    y += 1
    for stage, lab, kind in items:
        r = M[stage]
        e = abs(r["error"]) * 100
        ax.text(-0.04, y, lab, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=6.2, color=S.INK2)
        ax.plot([5e-3, e], [y, y], color=S.GRID, lw=0.6, zorder=1)
        ax.plot(e, y, ls="none", ms=3.6, mew=0.8, zorder=3, **MK[kind])
        if stage in NOTE:
            ax.annotate(NOTE[stage], (e, y), xytext=(-5, 0), textcoords="offset points",
                        ha="right", va="center", fontsize=5.6, color=S.INK2,
                        bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none"))
        ax.text(xr_text + 0.02, y, fmt_t(r.get("production_runtime_s")),
                transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=5.9,
                color=S.INK2)
        ax.text(xr_text + 0.40, y, fmt_t(r.get("reference_runtime_s")),
                transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=5.9,
                color=S.INK2)
        y += 1
h = [Line2D([], [], ls="none", ms=3.6, mew=0.8, label=l, **MK[k]) for k, l in
     (("C", "commercial FEM / CFD"), ("O", "open-source FEM"), ("F", "closed form"),
      ("S", "self-consistency"))]
fig.legend(handles=h, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.955),
           columnspacing=0.9, handletextpad=0.3, fontsize=6.2)
S.save(fig, "fig10_verification")
