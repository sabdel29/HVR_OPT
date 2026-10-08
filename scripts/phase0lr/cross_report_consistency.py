#!/usr/bin/env python3
"""Phase-0L-R Part 24 -- do BOTH reports agree with the contract, and with each other?

The contract is results/CURRENT_SCIENTIFIC_STATUS.yaml. Both PDFs are re-opened, their text is
extracted AFTER generation, and each current claim is checked as a pair of conditions:

  REQUIRED  -- at least one of these must appear (the report states the current position)
  FORBIDDEN -- none of these may appear unretracted (the report states a superseded position)

A FORBIDDEN hit inside a sentence that itself retracts the claim is not a failure; that is the
record working. Any real disagreement fails the build.
"""
from __future__ import annotations
import json, re, subprocess, sys, unicodedata
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]

# The number of completed gates is current state. It had been written out as a literal in
# five separate places and four of them went stale at once (DEFECT #57), so derive it.
import importlib.util as _ilu                                            # noqa: E402
_sp = _ilu.spec_from_file_location("_sa", R / "scripts/phase0mr3/semantic_audit.py")
_SA = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_SA)
_GATES = yaml.safe_load(
    (R / "configs/phase0mr3/semantic_contract.yaml").read_text())["meta"]["gates"]
_WORD = _SA.NUMWORD[len(_GATES)]
_PRIOR = [w for n, w in sorted(_SA.NUMWORD.items()) if n < len(_GATES)]
_CURRENT_PHASE = _GATES[-1]
OUT = R / "results" / "phase0lr"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.pdf"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf"
YML = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"

RETRACT = re.compile(
    r"WITHDRAWN|withdrawn|SUPERSEDED|superseded|no longer|was wrong|not defensible|"
    r"NOT validated|not validated|corrected|previously|before Phase 0L|refuted|must not|"
    r"never|rejected|stale|historical|retained as|is NOT|does NOT|earlier|"
    # "is BLOCKED rather than ready to execute" retracts the claim as plainly as any word in
    # the list above, but neither "blocked" nor "rather than" was in the vocabulary, so the
    # sentence read as an assertion of the very thing it denies.
    r"BLOCKED|blocked|rather than|instead of|re-sequenced|conditional|CONDITIONAL|"
    # "No template is fully realizable" negates the phrase it contains; without this
    # the checker read the denial as the assertion.
    r"No template|no template|none (?:is|are)|not realizable|zero of", re.I)


def text_of(pdf: Path) -> str:
    t = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                       capture_output=True, text=True).stdout
    return unicodedata.normalize("NFKD", t)


# A chapter of the HISTORICAL report whose heading marks it superseded is allowed to restate
# that chapter's own finding. The extracted PDF text keeps the headings, so the scope can be
# recovered from them -- without this the checker reads a chronological record as if every page
# were a present-tense claim.
# pdftotext renders a chapter heading as an optional number, the phase name, an em dash, and a
# title that may WRAP across lines -- so the superseded marker is looked for in a window after
# the match rather than on the same line.
# The separator must be a true em/en dash, as the headings use. An ASCII hyphen would let
# any in-text mention of "Phase 0J-R" match via the hyphen in "-R", silently splitting
# every real chapter and letting superseded text read as current.
CHAPTER = re.compile("^\\s*(?:\\d+\\s+)?Phase 0[A-Z](?:-R)?\\s+[\u2014\u2013]", re.M)
SUPERSEDED = re.compile(r"superseded by|extended by|SUPERSEDED", re.I)


def chapter_spans(body: str):
    """[(start, end, is_historical)] for the chronological report."""
    marks = [m.start() for m in CHAPTER.finditer(body)]
    out = []
    for k, i in enumerate(marks):
        j = marks[k + 1] if k + 1 < len(marks) else len(body)
        head = body[i:min(i + 260, j if j > i else len(body))]
        out.append((i, j, bool(SUPERSEDED.search(head))))
    return out


def sentences_with(body: str, rx: re.Pattern, spans=None):
    """Sentences containing a hit, skipping hits inside superseded chapters."""
    out = []
    for m in rx.finditer(body):
        if spans is not None:
            hist = next((h for a, b, h in spans if a <= m.start() < b), False)
            if hist:
                continue
        a = max(0, m.start() - 300); b = min(len(body), m.end() + 300)
        w = body[a:b]
        parts = re.split(r"(?<=[.!?])\s", w)
        out.append(next((s for s in parts if rx.search(s)), w))
    return out


