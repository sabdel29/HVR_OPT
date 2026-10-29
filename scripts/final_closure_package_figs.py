"""Z1 / Z2 package illustrations, drawn ONLY from the measured architecture spec.

    python scripts/final_closure_package_figs.py

reads   research/final_closure/architecture_geometry.json   (refused unless its sha256 verifies)
writes  presentation/prelim_hvr/figs/z1_package_cross_section.svg
        presentation/prelim_hvr/figs/z2_package_cross_section.svg
        presentation/prelim_hvr/figs/z1_z2_package_comparison.svg
        presentation/prelim_hvr/figs/z1_z2_exploded.png      (isometric SVG -> rsvg-convert)
        presentation/prelim_hvr/figs/regulator_cell_zoom.svg

GEOMETRY RULE. Every layer height, z coordinate and lateral width is read from the spec,
which was itself measured on the solver mesh. The constants in this file are pixels, font
sizes and colours. tests/final_closure/test_architecture_figures.py rejects any standalone
number in this source equal to a spec thickness or z value, so a typed-in height cannot
creep back, and checks every drawn band against the spec and against the mapping below.

THE Z MAPPING -- one function for Z1 and Z2, used by every cross-section figure:
  * knots = every layer boundary of BOTH stacks (their union), so a given z lands on the
    same pixel row in Z1 and in Z2;
  * every knot interval dz is drawn k * max(dz, Z_FLOOR_UM) pixels tall, k = PX_PER_MM_Z/1e3:
    linear, except that an interval thinner than Z_FLOOR_UM is drawn as if it were
    Z_FLOOR_UM thick, so the thin RDL, pad and TIM layers stay visible. Each such layer is
    labelled with its TRUE thickness;
  * horizontal scale px_per_mm_x per figure; the vertical exaggeration
    PX_PER_MM_Z / px_per_mm_x is written on the figure.

Things the model does NOT contain are drawn but never given a data-layer: the 48 V package
RDL sheet (a 2-D resistor network over the substrate underside, not an FE layer) and the
cold plate (the thermal model's top convective-film boundary, not meshed).
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import figstyle as F                                                # noqa: E402

SPEC_PATH = R / "research" / "final_closure" / "architecture_geometry.json"
COUPLING_PATH = R / "research" / "final_closure" / "coupling_checks.json"
STACKS_MD = R / "research" / "Z1_Z2_PHYSICALLY_SPECIFIED_STACKS.md"
FIGS = R / "presentation" / "prelim_hvr" / "figs"
OUT = {"Z1": FIGS / "z1_package_cross_section.svg",
       "Z2": FIGS / "z2_package_cross_section.svg",
       "pair": FIGS / "z1_z2_package_comparison.svg",
       "exploded": FIGS / "z1_z2_exploded.png",
       "cell": FIGS / "regulator_cell_zoom.svg",
       "power_path": FIGS / "z1_z2_power_path_final.svg",
       "power_path_48": FIGS / "z1_z2_power_path_48v.svg",
       "power_path_1v": FIGS / "z1_z2_power_path_1v.svg",
       "attach": FIGS / "z2_vr_attach_detail.svg"}
STAMP = "ILLUSTRATIVE — NOT TO SCALE"

# ------------------------------------------------------------------ mapping (pixels only)
PX_PER_MM_Z = 90.0          # vertical pixels per mm of true z, in every cross-section
Z_FLOOR_UM = 80.0           # thinner knot intervals are drawn as if this thick
PX_PER_MM_X_SINGLE = 30.0   # single-architecture figures
PX_PER_MM_X_PAIR = 15.0     # the side-by-side figure
COLD_PLATE_PX = 28.0        # the cold plate is a boundary condition: schematic height
SHEET_PX = 3.0              # the package RDL sheet is 2-D in the model: schematic height
FS = 14                     # smallest text anywhere
LINE = 17                   # label line pitch

KEY_MESSAGE = {
    "Z1": ("Z1 brings 48 V through the BGA and the substrate, converts inside the package, "
           "then a short 1 V path to the die"),
    "Z2": ("Z2 feeds 48 V straight into the backside regulator through the PCB opening, "
           "converts below the substrate, and sends only 1 V up through the attach and TSVs"),
}
FEED_TEXT = "ILLUSTRATIVE DIRECT 48-V FEED — exact connector geometry not specified"
CLEARANCE_TEXT = "1.0 mm sidewall clearance — void"
PILLAR = "#b87333"          # Cu pillar of the VR attach (schematic)
BGA_SIGNAL = "#d0d7de"      # a BGA ball that carries no HVR input current
SHEET_TEXT = ("48 V package RDL sheet — modelled as a 2-D network sheet; "
              "not a separate FE layer")


# =================================================================== spec access
def load_spec(path=SPEC_PATH) -> dict:
    """The spec, refused unless its own sha256 (computed as its generator does) verifies."""
    raw = json.loads(Path(path).read_text())
    body = {k: v for k, v in raw.items() if k != "sha256"}
    sha = hashlib.sha256(json.dumps(body, indent=1, default=float).encode()).hexdigest()
    if sha != raw.get("sha256"):
        raise ValueError(f"{path}: sha256 does not verify ({sha} != {raw.get('sha256')}); "
                         "regenerate it with final_closure_architecture_spec.py")
    for a in raw["architectures"].values():
        zs = [z for L in a["layers"] for z in (L["z0_um"], L["z1_um"])]
        if min(zs) != a["z_min_um"] or max(zs) != a["z_max_um"]:
            raise ValueError(f"{a['arch']}: layer extents disagree with z_min/z_max")
        for L in a["layers"]:
            if abs(L["z1_um"] - L["z0_um"] - L["t_um"]) > 1e-6:
                raise ValueError(f"{a['arch']}/{L['name']}: t_um != z1 - z0")
    return raw


def tiers(a) -> list:
    """Converter tiers: the layers whose out-of-cell volume is the underfill medium (the
    VR attach is not a converter tier; it is drawn on its own)."""
    return sorted((L for L in a["layers"] if "underfill_homog" in L["materials"]
                   and "attach" not in L["roles"]), key=lambda L: L["z0_um"])


def attach_layer(a):
    hit = [L for L in a["layers"] if "attach" in L["roles"]]
    return hit[0] if hit else None


def direct_fed(a) -> bool:
    return a.get("hv_feed") == "DIRECT_FEED"


def by_role(a, role) -> dict:
    hit = [L for L in a["layers"] if role in L["roles"]]
    if len(hit) != 1:
        raise ValueError(f"{a['arch']}: expected one layer with role {role!r}, got {len(hit)}")
    return hit[0]


def named(a, name) -> dict:
    return next(L for L in a["layers"] if L["name"] == name)


def substrate(a) -> list:
    return sorted((L for L in a["layers"] if "tsv_tile" in L["materials"]),
                  key=lambda L: L["z0_um"])


def is_embedded(a) -> bool:
    """True when the converter sits ABOVE the substrate (Z1), False when it hangs below."""
    t, s = tiers(a), substrate(a)
    if t[0]["z0_um"] >= s[-1]["z1_um"]:
        return True
    if t[-1]["z1_um"] <= s[0]["z0_um"]:
        return False
    raise ValueError(f"{a['arch']}: converter neither above nor below the substrate")


def kind(L) -> str:
    """Drawing class from the MESH materials and the ledger roles, never from the name."""
    m, r = L["materials"], set(L["roles"])
    if "board_fr4" in m:
        return "pcb"
    if "bga" in r:
        return "bga"
    if "tsv_tile" in m:
        return "substrate"
    if "attach" in r:
        return "attach"
    if "underfill_homog" in m:
        for role, k in (("hs", "gan"), ("ls", "gan"), ("caps", "caps"), ("ind", "inductor"),
                        ("rdl", "rdl")):
            if role in r:
                return "tier_" + k
        raise ValueError(f"converter tier {L['name']} has no device role")
    if "pads" in r:
        return "interface"
    if "die" in r:
        return "die"
    if "tim" in m:
        return "tim"
    if "rdl_tier" in m:
        return "top_rdl"
    raise ValueError(f"cannot classify layer {L['name']}")


TIER_FILL = {"tier_gan": F.MAT["gan"], "tier_caps": F.MAT["caps"],
             "tier_inductor": F.MAT["inductor"], "tier_rdl": F.MAT["rdl"]}
BAND_FILL = {"pcb": F.MAT["pcb"], "bga": "#f3f4f6", "substrate": F.MAT["silicon"],
             "interface": F.MAT["fill"], "die": F.MAT["die"], "tim": F.MAT["tim"],
             "top_rdl": F.MAT["rdl"], "attach": F.MAT["fill"]}

#: plain words for the layer names; the thickness is always appended FROM THE SPEC
PLAIN = {"board": "PCB", "sub_lower": "Si power substrate",
         "tile_band": "substrate top band (Si + TSV)",
         "bottom_substrate_rdl": "bottom-substrate RDL (high-side landing)",
         "interlayer_rdl": "interlayer RDL", "output_rdl": "output RDL (1 V + ground)",
         "land_side_attach_rdl": "1 V output / attach RDL (top of the regulator)",
         "attach_vr_substrate": "Cu-pillar attach: regulator → substrate (1 V only)",
         "flying_caps": "flying capacitors", "inductor_plus_cout": "inductors + output caps",
         "z2_top_rdl": "top RDL (1 V + ground)",
         "interface": "microbumps / Cu pads + underfill (die side)",
         "die": "compute die", "tim": "TIM (no lid in the model)"}


def plain_name(a, L) -> str:
    nm = re.sub(r"^(z1conv|conv)_\d+_", "", L["name"])
    m = re.match(r"gan_(hs|ls)_(\w+)$", nm)
    if m:
        return f"{'high' if m.group(1) == 'hs' else 'low'}-side GaN ({m.group(2)})"
    if nm == "bga":
        if direct_fed(a):
            return "BGA balls, peripheral (signals, aux, mechanical — NOT the 48 V feed)"
        where = ", peripheral only" if a["cutout_mm"] else ""
        return f"BGA balls{where} (48 V supply + return)"
    if nm == "die":
        return f"compute die ({a['die_mm'][0]:g} mm wide)"
    return PLAIN.get(nm) or L["role_text"] or nm


def fmt_um(v) -> str:
    return f"{v:g} µm"


def bga_row(a) -> list:
    """x (mm) of the legal BGA sites on the y = 0 row.

    Centred lattice at the spec pitch over the substrate, minus the opening. The 2-D count
    of the same rule must equal the spec's measured sites_legal, else nothing is drawn.
    """
    p, half_w, c = a["bga"]["pitch_mm"], a["substrate_mm"][0] / 2, a["cutout_mm"]
    n = int(math.floor(half_w / p + 1e-9))
    xs = [round(k * p, 9) for k in range(-n, n + 1)]
    inside = (lambda v: c is not None and abs(v) < c / 2)
    count = sum(1 for x in xs for y in xs if not (inside(x) and inside(y)))
    if count != a["bga"]["sites_legal"]:
        raise ValueError(f"{a['arch']}: lattice rule gives {count} sites, the spec measured "
                         f"{a['bga']['sites_legal']}")
    return [x for x in xs if not (inside(x) and inside(0.0))]


def tsv_grid(a) -> int:
    """Vias per row of one cell's square TSV lattice, checked to fit the cell."""
    t = a["tsv"]
    n = int(round(math.sqrt(t["n_per_cell"])))
    if n * n != t["n_per_cell"]:
        raise ValueError("TSV count per cell is not a square lattice")
    if ((n - 1) * t["pitch_um"] + t["d_um"]) / 1e3 > a["cells"]["side_mm"]:
        raise ValueError("TSV lattice does not fit inside the cell")
    return n


