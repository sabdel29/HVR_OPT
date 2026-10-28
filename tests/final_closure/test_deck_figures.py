"""Deck and figure guards (brief Part 24, tests 5-8): slide numbers come from artifacts,
tool images carry evidence, non-to-scale geometry says so, and a screenshot is never
presented as a re-render (or the reverse). Each guard also runs on a corrupted copy."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
D = R / "presentation" / "prelim_hvr"
sys.path.insert(0, str(R / "scripts"))


def _need(p):
    if not p.exists():
        pytest.skip(f"{p.name} not generated")
    return p


def _manifest():
    return list(csv.DictReader(_need(D / "FIGURE_MANIFEST.csv").open()))


# ----------------------------------------------- 5. slide values come from artifacts
def slide_value_violations(sv, html, resolve):
    bad = []
    for v in sv["values"]:
        cur = resolve(v["source"], v["key"])
        if cur is None or v["raw"] is None:
            bad.append(f"{v['label']}: no artifact value at {v['source']}:{v['key']}")
        elif isinstance(cur, (int, float)) and isinstance(v["raw"], (int, float)):
            if abs(cur - v["raw"]) > 1e-12 * max(1.0, abs(cur)):
                bad.append(f"{v['label']}: deck built from {v['raw']}, artifact now {cur}")
        elif cur != v["raw"]:
            bad.append(f"{v['label']}: deck built from {v['raw']!r}, artifact now {cur!r}")
        if v["text"] not in html:
            bad.append(f"{v['label']}: text {v['text']!r} not on the slides")
    return bad


def test_slide_values_come_from_artifacts():
    import prelim_deck_main as M
    sv = json.loads(_need(D / "slide_values.json").read_text())
    html = (D / "index.html").read_text()
    assert sv["values"], "no slide value was recorded"
    assert slide_value_violations(sv, html, M.resolve) == []


def test_slide_value_guard_negative():
    import prelim_deck_main as M
    sv = json.loads(_need(D / "slide_values.json").read_text())
    html = (D / "index.html").read_text()
    v0 = sv["values"][0]
    stale = dict(sv, values=[dict(v0, raw=(v0["raw"] * 1.01
                                           if isinstance(v0["raw"], (int, float)) else "x"))])
    assert slide_value_violations(stale, html, M.resolve)
    gone = html.replace(v0["text"], "")
    assert slide_value_violations(dict(sv, values=[v0]), gone, M.resolve)


# ----------------------------------------------- 6. tool images have evidence files
def evidence_violations(rows):
    bad = []
    for r in rows:
        p = D / r["figure"]
        if r["figure"].startswith("tool_evidence/"):
            for need in ("setup.json", "result.json", "README.md"):
                if not (p.parent / need).exists():
                    bad.append(f"{r['figure']}: no {need} beside it")
        if "re-render" in r["type"] or r["figure"].startswith("figs/rdl_reference_annotated"):
            side = p.with_suffix(".json")
            ev = list(p.parent.glob("*.json")) if not side.exists() else [side]
            if not side.exists() and not (r["figure"].startswith("figs/rdl_reference")
                                          and any((D / "tool_evidence").glob(
                                              "pkg_rdl_moose_Z*/06_annotated_render.json"))):
                bad.append(f"{r['figure']}: no sidecar evidence JSON")
    return bad


def test_validation_tool_images_have_evidence_files():
    assert evidence_violations(_manifest()) == []


def test_evidence_guard_negative():
    rows = [{"figure": "tool_evidence/no_such_stage/01_geometry.png",
             "type": "tool screenshot (native AEDT export)"}]
    assert evidence_violations(rows)


# ----------------------------------------------- 7. illustrative geometry is labelled
LABELS = ("ILLUSTRATIVE", "NOT TO SCALE", "vertical scale", "exaggerat", "schematic")


def label_violations(rows):
    bad = []
    for r in rows:
        sc = r["to-scale?"].lower()
        if not (sc.startswith("no") or sc.startswith("partly")):
            continue
        p = D / r["figure"]
        txt = ""
        if p.suffix == ".svg":
            txt = p.read_text()
        elif p.suffix == ".png":
            from PIL import Image
            with Image.open(p) as im:
                im.load()                  # text chunks after IDAT are read only on load
                txt = json.dumps({**im.info, **getattr(im, "text", {})}, default=str)
            for side in (p.with_suffix(".json"), p.with_suffix(".sources.json")):
                if side.exists():
                    txt += side.read_text()
        if not any(lab.lower() in txt.lower() for lab in LABELS):
            bad.append(f"{r['figure']}: not to scale but carries no such label")
    return bad


def test_illustrative_geometry_is_labelled():
    assert label_violations(_manifest()) == []


def test_illustrative_label_guard_negative(tmp_path):
    svg = tmp_path / "x.svg"
    svg.write_text("<svg><text>Z1 cross section</text></svg>")
    # an absolute path joined onto D stays absolute, so the guard reads this file
    assert label_violations([{"figure": str(svg), "to-scale?": "no"}])
    svg.write_text("<svg><text>ILLUSTRATIVE — NOT TO SCALE</text></svg>")
    assert label_violations([{"figure": str(svg), "to-scale?": "no"}]) == []


def test_illustrative_label_guard_reads_png_text_after_idat(tmp_path):
    """The package figures stamp the label in an iTXt chunk just before IEND; a guard that
    read only the pre-IDAT header would call the stamped exploded view unlabelled."""
    import io
    from PIL import Image
    import final_closure_package_figs as P
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(buf, "PNG")
    png = tmp_path / "x.png"
    png.write_bytes(buf.getvalue())
    assert label_violations([{"figure": str(png), "to-scale?": "no"}])
    png.write_bytes(P._png_with_text(buf.getvalue(), "Description",
                                     "ILLUSTRATIVE — NOT TO SCALE"))
    assert label_violations([{"figure": str(png), "to-scale?": "no"}]) == []


# ----------------------------------------------- 8. screenshot vs re-render, never mixed
def _column_header(html, rel):
    i = html.find(f'src="{rel}"')
    if i < 0:
        return None
    j = html.rfind("<h3>", 0, i)
    return re.sub(r"<[^>]+>", "", html[j:html.find("</h3>", j)]) if j >= 0 else ""


def mixup_violations(rows, html):
    bad = []
    for r in rows:
        rel, typ = r["figure"], r["type"].lower()
        p = D / rel
        head = (_column_header(html, rel) or "").lower()
        side = p.with_suffix(".json")
        st = side.read_text() if side.exists() else ""
        if "re-render" in typ:
            if "EXACT GEOMETRY RE-RENDERED FROM REFERENCE MODEL" not in st:
                bad.append(f"{rel}: re-render without the re-render banner in its sidecar")
            if "screenshot" in head:
                bad.append(f"{rel}: a re-render captioned as a screenshot")
        if "screenshot" in typ:
            if not rel.startswith("tool_evidence/"):
                bad.append(f"{rel}: screenshot outside tool_evidence/")
            if "re-render" in head or "RE-RENDERED" in st:
                bad.append(f"{rel}: a screenshot presented as a re-render")
    return bad


def test_screenshots_never_confused_with_rerenders():
    html = (D / "index.html").read_text()
    assert mixup_violations(_manifest(), html) == []


def test_mixup_guard_negative():
    rows = [r for r in _manifest() if "re-render" in r["type"]]
    if not rows:
        pytest.skip("no re-render in the deck")
    html = (D / "index.html").read_text()
    rel = rows[0]["figure"]
    bad = html.replace(f'src="{rel}"', f'src="{rel}"', 1)
    k = bad.find(f'src="{rel}"')
    j = bad.rfind("<h3>", 0, k)
    bad = bad[:j] + "<h3>Ansys screenshot</h3>" + bad[j + 4:]
    assert mixup_violations(rows, bad)
