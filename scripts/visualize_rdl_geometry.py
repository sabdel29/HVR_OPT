"""Exact geometry, explained diagram and annotated MOOSE render of the package 48 V RDL.

WHAT IS SOLVED. The package 48 V RDL is a plan-view, steady DC problem on ONE copper
sheet over the 30 x 30 mm substrate underside (conductance sigma_s = 1/R_sq, insulated
edges). BGA balls (0.4 mm discs) couple the sheet to the rail (V = 0) through an areal
conductance g_a; the 49 converter VIN pads (0.2 mm squares, one per cell) each draw I/49:

    -div(sigma_s grad V) + g_a V [balls] = -(I/49)/A_pad [pads]

The production solver is a refined finite-volume sheet; the independent reference is
MOOSE heat_transfer-opt solving the same equation as div(k grad T) = -q on a gmsh mesh.

ONE GEOMETRY SOURCE. Every coordinate here comes from
scripts/reference_tools/moose_pkg_rdl_reference.py::problem() -- the function that built
the MOOSE mesh -- so the diagram, the overlay and the solver cannot disagree. Literals that
problem()/gmsh_mesh() use but do not return (ball radius, sheet rectangle, sheet
construction) are read from their SOURCE, so an upstream change breaks this build instead
of silently invalidating a figure.

PRODUCTS
  geometry   research/final_closure/rdl_geometry_{Z1,Z2}.json -- both rails, with a
             SHA-256 `geometry_hash` over canonical JSON. The idea (no value) is Omelet's
             Assembly.geometry_hash (mgharib5/Omelet-pkgintc, branch
             pkg-interconnect-physics, pkgintc/geom/assembly.py:451-457: sorted-key JSON,
             then SHA-256). Unlike Omelet, coordinates are first rounded to 1e-6 mm (other
             floats to 12 significant digits) so float noise cannot change the identity.
  explained  presentation/prelim_hvr/figs/rdl_model_explained_{arch}.svg
  render     presentation/prelim_hvr/figs/rdl_reference_annotated_{arch}.png from MOOSE's
             own Exodus output at the LAST time step (a Steady solve stores the initial
             condition as step 0). VTK draws the field; the annotations are a separate
             transparent layer composited on top, and every field pixel that layer does not
             cover is asserted byte-identical to VTK's output.
             + tool_evidence/pkg_rdl_moose_{arch}/06_annotated_render.json,
               07_slide_numbers.json, and a JSON sidecar next to a scratch copy of the PNG.

usage:  python scripts/visualize_rdl_geometry.py [geometry|explained|render|all]
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
# The reference script puts its own module directories at the FRONT of sys.path when it
# is imported, so module resolution is exactly what it is when that script runs alone.
sys.path.insert(0, str(R / "scripts" / "reference_tools"))
sys.path.insert(0, str(R / "scripts"))
import moose_pkg_rdl_reference as REF                               # noqa: E402
import figstyle as FS                                               # noqa: E402
from hvr_scratch import path as scratch                             # noqa: E402

FC = R / "research" / "final_closure"
FIGS = R / "presentation" / "prelim_hvr" / "figs"
EV = R / "presentation" / "prelim_hvr" / "tool_evidence"
SCR = Path(os.environ.get("RDLFIGS_SCRATCH", Path.home() / "claude_scratch" / "rdlfigs"))
ARCHS = ("Z1", "Z2")
RAILS = ("supply", "return")
SCHEMA = "hvr_opt.rdl_geometry.v1"
OMELET_IDEA = ("mgharib5/Omelet-pkgintc@pkg-interconnect-physics "
               "pkgintc/geom/assembly.py:451-457 (Assembly._canonical, geometry_hash)")
MINUS = "−"
CAPTION = "The solver is looking down on this particular copper layer"
#: the package 48 V sheet exists only in a BGA-fed package: for Z2 that is the controlled
#: experiment, never the primary (direct-fed) Z2, whose 48 V does not enter the package
CONTROL_LABEL = ("Z2_BGA_FED_CONTROL -- BGA-fed control, not the primary Z2 "
                 "(which takes its 48 V directly)")
# An UNQUOTED family name containing spaces or ending in a digit ("Source Sans 3") is not
# a valid CSS identifier: Chrome and librsvg >= 2.5x then drop the WHOLE list and fall
# back to serif (seen 2026-10-27 with the etm env's rsvg-convert 2.62.3 and Chrome 151;
# /bin/rsvg-convert 2.42.7 is lenient). figstyle.FONT is quoted now; this re-quotes
# defensively so the figures cannot regress if it ever is not. Families and order are
# figstyle's.
QFONT = ", ".join(
    (f"'{n}'" if (" " in n or n[-1:].isdigit()) else n)
    for n in (f.strip().strip("'\"") for f in FS.FONT.split(",")))


def rel(p):
    p = Path(p)
    try:
        return str(p.relative_to(R))
    except ValueError:
        return str(p)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def num(v, nd=4):
    """A signed number with a true minus sign."""
    s = f"{v:.{nd}f}"
    return s.replace("-", MINUS)


# =================================================================== geometry =====
def _mm(v):
    """Canonical coordinate: 1e-6 mm grid, never -0.0."""
    return round(float(v), 6) + 0.0


def _sig(v):
    """Canonical non-coordinate scalar: 12 significant digits."""
    return float(f"{float(v):.12g}") + 0.0


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)


def sha256(obj) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def _src(fn, pattern, what):
    m = re.search(pattern, inspect.getsource(fn))
    if not m:
        raise RuntimeError(f"cannot read the {what} from {fn.__module__}.{fn.__name__}(): "
                           "the reference source changed -- update this extractor")
    return m.groups()


def reference_constants():
    """Literals problem()/gmsh_mesh()/production() use but do not return."""
    r_gmsh = _src(REF.gmsh_mesh, r"addDisk\(x, y, 0, ([0-9.]+), ([0-9.]+)\)", "ball radius")
    d_prod = _src(REF.production, r'overlap\(x, y, ([0-9.]+), "disc"\)', "ball diameter")
    r_area = _src(REF.problem, r"a_ball = math\.pi \* ([0-9.]+) \*\* 2", "ball area radius")
    rect = _src(REF.gmsh_mesh,
                r"addRectangle\((-?[0-9.]+), (-?[0-9.]+), 0, ([0-9.]+), ([0-9.]+)\)", "sheet")
    t_occ = _src(REF.problem, r"sheet_resistance_ohm_sq\(([0-9.eE+-]+), ([0-9.]+)\)",
                 "sheet construction")
    rho_case = _src(REF.problem, r'RHO_C_CASES\["(\w+)"\]', "contact case")
    t_ball = _src(REF.problem, r"bga_ball_resistance_ohm\(([0-9.]+)\)", "ball temperature")
    r = float(r_gmsh[0])
    if not (float(r_gmsh[1]) == r and abs(2 * r - float(d_prod[0])) < 1e-12
            and float(r_area[0]) == r):
        raise RuntimeError(f"ball size disagrees across the reference: gmsh {r_gmsh}, "
                           f"production {d_prod}, problem {r_area}")
    x0, y0, wx, wy = map(float, rect)
    half = REF.K.SUBSTRATE_MM / 2.0
    if (x0, y0, wx, wy) != (-half, -half, 2 * half, 2 * half):
        raise RuntimeError(f"MOOSE sheet {rect} is not the {REF.K.SUBSTRATE_MM} mm substrate")
    return {"ball_radius_mm": r, "sheet_rect_mm": [x0, y0, wx, wy],
            "t_cu_mm": float(t_occ[0]), "occupancy": float(t_occ[1]),
            "rho_c_case": rho_case[0], "ball_T_C": float(t_ball[0])}


def matched_count():
    return int(json.loads((FC / "package_network.json").read_text())["matched_count"])


def die_side_mm():
    import yaml
    st = yaml.safe_load((R / "configs/phase0b/package_stack.yaml").read_text())
    fd = next(v for k, v in _walk_yaml(st) if k == "functional_die")
    sx, sy = float(fd["size_x"]["value"]), float(fd["size_y"]["value"])
    arch = json.loads((FC / "architecture_geometry.json").read_text())["architectures"]
    for a in ARCHS:
        if [sx, sy] != [float(v) for v in arch[a]["die_mm"]]:
            raise RuntimeError(f"die footprint: package_stack.yaml {sx}x{sy} vs "
                               f"architecture_geometry.json {arch[a]['die_mm']}")
    if sx != sy:
        raise RuntimeError("the die is drawn as a square")
    return sx


def _walk_yaml(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, v
            yield from _walk_yaml(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_yaml(v)


def build_payload(arch, pbs, cells, tile, cut, half, r_ball, N):
    """The hashed geometry -- a pure function of the raw inputs (so it can be re-run on
    perturbed inputs as a negative test). List ORDER is kept: ball{i} and pad{i} are the
    MOOSE block names, so order is part of the identity of the solved problem."""
    def square(h):
        return [[_mm(-h), _mm(-h)], [_mm(h), _mm(-h)], [_mm(h), _mm(h)], [_mm(-h), _mm(h)]]
    s = pbs["supply"]
    return {
        "schema": SCHEMA,
        "arch": arch,
        "units": {"length": "mm", "sigma_s": "S (sheet conductance, 1/R_sq)",
                  "g_a": "S/mm^2", "i_total": "A"},
        "sheet": {"outline_mm": square(half), "sigma_s_S": _sig(s["sigma_s"])},
        "cutout": (None if not cut else
                   {"shape": "square", "centre_mm": [0.0, 0.0], "side_mm": _mm(cut),
                    "outline_mm": square(cut / 2.0)}),
        "cells": {"n": len(cells), "side_mm": _mm(tile),
                  "centres_mm": [[_mm(x), _mm(y)] for x, y in cells]},
        "ball_diameter_mm": _mm(2 * r_ball),
        "g_a_S_per_mm2": _sig(s["g_a"]),
        "i_total_A": _sig(s["i_total"]),
        "matched_count_per_rail": int(N),
        "rails": {rail: {"balls_mm": [[_mm(x), _mm(y)] for x, y in pb["balls"]],
                         "pads_mm": [[_mm(x), _mm(y), _mm(c)] for x, y, c in pb["pads"]]}
                  for rail, pb in pbs.items()},
    }


def rail_payload(geom, rail):
    """The exact problem one rail solves (what a MOOSE run of that rail saw)."""
    return {"schema": SCHEMA, "arch": geom["arch"], "rail": rail, "units": geom["units"],
            "sheet": geom["sheet"], "cutout": geom["cutout"],
            "ball_diameter_mm": geom["ball_diameter_mm"],
            "g_a_S_per_mm2": geom["g_a_S_per_mm2"], "i_total_A": geom["i_total_A"],
            **geom["rails"][rail]}


def geometry_checks(geom, pbs, r_ball):
    """Physical sanity of the selected geometry, asserted (not just recorded)."""
    import physical_coords as PCO
    half = geom["sheet"]["outline_mm"][2][0]
    sup = [tuple(p) for p in pbs["supply"]["balls"]]
    ret = [tuple(p) for p in pbs["return"]["balls"]]
    out = {}
    assert not set(sup) & set(ret), "a ball is assigned to both rails"
    for rail, pb in pbs.items():
        b = np.array(pb["balls"], float)
        pads = np.array(pb["pads"], float)
        assert all(PCO.is_on_bga_lattice(x, y) for x, y in pb["balls"]), rail
        bs = {(round(x, 9) + 0.0, round(y, 9) + 0.0) for x, y in pb["balls"]}
        assert all((round(-x, 9) + 0.0, round(-y, 9) + 0.0) in bs for x, y in bs), \
            f"{rail}: ball set is not mirror-symmetric"
        assert np.all(np.abs(b) + r_ball <= half), f"{rail}: a ball leaves the sheet"
        assert np.all(np.abs(pads[:, :2]) + pads[:, 2:] / 2 <= half), f"{rail}: pad off sheet"
        # clearance between every ball disc and every pad square (no overlap)
        dx = np.maximum(np.abs(b[:, None, 0] - pads[None, :, 0]) - pads[None, :, 2] / 2, 0)
        dy = np.maximum(np.abs(b[:, None, 1] - pads[None, :, 1]) - pads[None, :, 2] / 2, 0)
        clr = float(np.min(np.hypot(dx, dy)) - r_ball)
        assert clr > 0, f"{rail}: a ball overlaps a pad"
        raw = np.r_[b.ravel(), pads.ravel()]
        rnd = np.array([_mm(v) for v in raw])
        out[rail] = {"n_balls": len(b), "n_pads": len(pads),
                     "min_ball_to_pad_clearance_mm": round(clr, 6),
                     "max_ball_radius_from_centre_mm": round(float(np.max(np.hypot(*b.T))), 6),
                     "rounding_max_shift_mm": float(np.max(np.abs(raw - rnd)))}
        assert out[rail]["rounding_max_shift_mm"] <= 5e-7 + 1e-15
    if geom["cutout"]:
        c2 = geom["cutout"]["side_mm"] / 2
        allb = np.array(sup + ret, float)
        inner = float(np.min(np.max(np.abs(allb), axis=1)) - r_ball - c2)
        assert inner > 0, "a ball disc reaches into the PCB opening"
        out["cutout_ball_clearance_mm"] = round(inner, 6)
    return out


def hash_negative_tests(arch, pbs, cells, tile, cut, half, r_ball, N, h0):
    """The hash must CHANGE for a real change and must NOT change for float noise."""
    def h_of(mut):
        p2 = {k: {kk: (list(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()}
              for k, v in pbs.items()}
        mut(p2)
        return sha256(build_payload(arch, p2, cells, tile, cut, half, r_ball, N))

    def shift(p2, d):
        x, y = p2["supply"]["balls"][0]
        p2["supply"]["balls"][0] = (x + d, y)

    def swap(p2):
        p2["supply"], p2["return"] = p2["return"], p2["supply"]

    res = {"one_ball_moved_1e-5_mm_changes_hash": h_of(lambda p: shift(p, 1e-5)) != h0,
           "one_ball_moved_1e-9_mm_keeps_hash": h_of(lambda p: shift(p, 1e-9)) == h0,
           "rails_swapped_changes_hash": h_of(swap) != h0}
    if not all(res.values()):
        raise AssertionError(f"geometry_hash negative test failed: {res}")
    return res


def build_geometry(arch):
    N = matched_count()
    sig_default = inspect.signature(REF.problem).parameters["N"].default
    if sig_default != N:
        raise RuntimeError(f"problem() defaults to N={sig_default} but the matched count is {N}")
    c = reference_constants()
    pbs = {rail: REF.problem(arch, rail, N) for rail in RAILS}
    s, g = pbs["supply"], pbs["return"]
    for k in ("sigma_s", "g_a", "i_total", "N"):
        assert s[k] == g[k], f"rails differ in {k}"
    cells = REF.PCO.physical_cell_coordinates()
    tile = float(REF.RF.VR_TILE_SIDE_MM)
    for rail, pb in pbs.items():
        assert pb["pads"] == REF.RF.cell_terminals(cells, rail, "VIN_PAD"), rail
        assert len(pb["balls"]) == N and len(pb["pads"]) == len(cells) == 49, rail
    cut = REF.K.architecture_cutout_mm(arch)
    half = REF.K.SUBSTRATE_MM / 2.0
    r_ball = c["ball_radius_mm"]
    rsq = REF.K.sheet_resistance_ohm_sq(c["t_cu_mm"], c["occupancy"])
    assert abs(1.0 / rsq - s["sigma_s"]) <= 1e-12 * s["sigma_s"], "sigma_s construction"
    rho_c = REF.K.RHO_C_CASES[c["rho_c_case"]]
    r_b = REF.PI.bga_ball_resistance_ohm(c["ball_T_C"])
    assert abs(1.0 / (rho_c + r_b * math.pi * r_ball ** 2) - s["g_a"]) <= 1e-12 * s["g_a"]
    arch_json = json.loads((FC / "architecture_geometry.json").read_text())["architectures"][arch]
    assert abs(arch_json["cells"]["side_mm"] - tile) < 1e-9, "cell side differs"
    assert (arch_json["cutout_mm"] or None) == (cut or None), "cutout differs"

    geom = build_payload(arch, pbs, cells, tile, cut, half, r_ball, N)
    h = sha256(geom)
    neg = hash_negative_tests(arch, pbs, cells, tile, cut, half, r_ball, N, h)
    checks = geometry_checks(geom, pbs, r_ball)
    return {
        "generated_by": "scripts/visualize_rdl_geometry.py geometry",
        "geometry_source": ("scripts/reference_tools/moose_pkg_rdl_reference.py::"
                            "problem(arch, rail, N) -- the function that built the MOOSE mesh"),
        "geometry_hash": h,
        "rail_hashes": {rail: sha256(rail_payload(geom, rail)) for rail in RAILS},
        "hash_method": {
            "digest": "SHA-256 of the UTF-8 bytes of json.dumps(geometry, sort_keys=True, "
                      "separators=(',', ':'), ensure_ascii=True)",
            "rounding": "coordinates and lengths round(v, 6) + 0.0 mm (1e-6 mm grid, no "
                        "-0.0); sigma_s, g_a, i_total to 12 significant digits",
            "order": "ball and pad lists keep problem() order (= MOOSE block names "
                     "ball{i}, pad{i}); reordering is a different identity",
            "rail_hashes": "the same digest over one rail's problem (sheet, cutout, ball "
                           "diameter, g_a, i_total, that rail's balls and pads)",
            "idea_from": OMELET_IDEA + "; no Omelet value, constant or code is used",
            "negative_tests": neg},
        "geometry": geom,
        "context": {
            "die_footprint_mm": die_side_mm(),
            "die_source": "configs/phase0b/package_stack.yaml functional_die (== "
                          "architecture_geometry.json die_mm)",
            "architecture_label": CONTROL_LABEL if arch == "Z2" else arch_json["label"],
            "matched_count_source": "research/final_closure/package_network.json matched_count",
            "sheet_construction": {"t_cu_mm": c["t_cu_mm"], "occupancy": c["occupancy"],
                                   "R_sq_ohm": rsq,
                                   "source": "problem(): K.sheet_resistance_ohm_sq(t, occ)"},
            "contact": {"rho_c_case": c["rho_c_case"], "rho_c_ohm_mm2": rho_c,
                        "R_ball_ohm": r_b, "ball_T_C": c["ball_T_C"],
                        "relation": "g_a = 1 / (rho_c + R_ball * pi r^2)"},
            "rail_solved_by_moose_reference": "supply (problem(arch) default rail)"},
        "checks": checks,
    }


def plain_svg(G, path):
    """Bare exact geometry, 25 px/mm, for inspection only (scratch)."""
    g = G["geometry"]
    k, half = 25.0, g["sheet"]["outline_mm"][2][0]
    W = int(2 * half * k + 40)
    X = lambda x: 20 + (x + half) * k                                  # noqa: E731
    Y = lambda y: 20 + (half - y) * k                                  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{W}" '
         f'data-geometry-hash="{G["geometry_hash"]}">',
         f'<rect width="{W}" height="{W}" fill="#fff"/>',
         f'<rect x="{X(-half)}" y="{Y(half)}" width="{2*half*k}" height="{2*half*k}" '
         'fill="#f6e7d6" stroke="#000"/>']
    if g["cutout"]:
        c2 = g["cutout"]["side_mm"] / 2
        o.append(f'<rect x="{X(-c2)}" y="{Y(c2)}" width="{2*c2*k}" height="{2*c2*k}" '
                 'fill="none" stroke="#c00" stroke-dasharray="6,4"/>')
    t = g["cells"]["side_mm"]
    for x, y in g["cells"]["centres_mm"]:
        o.append(f'<rect x="{X(x-t/2):.2f}" y="{Y(y+t/2):.2f}" width="{t*k:.2f}" '
                 f'height="{t*k:.2f}" fill="none" stroke="#999" stroke-width="0.6"/>')
    r = g["ball_diameter_mm"] / 2
    for rail, fill in (("supply", "#e36209"), ("return", "none")):
        for x, y in g["rails"][rail]["balls_mm"]:
            o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{r*k:.2f}" fill="{fill}" '
                     'stroke="#000" stroke-width="0.8"/>')
        for x, y, c in g["rails"][rail]["pads_mm"]:
            o.append(f'<rect x="{X(x-c/2):.2f}" y="{Y(y+c/2):.2f}" width="{c*k:.2f}" '
                     f'height="{c*k:.2f}" fill="{"#000" if rail == "supply" else "none"}" '
                     'stroke="#000" stroke-width="0.6"/>')
    o.append("</svg>\n")
    path.write_text("\n".join(o))


def run_geometry():
    SCR.mkdir(parents=True, exist_ok=True)
    out = {}
    for arch in ARCHS:
        G = build_geometry(arch)
        f = FC / f"rdl_geometry_{arch}.json"
        f.write_text(json.dumps(G, indent=1) + "\n")
        back = json.loads(f.read_text())
        assert sha256(back["geometry"]) == G["geometry_hash"], "hash does not survive a reload"
        plain_svg(G, SCR / f"rdl_geometry_{arch}_exact.svg")
        g = G["geometry"]
        print(f"[geometry] {arch}: {rel(f)}")
        print(f"  geometry_hash  {G['geometry_hash']}")
        for rail in RAILS:
            ck = G["checks"][rail]
            print(f"  {rail:<6} hash {G['rail_hashes'][rail][:16]}...  {ck['n_balls']} balls "
                  f"(r_max {ck['max_ball_radius_from_centre_mm']:.3f} mm), {ck['n_pads']} pads, "
                  f"min ball-pad clearance {ck['min_ball_to_pad_clearance_mm']:.3f} mm")
        cut = g["cutout"]
        opening = ("no PCB opening" if not cut else
                   "PCB opening %g mm, nearest ball disc %.3f mm outside it"
                   % (cut["side_mm"], G["checks"]["cutout_ball_clearance_mm"]))
        print(f"  sheet {2 * g['sheet']['outline_mm'][2][0]:g} mm square, sigma_s "
              f"{g['sheet']['sigma_s_S']:.4f} S (R_sq {1e3 / g['sheet']['sigma_s_S']:.3f} "
              f"mOhm/sq), g_a {g['g_a_S_per_mm2']:.6g} S/mm^2, {opening}")
        out[arch] = G
    return out


def load_geometry(arch):
    G = json.loads((FC / f"rdl_geometry_{arch}.json").read_text())
    if sha256(G["geometry"]) != G["geometry_hash"]:
        raise RuntimeError(f"rdl_geometry_{arch}.json: stored hash does not match its content")
    if G != json.loads(json.dumps(build_geometry(arch))):
        raise RuntimeError(f"rdl_geometry_{arch}.json is stale against problem(); "
                           "re-run the geometry step")
    return G


# ================================================================== explained =====
def _rich(x, y, parts, size=15, anchor="start", fill=FS.INK, weight="normal"):
    """One line of text with sub/superscripts: parts = [(text, kind)], kind in
    '', 'sub', 'sup', 'i' (italic). Uses dy shifts (rsvg 2.42 has no baseline-shift)."""
    out, cur, pend = [], 0.0, 0
    for t, kind in parts:
        # rsvg 2.42 and 2.62 both drop spaces (even no-break ones) at a tspan boundary, so
        # boundary spaces become an explicit dx; inner runs of spaces become no-break spaces
        lead, trail = len(t) - len(t.lstrip(" ")), len(t) - len(t.rstrip(" "))
        t = re.sub(r" {2,}", lambda m: " " * len(m.group()), t.strip(" "))
        dx = (pend + lead) * 0.28 * size
        pend = trail
        dxa = f' dx="{dx:.1f}"' if dx else ""
        if kind in ("sub", "sup"):
            dy = 0.32 * size if kind == "sub" else -0.42 * size
            out.append(f'<tspan{dxa} dy="{dy - cur:.1f}" font-size="{0.72 * size:.1f}">'
                       f'{FS.esc(t)}</tspan>')
            cur = dy
        else:
            style = ' font-style="italic"' if kind == "i" else ""
            out.append(f'<tspan{dxa} dy="{-cur:.1f}"{style}>{FS.esc(t)}</tspan>')
            cur = 0.0
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{fill}" font-weight="{weight}">' + "".join(out) + "</text>\n")


def _ball(cx, cy, r, rail, sw=1.0):
    if rail == "supply":
        return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{FS.I48}" '
                f'stroke="{FS.INK}" stroke-width="{sw * 0.7:.2f}"/>\n')
    return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#ffffff" '
            f'stroke="{FS.IRET}" stroke-width="{sw * 1.1:.2f}"/>\n')


def _pad(cx, cy, a, rail, sw=1.0):
    if rail == "supply":
        return (f'<rect x="{cx - a / 2:.2f}" y="{cy - a / 2:.2f}" width="{a:.2f}" '
                f'height="{a:.2f}" fill="{FS.INK}" stroke="{FS.INK}" stroke-width="{0.5 * sw:.2f}"/>\n')
    return (f'<rect x="{cx - a / 2:.2f}" y="{cy - a / 2:.2f}" width="{a:.2f}" '
            f'height="{a:.2f}" fill="#ffffff" stroke="{FS.IRET}" stroke-width="{0.9 * sw:.2f}"/>\n')


def _layer_style(name):
    n = name.lower()
    if n == "board":
        return FS.MAT["pcb"]
    if n == "bga":
        return FS.MAT["solder"]
    if n in ("sub_lower", "tile_band"):
        return FS.MAT["silicon"]
    if "rdl" in n:
        return FS.MAT["rdl"]
    if "attach" in n:            # Cu pillars in underfill: drawn as the underfill it mostly is
        return FS.MAT["fill"]
    if "gan" in n:
        return FS.MAT["gan"]
    if "caps" in n:
        return FS.MAT["caps"]
    if "inductor" in n:
        return FS.MAT["inductor"]
    if n == "interface":
        return FS.MAT["solder"]
    if n == "die":
        return FS.MAT["die"]
    if n == "tim":
        return FS.MAT["tim"]
    raise KeyError(f"no style for layer {name!r}")


def _place_labels(want, lo, hi, gap):
    """1-D label placement: keep order, keep >= gap apart, stay inside [lo, hi]."""
    pos = list(want)
    for i in range(1, len(pos)):
        pos[i] = max(pos[i], pos[i - 1] + gap)
    if pos and pos[-1] > hi:
        pos[-1] = hi
        for i in range(len(pos) - 2, -1, -1):
            pos[i] = min(pos[i], pos[i + 1] - gap)
    if pos and pos[0] < lo:
        raise RuntimeError(f"{len(pos)} labels do not fit in {hi - lo:.0f} px at gap {gap}")
    return pos


def stack_inset(arch, x0, y0, w, h, label_x):
    """Cross-section of the package stack, z to scale from architecture_geometry.json,
    with the 48 V RDL sheet (z = 0: top of the BGA, land side of the substrate) marked."""
    A = json.loads((FC / "architecture_geometry.json").read_text())["architectures"][arch]
    layers = A["layers"]
    half = A["substrate_mm"][0] / 2.0
    die2 = A["die_mm"][0] / 2.0
    cut2 = (A["cutout_mm"] or 0.0) / 2.0
    zlo = min(L["z0_um"] for L in layers)
    zhi = max(L["z1_um"] for L in layers)
    kz = h / (zhi - zlo)
    kx = w / (2 * half)
    Zp = lambda z: y0 + (zhi - z) * kz                                   # noqa: E731
    Xp = lambda x: x0 + (x + half) * kx                                  # noqa: E731
    bga = next(L for L in layers if L["name"] == "bga")
    sub = [L for L in layers if L["name"] in ("sub_lower", "tile_band")]
    if not (bga["z1_um"] == 0.0 and min(L["z0_um"] for L in sub) == 0.0):
        raise RuntimeError("the sheet is drawn at z = 0 = top of the BGA = bottom of the "
                           "substrate; architecture_geometry.json no longer says so")
    o = []

    def spans(L):
        if L["footprint"] == "die":
            return [(-die2, die2)]
        if L.get("region") == "inside_cutout":
            return [(-cut2, cut2)]
        if cut2 and L["name"] in ("board", "bga"):
            return [(-half, -cut2), (cut2, half)]          # the PCB opening
        return [(-half, half)]

    for L in layers:
        col = _layer_style(L["name"])
        for a, b in spans(L):
            yt, yb = Zp(L["z1_um"]), Zp(L["z0_um"])
            if L["name"] == "bga":
                o.append(FS.rect(Xp(a), yt, (b - a) * kx, yb - yt, "#f4f5f7", FS.LINE, 0.5))
                span = (b - a) * kx
                d = min((yb - yt) * 0.8, span * 0.8, 14.0)
                n = max(1, int(span // (d * 1.35)))
                for i in range(n):
                    cx = Xp(a) + (i + 0.5) * span / n
                    o.append(f'<circle cx="{cx:.2f}" cy="{(yt + yb) / 2:.2f}" r="{d / 2:.2f}" '
                             f'fill="{col}" stroke="{FS.MUTED}" stroke-width="0.6"/>\n')
            else:
                o.append(FS.rect(Xp(a), yt, (b - a) * kx, max(yb - yt, 0.7), col, FS.INK, 0.35))
    zs = Zp(0.0)
    o.append(f'<line x1="{Xp(-half) - 18:.2f}" y1="{zs:.2f}" x2="{Xp(half) + 2:.2f}" '
             f'y2="{zs:.2f}" stroke="{FS.I48}" stroke-width="4"/>\n')
    ex, ey = Xp(-half) - 18, y0 - 8
    o.append(f'<ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="10" ry="6" fill="#ffffff" '
             f'stroke="{FS.INK}" stroke-width="1.3"/><circle cx="{ex:.1f}" cy="{ey:.1f}" '
             f'r="2.8" fill="{FS.INK}"/>\n')
    o.append(FS.arrow([(ex, ey + 9), (ex, zs - 5)], "48", 2.2))

    def grp(names):
        Ls = [L for L in layers if L["name"] in names]
        return min(L["z0_um"] for L in Ls), max(L["z1_um"] for L in Ls)

    def zr(a, b):
        return f"{num(a, 0)}…{num(b, 0)} µm"
    conv = [L["name"] for L in layers if L["name"].startswith(("z1conv_", "conv_"))]
    conv_right = max(b for n in conv for a, b in spans(next(L for L in layers
                                                            if L["name"] == n)))
    # (label, z-range, right edge of the layer in mm -- the leader ends ON that layer)
    items = [("compute die", grp(["die"]), die2),
             ("Si substrate + TSVs", grp(["sub_lower", "tile_band"]), half),
             (("converter (in opening)" if cut2 else "converter tiers"), grp(conv), conv_right),
             (("BGA (outside opening)" if cut2 else "BGA balls"), grp(["bga"]), half),
             (("PCB (%g mm opening)" % (2 * cut2) if cut2 else "PCB"), grp(["board"]), half)]
    labs = [(n, (Zp(a) + Zp(b)) / 2, zr(a, b), False, xr) for n, (a, b), xr in items]
    labs.append(("48 V RDL sheet", zs, "z = 0 µm · this plan view", True, half))
    labs.sort(key=lambda t: t[1])
    pos = _place_labels([t[1] for t in labs], y0 + 6, y0 + h - 6, 33.0)
    for (name, yf, sub_t, hot, xr), yl in zip(labs, pos):
        c = FS.I48 if hot else FS.MUTED
        xf = Xp(xr) - (3 if xr < half else -3)
        o.append(f'<polyline points="{xf:.1f},{yf:.1f} {x0 + w + 8:.1f},{yf:.1f} '
                 f'{label_x - 14:.1f},{yl - 6:.1f} {label_x - 5:.1f},{yl - 6:.1f}" '
                 f'fill="none" stroke="{c}" stroke-width="{1.6 if hot else 1}"/>'
                 f'<circle cx="{xf:.1f}" cy="{yf:.1f}" r="2.2" fill="{c}"/>\n')
        o.append(FS.text(label_x, yl - 1, name, 14, weight="bold" if hot else "normal",
                         fill=FS.I48 if hot else FS.INK, halo=False))
        o.append(FS.text(label_x, yl + 14, sub_t, 13, fill=FS.MUTED, halo=False))
    return "".join(o), {"z_range_um": [zlo, zhi], "kz_px_per_um": kz, "kx_px_per_mm": kx,
                        "z_exaggeration": kz * 1000.0 / kx}


def _sci(v, nd=3):
    """'2.04 x 10^4' with a Unicode superscript exponent."""
    e = int(math.floor(math.log10(abs(v))))
    sup = str(e).translate(str.maketrans("-0123456789", "⁻⁰¹²³"
                                         "⁴⁵⁶⁷⁸⁹"))
    return f"{v / 10 ** e:.{nd - 1}f} × 10{sup}"


def _leader_path(X, Y, path_mm, lines, at_mm, anchor, fill, size=14, weight="normal"):
    """A leader routed through `path_mm` (label end first, feature last -- dotted) with the
    text `lines` stacked from the first baseline at `at_mm`."""
    pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in path_mm)
    o = [f'<polyline points="{pts}" fill="none" stroke="{FS.MUTED}" stroke-width="1.1"/>\n',
         f'<circle cx="{X(path_mm[-1][0]):.1f}" cy="{Y(path_mm[-1][1]):.1f}" r="2.4" '
         f'fill="{FS.MUTED}"/>\n']
    for i, t in enumerate(lines):
        o.append(FS.text(X(at_mm[0]), Y(at_mm[1]) + i * (size + 3), t, size, anchor, weight,
                         fill))
    return "".join(o)


def explained_svg(arch, G):
    g, ctx = G["geometry"], G["context"]
    W, H = 1100, 1000
    PX, PY, PS, HWE = 70, 112, 660, 15.6
    s = PS / (2 * HWE)
    X = lambda x: PX + (x + HWE) * s                                     # noqa: E731
    Y = lambda y: PY + (HWE - y) * s                                     # noqa: E731
    half = g["sheet"]["outline_mm"][2][0]
    r = g["ball_diameter_mm"] / 2
    tile = g["cells"]["side_mm"]
    ncell = len(g["cells"]["centres_mm"])
    die = ctx["die_footprint_mm"]
    cut = g["cutout"]
    N = g["matched_count_per_rail"]
    sup, ret = g["rails"]["supply"], g["rails"]["return"]
    npad = len(sup["pads_mm"])
    a_pad = sup["pads_mm"][0][2]
    col = FS.Z1 if arch == "Z1" else FS.Z2
    label = ctx["architecture_label"].replace(" -- ", " — ")
    title = f"Package 48 V RDL model — {arch}"
    o = [FS.svg_open(W, H, title,
                     f"{label}. Plan view of the copper sheet the 2-D solver sees; geometry "
                     f"from problem(), geometry_hash {G['geometry_hash']}",
                     extra=(f'data-geometry-hash="{G["geometry_hash"]}" data-arch="{arch}" '
                            f'data-supply-rail-hash="{G["rail_hashes"]["supply"]}"'))]
    o.append(f'<g font-family="{QFONT}">\n')
    # ------------------------------------------------------------- header
    o.append(FS.rect(22, 20, 58, 40, col, col, 1, 'rx="7"'))
    o.append(FS.text(51, 49, arch, 25, "middle", "bold", "#ffffff", halo=False))
    o.append(FS.text(96, 44, "Package 48 V RDL — the copper sheet the 2-D solver sees",
                     25, weight="bold", halo=False))
    sub_t = label + (" · no PCB opening" if not cut else
                     f" ({cut['side_mm']:g} mm)")
    o.append(FS.text(96, 72, sub_t, 16, fill=FS.MUTED, halo=False))
    o.append(FS.text(96, 95, "Plan view, to scale; every shape from problem() of the MOOSE "
                     f"reference · geometry hash {G['geometry_hash'][:12]}…", 14,
                     fill=FS.MUTED, halo=False))
    # ------------------------------------------------------------- plan view
    o.append(FS.rect(X(-half), Y(half), 2 * half * s, 2 * half * s, FS.MAT["rdl"], FS.INK, 1.6,
                     'fill-opacity="0.16"'))
    if cut:
        c2 = cut["side_mm"] / 2
        o.append(FS.rect(X(-c2), Y(c2), 2 * c2 * s, 2 * c2 * s, FS.OPEN, FS.OPEN, 1.8,
                         'fill-opacity="0.045" stroke-dasharray="9,5"'))
    for x, y in g["cells"]["centres_mm"]:
        o.append(FS.rect(X(x - tile / 2), Y(y + tile / 2), tile * s, tile * s, "none",
                         "#8c959f", 0.8))
    o.append(FS.rect(X(-die / 2), Y(die / 2), die * s, die * s, "none", FS.INK, 1.4,
                     'stroke-dasharray="10,6"'))
    arrows = []
    if arch == "Z1":
        rs = max(math.hypot(*p) for p in sup["balls_mm"]) + 0.6
        for k in range(8):
            t = math.radians(22.5 + 45 * k)
            r1 = 8.4 if k % 2 == 0 else 7.4
            arrows.append([(rs * math.cos(t), rs * math.sin(t)),
                           (r1 * math.cos(t), r1 * math.sin(t))])
        tag = (8.2, 3.9, "start")
    else:
        for ux, uy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            vx, vy = -uy, ux
            for off in (0.0, 2.6, -2.6):
                a = (11.1 * ux + off * vx, 11.1 * uy + off * vy)
                b = (7.3 * ux + 1.45 * off * vx, 7.3 * uy + 1.45 * off * vy)
                arrows.append([a, b])
        tag = (-4.3, 9.75, "end")
    for a, b in arrows:
        o.append(FS.arrow([(X(a[0]), Y(a[1])), (X(b[0]), Y(b[1]))], "48", 2.2,
                          'stroke-opacity="0.92"'))
    o.append(FS.text(X(tag[0]), Y(tag[1]), "schematic", 14, tag[2], fill=FS.I48,
                     extra='font-style="italic"'))
    for x, y in ret["balls_mm"]:
        o.append(_ball(X(x), Y(y), r * s, "return"))
    for x, y in sup["balls_mm"]:
        o.append(_ball(X(x), Y(y), r * s, "supply"))
    for x, y, c in ret["pads_mm"]:
        o.append(_pad(X(x), Y(y), c * s, "return"))
    for x, y, c in sup["pads_mm"]:
        o.append(_pad(X(x), Y(y), c * s, "supply"))
    for v in range(-15, 16, 5):
        o.append(f'<line x1="{X(v):.1f}" y1="{Y(-half) + 2:.1f}" x2="{X(v):.1f}" '
                 f'y2="{Y(-half) + 8:.1f}" stroke="{FS.INK}"/>'
                 f'<line x1="{X(-half) - 8:.1f}" y1="{Y(v):.1f}" x2="{X(-half) - 2:.1f}" '
                 f'y2="{Y(v):.1f}" stroke="{FS.INK}"/>\n')
        o.append(FS.text(X(v), Y(-half) + 24, num(v, 0), 14, "middle", halo=False))
        o.append(FS.text(X(-half) - 11, Y(v) + 5, num(v, 0), 14, "end", halo=False))
    o.append(FS.text(X(half), Y(-half) + 42, "x (mm)", 14, "end", fill=FS.MUTED, halo=False))
    o.append(FS.text(X(-half) - 11, Y(half) - 12, "y (mm)", 14, "end", fill=FS.MUTED,
                     halo=False))
    o.append(FS.text(X(0), Y(14.05), f"package substrate {2 * half:g} × {2 * half:g} mm "
                     "= extent of the 48 V RDL sheet", 14, "middle", fill=FS.INK))
    o.append(_explained_labels(arch, g, ctx, X, Y))
    o.append(FS.scale_bar(X(-2.5), Y(-14.45), 5 * s, "5 mm", 14))
    # ------------------------------------------------------------- equation box
    bx, by = 20, 826
    o.append(FS.rect(bx, by, 712, 164, "#f6f8fa", FS.LINE, 1, 'rx="6"'))
    o.append(FS.text(bx + 14, by + 24, "What the solver computes — the same problem in "
                     "the production FV solver and in MOOSE", 16, weight="bold", halo=False))
    o.append(_rich(bx + 14, by + 56, [(MINUS + "∇·(σ", ""), ("s", "sub"),
                                      (" ∇V) + g", ""), ("a", "sub"),
                                      (" V [balls]  =  " + MINUS + f"(I/{npad}) / A", ""),
                                      ("pad", "sub"),
                                      (" [pads],    ∂V/∂n = 0 on the sheet edge", "")],
                   19))
    sig, ga = g["sheet"]["sigma_s_S"], g["g_a_S_per_mm2"]
    sc = ctx["sheet_construction"]
    o.append(_rich(bx + 14, by + 86, [("σ", ""), ("s", "sub"),
                                      (f" = 1/R", ""), ("sq", "sub"),
                                      (f" = {sig:.1f} S  ({sc['t_cu_mm'] * 1e3:g} µm Cu at "
                                       f"{sc['occupancy'] * 100:g} % occupancy)   ·   g", ""),
                                      ("a", "sub"),
                                      (f" = {_sci(ga)} S/mm²  (ball + contact, to the rail)",
                                       "")], 15))
    o.append(_rich(bx + 14, by + 111, [(f"I = {g['i_total_A']:g} A in total, I/{npad} per VIN "
                                        "pad (A", ""), ("pad", "sub"),
                                       (f" = {a_pad:g} × {a_pad:g} mm)   ·   V = "
                                        "potential relative to the 48 V rail (V ≤ 0)", "")],
                   15))
    o.append(_rich(bx + 14, by + 136, [("MOOSE heat_transfer-opt solves it as ∇·(k∇T) = "
                                        + MINUS + "q with k ↔ σ", ""), ("s", "sub"),
                                       (", T ↔ V (reference run: supply rail).", "")], 15))
    o.append(FS.text(bx + 14, by + 156, "The return rail is the same model with the return "
                     "balls and return pads.", 14, fill=FS.MUTED, halo=False))
    # ------------------------------------------------------------- legend
    lx, ly = 768, 112
    o.append(FS.rect(lx - 10, ly, 330, 292, "#ffffff", FS.LINE, 1, 'rx="6"'))
    o.append(FS.text(lx, ly + 24, "Legend", 16, weight="bold", halo=False))
    o.append(FS.text(lx + 64, ly + 24, f"{N} BGA balls per rail (matched)", 15,
                     weight="bold", fill=FS.I48, halo=False))
    rows = [
        ("sheet", f"48 V RDL copper sheet ({2 * half:g} × {2 * half:g} mm)"),
        ("supply", f"48 V supply BGA ball, Ø {g['ball_diameter_mm']:g} mm"),
        ("return", "return BGA ball"),
        ("vin", f"converter VIN pad, {a_pad:g} mm: draws I/{npad}"),
        ("rpad", "converter return pad"),
        ("cell", f"converter cell, {tile:.2f} mm ({int(round(ncell ** 0.5))} × "
                 f"{int(round(ncell ** 0.5))})"),
        ("die", f"compute-die footprint, {die:g} mm"),
        ("cut", (f"PCB opening, {cut['side_mm']:g} mm" if cut else "no PCB opening in Z1")),
        ("arrow", "current path (schematic)"),
    ]
    for i, (kind, txt) in enumerate(rows):
        cy = ly + 52 + i * 27
        cx = lx + 12
        if kind == "sheet":
            o.append(FS.rect(cx - 10, cy - 8, 20, 16, FS.MAT["rdl"], FS.INK, 1.2,
                             'fill-opacity="0.16"'))
        elif kind in ("supply", "return"):
            o.append(_ball(cx, cy, 6.5, kind, 1.4))
        elif kind in ("vin", "rpad"):
            o.append(_pad(cx, cy, 9, "supply" if kind == "vin" else "return", 1.4))
        elif kind == "cell":
            o.append(FS.rect(cx - 9, cy - 9, 18, 18, "none", "#8c959f", 1.1))
        elif kind == "die":
            o.append(f'<line x1="{cx - 11}" y1="{cy}" x2="{cx + 11}" y2="{cy}" '
                     f'stroke="{FS.INK}" stroke-width="1.6" stroke-dasharray="6,3"/>\n')
        elif kind == "cut" and cut:
            o.append(FS.rect(cx - 10, cy - 8, 20, 16, FS.OPEN, FS.OPEN, 1.6,
                             'fill-opacity="0.06" stroke-dasharray="5,3"'))
        elif kind == "arrow":
            o.append(FS.arrow([(cx - 12, cy), (cx + 12, cy)], "48", 2.2))
        o.append(FS.text(lx + 32, cy + 5, txt, 14, fill=FS.INK if (kind != "cut" or cut)
                         else FS.MUTED, halo=False))
    # ------------------------------------------------------------- stack inset
    iy = 436
    o.append(FS.text(lx - 6, iy, "Where this sheet sits (cross-section)", 16, weight="bold",
                     halo=False))
    ins, info = stack_inset(arch, lx + 22, iy + 36, 104, 420, lx + 150)
    o.append(ins)
    # one <text> element, so the caption is one searchable string
    o.append(f'<text x="{lx - 6}" y="{iy + 494}" font-size="15" font-weight="bold" '
             f'fill="{FS.I48}"><tspan x="{lx - 6}" dy="0">{FS.esc(CAPTION[:35])}</tspan>'
             f'<tspan x="{lx - 6}" dy="19">{FS.esc(CAPTION[35:])}</tspan></text>\n')
    o.append(FS.text(lx - 6, iy + 534, f"z stretched ×{info['z_exaggeration']:.0f} relative to x; "
                     "sheet line thickened", 13, fill=FS.MUTED, halo=False))
    o.append("</g>\n")
    o.append(FS.svg_close())
    return "".join(o), info


def _explained_labels(arch, g, ctx, X, Y):
    """Leader labels with routes chosen so no leader crosses a ball (checked in
    _leader_clearance); feature points are real geometry from problem()."""
    sup, ret = g["rails"]["supply"], g["rails"]["return"]
    N = g["matched_count_per_rail"]
    npad = len(sup["pads_mm"])
    die = ctx["die_footprint_mm"]

    def find(pts, x, y):
        p = min(pts, key=lambda q: math.hypot(q[0] - x, q[1] - y))
        assert math.hypot(p[0] - x, p[1] - y) < 1e-6, f"no terminal at ({x}, {y})"
        return p[0], p[1]

    specs = []
    pad = find(sup["pads_mm"], -7.39633, -10.561573)
    specs.append(([(-8.25, -12.5), pad], ["VIN pad (1 of %d):" % npad, "one per converter cell"],
                  (-14.7, -12.75), "start", FS.INK, "normal"))
    if arch == "Z1":
        b = find(sup["balls_mm"], 0.0, 3.2)
        specs.append(([(-3.35, 12.35), b], [f"48 V supply: {N} BGA balls"], (-3.6, 12.2),
                      "end", FS.I48, "bold"))
        rb = find(ret["balls_mm"], 1.6, 4.0)
        specs.append(([(3.35, 12.35), rb], [f"return: {N} BGA balls (ring)"], (3.6, 12.2),
                      "start", FS.IRET, "bold"))
        specs.append(([(7.45, -12.45), (8.2, -die / 2)], ["compute-die footprint",
                                                          f"{die:g} mm (projected)"],
                      (14.7, -12.75), "end", FS.INK, "normal"))
    else:
        b = find(sup["balls_mm"], -12.8, 0.8)
        specs.append(([(-14.4, 11.55), (-14.4, 0.8), b], ["48 V supply:", f"{N} BGA balls"],
                      (-14.7, 12.95), "start", FS.I48, "bold"))
        rb = find(ret["balls_mm"], 13.6, 0.0)
        specs.append(([(14.4, 11.55), (14.4, 0.0), rb], ["return:", f"{N} BGA balls"],
                      (14.7, 12.95), "end", FS.IRET, "bold"))
        c2 = g["cutout"]["side_mm"] / 2
        specs.append(([(7.1, -12.45), (8.6, -c2)], [f"PCB opening {2 * c2:g} mm:",
                                                     "no BGA balls inside"],
                      (14.7, -12.75), "end", FS.OPEN, "normal"))
    _leader_clearance(g, [sp[0] for sp in specs])
    return "".join(_leader_path(X, Y, path, lines, at, anchor, fill, 14, w)
                   for path, lines, at, anchor, fill, w in specs)


def _leader_clearance(g, paths, margin=0.03):
    """Assert that no leader passes over a ball it does not point at."""
    r = g["ball_diameter_mm"] / 2
    balls = [tuple(b) for rail in RAILS for b in g["rails"][rail]["balls_mm"]]
    for path in paths:
        end = tuple(path[-1])
        for (ax, ay), (bx, by) in zip(path[:-1], path[1:]):
            for cx, cy in balls:
                if math.hypot(cx - end[0], cy - end[1]) < 1e-9:
                    continue
                dx, dy = bx - ax, by - ay
                t = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / (dx * dx + dy * dy)))
                d = math.hypot(ax + t * dx - cx, ay + t * dy - cy)
                if d < r + margin:
                    raise AssertionError(f"leader {path} crosses ball ({cx}, {cy}): {d:.3f} mm")


def run_explained(geoms):
    FIGS.mkdir(parents=True, exist_ok=True)
    for arch in ARCHS:
        G = geoms[arch]
        svg, info = explained_svg(arch, G)
        f = FIGS / f"rdl_model_explained_{arch}.svg"
        f.write_text(svg)
        print(f"[explained] {arch}: {rel(f)} (z exaggeration x{info['z_exaggeration']:.1f})")


# ===================================================================== render =====
W_R, H_R = 1100, 1000
FIELD = {"x": 74, "y": 116, "size": 716, "half": 15.4}        # px; world window +-half mm
CBAR = {"x": 826, "y": 178, "w": 28, "h": 320}
ARROW_SPACING_MM = 2.0
ARROW_EXCLUDE_MM = 0.55          # no arrow within this distance of a ball or pad centre
ARROW_MIN_FRAC_P95 = 0.01        # omit arrows where |grad V| < 1 % of its 95th percentile
CREDIT = ("MOOSE heat_transfer-opt (INL) — DC-conduction analogue; rendered with VTK "
          "{vtk}")


def _rsvg():
    exe = shutil.which("rsvg-convert")
    if not exe:
        raise RuntimeError("rsvg-convert is required to rasterise the annotation layer")
    ver = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.split()
    return exe, (ver[2] if len(ver) > 2 else "unknown")


def read_exodus_last(exo):
    """The Exodus file at its LAST stored step, variable V selected by name."""
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkExodusIIReader()
    r.SetFileName(str(exo))
    r.UpdateInformation()
    names = [r.GetPointResultArrayName(i) for i in range(r.GetNumberOfPointResultArrays())]
    if "V" not in names:
        raise RuntimeError(f"{exo}: no nodal variable V (has {names})")
    for nm in names:
        r.SetPointResultArrayStatus(nm, 1 if nm == "V" else 0)
    r.SetAllArrayStatus(vtk.vtkExodusIIReader.GLOBAL, 1)
    nts = r.GetNumberOfTimeSteps()
    info = r.GetExecutive().GetOutputInformation(0)
    key = vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS()
    times = [info.Get(key, i) for i in range(info.Length(key))]

    def blocks_at(step):
        r.SetTimeStep(step)
        r.Update()
        eb = r.GetOutput().GetBlock(0)
        out = {}
        for i in range(eb.GetNumberOfBlocks()):
            ds = eb.GetBlock(i)
            out[eb.GetMetaData(i).Get(vtk.vtkCompositeDataSet.NAME())] = ds
        return out

    b0 = blocks_at(0)
    v0 = np.concatenate([vtk_to_numpy(d.GetPointData().GetArray("V")) for d in b0.values()])
    step = nts - 1
    B = blocks_at(step)                      # the reader now sits on the last step
    V = np.concatenate([vtk_to_numpy(d.GetPointData().GetArray("V")) for d in B.values()])
    if not np.ptp(V) > 0:
        raise RuntimeError(f"{exo}: V is uniform at step {step} -- not a solved state")
    return r, B, {"n_steps": nts, "step": step, "times": times, "time": times[step],
                  "step0_min": float(v0.min()), "step0_max": float(v0.max()),
                  "vmin": float(V.min()), "vmax": float(V.max())}


def _tri_arrays(ds):
    from vtk.util.numpy_support import vtk_to_numpy
    P = vtk_to_numpy(ds.GetPoints().GetData()).astype(float)[:, :2]
    T = vtk_to_numpy(ds.GetCells().GetConnectivityArray()).reshape(-1, 3) \
        if hasattr(ds, "GetCells") else vtk_to_numpy(ds.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    V = vtk_to_numpy(ds.GetPointData().GetArray("V")).astype(float)
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    area = 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
    return P, T, V, area, (a + b + c) / 3.0, V[T].mean(axis=1)


def verify_against_solve(arch, G, B, meta, exo):
    """The rendered file IS the reference run: mesh, blocks, constants and pad averages."""
    import csv
    import vtk
    wd = exo.parent
    deck = (wd / "rdl.i").read_text()
    msh = re.search(r"file = (\S+)", deck).group(1)
    tag = re.search(r"rdl_(m\d)\.msh$", msh).group(1)
    ref = json.loads((FC / f"reference_pkg_rdl_moose_{arch}.json").read_text())
    g = G["geometry"]
    sup = g["rails"]["supply"]
    nb, npd = len(sup["balls_mm"]), len(sup["pads_mm"])
    want = {f"ball{i}" for i in range(nb)} | {f"pad{i}" for i in range(npd)} | {"sheet"}
    if set(B) != want:
        raise RuntimeError(f"Exodus blocks {sorted(set(B) ^ want)[:6]} differ from the geometry")
    deck_balls = re.search(r"\[contact\].*?block = '([^']*)'", deck, re.S).group(1).split()
    deck_pads = re.search(r"\[draw\].*?block = '([^']*)'", deck, re.S).group(1).split()
    assert deck_balls == [f"ball{i}" for i in range(nb)] and \
        deck_pads == [f"pad{i}" for i in range(npd)], "rdl.i blocks differ"
    rate = float(re.search(r"rate = ([0-9.eE+-]+)", deck).group(1))
    val = float(re.search(r"value = ([0-9.eE+-]+)", deck).group(1))
    kk = float(re.search(r"prop_values = '([0-9.eE+-]+)'", deck).group(1))
    i_pad = g["i_total_A"] / npd
    a_pad = sup["pads_mm"][0][2] ** 2
    for got, exp, nm in ((rate, g["g_a_S_per_mm2"], "g_a"), (val, -i_pad / a_pad, "draw"),
                         (kk, g["sheet"]["sigma_s_S"], "sigma_s")):
        if abs(got - exp) > 1e-9 * abs(exp):
            raise RuntimeError(f"rdl.i {nm} = {got} but problem() gives {exp}")
    ntri = sum(d.GetNumberOfCells() for d in B.values())
    types = {d.GetCellType(j) for d in B.values() for j in range(min(3, d.GetNumberOfCells()))}
    if ntri != ref["moose"][tag]["n_elements"]:
        raise RuntimeError(f"Exodus has {ntri} cells, {tag} mesh had {ref['moose'][tag]['n_elements']}")
    if types != {vtk.VTK_TRIANGLE}:
        raise RuntimeError(f"unexpected cell types {types}")
    # block geometry vs problem() (Exodus coordinates are float32)
    r = g["ball_diameter_mm"] / 2
    off_b, off_p, area_b, area_p = 0.0, 0.0, [], []
    for i, (x, y) in enumerate(sup["balls_mm"]):
        _, _, _, ar, cen, _ = _tri_arrays(B[f"ball{i}"])
        cx, cy = (ar[:, None] * cen).sum(0) / ar.sum()
        off_b = max(off_b, math.hypot(cx - x, cy - y))
        area_b.append(ar.sum())
    vcsv = None
    rows = list(csv.DictReader((wd / "rdl_out.csv").open()))
    vcsv = np.array([float(rows[-1][f"v{i}"]) for i in range(npd)])
    rec = []
    for i, (x, y, c) in enumerate(sup["pads_mm"]):
        _, _, _, ar, cen, vm = _tri_arrays(B[f"pad{i}"])
        cx, cy = (ar[:, None] * cen).sum(0) / ar.sum()
        off_p = max(off_p, math.hypot(cx - x, cy - y))
        area_p.append(ar.sum() - c * c)
        rec.append((ar * vm).sum() / ar.sum())
    rec = np.array(rec)
    fd = B["sheet"].GetFieldData()
    vg = np.array([fd.GetArray(f"v{i}").GetValue(fd.GetArray(f"v{i}").GetNumberOfTuples() - 1)
                   for i in range(npd)])
    r_eff_csv = float(np.sum(i_pad * np.abs(vcsv)))
    m = ref["moose"][tag]
    out = {
        "rdl_i_mesh_file": msh, "rdl_i_mesh_file_exists": Path(msh).exists(),
        "mesh_tag": tag, "reference_json_n_elements": m["n_elements"],
        "exodus_n_triangles": ntri, "cell_type": "VTK_TRIANGLE (linear, 3-node)",
        "blocks": {"ball": nb, "pad": npd, "sheet": 1},
        "rdl_i_constants_equal_problem": True,
        "ball_block_centroid_max_offset_mm": off_b,
        "pad_block_centroid_max_offset_mm": off_p,
        "ball_block_area_rel_deficit_max": float(max(1 - a / (math.pi * r * r) for a in area_b)),
        "pad_block_area_max_abs_err_mm2": float(np.max(np.abs(area_p))),
        "exodus_globals_vs_csv_max_abs_V": float(np.max(np.abs(vg - vcsv))),
        "pad_average_recomputed_from_nodal_V_max_rel_err": float(np.max(np.abs(rec - vcsv) / np.abs(vcsv))),
        "R_eff_from_csv_ohm": r_eff_csv, "reference_json_R_eff_ohm": m["R_eff_ohm"],
        "max_pad_drop_from_csv_V": float(np.max(np.abs(vcsv))),
        "reference_json_max_pad_drop_V": m["max_pad_drop_V"],
        "worst_pad_index": int(np.argmax(np.abs(vcsv))),
        "worst_pad_mm": sup["pads_mm"][int(np.argmax(np.abs(vcsv)))][:2]}
    # float32 coordinates in the Exodus bound the centroid and area tolerances
    assert off_b < 1e-5 and off_p < 1e-5, (off_b, off_p)
    assert out["pad_block_area_max_abs_err_mm2"] < 1e-6
    assert out["ball_block_area_rel_deficit_max"] < 1e-3          # inscribed polygon
    assert out["exodus_globals_vs_csv_max_abs_V"] < 1e-15
    assert out["pad_average_recomputed_from_nodal_V_max_rel_err"] < 1e-6
    if r_eff_csv != m["R_eff_ohm"] or out["max_pad_drop_from_csv_V"] != m["max_pad_drop_V"]:
        raise RuntimeError(f"{arch}: CSV ({r_eff_csv}, {out['max_pad_drop_from_csv_V']}) does "
                           f"not reproduce the reference JSON ({m['R_eff_ohm']}, {m['max_pad_drop_V']})")
    return out


def _viridis_lut(vmin, vmax):
    import vtk
    import matplotlib
    cols = np.asarray(matplotlib.colormaps["viridis"].colors, float)
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(len(cols))
    lut.SetTableRange(vmin, vmax)
    lut.Build()                  # documented order: Build(), then load the explicit table
    for i, (r_, g_, b_) in enumerate(cols):
        lut.SetTableValue(i, r_, g_, b_, 1.0)
    return lut, cols


def _mapper(port_or_data, lut, vmin, vmax):
    import vtk
    m = vtk.vtkPolyDataMapper()
    if isinstance(port_or_data, vtk.vtkPolyData):
        m.SetInputData(port_or_data)
    else:
        m.SetInputConnection(port_or_data)
    m.SetScalarModeToUsePointFieldData()
    m.SelectColorArray("V")
    m.SetLookupTable(lut)
    m.SetScalarRange(vmin, vmax)
    m.UseLookupTableScalarRangeOn()
    m.InterpolateScalarsBeforeMappingOn()          # colour = LUT(V) per pixel, not RGB blend
    m.ScalarVisibilityOn()
    return m


def _viewport(x, y, w, h):
    return (x / W_R, (H_R - y - h) / H_R, (x + w) / W_R, (H_R - y) / H_R)


def _camera(ren, cx, cy, half_h):
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    cam.SetFocalPoint(cx, cy, 0.0)
    cam.SetPosition(cx, cy, 50.0)
    cam.SetViewUp(0.0, 1.0, 0.0)
    cam.SetParallelScale(half_h)
    cam.SetClippingRange(1.0, 100.0)


def _grab(rw):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    a = vtk_to_numpy(w2i.GetOutput().GetPointData().GetScalars())
    return a.reshape(H_R, W_R, 3)[::-1].copy()


def vtk_render(reader, B, vmin, vmax):
    """Field + colour bar through ONE colouring path; returns the image and checks."""
    import vtk
    gf = vtk.vtkCompositeDataGeometryFilter()
    gf.SetInputConnection(reader.GetOutputPort())
    gf.Update()
    poly = gf.GetOutput()
    lut, cols = _viridis_lut(vmin, vmax)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(W_R, H_R)
    rw.SetMultiSamples(0)
    bg = vtk.vtkRenderer()
    bg.SetBackground(1, 1, 1)
    bg.SetViewport(0, 0, 1, 1)
    rw.AddRenderer(bg)
    F = FIELD
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    ren.SetViewport(*_viewport(F["x"], F["y"], F["size"], F["size"]))
    act = vtk.vtkActor()
    act.SetMapper(_mapper(gf.GetOutputPort(), lut, vmin, vmax))
    act.GetProperty().LightingOff()                 # unshaded: pixel colour = LUT colour
    ren.AddActor(act)
    _camera(ren, 0.0, 0.0, F["half"])
    rw.AddRenderer(ren)
    # colour bar: a plane whose V runs linearly from vmin (bottom) to vmax (top)
    C = CBAR
    asp = C["w"] / C["h"]
    pl = vtk.vtkPlaneSource()
    pl.SetOrigin(0, 0, 0)
    pl.SetPoint1(asp, 0, 0)
    pl.SetPoint2(0, 1, 0)
    pl.SetResolution(1, 1)
    pl.Update()
    bar = pl.GetOutput()
    from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
    py = vtk_to_numpy(bar.GetPoints().GetData())[:, 1].astype(float)
    sv = numpy_to_vtk(vmin * (1.0 - py) + vmax * py, deep=True)   # exact at both ends
    sv.SetName("V")
    bar.GetPointData().AddArray(sv)
    cren = vtk.vtkRenderer()
    cren.SetBackground(1, 1, 1)
    cren.SetViewport(*_viewport(C["x"], C["y"], C["w"], C["h"]))
    cact = vtk.vtkActor()
    cact.SetMapper(_mapper(bar, lut, vmin, vmax))
    cact.GetProperty().LightingOff()
    cren.AddActor(cact)
    _camera(cren, asp / 2, 0.5, 0.5)
    rw.AddRenderer(cren)
    img = _grab(rw)
    # ---- checks on what VTK actually did
    bar_range = (float(np.min(vtk_to_numpy(sv))), float(np.max(vtk_to_numpy(sv))))
    assert lut.GetRange() == (vmin, vmax) and bar_range == (vmin, vmax), \
        (lut.GetRange(), bar_range, vmin, vmax)
    assert act.GetMapper().GetScalarRange() == (vmin, vmax)
    # the table is still viridis after rendering (VTK stores it as 8-bit RGBA, hence the
    # half-level tolerance); a rebuilt default hue ramp would differ by ~0.5-1.0
    tab = np.array([lut.GetTableValue(i)[:3] for i in range(lut.GetNumberOfTableValues())])
    assert tab.shape == cols.shape and np.max(np.abs(tab - cols)) <= 0.5 / 255 + 1e-9
    s = F["size"] / (2 * F["half"])
    coord = vtk.vtkCoordinate()
    coord.SetCoordinateSystemToWorld()
    cam_err = 0.0
    for x, y in ((-15, -15), (15, 15), (-15, 15), (15, -15), (0, 0), (7.3, -4.1)):
        coord.SetValue(x, y, 0.0)
        dx, dy = coord.GetComputedDoubleDisplayValue(ren)
        ex, ey = F["x"] + (x + F["half"]) * s, F["y"] + (F["half"] - y) * s
        cam_err = max(cam_err, abs(dx - ex), abs((H_R - dy) - ey))
    assert cam_err < 0.01, f"VTK camera disagrees with the overlay transform by {cam_err} px"
    return img, {"rw": rw, "ren": ren, "poly": poly, "lut": lut, "cols": cols,
                 "field_actor": act, "bar_actor": cact, "bar_renderer": cren,
                 "camera_vs_overlay_max_px": cam_err, "window_class": rw.GetClassName(),
                 "colour_bar_range_V": bar_range}


def registration_check(R_, B, G):
    """Render the Exodus BALL and PAD blocks themselves through the SAME camera and compare
    their pixel centroids with problem() centres pushed through the overlay transform."""
    import vtk
    rw, ren = R_["rw"], R_["ren"]
    R_["field_actor"].VisibilityOff()
    R_["bar_actor"].VisibilityOff()
    acts = []
    for kind, rgb in (("ball", (1, 0, 0)), ("pad", (0, 1, 0))):
        app = vtk.vtkAppendPolyData()
        for name, ds in B.items():
            if re.fullmatch(kind + r"\d+", name):
                gfl = vtk.vtkGeometryFilter()
                gfl.SetInputData(ds)
                gfl.Update()
                app.AddInputData(gfl.GetOutput())
        app.Update()
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(app.GetOutput())
        m.ScalarVisibilityOff()
        a = vtk.vtkActor()
        a.SetMapper(m)
        a.GetProperty().SetColor(*rgb)
        a.GetProperty().LightingOff()
        ren.AddActor(a)
        acts.append(a)
    ren.SetBackground(0, 0, 0)
    img = _grab(rw)
    for a in acts:
        ren.RemoveActor(a)
    ren.SetBackground(1, 1, 1)
    R_["field_actor"].VisibilityOn()
    R_["bar_actor"].VisibilityOn()
    F = FIELD
    s = F["size"] / (2 * F["half"])
    g = G["geometry"]["rails"]["supply"]
    res = {}
    for kind, ch, pts in (("ball", 0, g["balls_mm"]), ("pad", 1, g["pads_mm"])):
        mask = img[:, :, ch] > 127
        worst, counts = 0.0, []
        for p in pts:
            ex, ey = F["x"] + (p[0] + F["half"]) * s, F["y"] + (F["half"] - p[1]) * s
            x0, x1 = int(ex - 9), int(ex + 10)
            y0, y1 = int(ey - 9), int(ey + 10)
            sub = mask[y0:y1, x0:x1]
            yy, xx = np.nonzero(sub)
            if len(xx) == 0:
                raise AssertionError(f"{kind} at {p[:2]} not found in the block render")
            cx, cy = x0 + xx.mean() + 0.5, y0 + yy.mean() + 0.5
            worst = max(worst, math.hypot(cx - ex, cy - ey))
            counts.append(len(xx))
        res[kind] = {"n": len(pts), "max_centroid_offset_px": worst,
                     "mask_px_min_max": [int(min(counts)), int(max(counts))]}
    lim = 0.75                     # sub-pixel: a 5 px pad rasterises to whole pixels
    assert res["ball"]["max_centroid_offset_px"] < lim and \
        res["pad"]["max_centroid_offset_px"] < lim, res
    res["px_per_mm"] = s
    return res


def colour_check(img, R_, vmin, vmax, n=600, seed=7):
    """Rendered pixel colour vs LUT(V) with V interpolated from the mesh at the pixel
    centre; proves the colours are VTK's mapping of the solved field and nothing else."""
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    poly, lut = R_["poly"], R_["lut"]
    P = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)[:, :2]
    T = vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    V = vtk_to_numpy(poly.GetPointData().GetArray("V")).astype(float)
    loc = vtk.vtkStaticCellLocator()
    loc.SetDataSet(poly)
    loc.BuildLocator()
    F = FIELD
    s = F["size"] / (2 * F["half"])
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n):
        while True:
            i = int(rng.integers(F["x"], F["x"] + F["size"]))
            j = int(rng.integers(F["y"], F["y"] + F["size"]))
            x = (i + 0.5 - F["x"]) / s - F["half"]
            y = F["half"] - (j + 0.5 - F["y"]) / s
            if abs(x) < 14.9 and abs(y) < 14.9:
                break
        cid = loc.FindCell([x, y, 0.0])
        a, b, c = P[T[cid]]
        M = np.array([[b[0] - a[0], c[0] - a[0]], [b[1] - a[1], c[1] - a[1]]])
        l1, l2 = np.linalg.solve(M, [x - a[0], y - a[1]])
        v = (1 - l1 - l2) * V[T[cid, 0]] + l1 * V[T[cid, 1]] + l2 * V[T[cid, 2]]
        c3 = [0.0, 0.0, 0.0]
        lut.GetColor(v, c3)
        rgb = 255.0 * np.array(c3, float)
        diffs.append(np.abs(img[j, i].astype(float) - rgb).max())
    d = np.array(diffs)
    out = {"n_pixels": n, "max_abs_rgb_diff": float(d.max()),
           "p95_abs_rgb_diff": float(np.percentile(d, 95)),
           "median_abs_rgb_diff": float(np.median(d)),
           "note": "8-bit levels between each rendered pixel and lut.GetColor(V) with V "
                   "interpolated barycentrically on the mesh at the pixel centre"}
    assert out["p95_abs_rgb_diff"] <= 4 and out["max_abs_rgb_diff"] <= 10, out
    return out, (P, T, V, loc)


