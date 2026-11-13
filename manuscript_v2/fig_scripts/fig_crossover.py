"""Fig. 6 (proposed): the direct-feed requirement.

Platform-inclusive loss difference  dP(R) = P_Z2(R) - P_Z1  against the swept external
feed-loop resistance R of the direct-fed backside regulator, one panel per admissible
scenario (each with its own y-scale; S2 has no admissible Z1 reference and is omitted).
Below zero the backside architecture has the lower platform-inclusive loss. R* is the
crossover. Context marker: the embedded architecture's own package 48-V loop
(supply + return, 20 C), package_network.json. Data: direct_feed_crossover.json.
"""
import numpy as np
import matplotlib.pyplot as plt
import style as S

S.setup()
cx = S.J("direct_feed_crossover.json")["scenarios"]
pk = S.J("package_network.json")
r_z1 = 1e3 * pk["loop"]["Z1"]["r_loop_ohm"]       # 2.262 mOhm at 20 C

fig, axes = plt.subplots(2, 1, figsize=(S.COL_W, 3.15), sharex=True,
                         gridspec_kw={"hspace": 0.38, "left": 0.16, "right": 0.97,
                                      "bottom": 0.13, "top": 0.93})
spec = [("HV_S0", "S0, smoothed input", (-1.6, 3.2)),
        ("HV_S1", "S1, pulsed at the buck duty", (-48, 64))]
for k, (ax, (s, name, yl)) in enumerate(zip(axes, spec)):
    c = cx[s]
    sw = [p for p in c["sweep"] if p.get("feasible", True) and p["P_total_w"] is not None]
    R = np.array([p["R_mohm"] for p in sw])
    dP = np.array([p["P_total_w"] for p in sw]) - c["P_Z1_w"]
    ax.set_xscale("log")
    ax.set_xlim(0.01, 40)
    ax.set_ylim(*yl)
    ax.axhspan(yl[0], 0, color=S.Z2, alpha=0.07, lw=0, zorder=0)
    ax.axhspan(0, yl[1], color=S.Z1, alpha=0.07, lw=0, zorder=0)
    ax.axhline(0, color=S.AXIS, lw=0.6, zorder=1)
    ax.plot(R, dP, color=S.INK, lw=1.2, zorder=3)
    rs = c["R_star_mohm"]
    ax.plot(rs, 0, "o", ms=4.5, mfc="white", mec=S.INK, mew=0.9, zorder=5)
    eta = 100 * c["efficiency_Z2_at_R_star"]
    ax.annotate(f"$R^*$ = {rs:.2f} m$\\Omega$\n($\\eta$ = {eta:.1f} %)", (rs, 0),
                xytext=(-7, 7), textcoords="offset points",
                ha="right", va="bottom", fontsize=7, color=S.INK)
    adv = c["advantage_at_zero_feed_w"]
    ax.annotate(f"lossless feed: Z2 lower by {adv:.1f} W", (0.012, -adv),
                xytext=(0, -3), textcoords="offset points", ha="left", va="top",
                fontsize=6.3, color=S.INK2)
    # context: the embedded architecture's own package 48-V loop resistance
    ax.axvline(r_z1, color=S.MUTED, lw=0.6, ls=(0, (2, 2)), zorder=2)
    if k == 0:
        ax.text(r_z1 * 1.06, yl[1] * 0.96, "Z1 package\n48-V loop", ha="left", va="top",
                fontsize=6.3, color=S.INK2)
    ax.text(0.012, yl[1] * 0.93, "Z1 lower", ha="left", va="top", fontsize=6.5,
            color=S.INK2)
    ax.text(0.012, yl[0] * 0.08, "Z2 lower", ha="left", va="top", fontsize=6.5,
            color=S.INK2)
    ax.set_ylabel(r"$P_\mathrm{Z2}-P_\mathrm{Z1}$ (W)")
    S.panel(ax, "ab"[k], name, y=1.03)
    ax.grid(axis="x", which="major", color=S.GRID, lw=0.5)
axes[1].set_xlabel(r"Direct-feed loop resistance $R_\mathrm{feed}$ (m$\Omega$)")
S.save(fig, "fig6_crossover")
