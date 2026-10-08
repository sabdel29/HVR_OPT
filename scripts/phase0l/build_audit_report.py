#!/usr/bin/env python3
"""Build and verify results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.{md,pdf}.

Phase-0L Part XXIII. The verification runs against the BUILT ARTIFACT -- the final Markdown and
the text extracted from the final PDF -- not against the source that was intended to produce it.
Every check that can fail the build does fail it.
"""
from __future__ import annotations
import json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
MD = RES / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
PDF = RES / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf"
TMP = RES / ".audit_report_source.md"
TEX = RES / ".audit_report_structure.tex"
LOG = RES / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT_BUILD_LOG.md"
SEM = RES / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT_SEMANTIC_AUDIT.md"

DELIM = re.compile(r"^\|[:\-\s|]+\|\s*$")
ATX = re.compile(r"^#{1,4} \S")
PROTECT = re.compile(r"(```.*?```|`[^`\n]*`|\$\$.*?\$\$|\$[^$\n]*\$)", re.S)

# Characters proven to render in this pandoc 2.0.6 + xelatex chain, by their presence in the
# already-built ETM_DVPD_FULL_TECHNICAL_REPORT.pdf.
PROVEN = set("—µ°²Ω×·–Δ→σ−"
             "η₁ρδΣ≤α≈εθ")
# Greek and relational glyphs the sanitiser converts to math before xelatex sees them.
BARE = {"σ": r"$\sigma$", "ρ": r"$\rho$", "η": r"$\eta$", "α": r"$\alpha$",
        "θ": r"$\theta$", "ν": r"$\nu$", "≤": r"$\le$", "≥": r"$\ge$",
        "≈": r"$\approx$", "δ": r"$\delta$", "β": r"$\beta$", "γ": r"$\gamma$",
        "λ": r"$\lambda$", "π": r"$\pi$", "τ": r"$\tau$", "φ": r"$\varphi$",
        "ω": r"$\omega$", "ε": r"$\varepsilon$", "κ": r"$\kappa$", "μ": r"$\mu$",
        "Σ": r"$\Sigma$", "∇": r"$\nabla$", "∂": r"$\partial$", "∫": r"$\int$",
        "√": r"$\sqrt{}$", "≫": r"$\gg$", "≪": r"$\ll$", "±": r"$\pm$", "∞": r"$\infty$"}
CHECKS: list[tuple[str, bool, str]] = []


