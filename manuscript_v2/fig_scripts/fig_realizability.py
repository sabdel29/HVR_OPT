"""Fig. 4: tier order is a realizability constraint, for the production capacitor and the
thin-capacitor sensitivity.

TCPMT round 3: the converter cell is built of MIXED tiers (a tier holds parts of several
classes, the design record's decided tiers), so the order question is asked of those tiers.
(a) The decided tiers in the PRODUCTION order of the tier-order analysis, to scale in z (input
    end at the bottom, 10-um RDLs between the tiers), for
    rated -- the design in force, with the rated 0603 MLCC (left), and
    thin  -- the thin-capacitor sensitivity (the design record's entry of the design in force with
             the 100-um flying capacitor, right).
    Every part is drawn at its own height; the copper posts that bridge a shorter part fill the
    rest of its tier (hatched). A bar marks the worst net of each net class that must cross a
    whole tier with a build-up via (with the crossed depth of its worst via level).
(b) Worst via aspect ratio per net class (AR = deepest crossed level / via diameter, die
    terminals on both faces), production order (bar) and the range over every order of the
    decided tiers (line), against the 1:1 build-up (stacked-microvia) limit.

Data: tcpmt_revision/tier_order.json (designs.<key>: chosen order, its part assignment and per-net
aspect ratios, every decided order, via diameter, RDL thickness, the repartition search) of the
design in force and its thin-capacitor sensitivity (configs/design_points.yaml).
"""
import re
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

S.setup()
TO = (S.JP(S.TR / "tier_order.json") or {}).get("designs") or {}
KEY = S.DR.name()
if KEY not in TO:
    raise SystemExit(f"tier_order.json has no entry for design {KEY}: tier order unknown")


def thin_key():
    """The record's thin-capacitor sensitivity of the design in force: same count, topology
    and parts, a lower flying-capacitor height."""
    me = S.DR.get(KEY)
    for k in S.DR.keys():
        e = S.DR.get(k)
        if k != KEY and e.get("n_vr") == me["n_vr"] and e.get("topology") == me["topology"] \
                and e.get("capacitor") == me["capacitor"] \
                and float(e.get("cap_height_um") or 1e9) < float(me.get("cap_height_um") or 0):
            return k
    return None


EIA = {"GRM155": "0402", "GRM188": "0603", "GRM21": "0805", "GRM31": "1206", "GCM21": "0805"}


def cap_size(name):
    m = re.search(r"(G[RC]M\d+)", str(name))
    return next((v for k, v in EIA.items() if m and m.group(1).startswith(k)), "")


K0 = thin_key()
CASES = [("rated", KEY), ("thin", K0)]
CLS = S.DR.CLASSES                                     # tier vectors are in this class order
TOK = {"hs": "gan_hs", "ls": "gan_ls", "cf": "cap_fly", "L": "inductor"}
NETCLASS = [(("vin", "gan_hs"), "VIN→HS"), (("gan_hs", "cap_fly"), "HS→$C_\\mathrm{f}$"),
            (("gan_hs", "gan_ls"), "HS→LS"), (("gan_ls", "inductor"), "SW→$L$"),
            (("inductor", "out"), "$L$→$V_\\mathrm{o}$")]
#: two-line tick labels of panel (b)
TICK = {"VIN→HS": "VIN\n→HS", "HS→$C_\\mathrm{f}$": "HS\n→$C_\\mathrm{f}$", "HS→LS": "HS\n→LS",
        "SW→$L$": "SW\n→$L$", "$L$→$V_\\mathrm{o}$": "$L$\n→$V_\\mathrm{o}$"}


def endpoint(tok):
    if tok == "vin":
        return ("vin", None)
    if tok == "vout":
        return ("out", None)
    m = re.match(r"([a-zA-Z]+)(\d+)$", tok)
    return (TOK[m.group(1)], int(m.group(2)))


def net_class(name):
    a, b = name.split("_to_")
    return endpoint(a)[0], endpoint(b)[0]


def crossed(name, asg, n_tiers):
    """tier positions (0 = input end) a net crosses whole, die terminals on both faces"""
    a, b = (endpoint(t) for t in name.split("_to_"))
    tier = {e: asg.get(f"{e[0]}{e[1]}", 0) - 1 for e in (a, b) if e[1] is not None}
    if a[0] == "vin":
        return list(range(0, tier[b]))
    if b[0] == "out":
        return list(range(tier[a] + 1, n_tiers))
    lo, hi = sorted((tier[a], tier[b]))
    return list(range(lo + 1, hi))


def class_worst(net_ar):
    """{net class: (worst AR, net)}"""
    out = {}
    for n, ar in net_ar.items():
        k = net_class(n)
        if k not in out or ar > out[k][0]:
            out[k] = (ar, n)
    return out


