"""Fig. 2 (proposed): the synthesised hybrid regulator cell (vector redraw of the thesis
schematic) and its two switching phases.

(a) 3:1 switched-capacitor stage feeding K = 3 inductor branches (N = 3, K_A = 2):
    S1, S3 conduct in phase A (L1, L3 driven at 16 V), S2 in phase B (L2 driven at 16 V);
    S4-S6 freewheel the undriven inductors. C1 holds 32 V, C2 16 V.
(b) Gate timing over one period T = 1/f_sw with D = D_DUTY, and the input current drawn
    from the 48-V rail (only in phase A) - the origin of the pulsed-input scenarios; the sum
    over the decoupling plan's interleaved clock phases.
D, f_sw, the branch current, the clock phases and the C_in ring are read from the decoupling
chain's artifact (tcpmt_revision/input_decoupling.json), else from the design record (D, f_sw,
I_cell / K and its committed decoupling plan); k bare -> with C_in from the macros, else from
the artifact. The schematic is the N3K3K_A2 cell: another topology is refused.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Arc, FancyArrowPatch
import re
import style as S

S.setup()
if S.DR.topology() != (3, 3, 2):
    raise SystemExit(f"fig_converter draws the N3K3K_A2 cell; design {S.DR.name()} is "
                     f"N{S.DR.topology()[0]}K{S.DR.topology()[1]}K_A{S.DR.topology()[2]}")
dec = S.JP(S.TR / "input_decoupling.json") or {}
des = (dec.get("circuit") or {}).get("design") or {}
if des.get("n_cell") not in (None, S.DR.n_vr()):
    raise SystemExit(f"input_decoupling.json is of {des.get('n_cell')} cells, the design in "
                     f"force has {S.DR.n_vr()}")
summ = dec.get("summary") or {}
rec = summ.get("recommended") or {}
_drd = S.DR.get().get("decoupling") or {}
D_DUTY = des.get("D") or S.DR.buck_duty()
FSW_K = (des.get("f_sw_hz") or S.DR.get()["f_sw_hz"]) / 1e3
I_L = des.get("I_L_a") or S.DR.i_cell_a() / S.DR.topology()[1]
m_ph = re.search(r"(\d+) clock phases", rec.get("interleaving", ""))
N_PH = (rec.get("n_clock_phases") or (int(m_ph.group(1)) if m_ph else None))
m_cin = re.search(r"\((\d+) x (\d{4}) ([\d.]+-V \w+), ([\d.]+) uF",
                  summ.get("figure_caption", ""))
_kled = (summ.get("ledger_at_S0_temperatures") or {}).get("k_eq") or rec.get("k_eq")
K_OPEN = S.macro("DecapKopen") or (f"{summ['k_open_cell_waveform']:.1f}"
                                   if summ.get("k_open_cell_waveform") else None)
K_EQ = S.macro("DecapKeq") or (f"{_kled:.2f}" if _kled else None)
if not dec:                                     # the committed plan of the design record
    K_OPEN = K_OPEN or (f"{_drd['k_open']:.1f}" if _drd.get("k_open") else None)
    K_EQ = K_EQ or (f"{_drd['k_eq']:.2f}" if _drd.get("k_eq") else None)
    _mp = re.match(r"(dual|latin|rows)(\d+)", str(_drd.get("phase_pattern") or ""))
    if N_PH is None and _mp:
        N_PH = int(_mp.group(2)) * (2 if _mp.group(1) == "dual" else 1)
LW = 0.9
fig = plt.figure(figsize=(S.COL_W, 4.25))
ax = fig.add_axes([0.0, 0.385, 1.0, 0.60])
ax.set_xlim(-0.2, 10.2)
ax.set_ylim(0.0, 8.3)
ax.set_aspect("equal")
ax.axis("off")


def w(x0, y0, x1, y1, c=S.INK, lw=LW):
    ax.plot([x0, x1], [y0, y1], color=c, lw=lw, solid_capstyle="round", zorder=2)


def dot(x, y):
    ax.add_patch(Circle((x, y), 0.07, fc=S.INK, ec="none", zorder=4))


def sw_v(x, yt, yb, name, ph):
    """vertical SPST between yt (top) and yb (bottom)"""
    g = (yt - yb)
    w(x, yt, x, yt - 0.28 * g)
    w(x, yb, x, yb + 0.28 * g)
    ax.add_patch(Circle((x, yb + 0.28 * g), 0.05, fc="white", ec=S.INK, lw=0.7, zorder=3))
    w(x, yb + 0.28 * g, x - 0.32, yt - 0.30 * g)
    ax.text(x - 0.42, (yt + yb) / 2 + 0.05, name, ha="right", va="center", fontsize=7)
    ax.text(x + 0.16, (yt + yb) / 2 + 0.05, ph, ha="left", va="center", fontsize=7,
            fontweight="bold")


def sw_h(xl, xr, y, name, ph, gnd_right=True):
    g = xr - xl
    w(xl, y, xl + 0.28 * g, y)
    w(xr - 0.28 * g, y, xr, y)
    ax.add_patch(Circle((xl + 0.28 * g, y), 0.05, fc="white", ec=S.INK, lw=0.7, zorder=3))
    w(xl + 0.28 * g, y, xr - 0.30 * g, y + 0.30)
    ax.text((xl + xr) / 2, y + 0.42, name, ha="center", va="bottom", fontsize=7)
    ax.text((xl + xr) / 2, y - 0.16, ph, ha="center", va="top", fontsize=7,
            fontweight="bold")
    gx = xr if gnd_right else xl
    gnd(gx, y)


def gnd(x, y, down=True):
    w(x, y, x, y - 0.18)
    for k, hw in enumerate((0.20, 0.13, 0.06)):
        w(x - hw, y - 0.18 - 0.08 * k, x + hw, y - 0.18 - 0.08 * k, lw=0.8)


def cap_h(x0, x1, y, name, val):
    xm = (x0 + x1) / 2
    w(x0, y, xm - 0.09, y)
    w(xm + 0.09, y, x1, y)
    w(xm - 0.09, y - 0.26, xm - 0.09, y + 0.26, lw=1.2)
    w(xm + 0.09, y - 0.26, xm + 0.09, y + 0.26, lw=1.2)
    ax.text(xm, y + 0.36, f"{name} ({val})", ha="center", va="bottom", fontsize=6.8)


def cap_v(x, y0, y1, name):
    ym = (y0 + y1) / 2
    w(x, y1, x, ym + 0.09)
    w(x, y0, x, ym - 0.09)
    w(x - 0.26, ym + 0.09, x + 0.26, ym + 0.09, lw=1.2)
    w(x - 0.26, ym - 0.09, x + 0.26, ym - 0.09, lw=1.2)
    ax.text(x - 0.36, ym, name, ha="right", va="center", fontsize=7)


def ind_v(x, yt, yb, name, cur):
    n, r = 4, 0.17
    ys = np.linspace(yt - 0.35, yt - 0.35 - 2 * r * n, n + 1)
    w(x, yt, x, ys[0])
    for k in range(n):
        ax.add_patch(Arc((x, ys[k] - r), 2 * r, 2 * r, theta1=-90, theta2=90, color=S.INK,
                         lw=LW, zorder=2))
    w(x, ys[-1], x, yb)
    ax.text(x + 0.30, (yt + yb) / 2 + 0.25, name, ha="left", va="center", fontsize=7)
    ax.text(x + 0.30, (yt + yb) / 2 - 0.15, cur, ha="left", va="center", fontsize=6.5,
            color=S.INK2)


IL_TXT = f"{I_L:.1f} A"
# rails
YIN, YB = 7.7, 1.25
X = 5.0
# input source
ax.add_patch(Circle((1.0, 6.9), 0.34, fc="white", ec=S.INK, lw=LW, zorder=3))
ax.text(1.0, 7.03, "+", ha="center", va="center", fontsize=7)
ax.text(1.0, 6.78, "−", ha="center", va="center", fontsize=7)
w(1.0, 7.24, 1.0, YIN, c=S.V48, lw=1.4)
w(1.0, YIN, X, YIN, c=S.V48, lw=1.4)
gnd(1.0, 6.56)
# package input capacitance (ring outside the cell grid)
XC = 2.75
dot(XC, YIN)
cap_v(XC, 6.75, YIN, "")
gnd(XC, 6.75)
ax.text(XC + 0.36, 7.25, "$C_\\mathrm{in}$", ha="left", va="center", fontsize=7)
ax.text(XC + 0.36, 6.85, "(ring)", ha="left", va="center", fontsize=6.5, color=S.INK2)
ax.text(0.5, 6.9, "48 V", ha="right", va="center", fontsize=7)
# stack S1 - S2 - S3
n1, n2, n3 = 6.35, 5.0, 3.35
sw_v(X, YIN, n1 + 0.05, "S$_1$", "A")
dot(X, n1)
sw_v(X, n1, n2 + 0.05, "S$_2$", "B")
dot(X, n2)
sw_v(X, n2, n3 + 0.05, "S$_3$", "A")
dot(X, n3)
# C1 to Vx1 (right), S5, L1
XV1 = 8.3
cap_h(X, XV1, n1, "C$_1$", "32 V")
dot(XV1, n1)
sw_h(XV1, XV1 + 1.25, n1, "S$_5$", r"$\overline{\mathrm{A}}$")
ind_v(XV1, n1, YB, "L$_1$", IL_TXT)
# C2 to Vx2 (left), S6, L2
XV2 = 2.1
cap_h(XV2, X, n2, "C$_2$", "16 V")
dot(XV2, n2)
sw_h(XV2 - 1.25, XV2, n2, "S$_6$", r"$\overline{\mathrm{B}}$", gnd_right=False)
ind_v(XV2, n2, YB, "L$_2$", IL_TXT)
# n3: S4, L3
sw_h(X + 0.25, X + 1.5, n3, "S$_4$", r"$\overline{\mathrm{A}}$")
w(X, n3, X + 0.25, n3)
ind_v(X, n3, YB, "L$_3$", IL_TXT)
# output bus
w(XV2, YB, XV1 + 0.9, YB, c=S.V1, lw=1.4)
for xx in (XV2, X, XV1):
    dot(xx, YB)
cap_v(3.55, 0.35, YB, "C$_\\mathrm{o}$")
gnd(3.55, 0.35)
ax.add_patch(Circle((XV1 + 0.9, 0.8), 0.28, fc="white", ec=S.INK, lw=LW, zorder=3))
ax.add_patch(FancyArrowPatch((XV1 + 0.9, 1.0), (XV1 + 0.9, 0.58), arrowstyle="-|>",
                             mutation_scale=6, color=S.INK, lw=0.8, zorder=4))
w(XV1 + 0.9, YB, XV1 + 0.9, 1.08)
gnd(XV1 + 0.9, 0.52)
ax.text(XV1 + 1.25, 0.8, f"{3 * I_L:.1f} A", ha="left", va="center", fontsize=6.6)
ax.text(XV2 - 0.15, YB + 0.18, "1 V", ha="right", va="bottom", fontsize=7)
S.panel(ax, "a", "Hybrid cell: 3:1 SC stage + $K$ = 3 inductor branches", x=0.0, y=0.985)

# ---------------------------------------------------------------- (b) timing
bx = fig.add_axes([0.13, 0.135, 0.83, 0.20])
T = 1.0
D = float(D_DUTY)                       # the buck duty N V_out / V_in of the design in force
t = np.linspace(0, 2 * T, 4001)
sig = {"A (S$_1$, S$_3$)": ((t % T) < D),
       "B (S$_2$)": (((t - T / 2) % T) < D),
       "$i_\\mathrm{in}$, cell": ((t % T) < D)}
if N_PH:
    sig[f"$\\Sigma i_\\mathrm{{in}}$, {N_PH} ph."] = np.any(
        [(((t - j * T / N_PH) % T) < D) for j in range(N_PH)], axis=0)
for k, (name, s) in enumerate(sig.items()):
    base = len(sig) - 1 - k
    col = S.V48 if k >= 2 else S.INK
    bx.fill_between(t, base, base + 0.7 * s, step="pre", color=col,
                    alpha=0.18 if k >= 2 else 0.0, lw=0)
    bx.step(t, base + 0.7 * s, where="pre", color=col, lw=0.9)
    bx.text(-0.04, base + 0.25, name, ha="right", va="center", fontsize=6.6)
bx.set_xlim(0, 2 * T)
bx.set_ylim(-0.15, len(sig) - 0.05)
bx.set_yticks([])
bx.set_xticks([0, T / 2, T, 1.5 * T, 2 * T], ["0", "$T$/2", "$T$", "3$T$/2", "2$T$"])
bx.spines["left"].set_visible(False)
bx.grid(False)
yb_ = len(sig) - 1
bx.annotate("", (T + D, yb_ + 0.85), (T, yb_ + 0.85), arrowprops=dict(
    arrowstyle="<->", lw=0.6, color=S.INK2, shrinkA=0, shrinkB=0))
bx.text(T + D + 0.03, yb_ + 0.85, f"$DT$ ($D$ = {D:.4g})", ha="left", va="center",
        fontsize=6.5, color=S.INK2)
bx.text(0.14, len(sig) - 2.6, "input current only in phase A", ha="left", va="center",
        fontsize=6.5, color=S.INK2)
S.panel(bx, "b", f"Two switching phases ($f_\\mathrm{{sw}}$ = {FSW_K:.0f} kHz)", x=-0.13,
        y=1.02)
lines = []
if m_cin:
    n_, size_, rat_, c_ = m_cin.groups()
    lines.append(f"$C_\\mathrm{{in}}$: {n_} × {size_} {rat_}, {float(c_):.0f} µF, "
                 "in a ring outside the cell grid")
else:
    S.pending(bx, 0.0, -0.75, "C_in parts", "input_decoupling.json")
if N_PH and K_OPEN and K_EQ:
    lines.append(f"{N_PH} interleaved clock phases + $C_\\mathrm{{in}}$: "
                 f"$k$ = {K_OPEN} (bare) → {K_EQ}")
fig.text(0.02, 0.005, "\n".join(lines), ha="left", va="bottom", fontsize=6.5, color=S.INK,
         linespacing=1.2)
S.save(fig, "fig2_converter")