def lateral(a, L) -> list:
    """In-plane pieces (x0, x1) in mm of a layer on the y = 0 section.

    'inside_cutout' layers fill the opening. A full-footprint layer whose z range overlaps
    an inside-cutout layer cannot occupy the opening too (two media cannot share a volume),
    so it is drawn as the annulus outside it -- the PCB frame and the peripheral BGA.
    """
    half = (a["substrate_mm"][0] if L["footprint"] == "substrate" else a["die_mm"][0]) / 2
    c = a["cutout_mm"]
    if L["region"] == "inside_cutout":
        ooc = a.get("out_of_cell") or {}
        if ooc.get("ring") == "VOID" and ooc.get("extent_x_mm"):
            # the fill stops at the measured cell-grid bounding box; the ring is void
            return [tuple(ooc["extent_x_mm"])]
        return [(-c / 2, c / 2)]
    if c and any(I["region"] == "inside_cutout" and I["z0_um"] < L["z1_um"]
                 and L["z0_um"] < I["z1_um"] for I in a["layers"]):
        return [(-half, -c / 2), (c / 2, half)]
    return [(-half, half)]


def key_message(a) -> str:
    """The plain-language line, refused if the spec geometry no longer says it."""
    emb, cut = is_embedded(a), a["cutout_mm"]
    z1_like, z2_like = emb and cut is None, (not emb) and bool(cut)
    if (a["arch"] == "Z1") != z1_like or (a["arch"] == "Z2") != z2_like:
        raise ValueError(f"{a['arch']}: key message contradicts the spec geometry")
    return KEY_MESSAGE[a["arch"]]


def coupling_fact(key):
    try:
        return json.loads(COUPLING_PATH.read_text()).get(key)
    except (OSError, ValueError):
        return None


# =================================================================== the z mapping
class ZMap:
    """THE z -> pixel mapping. One instance serves Z1 and Z2 in every cross-section."""

    def __init__(self, spec, px_per_mm_z=PX_PER_MM_Z, floor_um=Z_FLOOR_UM):
        self.knots = sorted({z for a in spec["architectures"].values()
                             for L in a["layers"] for z in (L["z0_um"], L["z1_um"])})
        self.k = px_per_mm_z / 1e3
        self.floor = floor_um
        self.acc = [0.0]
        for z0, z1 in zip(self.knots, self.knots[1:]):
            self.acc.append(self.acc[-1] + self.k * max(z1 - z0, floor_um))

    def h(self, z):
        """Pixels above the lowest knot (the PCB backside)."""
        kn = self.knots
        if z <= kn[0]:
            return (z - kn[0]) * self.k
        if z >= kn[-1]:
            return self.acc[-1] + (z - kn[-1]) * self.k
        i = bisect.bisect_right(kn, z) - 1
        return self.acc[i] + (self.acc[i + 1] - self.acc[i]) * (z - kn[i]) / (kn[i + 1] - kn[i])

    @property
    def total(self):
        return self.acc[-1]


# =================================================================== small SVG helpers
def tw(s, size, bold=False):
    """Approximate advance width, Helvetica-class metrics (what rsvg resolves here)."""
    em = 0.0
    for ch in str(s):
        if ch == " ":
            em += 0.278
        elif ch in "ijl.,:;|!'`":
            em += 0.24
        elif ch in "frtI()[]-/":
            em += 0.36
        elif ch in "mwMW@%—":
            em += 0.86
        elif ch.isupper():
            em += 0.68
        elif ch.isdigit():
            em += 0.556
        else:
            em += 0.54
    return em * size * (1.07 if bold else 1.0)


UNITS = {"V", "mm", "µm", "kA", "A", "W", "px/mm"}


def wrap(s, max_w, size, bold=False) -> list:
    """Greedy word wrap that never separates a number from its unit ("1 V", "737 µm")."""
    words = []
    for w in str(s).split(" "):
        if words and w.rstrip(",;.)") in UNITS and re.fullmatch(r"[\d.]+", words[-1]):
            words[-1] += " " + w
        else:
            words.append(w)
    out, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if not cur or tw(t, size, bold) <= max_w:
            cur = t
        else:
            out.append(cur)
            cur = w
    return out + [cur]


def num(v):
    return f"{v:.2f}"


def attrs(**kw) -> str:
    return " ".join(f'{k.replace("_", "-")}="{F.esc(v)}"' for k, v in kw.items())


def poly(points, stroke, sw, dash=None, fill="none", extra=""):
    pts = " ".join(f"{num(x)},{num(y)}" for x, y in points)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<polyline points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
            f'{d} stroke-linejoin="round" {extra}/>\n')


#: arrowheads with orient="auto" (SVG 1.1). figstyle's markers use the SVG 2 value
#: "auto-start-reverse", which librsvg 2.42 (this host's rsvg-convert) ignores, drawing every
#: head pointing right. Only marker-end is used here, so "auto" is exact everywhere.
ARROW_KINDS = {"48": (F.I48, "pk48"), "1v": (F.I1V, "pk1v"), "ret": (F.IRET, "pkret")}


def marker_defs() -> str:
    return "".join(f'<marker id="{mk}" viewBox="0 0 12 12" refX="10.2" refY="6" '
                   f'markerWidth="7" markerHeight="7" orient="auto">'
                   f'<path d="M0,0 L12,6 L0,12 z" fill="{col}"/></marker>'
                   for col, mk in ARROW_KINDS.values())


def arrow(points, kind_, sw=2.6, extra=""):
    col, mk = ARROW_KINDS[kind_]
    dash = F.DASH_RET if kind_ == "ret" else None
    return poly(points, col, sw, dash=dash, extra=f'marker-end="url(#{mk})" {extra}')


def harrow(points, kind_, sw=2.6, extra=""):
    """An arrow on a white halo, so it reads over copper and silicon alike."""
    return poly(points, "#ffffff", sw + 3.4, extra='stroke-linecap="round" opacity="0.92"') \
        + arrow(points, kind_, sw, extra)


def tag(x, y, s, col, anchor="middle", dashed=False, size=FS):
    """A boxed arrow label: white box, coloured border and bold coloured text."""
    w, h = tw(s, size, True) + 14, size + 9
    x0 = {"middle": x - w / 2, "start": x, "end": x - w}[anchor]
    dash = f'stroke-dasharray="{F.DASH_RET}"' if dashed else ""
    return (F.rect(x0, y - h / 2, w, h, "#ffffff", col, 1.5, f'rx="4" {dash}')
            + F.text(x0 + w / 2, y + size * 0.36, s, size, "middle", "bold", col, halo=False))


def label_lines(name, thick, max_w, size=FS) -> list:
    """[(text, bold_tail)] lines; the true thickness rides in bold on the last line."""
    tail = f"  {thick}" if thick else ""
    if tw(name + tail, size) <= max_w:
        return [(name, thick)]
    lines = [(t, None) for t in wrap(name, max_w, size)]
    if thick and tw(lines[-1][0] + tail, size) <= max_w:
        lines[-1] = (lines[-1][0], thick)
    elif thick:
        lines.append(("", thick))
    return lines


def text_line(x, y, body, bold_tail, anchor, size=FS, fill=F.INK):
    # a dx gap, never whitespace: librsvg 2.42 drops any whitespace (even no-break spaces)
    # beside a tspan, which would glue the name to its thickness
    tail = (f'<tspan dx="{size * 0.5:g}" font-weight="bold">{F.esc(bold_tail)}</tspan>'
            if bold_tail else "")
    return (f'<text x="{num(x)}" y="{num(y)}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{fill}">{F.esc(body)}{tail}</text>\n')


def spread(want, heights, lo, hi) -> list:
    """Order-preserving, least-displacement placement of label blocks inside [lo, hi].

    want: desired centre of each block; heights: block heights. Returns the centres."""
    order = sorted(range(len(want)), key=lambda i: want[i])
    blocks = []

    def top(b):
        return min(max(b["S"] / b["n"], lo), hi - b["H"])

    for i in order:
        blocks.append({"m": [i], "H": heights[i], "S": want[i] - heights[i] / 2, "n": 1})
        while len(blocks) > 1 and top(blocks[-2]) + blocks[-2]["H"] > top(blocks[-1]):
            a, b = blocks[-2], blocks[-1]
            blocks[-2:] = [{"m": a["m"] + b["m"], "H": a["H"] + b["H"],
                            "S": a["S"] + b["S"] - b["n"] * a["H"], "n": a["n"] + b["n"]}]
    out = [0.0] * len(want)
    for b in blocks:
        t = top(b)
        for i in b["m"]:
            out[i] = t + heights[i] / 2
            t += heights[i]
    return out


def leaders(reqs, side, x_edge, x_text, max_w, lo, hi, size=FS) -> str:
    """Leader lines from features to a label column on one side, never crossing."""
    for q in reqs:
        q["lines"] = label_lines(q["name"], q.get("thick"), max_w, size)
    heights = [len(q["lines"]) * LINE + 5 for q in reqs]
    ys = spread([q["dot"][1] for q in reqs], heights, lo, hi)
    out, sgn = [], 1 if side == "right" else -1
    anchor = "start" if side == "right" else "end"
    for q, y in zip(reqs, ys):
        x0, y0 = q["dot"]
        pts = [(x0, y0), (x_edge, y0), (x_text - sgn * 5, y)]
        out.append(poly(pts, "#ffffff", 3.2, extra='opacity="0.85"'))
        out.append(poly(pts, F.MUTED, 1.1))
        out.append(f'<circle cx="{num(x0)}" cy="{num(y0)}" r="2.8" fill="{F.INK}" '
                   f'stroke="#ffffff" stroke-width="1"/>\n')
        n = len(q["lines"])
        for j, (body, tail) in enumerate(q["lines"]):
            yy = y + (j - (n - 1) / 2) * LINE + size * 0.36
            out.append(text_line(x_text, yy, body, tail, anchor, size))
    return "".join(out)