def current_arrows(mesh, G):
    """-grad V of the linear (P1) field, per containing triangle, on a regular grid."""
    P, T, V, loc = mesh
    g = G["geometry"]["rails"]["supply"]
    feats = np.array([b[:2] for b in g["balls_mm"]] + [p[:2] for p in g["pads_mm"]], float)
    half = G["geometry"]["sheet"]["outline_mm"][2][0]
    xs = np.arange(-half + ARROW_SPACING_MM / 2, half, ARROW_SPACING_MM)
    pts, grads = [], []
    for x in xs:
        for y in xs:
            if np.min(np.hypot(feats[:, 0] - x, feats[:, 1] - y)) < ARROW_EXCLUDE_MM:
                continue
            cid = loc.FindCell([x, y, 0.0])
            a, b, c = P[T[cid]]
            M = np.array([[b[0] - a[0], b[1] - a[1]], [c[0] - a[0], c[1] - a[1]]])
            gv = np.linalg.solve(M, [V[T[cid, 1]] - V[T[cid, 0]], V[T[cid, 2]] - V[T[cid, 0]]])
            pts.append((x, y))
            grads.append(gv)
    pts, grads = np.array(pts), np.array(grads)
    mag = np.hypot(grads[:, 0], grads[:, 1])
    thr = ARROW_MIN_FRAC_P95 * np.percentile(mag, 95)
    keep = mag >= thr
    u = -grads[keep] / mag[keep, None]
    return pts[keep], u, {"method": "-grad V of the P1 field in the containing triangle",
                          "spacing_mm": ARROW_SPACING_MM, "exclude_near_terminal_mm":
                          ARROW_EXCLUDE_MM, "threshold": f"|grad V| >= {ARROW_MIN_FRAC_P95:g} "
                          "x its 95th percentile over the samples", "threshold_V_per_mm":
                          float(thr), "n_candidates": int(len(mag)),
                          "n_after_threshold": int(keep.sum()), "length": "fixed (direction only)"}