def chk(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append((name, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  --- {detail}" if detail else ""))
    return bool(ok)


def fence_mask(lines):
    mask, inside = [], False
    for l in lines:
        if l.strip().startswith("```"):
            mask.append(True); inside = not inside; continue
        mask.append(inside)
    return mask


def repair_markdown() -> tuple[int, int]:
    lines = MD.read_text().split("\n")
    mask = fence_mask(lines)
    out, tfix, hfix = [], 0, 0
    for i, l in enumerate(lines):
        if mask[i]:
            out.append(l); continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        nxt_fence = mask[i + 1] if i + 1 < len(mask) else True
        is_header = (not nxt_fence and DELIM.match(nxt) and set(nxt) <= set("|:- ")
                     and l.lstrip().startswith("|"))
        is_heading = ATX.match(l)
        if (is_header or is_heading) and out and out[-1].strip() != "":
            out.append("")
            tfix += bool(is_header); hfix += bool(is_heading)
        out.append(l)
    if tfix or hfix:
        MD.write_text("\n".join(out))
    return tfix, hfix


def sanitise(text: str) -> tuple[str, int]:
    n, out = 0, []
    for i, part in enumerate(PROTECT.split(text)):
        if i % 2 == 1:
            out.append(part); continue
        for src, dst in BARE.items():
            n += part.count(src); part = part.replace(src, dst)
        for dst in BARE.values():                 # a closing '$' before a digit is not math
            for d in "0123456789":
                part = part.replace(dst + d, dst + " " + d)
        out.append(part)
    return "".join(out), n


def run(cmd, cwd=RES):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=2400)
    if p.returncode != 0:
        print(p.stdout[-3000:]); print(p.stderr[-4000:])
        sys.exit(f"failed rc={p.returncode}: {cmd[0]}")
    return p


COMMON = ["--pdf-engine=xelatex", "--toc", "--toc-depth=2",
          "-V", "geometry:margin=2.1cm", "-V", "fontsize=10pt",
          "-V", "colorlinks=true", "-V", "linkcolor=RoyalBlue",
          "-V", "urlcolor=RoyalBlue", "--resource-path", str(RES)]


def build():
    tfix, hfix = repair_markdown()
    print(f"[repair]   blank line inserted before {tfix} table headers, {hfix} headings")
    raw = MD.read_text()
    src, nsub = sanitise(raw)
    TMP.write_text(src)
    print(f"[sanitise] {nsub} glyph substitutions")
    print("[pandoc]   structure probe")
    run(["pandoc", str(TMP), "-s", "-o", str(TEX), "--toc"])
    print("[pandoc]   building PDF")
    p = run(["pandoc", str(TMP), "-o", str(PDF)] + COMMON)
    return raw, src, p.stderr, {"table_fixes": tfix, "heading_fixes": hfix, "subs": nsub,
                                "cmd": "pandoc " + " ".join([TMP.name, "-o", PDF.name] + COMMON)}


def verify(raw: str, src: str, pandoc_err: str) -> str:
    lines = raw.split("\n"); mask = fence_mask(lines)
    md_headings = [l for i, l in enumerate(lines) if not mask[i] and ATX.match(l)]
    tex = TEX.read_text()
    n_tex_sec = len(re.findall(r"\\section\{|\\subsection\{|\\subsubsection\{", tex))

    # ---- markdown-side checks -------------------------------------------------------------
    leftover = re.findall(r"@@[A-Z0-9_]+@@", raw)
    chk("no unreplaced placeholders", not leftover, ", ".join(sorted(set(leftover)))[:120])
    chk("no literal escaped dollars", "\\$" not in raw)
    unknown = sorted({c for c in raw if ord(c) > 127 and c not in PROVEN and c not in BARE})
    chk("every non-ASCII glyph is proven or converted", not unknown,
        " ".join(f"{c!r} U+{ord(c):04X} {unicodedata.name(c,'?')}" for c in unknown)[:220])
    # a '$' inside an inline code span is literal, not a math delimiter
    nocode = [re.sub(r"`[^`\n]*`", "", l) for l in lines]
    odd = [i + 1 for i, l in enumerate(nocode)
           if not mask[i] and not lines[i].strip().startswith("$$") and l.count("$") % 2]
    chk("inline math delimiters balanced on every line", not odd, str(odd[:8]))

    # ---- figures --------------------------------------------------------------------------
    figs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", raw)
    missing = [f for f in figs if not Path(f).is_file()]
    chk(f"all {len(figs)} figure files exist", not missing, "; ".join(missing[:4]))
    chk("no pandoc missing-resource warning", "Could not fetch resource" not in pandoc_err,
        pandoc_err[-300:] if "Could not fetch" in pandoc_err else "")

    # ---- PDF ------------------------------------------------------------------------------
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    chk("PDF page count plausible for a 40-70 page report", 35 <= pages <= 110, f"{pages} pages")
    txt = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                         capture_output=True, text=True).stdout
    chk("PDF text extraction non-empty", len(txt) > 40000, f"{len(txt)} chars")

    # every intended text page extracts something
    blank = []
    for pg in range(1, pages + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(pg), "-l", str(pg), str(PDF), "-"],
                           capture_output=True, text=True).stdout.strip()
        if len(t) < 20:
            blank.append(pg)
    chk("no page extracts as empty text", not blank, f"pages {blank[:10]}")

    imgs = subprocess.run(["pdfimages", "-list", str(PDF)], capture_output=True,
                          text=True).stdout.strip().split("\n")
    n_img = max(0, len(imgs) - 2)
    chk(f"all {len(figs)} figures embedded as images", n_img >= len(figs), f"{n_img} images")

    # headings: every markdown heading title must appear in the extracted text
    titles = [re.sub(r"^#+\s+", "", h).strip() for h in md_headings]
    # Compare on an alphanumeric signature. Markdown emphasis, inline code, LaTeX braces and
    # subscripts, em dashes and Greek glyphs all render differently in the PDF than they are
    # written, and none of those differences means a heading is missing.
    # xelatex typesets math in Unicode mathematical-italic (U+1D400 block); NFKD folds those
    # back to ASCII so that "$N_{required}$" and its rendered form compare equal.
    sig = lambda x: re.sub(r"[^a-z0-9]", "",
                           unicodedata.normalize("NFKD", x).lower())
    flat = sig(txt)
    absent = [t for t in titles if sig(t)[:34] not in flat]
    chk(f"all {len(titles)} headings present in the PDF text", not absent,
        "; ".join(absent[:4]))
    chk("structure probe found comparable section count", abs(n_tex_sec - len(titles)) <= 2,
        f"tex {n_tex_sec} vs md {len(titles)}")

    # TOC
    first = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "4", str(PDF), "-"],
                           capture_output=True, text=True).stdout
    chk("TOC present and lists the last section",
        "Contents" in first and "Glossary" in first)

    # no raw markdown survived into the rendered text
    raw_tbl = [l for l in txt.split("\n") if l.count("|") >= 3 and set(l.strip()) <= set("|:- ")]
    chk("no raw Markdown table delimiter rows in the PDF", not raw_tbl, str(raw_tbl[:2]))
    # ".png" legitimately appears in the code-architecture table, which names generated files;
    # what must NOT appear is unrendered image syntax or a leaked absolute figure path.
    figdir = "/home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results/phase0l"
    chk("no unrendered image syntax in the PDF text", "![" not in txt)
    chk("no absolute figure path visible to the reader", figdir not in txt)
    chk("no literal ATX hashes leaked into the PDF text",
        not re.search(r"^#{1,4} \S", txt, re.M))

    # control characters
    ctrl = sorted({c for c in raw if ord(c) < 32 and c not in "\n\t"})
    chk("no stray control characters", not ctrl, repr(ctrl))
    return txt


