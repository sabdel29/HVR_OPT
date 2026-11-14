"""Fig. 6: the direct-feed requirement of the backside integrations.

Platform-inclusive loss difference dP(R) = P_Zb(R) - P_Z1 of each directly fed backside
integration b (Z2, Z3) against the swept external feed-loop resistance R, one panel per
admissible scenario (S2 has no admissible Z1 reference and is omitted). Below zero the
backside integration has the lower platform-inclusive loss; R* is the crossover, and a
curve that starts above zero has no crossover (behind even with a lossless feed).
Context marker: the embedded integration's own package 48-V loop (package_network.json).
Data: direct_feed_crossover.json ("architectures" block; older files: Z2 only).
"""
import numpy as np
import matplotlib.pyplot as plt
import style as S

S.setup()
cx = S.J("direct_feed_crossover.json")
per = cx.get("architectures") or {"Z2": {"scenarios": cx["scenarios"]}}
pk = S.J("package_network.json")
r_z1 = 1e3 * pk["loop"]["Z1"]["r_loop_ohm"]

fig, axes = plt.subplots(2, 1, figsize=(S.COL_W, 3.2), sharex=True,
                         gridspec_kw={"hspace": 0.40, "left": 0.16, "right": 0.97,
                                      "bottom": 0.13, "top": 0.92})
spec = [("HV_S0", "S0, smoothed input"), ("HV_S1", "S1, pulsed at the buck duty")]
for k, (ax, (s, name)) in enumerate(zip(axes, spec)):
    curves = []
    for b, c in per.items():
        cs = (c.get("scenarios") or {}).get(s)
        if not cs:
            continue
        sw = [p for p in cs["sweep"] if p.get("feasible", True) and p["P_total_w"] is not None]
        R = np.array([p["R_mohm"] for p in sw])
        dP = np.array([p["P_total_w"] for p in sw]) - cs["P_Z1_w"]
        curves.append((b, cs, R, dP))
    # window around the crossover region: the feed becomes infeasible near R_max and dP
    # diverges there, which would flatten everything of interest near zero
    adv = max(abs(cs["advantage_at_zero_feed_w"]) for _, cs, _, _ in curves)
    lo = min(min(d[(r >= 0.01) & (r <= 100)].min() for _, _, r, d in curves), 0.0)
    hi = min(max(max(d[(r >= 0.01) & (r <= 100)].max() for _, _, r, d in curves), 0.0),
             2.0 * adv + 5.0)
    pad = 0.12 * (hi - lo)
    yl = (lo - pad, hi + pad)
    ax.set_xscale("log")
    ax.set_xlim(0.01, 100)
    ax.set_ylim(*yl)
    ax.axhline(0, color=S.AXIS, lw=0.6, zorder=1)
    for j, (b, cs, R, dP) in enumerate(curves):
        ax.plot(R, dP, color=S.ARCH[b], lw=1.3, zorder=3)
        rs = cs.get("R_star_mohm")
        # curve label at the left end, where the curves are farthest apart
        behind = not rs
        ax.annotate(b + (" (behind at zero feed)" if behind else ""), (0.012, dP[0]),
                    xytext=(0, 3), textcoords="offset points", ha="left", va="bottom",
                    fontsize=6.4, color=S.INK)
        if rs:                                       # a crossover exists
            ax.plot(rs, 0, "o", ms=4.5, mfc="white", mec=S.INK, mew=0.9, zorder=5)
            ax.annotate(f"$R^*_\\mathrm{{{b}}}$ = {rs:.2f} m$\\Omega$", (rs, 0),
                        xytext=(-6, 6 + 10 * j), textcoords="offset points", ha="right",
                        va="bottom", fontsize=6.6, color=S.INK)

    ax.axvline(r_z1, color=S.MUTED, lw=0.6, ls=(0, (2, 2)), zorder=2)
    if k == 0:
        ax.text(r_z1 * 1.06, yl[1] - 0.04 * (yl[1] - yl[0]), "Z1 package\n48-V loop",
                ha="left", va="top", fontsize=6.2, color=S.INK2)
    ax.text(0.05, yl[1] - 0.04 * (yl[1] - yl[0]), "Z1 lower", ha="left", va="top",
            fontsize=6.4, color=S.INK2)
    if yl[0] < 0:
        ax.text(90, yl[0] + 0.04 * (yl[1] - yl[0]), "backside lower", ha="right",
                va="bottom", fontsize=6.4, color=S.INK2)
    ax.set_ylabel(r"$P_\mathrm{backside}-P_\mathrm{Z1}$ (W)")
    S.panel(ax, "ab"[k], name, y=1.03)
    ax.grid(axis="x", which="major", color=S.GRID, lw=0.5)
axes[1].set_xlabel(r"Direct-feed loop resistance $R_\mathrm{feed}$ (m$\Omega$)")
S.save(fig, "fig6_crossover")
