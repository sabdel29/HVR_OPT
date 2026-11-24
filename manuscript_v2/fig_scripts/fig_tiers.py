"""Fig. 8 (paper Fig. 10): the three integrations compared three ways, in the production state
(implemented decoupling: two interleaved 6-phase clock groups and a ring of input capacitors).

(a) Package-internal loss at a common temperature (25 and 100 C, no electrothermal coupling)
    and coupled under cooling A (the same top cold plate) and cooling B (the same top and
    bottom plates).
(b) Peak temperature with the GaN junction rating, (c) die warpage, (d) the largest relative
    displacement across the ball layer, under cooling A and B.
(e) Joint response of the production local model (full cut-boundary displacement, ramped
    loads) at each case's critical joint, production state: the bar is the production solder
    law (macro MvEps<t><Arch>), the error bar its numerical U95 (MvEpsU<t><Arch>), the open
    markers the other two laws of the band (MvEpsXiao..., MvEpsMeas...).

Values: the generated results_macros.tex (scripts/tcpmt_manuscript_macros.py and
scripts/tcpmt_review_macros.py, from the case files) -- the coupled bars and Table V print the
same numbers -- and, for the common-temperature bars of the production state, the results
writer's macros_results.tex (\\WrIsoLo<Arch> at 25 C, \\WrIsoHi<Arch> at 100 C); a value not yet
generated is drawn as a visible 'pending' marker. Z3 under A and B is the coupled land-side
case. Error bars: +/-U95 from research/tcpmt_revision/uncertainty.json (production state; for
(e) the joint's numerical U95). Hatched bars: the production-state
feasibility record of that case (research/tcpmt_revision/feasibility.json, keys '<tier>_<arch>')
lists a failed limit; a record of another case file is never used.
"""
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import style as S

S.setup()
ARCHS = ("Z1", "Z2", "Z3")
WORD = {"Z1": "Zone", "Z2": "Ztwo", "Z3": "Zthree"}
STATE = S.PROD                       # production input state (implemented decoupling)


def m(name):
    v = S.macro(name)
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def _writer_macros():
    """{name: value} of the results writer's macros_results.tex (the repository copy first, then
    the campaign root's); style.macro reads results_macros.tex only."""
    out = {}
    for f in (S.REPO / "manuscript_v2" / "macros_results.tex",
              S.MACROS.parent / "macros_results.tex"):
        if f.is_file():
            for k, v in re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}", f.read_text()):
                out.setdefault(k, v.strip())
    return out


WR = _writer_macros()


def wm(name):
    v = WR.get(name)
    try:
        return float(v) if v not in (None, "", "--") else None
    except ValueError:
        return None


unc = S.JP(S.TR / "uncertainty.json") or {}
U = unc.get("U") or {}
feas = S.JP(S.TR / "feasibility.json") or {}
limits = feas.get("limits") or {}
GAN = m("GanTjMax") or limits.get("gan_Tj_C")

# key -> (macro stem, uncertainty key)
KEYS = {"P": ("Ploss", "P"), "Tmax": ("Tmax", "T"), "warp": ("Warp", "warp"),
        "du": ("Du", "du"), "eps": ("Eps", "eps")}


def value(key, grp, a):
    if key == "P" and grp in ("iso25", "iso100"):
        return wm(f"WrIso{'Hi' if grp == 'iso100' else 'Lo'}{WORD[a]}")
    if grp not in ("A", "B"):
        return None
    if key == "eps":                 # production local model, production solder law
        return m(f"MvEps{grp}{WORD[a]}")
    return m(f"{KEYS[key][0]}{grp}{WORD[a]}")


def other_laws(grp, a):
    """the joint response under the other laws of the solder-law band (same case)"""
    return [v for v in (m(f"MvEpsXiao{grp}{WORD[a]}"), m(f"MvEpsMeas{grp}{WORD[a]}"))
            if v is not None]


def err(key, grp, a):
    if grp not in ("A", "B"):
        return None
    if key == "eps":
        return m(f"MvEpsU{grp}{WORD[a]}")
    return U.get(f"{grp}.{a}.{KEYS[key][1]}")


def infeasible(grp, a):
    """The production-state feasibility record of this very case lists a failed limit."""
    rec = (feas.get("cases") or {}).get(f"{grp}_{a}") or {}
    p = S.TC.case_path(STATE, grp, a)
    if not rec or p is None or rec.get("case") != p.name:
        return False
    return bool(rec.get("fails"))


