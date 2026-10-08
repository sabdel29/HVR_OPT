#!/usr/bin/env python3
"""Phase-0M-R Section 2 -- DEFECT #53 audit and its permanent guard.

The guard is deliberately NOT a keyword scanner over the reports. Both reports are generated
from one YAML, so a keyword scanner over them can only find what a human already suspected.
Instead every check below is a REAL SENTENCE taken verbatim from a prior artifact, paired
with the contract field it contradicts and the phase that superseded it. The build must fail
if any of them reappears in a current-facing block.

Each entry carries `source_artifact`: the file the sentence was actually copied from, so the
guard cannot be accused of testing an invented paraphrase.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
from state_contract import load as load_contract                           # noqa: E402

HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
GEN = R / "results" / "phase0g" / "generated_status_sections.md"
CF = R / "results" / "phase0h" / "generated_current_facing.md"

# (id, verbatim fragment, contract field it contradicts, superseded by, source artifact)
STALE = [
    ("S1", "Of eight enumerated failure mechanisms, ONE is computable at M0",
     "current_mechanical_capability", "Phase 0I added the solder-fatigue mechanism",
     "results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.basis[3] (Phase-0H text)"),
    ("S2", "Neither local candidate survives validation for decision use",
     "current_solder_metric_status",
     "Phase 0I supplied a convergent metric; Phase 0I-R verified it",
     "results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.basis[5] (Phase-0H text)"),
    ("S3", "both candidate sources return HTTP 403",
     "current_life_law_status",
     "Phase 0J-R obtained the primary sources and reproduced the calibration",
     "results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.g2_note (Phase-0J text)"),
    ("S4", "failure-relevant local damage metric with a sourced SAC305 constitutive model",
     "current_constitutive_status",
     "Phases 0L and 0L-R: the creep card is Sn3.9Ag0.6Cu and is not validated at package "
     "stresses",
     "results/CURRENT_SCIENTIFIC_STATUS.yaml::next_gate.rationale (Phase-0I text)"),
    ("S5", "the project has been measuring the LOAD rather than the DAMAGE",
     "current_mechanical_capability", "Phase 0I added the local inelastic damage metric",
     "results/CURRENT_SCIENTIFIC_STATUS.yaml::verdict.what_this_is_not (Phase-0H text)"),
    ("S6", "N_required is the sole blocker",
     "current_required_life_status", "Phase 0K withdrew that framing",
     "results/phase0k/G2_DECISION_REGIONS.md (quoted there in order to be refused)"),
]

# claims that must not appear unqualified anywhere current-facing (Section 24 list)
FORBIDDEN_CURRENT = [
    ("F1", r"only one mechanical mechanism (is )?computable", "current_mechanical_capability"),
    ("F2", r"no (SAC305 )?life law exists", "current_life_law_status"),
    ("F3", r"intra-VR routing is (already )?included", "current_routing_status"),
    ("F4", r"physical cooling is (already )?(active|in production|used)", "current_cooling_status"),
    ("F5", r"2\.5D (as a class )?is eliminated", "current_phase"),
    ("F6", r"TSV radius is (universally )?irrelevant", "current_phase"),
    ("F7", r"fully bidirectionally (ETM )?coupled|fully coupled ETM framework",
     "current_ET_coupling_level"),
    ("F8", r"CROWDING_DEFAULT = 1\.326 is (the )?current", "current_current_crowding_status"),
]

HIST_MARKERS = ("superseded", "SUPERSEDED", "historical", "HISTORICAL", "withdrawn",
                "WITHDRAWN", "retracted", "RETRACTED", "Phase 0H ", "Phase 0I ",
                "Phase 0J ", "no longer", "was true", "DEFECT #53", "in order to be refused",
                "NOT DEFENSIBLE", "previous text", "Historical note")


def current_facing_spans(md: str) -> list[tuple[int, int, str]]:
    """Blocks a reader would take as describing the framework NOW."""
    spans = []
    for name in ("exec_summary", "governing_equations", "validation_status",
                 "reliability_metric", "publication_claims", "current_state_contract"):
        for m in re.finditer(rf"<!-- BEGIN GENERATED: {name} -->(.*?)"
                             rf"<!-- END GENERATED: {name} -->", md, re.S):
            spans.append((m.start(), m.end(), name))
    m = re.search(r"## Current scientific status \(Phase [^)]+\)(.*?)(?=\n\\newpage|\Z)",
                  md, re.S)
    if m:
        spans.append((m.start(), m.end(), "current scientific status"))
    return spans


def sentence_at(md: str, i: int) -> str:
    a = max(md.rfind(".", 0, i), md.rfind("\n", 0, i)) + 1
    b = md.find(".", i)
    return md[a:(b + 1 if b > 0 else i + 240)]


def scan(path: Path, label: str) -> list[dict]:
    md = path.read_text()
    spans = current_facing_spans(md)
    out = []
    for sid, frag, field, superseded, src in STALE:
        for m in re.finditer(re.escape(frag), md):
            blk = next((n for a, b, n in spans if a <= m.start() < b), None)
            if blk is None:
                continue
            ctx = sentence_at(md, m.start())
            if any(h in ctx for h in HIST_MARKERS):
                continue
            out.append({"report": label, "id": sid, "block": blk, "field": field,
                        "superseded_by": superseded, "source_artifact": src,
                        "excerpt": ctx[:200]})
    for fid, pat, field in FORBIDDEN_CURRENT:
        for m in re.finditer(pat, md, re.I):
            blk = next((n for a, b, n in spans if a <= m.start() < b), None)
            if blk is None:
                continue
            ctx = sentence_at(md, m.start())
            if any(h in ctx for h in HIST_MARKERS):
                continue
            out.append({"report": label, "id": fid, "block": blk, "field": field,
                        "superseded_by": "forbidden current-facing claim",
                        "source_artifact": "Phase-0M-R Section 24 list",
                        "excerpt": ctx[:200]})
    return out


def main() -> int:
    load_contract()          # fails loudly if the contract is missing or malformed
    hits = []
    for p, lab in ((HIST, "HISTORICAL"), (STAND, "STANDALONE"),
                   (GEN, "GENERATED_STATUS"), (CF, "GENERATED_CURRENT_FACING")):
        if p.is_file():
            hits += scan(p, lab)
    for h in hits:
        print(f"  [{h['report']}] {h['id']} in <{h['block']}> contradicts "
              f"{h['field']}\n      {h['excerpt'][:150]}")
    print(f"\n{len(hits)} stale current-facing claim(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
