"""Package illustrations against the measured architecture spec.

scripts/final_closure_package_figs.py draws the Z1/Z2 cross-sections, the side-by-side
comparison and the exploded view from research/final_closure/architecture_geometry.json.
These tests make the figures PROVE they used it: every layer at its spec z, every drawn
band where the shared z-mapping puts it, no typed-in height in the generator, the spec
in agreement with the configuration objects, stated exaggeration, and a fresh render
identical to the committed files. Fast: no mesh is built.

Each check is a helper returning a list of problems, so the negative tests at the bottom
feed it the REAL artifact text with one real value corrupted and assert that it fails.
"""
from __future__ import annotations

import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0mr", "scripts/phase0i", "scripts/phase0g",
           "scripts/phase0b", "scripts"):
    if str(R / _p) not in sys.path:
        sys.path.insert(0, str(R / _p))

SPEC = R / "research" / "final_closure" / "architecture_geometry.json"
GEN = R / "scripts" / "final_closure_package_figs.py"
FIGS = R / "presentation" / "prelim_hvr" / "figs"
SECTIONS = {"Z1": FIGS / "z1_package_cross_section.svg",
            "Z2": FIGS / "z2_package_cross_section.svg"}
PAIR = FIGS / "z1_z2_package_comparison.svg"
EXPLODED = FIGS / "z1_z2_exploded.png"
CELL = FIGS / "regulator_cell_zoom.svg"
STAMP = "ILLUSTRATIVE — NOT TO SCALE"
TOL_PX = 0.02            # attributes are written to 2 decimals
CONV = re.compile(r"^(z1conv|conv)_\d+_")


# ================================================================ helpers
def spec() -> dict:
    return json.loads(SPEC.read_text())


def svg(path) -> ET.Element:
    assert Path(path).exists(), f"{path} missing; run scripts/final_closure_package_figs.py"
    return ET.fromstring(Path(path).read_text())


def converter_tiers(a) -> list:
    """Independent of the generator's material rule: by layer name."""
    return sorted((L for L in a["layers"] if CONV.match(L["name"])), key=lambda L: L["z0_um"])


def by_attr(root, attr) -> dict:
    out = {}
    for el in root.iter():
        v = el.get(attr)
        if v is not None:
            out.setdefault(v, []).append(el)
    return out


def check_layers(root, a) -> list:
    """(a) every spec layer is drawn with data-z0/z1-um equal to the spec; no extra layer."""
    probs, els = [], by_attr(root, "data-layer")
    names = {L["name"] for L in a["layers"]}
    for L in a["layers"]:
        got = els.get(L["name"])
        if not got:
            probs.append(f"{L['name']}: no element with data-layer")
            continue
        for el in got:
            for key in ("z0_um", "z1_um"):
                attr = "data-" + key.replace("_", "-")
                v = el.get(attr)
                if v is None or abs(float(v) - float(L[key])) > 1e-9:
                    probs.append(f"{L['name']}: {attr} = {v}, spec {L[key]}")
    probs += [f"{n}: drawn as a layer but not in the spec" for n in els if n not in names]
    return probs


def heights(sp, k_px_per_um, floor_um) -> dict:
    """The shared z-mapping, re-derived here: pixels above the lowest knot, at each knot."""
    knots = sorted({z for a in sp["architectures"].values() for L in a["layers"]
                    for z in (L["z0_um"], L["z1_um"])})
    h, acc = {knots[0]: 0.0}, 0.0
    for z0, z1 in zip(knots, knots[1:]):
        acc += k_px_per_um * max(z1 - z0, floor_um)
        h[z1] = acc
    return h


def expected_pieces(a, L) -> list:
    """Lateral extent on the y = 0 section, from the spec footprints and the opening."""
    W, D, C = a["substrate_mm"][0], a["die_mm"][0], a["cutout_mm"]
    half = (W if L["footprint"] == "substrate" else D) / 2
    if L["region"] == "inside_cutout":
        return [(-C / 2, C / 2)]
    if C and any(I["region"] == "inside_cutout" and I["z0_um"] < L["z1_um"]
                 and L["z0_um"] < I["z1_um"] for I in a["layers"]):
        return [(-half, -C / 2), (C / 2, half)]
    return [(-half, half)]


