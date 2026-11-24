"""Fig. 9 (paper Fig. 11): ordering-robustness map -- which package decisions move which
ranking of the embedded (Z1) and package-backside (Z2) regulators.

Rows: every sensitivity input run on the production mesh, grouped by the design decision it
represents (identical-outcome parameter sweeps merged, with their count). The classical
decisions are run on the ideal-decoupling reference (k_rms = 1, cooling A); the group
"Implemented decoupling, cooling A" holds the decisions run in the production state, and it
opens with its own production-verdict row, so each group is read against its own baseline.
Columns: the rankings; the joint column is the joint response of each integration, solved at
the K worst sites of its reference case or, where escalated, by a full critical-joint search
(tcpmt_mech_joint_screen -> robustness_joint.json; the
largest ball displacement, the disproven proxy, is no longer a column). Cell state is carried by a
glyph AND a fill, never colour alone:
  preserved  ·  light neutral          withdrawn ( |D + beta| <= U95 )  ≈  mid neutral
  reversed toward Z1 / Z2  -> that architecture's identity colour with its label
  pending (the variant's mesh differs; its own ladder is needed)  ?
Each cell prints the gap Z2 - Z1 under that decision (min...max over the merged variants;
units in the header). Positive: Z1 lower.
ONE RULE (scripts/tcpmt_resolution.py): every cell is the verdict final_closure_classB.py
formed with the rule of Table IV, |D + beta_D| > U95(D); this script classifies nothing
itself. A variant has no ladder of its own: its U is the production pair's, transferred
provisionally on the identical mesh; a variant on another mesh is PENDING.
Data: classB_sensitivity_rows.csv (gate rows and robustness.newer_decisions_A rows),
robustness_B.json / robustness_mech_SDEC.json (mechanics-only groups), robustness_joint.json
(the joint column of every group).
"""
import csv
from collections import OrderedDict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

S.setup()
rows = list(csv.DictReader(open(S.FC / "classB_sensitivity_rows.csv")))
#: the joint column: the joint response of each integration, solved at the worst sites of its
#: reference case or searched in full where escalated (tcpmt_mech_joint_screen ->
#: robustness_joint.json), judged with the same rule
JOINT = "d_eps_screen"
OBS = [("P_loss_package_internal_w", "Package-\ninternal loss"),
       ("T_max_C", "Peak\ntemperature"),
       ("die_warpage_pv_um", "Die\nwarpage"),
       (JOINT, "Joint\nresponse")]

# (group, label, [case names merged into this row])
LAYOUT = [
    ("Backside interconnect", [
        ("TSV field minimal (64 per cell)", ["tsv_min"]),
        ("TSV field reduced (729 per cell)", ["tsv_mid"]),
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
        ("Out-of-cell volume void", ["f2_void"]),
        ("Opening filled to the PCB sidewall", ["f1_sidewall_filled"]),
        ("Converter-tier conductivity ×0.1", ["conv_k_tenth"]),
        ("GaN-tier conductivity ×0.5", ["gan_k_half"]),
        ("Converter-tier $E$, CTE (4)", ["conv_E80_a4", "conv_E80_a10", "conv_E160_a4",
                                          "conv_E160_a10"]),
        ("Low-CTE mold compound (2)", ["encap_emc_lowcte", "encap_emc_lowcte_const"]),
        ("Underfill-class encapsulant", ["encap_uf_tg"]),
    ]),
    ("Board", [
        ("Board-bottom film 10 → 100 W/m$^2$K", ["board_hbot100"]),
        ("Board-bottom film 10 → 500 W/m$^2$K", ["board_hbot500"]),
        ("Layered board (copper per layer)", ["board_h1"]),
        ("PCB copper coverage 25 % / 75 % (2)", ["board_eta025", "board_eta075"]),
        ("PCB 2.4 mm thick", ["board_t2p4"]),
        ("BGA depopulated (420 of 528)", ["bga_depop"]),
        ("BGA layer from the local solder card", ["bga_card_local"]),
    ]),
]

# newer decisions: (label, variant) run for Z1 and Z2 under cooling A, classified by
# final_closure_classB.py (gate robustness.newer_decisions_A) with the same rule
NEW_A = [("Core-heavy die power map", "die_hotspot_A"),
         ("Plate interface follows the warpage", "tim_warp_fb_A")]