panels = [("P", "a", "Package-internal loss (W)", [("25 °C", "iso25"), ("100 °C", "iso100"),
                                                   ("A", "A"), ("B", "B")], "{:.0f}"),
          ("Tmax", "b", "Peak temperature (°C)", [("A", "A"), ("B", "B")], "{:.0f}"),
          ("warp", "c", "Die warpage (µm)", [("A", "A"), ("B", "B")], "{:.1f}"),
          ("du", "d", r"Largest ball $\Delta u_\mathrm{c}$ (µm)", [("A", "A"), ("B", "B")],
           "{:.2f}"),
          ("eps", "e", r"$\Delta\varepsilon_\mathrm{in}$ ($10^{-3}$/cycle)",
           [("A", "A"), ("B", "B")], "{:.1f}")]
fig, axes = plt.subplots(1, 5, figsize=(S.DBL_W, 2.3),
                         gridspec_kw={"width_ratios": [1.75, 1, 1, 1, 1], "wspace": 0.36,
                                      "left": 0.05, "right": 0.995, "bottom": 0.16,
                                      "top": 0.79})
w = 0.25
any_infeasible = False
for ax, (key, letter, title, groups, fmt) in zip(axes, panels):
    tops = []
    for _, g in groups:
        for a in ARCHS:
            v = value(key, g, a)
            if v is not None:
                tops.append(v + (err(key, g, a) or 0.0))
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
                src = ("macros_results.tex" if g.startswith("iso") else "results_macros.tex")
                S.pending(ax, xc, top * 0.03, f"{a} {lab}", src, transform=ax.transData,
                          rotation=90, ha="center", va="bottom")
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
            if key == "eps":
                for vo in other_laws(g, a):
                    ax.plot(xc, vo, "o", ms=2.6, mfc="white", mec=S.INK, mew=0.6, zorder=7)
            inside = v > 0.34 * top and not bad
            ylab = v * 0.5 if inside else v + (e or 0.0) + top * 0.025
            if key == "Tmax" and not inside and GAN and abs(ylab - GAN) < 0.12 * top:
                ylab = GAN + top * 0.09
            ax.text(xc, ylab, fmt.format(v), ha="center", va="center" if inside else "bottom",
                    rotation=90, fontsize=6.5, color="white" if inside else S.INK, zorder=6,
                    bbox=None if inside else dict(fc="white", ec="none", pad=0.2))
    ax.set_xticks(range(len(groups)), [l for l, _ in groups])
    ax.tick_params(axis="x", length=0, pad=2)
    S.panel(ax, letter, title, y=1.04)
axes[0].axvline(1.5, color=S.GRID, lw=0.8, zorder=0)
axes[0].text(0.5, axes[0].get_ylim()[1] * 0.985, "no coupling", ha="center", va="top",
             fontsize=6.5, color=S.INK2)
axes[0].text(3.0, axes[0].get_ylim()[1] * 0.985, "coupled", ha="center", va="top",
             fontsize=6.5, color=S.INK2)
handles = [Patch(fc=S.ARCH[a], ec="none", label=S.ARCH_NAME[a]) for a in ARCHS]
if any_infeasible:
    handles.append(Patch(fc=S.NEUTRAL, ec="white", hatch="xxxx", lw=0,
                         label="infeasible (a limit fails)"))
handles.append(Line2D([], [], color=S.INK, lw=0.6, marker="_", ms=4, label="±$U_{95}$"))
handles.append(Line2D([], [], ls="none", marker="o", ms=2.6, mfc="white", mec=S.INK, mew=0.6,
                      label="other solder laws (e)"))
fig.legend(handles=handles, loc="upper center", ncol=len(handles),
           bbox_to_anchor=(0.52, 1.02), columnspacing=1.1, handletextpad=0.5)
fig.text(0.52, 0.01, "Implemented decoupling   ·   A: the same top cold plate   ·   B: the same top "
         "and bottom cold plates (bottom plate through a 50-µm TIM under the cell grid)   ·   "
         "Z3: coupled land side, 40 µm", ha="center", va="bottom", fontsize=6.5, color=S.INK2)
S.save(fig, "fig8_tiers")
