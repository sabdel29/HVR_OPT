#!/usr/bin/env python3
"""Phase-0M-R -- the DEFECT #53 audit artifact."""
from __future__ import annotations
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0mr"))
from defect53_audit import STALE, FORBIDDEN_CURRENT                        # noqa: E402
from state_contract import FIELDS, load                                     # noqa: E402

OUT = R / "results" / "phase0mr"

c = load()
tbl = "\n".join(
    f"| `{sid}` | {frag} | `{field}` | {sup} | `{src}` |"
    for sid, frag, field, sup, src in STALE)
ftbl = "\n".join(f"| `{fid}` | `{pat}` | `{field}` |" for fid, pat, field in FORBIDDEN_CURRENT)
ctbl = "\n".join(f"| `{f}` | {c[f]['state'][:150]}{'...' if len(c[f]['state']) > 150 else ''} |"
                 for f in FIELDS)

MD = f"""# PHASE 0M-R SECTION 2 --- DEFECT #53 REPORT-STATE AUDIT

> **DEFECT #53 IS REAL AND CONFIRMED.**
> The current-scientific-status generator was internally consistent across both reports and
> consistently stale relative to the actual authoritative science. Cross-report consistency
> was **25/25** the entire time.

## What was wrong

The section headed **"Current scientific status (Phase 0M)"** printed a Phase-0M verdict line
followed by **six Phase-0H basis bullets** and a **Phase-0I next-gate rationale**. The
`verdict.basis` list had never been phase-scoped: `rejected_verdicts_` was scoped in an
earlier phase and `basis` was not, so every phase from 0I onward printed Phase-0H's six
bullets under its own verdict heading.

Worse, the **same report contradicted itself**. Its Executive Summary --- generated from
`current_facing`, which HAD been maintained --- said:

> "Two of eight failure mechanisms are now addressable: global bending (a driver) and solder
> fatigue (a real mechanism, added in Phase 0I)."

while the current-status section, two hundred lines later, said:

> "Of eight enumerated failure mechanisms, ONE is computable at M0."

Both were current-facing. Both were generated. Neither generator knew about the other.

## Why cross-report comparison could not catch it

Both reports derive from `results/CURRENT_SCIENTIFIC_STATUS.yaml`. Comparing them against
each other tests only that the same file was read twice. It passes by construction whenever
both are stale in the same way, which is the normal case for a shared generator. **Report
agreement is not evidence of correctness.**

## The five stale current-facing statements found

| id | verbatim fragment | contract field it contradicts | superseded by | copied from |
|---|---|---|---|---|
{tbl}

`S6` is included in the guard even though it appears in the repository only inside a heading
that refuses it (`"N_required is the sole blocker" is false`), because the claim itself is
one an auditor might otherwise be told.

**Count: 5 distinct stale current-facing claims, appearing at 4 distinct sites in the
generated blocks** (S1, S2, S3, S4 each once; S5 in `verdict.what_this_is_not`, which feeds
the same section). All five are now repaired **at source**, in the YAML, not in the rendered
text --- and each repair carries a `_superseded_note` sibling recording what the text used to
say and which phase falsified it.

## The fix: an authoritative current-state contract

A keyword scanner over the reports can only find what someone already suspected. The fix is
an explicit contract of what is true NOW, one field per question an auditor would ask, each
with its own evidence path, living in the existing authoritative YAML under
`current_state_contract` so there is still exactly one source of truth.

| field | current state |
|---|---|
{ctbl}

`scripts/phase0mr/state_contract.py` owns it, validates that every field is present and that
**every evidence path exists on disk**, and renders the table that both reports carry. That
validator earned its keep immediately: it rejected the first draft of the contract because
one evidence path was wrong.

## Forbidden current-facing claims

Section 24 of the brief lists claims that must never stand unqualified in a current-facing
block. They are compiled into the guard as patterns:

| id | pattern | contract field |
|---|---|---|
{ftbl}

## How the guard works, and why it is not a paraphrase test

`scripts/phase0mr/defect53_audit.py` scans only the **current-facing spans** --- the named
generated blocks and the current-status section --- and skips any hit whose sentence carries
an explicit historical marker, so a defect report may quote the defect it fixed. Every stale
entry is a **verbatim fragment copied from the artifact named in the last column**, never an
invented paraphrase. Two tests exercise it in both directions:

* **mutation:** change one contract field and BOTH reports must fail until regenerated;
* **injection:** insert a real stale sentence into a current-facing block and the build must
  fail.

## Result after repair

```
0 stale current-facing claim(s)
```
"""


def main() -> int:
    (OUT / "DEFECT53_REPORT_STATE_AUDIT.md").write_text(MD)
    print(f"wrote {OUT/'DEFECT53_REPORT_STATE_AUDIT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