def legend_block(x, y, items, cols, col_w, size=FS) -> str:
    """items: (kind, colour, label); kind in fill | air | sheet | 48 | 1v | ret."""
    out, per, box = [], -(-len(items) // cols), 15
    for i, (k, c, lab) in enumerate(items):
        cx, cy = x + (i // per) * col_w, y + (i % per) * (box + 7)
        if k == "fill":
            out.append(F.rect(cx, cy, box, box, c, F.INK, 0.8))
        elif k == "air":
            out.append(F.rect(cx, cy, box, box, "#ffffff", F.MUTED, 1.2,
                              'stroke-dasharray="4,3"'))
        elif k == "sheet":
            out.append(F.rect(cx - 2, cy + box / 2 - SHEET_PX / 2, box + 4, SHEET_PX, F.I48,
                              F.INK, 0.5))
        elif k == "feed":
            out.append(F.rect(cx - 2, cy + 2, box + 4, box - 4, "#fff4e5", F.I48, 1.4, 'rx="3"'))
        else:
            out.append(arrow([(cx - 2, cy + box / 2), (cx + box + 9, cy + box / 2)], k, 2.3))
        dx = box + (17 if k in ("48", "1v", "ret") else 8)
        out.append(F.text(cx + dx, cy + box * 0.82, lab, size, halo=False))
    return "".join(out)


def legend_items(archs) -> list:
    has_air = any(a["cutout_mm"] for a in archs)
    items = [("fill", F.MAT["pcb"], "PCB laminate"),
             ("fill", F.MAT["solder"], "solder: BGA balls"),
             ("fill", F.MAT["silicon"], "silicon"),
             ("fill", F.MAT["tsv"], "Cu TSV field (vias schematic)"),
             ("fill", F.MAT["rdl"], "Cu RDL tier"),
             ("fill", F.MAT["gan"], "GaN-on-Si device tier"),
             ("fill", F.MAT["caps"], "flying capacitors"),
             ("fill", F.MAT["inductor"], "inductors + output caps"),
             ("fill", F.MAT["fill"], "underfill (outside the cells)"),
             ("fill", F.MAT["die"], "compute die"),
             ("fill", F.MAT["tim"], "TIM"),
             ("fill", F.MAT["coldplate"], "cold plate (schematic)")]
    if has_air:
        items.append(("air", None, "air / void (PCB opening, clearance)"))
    if any(direct_fed(a) for a in archs):
        items += [("fill", PILLAR, "Cu-pillar VR attach (1 V only)"),
                  ("fill", BGA_SIGNAL, "BGA ball: signals / mechanical only"),
                  ("feed", None, "direct 48 V feed (illustrative)")]
    if any(not direct_fed(a) for a in archs):
        items.append(("sheet", None, "48 V package sheet (2-D, not FE)"))
    items += [("48", None, "48 V in"), ("1v", None, "1 V out"),
              ("ret", None, "return (dashed)")]
    return items


def patterns() -> str:
    """Schematic textures: TSV stripes, microbumps, cold-plate channels."""
    si, cu = F.MAT["silicon"], F.MAT["tsv"]
    return ("<defs>" + marker_defs() +
            f'<pattern id="tsvp" width="4" height="8" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="8" fill="{si}"/><rect x="1" width="1.8" height="8" '
            f'fill="{cu}"/></pattern>'
            f'<pattern id="pillar" width="5" height="8" patternUnits="userSpaceOnUse">'
            f'<rect width="5" height="8" fill="{F.MAT["fill"]}"/>'
            f'<rect x="1.4" y="0" width="2.2" height="8" fill="{PILLAR}"/></pattern>'
            f'<pattern id="bump" width="6" height="8" patternUnits="userSpaceOnUse">'
            f'<rect width="6" height="8" fill="{F.MAT["fill"]}"/>'
            f'<rect x="1.5" y="0" width="3" height="8" rx="1.2" fill="{F.MAT["solder"]}"/>'
            "</pattern>"
            f'<pattern id="chan" width="14" height="{COLD_PLATE_PX}" '
            'patternUnits="userSpaceOnUse">'
            f'<rect width="14" height="{COLD_PLATE_PX}" fill="{F.MAT["coldplate"]}"/>'
            f'<rect x="4" y="7" width="6" height="{COLD_PLATE_PX - 14}" rx="2" '
            'fill="#ffffff" opacity="0.85"/></pattern>'
            "</defs>\n")


def metadata_block(obj) -> str:
    body = json.dumps(obj, indent=1, ensure_ascii=False)
    return f'<metadata id="package-figure-spec"><![CDATA[\n{body}\n]]></metadata>\n'


def stamp(x, y, s, size=FS + 1, col=F.OPEN) -> str:
    """figstyle.stamp, but sized from the text so bold capitals never overrun the box."""
    w = tw(s, size, True) + 18
    return (F.rect(x, y, w, size + 12, "#ffffff", col, 1.6)
            + F.text(x + 9, y + size + 2, s, size, weight="bold", fill=col, halo=False))


# =================================================================== one section panel
class Section:
    """One architecture, sectioned at y = 0, drawn with the shared ZMap."""

    def __init__(self, a, zm, x_left, y_datum, s_x, label_side="right"):
        self.a, self.zm, self.s = a, zm, s_x
        self.x_left, self.y_datum, self.side = x_left, y_datum, label_side
        self.W, self.D, self.C = a["substrate_mm"][0], a["die_mm"][0], a["cutout_mm"]
        self.cells = sorted(a["cells"]["centres_x_mm"])
        self.side_mm = a["cells"]["side_mm"]
        self.sites = bga_row(a)
        self.embedded = is_embedded(a)
        tsv_grid(a)

    # ---- coordinates
    def X(self, x_mm):
        return self.x_left + (x_mm + self.W / 2) * self.s

    def Y(self, z_um):
        return self.y_datum - self.zm.h(z_um)

    @property
    def x_right(self):
        return self.X(self.W / 2)

    def mirror(self):
        """+1 when the arrows live on the +x half, -1 for the -x half (away from labels)."""
        return -1 if self.side == "right" else 1

    # ---- geometry layers
    def bands(self) -> str:
        out = []
        for L in sorted(self.a["layers"], key=lambda L: L["z0_um"]):
            k = kind(L)
            y1, y0 = self.Y(L["z1_um"]), self.Y(L["z0_um"])
            fill = F.MAT["fill"] if k.startswith("tier_") else BAND_FILL[k]
            if k == "interface":
                fill = "url(#bump)"
            for i, (x0, x1) in enumerate(lateral(self.a, L)):
                meta = attrs(data_layer=L["name"], data_z0_um=repr(float(L["z0_um"])),
                             data_z1_um=repr(float(L["z1_um"])),
                             data_t_um=repr(float(L["t_um"])), data_x0_mm=repr(x0),
                             data_x1_mm=repr(x1), data_kind=k, data_piece=i)
                out.append(F.rect(self.X(x0), y1, (x1 - x0) * self.s, y0 - y1, fill, F.INK,
                                  0.6, meta))
            if k.startswith("tier_"):
                for cx in self.cells:
                    x0 = cx - self.side_mm / 2
                    out.append(F.rect(self.X(x0), y1, self.side_mm * self.s, y0 - y1,
                                      TIER_FILL[k], F.INK, 0.6,
                                      attrs(data_cell_of=L["name"], data_cx_mm=repr(cx),
                                            data_side_mm=repr(self.side_mm))))
            if k == "substrate":
                for cx in self.cells:
                    x0 = cx - self.side_mm / 2
                    out.append(F.rect(self.X(x0), y1, self.side_mm * self.s, y0 - y1,
                                      "url(#tsvp)", F.INK, 0.5,
                                      attrs(data_tsv_field_of=L["name"], data_cx_mm=repr(cx))))
            if k == "attach":
                for cx in self.cells:
                    x0 = cx - self.side_mm / 2
                    out.append(F.rect(self.X(x0), y1, self.side_mm * self.s, y0 - y1,
                                      "url(#pillar)", F.INK, 0.5,
                                      attrs(data_vr_attach_of=L["name"], data_cx_mm=repr(cx))))
        return "".join(out)

    def clearance(self) -> str:
        """The void ring between the cell-grid bounding box and the PCB sidewall."""
        ooc = self.a.get("out_of_cell") or {}
        if not (self.C and ooc.get("ring") == "VOID" and ooc.get("extent_x_mm")):
            return ""
        t = tiers(self.a)
        att = attach_layer(self.a)
        z0, z1 = t[0]["z0_um"], (att or t[-1])["z1_um"]
        y1, y0 = self.Y(z1), self.Y(z0)
        out = []
        for xa, xb in ((-self.C / 2, ooc["extent_x_mm"][0]), (ooc["extent_x_mm"][1], self.C / 2)):
            out.append(F.rect(self.X(xa), y1, (xb - xa) * self.s, y0 - y1, "#ffffff", F.MUTED,
                              1.0, 'stroke-dasharray="3,2" ' + attrs(
                                  data_feature="sidewall-clearance-void",
                                  data_x0_mm=repr(xa), data_x1_mm=repr(xb))))
        return "".join(out)

    def balls(self) -> str:
        L = by_role(self.a, "bga")
        y1, y0 = self.Y(L["z1_um"]), self.Y(L["z0_um"])
        rx = self.a["bga"]["pitch_mm"] / 4 * self.s       # outline schematic: half the pitch
        out = []
        # a direct-fed Z2's balls carry no HVR input current: drawn in the signal colour
        col = BGA_SIGNAL if direct_fed(self.a) else F.MAT["solder"]
        role = "signal-mechanical" if direct_fed(self.a) else "48v-power-and-signal"
        for x in self.sites:
            out.append(f'<ellipse cx="{num(self.X(x))}" cy="{num((y0 + y1) / 2)}" '
                       f'rx="{num(rx)}" ry="{num((y0 - y1) / 2 - 0.6)}" '
                       f'fill="{col}" stroke="{F.INK}" stroke-width="0.6" '
                       f'{attrs(data_bga_x_mm=repr(x), data_bga_role=role)}/>\n')
        return "".join(out)

    def air(self) -> str:
        """The PCB opening below the hanging converter: empty air in the model."""
        if not self.C:
            return ""
        z_bot = min(L["z0_um"] for L in tiers(self.a))
        z_pcb = self.a["z_min_um"]
        x0, y_top, y_bot = self.X(-self.C / 2), self.Y(z_bot), self.Y(z_pcb)
        w = self.C * self.s
        out = [F.rect(x0, y_top, w, y_bot - y_top, F.MAT["air"], F.MUTED, 1.3,
                      'stroke-dasharray="6,4" ' + attrs(data_feature="pcb-opening-air",
                                                       data_cutout_mm=repr(self.C)))]
        gap = z_bot - z_pcb
        adiabatic = (coupling_fact("z2_cutout_underside") or {}).get("adiabatic")
        mid = (y_top + y_bot) / 2
        cx = self.X(0.0)
        max_w = w - 24
        line1 = f"PCB opening {self.C:g} mm — air"
        line2 = (f"{fmt_um(gap)} clear of the PCB backside"
                 + ("; converter underside adiabatic in the model" if adiabatic else ""))
        lines = [line1] + wrap(line2, max_w, FS)
        if direct_fed(self.a):
            # the feed sits under the second-outermost cell on the arrow side: centre the
            # text in the free span beyond it, in three short lines that fit the gap
            m = self.mirror()
            cs = sorted(self.cells, key=lambda x: -m * x)
            xa = cs[1] - m * self.side_mm
            xb = -m * self.C / 2
            cx = self.X((xa + xb) / 2)
            lines = [line1, f"{fmt_um(gap)} clear of the PCB backside"]
            if adiabatic:
                lines.append("underside adiabatic in the model")
        for j, s in enumerate(lines):
            out.append(F.text(cx, mid + (j - (len(lines) - 1) / 2) * LINE + FS * 0.36, s, FS,
                              "middle", "bold" if j == 0 else "normal", F.MUTED, halo=False))
        return "".join(out)

    def sheet(self) -> str:
        if direct_fed(self.a):                 # no package 48 V network in a direct-fed Z2
            return ""
        z = substrate(self.a)[0]["z0_um"]
        y = self.Y(z)
        return F.rect(self.X(-self.W / 2), y - SHEET_PX / 2, self.W * self.s, SHEET_PX, F.I48,
                      F.INK, 0.5, attrs(data_feature="pkg-48v-rdl-sheet", data_fe_layer="false",
                                        data_z_um=repr(float(z))))

    def cold_plate(self) -> str:
        tim = named(self.a, "tim")
        y = self.Y(tim["z1_um"])
        return F.rect(self.X(-self.D / 2), y - COLD_PLATE_PX, self.D * self.s, COLD_PLATE_PX,
                      "url(#chan)", F.INK, 0.8,
                      attrs(data_feature="cold-plate", data_schematic="true",
                            data_fe_layer="false"))

    # ---- current paths
    def currents(self) -> tuple:
        """(arrows svg, tags svg). Paths are schematic; their topology is the spec's."""
        a, m = self.a, self.mirror()
        side, p = self.side_mm, a["bga"]["pitch_mm"]
        cs = sorted(self.cells, key=lambda x: -m * x)          # outermost cell first
        mid = (lambda L: (L["z0_um"] + L["z1_um"]) / 2)
        z_hs, z_ind, z_die = mid(by_role(a, "hs")), mid(by_role(a, "ind")), mid(by_role(a, "die"))
        z_sheet, z_pcb = substrate(a)[0]["z0_um"], a["z_min_um"]
        y_sheet, y_pcb = self.Y(z_sheet), self.Y(z_pcb)
        off = SHEET_PX + 3.0
        near = (lambda target: min(self.sites, key=lambda s: abs(s - target)))
        arrows, tags = [], []
        if self.embedded:
            c = cs[1]
            xb_s, xb_r = near(c + m * (side + p) / 2), near(c - m * (side + p) / 2)
            xs_, xr_ = c + m * side / 4, c - m * side / 4
            sup = [(xb_s, y_pcb), (xb_s, y_sheet), (xs_, y_sheet), (xs_, self.Y(z_hs))]
            ret = [(xr_, self.Y(z_hs)), (xr_, y_sheet + off), (xb_r, y_sheet + off),
                   (xb_r, y_pcb)]
        elif direct_fed(a):
            # the DIRECT FEED: a dedicated connection reaches the regulator's 48 V input
            # terminals from the opening side; no BGA ball or package sheet carries it
            c = cs[1]
            xs_, xr_ = c + m * side / 4, c - m * side / 4
            xb_s, xb_r = xs_, xr_
            sup = [(xs_, y_pcb + 4), (xs_, self.Y(z_hs))]
            ret = [(xr_, self.Y(z_hs)), (xr_, y_pcb + 4)]
            z_bot = min(L["z0_um"] for L in tiers(a))
            yb = self.Y(z_bot)
            cw, chh = 1.6 * side * self.s, 13.0
            arrows.append(F.rect(self.X(c) - cw / 2, yb + 3, cw, chh, "#fff4e5", F.I48, 1.4,
                                 'rx="3" ' + attrs(data_feature="direct-48v-feed",
                                                   data_illustrative="true")))
        else:
            outer = sorted((s for s in self.sites if m * s > 0), key=lambda s: -m * s)
            xb_s, xb_r = outer[1], outer[2]
            xs_, xr_ = cs[1] + m * side / 4, cs[0] - m * side / 4
            sup = [(xb_s, y_pcb), (xb_s, y_sheet), (xs_, y_sheet), (xs_, self.Y(z_hs))]
            ret = [(xr_, self.Y(z_hs)), (xr_, y_sheet + off), (xb_r, y_sheet + off),
                   (xb_r, y_pcb)]
        px = (lambda pts: [(self.X(x), y) for x, y in pts])
        arrows.append(harrow(px(sup), "48", 2.6, 'data-current="48v-in"'))
        arrows.append(harrow(px(ret), "ret", 2.2, 'data-current="48v-return"'))
        # 1 V loop at every cell: out on the cell's outer side, its return on the inner side
        d1 = side / 5
        for c in self.cells:
            xo, xr = self.X(c + m * d1), self.X(c - m * d1)
            arrows.append(harrow([(xo, self.Y(z_ind)), (xo, self.Y(z_die))], "1v", 2.0,
                                 'data-current="1v-out"'))
            arrows.append(harrow([(xr, self.Y(z_die)), (xr, self.Y(z_ind))], "ret", 1.6,
                                 'data-current="1v-return"'))
        # tags: 48 V below the PCB backside under their balls; 1 V outside the die edge
        ty = y_pcb + 17
        a_in, a_ret = ("end", "start") if m < 0 else ("start", "end")
        tags.append(tag(self.X(xb_s) + (6 if a_in == "end" else -6), ty, "48 V in", F.I48, a_in))
        tags.append(tag(self.X(xb_r) + (6 if a_ret == "end" else -6), ty, "48 V return",
                        F.IRET, a_ret, dashed=True))
        tags.append(poly([(self.X(xb_s), y_pcb + 2), (self.X(xb_s), ty - 6)], F.I48, 1.2))
        tags.append(poly([(self.X(xb_r), y_pcb + 2), (self.X(xb_r), ty - 6)], F.IRET, 1.2,
                         dash="3,2"))

        c0 = cs[0]
        x_tag = self.X(m * self.D / 2) + m * 9
        t_anchor = "start" if m > 0 else "end"
        xo0, xr0 = self.X(c0 + m * d1), self.X(c0 - m * d1)   # outermost cell's two arrows
        if self.embedded:
            # beside the die; the return tag sits below the arrow tails (no crossing)
            y_out = self.Y(z_die)
            y_ret = self.Y(z_ind) + 15
            tags.append(poly([(x_tag, y_out), (xo0, y_out)], F.I1V, 1.2))
            tags.append(poly([(x_tag, y_ret), (xr0, y_ret), (xr0, self.Y(z_ind) + 5)], F.IRET,
                             1.2, dash="3,2"))
        else:
            # the arrows' lower ends share z with the PCB frame, where the 48 V paths run:
            # 1 V out at the substrate top, the return just above the arrow tips
            y_out = self.Y(substrate(a)[-1]["z1_um"])
            y_ret = self.Y(z_die) - 16
            tags.append(poly([(x_tag, y_out), (xo0, y_out)], F.I1V, 1.2))
            tags.append(poly([(x_tag, y_ret), (xr0, y_ret), (xr0, self.Y(z_die) - 2)], F.IRET,
                             1.2, dash="3,2"))
        tags.append(tag(x_tag, y_out, "1 V out", F.I1V, t_anchor))
        tags.append(tag(x_tag, y_ret, "1 V return", F.IRET, t_anchor, dashed=True))
        return "".join(arrows), "".join(tags)

    # ---- labels
    def label_requests(self, compact=False) -> list:
        a, s = self.a, self.side
        sg = 1 if s == "right" else -1
        x_pkg = sg * (self.W / 2 - (self.W - self.D) / 4)          # outside die, inside frame
        x_cell = sg * (max(abs(c) for c in self.cells) + self.side_mm / 4)
        x_die = sg * (self.D / 2 - self.side_mm / 4)
        bga = by_role(a, "bga")
        reqs = []
        mid = (lambda z0, z1: (z0 + z1) / 2)
        for L in a["layers"]:
            k, z0, z1 = kind(L), L["z0_um"], L["z1_um"]
            zc = mid(z0, z1)
            if k.startswith("tier_") or k == "attach":
                x = x_cell
                if self.C and z0 < bga["z0_um"] < z1:     # keep the leader off the BGA row
                    zc = mid(z0, bga["z0_um"])
            elif k == "bga":
                x = min(self.sites, key=lambda v: abs(v - x_pkg))
            elif k in ("interface", "die", "tim"):
                x = x_die
            else:
                x = x_pkg
                if k == "pcb":                             # board label at the bottom
                    zc = z0 + (z1 - z0) / 4
                elif k == "substrate" and L is substrate(a)[0]:
                    zc = z0 + (z1 - z0) / 4                # leave the upper part to the TSVs
            reqs.append({"name": plain_name(a, L), "thick": fmt_um(L["t_um"]),
                         "dot": (self.X(x), self.Y(zc))})
        sub = substrate(a)
        tz = sub[0]["z0_um"] + 3 * (sub[0]["z1_um"] - sub[0]["z0_um"]) / 4
        n = tsv_grid(a)
        t = a["tsv"]
        land = "; lands on the Cu-pillar attach" if attach_layer(a) else ""
        tsv_txt = (f"Cu TSV field under each cell — {t['rail_carried']}{land}"
                   if compact else
                   f"Cu TSV field under each cell — {t['rail_carried']}; {t['n_per_cell']} "
                   f"vias ({n} × {n}), Ø{t['d_um']:g} µm at {t['pitch_um']:g} µm pitch")
        reqs.append({"name": tsv_txt, "thick": None,
                     "dot": (self.X(sg * max(abs(c) for c in self.cells)), self.Y(tz))})
        if not direct_fed(a):
            reqs.append({"name": SHEET_TEXT, "thick": None,
                         "dot": (self.X(sg * (self.W / 2 - self.side_mm / 3)),
                                 self.Y(sub[0]["z0_um"]))})
        if direct_fed(a):
            m_ = self.mirror()
            c_ = sorted(self.cells, key=lambda x: -m_ * x)[1]
            z_b = min(L["z0_um"] for L in tiers(a))
            reqs.append({"name": FEED_TEXT, "thick": None,
                         "dot": (self.X(c_), self.Y(z_b) + 9)})
        ooc = a.get("out_of_cell") or {}
        if self.C and ooc.get("ring") == "VOID" and ooc.get("extent_x_mm"):
            t_ = tiers(a)
            reqs.append({"name": CLEARANCE_TEXT, "thick": None,
                         "dot": (self.X(sg * (ooc["extent_x_mm"][1] + self.C / 2) / 2),
                                 self.Y((t_[0]["z0_um"] + t_[-1]["z1_um"]) / 2))})
        tim = named(a, "tim")
        reqs.append({"name": ("cold plate (schematic) — top cooling boundary: convective "
                              "film on the TIM top, not meshed"),
                     "thick": None,
                     "dot": (self.X(x_die), self.Y(tim["z1_um"]) - COLD_PLATE_PX / 2)})
        return reqs

    def converter_bracket(self, x) -> str:
        t = tiers(self.a)
        z0, z1 = t[0]["z0_um"], t[-1]["z1_um"]
        y0, y1 = self.Y(z0), self.Y(z1)
        c = self.a["cells"]
        out = [poly([(x + 6, y1), (x, y1), (x, y0), (x + 6, y0)], F.INK, 1.4)]
        lines = ["converter", fmt_um(z1 - z0), f"{len(t)} tiers",
                 f"{c['n']} cells ({c['grid']} × {c['grid']})"]
        if not self.embedded:
            lines.append("hangs in the opening")
        ym = (y0 + y1) / 2
        for j, s in enumerate(lines):
            out.append(F.text(x - 8, ym + (j - (len(lines) - 1) / 2) * LINE + FS * 0.36, s, FS,
                              "end", "bold" if j == 0 else "normal", halo=False))
        return "".join(out)

    def metadata(self) -> dict:
        a = self.a
        t, sub, board, bga = tiers(a), substrate(a), named(a, "board"), by_role(a, "bga")
        hvr = {"what": ("converter embedded between substrate and die" if self.embedded
                        else "converter on the substrate backside (land side), hanging in "
                             "the PCB opening"),
               "tiers": len(t), "layers": [L["name"] for L in t],
               "z0_um": t[0]["z0_um"], "z1_um": t[-1]["z1_um"],
               "height_um": t[-1]["z1_um"] - t[0]["z0_um"]}
        sub_d = {"layers": [L["name"] for L in sub], "z0_um": sub[0]["z0_um"],
                 "z1_um": sub[-1]["z1_um"], "thickness_um": sub[-1]["z1_um"] - sub[0]["z0_um"],
                 "width_mm": a["substrate_mm"][0]}
        rdl = {"what": "48 V package RDL sheet", "fe_layer": False,
               "model": "2-D resistor network over the substrate underside",
               "z_um": sub[0]["z0_um"], "width_mm": a["substrate_mm"][0]}
        items = {
            "bga": {"layer": bga["name"], "pitch_mm": a["bga"]["pitch_mm"],
                    "sites_legal": a["bga"]["sites_legal"], "height_um": a["bga"]["height_um"],
                    "balls_on_section_row": len(self.sites),
                    "peripheral_only": bool(self.C),
                    "electrical_role": ("signals, auxiliary rails, mechanical -- NOT the 48 V "
                                        "HVR feed" if direct_fed(a) else
                                        "48 V supply + return, signals, mechanical")},
            "pcb": {"layer": board["name"], "thickness_um": board["t_um"],
                    "z0_um": board["z0_um"], "z1_um": board["z1_um"],
                    "annular_frame": bool(self.C)},
            "tsv_field": dict(a["tsv"], layers=[L["name"] for L in sub],
                              per_row=tsv_grid(a)),
            "cell_arrangement": {"n": a["cells"]["n"], "grid": a["cells"]["grid"],
                                 "arrangement": f"{a['cells']['grid']}x{a['cells']['grid']}",
                                 "side_mm": a["cells"]["side_mm"],
                                 "centres_x_mm_on_section": self.cells},
        }
        if self.embedded:
            items.update(embedded_hvr=hvr, substrate=sub_d, package_rdl=rdl)
        else:
            items.update(backside_hvr=hvr, thin_substrate=sub_d,
                         pcb_cutout={"width_mm": self.C, "air_below_converter_um":
                                     t[0]["z0_um"] - a["z_min_um"]})
            if direct_fed(a):
                att = attach_layer(a)
                items.update(
                    direct_48v_feed={"what": FEED_TEXT, "illustrative": True,
                                     "parameter": "R_Z2_direct_feed_loop (swept)"},
                    vr_attach={"layer": att["name"], "t_um": att["t_um"],
                               "z0_um": att["z0_um"], "z1_um": att["z1_um"],
                               "technology": (a.get("attach") or {}).get("technology")}
                    if att else None,
                    sidewall_clearance=a.get("out_of_cell"))
            else:
                items.update(package_hv_rdl=rdl)
        return {"architecture": a["arch"], "label": a["label"], "items": items}

    def draw(self) -> tuple:
        """(geometry svg, arrows svg, tags svg)."""
        geo = (self.bands() + self.clearance() + self.balls() + self.air() + self.sheet()
               + self.cold_plate())
        arr, tg = self.currents()
        return geo, arr, tg


# =================================================================== figures
def _scale_note(s_x, zm) -> list:
    v = PX_PER_MM_Z / s_x
    return [f"Section at y = 0 through the middle row of cells. Horizontal {s_x:g} px/mm; "
            f"vertical scale ×{v:g} (vertical exaggeration).",
            f"Layers thinner than {zm.floor:g} µm are drawn at a minimum height (as "
            f"{zm.floor:g} µm thick); true thickness labelled. Z1 and Z2 share one z-mapping."]


def _root_attrs(spec, zm, s_x, y_datum, arch, x_left) -> str:
    return attrs(data_spec_sha256=spec["sha256"], data_architecture=arch,
                 data_figure="package-cross-section",
                 data_px_per_mm_x=f"{s_x:g}", data_px_per_mm_z=f"{PX_PER_MM_Z:g}",
                 data_vertical_exaggeration=f"{PX_PER_MM_Z / s_x:g}",
                 data_z_floor_um=f"{zm.floor:g}", data_y_datum_px=num(y_datum),
                 data_x_left_px=num(x_left) if x_left is not None else "per-panel",
                 data_datum="PCB backside (lowest knot of the shared z-mapping)")


def _bars(x, y, s_x, zm) -> str:
    hb = 5.0
    vb_mm = 0.5
    vb = vb_mm * 1e3 * zm.k
    out = [F.scale_bar(x, y, hb * s_x, f"{hb:g} mm", FS)]
    xv = x + hb * s_x + 34
    out.append(f'<line x1="{num(xv)}" y1="{num(y + 6)}" x2="{num(xv)}" y2="{num(y + 6 - vb)}" '
               f'stroke="{F.INK}" stroke-width="2"/>'
               f'<line x1="{num(xv - 4)}" y1="{num(y + 6)}" x2="{num(xv + 4)}" y2="{num(y + 6)}" '
               f'stroke="{F.INK}"/><line x1="{num(xv - 4)}" y1="{num(y + 6 - vb)}" '
               f'x2="{num(xv + 4)}" y2="{num(y + 6 - vb)}" stroke="{F.INK}"/>\n')
    out.append(F.text(xv + 8, y + 6 - vb / 2 - 2, f"{vb_mm:g} mm vertical", FS, halo=False))
    out.append(F.text(xv + 8, y + 6 - vb / 2 + 15, f"(valid for layers ≥ {zm.floor:g} µm)",
                      FS, fill=F.MUTED, halo=False))
    return "".join(out)


def cross_section_svg(spec, arch) -> str:
    a = spec["architectures"][arch]
    zm = ZMap(spec)
    Wc, Hc = 1500, 900
    s_x = PX_PER_MM_X_SINGLE
    x_left = 196.0
    top = 132.0
    y_datum = top + COLD_PLATE_PX + zm.total
    sec = Section(a, zm, x_left, y_datum, s_x, "right")
    geo, arr, tg = sec.draw()
    title = a["label"].replace(" -- ", " — ")
    out = [F.svg_open(Wc, Hc, title, key_message(a),
                      _root_attrs(spec, zm, s_x, y_datum, arch, x_left)),
           patterns(), metadata_block(dict(sec.metadata(), spec_sha256=spec["sha256"]))]
    out.append(F.text(24, 38, title, 26, weight="bold", halo=False))
    out.append(F.text(24, 67, key_message(a), 18, fill=F.Z1 if arch == "Z1" else F.Z2,
                      weight="bold", halo=False))
    for j, s in enumerate(_scale_note(s_x, zm)):
        out.append(F.text(24, 92 + j * 18, s, FS, fill=F.MUTED, halo=False))
    out += [geo, arr, tg]
    out.append(sec.converter_bracket(x_left - 14))
    out.append(F.text(x_left - 8, y_datum - 5, "PCB backside", FS, "end", fill=F.MUTED,
                      halo=False))
    x_edge = sec.x_right + 14
    x_text = x_edge + 34
    out.append(leaders(sec.label_requests(), "right", x_edge, x_text, Wc - x_text - 12,
                       top - 12, y_datum + 12))
    out.append(_bars(24, y_datum + 92, s_x, zm))
    items = legend_items([a])
    out.append(legend_block(420, y_datum + 40, items, 4, 268))
    out.append(F.svg_close())
    return "".join(out)


def comparison_svg(spec) -> str:
    zm = ZMap(spec)
    Wc, Hc = 1600, 900
    s_x = PX_PER_MM_X_PAIR
    A = spec["architectures"]
    w_draw = A["Z1"]["substrate_mm"][0] * s_x
    gap = 92.0
    x1 = (Wc - gap) / 2 - w_draw
    x2 = (Wc + gap) / 2
    top = 150.0
    y_datum = top + COLD_PLATE_PX + zm.total
    secs = {"Z1": Section(A["Z1"], zm, x1, y_datum, s_x, "left"),
            "Z2": Section(A["Z2"], zm, x2, y_datum, s_x, "right")}
    out = [F.svg_open(Wc, Hc, "Z1 vs Z2 package cross-sections",
                      "Side-by-side at identical scale and z-mapping, aligned on the PCB "
                      "backside", _root_attrs(spec, zm, s_x, y_datum, "Z1,Z2", None)),
           patterns(),
           metadata_block({"spec_sha256": spec["sha256"],
                           "panels": {k: s.metadata() for k, s in secs.items()}})]
    out.append(F.text(Wc / 2, 30, "Z1 vs Z2 — identical scale, identical z-mapping, aligned "
                      "on the PCB backside", 22, "middle", "bold", halo=False))
    out.append(F.text(Wc / 2, 52, " ".join(_scale_note(s_x, zm)), FS, "middle", fill=F.MUTED,
                      halo=False))
    for arch, sec in secs.items():
        a = A[arch]
        cx = sec.X(0.0)
        col = F.Z1 if arch == "Z1" else F.Z2
        out.append(F.text(cx, 82, a["label"].replace(" -- ", " — "), 17, "middle", "bold",
                          col, halo=False))
        for j, s in enumerate(wrap(key_message(a), w_draw, FS + 1)):   # within its panel
            out.append(F.text(cx, 104 + j * 18, s, FS + 1, "middle", halo=False))
    for arch, sec in secs.items():
        geo, arr, tg = sec.draw()
        out.append(f'<g {attrs(data_panel=arch, data_x_left_px=num(sec.x_left))}>\n'
                   + geo + arr + tg + "</g>\n")
    # datum lines through both drawings and the gap between them
    for z, lab in ((spec["architectures"]["Z1"]["z_min_um"], ["PCB", "backside", "(datum)"]),
                   (substrate(A["Z1"])[0]["z0_um"], ["substrate", "underside"])):
        y = secs["Z1"].Y(z)
        out.append(poly([(x1 - 8, y), (x2 + w_draw + 8, y)], F.INK, 1.0, dash="2,3",
                        extra='opacity="0.75"'))
        below = z > spec["architectures"]["Z1"]["z_min_um"]
        for j, s in enumerate(lab):
            yy = y + 17 + j * 15 if below else y - 6 - (len(lab) - 1 - j) * 15
            out.append(F.text(Wc / 2, yy, s, FS, "middle", "bold", F.MUTED))
    out.append(leaders(secs["Z1"].label_requests(compact=True), "left", x1 - 14,
                       x1 - 44, x1 - 56, top - 8, y_datum + 12))
    out.append(leaders(secs["Z2"].label_requests(compact=True), "right", x2 + w_draw + 14,
                       x2 + w_draw + 44, Wc - (x2 + w_draw + 44) - 12, top - 8, y_datum + 12))
    out.append(legend_block(36, y_datum + 40, legend_items(A.values()), 4, 296))
    out.append(_bars(1252, y_datum + 92, s_x, zm))
    out.append(F.svg_close())
    return "".join(out)


# =================================================================== exploded (isometric)
def exploded_svg(spec) -> str:
    """Both stacks exploded along z, every slab in the spec's z order. ILLUSTRATIVE."""
    Wc, Hc = 1600, 900
    cos30, sin30 = math.cos(math.radians(30)), 0.5
    s_iso, flat = 4.6, 0.6
    y_top, y_bot = 180.0, Hc - 60.0                # back corner of the top slab .. front corner
    t_max = max(L["t_um"] for a in spec["architectures"].values() for L in a["layers"])
    slab_h = (lambda t: 3.0 + 9.0 * math.sqrt(t / t_max))        # illustrative thickness
    sheet_h, cold_h = 2.0, 12.0
    out = [F.svg_open(Wc, Hc, "Z1 and Z2 stacks, exploded",
                      "Layer order and ownership from the measured spec; illustrative "
                      "thicknesses and gaps", attrs(data_spec_sha256=spec["sha256"],
                                                    data_figure="exploded",
                                                    data_stamp=STAMP)),
           patterns()]
    out.append(F.text(28, 42, "Z1 and Z2 stacks, exploded — layer order and component "
                      "ownership from the measured spec", 24, weight="bold", halo=False))
    out.append(stamp(28, 56, STAMP))
    out.append(F.text(28, 108, "Slab thicknesses and gaps are illustrative; every label gives "
                      "the true thickness. The 48 V package sheet and the cold plate are drawn "
                      "but are not FE layers.", FS, fill=F.MUTED, halo=False))

    face_half = max(a["substrate_mm"][0] for a in spec["architectures"].values()) / 2 \
        * 2 * s_iso * sin30 * flat
    base = y_bot - face_half

    def P(cx, x, y, zs):
        return (cx + (x - y) * s_iso * cos30, base - (x + y) * s_iso * sin30 * flat - zs)

    def quad(cx, x0, x1, y0, y1, z):
        return [P(cx, x0, y0, z), P(cx, x1, y0, z), P(cx, x1, y1, z), P(cx, x0, y1, z)]

    def pg(pts, fill, extra="", sw=0.7):
        d = " ".join(f"{num(x)},{num(y)}" for x, y in pts)
        return (f'<polygon points="{d}" fill="{fill}" stroke="{F.INK}" stroke-width="{sw}" '
                f'stroke-linejoin="round" {extra}/>\n')

    def shade(hexcol, f):
        c = hexcol.lstrip("#")
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
        return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * f))) for v in (r, g, b))

    def sides(cx, h0, h1, zb, h, fill, ex):
        """The two visible side faces of a square slab [h0, h1]^2 between zb and zb + h."""
        f1 = [P(cx, h0, h0, zb + h), P(cx, h1, h0, zb + h), P(cx, h1, h0, zb), P(cx, h0, h0, zb)]
        f2 = [P(cx, h0, h0, zb + h), P(cx, h0, h1, zb + h), P(cx, h0, h1, zb), P(cx, h0, h0, zb)]
        return pg(f1, shade(fill, 0.78), ex) + pg(f2, shade(fill, 0.9), ex)

    for col, arch in enumerate(("Z1", "Z2")):
        a = spec["architectures"][arch]
        cx = 286 + col * 800
        Wm, Dm, Cm = a["substrate_mm"][0], a["die_mm"][0], a["cutout_mm"]
        cells = sorted(a["cells"]["centres_x_mm"])
        side = a["cells"]["side_mm"]
        sub0 = substrate(a)[0]
        seq = [("layer", L) for L in sorted(a["layers"], key=lambda L: (L["z0_um"], L["z1_um"]))]
        i_sub = next(i for i, (_, L) in enumerate(seq) if L is sub0)
        if not direct_fed(a):                  # a direct-fed Z2 has no package 48 V sheet
            seq.insert(i_sub, ("sheet", sub0))
        seq.append(("cold", None))
        hs = [sheet_h if t == "sheet" else cold_h if t == "cold" else slab_h(L["t_um"])
              for t, L in seq]
        face = 2 * face_half                           # screen height of a full top face
        gap = (y_bot - y_top - face - sum(hs)) / (len(seq) - 1)
        colc = F.Z1 if arch == "Z1" else F.Z2
        out.append(F.text(cx + 150, 150, a["label"].replace(" -- ", " — "), 17, "middle", "bold",
                          colc, halo=False))
        zb, labels = 0.0, []
        out.append(f'<g {attrs(data_panel=arch)}>\n')
        for order, ((typ, L), h) in enumerate(zip(seq, hs)):
            if typ == "sheet":
                hw = Wm / 2
                out.append(pg(quad(cx, -hw, hw, -hw, hw, zb + h), F.I48,
                              'fill-opacity="0.34" stroke-dasharray="5,3" '
                              + attrs(data_feature="pkg-48v-rdl-sheet", data_order=order,
                                      data_fe_layer="false"), 1.2))
                labels.append((P(cx, hw, -hw, zb + h), SHEET_TEXT, None))
            elif typ == "cold":
                hw = Dm / 2
                cp = F.MAT["coldplate"]
                ex = attrs(data_feature="cold-plate", data_order=order, data_schematic="true")
                out.append(sides(cx, -hw, hw, zb, h, cp, ex)
                           + pg(quad(cx, -hw, hw, -hw, hw, zb + h), cp, ex))
                labels.append((P(cx, hw, -hw, zb + h / 2),
                               "cold plate (schematic) — top cooling boundary of the model",
                               None))
            else:
                k = kind(L)
                pieces = lateral(a, L)
                hw = max(abs(v) for pc in pieces for v in pc)
                fill = F.MAT["fill"] if k.startswith("tier_") else BAND_FILL[k]
                if direct_fed(a) and "hs" in L["roles"] and order > 0:
                    # the direct 48 V feed, in the gap below the deepest (high-side) tier
                    fx0, fy0 = P(cx, 0.0, 0.0, zb - gap)
                    fx1, fy1 = P(cx, 0.0, 0.0, zb)
                    out.append(f'<line x1="{num(fx0)}" y1="{num(fy0)}" x2="{num(fx1)}" '
                               f'y2="{num(fy1)}" stroke="{F.I48}" stroke-width="3" '
                               f'{attrs(data_feature="direct-48v-feed")}/>\n')
                    out.append(F.rect(fx1 - 16, (fy0 + fy1) / 2 - 7, 32, 14, "#fff4e5", F.I48,
                                      1.4, 'rx="3"'))
                    labels.append((((fx0 + fx1) / 2 + 16, (fy0 + fy1) / 2),
                                   "direct 48 V feed through the PCB opening (illustrative; "
                                   "connector not specified)", None))
                if k == "interface":
                    fill = F.MAT["solder"]
                ex = attrs(data_layer=L["name"], data_order=order,
                           data_z0_um=repr(float(L["z0_um"])), data_z1_um=repr(float(L["z1_um"])))
                out.append(sides(cx, -hw, hw, zb, h, fill, ex))
                top = quad(cx, -hw, hw, -hw, hw, zb + h)
                if len(pieces) == 2:                   # annulus: the PCB frame, the BGA ring
                    ch = Cm / 2
                    hole = quad(cx, -ch, ch, -ch, ch, zb + h)
                    d_o = " ".join(f"{num(x)},{num(y)}" for x, y in top)
                    d_i = " ".join(f"{num(x)},{num(y)}" for x, y in hole)
                    out.append(f'<path d="M{d_o} Z M{d_i} Z" fill="{fill}" fill-rule="evenodd" '
                               f'stroke="{F.INK}" stroke-width="0.7" {ex}/>\n')
                    w1 = [P(cx, -ch, ch, zb + h), P(cx, ch, ch, zb + h), P(cx, ch, ch, zb),
                          P(cx, -ch, ch, zb)]
                    w2 = [P(cx, ch, -ch, zb + h), P(cx, ch, ch, zb + h), P(cx, ch, ch, zb),
                          P(cx, ch, -ch, zb)]
                    out += [pg(w1, shade(fill, 0.7)), pg(w2, shade(fill, 0.84))]
                else:
                    out.append(pg(top, fill, ex))
                # component ownership on the top face
                if k.startswith("tier_") or k == "substrate":
                    cf = TIER_FILL.get(k, F.MAT["tsv"])
                    for xc in cells:
                        for yc in cells:
                            out.append(pg(quad(cx, xc - side / 2, xc + side / 2, yc - side / 2,
                                               yc + side / 2, zb + h), cf, sw=0.4))
                elif k == "attach":
                    for xc in cells:
                        for yc in cells:
                            out.append(pg(quad(cx, xc - side / 2, xc + side / 2, yc - side / 2,
                                               yc + side / 2, zb + h), PILLAR, sw=0.4))
                elif k == "bga":
                    pitch = a["bga"]["pitch_mm"]
                    n = int(Wm / 2 / pitch + 1e-9)
                    row = [round(v * pitch, 9) for v in range(-n, n + 1)]
                    inside = (lambda v: Cm is not None and abs(v) < Cm / 2)
                    for xv in row:
                        for yv in row:
                            if not (inside(xv) and inside(yv)):
                                X_, Y_ = P(cx, xv, yv, zb + h)
                                out.append(f'<ellipse cx="{num(X_)}" cy="{num(Y_)}" rx="1.25" '
                                           f'ry="0.8" fill="{F.INK}" opacity="0.6"/>\n')
                labels.append((P(cx, hw, -hw, zb + h / 2), plain_name(a, L), fmt_um(L["t_um"])))
            zb += h + gap
        out.append("</g>\n")
        reqs = [{"name": n, "thick": t, "dot": d} for d, n, t in labels]
        x_edge = cx + Wm * s_iso * cos30 + 16
        out.append(leaders(reqs, "right", x_edge, x_edge + 31, 330, y_top - 12, base + 6))
        for j, s in enumerate(wrap(key_message(a), 640, FS + 1, True)):
            out.append(F.text(cx + 150, Hc - 34 + j * 18, s, FS + 1, "middle", "bold", colc,
                              halo=False))
    out.append(F.svg_close())
    return "".join(out)


