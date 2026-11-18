"""Fig. 9 (proposed): ordering-robustness map — which neighbouring decisions move which
architecture ordering.

Rows: every sensitivity input run on the production mesh at S0 (grouped by the design
decision it represents; identical-outcome parameter sweeps merged, with their count).
Columns: the orderings. Cell state is carried by a glyph AND a fill, never colour alone:
  preserved  ·  light neutral          withdrawn (gap within 2U)  ≈  mid neutral
  reversed toward Z1 / Z2  -> that architecture's identity colour with its label
Top row: the production verdict. Each cell prints the gap Z2 - Z1 under that decision
(min...max over the merged variants; units in the header). Positive: Z1 lower.
Rows of the newer decisions (cooling A, case files sensitivity/etm_{Z1,Z2}_HV_S0__<v>.json)
are classified with the same rule, against twice the paired uncertainty of the production
comparison (research/tcpmt_revision/uncertainty.json, comparisons A Z1/Z2).
Data: classB_sensitivity_rows.csv, ordering.json, uncertainty.json, the case files.
"""
import csv
from collections import OrderedDict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

S.setup()
rows = list(csv.DictReader(open(S.FC / "classB_sensitivity_rows.csv")))
OBS = [("P_loss_package_internal_w", "Package-\ninternal loss"),
       ("T_max_C", "Peak\ntemperature"),
       ("die_warpage_pv_um", "Die\nwarpage"),
       ("du_c_um", "Joint\ndriver $\\Delta u_\\mathrm{c}$")]

# (group, label, [case names merged into this row])
LAYOUT = [
    ("Backside interconnect", [
        ("TSV field minimal (64 per cell)", ["tsv_min"]),
        ("TSV field half density (729 per cell)", ["tsv_mid"]),
        ("Attach sparse (30 µm, 80-µm pitch)", ["attach_sparse"]),
        ("Attach sparse, column-stiffened", ["attach_sparse_stiff"]),
        ("Attach all-solder", ["attach_sn"]),
        ("Attach 40 µm tall", ["attach_h40"]),
        ("Attach 20 µm tall", ["attach_h20"]),
        ("Attach stiffness / underfill (3)", ["attach_stiff", "attach_uf_soft", "attach_uf_stiff"]),
        ("Contact $\\rho_c$ 10$^{-6}$–10$^{-4}$ Ω mm$^2$ (3)",
         ["rho_c=1e-06", "rho_c=1e-05", "rho_c=0.0001"]),
        ("1-V pads at the IR-drop floor", ["pad_drop"]),
    ]),
    ("48-V feed", [
        ("Feed loss deposited in the package", ["feed_heat_at_crossover"]),
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
        ("Z1 tiers in the reference order", ["z1_tier_reference"]),
        ("Out-of-cell volume void", ["f2_void"]),
        ("Opening filled to the PCB sidewall", ["f1_sidewall_filled"]),
        ("Converter-tier conductivity ×0.1", ["conv_k_tenth"]),
        ("GaN-tier conductivity ×0.5", ["gan_k_half"]),
        ("Converter-tier $E$, CTE (4)", ["conv_E80_a4", "conv_E80_a10", "conv_E160_a4",
                                          "conv_E160_a10"]),
    ]),
    ("Board", [
        ("Board-bottom film 100 W/m$^2$K (10)", ["board_hbot100"]),
        ("Board-bottom film 500 W/m$^2$K (10)", ["board_hbot500"]),
        ("PCB as 5-block laminate", ["board_h1"]),
        ("PCB copper coverage 25 % / 75 % (2)", ["board_eta025", "board_eta075"]),
        ("PCB 3.2 mm thick", ["board_t3p2"]),
        ("BGA depopulated (420 of 528)", ["bga_depop"]),
    ]),
]

# newer decisions: (label, variant) run for Z1 and Z2 under cooling A
NEW_A = [("Die hot-spot power map", "die_hotspot_A"),
         ("Local cold-plate $h$ map", "plate_local_h_A"),
         ("TIM warpage feedback", "tim_warp_fb_A")]
OKEY = {"P_loss_package_internal_w": "P", "T_max_C": "T", "die_warpage_pv_um": "warp",
        "du_c_um": "du"}
unc = S.JP(S.TR / "uncertainty.json") or {}
UPAIR = {c["output"]: c["U_D_paired"] for c in unc.get("comparisons", [])
         if c.get("tier") == "A" and {c.get("a"), c.get("b")} == {"Z1", "Z2"}}


def case_obs(c):
    m = c.get("mechanics") or {}
    return {"P_loss_package_internal_w": c.get("P_loss_w"),
            "T_max_C": (c.get("thermal") or {}).get("T_max_C"),
            "die_warpage_pv_um": m.get("die_warpage_pv_um"),
            "du_c_um": ((m.get("joint_search") or {}).get("critical") or {}).get("du_um")}


NEWROWS = {}
for lab, v in NEW_A:
    c1 = S.JP(S.SENS / f"etm_Z1_HV_S0__{v}.json")
    c2 = S.JP(S.SENS / f"etm_Z2_HV_S0__{v}.json")
    if not (c1 and c2):
        continue
    o1, o2 = case_obs(c1), case_obs(c2)
    NEWROWS[v] = {}
    for obs, k in OKEY.items():
        if o1[obs] is None or o2[obs] is None or k not in UPAIR:
            NEWROWS[v][obs] = None
            continue
        d = o2[obs] - o1[obs]
        verdict = ("Z1 lower" if d > 0 else "Z2 lower") if abs(d) > 2 * UPAIR[k] else "unresolved"
        NEWROWS[v][obs] = (d, verdict)
