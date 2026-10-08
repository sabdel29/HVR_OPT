#!/usr/bin/env python3
"""Phase-0H Sec.2 -- structural scope/unit guards for electrical quantities.

WHY THIS EXISTS (DEFECT #30)
`vertical_tier()` is evaluated with the PER-REGULATOR current and the PER-TILE footprint, so
its power is one regulator's loss. `rdl_network_solve()` is driven with every source and the
full load, so its power is the WHOLE SYSTEM's loss. Phases 0D-R, 0E and 0F added the two
together, understating every vertical tier by n_vr -- 4x at 240 W and 49x at the 1 kW
reference. It inverted an architecture conclusion and survived three phases and a 25x
tighter convergence tolerance.

Phase 0G fixed the arithmetic and wrote a comment. A comment cannot fail a build. This module
makes the mistake structurally impossible: a quantity carries its scope and units, and adding
two quantities whose scope or units differ raises. Converting between scopes is possible only
through an explicit call that names the conversion factor.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field, replace
from typing import Iterable


class Scope(enum.Enum):
    """What population a quantity describes."""
    PER_REGULATOR = "PER_REGULATOR"
    SYSTEM = "SYSTEM"

    def __str__(self) -> str:      # keeps f-strings and CSV columns readable
        return self.value


class ScopeError(TypeError):
    """Raised when quantities of different scope or units are combined."""


@dataclass(frozen=True)
class Q:
    """A physical quantity that knows its scope, units and provenance.

    `rail` and `tier` are carried for provenance only; they never gate arithmetic, because
    summing an HV tier and an LV tier into a total is legitimate.
    """
    value: float
    units: str
    scope: Scope
    tier: str | None = None
    rail: str | None = None

    # ---------------------------------------------------------------- arithmetic guards
    def _check(self, other: "Q", op: str) -> None:
        if not isinstance(other, Q):
            raise ScopeError(f"cannot {op} a Q and a bare {type(other).__name__}; "
                             f"wrap it with Q(value, units, scope) so its scope is explicit")
        if self.units != other.units:
            raise ScopeError(f"cannot {op} {self.units} and {other.units}")
        if self.scope is not other.scope:
            raise ScopeError(
                f"cannot {op} a {self.scope} quantity ({self.tier or '?'}) and a "
                f"{other.scope} quantity ({other.tier or '?'}) -- this is DEFECT #30. "
                f"Convert explicitly with .to_system(n_vr) or .to_per_regulator(n_vr).")

    def __add__(self, other: "Q") -> "Q":
        if other == 0 or other is None:            # allows sum() to start from 0
            return self
        self._check(other, "add")
        return Q(self.value + other.value, self.units, self.scope,
                 tier=None if self.tier != other.tier else self.tier,
                 rail=None if self.rail != other.rail else self.rail)

    __radd__ = __add__

    def __sub__(self, other: "Q") -> "Q":
        self._check(other, "subtract")
        return Q(self.value - other.value, self.units, self.scope)

    def __mul__(self, k: float) -> "Q":
        """Scaling by a DIMENSIONLESS scalar. Scope is unchanged on purpose: multiplying by
        n_vr is a scope CONVERSION and must go through to_system()."""
        if isinstance(k, Q):
            raise ScopeError("multiplying two scoped quantities is not defined here; "
                             "use .to_system(n) for a scope change")
        return replace(self, value=self.value * float(k))

    __rmul__ = __mul__

    # ---------------------------------------------------------------- scope conversion
    def to_system(self, n_vr: int) -> "Q":
        """PER_REGULATOR -> SYSTEM by multiplying by the regulator count."""
        if self.scope is Scope.SYSTEM:
            return self
        if n_vr <= 0:
            raise ScopeError(f"n_vr must be positive, got {n_vr}")
        return replace(self, value=self.value * n_vr, scope=Scope.SYSTEM)

    def to_per_regulator(self, n_vr: int) -> "Q":
        if self.scope is Scope.PER_REGULATOR:
            return self
        if n_vr <= 0:
            raise ScopeError(f"n_vr must be positive, got {n_vr}")
        return replace(self, value=self.value / n_vr, scope=Scope.PER_REGULATOR)

    def as_(self, scope: Scope, n_vr: int) -> "Q":
        return self.to_system(n_vr) if scope is Scope.SYSTEM else self.to_per_regulator(n_vr)

    def __float__(self) -> float:
        return float(self.value)

    def __repr__(self) -> str:
        t = f", {self.tier}" if self.tier else ""
        return f"Q({self.value:.6g} {self.units}, {self.scope}{t})"


# -------------------------------------------------------------------- convenience builders
def watts_per_regulator(v: float, tier: str | None = None, rail: str | None = None) -> Q:
    return Q(float(v), "W", Scope.PER_REGULATOR, tier, rail)


def watts_system(v: float, tier: str | None = None, rail: str | None = None) -> Q:
    return Q(float(v), "W", Scope.SYSTEM, tier, rail)


def total(qs: Iterable[Q], expect: Scope, units: str = "W") -> Q:
    """Sum quantities, asserting every term already has the expected scope and units.

    Using this instead of the builtin sum() is what turns DEFECT #30 from a silent
    arithmetic slip into a raised exception at the summation site.
    """
    qs = list(qs)
    if not qs:
        return Q(0.0, units, expect)
    for q in qs:
        if not isinstance(q, Q):
            raise ScopeError(f"total() got a bare {type(q).__name__}; every term must be a Q")
        if q.scope is not expect:
            raise ScopeError(f"total() expected {expect} but term {q.tier or '?'} is "
                             f"{q.scope} -- convert it explicitly (DEFECT #30)")
        if q.units != units:
            raise ScopeError(f"total() expected {units} but term {q.tier or '?'} is {q.units}")
    out = qs[0]
    for q in qs[1:]:
        out = out + q
    return replace(out, tier=None, rail=None)
