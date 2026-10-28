"""Annotated crops of the REAL AEDT session exports (tool_evidence/*/01_geometry*.png).

For every screenshot:
  * crop = bounding box of all non-background pixels (model, Ansys mark, axis triad,
    ruler, CS label) plus a small pad, so only empty margin is removed and the tool
    stays identifiable;
  * the cropped AEDT pixels are copied unchanged (RGBA, including AEDT's own partial
    alpha). A title band above, a key band below and -- only where a label does not fit
    in the screenshot's own margin -- white side bands are added OUTSIDE the screenshot;
  * labels are drawn on a separate overlay layer and composited only where the overlay
    is non-transparent: every other screenshot pixel is bit-identical to the original,
    which is verified and recorded;
  * every label comes from setup.json (or, for 'adiabatic sides', the README.md) in the
    same folder. Where those files do not say where something is, nothing is labelled.
    Label anchors use the orthographic isometric projection of the AEDT view, calibrated
    on the model's own silhouette in the screenshot (scale and offset fitted, residual
    recorded).

Output: <stage>/02_annotated[_kx|_kz].png + .json beside it.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
import figstyle as FS                                                # noqa: E402

EV = R / "presentation" / "prelim_hvr" / "tool_evidence"
FONT_R = "/usr/share/fonts/google-noto/NotoSans-Regular.ttf"
FONT_B = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"
HEAD = 92
S6, S2 = math.sqrt(6.0), math.sqrt(2.0)
C_HEAT, C_COOL, C_BC, C_MAT = FS.OPEN, FS.Z1, FS.ACCENT, FS.INK
SIZE = 23
GAP = 14


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_D = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def wrap(text, f, width):
    words, lines, cur = text.split(" "), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if _D.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    return lines + ([cur] if cur else [])


# ------------------------------------------------------------------ geometry ----
def nonwhite(a):
    return a[..., :3].min(axis=2) < 245


def crop_box(a, pad=10):
    ys, xs = np.nonzero(nonwhite(a))
    h, w = a.shape[:2]
    return (max(int(xs.min()) - pad, 0), max(int(ys.min()) - pad, 0),
            min(int(xs.max()) + pad + 1, w), min(int(ys.max()) + pad + 1, h))


def model_extremes(a):
    m = nonwhite(a)
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    sizes = ndi.sum(m, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    ys, xs = np.nonzero(lab == k)
    return {"u_left": int(xs.min()), "u_right": int(xs.max()),
            "v_top": int(ys.min()), "v_bottom": int(ys.max()), "pixels": int(sizes[k - 1])}


class Iso:
    """AEDT default isometric view: viewer along (+1,-1,+1); +x right-down, +y right-up.
    u = cu + s (x + y)/sqrt2 ;  v = cv - s (-x + y + 2 z)/sqrt6   (pixels, mm)."""

    def __init__(self, rows, rhs):
        A, b = np.array(rows, float), np.array(rhs, float)
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        self.cu, self.cv, self.s = map(float, sol)
        self.residual_px = [float(x) for x in A @ sol - b]

    def __call__(self, x, y, z):
        return (self.cu + self.s * (x + y) / S2, self.cv - self.s * (-x + y + 2 * z) / S6)


def iso_box(ext, x0, x1, y0, y1, z0, z1, use=("u_left", "u_right", "v_top", "v_bottom")):
    eq = {"u_left": ([1, 0, (x0 + y0) / S2], ext["u_left"]),
          "u_right": ([1, 0, (x1 + y1) / S2], ext["u_right"]),
          "v_top": ([0, 1, -(-x0 + y1 + 2 * z1) / S6], ext["v_top"]),
          "v_bottom": ([0, 1, -(-x1 + y0 + 2 * z0) / S6], ext["v_bottom"])}
    return Iso([eq[k][0] for k in use], [eq[k][1] for k in use])


# ------------------------------------------------------------------ labels ------
@dataclass
class Label:
    lines: list
    color: str
    side: str                      # 'L' (right-aligned to the stack column), 'R', 'free'
    anchor: tuple | None = None    # ORIGINAL-image (u, v) the leader points at
    pref_v: float | None = None    # preferred vertical centre, original v
    pos: tuple | None = None       # free labels: original-image top-left (u, v)
    bracket: tuple | None = None   # (u, v0, v1) original coords
    source: list = field(default_factory=list)
    fonts: list = field(default_factory=list)
    w: float = 0
    h: float = 0

    def measure(self):
        self.fonts = [font(SIZE, True)] + [font(SIZE - 3)] * (len(self.lines) - 1)
        self.w = max(_D.textlength(t, font=f) for t, f in zip(self.lines, self.fonts))
        self.h = sum(f.size + 6 for f in self.fonts)


def stack(labels, lo, hi):
    """1-D non-overlapping vertical placement; returns tops (canvas y)."""
    order = sorted(range(len(labels)), key=lambda i: labels[i][0])
    tops = {}
    prev = lo - GAP
    for i in order:
        c, h = labels[i]
        t = max(c - h / 2, prev + GAP, lo)
        tops[i] = t
        prev = t + h
    nxt = hi + GAP
    for i in reversed(order):
        c, h = labels[i]
        if tops[i] + h > nxt - GAP:
            tops[i] = nxt - GAP - h
        nxt = tops[i]
    return [tops[i] for i in range(len(labels))]


def render(a, box, ext, labels, title, subtitle, key_lines):
    x0, y0, x1, y1 = box
    crop = a[y0:y1, x0:x1].copy()
    h, w = crop.shape[:2]
    for lb in labels:
        lb.measure()
    # side bands only where the screenshot's own margin is too narrow
    left_col = (ext["u_left"] - x0) - 14 - 18 if ext else 0
    right_col = (ext["u_right"] - x0) + 40 if ext else w
    need_l = max([lb.w for lb in labels if lb.side == "L"] + [0]) + 12
    need_r = max([lb.w for lb in labels if lb.side == "R"] + [0]) + 12
    lp = int(max(0, need_l - left_col)) if any(lb.side == "L" for lb in labels) else 0
    rp = int(max(0, need_r - (w - right_col))) if any(lb.side == "R" for lb in labels) else 0
    W = w + lp + rp
    keys = [ln for para in key_lines for ln in wrap(para, font(18), W - 28)]
    foot = 20 + 25 * len(keys)
    Hc = HEAD + h + foot
    canvas = np.full((Hc, W, 4), 255, np.uint8)
    canvas[HEAD:HEAD + h, lp:lp + w] = crop             # AEDT pixels, bit-identical

    def P(uv):
        return (uv[0] - x0 + lp, uv[1] - y0 + HEAD)

    ov = Image.new("RGBA", (W, Hc), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    white = (255, 255, 255, 255)
    placed = []
    lo, hi = HEAD + 8, HEAD + h - 8
    for side in ("L", "R"):
        grp = [lb for lb in labels if lb.side == side]
        if not grp:
            continue
        lo_s = HEAD + max(0, 64 - y0) if side == "R" else lo     # keep clear of the mark
        tops = stack([(P((0, lb.pref_v))[1], lb.h) for lb in grp], lo_s, hi)
        for lb, t in zip(grp, tops):
            if side == "L":
                xr = lp + left_col
                placed.append((lb, xr - lb.w, t))
            else:
                placed.append((lb, lp + right_col, t))
    for lb in labels:
        if lb.side == "free":
            u, v = P(lb.pos)
            placed.append((lb, u, v))
    boxes = []
    for lb, x, t in placed:
        if lb.bracket:
            u, v0, v1 = lb.bracket
            (bx, a_), (_, b_) = P((u, v0)), P((u, v1))
            for wd, c in ((5, white), (2, rgb(FS.MUTED))):
                d.line([(bx + 10, a_), (bx, a_), (bx, b_), (bx + 10, b_)], fill=c, width=wd)
            ym = t + lb.fonts[0].size / 2 + 4
            for wd, c in ((5, white), (2, rgb(FS.MUTED))):
                d.line([(x + lb.w + 4, ym), (bx - 2, (a_ + b_) / 2)], fill=c, width=wd)
        if lb.anchor is not None:
            ax, ay = P(lb.anchor)
            left_of = ax > x + lb.w
            ex = x + lb.w + 6 if left_of else x - 6
            ey = t + lb.fonts[0].size / 2 + 4
            if x - 6 <= ax <= x + lb.w + 6:
                ex, ey = ax, (t + lb.h + 4 if ay > t + lb.h else t - 4)
            for wd, c in ((5, white), (2, rgb(lb.color))):
                d.line([(ex, ey), (ax, ay)], fill=c, width=wd)
            d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=rgb(lb.color), outline=white,
                      width=2)
        yy = t
        for txt, f in zip(lb.lines, lb.fonts):
            xx = x + (lb.w - _D.textlength(txt, font=f) if lb.side == "L" else 0)
            d.text((xx, yy), txt, font=f, fill=rgb(lb.color), stroke_width=4,
                   stroke_fill=white)
            yy += f.size + 6
        boxes.append((x, t, x + lb.w, t + lb.h))
    o = np.asarray(ov).astype(np.float64)
    al = o[..., 3:4] / 255.0
    touched = o[..., 3] > 0
    blend = o[..., :3] * al + canvas[..., :3] * (1 - al)
    res = canvas.copy()
    res[..., :3] = np.where(touched[..., None], np.rint(blend), canvas[..., :3]).astype(np.uint8)
    res[..., 3] = np.where(touched, 255, canvas[..., 3])
    img = Image.fromarray(res, "RGBA")
    dd = ImageDraw.Draw(img)
    dd.text((14, 10), title, font=font(27, True), fill=rgb(FS.INK))
    dd.text((14, 50), subtitle, font=font(19), fill=rgb(FS.MUTED))
    dd.line([(0, HEAD - 1), (W, HEAD - 1)], fill=rgb(FS.LINE), width=1)
    dd.line([(0, HEAD + h), (W, HEAD + h)], fill=rgb(FS.LINE), width=1)
    y = HEAD + h + 10
    for ln in keys:
        dd.text((14, y), ln, font=font(18), fill=rgb(FS.MUTED))
        y += 25
    # verification: screenshot pixels not under the overlay are unchanged
    region = res[HEAD:HEAD + h, lp:lp + w]
    under = touched[HEAD:HEAD + h, lp:lp + w]
    same = bool(np.all(region[~under] == crop[~under]))
    clip = [b for b in boxes if b[0] < 0 or b[2] > W or b[1] < HEAD or b[3] > HEAD + h]
    coll = [(i, j) for i in range(len(boxes)) for j in range(i + 1, len(boxes))
            if boxes[i][0] < boxes[j][2] and boxes[j][0] < boxes[i][2]
            and boxes[i][1] < boxes[j][3] and boxes[j][1] < boxes[i][3]]
    return img, {"overlay_fraction_of_crop": float(under.mean()),
                 "untouched_pixels_identical_to_original": same,
                 "label_box_collisions": coll, "labels_clipped": len(clip),
                 "side_bands_px": {"left": lp, "right": rp},
                 "screenshot_offset_in_output_px": [lp, HEAD]}


# ------------------------------------------------------------------ stages ------
def column_stage(stage):
    d = EV / stage
    spec = json.loads((d / "setup.json").read_text())
    readme = (d / "README.md").read_text()
    assert "adiabatic sides" in readme
    a = np.asarray(Image.open(d / "01_geometry.png").convert("RGBA"))
    p, t = spec["pitch_mm"], spec["tile_mm"]
    L = spec["layers"]
    zmin, zmax = L[0]["z0"], L[-1]["z1"]
    ext = model_extremes(a)
    iso = iso_box(ext, -p / 2, p / 2, -p / 2, p / 2, zmin, zmax)
    box = crop_box(a)
    labels = []

    groups = []
    for i, ly in enumerate(L):
        n = ly["name"]
        key = ("board" if n == "board" else "bga" if n == "bga" else
               "sub" if n in ("sub_lower", "tile_band") else "conv" if "conv" in n else
               "die" if n == "die" else "tim" if n == "tim" else "thin")
        if groups and groups[-1][0] == key:
            groups[-1][2] = ly["z1"]
            groups[-1][3].append(i)
        else:
            groups.append([key, ly["z0"], ly["z1"], [i]])
    names = {"board": "board", "bga": "BGA layer", "sub": "substrate",
             "conv": "converter tiers", "die": "die (silicon)", "tim": "TIM"}

    def detail(key, ix):
        mt = sorted({L[i]["mat_tile"] for i in ix})
        mg = sorted({L[i]["mat_gap"] for i in ix})
        if mt == mg and len(mt) == 1:
            return [f"material: {mt[0]}"]
        if key == "conv":
            return ["tile: " + ", ".join(mt[:2]) + ",", ", ".join(mt[2:]) +
                    "  ·  gap: " + ", ".join(mg)]
        return [f"tile: {', '.join(mt)}  ·  gap: {', '.join(mg)}"]

    ub = ext["u_left"] - 14
    for key, z0, z1, ix in groups:
        if key == "thin":
            continue
        v0, v1 = iso(-p / 2, -p / 2, z1)[1], iso(-p / 2, -p / 2, z0)[1]
        th = (z1 - z0) * 1e3
        ths = f"{th:.0f} µm" if th < 1000 else f"{th / 1e3:.2f} mm"
        labels.append(Label([f"{names[key]} · {ths}"] + detail(key, ix), C_MAT, "L",
                            pref_v=0.5 * (v0 + v1), bracket=(ub, v0, v1),
                            source=[f"setup.json layers[{i}] ({L[i]['name']}): z0, z1, "
                                    "mat_tile, mat_gap" for i in ix]))
    labels.append(Label(["COOLED FACE: top of TIM",
                         f"film h = {spec['h_top']:,.0f} W/m²K".replace(",", " "),
                         f"to fluid at {spec['T_fluid_C']:.2f} °C"], C_COOL, "R",
                        anchor=iso(p / 4, p / 4, zmax), pref_v=iso(p / 4, p / 4, zmax)[1] - 60,
                        source=["setup.json h_top", "setup.json T_fluid_C",
                                "setup.json layers[-1] (tim) z1"]))
    die = next(ly for ly in L if ly["name"] == "die")
    srcs = spec["sources"]
    die_w = sum(s["W"] for s in srcs if s["layers"] == ["die"])
    zd = 0.5 * (die["z0"] + die["z1"])
    labels.append(Label(["HEAT INPUT: die layer", f"{die_w:.2f} W in the whole die volume"],
                        C_HEAT, "R", anchor=iso(p / 2, 0.0, zd), pref_v=iso(p / 2, 0, zd)[1],
                        source=["setup.json sources[layers == ['die']].W",
                                "setup.json layers (die) z0, z1"]))
    conv = [ly for ly in L if "conv" in ly["name"]]
    zc = 0.5 * (min(c["z0"] for c in conv) + max(c["z1"] for c in conv))

    def nice(s):
        n = s["layers"][0]
        return ("GaN HS" if "gan_hs" in n else "GaN LS" if "gan_ls" in n else
                "inductor + C_out" if "inductor" in n else "flying caps" if "caps" in n
                else "RDL tiers" if "rdl" in n else "substrate" if n == "sub_lower"
                else "microbumps" if n == "interface" else n)
    tile_src = sorted([s for s in srcs if s["in_tile"]], key=lambda s: -s["W"])
    big = [f"{nice(s)} {s['W']:.2f} W" for s in tile_src if s["W"] >= 0.02]
    small = sum(s["W"] for s in tile_src if s["W"] < 0.02)
    lines = ["HEAT INPUT: converter tile"] + [" · ".join(big[i:i + 2])
                                              for i in range(0, len(big), 2)]
    if small > 0:
        lines.append(f"+ {small:.3f} W in smaller tile tiers")
    labels.append(Label(lines, C_HEAT, "R", anchor=iso(t / 2, 0.0, zc),
                        pref_v=iso(t / 2, 0.0, zc)[1],
                        source=["setup.json sources[in_tile == true].W, layers",
                                "setup.json tile_mm"]))
    zs = 0.5 * (zmin + min(c["z0"] for c in conv)) if spec["bottom_film"] else \
        0.5 * (zmin + zc)
    labels.append(Label(["SIDES: adiabatic", "(README.md in this folder)"], C_BC, "R",
                        anchor=iso(p / 2, -p / 4, zs), pref_v=iso(p / 2, -p / 4, zs)[1],
                        source=["README.md: 'adiabatic sides'"]))
    bot = iso(p / 2, 0.0, zmin)
    if spec["bottom_film"]:
        labels.append(Label(["UNDERSIDE (hidden): film",
                             f"h = {spec['h_bot']:.0f} W/m²K to {spec['T_amb_C']:.0f} °C"],
                            C_COOL, "R", anchor=bot, pref_v=bot[1],
                            source=["setup.json bottom_film = true", "setup.json h_bot",
                                    "setup.json T_amb_C"]))
    else:
        labels.append(Label(["UNDERSIDE (hidden): no film", "(bottom_film = false)"],
                            C_BC, "R", anchor=bot, pref_v=bot[1],
                            source=["setup.json bottom_film = false"]))
    thin = [L[i]["name"] for g in groups if g[0] == "thin" for i in g[3]]
    om = spec.get("omitted_sources", [])
    title = (f"Ansys AEDT 2026 R1 Mechanical · matched unit cell {spec['arch']} "
             f"{spec['scenario'].replace('_', '-')} · annotated crop")
    sub = ("Real session export (native ExportModelImageToFile); cropped only. "
           "Labels are an overlay drawn from setup.json in this folder.")
    keys = [f"Red = heat input · blue = cooled face · purple = boundary condition · "
            f"black = material. Cell pitch {p:.3f} mm with the {t:.3f} mm converter tile "
            f"at its centre; Q_cell = {spec['Q_cell_W']:.2f} W.",
            "Thin 10 µm tiers (" + ", ".join(sorted({n.split('_', 1)[-1] if 'conv' in n
                                                     else n for n in thin}))
            + ", and the RDL tiers inside the converter stack) are below one pixel here and "
              "are not bracketed." + (" Source omitted from this cell (setup.json "
                                     "omitted_sources): " + ", ".join(
                                         f"{s['layers'][0]} {s['W']:.3f} W" for s in om)
                                     + "." if om else ""),
            "No mesh is visible in this export, so none is labelled."]
    img, meta = render(a, box, ext, labels, title, sub, keys)
    meta["thin_layers_not_bracketed"] = thin
    return img, meta, labels, box, iso, ext


def bilayer_stage(stage="mech_bilayer"):
    d = EV / stage
    spec = json.loads((d / "setup.json").read_text())
    a = np.asarray(Image.open(d / "01_geometry.png").convert("RGBA"))
    assert "quarter 10 x 10 mm" in spec["geometry"]
    assert "Si 0.3 mm on organic 0.3 mm" in spec["geometry"]
    assert "symmetry x=0, y=0" in spec["supports"] and "0.1 mm patch" in spec["supports"]
    Lq, h1, h2 = 5.0, 0.3, 0.3          # quarter of 10 mm; organic below, Si on top
    ext = model_extremes(a)
    # AEDT's global-axis arrow sits on the left corner: fit on the other three extremes
    iso = iso_box(ext, 0, Lq, 0, Lq, 0, h1 + h2, use=("u_right", "v_top", "v_bottom"))
    box = crop_box(a)
    src_g, src_s, src_l = ["setup.json geometry"], ["setup.json supports"], ["setup.json load"]
    o = iso(0, 0, 0)                     # origin = plate centre (left corner)
    top = iso(0, Lq, h1 + h2)              # top corner
    rf = iso(Lq, Lq / 2, 0)                # middle of the free x = 5 mm face, bottom edge
    # each label sits in the empty screenshot region next to its feature
    labels = [
        Label(["SYMMETRY: x = 0", "(back-left face, hidden;", "its top edge marked)"], C_BC,
              "free", anchor=iso(0.0, 2.2, h1 + h2), pos=(o[0] - 125, top[1] + 35),
              source=src_s),
        Label(["LOAD: uniform ΔT = 100 K", "on both layers (no heat input,",
               "no cooled face)"], C_HEAT, "free", anchor=iso(Lq / 2, Lq / 2, h1 + h2),
              pos=(top[0] + 190, top[1] - 5), source=src_l),
        # Si is the upper layer: its leader lands on the top face, so it never crosses
        # the organic band; organic is reached from below on the free x = 5 mm face
        Label(["Si · 0.3 mm (upper layer;", "its top face)"], C_MAT, "free",
              anchor=iso(0.84 * Lq, 0.88 * Lq, h1 + h2), pos=(top[0] + 348, top[1] + 125),
              source=src_g),
        Label(["organic · 0.3 mm (lower layer)"], C_MAT, "free",
              anchor=iso(Lq, 0.64 * Lq, 0.4 * h2), pos=(rf[0] + 82, rf[1] - 21),
              source=src_g),
        Label(["Z-RESTRAINED PATCH (0.1 mm)", "at the plate centre: origin,",
               "on the underside (hidden)"], C_BC, "free", anchor=o,
              pos=(o[0] - 135, o[1] + 140),
              source=src_s + ["setup.json geometry: quarter plate, so the plate centre is "
                              "the corner where the symmetry planes x = 0 and y = 0 meet"]),
        Label(["SYMMETRY: y = 0", "(this front-left face)"], C_BC, "free",
              anchor=iso(2.6, 0.0, 0.5 * (h1 + h2)), pos=(o[0] + 205, o[1] + 255),
              source=src_s),
    ]
    title = ("Ansys AEDT 2026 R1 Mechanical (structural) · silicon-on-organic bilayer · "
             "annotated crop")
    sub = ("Real session export (native ExportModelImageToFile); cropped only. "
           "Labels are an overlay drawn from setup.json in this folder.")
    keys = ["Purple = boundary condition · red = load · black = material. Quarter of a "
            "10 x 10 mm plate (5 x 5 mm modelled), Si 0.3 mm on organic 0.3 mm.",
            "The axis arrows at the left corner are AEDT's global coordinate system; the "
            "plate centre is that corner. No mesh is visible in this export, so none is "
            "labelled."]
    img, meta = render(a, box, ext, labels, title, sub, keys)
    return img, meta, labels, box, iso, ext


def rve_stage(stage, src, key):
    d = EV / stage
    spec = json.loads((d / "setup.json").read_text())[key]
    a = np.asarray(Image.open(d / src).convert("RGBA"))
    box = crop_box(a)
    items = [(f"observable: {spec['observable']}", f"setup.json {key}.observable"),
             (f"production model: {spec['production_model']}",
              f"setup.json {key}.production_model"),
             (f"reference: {spec['reference_tool']}", f"setup.json {key}.reference_tool")]
    if spec.get("cu_fraction") is not None:
        items.append((f"Cu fraction {spec['cu_fraction']:.4f}", f"setup.json {key}.cu_fraction"))
    labels = [Label([t], C_MAT, "none", source=[s]) for t, s in items]
    nice = {"tsv_bulk": "single TSV", "tsv_tile_kx": "TSV tile RVE, in-plane (kx) run",
            "tsv_tile_kz": "TSV tile RVE, through-plane (kz) run",
            "rdl_tier_kx": "RDL tier RVE, in-plane (kx) run",
            "rdl_tier_kz": "RDL tier RVE, through-plane (kz) run"}[key]
    title = f"Ansys AEDT 2026 R1 Mechanical · {nice} · annotated crop"
    sub = ("Real session export (native ExportModelImageToFile); cropped only. "
           "Caption drawn from setup.json in this folder.")
    keys = [" · ".join(t for t, _ in items[:2]) + ".",
            " · ".join(t for t, _ in items[2:]) + ".",
            "setup.json does not say which faces carry the source and the sink, nor which "
            "body is which material, so no face, part or boundary is labelled. No mesh is "
            "visible in this export."]
    img, meta = render(a, box, None, [], title, sub, keys)
    return img, meta, labels, box, None, None


JOBS = [("thermal_column_Z1", "01_geometry.png", "02_annotated",
         lambda: column_stage("thermal_column_Z1")),
        ("thermal_column_Z2", "01_geometry.png", "02_annotated",
         lambda: column_stage("thermal_column_Z2")),
        ("mech_bilayer", "01_geometry.png", "02_annotated", lambda: bilayer_stage()),
        ("tsv_bulk", "01_geometry.png", "02_annotated",
         lambda: rve_stage("tsv_bulk", "01_geometry.png", "tsv_bulk")),
        ("tsv_tile_rve", "01_geometry_kx.png", "02_annotated_kx",
         lambda: rve_stage("tsv_tile_rve", "01_geometry_kx.png", "tsv_tile_kx")),
        ("tsv_tile_rve", "01_geometry_kz.png", "02_annotated_kz",
         lambda: rve_stage("tsv_tile_rve", "01_geometry_kz.png", "tsv_tile_kz")),
        ("rdl_tier_rve", "01_geometry_kx.png", "02_annotated_kx",
         lambda: rve_stage("rdl_tier_rve", "01_geometry_kx.png", "rdl_tier_kx")),
        ("rdl_tier_rve", "01_geometry_kz.png", "02_annotated_kz",
         lambda: rve_stage("rdl_tier_rve", "01_geometry_kz.png", "rdl_tier_kz"))]


def main():
    only = set(sys.argv[1:])
    for stage, src, out, fn in JOBS:
        if only and stage not in only:
            continue
        d = EV / stage
        before = sha(d / src)
        img, meta, labels, box, iso, ext = fn()
        img.save(d / f"{out}.png", optimize=True)
        assert sha(d / src) == before                    # the original is never touched
        rec = {"source_image": f"presentation/prelim_hvr/tool_evidence/{stage}/{src}",
               "source_sha256": before,
               "source_size_px": list(Image.open(d / src).size),
               "crop_box_px_xywh": [box[0], box[1], box[2] - box[0], box[3] - box[1]],
               "crop_rule": "bounding box of all non-background pixels (model, Ansys mark, "
                            "axis triad, ruler, CS label) + 10 px pad",
               "bands_added": "title band above and key band below, plus white side bands "
                              "where labels need room; all outside the screenshot",
               "labels": [{"text": " / ".join(lb.lines), "source_fields": lb.source,
                           "kind": {"L": "material stack", "R": "boundary condition / source",
                                    "free": "label", "none": "caption (no position)"}[lb.side]}
                          for lb in labels],
               "setup_json_sha256": sha(d / "setup.json"),
               "verification": meta,
               "generator": "scripts/reference_tools/aedt_annotate_screenshots.py",
               "output_sha256": sha(d / f"{out}.png")}
        if iso is not None:
            rec["projection"] = {"model": "orthographic isometric, viewer along (+1,-1,+1)",
                                 "fitted_px_per_mm": iso.s, "cu_px": iso.cu, "cv_px": iso.cv,
                                 "fit_residual_px": iso.residual_px,
                                 "silhouette_extremes_px": ext}
        (d / f"{out}.json").write_text(json.dumps(rec, indent=2) + "\n")
        print(f"{stage}/{out}.png  overlay {meta['overlay_fraction_of_crop']:.3f}  "
              f"identical {meta['untouched_pixels_identical_to_original']}  "
              f"collisions {meta['label_box_collisions']}  clipped {meta['labels_clipped']}  "
              f"bands {meta['side_bands_px']}")


if __name__ == "__main__":
    main()
