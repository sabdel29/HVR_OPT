# Build log --- current-framework audit report

| item | value |
|---|---|
| Markdown | `ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md` (1033 lines, 81973 chars) |
| PDF | `ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf` (52 pages, 0.75 MB) |
| figures | 8 |
| headings | 55 |
| glyph substitutions | 0 |
| blank lines inserted before table headers | 0 |
| blank lines inserted before headings | 0 |
| pandoc | pandoc 2.0.6 |
| TeX | XeTeX 3.14159265-2.6-0.99999 (TeX Live 2018) |
| checks | **106/106 passed** |

## Command

```
pandoc .audit_report_source.md -o ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.pdf --pdf-engine=xelatex --toc --toc-depth=2 -V geometry:margin=2.1cm -V fontsize=10pt -V colorlinks=true -V linkcolor=RoyalBlue -V urlcolor=RoyalBlue --resource-path /home/beams0/MGHARIB/Mohamed_stuff/HVR_OPT/results
```

## Checks

| # | check | result | detail |
|---|---|---|---|
| 1 | no unreplaced placeholders | PASS |  |
| 2 | no literal escaped dollars | PASS |  |
| 3 | every non-ASCII glyph is proven or converted | PASS |  |
| 4 | inline math delimiters balanced on every line | PASS | [] |
| 5 | all 8 figure files exist | PASS |  |
| 6 | no pandoc missing-resource warning | PASS |  |
| 7 | PDF page count plausible for a 40-70 page report | PASS | 52 pages |
| 8 | PDF text extraction non-empty | PASS | 132772 chars |
| 9 | no page extracts as empty text | PASS | pages [] |
| 10 | all 8 figures embedded as images | PASS | 16 images |
| 11 | all 55 headings present in the PDF text | PASS |  |
| 12 | structure probe found comparable section count | PASS | tex 55 vs md 55 |
| 13 | TOC present and lists the last section | PASS |  |
| 14 | no raw Markdown table delimiter rows in the PDF | PASS | [] |
| 15 | no unrendered image syntax in the PDF text | PASS |  |
| 16 | no absolute figure path visible to the reader | PASS |  |
| 17 | no literal ATX hashes leaked into the PDF text | PASS |  |
| 18 | no stray control characters | PASS | [] |
| 19 | self-test: creep law stated as a function of total von Mises stress | PASS |  |
| 20 | self-test not exonerated: creep law stated as a function of total von Mises stress | PASS | an exoneration term appears inside the violating sentence itself |
| 21 | self-test: card called measured data for the correct alloy | PASS |  |
| 22 | self-test not exonerated: card called measured data for the correct alloy | PASS | an exoneration term appears inside the violating sentence itself |
| 23 | self-test: stress window called the joint's operating range | PASS |  |
| 24 | self-test not exonerated: stress window called the joint's operating range | PASS | an exoneration term appears inside the violating sentence itself |
| 25 | self-test: card described as near its calibrated range | PASS |  |
| 26 | self-test not exonerated: card described as near its calibrated range | PASS | an exoneration term appears inside the violating sentence itself |
| 27 | self-test: extrapolation asserted to be common mode without a test | PASS |  |
| 28 | self-test not exonerated: extrapolation asserted to be common mode without a test | PASS | an exoneration term appears inside the violating sentence itself |
| 29 | self-test: Yuan Table 26 cited | PASS |  |
| 30 | self-test not exonerated: Yuan Table 26 cited | PASS | an exoneration term appears inside the violating sentence itself |
| 31 | self-test: Yuan Table 27 or 31 cited | PASS |  |
| 32 | self-test not exonerated: Yuan Table 27 or 31 cited | PASS | an exoneration term appears inside the violating sentence itself |
| 33 | self-test: rate-independent plasticity claimed to be present | PASS |  |
| 34 | self-test not exonerated: rate-independent plasticity claimed to be present | PASS | an exoneration term appears inside the violating sentence itself |
| 35 | self-test: absolute life stated as a bare fact | PASS |  |
| 36 | self-test not exonerated: absolute life stated as a bare fact | PASS | an exoneration term appears inside the violating sentence itself |
| 37 | self-test: experiment called frozen | PASS |  |
| 38 | self-test not exonerated: experiment called frozen | PASS | an exoneration term appears inside the violating sentence itself |
| 39 | self-test: G2 claimed tested | PASS |  |
| 40 | self-test not exonerated: G2 claimed tested | PASS | an exoneration term appears inside the violating sentence itself |
| 41 | self-test: optimizer claimed permitted | PASS |  |
| 42 | self-test not exonerated: optimizer claimed permitted | PASS | an exoneration term appears inside the violating sentence itself |
| 43 | self-test: Z2/Z1 = 1.21-1.38 called validated | PASS |  |
| 44 | self-test not exonerated: Z2/Z1 = 1.21-1.38 called validated | PASS | an exoneration term appears inside the violating sentence itself |
| 45 | self-test: experiment called ready to execute | PASS |  |
| 46 | self-test not exonerated: experiment called ready to execute | PASS | an exoneration term appears inside the violating sentence itself |
| 47 | self-test: 34 specimens called sufficient | PASS |  |
| 48 | self-test not exonerated: 34 specimens called sufficient | PASS | an exoneration term appears inside the violating sentence itself |
| 49 | self-test: creep model called validated to 100 MPa | PASS |  |
| 50 | self-test not exonerated: creep model called validated to 100 MPa | PASS | an exoneration term appears inside the violating sentence itself |
| 51 | self-test: creep data called SAC305 | PASS |  |
| 52 | self-test not exonerated: creep data called SAC305 | PASS | an exoneration term appears inside the violating sentence itself |
| 53 | self-test: high-stress error said to cancel | PASS |  |
| 54 | self-test not exonerated: high-stress error said to cancel | PASS | an exoneration term appears inside the violating sentence itself |
| 55 | self-test: A sigma^n called the current combined VISCO law | PASS |  |
| 56 | self-test not exonerated: A sigma^n called the current combined VISCO law | PASS | an exoneration term appears inside the violating sentence itself |
| 57 | self-test: Arrhenius attributed to CalculiX | PASS |  |
| 58 | self-test not exonerated: Arrhenius attributed to CalculiX | PASS | an exoneration term appears inside the violating sentence itself |
| 59 | self-test: local reliability model called fully validated | PASS |  |
| 60 | self-test not exonerated: local reliability model called fully validated | PASS | an exoneration term appears inside the violating sentence itself |
| 61 | self-test: N_required called the only remaining blocker | PASS |  |
| 62 | self-test not exonerated: N_required called the only remaining blocker | PASS | an exoneration term appears inside the violating sentence itself |
| 63 | final Markdown: creep law stated as a function of total von Mises stress | PASS |  |
| 64 | final Markdown: card called measured data for the correct alloy | PASS |  |
| 65 | final Markdown: stress window called the joint's operating range | PASS |  |
| 66 | final Markdown: card described as near its calibrated range | PASS |  |
| 67 | final Markdown: extrapolation asserted to be common mode without a test | PASS |  |
| 68 | final Markdown: Yuan Table 26 cited | PASS |  |
| 69 | final Markdown: Yuan Table 27 or 31 cited | PASS |  |
| 70 | final Markdown: rate-independent plasticity claimed to be present | PASS |  |
| 71 | final Markdown: absolute life stated as a bare fact | PASS |  |
| 72 | final Markdown: experiment called frozen | PASS |  |
| 73 | final Markdown: G2 claimed tested | PASS |  |
| 74 | final Markdown: optimizer claimed permitted | PASS |  |
| 75 | final Markdown: Z2/Z1 = 1.21-1.38 called validated | PASS |  |
| 76 | final Markdown: experiment called ready to execute | PASS |  |
| 77 | final Markdown: 34 specimens called sufficient | PASS |  |
| 78 | final Markdown: creep model called validated to 100 MPa | PASS |  |
| 79 | final Markdown: creep data called SAC305 | PASS |  |
| 80 | final Markdown: high-stress error said to cancel | PASS |  |
| 81 | final Markdown: A sigma^n called the current combined VISCO law | PASS |  |
| 82 | final Markdown: Arrhenius attributed to CalculiX | PASS |  |
| 83 | final Markdown: local reliability model called fully validated | PASS |  |
| 84 | final Markdown: N_required called the only remaining blocker | PASS |  |
| 85 | PDF-extracted text: creep law stated as a function of total von Mises stress | PASS |  |
| 86 | PDF-extracted text: card called measured data for the correct alloy | PASS |  |
| 87 | PDF-extracted text: stress window called the joint's operating range | PASS |  |
| 88 | PDF-extracted text: card described as near its calibrated range | PASS |  |
| 89 | PDF-extracted text: extrapolation asserted to be common mode without a test | PASS |  |
| 90 | PDF-extracted text: Yuan Table 26 cited | PASS |  |
| 91 | PDF-extracted text: Yuan Table 27 or 31 cited | PASS |  |
| 92 | PDF-extracted text: rate-independent plasticity claimed to be present | PASS |  |
| 93 | PDF-extracted text: absolute life stated as a bare fact | PASS |  |
| 94 | PDF-extracted text: experiment called frozen | PASS |  |
| 95 | PDF-extracted text: G2 claimed tested | PASS |  |
| 96 | PDF-extracted text: optimizer claimed permitted | PASS |  |
| 97 | PDF-extracted text: Z2/Z1 = 1.21-1.38 called validated | PASS |  |
| 98 | PDF-extracted text: experiment called ready to execute | PASS |  |
| 99 | PDF-extracted text: 34 specimens called sufficient | PASS |  |
| 100 | PDF-extracted text: creep model called validated to 100 MPa | PASS |  |
| 101 | PDF-extracted text: creep data called SAC305 | PASS |  |
| 102 | PDF-extracted text: high-stress error said to cancel | PASS |  |
| 103 | PDF-extracted text: A sigma^n called the current combined VISCO law | PASS |  |
| 104 | PDF-extracted text: Arrhenius attributed to CalculiX | PASS |  |
| 105 | PDF-extracted text: local reliability model called fully validated | PASS |  |
| 106 | PDF-extracted text: N_required called the only remaining blocker | PASS |  |
