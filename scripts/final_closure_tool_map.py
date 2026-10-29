"""What software is doing what? -- the tool map of the HVR_OPT final-closure study.

Writes presentation/prelim_hvr/figs/tool_map.svg (1600 x 900 slide, every text >= 16 px)
from the small table below. Tool names, versions and execution status are NOT typed here:
each box lists provenance names, and its version label and its EXECUTED / NOT EXECUTED
stamp are read from research/final_closure/tool_provenance.json.

The build fails loudly if
  * a box names a tool that is not in tool_provenance.json, or the tools sharing a box
    disagree on status;
  * a provenance tool of a mapped lane (inputs, production, references, host platform,
    visualisation, not executed) is missing from the map;
  * presentation/prelim_hvr/tool_intro.json drifts from the provenance (name, status, URL);
  * a file the figure names does not exist;
  * any text line would overflow its box, any text is below 16 px, any two boxes overlap,
    or an arrow runs through a box it does not connect.
`--selftest` feeds each guard a real offending input and requires it to fail.

    python scripts/final_closure_tool_map.py                 # write the SVG
    python scripts/final_closure_tool_map.py --png OUT.png   # also rasterise (rsvg-convert)
    python scripts/final_closure_tool_map.py --selftest
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import figstyle as F                                                # noqa: E402

PROV = R / "research" / "final_closure" / "tool_provenance.json"
INTRO = R / "presentation" / "prelim_hvr" / "tool_intro.json"
OUT = R / "presentation" / "prelim_hvr" / "figs" / "tool_map.svg"
W, H = 1600, 900
MIN_PX = 16
FIT = 1.06                     # head-room for font substitution (metrics are Helvetica's)
MAPPED_LANES = ("inputs", "production", "reference", "platform", "visualisation",
                "not_executed")
#: files the figure names; each must exist
FILES_NAMED = ("research/final_closure/accuracy_speed_matrix.json",
               "presentation/prelim_hvr/HVR_OPT_Prelim.pdf")
RESULTS_GLOB = "research/final_closure/*.json"

# ----------------------------------------------------------------------- layout table
#: lane id, header, x, width. Data flows left to right; "Not executed" is the last lane
#: so that no arrow has to cross it.
LANES = [("inputs", "Inputs & geometry", 20, 290),
         ("production", "Production solvers", 330, 310),
         ("reference", "Independent references", 660, 300),
         ("visualisation", "Visualisation & deck", 980, 300),
         ("not_executed", "Not executed", 1300, 280)]
LANE_TOP, LANE_BOTTOM, HEAD_H = 96, 802, 42
#: box insets from the lane edge: (left, right); the wider side carries a collector line
INSET = {"inputs": (12, 12), "production": (12, 26), "reference": (26, 12),
         "visualisation": (12, 12), "not_executed": (12, 12)}

#: {v0}, {v1}, ... are replaced by version_short of tools[0], tools[1], ...
BOXES = [
    dict(id="gmsh", lane="inputs", y=150, tools=["Gmsh"], title="Gmsh {v0}",
         body=["2-D triangle mesh of the", "wiring sheet, for MOOSE"]),
    dict(id="cfg", lane="inputs", y=284, tools=["In-house package builders + YAML configs"],
         title="YAML configs + builders", body=["Z1, Z2 layers, materials,",
                                                "converter tiles (in-house)"]),
    dict(id="mesh", lane="inputs", y=438, tools=["In-house structured hex mesher (etm.mesh)"],
         title="etm.mesh (in-house)", body=["one brick mesh for both the",
                                            "thermal and structural runs"]),
    dict(id="net", lane="production", y=196,
         tools=["In-house package-network FV solver", "In-house electrical ledger", "SciPy"],
         title="Electrical network + ledger", body=["in-house FV: Z1 48 V RDL",
                                                    "and the BGA-fed control;",
                                                    "ledger: every rail's loss"]),
    dict(id="ccx_t", lane="production", y=366,
         tools=["CalculiX (ccx)", "In-house E-T fixed-point driver"],
         title="CalculiX {v0} · thermal FE", body=["package temperature field,",
                                                         "inside the E-T fixed point"]),
    dict(id="ccx_s", lane="production", y=520, tools=["CalculiX (ccx)"],
         title="CalculiX {v0} · structural", body=["thermoelastic FE, once, on",
                                                         "the converged temperatures"]),
    dict(id="ccx_l", lane="production", y=674, tools=["CalculiX (ccx)"],
         title="CalculiX {v0} · local solder", body=["viscoplastic submodel of",
                                                           "the critical solder joint"]),
    dict(id="moose", lane="reference", y=150,
         tools=["MOOSE heat_transfer module (heat_transfer-opt)"],
         title="MOOSE heat_transfer", body=["open-source FE from INL;",
                                            "independent current + heat",
                                            "re-solves of the FV RDL"]),
    dict(id="aedt", lane="reference", y=304,
         tools=["AEDT Mechanical (thermal, structural)", "PyAEDT (ansys.aedt.core)",
                "Ansys Electronics Desktop 2026 R1"],
         title="Ansys Mechanical", body=["in AEDT {v0}, scripted by", "PyAEDT {v1}: via, layer,",
                                         "unit-cell, bilayer checks"]),
    dict(id="cf", lane="reference", y=479, tools=["Closed-form references (in-house)"],
         title="Closed forms (in-house)", body=["Timoshenko bilayer bending,",
                                                "a hand-check of CalculiX"]),
    dict(id="vtk", lane="visualisation", y=150, tools=["VTK"], title="VTK {v0}",
         body=["visualisation only: renders", "the MOOSE Exodus fields"]),
    dict(id="mpl", lane="visualisation", y=304, tools=["Matplotlib"], title="Matplotlib {v0}",
         body=["draws every chart and field", "image from saved results"]),
    dict(id="deck", lane="visualisation", y=458, tools=["Reveal.js", "Google Chrome (headless)"],
         title="Reveal.js {v0} + Chrome", body=["HTML slide deck; headless",
                                                 "Chrome {v1} prints the PDF:",
                                                 "HVR_OPT_Prelim.pdf"]),
    dict(id="svg", lane="visualisation", y=633, tools=["Native SVG via Python",
                                                       "rsvg-convert (librsvg)"],
         title="Native SVG (Python)", body=["diagrams, incl. this map;",
                                            "rsvg-convert {v1} → PNG"]),
    dict(id="q3d", lane="not_executed", y=150, tools=["Ansys Q3D Extractor"],
         title="Ansys Q3D Extractor", body=["R, L, C of wiring"], reason="license unavailable"),
    dict(id="maxwell", lane="not_executed", y=284, tools=["Ansys Maxwell (DC conduction)"],
         title="Ansys Maxwell (DC)", body=["DC current-flow solver"],
         reason="license unavailable"),
    dict(id="icepak", lane="reference", y=626, tools=["Ansys Icepak"], title="Ansys Icepak",
         body=["conjugate CFD of one", "cold-plate channel"]),
    dict(id="hfss", lane="not_executed", y=418, tools=["Ansys HFSS"], title="Ansys HFSS",
         body=["high-frequency EM solver"], reason="earlier try; no result used"),
]

#: lane notes: (lane, y of first baseline, lines)
NOTES = [("inputs", 600, ["Production meshes are", "built in-house; Gmsh only",
                          "meshes the MOOSE check."]),
         ("not_executed", 578, ["No arrows: no number from", "these tools enters any",
                                "result."])]

#: data flows. Each is a list of points; ("box", side, frac) anchors a point on a box
#: edge: side in left/right/top/bottom, frac along that edge (0 = top or left end).
#: "label": (text, x, y, anchor). "via" pass-through boxes are not allowed.
FLOWS = [
    dict(pts=[("cfg", "bottom", 0.5), ("mesh", "top", 0.5)], label=("geometry", 8, 0, "start")),
    dict(pts=[("cfg", "right", 0.19), ("net", "left", None)]),
    dict(pts=[("mesh", "right", 0.19), ("ccx_t", "left", None)]),
    dict(pts=[("mesh", "right", 0.86), ("ccx_s", "left", None)]),
    dict(pts=[("gmsh", "right", 0.36), ("moose", "left", None)],
         label=("wiring-sheet mesh (.msh)", "lane:production", -10, "middle")),
    dict(pts=[("net", "bottom", 0.12), ("ccx_t", "top", 0.12)], label=("losses", 8, 0, "start")),
    dict(pts=[("ccx_t", "top", 0.88), ("net", "bottom", 0.88)],
         label=("temperatures", -8, 0, "end")),
    dict(pts=[("ccx_t", "bottom", 0.5), ("ccx_s", "top", 0.5)],
         label=("temperature field", 8, 0, "start")),
    dict(pts=[("ccx_s", "bottom", 0.5), ("ccx_l", "top", 0.5)],
         label=("critical joint: du, T", 8, 0, "start")),
    dict(pts=[("moose", "right", 0.5), ("vtk", "left", None)]),
    dict(pts=[("vtk", "bottom", 0.5), ("mpl", "top", 0.5)], label=("field arrays", 8, 0, "start")),
    dict(pts=[("mpl", "bottom", 0.5), ("deck", "top", 0.5)], label=("charts (SVG)", 8, 0, "start")),
    dict(pts=[("svg", "top", 0.5), ("deck", "bottom", 0.5)], label=("diagrams", 8, 0, "start")),
]
#: collectors: every box listed sends its results down one line into the results bus
COLLECTORS = [("production", ["net", "ccx_t", "ccx_s", "ccx_l"], "right"),
              ("reference", ["moose", "aedt", "cf", "icepak"], "left")]
BUS = dict(x0=330, x1=960, y=814, h=46,
           lines=[("Results on disk: research/final_closure/*.json", "bold"),
                  ("production results + comparison numbers (accuracy_speed_matrix.json)",
                   "normal")],
           to="mpl", riser_x=970)

# ----------------------------------------------------------------------- text metrics
_AFM = {}


def _afm(bold):
    """Glyph advance widths (1/1000 em) of Helvetica / Helvetica-Bold, from the AFM files
    shipped with Matplotlib. Arial and Nimbus Sans, which this host substitutes for the
    figstyle font stack, share these metrics."""
    key = "phvb8a.afm" if bold else "phvr8a.afm"
    if key not in _AFM:
        wid = {}
        path = Path(matplotlib.get_data_path()) / "fonts" / "afm" / key
        for line in path.read_text(encoding="latin-1").splitlines():
            if line.startswith("C "):
                f = dict(s.strip().split(" ", 1) for s in line.split(";") if s.strip())
                if 32 <= int(f["C"]) < 127:
                    wid[chr(int(f["C"]))] = float(f["WX"])
        wid["'"] = wid.get("'", 222.0)
        _AFM[key] = wid
    return _AFM[key]


_WIDE = {"→": 1000, "·": 278, "—": 1000, "–": 556, "ç": 500,
         "é": 556, "°": 400}


def measure(s, size, bold=False):
    w = _afm(bold)
    return sum(w.get(c, _WIDE.get(c, 1000)) for c in s) / 1000.0 * size


class LayoutError(ValueError):
    pass


_GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui"}
#: the exact stack scripts/figstyle.py once set (presentation/prelim_hvr/
#: VISUAL_TOOL_INVENTORY.md, "Issue found during this inventory"): both renderers fell
#: back to serif on it
UNQUOTED_FONT_REAL = "Source Sans 3, Segoe UI, Helvetica, Arial, sans-serif"


def css_font_family(stack):
    """figstyle.FONT lists Source Sans 3 unquoted. A family name containing a number token
    is invalid CSS, so Chrome and rsvg-convert both drop the whole declaration and fall back
    to the default SERIF font. The family list still comes from figstyle; this only quotes
    every name that is not a single CSS identifier."""
    fams = [f.strip() for f in stack.split(",")]
    return ", ".join(f if f in _GENERIC or f.isidentifier() else f"'{f}'" for f in fams)


def check_font_family(value):
    for f in (x.strip() for x in value.split(",")):
        if not (f in _GENERIC or f.isidentifier() or (f[0] == f[-1] == "'" and len(f) > 2)):
            raise LayoutError(f"font-family entry {f!r} is not valid CSS unquoted; the "
                              f"renderer would fall back to serif")


# ----------------------------------------------------------------------- checks
def load_provenance(path=PROV):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return {t["name"]: t for t in d["tools"]}


def check_table(boxes, prov):
    """Every box names provenance tools that agree on status; every mapped tool is drawn."""
    for b in boxes:
        for t in b["tools"]:
            if t not in prov:
                raise LayoutError(f"box {b['id']}: tool {t!r} is not in tool_provenance.json")
        st = {prov[t]["status"] for t in b["tools"]}
        if len(st) != 1:
            raise LayoutError(f"box {b['id']}: tools disagree on status {sorted(st)}")
        if b["lane"] == "not_executed" and st == {"EXECUTED"}:
            raise LayoutError(f"box {b['id']}: EXECUTED tool drawn in the Not executed lane")
        if b["lane"] != "not_executed" and st != {"EXECUTED"}:
            raise LayoutError(f"box {b['id']}: {sorted(st)} tool drawn as part of the flow")
    drawn = {t for b in boxes for t in b["tools"]}
    missing = [n for n, t in prov.items() if t["lane"] in MAPPED_LANES and n not in drawn]
    if missing:
        raise LayoutError(f"provenance tools missing from the map: {missing}")


def check_intro(intro_path, prov):
    d = json.loads(Path(intro_path).read_text(encoding="utf-8"))
    names = [t["name"] for t in d["tools"]]
    if set(names) != set(prov):
        raise LayoutError(f"tool_intro.json names differ from provenance: "
                          f"{sorted(set(names) ^ set(prov))}")
    for t in d["tools"]:
        p = prov[t["name"]]
        if t["status"] != p["status"]:
            raise LayoutError(f"tool_intro {t['name']}: status {t['status']!r} != "
                              f"provenance {p['status']!r}")
        if t["source_url"] != (p.get("official_url") or p.get("quote_source")):
            raise LayoutError(f"tool_intro {t['name']}: source_url differs from provenance")
        if len(t["one_liner"].split()) > 40:
            raise LayoutError(f"tool_intro {t['name']}: one_liner over 40 words")


def check_files(files=FILES_NAMED):
    for f in files:
        if not (R / f).exists():
            raise LayoutError(f"the figure names {f}, which does not exist")
    if not glob.glob(str(R / RESULTS_GLOB)):
        raise LayoutError(f"no file matches {RESULTS_GLOB}")


# ----------------------------------------------------------------------- geometry
def lane(lid):
    for L in LANES:
        if L[0] == lid:
            return L
    raise LayoutError(f"unknown lane {lid}")


def stamp_text(status):
    return "EXECUTED" if status == "EXECUTED" else (
        "NOT INSTALLED" if status == "NOT INSTALLED" else "NOT EXECUTED")


def box_geometry(b):
    _, _, lx, lw = lane(b["lane"])
    il, ir = INSET[b["lane"]]
    n = len(b["body"]) + (1 if b.get("reason") else 0)
    return lx + il, b["y"], lw - il - ir, 9 + 22 + 21 * n + 8 + 26 + 9


def resolve_text(b, prov):
    v = {f"v{i}": prov[t]["version_short"] for i, t in enumerate(b["tools"])}
    return b["title"].format(**v), [s.format(**v) for s in b["body"]]


def anchor(geo, a, other=None):
    bid, side, frac = a
    x, y, w, h = geo[bid]
    if frac is None:                     # align with the other end of a straight segment
        ox, oy = other
        return (x if side == "left" else x + w, oy) if side in ("left", "right") else \
               (ox, y if side == "top" else y + h)
    return {"left": (x, y + frac * h), "right": (x + w, y + frac * h),
            "top": (x + frac * w, y), "bottom": (x + frac * w, y + h)}[side]


def flow_points(geo, f):
    pts, prev = [], None
    for a in f["pts"]:
        p = anchor(geo, a, prev) if isinstance(a, tuple) and isinstance(a[0], str) else a
        pts.append(p)
        prev = p
    return pts


def _crosses(seg, rect, pad=1.0):
    (x0, y0), (x1, y1) = seg
    rx, ry, rw, rh = rect
    rx, ry, rw, rh = rx + pad, ry + pad, rw - 2 * pad, rh - 2 * pad
    if abs(y0 - y1) < 1e-9:              # horizontal
        return ry < y0 < ry + rh and max(x0, x1) > rx and min(x0, x1) < rx + rw
    if abs(x0 - x1) < 1e-9:              # vertical
        return rx < x0 < rx + rw and max(y0, y1) > ry and min(y0, y1) < ry + rh
    raise LayoutError(f"segment {seg} is not axis-aligned")


# ----------------------------------------------------------------------- drawing
def build(boxes=BOXES, flows=FLOWS, prov=None, write=True):
    prov = prov if prov is not None else load_provenance()
    check_table(boxes, prov)
    check_intro(INTRO, prov)
    check_files()
    geo = {b["id"]: box_geometry(b) for b in boxes}
    errors, texts = [], []

    def put(x, y, s, size, avail, bold=False, anchor_="start", fill=F.INK, halo=True,
            where=""):
        if size < MIN_PX:
            errors.append(f"{where}: text below {MIN_PX}px: {s!r}")
        need = measure(s, size, bold) * FIT
        if avail is not None and need > avail:
            errors.append(f"{where}: {s!r} needs {need:.0f}px, has {avail:.0f}px")
        x0 = x if anchor_ == "start" else x - need / 2 if anchor_ == "middle" else x - need
        texts.append((x0, y - size * 0.8, need, size, s, where))
        return F.text(x, y, s, size, anchor_, "bold" if bold else "normal", fill, halo)

    svg = [F.svg_open(W, H, "What software is doing what?",
                      "Software map of the HVR_OPT final-closure study: inputs, production "
                      "solvers, independent references, visualisation, and tools not executed. "
                      "Generated by scripts/final_closure_tool_map.py from "
                      "research/final_closure/tool_provenance.json.")]
    family = css_font_family(F.FONT)
    check_font_family(family)
    svg.append(f'<g font-family="{family}">\n')
    # title, subtitle, legend
    svg.append(put(24, 46, "What software is doing what?", 32, 980, bold=True, where="title"))
    svg.append(put(24, 76, "HVR_OPT final-closure study: who computes the results, who checks "
                           "them, who draws them.", 17, 1000, fill=F.MUTED, where="subtitle"))
    lx, step = 1010, 290
    for i, (status, note) in enumerate((("EXECUTED", "ran in this study"),
                                        ("NOT EXECUTED", "no number used"))):
        col = F.OK if status == "EXECUTED" else F.OPEN
        sw = measure(status, 16, True) + 16
        x = lx + i * step
        svg.append(F.rect(x, 18, sw, 26, "#fff", col, 1.6, 'rx="3"'))
        svg.append(put(x + 8, 37, status, 16, sw - 8, bold=True, fill=col, halo=False,
                       where="legend"))
        svg.append(put(x + sw + 8, 37, note, 16, step - sw - 14, where="legend"))
    svg.append(F.arrow([(lx, 66), (lx + 44, 66)], "ink", 2.0))
    svg.append(put(lx + 54, 72, "data flow", 16, 120, where="legend"))
    svg.append(put(lx + step, 72, "in-house = written for this study", 16, W - 24 - lx - step,
                   fill=F.MUTED, where="legend"))

    # lanes
    for lid, head, x, w in LANES:
        bad = lid == "not_executed"
        col = F.OPEN if bad else F.LINE
        svg.append(F.rect(x, LANE_TOP, w, LANE_BOTTOM - LANE_TOP, col, "none", 0,
                          f'rx="8" fill-opacity="{0.05 if bad else 0.28}"'))
        if bad:
            svg.append(F.rect(x, LANE_TOP, w, LANE_BOTTOM - LANE_TOP, "url(#hatch)", "none",
                              0, 'rx="8" opacity="0.30"'))
        svg.append(F.rect(x, LANE_TOP, w, HEAD_H, col, "none", 0,
                          f'rx="8" fill-opacity="{0.16 if bad else 1}"'))
        svg.append(put(x + w / 2, LANE_TOP + 28, head, 19, w - 16, bold=True,
                       anchor_="middle", fill=F.OPEN if bad else F.INK, halo=False,
                       where=f"lane {lid}"))

    # notes
    for lid, y0, lines in NOTES:
        _, _, x, w = lane(lid)
        for i, s in enumerate(lines):
            svg.append(put(x + 16, y0 + 21 * i, s, 16, w - 32, fill=F.MUTED, where=f"note {lid}"))

    # boxes
    for b in boxes:
        x, y, w, h = geo[b["id"]]
        status = prov[b["tools"][0]]["status"]
        ok = status == "EXECUTED"
        col = F.OK if ok else F.OPEN
        if ok:
            svg.append(F.rect(x, y, w, h, "#fff", F.INK, 1.2, 'rx="6"'))
        else:
            svg.append(F.rect(x, y, w, h, "#fff", F.OPEN, 1.4, 'rx="6" stroke-dasharray="6,4"'))
            svg.append(F.rect(x, y, w, h, "url(#hatch)", "none", 0, 'rx="6" opacity="0.22"'))
        svg.append(F.rect(x, y + 1, 6, h - 2, col, "none", 0))
        title, body = resolve_text(b, prov)
        avail = w - 16 - 10
        svg.append(put(x + 16, y + 9 + 18, title, 18, avail, bold=True, where=b["id"]))
        for i, s in enumerate(body):
            svg.append(put(x + 16, y + 9 + 22 + 21 * i + 16, s, 16, avail, where=b["id"]))
        if b.get("reason"):
            svg.append(put(x + 16, y + 9 + 22 + 21 * len(body) + 16, b["reason"], 16, avail,
                           bold=True, fill=F.OPEN, where=b["id"]))
        st = stamp_text(status)
        sw = measure(st, 16, True) + 16
        sy = y + h - 9 - 26
        svg.append(F.rect(x + 16, sy, sw, 26, "#fff", col, 1.6, 'rx="3"'))
        svg.append(put(x + 24, sy + 19, st, 16, sw - 8, bold=True, fill=col, halo=False,
                       where=b["id"]))

    # flows
    segs = []
    for f in flows:
        pts = flow_points(geo, f)
        ends = {a[0] for a in f["pts"] if isinstance(a, tuple) and isinstance(a[0], str)}
        for a in f["pts"]:                 # a straight end must land on its box
            if isinstance(a, tuple) and isinstance(a[0], str) and a[2] is None:
                x, y, w, h = geo[a[0]]
                px, py = pts[f["pts"].index(a)]
                if a[1] in ("left", "right") and not (y + 4 <= py <= y + h - 4):
                    errors.append(f"flow into {a[0]} at y={py:.0f} misses the box")
                if a[1] in ("top", "bottom") and not (x + 4 <= px <= x + w - 4):
                    errors.append(f"flow into {a[0]} at x={px:.0f} misses the box")
        for s in zip(pts, pts[1:]):
            segs.append((s, ends))
        svg.append(F.arrow(pts, "ink", 2.0))
        if f.get("label"):
            s, dx, dy, anc = f["label"]
            (x0, y0), (x1, y1) = pts[0], pts[-1]
            if isinstance(dx, str):        # centred in a lane, just above a horizontal line
                _, _, lx_, lw_ = lane(dx.split(":")[1])
                svg.append(put(lx_ + lw_ / 2, y0 + dy, s, 16, lw_ - 16, anchor_="middle",
                               fill=F.MUTED, where="flow label"))
            else:                          # beside a vertical segment, mid-gap
                svg.append(put(x0 + dx, (y0 + y1) / 2 + 6 + dy, s, 16, None, anchor_=anc,
                               fill=F.MUTED, where="flow label"))

    # collectors into the results bus
    bus_top = BUS["y"]
    for lid, ids, side in COLLECTORS:
        _, _, x, w = lane(lid)
        cx = x + w - 13 if side == "right" else x + 13
        ys = []
        for bid in ids:
            bx, by, bw, bh = geo[bid]
            yy = by + bh - 18
            ex = bx + bw if side == "right" else bx
            svg.append(f'<polyline points="{ex:.2f},{yy:.2f} {cx:.2f},{yy:.2f}" fill="none" '
                       f'stroke="{F.INK}" stroke-width="2"/>\n'
                       f'<circle cx="{cx:.2f}" cy="{yy:.2f}" r="3.2" fill="{F.INK}"/>\n')
            segs.append((((ex, yy), (cx, yy)), {bid}))
            ys.append(yy)
        pts = [(cx, min(ys)), (cx, bus_top)]
        svg.append(F.arrow(pts, "ink", 2.0))
        segs.append((tuple(pts), set(ids)))

    # results bus and its riser into Matplotlib
    bx0, bx1, by, bh = BUS["x0"], BUS["x1"], BUS["y"], BUS["h"]
    svg.append(F.rect(bx0, by, bx1 - bx0, bh, F.LINE, F.MUTED, 1.0, 'rx="6" fill-opacity="0.55"'))
    for i, (s, wt) in enumerate(BUS["lines"]):
        svg.append(put(bx0 + 12, by + 19 + 20 * i, s, 16, bx1 - bx0 - 24, bold=wt == "bold",
                       halo=False, where="bus"))
    tx, ty, tw, th = geo[BUS["to"]]
    rx_ = BUS["riser_x"]
    riser = [(bx1, by + bh / 2), (rx_, by + bh / 2), (rx_, ty + th / 2), (tx, ty + th / 2)]
    svg.append(F.arrow(riser, "ink", 2.0))
    for s in zip(riser, riser[1:]):
        segs.append((s, {BUS["to"]}))

    # footer
    svg.append(put(24, 888, "Versions and status are read from "
                            "research/final_closure/tool_provenance.json; generator: "
                            "scripts/final_closure_tool_map.py", 16, W - 48, fill=F.MUTED,
                   where="footer"))
    svg.append("</g>\n")
    svg.append(F.svg_close())

    # geometry guards: boxes do not overlap; no segment crosses a box it does not connect;
    # no text overlaps a box it does not belong to
    ids = list(geo)
    for i, a in enumerate(ids):
        for b_ in ids[i + 1:]:
            ax, ay, aw, ah = geo[a]
            bx_, by_, bw_, bh_ = geo[b_]
            if ax < bx_ + bw_ and bx_ < ax + aw and ay < by_ + bh_ and by_ < ay + ah:
                errors.append(f"boxes {a} and {b_} overlap")
    for bid, (x, y, w, h) in geo.items():
        if y + h > LANE_BOTTOM - 6:
            errors.append(f"box {bid} runs past the lane bottom")
    for seg, ends in segs:
        for bid, rect in geo.items():
            if bid in ends:
                continue
            if _crosses(seg, rect):
                errors.append(f"segment {seg} crosses box {bid}")
    for (x0, y0, tw_, th_, s, where) in texts:
        for bid, (x, y, w, h) in geo.items():
            if where == bid:
                continue
            if x0 < x + w and x < x0 + tw_ and y0 < y + h and y < y0 + th_:
                errors.append(f"text {s!r} ({where}) overlaps box {bid}")
        if x0 < 4 or x0 + tw_ > W - 4:
            errors.append(f"text {s!r} leaves the canvas")
    for i, (ax, ay, aw, ah, sa, wa) in enumerate(texts):
        for (bx_, by_, bw_, bh_, sb, wb) in texts[i + 1:]:
            if ax < bx_ + bw_ and bx_ < ax + aw and ay < by_ + bh_ and by_ < ay + ah:
                errors.append(f"text {sa!r} ({wa}) overlaps text {sb!r} ({wb})")
    if errors:
        raise LayoutError("tool map layout failed:\n  " + "\n  ".join(errors))
    out = "".join(svg)
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(out, encoding="utf-8")
    return out


# ----------------------------------------------------------------------- self-test
def selftest():
    """Each guard is fed a REAL offending input and must fail; the real table must pass."""
    prov = load_provenance()
    build(write=False, prov=prov)
    cases = []
    # 1. a name that is in the visual inventory but not in the provenance
    b = copy.deepcopy(BOXES)
    b[next(i for i, x in enumerate(b) if x["id"] == "vtk")]["tools"] = ["ParaView/pvpython"]
    cases.append(("unknown tool name", dict(boxes=b)))
    # 2. the status wording itself, as a box line, overflows a Not-executed box
    b = copy.deepcopy(BOXES)
    b[next(i for i, x in enumerate(b) if x["id"] == "q3d")]["body"] = [
        "NOT EXECUTED IN THIS STUDY — LICENSE UNAVAILABLE"]
    cases.append(("text overflow", dict(boxes=b)))
    # 3. an unlicensed tool drawn as part of the executed flow
    b = copy.deepcopy(BOXES)
    b[next(i for i, x in enumerate(b) if x["id"] == "aedt")]["tools"].append("Ansys Q3D Extractor")
    cases.append(("status disagreement in one box", dict(boxes=b)))
    # 4. a mapped tool silently dropped from the map
    b = [x for x in copy.deepcopy(BOXES) if x["id"] != "hfss"]
    cases.append(("tool missing from map", dict(boxes=b)))
    # 5. an arrow routed through a box (Gmsh straight to VTK crosses MOOSE)
    fl = copy.deepcopy(FLOWS) + [dict(pts=[("gmsh", "right", 0.36), ("vtk", "left", None)])]
    cases.append(("arrow through a box", dict(flows=fl)))
    # 6. a box moved onto its neighbour
    b = copy.deepcopy(BOXES)
    b[next(i for i, x in enumerate(b) if x["id"] == "ccx_s")]["y"] = 470
    cases.append(("overlapping boxes", dict(boxes=b)))
    caught = 0
    for name, kw in cases:
        try:
            build(write=False, prov=prov, **kw)
        except LayoutError as e:
            caught += 1
            print(f"  caught: {name}: {str(e).splitlines()[-1].strip()[:110]}")
        else:
            print(f"  MISSED: {name}")
    # 7. tool_intro drift: a status edited in a copy of the file
    d = json.loads(INTRO.read_text(encoding="utf-8"))
    for t in d["tools"]:
        if t["name"] == "Ansys Q3D Extractor":
            t["status"] = "NOT EXECUTED IN THIS STUDY"
    tmp = OUT.parent / ".tool_intro_selftest.json"
    tmp.write_text(json.dumps(d), encoding="utf-8")
    try:
        check_intro(tmp, prov)
        print("  MISSED: tool_intro status drift")
    except LayoutError as e:
        caught += 1
        print(f"  caught: tool_intro status drift: {str(e)[:110]}")
    finally:
        tmp.unlink()
    # 8. a named file that does not exist
    try:
        check_files(FILES_NAMED + ("research/final_closure/reference_q3d_dc.json",))
        print("  MISSED: missing named file")
    except LayoutError as e:
        caught += 1
        print(f"  caught: missing named file: {str(e)[:110]}")
    # 9. the REAL unquoted stack figstyle once carried (VISUAL_TOOL_INVENTORY.md) must be
    #    rejected; figstyle's current, quoted one accepted
    try:
        check_font_family(UNQUOTED_FONT_REAL)
        print("  MISSED: unquoted font-family")
    except LayoutError as e:
        caught += 1
        print(f"  caught: unquoted font-family: {str(e)[:110]}")
    check_font_family(F.FONT)
    check_font_family(css_font_family(F.FONT))
    total = len(cases) + 3
    print(f"real table passes; {caught}/{total} injected violations caught")
    return 0 if caught == total else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--png", help="also rasterise to this PNG path with rsvg-convert")
    ap.add_argument("--width", type=int, default=W)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    build()
    print(f"wrote {OUT.relative_to(R)}")
    if a.png:
        exe = shutil.which("rsvg-convert")
        if not exe:
            print("rsvg-convert not found", file=sys.stderr)
            return 2
        subprocess.run([exe, "-w", str(a.width), "-o", a.png, str(OUT)], check=True)
        print(f"wrote {a.png} ({a.width} px wide)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
