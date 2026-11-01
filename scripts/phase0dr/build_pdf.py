#!/usr/bin/env python3
"""Build ETM_DVPD_FULL_TECHNICAL_REPORT.pdf from the Markdown deliverable.

Three responsibilities:
  1. REPAIR the Markdown in place -- a pipe table whose header row directly
     follows a non-blank line is not parsed as a table by pandoc (or GitHub);
     it degrades into a paragraph of literal '|' characters.
  2. SANITISE, for the PDF pass only, the Unicode glyphs Latin Modern lacks, so
     xelatex cannot silently DROP them. Code fences, inline code and existing
     $math$ are protected verbatim.
  3. VERIFY the output programmatically -- structure, figures, tables, glyphs
     and the absence of superseded results presented as final. A PDF that fails
     verification is reported as a failure, not shipped quietly.
"""
from __future__ import annotations
import os, re, subprocess, sys, shutil
from pathlib import Path

#: one fixed build time (honoured by xdvipdfmx and used for the log's "Built" line), so a
#: rebuild of unchanged sources writes a byte-identical build log -- the test suite rebuilds
#: this report and must leave the tracked tree clean
os.environ.setdefault("SOURCE_DATE_EPOCH", "1793000000")

ROOT = Path(__file__).resolve().parents[2]
RES  = ROOT / "results"
MD   = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
PDF  = RES / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
TMP  = RES / ".report_pdf_source.md"
TEX  = RES / ".report_structure_check.tex"

DELIM = re.compile(r"^\|[:\-\s|]+\|\s*$")
ATX   = re.compile(r"^#{1,4} \S")

COMPOUND = [("σ₁", r"$\sigma_1$"), ("ρ_Cu", r"$\rho_{Cu}$"),
            ("ρ_solder", r"$\rho_{solder}$"), ("α_GaN", r"$\alpha_{GaN}$")]
BARE = {"σ": r"$\sigma$", "ρ": r"$\rho$", "η": r"$\eta$", "α": r"$\alpha$",
        "θ": r"$\theta$", "ν": r"$\nu$", "≤": r"$\le$", "≥": r"$\ge$",
        "≈": r"$\approx$", "₁": r"$_1$", "δ": r"$\delta$", "β": r"$\beta$",
        "γ": r"$\gamma$", "λ": r"$\lambda$", "π": r"$\pi$", "τ": r"$\tau$",
        "φ": r"$\varphi$", "ω": r"$\omega$", "ε": r"$\varepsilon$",
        "κ": r"$\kappa$", "μ": r"$\mu$", "Σ": r"$\Sigma$"}
PROTECT = re.compile(r"(```.*?```|`[^`\n]*`|\$[^$\n]*\$)", re.S)


def _fence_mask(lines: list[str]) -> list[bool]:
    """True where the line sits inside a fenced code block."""
    mask, inside = [], False
    for l in lines:
        if l.strip().startswith("```"):
            mask.append(True); inside = not inside; continue
        mask.append(inside)
    return mask


def count_md_tables(text: str) -> int:
    lines = text.split("\n"); m = _fence_mask(lines)
    return sum(1 for i, l in enumerate(lines)
               if not m[i] and DELIM.match(l) and set(l) <= set("|:- "))


def count_md_headings(text: str) -> int:
    lines = text.split("\n"); m = _fence_mask(lines)
    return sum(1 for i, l in enumerate(lines) if not m[i] and ATX.match(l))


def repair_markdown() -> tuple[int, int]:
    """Insert the blank line pandoc needs before a pipe-table header row and
    before an ATX heading. Without it the construct is swallowed into the
    preceding paragraph and emitted as literal '#' / '|' text."""
    lines = MD.read_text().split("\n")
    mask = _fence_mask(lines)
    out, tfix, hfix = [], 0, 0
    for i, l in enumerate(lines):
        if mask[i]:
            out.append(l); continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        nxt_in_fence = mask[i + 1] if i + 1 < len(mask) else True
        is_header = (not nxt_in_fence and DELIM.match(nxt)
                     and set(nxt) <= set("|:- ") and l.lstrip().startswith("|"))
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
    inserted = [d for _, d in COMPOUND] + list(BARE.values())
    for i, part in enumerate(PROTECT.split(text)):
        if i % 2 == 1:                        # protected span: pass through
            out.append(part); continue
        for src, dst in COMPOUND:
            n += part.count(src); part = part.replace(src, dst)
        for src, dst in BARE.items():
            n += part.count(src); part = part.replace(src, dst)
        # pandoc does not treat a closing '$' followed by a digit as math;
        # give our own insertions a separating space so they stay math.
        for dst in inserted:
            for d in "0123456789":
                part = part.replace(dst + d, dst + " " + d)
        out.append(part)
    return "".join(out), n


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=RES, timeout=1800)
    if p.returncode != 0:
        print(p.stderr[-4000:]); sys.exit(f"failed rc={p.returncode}: {cmd[0]}")
    return p


COMMON = ["--pdf-engine=xelatex", "--toc", "--toc-depth=2",
          "-V", "geometry:margin=2.1cm", "-V", "fontsize=10pt",
          "-V", "colorlinks=true", "-V", "linkcolor=RoyalBlue",
          "-V", "urlcolor=RoyalBlue", "--resource-path", str(RES)]


