# TCPMT PRE-SUBMISSION STATUS

State of `ETM_DVPD_JOURNAL_MANUSCRIPT.pdf` after the reviewer-hardening pass.

## Verdict

**A — READY FOR COAUTHOR / ADVISOR TECHNICAL REVIEW.**

Not B. The single remaining blocker is editorial rather than technical, and it is one a
coauthor should sign off rather than one a tool should decide unilaterally: the title was
changed in this pass, and the author list and venue formatting remain unresolved. Nothing
technical is outstanding.

## What was done in this pass

| task | outcome |
|---|---|
| Integration-tolerance robustness of the final local response | five-value ladder run; two tolerances converge and agree to twelve digits; three tighter ones complete zero increments. Outcome A with a one-sided bracket |
| Omitted converter-loss wording | "do not affect the comparison" narrowed to "not expected to alter the reported ordering", with exact cancellation explicitly not asserted, in both places it appeared |
| Hostile reviewer audit | eleven objections: 7 closed, 1 partially closed, 2 acceptable limitations, 1 editorial blocker |
| Title | "Reliability Response" found undefined anywhere in the manuscript; changed to "Inelastic Response" |

## Technical state

| check | result |
|---|---|
| pages | 15 |
| LaTeX errors / undefined references / overfull boxes | 0 / 0 / 0 |
| manuscript numerical audit | 82/82 values against frozen artifacts |
| near-miss variants, unaccounted ablation cells | 0, 0 |
| forbidden claims, internal vocabulary, first person | 0, 0, 0 |
| floats referenced, citations resolving | 17/17, 25/25 |
| shared ten-word sequences with the style reference | 0 |
| frozen Z1/Z2 global pair | bit-identical to the paper-freeze state |

## Open items, and who owns them

**Human-only, must be resolved before submission:**

1. **Author list, affiliations, acknowledgment and funding statement.** A provisional author
   line is in place.
2. **Venue formatting and page limit.** A generic IEEE journal class is used and the paper is
   15 pages. The publisher's author instructions are unreachable from this host and were
   **not** verified. `\balance` is currently disabled with an explanatory comment, because
   with the present reference list it costs a 2.46 pt overfull box on the last page.
3. **Confirm the title change.** "Architecture-Dependent Reliability Response" became
   "Architecture-Dependent Inelastic Response" on the finding that "reliability response"
   appeared in the title and nowhere else in the manuscript, while the paper explicitly
   declines damage, life and failure claims. The reasoning is in
   `TCPMT_HOSTILE_REVIEWER_AUDIT.md` R11; revert if a coauthor prefers the original.
4. **Page ranges for two solder-calibration references**, cited from the framework's verified
   use of their calibrations rather than from the originals.

**Scientific limitations carried into submission, all disclosed in the paper:**

* The solder constitutive card is evaluated at 15–17× yield against a fit over
  7.51–15.92 MPa. The ordering is the result; the magnitude is an envelope.
* The integration tolerance cannot be bracketed from below; no tighter tolerance converges.
* Absolute temperatures rest on a correlation validated at its laminar operating point;
  conjugate CFD was attempted and discarded, and no CFD result is claimed.
* Absolute efficiency is underestimated: inductor core loss and capacitor dielectric loss
  are not evaluated.
* Neither architecture is manufacturable or qualified; four process inputs are unavailable.
* No damage law, life relation or allowable is established, and none is applied.

## Reproduction

    python scripts/phase0mr3c/trace_local_inputs.py
    python scripts/phase0mr3c/run_final_local_response.py
    python scripts/phase0mr3c/cetol_robustness.py
    python scripts/phase0mr3c/gan_alpha_sensitivity.py
    python scripts/phase0mr3c/timing_from_replay.py
    python scripts/phase0mr3c/audit_manuscript.py
    python scripts/phase0mr3c/write_claim_audit.py

All require `PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH` so that `ccx` resolves.
