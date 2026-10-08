#!/usr/bin/env python3
"""Phase-0M-R3 Section 1F --- semantic audit with cross-field and structural rules.

DEFECT #56. The Phase-0M-R2 checker was section-scoped, which fixed the flat-string
problem, but it stayed CONTRACT-DRIVEN: it could only find a contradiction for a claim
somebody had already entered. Five real current-facing contradictions survived it, and
two of the five are not claim-shaped at all -- a paragraph shipped four times, and two
different report dates in the same document. No list of claims can express "these two
statements contradict each other" or "this paragraph appears more than once".

Three rule families are therefore checked:

    claims       a field, its authoritative value, and the wording it licenses
    cross_field  an invariant BETWEEN fields
    structural   document shape: duplication, date coherence, sentinel uniqueness
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
OUT = R / "results" / "phase0mr3"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"

RETRACT = re.compile(
    r"WITHDRAWN|withdrawn|SUPERSEDED|superseded|no longer|was wrong|not defensible|"
    r"corrected|previously|refuted|must not|never|rejected|stale|historical|"
    r"status at discovery|is NOT|does NOT|earlier|obsolete|BLOCKED|rather than|"
    r"instead of|conditional|CONDITIONAL|No template|none (?:is|are)|not realizable",
    re.I)



# A phrase can appear in a current-facing section without being ASSERTED there. Two cases
# recur and both are the record working correctly:
#   QUOTED     "'Validated relative life' is NOT earned"  -- the phrase is being forbidden
#   NEGATED    "No template is fully realizable", "Fluent NOT INSTALLED"
# This is deliberately much narrower than the RETRACT vocabulary, which is a loose word
# list and cleared real contradictions when it was applied to cross-field rules.
# A markdown code span is a quotation too. The Phase-0M-R3A withdrawal notice
# "THE WORDING `SOURCED 34 um VIA` IS WITHDRAWN" is the record forbidding the phrase,
# not asserting it, and it must not be read as the claim it retires.
# The gate roll is spelled out in words in the executive summary. One definition, so a
# fourth copy of the count cannot drift the way the first three did (DEFECT #57).
NUMWORD = {17: "Seventeen", 18: "Eighteen", 19: "Nineteen", 20: "Twenty",
           21: "Twenty-one", 22: "Twenty-two", 23: "Twenty-three"}

_QUOTE = re.compile(r"[\u201c\u2018\"'`]")
# The negation may be a few words back within the same clause -- "No template is fully
# realizable" puts it three words before the phrase. The window stops at a clause boundary
# so a negation in a PREVIOUS sentence cannot clear this one.
_NEG_BEFORE = re.compile(
    r"(?:\bnot\b|\bno\b|\bnever\b|\bdo not\b|\bmust not\b|\bnone\b|\bnor\b|"
    r"\bwithout\b|\bcannot\b|\bneither\b)[^.;:]{0,40}$", re.I)
_NEG_AFTER = re.compile(
    r"^\W*(?:is|are|was|were)?\s*(?:NOT|not)\b|^\W*(?:NOT INSTALLED|NOT FOUND)", re.I)


def mentioned_not_asserted(seg: str, start: int, end: int) -> bool:
    """Is this occurrence quoted, or negated immediately before or after?"""
    before = seg[max(0, start - 70):start]
    after = seg[end:end + 40]
    # the negation can fall INSIDE the match, e.g. "Fluent NOT INSTALLED" when the
    # pattern is "Fluent .{0,20}(available|installed)"
    if re.search(r"\b(?:NOT|not|never|no)\b", seg[start:end]):
        return True
    if _NEG_BEFORE.search(before) or _NEG_AFTER.match(after):
        return True
    # quoted: an odd number of quote marks between the start of the sentence and here.
    # An apostrophe INSIDE a word is not a quote mark. Counting it as one silently
    # exonerated every forbidden phrase that happened to follow a possessive in the same
    # sentence -- "the joint's damage-weighted median stress" was cleared on the strength
    # of the apostrophe in "joint's" (DEFECT #61).
    sent_start = max(seg.rfind(". ", 0, start), 0)
    head = re.sub(r"(?<=[A-Za-z])['\u2019](?=[A-Za-z])", "", seg[sent_start:start])
    if len(_QUOTE.findall(head)) % 2 == 1:
        return True
    # the phrase itself wrapped in quotes
    if start > 0 and _QUOTE.match(seg[start - 1]) and end < len(seg) \
            and _QUOTE.match(seg[end]):
        return True
    return False


def load(path: Path = CONTRACT) -> dict:
    return yaml.safe_load(path.read_text())


def split_sections(body: str) -> dict[str, tuple[int, int]]:
    marks = [(m.start(), m.group(1).strip()) for m in re.finditer(r"(?m)^# (.+)$", body)]
    out: dict[str, tuple[int, int]] = {}
    if marks:
        out["__frontmatter__"] = (0, marks[0][0])
    for k, (i, title) in enumerate(marks):
        j = marks[k + 1][0] if k + 1 < len(marks) else len(body)
        out[title] = (i, j)
    return out


def is_historical(title: str, markers: list[str]) -> bool:
    return any(mk.lower() in title.lower() for mk in markers)


def resolve(key: str, sections: dict) -> list[str]:
    if key in sections:
        return [key]
    return [t for t in sections if t.startswith(key + " ")]


def paragraphs(body: str, min_chars: int) -> list[str]:
    out = []
    for p in re.split(r"\n\s*\n", body):
        s = " ".join(p.split())
        if len(s) >= min_chars and not s.startswith("|") and not s.startswith("<!--"):
            out.append(s)
    return out


# ---------------------------------------------------------------- the three families
def check_claims(body: str, c: dict, sections: dict) -> list[dict]:
    bad = []
    markers = c["historical_chapter_markers"]
    for cl in c["claims"]:
        for sw in cl.get("stale_wording", []):
            norm = re.sub(r"\s+", " ", sw).strip()
            for t, (a, b) in sections.items():
                seg = re.sub(r"\s+", " ", body[a:b])
                if norm not in seg:
                    continue
                allowed = any(t in resolve(k, sections)
                              for k in cl.get("historical_allowed_in", []))
                if allowed or is_historical(t, markers):
                    continue
                i = seg.index(norm)
                # A nearby retraction clears a QUOTED historical claim. It must NOT clear a
                # claim that is internally self-contradictory or that states the current
                # position wrongly: both the cooling wording and the "measures DAMAGE"
                # wording sat beside an unrelated "WITHDRAWN" and were cleared by it.
                if cl.get("retraction_exonerates", True) and \
                        RETRACT.search(seg[max(0, i - 300):i + 300]):
                    continue
                bad.append({"rule_family": "claim", "rule_id": cl["claim_id"],
                            "section": t, "problem": "forbidden historical wording",
                            "text": norm[:150]})
    return bad


def check_cross_field(body: str, c: dict, sections: dict) -> list[dict]:
    """Invariants BETWEEN fields. This is what Phase 0M-R2 structurally could not do."""
    bad = []
    markers = c["historical_chapter_markers"]
    auth = c["authoritative"]

    def current_sections():
        for t, (a, b) in sections.items():
            if is_historical(t, markers):
                continue
            yield t, re.sub(r"\s+", " ", body[a:b])

    for rule in c["cross_field"]:
        rid = rule["id"]
        pats = (rule.get("singular_patterns", []) + rule.get("contradiction_patterns", [])
                + rule.get("forbidden_in_current", []) + rule.get("forbidden_pairing", [])
                + rule.get("forbidden_patterns", []))
        # A cross-field rule describes a CONTRADICTION between two statements. A
        # retraction word nearby cannot resolve it -- and in practice the vocabulary
        # ("blocked", "conditional") occurs naturally in exactly these paragraphs, so
        # applying it here silently disabled three of the five invariants. Exoneration is
        # therefore opt-in per rule and off by default.
        exonerable = rule.get("retraction_exonerates", False)
        for t, seg in current_sections():
            for p in pats:
                for m in re.finditer(p, seg, re.I):
                    win = seg[max(0, m.start() - 300):m.end() + 300]
                    if exonerable and RETRACT.search(win):
                        continue
                    if mentioned_not_asserted(seg, m.start(), m.end()):
                        continue
                    bad.append({"rule_family": "cross_field", "rule_id": rid,
                                "section": t,
                                "problem": rule["description"].split(".")[0][:110],
                                "text": " ".join(m.group(0).split())[:150]})
        # positive side: if the hole is named, the production point must be named with it
        if rid == "cooling_hole_and_production_point":
            need = rule.get("requires_when_hole_mentioned", [])
            for t, seg in current_sections():
                if re.search(r"domain hole", seg, re.I) and not all(
                        re.search(re.escape(n), seg, re.I) for n in need):
                    bad.append({"rule_family": "cross_field", "rule_id": rid,
                                "section": t,
                                "problem": "names the hole without saying which point is in it",
                                "text": ""})
    return bad


def check_structural(body: str, c: dict) -> list[dict]:
    bad = []
    st = c["structural"]
    if st.get("sentinel_blocks_unique"):
        for name, n in Counter(
                re.findall(r"<!-- BEGIN GENERATED: (\w+) -->", body)).items():
            if n > 1:
                bad.append({"rule_family": "structural", "rule_id": "sentinel_unique",
                            "section": "-", "problem": f"generated block appears {n} times",
                            "text": name})
    dup = st.get("no_duplicate_paragraph")
    if dup:
        for p, n in Counter(paragraphs(body, dup["min_chars"])).items():
            if n > dup["max_occurrences"]:
                bad.append({"rule_family": "structural", "rule_id": "no_duplicate_paragraph",
                            "section": "-",
                            "problem": f"paragraph appears {n} times", "text": p[:150]})
    dc = st.get("date_coherence")
    if dc:
        fm = re.search(rf'(?m)^{dc["front_matter_key"]}:\s*"([^"]+)"', body)
        for lab in dc.get("forbidden_bare_labels", []):
            for m in re.finditer(rf"\|\s*{re.escape(lab)}\s*\|\s*([^|]+)\|", body):
                val = m.group(1).strip()
                if fm and val != fm.group(1):
                    bad.append({"rule_family": "structural", "rule_id": "date_coherence",
                                "section": "-",
                                "problem": f"'{lab}' = {val} but front matter = {fm.group(1)}",
                                "text": m.group(0)[:150]})
                else:
                    bad.append({"rule_family": "structural", "rule_id": "date_coherence",
                                "section": "-",
                                "problem": f"ambiguous bare label '{lab}'",
                                "text": m.group(0)[:150]})
        for lab in dc.get("required_labels", []):
            if lab not in body:
                bad.append({"rule_family": "structural", "rule_id": "date_coherence",
                            "section": "Provenance and tool versions",
                            "problem": f"required date label missing: '{lab}'", "text": ""})
    # Phase 0M-R3B: the provenance table is itself current state. It shipped reading
    # "Phase completed | 0M-R3" while the report's own chapter said 0M-R3A was
    # authoritative -- the same defect class as #57, in the one table a reader checks
    # first to decide how current the document is.
    pc = st.get("provenance_is_current")
    if pc:
        gate = c["meta"]["gates"][-1]
        m = re.search(r"\|\s*Phase completed\s*\|\s*([^|]+)\|", body)
        if not m:
            bad.append({"rule_family": "structural", "rule_id": "provenance_is_current",
                        "section": "Provenance and tool versions",
                        "problem": "no 'Phase completed' row", "text": ""})
        elif not m.group(1).strip().startswith(gate):
            bad.append({"rule_family": "structural", "rule_id": "provenance_is_current",
                        "section": "Provenance and tool versions",
                        "problem": f"'Phase completed' must name the current gate {gate}",
                        "text": m.group(0).strip()[:150]})
        gen = re.search(r"\|\s*Report generated\s*\|\s*([^|]+)\|", body)
        if m and gen:
            d_phase = re.search(r"\d{4}-\d{2}-\d{2}", m.group(1))
            d_gen = re.search(r"\d{4}-\d{2}-\d{2}", gen.group(1))
            if d_phase and d_gen and d_gen.group(0) < d_phase.group(0):
                bad.append({"rule_family": "structural",
                            "rule_id": "provenance_is_current",
                            "section": "Provenance and tool versions",
                            "problem": "report generated before the phase it reports",
                            "text": f"{gen.group(0)} / {m.group(0)}"[:150]})

    snw = st.get("single_next_work")
    if snw:
        body1 = re.sub(r"\s+", " ", body)
        for done in snw.get("completed_must_not_appear", []):
            for m in re.finditer(re.escape(re.sub(r"\s+", " ", done)), body1, re.I):
                win = body1[max(0, m.start() - 300):m.end() + 300]
                if re.search(r"COMPLETE|completed in Phase|done in Phase|not future work",
                             win, re.I):
                    continue
                bad.append({"rule_family": "structural", "rule_id": "single_next_work",
                            "section": "-",
                            "problem": "a COMPLETED action is listed as future work",
                            "text": done[:150]})
    if st.get("gate_count_derived"):
        want = c["meta"]["gates"]
        m = re.search(r"([\w-]+) sequential falsification gates\s*\(([^)]*)\)",
                      re.sub(r"\s+", " ", body))
        if not m:
            bad.append({"rule_family": "structural", "rule_id": "gate_count",
                        "section": "Executive Summary",
                        "problem": "no gate sentence", "text": ""})
        else:
            got = [x.strip() for x in m.group(2).split(",") if x.strip()]
            if got != want or m.group(1) != NUMWORD.get(len(want)):
                bad.append({"rule_family": "structural", "rule_id": "gate_count",
                            "section": "Executive Summary",
                            "problem": f"expected {NUMWORD.get(len(want))} and {want}",
                            "text": f"{m.group(1)} / {got}"})
    return bad


def audit(body: str, c: dict) -> list[dict]:
    s = split_sections(body)
    return check_claims(body, c, s) + check_cross_field(body, c, s) + check_structural(body, c)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-prefix", default="")
    a = ap.parse_args()
    c = load()
    rows = []
    for tag, p in (("HISTORICAL", HIST), ("STANDALONE", STAND)):
        if not p.is_file():
            continue
        for f in audit(p.read_text(), c):
            f["report"] = tag
            rows.append(f)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.out_prefix:
        with open(OUT / f"stale_claims_{a.out_prefix}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["report", "rule_family", "rule_id",
                                               "section", "problem", "text"])
            w.writeheader(); w.writerows(rows)
    for r in rows:
        print(f"  {r['report']:10s} {r['rule_family']:12s} {r['rule_id']:34s} "
              f"[{r['section'][:26]}] {r['problem'][:70]}")
    fam = Counter(r["rule_family"] for r in rows)
    print(f"\n{len(rows)} finding(s)  {dict(fam)}")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
