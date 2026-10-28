"""Render the prelim deck to PDF, rasterise every page, build QA contact sheets, and check.
Fails loudly.

  presentation/prelim_hvr/HVR_OPT_Prelim.pdf      one page per slide (headless Chrome)
  presentation/prelim_hvr/qa/contact_sheet.png    the MAIN slides, numbered
  presentation/prelim_hvr/qa/contact_sheet_appendix.png
  presentation/prelim_hvr/qa/pages/page-NN.png    every page at 1600 px (not committed)
  presentation/prelim_hvr/qa/qa_report.json       machine checks per page

Machine checks cannot judge a figure; the contact sheets and pages are what a person
inspects, and presentation/prelim_hvr/qa/inspection_log.json records that inspection.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "presentation" / "prelim_hvr"
PDF = D / "HVR_OPT_Prelim.pdf"
QA = D / "qa"


def _render_pages():
    pages = QA / "pages"
    if pages.exists():
        shutil.rmtree(pages)
    pages.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", "1600", "-scale-to-y", "-1",
                    str(PDF), str(pages / "page")], check=True, timeout=600)
    return sorted(pages.glob("page-*.png"))


def _ink_fraction_bottom(png):
    """Share of non-white pixels in the bottom 5 % band above the footer: content that
    runs into the footer band means the slide overflows."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, h = im.size
    band = im.crop((0, int(h * 0.90), w, int(h * 0.955)))
    px = band.getdata()
    return sum(1 for p in px if p < 200) / max(1, len(px))


def _sheet(pngs, out, cols, title):
    if not pngs:
        return
    args = ["montage"] + [str(p) for p in pngs] + [
        "-tile", f"{cols}x", "-geometry", "480x270+8+8", "-background", "#e9edf1",
        "-label", "%f", "-pointsize", "14", "-title", title, str(out)]
    # label each tile with its page number (file name page-NN.png)
    subprocess.run(args, check=True, timeout=600)


def main() -> int:
    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser")
                   if shutil.which(c)), None)
    if not chrome:
        print("no chromium binary found; cannot render", file=sys.stderr)
        return 2
    n_slides = (D / "print.html").read_text().count('<div class=\'pg reveal\'>')
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--allow-file-access-from-files", "--no-pdf-header-footer",
                    "--virtual-time-budget=25000",
                    f"--print-to-pdf={PDF}",
                    f"file://{D / 'print.html'}"],
                   check=True, capture_output=True, timeout=300)
    data = PDF.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    print(f"slides={n_slides}  pdf_pages={pages}  size={len(data)/1e6:.2f} MB")
    ok = True
    if pages != n_slides:
        print(f"FAIL one page per slide: {pages} != {n_slides}", file=sys.stderr)
        ok = False
    if len(data) < 100_000:
        print("FAIL pdf suspiciously small -- probably blank", file=sys.stderr)
        ok = False
    html = (D / "index.html").read_text()
    missing = [m for m in re.findall(r'src="((?:figs|tool_evidence)/[^"]+)"', html)
               if not (D / m).exists()]
    if missing:
        print("FAIL missing figures:", missing, file=sys.stderr)
        ok = False
    if "MISSING FIGURE" in html:
        print("FAIL a slide carries a MISSING FIGURE banner", file=sys.stderr)
        ok = False
    QA.mkdir(parents=True, exist_ok=True)
    pngs = _render_pages()
    sv = json.loads((D / "slide_values.json").read_text()) if (D / "slide_values.json").exists() else {}
    n_main = sv.get("n_main", len(pngs))
    report = []
    for i, p in enumerate(pngs, 1):
        ink = _ink_fraction_bottom(p)
        report.append({"page": i, "main": i <= n_main, "bottom_band_ink": round(ink, 4),
                       "overflow_suspect": ink > 0.02})
    (QA / "qa_report.json").write_text(json.dumps(
        {"n_pages": len(pngs), "n_main": n_main, "pages": report}, indent=1))
    sus = [r["page"] for r in report if r["overflow_suspect"]]
    if sus:
        print("WARN pages whose content reaches the footer band:", sus)
    _sheet(pngs[:n_main], QA / "contact_sheet.png", 5, "HVR_OPT prelim -- main slides")
    _sheet(pngs[n_main:], QA / "contact_sheet_appendix.png", 6,
           "HVR_OPT prelim -- appendix")
    print("QA PASS" if ok else "QA FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