def check_geometry(root, a, sp, scope=None) -> list:
    """Every band rect sits where the shared mapping and the spec footprint put it."""
    scope = root if scope is None else scope
    s_x = float(root.get("data-px-per-mm-x"))
    k = float(root.get("data-px-per-mm-z")) / 1e3
    floor = float(root.get("data-z-floor-um"))
    y_d = float(root.get("data-y-datum-px"))
    x_l = float((scope if scope is not root else root).get("data-x-left-px"))
    h = heights(sp, k, floor)
    W = a["substrate_mm"][0]
    X = (lambda x: x_l + (x + W / 2) * s_x)
    probs = []
    els = by_attr(scope, "data-layer")
    for L in a["layers"]:
        rects = sorted(els.get(L["name"], []), key=lambda e: float(e.get("x")))
        want = expected_pieces(a, L)
        if len(rects) != len(want):
            probs.append(f"{L['name']}: {len(rects)} pieces drawn, {len(want)} expected")
            continue
        for el, (x0, x1) in zip(rects, want):
            got = [float(el.get(c)) for c in ("x", "y", "width", "height")]
            exp = [X(x0), y_d - h[L["z1_um"]], (x1 - x0) * s_x, h[L["z1_um"]] - h[L["z0_um"]]]
            if any(abs(g - e) > TOL_PX for g, e in zip(got, exp)):
                probs.append(f"{L['name']}: rect {got} != expected {exp}")
    # cells of every converter tier, TSV fields under them
    cx_spec = sorted(a["cells"]["centres_x_mm"])
    side = a["cells"]["side_mm"]
    for attr, layers in (("data-cell-of", converter_tiers(a)),
                         ("data-tsv-field-of", [L for L in a["layers"]
                                                if "tsv_tile" in L["materials"]])):
        cells = by_attr(scope, attr)
        for L in layers:
            got = sorted(cells.get(L["name"], []), key=lambda e: float(e.get("x")))
            if len(got) != a["cells"]["grid"]:
                probs.append(f"{L['name']}: {len(got)} {attr} rects, grid {a['cells']['grid']}")
                continue
            for el, cx in zip(got, cx_spec):
                if (abs(float(el.get("x")) - X(cx - side / 2)) > TOL_PX
                        or abs(float(el.get("width")) - side * s_x) > TOL_PX):
                    probs.append(f"{L['name']}: cell at {el.get('x')} != spec centre {cx}")
    return probs


def bga_row(a) -> list:
    """Centred lattice at the spec pitch, minus the opening; 2-D count == sites_legal."""
    p, half, C = a["bga"]["pitch_mm"], a["substrate_mm"][0] / 2, a["cutout_mm"]
    n = int(half / p + 1e-9)
    xs = [round(i * p, 9) for i in range(-n, n + 1)]
    inside = (lambda v: C is not None and abs(v) < C / 2)
    assert sum(1 for x in xs for y in xs if not (inside(x) and inside(y))) \
        == a["bga"]["sites_legal"]
    return [x for x in xs if not (inside(x) and inside(0.0))]


def check_balls(root, a, scope=None) -> list:
    scope = root if scope is None else scope
    s_x = float(root.get("data-px-per-mm-x"))
    x_l = float((scope if scope is not root else root).get("data-x-left-px"))
    W, C = a["substrate_mm"][0], a["cutout_mm"]
    balls = [el for el in scope.iter() if el.get("data-bga-x-mm") is not None]
    got = sorted(float(el.get("data-bga-x-mm")) for el in balls)
    probs = []
    if got != pytest.approx(bga_row(a), abs=1e-9):
        probs.append(f"ball row {got} != lattice {bga_row(a)}")
    for el in balls:
        x = float(el.get("data-bga-x-mm"))
        if C and abs(x) < C / 2:
            probs.append(f"ball at {x} mm is inside the {C} mm opening")
        if abs(float(el.get("cx")) - (x_l + (x + W / 2) * s_x)) > TOL_PX:
            probs.append(f"ball {x} mm drawn at cx {el.get('cx')}")
    return probs