def build() -> list[str]:
    global STATS
    tfix, hfix = repair_markdown()
    print(f"[repair]   blank line inserted before {tfix} table headers, {hfix} headings")
    clean, nsub = sanitise(MD.read_text())
    TMP.write_text(clean)
    print(f"[sanitise] {nsub} glyph substitutions")
    run(["pandoc", str(TMP), "-s", "-o", str(TEX), "--toc"])          # structure probe
    print("[pandoc]   building PDF")
    p = run(["pandoc", str(TMP), "-o", str(PDF)] + COMMON)
    STATS = {"table_fixes": tfix, "heading_fixes": hfix, "glyph_subs": nsub,
             "cmd": "pandoc " + " ".join([TMP.name, "-o", PDF.name] + COMMON)}
    return [l for l in p.stderr.splitlines() if l.strip()]


def verify(warn: list[str]):
    ok = True
    rows: list[tuple[str, bool, str]] = []
    def chk(label, cond, detail=""):
        nonlocal ok
        cond = bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")
        rows.append((label, cond, detail))
        ok = ok and cond

    print("\n=== PDF VERIFICATION ===")
    md, tex = MD.read_text(), TEX.read_text()
    chk("pdf exists", PDF.is_file())
    size = PDF.stat().st_size / 1e6
    chk("pdf non-trivial size", size > 0.3, f"{size:.2f} MB")

    missing = [l for l in warn if "Missing character" in l]
    chk("no glyphs dropped by the font", not missing, f"{len(missing)} dropped")

    nhd_md = count_md_headings(md)
    nhd_tex = sum(len(re.findall(r"^\\" + k + r"\{", tex, re.M))
                  for k in ("section", "subsection", "subsubsection", "paragraph"))
    chk("every markdown heading typeset as a section", nhd_md == nhd_tex,
        f"{nhd_md} in md, {nhd_tex} in tex")
    chk("no literal '#' heading leaked", not re.search(r"^#{1,4} ", tex, re.M))

    ntab_md, ntab_tex = count_md_tables(md), tex.count(r"\begin{longtable}")
    chk("every markdown table typeset as a table", ntab_md == ntab_tex,
        f"{ntab_md} in md, {ntab_tex} in tex")
    leak = tex.count("textbar{}")
    chk("no table rows leaked as literal pipes", leak == 0, f"{leak} leaked cells")

    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    # DEFECT #34: pandoc runs with cwd = results/, so a path written relative to the REPO
    # ROOT ("results/phase0g/FIG.png") resolves to results/results/... and the figure is
    # silently replaced by its alt text. Neither old check caught it: `Path(r).is_file()` is
    # evaluated from the repo root, where the path DOES exist, and `nimg >= len(refs)` is
    # satisfied by any PDF whose remaining figures contain several image objects each.
    absent = [r for r in refs if not (Path(r) if Path(r).is_absolute()
                                      else RES / r).is_file()]
    chk("all figure files exist FROM PANDOC'S WORKING DIRECTORY", not absent,
        f"{len(refs)} figures; unresolvable {absent[:3]}")
    unfetched = sorted({m.group(1) for l in warn
                        for m in [re.search(r"Could not fetch resource '([^']+)'", l)] if m})
    chk("pandoc fetched every figure", not unfetched,
        f"{len(unfetched)} replaced by alt text: {unfetched[:3]}")
    nimg = len(subprocess.run(["pdfimages", "-list", str(PDF)],
                              capture_output=True, text=True).stdout.splitlines()) - 2
    chk("figures embedded in pdf", nimg >= len(refs), f"{nimg} image objects / {len(refs)} figures")
    chk("every figure has a caption", md.count("![") == len(re.findall(r"!\[[^\]]+\]", md)),
        "no empty alt text")

    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    chk("page count plausible", pages >= 25, f"{pages} pages")
    txt = subprocess.run(["pdftotext", str(PDF), "-"], capture_output=True, text=True).stdout
    chk("text layer searchable", len(txt) > 40000, f"{len(txt)} chars extracted")
    chk("table of contents present", "Contents" in txt[:6000])
    chk("no unresolved image markup", "![" not in txt)
    chk("no literal latex leaked into text", "\\textbar" not in txt and "\\le" not in txt)

    # PHASE-0H DEFECT #32. This list was frozen at Phase 0E and still demanded the free-package
    # exchange rates 3.70 and 11.48 W/um -- headline numbers for the footprint opposition that
    # Phase 0G withdrew for mounted assemblies. A check that insists a superseded headline stay
    # in the document works against the ledger that forbids asserting it. The list now holds
    # structural markers, withdrawn values that must remain VISIBLE as retracted, and the
    # current headline numbers.
    for s in [# structural
              "INFEASIBLE", "Phase-0D-R", "Phase 0E", "ECTC-2024",
              # withdrawn, must stay visible with their retraction
              "16.2", "188.8", "46.7",
              # current headlines (Phases 0F-0H)
              "49.0",        # the DEFECT #30 scope ratio n_vr
              "6.633",       # electrical gain of the larger mounted footprint, W
              "8.287",       # free-package limit BC-B cannot recover, um
              "0.739"]:      # the free limit BC-B never recovers, um
        chk(f"expected result present: {s!r}", s in txt)

    # Phase-0E withdrew two Phase-0D-R claims. Neither may stand unqualified anywhere.
    # ---------------------------------------------------------------- semantic ledger
    # Phase-0F Sec.19: a statement that WAS true in an earlier phase must not survive into
    # the document as a CURRENT claim. Each entry is (label, pattern, exonerating context).
    # A hit is a failure unless a historical/superseded marker appears near it.
    # DEFECT #31: this list used to contain "was ", "were ", "became", "becomes" and
    # "earlier". In English technical prose at least one of those appears within any 800-
    # character window, so every ledger entry passed unconditionally. A negative test --
    # injecting three unqualified re-assertions and confirming the ledger stayed green --
    # exposed it. The vocabulary is now restricted to markers that can only be present
    # DELIBERATELY, and the window is the containing sentence rather than a page of prose.
    HIST = ("supersed", "historical record", "withdraw", "no longer", "not current",
            "phase 0b", "phase-0b", "phase 0c", "phase-0c", "phase 0d", "phase-0d",
            "artifact", "artefact", "rejected", "does not exist", "retract",
            "corrected", "previously reported", "as stated at", "we now",
            # negations and machine-readable ledger rows are not assertions
            "no interior optimum", "no active mechanical", "not a synthesis constraint",
            "must not be made", "must not be used", "nothing binds", "was an assumption",
            "_opposition**", "_188**", "exchange_rate_", "ansys_unavailable",
            "unit_consistency_defect", "no_arch_dependent", "archb_", "win_win_win",
            "assembly_state_reversal", "archb_interior_optimum", "cut the placement",
            "cannot become active", "closed it negatively", "is missing is any evidence",
            "asked whether", "the next gate should")
    LEDGER = [
        ("ANSYS licence is NOT unavailable",
         r"licence unavailable|license unavailable|licence server is down|"
         r"no ANSYS cross-validation exists", ("restored", "2026-09-06")),
        ("RDL stack is NOT open/assumed",
         r"RDL (metal )?stack is (an assumption|unsourced|OPEN)", HIST),
        ("BC-B is NOT untested",
         r"BC-?B[^.]{0,50}(NOT TESTED|is deferred|remains deferred)", HIST),
        ("MOOSE package thermal is NOT untested",
         r"MOOSE[^.]{0,60}(NOT TESTED|has not been validated)", HIST),
        # ---- Phase-0G additions: three claims this phase withdrew ----------------
        # Each was TRUE as written in an earlier phase, which is exactly why a plain
        # regex on the words cannot catch it -- the exonerating context is required.
        ("the assembly-state reversal is NOT a current claim",
         r"assembly[- ]state[^.]{0,60}revers", HIST),
        ("footprint opposition is NOT current for mounted assemblies",
         r"footprint[^.]{0,70}(oppos|the two oppose)",
         HIST + ("disappears", "negative:", "does not exist", "absent")),
        ("the ARCH_B interior optimum is NOT current",
         r"ARCH_B[^.]{0,80}interior (electrical )?optimum", HIST),
        ("BC-B is NOT presented as a valid mounted model",
         r"BC-?B[^.]{0,60}(models? (a|the) mounted|valid mounted|represents a board)", HIST),
        ("vertical-tier losses are NOT still per-regulator",
         r"per[- ]regulator[^.]{0,40}(summed|added) (with|to)[^.]{0,40}system[- ]wide", HIST),
        ("placement spread 188.8 % is NOT current", r"188\.8", HIST),
        ("exchange rate 16.2 W/um is NOT current", r"16\.2 W", HIST),
        ("exchange rate 2.03 W/um is NOT current", r"2\.03 W", HIST),
        ("no-constraint-at-240-W is NOT asserted",
         r"no (feasibility )?(reversal|constraint)[^.]{0,60}240", ("withdraw",)),
        ("RDL magnitudes are not called upper bounds",
         r"all RDL (magnitudes|values) are upper bounds", HIST),
        ("150 um tile is NOT presented as buildable",
         r"150 um tile[^.]{0,60}(is|remains) (valid|realizable|buildable)", HIST),
        # ---- Phase-0F additions ----
        ("the 150 um tile is not current",
         r"tile (thickness )?(of )?150 (um|µm)",
         HIST + ("unbuildable", "cannot", "superseded", "720", "replaced")),
        ("200/500 um substrates are not a current sweep range",
         r"200\s*(->|→|-|to)\s*500 (um|µm)",
         HIST + ("infeasible", "unbuildable", "cannot", "superseded")),
        ("Phase-0B cooling coefficient is not current at 1 kW",
         r"17\s*521", HIST + ("recalibrat", "9.47", "1 kw", "would have", "carried")),
        ("the geometry mismatch is not called harmless",
         r"does not affect trends", ("assumption", "half wrong", "was ", "tested",
                                     "never", "phase 0e", "phase-0e", "superseded")),
        ("mechanics is not claimed to bind at 1 kW",
         r"mechanic[^.]{0,60}(binds|constrain|active constraint)",
         ("not ", "no ", "would", "if ", "cannot", "nothing")),
        ("the epsilon sweep is labelled parametric",
         r"\bfeasib\w* (at|limit) (3\.04|1\.27)", ("parametric", "hypothetical")),
    ]
    print("  --- semantic ledger (Phase-0F Sec.19) ---")
    # A claim is exonerated by its SECTION as well as by its sentence. "HVR footprint is a
    # genuine ETM opposition" inside "# Phase 0E ..." or "# Positive Results (historical
    # record ...)" is a faithful record of what that phase concluded; the same sentence in
    # the Phase-0G section or the generated status block would be a live false claim. The
    # ledger therefore runs on the MARKDOWN, where headings are unambiguous, and scores each
    # hit against its own sentence OR its containing section heading.
    HIST_SECTION = ("historical record", "superseded by phase", "phase 0a", "phase 0b",
                    "phase 0c", "phase 0d", "phase 0e", "phase 0f",
                    # sections whose entire purpose is to list rejected / withdrawn items
                    "verdicts considered and rejected", "claims that must not be made",
                    "model defects discovered and fixed", "superseded")

    def sections(t: str):
        """[(start_offset, level, heading_text_lower)] for every ATX heading, in order."""
        out, off = [], 0
        for line in t.splitlines(keepends=True):
            st = line.lstrip()
            if st.startswith("#"):
                lvl = len(st) - len(st.lstrip("#"))
                out.append((off, lvl, st.strip("# \n").lower()))
            off += len(line)
        return out

    def heading_at(secs, i: int) -> str:
        """The whole enclosing heading CHAIN. A subsection inside '# Phase 0E ...' inherits
        that phase's historical framing; using only the nearest heading missed it."""
        chain: dict[int, str] = {}
        for off, lvl, h in secs:
            if off > i:
                break
            chain = {k: v for k, v in chain.items() if k < lvl}
            chain[lvl] = h
        return " || ".join(chain[k] for k in sorted(chain))

    def sentence_at(t: str, i: int) -> str:
        """The clause a claim actually lives in.

        The unit is the PARAGRAPH (or the table cell), not the sentence. Markdown is
        hard-wrapped at ~95 characters, so a newline-bounded window splits one sentence
        across several windows; and a sentence-bounded window rejects a retraction written
        in the very next sentence of the same paragraph, which a reader plainly does read as
        qualifying the claim. The paragraph is the smallest unit that is fair to the prose
        and still far tighter than the +-800-character window this replaced. Capped at 400
        characters either side.
        """
        D = ("\n\n", "|")   # paragraph or table cell -- see the docstring
        lo = max((t.rfind(d, max(0, i - 400), i) for d in D), default=-1)
        hi = min((h for h in (t.find(d, i, i + 400) for d in D) if h != -1), default=-1)
        return t[(lo + 1 if lo != -1 else max(0, i - 400)):
                 (hi if hi != -1 else min(len(t), i + 400))]

    secs = sections(md)

    # ---------------------------------------------------- CURRENT-FACING SECTION AUDIT
    # PHASE-0H DEFECT #32. The Phase-0G ledger exonerates a withdrawn claim whenever its
    # enclosing heading marks a historical phase. That is right for the narrative, and wrong
    # for the sections that speak in the PRESENT TENSE: the Executive Summary, the
    # governing-equation status, the validation status, the novelty statement, the current
    # limitations, the publication-defensible claims and the next steps. Those are now
    # GENERATED from CURRENT_SCIENTIFIC_STATUS.yaml, so a withdrawn claim appearing in one of
    # them means either a hand edit or a stale generator -- and no historical framing can
    # excuse it. Every pattern below is verified NOT to match the generated text, and the
    # whole audit is negative-tested in tests/phase0h/test_current_facing.py.
    # PHASE-0I-R: the LIVE PHASE NARRATIVE is current-facing too. Phase 0I's section is
    # headed "(current authoritative)" yet sat outside this list, so its over-claims -- "Z5 is
    # eliminated", "1.9-3.8x relative life", "Z1 keeps a 30 mW edge" -- were never checked. A
    # guard that cannot see the section it needs to police is not a guard.
    CURRENT_FACING = ("executive summary", "governing-equation status", "validation status",
                      "publication-defensible claims", "claims that must not be made",
                      "next steps", "current scientific status", "current authoritative",
                      "the local reliability metric, exactly defined")
    # Subsections whose entire job is to NAME withdrawn or forbidden claims. A stale claim
    # printed there is the record working, not the defect.
    CF_EXEMPT = ("superseded", "verdicts considered and rejected",
                 "claims that must not be made", "defects logged")
    FORBIDDEN_IN_CURRENT = [
        ("thickness called win/win/win", r"win/win/win"),
        ("architecture-independent thickness asserted",
         r"[Nn]o architecture-dependent thickness (tradeoff|trade-off) exists"),
        ("ARCH_B interior optimum asserted as current",
         r"ARCH_B[^.]{0,60}(develops|has|retains)(?![^.]{0,12}\bno\b)"
         r"[^.]{0,40}interior[^.]{0,30}optimum"),
        ("footprint opposition asserted as current",
         r"footprint[^.]{0,40}(is|remains) a (real|genuine)[^.]{0,20}opposition|"
         r"footprint[^.]{0,60}point in opposite directions"),
        ("R_field still divided by n_req",
         r"R_?\{?field\}?[^.\n]{0,20}=[^.\n]{0,40}n_?\{?req",
         ("superseded", "phase 0d", "phase-0d", "conflated")),
        ("MOOSE package validation still called undone",
         r"\*\*Not done:\*\*[^.]{0,120}MOOSE"),
        ("BC-B still called a compliant mounted support",
         r"BC-?B is a compliant support"),
        # A sentence that RETRACTS the comparison, or forbids it, is not making it. Without
        # this the guard fired on Phase 0H's own retraction, which would have pushed the text
        # towards deleting the record instead of correcting it.
        ("unsourced conventional-limit comparison",
         r"(?!(?:[^.]*(?:RETRACT|retract|unsourced|UNKNOWN|must not|no source)))"
         r"[^.]{0,80}orders? of magnitude below[^.]{0,60}conventional"),
        # ---- Phase-0I-R additions (Sec.20). Every one is negative-tested WITH THE REAL
        # ---- SENTENCE that appeared in the report, not with a paraphrase (DEFECT #36).
        ("relative life called parameter-free",
         r"relative[- ]life[^.\n]{0,45}parameter[- ]free|parameter[- ]free[^.\n]{0,45}relative[- ]life|"
         r"(life|N_f)[^.\n]{0,30}ratio[^.\n]{0,30}parameter[- ]free",
         ('does not cancel', 'misleading', 'not parameter-free', 'm does not', 'withdraw',
          'corrected', 'exponent does not')),
        ("total inelastic claimed without creep",
         r"(total inelastic|inelastic (strain|damage)|(?:delta|d)[- _]?eps[- _]?in|PEEQ)[^.\n]{0,75}"
         r"(plastic[- ]only|plastic strain only|excludes creep|without creep|no creep|creep[- ]free|omits creep)|"
         r"(plastic[- ]only|excludes creep|omits creep)[^.\n]{0,45}(total inelastic|inelastic strain|PEEQ)",
         ('rejected', 'disproved', 'did not occur', 'was the failure mode', 'proven', '1.0000',
          'that inference does not follow')),
        ("2.5D eliminated as a class",
         r"(2\.5D|Z5)\s+(is|are|was|were)\s+(now\s+)?eliminated|"
         r"eliminat\w+[^.\n]{0,25}2\.5D as a class|all 2\.5D[^.\n]{0,30}(eliminat|infeasible)|"
         r"(2\.5D|Z5)[^.\n]{0,25}(is|are)[^.\n]{0,20}(ruled out|infeasible|dead)",
         ('tested', 'topology', 'over-reach', 'withdraw', 'not a statement about 2.5d',
          'low-voltage-lateral')),
        ("0.300 mm called manufacturable",
         r"0\.300?\s*mm[^.\n]{0,60}(manufacturab|realizab|realisab|fully buildable|universally|is buildable)|"
         r"(manufacturab|realizab|realisab|universally)[^.\n]{0,45}0\.300?\s*mm",
         ('not a manufactur', 'component-height', 'is open', 'remains open', 'guarantee',
          'source-demonstrated', 'tsv-layer', 'where the guard looked for')),
        ("Z1 claimed electrically preferred over Z4",
         r"Z1[^.\n]{0,60}electrically (better|preferred|superior|beats)[^.\n]{0,30}Z4|"
         r"Z1[^.\n]{0,45}(beats|outperforms|wins)[^.\n]{0,30}Z4|"
         r"Z1[^.\n]{0,45}(keeps|retains|holds|maintains|enjoys)[^.\n]{0,45}(edge|advantage|lead|margin)",
         ('indistinguishable', 'unresolved', 'must not', '0.14 sigma', 'not be described',
          'frozen', 'where the guard looked for')),
        ("only one mechanical failure mechanism modelled",
         r"only\s+(one|1|ONE)\b[^.\n]{0,60}failure mechanism|"
         r"failure mechanisms?[^.\n]{0,45}only\s+(one|1|ONE)\b|"
         r"only\s+(one|1|ONE)\b[^.\n]{0,40}(is|are)\s+computable",
         ('at m0', 'historical', 'stale', 'supersed', 'no longer', 'two of eight',
          'two are now')),
        # ---- Phase-0K-R additions (DEFECT #39 and Sec.3). Verbatim self-tests below.
        ("Phase 0K named as the next work",
         r"[Nn]ext work[^.\n]{0,30}(is )?PHASE 0K\b(?![-\u2011]R)|"
         r"PHASE 0K -- SYSTEM-OWNER MISSION DEFINITION",
         ('supersed', 'phase 0k-r', 'historical', 'withdraw', 'has run',
          'phase 0k established', 'still read', 'fragments were not', 'defect #39')),
        ("-40 C test called validated by the current model",
         r"-40[^.\n]{0,50}(validated|within (the )?(validated|calibrated) domain)|"
         r"(validated|calibrated)[^.\n]{0,40}-40\s*C",
         ('withdraw', 'not validated', 'invalid', 'supersed', 'is 85 k below', 'historical',
          'cannot', 'no sub-zero')),
        ("16 specimens claimed sufficient for all scatter",
         r"16 (specimens|packages)[^.\n]{0,60}(sufficient|proven|adequate)[^.\n]{0,40}"
         r"(all|every|any)[^.\n]{0,30}(scatter|beta)|"
         r"n = 16[^.\n]{0,40}proven sufficient",
         ('insufficient', 'not sufficient', 'withdraw', 'supersed', 'marginal', 'historical')),
        ("one thermal condition claimed to identify the law",
         r"[Oo]ne (thermal )?(cycle )?condition[^.\n]{0,40}identif\w+[^.\n]{0,30}"
         r"(law|model form)|"
         r"[Aa] single (thermal )?condition[^.\n]{0,30}(identifies|can identify)",
         ('cannot', 'not identify', 'campaign', 'withdraw', 'supersed', 'historical')),
        # ---- Phase-0K additions (DEFECT #38). Each is self-tested below with the VERBATIM
        # ---- sentence that was actually standing in the report.
        ("no lifetime predicted anywhere",
         r"[Nn]o lifetime is predicted (anywhere|in this project)",
         ('supersed', 'phase 0j', 'withdraw', 'was the phase', 'no longer', 'historical')),
        ("relative life called exponent-limited",
         r"unsourced exponent|exponent m does NOT cancel, and no m\s+is sourced|"
         r"no m is sourced for this metric",
         ('supersed', 'withdraw', 'no longer unsourced', 'phase-0i parametric',
          'historical', 'bounded by the')),
        ("withdrawn 1.25-9.18 parametric life span",
         r"1\.25\s*(to|-|--|\u2013)\s*9\.18|spans 1\.25",
         ('supersed', 'withdraw', 'phase-0i parametric', 'no longer unsourced', 'historical')),
        ("no SAC305 life law asserted",
         r"[Nn]o (admissible )?SAC305 life law (exists|was retrievable|is available)|"
         r"no SAC/SnAgCu life law",
         ('supersed', 'withdraw', 'phase 0j', 'access limitation', 'historical',
          'have since been supplied')),
        ("solder fatigue said to have no life law",
         r"solder fatigue[^.\n]{0,60}(has no life law|no life law)|"
         r"but has no life law and",
         ('supersed', 'withdraw', 'phase 0j', 'historical', 'admitted four')),
        ("N_required called the sole blocker",
         r"(N_?required|required life)[^.\n]{0,40}(is|remains) the (sole|only) blocker|"
         r"(sole|only) blocker[^.\n]{0,40}(N_?required|required life)",
         ('supersed', 'withdraw', 'phase 0j-r stated', 'not the sole', 'two open',
          'historical', 'formally', 'is false', 'withdraws that', 'recorded it')),
        # ---- Phase-0J-R additions. Each is self-tested below.
        ("superseded Syed 2004 ORIGINAL constants",
         r"0\.0358|0\.0405(?![0-9])|(?<![0-9.])0\.0012(?![0-9])|(?<![0-9.])0\.0014(?![0-9])",
         ('supersed', 'original', 'withdraw', 'corrected', 'uncorrected', 'ieee ectc',
          'not to be used', 'first-cycle')),
        ("withdrawn 1.558 relative-life ratio",
         r"1\.558",
         ('withdraw', 'supersed', 'algebraic', 'unmatched', 'phase 0j reported',
          'phase-0j value')),
        ("zero-dwell waveform asserted",
         r"zero dwell|ZERO dwell|no dwell at (either|any) extreme|dwell of zero",
         ('supersed', 'wrong', 'withdraw', 'phase 0j reported', 'is a step', 'square wave',
          'doubly false', 'was wrong')),
        # Phase-0J Sec.38 / DEFECT #37: the 1.96 % thickness effect belongs to the REJECTED
        # Phase-0H smeared-interface-shear proxy, not to the M2 metric that replaced it.
        ("superseded 1.96 % local-proxy thickness result",
         r"1\.96\s*%[^.\n]{0,90}(uncertaint|below|resolv|local metric)|"
         r"(local metric|thickness effect)[^.\n]{0,60}1\.96\s*%",
         ('supersed', 'withdraw', 'rejected', 'phase-0h figure', 'historical',
          'smeared interface')),
        ("unsourced 1.9-3.8x relative-life ratio",
         r"1\.9\s*(-|--|\u2013)\s*3\.8\s*x",
         ('unsourced', 'withdraw', 'parametric', 'quoted', 'provenance', 'annotat',
          'does not cancel')),
        ("mechanics asserted to bind",
         r"\bmechanic\w*\b(?:(?!\bnot\b)[^.\n]){0,60}?\b(binds|bind|is a synthesis constraint)\b",
         ("missing", "whether", "evidence", "no criterion", "never",
          "asked", "would", "cannot", "nothing")),
    ]
    # ---- DEFECT #36: guard self-test. Every current-facing guard must reject the VERBATIM
    # ---- sentence it was written for. These strings are the real historical text, quoted from
    # ---- the report and its defect log -- not paraphrases invented to match the regexes.
    GUARD_SELFTEST = [
        ("relative life called parameter-free",
         "The relative-life ratio is parameter-free in the life-law constant C."),
        ("total inelastic claimed without creep",
         "The total inelastic damage metric is plastic-only and excludes creep by construction."),
        ("2.5D eliminated as a class", "Z5 is eliminated on electrical grounds."),
        ("0.300 mm called manufacturable", "A 0.300 mm substrate is realizable."),
        ("Z1 claimed electrically preferred over Z4", "Z1 keeps a 30 mW edge over Z4."),
        ("only one mechanical failure mechanism modelled",
         "Phase 0H also found that of eight failure mechanisms only ONE is computable at the "
         "present fidelity."),
        ("mechanics asserted to bind", "Package mechanics binds the electrical design."),
        ("unsourced 1.9-3.8x relative-life ratio",
         "The backside architecture delivers 1.9-3.8x relative life."),
        ("superseded 1.96 % local-proxy thickness result",
         "In the one local metric available the thickness effect is 1.96 %, which is 7x below "
         "that metric's own uncertainty."),
        ("superseded Syed 2004 ORIGINAL constants",
         "The life prediction model for SnAgCu is N_f = (0.0358 eps_acc)^-1."),
        ("withdrawn 1.558 relative-life ratio",
         "Z2 lives 1.558x as long as Z1."),
        ("zero-dwell waveform asserted",
         "The applied waveform is a symmetric triangle with zero dwell at either extreme."),
        ("no lifetime predicted anywhere",
         "No lifetime is predicted anywhere."),
        ("relative life called exponent-limited",
         "A RELATIVE life ratio can be reported because the life-law constant C cancels in a "
         "ratio -- but the EXPONENT m does NOT cancel, and no m is sourced for this metric and "
         "alloy."),
        ("withdrawn 1.25-9.18 parametric life span",
         "Over m = 0.5 to 5 the Z2/Z1 ratio spans 1.25 to 9.18."),
        ("no SAC305 life law asserted",
         "No admissible SAC305 life law exists for the current metric and regime."),
        ("solder fatigue said to have no life law",
         "Solder fatigue became computable at M2 but has no life law and so yields no "
         "pass/fail."),
        ("N_required called the sole blocker",
         "Requirement 2 is now the sole blocker: N_required must come from the system owner."),
        ("Phase 0K named as the next work",
         "Exact next work. PHASE 0K -- SYSTEM-OWNER MISSION DEFINITION."),
        ("-40 C test called validated by the current model",
         "The -40 C test is validated by the current SAC305 material model."),
        ("16 specimens claimed sufficient for all scatter",
         "16 specimens per cell is proven sufficient for all plausible Weibull scatter."),
        ("one thermal condition claimed to identify the law",
         "One thermal condition identifies the fatigue law."),
        # The eight pre-0I-R guards, retro-fitted with the same self-test. DEFECT #36 was a
        # Phase-0I-R defect, but nothing made these eight immune to it.
        ("thickness called win/win/win",
         "Substrate thickness is a win/win/win variable across all three domains."),
        ("architecture-independent thickness asserted",
         "No architecture-dependent thickness trade-off exists."),
        ("ARCH_B interior optimum asserted as current",
         "ARCH_B develops a genuine interior optimum in substrate thickness."),
        ("footprint opposition asserted as current",
         "The footprint effect is a real cross-domain opposition."),
        ("R_field still divided by n_req", "R_field = R_single / n_req for the via field."),
        ("MOOSE package validation still called undone",
         "**Not done:** an independent MOOSE package-mechanics validation."),
        ("BC-B still called a compliant mounted support", "BC-B is a compliant support."),
        ("unsourced conventional-limit comparison",
         "The 40 um figure is two orders of magnitude below conventional limits."),
    ]
    _by_label = {lab: (pat, rest[0] if rest else ())
                 for lab, pat, *rest in FORBIDDEN_IN_CURRENT}
    blind = []
    for lab, sent in GUARD_SELFTEST:
        pat, ctx = _by_label[lab]
        if not re.search(pat, sent, re.I):
            blind.append(f"{lab}: PATTERN MISSES ITS OWN SENTENCE")
        elif any(c in sent.lower() for c in ctx):
            blind.append(f"{lab}: EXONERATED BY ITS OWN CONTEXT")
    chk("every current-facing guard rejects the sentence it was written for",
        not blind, "; ".join(blind))
    missing = sorted({l for l, *_ in FORBIDDEN_IN_CURRENT} - {l for l, _ in GUARD_SELFTEST})
    chk("every current-facing guard has a self-test sentence", not missing, f"missing: {missing}")

    # DEFECT #32 secondary finding: two guards were written to disk with corrupted escapes
    # (a lost backslash, and \b turned into literal backspace bytes) and silently could not
    # match. A guard whose SOURCE is damaged reports PASS on everything.
    guard_src = Path(__file__).read_bytes()
    ctrl = [b for b in guard_src if b < 9 or b in (11, 12) or 14 <= b < 32]
    chk("no control characters in the guard source", not ctrl,
        f"{len(ctrl)} byte(s)")

    cf_hits = []
    for label, pat, *rest in FORBIDDEN_IN_CURRENT:
        ctx = rest[0] if rest else ()
        for m in re.finditer(pat, md, re.I):
            head = heading_at(secs, m.start())
            sent = sentence_at(md, m.start()).lower()
            if any(c in head for c in CURRENT_FACING) \
                    and not any(c in head for c in CF_EXEMPT) \
                    and not any(c in sent for c in ctx):
                cf_hits.append((label, head[-46:], " ".join(sentence_at(md, m.start()).split())[:90]))
    for label, *_ in FORBIDDEN_IN_CURRENT:
        bad = [h for h in cf_hits if h[0] == label]
        chk(f"current-facing: {label}", not bad,
            f"{len(bad)} hit(s)" + (f" e.g. [{bad[0][1]}] {bad[0][2]}" if bad else ""))

    # the generated fragments in the report must still match the generator's output
    cfp = ROOT / "results" / "phase0h" / "generated_current_facing.md"
    if cfp.is_file():
        gen = cfp.read_text()
        for name in ("exec_summary", "governing_equations", "validation_status",
                     "publication_claims"):
            blk = re.search(rf"<!-- BEGIN GENERATED: {name} -->\n.*?"
                            rf"<!-- END GENERATED: {name} -->\n", gen, re.S)
            chk(f"report carries generated block '{name}' verbatim",
                bool(blk) and blk.group(0) in md)

    for label, pat, ctx in LEDGER:
        hits = [m.start() for m in re.finditer(pat, md, re.I)]
        bad = [h for h in hits
               if not any(c in sentence_at(md, h).lower() for c in ctx)
               and not any(c in heading_at(secs, h) for c in HIST_SECTION)
               and not any(c in heading_at(secs, h) for c in ctx)]
        chk(label, not bad, f"{len(hits)} mention(s), {len(bad)} unqualified")

    # Only ASSERTIONS that ARCH_B / the LV-TSV architecture is infeasible are policed;
    # a definition ("if n_req > n_avail the architecture is infeasible") and a hypothetical
    # ("were it mechanically infeasible") are legitimate uses of the word.
    for term, ctx, label in [
            (r"ARCH_B[^.]{0,80}infeasible|LV-TSV[^.]{0,80}infeasible|"
             r"infeasible[^.]{0,60}ARCH_B",
             ("withdraw", "4.8", "unsourced", "rested on", "would become infeasible",
              "0d-r", "phase-0d-r", "not infeasible", "feasible under"),
             "ARCH_B infeasibility"),
            ("no feasibility reversal", ("withdraw",), "the 240 W feasibility negative")]:
        hits = [m.start() for m in re.finditer(term, txt, re.I)]
        bad = [h for h in hits
               if not any(c in txt[max(0, h - 900):h + 900].lower() for c in ctx)]
        chk(f"withdrawn claim never stands unqualified: {label}", not bad,
            f"{len(hits)} mentions, {len(bad)} unqualified")
    # Match the stale QUANTITIES, not the bare digits: "2.03" also occurs as a legitimate
    # Phase-0F TSV loss in mW, and flagging that would be a false positive.
    for stale, ctx in [(r"2\.03 W", ("supersed", "withdraw", "Phase 0D", "Phase-0D",
                                     "corrected", "8x", "8×")),
                       (r"1\.08 %|1\.08%", ("withdraw", "supersed", "WITHDRAWN",
                                             "corrected"))]:
        hits = [m.start() for m in re.finditer(stale, txt)]
        bad = [h for h in hits if not any(c.lower() in txt[max(0, h-700):h+700].lower() for c in ctx)]
        chk(f"stale quantity {stale!r} never presented as final", not bad,
            f"{len(hits)} mentions, {len(bad)} without retraction context")
    return ok, rows