def _arrow_poly(cx, cy, ux, uy, L=22.0, w=2.6, hl=8.5, hw=8.0):
    """A filled arrow centred on (cx, cy) pointing along (ux, uy) in image coordinates."""
    px, py = -uy, ux
    tx, ty = cx + ux * L / 2, cy + uy * L / 2
    bx, by = cx - ux * L / 2, cy - uy * L / 2
    nx, ny = tx - ux * hl, ty - uy * hl
    pts = [(bx + px * w / 2, by + py * w / 2), (nx + px * w / 2, ny + py * w / 2),
           (nx + px * hw / 2, ny + py * hw / 2), (tx, ty), (nx - px * hw / 2, ny - py * hw / 2),
           (nx - px * w / 2, ny - py * w / 2), (bx - px * w / 2, by - py * w / 2)]
    return ('<polygon points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) +
            f'" fill="#ffffff" stroke="{FS.INK}" stroke-width="0.9" stroke-linejoin="round"/>\n')


def _text_box(x, y, s, size, anchor, bold=True):
    """Approximate pixel box of one text line (baseline y)."""
    w = (0.58 if bold else 0.53) * size * len(s)
    x0 = x - w if anchor == "end" else (x - w / 2 if anchor == "middle" else x)
    return (x0 - 6, y - size - 4, x0 + w + 6, y + 6)


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def _render_label_specs(arch, G, chk):
    """(path_mm, stop_mm, lines, at_mm, anchor, colour). The leader is drawn to `stop_mm`
    short of the feature centre so it ends ON the outline and never hides it."""
    g = G["geometry"]
    sup = g["rails"]["supply"]
    N = len(sup["balls_mm"])
    npad = len(sup["pads_mm"])
    r = g["ball_diameter_mm"] / 2
    c = sup["pads_mm"][0][2]
    stop_b, stop_p = r + 0.05, c / math.sqrt(2) + 0.05
    wx, wy = chk["worst_pad_mm"]
    drop = chk["max_pad_drop_from_csv_V"] * 1e3

    def find(pts, x, y):
        p = min(pts, key=lambda q: math.hypot(q[0] - x, q[1] - y))
        assert math.hypot(p[0] - x, p[1] - y) < 1e-6, f"no terminal at ({x}, {y})"
        return p[0], p[1]
    S = []
    if arch == "Z1":
        S.append(([(-3.35, 12.35), find(sup["balls_mm"], 0.0, 3.2)], stop_b,
                  [f"48 V enters: {N} supply balls"], (-3.6, 12.2), "end", FS.INK))
        S.append(([(3.35, 12.35), find(sup["pads_mm"], 5.264641, 8.429883)], stop_p,
                  [f"drawn by {npad} VIN pads, 1/{npad} A each"], (3.6, 12.2), "start", FS.INK))
        S.append(([(-11.9, -12.75), (wx, wy)], stop_p,
                  [f"worst pad: {drop:.3f} mV below the rail", "(pad average)"],
                  (-14.7, -13.3), "start", FS.INK))
    else:
        S.append(([(-14.4, 11.55), (-14.4, 0.8), find(sup["balls_mm"], -12.8, 0.8)], stop_b,
                  ["48 V enters:", f"{N} supply balls"], (-14.7, 12.95), "start", FS.INK))
        S.append(([(11.6, 11.7), find(sup["pads_mm"], 8.429883, 8.429883)], stop_p,
                  ["drawn by", f"{npad} VIN pads,", f"1/{npad} A each"], (14.7, 13.3), "end",
                  FS.INK))
        S.append(([(-8.6, -12.55), (wx, wy)], stop_p,
                  [f"worst pad: {drop:.3f} mV", "below the rail (centre cell)"],
                  (-14.7, -13.0), "start", FS.INK))
        c2 = g["cutout"]["side_mm"] / 2
        S.append(([(9.0, -12.5), (9.6, -c2)], 0.0, [f"PCB opening {2 * c2:g} mm:",
                                                    "no balls inside"], (14.7, -13.0), "end",
                  FS.OPEN))
    _leader_clearance(g, [sp[0] for sp in S])
    return S


