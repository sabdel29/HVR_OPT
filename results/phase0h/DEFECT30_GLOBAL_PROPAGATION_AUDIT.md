# Phase 0H Sec. 2 — Propagating DEFECT #30 through every authoritative electrical result

## 1. The defect, and why a comment was not enough

`vertical_tier()` is evaluated with the **per-regulator** current and the **per-tile**
footprint, so its power is one regulator's via-field loss. `rdl_network_solve()` is driven with
every source and the full load, so its power is the **whole system's** lateral loss. Phases
0D-R, 0E and 0F added the two directly, understating every vertical tier by `n_vr`.

Phase 0G corrected the arithmetic at the single summation site and wrote a comment explaining
it. A comment cannot fail a build, and DEFECT #31 had just demonstrated that a guard nobody has
watched fail is not a guard.

## 2. The API now carries scope structurally

`scripts/phase0h/scope.py` introduces a quantity that knows what population it describes:

```
Q(value, units, scope: PER_REGULATOR | SYSTEM, tier, rail)
```

* `Q.__add__` raises `ScopeError` if scope **or** units differ. The error text names DEFECT #30.
* `total(terms, expect=Scope.SYSTEM)` rejects any term whose scope is not the expected one, and
  rejects bare floats outright — a raw number has no scope and must not enter a sum.
* Scalar multiplication deliberately **does not** change scope, so the old `p_w * n_vr`
  spelling cannot launder a per-regulator quantity into a system one. Crossing scopes requires
  the explicit `to_system(n_vr)` / `to_per_regulator(n_vr)`.
* `vertical_tier()` is renamed **`vertical_tier_per_regulator()`** (the old name kept as an
  alias), and `TierResult` carries a `scope` **field**, so the scope reaches every CSV and JSON
  the object is written into.

`evaluate()` now sums through `total(...)`, so the defect is a raised exception at the
summation site rather than a silent factor of 49.

### Negative-tested, not asserted

`tests/phase0h/test_scope.py` — 17 tests, all written so that removing the protection makes
them fail. Two mutations were run to confirm this:

| mutation | result |
|---|---|
| disable the scope check inside `Q._check` | **3 tests fail** |
| revert `evaluate()` to the DEFECT #30 arithmetic (`r.p` instead of `r.p_system(n_vr)`) | **`ScopeError` raised; 1 failure + 4 errors** |

Both were reverted and the suite is green.

## 3. 240-W replay — and the Phase-0E ranking DID move

All eleven Phase-0E candidates were re-run with the corrected, scope-guarded evaluator, written
to `results/phase0h/` so that `results/phase0e/` stays untouched.

| case | P_elec published (W) | P_elec corrected (W) | Δ (mW) | Δ % |
|---|---|---|---|---|
| ARCH_A distributed j=2.0 h=0.5 | 22.5303 | 22.5529 | +22.64 | +0.100 |
| ARCH_A asymmetric j=2.0 h=0.5 | 33.0517 | 33.0748 | +23.06 | +0.070 |
| ARCH_A edge j=2.0 h=0.5 | 26.9816 | 27.0045 | +22.88 | +0.085 |
| ARCH_A compact j=2.0 h=0.5 | 28.2183 | 28.2413 | +23.01 | +0.082 |
| ARCH_A distributed j=2.0 h=0.2 | 22.6823 | 22.6987 | +16.40 | +0.072 |
| **ARCH_B distributed j=2.0 h=0.2** | 22.6983 | 22.7627 | **+64.42** | +0.284 |
| **ARCH_B distributed j=2.0 h=0.5** | 22.6417 | 22.9985 | **+356.83** | **+1.576** |
| ARCH_A distributed j=1.5 h=0.2 | 17.8488 | 17.8649 | +16.05 | +0.090 |
| ARCH_A distributed j=1.5 h=0.5 | 17.7844 | 17.8068 | +22.40 | +0.126 |
| ARCH_A distributed j=4.0 h=0.2 | 38.7276 | 38.7456 | +17.97 | +0.046 |
| ARCH_A distributed j=4.0 h=0.5 | 37.8271 | 37.8517 | +24.58 | +0.065 |

**Ranking identical: NO.** Three positions moved:

| position | published | corrected |
|---|---|---|
| 3 | ARCH_B distributed h=0.5 | ARCH_A distributed h=0.2 |
| 4 | ARCH_A distributed h=0.2 | ARCH_B distributed h=0.2 |
| 5 | ARCH_B distributed h=0.2 | ARCH_B distributed h=0.5 |

