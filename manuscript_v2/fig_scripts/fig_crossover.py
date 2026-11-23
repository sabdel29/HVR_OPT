"""Fig. 6: the 48-V feed requirement of the package-backside integration, in the production
state (implemented decoupling: two interleaved 6-phase clock groups and a ring of input
capacitors), under cooling A (one top plate) and cooling B (top and bottom plates).

Loss difference dP(R) = P_int,b + P_feed(R) - P_Z1 of a directly fed backside integration b
against the embedded regulator Z1 in the same cooling, over the external feed-loop resistance
R. Z1's 48-V path lies inside its package boundary (no external feed). The feed carries the
cells' residual pulsed current, k_rms x the average, and the average itself rises with the feed
loss: I = (P_load + P_int,b + P_feed) / V_in, P_feed = R (k_rms I)^2 -- the self-consistent
platform point of final_closure_direct_feed. The curve's zero is checked against the stored
crossover R* (research/tcpmt_revision/tier_feed_crossover.json, production state); a mismatch
above 1 % is printed. Below zero the backside integration has the lower loss. R* = 0 ('none'):
behind even with a lossless feed -- such an integration is noted, not drawn, when it lies far
off the panel's scale (Z3).
Markers: the feed resistances of Z2 evaluated in research/tcpmt_revision/platform_inclusive.json
(feeds: the BGA-ring feed through the substrate 48-V RDL, which Table V charges, and a flex
bridge estimate).
"""
import numpy as np
import matplotlib.pyplot as plt
import style as S

S.setup()
cx = S.JP(S.TR / "tier_feed_crossover.json") or {}
STATE = S.PROD
tiers = (cx.get("states") or {}).get(STATE) or {}
feeds = (S.JP(S.TR / "platform_inclusive.json") or {}).get("feeds") or {}
FEED_MARK = [(1e3 * feeds[k]["R_ohm"], lab) for k, lab in
             (("Z2_flex", "flex feed"), ("Z2_bga_fed", "BGA-ring feed")) if k in feeds]
P_LOAD = S.DR.P_LOAD_W
R_LO, R_HI = 0.01, 30.0                       # mOhm


def curve(v, R_mohm):
    """dP(R) of one backside record; None beyond feed collapse."""
    k = v["k_feed"]
    p_int = v["P_internal_w"]
    i0 = v["I_48_rms_a"] / k                  # average 48-V current at zero feed
    v_in = (P_LOAD + p_int) / i0
    p0 = P_LOAD + p_int
    out = []
    for r in R_mohm * 1e-3:
        a = k * k * r
        disc = v_in * v_in - 4.0 * a * p0
        if disc <= 0:
            out.append(np.nan)
            continue
        i = (v_in - np.sqrt(disc)) / (2.0 * a)
        out.append(p_int + a * i * i - v["P_Z1_w"])
    return np.array(out)


fig, axes = plt.subplots(2, 1, figsize=(S.COL_W, 3.3), sharex=True,
                         gridspec_kw={"hspace": 0.42, "left": 0.16, "right": 0.97,
                                      "bottom": 0.12, "top": 0.93})