def overlay_svg(arch, G, meta, ver, arrows, chk, ref, vtk_version):
    F, C = FIELD, CBAR
    s = F["size"] / (2 * F["half"])
    X = lambda x: F["x"] + (x + F["half"]) * s                         # noqa: E731
    Y = lambda y: F["y"] + (F["half"] - y) * s                         # noqa: E731
    g = G["geometry"]
    half = g["sheet"]["outline_mm"][2][0]
    sup = g["rails"]["supply"]
    r = g["ball_diameter_mm"] / 2
    vmin, vmax = meta["vmin"], meta["vmax"]
    col = FS.Z1 if arch == "Z1" else FS.Z2
    LS = 15                                                  # in-field label size
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_R}" height="{H_R}" '
         f'viewBox="0 0 {W_R} {H_R}" font-family="{QFONT}" '
         f'data-geometry-hash="{G["geometry_hash"]}">\n<defs>{FS.arrow_defs()}</defs>\n']
    # ---------------------------------------------------------------- header
    o.append(FS.rect(22, 18, 58, 40, col, col, 1, 'rx="7"'))
    o.append(FS.text(51, 47, arch, 25, "middle", "bold", "#ffffff", halo=False))
    o.append(FS.text(96, 42, "MOOSE reference field — package 48 V RDL (supply rail)", 25,
                     weight="bold", halo=False))
    o.append(FS.text(96, 68, G["context"]["architecture_label"].replace(" -- ", " — ")
                     + " · copper sheet seen from above", 16, fill=FS.MUTED, halo=False))
    o.append(_rich(96, 94, [("solved: " + MINUS + "∇·(σ", ""), ("s", "sub"),
                            (" ∇V) + g", ""), ("a", "sub"),
                            (" V [balls] = " + MINUS + f"(I/{len(sup['pads_mm'])})/A", ""),
                            ("pad", "sub"),
                            (" [pads],  I = 1 A,  insulated edges", "")], 15, fill=FS.INK))
    # ---------------------------------------------------------------- labels first, so the
    # arrows can be kept out of their boxes and off their leaders
    specs = _render_label_specs(arch, G, chk)
    boxes, segs = [], []
    for path, stop, lines, at, anchor, fill in specs:
        for i, t in enumerate(lines):
            boxes.append(_text_box(X(at[0]), Y(at[1]) + i * (LS + 3), t, LS, anchor))
        pp = [(X(x), Y(y)) for x, y in path]
        segs.extend(zip(pp[:-1], pp[1:]))
    apts, au = arrows
    kept = []
    for (x, y), (ux, uy) in zip(apts, au):
        px, py = X(x), Y(y)
        if any(b[0] - 8 <= px <= b[2] + 8 and b[1] - 8 <= py <= b[3] + 8 for b in boxes):
            continue
        if any(_seg_dist(px, py, *a, *b) < 13 for a, b in segs):
            continue
        kept.append((px, py, ux, -uy))                  # image y points down
    # ---------------------------------------------------------------- field annotations
    o.append(FS.rect(X(-half), Y(half), 2 * half * s, 2 * half * s, "none", FS.INK, 1.5))
    if g["cutout"]:
        c2 = g["cutout"]["side_mm"] / 2
        o.append(FS.rect(X(-c2), Y(c2), 2 * c2 * s, 2 * c2 * s, "none", "#ffffff", 3.2))
        o.append(FS.rect(X(-c2), Y(c2), 2 * c2 * s, 2 * c2 * s, "none", FS.OPEN, 1.8,
                         'stroke-dasharray="9,6"'))
    for px, py, ux, uy in kept:
        o.append(_arrow_poly(px, py, ux, uy))
    for x, y in sup["balls_mm"]:
        o.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="{r * s:.2f}" fill="none" '
                 f'stroke="{FS.INK}" stroke-width="2.2"/><circle cx="{X(x):.2f}" '
                 f'cy="{Y(y):.2f}" r="{r * s:.2f}" fill="none" stroke="#ffffff" '
                 f'stroke-width="0.9"/>\n')
    for x, y, c in sup["pads_mm"]:
        a = c * s
        o.append(f'<rect x="{X(x) - a / 2:.2f}" y="{Y(y) - a / 2:.2f}" width="{a:.2f}" '
                 f'height="{a:.2f}" fill="none" stroke="{FS.INK}" stroke-width="2.2"/>'
                 f'<rect x="{X(x) - a / 2:.2f}" y="{Y(y) - a / 2:.2f}" width="{a:.2f}" '
                 f'height="{a:.2f}" fill="none" stroke="#ffffff" stroke-width="0.9"/>\n')
    for path, stop, lines, at, anchor, fill in specs:
        (ax, ay), (bx, by) = path[-2], path[-1]
        L = math.hypot(bx - ax, by - ay)
        end = (bx - (bx - ax) / L * stop, by - (by - ay) / L * stop)
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in list(path[:-1]) + [end])
        o.append(f'<polyline points="{pts}" fill="none" stroke="#ffffff" stroke-width="3.6" '
                 f'stroke-linecap="round"/><polyline points="{pts}" fill="none" '
                 f'stroke="{FS.INK}" stroke-width="1.4" stroke-linecap="round"/>\n')
        for i, t in enumerate(lines):
            o.append(FS.text(X(at[0]), Y(at[1]) + i * (LS + 3), t, LS, anchor, "bold", fill))
    # ---------------------------------------------------------------- axes, scale bar
    yb = F["y"] + F["size"]
    for v in range(-15, 16, 5):
        o.append(f'<line x1="{X(v):.1f}" y1="{yb:.1f}" x2="{X(v):.1f}" y2="{yb + 6:.1f}" '
                 f'stroke="{FS.INK}"/><line x1="{F["x"] - 6:.1f}" y1="{Y(v):.1f}" '
                 f'x2="{F["x"]:.1f}" y2="{Y(v):.1f}" stroke="{FS.INK}"/>\n')
        o.append(FS.text(X(v), yb + 22, num(v, 0), 14, "middle", halo=False))
        o.append(FS.text(F["x"] - 9, Y(v) + 5, num(v, 0), 14, "end", halo=False))
    o.append(FS.text(F["x"] + F["size"], yb + 42, "x (mm)", 14, "end", fill=FS.MUTED,
                     halo=False))
    o.append(FS.text(F["x"] - 9, F["y"] - 8, "y (mm)", 14, "end", fill=FS.MUTED, halo=False))
    sy = yb + 40
    o.append(f'<line x1="{F["x"]:.1f}" y1="{sy}" x2="{F["x"] + 5 * s:.1f}" y2="{sy}" '
             f'stroke="{FS.INK}" stroke-width="2.4"/><line x1="{F["x"]:.1f}" y1="{sy - 5}" '
             f'x2="{F["x"]:.1f}" y2="{sy + 5}" stroke="{FS.INK}" stroke-width="1.4"/><line '
             f'x1="{F["x"] + 5 * s:.1f}" y1="{sy - 5}" x2="{F["x"] + 5 * s:.1f}" y2="{sy + 5}" '
             f'stroke="{FS.INK}" stroke-width="1.4"/>\n')
    o.append(FS.text(F["x"] + 5 * s + 8, sy + 5, "5 mm", 14, halo=False))
    # ---------------------------------------------------------------- colour bar
    o.append(FS.text(C["x"] - 6, C["y"] - 40, "V at 1 A of rail current", 15, weight="bold",
                     halo=False))
    o.append(FS.text(C["x"] - 6, C["y"] - 20, "mV  (1 mV per A = 1 mΩ; 0 = rail)", 14,
                     fill=FS.MUTED, halo=False))
    o.append(FS.rect(C["x"], C["y"], C["w"], C["h"], "none", FS.INK, 1))
    Yb = lambda v: C["y"] + (vmax - v) / (vmax - vmin) * C["h"]       # noqa: E731
    step = 0.5e-3 if (vmax - vmin) > 1.5e-3 else 0.2e-3
    ticks, t = [], math.ceil(vmin / step) * step
    while t < vmax - 1e-12:
        ticks.append(t)
        t += step
    for v in ticks:
        if C["y"] + 16 < Yb(v) < C["y"] + C["h"] - 16:
            o.append(f'<line x1="{C["x"] + C["w"]:.1f}" y1="{Yb(v):.1f}" '
                     f'x2="{C["x"] + C["w"] + 6:.1f}" y2="{Yb(v):.1f}" stroke="{FS.INK}"/>\n')
            o.append(FS.text(C["x"] + C["w"] + 10, Yb(v) + 5, num(v * 1e3, 1), 14, halo=False))

    def tiny(v):
        a = abs(v)
        if a < 1e-6:
            return f"{num(v * 1e9, 1)} nV"
        if a < 1e-3:
            return f"{num(v * 1e6, 2)} µV"
        return f"{num(v * 1e3, 4)} mV"
    o.append(FS.text(C["x"] + C["w"] + 10, C["y"] + 7, f"{tiny(vmax)} (max)", 14,
                     fill=FS.MUTED, halo=False))
    o.append(FS.text(C["x"] + C["w"] + 10, C["y"] + C["h"] + 4, f"{tiny(vmin)} (min)", 14,
                     fill=FS.MUTED, halo=False))
    o.append(FS.text(C["x"] - 6, C["y"] + C["h"] + 28, "range = Exodus V min/max (last step)",
                     14, fill=FS.MUTED, halo=False))
    # ---------------------------------------------------------------- legend
    lx, ly = C["x"] - 6, C["y"] + C["h"] + 60
    o.append(FS.text(lx, ly, "Overlay, from problem()", 15, weight="bold", halo=False))
    rows = [("ball", f"supply BGA ball Ø {g['ball_diameter_mm']:g} mm: 48 V in"),
            ("pad", f"VIN pad {sup['pads_mm'][0][2]:g} mm: draws I/{len(sup['pads_mm'])}"),
            ("arrow", "current direction, " + MINUS + "∇V"),
            ("edge", "package edge (insulated)")]
    if g["cutout"]:
        rows.append(("cut", f"PCB opening {g['cutout']['side_mm']:g} mm"))
    for i, (kind, txt) in enumerate(rows):
        cy = ly + 24 + i * 24
        cx = lx + 10
        if kind == "ball":
            o.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="#fde725" stroke="{FS.INK}" '
                     f'stroke-width="2.2"/><circle cx="{cx}" cy="{cy}" r="6" fill="none" '
                     f'stroke="#ffffff" stroke-width="0.9"/>\n')
        elif kind == "pad":
            o.append(f'<rect x="{cx - 5}" y="{cy - 5}" width="10" height="10" fill="#3b528b" '
                     f'stroke="{FS.INK}" stroke-width="2.2"/><rect x="{cx - 5}" y="{cy - 5}" '
                     f'width="10" height="10" fill="none" stroke="#ffffff" stroke-width="0.9"/>\n')
        elif kind == "arrow":
            o.append(_arrow_poly(cx, cy, 1.0, 0.0, L=20))
        elif kind == "edge":
            o.append(f'<line x1="{cx - 10}" y1="{cy}" x2="{cx + 10}" y2="{cy}" '
                     f'stroke="{FS.INK}" stroke-width="1.6"/>\n')
        elif kind == "cut":
            o.append(f'<line x1="{cx - 10}" y1="{cy}" x2="{cx + 10}" y2="{cy}" '
                     f'stroke="{FS.OPEN}" stroke-width="1.8" stroke-dasharray="5,3"/>\n')
        o.append(FS.text(lx + 26, cy + 5, txt, 14, halo=False))
    o.append(FS.text(lx, ly + 24 + len(rows) * 24, "arrows: direction only", 14,
                     fill=FS.MUTED, halo=False))
    # ---------------------------------------------------------------- numbers
    m3, l3 = ref["moose"]["m3"], ref["production_L3"]
    ny = 746
    o.append(FS.rect(lx - 8, ny - 23, 276, 170, "#f6f8fa", FS.LINE, 1, 'rx="6"'))
    o.append(FS.text(lx, ny, "MOOSE vs production FV, at 1 A", 15, weight="bold", halo=False))
    rows = [("R_eff = P / I² (MOOSE vs FV)",
             f"{m3['R_eff_ohm'] * 1e3:.4f} vs {l3['R_eff_ohm'] * 1e3:.4f} mΩ",
             f"{100 * ref['rel_err_R_eff']:+.3f} %"),
            ("largest pad drop (MOOSE vs FV)", f"{m3['max_pad_drop_V'] * 1e3:.4f} vs "
             f"{l3['max_pad_drop_V'] * 1e3:.4f} mV", f"{100 * ref['rel_err_max_drop']:+.3f} %")]
    for i, (k, v, e) in enumerate(rows):
        yy = ny + 24 + i * 44
        o.append(FS.text(lx, yy, k, 14, fill=FS.MUTED, halo=False))
        o.append(FS.text(lx, yy + 19, v, 15, halo=False))
        o.append(FS.text(lx + 264, yy + 19, e.replace("-", MINUS), 15, "end", "bold", FS.OK,
                         halo=False))
    tm, tp = m3["timing"], l3["timing"]
    o.append(FS.text(lx, ny + 117, f"runtime: MOOSE {tm['median_s']:.1f} s, FV "
                     f"{tp['median_s']:.1f} s", 14, halo=False))
    o.append(FS.text(lx, ny + 136, f"median of {tm['repeats']} repeats, 1 core each", 14,
                     fill=FS.MUTED, halo=False))
    # ---------------------------------------------------------------- footer
    o.append(FS.text(22, H_R - 66, CREDIT.format(vtk=vtk_version), 15, weight="bold",
                     halo=False))
    o.append(FS.text(22, H_R - 43, f"Data: rdl_out.e, last time step ({meta['step']} of "
                     f"0–{meta['n_steps'] - 1}; step 0 = initial condition), nodal V, "
                     + f"{chk['exodus_n_triangles']:,}".replace(",", "\u2009")
                     + f" linear triangles, mesh {chk['mesh_tag']} "
                     f"(h_fine {ref['moose'][chk['mesh_tag']]['h_fine_mm']:g} mm)",
                     14, fill=FS.MUTED, halo=False))
    o.append(FS.text(22, H_R - 21, "Field pixels are VTK's own output; annotations are a "
                     f"separate layer on top (outline registration {ver:.2f} px) · "
                     f"geometry {G['geometry_hash'][:12]}…", 14, fill=FS.MUTED,
                     halo=False))
    o.append("</svg>\n")
    return "".join(o), {"n_arrows_drawn": len(kept), "n_arrows_hidden_by_labels":
                        len(apts) - len(kept)}


