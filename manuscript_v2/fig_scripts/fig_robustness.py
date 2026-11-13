"""Fig. 9 (proposed): ordering-robustness map — which neighbouring decisions move which
architecture ordering.

Rows: every sensitivity input run on the production mesh at S0 (grouped by the design
decision it represents; identical-outcome parameter sweeps merged, with their count).
Columns: the orderings. Cell state is carried by a glyph AND a fill, never colour alone:
  preserved  ·  light neutral          withdrawn (gap within 2U)  ≈  mid neutral
  reversed toward Z1 / Z2  -> that architecture's identity colour with its label
Top row: the production verdict. Data: classB_sensitivity_rows.csv, ordering.json.
"""
import csv
from collections import OrderedDict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

S.setup()
rows = list(csv.DictReader(open(S.FC / "classB_sensitivity_rows.csv")))
OBS = [("P_loss_package_internal_w", "Package-\ninternal loss"),
       ("P_loss_platform_inclusive_w", "Platform-\nincl. loss"),
       ("T_max_C", "Peak\ntemperature"),
       ("die_warpage_pv_um", "Die\nwarpage"),
       ("du_c_um", "Joint\ndriver $\\Delta u_\\mathrm{c}$")]

# (group, label, [case names merged into this row])
LAYOUT = [
    ("Backside interconnect", [
        ("TSV field minimal (64 per cell)", ["tsv_min"]),
        ("TSV field half density (729 per cell)", ["tsv_mid"]),
        ("Attach sparse (30 µm at 80 µm pitch)", ["attach_sparse"]),
        ("Attach sparse, column-stiffened", ["attach_sparse_stiff"]),
        ("Attach all-solder", ["attach_sn"]),
        ("Attach 40 µm tall", ["attach_h40"]),
        ("Attach 20 µm tall", ["attach_h20"]),
        ("Attach stiffness / underfill (3)", ["attach_stiff", "attach_uf_soft", "attach_uf_stiff"]),
        ("Contact resistivity 10$^{-6}$–10$^{-4}$ Ω cm$^2$ (3)",
         ["rho_c=1e-06", "rho_c=1e-05", "rho_c=0.0001"]),
        ("1-V pads at the IR-drop floor", ["pad_drop"]),
    ]),
    ("48-V feed", [
        ("Direct-feed loop 0.1 $R^*$", ["R_feed = 0.1 R* = 0.177 mOhm"]),
        ("Direct-feed loop = $R^*$", ["R_feed = 1 R* = 1.77 mOhm"]),
        ("Direct-feed loop 10 $R^*$", ["R_feed = 10 R* = 17.7 mOhm"]),
        ("Feed loss deposited inside the package", ["feed_heat_at_crossover"]),
        ("Z1 48-V RDL with more copper (3)",
         ["t_cu=0.005, occupancy=0.8", "t_cu=0.01, occupancy=0.3", "t_cu=0.01, occupancy=0.8"]),
        ("Z1 48-V RDL with less copper (2)",
         ["t_cu=0.002, occupancy=0.3", "t_cu=0.005, occupancy=0.3"]),
    ]),
    ("Cooling", [
        ("Second cold plate under Z2", ["z2_cooled"]),
        ("Z2 backside plate via 50 µm TIM", ["z2_cooled_tim"]),
        ("Cold-plate $h$ from conjugate CFD", ["icepak_equivalent"]),
    ]),
    ("Construction, materials", [
        ("Out-of-cell volume void", ["f2_void"]),
        ("Opening filled to the PCB sidewall", ["f1_sidewall_filled"]),
        ("Converter-tier conductivity ×0.1", ["conv_k_tenth"]),
        ("GaN-tier conductivity ×0.5", ["gan_k_half"]),
        ("Converter-tier $E$, CTE (4)", ["conv_E80_a4", "conv_E80_a10", "conv_E160_a4",
                                          "conv_E160_a10"]),
    ]),
    ("Board", [
        ("PCB as 5-block laminate", ["board_h1"]),
        ("PCB copper coverage 25 % / 75 % (2)", ["board_eta025", "board_eta075"]),
        ("PCB 3.2 mm thick", ["board_t3p2"]),
        ("BGA field depopulated (420 of 528)", ["bga_depop"]),
    ]),
]

RANK = {"n/a": 0, "preserved": 1, "withdrawn": 2, "reversed": 3}


def state(case, obs):
    rs = [r for r in rows if r["case"] == case and r["observable"] == obs]
    if not rs:
        return ("n/a", None)
    r = rs[0]
    alt, prod = r["alternate_verdict"].strip(), r["production_verdict"].strip()
    if r["outcome"] in ("n/a", "") or alt in ("", "--", "n/a"):
        return ("n/a", None)
    if alt == prod:
        return ("preserved", None)
    if alt == "unresolved":
        return ("withdrawn", None)
    if alt in ("Z1 lower", "Z2 lower"):
        return ("reversed", alt.split()[0])
    return ("n/a", None)


def merged(cases, obs):
    st = [state(c, obs) for c in cases]
    st = [s for s in st if s[0] != "n/a"] or [("n/a", None)]
    worst = max(st, key=lambda s: RANK[s[0]])
    n = sum(1 for s in st if s == worst)
    return worst, (n, len(st)) if len(st) > 1 and n != len(st) else None