NEWER_GATE = "robustness.newer_decisions_A"
NEWER_GROUP = "Implemented decoupling, cooling A"
_have = {r["case"] for r in rows if r["gate"] == NEWER_GATE}
if _have:
    LAYOUT.append((NEWER_GROUP, [(lab, [v]) for lab, v in NEW_A if v in _have]))

# TCPMT round 3 (finding 8 and the production-state mechanics): mechanics-only decisions run
# on converged fields, judged with the same rule against their own baseline (the cooling-B
# reference case, or each production-state case), from tcpmt_mech_variants (judgeB /
# judge-state). Each becomes a group with its own baseline row; loss and peak temperature are
# not evaluated (mechanics only).
import json                                                          # noqa: E402
MECH_LABEL = {"encap_uf_tg": "Underfill-class encapsulant",
              "encap_emc_lowcte": "Low-CTE mold compound",
              "encap_emc_lowcte_const": "Mold compound without glass transition",
              "bga_card_local": "BGA layer from the local solder card",
              "attach_stiff": "Attach card column-stiffened", "attach_uf_soft": "Attach underfill soft",
              "attach_uf_stiff": "Attach underfill stiff"}
OBS_KEY = {"warp": "die_warpage_pv_um", "du": "du_c_um"}
GROUP_GATE = {NEWER_GROUP: NEWER_GATE}       # group -> gate of its own baseline row


def _mech_label(name):
    if name in MECH_LABEL:
        return MECH_LABEL[name]
    if name.startswith("conv_E"):
        return "Converter-tier $E$, CTE"
    return name


def _mech_rows(gate, case, orderings, values, base):
    """classB-style rows (the Z1/Z2 ordering of warpage and du) of one mechanics-only
    decision, for state() / gap() / prod_gap()."""
    out = []
    for y, obs in OBS_KEY.items():
        o = orderings.get(f"{y}:Z1/Z2")
        if not o:
            continue
        bl = o.get("base_verdict") or f"{o['base_lower']} lower"
        out.append({"gate": gate, "case": case, "observable": obs,
                    "alternate_verdict": o.get("verdict") or "pending",
                    "production_verdict": bl, "outcome": "judged",
                    "alternate_Z1": str((values.get("Z1") or {}).get(y)),
                    "alternate_Z2": str((values.get("Z2") or {}).get(y)),
                    "nominal_Z1": str((base.get("Z1") or {}).get(y)),
                    "nominal_Z2": str((base.get("Z2") or {}).get(y))})
    return out


def _mech_groups():
    groups = []
    d = S.TR / "robustness_B.json"
    if d.is_file():
        rb = json.loads(d.read_text())
        gate, items, merged_ = "robustness.cooling_B_mech", [], {}
        for name, r in (rb.get("variants") or {}).items():
            base = {a: v for a, v in (rb.get("base") or {}).items()}
            new = _mech_rows(gate, f"B::{name}", r.get("orderings") or {}, r.get("values") or {},
                             base)
            if new:
                rows.extend(new)
                merged_.setdefault(_mech_label(name), []).append(f"B::{name}")
        items = [(f"{lab} ({len(c)})" if len(c) > 1 else lab, c) for lab, c in merged_.items()]
        if items:
            g = "Cooling B, mechanics only (ideal decoupling)"
            groups.append((g, items))
            GROUP_GATE[g] = gate
    d = S.TR / "robustness_mech_SDEC.json"
    if d.is_file():
        rs = json.loads(d.read_text())
        for t in ("A", "B"):
            gate, items = f"robustness.production_mech_{t}", []
            for name, per in (rs.get("variants") or {}).items():
                r = per.get(t)
                if not r:
                    continue
                new = _mech_rows(gate, f"SDEC_{t}::{name}", r.get("orderings") or {},
                                 r.get("values") or {}, (rs.get("base") or {}).get(t) or {})
                if new:
                    rows.extend(new)
                    items.append((_mech_label(name), [f"SDEC_{t}::{name}"]))
            if items:
                g = f"Implemented decoupling, cooling {t}, mechanics only"
                groups.append((g, items))
                GROUP_GATE[g] = gate
    return groups


