#!/usr/bin/env python3
"""Phase-0M-R2 Section 1 --- SECTION-SCOPED current-state propagation checker.

DEFECT #54. The Phase-0M-R checker searched each report as one flat string. A REQUIRED
phrase found ANYWHERE satisfied the check for the entire document, so `microchannel`
occurring in the Phase-0M-R chapter passed the cooling check while the Validation Status
block three thousand lines earlier still described the frozen inverse-calibrated Robin
boundary. It also had no way at all to detect an OMISSION: a current-facing section that
simply never mentions a production model cannot be caught by a forbidden-phrase list.

This checker asks a different question, per claim and per named section:

    does THIS section, which speaks in the present tense about THIS subject,
    carry the CURRENT wording -- and does it carry no un-qualified historical wording?

Usage:
    python scripts/phase0mr2/claim_propagation.py [--report PATH] [--json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
CONTRACT = R / "configs" / "phase0mr2" / "current_state_claims.yaml"
OUT = R / "results" / "phase0mr2"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"

# A defect row may keep the status it had AT DISCOVERY, but only if the same row says
# which later phase closed it. Without that a reader cannot tell a live defect from a
# closed one, and the Phase-0M-R report had two such rows reading as live.
SUPERSESSION_QUALIFIER = re.compile(
    r"status at discovery|superseded by Phase|closed (?:in|by) Phase|"
    r"resolved (?:in|by) Phase|CLOSED IN PHASE|now in production", re.I)


def load_contract(path: Path = CONTRACT) -> dict:
    return yaml.safe_load(path.read_text())


def split_sections(body: str) -> dict[str, tuple[int, int]]:
    """Map top-level heading text -> (start, end) character offsets.

    Front matter, before the first heading, is addressable as `__frontmatter__` so the
    date can be checked like any other claim.
    """
    marks = [(m.start(), m.group(1).strip())
             for m in re.finditer(r"(?m)^# (.+)$", body)]
    out: dict[str, tuple[int, int]] = {}
    if marks:
        out["__frontmatter__"] = (0, marks[0][0])
    for k, (i, title) in enumerate(marks):
        j = marks[k + 1][0] if k + 1 < len(marks) else len(body)
        out[title] = (i, j)
    return out


def is_historical(title: str, markers: list[str]) -> bool:
    return any(mk.lower() in title.lower() for mk in markers)


def resolve(section_key: str, sections: dict) -> list[str]:
    """A contract may name a section exactly, or name a phase chapter by prefix."""
    if section_key in sections:
        return [section_key]
    pref = [t for t in sections if t.startswith(section_key + " ")
            or t.startswith(section_key + " ---")]
    return pref


def expected_gate_sentence(meta: dict) -> tuple[str, str]:
    # One definition of the number word, shared with scripts/phase0mr3/semantic_audit.py.
    # A local copy that stopped at 20 turned a correct 21-gate report into a failure.
    import importlib.util as _ilu
    _s = _ilu.spec_from_file_location(
        "_sa", Path(__file__).resolve().parents[2] / "scripts/phase0mr3/semantic_audit.py")
    _m = _ilu.module_from_spec(_s); _s.loader.exec_module(_m)
    n = len(meta["gates"])
    return _m.NUMWORD.get(n, str(n)), ", ".join(meta["gates"])


def audit(body: str, contract: dict) -> tuple[list[dict], list[dict]]:
    sections = split_sections(body)
    markers = contract["historical_chapter_markers"]
    coverage, stale = [], []

    for c in contract["claims"]:
        cid = c["claim_id"]
        # ---- 1. is the CURRENT wording present in every section that must carry it?
        for key in c.get("required_in", []):
            targets = resolve(key, sections)
            if not targets:
                coverage.append({"claim_id": cid, "section": key, "kind": "required",
                                 "present": False, "detail": "SECTION NOT FOUND"})
                stale.append({"claim_id": cid, "section": key,
                              "problem": "section named by the contract does not exist",
                              "text": ""})
                continue
            for t in targets:
                a, b = sections[t]
                seg = body[a:b]
                ok, why = current_present(cid, c, seg, contract)
                coverage.append({"claim_id": cid, "section": t, "kind": "required",
                                 "present": ok, "detail": why})
                if not ok:
                    stale.append({"claim_id": cid, "section": t,
                                  "problem": f"current wording absent: {why}",
                                  "text": ""})

        # ---- 2. does any section carry the real stale sentence un-qualified?
        for sw in c.get("stale_wording", []):
            norm = re.sub(r"\s+", " ", sw).strip()
            for t, (a, b) in sections.items():
                seg = re.sub(r"\s+", " ", body[a:b])
                if norm not in seg:
                    continue
                allowed = [k for k in c.get("historical_allowed_in", [])
                           if t in resolve(k, sections)]
                if allowed or is_historical(t, markers):
                    # historical chapters may restate their own finding, but a DEFECT
                    # row must still say which phase closed it
                    if t == "Model Defects Discovered and Fixed":
                        i = seg.index(norm)
                        if not SUPERSESSION_QUALIFIER.search(seg[max(0, i - 400):i + 400]):
                            stale.append({"claim_id": cid, "section": t,
                                          "problem": "historical defect status with no "
                                                     "supersession qualifier",
                                          "text": norm[:160]})
                    continue
                stale.append({"claim_id": cid, "section": t,
                              "problem": "historical wording in a current-facing section",
                              "text": norm[:160]})
    return coverage, stale


def current_present(cid: str, c: dict, seg: str, contract: dict) -> tuple[bool, str]:
    """Claim-specific evidence that the CURRENT position is actually stated here."""
    seg1 = re.sub(r"\s+", " ", seg)
    if cid == "gate_count":
        # Parse the ACTUAL enumerated list that follows the phrase, and compare it
        # element by element. Scanning the section for each gate name separately
        # repeats the very defect this phase is fixing: "0M-R2" occurs elsewhere in
        # the Executive Summary, so a missing entry in the LIST went undetected.
        word, lst = expected_gate_sentence(contract["meta"])
        m = re.search(r"([\w-]+) sequential falsification gates\s*\(([^)]*)\)", seg1)
        if not m:
            return False, "no 'N sequential falsification gates (...)' sentence found"
        if m.group(1) != word:
            return False, f"count word is {m.group(1)!r}, expected {word!r}"
        got = [x.strip() for x in m.group(2).split(",") if x.strip()]
        want = list(contract["meta"]["gates"])
        if got != want:
            missing = [g for g in want if g not in got]
            extra = [g for g in got if g not in want]
            return False, (f"enumerated list differs: missing {missing or 'none'}, "
                           f"unexpected {extra or 'none'}")
        return True, f"{word}, list matches all {len(want)} gates in order"
    if cid == "phase_authority":
        # The SENTENCE that asserts authority must name the current phase. Requiring
        # only that both strings appear in the section lets "Phase 0M is the current
        # authoritative phase" pass whenever 0M-R2 is mentioned anywhere nearby.
        ph = contract["meta"]["current_authoritative_phase"]
        claims_auth = re.findall(
            r"Phase\s+(0[A-Z0-9\-]+)\s+is\s+the\s+current(?:ly)?\s+authoritative", seg1, re.I)
        if not claims_auth:
            return False, (f"no sentence of the form 'Phase {ph} is the current "
                           f"authoritative phase'")
        wrong = [x for x in claims_auth if x != ph]
        if wrong:
            return False, f"a superseded phase claims authority: {sorted(set(wrong))}"
        return True, f"Phase {ph} named as current authoritative"
    if cid == "next_work":
        return (re.search(r"0M-R2|Phase 0M-R2", seg1) is not None,
                "next-work paragraph must reference the Phase-0M-R2 ledger")
    if cid == "transition_resistance_production":
        return (re.search(r"Delta_R|\\Delta R|R_\{?3D\}?\s*-\s*R_\{?1D\}?|per-class", seg1)
                is not None,
                "electrical validation must state the per-class transition resistance")
    if cid == "cooling_production_boundary":
        return (re.search(r"microchannel|Nusselt|streamwise coolant", seg1, re.I) is not None,
                "thermal validation must state the physical cooler in production")
    if cid == "intravr_routing_production":
        return (re.search(r"intra-VR|intra_?VR", seg1, re.I) is not None,
                "defect register must record intra-VR routing")
    if cid == "cooling_model_adopted":
        return (re.search(r"cooling", seg1, re.I) is not None,
                "defect register must record the cooling model")
    if cid == "thermal_separation":
        bad = re.search(r"temperature does not matter for fatigue", seg1, re.I)
        if bad:
            return False, "FORBIDDEN phrasing 'temperature does not matter for fatigue'"
        return (re.search(r"hottest|do separate in temperature|separate in temperature",
                          seg1, re.I) is not None,
                "must state that the architectures DO separate in temperature")
    if cid == "report_date":
        m = re.search(r'date:\s*"(\d{4}-\d{2}-\d{2})"', seg1)
        if not m:
            return False, "no date in front matter"
        return (m.group(1) >= "2026-09-17", f"date is {m.group(1)}")
    return True, "no positive test defined"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(HIST))
    ap.add_argument("--out-prefix", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    contract = load_contract()
    body = Path(a.report).read_text()
    coverage, stale = audit(body, contract)

    OUT.mkdir(parents=True, exist_ok=True)
    if a.out_prefix:
        with open(OUT / "current_claim_coverage.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["claim_id", "section", "kind",
                                               "present", "detail"])
            w.writeheader(); w.writerows(coverage)
        with open(OUT / f"stale_claims_{a.out_prefix}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["claim_id", "section", "problem", "text"])
            w.writeheader(); w.writerows(stale)

    if a.json:
        print(json.dumps({"coverage": coverage, "stale": stale}, indent=1))
    else:
        for s in stale:
            print(f"  STALE  {s['claim_id']:32s} [{s['section'][:38]}] {s['problem']}")
        miss = [c for c in coverage if not c["present"]]
        print(f"\n{len(coverage) - len(miss)}/{len(coverage)} required placements present, "
              f"{len(stale)} stale finding(s)")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