PROD = ["Z2", "cond.", "Z1", "Z1", "Z1"]       # production verdicts at S0 (ordering.json)
HEAD = ["Int.\nloss", "Platf.\nloss", "Peak\ntemp.", "Die\nwarp.", "Joint\ndriver"]

COLW_IN, ROWH_IN, LAB_IN = 0.31, 0.138, 1.92
n_body = sum(len(g[1]) for g in LAYOUT) + len(LAYOUT)
HEAD_R, LEG_R = 2.3, 3.3                       # header and legend heights, in rows
W = S.COL_W
H = (n_body + 1 + HEAD_R + LEG_R) * ROWH_IN + 0.05
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
xl = -LAB_IN / COLW_IN                          # label area in column units
xr = (W - LAB_IN) / COLW_IN
ax.set_xlim(xl, xr)
ax.set_ylim(n_body + 1 + 0.15, -(HEAD_R + LEG_R))
ax.axis("off")
FILL = {"preserved": "#f3f2ee", "withdrawn": "#cfcdc6", "n/a": "white"}
GLYPH = {"preserved": "·", "withdrawn": "≈", "n/a": "–"}
x0c = 0.12                                      # left inset of the cell block


def cell(ix, iy, st, who=None, note=None):
    x, y = x0c + ix, iy
    pad = 0.07
    if st == "reversed":
        fc, txt, tc, ec = S.ARCH[who], who, "white", "none"
    elif st == "prod":
        if who in S.ARCH:
            fc, txt, tc, ec = S.ARCH[who], who, "white", "none"
        else:
            fc, txt, tc, ec = "white", who, S.INK, S.AXIS
    else:
        fc, txt, tc, ec = FILL[st], GLYPH[st], S.INK2, "none"
    ax.add_patch(Rectangle((x + pad, y + pad), 1 - 2 * pad, 1 - 2 * pad, fc=fc, ec=ec,
                           lw=0.5))
    big = st in ("reversed", "prod")
    ax.text(x + 0.5, y + 0.5 + (0.0 if big else 0.02), txt, ha="center", va="center",
            fontsize=6.2 if big else 7.5, color=tc,
            fontweight="bold" if st == "reversed" else "normal")
    if note:
        ax.text(x + 0.93, y + 0.90, f"{note[0]}/{note[1]}", ha="right", va="bottom",
                fontsize=4.4, color="white" if st == "reversed" else S.INK2)


# legend block (top)
ly = -(HEAD_R + LEG_R) + 0.55
items = [("prod", "Z1", "Z1 lower"), ("prod", "Z2", "Z2 lower"),
         ("preserved", None, "preserved"), ("withdrawn", None, "withdrawn (gap < 2$U$)"),
         ("n/a", None, "not evaluated")]
pos = [(xl + 0.15, ly), (xl + 2.65, ly), (xl + 5.15, ly), (xl + 0.15, ly + 1.0),
       (xl + 5.15, ly + 1.0)]
for (st, who, lab), (lx, lyy) in zip(items, pos):
    fc = S.ARCH[who] if who else FILL[st]
    ax.add_patch(Rectangle((lx, lyy), 0.62, 0.78, fc=fc, ec="none"))
    ax.text(lx + 0.31, lyy + 0.41, who if who else GLYPH[st], ha="center", va="center",
            fontsize=5.6 if who else 7.5, color="white" if who else S.INK2,
            fontweight="bold" if who else "normal")
    ax.text(lx + 0.8, lyy + 0.41, lab, ha="left", va="center", fontsize=6.5, color=S.INK2)
ax.text(xl + 0.15, ly + 2.35, "Coloured cell in the map: the ordering reverses toward that "
        "architecture;  n/m: n of m merged variants.", ha="left", va="center",
        fontsize=6.0, color=S.INK2)

# header
for j, lab in enumerate(HEAD):
    ax.text(x0c + j + 0.5, -0.15, lab, ha="center", va="bottom", fontsize=6.4,
            color=S.INK, linespacing=1.0)

iy = 0
ax.text(x0c - 0.12, iy + 0.5, "Production verdict (S0)", ha="right", va="center",
        fontsize=6.6, color=S.INK, fontweight="bold")
for j, v in enumerate(PROD):
    cell(j, iy, "prod", v)
iy += 1
for gname, items in LAYOUT:
    ax.plot([xl + 0.1, x0c + len(OBS)], [iy + 0.12, iy + 0.12], color=S.GRID, lw=0.6)
    ax.text(xl + 0.1, iy + 0.62, gname, ha="left", va="center", fontsize=6.7,
            color=S.INK, fontstyle="italic")
    iy += 1
    for lab, cases in items:
        ax.text(x0c - 0.12, iy + 0.5, lab, ha="right", va="center", fontsize=6.2,
                color=S.INK2)
        for j, (obs, _) in enumerate(OBS):
            (st, who), note = merged(cases, obs)
            cell(j, iy, st, who, note)
        iy += 1
S.save(fig, "fig9_robustness_map")
