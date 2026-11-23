"""Fig. 8 (scenarios): the embedded (Z1) and package-backside (Z2) regulators under cooling A in
three 48-V input states.

  ideal decoupling        reference: the cells draw a smooth input current (k_rms = 1)
  implemented decoupling  PRODUCTION: two interleaved 6-phase clock groups and a ring of
                          input capacitors outside the cell grid
  bare decoupling         reference: no decoupling, every cell's input pulse at the buck duty
The k_rms printed for each state is the factor its case was computed with (the package 48-V
current over its DC average, read from the Z1 case's ledger), never a typed number.

One quantity per panel (small multiples, one y-axis each): package-internal loss, peak
temperature, die warpage and critical-joint displacement. The local joint response is not
drawn: it is solved for the ideal and bare references only. Whiskers: +/-U95 where the case
has a mesh ladder of its own (research/tcpmt_revision/uncertainty.json: the production state
under 'U', the ideal-decoupling reference under 'reference_cases'); the bare reference has no
ladder and carries no whisker. Hatched: the feasibility record of that very case file
(research/tcpmt_revision/feasibility.json, keys S0_A_<arch>, A_<arch>, S1_A_<arch>) lists a
failed limit of the filter in force.
Cases: the case registry (scripts/tcpmt_cases.py), cooling A.
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
import style as S

S.setup()
TIER = "A"
#: (registry state, tick label, feasibility key prefix, uncertainty source)
STATES = [("S0", "ideal", "S0_A_", "reference"),
          (S.PROD, "implemented", "A_", "production"),
          ("S1", "bare", "S1_A_", None)]
ARCHS = ("Z1", "Z2")

CASE = {}
for st, _, _, _ in STATES:
    for a in ARCHS:
        p = S.TC.case_path(st, TIER, a)
        if p is not None:
            CASE[(st, a)] = (p, json.loads(p.read_text()))

unc = S.JP(S.TR / "uncertainty.json") or {}
feas = (S.JP(S.TR / "feasibility.json") or {}).get("cases") or {}
UKEY = {"P": "P", "T": "T", "warp": "warp", "du": "du"}


def val(st, a, key):
    c = (CASE.get((st, a)) or (None, None))[1]
    if c is None:
        return None
    m = c.get("mechanics") or {}
    return {"P": c.get("P_loss_w"), "T": (c.get("thermal") or {}).get("T_max_C"),
            "warp": m.get("die_warpage_pv_um"),
            "du": ((m.get("joint_search") or {}).get("critical") or {}).get("du_um")}[key]


def u95(st, a, key, src):
    if src == "production":
        return (unc.get("U") or {}).get(f"{TIER}.{a}.{UKEY[key]}")
    if src == "reference":
        rc = (unc.get("reference_cases") or {}).get(a) or {}
        return ((rc.get("outputs") or {}).get(UKEY[key]) or {}).get("U95")
    return None


def infeasible(st, a, prefix):
    rec = feas.get(f"{prefix}{a}") or {}
    p = (CASE.get((st, a)) or (None, None))[0]
    if not rec or p is None or rec.get("case") != p.name:
        return False
    return bool(rec.get("fails"))


def k_rms(st):
    """package 48-V RMS current over its DC average in the Z1 case of this state"""
    c = (CASE.get((st, "Z1")) or (None, None))[1]
    if c is None:
        return None
    r = next((x for x in c["ledger_rows"] if x["term"] == "P_pkg_RDL_HV_supply"), None)
    return (r["I_a"] / c["i_hv_avg_a"]) if (r and r.get("I_a") and c.get("i_hv_avg_a")) else None


panels = [("P", "Package-internal loss (W)", "{:.1f}"),
          ("T", "Peak temperature (°C)", "{:.1f}"),
          ("warp", "Die warpage, P–V (µm)", "{:.1f}"),
          ("du", r"Joint driver $\Delta u_\mathrm{c}$ (µm)", "{:.2f}")]
fig, axes = plt.subplots(1, 4, figsize=(S.DBL_W, 2.1),
                         gridspec_kw={"wspace": 0.34, "left": 0.05, "right": 0.995,
                                      "bottom": 0.22, "top": 0.79})
x = np.arange(len(STATES))
NA = len(ARCHS)
w = 0.66 / NA


def xpos(n, j):
    return x[j] + (n - (NA - 1) / 2) * (w + 0.03)


any_bad = False
for k, (ax, (key, title, fmt)) in enumerate(zip(axes, panels)):
    vals = [v + (u95(st, a, key, src) or 0.0) for st, _, _, src in STATES for a in ARCHS
            if (v := val(st, a, key)) is not None]
    top = 1.18 * max(vals) if vals else 1.0
    ax.set_xlim(-0.6, len(STATES) - 0.4)
    ax.set_ylim(0, top)
    for n, a in enumerate(ARCHS):
        for j, (st, lab, prefix, src) in enumerate(STATES):
            v = val(st, a, key)
            xc = xpos(n, j)
            if v is None:
                S.pending(ax, xc, top * 0.03, f"{a} {lab}", "case registry",
                          transform=ax.transData, rotation=90, ha="center", va="bottom")
                continue
            S.rbar(ax, xc, v, w, S.ARCH[a])
            bad = infeasible(st, a, prefix)
            if bad:
                any_bad = True
                ax.add_patch(Rectangle((xc - w / 2, 0), w, v, fc="none", ec="white", lw=0,
                                       hatch="xxxx", zorder=3))
            e = u95(st, a, key, src)
            if e:
                ax.errorbar(xc, v, yerr=e, fmt="none", ecolor=S.INK, elinewidth=0.6,
                            capsize=1.5, capthick=0.6, zorder=5)
            inside = v > 0.36 * top and not bad
            ax.text(xc, v * 0.5 if inside else v + (e or 0.0) + top * 0.025, fmt.format(v),
                    ha="center", va="center" if inside else "bottom", rotation=90,
                    fontsize=6.2, color="white" if inside else S.INK, zorder=6,
                    bbox=None if inside else dict(fc="white", ec="none", pad=0.2))
    ax.set_xticks(x, [lab for _, lab, _, _ in STATES])
    ax.tick_params(axis="x", length=0, pad=2)
    S.panel(ax, "abcd"[k], title, y=1.04)

handles = [Patch(fc=S.ARCH[a], ec="none", label=S.ARCH_NAME[a]) for a in ARCHS]
if any_bad:
    handles.append(Patch(fc=S.NEUTRAL, ec="white", hatch="xxxx", lw=0,
                         label="infeasible (a limit fails)"))
handles.append(Line2D([], [], color=S.INK, lw=0.6, marker="_", ms=4, label="±$U_{95}$"))
fig.legend(handles=handles, loc="upper center", ncol=len(handles), bbox_to_anchor=(0.52, 1.03),
           columnspacing=1.4, handletextpad=0.5)


def ktxt(st):
    k = k_rms(st)
    return "" if k is None else f", $k_\\mathrm{{rms}}$ = {k:.2f}"


fig.text(0.52, 0.02, f"Input decoupling, cooling A:  ideal{ktxt('S0')}   ·   implemented "
         f"(interleaved clocks and an input-capacitor ring){ktxt(S.PROD)}   ·   bare (pulse at "
         f"the buck duty){ktxt('S1')}", ha="center", va="bottom", fontsize=6.6, color=S.INK2)
S.save(fig, "fig8_scenarios")