DATA = {}
for case, key in CASES:
    t = TO.get(key) if key else None
    if not t:
        continue
    ch = t["chosen"]
    rng = {}
    for o in t.get("decided_orders") or [ch]:
        for k, (ar, _n) in class_worst(o["net_ar_both"]).items():
            lo, hi = rng.get(k, (ar, ar))
            rng[k] = (min(lo, ar), max(hi, ar))
    DATA[case] = dict(key=key, t=t, ch=ch, worst=class_worst(ch["net_ar_both"]), rng=rng,
                      d=float(t["via_diameter_um"]), rdl=float(t.get("rdl_um", S.DR.RDL_UM)),
                      lim=float(t.get("ar_limit", 1.0)), entry=S.DR.get(key))

fig = plt.figure(figsize=(S.COL_W, 3.9))
ax = fig.add_axes([0.0, 0.43, 1.0, 0.525])
bxs = [fig.add_axes([0.11, 0.10, 0.38, 0.165]), fig.add_axes([0.60, 0.10, 0.38, 0.165])]
W = 0.5
X0 = {"rated": 0.86, "thin": 3.26}
ztop = 0.0


def stack(case):
    """draw the production order of one case; returns (z extents per tier, stack top)"""
    dd = DATA[case]
    x0, rdl = X0[case], dd["rdl"]
    z, ext = rdl, []
    ax.plot([x0, x0 + W], [rdl / 2] * 2, color=S.MAT["rdl"], lw=1.0)
    for vec, um in zip(dd["ch"]["tiers"], dd["ch"]["tier_um"]):
        parts = {c: int(n) for c, n in zip(CLS, vec) if n}
        xs = x0
        ph = dd["entry"].get("part_heights_um") or {}
        for c, f in S.tier_fill(parts, dd["key"]):
            h = min(float(ph.get(c, um)), um)
            ax.add_patch(Rectangle((xs, z), W * f, h, fc=S.CLASS_COLOR[c], ec="white",
                                   lw=0.3))
            if um - h > 1.0:                       # copper posts over a shorter part
                ax.add_patch(Rectangle((xs, z + h), W * f, um - h, fc=S.MAT["fill"],
                                       ec=S.MAT["tsv"], lw=0.0, hatch="||||||"))
            xs += W * f
        ax.text(x0 - 0.05, z + um / 2, S.tier_label(parts), ha="right", va="center",
                fontsize=6, color=S.INK2)
        ext.append((z, z + um))
        z += um
        ax.plot([x0, x0 + W], [z + rdl / 2] * 2, color=S.MAT["rdl"], lw=1.0)
        z += rdl
    return ext, z


for case in ("rated", "thin"):
    if case not in DATA:
        continue
    dd = DATA[case]
    ext, z = stack(case)
    ztop = max(ztop, z)
    dd["ext"] = ext
    # whole-tier crossings: the worst net of each class, a bar over the tiers it crosses
    bars = []
    for k, lab in NETCLASS:
        if k not in dd["worst"]:
            continue
        ar, n = dd["worst"][k]
        cr = crossed(n, dd["ch"]["assignment"], len(ext))
        if not cr or ar <= dd["rdl"] / dd["d"] + 1e-9:
            continue
        bars.append((ext[min(cr)][0], ext[max(cr)][1], lab, ar * dd["d"], ar))
    xb0 = X0[case] + W + 0.07
    labs = []
    for j, (lo, hi, lab, dep, ar) in enumerate(bars):
        xv = xb0 + 0.085 * j
        ax.plot([xv, xv], [lo, hi], color=S.INK, lw=1.6 if ar > dd["lim"] else 0.9,
                solid_capstyle="butt")
        for zz in (lo, hi):
            ax.plot([xv - 0.03, xv + 0.03], [zz] * 2, color=S.INK, lw=0.6)
        labs.append([(lo + hi) / 2, f"{lab} {dep:.0f} µm"])
    # label rows to the right of the bars, spread to a minimum gap
    labs.sort(key=lambda r: -r[0])
    gap = 0.075 * (ztop + 400)
    for _ in range(200):
        moved = False
        for i in range(len(labs) - 1):
            g = labs[i][0] - labs[i + 1][0]
            if g < gap:
                labs[i][0] += (gap - g) / 2 + 1e-6
                labs[i + 1][0] -= (gap - g) / 2 + 1e-6
                moved = True
        if not moved:
            break
    xl = xb0 + 0.085 * max(len(bars) - 1, 0) + 0.06
    for zl, txt in labs:
        ax.text(xl, zl, txt, ha="left", va="center", fontsize=6, color=S.INK)