def _png_with_text(png: bytes, key: str, text_: str) -> bytes:
    """Insert one uncompressed iTXt chunk before IEND (pure Python, no imaging library)."""
    data = key.encode("latin-1") + b"\0\0\0" + b"\0" + b"\0" + text_.encode("utf-8")
    chunk = (struct.pack(">I", len(data)) + b"iTXt" + data
             + struct.pack(">I", zlib.crc32(b"iTXt" + data) & 0xFFFFFFFF))
    i = png.rindex(b"IEND") - 4
    return png[:i] + chunk + png[i:]


def render_png(svg_text: str, width: int) -> bytes:
    r = subprocess.run(["rsvg-convert", "-w", str(width), "-b", "white"],
                       input=svg_text.encode(), capture_output=True, check=True)
    return r.stdout


# =================================================================== one regulator cell
def cell_inventory():
    """Per-cell component counts from the stack card's section-4 inventory table."""
    txt = STACKS_MD.read_text()
    out = {}
    for key, pat in (("hs", r"\|\s*HS/cell\s*\|\s*(\d+)"), ("ls", r"\|\s*LS/cell\s*\|\s*(\d+)"),
                     ("ind", r"\|\s*inductors/cell\s*\|\s*(\d+)"),
                     ("caps", r"\|\s*flying caps/cell\s*\|\s*(\d+)"),
                     ("total", r"\|\s*components/cell\s*\|\s*(\d+)")):
        m = re.search(pat, txt)
        if not m:
            raise ValueError(f"inventory row {key} not found in {STACKS_MD.name}")
        out[key] = int(m.group(1))
    if out["hs"] + out["ls"] + out["ind"] + out["caps"] != out["total"]:
        raise ValueError("cell inventory does not add up")
    return out