if NEWROWS:
    LAYOUT.append(("Newer decisions (cooling A)",
                   [(lab, ["new:" + v]) for lab, v in NEW_A if v in NEWROWS]))

RANK = {"n/a": 0, "preserved": 1, "withdrawn": 2, "reversed": 3}


def gap(case, obs):
    """Z2 - Z1 under the decision, or None."""
    if case.startswith("new:"):
        x = NEWROWS.get(case[4:], {}).get(obs)
        return x[0] if x else None
    rs = [r for r in rows if r["case"] == case and r["observable"] == obs]
    if not rs or rs[0]["outcome"] in ("n/a", ""):
        return None
    try:
        return float(rs[0]["alternate_Z2"]) - float(rs[0]["alternate_Z1"])
    except ValueError:
        return None


def prod_gap(obs):
    r = next((r for r in rows if r["observable"] == obs and r["nominal_Z1"]), None)
    return float(r["nominal_Z2"]) - float(r["nominal_Z1"]) if r else None


DEC = {"P_loss_package_internal_w": 1, "T_max_C": 1, "die_warpage_pv_um": 1, "du_c_um": 2}


def gtxt(vals, obs):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    dd = DEC[obs]
    f = (lambda v: f"{v:+.{dd}f}".replace("-", "−")) if True else None
    lo, hi = min(vals), max(vals)
    if f(lo) == f(hi):
        return f(lo)
    g = (lambda v: f"{v:.{dd}f}".replace("-", "−"))
    return f"{g(lo)}…{g(hi)}"


def state(case, obs):
    if case.startswith("new:"):
        x = NEWROWS.get(case[4:], {}).get(obs)
        if not x:
            return ("n/a", None)
        alt, prod = x[1], f"{PROD[[o for o, _ in OBS].index(obs)]} lower"
        if alt == prod:
            return ("preserved", None)
        if alt == "unresolved":
            return ("withdrawn", None)
        return ("reversed", alt.split()[0])
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


def _prod(key):
    """The production verdict at S0, read from ordering.json (never typed in)."""
    v = (S.J("ordering.json")["orderings"][key]["per_scenario"] or {}).get("HV_S0", "")
    if v.endswith("lower"):
        return v.split()[0]
    if v.startswith("conditional"):
        return "cond."
    if v.startswith("Z1 lower for any") or v.startswith("Z2 lower for any"):
        return v.split()[0]
    return "≈" if v == "unresolved" else "–"


PROD = [_prod(k) for k, _ in OBS]
HEAD = ["Int. loss\n(W)", "Peak\ntemp. (K)", "Die warp.\n(µm)", "Joint\n$\\Delta u_\\mathrm{c}$ (µm)"]

COLW_IN, ROWH_IN, LAB_IN = 0.45, 0.145, 1.64
n_body = sum(len(g[1]) for g in LAYOUT) + len(LAYOUT)
HEAD_R, LEG_R = 2.4, 4.0                       # header and legend heights, in rows
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


def cell(ix, iy, st, who=None, note=None, val=None):
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
    if val is not None:
        txt = val if st != "prod" else f"{who} {val}"
    ax.text(x + 0.5, y + 0.5 + (0.0 if (big or val) else 0.02), txt, ha="center",
            va="center", fontsize=6.5 if (big or val) else 7.5, color=tc,
            fontweight="bold" if st == "reversed" else "normal")


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
ax.text(xl + 0.15, ly + 2.75, "Numbers: gap Z2 − Z1 (min…max over merged variants);\n"
        "colored: the ordering reverses toward that architecture.", ha="left", va="center",
        fontsize=6.5, color=S.INK2)

# header
for j, lab in enumerate(HEAD):
    ax.text(x0c + j + 0.5, -0.15, lab, ha="center", va="bottom", fontsize=6.5,
            color=S.INK, linespacing=1.0)

iy = 0
ax.text(x0c - 0.12, iy + 0.5, "Production verdict (S0)", ha="right", va="center",
        fontsize=6.6, color=S.INK, fontweight="bold")
for j, v in enumerate(PROD):
    cell(j, iy, "prod", v, val=gtxt([prod_gap(OBS[j][0])], OBS[j][0]))
iy += 1
for gname, items in LAYOUT:
    ax.plot([xl + 0.1, x0c + len(OBS)], [iy + 0.12, iy + 0.12], color=S.GRID, lw=0.6)
    ax.text(xl + 0.1, iy + 0.62, gname, ha="left", va="center", fontsize=6.7,
            color=S.INK, fontstyle="italic")
    iy += 1
    for lab, cases in items:
        ax.text(x0c - 0.12, iy + 0.5, lab, ha="right", va="center", fontsize=6.5,
                color=S.INK2)
        for j, (obs, _) in enumerate(OBS):
            (st, who), note = merged(cases, obs)
            cell(j, iy, st, who, note,
                 val=None if st == "n/a" else gtxt([gap(c, obs) for c in cases], obs))
        iy += 1
S.save(fig, "fig9_robustness_map")