def composite(base, svg_text, png_out, meta_text):
    """Rasterise the annotation layer and alpha-composite it over the VTK image. Asserts
    that every pixel the layer leaves transparent is byte-identical to VTK's output."""
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    exe, rver = _rsvg()
    SCR.mkdir(parents=True, exist_ok=True)
    svg_p = SCR / (png_out.stem + "_overlay.svg")
    svg_p.write_text(svg_text)
    pngs = []
    for k in range(2):                       # two renders must agree (font fallback guard)
        p = SCR / f"{png_out.stem}_overlay_{k}.png"
        subprocess.run([exe, "-w", str(W_R), "-h", str(H_R), "-f", "png", "-o", str(p),
                        str(svg_p)], check=True)
        pngs.append(p.read_bytes())
    if pngs[0] != pngs[1]:
        raise RuntimeError("rsvg-convert rendered the overlay differently twice")
    ov = Image.open(SCR / f"{png_out.stem}_overlay_0.png").convert("RGBA")
    assert ov.size == (W_R, H_R), ov.size
    bimg = Image.fromarray(base, "RGB").convert("RGBA")
    out = Image.alpha_composite(bimg, ov).convert("RGB")
    a = np.asarray(ov)[:, :, 3]
    o_arr = np.asarray(out)
    untouched = a == 0
    assert np.array_equal(o_arr[untouched], base[untouched]), "composite altered field pixels"
    F = FIELD
    fa = untouched[F["y"]:F["y"] + F["size"], F["x"]:F["x"] + F["size"]]
    info = PngInfo()
    for k, v in meta_text.items():
        info.add_text(k, str(v))
    out.save(png_out, pnginfo=info, optimize=True)
    return {"overlay_renderer": f"rsvg-convert {rver} ({exe})",
            "overlay_svg": str(svg_p),
            "field_viewport_pixels_untouched_fraction": float(fa.mean()),
            "untouched_pixels_identical_to_vtk": True}