def cell_zoom_svg(spec) -> str:
    """ONE regulator cell per architecture: true proportions, schematic device placement."""
    inv = cell_inventory()
    Wc, Hc = 1500, 900
    s = 150.0                                   # px per mm, BOTH axes: no exaggeration
    out = [F.svg_open(Wc, Hc, "One regulator cell — Z1 and Z2",
                      "Cell side and tier heights from the spec; device placement schematic",
                      attrs(data_spec_sha256=spec["sha256"], data_figure="cell-zoom",
                            data_px_per_mm_x=f"{s:g}", data_px_per_mm_z=f"{s:g}",
                            data_vertical_exaggeration="1", data_z_floor_um=f"{Z_FLOOR_UM:g}")),
           patterns()]
    out.append(F.text(24, 38, "One regulator cell (1 of 49) — tiers from the measured spec",
                      24, weight="bold", halo=False))
    out.append(F.text(24, 64, f"Each cell holds {inv['total']} components: {inv['hs']} high-side "
                      f"GaN, {inv['ls']} low-side GaN, {inv['ind']} inductors, {inv['caps']} "
                      "flying capacitors (stack card §4). Identical in Z1 and Z2; only the "
                      "orientation and the neighbours change.", FS + 1, halo=False))
    out.append(stamp(24, 78, "DEVICE PLACEMENT SCHEMATIC — cell side and tier heights true", FS))
    out.append(F.text(24, Hc - 22, f"True proportions: {s:g} px/mm horizontally and vertically "
                      "(vertical scale ×1), except layers thinner than "
                      f"{Z_FLOOR_UM:g} µm, drawn {Z_FLOOR_UM:g} µm tall; true thickness labelled.",
                      FS, fill=F.MUTED, halo=False))
    y_base = 712.0
    for col, arch in enumerate(("Z1", "Z2")):
        a = spec["architectures"][arch]
        side = a["cells"]["side_mm"]
        t = tiers(a)
        emb = is_embedded(a)
        x0 = 96 + col * 700
        w = side * s
        k = s / 1e3
        ys, cum = {}, y_base                    # deepest tier at the bottom in both
        for L in t:
            h = max(L["t_um"], Z_FLOOR_UM) * k
            ys[L["name"]] = (cum - h, cum)
            cum -= h
        att = attach_layer(a)
        if att is not None:                     # the VR attach above the land-side RDL
            h = max(att["t_um"], Z_FLOOR_UM) * k
            ys[att["name"]] = (cum - h, cum)
            cum -= h
        y_top = cum
        colc = F.Z1 if emb else F.Z2
        out.append(F.text(x0 + w / 2 + 120, 150, a["label"].replace(" -- ", " — "), 17, "middle",
                          "bold", colc, halo=False))
        up = ("↑ microbumps, then the die" if emb else "↑ substrate TSVs, then the die")
        dn = ("↓ substrate TSVs" if emb else
              "↓ direct 48 V feed through the PCB opening (illustrative)" if direct_fed(a)
              else "↓ air in the PCB opening")
        out.append(F.text(x0 + w / 2 + 24, y_top - 12, up, FS, "middle", fill=F.MUTED, halo=False))
        out.append(F.text(x0 + w / 2 + 24, y_base + 22, dn, FS, "middle", fill=F.MUTED,
                          halo=False))
        reqs = []
        out.append(f'<g {attrs(data_panel=arch)}>\n')
        for L in t:
            y1, y2 = ys[L["name"]]
            kk = kind(L)
            base_fill = F.MAT["rdl"] if kk == "tier_rdl" else F.MAT["fill"]
            out.append(F.rect(x0, y1, w, y2 - y1, base_fill, F.INK, 0.7,
                              attrs(data_layer=L["name"], data_z0_um=repr(float(L["z0_um"])),
                                    data_z1_um=repr(float(L["z1_um"])))))
            n = {"tier_gan": inv["hs"] if "hs" in L["roles"] else inv["ls"],
                 "tier_inductor": inv["ind"], "tier_caps": inv["caps"]}.get(kk, 0)
            for j in range(n):                  # devices kept clear of the arrow margin
                span = w - 48
                bw = span / n * 0.78
                xc = x0 + 48 + (j + 0.5) * span / n
                out.append(F.rect(xc - bw / 2, y1 + 3, bw, y2 - y1 - 6, TIER_FILL[kk], F.INK, 0.7,
                                  'rx="3" ' + attrs(data_component_of=L["name"])))
            nm = plain_name(a, L)
            reqs.append({"name": f"{n} × {nm}" if n else nm, "thick": fmt_um(L["t_um"]),
                         "dot": (x0 + w - 6, (y1 + y2) / 2)})
        if att is not None:
            y1, y2 = ys[att["name"]]
            out.append(F.rect(x0, y1, w, y2 - y1, "url(#pillar)", F.INK, 0.7,
                              attrs(data_layer=att["name"], data_z0_um=repr(float(att["z0_um"])),
                                    data_z1_um=repr(float(att["z1_um"])))))
            reqs.append({"name": plain_name(a, att), "thick": fmt_um(att["t_um"]),
                         "dot": (x0 + w - 6, (y1 + y2) / 2)})
        out.append("</g>\n")
        # where 48 V enters and 1 V leaves (schematic, inside the cell's free left margin)
        hs_y = sum(ys[by_role(a, "hs")["name"]]) / 2
        ind_y = sum(ys[by_role(a, "ind")["name"]]) / 2
        x48, x1v = x0 + 14, x0 + 32
        if emb or direct_fed(a):
            # Z1 (from the substrate TSVs) and the direct-fed Z2 (from the external feed)
            # both take 48 V at the high-side RDL, from below
            out.append(harrow([(x48, y_base + 34), (x48, hs_y)], "48", 2.5))
            out.append(tag(x48 + 8, y_base + 46, "48 V in", F.I48, "end"))
        else:
            out.append(harrow([(x48, y_top - 31), (x48, hs_y)], "48", 2.5))
            out.append(tag(x48 + 8, y_top - 42, "48 V in", F.I48, "end"))
        out.append(harrow([(x1v, ind_y), (x1v, y_top - 31)], "1v", 2.5))
        out.append(tag(x1v - 6, y_top - 42, "1 V out", F.I1V, "start" if emb else "end"))
        xe = x0 + w + 14
        out.append(leaders(reqs, "right", xe, xe + 31, (Wc - 12 if col else x0 + 690) - xe - 31,
                           y_top - 4, y_base + 4))
        out.append(F.scale_bar(x0, y_base + 66, w, f"cell side {side:.4g} mm (from the spec)", FS))
    out.append(F.svg_close())
    return "".join(out)