def write_log(rows, warn, ok):
    import hashlib, datetime
    def sha(f): return hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16]
    md = MD.read_text()
    figs = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", md)
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
    pandoc_v = subprocess.run(["pandoc", "-v"], capture_output=True, text=True).stdout.split("\n")[0]
    xetex_v = subprocess.run(["xelatex", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    gens = sorted((ROOT / "scripts" / "phase0dr").glob("build_full_report*.py"))

    L = ["# PDF Build Log --- ETM_DVPD_FULL_TECHNICAL_REPORT", "",
         f"Built (SOURCE_DATE_EPOCH {os.environ['SOURCE_DATE_EPOCH']}, "
         f"{datetime.datetime.fromtimestamp(int(os.environ['SOURCE_DATE_EPOCH']), datetime.timezone.utc):%Y-%m-%d %H:%M} UTC) "
         "by `scripts/phase0dr/build_pdf.py`.",
         f"Verification: **{'PASSED' if ok else 'FAILED'}** ({sum(r[1] for r in rows)}/{len(rows)} checks).", "",
         "## Command", "", "```", STATS["cmd"], "```", "",
         "## Toolchain", "",
         "| tool | version |", "|:--|:--|",
         f"| pandoc | {pandoc_v} |", f"| TeX | {xetex_v} |",
         f"| poppler | {subprocess.run(['pdftotext','-v'],capture_output=True,text=True).stderr.splitlines()[0]} |", "",
         "## Sources", "",
         "| file | role | sha256[:16] |", "|:--|:--|:--|",
         f"| `results/{MD.name}` | Markdown deliverable ({len(md.splitlines())} lines) | `{sha(MD)}` |"]
    for g in gens:
        L.append(f"| `scripts/phase0dr/{g.name}` | section generator | `{sha(g)}` |")
    L += ["", "## Figures embedded", "", "| # | file | kB | caption |", "|--:|:--|--:|:--|"]
    for i, (cap, f) in enumerate(figs, 1):
        # figure links may be repo-relative (Phase 0G) or absolute (earlier phases)
        fp = Path(f)
        rel = fp.relative_to(ROOT) if fp.is_absolute() and fp.is_relative_to(ROOT) else fp
        abs_ = fp if fp.is_absolute() else ROOT / fp
        kb = f"{abs_.stat().st_size/1024:.0f}" if abs_.exists() else "MISSING"
        L.append(f"| {i} | `{rel}` | {kb} | {cap[:60]} |")
    L += ["", "## Output", "", "```", info.strip(), "```", "",
          "## Source repairs applied by the build", "",
          f"* blank line inserted before **{STATS['heading_fixes']} headings** and "
          f"**{STATS['table_fixes']} table header rows** --- without it pandoc (and GitHub) "
          "swallow the construct into the preceding paragraph and emit literal `#` / `|` text. "
          "The repair is written back to the Markdown, so both deliverables are correct.",
          f"* **{STATS['glyph_subs']} Unicode glyphs** absent from Latin Modern "
          "(sigma, rho, eta, alpha, theta, nu, le, approx, subscript-1) replaced with math-mode "
          "equivalents for the PDF pass only; code fences, inline code and existing `$math$` are "
          "protected. Without this xelatex drops the characters **silently**.", "",
          "## Verification checks", "", "| check | result | detail |", "|:--|:--|:--|"]
    for lab, good, det in rows:
        L.append(f"| {lab} | {'PASS' if good else 'FAIL'} | {det or '--'} |")
    L += ["", "## Warnings from the final pass", ""]
    L += (["```"] + warn[:40] + ["```"]) if warn else ["None."]
    L += ["", "## Defects this build step found and fixed", "",
          "These were introduced by the report generators and caught by the checks above, "
          "not by reading the PDF:", "",
          "1. **20 of 33 headings were not headings.** A `\\newpage` or a paragraph directly "
          "above an ATX heading absorbed it; the TOC listed 13 entries and the text showed a "
          "literal `#`. Now checked by comparing heading counts in Markdown and LaTeX.",
          "2. **4 of 16 tables were not tables** --- 142 cells rendered as literal `|` text. "
          "Same missing-blank-line cause. Now checked by comparing table counts and asserting "
          "zero `\\textbar` leakage.",
          "3. **9 glyph classes silently dropped** by Latin Modern. Now a hard failure.",
          "4. **`$\\le$0.72` was not parsed as math** --- pandoc ignores a closing `$` followed "
          "by a digit, so the raw macro reached the text layer. The sanitiser now inserts a "
          "separating space.", ""]
    (RES / "ETM_DVPD_FULL_TECHNICAL_REPORT_BUILD_LOG.md").write_text("\n".join(L))
    print(f"[log]      wrote {(RES / 'ETM_DVPD_FULL_TECHNICAL_REPORT_BUILD_LOG.md').name}")


STATS: dict = {}

if __name__ == "__main__":
    for t in ("pandoc", "xelatex", "pdfinfo", "pdftotext", "pdfimages"):
        if not shutil.which(t): sys.exit(f"missing required tool: {t}")
    warn = build()
    good, rows = verify(warn)
    write_log(rows, warn, good)
    for f in (TMP, TEX): f.unlink(missing_ok=True)
    print("\n" + ("PDF VERIFIED" if good else "PDF VERIFICATION FAILED"))
    sys.exit(0 if good else 1)
