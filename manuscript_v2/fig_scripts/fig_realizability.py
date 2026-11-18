"""Fig. 4 (paper Fig. 5): tier order is a realizability constraint, for both capacitor cases.

(a) The same four component tiers in the reference order (HS, LS, C_f, L) and the
    repartitioned order (HS, C_f, LS, L), to scale in z, for
    A0 -- the technology-conditional 100-um flying-capacitor tier of the production stack, and
    A1 -- the rated 0603 MLCC tier (maximum part height + mounting allowance).
    A bar marks each net that must cross a whole tier with a build-up via.
(b) Worst via aspect ratio per net at the assumed build-up via diameter
    (AR = crossed depth / diameter), against the 1:1 build-up (stacked-microvia) limit.

Data: tier heights from configs/phase0nx/z1_physical.yaml (production stack, A0); the A1 tier
height and the via diameter from research/tcpmt_revision/flying_caps.json
(summary.min_tier_um_10pct, summary.via_AR_10pct; diameter = tier / AR).
"""
import yaml
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

S.setup()
cfg = yaml.safe_load(open(S.SRC / "configs" / "phase0nx" / "z1_physical.yaml"))
tiers = cfg["converter"]["tiers_from_substrate_upward"]


def tier_um(prefix):
    return next(float(t["um"]) for t in tiers if t["name"].startswith(prefix))


T0 = {"HS": tier_um("gan_hs"), "LS": tier_um("gan_ls"), "Cf": tier_um("flying_caps"),
      "L": tier_um("inductor_plus_cout")}
RDL = tier_um("interlayer_rdl")
fc = (S.JP(S.TR / "flying_caps.json") or {}).get("summary") or {}
CASES = {"A0": dict(T0)}
if fc.get("min_tier_um_10pct") and fc.get("via_AR_10pct"):
    tA1 = float(fc["min_tier_um_10pct"][-1])
    D_VIA = tA1 / float(fc["via_AR_10pct"][-1])
    CASES["A1"] = dict(T0, Cf=tA1)
else:
    D_VIA = None
if D_VIA is None:
    raise SystemExit("flying_caps.json summary missing: via diameter unknown")
D_VIA = round(D_VIA, 6)

FILL = {"HS": S.MAT["gan"], "LS": S.MAT["gan"], "Cf": S.MAT["caps"], "L": S.MAT["inductor"]}
SHORT = {"HS": "HS", "LS": "LS", "Cf": "", "L": "L"}
ORD = {"ref.": ["HS", "LS", "Cf", "L"], "repart.": ["HS", "Cf", "LS", "L"]}
NETS = [("HS", "Cf", "HS→$C_\\mathrm{f}$"), ("HS", "LS", "HS→LS"), ("LS", "L", "SW→$L$")]
CASE_LAB = {"A0": f"A0: {T0['Cf']:.0f}-µm $C_\\mathrm{{f}}$ tier",
            "A1": f"A1: rated 0603 MLCC, {CASES.get('A1', T0)['Cf']:.0f}-µm tier"}

fig = plt.figure(figsize=(S.COL_W, 3.55))
ax = fig.add_axes([0.0, 0.39, 1.0, 0.55])
bxs = [fig.add_axes([0.12, 0.075, 0.36, 0.20]), fig.add_axes([0.61, 0.075, 0.36, 0.20])]
W = 0.55


def stack(x0, T, order):
    z, ext = 0.0, {}
    for k, t in enumerate(order):
        ax.add_patch(Rectangle((x0, z), W, T[t], fc=FILL[t], ec="none"))
        if SHORT[t]:
            ax.text(x0 + W / 2, z + T[t] / 2, SHORT[t], ha="center", va="center",
                    fontsize=6.5, color="white")
        ext[t] = (z, z + T[t])
        z += T[t]
        if k < 3:
            ax.plot([x0, x0 + W], [z + RDL / 2] * 2, color=S.MAT["rdl"], lw=1.0)
            z += RDL
    return ext, z


