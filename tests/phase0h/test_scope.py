"""Phase-0H Sec.2 -- negative tests for the scope/unit guard.

DEFECT #30 was a per-regulator quantity added to a system-wide one. Phase 0G fixed the
arithmetic and wrote a comment; DEFECT #31 then showed that a guard nobody has watched fail
is not a guard. Every assertion here is written so that REMOVING the protection it tests
makes it fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0h"))
sys.path.insert(0, str(R / "scripts" / "phase0e"))
sys.path.insert(0, str(R / "scripts" / "phase0dr"))

from scope import Q, Scope, ScopeError, total, watts_per_regulator, watts_system


# ------------------------------------------------------------------ the DEFECT #30 shape
def test_adding_per_regulator_to_system_raises():
    """The exact arithmetic that produced DEFECT #30 must now be impossible."""
    tsv = watts_per_regulator(0.0897768, tier="tsv")
    rdl = watts_system(0.4886, tier="rdl")
    with pytest.raises(ScopeError, match="DEFECT #30"):
        _ = tsv + rdl
    with pytest.raises(ScopeError, match="DEFECT #30"):
        _ = rdl + tsv


def test_total_rejects_a_per_regulator_term():
    tiers = [watts_per_regulator(0.09, tier="tsv"), watts_per_regulator(0.01, tier="c4")]
    with pytest.raises(ScopeError, match="DEFECT #30"):
        total(tiers + [watts_system(0.49, tier="rdl")], Scope.SYSTEM)


def test_total_rejects_a_bare_float():
    """A raw float has no scope, so it must not be silently accepted into a sum."""
    with pytest.raises(ScopeError, match="bare float"):
        total([watts_system(1.0), 2.0], Scope.SYSTEM)


def test_adding_a_bare_float_raises():
    with pytest.raises(ScopeError, match="bare float"):
        _ = watts_system(1.0) + 2.0


def test_unit_mismatch_raises():
    with pytest.raises(ScopeError, match="cannot add W and K"):
        _ = watts_system(1.0) + Q(2.0, "K", Scope.SYSTEM)
    with pytest.raises(ScopeError, match="expected W"):
        total([Q(2.0, "K", Scope.SYSTEM)], Scope.SYSTEM, units="W")


def test_multiplying_two_scoped_quantities_raises():
    """n_vr scaling is a scope CONVERSION, not a product; it must not be spelled as one."""
    with pytest.raises(ScopeError):
        _ = watts_per_regulator(1.0) * watts_system(49.0)


def test_scalar_multiplication_does_not_change_scope():
    """The DEFECT #30 fix `p_w * n_vr` looked like scaling. Scaling must NOT launder scope."""
    q = watts_per_regulator(1.0, tier="tsv") * 49
    assert q.scope is Scope.PER_REGULATOR
    assert q.value == pytest.approx(49.0)
    with pytest.raises(ScopeError, match="DEFECT #30"):
        _ = q + watts_system(1.0)


# ------------------------------------------------------------------ conversions
def test_explicit_conversion_is_the_only_way_across():
    tsv = watts_per_regulator(0.0897768, tier="tsv")
    assert tsv.to_system(49).value == pytest.approx(4.399, rel=2e-3)
    assert tsv.to_system(49).scope is Scope.SYSTEM
    assert total([tsv.to_system(49), watts_system(0.4886)], Scope.SYSTEM).value \
        == pytest.approx(4.888, rel=1e-3)


def test_conversion_round_trips():
    q = watts_per_regulator(1.234, tier="tsv")
    assert q.to_system(49).to_per_regulator(49).value == pytest.approx(1.234)


def test_conversion_is_idempotent_not_repeated():
    """to_system() on an already-system quantity must be a no-op, not a second multiply."""
    q = watts_system(4.399)
    assert q.to_system(49).value == pytest.approx(4.399)


@pytest.mark.parametrize("n", [0, -1])
def test_nonpositive_regulator_count_raises(n):
    with pytest.raises(ScopeError, match="must be positive"):
        watts_per_regulator(1.0).to_system(n)


def test_empty_total_keeps_scope():
    z = total([], Scope.SYSTEM)
    assert z.value == 0.0 and z.scope is Scope.SYSTEM


# ------------------------------------------------------------------ the evaluator itself
@pytest.fixture(scope="module")
def ev():
    import architecture0e as A
    from stack import stacks_from_cfg
    st = stacks_from_cfg()["ectc2024_primary"]
    xy = [(x, y) for x in (-5.0, 5.0) for y in (-5.0, 5.0)]
    return A, A.evaluate("ARCH_B", xy, 2.0, 1.5, 200.0, 40.0, 85.0, st)


def test_tier_results_declare_per_regulator_scope(ev):
    _, e = ev
    assert e["P_by_tier_scope"] == "SYSTEM"
    assert e["P_by_tier_per_vr_scope"] == "PER_REGULATOR"
    for t in e["tiers"]:
        assert t["scope"] == "PER_REGULATOR", t["tier"]


def test_evaluator_totals_are_system_wide(ev):
    _, e = ev
    n = e["n_vr"]
    for tier, per_vr in e["P_by_tier_per_vr_w"].items():
        assert e["P_by_tier_w"][tier] == pytest.approx(n * per_vr, rel=1e-12), tier
    assert e["P_pdn_w"] == pytest.approx(sum(e["P_by_tier_w"].values()), rel=1e-12)


def test_tier_result_exposes_a_guarded_quantity(ev):
    A, e = ev
    from stack import stacks_from_cfg
    import ppdn as ppdn0dr
    P = ppdn0dr.load_paths()
    r = A.vertical_tier_per_regulator("tsv", P["tiers"]["tsv"], "LV", 20.0, 4.0, 85.0,
                                      1.35e-3, 1.0e8, "A_min_capability")
    assert r.p.scope is Scope.PER_REGULATOR
    assert r.p_system(49).scope is Scope.SYSTEM
    assert r.p_system(49).value == pytest.approx(49 * r.p_w, rel=1e-12)
    with pytest.raises(ScopeError, match="DEFECT #30"):
        _ = r.p + watts_system(1.0)


def test_legacy_alias_still_points_at_the_explicit_function(ev):
    A, _ = ev
    assert A.vertical_tier is A.vertical_tier_per_regulator
