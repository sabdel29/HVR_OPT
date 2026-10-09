#!/usr/bin/env python3
"""Layout engine for the SK hynix deck. Content lives in deck_content.py."""
from __future__ import annotations
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

HERE = Path(__file__).resolve().parent
FIGS = HERE / "figs"

W, H = 13.3333, 7.5
MARG = 0.45
CW = W - 2 * MARG                      # content width
TOP = 1.42                             # top of the content area
BOT = 6.98                             # bottom of the content area

BLU = RGBColor(0x00, 0x72, 0xB2)
ORA = RGBColor(0xD5, 0x5E, 0x00)
GRN = RGBColor(0x00, 0x9E, 0x73)
RED = RGBColor(0xC1, 0x12, 0x1F)
PUR = RGBColor(0x7B, 0x5E, 0xA7)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GRY = RGBColor(0x5A, 0x5A, 0x5A)
LGY = RGBColor(0x8A, 0x8A, 0x8A)
WHT = RGBColor(0xFF, 0xFF, 0xFF)
FILL = {"BLU": RGBColor(0xEC, 0xF4, 0xFA), "ORA": RGBColor(0xFD, 0xF2, 0xEA),
        "GRN": RGBColor(0xEB, 0xF7, 0xF3), "RED": RGBColor(0xFD, 0xEE, 0xEE),
        "GRY": RGBColor(0xF2, 0xF2, 0xF2),
        "PUR": RGBColor(0xF4, 0xF1, 0xF9)}
ACC = {"BLU": BLU, "ORA": ORA, "GRN": GRN, "RED": RED, "GRY": GRY, "PUR": PUR}

# Build log: every slide appends one record so PRESENTATION_TIMING.md,
# the source audit and the claim matrix are generated from the real deck.
LOG = []


def log_new(kind):
    LOG.append({"kind": kind, "title": None, "kicker": None,
                "figures": [], "takeaway": None, "notes": "",
                "tables": 0, "bullets": 0})
    return LOG[-1]


def _tf(shape, size, bold=False, color=INK, align=PP_ALIGN.LEFT, space=1.0):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = space
    r = p.add_run()
    r.font.size = Pt(size); r.font.bold = bold
    r.font.color.rgb = color; r.font.name = "Calibri"
    return tf, p, r


def textbox(s, text, left, top, width, height, size, **kw):
    sh = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf, p, r = _tf(sh, size, **kw)
    r.text = text
    return sh


def chrome(s, title, kicker=None, accent="GRY", page=None, tag=None):
    """Accent bar, kicker, title, footer."""
    if LOG:
        LOG[-1]["title"] = title; LOG[-1]["kicker"] = kicker
        LOG[-1]["accent"] = accent
    col = ACC[accent]
    bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(W), Inches(0.10))
    bar.fill.solid(); bar.fill.fore_color.rgb = col; bar.line.fill.background()
    bar.shadow.inherit = False
    if kicker:
        textbox(s, kicker.upper(), MARG, 0.17, CW, 0.30, 12.5, bold=True, color=col)
    textbox(s, title, MARG, 0.47, CW, 0.82, 26, bold=True, color=INK, space=0.92)
    if page is not None:
        textbox(s, str(page), W - MARG - 0.9, 7.03, 0.9, 0.30, 11,
                color=LGY, align=PP_ALIGN.RIGHT)
    if tag:
        textbox(s, tag, MARG, 7.03, 9.5, 0.30, 11, color=LGY)


def figure(s, name, top=None, maxh=None, maxw=None):
    """Place a PNG centred, scaled to fit, never upscaled past its native size."""
    if name.startswith("p_") and (FIGS / "deck" / name).exists():
        name = "deck/" + name          # slide supplies the title
    p = FIGS / name
    iw, ih = Image.open(p).size
    native_w = iw / 200.0                      # figures are saved at 200 dpi
    native_h = ih / 200.0
    top = TOP if top is None else top
    maxw = (CW if maxw is None else maxw)
    maxh = ((BOT - top) if maxh is None else maxh)
    if LOG:
        LOG[-1]["figures"].append(name)
    sc = min(maxw / native_w, maxh / native_h, 1.0)
    w, h = native_w * sc, native_h * sc
    s.shapes.add_picture(str(p), Inches((W - w) / 2), Inches(top),
                         Inches(w), Inches(h))
    return top + h, sc


def takeaway(s, text, accent="GRY", top=None, height=0.66, size=16.5):
    if LOG:
        LOG[-1]["takeaway"] = text
    top = (BOT - height) if top is None else top
    box = s.shapes.add_shape(5, Inches(MARG), Inches(top), Inches(CW), Inches(height))
    box.fill.solid(); box.fill.fore_color.rgb = FILL[accent]
    box.line.color.rgb = ACC[accent]; box.line.width = Pt(1.25)
    box.shadow.inherit = False
    tf = box.text_frame
    tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.16)
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; p.line_spacing = 0.95
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = True
    r.font.color.rgb = INK; r.font.name = "Calibri"
    return box


def bullets(s, items, left=MARG, top=None, width=None, size=19, accent="GRY",
            gap=0.30):
    """items: str, or (text, level) with level 0/1."""
    top = TOP + 0.10 if top is None else top
    width = CW if width is None else width
    if LOG:
        LOG[-1]["bullets"] += len(items)
    sh = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width),
                              Inches(BOT - top - 0.1))
    tf = sh.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    first = True
    for it in items:
        txt, lvl = (it, 0) if isinstance(it, str) else it
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.line_spacing = 1.12
        p.space_after = Pt(gap * 72 * (0.55 if lvl else 1.0))
        r = p.add_run()
        r.text = ("\u2022  " if lvl == 0 else "\u2013  ") + txt
        r.font.size = Pt(size if lvl == 0 else size - 2.5)
        r.font.color.rgb = INK if lvl == 0 else GRY
        r.font.name = "Calibri"
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(0.30 if lvl == 0 else 0.72))))
        pPr.set("indent", str(int(Inches(-0.30))))
    return sh


def table(s, rows, left=None, top=None, width=None, size=14, hdr=True,
          accent="GRY", colw=None):
    top = TOP + 0.08 if top is None else top
    width = CW if width is None else width
    left = MARG if left is None else left
    if LOG:
        LOG[-1]["tables"] += 1
    nr, nc = len(rows), len(rows[0])
    h = min(0.42 * nr, BOT - top - 0.05)
    gt = s.shapes.add_table(nr, nc, Inches(left), Inches(top),
                            Inches(width), Inches(h)).table
    if colw:
        tot = sum(colw)
        for j, cwj in enumerate(colw):
            gt.columns[j].width = Emu(int(Inches(width) * cwj / tot))
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = gt.cell(i, j)
            c.text = ""
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.02)
            tf = c.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run(); r.text = str(val)
            r.font.size = Pt(size); r.font.name = "Calibri"
            r.font.bold = bool(hdr and i == 0)
            r.font.color.rgb = WHT if (hdr and i == 0) else INK
            c.fill.solid()
            c.fill.fore_color.rgb = (ACC[accent] if (hdr and i == 0)
                                     else (WHT if i % 2 else FILL[accent]))
    return gt


def notes(s, text):
    if LOG:
        LOG[-1]["notes"] = text.strip()
    s.notes_slide.notes_text_frame.text = text.strip()


def new(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def deck():
    prs = Presentation()
    prs.slide_width = Inches(W); prs.slide_height = Inches(H)
    return prs
