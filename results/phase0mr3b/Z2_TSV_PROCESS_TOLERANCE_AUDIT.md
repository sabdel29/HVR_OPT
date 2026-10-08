# PHASE 0M-R3B SECTION 8 --- IS THE ARCH_Z2 TSV MARGIN PROCESS-QUALIFIED?

**No. It is parametric.** No manufacturing tolerance for this process was sourced from this host, so the honest question is inverted: rather than assert a margin against an assumed tolerance, report the tolerance each diameter can absorb before the sourced AR <= 10 rule is violated.

| parameter | provenance | what the search found |
|---|---|---|
| etched depth tolerance | **OPEN** | OpenAlex: 338 hits on DRIE depth control, none giving a process tolerance for a 300 um TSV; the two on-point reviews are MDPI and every route to their full text returns a block page from this host |
| via diameter tolerance | **OPEN** | same searches; no numeric diameter tolerance found |
| liner / plating tolerance | **OPEN** | 7 hits, none giving a tolerance band |
| taper / scallop | **OPEN** | DRIE taper papers found but for MEMS geometries at other scales; no transferable tolerance |
| aspect-ratio process limit | **SOURCE_BACKED** | AR <= 10 is the framework's own source-backed hard rule and is unchanged |
| overlay / alignment | **OPEN** | no source |
| pitch / KOZ tolerance | **SOURCE_BACKED** | s_min = 30 um, framework SOURCE_BACKED |

## What each diameter can absorb

Worst case shrinks the diameter and deepens the via together, so `AR_worst = L(1+t) / (d(1-t)) <= 10` gives `t = (10d - L) / (10d + L)`.

| d | AR | M_AR | max symmetric tolerance before AR = 10 | passes the 2 % parametric bound |
|---|---|---|---|---|
| 30 um | 10.000 | 1.000 | **0.00 %** | NO |
| 32 um | 9.375 | 1.067 | **3.23 %** | yes |
| 34 um | 8.823 | 1.133 | **6.25 %** | yes |
| 36 um | 8.333 | 1.200 | **9.09 %** | yes |

30 um can absorb nothing: it sits exactly on the rule. 32 um can absorb 3.23 %, 34 um 6.25 %, 36 um 9.09 %.

**Licensed wording:** *32 um is PARAMETRICALLY MARGINED at a 2 % symmetric tolerance and is NOT process-qualified.* The phrase "process margin closed" is not available until a real tolerance is sourced.

32 um remains the smallest evaluated diameter with positive margin, so it remains preferred over 30 um on margin and over 34/36 um on via count -- a design-side preference, not a qualification.
