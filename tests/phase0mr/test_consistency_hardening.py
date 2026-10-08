"""Phase 0M-R -- the two blind spots found in the cross-report checker, pinned.

Both were found by the checker itself once Phase-0M-R claims were added, and both had the
same shape: a claim that IS in the document read as absent, or a claim that is NOT being
asserted read as asserted. Each test injects the REAL offending text, not a paraphrase.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0lr"))
sys.path.insert(0, str(R / "scripts" / "phase0m"))

from cross_report_consistency import RETRACT, flex, quoted        # noqa: E402


class TestLineBreakTolerance:
    # exactly as pdftotext rendered it in ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf
    WRAPPED = ("The variable mismatch, stated plainly. The creep card in this repository was "
               "fitted against total applied\nstress in the source experiments, while the "
               "solver drives it with the overstress.")

    def test_the_real_wrapped_claim_was_missed_before_and_is_found_now(self):
        pat = r"total applied (?:uniaxial )?stress"
        assert re.search(pat, self.WRAPPED, re.I) is None, \
            "if this ever matches, the bug being pinned has changed shape"
        assert re.search(flex(pat), self.WRAPPED, re.I) is not None

    def test_hardening_applies_to_FORBIDDEN_patterns_too(self):
        """The dangerous direction: a stale claim hidden by where the line broke."""
        stale = ("the production ET loop still uses an inverse-calibrated\n"
                 "Robin coefficient h = 166 000 W/m2K")
        pat = r"production ET loop still uses an inverse-calibrated Robin"
        assert re.search(pat, stale, re.I) is None
        assert re.search(flex(pat), stale, re.I) is not None

    def test_soft_hyphenation_is_tolerated(self):
        """xelatex typeset the licensed wording as `constitutive-law-\\nindependent`."""
        wrapped = ("The global package supplies a constitutive-law-\nindependent deformation "
                   "driver favoring Z2, and every presently testable combination preserves it.")
        sys.path.insert(0, str(R / "scripts" / "phase0m"))
        from pdf_text_inspect import flex as pflex
        pat = r"constitutive-law-independent deformation driver favoring Z2"
        assert re.search(pat, wrapped) is None
        assert re.search(pflex(pat), wrapped) is not None

    def test_flex_does_not_corrupt_character_classes(self):
        """A space inside [...] must stay literal, or the pattern silently changes meaning."""
        assert flex(r"a b[ c]d") == r"a\s+b[ c]d"   # outside space flexed, inside kept
        assert re.search(flex(r"N_?\{?required\}?[^.\n]{0,40}OPEN"),
                         "N_required is OPEN") is not None


class TestQuotationIsNotAssertion:
    # the real sentence from the standalone report, which FORBIDS the phrase it contains
    REAL = ('The permitted conclusion is therefore not “TSV radius is irrelevant”. '
            'It is: the TSV cross-section is not an independent field-loss lever.')

    def test_a_forbidden_phrase_inside_quotes_is_a_mention_not_a_claim(self):
        pat = r"TSV radius is irrelevant"
        assert re.search(pat, self.REAL) is not None, "the phrase really is present"
        assert not RETRACT.search(self.REAL.split(". ")[0] + "."), \
            "the retraction vocabulary alone does not save this sentence"
        assert quoted(self.REAL, pat) is True

    def test_an_UNQUOTED_assertion_is_still_caught(self):
        """The guard must not become a loophole: drop the quotes and it must fail again."""
        bare = "TSV radius is irrelevant to the field loss and may be chosen freely."
        assert quoted(bare, r"TSV radius is irrelevant") is False

    def test_one_quoted_and_one_bare_occurrence_still_fails(self):
        mixed = ('We do not say “TSV radius is irrelevant” here, but later: '
                 'TSV radius is irrelevant.')
        assert quoted(mixed, r"TSV radius is irrelevant") is False


class TestRetractionVocabulary:
    def test_the_real_blocked_sentence_is_recognised_as_a_retraction(self):
        real = ("The board-level campaign is re-sequenced, not cancelled, and is BLOCKED "
                "rather than ready to execute.")
        assert RETRACT.search(real), \
            "'BLOCKED rather than' retracts as plainly as any listed word"

    def test_a_bare_assertion_is_still_not_a_retraction(self):
        assert not RETRACT.search("The experiment is ready to execute.")