# Semantic guards. Each pattern is paired with the VERBATIM sentence it must catch, so that a
# guard which no longer matches the thing it was written for fails the build (the lesson of
# DEFECT #36: a paraphrase written beside the regex tests the author, not the failure).
GUARDS: list[tuple[str, str, str]] = [
    ("creep law stated as a function of total von Mises stress",
     r"eps_dot\s*=\s*A\s*\(?T\)?\s*\*?\s*sigma\s*\^?\s*n|creep rate is\s+A\s*sigma",
     "the current report writes the creep law as eps_dot = A(T) * sigma^n(T)"),
    ("card called measured data for the correct alloy",
     r"measured data for the correct alloy",
     "it is measured data for the correct alloy, at four temperatures"),
    ("stress window called the joint's operating range",
     r"stress range 7\.5-15\.9 MPa is exactly the range a solder joint",
     "its stress range 7.5-15.9 MPa is exactly the range a solder joint operates in"),
    ("card described as near its calibrated range",
     r"near its calibrated range",
     "the card is evaluated near its calibrated range"),
    ("extrapolation asserted to be common mode without a test",
     r"common mode and cancels in a ratio",
     "the constitutive extrapolation applies identically to all three architectures, so it is "
     "common mode and cancels in a ratio"),
    ("Yuan Table 26 cited",
     r"Table\s*26", "Yuan (2023) Materials 16(14):4922, Table 26"),
    ("Yuan Table 27 or 31 cited",
     r"Table\s*(27|31)", "Yuan 2023 Table 27, EINNs + BI re-fit"),
    ("rate-independent plasticity claimed to be present",
     r"rate-independent plastic strain (is|are) (present|computed)",
     "rate-independent plastic strain is present in the joint"),
    ("absolute life stated as a bare fact",
     r"Z2 (survives|lasts) \d+ cycles",
     "Z2 survives 3206 cycles"),
    ("experiment called frozen",
     r"experiment is (now )?FROZEN|design is frozen",
     "the experiment is now FROZEN at 34 specimens per cell"),
    ("G2 claimed tested",
     r"G2 (is|was) (now )?(TESTED|PASSED|closed|satisfied by)", "G2 is now TESTED"),
    ("optimizer claimed permitted",
     r"optimi[sz]er is (now )?(allowed|permitted|unblocked)", "the optimizer is now allowed"),
    # ---- Phase-0L-R Part 25: each pattern is paired with the VERBATIM sentence the brief
    # ---- names, and the self-test fails the build if a pattern stops catching its sentence.
    ("Z2/Z1 = 1.21-1.38 called validated",
     r"1\.21\s*(?:--|-|\u2013|\u2014|to)\s*1\.38[^.\n]{0,40}\b(is |are )?validated|"
     r"validated[^.\n]{0,30}1\.21",
     "Z2/Z1 = 1.21-1.38 is validated."),
    ("experiment called ready to execute",
     r"experiment is ready to execute|ready to execute",
     "The experiment is ready to execute."),
    ("34 specimens called sufficient",
     r"34 specimens per cell are sufficient|34\s*(?:specimens?\s*)?(?:per|/)\s*cell",
     "34 specimens per cell are sufficient."),
    ("creep model called validated to 100 MPa",
     r"creep model is validated to \d+\s*MPa|validated to 100 MPa",
     "The SAC305 creep model is validated to 100 MPa."),
    ("creep data called SAC305",
     r"creep data are SAC305|creep data is SAC305|SAC305 creep (?:data|points)",
     "The creep data are SAC305."),
    ("high-stress error said to cancel",
     r"high-stress error cancels|error cancels in the ratio",
     "The high-stress error cancels in the ratio."),
    ("A sigma^n called the current combined VISCO law",
     r"CalculiX uses A\(T\)\s*sigma\^n|"
     r"creep eps_dot_cr = A\(T\) sigma\^n|"
     r"current[^.\n]{0,40}\*?VISCO[^.\n]{0,40}A\(T\)\s*sigma\^n",
     "CalculiX uses A(T) sigma^n in the current combined *VISCO model."),
    ("Arrhenius attributed to CalculiX",
     r"CalculiX evaluates A\(T\) with an Arrhenius|CalculiX[^.\n]{0,40}Arrhenius law",
     "CalculiX evaluates A(T) with an Arrhenius law."),
    ("local reliability model called fully validated",
     r"local reliability model is fully validated|local[^.\n]{0,30}fully validated",
     "The local reliability model is fully validated."),
    ("N_required called the only remaining blocker",
     r"N_?\{?required\}? is the only remaining blocker|only remaining blocker",
     "N_required is the only remaining blocker."),
]
# Phrases that are allowed to contain a guard pattern because they are the report SAYING the
# claim is withdrawn. Scoped tightly: the exoneration must be in the same sentence.
EXONERATE = re.compile(
    r"(WITHDRAWN|withdrawn|is wrong|does not|cannot|NOT |not defensible|superseded|"
    r"corrected here|was assumed|is refuted|no Table 26|eleven tables|previously|"
    r"is the claim|tested, not assumed|rather than assumed)", re.I)