def _joint_rows():
    """classB-style rows of the joint column from the joint-response screen: every variant's
    Z1/Z2 ordering of the joint response (x 1e-3 per cycle) against its group's baseline."""
    f = S.TR / "robustness_joint.json"
    if not f.is_file():
        return
    d = json.loads(f.read_text())
    where = {"S0_A": ("robustness.joint_reference", "{}"), "SDEC_new_A": (NEWER_GATE, "{}"),
             "S0_B": ("robustness.cooling_B_mech", "B::{}"),
             "SDEC_mech_A": ("robustness.production_mech_A", "SDEC_A::{}"),
             "SDEC_mech_B": ("robustness.production_mech_B", "SDEC_B::{}")}
    for g, (gate, fmt) in where.items():
        for name, r in sorted(((d.get("groups") or {}).get(g) or {}).items()):
            o = (r.get("orderings") or {}).get("eps:Z1/Z2")
            if not o:
                continue
            v, b = o["variant"], o["base"]
            rows.append({"gate": gate, "case": fmt.format(name), "observable": JOINT,
                         "alternate_verdict": o.get("verdict") or "pending",
                         "production_verdict": o.get("base_verdict") or "",
                         "outcome": "pending" if o.get("verdict") == "pending" else "judged",
                         "alternate_Z1": str(1e3 * v[0]), "alternate_Z2": str(1e3 * v[1]),
                         "nominal_Z1": str(1e3 * b[0]), "nominal_Z2": str(1e3 * b[1])})


_joint_rows()
LAYOUT += _mech_groups()

RANK = {"n/a": 0, "preserved": 1, "pending": 2, "withdrawn": 3, "reversed": 4}


def gap(case, obs):
    """Z2 - Z1 under the decision, or None."""
    rs = [r for r in rows if r["case"] == case and r["observable"] == obs]
    if not rs or rs[0]["outcome"] in ("n/a", ""):
        return None
    try:
        return float(rs[0]["alternate_Z2"]) - float(rs[0]["alternate_Z1"])
    except ValueError:
        return None


def _base_rows(newer):
    """the rows of the reference baseline (classical gates; newer False), or of the group gate
    `newer` (True: the production-state cooling-A gate)"""
    if newer is True:
        newer = NEWER_GATE
    own = set(GROUP_GATE.values())
    if not newer:
        return [r for r in rows if r["gate"] not in own]
    return [r for r in rows if r["gate"] == newer]


def prod_gap(obs, newer=False):
    r = next((r for r in _base_rows(newer) if r["observable"] == obs and r["nominal_Z1"]
              and r["nominal_Z1"] != "None"), None)
    return float(r["nominal_Z2"]) - float(r["nominal_Z1"]) if r else None


DEC = {"P_loss_package_internal_w": 1, "T_max_C": 1, "die_warpage_pv_um": 1, "du_c_um": 2,
       JOINT: 2}


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
    rs = [r for r in rows if r["case"] == case and r["observable"] == obs]
    if not rs:
        return ("n/a", None)
    r = rs[0]
    alt, prod = r["alternate_verdict"].strip(), r["production_verdict"].strip()
    if alt == "pending" or r["outcome"] == "pending":
        return ("pending", None)
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


def _prod(key, newer=False):
    """The baseline verdict under the unified rule, as classB formed it on the pair's own
    ladders (never typed in): the ideal-decoupling reference for the classical gates, the
    production state (implemented decoupling) for the newer cooling-A gate."""
    v = next((r["production_verdict"].strip() for r in _base_rows(newer)
              if r["observable"] == key and r.get("production_verdict")), "")
    if v.endswith("lower"):
        return v.split()[0]
    return "≈" if v == "unresolved" else "–"


PROD = [_prod(k) for k, _ in OBS]
PROD_NEW = [_prod(k, True) for k, _ in OBS]
PROD_GROUP = {g: [_prod(k, gate) for k, _ in OBS] for g, gate in GROUP_GATE.items()}
HEAD = ["Int. loss\n(W)", "Peak\ntemp. (K)", "Die warp.\n(µm)",
        "Joint resp.\n(10$^{-3}$/cyc.)"]

COLW_IN, ROWH_IN, LAB_IN = 0.45, 0.145, 1.64
n_body = (sum(len(g[1]) for g in LAYOUT) + len(LAYOUT)
          + sum(1 for g in LAYOUT if g[0] in GROUP_GATE))