The correction is **architecture-selective**, which is exactly why it changes an ordering rather
than shifting a curve. ARCH_A carries only leakage-scale current on its vias, so its tiers move
by 16–25 mW. ARCH_B routes the **1 V rail** through the via field, so at `h = 0.5 mm` it moves
by **357 mW** — 15× more — and drops from third-best to worst of the five distributed cases.

**DEFECT #30 flattered ARCH_B at 240 W as well as at 1 kW.** Phase 0G established that it
manufactured ARCH_B's interior optimum at the reference scale; this shows it also inverted an
architecture comparison two phases earlier, at a scale nobody had re-examined.

## 4. 1-kW interconnect decomposition, system-wide

Every column is **SYSTEM** scope, `n_vr = 49`:

| arch | h_sub (mm) | P_conv | P_TSV | P_RDL | P_µbump | P_BGA | **P_PDN** | P_total |
|---|---|---|---|---|---|---|---|---|
| ARCH_A | 0.80 | 124.4343 | 0.0102 | 0.6421 | 0.0563 | 0.0116 | **0.7202** | 125.1546 |
| ARCH_A | 1.50 | 124.3810 | 0.0994 | 0.6419 | 0.0563 | 0.0116 | **0.8092** | 125.1902 |
| ARCH_A | 2.00 | 124.3742 | 0.1632 | 0.6419 | 0.0563 | 0.0116 | **0.8729** | 125.2471 |
| ARCH_B | 0.80 | 124.4467 | 0.4503 | 0.6422 | 0.0563 | 0.0116 | **1.1604** | 125.6071 |
| ARCH_B | 1.50 | 124.5020 | 4.3918 | 0.6424 | 0.0564 | 0.0116 | **5.1021** | 129.6042 |
| ARCH_B | 2.00 | 124.5729 | 7.2100 | 0.6438 | 0.0564 | 0.0116 | **7.9206** | 132.4934 |

Two structural facts, both only visible once the scopes agree:

1. **ARCH_B's via field is the entire architecture difference.** `P_TSV` grows 0.45 → 7.21 W
   across the thickness range while every other tier is flat. `P_RDL` changes by 0.3 %.
2. **The Phase-0D-R claim that lateral RDL dominates distribution loss is now
   architecture-conditional.** It holds for ARCH_A at every thickness (RDL 0.64 W against TSV
   0.01–0.16 W). It fails for ARCH_B above roughly 0.9 mm, where the via field exceeds the RDL
   by up to 11×. That claim is reclassified accordingly.

## 5. Status of every authoritative electrical magnitude

| result | status | where |
|---|---|---|
| ARCH_A 1-kW thickness sweep | **REPLAYED** (Phase 0G, post-fix) | `phase0g/crossover_hires_ARCH_A_fixedA.csv` |
| ARCH_B 1-kW thickness sweep | **REPLAYED** (Phase 0G, post-fix) | `phase0g/crossover_hires_ARCH_B_fixedB.csv` |
| ARCH_B corner robustness, 9 corners | **REPLAYED** | `phase0g/electrical_crossover_summary.csv` |
| footprint pair M=36/49 | **REPLAYED** | Phase 0G; −6.633 W for the larger footprint |
| placement, 3 lattices | **REPLAYED** | `phase0g/placement_corrected_1kw.csv` |
| full interconnect decomposition | **REPLAYED (this phase)** | `interconnect_decomposition_1kw.csv` |
| ET fixed point | **REPLAYED** | inside every run above |
| 240-W Phase-0E candidates | **REPLAYED (this phase)** | `replay240_candidates.csv` |
| Phase-0D-R absolute magnitudes | **HISTORICAL** — superseded on other grounds too (unsourced RDL stack, 4.8 mA via limit) | ledger |
| Phase-0E candidate table as published | **HISTORICAL** — superseded by `replay240_candidates.csv` | ledger |
| Phase-0F 1-kW tables as published | **HISTORICAL** — superseded by the Phase-0G/0H replays | ledger |

**No Phase-0D-R / 0E / 0F electrical magnitude remains "current" without having been replayed
or explicitly marked historical.**

## 6. A caveat that outranks the correction

Every 240-W case above uses `h_sub` = 0.2 or 0.5 mm and a ~5 mm tile. Phase 0F proved that
geometry unbuildable, and Sec. 12 of this phase pushes the minimum realizable substrate further
still, to 1.176–1.426 mm. **The corrected 240-W ranking is therefore a corrected ranking of
designs that cannot be built.** It is reported because the question asked was whether the
correction changes a published conclusion — it does — and not because the ranking is
actionable.