def flex(pattern: str) -> str:
    r"""Make a pattern tolerant of the line breaks pdftotext inserts.

    A claim is a claim wherever the line happens to wrap. Matching a literal space meant
    `total applied stress` was MISSED when the PDF broke it as `total applied\nstress` --
    and, far worse, the same blindness applied to the FORBIDDEN patterns, so a stale claim
    could have passed purely because of where the typesetter broke the line. Every space
    outside a character class becomes `\s+`.
    """
    out, depth, esc = [], 0, False
    for ch in pattern:
        if esc:
            out.append(ch); esc = False; continue
        if ch == "\\":
            out.append(ch); esc = True; continue
        if ch == "[":
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
        out.append(r"\s+" if (ch == " " and depth == 0) else ch)
    return "".join(out)


def quoted(sentence: str, pattern: str) -> bool:
    """Is every occurrence of the forbidden phrase inside quotation marks?

    A report that names a forbidden claim in order to forbid it -- `The permitted conclusion
    is therefore not "TSV radius is irrelevant"` -- is the record working, not a violation.
    Matching on RETRACT words alone missed that, because the negation sits outside the
    vocabulary. A phrase the document places in quotes is being MENTIONED, not asserted.
    """
    rx = re.compile(pattern, re.I)
    spans = [m.span() for m in rx.finditer(sentence)]
    if not spans:
        return False
    quotes = [(m.start(), m.end()) for m in
              re.finditer(r"[\u201c\"][^\u201d\"]{0,200}[\u201d\"]", sentence)]
    return all(any(q0 < a and b <= q1 for q0, q1 in quotes) for a, b in spans)