def visible_text(root) -> list:
    return ["".join(el.itertext()) for el in root.iter() if el.tag.endswith("text")]


def metadata(root) -> dict:
    md = [el for el in root.iter() if el.tag.endswith("metadata")]
    assert md, "no <metadata> block"
    return json.loads(md[0].text)


REQUIRED_ITEMS = {"Z1": ("embedded_hvr", "substrate", "package_rdl", "bga", "pcb", "tsv_field",
                         "cell_arrangement"),
                  "Z2": ("backside_hvr", "pcb_cutout", "thin_substrate", "tsv_field",
                         "package_hv_rdl", "bga", "pcb", "cell_arrangement")}


def check_metadata(md, a, sp) -> list:
    arch, items = a["arch"], md.get("items", {})
    probs = [f"metadata lacks {k}" for k in REQUIRED_ITEMS[arch] if k not in items]
    if probs:
        return probs
    sub = sorted((L for L in a["layers"] if "tsv_tile" in L["materials"]),
                 key=lambda L: L["z0_um"])
    t_sub = sub[-1]["z1_um"] - sub[0]["z0_um"]
    board = next(L for L in a["layers"] if L["name"] == "board")
    tiers = converter_tiers(a)
    hvr = items["embedded_hvr" if arch == "Z1" else "backside_hvr"]
    sub_md = items["substrate" if arch == "Z1" else "thin_substrate"]
    rdl = items["package_rdl" if arch == "Z1" else "package_hv_rdl"]
    checks = [(sub_md["thickness_um"], t_sub, "substrate thickness"),
              (hvr["tiers"], len(tiers), "converter tiers"),
              (hvr["height_um"], tiers[-1]["z1_um"] - tiers[0]["z0_um"], "converter height"),
              (rdl["fe_layer"], False, "package RDL is not an FE layer"),
              (rdl["z_um"], sub[0]["z0_um"], "package RDL at the substrate underside"),
              (items["pcb"]["thickness_um"], board["t_um"], "PCB thickness"),
              (items["bga"]["pitch_mm"], a["bga"]["pitch_mm"], "BGA pitch"),
              (items["bga"]["sites_legal"], a["bga"]["sites_legal"], "BGA sites"),
              (items["tsv_field"]["n_per_cell"], a["tsv"]["n_per_cell"], "TSVs per cell"),
              (items["tsv_field"]["rail_carried"], a["tsv"]["rail_carried"], "TSV rail"),
              (items["cell_arrangement"]["n"], a["cells"]["n"], "cell count"),
              (items["cell_arrangement"]["arrangement"],
               f"{a['cells']['grid']}x{a['cells']['grid']}", "cell arrangement")]
    if arch == "Z2":
        checks.append((items["pcb_cutout"]["width_mm"], a["cutout_mm"], "PCB cutout"))
    return [f"{what}: figure {got!r} != spec {want!r}" for got, want, what in checks
            if got != want]


NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])")


def forbidden_values(sp) -> set:
    v = set()
    for a in sp["architectures"].values():
        for L in a["layers"]:
            v |= {abs(float(L[k])) for k in ("z0_um", "z1_um", "t_um")}
        v |= {abs(float(a["z_min_um"])), abs(float(a["z_max_um"]))}
    v.discard(0.0)       # the datum itself: banning 0 would ban every index and origin
    return v


def forbidden_literals(src, sp) -> list:
    """(c) standalone numbers equal to a spec thickness or z value, in um or in mm.

    The whole source is scanned, strings and comments included. The mm form catches a
    height typed as 0.685; 0.5 is exempt there only (the universal half factor) --
    500 um itself is still caught."""
    bad, hits = forbidden_values(sp), []
    for i, line in enumerate(src.splitlines(), 1):
        for m in NUM.finditer(line):
            tok = m.group(1)
            val = float(tok)
            mm = round(val * 1e3, 6) if "." in tok else None
            if val in bad or (mm in bad and val != 0.5):
                hits.append((i, tok, line.strip()))
    return hits


