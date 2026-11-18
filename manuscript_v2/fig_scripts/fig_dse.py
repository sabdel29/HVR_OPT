"""Fig. 3: converter design-space exploration over regulator count.

(a) The electrical screen: conversion + routing loss at 25 C against regulator count M at the
paper's specification (1 kW, 48 V -> 1 V, 500 mm2, J = 3.5 A/mm2, 90-device discrete library),
with the converter RE-SYNTHESIZED at every M (solid, corrected flying-capacitor rule) versus held
at N3K3K_A2 (dashed). The published (legacy-rule) re-synthesized curve is drawn faded. Every
sampled count carries a marker (shape = selected member; x = no feasible member). Each jump is
tagged with the area constraint that becomes active there (the member selected at the previous
count no longer fits the per-cell budget at the new count). The infeasible range is shaded; the
integration design point (M = 49) is ringed.
(b) The two counts carried through the full coupled chain (Z1, cooling A): package-internal loss
on the coupled boundary, which is NOT the screen's boundary, so it has its own axis.

Data: research/tcpmt_revision/dse_j35/data/case_{C,D}_etm35_caprule_full.csv (else
_caprule.csv), case_{C,D}_etm35.csv (published), all_architectures_etm35*.csv;
research/tcpmt_revision/countopt/etm_Z1_M64N2K2KA1C4_HV_S0_h1.1_r21.json and
research/final_closure/etm_Z1_HV_S0_h1.1_r21.json (P_loss_w).
"""
import csv
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import style as S

S.setup()
D = S.TR / "dse_j35" / "data"
MEMBER = {"N=3,K=3,K_A=2": ("o", "N3K3K$_A$2"), "N=2,K=2,K_A=1": ("s", "N2K2K$_A$1"),
          "N=4,K=4,K_A=2": ("^", "N4K4K$_A$2")}


def short(arch):
    p = dict(kv.split("=") for kv in arch.split(","))
    return f"N{p['N']}K{p['K']}"


def load(path):
    out = []
    for r in csv.DictReader(open(path)):
        ok = r["feasible"] == "True"
        out.append(dict(M=int(float(r["M"])), ok=ok,
                        tot=float(r["total_loss_W"]) if ok else None,
                        arch=r["arch"] if ok else None,
                        budget=float(r["area_budget_mm2"]) if r.get("area_budget_mm2") else None))
    return out


# ---------------------------------------------------------------- the screens
tag = next((t for t in ("_caprule_full", "_caprule") if (D / f"case_D_etm35{t}.csv").is_file()),
           None)
Dleg, Cleg = load(D / "case_D_etm35.csv"), load(D / "case_C_etm35.csv")
if tag:
    Dd, Cc = load(D / f"case_D_etm35{tag}.csv"), load(D / f"case_C_etm35{tag}.csv")
    aa = D / f"all_architectures_etm35{tag}.csv"
else:
    Dd, Cc, aa = Dleg, Cleg, D / "all_architectures_etm35.csv"
allarch = [r for r in csv.DictReader(open(aa)) if r["switch_mode"] == "discrete"]


def member_key(r):
    return f"N={r['N']},K={r['K']},K_A={r['K_A']}"


def smallest_tier(arch):
    a = [float(r["area"]) for r in allarch if member_key(r) == arch and r["area_ok"] == "True"]
    return min(a) if a else None


def area_ok(arch, M):
    rs = [r for r in allarch if member_key(r) == arch and int(r["M"]) == M]
    return any(r["area_ok"] == "True" for r in rs) if rs else None


# ---------------------------------------------------------------- coupled chain (other boundary)
c64 = S.JP(S.TR / "countopt" / "etm_Z1_M64N2K2KA1C4_HV_S0_h1.1_r21.json")
c49 = S.JP(S.FC / "etm_Z1_HV_S0_h1.1_r21.json")
coupled = {}
if c49:
    coupled[int((c49.get("design") or {}).get("n_vr") or 49)] = c49["P_loss_w"]
if c64:
    coupled[int((c64.get("design") or {})["n_vr"])] = c64["P_loss_w"]

fig, (ax, bx) = plt.subplots(2, 1, figsize=(S.COL_W, 3.55), sharex=True,
                             gridspec_kw={"height_ratios": [3.3, 1.0], "hspace": 0.16})
