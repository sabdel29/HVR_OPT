#!/usr/bin/env python3
"""Phase-0M Part 0-D -- ONE authoritative specimen-count provenance table.

Four different specimen counts are live in this repository and they have been quoted against
each other. They are not competing estimates of the same thing: each answers a different
question, and three of the four are not the current design. This file is the only place the
distinction is defined; everything else must cite it.
"""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

ROWS = [
    dict(phase="0K-R", n_per_cell=34, cells=4, packages=136, status="HISTORICAL",
         model="M0_COARSE", solver_control="DEFAULT (dt0=1e-5, dtmax=10 s)", D=1.4395,
         energy_metric="DEFECT #46 present (inflated ~18.5 %)",
         question="How many packages does a Z1-vs-Z2 discrimination need, at the solver "
                  "settings and constitutive model Phase 0K-R actually ran?",
         superseded_by="0L; the solver settings were under-integrated",
         evidence="results/phase0kr/PHASE0KR_EXPERIMENTAL_CLOSURE.md, "
                  "results/phase0l/method_reproduction_check.csv"),
    dict(phase="0L", n_per_cell=68, cells=4, packages=272, status="HISTORICAL",
         model="M1_NHI (worst case across admitted models)",
         solver_control="TIGHT (dt0=1e-8, dtmax=10 s)", D=1.4001,
         energy_metric="DEFECT #46 present (inflated ~18.5 %)",
         question="What is the WORST-CASE requirement across every constitutive model "
                  "admitted after the Phase-0L constitutive audit?",
         superseded_by="0L-R; a worst-case envelope over models is not a design point, and "
                       "the energy metric it used was inflated",
         evidence="results/phase0l/PHASE0L_HIGH_STRESS_CONSTITUTIVE_GATE.md Sec. 6"),
    dict(phase="0L-R", n_per_cell=48, cells=4, packages=192, status="CURRENT / CONDITIONAL",
         model="M1 (the selected model)", solver_control="TIGHT (dt0=1e-8, dtmax=10 s)",
         D=1.7256, energy_metric="DEFECT #46 fixed; Phase-0M ME route agrees to 0.80 %",
         question="How many packages does the SELECTED model require at corrected solver "
                  "settings and a corrected energy integral?",
         superseded_by="-- current, but CONDITIONAL: not to be frozen while the constitutive "
                       "extrapolation dominates the uncertainty budget",
         evidence="results/phase0lr/PHASE0LR_CONSTITUTIVE_AND_REPORT_CLOSURE.md Sec. 6, "
                  "results/phase0lr/sample_count_vs_simulation_uncertainty.csv"),
    dict(phase="0L-R counterfactual", n_per_cell=16, cells=4, packages=64,
         status="NUMERICS-ONLY COUNTERFACTUAL", model="M0_COARSE (the INCUMBENT physics)",
         solver_control="TIGHT (dt0=1e-8, dtmax=10 s)", D=1.7174,
         energy_metric="DEFECT #46 fixed",
         question="What would Phase 0K-R's own model have required if ONLY the numerics were "
                  "corrected and the physics left untouched?",
         superseded_by="-- not a design; it exists to separate the numerical correction from "
                       "the constitutive one",
         evidence="results/phase0lr/numerics_vs_constitutive_decomposition.csv"),
]

MD = """# PHASE 0M PART 0-D --- SPECIMEN-COUNT PROVENANCE

**Authoritative.** Four specimen counts are live in this repository. They are not competing
estimates of one quantity; each answers a different question and three of the four are not the
current design. Any document quoting a specimen count must name which row it means.

| Phase | n / cell | cells | packages | status | model | solver control | D | energy metric |
|---|---|---|---|---|---|---|---|---|
{table}

## What each row answers

{detail}

## The one-line summary

* **Current conditional estimate: 48 per cell, 192 packages** (Phase 0L-R, model M1, corrected
  solver control, DEFECT #46 fixed). CONDITIONAL, and explicitly **not frozen**.
* **34 / 136** is HISTORICAL (Phase 0K-R). It is reproducible at the settings it used and is
  not the current design.
* **68 / 272** is HISTORICAL (Phase 0L). It is a worst-case envelope across models, not a
  design point, and it was computed on an inflated energy metric.
* **16 / 64** is a COUNTERFACTUAL. It isolates the numerical correction from the constitutive
  one and is not a design.

## Why the current number moved, decomposed

The requirement moved for two independent reasons and the brief requires them separated:

| step | change | n / cell | cause |
|---|---|---|---|
| Phase-0K-R design | -- | 34 | baseline |
| correct the integration only | D 1.4395 -> 1.7174 | 34 -> 16 | **NUMERICS.** Same physics. |
| then correct the constitutive model | D 1.7174 -> 1.7256 | 16 -> 48 | **PHYSICS.** |

D moves **+19.3 %** from integration control and **+0.5 %** from the constitutive model, so the
discrimination ratio itself is overwhelmingly a numerics story. The specimen count is not: it
falls to 16 on numerics and then rises to 48 on the model, because n depends on the spread in
`w/eps` across the two test cells and not on D at a single cell.

## The count is not the binding term

The ceiling on the discrimination index is **Z = 3.61 against a target of 3.0**, and that
ceiling is set by the **simulation-uncertainty floor**, not by the specimen count. Halving the
simulation uncertainty (0.06 -> 0.03 per-architecture standard error) cuts the campaign from
192 packages to 72. No number of boards can lower the floor. See
`results/phase0lr/sample_count_vs_simulation_uncertainty.csv` and
`results/phase0lr/MATERIAL_TEST_VS_PACKAGE_TEST_VALUE.md`.
"""


def main() -> int:
    with open(OUT / "specimen_count_provenance.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0]))
        w.writeheader()
        w.writerows(ROWS)
    tbl = "\n".join(
        f"| {r['phase']} | **{r['n_per_cell']}** | {r['cells']} | **{r['packages']}** | "
        f"{r['status']} | `{r['model']}` | {r['solver_control']} | {r['D']:.4f} | "
        f"{r['energy_metric']} |" for r in ROWS)
    det = "\n\n".join(
        f"**{r['phase']} --- {r['status']}.** {r['question']}\n\n"
        f"* Superseded by: {r['superseded_by']}\n"
        f"* Evidence: `{r['evidence']}`" for r in ROWS)
    (OUT / "SPECIMEN_COUNT_PROVENANCE.md").write_text(
        MD.format(table=tbl, detail=det))
    print(f"wrote {OUT/'SPECIMEN_COUNT_PROVENANCE.md'} and .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