def run_render(geoms):
    import vtk
    vtk_version = vtk.vtkVersion.GetVTKVersion()
    exe, rver = _rsvg()
    # warm-up: the first rasterisation in a fresh font cache is not trusted
    warm = SCR / "warmup.svg"
    SCR.mkdir(parents=True, exist_ok=True)
    warm.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20" '
                    f'font-family="{QFONT}"><text x="2" y="15">Ag</text></svg>')
    subprocess.run([exe, "-o", str(SCR / "warmup.png"), str(warm)], check=True)
    for arch in ARCHS:
        G = geoms[arch]
        exo = scratch(f"moose_rdl_{arch}") / "rdl_out.e"
        if not exo.exists():
            print(f"[render] {arch}: no Exodus at {exo}; skipped")
            continue
        ref = json.loads((FC / f"reference_pkg_rdl_moose_{arch}.json").read_text())
        reader, B, meta = read_exodus_last(exo)
        if not (meta["step"] == meta["n_steps"] - 1 and meta["step0_min"] == 0.0
                and meta["step0_max"] == 0.0):
            raise RuntimeError(f"{arch}: unexpected time-step layout {meta}")
        chk = verify_against_solve(arch, G, B, meta, exo)
        img, R_ = vtk_render(reader, B, meta["vmin"], meta["vmax"])
        reg = registration_check(R_, B, G)
        img2 = _grab(R_["rw"])
        assert np.array_equal(img, img2), "VTK render not reproducible after the mask pass"
        col_chk, mesh = colour_check(img, R_, meta["vmin"], meta["vmax"])
        apts, au, ainfo = current_arrows(mesh, G)
        ver = max(reg["ball"]["max_centroid_offset_px"], reg["pad"]["max_centroid_offset_px"])
        svg, ov_info = overlay_svg(arch, G, meta, ver, (apts, au), chk, ref, vtk_version)
        ainfo.update(ov_info)
        FIGS.mkdir(parents=True, exist_ok=True)
        png = FIGS / f"rdl_reference_annotated_{arch}.png"
        exo_sha = sha_file(exo)
        comp = composite(img, svg, png, {
            "Title": f"MOOSE reference field, package 48 V RDL {arch}",
            "Source": CREDIT.format(vtk=vtk_version), "geometry_hash": G["geometry_hash"],
            "exodus_sha256": exo_sha, "Software": "scripts/visualize_rdl_geometry.py"})
        from PIL import Image
        Image.fromarray(img, "RGB").save(SCR / f"rdl_reference_vtk_only_{arch}.png")
        shutil.copy(png, SCR / png.name)
        ev = {
            "figure": rel(png), "figure_sha256": sha_file(png),
            "generated_by": "scripts/visualize_rdl_geometry.py render",
            "exodus": {"path": str(exo), "bytes": exo.stat().st_size, "sha256": exo_sha},
            "time_step": {"index_used": meta["step"], "n_steps": meta["n_steps"],
                          "time_values": meta["times"], "time_used": meta["time"],
                          "step0_V_min_max": [meta["step0_min"], meta["step0_max"]],
                          "why_last": "MOOSE Steady stores the initial condition as step 0"},
            "variable": "V (nodal)", "units": "V at 1 A total rail current (= ohm-equivalent)",
            "V_min_V": meta["vmin"], "V_max_V": meta["vmax"],
            "colour_bar_range_V": list(R_["colour_bar_range_V"]),
            "colour_bar_range_equals_exodus_min_max": True,
            "n_cells": chk["exodus_n_triangles"], "n_points_rendered": int(R_["poly"].GetNumberOfPoints()),
            "geometry_hash": G["geometry_hash"], "supply_rail_hash": G["rail_hashes"]["supply"],
            "geometry_file": f"research/final_closure/rdl_geometry_{arch}.json",
            "render": {"tool": "VTK", "version": vtk_version, "window": R_["window_class"],
                       "reader": "vtkExodusIIReader -> vtkCompositeDataGeometryFilter -> "
                                 "vtkPolyDataMapper", "colormap": "viridis (matplotlib "
                       "256-entry table, perceptually uniform)", "lighting": "off",
                       "interpolate_scalars_before_mapping": True, "multisamples": 0,
                       "image_px": [W_R, H_R], "field_viewport_px": FIELD,
                       "colour_bar_viewport_px": CBAR, "px_per_mm": reg["px_per_mm"],
                       "overlay": comp},
            "registration": {"camera_vs_overlay_transform_max_px": R_["camera_vs_overlay_max_px"],
                             "method": "the Exodus ball/pad blocks are rendered as masks "
                                       "through the same VTK camera; their pixel centroids "
                                       "are compared with problem() centres mapped by the "
                                       "overlay transform", **reg},
            "colour_check": col_chk,
            "arrows": ainfo,
            "consistency_with_solve": chk,
            "credit_label": CREDIT.format(vtk=vtk_version),
            "render_key": render_key(G, exo_sha, vtk_version, rver),
            "render_key_scope": ("SHA-256 over geometry hash, Exodus SHA-256, VTK and "
                                 "rsvg versions, colormap, viewports, arrow parameters "
                                 "and this script's SHA-256: the figure is a different "
                                 "artefact if any of them changes (idea of Omelet "
                                 "Assembly.solver_cache_key, pkgintc/geom/assembly.py:"
                                 "459-488; no Omelet code or value used)"),
        }
        evd = EV / f"pkg_rdl_moose_{arch}"
        (evd / "06_annotated_render.json").write_text(json.dumps(ev, indent=1) + "\n")
        (SCR / f"rdl_reference_annotated_{arch}.json").write_text(json.dumps(ev, indent=1) + "\n")
        (evd / "07_slide_numbers.json").write_text(json.dumps(slide_numbers(arch, ref), indent=1)
                                                    + "\n")
        print(f"[render] {arch}: {rel(png)}  V [{meta['vmin']:.6e}, {meta['vmax']:.6e}] V at "
              f"step {meta['step']}/{meta['n_steps'] - 1}; registration "
              f"{ver:.3f} px; colour p95 {col_chk['p95_abs_rgb_diff']:.0f} levels; "
              f"{ainfo['n_arrows_drawn']} arrows; untouched field pixels "
              f"{100 * comp['field_viewport_pixels_untouched_fraction']:.1f} %")


