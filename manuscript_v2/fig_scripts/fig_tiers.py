"""Fig. 8: the three integrations under the three-tier comparison at S0.

(a) Package-internal loss at a common temperature (25 and 100 C, no coupling) and coupled
    under cooling A (the same top cold plate) and cooling B (the same top and bottom plates).
(b) Peak temperature, (c) die warpage, (d) critical-joint displacement and (e) local inelastic
strain increment at the base local mesh, under A and B.
Open diamonds: the interface-free bottom plate (a bound) for the backside integrations.
Data: the production and sensitivity case files through scripts/tcpmt_manuscript_macros.py
(TIERS, case_record) and the isothermal ledger, so the figure and Table II read the same
records.
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import style as S

sys.path.insert(0, str(S.SRC / "scripts"))
import tcpmt_manuscript_macros as TM                                 # noqa: E402

S.setup()
ARCHS = ("Z1", "Z2", "Z3")
recs = {}
for t, row in TM.TIERS.items():
    for a, (kind, v) in row.items():
        r = TM.case_record(kind, a, v)
        if r is not None:
            recs[(t, a)] = r
lm = (S.J("local_mesh_study.json") or {}).get("cases") or {}
for t, row in TM.TIERS.items():
    for a, (kind, v) in row.items():
        if kind == "prod" and (t, a) in recs:
            recs[(t, a)]["eps"] = (((lm.get(f"{a}_HV_S0") or {}).get("levels") or {})
                                   .get("L0") or {}).get("d_peeq_per_cycle")
iso = {}
try:
    import final_closure_ledger as FL
    keys = ("conv", "hs", "ls", "ind", "caps", "bga", "sub", "interface", "attach", "pcb_via")
    for T in (25.0, 100.0):
        for a in ARCHS:
            iso[(T, a)] = FL.self_consistent(a, "HV_S0", {k: T for k in keys})["P_loss_w"]
except Exception as e:                                                # noqa: BLE001
    print("isothermal ledger unavailable:", e)

panels = [("P", "(a) Package-internal loss (W)", [("25 °C", "iso25"), ("100 °C", "iso100"),
                                                  ("A", "A"), ("B", "B")], "{:.0f}"),
          ("Tmax", "(b) Peak temperature (°C)", [("A", "A"), ("B", "B")], "{:.0f}"),
          ("warp", "(c) Die warpage (µm)", [("A", "A"), ("B", "B")], "{:.1f}"),
          ("du", r"(d) Joint driver $\Delta u_\mathrm{c}$ (µm)", [("A", "A"), ("B", "B")],
           "{:.2f}"),
          ("eps_m", r"(e) $\Delta\varepsilon_\mathrm{in}$, L0 ($10^{-3}$/cycle)",
           [("A", "A"), ("B", "B")], "{:.1f}")]
for r in recs.values():                         # local response in 1e-3 per cycle
    r["eps_m"] = 1e3 * r["eps"] if r.get("eps") else None
fig, axes = plt.subplots(1, 5, figsize=(S.DBL_W, 2.15),
                         gridspec_kw={"width_ratios": [1.75, 1, 1, 1, 1], "wspace": 0.36,
                                      "left": 0.05, "right": 0.995, "bottom": 0.17,
                                      "top": 0.80})
w = 0.25


def value(key, grp, a):
    if grp == "iso25":
        return iso.get((25.0, a)) if key == "P" else None
    if grp == "iso100":
        return iso.get((100.0, a)) if key == "P" else None
    r = recs.get((grp, a))
    return None if r is None else r.get(key)


for ax, (key, title, groups, fmt) in zip(axes, panels):
    vals = [v for _, g in groups for a in ARCHS for v in [value(key, g, a)] if v is not None]
    bnd = [recs[("I", a)].get(key) for a in ("Z2", "Z3") if ("I", a) in recs and "B" in
           [g for _, g in groups]]
    top = 1.18 * max(vals + [b for b in bnd if b is not None]) if vals else 1.0
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylim(0, top)
    for j, (lab, g) in enumerate(groups):
        for n, a in enumerate(ARCHS):
            v = value(key, g, a)
            xc = j + (n - 1) * (w + 0.02)
            if v is None:
                ax.text(xc, top * 0.02, "n/a", ha="center", va="bottom", fontsize=5.5,
                        color=S.INK2, rotation=90)
                continue
            S.rbar(ax, xc, v, w, S.ARCH[a])
            inside = v > 0.32 * top
            ax.text(xc, v * 0.5 if inside else v + top * 0.02, fmt.format(v), ha="center",
                    va="center" if inside else "bottom", rotation=90, fontsize=5.8,
                    color="white" if inside else S.INK)
            if g == "B" and ("I", a) in recs and recs[("I", a)].get(key) is not None:
                ax.plot(xc, recs[("I", a)][key], "D", ms=3.6, mfc="white", mec=S.INK,
                        mew=0.7, zorder=5)
    ax.set_xticks(range(len(groups)), [l for l, _ in groups])
    ax.tick_params(axis="x", length=0, pad=2)
    S.panel(ax, title[1], title[4:], y=1.04)
axes[0].axvline(1.5, color=S.GRID, lw=0.8, zorder=0)
axes[0].text(0.5, axes[0].get_ylim()[1] * 0.985, "no coupling", ha="center", va="top",
             fontsize=6.0, color=S.INK2)
axes[0].text(2.5, axes[0].get_ylim()[1] * 0.985, "coupled", ha="center", va="top",
             fontsize=6.0, color=S.INK2)
handles = [Patch(fc=S.ARCH[a], ec="none", label=S.ARCH_NAME[a]) for a in ARCHS] + [
    Line2D([], [], marker="D", ls="none", mfc="white", mec=S.INK, ms=4,
           label="interface-free bottom plate (bound)")]
fig.legend(handles=handles, loc="upper center", ncol=4, bbox_to_anchor=(0.52, 1.02),
           columnspacing=1.4, handletextpad=0.5)
fig.text(0.52, 0.01, "A: the same top cold plate   ·   B: the same top and bottom cold plates "
         "(bottom plate through a 50-µm TIM under the cell grid)   ·   smoothed input (S0)",
         ha="center", va="bottom", fontsize=6.6, color=S.INK2)
S.save(fig, "fig8_tiers")