# claim id -> (label, REQUIRED patterns, FORBIDDEN patterns, which reports must carry it)
CLAIMS = {
 "current_phase": ("current phase is 0M-R3",
   [r"Phase 0M-R3|PHASE 0M-R3|0M-R3"], [], ["HISTORICAL", "STANDALONE"]),
 "creep_source_alloy": ("creep data alloy is Sn3.9Ag0.6Cu, not SAC305",
   [r"Sn3\.9Ag0\.6Cu"], [r"SAC305 creep (?:data|points) \|", r"creep data are SAC305"],
   ["HISTORICAL", "STANDALONE"]),
 "solver_stress_law": ("solver drives creep with the OVERSTRESS",
   [r"overstress", r"sigma_?\{?vm\}?\s*[-−]\s*sigma_?\{?y"], [], ["HISTORICAL", "STANDALONE"]),
 "fit_stress_variable": ("the card was fitted against TOTAL APPLIED stress",
   [r"total applied (?:uniaxial )?stress"], [], ["HISTORICAL", "STANDALONE"]),
 "stress_domain": ("calibration window is 7.51-15.92 MPa",
   [r"7\.51[^0-9]{0,6}15\.92"], [], ["HISTORICAL", "STANDALONE"]),
 "high_stress_status": ("high-stress response is NOT closed",
   [r"not closed|NOT CLOSED|extrapolat"], [r"creep model is validated to \d+ ?MPa"],
   ["HISTORICAL", "STANDALONE"]),
 "relative_reliability": ("ordering robust, magnitude conditional",
   [r"conditional relative-life envelope|CONDITIONAL|conditional"],
   [r"RELATIVE LIFE IS VALIDATED", r"validated relative life"],
   ["HISTORICAL", "STANDALONE"]),
 "z2_z1_envelope": ("the current Z2/Z1 envelope is quoted, and 1.21-1.38 is not",
   [r"1\.1[5-9]|1\.2[0-9]"], [r"1\.21\s*(?:-|–|—|to)\s*1\.38"],
   ["HISTORICAL", "STANDALONE"]),
 "experiment_status": ("experiment is blocked / provisional, not ready to execute",
   [r"BLOCKED|blocked|provisional|PROVISIONAL|not frozen"],
   [r"ready to execute"], ["HISTORICAL", "STANDALONE"]),
 "sample_count": ("the superseded 34/136 design is not stated as current",
   [], [r"34 (?:specimens? )?per cell", r"136 (?:total )?packages"],
   ["HISTORICAL", "STANDALONE"]),
 "n_required": ("N_required is OPEN",
   [r"N_?\{?required\}?[^.\n]{0,40}OPEN|no field or product requirement|OPEN"],
   [r"only remaining blocker"], ["HISTORICAL", "STANDALONE"]),
 "g2": ("G2 is NOT TESTED",
   [r"NOT TESTED|not tested"], [r"G2 is (now )?(TESTED|satisfied by|closed)"],
   ["HISTORICAL", "STANDALONE"]),
 "optimizer": ("optimizer remains forbidden",
   [r"FORBIDDEN|forbidden|remains forbidden|not allowed"],
   [r"optimi[sz]er is (now )?(allowed|permitted|unblocked)"], ["HISTORICAL", "STANDALONE"]),

 # ---- Phase 0M-R. Each of these was TRUE at the end of Phase 0M and is FALSE now, so the
 # forbidden pattern is the exact wording Phase 0M used. DEFECT #53 was possible because both
 # reports agreed with each other while both were stale; agreement alone is not a check.
 "crowding_constant": ("the 1.326 global constant is retired from production",
   [r"per[- ]class|geometry-specific|0\.25[^0-9]{0,6}0\.73"],
   [r"production still multiplies every interconnect class by one global constant",
    r"one global constant, 1\.326, is applied to"], ["HISTORICAL", "STANDALONE"]),
 "cooling_in_production": ("cooling is physical and in the production loop",
   [r"Shah (?:&|and) London|Nu\s*\*?\s*k_?f\s*/\s*D_?h|microchannel"],
   [r"production ET loop still uses an inverse-calibrated Robin",
    r"cooling (?:is|remains) SCREENING-ONLY"], ["HISTORICAL", "STANDALONE"]),
 "intravr_in_ledger": ("intra-VR routing is in the production loss total",
   [r"intra-VR|intra_?VR"],
   [r"NOT IN THE PRODUCTION LOSS", r"absent from the (?:production )?total"],
   ["HISTORICAL", "STANDALONE"]),
 "rdl_anisotropy_direction": ("the RDL in-plane anisotropy claim is narrowed",
   [r"in-plane isotropic|through-thickness"],
   [r"the production RDL is 153x to 276x anisotropic",
    r"RDL is 153. to 276. anisotropic in-plane"], ["HISTORICAL", "STANDALONE"]),
 "dR_not_excess": ("Delta_R is a difference against a stated reference, not an excess",
   [r"difference against a stated|1-D reference|negative"],
   [r"excess resistance is the transferable"], ["HISTORICAL", "STANDALONE"]),
 "tsv_radius_wording": ("the licensed TSV wording is used, and the unlicensed one is not",
   [r"not an independent FIELD-LOSS lever|not a FIELD-LOSS lever|feasibility"],
   [r"TSV radius is irrelevant", r"radius does not matter"],
   ["HISTORICAL", "STANDALONE"]),
 "ordering_survives": ("Z2 stays ahead of Z1 on the driver after integration",
   [r"Z2[^.\n]{0,80}(?:better|ahead|less|lower)[^.\n]{0,40}Z1|preserved"],
   [r"Z1 (?:is now )?better than Z2 on (?:the )?(?:driver|solder)"],
   ["HISTORICAL", "STANDALONE"]),
 "z4_conditional": ("the Z4 result is stated as conditional on the layer substitution",
   [r"CONDITIONAL|conditional"],
   [r"Z4 is mechanically better than Z1"], ["HISTORICAL", "STANDALONE"]),
 "no_rate_independent_overclaim": ("the licensed plasticity wording is used",
   [], [r"rate-independent plasticity would double-count Norton"],
   ["HISTORICAL", "STANDALONE"]),
 "icepak_not_validated": ("no Icepak validation is claimed",
   [], [r"validated against Icepak", r"Icepak validation (?:is )?complete"],
   ["HISTORICAL", "STANDALONE"]),

 # ---- Phase 0M-R2. Each forbidden pattern below is the VERBATIM wording the delivered
 # Phase-0M-R report used, recovered from it, not a paraphrase.
 "gate_count_current": ("the gate count includes every completed gate",
   [rf"{_WORD} sequential falsification gates"],
   [rf"{w} sequential falsification gates" for w in _PRIOR],
   ["HISTORICAL"]),
 "phase_authority_unique": (f"only Phase {_CURRENT_PHASE} is current authoritative",
   [rf"Phase {_CURRENT_PHASE}"],
   [r"Phase 0M --- Geometry-Resolved Power Delivery, Component-Level Architecture, "
    r"Cooling and ETM-Coupling Audit \(current authoritative\)",
    r"Realizable-Template Repair, Cooling Validation and Final Current-State Closure "
    r"\(current authoritative\)"],
   ["HISTORICAL"]),
 "z4_real_geometry": ("ARCH_Z4 has a real power die, not a substituted heat source",
   [r"power die|pdie_"],
   [r"Z4's converter heat has nowhere to go",
    r"deposited in the interface layer immediately beneath the compute die"],
   ["HISTORICAL"]),
 "fifty_g_s_withdrawn": ("the 50 g/s cooling point is withdrawn",
   [r"OUT_OF_MODEL_DOMAIN|no validated correlation|withdraw"],
   [r"reaching the calibrated value needs 50 g/s in the transitional"],
   ["HISTORICAL", "STANDALONE"]),
 "tsv_span_architecture_aware": ("the TSV span is architecture-aware",
   [r"74 um|architecture-aware"],
   [r"at 1300 um no radius in the swept range works"],
   ["HISTORICAL", "STANDALONE"]),
 "nothing_realizable": ("no template is called realizable",
   [r"0 of 12|no template is|not yet buildable|NEVER"],
   [r"is fully realizable", r"templates are realizable"],
   ["HISTORICAL", "STANDALONE"]),
 "pumping_scope_declared": ("pumping power scope is stated",
   [r"FACILITY|facility"], [], ["HISTORICAL"]),
 "no_temperature_dismissal": ("the licensed temperature wording is used",
   [], [r"temperature does not matter for fatigue"], ["HISTORICAL", "STANDALONE"]),
}