spec = [("A", "Cooling A: one top cold plate"), ("B", "Cooling B: top and bottom plates")]
R = np.logspace(np.log10(R_LO), np.log10(R_HI), 400)
for k, (ax, (t, name)) in enumerate(zip(axes, spec)):
    row = tiers.get(t) or {}
    v2 = row.get("Z2")
    if not v2 or v2.get("error"):
        S.pending(ax, 0.05, 0.5, f"Z2 crossover, cooling {t}", "tier_feed_crossover.json")
        S.panel(ax, "ab"[k], name, y=1.03)
        continue
    d2 = curve(v2, R)
    ok = np.isfinite(d2)
    adv = abs(v2["advantage_at_zero_feed_w"])
    lo = min(np.nanmin(d2[ok]), 0.0)
    hi = max(0.0, min(np.nanmax(d2[ok]), 10.0 + 1.2 * adv))
    pad = 0.12 * (hi - lo)
    yl = (lo - pad, hi + pad)
    ax.set_xscale("log")
    ax.set_xlim(R_LO, R_HI)
    ax.set_ylim(*yl)
    ax.axhline(0, color=S.AXIS, lw=0.6, zorder=1)
    ax.plot(R[ok], d2[ok], color=S.ARCH["Z2"], lw=1.3, zorder=3)
    ax.annotate("Z2", (R_LO * 1.2, d2[ok][0]), xytext=(0, 3), textcoords="offset points",
                ha="left", va="bottom", fontsize=6.6, color=S.INK)
    rs = v2.get("R_star_mohm")
    if rs:                                          # a crossover exists
        # the drawn curve must cross zero where the stored R* says
        zc = np.interp(0.0, d2[ok], R[ok]) if np.all(np.diff(d2[ok]) > 0) else None
        if zc is not None and abs(zc / rs - 1) > 0.01:
            print(f"WARNING cooling {t}: curve zero {zc:.3f} mOhm vs stored R* {rs:.3f} mOhm")
        ax.plot(rs, 0, "o", ms=4.5, mfc="white", mec=S.INK, mew=0.9, zorder=5)
        right = bool(FEED_MARK) and rs > max(rf for rf, _ in FEED_MARK)
        ax.annotate(f"$R^*$ = {rs:.2f} m$\\Omega$", (rs, 0),
                    xytext=(6, -6) if right else (-6, 5), textcoords="offset points",
                    ha="left" if right else "right", va="top" if right else "bottom",
                    fontsize=6.6, color=S.INK, zorder=6)
    else:
        ax.text(R_LO * 1.2, yl[1] - 0.2 * (yl[1] - yl[0]), "Z2 behind at zero feed",
                ha="left", va="top", fontsize=6.4, color=S.INK2)
    v3 = row.get("Z3")
    d3c = None                                      # the Z3 curve, when it is drawn
    if v3 and not v3.get("error"):
        d3 = v3["P_internal_w"] - v3["P_Z1_w"]
        if d3 > yl[1]:                              # far off this scale: say it, do not draw
            ax.text(R_HI * 0.93, yl[1] - 0.05 * (yl[1] - yl[0]),
                    f"Z3: behind by {d3:.1f} W at zero feed", ha="right", va="top",
                    fontsize=6.2, color=S.INK2, zorder=6,
                    bbox=dict(fc="white", ec="none", pad=0.6))
        else:
            d3c = curve(v3, R)
            ok3 = np.isfinite(d3c) & (d3c <= yl[1])
            d3c = np.where(ok3, d3c, np.nan)
            ax.plot(R[ok3], d3c[ok3], color=S.ARCH["Z3"], lw=1.3, zorder=3)
            ax.annotate("Z3 (behind at zero feed)", (R_LO * 1.2, d3c[ok3][0]), xytext=(0, 3),
                        textcoords="offset points", ha="left", va="bottom", fontsize=6.4,
                        color=S.INK)
    drawn = [d2] + ([d3c] if d3c is not None else [])
    for rf, lab in FEED_MARK:
        ax.axvline(rf, color=S.MUTED, lw=0.6, ls=(0, (2, 2)), zorder=2)
        occ = sorted([0.0, 1.0, (0.0 - yl[0]) / (yl[1] - yl[0])]
                     + [(float(np.interp(rf, R, d)) - yl[0]) / (yl[1] - yl[0]) for d in drawn
                        if np.isfinite(np.interp(rf, R, d))])
        occ = [min(max(o, 0.0), 1.0) for o in occ]
        g0, g1 = max(zip(occ[:-1], occ[1:]), key=lambda g: g[1] - g[0])
        ax.text(rf * 1.08, yl[0] + 0.5 * (g0 + g1) * (yl[1] - yl[0]),
                f"{lab}\n{rf:.2f} m$\\Omega$", ha="left", va="center", fontsize=6.0,
                color=S.INK2, linespacing=1.0, rotation=90, zorder=4)
    ax.text(R_LO * 1.2, yl[1] - 0.05 * (yl[1] - yl[0]), "Z1 lower", ha="left", va="top",
            fontsize=6.4, color=S.INK2)
    if yl[0] < 0:
        ax.text(R_HI * 0.93, yl[0] + 0.05 * (yl[1] - yl[0]), "backside lower", ha="right",
                va="bottom", fontsize=6.4, color=S.INK2)
    ax.set_ylabel(r"$P_\mathrm{backside}-P_\mathrm{Z1}$ (W)")
    S.panel(ax, "ab"[k], name, y=1.03)
    ax.grid(axis="x", which="major", color=S.GRID, lw=0.5)
axes[1].set_xlabel(r"48-V feed-loop resistance $R_\mathrm{feed}$ (m$\Omega$)")
fig.text(0.52, 0.995, "Implemented decoupling: the feed carries $k_\\mathrm{rms}$ = "
         + (f"{tiers['A']['Z2']['k_feed']:.2f}" if tiers.get("A", {}).get("Z2") else "–")
         + " times the average current", ha="center", va="top", fontsize=6.3, color=S.INK2)
S.save(fig, "fig6_crossover")
