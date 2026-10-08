# Phase 0I Sec. 4 — Rail-aware power paths, per architecture

## 1. "The TSV carries 48 V" and "the TSV carries 1 V" are both wrong as global statements

Which rail crosses the substrate is set by **where the conversion happens relative to the
substrate**, and that is an architecture choice, not a property of the technology.

| architecture | conversion happens | rail on the TSV | current on the TSV |
|---|---|---|---|
| Z1 EMBEDDED | inside the substrate, above the via field | **HV** | 23.43 A |
| Z2 BACKSIDE | below the substrate | **LV** | **1000.00 A** |
| Z4 POWER DIE | above the substrate | **HV** | 23.43 A |
| Z5 2.5D | above the substrate, laterally | **HV** | 23.43 A |

A factor of **42.7 in current**, hence **1822 in I²**, decided purely by z-placement.

## 2. Full segment chains

Every segment is SYSTEM scope under the Phase-0H guard, so a per-regulator term cannot enter
these totals (DEFECT #30). Machine-readable: `power_paths_by_architecture.csv`.

### Z1 EMBEDDED
`board → BGA (HV, 23.4 A) → TSV through h_sub − t_cell (HV, 23.4 A) → conversion inside the
power layers → microbump (LV, 1000 A, 10 µm) → RDL spreading under the die (LV)`

### Z2 BACKSIDE
`board → BGA (HV, 23.4 A, short) → conversion on the backside chiplet → TSV through the FULL
h_sub (LV, 1000 A) → microbump (LV) → RDL under the die (LV)`

### Z4 POWER DIE
`board → BGA (HV) → TSV through the FULL h_sub (HV, 23.4 A) → conversion on the power die →
hybrid pads (LV, 1000 A, 10 µm — the shortest possible 1 V path) → power-die RDL (LV)`

### Z5 2.5D LATERAL
`board → BGA (HV) → TSV (HV) → conversion beside the die → LONG lateral interposer RDL (LV,
1000 A) → microbump (LV)`

## 3. Losses at each architecture's electrically best realizable point

| architecture | h* (mm) | n_TSV allocated | P_TSV | P_RDL | P_BGA | P_µbump | **P_total** |
|---|---|---|---|---|---|---|---|
| Z1 EMBEDDED | 1.30 | 332 | 0.0098 | 0.6451 | 0.1139 | 0.0566 | **126.090 W** |
| Z4 POWER DIE | 0.30 | 332 | 0.0397 | 0.6451 | 0.1139 | 0.0566 | **126.120 W** |
| Z2 BACKSIDE | 0.30 | **14 148** | 1.6979 | 0.6451 | 0.1139 | 0.0566 | **127.778 W** |
| Z5 2.5D | 0.30 | 332 | 0.0397 | **768.0721** | 0.1139 | 0.0566 | **893.547 W** |

## 4. An unplanned cross-check of the allocation model

Z2 puts 1000 A on the via field, and the allocator returns **14 148 TSVs**. June-2026
Table III independently reports **14 148 TSVs** for PL3 in its optimised 48 V→1 V allocation.

The two numbers were produced by different machinery — the reference paper's own optimiser
and this project's `allocate()` under the source-backed current density — and they agree
exactly. That is a meaningful validation of the allocation rule at the one point where the
comparison is possible.

## 5. What the paths explain

* **Z1's electrical advantage is geometric, not architectural.** At `h_sub` = 1.30 mm with a
  1.226 mm embedded cell, the via field is only **74 µm** long, so `P_TSV` = 9.8 mW. Z4 must
  run the same 23.4 A through the full 300 µm and pays 39.7 mW. The whole Z1-versus-Z4
  difference is 30 mW on 126 W.
* **Z2's penalty is unavoidable, not tunable.** Its 1.698 W of via loss is what it costs to
  carry 1000 A vertically, and it grows linearly with substrate thickness (1.698 W at 0.30 mm
  to 11.319 W at 2.00 mm). Z2 must be thin; it has no choice.
* **Z5 is the control that proves the concept.** 768 W of lateral RDL loss at 52.8 %
  efficiency is what DVPD exists to avoid, and it is the reason a vertical architecture is
  worth its packaging difficulty at all.