def png_text(data: bytes) -> dict:
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    i, out = 8, {}
    while i < len(data):
        n = struct.unpack(">I", data[i:i + 4])[0]
        typ, body = data[i + 4:i + 8], data[i + 8:i + 8 + n]
        if typ == b"iTXt":
            key, rest = body.split(b"\0", 1)
            rest = rest[2:]                                   # compression flag, method
            _lang, rest = rest.split(b"\0", 1)
            _tkey, txt = rest.split(b"\0", 1)
            out[key.decode("latin-1")] = txt.decode("utf-8")
        elif typ == b"IHDR":
            out["_size"] = struct.unpack(">II", body[:8])
        i += 12 + n
    return out


def gen():
    import final_closure_package_figs as G
    return G


# ================================================================ (a) layers at spec z
@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_every_spec_layer_is_drawn_at_its_spec_z(arch):
    a = spec()["architectures"][arch]
    root = svg(SECTIONS[arch])
    assert root.get("data-architecture") == arch
    assert check_layers(root, a) == []


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_every_band_sits_where_the_shared_mapping_and_the_footprint_put_it(arch):
    sp = spec()
    root = svg(SECTIONS[arch])
    a = sp["architectures"][arch]
    assert check_geometry(root, a, sp) == []
    assert check_balls(root, a) == []


def test_comparison_panels_share_one_mapping_and_match_the_spec():
    sp = spec()
    root = svg(PAIR)
    panels = {g.get("data-panel"): g for g in root.iter() if g.get("data-panel")}
    assert set(panels) == {"Z1", "Z2"}
    for arch, g in panels.items():
        a = sp["architectures"][arch]
        assert check_layers(g, a) == [], arch
        assert check_geometry(root, a, sp, g) == [], arch
        assert check_balls(root, a, g) == [], arch
    # physically identical layers land on identical pixel rows in both panels
    rows = {arch: {el.get("data-layer"): (el.get("y"), el.get("height"))
                   for el in g.iter() if el.get("data-layer")} for arch, g in panels.items()}
    for name in ("board", "bga", "sub_lower", "tile_band"):
        assert rows["Z1"][name] == rows["Z2"][name], name


def test_z2_opening_is_empty_air_and_the_pcb_an_annular_frame():
    sp = spec()
    a = sp["architectures"]["Z2"]
    root = svg(SECTIONS["Z2"])
    C, W = a["cutout_mm"], a["substrate_mm"][0]
    s_x = float(root.get("data-px-per-mm-x"))
    air = by_attr(root, "data-feature").get("pcb-opening-air")
    assert air and len(air) == 1
    assert abs(float(air[0].get("width")) - C * s_x) < TOL_PX
    for name in ("board", "bga"):
        pieces = by_attr(root, "data-layer")[name]
        spans = sorted((float(e.get("data-x0-mm")), float(e.get("data-x1-mm"))) for e in pieces)
        assert spans == [(-W / 2, -C / 2), (C / 2, W / 2)], name
    deepest = min(L["z0_um"] for L in converter_tiers(a))
    assert deepest > a["z_min_um"], "the converter must not reach the PCB backside"


# ================================================================ (b) spec identity
@pytest.mark.parametrize("path", [SECTIONS["Z1"], SECTIONS["Z2"], PAIR, CELL])
def test_svg_root_carries_the_spec_sha256(path):
    sp = spec()
    assert svg(path).get("data-spec-sha256") == sp["sha256"]


def test_the_spec_hash_verifies():
    gen().load_spec(SPEC)                      # raises unless the sha256 recomputes


# ================================================================ (c) nothing typed in
def test_generator_contains_no_spec_thickness_or_z_literal():
    hits = forbidden_literals(GEN.read_text(), spec())
    assert hits == [], "\n".join(f"line {i}: {t}  | {s}" for i, t, s in hits)