def semantic_audit(md_text: str, pdf_text: str) -> None:
    print("\n[semantic] guard self-test: every pattern must catch its own violating sentence")
    for name, pat, canonical in GUARDS:
        hit = re.search(pat, canonical, re.I)
        chk(f"self-test: {name}", bool(hit),
            "" if hit else f"pattern does not match its canonical sentence: {canonical[:70]}")
        if hit:
            chk(f"self-test not exonerated: {name}", not EXONERATE.search(canonical),
                "an exoneration term appears inside the violating sentence itself")

    print("\n[semantic] scanning the BUILT artifacts")
    for label, body in (("final Markdown", md_text), ("PDF-extracted text", pdf_text)):
        for name, pat, _ in GUARDS:
            bad = []
            for m in re.finditer(pat, body, re.I):
                a = max(0, m.start() - 320); b = min(len(body), m.end() + 320)
                window = body[a:b]
                sent = re.split(r"(?<=[.!?])\s", window)
                near = next((s for s in sent if re.search(pat, s, re.I)), window)
                if not EXONERATE.search(near):
                    bad.append(near.strip().replace("\n", " ")[:120])
            chk(f"{label}: {name}", not bad, " || ".join(bad[:2]))


def main() -> int:
    print("=" * 96)
    print("BUILD  results/ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf")
    print("=" * 96)
    raw, src, err, stats = build()
    txt = verify(raw, src, err)
    semantic_audit(raw, txt)

    npass = sum(1 for _, ok, _ in CHECKS if ok)
    ntot = len(CHECKS)
    print("\n" + "=" * 96)
    print(f"{npass}/{ntot} checks passed")
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    figs = len(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", raw))
    size_mb = PDF.stat().st_size / 1e6

    pandoc_v = subprocess.run(["pandoc", "-v"], capture_output=True, text=True).stdout.split("\n")[0]
    xetex_v = subprocess.run(["xelatex", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    LOG.write_text("\n".join([
        "# Build log --- current-framework audit report", "",
        f"| item | value |", "|---|---|",
        f"| Markdown | `{MD.name}` ({len(raw.splitlines())} lines, {len(raw)} chars) |",
        f"| PDF | `{PDF.name}` ({pages} pages, {size_mb:.2f} MB) |",
        f"| figures | {figs} |",
        f"| headings | {len(re.findall(r'^#{1,4} ', raw, re.M))} |",
        f"| glyph substitutions | {stats['subs']} |",
        f"| blank lines inserted before table headers | {stats['table_fixes']} |",
        f"| blank lines inserted before headings | {stats['heading_fixes']} |",
        f"| pandoc | {pandoc_v} |", f"| TeX | {xetex_v} |",
        f"| checks | **{npass}/{ntot} passed** |", "",
        "## Command", "", "```", stats["cmd"], "```", "",
        "## Checks", "", "| # | check | result | detail |", "|---|---|---|---|",
        *[f"| {i} | {n} | {'PASS' if ok else '**FAIL**'} | {d[:150]} |"
          for i, (n, ok, d) in enumerate(CHECKS, 1)],
    ]) + "\n")
    sem_rows = [c for c in CHECKS if c[0].startswith(("final Markdown:", "PDF-extracted text:",
                                                      "self-test:"))]
    SEM.write_text("\n".join([
        "# Post-build semantic audit --- current-framework audit report", "",
        "The scan runs on the FINAL Markdown and on the text extracted from the FINAL PDF, "
        "after generation, not on the source that was intended to produce them.", "",
        f"{sum(1 for _,ok,_ in sem_rows if ok)}/{len(sem_rows)} semantic checks passed.", "",
        "| check | result | detail |", "|---|---|---|",
        *[f"| {n} | {'PASS' if ok else '**FAIL**'} | {d[:160]} |" for n, ok, d in sem_rows],
    ]) + "\n")
    print(f"wrote {LOG}\nwrote {SEM}")
    if npass != ntot:
        print("\nBUILD NOT VERIFIED")
        return 1
    print("\nPDF VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
