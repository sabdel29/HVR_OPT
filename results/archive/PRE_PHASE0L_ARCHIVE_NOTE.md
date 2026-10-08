# Pre-Phase-0L archive

Phase-0L brief, Part XXIV: "Archive the pre-Phase-0L PDF byte-identical."

| file | md5 | matches `results/phase0l/BASELINE.md`? |
|---|---|---|
| `pre_phase0l_ETM_DVPD_FULL_TECHNICAL_REPORT.md` | `3b536332bd90d55e1655f7a3a46f236f` | yes |
| `pre_phase0l_ETM_DVPD_FULL_TECHNICAL_REPORT.pdf` | `250ba2b4da6099691654dded2f367544` | yes |
| `pre_phase0l_CURRENT_SCIENTIFIC_STATUS.yaml` | `622e35dba403094d780a1c8c80b59455` | yes |

**A note on the older `ETM_DVPD_FULL_TECHNICAL_REPORT_PHASE0KR.pdf` in this directory.** Its
Markdown is byte-identical to the pre-0L Markdown (`3b536332...` for both), but its **PDF bytes
differ** (`ec53fddc53fdd3342aa16aa06b72bcf0`). The two are separate xelatex builds of the same
source, and the PDF format embeds build-time identifiers, so identical Markdown does not give an
identical PDF. The file archived as the pre-0L snapshot is therefore the one whose md5 matches
the recorded baseline, not the one whose name matches the previous phase.

This is worth stating because it is a trap: a byte-identity check on a PDF verifies the build,
not the content, and a content-identity check must be run on the Markdown.
