"""Fig. 10: every production model against its matched reference (matched-reference checks only;
self-consistency checks -- solver and mesh -- are reported in the uncertainty table).
The series-rule RDL card is drawn open ('replaced': the reference tensor is adopted).
The complete-package row is CalculiX against MOOSE on the identical Z1 mesh
(tcpmt_revision/fullpkg_verification.json, summary.Z1.identical_mesh.T_max_err_pct_of_rise,
runtime_s_median). The cold-plate row is the production plate model (three-wall H1 Nusselt
number) against the conjugate CFD solution (tcpmt_revision/cooling_spec.json,
plate.cfd_comparison: mean base temperature rise). The structural-solver row is the iterative
solver of the production meshes against the direct solver on the same base mesh (die warpage;
final_closure/mesh_convergence.json structural_solver_checks).

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
fp = (S.JP(S.TR / "fullpkg_verification.json") or {}).get("summary") or {}
z1 = fp.get("Z1") or {}
if isinstance((z1.get("identical_mesh") or {}).get("T_max_err_pct_of_rise"), (int, float)):
    rt = z1.get("runtime_s_median") or {}
    M["fullpkg_Z1"] = {"stage": "fullpkg_Z1",
                       "error": z1["identical_mesh"]["T_max_err_pct_of_rise"] / 100.0,
                       "production_runtime_s": rt.get("calculix"),
                       "reference_runtime_s": rt.get("moose_hypre")}

# the plate model in force against the conjugate CFD solution (the matrix row predates it)
cf = ((S.JP(S.TR / "cooling_spec.json") or {}).get("plate") or {}).get("cfd_comparison") or {}
if isinstance(cf.get("dT_base_mean_rel_diff"), (int, float)) and "cooling_icepak" in M:
    M["cooling_icepak"] = dict(M["cooling_icepak"], error=cf["dT_base_mean_rel_diff"])
elif "cooling_icepak" in M:
    del M["cooling_icepak"]                 # never the superseded correlation
# iterative (production) against direct structural solver, same base mesh and field
sc = (S.JP(S.FC / "mesh_convergence.json") or {}).get("structural_solver_checks") or {}
_it = next((v for k, v in sc.items() if "ITERATIVE" in k and v.get("ok")), None)
_dr = next((v for k, v in sc.items() if "SPOOLES" in k and v.get("ok")), None)
if _it and _dr:
    M["solver_iter_direct"] = {"stage": "solver_iter_direct",
                               "error": _it["die_warpage_pv_um"] / _dr["die_warpage_pv_um"] - 1,
                               "production_runtime_s": _it.get("wall_s"),
                               "reference_runtime_s": _dr.get("wall_s")}

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
                              ("pkg_rdl_Z2", "Z2 ring-feed network", "O")]),
    ("Package thermal", [("thermal_column_aedt_Z1", "Z1 unit cell vs AEDT", "C"),
                         ("thermal_column_moose_Z1", "Z1 unit cell vs MOOSE", "O"),
                         ("thermal_column_aedt_Z2", "Z2 unit cell vs AEDT", "C"),
                         ("thermal_column_moose_Z2", "Z2 unit cell vs MOOSE", "O")]),
    ("Complete package", [("fullpkg_Z1", "Z1 package, $T_\\max$ vs MOOSE", "O")]),
    ("Thermoelastic", [("mech_bilayer_closed_form", "Bilayer vs closed form", "F"),
                       ("mech_bilayer_aedt", "Bilayer vs AEDT", "C"),
                       ("solver_iter_direct", "Iterative vs direct solver, warpage", "S")]),
    ("Cooling boundary", [("cooling_icepak", "Cold plate vs CFD", "C")]),
]
REPLACED = {"rdl_tier_kz"}          # drawn open: the card was replaced by the reference
MK = {"C": dict(marker="o", mfc=S.INK, mec=S.INK),          # commercial FEM / CFD
      "O": dict(marker="s", mfc="white", mec=S.INK),        # open-source FEM
      "F": dict(marker="D", mfc="white", mec=S.INK),        # closed form
      "S": dict(marker="x", mfc=S.INK, mec=S.INK)}          # self-consistency check
NOTE = {"rdl_tier_kz": "replaced", "fullpkg_Z1": "identical mesh, % of rise",
        "solver_iter_direct": "not in $U_{95}$"}


def fmt_t(t):
    if t is None:
        return "–"
    if t < 1e-3:
        return f"{t * 1e6:.1f} µs"
    if t < 1:
        return f"{t * 1e3:.0f} ms"
    return f"{t:.0f} s" if t < 1e3 else f"{t / 60:.0f} min"


# a benchmark missing from the matrix (or without a numeric error) is dropped, never invented
# the plate model in force against the conjugate CFD solution (the matrix row predates it)
cf = ((S.JP(S.TR / "cooling_spec.json") or {}).get("plate") or {}).get("cfd_comparison") or {}
if isinstance(cf.get("dT_base_mean_rel_diff"), (int, float)) and "cooling_icepak" in M:
    M["cooling_icepak"] = dict(M["cooling_icepak"], error=cf["dT_base_mean_rel_diff"])
elif "cooling_icepak" in M:
    del M["cooling_icepak"]                 # never the superseded correlation
# iterative (production) against direct structural solver, same base mesh and field
sc = (S.JP(S.FC / "mesh_convergence.json") or {}).get("structural_solver_checks") or {}
_it = next((v for k, v in sc.items() if "ITERATIVE" in k and v.get("ok")), None)
_dr = next((v for k, v in sc.items() if "SPOOLES" in k and v.get("ok")), None)
if _it and _dr:
    M["solver_iter_direct"] = {"stage": "solver_iter_direct",
                               "error": _it["die_warpage_pv_um"] / _dr["die_warpage_pv_um"] - 1,
                               "production_runtime_s": _it.get("wall_s"),
                               "reference_runtime_s": _dr.get("wall_s")}

GROUPS = [(g, [it for it in items if it[0] in M and isinstance(M[it[0]].get("error"), (int, float))])
          for g, items in GROUPS]
# the plate model in force against the conjugate CFD solution (the matrix row predates it)
cf = ((S.JP(S.TR / "cooling_spec.json") or {}).get("plate") or {}).get("cfd_comparison") or {}
if isinstance(cf.get("dT_base_mean_rel_diff"), (int, float)) and "cooling_icepak" in M:
    M["cooling_icepak"] = dict(M["cooling_icepak"], error=cf["dT_base_mean_rel_diff"])
elif "cooling_icepak" in M:
    del M["cooling_icepak"]                 # never the superseded correlation
# iterative (production) against direct structural solver, same base mesh and field
sc = (S.JP(S.FC / "mesh_convergence.json") or {}).get("structural_solver_checks") or {}
_it = next((v for k, v in sc.items() if "ITERATIVE" in k and v.get("ok")), None)
_dr = next((v for k, v in sc.items() if "SPOOLES" in k and v.get("ok")), None)
if _it and _dr:
    M["solver_iter_direct"] = {"stage": "solver_iter_direct",
                               "error": _it["die_warpage_pv_um"] / _dr["die_warpage_pv_um"] - 1,
                               "production_runtime_s": _it.get("wall_s"),
                               "reference_runtime_s": _dr.get("wall_s")}

GROUPS = [(g, items) for g, items in GROUPS if items]
n = sum(len(g[1]) for g in GROUPS) + len(GROUPS)
fig = plt.figure(figsize=(S.COL_W, 0.135 * n + 0.95))
ax = fig.add_axes([0.43, 0.07, 0.33, 0.84])
ax.set_xscale("log")
ax.set_xlim(1e-5, 60)
ax.set_ylim(n - 0.3, -0.7)
ax.grid(axis="x", which="major", color=S.GRID, lw=0.5)
ax.grid(axis="y", visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_yticks([])
ax.axvline(1.0, color=S.MUTED, lw=0.6, ls=(0, (2, 2)), zorder=1)
ax.text(1.0, -0.65, "1 %", ha="center", va="bottom", fontsize=6.5, color=S.INK2)
ax.set_xlabel("|relative error| vs reference (%)", labelpad=1.5)
y = 0
xr_text = 1.03          # axes fraction for runtime columns
ax.text(xr_text + 0.02, -0.65, "model", transform=ax.get_yaxis_transform(), ha="left",
        va="bottom", fontsize=6.5, color=S.INK2)
ax.text(xr_text + 0.38, -0.65, "reference", transform=ax.get_yaxis_transform(), ha="left",
        va="bottom", fontsize=6.5, color=S.INK2)
for gname, items in GROUPS:
    ax.text(-1.28, y + 0.15, gname, transform=ax.get_yaxis_transform(), ha="left",
            va="center", fontsize=6.6, color=S.INK, fontstyle="italic")
    y += 1
    for stage, lab, kind in items:
        r = M[stage]
        e = abs(r["error"]) * 100
        ax.text(-0.04, y, lab, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=6.5, color=S.INK2)
        ax.plot([1e-5, e], [y, y], color=S.GRID, lw=0.6, zorder=1)
        mk = dict(MK[kind])
        if stage in REPLACED:
            mk["mfc"] = "white"
        ax.plot(e, y, ls="none", ms=3.6, mew=0.8, zorder=3, **mk)
        if stage in NOTE:
            right = e < 1e-2
            ax.annotate(NOTE[stage], (e, y), xytext=(5 if right else -5, 0),
                        textcoords="offset points", ha="left" if right else "right",
                        va="center", fontsize=6.5, color=S.INK2,
                        bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none"))
        ax.text(xr_text + 0.02, y, fmt_t(r.get("production_runtime_s")),
                transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=6.5,
                color=S.INK2)
        ax.text(xr_text + 0.38, y, fmt_t(r.get("reference_runtime_s")),
                transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=6.5,
                color=S.INK2)
        y += 1
h = [Line2D([], [], ls="none", ms=3.6, mew=0.8, label=l, **MK[k]) for k, l in
     (("C", "commercial FE / CFD"), ("O", "open-source FE"), ("F", "closed form"),
      ("S", "direct solver"))]
h.append(Line2D([], [], ls="none", ms=3.6, mew=0.8, marker="o", mfc="white", mec=S.INK,
                label="replaced card"))
fig.legend(handles=h, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.94),
           columnspacing=0.8, handletextpad=0.3, fontsize=6.5)
S.save(fig, "fig10_verification")