fig.subplots_adjust(left=0.135, right=0.985, bottom=0.115, top=0.845)
XMAX = max(r["M"] for r in Dd) + 3
ax.set_xlim(33, XMAX)
ax.set_ylim(80, 131)
ax.set_ylabel("Conversion + routing (W)")

# ---------------------------------------------------------------- infeasible range
infeas = [r["M"] for r in Dd if not r["ok"]]
m_inf = min(infeas)
for a_ in (ax, bx):
    a_.axvspan(m_inf, XMAX, color=S.LIGHT, lw=0, zorder=0)
y_x = 82.6
for m in infeas:
    ax.plot(m, y_x, "x", ms=4.6, mew=1.0, color=S.INK, zorder=4, clip_on=False)
last_ok = max((r for r in Dd if r["ok"]), key=lambda r: r["M"])
cause = smallest_tier(last_ok["arch"])
b_inf = next(r["budget"] for r in Dd if r["M"] == m_inf) or 1000.0 / m_inf / 3.5
ax.text((m_inf + XMAX) / 2, 97.0,
        f"no feasible\nmember,\n$M$ ≥ {m_inf}:\n{short(last_ok['arch'])} tier\n"
        f"≥ {cause:.2f} >\n{b_inf:.2f} mm$^2$",
        ha="center", va="center", fontsize=6.5, color=S.INK2, linespacing=1.05)


def curve(rows, ls, color, lw, alpha, z, marker_fc="white", ms=4.6, member_marks=True):
    ok = [r for r in rows if r["ok"]]
    ax.plot([r["M"] for r in ok], [r["tot"] for r in ok], ls=ls, color=color, lw=lw,
            alpha=alpha, zorder=z)
    for r in ok:
        mk = MEMBER.get(r["arch"], ("o", ""))[0] if member_marks else "o"
        ax.plot(r["M"], r["tot"], mk, ms=ms, mfc=marker_fc, mec=color, mew=0.9, alpha=alpha,
                zorder=z + 1)


FADE = 0.3
if tag:
    curve(Dleg, "-", S.MUTED, 0.9, FADE + 0.15, 2, ms=3.4)              # published, faded
curve(Cc, (0, (3, 2)), S.INK2, 1.0, 1.0, 3, marker_fc=S.INK2, ms=2.6, member_marks=False)
curve(Dd, "-", S.INK, 1.3, 1.0, 6)
okC = [r for r in Cc if r["ok"]]
c_inf = min((r["M"] for r in Cc if not r["ok"]), default=None)
if c_inf is not None:
    ax.annotate(f"held N3K3:\ninfeasible\nfrom $M$ = {c_inf}", (okC[-1]["M"], okC[-1]["tot"]),
                xytext=(okC[-1]["M"] + 2.6, okC[-1]["tot"] - 6.5), ha="left", va="top",
                fontsize=6.5, color=S.INK2, linespacing=1.0,
                arrowprops=dict(arrowstyle="-", lw=0.5, color=S.MUTED, shrinkA=0, shrinkB=2))

# ---------------------------------------------------------------- jumps and their causes
okD = [r for r in Dd if r["ok"]]
jumps = []
for prev, cur in zip(okD[:-1], okD[1:]):
    if cur["tot"] > prev["tot"] and prev["arch"] != cur["arch"] and \
            area_ok(prev["arch"], cur["M"]) is False:
        jumps.append((prev, cur, smallest_tier(prev["arch"]), cur["budget"]))
