# Phase-0F Sec.1 — Geometry Realizability Audit

## 1. The inconsistency, and why it could not be waved through

Phase 0B fixed the mechanical HVR tile at **150 µm**, tagged PROVISIONAL with the note
*"MUST be replaced by the HVR compiler stack height"*. Phase 0E found that the converter the
compiler actually selects contains a **500 µm** inductor and recorded the mismatch with the
remark that it *"does not affect trends"*. That remark was an assumption, not a result. This
audit tests it, and the first half of it is wrong: the geometry was never buildable.

## 2. Where each component physically lives

June-2026 Sec. II states the architecture explicitly:

> "high-side GaN switches ... flip-chipped to the RDL of the bottom substrate, while low-side
> switches (bottom layer), flying capacitors (middle layer), and inductors (top layer near the
> POLs) are embedded within the subsequent substrate power layers"

and

> "the number of power layers is ultimately determined by the number and size of components in
> the chosen VR topology and constrained by the capabilities of advanced packaging technologies"

So the VR cell is a **vertical stack of substrate power layers**, its height is set by its
components, and the TSV field runs beneath it from the substrate underside. The governing rule
is therefore

```
t_cell + h_tsv <= h_sub ,      h_tsv >= 50 um
```

| component | where it lives | height | provenance |
|---|---|---:|---|
| inductor | embedded in a substrate power layer (the selected part's own `category` is `silicon_interposer`) | **500 µm** | **SOURCED** — upstream `INDUCTOR_LIBRARY`, Rasheedi TCPMT 2026 |
| low-side GaN | embedded, bottom power layer | — | **OPEN** — the EPC table gives `Package(mm)` as lateral only ("LGA 2.5 x 1.5") |
| high-side GaN | flip-chipped to the bottom-substrate RDL | — | **OPEN**, same reason |
| flying capacitors | embedded, middle power layer | — | **OPEN** — no height field in the capacitor library |
| inter-layer RDL | between power layers | 10 µm | SOURCED (ECTC-2024) |
| TSV field | substrate underside up to the cell | h_sub − t_cell | derived |
| minimum TSV length | — | 50 µm | ASSUMPTION |

Because only the inductor height is sourced, the constraint is stated on the inductor as a
**necessary** condition. The two open heights can only make a combination *less* feasible, so
**every INFEASIBLE verdict below is robust to them**.

## 3. Height envelope

Three bounds are carried rather than inventing the two open values:

| bound | GaN layer | MLCC layer | t_cell with the 500 µm inductor |
|---|---:|---:|---:|
| optimistic | 0 µm (components co-located inside the tallest layer) | 0 µm | 520 µm |
| **nominal** | 100 µm | 100 µm | **720 µm** |
| pessimistic | 250 µm | 250 µm | 1020 µm |

## 4. How many library inductors actually fit

| h_sub | optimistic | nominal | pessimistic |
|---:|---:|---:|---:|
| **200 µm** | 1 of 11 | **0 of 11** | **0 of 11** |
| **500 µm** | 5 of 11 | 1 of 11 | **0 of 11** |
| 800 µm | 10 of 11 | 8 of 11 | 1 of 11 |
| 1200 µm | 10 of 11 | 10 of 11 | 10 of 11 |

## 5. Verdict on the geometry used by Phase 0B–0E

```
h_sub = 200 um  :  GEOMETRICALLY INFEASIBLE under every bound
h_sub = 500 um  :  GEOMETRICALLY INFEASIBLE under the nominal and pessimistic bounds
```

The selected converter's cell is 720 µm tall (nominal); a 200 µm substrate cannot contain it
at all, and a 500 µm substrate cannot either. **Both endpoints of the thickness sweep that
produced the "thicker is win/win/win" result across four phases are unbuildable with the
converter that sweep assumed.**

Under the optimistic bound a 500 µm substrate does admit a converter, but not that one: the
best design available from the fitting inductor set costs **27.375 W per VR at 25 °C against
4.248 W — 6.4× worse**. Thin substrates are not merely awkward for this architecture; they
force a fundamentally worse converter.

**The realizable substrate range for the selected converter begins near 800 µm.** Across
800–1500 µm the compiler selects the *same* design (N3K3KA2, `Shared_Core_UIC_250_nH`,
P_conv = 4.248 W/VR at 25 °C), which makes the thickness sweep a better-controlled experiment
than the original: only the substrate and the TSV length change.

## 6. Do the previous trend directions survive?

Re-run at the true cell height (t_tile = 720 µm) over the realizable range, 240 W, BC-A,
everything else unchanged:

| comparison | Phase 0B–0E (unbuildable geometry) | Phase 0F (realizable) | direction |
|---|---:|---:|---|
| thickness, thin → thick | −56.5 % warpage (200→500 µm) | **−81.9 %** (800→1500 µm) | **survives, stronger** |
| footprint, small → large | +87.9 % warpage | **+108.3 %** | **survives, stronger** |
| placement, distributed → edge | −41.5 % warpage | **−49.4 %** | **survives, stronger** |

All three **directions survive**, and all three magnitudes grow by 20–45 %. Energy balance
closes to ±0.000 % in every run, and the `real_dist` case reproduces `real_thick` to the last
digit (0.432 µm) as an internal consistency check.

**So the Phase-0E remark was half right and half wrong.** The trend directions do survive —
but that was an assumption, and it was made about a geometry that could not be built. The
magnitudes it produced were all wrong by tens of percent, and the substrate thicknesses it
swept were both impossible.

## 7. What this changes for Phase 0F

* The thickness axis is redefined: the realizable range is **800–1500 µm**, not 200–500 µm.
* The mechanical tile is **720 µm**, not 150 µm, so the CTE-mismatched inclusion is 4.8× thicker.
* Absolute warpage magnitudes from every earlier phase are superseded.
* A converter/substrate pair must now pass `check()` before it is simulated. No impossible
  geometry is meshed anywhere in Phase 0F.

## 8. Still open

* GaN and MLCC layer heights. The nominal bound is used for all Phase-0F work; the
  pessimistic bound would push the minimum realizable substrate to ~1070 µm and would not
  change any verdict, only the axis limits.
* Whether a real DVPD substrate would use one 800 µm layer or three stacked ~270 µm layers.
  The mechanical model treats the cell as a single homogeneous composite inclusion either way;
  a layered cell would differ in local stiffness distribution but not in total inclusion volume.
* Cavity vs fully-embedded construction. The audit assumes fully embedded, which is what June
  describes; a cavity-mounted inductor protruding above the substrate would relax the height
  constraint but introduce a free surface the mechanical model does not have.

Driver: `scripts/phase0f/geometry.py`, `scripts/phase0f/run_geometry_recheck.py`.
Data: `results/phase0f/geometry_recheck.csv`.
