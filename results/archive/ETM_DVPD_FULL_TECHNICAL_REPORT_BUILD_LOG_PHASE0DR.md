# PDF Build Log --- ETM_DVPD_FULL_TECHNICAL_REPORT

Built 2026-09-05 18:48 by `scripts/phase0dr/build_pdf.py`.
Verification: **PASSED** (21/21 checks).

## Command

```
pandoc .report_pdf_source.md -o ETM_DVPD_FULL_TECHNICAL_REPORT.pdf --pdf-engine=xelatex --toc --toc-depth=2 -V geometry:margin=2.1cm -V fontsize=10pt -V colorlinks=true -V linkcolor=RoyalBlue -V urlcolor=RoyalBlue --resource-path /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results
```

## Toolchain

| tool | version |
|:--|:--|
| pandoc | pandoc 2.0.6 |
| TeX | XeTeX 3.14159265-2.6-0.99999 (TeX Live 2018) |
| poppler | pdftotext version 20.11.0 |

## Sources

| file | role | sha256[:16] |
|:--|:--|:--|
| `results/ETM_DVPD_FULL_TECHNICAL_REPORT.md` | Markdown deliverable (940 lines) | `715de7a0c129b31e` |
| `scripts/phase0dr/build_full_report.py` | section generator | `1fc6ef876c663f27` |
| `scripts/phase0dr/build_full_report2.py` | section generator | `d1e9a13d58674d89` |
| `scripts/phase0dr/build_full_report3.py` | section generator | `5d868354be5f9383` |
| `scripts/phase0dr/build_full_report4.py` | section generator | `bf1f5a1ccc5eef46` |
| `scripts/phase0dr/build_full_report5.py` | section generator | `5f6843ccef104ddc` |

## Figures embedded

| # | file | kB | caption |
|--:|:--|--:|:--|
| 1 | `results/phase0dr/FIG_H_phase0d_vs_0dr.png` | 84 | **Figure 1.** What the architecture-aware correction changed |
| 2 | `results/phase0b/PHASE0B_DECISIVE_FIGURE_BC_A.png` | 320 | **Figure 2.** Phase-0B decisive figure. Identical converter  |
| 3 | `results/phase0c/PHASE0C_DVPD_LEVER_FIGURE.png` | 383 | **Figure 3.** Phase-0C lever ranking. Red = DVPD-specific, b |
| 4 | `results/phase0d/PHASE0D_ET_VS_ETM_PARETO.png` | 200 | **Figure 4.** Phase-0D ET vs ETM Pareto fronts. Superseded b |
| 5 | `results/phase0dr/FIG_A_power_paths.png` | 128 | **Figure 5.** Architecture-aware power paths. Which rail tra |
| 6 | `results/phase0dr/FIG_C_hv_lv_thickness.png` | 159 | **Figure 6.** HV-TSV vs LV-TSV thickness chain. The LV penal |
| 7 | `results/phase0dr/FIG_B_loss_decomposition.png` | 95 | **Figure 7.** Interconnect loss decomposition. Lateral RDL,  |
| 8 | `results/phase0dr/FIG_F_footprint.png` | 134 | **Figure 8.** Footprint tradeoff after the PPDN correction.  |
| 9 | `results/phase0dr/FIG_G_pareto_corrected.png` | 104 | **Figure 9.** Corrected ET vs ETM Pareto. ET front is a sing |

## Output

```
Title:          Electrothermal–Mechanical Co-Design of Distributed Vertical Power Delivery: Model Development, Falsification Gates, and Coupled Architecture Results
Author:         HVR_Journal_System_Level / ETM-DVPD — HiPerCAS Lab, University of Illinois Chicago
Creator:        LaTeX with hyperref package
Producer:       XeTeX 0.99999
CreationDate:   Sat Sep  5 18:48:57 2026 CDT
Tagged:         no
UserProperties: no
Suspects:       no
Form:           none
JavaScript:     no
Pages:          28
Encrypted:      no
Page size:      612 x 792 pts (letter)
Page rot:       0
File size:      1804799 bytes
Optimized:      no
PDF version:    1.5
```

## Source repairs applied by the build

* blank line inserted before **0 headings** and **0 table header rows** --- without it pandoc (and GitHub) swallow the construct into the preceding paragraph and emit literal `#` / `|` text. The repair is written back to the Markdown, so both deliverables are correct.
* **12 Unicode glyphs** absent from Latin Modern (sigma, rho, eta, alpha, theta, nu, le, approx, subscript-1) replaced with math-mode equivalents for the PDF pass only; code fences, inline code and existing `$math$` are protected. Without this xelatex drops the characters **silently**.

## Verification checks

| check | result | detail |
|:--|:--|:--|
| pdf exists | PASS | -- |
| pdf non-trivial size | PASS | 1.80 MB |
| no glyphs dropped by the font | PASS | 0 dropped |
| every markdown heading typeset as a section | PASS | 33 in md, 33 in tex |
| no literal '#' heading leaked | PASS | -- |
| every markdown table typeset as a table | PASS | 16 in md, 16 in tex |
| no table rows leaked as literal pipes | PASS | 0 leaked cells |
| all figure files exist | PASS | 9 figures; missing [] |
| figures embedded in pdf | PASS | 18 image objects / 9 figures |
| every figure has a caption | PASS | no empty alt text |
| page count plausible | PASS | 28 pages |
| text layer searchable | PASS | 51156 chars extracted |
| table of contents present | PASS | -- |
| no unresolved image markup | PASS | -- |
| no literal latex leaked into text | PASS | -- |
| corrected result present: '16.2' | PASS | -- |
| corrected result present: '188.8' | PASS | -- |
| corrected result present: 'INFEASIBLE' | PASS | -- |
| corrected result present: 'Phase-0D-R' | PASS | -- |
| stale value '2.03' never presented as final | PASS | 3 mentions, 0 without retraction context |
| stale value '1.08' never presented as final | PASS | 4 mentions, 0 without retraction context |

## Warnings from the final pass

None.

## Defects this build step found and fixed

These were introduced by the report generators and caught by the checks above, not by reading the PDF:

1. **20 of 33 headings were not headings.** A `\newpage` or a paragraph directly above an ATX heading absorbed it; the TOC listed 13 entries and the text showed a literal `#`. Now checked by comparing heading counts in Markdown and LaTeX.
2. **4 of 16 tables were not tables** --- 142 cells rendered as literal `|` text. Same missing-blank-line cause. Now checked by comparing table counts and asserting zero `\textbar` leakage.
3. **9 glyph classes silently dropped** by Latin Modern. Now a hard failure.
4. **`$\le$0.72` was not parsed as math** --- pandoc ignores a closing `$` followed by a digit, so the raw macro reached the text layer. The sanitiser now inserts a separating space.