HEAD_R, LEG_R = 2.4, 5.0                       # header and legend heights, in rows
W = S.COL_W
H = (n_body + 1 + HEAD_R + LEG_R) * ROWH_IN + 0.05
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])
xl = -LAB_IN / COLW_IN                          # label area in column units
xr = (W - LAB_IN) / COLW_IN
ax.set_xlim(xl, xr)
ax.set_ylim(n_body + 1 + 0.15, -(HEAD_R + LEG_R))
ax.axis("off")
FILL = {"preserved": "#f3f2ee", "withdrawn": "#cfcdc6", "pending": "#e4e2dc", "n/a": "white"}
GLYPH = {"preserved": "·", "withdrawn": "≈", "pending": "?", "n/a": "–"}
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
        txt = (f"{who} {val}" if st == "prod" else f"{val} ?" if st == "pending"
               else f"≈{val}" if st == "withdrawn" else val)
    # long ranges ("-0.29...-0.24") shrink so that they stay inside the cell
    n_ch = len(str(txt))
    fs = (6.5 if n_ch <= 9 else 5.6 if n_ch == 10 else 4.6) if (big or val) else 7.5
    ax.text(x + 0.5, y + 0.5 + (0.0 if (big or val) else 0.02), txt, ha="center",
            va="center", fontsize=fs, color=tc,
            fontweight="bold" if st == "reversed" else "normal")


# legend block (top)
ly = -(HEAD_R + LEG_R) + 0.55
items = [("prod", "Z1", "Z1 lower"), ("prod", "Z2", "Z2 lower"),
         ("preserved", None, "preserved"),
         ("withdrawn", None, "withdrawn ($|D+\\beta|\\leq U_{95}$)"),
         ("pending", None, "pending (own ladder)"), ("n/a", None, "not evaluated")]
pos = [(xl + 0.15, ly), (xl + 2.65, ly), (xl + 5.15, ly), (xl + 0.15, ly + 1.0),
       (xl + 0.15, ly + 2.0), (xl + 5.15, ly + 1.0)]
for (st, who, lab), (lx, lyy) in zip(items, pos):
    fc = S.ARCH[who] if who else FILL[st]
    ax.add_patch(Rectangle((lx, lyy), 0.62, 0.78, fc=fc, ec="none"))
    ax.text(lx + 0.31, lyy + 0.41, who if who else GLYPH[st], ha="center", va="center",
            fontsize=5.6 if who else 7.5, color="white" if who else S.INK2,
            fontweight="bold" if who else "normal")
    ax.text(lx + 0.8, lyy + 0.41, lab, ha="left", va="center", fontsize=6.5, color=S.INK2)
ax.text(xl + 0.15, ly + 3.75, "Numbers: gap Z2 − Z1 (min…max over merged variants);\n"
        "colored: the ordering reverses toward that integration.", ha="left", va="center",
        fontsize=6.5, color=S.INK2)

# header
for j, lab in enumerate(HEAD):
    ax.text(x0c + j + 0.5, -0.15, lab, ha="center", va="bottom", fontsize=6.5,
            color=S.INK, linespacing=1.0)

iy = 0
ax.text(x0c - 0.12, iy + 0.5, "Reference verdict (ideal decoupling)", ha="right",
        va="center", fontsize=6.6, color=S.INK, fontweight="bold")
for j, v in enumerate(PROD):
    cell(j, iy, "prod", v, val=gtxt([prod_gap(OBS[j][0])], OBS[j][0]))
iy += 1
for gname, items in LAYOUT:
    ax.plot([xl + 0.1, x0c + len(OBS)], [iy + 0.12, iy + 0.12], color=S.GRID, lw=0.6)
    ax.text(xl + 0.1, iy + 0.62, gname, ha="left", va="center", fontsize=6.7,
            color=S.INK, fontstyle="italic")
    iy += 1
    if gname in GROUP_GATE:             # this group's own baseline (its verdicts and gaps)
        gate = GROUP_GATE[gname]
        ax.text(x0c - 0.12, iy + 0.5, "Production verdict" if gname == NEWER_GROUP else
                "Baseline verdict", ha="right", va="center", fontsize=6.6, color=S.INK,
                fontweight="bold")
        for j, v in enumerate(PROD_GROUP[gname]):
            val = gtxt([prod_gap(OBS[j][0], gate)], OBS[j][0])
            if v == "–" and val is None:
                cell(j, iy, "n/a")
            else:
                cell(j, iy, "prod", v, val=val)
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
