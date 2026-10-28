"""One visual language for every HVR_OPT figure (diagrams, field renders, charts, slides).

Colours: the architecture and status colours are the deck's own (presentation/prelim_hvr/
theme.css); the material and current colours below are used by every diagram so a reader
learns them once. Colour is never the only signal: every coloured element also carries a
label, a line style or a hatch.

SVG helpers write plain SVG 1.1 text (no external library), so a figure is a reviewable
source file and renders identically in Chrome, rsvg-convert and LaTeX (via PDF).
"""
from __future__ import annotations

import html

# ---------------------------------------------------------------- deck colours
INK, MUTED, LINE, BG = "#10151c", "#5a6672", "#d7dde4", "#ffffff"
OK, WARN, OPEN, HIST, ACCENT = "#1a7f37", "#bf8700", "#cf222e", "#8c959f", "#6639ba"
Z1, Z2 = "#1f6feb", "#d1442f"

# ---------------------------------------------------------------- materials
MAT = {
    "pcb": "#4f7f5a",          # laminate + copper planes (IT-968G board)
    "solder": "#b9bec6",       # BGA balls, microbumps
    "silicon": "#9aa5b8",      # power substrate
    "tsv": "#c4783c",          # copper through-silicon vias
    "rdl": "#d9893f",          # 10 um copper redistribution tiers
    "gan": "#6d58a8",          # GaN-on-Si device tiers
    "caps": "#d8b24a",         # flying capacitors
    "inductor": "#8a6a48",     # inductors + output capacitors
    "fill": "#efe6d2",         # underfill / mould between cells
    "die": "#4c5d70",          # compute die
    "tim": "#e8c46a",          # thermal interface material
    "coldplate": "#a9cdea",    # microchannel cold plate (schematic)
    "air": "#ffffff",          # the PCB opening
}
MAT_LABEL = {"pcb": "PCB (18 layers)", "solder": "solder (BGA / microbumps)",
             "silicon": "silicon substrate", "tsv": "Cu TSV field", "rdl": "Cu RDL (10 um)",
             "gan": "GaN device tier", "caps": "flying capacitors",
             "inductor": "inductors + output caps", "fill": "underfill / mould",
             "die": "compute die", "tim": "TIM", "coldplate": "cold plate (schematic)"}

# ---------------------------------------------------------------- currents
I48 = "#e36209"                # 48 V supply
I1V = "#8250df"                # 1 V output
IRET = "#3d464f"               # return (always dashed)
DASH_RET = "7,4"

#: CSS font list: names with spaces MUST be quoted, or Chrome and rsvg-convert reject
#: the whole list and fall back to a serif face (found by the tool-map guard)
FONT = "'Source Sans 3', 'Segoe UI', Arial, Helvetica, sans-serif"


def esc(s):
    return html.escape(str(s), quote=True)


def svg_open(w, h, title, desc="", extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}" {extra}>\n'
            f'<title>{esc(title)}</title><desc>{esc(desc)}</desc>\n'
            f'<defs>{arrow_defs()}</defs>\n'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>\n')


def svg_close():
    return "</svg>\n"


def arrow_defs():
    out = []
    # orient="auto" (SVG 1.1): the SVG 2 value auto-start-reverse is ignored by
    # rsvg-convert 2.42 (/bin), which then draws every arrowhead pointing right
    for name, col in (("a48", I48), ("a1v", I1V), ("aret", IRET), ("aink", INK),
                      ("amuted", MUTED)):
        out.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="8.5" refY="5" '
                   f'markerWidth="7" markerHeight="7" orient="auto">'
                   f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
    out.append('<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
               'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" '
               f'stroke="{MUTED}" stroke-width="1"/></pattern>')
    return "".join(out)


def rect(x, y, w, h, fill, stroke=INK, sw=0.8, extra=""):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>\n')


def text(x, y, s, size=14, anchor="start", weight="normal", fill=INK, halo=True, extra=""):
    """Text with a white halo so it stays legible over any fill."""
    t = esc(s)
    base = (f'x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" {extra}')
    h = (f'<text {base} fill="none" stroke="{BG}" stroke-width="3.5" '
         f'stroke-linejoin="round">{t}</text>') if halo else ""
    return h + f'<text {base} fill="{fill}">{t}</text>\n'


def leader(x0, y0, x1, y1, label, size=13, anchor="start", fill=INK, dot=True):
    """A leader line from a feature (x0, y0) to a label at (x1, y1)."""
    s = (f'<polyline points="{x0:.2f},{y0:.2f} {x1:.2f},{y1:.2f}" fill="none" '
         f'stroke="{MUTED}" stroke-width="1"/>\n')
    if dot:
        s += f'<circle cx="{x0:.2f}" cy="{y0:.2f}" r="2.2" fill="{MUTED}"/>\n'
    dx = 4 if anchor == "start" else -4 if anchor == "end" else 0
    return s + text(x1 + dx, y1 + size * 0.35, label, size, anchor, fill=fill)


def arrow(points, kind="48", sw=2.4, extra=""):
    col, mk = {"48": (I48, "a48"), "1v": (I1V, "a1v"), "ret": (IRET, "aret"),
               "ink": (INK, "aink"), "muted": (MUTED, "amuted")}[kind]
    dash = f' stroke-dasharray="{DASH_RET}"' if kind == "ret" else ""
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{sw}"'
            f'{dash} marker-end="url(#{mk})" stroke-linejoin="round" {extra}/>\n')


def scale_bar(x, y, length_px, label, size=12):
    return (f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x + length_px:.2f}" y2="{y:.2f}" '
            f'stroke="{INK}" stroke-width="2"/>'
            f'<line x1="{x:.2f}" y1="{y - 4:.2f}" x2="{x:.2f}" y2="{y + 4:.2f}" stroke="{INK}"/>'
            f'<line x1="{x + length_px:.2f}" y1="{y - 4:.2f}" x2="{x + length_px:.2f}" '
            f'y2="{y + 4:.2f}" stroke="{INK}"/>\n'
            + text(x + length_px / 2, y - 7, label, size, "middle"))


def legend(x, y, items, size=13, box=14, gap=6, cols=1, col_w=230):
    """items: (kind, colour_or_key, label); kind 'fill' | '48' | '1v' | 'ret' | 'hatch'."""
    out, n = [], len(items)
    per = -(-n // cols)
    for i, (kind, c, lab) in enumerate(items):
        cx = x + (i // per) * col_w
        cy = y + (i % per) * (box + gap)
        if kind == "fill":
            out.append(rect(cx, cy, box, box, MAT.get(c, c), sw=0.8))
        elif kind == "hatch":
            out.append(rect(cx, cy, box, box, "url(#hatch)", sw=0.8))
        else:
            out.append(arrow([(cx, cy + box / 2), (cx + box + 10, cy + box / 2)], kind, 2.2))
        out.append(text(cx + box + (16 if kind in ("48", "1v", "ret") else 6),
                        cy + box * 0.8, lab, size, halo=False))
    return "".join(out)


def stamp(x, y, s, size=13, fill=OPEN):
    """A boxed status stamp, e.g. 'ILLUSTRATIVE -- NOT TO SCALE'."""
    w = 0.56 * size * len(s) + 16
    return (rect(x, y, w, size + 12, "#fff", fill, 1.6)
            + text(x + 8, y + size + 2, s, size, weight="bold", fill=fill, halo=False))
