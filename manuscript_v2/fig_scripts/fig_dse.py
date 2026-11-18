"""Fig. (capability 3): converter design-space exploration over regulator count.

Conversion + routing loss against regulator count M at the paper's specification
(1 kW, 48 V -> 1 V, 500 mm2, J = 3.5 A/mm2, 90-device discrete library, ripple 0.5),
with the converter architecture RE-SYNTHESIZED at every M (solid) versus held at the
N=3, K=3 architecture of the integration study (dashed). Every sampled count carries a
marker (shape = selected member; x = no feasible member). Each jump is annotated with the
constraint that becomes active there: the member selected at the previous count no longer
fits the per-cell area budget (all_architectures_etm35.csv: area_ok, smallest feasible tier
of that member vs the budget at the new count). The infeasible range is shaded and the
integration design point (M = 49) is ringed.

Pending artifacts (drawn when present, otherwise a visible 'pending' note):
  research/tcpmt_revision/dse_caprule.json (+ its CSVs)  the screen under the corrected
      flying-capacitor rule: corrected curve solid, the published (legacy) curve faded
  research/tcpmt_revision/count_optimum_etm.json         the candidate carried through the
      full coupled chain
Data: research/tcpmt_revision/dse_j35/data/case_{C,D}_etm35.csv, all_architectures_etm35.csv.
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import style as S

S.setup()
D = S.TR / "dse_j35" / "data"
MEMBER = {"N=3,K=3,K_A=2": ("o", "N3K3K$_A$2"), "N=2,K=2,K_A=1": ("s", "N2K2K$_A$1"),
          "N=4,K=4,K_A=2": ("^", "N4K4K$_A$2")}


def short(arch):
    """'N=4,K=4,K_A=2' -> 'N4K4'"""
    p = dict(kv.split("=") for kv in arch.split(","))
    return f"N{p['N']}K{p['K']}"


def load(path):
    out = []
    for r in csv.DictReader(open(path)):
        ok = r["feasible"] == "True"
        out.append(dict(M=int(float(r["M"])), ok=ok,
                        tot=float(r["total_loss_W"]) if ok else None,
                        arch=r["arch"] if ok else None,
                        area=float(r["area_mm2"]) if ok else None,
                        budget=float(r["area_budget_mm2"]) if r.get("area_budget_mm2") else None,
                        I_vr=float(r["I_vr_A"]) if r.get("I_vr_A") else None))
    return out


def load_caprule():
    """Rows of the corrected-rule screen, from dse_caprule.json: rows embedded in it, or the
    CSVs it names, or the conventional location next to the published screen."""
    j = S.JP(S.TR / "dse_caprule.json")
    if j is None:
        return None, "dse_caprule.json"
    found = {}

    def rows_from(obj):
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "M" in obj[0] and \
                any(k in obj[0] for k in ("total_loss_W", "total_loss_w", "loss_W")):
            out = []
            for r in obj:
                tot = r.get("total_loss_W", r.get("total_loss_w", r.get("loss_W")))
                ok = str(r.get("feasible", tot is not None)) in ("True", "true", "1") \
                    and tot not in (None, "")
                out.append(dict(M=int(float(r["M"])), ok=ok, tot=float(tot) if ok else None,
                                arch=r.get("arch") if ok else None))
            return out
        return None

    def walk(obj, key=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, k)
        elif isinstance(obj, list):
            r = rows_from(obj)
            if r is not None:
                found.setdefault("C" if ("C" in key.upper().split("_") or "fixed" in key.lower())
                                 else "D", r)
            else:
                for v in obj:
                    walk(v, key)
        elif isinstance(obj, str) and obj.endswith(".csv"):
            for base in (S.TR, S.TR / "dse_caprule", S.SRC, S.TR / "dse_j35" / "data"):
                p = (base / obj) if not Path(obj).is_absolute() else Path(obj)
                if p.is_file():
                    case = "C" if "case_C" in p.name else "D" if "case_D" in p.name else None
                    if case:
                        found.setdefault(case, load(p))
                    break
    walk(j)
    if "D" not in found:                                   # conventional locations
        for pat in ("dse_caprule/data/case_D_*.csv", "dse_j35/data/case_D_*cap*.csv"):
            hits = sorted(S.TR.glob(pat))
            if hits:
                found["D"] = load(hits[-1])
                c = hits[-1].with_name(hits[-1].name.replace("case_D_", "case_C_"))
                if c.is_file():
                    found["C"] = load(c)
                break
    if "D" not in found:
        return None, "dse_caprule.json (no screen rows found in it)"
    return found, None


def load_count_candidate():
    """The count carried through the full coupled chain (count_optimum_etm.json)."""
    j = S.JP(S.TR / "count_optimum_etm.json")
    if j is None:
        return None
    cands = []

    def walk(o, key=""):
        if isinstance(o, dict):
            m = next((o[k] for k in ("M", "count", "M_candidate", "n_cells") if
                      isinstance(o.get(k), (int, float))), None)
            if m is not None and key.lower() not in ("macros",):
                p = next((o[k] for k in ("P_loss_w", "P_loss_W", "P_coupled_W", "P_loss_coupled_w")
                          if isinstance(o.get(k), (int, float))), None)
                cands.append((key, int(m), p))
            for k, v in o.items():
                if k != "macros":
                    walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
    walk(j)
    pick = [c for c in cands if any(t in c[0].lower() for t in ("candidate", "best", "optimum",
                                                                 "selected", "coupled"))]
    return (pick or cands or [None])[0]


Dd, Cc = load(D / "case_D_etm35.csv"), load(D / "case_C_etm35.csv")
allarch = [r for r in csv.DictReader(open(D / "all_architectures_etm35.csv"))
           if r["switch_mode"] == "discrete"]


def member_key(r):
    return f"N={r['N']},K={r['K']},K_A={r['K_A']}"


def smallest_tier(arch):
    """The smallest feasible tier footprint of a member over every sampled count."""
    a = [float(r["area"]) for r in allarch if member_key(r) == arch and r["area_ok"] == "True"]
    return min(a) if a else None


def area_ok(arch, M):
    rs = [r for r in allarch if member_key(r) == arch and int(r["M"]) == M]
    return any(r["area_ok"] == "True" for r in rs) if rs else None


cap, cap_missing = load_caprule()
cand = load_count_candidate()

fig, ax = plt.subplots(figsize=(S.COL_W, 2.72))
fig.subplots_adjust(left=0.135, right=0.985, bottom=0.155, top=0.835)
XMAX = max(r["M"] for r in Dd) + 3
ax.set_xlim(33, XMAX)
ax.set_ylim(80, 127)
ax.set_xlabel("Regulator count $M$ (at $J_\\mathrm{t}$ = 3.5 A/mm$^2$)")
ax.set_ylabel("Conversion + routing loss (W)")

# ---------------------------------------------------------------- infeasible range
infeas = [r["M"] for r in Dd if not r["ok"]]
m_inf = min(infeas)
ax.axvspan(m_inf, XMAX, color=S.LIGHT, lw=0, zorder=0)
y_x = 82.6                                     # baseline row of the 'no feasible member' marks
for m in infeas:
    ax.plot(m, y_x, "x", ms=4.6, mew=1.0, color=S.INK, zorder=4, clip_on=False)
last_ok = max((r for r in Dd if r["ok"]), key=lambda r: r["M"])
cause = smallest_tier(last_ok["arch"])
b_inf = next(r["budget"] for r in Dd if r["M"] == m_inf) or 1000.0 / m_inf / 3.5
ax.text((m_inf + XMAX) / 2, 126.0,
        f"no feasible member,\n$M$ ≥ {m_inf}: {short(last_ok['arch'])} tier\n≥ {cause:.2f} > {b_inf:.2f} mm$^2$",
        ha="center", va="top", fontsize=6.5, color=S.INK2, linespacing=1.05)

# ---------------------------------------------------------------- curves
legacy_alpha = 0.32 if cap else 1.0


def curve(rows, ls, color, lw, alpha, z, marker_fc="white", ms=4.6, member_marks=True):
    ok = [r for r in rows if r["ok"]]
    ax.plot([r["M"] for r in ok], [r["tot"] for r in ok], ls=ls, color=color, lw=lw,
            alpha=alpha, zorder=z)
    for r in ok:
        m = MEMBER.get(r["arch"], ("o", ""))[0] if member_marks else "o"
        ax.plot(r["M"], r["tot"], m, ms=ms, mfc=marker_fc, mec=color, mew=0.9, alpha=alpha,
                zorder=z + 1)


# fixed architecture (dashed, small dots at every sampled feasible count)
curve(Cc, (0, (3, 2)), S.MUTED, 1.0, legacy_alpha, 2, marker_fc=S.MUTED, ms=2.6,
      member_marks=False)
okC = [r for r in Cc if r["ok"]]
c_inf = min((r["M"] for r in Cc if not r["ok"]), default=None)
if c_inf is not None:
    ax.annotate(f"held N3K3:\ninfeasible\nfrom $M$ = {c_inf}", (okC[-1]["M"], okC[-1]["tot"]),
                xytext=(okC[-1]["M"] + 1.0, okC[-1]["tot"] - 3.0), ha="left", va="top",
                fontsize=6.5, color=S.INK2, linespacing=1.0,
                arrowprops=dict(arrowstyle="-", lw=0.5, color=S.MUTED, shrinkA=0, shrinkB=2))
# re-synthesized (published capacitor rule)
curve(Dd, "-", S.INK, 1.1, legacy_alpha, 3)
if cap:
    curve(cap["D"], "-", S.INK, 1.3, 1.0, 6)
    if cap.get("C"):
        curve(cap["C"], (0, (3, 2)), S.INK2, 1.0, 1.0, 5, marker_fc=S.INK2, ms=2.6,
              member_marks=False)
else:
    S.pending(ax, m_inf + 0.8, 104.0, "corrected-rule\ncurve", cap_missing,
              transform=ax.transData)

# ---------------------------------------------------------------- jumps and their causes
ref = cap["D"] if cap else Dd
okD = [r for r in ref if r["ok"]]
jumps = []
for prev, cur in zip(okD[:-1], okD[1:]):
    if cur["tot"] > prev["tot"] and prev["arch"] != cur["arch"] and \
            area_ok(prev["arch"], cur["M"]) is False:
        jumps.append((prev, cur, smallest_tier(prev["arch"]), cur["budget"]))
# each jump is tagged at its rise; the causes are listed in the free band at the top
ROMAN = ("i", "ii", "iii", "iv")
lines = []
for k, (prev, cur, amin, bud) in enumerate(jumps):
    tag = ROMAN[k]
    xm, ym = (prev["M"] + cur["M"]) / 2, (prev["tot"] + cur["tot"]) / 2
    ax.text(xm + 0.9, ym, f"({tag})", ha="left", va="center", fontsize=6.5, color=S.INK,
            zorder=8, bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none"))
    lines.append(f"({tag}) $M$ = {cur['M']}: {short(prev['arch'])} tier ≥ {amin:.2f} mm$^2$"
                 f" > {bud:.2f}-mm$^2$ budget")
if lines:
    ax.text(41.0, 126.2, "jump caused by the area constraint:\n" + "\n".join(lines),
            ha="left", va="top", fontsize=6.5, color=S.INK, linespacing=1.15)

# ---------------------------------------------------------------- design point, optimum
p49 = next(r for r in ref if r["M"] == 49)
best = min(okD, key=lambda r: r["tot"])
ax.plot(49, p49["tot"], "o", ms=8.5, mfc="none", mec=S.INK, mew=1.0, zorder=7)
ax.annotate(f"integration design\npoint $M$ = 49,\n{p49['tot']:.1f} W", (49, p49["tot"]),
            xytext=(34.2, 90.6), ha="left", va="top", fontsize=6.5, color=S.INK,
            linespacing=1.05,
            arrowprops=dict(arrowstyle="-", lw=0.5, color=S.MUTED, shrinkA=0, shrinkB=4))
ax.annotate(f"optimum\n$M$ = {best['M']},\n{best['tot']:.1f} W", (best["M"], best["tot"]),
            xytext=(best["M"] + 1.4, best["tot"] + 0.2), ha="left", va="center",
            fontsize=6.5, color=S.INK, linespacing=1.05)

# ---------------------------------------------------------------- coupled-chain candidate
if cand:
    key, m_c, p_c = cand
    r_c = next((r for r in ref if r["M"] == m_c and r["ok"]), None)
    if r_c is not None:
        ax.plot(m_c, r_c["tot"], "*", ms=8.5, mfc=S.INK, mec="white", mew=0.5, zorder=8)
        lab = f"full coupled chain: $M$ = {m_c}" + (f", {p_c:.1f} W" if p_c else "")
        ax.annotate(lab, (m_c, r_c["tot"]), xytext=(4, 8), textcoords="offset points",
                    ha="left", va="bottom", fontsize=6.5, color=S.INK)
else:
    S.pending(ax, m_inf + 0.8, 97.0, "coupled-chain\ncandidate", "count_optimum_etm.json",
              transform=ax.transData)

# ---------------------------------------------------------------- legend
h = [Line2D([], [], color=S.INK, lw=1.1, label="re-synthesized at every $M$"),
     Line2D([], [], color=S.MUTED, lw=1.0, ls=(0, (3, 2)), marker="o", ms=2.6, mfc=S.MUTED,
            mec=S.MUTED, label="held at N3K3K$_A$2")]
h += [Line2D([], [], marker=m, ls="none", mfc="white", mec=S.INK, ms=4.6, mew=0.9, label=l)
      for m, l in MEMBER.values()]
h += [Line2D([], [], marker="x", ls="none", color=S.INK, ms=4.6, mew=1.0,
             label="sampled, no feasible member")]
if cap:
    h = [Line2D([], [], color=S.INK, lw=1.3, label="corrected capacitor rule"),
         Line2D([], [], color=S.INK, lw=1.1, alpha=legacy_alpha,
                label="published rule (legacy)")] + h[1:]
if cand:
    h.append(Line2D([], [], marker="*", ls="none", mfc=S.INK, mec="white", ms=8,
                    label="carried through the coupled chain"))
fig.legend(handles=h, loc="upper center", ncol=3, bbox_to_anchor=(0.54, 1.005),
           fontsize=6.5, columnspacing=0.9, handletextpad=0.4, labelspacing=0.3)
S.save(fig, "fig_dse")
