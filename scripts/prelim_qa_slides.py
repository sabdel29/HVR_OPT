"""Render the prelim deck to PDF and check every page. Fails loudly."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
D = R / "presentation" / "prelim_hvr"
PDF = D / "HVR_OPT_Prelim.pdf"


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
    missing = [m for m in re.findall(r'src="(figs/[^"]+)"',
                                     (D / "index.html").read_text())
               if not (D / m).exists()]
    if missing:
        print("FAIL missing figures:", missing, file=sys.stderr)
        ok = False
    print("QA PASS" if ok else "QA FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
