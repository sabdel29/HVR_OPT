# REPRODUCE

How to re-derive the frozen results and re-check the manuscript.

---

## 0. Environment

The project Python and the CalculiX solver live in a private environment. The system
`python3` does **not** have the packages, and a different `ccx` earlier on `PATH` will cause
`Permission denied`. Always:

    export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH

Verify:

    which python ccx          # both under envs/etm/bin
    ccx -v                    # CalculiX Version 2.23

`pdflatex` and `bibtex` are system-wide at `/bin` and need nothing.

**Submodule.** The converter loss model is a separate repository:

    git submodule update --init --recursive

Without it, `scripts/phase0d/electrical.py` and the synthesis path cannot import
`HVR_FULL_OPT_EPC_V2`.

---

## 1. Fastest meaningful check (seconds)

    python scripts/phase0mr3c/audit_manuscript.py

Re-reads 82 numerical values out of the frozen CSV/JSON artifacts and checks each against
the manuscript text, plus near-miss typos, forbidden claims, terminology, float references
and citations. Expected final line: `MANUSCRIPT AUDIT PASSED`.

This is the check to run after *any* edit to the paper.

---

## 2. Rebuild the manuscript

    cd manuscript
    pdflatex ETM_DVPD_JOURNAL_MANUSCRIPT
    bibtex   ETM_DVPD_JOURNAL_MANUSCRIPT
    pdflatex ETM_DVPD_JOURNAL_MANUSCRIPT
    pdflatex ETM_DVPD_JOURNAL_MANUSCRIPT

Expect **15 pages, 0 errors, 0 undefined references, 0 overfull boxes, 25 references**.
`IEEEtran.cls` is in the folder, so this does not depend on the system TeX having it.

---

## 3. Regenerate the figures

    python scripts/phase0mr3c/make_manuscript_figures.py

Writes all eight `manuscript/figs/fig*.pdf` from the frozen artifacts. Safe to re-run; it
reads frozen data and recomputes nothing physical.

---

## 4. Re-derive the frozen results

Each script reads frozen inputs and **asserts** against frozen outputs, so none of them can
silently drift. Times are on 48 cores.

| step | command | ~time | writes |
|---|---|---|---|
| trace local-submodel inputs | `python scripts/phase0mr3c/trace_local_inputs.py` | sec | `local_submodel_inputs.csv` |
| final local solder response | `python scripts/phase0mr3c/run_final_local_response.py` | ~2 min | `final_local_response.csv` |
| CETOL robustness ladder | `python scripts/phase0mr3c/cetol_robustness.py` | ~4 min | `cetol_final_pair.csv` |
| α_GaN sensitivity | `python scripts/phase0mr3c/gan_alpha_sensitivity.py` | sec | `gan_alpha_sensitivity.csv` |
| stage timing breakdown | `python scripts/phase0mr3c/timing_from_replay.py` | sec | `timing_breakdown.json` |
| die-surface field for Fig. 6 | `python scripts/phase0mr3c/extract_die_field.py` | sec | `die_surface_field_*.csv` |

`trace_local_inputs.py` reproduces T_max, T_mean, die warpage and Δu_c exactly from the
stored fields before it derives anything, and stops if any differs.

### The full ETM replay

    python scripts/phase0mr3c/run_final_replay.py

Re-solves both architectures end to end: 3 electrical–thermal iterations each containing
3–4 fluid-coupled thermal FE sub-solves, then one thermoelastic solve after convergence.
**~135 s (Z1) and ~204 s (Z2)**, 48 cores. Writes `final_etm_replay.csv`.

Note the solver scratch this produces (`results/phase0mr/replay/`) is git-ignored and can
reach several GB.

---

## 5. Framework-level audits

    python scripts/phase0mr3/semantic_audit.py           # → 0 findings
    python scripts/phase0lr/cross_report_consistency.py  # → 58/58 checks pass
    python scripts/phase0m/pdf_text_inspect.py           # → ALL PDF TEXT CHECKS PASS
    python scripts/phase0mr3c/write_claim_audit.py       # regenerates the claim audit

`ETM_DVPD_CLAIM_AUDIT.md` is **generated** — edit the generator, never the output.

---

## 6. Tests

    python -m pytest tests/phase0mr3c -q     # ~47 tests, the manuscript guards
    python -m pytest tests/ -q               # full suite, ~800 tests, ~10 min

**Run test sessions one at a time.** `test_reports_regenerate_idempotently` rebuilds shared
report files and PDFs; running it concurrently with anything else produces a failure that
looks like a regression and is not. This has cost real debugging time more than once.

---

## 7. What is *not* reproducible from this repository

Excluded deliberately, with the reason:

| not here | why | how to get it back |
|---|---|---|
| ~36 GB of CalculiX `.dat`/`.frd`/`.inp` scratch | regenerable, and far too large to track | re-run the scripts above |
| 543 `.npy` mesh/displacement arrays (240 MB) | solver intermediates | re-run the sweep drivers |
| ANSYS `.aedtresults` trees | tool scratch | re-run in AEDT |
| publisher PDFs (`results/Papers/`, `results/phase0j/sources/`) | copyrighted, not ours to redistribute | fetch from the publishers; all are cited |
| the ~10 MB generated report PDFs | regenerable; the Markdown source **is** tracked | `python scripts/phase0mr3b/rebuild_reports.py` |
| CalculiX manual and source tarball | third party | upstream at dhondt.de |
| `.claude/` | internal tooling config and an internal endpoint | not needed |

Nothing in that list was deleted locally — it is simply untracked.