CASE_LAB = {}
for case, dd in DATA.items():
    e = dd["entry"]
    if case == "thin":
        CASE_LAB[case] = (f"Sensitivity: {float(e['cap_height_um']):.0f}-µm "
                          f"$C_\\mathrm{{f}}$ tier")
    else:
        CASE_LAB[case] = (f"Design point: rated {cap_size(e['capacitor'])} MLCC "
                          f"({float(e['cap_height_um']):.0f} µm)")
for case in ("rated", "thin"):
    if case in DATA:
        ax.text(X0[case] - 0.85, ztop + 140, CASE_LAB[case], ha="left", va="bottom",
                fontsize=6.5, color=S.INK)
    else:
        S.pending(ax, X0[case] - 0.8, 0.5, f"{case} tier order", "tier_order.json",
                  transform=ax.get_yaxis_transform())
ax.set_xlim(-0.05, 4.98)
ax.set_ylim(-260, ztop + 560)
ax.axis("off")
ax.plot([0.0, 0.0], [0, 500], color=S.INK, lw=0.8)
ax.text(0.05, 250, "500 µm", rotation=90, ha="left", va="center", fontsize=6.5)
ax.text(2.45, -60, "input end (48 V) at the bottom", ha="center", va="top", fontsize=6,
        color=S.INK2)
S.panel(ax, "a", "The four mixed tiers in the chosen order, with copper posts (hatched)",
        x=0.0, y=0.985)

# (b) worst AR per net class: production order (bar), range over every decided order (line)
labels = [lab for _, lab in NETCLASS]
for bx, case in zip(bxs, ("rated", "thin")):
    bx.set_yscale("log")
    bx.set_ylim(0.05, 60)
    if case not in DATA:
        S.pending(bx, 0.1, 0.5, f"{case} tier order", "tier_order.json")
        continue
    dd = DATA[case]
    bx.axhline(dd["lim"], color=S.MUTED, lw=0.7, ls=(0, (2, 2)))
    for i, (k, lab) in enumerate(NETCLASS):
        if k not in dd["worst"]:
            continue
        v = dd["worst"][k][0]
        lo, hi = dd["rng"].get(k, (v, v))
        vp = max(v, 0.06)
        bx.bar(i, vp, 0.55, color=S.INK, edgecolor=S.INK, lw=0.7, zorder=2)
        bx.plot([i + 0.36] * 2, [max(lo, 0.06), max(hi, 0.06)], color=S.INK2, lw=0.9,
                zorder=3, solid_capstyle="butt")
        for yy in (lo, hi):
            bx.plot([i + 0.30, i + 0.42], [max(yy, 0.06)] * 2, color=S.INK2, lw=0.6, zorder=3)
        txt = "0" if v == 0 else (f"{v:.2f}" if v < 1 else f"{v:.1f}")
        bx.text(i - 0.02, vp * 1.18, txt, ha="center", va="bottom", fontsize=6, color=S.INK)
    bx.set_xticks(range(len(labels)), [TICK.get(l, l) for l in labels], fontsize=6,
                  linespacing=0.95)
    bx.tick_params(axis="x", length=0, pad=1)
    bx.grid(False)
    n_ord = len(dd["t"].get("decided_orders") or [])
    ok = dd["t"].get("n_meeting_via_rule")
    bx.set_title(f"{ {'rated': 'Design point', 'thin': 'Thin $C_\\mathrm{f}$'}[case]}: "
                 f"{ok if ok is not None else '?'} of {n_ord} orders meet 1:1",
                 fontsize=6.5, pad=1, loc="left")
bxs[0].set_ylabel("Worst via AR", labelpad=1)
d_via = next(iter(DATA.values()))["d"]
fig.text(0.0, 0.375, f"(b) Worst via aspect ratio per net class at {d_via:.0f}-µm vias",
         ha="left", va="bottom", fontsize=8, color=S.INK)
_t = (DATA.get("rated") or {}).get("t", {})
rs = _t.get("repartition_search") or {}
key_txt = "■ chosen order   | range over every order of the tiers   - - 1:1 build-up limit"
if rs.get("best_worst_ar") and rs.get("n_ordered"):
    key_txt += (f"\ndesign point: best over every regrouping into ≤ {rs.get('max_tiers', '?')} "
                f"tiers ({rs['n_ordered']} orders), AR {rs['best_worst_ar']['worst_ar_both']:.1f}")
sf = _t.get("single_face") or {}
if sf.get("chosen_order_worst_ar_single") is not None:
    key_txt += (f"\ndesign point with single-face terminals: {'same order' if sf.get('same_as_chosen') else 'another order'}"
                f", AR {sf['chosen_order_worst_ar_single']:.1f}")
fig.text(0.0, 0.368, key_txt, ha="left", va="top", fontsize=6, color=S.INK2, linespacing=1.15)
S.save(fig, "fig4_realizability")