# =================================================================== power path
def _pp_numbers():
    """Currents and counts for the power-path figure, from the artifacts (never typed)."""
    D = R / "research" / "final_closure"
    out = {"i48": None, "n_bga": None, "attach": None}
    try:
        fin = json.loads((D / "final_results.json").read_text())
        z1 = next(f for f in fin if f["arch"] == "Z1" and f["scenario"] == "HV_S0")
        out["i48"] = z1["I_48_avg_a"]
    except (OSError, StopIteration, KeyError, ValueError):
        pass
    try:
        out["n_bga"] = json.loads((D / "package_network.json").read_text())["matched_count"]
    except (OSError, KeyError, ValueError):
        pass
    try:
        out["attach"] = json.loads((D / "z2_direct_feed_architecture.json").read_text())[
            "vr_attach"]
    except (OSError, KeyError, ValueError):
        pass
    return out


def power_path_svg(spec, focus=None) -> str:
    """Z1 vs Z2 power paths, schematic. Layer ORDER and roles come from the spec; heights
    are schematic (stamped). It answers: where 48 V enters, what crosses the substrate,
    where conversion happens, where 1 V begins and how the load returns.

    Layout per panel: supply arrows in a channel LEFT of the stack (48 V up to the
    converter input, 1 V up from its output; the converter height between them carries
    the conversion bracket), the return in a channel RIGHT of the stack, and, for Z2, the
    PCB frame with its signal/mechanical BGA beyond the return channel."""
    num_ = _pp_numbers()
    A = spec["architectures"]
    if not (not direct_fed(A["Z1"]) and direct_fed(A["Z2"])):
        raise ValueError("power-path figure expects a BGA-fed Z1 and a direct-fed Z2")
    i48 = num_["i48"]
    i48_txt = f"about {i48:.0f} A" if i48 else "low current"
    nb = num_["n_bga"]
    att = num_["attach"] or {}
    Wc, Hc = 1600, 900
    mk = "".join(f'<marker id="pp{k}" viewBox="0 0 12 12" refX="10.2" refY="6" '
                 f'markerWidth="3.6" markerHeight="3.6" orient="auto">'
                 f'<path d="M0,0 L12,6 L0,12 z" fill="{c}"/></marker>'
                 for k, (c, _m) in ARROW_KINDS.items())
    out = [F.svg_open(Wc, Hc, "Z1 vs Z2 power paths",
                      "Where 48 V enters, what crosses the substrate, where conversion happens",
                      attrs(data_spec_sha256=spec["sha256"], data_figure="power-path",
                            data_schematic="true")),
           patterns(), f"<defs>{mk}</defs>\n"]
    title = {None: "Where does the power go? Z1 vs Z2",
             "48": "Where does 48 V go? Z1 vs Z2",
             "1v": "After conversion, where does 1 V go? Z1 vs Z2"}[focus]
    out.append(F.text(24, 42, title, 28, weight="bold", halo=False))
    out.append(stamp(24, 54, "SCHEMATIC — NOT TO SCALE (layer order from the measured spec)", FS))
    BH = 60.0
    THIN = ("rdl_out", "rdl_hv", "attach", "top")
    y0 = 800.0

    def stack(x, w, blocks, hi=None):
        pos, y = {}, y0
        for key, lab, fill, tcol in blocks:
            h = BH * (0.6 if key in THIN else 1.0)
            border = (F.I48 if hi == "48" else F.I1V) if key == "sub" else F.INK
            sw_ = 3.2 if key == "sub" else 0.9
            out.append(F.rect(x, y - h, w, h, fill, border, sw_, attrs(data_block=key)))
            if key == "attach":                 # label on a white plate over the pattern
                tw_ = tw(lab, FS, True) + 16
                out.append(F.rect(x + w / 2 - tw_ / 2, y - h / 2 - 11, tw_, 21, "#ffffff",
                                  "none", 0, 'opacity="0.92" rx="3"'))
            lines = wrap(lab, w - 16, FS + 1)
            for j, ln in enumerate(lines):
                out.append(F.text(x + w / 2, y - h / 2 + (j - (len(lines) - 1) / 2) * 17 + 5,
                                  ln, FS + 1 if key != "attach" else FS, "middle",
                                  "bold" if j == 0 else "normal", tcol, halo=False))
            pos[key] = (y - h, y)
            y -= h
        return pos

    def arr(x, ya, yb, k, sw=5.0):
        col = ARROW_KINDS[k][0]
        dash = 'stroke-dasharray="9,6" ' if k == "ret" else ""
        # a focused figure keeps its own rail at full strength and fades the others
        op = "" if (focus is None or k == focus) else 'opacity="0.18" '
        return (f'<path d="M{num(x)},{num(ya)} L{num(x)},{num(yb)}" stroke="{col}" '
                f'stroke-width="{sw}" fill="none" {dash}{op}marker-end="url(#pp{k})" '
                f'{attrs(data_current=k, data_focus=str(focus))}/>\n')

    def lab(x, y, t_, col, anc="end", width=170, k=None):
        if focus is not None and k is not None and k != focus:
            return
        for j, ln in enumerate(wrap(t_, width, FS + 1, True)):
            out.append(F.text(x, y + j * 18, ln, FS + 1, anc, "bold", col, halo=False))

    def bracket(x, ya, yb, txt):
        out.append(poly([(x + 8, ya), (x, ya), (x, yb), (x + 8, yb)], F.INK, 1.6))
        out.append(F.text(x - 8, (ya + yb) / 2 + 5, txt, FS + 1, "end", "bold", halo=False))

    # ---------------- Z1 (panel 0 .. 800)
    x1, w1 = 260, 400
    out.append(F.text(x1 + w1 / 2, 104, "Z1 — converter embedded above the substrate", 21,
                      "middle", "bold", F.Z1, halo=False))
    out.append(F.text(x1 + w1 / 2, 128, "48 V crosses the package and the substrate BEFORE "
                      "conversion", FS + 1, "middle", "bold", F.I48, halo=False))
    p1 = stack(x1, w1, [
        ("pcb", "PCB — 48 V platform supply", F.MAT["pcb"], "#ffffff"),
        ("bga", (f"BGA 48 V power field: {nb} + {nb} balls (plus signals)" if nb
                 else "BGA 48 V power field"), F.MAT["solder"], F.INK),
        ("rdl_hv", "package 48 V RDL sheet", "#fde2c8", F.INK),
        ("sub", f"Si substrate — 48 V TSV field ({i48_txt})", F.MAT["silicon"], F.INK),
        ("hs", "high-side GaN", F.MAT["gan"], "#ffffff"),
        ("caps", "flying capacitors", F.MAT["caps"], F.INK),
        ("ls", "low-side GaN", F.MAT["gan"], "#ffffff"),
        ("ind", "inductors + Cout", F.MAT["inductor"], "#ffffff"),
        ("rdl_out", "1 V output RDL", F.MAT["rdl"], F.INK),
        ("top", "microbumps", F.MAT["fill"], F.INK),
        ("die", "compute die — 1 V, about 1 kA", F.MAT["die"], "#ffffff")], hi="48")
    a1 = x1 - 34
    out.append(arr(a1, p1["pcb"][1] - 6, p1["hs"][1] - 2, "48"))
    out.append(arr(a1, p1["ind"][0] + 2, p1["die"][1] - 4, "1v"))
    out.append(arr(x1 + w1 + 34, p1["die"][1] - 2, p1["pcb"][1] - 6, "ret", 3.6))
    lab(a1 - 14, (p1["pcb"][1] + p1["hs"][1]) / 2, "48 V in", F.I48, k="48")
    lab(a1 - 14, (p1["ind"][0] + p1["die"][1]) / 2 - 8, "1 V out to the die", F.I1V, k="1v")
    lab(x1 + w1 + 48, (p1["die"][1] + p1["pcb"][1]) / 2, "return", F.IRET, "start", 90,
        k="ret")
    bracket(a1 - 4, p1["ind"][0], p1["hs"][1], "conversion")

    # ---------------- Z2 (panel 800 .. 1600)
    x2, w2 = 1010, 400
    out.append(F.text(x2 + w2 / 2, 104, "Z2 — direct-fed converter below the substrate", 21,
                      "middle", "bold", F.Z2, halo=False))
    out.append(F.text(x2 + w2 / 2, 128, "only 1 V crosses the substrate, AFTER conversion",
                      FS + 1, "middle", "bold", F.I1V, halo=False))
    p2 = stack(x2, w2, [
        ("feed", "direct 48 V feed through the PCB opening (ILLUSTRATIVE — connector not "
                 "specified)", "#fff4e5", F.I48),
        ("hs", "high-side GaN (deepest)", F.MAT["gan"], "#ffffff"),
        ("caps", "flying capacitors", F.MAT["caps"], F.INK),
        ("ls", "low-side GaN", F.MAT["gan"], "#ffffff"),
        ("ind", "inductors + Cout (nearest the substrate)", F.MAT["inductor"], "#ffffff"),
        ("rdl_out", "1 V output / attach RDL", F.MAT["rdl"], F.INK),
        ("attach", "Cu-pillar attach: regulator → substrate (1 V only)", "url(#pillar)",
         F.INK),
        ("sub", "Si substrate — 1 V VDD + GND TSV fields (about 1 kA)", F.MAT["silicon"],
         F.INK),
        ("top", "top 1 V RDL + microbumps", F.MAT["fill"], F.INK),
        ("die", "compute die — 1 V, about 1 kA", F.MAT["die"], "#ffffff")], hi="1v")
    a2 = x2 - 34
    out.append(arr(a2, p2["feed"][1] - 4, p2["hs"][1] - 2, "48"))
    out.append(arr(a2, p2["ind"][0] + 2, p2["die"][1] - 4, "1v"))
    out.append(arr(x2 + w2 + 34, p2["die"][1] - 2, p2["feed"][1] - 6, "ret", 3.6))
    lab(a2 - 14, (p2["feed"][0] + p2["hs"][1]) / 2, "48 V in, directly", F.I48, k="48")
    lab(a2 - 14, (p2["ind"][0] + p2["die"][1]) / 2 - 8, "1 V out to the die", F.I1V, k="1v")
    lab(x2 + w2 + 48, p2["die"][0] + 18, "return: TSVs → regulator → feed", F.IRET, "start",
        130, k="ret")
    bracket(a2 - 4, p2["ind"][0], p2["hs"][1], "conversion")
    # PCB frame + signal/mechanical BGA beside the opening (beyond the return channel)
    fx, fw = x2 + w2 + 62, 112
    f_top = p2["ind"][0]
    out.append(F.rect(fx, f_top, fw, p2["feed"][1] - f_top, F.MAT["pcb"], F.INK, 0.9,
                      attrs(data_block="pcb-frame")))
    for j in range(3):
        out.append(f'<circle cx="{num(fx + 21 + j * 36)}" cy="{num(f_top - 9)}" r="8.5" '
                   f'fill="{BGA_SIGNAL}" stroke="{F.INK}" stroke-width="0.8" '
                   f'{attrs(data_bga_role="signal-mechanical")}/>\n')
    out.append(F.text(fx + fw / 2, f_top + 31, "PCB frame", FS, "middle", "bold", "#ffffff",
                      halo=False))
    out.append(F.text(fx + fw / 2, f_top + 48, "around the", FS, "middle", "normal", "#ffffff",
                      halo=False))
    out.append(F.text(fx + fw / 2, f_top + 64, "opening", FS, "middle", "normal", "#ffffff",
                      halo=False))
    for j, ln in enumerate(wrap("BGA: signals, auxiliary rails, mechanical support — NOT the "
                                "48 V feed", 150, FS, True)):
        out.append(F.text(fx + fw / 2, f_top - 92 + j * 17, ln, FS, "middle", "bold",
                          F.MUTED, halo=False))
    # legend
    lg = [("48", None, "48 V supply"), ("1v", None, "1 V supply"),
          ("ret", None, "return (dashed)"), ("fill", BGA_SIGNAL, "BGA ball: signal / mechanical"),
          ("fill", F.MAT["solder"], "BGA ball in Z1's 48 V power field"),
          ("fill", PILLAR, "Cu pillar (Z2 regulator attach)")]
    out.append(legend_block(260, 830, lg, 3, 360))
    out.append(F.text(24, Hc - 11, "Arrows show where current flows, not an electrical series "
                      "chain: the converter has switch-node, flying-capacitor and phase "
                      "connections between its tiers.", FS, fill=F.MUTED, halo=False))
    out.append(F.svg_close())
    return "".join(out)