# ================================================================ (d) spec == configuration
def test_spec_agrees_with_the_configuration_objects():
    import physical_package as PP
    import z2_converter as Z2C
    sp = spec()
    A = sp["architectures"]
    z1 = PP.load_z1_package_config()
    z2 = PP.load_physical_package_config(R / "configs/phase0nt/z2_2p4mm_cutout.yaml")
    t1 = converter_tiers(A["Z1"])
    assert [L["t_um"] for L in t1] == pytest.approx([um for _n, um in z1.tiers], abs=1e-9)
    assert all(L["name"].endswith(n) for L, (n, _um) in zip(t1, z1.tiers))
    conv = Z2C.converter_layers(z2)             # deepest first, like the sort by z0
    t2 = converter_tiers(A["Z2"])
    assert [L["name"] for L in t2] == [c[0] for c in conv]
    assert [L["t_um"] for L in t2] == pytest.approx([c[1] * 1e3 for c in conv], abs=1e-9)
    board = {k: next(L for L in A[k]["layers"] if L["name"] == "board") for k in A}
    assert board["Z1"]["t_um"] == z1.board_thickness_um
    assert board["Z2"]["t_um"] == z2.board_thickness_um
    for k, cfg in (("Z1", z1), ("Z2", z2)):
        sub = [L for L in A[k]["layers"] if "tsv_tile" in L["materials"]]
        assert sum(L["t_um"] for L in sub) == pytest.approx(cfg.substrate_um, abs=1e-9)
    assert A["Z2"]["cutout_mm"] == z2.cutout_mm and A["Z1"]["cutout_mm"] is None
    lay1 = {L["name"]: L["t_um"] for L in A["Z1"]["layers"]}
    assert (lay1["interface"], lay1["die"], lay1["tim"]) == (z1.interface_um, z1.die_um,
                                                            z1.tim_um)
    # the generator's material rule picks exactly the converter tiers named in the spec
    G = gen()
    for k in A:
        assert [L["name"] for L in G.tiers(A[k])] == [L["name"] for L in converter_tiers(A[k])]


# ================================================================ (e) scale honesty
@pytest.mark.parametrize("path", [SECTIONS["Z1"], SECTIONS["Z2"], PAIR])
def test_vertical_exaggeration_and_minimum_height_are_stated_in_visible_text(path):
    root = svg(path)
    v = root.get("data-vertical-exaggeration")
    floor = root.get("data-z-floor-um")
    s_x, s_z = float(root.get("data-px-per-mm-x")), float(root.get("data-px-per-mm-z"))
    assert float(v) == pytest.approx(s_z / s_x)
    txt = " ".join(visible_text(root))
    assert re.search(rf"vertical scale ×{re.escape(v)}\b", txt), v
    assert "minimum height" in txt and f"{floor} µm" in txt
    assert "true thickness labelled" in txt


def test_exploded_view_is_stamped_illustrative_in_source_svg_and_png():
    sp = spec()
    assert STAMP in GEN.read_text()
    root = ET.fromstring(gen().exploded_svg(sp))
    assert any(STAMP in t for t in visible_text(root))
    meta = png_text(EXPLODED.read_bytes())
    assert STAMP in meta.get("Description", "")
    assert sp["sha256"] in meta["Description"], "PNG rendered from a different spec"
    assert meta["_size"] == (1600, 900)


def test_exploded_slabs_follow_the_spec_order_and_invent_no_layer():
    sp = spec()
    root = ET.fromstring(gen().exploded_svg(sp))
    panels = {g.get("data-panel"): g for g in root.iter() if g.get("data-panel")}
    assert set(panels) == set(sp["architectures"])
    for arch, a in sp["architectures"].items():
        order = []                                    # document order == painter order
        for el in panels[arch].iter():
            n = el.get("data-layer")
            if n and (not order or order[-1] != n):
                order.append(n)
        want = [L["name"] for L in sorted(a["layers"], key=lambda L: (L["z0_um"], L["z1_um"]))]
        assert order == want, arch
        assert check_layers(panels[arch], a) == [], arch


def test_cell_zoom_tiers_are_the_spec_tiers_in_order():
    sp = spec()
    root = svg(CELL)
    panels = {g.get("data-panel"): g for g in root.iter() if g.get("data-panel")}
    for arch, a in sp["architectures"].items():
        names = [el.get("data-layer") for el in panels[arch].iter() if el.get("data-layer")]
        assert names == [L["name"] for L in converter_tiers(a)], arch


