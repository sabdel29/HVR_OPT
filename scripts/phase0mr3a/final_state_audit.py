#!/usr/bin/env python3
"""Phase-0M-R3A --- the current-state audit, before and after, and the negative tests.

BEFORE is measured against the preserved Phase-0M-R3 reports under
results/phase0mr3a/_baseline_phase0mr3/, so the delta is reproducible rather than
remembered.

NEGATIVE_CORPUS is the single definition of the offending sentences. Every one of them is
VERBATIM from a shipped Phase-0M-R3 report or from the generator that produced it; the
line reference is recorded with it. tests/phase0mr3a/ imports this list, so the tests and
the artifact cannot drift apart.
"""
from __future__ import annotations
import csv, importlib.util, sys
from pathlib import Path

import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3a"
BASE = OUT / "_baseline_phase0mr3"
HIST = "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sa = _load("sa", R / "scripts" / "phase0mr3" / "semantic_audit.py")

# (item, rule_id, source, sentence)  -- item is the Section-13 letter
NEGATIVE_CORPUS: list[tuple[str, str, str, str]] = [
    ("C", "_table_row", f"{HIST}:3686",
     "| phase | **0M-R2 complete** | "
     "`results/phase0mr2/PHASE0MR2_REALIZABILITY_COOLING_STATE_CLOSURE.md` |"),
    ("C", "_table_row", f"{HIST}:3700",
     "| component partition status | **ZERO OF TWELVE REALIZABLE, AT ANY CORNER OF THE "
     "BOUNDED CLEARANCE ENVELOPE."),
    ("E", "single_next_work", f"{HIST}:4276",
     "acquisition in parallel; (2) ADOPT the Phase-0M physical cooling model into the ETM "
     "loop; (3)"),
    ("E", "single_next_work", f"{HIST}:4277",
     "PUT THE RDL IN THE MECHANICAL MESH, which is the largest unmodelled mechanism that "
     "could change"),
    ("F", "response_not_damage_life_failure", f"{HIST}:78",
     "the backside architecture shows 35.8 % less local damage than embedded"),
    ("F", "response_not_damage_life_failure", f"{STAND}:815",
     "Z2 accumulates less solder-fatigue damage than Z1"),
    ("F", "response_not_damage_life_failure", "0M-R3 current_facing wording",
     "Z2 outlives Z1 at the operating baseline."),
    ("G", "historical_358_not_current", f"{HIST}:78",
     "the backside architecture shows 35.8 % less local damage than embedded and the "
     "power-die architecture 12.4 % more"),
    ("O", "via_provenance_precise", f"{HIST}:133",
     "close the TSV process margin on ARCH_Z2, either by adopting the sourced 34 um via "
     "or by"),
    ("P", "gate_count", f"{STAND}:74",
     "**Method.** Twenty sequential falsification gates (0B, 0C, 0D, 0D-R, 0E, 0F, 0G, 0H, "
     "0I, 0I-R, 0J, 0J-R, 0K, 0K-R, 0L, 0L-R, 0M, 0M-R, 0M-R2, 0M-R3), each designed so "
     "that a negative result would stop the project rather than be absorbed."),
]

# Sentences that LOOK like the forbidden ones but are the record working correctly. A
# guard that rejects these is over-firing, which is how Phase 0M-R3 lost three invariants.
POSITIVE_CONTROL: list[tuple[str, str]] = [
    ("via_provenance_precise",
     "THE WORDING `SOURCED 34 um VIA` IS WITHDRAWN. No primary source specifies 34 um; "
     "what is source-backed is the RANGE."),
    ("response_not_damage_life_failure",
     "No current claim says Z2 outlives Z1; absolute life is not earned."),
    ("historical_358_not_current",
     "The historical Phase-0I figure of 35.8 % is NOT the present architecture result."),
]

ANCHOR = "**Method.**"


def inject(body: str, sentence: str) -> str:
    assert ANCHOR in body
    return body.replace(ANCHOR, sentence + "\n\n" + ANCHOR, 1)


def table_row_guard(body: str):
    import re
    return re.search(
        r"(?m)^\|[^|]*\|\s*\*\*(?:ZERO OF TWELVE REALIZABLE|0M-R2 complete)", body)


def scan(body: str, c: dict) -> list[dict]:
    return sa.audit(body, c)


def main() -> int:
    c = yaml.safe_load(CONTRACT.read_text())
    cur = {"historical": (R / "results" / HIST).read_text(),
           "standalone": (R / "results" / STAND).read_text()}
    before = {"historical": (BASE / HIST).read_text(),
              "standalone": (BASE / STAND).read_text()}

    for tag, corpus in (("before", before), ("after", cur)):
        rws = []
        for doc, body in corpus.items():
            for f in scan(body, c):
                rws.append({"document": doc, "rule_family": f["rule_family"],
                            "rule_id": f["rule_id"], "section": f["section"],
                            "problem": f["problem"], "text": f["text"]})
            if table_row_guard(body):
                rws.append({"document": doc, "rule_family": "structural",
                            "rule_id": "stale_current_state_row",
                            "section": "Current scientific status",
                            "problem": "a superseded phase is asserted as current state",
                            "text": table_row_guard(body).group(0)})
        p = OUT / f"stale_claims_{tag}.csv"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, ["document", "rule_family", "rule_id", "section",
                                    "problem", "text"])
            w.writeheader(); w.writerows(rws)
        print(f"  {tag:6s} {len(rws):3d} finding(s) -> {p.name}")

    rws, fails = [], 0
    for item, rid, src, sentence in NEGATIVE_CORPUS:
        if rid == "_table_row":
            fired = bool(table_row_guard(sentence + "\n"))
            got = "stale_current_state_row" if fired else ""
        else:
            hits = scan(inject(cur["historical"], sentence), c)
            got = ";".join(sorted({f["rule_id"] for f in hits}))
            fired = rid in got.split(";")
        fails += not fired
        rws.append({"item": item, "kind": "negative", "rule_id": rid, "source": src,
                    "sentence": sentence, "guard_fired": fired, "rules_that_fired": got})
    for rid, sentence in POSITIVE_CONTROL:
        hits = scan(inject(cur["historical"], sentence), c)
        got = ";".join(sorted({f["rule_id"] for f in hits}))
        ok = rid not in got.split(";")
        fails += not ok
        rws.append({"item": "-", "kind": "control", "rule_id": rid, "source": "0M-R3A",
                    "sentence": sentence, "guard_fired": not ok, "rules_that_fired": got})
    p = OUT / "semantic_negative_tests.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, ["item", "kind", "rule_id", "source", "sentence",
                                "guard_fired", "rules_that_fired"])
        w.writeheader(); w.writerows(rws)
    n_neg = sum(1 for r in rws if r["kind"] == "negative")
    print(f"  negative tests {n_neg} rejected, {len(rws) - n_neg} controls passed, "
          f"{fails} FAILURE(S) -> {p.name}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