def render_key(G, exo_sha, vtk_version, rver):
    """What the figure depends on, hashed -- the figure-level analogue of a solver cache key."""
    return sha256({"geometry_hash": G["geometry_hash"], "exodus_sha256": exo_sha,
                   "vtk": vtk_version, "rsvg": rver, "colormap": "viridis/256",
                   "field": FIELD, "cbar": CBAR, "image": [W_R, H_R],
                   "arrows": [ARROW_SPACING_MM, ARROW_EXCLUDE_MM, ARROW_MIN_FRAC_P95],
                   "script_sha256": sha_file(Path(__file__).resolve())})


def mesh_sensitivity(ref):
    """The reference's OWN mesh change between its two finest meshes, next to the
    model-reference difference. A difference smaller than that change is unresolved, not
    agreement (idea: Omelet docs/pkgintc/03_hfss_validation_plan.md:126-129)."""
    m2, m3 = ref["moose"]["m2"], ref["moose"]["m3"]
    out = {"meshes": {"m2_h_fine_mm": m2["h_fine_mm"], "m3_h_fine_mm": m3["h_fine_mm"],
                      "m2_n_elements": m2["n_elements"], "m3_n_elements": m3["n_elements"]}}
    for key, err in (("R_eff_ohm", ref["rel_err_R_eff"]),
                     ("max_pad_drop_V", ref["rel_err_max_drop"])):
        ch = (m3[key] - m2[key]) / m3[key]
        out[key] = {"rel_change_m2_to_m3": ch, "production_rel_err_vs_m3": err,
                    "error_over_mesh_change": abs(err) / abs(ch),
                    "difference_exceeds_reference_mesh_change": abs(err) > abs(ch)}
    return out