# =================================================================== VR attach detail
#: how much of the TSV depth the magnified attach view shows (a drawing choice, um)
WIN_TSV_UM = 48.0


def attach_detail_svg(spec) -> str:
    """The Z2 VR-to-substrate attach, magnified. Pillar diameter, pitch and heights come
    from the architecture spec (CLOSE_ANALOG literature geometry); the TSV diameter and
    pitch from the spec's TSV field. Schematic in that the landing pads are drawn but not
    resolved in the model (their spreading sits in the TSV two-end spreading term), and
    only the top WIN_TSV_UM of the substrate-deep TSVs is shown."""
    a = spec["architectures"]["Z2"]
    att = a.get("attach") or {}
    t = a["tsv"]
    if not att:
        raise ValueError("Z2 has no VR attach in the spec")
    d, pitch = float(att["d_um"]), float(att["pitch_um"])
    h_cu, h_cap = float(att["h_cu_um"]), float(att["h_cap_um"])
    tsv_d, tsv_p = float(t["d_um"]), float(t["pitch_um"])
    lay = {L["name"]: L for L in a["layers"]}
    t_rdl = float(next(L["t_um"] for n, L in lay.items() if "land_side_attach_rdl" in n))
    t_sub = sum(float(L["t_um"]) for L in a["layers"] if "tsv_tile" in L["materials"])
    side = float(a["cells"]["side_mm"])
    i_pillar = 1000.0 / a["cells"]["n"] / float(att["bumps_per_rail_per_cell"])
    k = 6.0                                       # px per um, both axes
    Wc, Hc = 1600, 900
    x0, win = 90.0, 2 * tsv_p                     # one VDD and one GND TSV
    X = (lambda um: x0 + um * k)
    out = [F.svg_open(Wc, Hc, "Z2 regulator-to-substrate attach",
                      "Cu pillar + solder cap + underfill; 1 V supply and return only",
                      attrs(data_spec_sha256=spec["sha256"], data_figure="vr-attach-detail",
                            data_px_per_um=f"{k:g}", data_schematic="true")),
           patterns()]
    out.append(F.text(24, 42, "The electrical bridge: regulator → package substrate (Z2)", 26,
                      weight="bold", halo=False))
    out.append(F.text(24, 68, "Only the 1 V supply and its return cross here, about 1 kA in "
                      "total; the 48 V input never does — it enters the regulator from below.",
                      FS + 2, fill=F.Z2, weight="bold", halo=False))
    out.append(stamp(24, 82, f"SCHEMATIC MAGNIFICATION — dimensions from the spec; "
                     f"{WIN_TSV_UM:g} of the {t_sub:g} µm TSV shown; landing pads not resolved "
                     "in the model", FS))
    y_ind = 790.0
    y_rdl_bot = y_ind - 46
    y_rdl_top = y_rdl_bot - t_rdl * k
    y_cap_top = y_rdl_top - h_cap * k             # the solder cap wets the regulator RDL
    y_cu_top = y_cap_top - h_cu * k               # the Cu pillar rises to the substrate pad
    y_pad_top = y_cu_top - 4 * k                  # landing pad (schematic)
    y_sub_top = y_pad_top - WIN_TSV_UM * k
    out.append(F.rect(X(0), y_rdl_bot, win * k, y_ind - y_rdl_bot, F.MAT["inductor"], F.INK, 0.8))
    out.append(F.text(X(win / 2), y_rdl_bot + 29, "regulator: inductors + output capacitors",
                      FS + 1, "middle", "bold", "#ffffff", halo=False))
    out.append(F.rect(X(0), y_rdl_top, win * k, y_rdl_bot - y_rdl_top, F.MAT["rdl"], F.INK, 0.8))
    out.append(F.rect(X(0), y_cu_top, win * k, y_rdl_top - y_cu_top, F.MAT["fill"], F.INK, 0.6))
    out.append(F.rect(X(0), y_sub_top, win * k, y_pad_top - y_sub_top, F.MAT["silicon"], F.INK,
                      0.8))
    for i in range(2):
        xc = (i + 0.5) * tsv_p
        pol = "VDD" if i == 0 else "GND"
        out.append(F.rect(X(xc - tsv_d / 2), y_sub_top, tsv_d * k, y_pad_top - y_sub_top,
                          F.MAT["tsv"], F.INK, 0.6, attrs(data_tsv=pol)))
        out.append(F.rect(X(xc - tsv_p / 2 + 2), y_pad_top, (tsv_p - 4) * k, y_cu_top - y_pad_top,
                          F.MAT["rdl"], F.INK, 0.5, attrs(data_landing_pad=pol)))
        out.append(F.text(X(xc), y_sub_top + 42, f"{pol} TSV", FS + 2, "middle", "bold",
                          "#ffffff", halo=False))
        for j in (-1, 1):                        # 2 of the 2 x 2 pillars under each TSV
            px_ = xc + j * pitch / 2
            out.append(F.rect(X(px_ - d / 2), y_cu_top, d * k, h_cu * k, PILLAR, F.INK, 0.6,
                              attrs(data_pillar=pol)))
            out.append(F.rect(X(px_ - d / 2) - 3, y_cap_top, d * k + 6, h_cap * k,
                              F.MAT["solder"], F.INK, 0.6, 'rx="8" ' + attrs(data_cap=pol)))
            kk = "1v" if pol == "VDD" else "ret"
            ya, yb = (y_rdl_top - 6, y_sub_top + 70) if pol == "VDD" else \
                (y_sub_top + 70, y_rdl_top - 6)
            out.append(arrow([(X(px_), ya), (X(px_), yb)], kk, 3.0))
    xr = X(win) + 34

    def dim(y_a, y_b, txt, at=None):
        out.append(poly([(xr, y_a), (xr + 11, y_a)], F.INK, 1.0))
        out.append(poly([(xr, y_b), (xr + 11, y_b)], F.INK, 1.0))
        out.append(poly([(xr + 5.5, y_a), (xr + 5.5, y_b)], F.INK, 1.2))
        lines = wrap(txt, Wc - xr - 42, FS + 1)
        yc = (y_a + y_b) / 2 if at is None else at
        for j, ln in enumerate(lines):
            out.append(F.text(xr + 21, yc + 5 + (j - (len(lines) - 1) / 2) * 18,
                              ln, FS + 1, halo=False))
    dim(y_sub_top, y_pad_top, f"Si package substrate: 1 V VDD and GND TSVs, Ø{tsv_d:g} µm at "
        f"{tsv_p:g} µm pitch, {t['n_per_cell']} per cell", at=y_pad_top - 42)
    dim(y_pad_top, y_cu_top, "TSV landing pads (schematic)")
    dim(y_cu_top, y_cap_top, f"Cu pillar {h_cu:g} µm tall, Ø{d:g} µm, {pitch:g} µm pitch")
    dim(y_cap_top, y_rdl_top, f"solder cap {h_cap:g} µm; underfill between the pillars")
    dim(y_rdl_top, y_rdl_bot, f"regulator 1 V output / attach RDL, {t_rdl:g} µm")
    facts = [f"{att.get('bumps_per_rail_per_cell')} pillars per rail in each {side:.2f} mm cell "
             f"(VDD/GND checkerboard): about {round((tsv_p / pitch) ** 2):d} under every TSV",
             f"1 kA / {a['cells']['n']} cells / {att.get('bumps_per_rail_per_cell')} ≈ "
             f"{1e3 * i_pillar:.0f} mA per pillar; no current-density allowable is claimed",
             f"geometry from Au et al., ECTC 2016 (Ø{d:g} µm Cu pillars at {pitch:g} µm pitch, "
             f"{h_cap:g} µm cap): a CLOSE ANALOG, not this package",
             f"height = the {att.get('h_total_um'):g} µm attach allowance of the clearance "
             "budget; other heights and all-solder bumps are class-B cases"]
    yf = 200.0
    for j, ln in enumerate(facts):
        for jj, l2 in enumerate(wrap(ln, Wc - xr - 60, FS + 1)):
            out.append(F.text(xr + 24, yf + j * 48 + jj * 18, ("• " if jj == 0 else "   ") + l2,
                              FS + 1, halo=False))
    lg = [("1v", None, "1 V supply (up the VDD pillars)"),
          ("ret", None, "1 V return (down the GND pillars)"),
          ("fill", PILLAR, "Cu pillar"), ("fill", F.MAT["solder"], "solder cap"),
          ("fill", F.MAT["fill"], "underfill"), ("fill", F.MAT["tsv"], "Cu TSV")]
    out.append(legend_block(xr, 830, lg, 3, 270))
    out.append(F.svg_close())
    return "".join(out)


