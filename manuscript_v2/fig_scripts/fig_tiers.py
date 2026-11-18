"""Fig. 8 (paper Fig. 9): the three integrations under the three-tier comparison at S0.

(a) Package-internal loss at a common temperature (25 and 100 C, no coupling) and coupled
    under cooling A (the same top cold plate) and cooling B (the same top and bottom plates).
(b) Peak temperature with the GaN junction rating, (c) die warpage, (d) critical-joint
displacement and (e) stabilized local inelastic strain increment at L0, under A and B.

Every value is read from the generated results_macros.tex (itself produced from the case files
by scripts/tcpmt_manuscript_macros.py and scripts/tcpmt_review_macros.py), so the figure and
Table II print the same numbers. Z3 under A and B is the coupled land-side case
(z3_land_t40_{A,B}_fvmap); its common-temperature loss is PIsoLandZthree / PIsoHotLandZthree.
Error bars: +/-U from research/tcpmt_revision/uncertainty.json. Crossed bars: a rating fails
(research/tcpmt_revision/feasibility.json limits applied to the plotted peak temperature, and
any failed check of the matching feasibility case).
Open diamond: the interface-free bottom plate (a bound), Z2 only -- the Z3 interface-free case
predates the coupled land side and is not drawn against it.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import style as S

S.setup()
ARCHS = ("Z1", "Z2", "Z3")
WORD = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}


def m(name):
    v = S.macro(name)
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


unc = S.JP(S.TR / "uncertainty.json") or {}
U = unc.get("U") or {}
feas = S.JP(S.TR / "feasibility.json") or {}
limits = feas.get("limits") or {}
GAN = m("GanTjMax") or limits.get("gan_Tj_C")
TIER_CASE = {("A", "Z3"): "etm_Z3_HV_S0__z3_land_t40_A_fvmap.json",
             ("B", "Z3"): "etm_Z3_HV_S0__z3_land_t40_B_fvmap.json"}

# key -> (macro stem, uncertainty key)
KEYS = {"P": ("Ploss", "P"), "Tmax": ("Tmax", "T"), "warp": ("Warp", "warp"),
        "du": ("Du", "du"), "eps": ("Eps", "eps")}


def value(key, grp, a):
    if key == "P" and grp in ("iso25", "iso100"):
        hot = "Hot" if grp == "iso100" else ""
        return m(f"PIso{hot}Land{WORD[a]}") if a == "Z3" else m(f"PIso{hot}{WORD[a]}")
    if grp not in ("A", "B"):
        return None
    return m(f"{KEYS[key][0]}{grp}{WORD[a]}")


def err(key, grp, a):
    if grp not in ("A", "B"):
        return None
    return U.get(f"{grp}.{a}.{KEYS[key][1]}")


def infeasible(grp, a):
    """A rating fails: the plotted peak temperature exceeds the GaN rating, or a check of the
    feasibility record for the same case file fails."""
    T = value("Tmax", grp, a)
    if T is not None and GAN is not None and T > GAN:
        return True
    rec = (feas.get("cases") or {}).get(f"{grp}_{a}") or {}
    want = TIER_CASE.get((grp, a))
    if want and rec.get("case") != want:
        return False
    return any(isinstance(c, dict) and not c.get("ok", True)
               for c in (rec.get("checks") or {}).values())


# interface-free bottom plate (bound), Z2 only
bound = {}
bc = S.JP(S.SENS / "etm_Z2_HV_S0__z2_cooled.json")
if bc:
    crit = ((bc.get("mechanics") or {}).get("joint_search") or {}).get("critical") or {}
    bound = {"P": bc.get("P_loss_w"), "Tmax": (bc.get("thermal") or {}).get("T_max_C"),
             "warp": (bc.get("mechanics") or {}).get("die_warpage_pv_um"), "du": crit.get("du_um")}

panels = [("P", "a", "Package-internal loss (W)", [("25 °C", "iso25"), ("100 °C", "iso100"),
                                                   ("A", "A"), ("B", "B")], "{:.0f}"),
          ("Tmax", "b", "Peak temperature (°C)", [("A", "A"), ("B", "B")], "{:.0f}"),
          ("warp", "c", "Die warpage (µm)", [("A", "A"), ("B", "B")], "{:.1f}"),
          ("du", "d", r"Joint driver $\Delta u_\mathrm{c}$ (µm)", [("A", "A"), ("B", "B")],
           "{:.2f}"),
          ("eps", "e", r"$\Delta\varepsilon_\mathrm{in}$, L0 ($10^{-3}$/cyc.)",
           [("A", "A"), ("B", "B")], "{:.1f}")]
fig, axes = plt.subplots(1, 5, figsize=(S.DBL_W, 2.25),
                         gridspec_kw={"width_ratios": [1.75, 1, 1, 1, 1], "wspace": 0.36,
                                      "left": 0.05, "right": 0.995, "bottom": 0.16,
                                      "top": 0.80})
w = 0.25
any_infeasible = False
for ax, (key, letter, title, groups, fmt) in zip(axes, panels):
    tops = []
    for _, g in groups:
        for a in ARCHS:
            v = value(key, g, a)
            if v is not None:
                tops.append(v + (err(key, g, a) or 0.0))
    if key in bound and bound[key] is not None:
        tops.append(bound[key])
    if key == "Tmax" and GAN:
        tops.append(GAN)
    top = 1.16 * max(tops) if tops else 1.0
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylim(0, top)
    if key == "Tmax" and GAN:
        ax.axhline(GAN, color=S.INK2, lw=0.7, ls=(0, (4, 2)), zorder=4)
        ax.text(len(groups) - 0.42, GAN + top * 0.012, f"GaN rating {GAN:.0f} °C", ha="right",
                va="bottom", fontsize=6.5, color=S.INK2, zorder=6,
                bbox=dict(fc="white", ec="none", pad=0.4))
    for j, (lab, g) in enumerate(groups):
        for n, a in enumerate(ARCHS):
            v = value(key, g, a)
            xc = j + (n - 1) * (w + 0.02)
            if v is None:
                S.pending(ax, xc, top * 0.03, f"{a} {g} {key}", "results_macros.tex",
                          transform=ax.transData, rotation=90, ha="center", va="bottom")
                continue
            S.rbar(ax, xc, v, w, S.ARCH[a])
            bad = g in ("A", "B") and infeasible(g, a)
            if bad:
                any_infeasible = True
                ax.add_patch(Rectangle((xc - w / 2, 0), w, v, fc="none", ec="white", lw=0,
                                       hatch="xxxx", zorder=3))
            e = err(key, g, a)
            if e:
                ax.errorbar(xc, v, yerr=e, fmt="none", ecolor=S.INK, elinewidth=0.6,
                            capsize=1.4, capthick=0.6, zorder=5)
            inside = v > 0.34 * top and not bad
            ylab = v * 0.5 if inside else v + (e or 0.0) + top * 0.025
            if key == "Tmax" and not inside and GAN and abs(ylab - GAN) < 0.12 * top:
                ylab = GAN + top * 0.09
            ax.text(xc, ylab, fmt.format(v), ha="center", va="center" if inside else "bottom",
                    rotation=90, fontsize=6.5, color="white" if inside else S.INK, zorder=6,
                    bbox=None if inside else dict(fc="white", ec="none", pad=0.2))
            if g == "B" and a == "Z2" and bound.get(key) is not None:
                ax.plot(xc, bound[key], "D", ms=3.6, mfc="white", mec=S.INK, mew=0.7,
                        zorder=7)
    ax.set_xticks(range(len(groups)), [l for l, _ in groups])
    ax.tick_params(axis="x", length=0, pad=2)
    S.panel(ax, letter, title, y=1.04)
axes[0].axvline(1.5, color=S.GRID, lw=0.8, zorder=0)
axes[0].text(0.5, axes[0].get_ylim()[1] * 0.985, "no coupling", ha="center", va="top",
             fontsize=6.5, color=S.INK2)
axes[0].text(3.0, axes[0].get_ylim()[1] * 0.985, "coupled", ha="center", va="top",
             fontsize=6.5, color=S.INK2)
handles = [Patch(fc=S.ARCH[a], ec="none", label=S.ARCH_NAME[a]) for a in ARCHS]
if bound:
    handles.append(Line2D([], [], marker="D", ls="none", mfc="white", mec=S.INK, ms=4,
                          label="Z2, interface-free bottom plate (bound)"))
if any_infeasible:
    handles.append(Patch(fc=S.Z3, ec="white", hatch="xxxx", lw=0,
                         label="infeasible (rating exceeded)"))
handles.append(Line2D([], [], color=S.INK, lw=0.6, marker="_", ms=4, label="±U"))
fig.legend(handles=handles, loc="upper center", ncol=len(handles),
           bbox_to_anchor=(0.52, 1.02), columnspacing=1.1, handletextpad=0.5)
fig.text(0.52, 0.01, "A: the same top cold plate   ·   B: the same top and bottom cold plates "
         "(bottom plate through a 50-µm TIM under the cell grid)   ·   smoothed input (S0)   ·   "
         "Z3: coupled land side, 40 µm", ha="center", va="bottom", fontsize=6.5, color=S.INK2)
S.save(fig, "fig8_tiers")