def slide_numbers(arch, ref):
    """Numbers for the deck's right-hand column, copied by code from the reference JSON."""
    src = FC / f"reference_pkg_rdl_moose_{arch}.json"
    m3, l3 = ref["moose"]["m3"], ref["production_L3"]
    return {
        "source": rel(src), "source_sha256": sha_file(src),
        "generated_by": "scripts/visualize_rdl_geometry.py render (values copied, not typed)",
        "arch": arch, "observables_at": "1 A total rail current (linear problem)",
        "production": {"label": "production finite-volume sheet, level L3",
                       "R_eff_ohm": l3["R_eff_ohm"], "max_pad_drop_V": l3["max_pad_drop_V"],
                       "n_control_volumes": l3["n_cv"], "runtime_s": l3["timing"],
                       "cores": ref["cores"]["production"]},
        "reference": {"label": "MOOSE heat_transfer-opt FEM, mesh m3",
                      "R_eff_ohm": m3["R_eff_ohm"], "max_pad_drop_V": m3["max_pad_drop_V"],
                      "n_elements": m3["n_elements"], "h_fine_mm": m3["h_fine_mm"],
                      "runtime_s": m3["timing"], "mpi_ranks": ref["cores"]["moose_mpi_ranks"],
                      "R_eff_extrapolated_ohm": ref.get("moose_R_eff_extrapolated_ohm")},
        "rel_err_R_eff": ref["rel_err_R_eff"], "rel_err_max_drop": ref["rel_err_max_drop"],
        "rel_err_R_eff_vs_extrapolated": ref.get("rel_err_R_eff_vs_extrapolated"),
        "runtime_ratio_moose_over_production": ref["speedup_L3_vs_moose_m3"],
        "reference_mesh_sensitivity": mesh_sensitivity(ref),
        "timing_method": ref["timing_method"], "load_average": ref["load_average"],
        "display": {
            "R_eff_production_mOhm": f"{l3['R_eff_ohm'] * 1e3:.4f}",
            "R_eff_moose_mOhm": f"{m3['R_eff_ohm'] * 1e3:.4f}",
            "rel_err_R_eff_pct": f"{100 * ref['rel_err_R_eff']:+.3f}",
            "max_pad_drop_production_mV": f"{l3['max_pad_drop_V'] * 1e3:.4f}",
            "max_pad_drop_moose_mV": f"{m3['max_pad_drop_V'] * 1e3:.4f}",
            "rel_err_max_drop_pct": f"{100 * ref['rel_err_max_drop']:+.3f}",
            "runtime_production_median_s": f"{l3['timing']['median_s']:.1f}",
            "runtime_moose_median_s": f"{m3['timing']['median_s']:.1f}",
            "runtime_ratio": f"{ref['speedup_L3_vs_moose_m3']:.2f}"},
    }



def main(argv):
    what = argv[1] if len(argv) > 1 else "all"
    if what not in ("geometry", "explained", "render", "all"):
        raise SystemExit(__doc__)
    if what in ("geometry", "all"):
        geoms = run_geometry()
    else:
        geoms = {a: load_geometry(a) for a in ARCHS}
    if what in ("explained", "all"):
        run_explained(geoms)
    if what in ("render", "all"):
        run_render(geoms)


if __name__ == "__main__":
    main(sys.argv)