# =================================================================== main
def build_all(spec=None) -> dict:
    """Every figure as text (SVG) -- pure, so the tests can re-render and compare."""
    spec = spec or load_spec()
    return {"Z1": cross_section_svg(spec, "Z1"), "Z2": cross_section_svg(spec, "Z2"),
            "pair": comparison_svg(spec), "exploded_svg": exploded_svg(spec),
            "cell": cell_zoom_svg(spec), "power_path": power_path_svg(spec),
            "power_path_48": power_path_svg(spec, "48"), "power_path_1v": power_path_svg(spec, "1v"),
            "attach": attach_detail_svg(spec)}


def main():
    spec = load_spec()
    figs = build_all(spec)
    FIGS.mkdir(parents=True, exist_ok=True)
    for k in ("Z1", "Z2", "pair", "cell", "power_path", "power_path_48", "power_path_1v",
              "attach"):
        OUT[k].write_text(figs[k])
        print("wrote", OUT[k].relative_to(R))
    png = render_png(figs["exploded_svg"], 1600)
    png = _png_with_text(png, "Description",
                         f"{STAMP}. Z1/Z2 exploded stacks; layer order from "
                         f"architecture_geometry.json sha256 {spec['sha256']}")
    OUT["exploded"].write_bytes(png)
    print("wrote", OUT["exploded"].relative_to(R))


if __name__ == "__main__":
    main()
