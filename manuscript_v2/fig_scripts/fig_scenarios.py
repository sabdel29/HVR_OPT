"""Fig. 8 (proposed): embedded vs backside across the three named 48-V input scenarios.

One quantity per panel (small multiples, one y-axis each). The Z1 operating point under
S2 is inadmissible (critical joint above the SAC305 solidus); it is drawn hatched and
clipped at the panel top so it does not set the scale. Whiskers: measured discretisation
uncertainty (global: mesh change; local: declared local-mesh U). Data: final_results.json,
ordering.json (research/final_closure), read-only.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
import style as S

S.setup()
fin = S.J("final_results.json")
od = S.J("ordering.json")["orderings"]
SC = ["HV_S0", "HV_S1", "HV_S2"]
TICK = ["S0", "S1", "S2"]


def g(a, s, k):
    return next(x.get(k) for x in fin if x["arch"] == a and x["scenario"] == s)


def unc(key, s):
    return (od[key].get("uncertainty_rel") or {}).get(s) or od[key].get("mesh_change") or 0.0


panels = [
    ("P_loss_package_internal_w", "Package-internal loss (W)", "{:.1f}", 220),
    ("T_max_C", "Peak temperature (°C)", "{:.1f}", 175),
    ("die_warpage_pv_um", "Die warpage, P–V (µm)", "{:.1f}", 85),
    ("du_c_um", r"Joint driver $\Delta u_\mathrm{c}$ (µm)", "{:.2f}", 4.2),
]

fig, axes = plt.subplots(1, 5, figsize=(S.DBL_W, 2.05),
                         gridspec_kw={"wspace": 0.42, "left": 0.055, "right": 0.995,
                                      "bottom": 0.20, "top": 0.80})
x = np.arange(3)
w = 0.34
for ax, (key, title, fmt, ytop) in zip(axes[:4], panels):
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(0, ytop)
    for n, a in enumerate(("Z1", "Z2")):
        for j, s in enumerate(SC):
            v = g(a, s, key)
            xc = x[j] + (n - 0.5) * (w + 0.03)
            infeasible = bool(g(a, s, "T_joint_at_or_above_solder_solidus"))
            if infeasible:
                hv = ytop * 0.97
                ax.add_patch(Rectangle((xc - w / 2, 0), w, hv, fc="white",
                                       ec=S.ARCH[a], lw=0.6, hatch="//////", zorder=2))
                ax.text(xc, hv * 1.005, "▲", ha="center", va="bottom", fontsize=5,
                        color=S.INK2)
                ax.text(xc, hv * 0.5, fmt.format(v), ha="center", va="center", fontsize=6,
                        color=S.INK, rotation=90,
                        bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none"))
                continue
            S.rbar(ax, xc, v, w, S.ARCH[a])
            u = unc(key if key != "P_loss_package_internal_w" else key, s)
            ax.errorbar(xc, v, yerr=v * u, fmt="none", ecolor=S.INK, elinewidth=0.6,
                        capsize=1.6, capthick=0.6, zorder=3)
            if s == "HV_S0":
                ax.text(xc, v * 0.5 if v > 0.30 * ytop else v + v * u + ytop * 0.03,
                        fmt.format(v), ha="center",
                        va="center" if v > 0.30 * ytop else "bottom", fontsize=6.2,
                        color="white" if v > 0.30 * ytop else S.INK, rotation=90)
    ax.set_xticks(x, TICK)
    ax.tick_params(axis="x", length=0, pad=2)
    for lab in ax.get_xticklabels():
        lab.set_fontsize(7)

titles = [p[1] for p in panels] + [r"Local $\Delta\varepsilon_\mathrm{in}$ ($10^{-3}$/cycle)"]
for k, (ax, t) in enumerate(zip(axes, titles)):
    S.panel(ax, "abcde"[k], t, y=1.04)

# (e) local inelastic response with its declared uncertainty
ax = axes[4]
ax.set_xlim(-0.6, 2.6)
ax.set_ylim(0, 11)
for n, a in enumerate(("Z1", "Z2")):
    for j, s in enumerate(SC):
        xc = x[j] + (n - 0.5) * (w + 0.03)
        v = g(a, s, "d_eps_in_per_cycle")
        if v is None:
            ax.text(xc, 0.4, "n/a", ha="center", va="bottom", fontsize=6, color=S.INK2,
                    rotation=90)
            continue
        u = g(a, s, "local_mesh_U_rel") or 0.0
        ext = bool(g(a, s, "T_joint_outside_norton_calibration"))
        ax.errorbar(xc, 1e3 * v, yerr=1e3 * v * u, fmt="o", ms=4.2, color=S.ARCH[a],
                    mfc="white" if ext else S.ARCH[a], mec=S.ARCH[a], mew=0.9,
                    ecolor=S.INK, elinewidth=0.6, capsize=1.6, capthick=0.6, zorder=3)
ax.set_xticks(x, TICK)
ax.tick_params(axis="x", length=0, pad=2)
for lab in ax.get_xticklabels():
    lab.set_fontsize(6.3)

handles = [Patch(fc=S.Z1, ec="none", label="Z1 embedded"),
           Patch(fc=S.Z2, ec="none", label="Z2 backside"),
           Patch(fc="white", ec=S.INK2, hatch="//////", lw=0.6,
                 label="inadmissible (joint ≥ SAC305 solidus), clipped"),
           Line2D([], [], marker="o", ls="none", mfc="white", mec=S.INK2, ms=4,
                  label="joint beyond solder-model calibration")]
fig.legend(handles=handles, loc="upper center", ncol=4, bbox_to_anchor=(0.52, 1.03),
           columnspacing=1.4, handletextpad=0.5)
fig.text(0.52, 0.035, "48-V input scenarios:  S0 smoothed (local input decoupling)   ·   "
         "S1 pulsed at the buck duty $D$   ·   S2 pulsed at the overall ratio 1/48",
         ha="center", va="bottom", fontsize=7, color=S.INK2)
S.save(fig, "fig8_scenarios")