ROMAN = ("i", "ii", "iii", "iv")
lines = []
for k, (prev, cur, amin, bud) in enumerate(jumps):
    t = ROMAN[k]
    xm, ym = (prev["M"] + cur["M"]) / 2, (prev["tot"] + cur["tot"]) / 2
    ax.text(xm + 0.9, ym, f"({t})", ha="left", va="center", fontsize=6.5, color=S.INK,
            zorder=8, bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none"))
    lines.append(f"({t}) $M$ = {cur['M']}: {short(prev['arch'])} tier ≥ {amin:.2f} mm$^2$"
                 f" > {bud:.2f}-mm$^2$ budget")
if lines:
    ax.text(43.5, 130.0, "jumps caused by the area constraint:\n" + "\n".join(lines),
            ha="left", va="top", fontsize=6.5, color=S.INK, linespacing=1.15)

# ---------------------------------------------------------------- design point, optimum
p49 = next(r for r in Dd if r["M"] == 49)
best = min(okD, key=lambda r: r["tot"])
ax.plot(49, p49["tot"], "o", ms=8.5, mfc="none", mec=S.INK, mew=1.0, zorder=7)
ax.annotate(f"integration design\npoint $M$ = 49,\n{p49['tot']:.1f} W", (49, p49["tot"]),
            xytext=(34.0, 92.5), ha="left", va="top", fontsize=6.5, color=S.INK,
            linespacing=1.05,
            arrowprops=dict(arrowstyle="-", lw=0.5, color=S.MUTED, shrinkA=0, shrinkB=4))
ax.annotate(f"optimum\n$M$ = {best['M']},\n{best['tot']:.1f} W", (best["M"], best["tot"]),
            xytext=(best["M"] + 1.3, best["tot"] + 0.5), ha="left", va="center",
            fontsize=6.5, color=S.INK, linespacing=1.05)
S.panel(ax, "a", "electrical screen, 25 °C", y=1.0)

# ---------------------------------------------------------------- (b) coupled chain
bx.set_xlabel("Regulator count $M$ (at $J_\\mathrm{t}$ = 3.5 A/mm$^2$)")
bx.set_ylabel("Coupled (W)")
if coupled:
    ms = sorted(coupled)
    ps = [coupled[m] for m in ms]
    lo, hi = min(ps), max(ps)
    pad = max(4.0, 0.6 * (hi - lo))
    bx.set_ylim(lo - pad, hi + pad)
    bx.plot(ms, ps, ls=":", color=S.MUTED, lw=0.8, zorder=2)
    for m, p in coupled.items():
        mk = "o" if m == 49 else "s"
        bx.plot(m, p, mk, ms=4.6, mfc=S.INK, mec=S.INK, zorder=4)
        bx.annotate(f"{p:.1f} W" + ("" if m == 49 else " (full chain)"), (m, p),
                    xytext=(5, 0), textcoords="offset points", ha="left", va="center",
                    fontsize=6.5, color=S.INK)
    if 49 in coupled:
        bx.plot(49, coupled[49], "o", ms=8.5, mfc="none", mec=S.INK, mew=1.0, zorder=5)
else:
    S.pending(bx, 0.3, 0.5, "coupled-chain losses", "countopt/etm_Z1_M64*.json")
if c64 is None:
    S.pending(bx, 0.45, 0.3, "M = 64 full chain", "countopt/etm_Z1_M64N2K2KA1C4_HV_S0_h1.1_r21.json")
bx.text(m_inf + 1.0, sum(bx.get_ylim()) / 2, "package-internal\nloss, Z1, cooling A",
        ha="left", va="center", fontsize=6.5, color=S.INK2, linespacing=1.05)
S.panel(bx, "b", "full coupled chain (other boundary)", y=1.0)

# ---------------------------------------------------------------- legend
h = [Line2D([], [], color=S.INK, lw=1.3, label="re-synthesized, corrected rule")]
if tag:
    h.append(Line2D([], [], color=S.MUTED, lw=0.9, alpha=FADE + 0.15,
                    label="re-synthesized, published rule"))
h.append(Line2D([], [], color=S.INK2, lw=1.0, ls=(0, (3, 2)), marker="o", ms=2.6,
                mfc=S.INK2, mec=S.INK2, label="held at N3K3K$_A$2"))
h += [Line2D([], [], marker=m, ls="none", mfc="white", mec=S.INK, ms=4.6, mew=0.9, label=l)
      for m, l in MEMBER.values()]
h += [Line2D([], [], marker="x", ls="none", color=S.INK, ms=4.6, mew=1.0,
             label="no feasible member")]
fig.legend(handles=h, loc="upper center", ncol=3, bbox_to_anchor=(0.54, 1.005),
           fontsize=6.5, columnspacing=0.9, handletextpad=0.4, labelspacing=0.3)
S.save(fig, "fig_dse")
