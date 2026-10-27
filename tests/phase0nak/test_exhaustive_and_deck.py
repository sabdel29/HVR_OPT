"""PHASE 0N-AK --- rigorous count closure, and the deck that reports it."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
for _p in ("scripts/phase0nw", "scripts/phase0m", "scripts/phase0mr", "scripts"):
    sys.path.insert(0, str(R / _p))

EX = R / "research/phase0nak/bga_exhaustive_closure.json"
DECK = R / "presentation/prelim_hvr"


@pytest.fixture(scope="module")
def ex():
    if not EX.exists():
        pytest.skip("run scripts/phase0nak_bga_exhaustive.py")
    return json.loads(EX.read_text())


def test_every_legal_even_count_was_evaluated(ex):
    """A sampled first passing point is not a minimum."""
    for arch in ("Z1", "Z2"):
        ns = sorted(r["n_per_rail"] for r in ex["screen"] if r["arch"] == arch)
        assert ns, arch
        assert ns == list(range(2, max(ns) + 1, 2)), (
            "gaps in the enumeration for %s" % arch)
        assert len(ns) > 100


def test_adopted_minima_are_verified_on_the_resolved_grid(ex):
    """The screening grid may not decide a minimum."""
    assert ex["meta"]["verify_grid"] > ex["meta"]["screen_grid"]
    for k, c in ex["closure"].items():
        if c["status"] != "CLOSED":
            continue
        assert c["verified"] is True, k
        assert c["verified_at_grid"] == ex["meta"]["verify_grid"], k
        assert c["peak_at_n_min_A"] <= c["criterion_A"], k
        # the next LOWER legal count must fail, or this is not a minimum
        assert c["lower_count_fails"] is True, k
        if c["peak_at_lower_A"] is not None:
            assert c["peak_at_lower_A"] > c["criterion_A"], k


def test_monotonicity_is_never_assumed(ex):
    assert ex["meta"]["monotonicity_assumed"] is False
    assert ex["meta"]["exhaustive"] is True
    for c in ex["closure"].values():
        assert "monotone_above_minimum" in c or c["status"].startswith("NOT_")


def test_non_monotonicity_is_recorded_where_it_occurs(ex):
    """Adding balls can make the peak WORSE, because changing N changes which
    sites the placement rule selects. Pinned: if this stops being true, the
    deck and the findings document must be updated with it."""
    bad = {k: c["larger_counts_that_FAIL"] for k, c in ex["closure"].items()
           if c.get("larger_counts_that_FAIL")}
    assert bad, ("no larger count fails anywhere -- re-check that the sweep is "
                 "still exhaustive before relaxing this")
    for k, ns in bad.items():
        n_min = ex["closure"][k]["n_min_screen"]
        assert all(n > n_min for n in ns), k


def test_unsatisfiable_scenarios_are_not_given_a_count(ex):
    for k, c in ex["closure"].items():
        if c["status"] == "NOT_SATISFIABLE_AT_ANY_LEGAL_COUNT":
            assert c.get("n_min_verified") is None
            assert c["best_peak_A"] > c["criterion_A"]


def test_supply_and_return_are_both_recorded(ex):
    r = ex["screen"][0]
    for rail in ("supply", "return"):
        for f in ("peak_fraction", "r_eff_ohm", "imax_over_imean",
                  "peak_over_equal_share", "overlap_with_tiles"):
            assert f"{rail}_{f}" in r, (rail, f)


# --- the deck -----------------------------------------------------------

def test_deck_and_pdf_exist_with_one_page_per_slide():
    idx = DECK / "index.html"
    prt = DECK / "print.html"
    pdf = DECK / "HVR_OPT_Prelim.pdf"
    assert idx.exists() and prt.exists() and pdf.exists()
    n_slides = prt.read_text().count("<div class='pg reveal'>")
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
    assert n_slides >= 30, n_slides
    assert pages == n_slides, (pages, n_slides)


def test_every_referenced_figure_exists():
    html = (DECK / "index.html").read_text()
    for m in re.findall(r'src="(figs/[^"]+)"', html):
        assert (DECK / m).exists(), m


def test_deck_does_not_claim_a_commercial_speedup():
    html = (DECK / "index.html").read_text()
    assert "NO CONTROLLED COMMERCIAL SPEEDUP IS CLAIMED" in html


def test_deck_labels_historical_results_as_historical():
    html = (DECK / "index.html").read_text()
    assert "HISTORICAL / FROZEN R3C" in html
    assert "HISTORICAL FROZEN R3C RUNTIME" in html
    # the frozen temperatures may appear ONLY under a historical banner
    i = html.find("118.32")
    assert i > 0 and "HISTORICAL" in html[max(0, i - 1500):i]


def test_deck_keeps_the_scenarios_out_of_bracket_language():
    html = (DECK / "index.html").read_text()
    assert "named scenarios" in html
    assert "no finite RMS upper bound" in html


def test_speaker_notes_cover_the_core_slides():
    md = (DECK / "SPEAKER_NOTES.md").read_text()
    assert md.count("## Slide ") >= 30
    assert md.count("_(no notes)_") <= 6


def test_node_modules_is_not_committed():
    assert not (DECK / "node_modules").exists()