res = {}
xs = {("A0", "ref."): 0.0, ("A0", "repart."): 1.0, ("A1", "ref."): 2.4, ("A1", "repart."): 3.4}
ztop = 0.0
for (case, name), x0 in xs.items():
    if case not in CASES:
        continue
    T = CASES[case]
    ext, z = stack(x0, T, ORD[name])
    ztop = max(ztop, z)
    ax.text(x0 + W / 2, -60, name, ha="center", va="top", fontsize=6.5, color=S.INK)
    res[(case, name)] = {}
    for a, b, nl in NETS:
        za, zb = ext[a], ext[b]
        lo, hi = (za, zb) if za[0] < zb[0] else (zb, za)
        depth = max(hi[0] - lo[1] - 2 * RDL, 0.0)        # dielectric between capture planes
        ar = (depth if depth > 0 else RDL) / D_VIA
        res[(case, name)][nl] = ar
        if depth > 0:
            xv = x0 + W + 0.07
            ax.plot([xv, xv], [lo[1], hi[0]], color=S.INK, lw=1.6 if ar > 1 else 0.9,
                    solid_capstyle="butt")
            for zz in (lo[1], hi[0]):
                ax.plot([xv - 0.04, xv + 0.04], [zz] * 2, color=S.INK, lw=0.6)
            ax.text(xv + 0.05, (lo[1] + hi[0]) / 2, f"{nl}\n{depth:.0f} µm", ha="left",
                    va="center", fontsize=6.5, color=S.INK, linespacing=1.0)
for case, x0 in (("A0", 0.0), ("A1", 2.4)):
    if case in CASES:
        ax.text(x0 - 0.05, ztop + 120, CASE_LAB[case], ha="left", va="bottom", fontsize=6.5,
                color=S.INK)
        # thin C_f tier label for A0
zc = None
if "A0" in CASES:
    ax.annotate("$C_\\mathrm{f}$", (0.0, T0["HS"] + T0["LS"] + 2 * RDL + T0["Cf"] / 2),
                xytext=(-0.05, T0["HS"] + T0["LS"] + 2 * RDL + T0["Cf"] / 2), ha="right",
                va="center", fontsize=6.5, color=S.INK2)
if "A1" in CASES:
    zA1 = T0["HS"] + RDL + CASES["A1"]["Cf"] / 2
    ax.text(3.4 + W / 2, zA1, "$C_\\mathrm{f}$", ha="center", va="center", fontsize=6.5,
            color=S.INK)
    zA1r = T0["HS"] + T0["LS"] + 2 * RDL + CASES["A1"]["Cf"] / 2
    ax.text(2.4 + W / 2, zA1r, "$C_\\mathrm{f}$", ha="center", va="center", fontsize=6.5,
            color=S.INK)
ax.set_xlim(-0.40, 4.98)
ax.set_ylim(-260, ztop + 560)
ax.axis("off")
ax.plot([-0.32, -0.32], [0, 500], color=S.INK, lw=0.8)
ax.text(-0.27, 250, "500 µm", rotation=90, ha="left", va="center", fontsize=6.5)
S.panel(ax, "a", "Same tiers, two orders, two capacitor cases", x=0.0, y=0.985)

# (b) worst AR per net, one small axis per case
nets = [n for _, _, n in NETS]
w = 0.36
for bx, case in zip(bxs, ("A0", "A1")):
    bx.set_yscale("log")
    bx.set_ylim(0.05, 60)
    bx.axhline(1.0, color=S.MUTED, lw=0.7, ls=(0, (2, 2)))
    if case not in CASES:
        S.pending(bx, 0.1, 0.5, f"{case} tier", "flying_caps.json")
        continue
    for k, name in enumerate(ORD):
        worst = max(res[(case, name)].values())
        for i, n in enumerate(nets):
            v = res[(case, name)][n]
            x = i + (k - 0.5) * (w + 0.04)
            bx.bar(x, v, w, color=S.INK if k == 0 else "white", edgecolor=S.INK, lw=0.7,
                   zorder=2)
            bx.text(x, v * 1.15, f"{v:.2f}" if v < 1 else f"{v:.1f}", ha="center",
                    va="bottom", fontsize=6.5, color=S.INK, rotation=90 if v >= 1 else 0)
    bx.set_xticks(range(len(nets)), nets, fontsize=6.5)
    bx.tick_params(axis="x", length=0, pad=1)
    bx.grid(False)
    bx.set_title(case, fontsize=7, pad=1, loc="left")
bxs[0].set_ylabel("Worst via AR", labelpad=1)
if "A1" in CASES and min(max(res[("A1", n)].values()) for n in ORD) > 1.0:
    bxs[1].set_title("A1: both > 1, copper posts", fontsize=6.5, pad=1,
                     loc="left")
fig.text(0.0, 0.34, f"(b) Worst via aspect ratio per net at {D_VIA:.0f}-µm vias", ha="left",
         va="bottom", fontsize=8, color=S.INK)
# order key
fig.text(0.0, 0.30, "■ reference order   □ repartitioned order   - - 1:1 build-up limit",
         ha="left", va="bottom", fontsize=6.5, color=S.INK2)
S.save(fig, "fig4_realizability")