def main() -> int:
    d = yaml.safe_load(YML.read_text())
    bodies = {"HISTORICAL": text_of(HIST), "STANDALONE": text_of(STAND)}
    # only the chronological report has superseded chapters; the standalone report has none
    spans = {"HISTORICAL": chapter_spans(bodies["HISTORICAL"]), "STANDALONE": None}
    rows, failures = [], []
    for cid, (label, req, forb, who) in CLAIMS.items():
        for rep in who:
            body = bodies[rep]
            ok_req = (not req) or any(re.search(flex(p), body, re.I) for p in req)
            bad = []
            for p in forb:
                for sent in sentences_with(body, re.compile(flex(p), re.I), spans[rep]):
                    if not RETRACT.search(sent) and not quoted(sent, flex(p)):
                        bad.append(" ".join(sent.split())[:120])
            status = "OK" if (ok_req and not bad) else "FAIL"
            if status == "FAIL":
                failures.append((cid, rep, label,
                                 "required statement absent" if not ok_req
                                 else f"forbidden claim unretracted: {bad[0]}"))
            rows.append({"claim_id": cid, "claim": label, "report": rep,
                         "required_present": ok_req, "forbidden_unretracted": bad[:2],
                         "status": status})
    (OUT / "cross_report_claims.json").write_text(json.dumps(
        {"contract": str(YML.relative_to(R)), "checks": rows,
         "n_checks": len(rows), "n_failures": len(failures)}, indent=1))

    L = ["# Cross-report consistency audit", "",
         "**Phase 0L-R, Part 24.** Both PDFs are re-opened after generation, their text "
         "extracted, and every current claim checked against the contract in "
         "`results/CURRENT_SCIENTIFIC_STATUS.yaml`. Machine-readable: `cross_report_claims.json`.",
         "", "| claim | report | required present | forbidden unretracted | status |",
         "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['claim']} | {r['report']} | {'yes' if r['required_present'] else '**NO**'} "
                 f"| {'**' + r['forbidden_unretracted'][0][:60] + '**' if r['forbidden_unretracted'] else 'none'} "
                 f"| {'PASS' if r['status']=='OK' else '**FAIL**'} |")
    L += ["", f"**{len(rows) - len(failures)} of {len(rows)} checks pass.**", ""]
    if failures:
        L += ["## Failures", ""]
        for cid, rep, label, why in failures:
            L.append(f"- **{rep} / {cid}** — {label}: {why}")
    else:
        L += ["No disagreement between the two reports or with the contract."]
    (OUT / "CROSS_REPORT_CONSISTENCY_AUDIT.md").write_text("\n".join(L) + "\n")

    print(f"{len(rows)-len(failures)}/{len(rows)} cross-report checks pass")
    for cid, rep, label, why in failures:
        print(f"  FAIL  {rep:>11} {cid:<22} {why[:90]}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