# ================================================================ content and freshness
@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_metadata_names_every_required_item_with_spec_values(arch):
    sp = spec()
    root = svg(SECTIONS[arch])
    assert check_metadata(metadata(root), sp["architectures"][arch], sp) == []
    pair = metadata(svg(PAIR))["panels"][arch]
    assert check_metadata(pair, sp["architectures"][arch], sp) == []


@pytest.mark.parametrize("arch", ["Z1", "Z2"])
def test_key_message_title_and_current_labels_are_visible(arch):
    G = gen()
    txt = visible_text(svg(SECTIONS[arch]))
    assert G.KEY_MESSAGE[arch] in txt
    assert spec()["architectures"][arch]["label"].replace(" -- ", " — ") in txt
    for lab in ("48 V in", "1 V out", "48 V return", "1 V return", G.SHEET_TEXT):
        assert any(lab in t for t in txt) or lab in " ".join(txt), lab


@pytest.mark.parametrize("path", [SECTIONS["Z1"], SECTIONS["Z2"], PAIR, CELL])
def test_no_text_below_fourteen_pixels(path):
    sizes = [float(el.get("font-size")) for el in svg(path).iter() if el.get("font-size")]
    assert sizes and min(sizes) >= 14


def test_committed_figures_are_a_fresh_render_of_the_current_spec_and_code():
    figs = gen().build_all(spec())
    for key, path in (("Z1", SECTIONS["Z1"]), ("Z2", SECTIONS["Z2"]), ("pair", PAIR),
                      ("cell", CELL)):
        assert path.read_text() == figs[key], f"{path.name} is stale: rerun the generator"


# ================================================================ negative tests
def test_negative_layer_check_fails_on_a_corrupted_z():
    sp = spec()
    a = sp["architectures"]["Z2"]
    hs = next(L for L in a["layers"] if "hs" in L["roles"])
    text = SECTIONS["Z2"].read_text()
    real = f'data-z1-um="{float(hs["z1_um"])!r}"'
    assert real in text
    bad = text.replace(real, f'data-z1-um="{float(hs["z1_um"]) + 1:.1f}"', 1)
    assert any(hs["name"] in p for p in check_layers(ET.fromstring(bad), a))


def test_negative_geometry_check_fails_on_a_shifted_band():
    sp = spec()
    a = sp["architectures"]["Z1"]
    text = SECTIONS["Z1"].read_text()
    m = re.search(r'<rect x="([\d.]+)" y="([\d.]+)"([^>]*data-layer="z1conv_1_gan_hs_\w+")',
                  text)
    assert m
    moved = text.replace(m.group(0), m.group(0).replace(f'y="{m.group(2)}"',
                                                        f'y="{float(m.group(2)) + 3:.2f}"'), 1)
    assert check_geometry(ET.fromstring(moved), a, sp) != []


def test_negative_literal_scan_catches_a_typed_in_height():
    sp = spec()
    hs = next(L for L in sp["architectures"]["Z1"]["layers"] if "hs" in L["roles"])
    src = GEN.read_text()
    for typed in (f"HS_UM = {float(hs['t_um'])!r}\n", f"HS_MM = {hs['t_um'] / 1e3!r}\n",
                  f"Z_PCB = {float(sp['architectures']['Z2']['z_min_um'])!r}\n"):
        assert forbidden_literals(src + typed, sp), typed


def test_negative_sha_and_metadata_checks_fail_when_stale():
    sp = spec()
    root = svg(SECTIONS["Z2"])
    stale = SECTIONS["Z2"].read_text().replace(sp["sha256"], "0" * 64)
    assert ET.fromstring(stale).get("data-spec-sha256") != sp["sha256"]
    md = metadata(root)
    del md["items"]["pcb_cutout"]
    assert check_metadata(md, sp["architectures"]["Z2"], sp) == ["metadata lacks pcb_cutout"]
    md = metadata(root)
    md["items"]["thin_substrate"]["thickness_um"] += 1
    assert check_metadata(md, sp["architectures"]["Z2"], sp)
